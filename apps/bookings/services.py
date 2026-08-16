from datetime import datetime, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.notifications.models import NotificationLog
from apps.notifications.services import notify
from apps.wallet import services as wallet_services

from .models import ACTIVE_PAYMENT_STATUSES, Booking, Match

CANCELLATION_WINDOW = timedelta(hours=2)


class BookingError(Exception):
    pass


def compute_pricing(mode: str, pay_mode: str, friend_count: int, price_per_seat: Decimal) -> dict:
    """Mirrors JoinMatchModal.tsx exactly:
    seats = mode === "alone" ? 1 : 1 + friends.length
    payable = (mode === "friends" && payMode === "split") ? 1 : seats
    total = payable * slotPrice
    """
    seats = 1 if mode == "alone" else 1 + friend_count
    payable = 1 if (mode == "friends" and pay_mode == "split") else seats
    return {"seats": seats, "payable": payable, "total": payable * price_per_seat}


def refresh_match_status(match: Match) -> None:
    if match.status not in (Match.Status.WAITING, Match.Status.CONFIRMED):
        return
    match.status = Match.Status.CONFIRMED if match.taken >= match.capacity else Match.Status.WAITING
    match.save(update_fields=["status"])


@transaction.atomic
def join_match(user: User, match: Match, mode: str, friend_ids: list, pay_mode: str) -> list[Booking]:
    match = Match.objects.select_for_update().get(pk=match.pk)

    if match.status not in (Match.Status.WAITING, Match.Status.CONFIRMED):
        raise BookingError("This match is no longer open for booking.")
    starts_at = timezone.make_aware(datetime.combine(match.date, match.start_time))
    if timezone.now() >= starts_at:
        raise BookingError("This match has already started.")

    friends = []
    if mode == "friends":
        unique_ids = {fid for fid in friend_ids if fid != user.id}
        friends = list(User.objects.filter(id__in=unique_ids))
        if len(friends) != len(unique_ids):
            raise BookingError("Some invited friends could not be found.")
        already_in = Booking.objects.filter(
            match=match, user__in=friends, payment_status__in=ACTIVE_PAYMENT_STATUSES
        ).exists()
        if already_in:
            raise BookingError("One of your friends already has a seat in this match.")
    pricing = compute_pricing(mode, pay_mode, len(friends), match.price_per_seat)

    if match.taken + pricing["seats"] > match.capacity:
        raise BookingError("Not enough seats left in this match.")
    if Booking.objects.filter(match=match, user=user, payment_status__in=ACTIVE_PAYMENT_STATUSES).exists():
        raise BookingError("You already have a seat in this match.")

    wallet_services.debit(
        user,
        pricing["total"],
        title="Match booking",
        subtitle=f"{match.stadium.name} · {match.date} {match.label}",
    )

    organizer_booking = Booking.objects.create(
        match=match,
        user=user,
        invited_by=user,
        payment_status=Booking.PaymentStatus.PAID,
        amount_charged=match.price_per_seat if pricing["payable"] >= 1 else 0,
    )
    bookings = [organizer_booking]

    friend_pays_now = pay_mode == "all"
    for friend in friends:
        bookings.append(
            Booking.objects.create(
                match=match,
                user=friend,
                invited_by=user,
                payment_status=Booking.PaymentStatus.PAID if friend_pays_now else Booking.PaymentStatus.PENDING,
                amount_charged=match.price_per_seat,
            )
        )
        if not friend_pays_now:
            notify(
                friend,
                NotificationLog.NotificationType.SPLIT_REQUEST,
                organizer_name=user.full_name or "A friend",
                stadium_name=match.stadium.name,
                date=match.date,
                time=match.label,
                amount=match.price_per_seat,
            )

    refresh_match_status(match)

    notify(
        user,
        NotificationLog.NotificationType.BOOKING_CONFIRMED,
        stadium_name=match.stadium.name,
        date=match.date,
        time=match.label,
    )
    if match.status == Match.Status.CONFIRMED:
        for booking in match.bookings.filter(payment_status__in=ACTIVE_PAYMENT_STATUSES):
            notify(
                booking.user,
                NotificationLog.NotificationType.WAITLIST_FILLED,
                stadium_name=match.stadium.name,
                date=match.date,
            )

    return bookings


def create_match(organizer: User, stadium, date, start_time, end_time, capacity, price_per_seat=None) -> Match:
    """Ad-hoc match creation by an organizer — separate from the recurring
    StadiumSlotTemplate → Match generator used for host-listed pitches."""
    return Match.objects.create(
        stadium=stadium,
        date=date,
        start_time=start_time,
        end_time=end_time,
        capacity=capacity,
        price_per_seat=price_per_seat or stadium.base_slot_price,
        created_by=organizer,
    )


