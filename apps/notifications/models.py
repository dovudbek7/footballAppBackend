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
