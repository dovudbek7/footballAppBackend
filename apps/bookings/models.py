import uuid

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel
from apps.stadiums.models import Stadium, StadiumSlotTemplate

ACTIVE_PAYMENT_STATUSES = ("pending", "paid", "waived")


class Match(TimeStampedModel):
    class Status(models.TextChoices):
        WAITING = "waiting", "Waiting for players"
        CONFIRMED = "confirmed", "Confirmed"
        FINISHED = "finished", "Finished"
        CANCELED = "canceled", "Canceled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    stadium = models.ForeignKey(Stadium, related_name="matches", on_delete=models.CASCADE)
    slot_template = models.ForeignKey(
        StadiumSlotTemplate, null=True, blank=True, on_delete=models.SET_NULL, related_name="matches"
    )

    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    # Snapshotted at creation time so later stadium/template edits never retroactively
    # change an already-scheduled match's price or capacity.
    capacity = models.PositiveSmallIntegerField()
    price_per_seat = models.DecimalField(max_digits=8, decimal_places=2)

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.WAITING)
    reminder_sent = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_matches"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["stadium", "date", "start_time"], name="unique_match_slot"),
        ]
        ordering = ["date", "start_time"]

    @property
    def format(self) -> str:
        per_side = self.capacity // 2
        return f"{per_side}v{per_side}"

    @property
    def taken(self) -> int:
        return self.bookings.filter(payment_status__in=ACTIVE_PAYMENT_STATUSES).count()

    @property
    def state(self) -> str:
        taken = self.taken
        if taken >= self.capacity:
            return "full"
        if taken / self.capacity >= 0.7:
            return "hot"
        return "available"

    @property
    def label(self) -> str:
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"


class Booking(TimeStampedModel):
    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        WAIVED = "waived", "Waived"
        REFUNDED = "refunded", "Refunded"
        CANCELED = "canceled", "Canceled"

    class Result(models.TextChoices):
        WON = "Won", "Won"
        LOST = "Lost", "Lost"
        DRAW = "Draw", "Draw"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    match = models.ForeignKey(Match, related_name="bookings", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="bookings", on_delete=models.CASCADE)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="invited_bookings"
    )

    payment_status = models.CharField(max_length=16, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    amount_charged = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    personal_result = models.CharField(max_length=8, choices=Result.choices, null=True, blank=True)
    is_motm = models.BooleanField(default=False)
    goals = models.PositiveSmallIntegerField(null=True, blank=True)
    assists = models.PositiveSmallIntegerField(null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)

    canceled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["match", "user"],
                condition=models.Q(payment_status__in=ACTIVE_PAYMENT_STATUSES),
                name="unique_active_booking_per_match_user",
            )
        ]

    @property
    def is_organizer(self) -> bool:
        return self.invited_by_id is None or self.invited_by_id == self.user_id


class MatchResult(TimeStampedModel):
    match = models.OneToOneField(Match, related_name="result", on_delete=models.CASCADE)
    score = models.CharField(max_length=16, blank=True)
    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)


class MatchChatMessage(TimeStampedModel):
    """A message in a match's group chat. Only players with an active booking can read/post."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    match = models.ForeignKey(Match, related_name="chat_messages", on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="chat_messages", on_delete=models.CASCADE)
    text = models.TextField(max_length=2000)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["match", "created_at"], name="chat_match_created_idx")]
