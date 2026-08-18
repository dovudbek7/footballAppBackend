from django.conf import settings
from rest_framework import serializers

from apps.wallet.services import get_or_create_wallet

from .models import ExperienceLevel, Friendship, User


class UserSerializer(serializers.ModelSerializer):
    friend_code = serializers.SerializerMethodField()
    referral_link = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "phone",
            "telegram_id",
            "telegram_username",
            "full_name",
            "bio",
            "avatar_url",
            "region",
            "city",
            "position",
            "experience_level",
            "language",
            "role",
            "friend_code",
            "referral_link",
            "is_onboarded",
        )
        read_only_fields = ("id", "phone", "telegram_id", "telegram_username", "role", "is_onboarded")

    def get_friend_code(self, obj):
        return get_or_create_wallet(obj).paynet_id

    def get_referral_link(self, obj):
        if not settings.TELEGRAM_BOT_USERNAME:
            return ""
        code = get_or_create_wallet(obj).paynet_id
        return f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start=ref_{code}"


class UserOnboardSerializer(serializers.ModelSerializer):
    """PATCH /accounts/me — used right after first login to fill in AuthPage fields."""

    class Meta:
        model = User
        fields = (
            "full_name",
            "bio",
            "avatar_url",
            "region",
            "city",
            "position",
            "experience_level",
            "language",
        )
        extra_kwargs = {"full_name": {"required": False}, "bio": {"required": False}}

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        if instance.full_name and not instance.is_onboarded:
            instance.is_onboarded = True
            instance.save(update_fields=["is_onboarded"])
        return instance


class OTPRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)

    def validate_phone(self, value):
        value = value.strip()
        if len(value) < 9:
            raise serializers.ValidationError("Phone number is too short.")
        return value


class OTPVerifySerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    code = serializers.CharField(max_length=6)


class TelegramWebAppAuthSerializer(serializers.Serializer):
    init_data = serializers.CharField()


class FriendSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField(source="full_name")
    avatar = serializers.CharField(source="avatar_url")


class FriendRequestSerializer(serializers.Serializer):
    """Incoming pending friend request."""

    id = serializers.IntegerField()
    user_id = serializers.UUIDField(source="user.id")
    name = serializers.CharField(source="user.full_name")
    avatar = serializers.CharField(source="user.avatar_url")
    created_at = serializers.DateTimeField()


class FriendAddSerializer(serializers.Serializer):
    """Accepts a user_id (from a search result), a phone number, @telegram_username,
    or a friend_code (wallet Paynet ID)."""

    user_id = serializers.UUIDField(required=False)
    phone = serializers.CharField(required=False)
    telegram_username = serializers.CharField(required=False)
    code = serializers.CharField(required=False)

    def validate(self, attrs):
        if not any(attrs.get(f) for f in ("user_id", "phone", "telegram_username", "code")):
            raise serializers.ValidationError("Provide a user_id, phone, telegram_username, or code.")
        return attrs