@transaction.atomic
def invite_to_match(inviter: User, match: Match, friend_ids: list) -> list[Booking]:
    """Adds friends to an already-joined match as pending (split-pay) seats."""
    match = Match.objects.select_for_update().get(pk=match.pk)

    if match.status not in (Match.Status.WAITING, Match.Status.CONFIRMED):
        raise BookingError("This match is no longer open for invites.")
    starts_at = timezone.make_aware(datetime.combine(match.date, match.start_time))
    if timezone.now() >= starts_at:
        raise BookingError("This match has already started.")

    unique_ids = {fid for fid in friend_ids if fid != inviter.id}
    friends = list(User.objects.filter(id__in=unique_ids))
    if len(friends) != len(unique_ids):
        raise BookingError("Some invited friends could not be found.")

    already_in = Booking.objects.filter(
        match=match, user__in=friends, payment_status__in=ACTIVE_PAYMENT_STATUSES
    ).exists()
    if already_in:
        raise BookingError("One of your friends already has a seat in this match.")
    if match.taken + len(friends) > match.capacity:
        raise BookingError("Not enough seats left in this match.")

    bookings = []
    for friend in friends:
        bookings.append(
            Booking.objects.create(
                match=match,
                user=friend,
                invited_by=inviter,
                payment_status=Booking.PaymentStatus.PENDING,
                amount_charged=match.price_per_seat,
            )
        )
        notify(
            friend,
            NotificationLog.NotificationType.MATCH_INVITE,
            organizer_name=inviter.full_name or "A friend",
            stadium_name=match.stadium.name,
            date=match.date,
            time=match.label,
        )

    refresh_match_status(match)
    return bookings


@transaction.atomic
def accept_split(booking: Booking, user: User) -> Booking:
    # Re-read under a row lock so concurrent accepts/cancels can't double-debit.
    booking = Booking.objects.select_for_update().select_related("match", "match__stadium").get(pk=booking.pk)

    if booking.user_id != user.id:
        raise BookingError("This booking does not belong to you.")
    if booking.payment_status != Booking.PaymentStatus.PENDING:
        raise BookingError("This booking is not awaiting payment.")

    match = booking.match
    starts_at = timezone.make_aware(datetime.combine(match.date, match.start_time))
    if timezone.now() >= starts_at:
        raise BookingError("This match has already started.")

    wallet_services.debit(
        user,
        booking.amount_charged,
        title="Split payment",
        subtitle=f"{booking.match.stadium.name} · {booking.match.date} {booking.match.label}",
    )
    booking.payment_status = Booking.PaymentStatus.PAID
    booking.save(update_fields=["payment_status"])
    refresh_match_status(booking.match)
    return booking


@transaction.atomic
def cancel_booking(booking: Booking, user: User) -> Booking:
    # Re-read under a row lock so a concurrent double-cancel can't double-refund.
    booking = Booking.objects.select_for_update().select_related("match", "match__stadium").get(pk=booking.pk)

    if booking.user_id != user.id:
        raise BookingError("This booking does not belong to you.")
    if booking.payment_status not in ACTIVE_PAYMENT_STATUSES:
        raise BookingError("This booking is already canceled.")

    match = booking.match
    if match.status == Match.Status.FINISHED:
        raise BookingError("This match is already finished.")

    starts_at = timezone.make_aware(datetime.combine(match.date, match.start_time))
    if timezone.now() >= starts_at:
        raise BookingError("This match has already started.")
    refundable = timezone.now() < starts_at - CANCELLATION_WINDOW

    if refundable and booking.payment_status == Booking.PaymentStatus.PAID:
        wallet_services.credit(
            user,
            booking.amount_charged,
            title="Booking refund",
            subtitle=f"{match.stadium.name} · {match.date} {match.label}",
        )
        booking.payment_status = Booking.PaymentStatus.REFUNDED
    else:
        booking.payment_status = Booking.PaymentStatus.CANCELED

    booking.canceled_at = timezone.now()
    booking.save(update_fields=["payment_status", "canceled_at"])

    # The organizer's cancel also releases seats of invited friends who never paid
    # their split share — those seats were only held on the organizer's behalf.
    if booking.is_organizer:
        pending_invitees = Booking.objects.select_for_update().filter(
            match=match,
            invited_by=user,
            payment_status=Booking.PaymentStatus.PENDING,
        ).exclude(user=user)
        for invitee in pending_invitees:
            invitee.payment_status = Booking.PaymentStatus.CANCELED
            invitee.canceled_at = timezone.now()
            invitee.save(update_fields=["payment_status", "canceled_at"])

    refresh_match_status(match)
    return booking
