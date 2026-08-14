"""aiogram v3 update handlers for the FutbolGo bot.

Runs as its own process (`python manage.py runbot`) but imports the Django ORM
directly — one codebase, one migration history, no duplicated models in a
second framework. Only handles *inbound* Telegram updates; outbound
notifications triggered from app logic (bookings, wallet, etc.) are sent
synchronously from the `web` process via `bot/telegram_client.py` (see
apps/notifications/services.py). This module only needs to send a message
back to whoever just messaged the bot, so it uses aiogram's own `message.answer`
directly instead of going through that synchronous HTTP helper.
"""

import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message
from django.utils import timezone

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart(deep_link=True))
async def start_with_token(message: Message, command: CommandObject):
    from apps.accounts.models import OTPCode, TelegramLinkToken, User

    token = command.args
    link = await TelegramLinkToken.objects.filter(token=token).afirst()

    if not link or link.is_expired:
        await message.answer("This login link has expired. Please request a new one on the website.")
        return

    if link.status == TelegramLinkToken.Status.LINKED:
        await message.answer("This link was already used. Please request a new one on the website.")
        return

    existing_owner = await User.objects.filter(
        telegram_id=message.from_user.id
    ).exclude(phone=link.phone).afirst()
    if existing_owner:
        await message.answer(
            "This Telegram account is already linked to a different phone number. "
            "Contact support if you believe this is a mistake."
        )
        return

    user, _ = await User.objects.aget_or_create(phone=link.phone)
    user.telegram_id = message.from_user.id
    user.telegram_username = message.from_user.username or ""
    await user.asave(update_fields=["telegram_id", "telegram_username"])

    otp = await OTPCode.objects.acreate(
        phone=link.phone,
        expires_at=timezone.now() + timezone.timedelta(seconds=OTPCode.TTL_SECONDS),
    )

    link.telegram_id = message.from_user.id
    link.status = TelegramLinkToken.Status.LINKED
    link.otp_code = otp
    await link.asave(update_fields=["telegram_id", "status", "otp_code"])

    await message.answer(f"Your FutbolGo login code: <b>{otp.code}</b> (valid 5 min).", parse_mode="HTML")


@router.message(CommandStart())
async def start_plain(message: Message):
    await message.answer(
        "Welcome to FutbolGo ⚽️\n"
        "Open the Mini App from the menu button to book a pitch, or log in on the website — "
        "you'll get a login code here."
    )


@router.message(Command("help"))
async def help_command(message: Message):
    await message.answer("FutbolGo bot: book pitches, find matches, get notified. Open the Mini App to get started.")


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(router)
    return dp


async def run_polling(bot: Bot) -> None:
    dp = build_dispatcher()
    await dp.start_polling(bot)
