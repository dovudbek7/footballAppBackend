"""Bot-side onboarding FSM: language → phone (contact) → name → region → intro.

Runs inside the aiogram polling process. Uses the async Django ORM directly
(models imported lazily inside handlers to avoid app-registry issues).
The user row is only written at the final step, so an abandoned onboarding
leaves no half-filled users behind; webapp logins that already created a row
(by telegram_id) are picked up and completed instead.
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    WebAppInfo,
)
from django.conf import settings

from apps.core.constants import REGIONS

from .texts import region_label, t

logger = logging.getLogger(__name__)
router = Router()

LANGUAGES = [("uz", "🇺🇿 O'zbekcha"), ("ru", "🇷🇺 Русский"), ("en", "🇬🇧 English")]


class Onboarding(StatesGroup):
    language = State()
    phone = State()
    name = State()
    region = State()


def _language_keyboard(prefix: str = "lang") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"{prefix}:{code}")]
            for code, label in LANGUAGES
        ]
    )


def _region_keyboard(lang: str) -> InlineKeyboardMarkup:
    rows, row = [], []
    for i, region in enumerate(REGIONS):
        row.append(InlineKeyboardButton(text=region_label(lang, region), callback_data=f"region:{i}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def open_app_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "open_app_button"),
                    web_app=WebAppInfo(url=settings.FRONTEND_URL),
                )
            ]
        ]
    )


def _normalize_phone(raw: str) -> str:
    phone = raw.strip().replace(" ", "")
    if not phone.startswith("+"):
        phone = f"+{phone}"
    return phone


async def begin_onboarding(message: Message, state: FSMContext, referral_code: str | None = None) -> None:
    await state.clear()
    if referral_code:
        await state.update_data(referral_code=referral_code)
    await state.set_state(Onboarding.language)
    await message.answer(t("uz", "choose_language"), reply_markup=_language_keyboard())


async def handle_referral_start(message: Message, state: FSMContext, code: str) -> None:
    """/start ref_<code> deep link — from the Friends-page share button or /referal.

    An already-onboarded user gets an instant friend request sent to the
    referrer; a new/incomplete signup carries the code through the FSM and
    the request is sent once onboarding finishes in `region_chosen`.
    """
    from apps.accounts.models import Friendship, User
    from apps.wallet.models import Wallet

    code = (code or "").strip().upper()
    wallet = await Wallet.objects.filter(paynet_id=code).select_related("user").afirst()
    referrer = wallet.user if wallet else None

    user = await User.objects.filter(telegram_id=message.from_user.id).afirst()

    if user and user.is_onboarded:
        lang = user.language
        if not referrer or referrer.id == user.id:
            await message.answer(
                t(lang, "welcome_back", name=user.full_name or message.from_user.first_name),
                reply_markup=open_app_keyboard(lang),
            )
            return

        exists = await Friendship.objects.filter(user=user, friend=referrer).aexists()
        if not exists:
            await Friendship.objects.acreate(user=user, friend=referrer)
            await _notify_referrer(message, referrer, user)

        await message.answer(
            t(lang, "referral_added", name=referrer.full_name or referrer.phone or "—"),
            reply_markup=open_app_keyboard(lang),
        )
        return

    await begin_onboarding(message, state, referral_code=code if referrer else None)


async def _notify_referrer(message: Message, referrer, new_friend) -> None:
    if not referrer.telegram_id:
        return
    try:
        await message.bot.send_message(
            referrer.telegram_id,
            t(referrer.language, "referral_friend_joined", name=new_friend.full_name or "Someone"),
            parse_mode="HTML",
        )
    except Exception:
        logger.warning("Could not notify referrer %s about new friend request", referrer.id)


@router.callback_query(Onboarding.language, F.data.startswith("lang:"))
async def language_chosen(callback: CallbackQuery, state: FSMContext):
    from apps.accounts.models import User

    lang = callback.data.split(":", 1)[1]
    if lang not in ("uz", "ru", "en"):
        lang = "uz"
    await state.update_data(language=lang)
    await callback.answer()
    await callback.message.edit_text(t(lang, "language_saved"))

    # A row may already exist from a Mini App login — persist the choice now.
    user = await User.objects.filter(telegram_id=callback.from_user.id).afirst()
    if user:
        user.language = lang
        await user.asave(update_fields=["language"])
        if user.phone:
            # Phone already known — skip straight to the name step.
            await state.set_state(Onboarding.name)
            await callback.message.answer(t(lang, "ask_name"), reply_markup=ReplyKeyboardRemove())
            return

    await state.set_state(Onboarding.phone)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(lang, "share_phone_button"), request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await callback.message.answer(t(lang, "ask_phone"), reply_markup=keyboard)


@router.message(Onboarding.phone, F.contact)
async def contact_received(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uz")

    contact = message.contact
    if not contact or contact.user_id != message.from_user.id:
        await message.answer(t(lang, "invalid_contact"))
        return

    await state.update_data(phone=_normalize_phone(contact.phone_number))
    await state.set_state(Onboarding.name)
    await message.answer(t(lang, "ask_name"), reply_markup=ReplyKeyboardRemove())


@router.message(Onboarding.phone)
async def phone_invalid(message: Message, state: FSMContext):
    data = await state.get_data()
    await message.answer(t(data.get("language", "uz"), "invalid_contact"))


@router.message(Onboarding.name, F.text)
async def name_received(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uz")

    name = (message.text or "").strip()
    if not (2 <= len(name) <= 120):
        await message.answer(t(lang, "invalid_name"))
        return

    await state.update_data(name=name)
    await state.set_state(Onboarding.region)
    await message.answer(t(lang, "ask_region"), reply_markup=_region_keyboard(lang))


@router.message(Onboarding.name)
async def name_invalid(message: Message, state: FSMContext):
    data = await state.get_data()
    await message.answer(t(data.get("language", "uz"), "invalid_name"))


@router.callback_query(Onboarding.region, F.data.startswith("region:"))
async def region_chosen(callback: CallbackQuery, state: FSMContext):
    from apps.accounts.models import User

    data = await state.get_data()
    lang = data.get("language", "uz")

    try:
        region = REGIONS[int(callback.data.split(":", 1)[1])]
    except (ValueError, IndexError):
        await callback.answer()
        return

    tg = callback.from_user
    phone = data.get("phone")

    user = await User.objects.filter(telegram_id=tg.id).afirst()
    phone_conflict = False
    if user is None and phone:
        # An OTP-created, phone-only account may already exist — attach Telegram to it.
        user = await User.objects.filter(phone=phone).afirst()
        if user and user.telegram_id and user.telegram_id != tg.id:
            user = None
            phone_conflict = True
        elif user:
            user.telegram_id = tg.id
    if user is None:
        user = User(telegram_id=tg.id)

    if phone and not phone_conflict and not user.phone:
        other = await User.objects.filter(phone=phone).exclude(pk=user.pk).afirst()
        if other:
            phone_conflict = True
        else:
            user.phone = phone

    user.full_name = data.get("name", user.full_name)
    user.region = region
    user.language = lang
    user.telegram_username = tg.username or user.telegram_username
    user.is_onboarded = True
    await user.asave()

    referral_code = data.get("referral_code")
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        f"📍 {region_label(lang, region)} ✅"
    )
    if phone_conflict:
        await callback.message.answer(t(lang, "phone_linked_other"))
    await callback.message.answer(
        t(lang, "intro", name=user.full_name),
        reply_markup=open_app_keyboard(lang),
    )

    if referral_code:
        from apps.accounts.models import Friendship
        from apps.wallet.models import Wallet

        wallet = await Wallet.objects.filter(paynet_id=referral_code).select_related("user").afirst()
        referrer = wallet.user if wallet else None
        if referrer and referrer.id != user.id:
            exists = await Friendship.objects.filter(user=user, friend=referrer).aexists()
            if not exists:
                await Friendship.objects.acreate(user=user, friend=referrer)
                await _notify_referrer(callback.message, referrer, user)


@router.callback_query(F.data.startswith("setlang:"))
async def change_language(callback: CallbackQuery):
    """/language picker for already-registered users."""
    from apps.accounts.models import User

    lang = callback.data.split(":", 1)[1]
    if lang not in ("uz", "ru", "en"):
        lang = "uz"
    user = await User.objects.filter(telegram_id=callback.from_user.id).afirst()
    if user:
        user.language = lang
        await user.asave(update_fields=["language"])
    await callback.answer()
    await callback.message.edit_text(t(lang, "language_saved"))
