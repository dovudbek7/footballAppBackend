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


async def begin_onboarding(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(Onboarding.language)
    await message.answer(t("uz", "choose_language"), reply_markup=_language_keyboard())


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
