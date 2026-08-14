from rest_framework import serializers

from .models import ExperienceLevel, Friendship, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "phone",
            "telegram_id",
            "telegram_username",
            "full_name",
            "avatar_url",
            "region",
            "city",
            "position",
            "experience_level",
            "is_onboarded",
        )
        read_only_fields = ("id", "phone", "telegram_id", "telegram_username", "is_onboarded")


class UserOnboardSerializer(serializers.ModelSerializer):
    """PATCH /accounts/me — used right after first login to fill in AuthPage fields."""

    class Meta:
        model = User
        fields = ("full_name", "avatar_url", "region", "city", "position", "experience_level")
        extra_kwargs = {"full_name": {"required": False}}

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


class FriendAddSerializer(serializers.Serializer):
    phone = serializers.CharField(required=False)
    telegram_username = serializers.CharField(required=False)

    def validate(self, attrs):
        if not attrs.get("phone") and not attrs.get("telegram_username"):
            raise serializers.ValidationError("Provide a phone or telegram_username.")
        return attrs
