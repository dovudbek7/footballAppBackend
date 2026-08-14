"""Thin outbound Telegram Bot API wrapper.

Imported by both the `web` process (Django views/signals send notifications
synchronously via HTTP) and the `bot` process (aiogram handlers). Keeping this
as a plain function around `requests` — not aiogram's async client — means the
synchronous Django request/response cycle never needs an event loop just to
DM a user.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org"


def send_message(telegram_id: int, text: str, parse_mode: str = "HTML") -> bool:
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set — skipping send to %s: %s", telegram_id, text)
        return False
    try:
        response = requests.post(
            f"{API_BASE}/bot{token}/sendMessage",
            json={"chat_id": telegram_id, "text": text, "parse_mode": parse_mode},
            timeout=10,
        )
        response.raise_for_status()
        return True
    except requests.RequestException:
        logger.exception("Failed to send Telegram message to %s", telegram_id)
        return False
