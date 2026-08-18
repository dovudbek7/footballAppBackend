from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Badge, UserBadge, UserSeasonScore
from .serializers import (
    BadgeSerializer,
    LeaderboardEntrySerializer,
    ProfileStatsSerializer,
    RecentActivitySerializer,
)
from .services import compute_profile_stats, compute_recent_activity


class ProfileStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = compute_profile_stats(request.user)
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
        items = compute_recent_activity(request.user)
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
