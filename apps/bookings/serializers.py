from datetime import datetime

from django.utils import timezone
from rest_framework import serializers

from .models import ACTIVE_PAYMENT_STATUSES, Booking, Match, MatchChatMessage, MatchResult
from .services import CANCELLATION_WINDOW


class MatchSlotSerializer(serializers.ModelSerializer):
    """The frontend's TimeSlot shape — GET /stadiums/{id}/slots?date=."""

    label = serializers.CharField(read_only=True)
    taken = serializers.IntegerField(read_only=True)
    state = serializers.CharField(read_only=True)

    class Meta:
        model = Match
        fields = ("id", "label", "taken", "capacity", "state", "price_per_seat")


class ScheduledMatchSerializer(serializers.ModelSerializer):
    """The frontend's ScheduledMatch shape, scoped to the requesting user — GET /matches/mine."""

    stadium_id = serializers.UUIDField(source="stadium.id", read_only=True)
    stadium_name = serializers.CharField(source="stadium.name", read_only=True)
    thumbnail = serializers.CharField(source="stadium.main_image_url", read_only=True)
    format = serializers.CharField(read_only=True)
    time = serializers.CharField(source="label", read_only=True)
    missing_players = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()
    my_result = serializers.SerializerMethodField()
    my_motm = serializers.SerializerMethodField()
    starts_at = serializers.SerializerMethodField()
    my_booking_id = serializers.SerializerMethodField()
    my_payment_status = serializers.SerializerMethodField()
    refundable = serializers.SerializerMethodField()

    class Meta:
        model = Match
        fields = (
            "id",
            "stadium_id",
            "stadium_name",
            "thumbnail",
            "format",
            "date",
            "time",
            "starts_at",
            "status",
            "missing_players",
            "score",
            "my_result",
            "my_motm",
            "my_booking_id",
            "my_payment_status",
            "refundable",
        )

    def get_missing_players(self, obj):
        if obj.status != Match.Status.WAITING:
            return None
        return obj.capacity - obj.taken

    def get_score(self, obj):
        result = getattr(obj, "result", None)
        return result.score if result else None

    def _my_booking(self, obj):
        user = self.context["request"].user
        return next(
            (b for b in obj.bookings.all() if b.user_id == user.id and b.payment_status in ACTIVE_PAYMENT_STATUSES),
            None,
        )

    def get_my_result(self, obj):
        booking = self._my_booking(obj)
        return booking.personal_result if booking else None

    def get_my_motm(self, obj):
        booking = self._my_booking(obj)
        return booking.is_motm if booking else False

    def get_starts_at(self, obj):
        return timezone.make_aware(datetime.combine(obj.date, obj.start_time)).isoformat()

    def get_my_booking_id(self, obj):
        booking = self._my_booking(obj)
        return str(booking.id) if booking else None

    def get_my_payment_status(self, obj):
        booking = self._my_booking(obj)
        return booking.payment_status if booking else None

    def get_refundable(self, obj):
        """True when canceling now would refund the seat (paid + more than 2h before kickoff)."""
        booking = self._my_booking(obj)
        if not booking or booking.payment_status != Booking.PaymentStatus.PAID:
            return False
        if obj.status not in (Match.Status.WAITING, Match.Status.CONFIRMED):
            return False
        starts_at = timezone.make_aware(datetime.combine(obj.date, obj.start_time))
        return timezone.now() < starts_at - CANCELLATION_WINDOW


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = (
            "id",
            "match",
            "user",
            "invited_by",
            "payment_status",
            "amount_charged",
            "personal_result",
            "is_motm",
            "goals",
            "assists",
        )
        read_only_fields = fields


class JoinMatchSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=["alone", "friends"])
    pay_mode = serializers.ChoiceField(choices=["all", "split"], default="all")
    friend_ids = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)


class InviteToMatchSerializer(serializers.Serializer):
    friend_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1)


class MatchCreateSerializer(serializers.Serializer):
    stadium_id = serializers.UUIDField()
    date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    capacity = serializers.IntegerField(min_value=2, max_value=22)
    price_per_seat = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0, required=False)


class MatchResultParticipantSerializer(serializers.Serializer):
    booking_id = serializers.UUIDField()
    result = serializers.ChoiceField(choices=Booking.Result.choices)
    is_motm = serializers.BooleanField(default=False)
    goals = serializers.IntegerField(required=False, min_value=0)
    assists = serializers.IntegerField(required=False, min_value=0)
    rating = serializers.DecimalField(max_digits=3, decimal_places=1, required=False, min_value=0, max_value=10)


class MatchResultInputSerializer(serializers.Serializer):
    score = serializers.CharField(max_length=16)
    participants = MatchResultParticipantSerializer(many=True)


class MatchResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatchResult
        fields = ("score", "entered_by", "created_at")


class ChatMessageSerializer(serializers.ModelSerializer):
    sender = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = MatchChatMessage
        fields = ("id", "sender", "text", "created_at", "is_mine")

    def get_sender(self, obj):
        return {
            "id": str(obj.sender_id),
            "name": obj.sender.full_name or obj.sender.telegram_username or "Player",
            "avatar": obj.sender.avatar_url,
        }

    def get_is_mine(self, obj):
        request = self.context.get("request")
        return bool(request and obj.sender_id == request.user.id)


class ChatMessageInputSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=2000, trim_whitespace=True)
