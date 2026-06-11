"""
Мультимовність — один модуль на всі мови.

Що тут лежить:
  • LANGUAGE_NAMES / LANGUAGE_EN  — реєстр мов (рідна назва для кнопок +
    англійська назва для промпта);
  • UI            — рядки інтерфейсу бота (функція t);
  • LABELS        — переклади доменних міток (інтереси, бюджет, тип місця,
    час доби), які потрапляють і в промпт, і на картки;
  • detect_language / normalize_lang — визначення та нормалізація мови.

ЯК ДОДАТИ НОВУ МОВУ ІНТЕРФЕЙСУ:
  1) додай її код у LANGUAGE_EN (англ. назва, потрібна для промпта);
  2) додай рідну назву з прапорцем у LANGUAGE_NAMES;
  3) додай блок перекладів у UI[...] і в кожен словник LABELS[...].
  Кнопку вибору мови система підхопить автоматично (offered_languages()).

ВАЖЛИВО: сам ПЛАН подорожі генерується БУДЬ-ЯКОЮ мовою (це робить LLM),
навіть якщо інтерфейс для неї ще не перекладено — тоді інтерфейс і підписи
показуємо англійською (FALLBACK), а текст плану лишається мовою користувача.
"""
from __future__ import annotations

import re

from planner.models import Budget, Interest, PlaceKind, TimeOfDay

DEFAULT_LANG = "uk"
FALLBACK_LANG = "en"

# Англійська назва мови — підставляється у промпт ("Reply in <name>").
# Тут можна тримати більше мов, ніж перекладено інтерфейс: план усе одно
# згенерується цією мовою.
LANGUAGE_EN = {
    "uk": "Ukrainian",
    "en": "English",
    "es": "Spanish",
    "de": "German",
    "fr": "French",
    "it": "Italian",
    "pl": "Polish",
    "ru": "Russian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "tr": "Turkish",
    "cs": "Czech",
    "ro": "Romanian",
    "ja": "Japanese",
    "zh": "Chinese",
    "ar": "Arabic",
}

# Рідна назва мови з прапорцем — для кнопок вибору мови.
LANGUAGE_NAMES = {
    "uk": "🇺🇦 Українська",
    "en": "🇬🇧 English",
    "es": "🇪🇸 Español",
    "de": "🇩🇪 Deutsch",
    "fr": "🇫🇷 Français",
    "it": "🇮🇹 Italiano",
    "pl": "🇵🇱 Polski",
    "ru": "🇷🇺 Русский",
}


# --------------------------------------------------------------------------- #
#  Доменні мітки (інтереси / бюджет / тип місця / час доби)
#  Ключ — англійський код (Enum), значення — людська назва кожною мовою.
# --------------------------------------------------------------------------- #
LABELS: dict[str, dict[str, dict[str, str]]] = {
    "interest": {
        "uk": {
            Interest.CULTURE: "Культура",
            Interest.FOOD: "Їжа",
            Interest.NATURE: "Природа",
            Interest.NIGHTLIFE: "Розваги",
            Interest.SHOPPING: "Шопінг",
            Interest.RELAX: "Відпочинок",
        },
        "en": {
            Interest.CULTURE: "Culture",
            Interest.FOOD: "Food",
            Interest.NATURE: "Nature",
            Interest.NIGHTLIFE: "Nightlife",
            Interest.SHOPPING: "Shopping",
            Interest.RELAX: "Relax",
        },
    },
    "budget": {
        "uk": {
            Budget.LOW: "Економний",
            Budget.MEDIUM: "Середній",
            Budget.HIGH: "Преміум",
        },
        "en": {
            Budget.LOW: "Budget",
            Budget.MEDIUM: "Mid-range",
            Budget.HIGH: "Premium",
        },
    },
    "kind": {
        "uk": {
            PlaceKind.ATTRACTION: "пам'ятка",
            PlaceKind.MUSEUM: "музей",
            PlaceKind.RESTAURANT: "ресторан",
            PlaceKind.CAFE: "кафе",
            PlaceKind.PARK: "парк",
            PlaceKind.VIEWPOINT: "оглядовий майданчик",
            PlaceKind.OTHER: "локація",
        },
        "en": {
            PlaceKind.ATTRACTION: "attraction",
            PlaceKind.MUSEUM: "museum",
            PlaceKind.RESTAURANT: "restaurant",
            PlaceKind.CAFE: "café",
            PlaceKind.PARK: "park",
            PlaceKind.VIEWPOINT: "viewpoint",
            PlaceKind.OTHER: "place",
        },
    },
    "time": {
        "uk": {
            TimeOfDay.BREAKFAST: "сніданок",
            TimeOfDay.MORNING: "ранок",
            TimeOfDay.LUNCH: "обід",
            TimeOfDay.NOON: "день",
            TimeOfDay.EVENING: "вечір",
            TimeOfDay.DINNER: "вечеря",
        },
        "en": {
            TimeOfDay.BREAKFAST: "breakfast",
            TimeOfDay.MORNING: "morning",
            TimeOfDay.LUNCH: "lunch",
            TimeOfDay.NOON: "afternoon",
            TimeOfDay.EVENING: "evening",
            TimeOfDay.DINNER: "dinner",
        },
    },
}


