from rest_framework import serializers

from .models import DeviceToken, NotificationLog


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = NotificationLog
        fields = ("id", "type", "text", "payload", "is_read", "created_at")

    def get_is_read(self, obj):
        return obj.read_at is not None


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = ("id", "token", "platform", "device_id", "is_active", "created_at")
        read_only_fields = ("id", "is_active", "created_at")


class DeviceTokenRegisterSerializer(serializers.Serializer):
    """Input-only serializer for POST /notifications/devices/.

    Deliberately not a ModelSerializer: the endpoint is an upsert keyed on
    `token`, so re-submitting an already-registered token is expected and
    must not trip a "unique" validation error.
    """

    token = serializers.CharField(max_length=255)
    platform = serializers.ChoiceField(choices=DeviceToken.Platform.choices)
    device_id = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
