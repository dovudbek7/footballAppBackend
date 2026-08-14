import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from django.test import override_settings
from rest_framework.test import APITestCase

from .models import Friendship, User

TEST_BOT_TOKEN = "12345:TEST_TOKEN"


def make_init_data(tg_user: dict, auth_date: int | None = None) -> str:
    pairs = {
        "auth_date": str(auth_date or int(time.time())),
        "query_id": "AAtest",
        "user": json.dumps(tg_user, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", TEST_BOT_TOKEN.encode(), hashlib.sha256).digest()
    pairs["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(pairs)


@override_settings(TELEGRAM_BOT_TOKEN=TEST_BOT_TOKEN)
class TelegramWebAppAuthTests(APITestCase):
    url = "/api/auth/telegram/webapp"

    def test_valid_init_data_creates_user_with_language(self):
        init_data = make_init_data(
            {"id": 777, "first_name": "Alisher", "last_name": "N", "username": "alisher", "language_code": "ru"}
        )
        response = self.client.post(self.url, {"init_data": init_data})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_new_user"])
        self.assertIn("access", response.data)
        user = User.objects.get(telegram_id=777)
        self.assertEqual(user.full_name, "Alisher N")
        self.assertEqual(user.language, "ru")
        self.assertEqual(response.data["user"]["language"], "ru")

    def test_unsupported_language_falls_back_to_uzbek(self):
        init_data = make_init_data({"id": 778, "first_name": "Jo", "language_code": "de"})
        response = self.client.post(self.url, {"init_data": init_data})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.get(telegram_id=778).language, "uz")

    def test_tampered_hash_rejected(self):
        init_data = make_init_data({"id": 779, "first_name": "Evil"})
        response = self.client.post(self.url, {"init_data": init_data + "x"})
        self.assertEqual(response.status_code, 400)

    def test_expired_auth_date_rejected(self):
        init_data = make_init_data({"id": 780, "first_name": "Old"}, auth_date=int(time.time()) - 100_000)
        response = self.client.post(self.url, {"init_data": init_data})
        self.assertEqual(response.status_code, 400)

    def test_repeat_login_is_not_new_and_refreshes_avatar(self):
        first = make_init_data({"id": 781, "first_name": "A", "photo_url": "https://t.me/a.jpg"})
        self.client.post(self.url, {"init_data": first})
        second = make_init_data({"id": 781, "first_name": "A", "photo_url": "https://t.me/b.jpg"})
        response = self.client.post(self.url, {"init_data": second})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_new_user"])
        self.assertEqual(User.objects.get(telegram_id=781).avatar_url, "https://t.me/b.jpg")


class MeAndFriendsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(telegram_id=1, full_name="Me")
        self.friend = User.objects.create_user(telegram_id=2, full_name="Friend", telegram_username="friendy")
        self.client.force_authenticate(self.user)

    def test_patch_me_updates_language_and_onboards(self):
        response = self.client.patch(
            "/api/accounts/me",
            {"full_name": "New Name", "region": "Tashkent", "language": "en"},
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.language, "en")
        self.assertTrue(self.user.is_onboarded)

    def test_friend_accept_route_uses_int_pk(self):
        friendship = Friendship.objects.create(user=self.friend, friend=self.user)
        response = self.client.post(f"/api/accounts/friends/{friendship.id}/accept")
        self.assertEqual(response.status_code, 200)
        friendship.refresh_from_db()
        self.assertEqual(friendship.status, Friendship.Status.ACCEPTED)
        self.assertTrue(
            Friendship.objects.filter(
                user=self.user, friend=self.friend, status=Friendship.Status.ACCEPTED
            ).exists()
        )

    def test_friend_add_by_username_ignores_null_phone_users(self):
        # A telegram-only user (phone=None) must not be matched when adding by username.
        response = self.client.post("/api/accounts/friends/add", {"telegram_username": "@friendy"})
        self.assertEqual(response.status_code, 201)
        friendship = Friendship.objects.get(user=self.user)
        self.assertEqual(friendship.friend_id, self.friend.id)
