from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from apps.core.models import TimeStampedModel


class NotificationLog(TimeStampedModel):
    class NotificationType(models.TextChoices):
        OTP_CODE = "otp_code", "OTP code"
        TELEGRAM_LINK = "telegram_link", "Telegram link"
        BOOKING_CONFIRMED = "booking_confirmed", "Booking confirmed"
        SPLIT_REQUEST = "split_request", "Split payment request"
        MATCH_REMINDER = "match_reminder", "Match reminder"
        WAITLIST_FILLED = "waitlist_filled", "Waitlist filled"
        SPLIT_EXPIRED = "split_expired", "Split payment expired"
        BADGE_UNLOCKED = "badge_unlocked", "Badge unlocked"
        TOPUP_APPROVED = "topup_approved", "Top-up approved"
        FRIEND_REQUEST = "friend_request", "Friend request"
        FRIEND_ACCEPTED = "friend_accepted", "Friend request accepted"
        MATCH_INVITE = "match_invite", "Match invite"
        ORGANIZER_REQUEST_APPROVED = "organizer_request_approved", "Organizer request approved"
        ORGANIZER_REQUEST_REJECTED = "organizer_request_rejected", "Organizer request rejected"

    class Status(models.TextChoices):
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    telegram_id = models.BigIntegerField(null=True, blank=True)
    type = models.CharField(max_length=32, choices=NotificationType.choices)
    text = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder)
    status = models.CharField(max_length=16, choices=Status.choices)
    error_text = models.TextField(blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class DeviceToken(TimeStampedModel):
    """A push-notification (FCM) registration for a user's mobile device.

    Additive to the Telegram notification path — see apps/notifications/services.py.
    """

    class Platform(models.TextChoices):
        IOS = "ios", "iOS"
        ANDROID = "android", "Android"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="device_tokens")
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=16, choices=Platform.choices)
    device_id = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_id}:{self.platform}:{self.token[:12]}..."
