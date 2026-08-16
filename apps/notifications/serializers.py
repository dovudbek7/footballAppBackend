from rest_framework import serializers

from .models import NotificationLog


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = NotificationLog
        fields = ("id", "type", "text", "payload", "is_read", "created_at")

    def get_is_read(self, obj):
        return obj.read_at is not None
