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
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from django.utils import timezone

from . import onboarding
from .texts import t

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
async def start_plain(message: Message, state: FSMContext):
    from apps.accounts.models import User

    user = await User.objects.filter(telegram_id=message.from_user.id).afirst()
    if user and user.is_onboarded:
        await message.answer(
            t(user.language, "welcome_back", name=user.full_name or message.from_user.first_name),
            reply_markup=onboarding.open_app_keyboard(user.language),
        )
        return

    await onboarding.begin_onboarding(message, state)


@router.message(Command("language"))
async def language_command(message: Message):
    from apps.accounts.models import User

    user = await User.objects.filter(telegram_id=message.from_user.id).afirst()
    lang = user.language if user else "uz"
    await message.answer(
        t(lang, "choose_language"),
        reply_markup=onboarding._language_keyboard(prefix="setlang"),
    )


@router.message(Command("help"))
async def help_command(message: Message):
    from apps.accounts.models import User

    user = await User.objects.filter(telegram_id=message.from_user.id).afirst()
    await message.answer(t(user.language if user else "uz", "help"))


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(router)
    dp.include_router(onboarding.router)
    return dp
