import secrets
import uuid

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


def generate_paynet_id():
    return secrets.token_hex(6).upper()


class ExchangeRate(TimeStampedModel):
    """Admin-editable rate. Latest row wins. balance_uzs is always balance_usd * rate,
    computed at serialization time — never stored, so it can't drift out of sync."""

    currency_pair = models.CharField(max_length=16, default="USD_UZS")
    rate = models.DecimalField(max_digits=12, decimal_places=2)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-created_at"]

    @classmethod
    def latest(cls, pair="USD_UZS"):
        return cls.objects.filter(currency_pair=pair).order_by("-created_at").first()


class Wallet(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name="wallet", on_delete=models.CASCADE)
    balance_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paynet_id = models.CharField(max_length=32, unique=True, default=generate_paynet_id)

    def __str__(self):
        return f"{self.user} — ${self.balance_usd}"


class PaymentMethod(models.Model):
    class Icon(models.TextChoices):
        CLICK = "click", "Click"
        PAYME = "payme", "Payme"
        CARD = "card", "Card"
        KIOSK = "kiosk", "Kiosk"

    key = models.SlugField(max_length=32, unique=True)
    name = models.CharField(max_length=64)
    description = models.CharField(max_length=255, blank=True)
    icon = models.CharField(max_length=16, choices=Icon.choices)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return self.name


class TopUpRequest(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="topup_requests", on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    admin_note = models.CharField(max_length=255, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_topups"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)


class Transaction(TimeStampedModel):
    class Kind(models.TextChoices):
        IN = "in", "In"
        OUT = "out", "Out"

    class Status(models.TextChoices):
        SUCCESS = "Success", "Success"
        PENDING = "Pending", "Pending"
        FAILED = "Failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, related_name="transactions", on_delete=models.CASCADE)
    kind = models.CharField(max_length=8, choices=Kind.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.SUCCESS)
    title = models.CharField(max_length=120)
    subtitle = models.CharField(max_length=255, blank=True)

    topup_request = models.ForeignKey(TopUpRequest, null=True, blank=True, on_delete=models.SET_NULL)
    booking = models.ForeignKey(
        "bookings.Booking", null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions"
    )

    class Meta:
        ordering = ["-created_at"]
