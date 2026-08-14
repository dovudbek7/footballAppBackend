import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from django.conf import settings

from apps.notifications.models import NotificationLog
from apps.notifications.services import notify

from .models import Language, OTPCode, TelegramLinkToken, User

INITDATA_MAX_AGE_SECONDS = 24 * 60 * 60


class TelegramAuthError(Exception):
    pass


def request_otp(phone: str) -> dict:
    """Step 1 of the OTP flow. Returns a dict describing what the frontend should do next.

    - {"status": "otp_sent"} — code was just DMed via Telegram (or returned inline in OTP_DEBUG_MODE).
    - {"status": "link_required", "deep_link": ...} — phone has no linked telegram_id yet;
      frontend should open the deep link and poll link-status.
    """
    if settings.OTP_DEBUG_MODE:
        otp = OTPCode.issue(phone)
        return {"status": "otp_sent", "debug_code": otp.code}

    user = User.objects.filter(phone=phone).first()
    if user and user.telegram_id:
        otp = OTPCode.issue(phone)
        notify(user, NotificationLog.NotificationType.OTP_CODE, code=otp.code)
        return {"status": "otp_sent"}

    token = TelegramLinkToken.issue(phone)
    return {
        "status": "link_required",
        "deep_link": token.deep_link(settings.TELEGRAM_BOT_USERNAME),
        "token": token.token,
    }


def link_status(token: str) -> dict:
    link = TelegramLinkToken.objects.filter(token=token).first()
    if not link:
        return {"status": "not_found"}
    if link.status == TelegramLinkToken.Status.LINKED:
        return {"status": "otp_sent"}
    if link.is_expired:
        return {"status": "expired"}
    return {"status": "pending"}


def verify_otp(phone: str, code: str) -> tuple[User, bool]:
    otp = (
        OTPCode.objects.filter(phone=phone, purpose=OTPCode.Purpose.LOGIN)
        .order_by("-created_at")
        .first()
    )
    if not otp or not otp.verify(code):
        raise TelegramAuthError("Invalid or expired code.")

    user, created = User.objects.get_or_create(phone=phone)
    return user, created


def _validate_init_data(init_data: str) -> dict:
    """Validate a Telegram Mini App initData string per Telegram's documented algorithm.

    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    pairs = dict(parse_qsl(init_data, strict_parsing=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise TelegramAuthError("Missing hash in init_data.")

    auth_date = pairs.get("auth_date")
    if not auth_date or time.time() - int(auth_date) > INITDATA_MAX_AGE_SECONDS:
        raise TelegramAuthError("init_data is expired.")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", settings.TELEGRAM_BOT_TOKEN.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise TelegramAuthError("Invalid init_data signature.")

    return pairs


def _initial_language(language_code: str | None) -> str:
    """Map Telegram's language_code to a supported app language."""
    if language_code:
        code = language_code.split("-")[0].lower()
        if code in Language.values:
            return code
    return Language.UZBEK


def authenticate_telegram_webapp(init_data: str) -> tuple[User, bool]:
    pairs = _validate_init_data(init_data)
    tg_user = json.loads(pairs["user"])
    telegram_id = tg_user["id"]

    user, created = User.objects.get_or_create(
        telegram_id=telegram_id,
        defaults={
            "telegram_username": tg_user.get("username", ""),
            "full_name": " ".join(filter(None, [tg_user.get("first_name"), tg_user.get("last_name")])),
            "avatar_url": tg_user.get("photo_url", ""),
            "language": _initial_language(tg_user.get("language_code")),
        },
    )
    if not created:
        update_fields = []
        if tg_user.get("username") and user.telegram_username != tg_user["username"]:
            user.telegram_username = tg_user["username"]
            update_fields.append("telegram_username")
        if tg_user.get("photo_url") and user.avatar_url != tg_user["photo_url"]:
            user.avatar_url = tg_user["photo_url"]
            update_fields.append("avatar_url")
        if update_fields:
            user.save(update_fields=update_fields)
    return user, created
