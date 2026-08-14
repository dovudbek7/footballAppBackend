from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.stadiums.models import Stadium
from apps.wallet.models import Wallet
from apps.wallet.services import get_or_create_wallet

from .models import Booking, Match


def make_stadium(**kwargs):
    defaults = {
        "name": "Test Arena",
        "district": "Chilonzor",
        "city": "Tashkent",
        "address": "Somewhere 1",
        "base_price_per_hour": Decimal("50"),
        "base_slot_price": Decimal("5"),
    }
    defaults.update(kwargs)
    return Stadium.objects.create(**defaults)


def make_match(stadium, starts_in: timedelta, capacity=10, price=Decimal("5"), status=Match.Status.WAITING):
    starts_at = timezone.localtime(timezone.now() + starts_in)
    return Match.objects.create(
        stadium=stadium,
        date=starts_at.date(),
        start_time=starts_at.time().replace(microsecond=0),
        end_time=(starts_at + timedelta(hours=1)).time().replace(microsecond=0),
        capacity=capacity,
        price_per_seat=price,
        status=status,
    )


def fund(user, amount="100"):
    wallet = get_or_create_wallet(user)
    Wallet.objects.filter(pk=wallet.pk).update(balance_usd=Decimal(amount))
    return wallet


class JoinMatchTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(telegram_id=10, full_name="Org")
        self.friend = User.objects.create_user(telegram_id=11, full_name="Fr")
        self.stadium = make_stadium()
        self.match = make_match(self.stadium, timedelta(hours=5))
        fund(self.user)
        fund(self.friend)
        self.client.force_authenticate(self.user)

    def url(self, match):
        return f"/api/matches/{match.id}/join"

    def test_join_alone_debits_wallet(self):
        response = self.client.post(self.url(self.match), {"mode": "alone"})
        self.assertEqual(response.status_code, 201)
        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance_usd, Decimal("95"))
        booking = Booking.objects.get(match=self.match, user=self.user)
        self.assertIn("my_booking_id", self.client.get("/api/matches/mine").data[0])
        self.assertEqual(
            self.client.get("/api/matches/mine").data[0]["my_booking_id"], str(booking.id)
        )

    def test_join_with_unknown_friend_rejected(self):
        import uuid

        response = self.client.post(
            self.url(self.match),
            {"mode": "friends", "pay_mode": "all", "friend_ids": [str(uuid.uuid4())]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Booking.objects.count(), 0)

    def test_join_with_friend_already_in_match_rejected(self):
        Booking.objects.create(
            match=self.match, user=self.friend, payment_status=Booking.PaymentStatus.PAID
        )
        response = self.client.post(
            self.url(self.match),
            {"mode": "friends", "pay_mode": "all", "friend_ids": [str(self.friend.id)]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_join_started_match_rejected(self):
        started = make_match(self.stadium, timedelta(hours=-1))
        response = self.client.post(self.url(started), {"mode": "alone"})
        self.assertEqual(response.status_code, 400)


class CancelBookingTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(telegram_id=20, full_name="Org")
        self.friend = User.objects.create_user(telegram_id=21, full_name="Fr")
        self.stadium = make_stadium()
        fund(self.user)
        self.client.force_authenticate(self.user)

    def cancel(self, booking):
        return self.client.post(f"/api/bookings/{booking.id}/cancel")

    def test_cancel_refundable_credits_wallet(self):
        match = make_match(self.stadium, timedelta(hours=5))
        self.client.post(f"/api/matches/{match.id}/join", {"mode": "alone"})
        booking = Booking.objects.get(match=match, user=self.user)
        response = self.cancel(booking)
        self.assertEqual(response.status_code, 200)
        booking.refresh_from_db()
        self.assertEqual(booking.payment_status, Booking.PaymentStatus.REFUNDED)
        self.assertEqual(Wallet.objects.get(user=self.user).balance_usd, Decimal("100"))

    def test_cancel_inside_window_no_refund(self):
        match = make_match(self.stadium, timedelta(hours=1))
        self.client.post(f"/api/matches/{match.id}/join", {"mode": "alone"})
        booking = Booking.objects.get(match=match, user=self.user)
        response = self.cancel(booking)
        self.assertEqual(response.status_code, 200)
        booking.refresh_from_db()
        self.assertEqual(booking.payment_status, Booking.PaymentStatus.CANCELED)
        self.assertEqual(Wallet.objects.get(user=self.user).balance_usd, Decimal("95"))

    def test_cancel_finished_match_rejected(self):
        match = make_match(self.stadium, timedelta(hours=5))
        booking = Booking.objects.create(
            match=match, user=self.user, payment_status=Booking.PaymentStatus.PAID,
            amount_charged=Decimal("5"),
        )
        match.status = Match.Status.FINISHED
        match.save(update_fields=["status"])
        response = self.cancel(booking)
        self.assertEqual(response.status_code, 400)

    def test_double_cancel_rejected(self):
        match = make_match(self.stadium, timedelta(hours=5))
        self.client.post(f"/api/matches/{match.id}/join", {"mode": "alone"})
        booking = Booking.objects.get(match=match, user=self.user)
        self.assertEqual(self.cancel(booking).status_code, 200)
        self.assertEqual(self.cancel(booking).status_code, 400)
        self.assertEqual(Wallet.objects.get(user=self.user).balance_usd, Decimal("100"))

    def test_organizer_cancel_cascades_pending_invitees(self):
        match = make_match(self.stadium, timedelta(hours=5))
        self.client.post(
            f"/api/matches/{match.id}/join",
            {"mode": "friends", "pay_mode": "split", "friend_ids": [str(self.friend.id)]},
            format="json",
        )
        organizer_booking = Booking.objects.get(match=match, user=self.user)
        invitee_booking = Booking.objects.get(match=match, user=self.friend)
        self.assertEqual(invitee_booking.payment_status, Booking.PaymentStatus.PENDING)

        self.cancel(organizer_booking)
        invitee_booking.refresh_from_db()
        self.assertEqual(invitee_booking.payment_status, Booking.PaymentStatus.CANCELED)


class MatchChatTests(APITestCase):
    def setUp(self):
        self.player = User.objects.create_user(telegram_id=30, full_name="P1")
        self.other = User.objects.create_user(telegram_id=31, full_name="Out")
        self.stadium = make_stadium()
        self.match = make_match(self.stadium, timedelta(hours=3))
        Booking.objects.create(
            match=self.match, user=self.player, payment_status=Booking.PaymentStatus.PAID
        )

    def url(self):
        return f"/api/matches/{self.match.id}/chat"

    def test_non_player_cannot_read_or_post(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(self.url()).status_code, 403)
        self.assertEqual(self.client.post(self.url(), {"text": "hi"}).status_code, 403)

    def test_player_posts_and_reads(self):
        self.client.force_authenticate(self.player)
        response = self.client.post(self.url(), {"text": "salom"})
        self.assertEqual(response.status_code, 201)
        listing = self.client.get(self.url())
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.data), 1)
        self.assertEqual(listing.data[0]["text"], "salom")
        self.assertTrue(listing.data[0]["is_mine"])

        after = listing.data[0]["created_at"]
        self.assertEqual(len(self.client.get(self.url(), {"after": after}).data), 0)

    def test_invalid_after_param_rejected(self):
        self.client.force_authenticate(self.player)
        self.assertEqual(self.client.get(self.url(), {"after": "garbage"}).status_code, 400)
