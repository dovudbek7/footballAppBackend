from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import NotificationLog
from apps.notifications.services import notify
from apps.wallet.services import InsufficientFunds

from . import services
from .models import ACTIVE_PAYMENT_STATUSES, Booking, Match, MatchResult
from .serializers import (
    BookingSerializer,
    JoinMatchSerializer,
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
            year, mon = month.split("-")
            qs = qs.filter(date__year=int(year), date__month=int(mon))
        return qs


class NextMatchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        match = (
            Match.objects.filter(
                bookings__user=request.user,
                bookings__payment_status__in=ACTIVE_PAYMENT_STATUSES,
                status=Match.Status.CONFIRMED,
                date__gte=timezone.now().date(),
            )
            .order_by("date", "start_time")
            .first()
        )
        if not match:
            return Response(None)
        starts_at = timezone.make_aware(
            timezone.datetime.combine(match.date, match.start_time)
        )
        return Response(
            {
                "match": ScheduledMatchSerializer(match, context={"request": request}).data,
                "starts_at": starts_at.isoformat(),
            }
        )


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

        serializer = MatchResultInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        for item in data["participants"]:
            Booking.objects.filter(id=item["booking_id"], match=match).update(
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