def label(category: str, member, lang: str) -> str:
    """Людська назва доменного коду (interest/budget/kind/time) обраною мовою."""
    tables = LABELS[category]
    table = tables.get(lang) or tables[FALLBACK_LANG]
    return table.get(member) or tables[FALLBACK_LANG].get(member, str(member.value))


def interest_label(interest: Interest, lang: str) -> str:
    return label("interest", interest, lang)


def budget_label(budget: Budget, lang: str) -> str:
    return label("budget", budget, lang)


def kind_label(kind: PlaceKind, lang: str) -> str:
    return label("kind", kind, lang)


def time_label(time: TimeOfDay, lang: str) -> str:
    return label("time", time, lang)


# --------------------------------------------------------------------------- #
#  Рядки інтерфейсу бота
# --------------------------------------------------------------------------- #
UI: dict[str, dict[str, str]] = {
    "uk": {
        "start": (
            "✈️ <b>Привіт! Я твій тревел-планер.</b>\n\n"
            "Складу тобі детальний план подорожі по днях — з місцями, "
            "ресторанами, маршрутами і гарними картками.\n\n"
            "Почнемо! <b>Куди плануєш поїхати?</b>\n"
            "<i>Напиши місто, напр.: Прага, Барселона, Рим…</i>"
        ),
        "cancel": "Скасовано. Напиши /start, щоб почати спочатку.",
        "city_too_short": "Хм, напиши, будь ласка, назву міста ще раз 🙂",
        "city_not_found": (
            "Хм, не можу знайти такого міста 🤔\n"
            "Перевір назву і напиши ще раз — напр.: <b>Рим</b>, <b>Барселона</b>."
        ),
        "city_ok": (
            "Чудовий вибір — <b>{city}</b>! 🌍\n\n"
            "<b>На скільки днів</b> ця подорож?\n"
            "<i>Напиши число, напр.: 3</i>"
        ),
        "city_wrong_type": (
            "Напиши, будь ласка, назву міста <b>текстом</b> 🙂\n"
            "<i>Голосові я поки не розумію — просто надрукуй місто, напр.: Рим.</i>"
        ),
        "days_invalid": "Напиши число від 1 до 30, будь ласка 🙂",
        "ask_interests": "Супер! Тепер обери, <b>що тобі цікаво</b> (можна кілька):",
        "days_wrong_type": "Напиши, будь ласка, <b>число</b> днів текстом 🙂 (напр.: 3)",
        "ask_budget": "І останнє — <b>який бюджет</b>?",
        "building": (
            "🧭 Готую твій план по <b>{city}</b> на {days} дн.\n"
            "Це займе хвилинку — складаю маршрут, шукаю місця і малюю картки…"
        ),
        "error": (
            "😔 Ой, щось пішло не так під час побудови плану.\n"
            "Спробуй ще раз: /start"
        ),
        "done": (
            "Готово! 🎒 Гарної подорожі!\n"
            "Збережи картки собі — вони працюють і офлайн.\n\n"
            "Хочеш ще один маршрут? Напиши /start"
        ),
        "btn_done": "➡️ Готово",
        "choose_language": "🌍 Оберіть мову / Choose your language:",
        "language_set": "Готово! Тепер спілкуюся з тобою українською 🇺🇦",
        # картки
        "card_day": "День",
        "card_transport": "Транспорт",
    },
    "en": {
        "start": (
            "✈️ <b>Hi! I'm your travel planner.</b>\n\n"
            "I'll build you a detailed day-by-day trip plan — with places, "
            "restaurants, routes and beautiful cards.\n\n"
            "Let's start! <b>Where would you like to go?</b>\n"
            "<i>Type a city, e.g.: Prague, Barcelona, Rome…</i>"
        ),
        "cancel": "Cancelled. Type /start to begin again.",
        "city_too_short": "Hmm, please type the city name once more 🙂",
        "city_not_found": (
            "Hmm, I can't find that city 🤔\n"
            "Check the spelling and try again — e.g.: <b>Rome</b>, <b>Barcelona</b>."
        ),
        "city_ok": (
            "Great choice — <b>{city}</b>! 🌍\n\n"
            "<b>How many days</b> is this trip?\n"
            "<i>Type a number, e.g.: 3</i>"
        ),
        "city_wrong_type": (
            "Please type the city name as <b>text</b> 🙂\n"
            "<i>I can't understand voice yet — just type the city, e.g.: Rome.</i>"
        ),
        "days_invalid": "Please type a number from 1 to 30 🙂",
        "ask_interests": "Great! Now pick <b>what you're into</b> (you can choose several):",
        "days_wrong_type": "Please type the <b>number</b> of days as text 🙂 (e.g.: 3)",
        "ask_budget": "And last — <b>what's your budget</b>?",
        "building": (
            "🧭 Building your plan for <b>{city}</b>, {days} day(s).\n"
            "This will take a minute — routing, finding places and drawing cards…"
        ),
        "error": (
            "😔 Oops, something went wrong while building the plan.\n"
            "Please try again: /start"
        ),
        "done": (
            "Done! 🎒 Have a wonderful trip!\n"
            "Save the cards — they work offline too.\n\n"
            "Want another route? Type /start"
        ),
        "btn_done": "➡️ Done",
        "choose_language": "🌍 Choose your language / Оберіть мову:",
        "language_set": "Done! I'll talk to you in English now 🇬🇧",
        # cards
        "card_day": "Day",
        "card_transport": "Transport",
    },
}


