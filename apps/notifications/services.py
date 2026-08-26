import logging
import os

from django.conf import settings

from bot.telegram_client import send_message

from .models import DeviceToken, NotificationLog

logger = logging.getLogger(__name__)

_TEMPLATES = {
    NotificationLog.NotificationType.OTP_CODE: "Your Sportify login code: <b>{code}</b> (valid 5 min).",
    NotificationLog.NotificationType.TELEGRAM_LINK: "Telegram linked to Sportify. Sending your login code now...",
    NotificationLog.NotificationType.BOOKING_CONFIRMED: (
        "✅ Booking confirmed: {stadium_name} on {date} at {time}."
    ),
    NotificationLog.NotificationType.SPLIT_REQUEST: (
        "⚽ {organizer_name} invited you to split-pay a seat at {stadium_name} "
        "on {date} at {time} — your share: ${amount}."
    ),
    NotificationLog.NotificationType.MATCH_REMINDER: (
        "⏰ Reminder: your match at {stadium_name} starts in {minutes} min."
    ),
    NotificationLog.NotificationType.WAITLIST_FILLED: (
        "🏁 Your match at {stadium_name} on {date} is now full — confirmed!"
    ),
    NotificationLog.NotificationType.SPLIT_EXPIRED: (
        "⌛ The split-pay seat you reserved for {friend_name} at {stadium_name} expired unpaid and was released."
    ),
    NotificationLog.NotificationType.BADGE_UNLOCKED: "🏆 Badge unlocked: {badge_title}!",
    NotificationLog.NotificationType.TOPUP_APPROVED: "💰 Top-up approved: ${amount} added to your wallet.",
    NotificationLog.NotificationType.FRIEND_REQUEST: (
        "🤝 {requester_name} sent you a friend request."
    ),
    NotificationLog.NotificationType.FRIEND_ACCEPTED: (
        "🤝 {friend_name} accepted your friend request."
    ),
    NotificationLog.NotificationType.MATCH_INVITE: (
        "⚽ {organizer_name} invited you to a match at {stadium_name} on {date} at {time}."
    ),
    NotificationLog.NotificationType.ORGANIZER_REQUEST_APPROVED: (
        "🎉 Tabriklaymiz! Organizer bo'lish so'rovingiz tasdiqlandi — endi o'zingiz o'yin yaratishingiz mumkin."
    ),
    NotificationLog.NotificationType.ORGANIZER_REQUEST_REJECTED: (
        "Organizer bo'lish so'rovingiz rad etildi."
    ),
}


def render_text(notification_type: str, **context) -> str:
    template = _TEMPLATES.get(notification_type, "{message}")
    return template.format(**context)


# --- Push (Firebase Cloud Messaging) -----------------------------------------
#
# Fully additive to the Telegram DM path above. Until a real Firebase
# service-account credentials file is dropped on disk and
# `FIREBASE_CREDENTIALS_PATH` is pointed at it, every function below is a
# silent no-op — no import of `firebase_admin`, no network call, no crash.
# This is intentional: it lets the DeviceToken registration API and this
# codepath ship ahead of the mobile app actually having Firebase configured.

_firebase_app_cache = {"initialized": False, "app": None}


def _get_firebase_app():
    """Lazily initializes and caches the Firebase app, or None if unconfigured."""
    if _firebase_app_cache["initialized"]:
        return _firebase_app_cache["app"]

    _firebase_app_cache["initialized"] = True

    credentials_path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", "") or ""
    if not credentials_path or not os.path.exists(credentials_path):
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials

        cred = credentials.Certificate(credentials_path)
        _firebase_app_cache["app"] = firebase_admin.initialize_app(cred)
    except Exception:
        logger.exception("Failed to initialize Firebase app from FIREBASE_CREDENTIALS_PATH")
        _firebase_app_cache["app"] = None

    return _firebase_app_cache["app"]


def _send_push(user, text: str) -> None:
    """Best-effort push send to every active device of `user`. Never raises."""
    app = _get_firebase_app()
    if app is None:
        return

    device_tokens = list(DeviceToken.objects.filter(user=user, is_active=True))
    if not device_tokens:
        return

    from firebase_admin import messaging

    for device_token in device_tokens:
        message = messaging.Message(
            notification=messaging.Notification(title="Sportify", body=text),
            token=device_token.token,
        )
        try:
            messaging.send(message, app=app)
        except messaging.UnregisteredError:
            device_token.is_active = False
            device_token.save(update_fields=["is_active"])
        except Exception:
            # Any other FCM/network failure: log and move on to the next
            # token rather than let one bad device fail the whole notify().
            logger.exception("Failed to send push notification to device token id=%s", device_token.id)


def notify(user, notification_type: str, **context) -> NotificationLog:
    text = render_text(notification_type, **context)

    if not user.telegram_id:
        log = NotificationLog.objects.create(
            user=user,
            telegram_id=None,
            type=notification_type,
            text=text,
            payload=context,
            status=NotificationLog.Status.SKIPPED,
            error_text="User has no linked telegram_id",
        )
    else:
        sent = send_message(user.telegram_id, text)
        log = NotificationLog.objects.create(
            user=user,
            telegram_id=user.telegram_id,
            type=notification_type,
            text=text,
            payload=context,
            status=NotificationLog.Status.SENT if sent else NotificationLog.Status.FAILED,
        )

    _send_push(user, text)

    return log
