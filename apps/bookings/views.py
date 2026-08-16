from datetime import datetime

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.notifications.models import NotificationLog
from apps.notifications.services import notify
from apps.stadiums.models import Stadium
from apps.wallet.services import InsufficientFunds

from . import services
from .models import ACTIVE_PAYMENT_STATUSES, Booking, Match, MatchChatMessage, MatchResult
from .serializers import (
    BookingSerializer,
    ChatMessageInputSerializer,
    ChatMessageSerializer,
    InviteToMatchSerializer,
    JoinMatchSerializer,
    MatchCreateSerializer,
    MatchResultInputSerializer,
    ScheduledMatchSerializer,
)


class JoinMatchView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        match = get_object_or_404(Match, pk=pk)
        serializer = JoinMatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            bookings = services.join_match(
                request.user, match, data["mode"], data["friend_ids"], data["pay_mode"]
            )
        except (services.BookingError, InsufficientFunds) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(BookingSerializer(bookings, many=True).data, status=status.HTTP_201_CREATED)


class InviteToMatchView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        match = get_object_or_404(Match, pk=pk)
        serializer = InviteToMatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            bookings = services.invite_to_match(request.user, match, serializer.validated_data["friend_ids"])
        except services.BookingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(BookingSerializer(bookings, many=True).data, status=status.HTTP_201_CREATED)


class MatchCreateView(APIView):
    """Organizers create ad-hoc matches at an existing stadium."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != Role.ORGANIZER:
            return Response(
                {"detail": "Only organizers can create matches."}, status=status.HTTP_403_FORBIDDEN
            )
        serializer = MatchCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        stadium = get_object_or_404(Stadium, pk=data["stadium_id"], is_active=True)
        try:
            match = services.create_match(
                request.user,
                stadium,
                data["date"],
                data["start_time"],
                data["end_time"],
                data["capacity"],
                data.get("price_per_seat"),
            )
        except IntegrityError:
            return Response(
                {"detail": "This stadium already has a match at that date and time."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(ScheduledMatchSerializer(match, context={"request": request}).data, status=status.HTTP_201_CREATED)


class AcceptSplitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        try:
            booking = services.accept_split(booking, request.user)
        except (services.BookingError, InsufficientFunds) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(BookingSerializer(booking).data)


class CancelBookingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        try:
            booking = services.cancel_booking(booking, request.user)
        except services.BookingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(BookingSerializer(booking).data)


class MyMatchesView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ScheduledMatchSerializer
    pagination_class = None

    def get_queryset(self):
        qs = Match.objects.filter(
            bookings__user=self.request.user, bookings__payment_status__in=ACTIVE_PAYMENT_STATUSES
        ).select_related("stadium").prefetch_related("bookings", "result").distinct()

        filter_ = self.request.query_params.get("filter", "all")
        if filter_ == "finished":
            qs = qs.filter(status=Match.Status.FINISHED)
        elif filter_ == "joined":
            qs = qs.exclude(status=Match.Status.FINISHED)

        month = self.request.query_params.get("month")
        if month:
            try:
                year, mon = (int(part) for part in month.split("-"))
            except ValueError:
                raise ValidationError({"month": "Expected YYYY-MM."})
            qs = qs.filter(date__year=year, date__month=mon)
        return qs


class NextMatchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        candidates = (
            Match.objects.filter(
                bookings__user=request.user,
                bookings__payment_status__in=ACTIVE_PAYMENT_STATUSES,
                status__in=(Match.Status.WAITING, Match.Status.CONFIRMED),
                date__gte=now.date(),
            )
            .select_related("stadium")
            .prefetch_related("bookings")
            .order_by("date", "start_time")
            .distinct()[:10]
        )
        for match in candidates:
            starts_at = timezone.make_aware(datetime.combine(match.date, match.start_time))
            if starts_at > now:
                return Response(
                    {
                        "match": ScheduledMatchSerializer(match, context={"request": request}).data,
                        "starts_at": starts_at.isoformat(),
                    }
                )
        return Response(None)


class MatchDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ScheduledMatchSerializer
    queryset = Match.objects.all()


class MatchResultView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        match = get_object_or_404(Match, pk=pk)
        can_enter = request.user.is_staff or match.bookings.filter(
            user=request.user, invited_by=request.user, payment_status__in=ACTIVE_PAYMENT_STATUSES
        ).exists()
        if not can_enter:
            return Response(
                {"detail": "Only the organizer or staff can enter a result."},
                status=status.HTTP_403_FORBIDDEN,
            )

        starts_at = timezone.make_aware(datetime.combine(match.date, match.start_time))
        if timezone.now() < starts_at:
            return Response(
                {"detail": "The match has not started yet."}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = MatchResultInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        for item in data["participants"]:
            Booking.objects.filter(
                id=item["booking_id"], match=match, payment_status__in=ACTIVE_PAYMENT_STATUSES
            ).update(
                personal_result=item["result"],
                is_motm=item.get("is_motm", False),
                goals=item.get("goals"),
                assists=item.get("assists"),
                rating=item.get("rating"),
            )

        match.status = Match.Status.FINISHED
        match.save(update_fields=["status"])

        # Booking results must be persisted before this save — gamification listens for
        # MatchResult.post_save and reads each booking's personal_result/goals/assists.
        MatchResult.objects.update_or_create(
            match=match, defaults={"score": data["score"], "entered_by": request.user}
        )

        for booking in match.bookings.filter(payment_status__in=ACTIVE_PAYMENT_STATUSES).select_related("user"):
            if booking.is_motm:
                notify(booking.user, NotificationLog.NotificationType.BADGE_UNLOCKED, badge_title="Man of the Match")

        return Response(ScheduledMatchSerializer(match, context={"request": request}).data)


class MatchChatView(APIView):
    """Polling-based group chat for a match's players.

    GET  /api/matches/{pk}/chat?after=<iso>  — messages after the given timestamp (ascending, max 100)
    POST /api/matches/{pk}/chat {text}       — send a message
    """

    permission_classes = [IsAuthenticated]

    def _get_match_for_player(self, request, pk):
        match = get_object_or_404(Match, pk=pk)
        is_player = match.bookings.filter(
            user=request.user, payment_status__in=ACTIVE_PAYMENT_STATUSES
        ).exists()
        if not is_player:
            return match, Response(
                {"detail": "Only players in this match can use its chat."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return match, None

    def get(self, request, pk):
        match, error = self._get_match_for_player(request, pk)
        if error:
            return error
        qs = MatchChatMessage.objects.filter(match=match).select_related("sender")
        after = request.query_params.get("after")
        if after:
            after_dt = parse_datetime(after)
            if not after_dt:
                return Response({"detail": "Invalid 'after' timestamp."}, status=status.HTTP_400_BAD_REQUEST)
            if timezone.is_naive(after_dt):
                after_dt = timezone.make_aware(after_dt)
            qs = qs.filter(created_at__gt=after_dt)
        messages = list(qs.order_by("created_at")[:100])
        return Response(ChatMessageSerializer(messages, many=True, context={"request": request}).data)

    def post(self, request, pk):
        match, error = self._get_match_for_player(request, pk)
        if error:
            return error
        serializer = ChatMessageInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = MatchChatMessage.objects.create(
            match=match, sender=request.user, text=serializer.validated_data["text"]
        )
        return Response(
            ChatMessageSerializer(message, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
