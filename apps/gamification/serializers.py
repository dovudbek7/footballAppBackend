from rest_framework import serializers

from .models import Badge, UserSkillRating


class PlayerStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSkillRating
        fields = ("key", "label", "value")


class ProfileStatsSerializer(serializers.Serializer):
    name = serializers.CharField()
    position = serializers.CharField()
    city = serializers.CharField()
    avatar = serializers.CharField()
    tier = serializers.CharField()
    matches_played = serializers.IntegerField()
    win_rate = serializers.FloatField()
    motm_awards = serializers.IntegerField()
    avg_rating = serializers.FloatField()
    stats = PlayerStatSerializer(many=True)


class BadgeSerializer(serializers.ModelSerializer):
    unlocked = serializers.BooleanField()

    class Meta:
        model = Badge
        fields = ("id", "code", "title", "requirement_text", "icon", "unlocked")


class RecentActivitySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    result = serializers.CharField()
    ago = serializers.CharField()
    stadium = serializers.CharField()
    detail = serializers.CharField()


class LeaderboardEntrySerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    user_id = serializers.UUIDField()
    name = serializers.CharField()
    avatar = serializers.CharField()
    points = serializers.IntegerField()
    is_you = serializers.BooleanField()