def t(key: str, lang: str, **kwargs) -> str:
    """Рядок інтерфейсу за ключем потрібною мовою (з фолбеком на англійську)."""
    table = UI.get(lang) or UI[FALLBACK_LANG]
    text = table.get(key) or UI[FALLBACK_LANG].get(key, key)
    return text.format(**kwargs) if kwargs else text


# --------------------------------------------------------------------------- #
#  Реєстр / нормалізація / визначення мови
# --------------------------------------------------------------------------- #
def offered_languages() -> list[str]:
    """Мови, для яких є перекладений інтерфейс (показуємо кнопками)."""
    order = list(LANGUAGE_NAMES.keys())
    have = [c for c in order if c in UI]
    # додати решту наявних UI-мов, яких немає в порядку (про всяк випадок)
    have += [c for c in UI if c not in have]
    return have


def language_native_name(code: str) -> str:
    return LANGUAGE_NAMES.get(code, LANGUAGE_EN.get(code, code))


def english_language_name(code: str) -> str:
    """Англійська назва мови для промпта (фолбек — сам код)."""
    return LANGUAGE_EN.get(code, code)


def normalize_lang(code: str | None) -> str:
    """'en-US' -> 'en'. Невідоме/порожнє -> DEFAULT_LANG."""
    if not code:
        return DEFAULT_LANG
    base = code.strip().lower().replace("_", "-").split("-")[0]
    return base or DEFAULT_LANG


# Українські літери, яких немає в російській абетці — надійний маркер uk.
_UK_ONLY = set("іїєґ")
_RU_ONLY = set("ыэъё")
_CYRILLIC = re.compile(r"[а-яёіїєґ]", re.IGNORECASE)


def detect_language(text: str, default: str = DEFAULT_LANG) -> str:
    """Легке визначення мови з тексту (без зовнішніх залежностей).

    Надійно розрізняє кирилицю (uk/ru) проти латиниці. Для латиниці назва
    міста надто коротка, щоб впевнено визначати мову, тож повертаємо default
    (його дає локаль Telegram або явний вибір користувача).
    Точне визначення з ГОЛОСУ зробить Whisper у голосовій хвилі.
    """
    low = (text or "").lower()
    if _CYRILLIC.search(low):
        if _UK_ONLY & set(low):
            return "uk"
        if _RU_ONLY & set(low):
            return "ru"
        return default if default in ("uk", "ru") else "uk"
    return default


# Зворотний пошук: будь-яка локалізована мітка -> Enum-член (страховка
# на випадок, якщо мозок поверне категорію словом, а не англ. кодом).
def match_enum(enum_cls, text: str):
    """Знайти Enum-член за англ. кодом АБО за будь-якою локалізованою міткою."""
    if not text:
        return None
    needle = str(text).strip().lower()
    for member in enum_cls:
        if needle in (member.value.lower(), member.name.lower()):
            return member
    category = _ENUM_CATEGORY.get(enum_cls)
    if category:
        for tables in LABELS[category].values():
            for member, lbl in tables.items():
                if needle == lbl.lower():
                    return member
    return None


_ENUM_CATEGORY = {
    Interest: "interest",
    Budget: "budget",
    PlaceKind: "kind",
    TimeOfDay: "time",
}