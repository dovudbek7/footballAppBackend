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
        BADGE_UNLOCKED = "badge_unlocked", "Badge unlocked"
        TOPUP_APPROVED = "topup_approved", "Top-up approved"

    class Status(models.TextChoices):
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    telegram_id = models.BigIntegerField(null=True, blank=True)
    type = models.CharField(max_length=32, choices=NotificationType.choices)
    payload = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder)
    status = models.CharField(max_length=16, choices=Status.choices)
    error_text = models.TextField(blank=True)
