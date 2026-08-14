from django.db.models import Avg
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import ACTIVE_PAYMENT_STATUSES, Booking

from .models import Badge, UserBadge, UserSeasonScore
from .serializers import (
    BadgeSerializer,
    LeaderboardEntrySerializer,
    ProfileStatsSerializer,
    RecentActivitySerializer,
)


def _timesince_label(dt):
    delta = timezone.now() - dt
    days = delta.days
    if days >= 1:
        return f"{days}d ago"
    hours = delta.seconds // 3600
    if hours >= 1:
        return f"{hours}h ago"
    return f"{max(delta.seconds // 60, 1)}m ago"


class ProfileStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        bookings = Booking.objects.filter(user=user, payment_status__in=ACTIVE_PAYMENT_STATUSES)
        matches_played = bookings.count()
        wins = bookings.filter(personal_result=Booking.Result.WON).count()
        motm_awards = bookings.filter(is_motm=True).count()
        avg_rating = bookings.aggregate(avg=Avg("rating"))["avg"] or 0

        data = {
            "name": user.full_name,
            "position": user.position,
            "city": user.city,
            "avatar": user.avatar_url,
            "tier": user.experience_level,
            "matches_played": matches_played,
            "win_rate": round(wins / matches_played * 100, 1) if matches_played else 0.0,
            "motm_awards": motm_awards,
            "avg_rating": round(float(avg_rating), 1),
            "stats": user.skill_ratings.all(),
        }
        return Response(ProfileStatsSerializer(data).data)


class ProfileBadgesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        unlocked_ids = set(
            UserBadge.objects.filter(user=request.user, unlocked_at__isnull=False).values_list(
                "badge_id", flat=True
            )
        )
        badges = list(Badge.objects.filter(is_active=True))
        for badge in badges:
            badge.unlocked = badge.id in unlocked_ids
        return Response(BadgeSerializer(badges, many=True).data)


class ProfileActivityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        bookings = (
            Booking.objects.filter(
                user=request.user,
                payment_status__in=ACTIVE_PAYMENT_STATUSES,
                match__status="finished",
            )
            .select_related("match", "match__stadium")
            .order_by("-updated_at")[:20]
        )
        items = []
        for booking in bookings:
            detail_parts = []
            if booking.rating is not None:
                detail_parts.append(f"{booking.rating} Rating")
            if booking.goals or booking.assists:
                detail_parts.append(f"{booking.goals or 0} Goal, {booking.assists or 0} Assists")
            items.append(
                {
                    "id": booking.id,
                    "result": booking.personal_result or "-",
                    "ago": _timesince_label(booking.updated_at),
                    "stadium": booking.match.stadium.name,
                    "detail": " • ".join(detail_parts),
                }
            )
        return Response(RecentActivitySerializer(items, many=True).data)


class LeaderboardView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        period = request.query_params.get("period") or timezone.now().strftime("%Y-%m")
        region = request.query_params.get("region", "")

        qs = UserSeasonScore.objects.filter(period=period)
        if region:
            qs = qs.filter(region__iexact=region)
        qs = qs.select_related("user").order_by("-points")[:50]

        current_user_id = request.user.id if request.user.is_authenticated else None
        entries = [
            {
                "rank": i + 1,
                "user_id": score.user_id,
                "name": score.user.full_name,
                "avatar": score.user.avatar_url,
                "points": score.points,
                "is_you": score.user_id == current_user_id,
            }
            for i, score in enumerate(qs)
        ]
        return Response(LeaderboardEntrySerializer(entries, many=True).data)
