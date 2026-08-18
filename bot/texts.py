"""Localized bot copy for the onboarding flow (uz/ru/en).

Keys are looked up as TEXTS[lang][key]; `t(lang, key, **fmt)` falls back to
Uzbek when a language or key is missing.
"""

TEXTS = {
    "uz": {
        "choose_language": "Assalomu alaykum! ⚽ <b>Sportify</b>'ga xush kelibsiz.\n\nTilni tanlang:",
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
            "<b>Sportify</b> — havaskor futbol uchun yagona ilova:\n"
            "⚽ Stadion bron qiling va o'yinlarga qo'shiling\n"
            "👥 Do'stlaringizni taklif qiling — to'lovni bo'lishib to'lang\n"
            "💰 Hamyon orqali qulay to'lov\n"
            "🏆 Reyting, bejdjlar va statistika\n\n"
            "Boshlash uchun quyidagi tugmani bosing 👇"
        ),
        "welcome_back": "Qaytganingizdan xursandmiz, <b>{name}</b>! ⚽\nIlovani ochish uchun tugmani bosing 👇",
        "open_app_button": "⚽ Ilovani ochish",
        "help": (
            "Sportify bot ⚽\n\n"
            "/start — ilovani ochish yoki ro'yxatdan o'tish\n"
            "/mymatches — kelayotgan o'yinlaringiz\n"
            "/today — bugungi bo'sh o'yinlar\n"
            "/referal — do'stlaringizni taklif qiling\n"
            "/language — tilni o'zgartirish\n"
            "/help — yordam\n\n"
            "Stadion bron qilish, o'yinlar va hamyon — barchasi Mini App ichida."
        ),
        "phone_linked_other": (
            "Bu telefon raqami boshqa Telegram hisobiga bog'langan. "
            "Xatolik deb hisoblasangiz, qo'llab-quvvatlash xizmatiga murojaat qiling."
        ),
        "not_registered": "Avval /start bosib ro'yxatdan o'ting.",
        "referal_text": (
            "👥 Do'stlaringizni <b>Sportify</b>'ga taklif qiling!\n\n"
            "Havolangiz:\n{link}\n\n"
            "Ular havola orqali kirsa, avtomatik do'stlik so'rovi yuboriladi."
        ),
        "referal_share_button": "Do'stlarga ulashish",
        "referal_share_text": "⚽ Sportify'da futbolga qo'shil! Havola orqali ro'yxatdan o't:",
        "referral_added": "✅ {name} bilan do'stlik so'rovi yuborildi!",
        "mymatches_header": "📅 Kelayotgan o'yinlaringiz:",
        "mymatches_empty": "Hozircha kelayotgan o'yinlaringiz yo'q. Ilovadan stadion tanlab bron qiling.",
        "mymatches_item": "{stadium} · {date} {time} — {status}",
        "today_header": "⚡ Bugungi bo'sh o'yinlar:",
        "today_empty": "Bugun bo'sh o'yinlar yo'q — ilovadan yangi o'yin tashkil qiling yoki keyinroq tekshiring.",
        "today_item": "{stadium} · {time} — {spots} joy bo'sh",
        "open_button": "Ochish",
    },
    "ru": {
        "choose_language": "Здравствуйте! ⚽ Добро пожаловать в <b>Sportify</b>.\n\nВыберите язык:",
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
            "<b>Sportify</b> — всё для любительского футбола:\n"
            "⚽ Бронируйте стадионы и присоединяйтесь к матчам\n"
            "👥 Приглашайте друзей — делите оплату\n"
            "💰 Удобная оплата через кошелёк\n"
            "🏆 Рейтинг, бейджи и статистика\n\n"
            "Нажмите кнопку ниже, чтобы начать 👇"
        ),
        "welcome_back": "Рады видеть вас снова, <b>{name}</b>! ⚽\nНажмите кнопку, чтобы открыть приложение 👇",
        "open_app_button": "⚽ Открыть приложение",
        "help": (
            "Бот Sportify ⚽\n\n"
            "/start — открыть приложение или зарегистрироваться\n"
            "/mymatches — ваши предстоящие матчи\n"
            "/today — свободные матчи сегодня\n"
            "/referal — пригласить друзей\n"
            "/language — сменить язык\n"
            "/help — помощь\n\n"
            "Бронирование стадионов, матчи и кошелёк — всё в Mini App."
        ),
        "phone_linked_other": (
            "Этот номер телефона привязан к другому Telegram-аккаунту. "
            "Если это ошибка, обратитесь в поддержку."
        ),
        "not_registered": "Сначала нажмите /start, чтобы зарегистрироваться.",
        "referal_text": (
            "👥 Приглашайте друзей в <b>Sportify</b>!\n\n"
            "Ваша ссылка:\n{link}\n\n"
            "Когда друг перейдёт по ссылке, ему автоматически отправится заявка в друзья."
        ),
        "referal_share_button": "Поделиться с друзьями",
        "referal_share_text": "⚽ Присоединяйся к футболу в Sportify! Регистрируйся по ссылке:",
        "referral_added": "✅ Заявка в друзья отправлена {name}!",
        "mymatches_header": "📅 Ваши предстоящие матчи:",
        "mymatches_empty": "Пока нет предстоящих матчей. Забронируйте стадион в приложении.",
        "mymatches_item": "{stadium} · {date} {time} — {status}",
        "today_header": "⚡ Свободные матчи сегодня:",
        "today_empty": "Сегодня свободных матчей нет — создайте новый в приложении или проверьте позже.",
        "today_item": "{stadium} · {time} — {spots} мест свободно",
        "open_button": "Открыть",
    },
    "en": {
        "choose_language": "Hello! ⚽ Welcome to <b>Sportify</b>.\n\nChoose your language:",
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
            "<b>Sportify</b> — everything for amateur football:\n"
            "⚽ Book pitches and join matches\n"
            "👥 Invite friends — split the payment\n"
            "💰 Pay easily from your wallet\n"
            "🏆 Rating, badges and stats\n\n"
            "Tap the button below to get started 👇"
        ),
        "welcome_back": "Welcome back, <b>{name}</b>! ⚽\nTap the button to open the app 👇",
        "open_app_button": "⚽ Open the app",
        "help": (
            "Sportify bot ⚽\n\n"
            "/start — open the app or sign up\n"
            "/mymatches — your upcoming matches\n"
            "/today — today's open matches\n"
            "/referal — invite your friends\n"
            "/language — change language\n"
            "/help — help\n\n"
            "Pitch booking, matches and wallet all live inside the Mini App."
        ),
        "phone_linked_other": (
            "This phone number is linked to a different Telegram account. "
            "Contact support if you believe this is a mistake."
        ),
        "not_registered": "Tap /start first to sign up.",
        "referal_text": (
            "👥 Invite your friends to <b>Sportify</b>!\n\n"
            "Your link:\n{link}\n\n"
            "When they join via the link, a friend request is sent automatically."
        ),
        "referal_share_button": "Share with friends",
        "referal_share_text": "⚽ Join football on Sportify! Sign up via my link:",
        "referral_added": "✅ Friend request sent to {name}!",
        "mymatches_header": "📅 Your upcoming matches:",
        "mymatches_empty": "No upcoming matches yet. Book a pitch in the app.",
        "mymatches_item": "{stadium} · {date} {time} — {status}",
        "today_header": "⚡ Today's open matches:",
        "today_empty": "No open matches today — create one in the app or check back later.",
        "today_item": "{stadium} · {time} — {spots} spots left",
        "open_button": "Open",
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
