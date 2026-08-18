from datetime import date

from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import ACTIVE_PAYMENT_STATUSES, Match
from apps.bookings.serializers import MatchSlotSerializer

from apps.accounts.models import Role

from .models import Amenity, FavoriteStadium, Review, Stadium
from .serializers import (
    ReviewSerializer,
    StadiumCreateSerializer,
    StadiumDetailSerializer,
    StadiumListSerializer,
)


def _annotated_stadiums():
    return Stadium.objects.filter(is_active=True).annotate(
        rating=Avg("reviews__rating"), reviews_count=Count("reviews")
    )


class StadiumListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = StadiumListSerializer

    def get_queryset(self):
        qs = _annotated_stadiums()
        if self.request.query_params.get("favorites") == "1":
            user = self.request.user
            if not user.is_authenticated:
                return qs.none()
            qs = qs.filter(
                id__in=FavoriteStadium.objects.filter(user=user).values_list("stadium_id", flat=True)
            )
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(district__icontains=search) | Q(city__icontains=search))
        city = self.request.query_params.get("city")
        if city:
            qs = qs.filter(city__iexact=city)
        district = self.request.query_params.get("district")
        if district:
            qs = qs.filter(district__iexact=district)
        amenities = self.request.query_params.get("amenities")
        if amenities:
            keys = [key.strip() for key in amenities.split(",") if key.strip()]
            for key in keys:
                qs = qs.filter(amenities__key=key)
        max_price = self.request.query_params.get("max_price")
        if max_price:
            qs = qs.filter(base_slot_price__lte=max_price)
        return qs.distinct()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user = self.request.user
        if user.is_authenticated:
            context["favorite_ids"] = set(
                FavoriteStadium.objects.filter(user=user).values_list("stadium_id", flat=True)
            )
        return context


class AmenityListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    pagination_class = None
    queryset = Amenity.objects.all()

    def list(self, request, *args, **kwargs):
        return Response([{"key": a.key, "label": a.label} for a in self.get_queryset()])


class StadiumCreateView(APIView):
    """Hosts list a new pitch."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != Role.HOST:
            return Response({"detail": "Only hosts can create listings."}, status=status.HTTP_403_FORBIDDEN)
        serializer = StadiumCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        stadium = serializer.save(owner_name=request.user.full_name)
        return Response(
            StadiumDetailSerializer(stadium, context={"request": request}).data, status=status.HTTP_201_CREATED
        )


class StadiumDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = StadiumDetailSerializer
    queryset = _annotated_stadiums()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user = self.request.user
        if user.is_authenticated:
            context["favorite_ids"] = set(
                FavoriteStadium.objects.filter(user=user).values_list("stadium_id", flat=True)
            )
        return context


class StadiumSlotsView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = MatchSlotSerializer
    pagination_class = None

    def get_queryset(self):
        stadium = get_object_or_404(Stadium, pk=self.kwargs["pk"])
        raw_date = self.request.query_params.get("date")
        if raw_date:
            try:
                target_date = date.fromisoformat(raw_date)
            except ValueError:
                raise ValidationError({"date": "Expected YYYY-MM-DD."})
        else:
            target_date = date.today()
        return Match.objects.filter(stadium=stadium, date=target_date, status__in=[
            Match.Status.WAITING, Match.Status.CONFIRMED,
        ]).prefetch_related("bookings")


class FavoriteToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        stadium = get_object_or_404(Stadium, pk=pk)
        FavoriteStadium.objects.get_or_create(user=request.user, stadium=stadium)
        return Response(status=status.HTTP_201_CREATED)

    def delete(self, request, pk):
        FavoriteStadium.objects.filter(user=request.user, stadium_id=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReviewListCreateView(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_queryset(self):
        return Review.objects.filter(stadium_id=self.kwargs["pk"]).select_related("author")

    def perform_create(self, serializer):
        stadium = get_object_or_404(Stadium, pk=self.kwargs["pk"])
        has_finished_booking = Match.objects.filter(
            stadium=stadium,
            status=Match.Status.FINISHED,
            bookings__user=self.request.user,
            bookings__payment_status__in=ACTIVE_PAYMENT_STATUSES,
        ).exists()
        if not has_finished_booking:
            raise PermissionDenied("You can only review a stadium after playing a finished match there.")
        serializer.save(stadium=stadium, author=self.request.user)
