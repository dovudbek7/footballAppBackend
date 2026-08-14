"""Localized bot copy for the onboarding flow (uz/ru/en).

Keys are looked up as TEXTS[lang][key]; `t(lang, key, **fmt)` falls back to
Uzbek when a language or key is missing.
"""

TEXTS = {
    "uz": {
        "choose_language": "Assalomu alaykum! ⚽ <b>FutbolGo</b>'ga xush kelibsiz.\n\nTilni tanlang:",
        "language_saved": "Ajoyib! Til: <b>O'zbekcha</b> 🇺🇿",
        "ask_phone": (
            "Ro'yxatdan o'tish uchun telefon raqamingizni yuboring.\n"
            "Quyidagi tugmani bosing 👇"
        ),
        "share_phone_button": "📱 Raqamni yuborish",
        "invalid_contact": "Iltimos, tugma orqali <b>o'zingizning</b> raqamingizni yuboring.",
        "ask_name": "Rahmat! Endi ism-familiyangizni yozing:",
        "invalid_name": "Iltimos, ismingizni matn ko'rinishida yuboring (2-120 belgi).",
        "ask_region": "Qaysi hududdansiz? Tanlang:",
        "intro": (
            "🎉 Tayyor, <b>{name}</b>!\n\n"
            "<b>FutbolGo</b> — havaskor futbol uchun yagona ilova:\n"
            "⚽ Stadion bron qiling va o'yinlarga qo'shiling\n"
            "👥 Do'stlaringizni taklif qiling — to'lovni bo'lishib to'lang\n"
            "💰 Hamyon orqali qulay to'lov\n"
            "🏆 Reyting, bejdjlar va statistika\n\n"
            "Boshlash uchun quyidagi tugmani bosing 👇"
        ),
        "welcome_back": "Qaytganingizdan xursandmiz, <b>{name}</b>! ⚽\nIlovani ochish uchun tugmani bosing 👇",
        "open_app_button": "⚽ Ilovani ochish",
        "help": (
            "FutbolGo bot ⚽\n\n"
            "/start — ilovani ochish yoki ro'yxatdan o'tish\n"
            "/language — tilni o'zgartirish\n"
            "/help — yordam\n\n"
            "Stadion bron qilish, o'yinlar va hamyon — barchasi Mini App ichida."
        ),
        "phone_linked_other": (
            "Bu telefon raqami boshqa Telegram hisobiga bog'langan. "
            "Xatolik deb hisoblasangiz, qo'llab-quvvatlash xizmatiga murojaat qiling."
        ),
    },
    "ru": {
        "choose_language": "Здравствуйте! ⚽ Добро пожаловать в <b>FutbolGo</b>.\n\nВыберите язык:",
        "language_saved": "Отлично! Язык: <b>Русский</b> 🇷🇺",
        "ask_phone": (
            "Для регистрации отправьте свой номер телефона.\n"
            "Нажмите кнопку ниже 👇"
        ),
        "share_phone_button": "📱 Отправить номер",
        "invalid_contact": "Пожалуйста, отправьте <b>свой</b> номер через кнопку.",
        "ask_name": "Спасибо! Теперь напишите ваше имя и фамилию:",
        "invalid_name": "Пожалуйста, отправьте имя текстом (2-120 символов).",
        "ask_region": "Из какого вы региона? Выберите:",
        "intro": (
            "🎉 Готово, <b>{name}</b>!\n\n"
            "<b>FutbolGo</b> — всё для любительского футбола:\n"
            "⚽ Бронируйте стадионы и присоединяйтесь к матчам\n"
            "👥 Приглашайте друзей — делите оплату\n"
            "💰 Удобная оплата через кошелёк\n"
            "🏆 Рейтинг, бейджи и статистика\n\n"
            "Нажмите кнопку ниже, чтобы начать 👇"
        ),
        "welcome_back": "Рады видеть вас снова, <b>{name}</b>! ⚽\nНажмите кнопку, чтобы открыть приложение 👇",
        "open_app_button": "⚽ Открыть приложение",
        "help": (
            "Бот FutbolGo ⚽\n\n"
            "/start — открыть приложение или зарегистрироваться\n"
            "/language — сменить язык\n"
            "/help — помощь\n\n"
            "Бронирование стадионов, матчи и кошелёк — всё в Mini App."
        ),
        "phone_linked_other": (
            "Этот номер телефона привязан к другому Telegram-аккаунту. "
            "Если это ошибка, обратитесь в поддержку."
        ),
    },
    "en": {
        "choose_language": "Hello! ⚽ Welcome to <b>FutbolGo</b>.\n\nChoose your language:",
        "language_saved": "Great! Language: <b>English</b> 🇬🇧",
        "ask_phone": (
            "To sign up, share your phone number.\n"
            "Tap the button below 👇"
        ),
        "share_phone_button": "📱 Share my number",
        "invalid_contact": "Please share <b>your own</b> number using the button.",
        "ask_name": "Thanks! Now type your full name:",
        "invalid_name": "Please send your name as text (2-120 characters).",
        "ask_region": "Which region are you from? Pick one:",
        "intro": (
            "🎉 All set, <b>{name}</b>!\n\n"
            "<b>FutbolGo</b> — everything for amateur football:\n"
            "⚽ Book pitches and join matches\n"
            "👥 Invite friends — split the payment\n"
            "💰 Pay easily from your wallet\n"
            "🏆 Rating, badges and stats\n\n"
            "Tap the button below to get started 👇"
        ),
        "welcome_back": "Welcome back, <b>{name}</b>! ⚽\nTap the button to open the app 👇",
        "open_app_button": "⚽ Open the app",
        "help": (
            "FutbolGo bot ⚽\n\n"
            "/start — open the app or sign up\n"
            "/language — change language\n"
            "/help — help\n\n"
            "Pitch booking, matches and wallet all live inside the Mini App."
        ),
        "phone_linked_other": (
            "This phone number is linked to a different Telegram account. "
            "Contact support if you believe this is a mistake."
        ),
    },
}

# Region display labels per language, keyed by the canonical English name
# stored in User.region (apps/core/constants.py).
REGION_LABELS = {
    "uz": {
        "Tashkent": "Toshkent",
        "Andijan": "Andijon",
        "Bukhara": "Buxoro",
        "Fergana": "Farg'ona",
        "Jizzakh": "Jizzax",
        "Kashkadarya": "Qashqadaryo",
        "Khorezm": "Xorazm",
        "Namangan": "Namangan",
        "Navoi": "Navoiy",
        "Samarkand": "Samarqand",
        "Sirdarya": "Sirdaryo",
        "Surkhandarya": "Surxondaryo",
        "Karakalpakstan": "Qoraqalpog'iston",
    },
    "ru": {
        "Tashkent": "Ташкент",
        "Andijan": "Андижан",
        "Bukhara": "Бухара",
        "Fergana": "Фергана",
        "Jizzakh": "Джизак",
        "Kashkadarya": "Кашкадарья",
        "Khorezm": "Хорезм",
        "Namangan": "Наманган",
        "Navoi": "Навои",
        "Samarkand": "Самарканд",
        "Sirdarya": "Сырдарья",
        "Surkhandarya": "Сурхандарья",
        "Karakalpakstan": "Каракалпакстан",
    },
    "en": {},  # canonical names are already English
}


def t(lang: str, key: str, **fmt) -> str:
    table = TEXTS.get(lang) or TEXTS["uz"]
    text = table.get(key) or TEXTS["uz"].get(key, key)
    return text.format(**fmt) if fmt else text


def region_label(lang: str, region: str) -> str:
    return REGION_LABELS.get(lang, {}).get(region, region)
