from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import DeviceToken, NotificationLog
from .services import notify

User = get_user_model()


class NotifyPushDisabledByDefaultTests(APITestCase):
    """`notify()` must behave identically to the pre-push behavior when no
    FIREBASE_CREDENTIALS_PATH is configured (the default, real state right now).
    """

    def setUp(self):
        self.user = User.objects.create_user(telegram_id=101, full_name="Push Tester")

    @patch("apps.notifications.services.send_message", return_value=True)
    def test_notify_sends_telegram_and_skips_push_silently(self, mock_send_message):
        log = notify(self.user, NotificationLog.NotificationType.BADGE_UNLOCKED, badge_title="First Goal")

        # Telegram path unaffected.
        mock_send_message.assert_called_once()
        self.assertEqual(log.status, NotificationLog.Status.SENT)
        self.assertEqual(log.type, NotificationLog.NotificationType.BADGE_UNLOCKED)

    @patch("apps.notifications.services.send_message", return_value=True)
    def test_notify_does_not_crash_with_active_device_token_but_no_credentials(self, mock_send_message):
        DeviceToken.objects.create(user=self.user, token="fake-fcm-token", platform=DeviceToken.Platform.ANDROID)

        # Should not raise even though the user has an active device token —
        # push must no-op because FIREBASE_CREDENTIALS_PATH is unset.
        log = notify(self.user, NotificationLog.NotificationType.BADGE_UNLOCKED, badge_title="No Crash")

        self.assertEqual(log.status, NotificationLog.Status.SENT)


class DeviceTokenRegisterViewTests(APITestCase):
    url = "/api/notifications/devices/"

    def setUp(self):
        self.user = User.objects.create_user(telegram_id=202, full_name="Device Tester")
        self.client.force_authenticate(self.user)

    def test_register_creates_device_token(self):
        response = self.client.post(
            self.url, {"token": "tok-1", "platform": "android", "device_id": "device-abc"}
        )
        self.assertEqual(response.status_code, 200)
        device_token = DeviceToken.objects.get(token="tok-1")
        self.assertEqual(device_token.user, self.user)
        self.assertEqual(device_token.platform, "android")
        self.assertTrue(device_token.is_active)

    def test_register_upserts_same_token(self):
        self.client.post(self.url, {"token": "tok-2", "platform": "ios", "device_id": "device-xyz"})
        response = self.client.post(self.url, {"token": "tok-2", "platform": "ios", "device_id": "device-xyz"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(DeviceToken.objects.filter(token="tok-2").count(), 1)

    def test_register_deactivates_old_token_for_same_device_id(self):
        self.client.post(self.url, {"token": "old-tok", "platform": "ios", "device_id": "device-1"})
        self.client.post(self.url, {"token": "new-tok", "platform": "ios", "device_id": "device-1"})

        old = DeviceToken.objects.get(token="old-tok")
        new = DeviceToken.objects.get(token="new-tok")
        self.assertFalse(old.is_active)
        self.assertTrue(new.is_active)

    def test_unregister_deactivates_token(self):
        self.client.post(self.url, {"token": "tok-3", "platform": "android", "device_id": "device-3"})
        response = self.client.post("/api/notifications/devices/unregister/", {"token": "tok-3"})
        self.assertEqual(response.status_code, 204)
        self.assertFalse(DeviceToken.objects.get(token="tok-3").is_active)
