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
        "es": {
            Interest.CULTURE: "Cultura",
            Interest.FOOD: "Comida",
            Interest.NATURE: "Naturaleza",
            Interest.NIGHTLIFE: "Vida nocturna",
            Interest.SHOPPING: "Compras",
            Interest.RELAX: "Relax",
        },
        "de": {
            Interest.CULTURE: "Kultur",
            Interest.FOOD: "Essen",
            Interest.NATURE: "Natur",
            Interest.NIGHTLIFE: "Nachtleben",
            Interest.SHOPPING: "Shopping",
            Interest.RELAX: "Erholung",
        },
        "fr": {
            Interest.CULTURE: "Culture",
            Interest.FOOD: "Gastronomie",
            Interest.NATURE: "Nature",
            Interest.NIGHTLIFE: "Vie nocturne",
            Interest.SHOPPING: "Shopping",
            Interest.RELAX: "Détente",
        },
        "it": {
            Interest.CULTURE: "Cultura",
            Interest.FOOD: "Cibo",
            Interest.NATURE: "Natura",
            Interest.NIGHTLIFE: "Vita notturna",
            Interest.SHOPPING: "Shopping",
            Interest.RELAX: "Relax",
        },
        "pl": {
            Interest.CULTURE: "Kultura",
            Interest.FOOD: "Jedzenie",
            Interest.NATURE: "Natura",
            Interest.NIGHTLIFE: "Życie nocne",
            Interest.SHOPPING: "Zakupy",
            Interest.RELAX: "Relaks",
        },
        "ru": {
            Interest.CULTURE: "Культура",
            Interest.FOOD: "Еда",
            Interest.NATURE: "Природа",
            Interest.NIGHTLIFE: "Развлечения",
            Interest.SHOPPING: "Шопинг",
            Interest.RELAX: "Отдых",
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
        "es": {
            Budget.LOW: "Económico",
            Budget.MEDIUM: "Medio",
            Budget.HIGH: "Premium",
        },
        "de": {
            Budget.LOW: "Günstig",
            Budget.MEDIUM: "Mittel",
            Budget.HIGH: "Premium",
        },
        "fr": {
            Budget.LOW: "Économique",
            Budget.MEDIUM: "Moyen",
            Budget.HIGH: "Premium",
        },
        "it": {
            Budget.LOW: "Economico",
            Budget.MEDIUM: "Medio",
            Budget.HIGH: "Premium",
        },
        "pl": {
            Budget.LOW: "Ekonomiczny",
            Budget.MEDIUM: "Średni",
            Budget.HIGH: "Premium",
        },
        "ru": {
            Budget.LOW: "Эконом",
            Budget.MEDIUM: "Средний",
            Budget.HIGH: "Премиум",
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
        "es": {
            PlaceKind.ATTRACTION: "atracción",
            PlaceKind.MUSEUM: "museo",
            PlaceKind.RESTAURANT: "restaurante",
            PlaceKind.CAFE: "café",
            PlaceKind.PARK: "parque",
            PlaceKind.VIEWPOINT: "mirador",
            PlaceKind.OTHER: "lugar",
        },
        "de": {
            PlaceKind.ATTRACTION: "Sehenswürdigkeit",
            PlaceKind.MUSEUM: "Museum",
            PlaceKind.RESTAURANT: "Restaurant",
            PlaceKind.CAFE: "Café",
            PlaceKind.PARK: "Park",
            PlaceKind.VIEWPOINT: "Aussichtspunkt",
            PlaceKind.OTHER: "Ort",
        },
        "fr": {
            PlaceKind.ATTRACTION: "attraction",
            PlaceKind.MUSEUM: "musée",
            PlaceKind.RESTAURANT: "restaurant",
            PlaceKind.CAFE: "café",
            PlaceKind.PARK: "parc",
            PlaceKind.VIEWPOINT: "point de vue",
            PlaceKind.OTHER: "lieu",
        },
        "it": {
            PlaceKind.ATTRACTION: "attrazione",
            PlaceKind.MUSEUM: "museo",
            PlaceKind.RESTAURANT: "ristorante",
            PlaceKind.CAFE: "caffè",
            PlaceKind.PARK: "parco",
            PlaceKind.VIEWPOINT: "punto panoramico",
            PlaceKind.OTHER: "luogo",
        },
        "pl": {
            PlaceKind.ATTRACTION: "atrakcja",
            PlaceKind.MUSEUM: "muzeum",
            PlaceKind.RESTAURANT: "restauracja",
            PlaceKind.CAFE: "kawiarnia",
            PlaceKind.PARK: "park",
            PlaceKind.VIEWPOINT: "punkt widokowy",
            PlaceKind.OTHER: "miejsce",
        },
        "ru": {
            PlaceKind.ATTRACTION: "достопримечательность",
            PlaceKind.MUSEUM: "музей",
            PlaceKind.RESTAURANT: "ресторан",
            PlaceKind.CAFE: "кафе",
            PlaceKind.PARK: "парк",
            PlaceKind.VIEWPOINT: "смотровая площадка",
            PlaceKind.OTHER: "место",
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
        "es": {
            TimeOfDay.BREAKFAST: "desayuno",
            TimeOfDay.MORNING: "mañana",
            TimeOfDay.LUNCH: "almuerzo",
            TimeOfDay.NOON: "tarde",
            TimeOfDay.EVENING: "noche",
            TimeOfDay.DINNER: "cena",
        },
        "de": {
            TimeOfDay.BREAKFAST: "Frühstück",
            TimeOfDay.MORNING: "Vormittag",
            TimeOfDay.LUNCH: "Mittagessen",
            TimeOfDay.NOON: "Nachmittag",
            TimeOfDay.EVENING: "Abend",
            TimeOfDay.DINNER: "Abendessen",
        },
        "fr": {
            TimeOfDay.BREAKFAST: "petit-déjeuner",
            TimeOfDay.MORNING: "matin",
            TimeOfDay.LUNCH: "déjeuner",
            TimeOfDay.NOON: "après-midi",
            TimeOfDay.EVENING: "soir",
            TimeOfDay.DINNER: "dîner",
        },
        "it": {
            TimeOfDay.BREAKFAST: "colazione",
            TimeOfDay.MORNING: "mattina",
            TimeOfDay.LUNCH: "pranzo",
            TimeOfDay.NOON: "pomeriggio",
            TimeOfDay.EVENING: "sera",
            TimeOfDay.DINNER: "cena",
        },
        "pl": {
            TimeOfDay.BREAKFAST: "śniadanie",
            TimeOfDay.MORNING: "rano",
            TimeOfDay.LUNCH: "obiad",
            TimeOfDay.NOON: "popołudnie",
            TimeOfDay.EVENING: "wieczór",
            TimeOfDay.DINNER: "kolacja",
        },
        "ru": {
            TimeOfDay.BREAKFAST: "завтрак",
            TimeOfDay.MORNING: "утро",
            TimeOfDay.LUNCH: "обед",
            TimeOfDay.NOON: "день",
            TimeOfDay.EVENING: "вечер",
            TimeOfDay.DINNER: "ужин",
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
    "es": {
        "start": (
            "✈️ <b>¡Hola! Soy tu planificador de viajes.</b>\n\n"
            "Te prepararé un plan detallado día a día — con lugares, "
            "restaurantes, rutas y bonitas tarjetas.\n\n"
            "¡Empecemos! <b>¿A dónde te gustaría ir?</b>\n"
            "<i>Escribe una ciudad, p. ej.: Praga, Barcelona, Roma…</i>"
        ),
        "cancel": "Cancelado. Escribe /start para empezar de nuevo.",
        "city_too_short": "Mmm, escribe el nombre de la ciudad otra vez, por favor 🙂",
        "city_not_found": (
            "Mmm, no encuentro esa ciudad 🤔\n"
            "Revisa el nombre e inténtalo de nuevo — p. ej.: <b>Roma</b>, <b>Barcelona</b>."
        ),
        "city_ok": (
            "¡Buena elección — <b>{city}</b>! 🌍\n\n"
            "<b>¿Cuántos días</b> dura el viaje?\n"
            "<i>Escribe un número, p. ej.: 3</i>"
        ),
        "city_wrong_type": (
            "Por favor, escribe el nombre de la ciudad como <b>texto</b> 🙂\n"
            "<i>Todavía no entiendo los audios — solo escribe la ciudad, p. ej.: Roma.</i>"
        ),
        "days_invalid": "Escribe un número del 1 al 30, por favor 🙂",
        "ask_interests": "¡Genial! Ahora elige <b>qué te interesa</b> (puedes elegir varios):",
        "days_wrong_type": "Escribe el <b>número</b> de días como texto, por favor 🙂 (p. ej.: 3)",
        "ask_budget": "Y por último — <b>¿cuál es tu presupuesto</b>?",
        "building": (
            "🧭 Preparando tu plan para <b>{city}</b>, {days} día(s).\n"
            "Tardaré un minuto — armando la ruta, buscando lugares y dibujando las tarjetas…"
        ),
        "error": (
            "😔 Vaya, algo salió mal al crear el plan.\n"
            "Inténtalo de nuevo: /start"
        ),
        "done": (
            "¡Listo! 🎒 ¡Que tengas un viaje maravilloso!\n"
            "Guarda las tarjetas — también funcionan sin conexión.\n\n"
            "¿Quieres otra ruta? Escribe /start"
        ),
        "btn_done": "➡️ Listo",
        "choose_language": "🌍 Elige tu idioma / Choose your language:",
        "language_set": "¡Listo! Ahora hablaré contigo en español 🇪🇸",
        "card_day": "Día",
        "card_transport": "Transporte",
    },
    "de": {
        "start": (
            "✈️ <b>Hi! Ich bin dein Reiseplaner.</b>\n\n"
            "Ich erstelle dir einen detaillierten Tagesplan — mit Orten, "
            "Restaurants, Routen und schönen Karten.\n\n"
            "Los geht's! <b>Wohin möchtest du reisen?</b>\n"
            "<i>Tippe eine Stadt, z. B.: Prag, Barcelona, Rom…</i>"
        ),
        "cancel": "Abgebrochen. Tippe /start, um neu zu beginnen.",
        "city_too_short": "Hmm, bitte tippe den Städtenamen noch einmal 🙂",
        "city_not_found": (
            "Hmm, ich finde diese Stadt nicht 🤔\n"
            "Prüfe die Schreibweise und versuch es erneut — z. B.: <b>Rom</b>, <b>Barcelona</b>."
        ),
        "city_ok": (
            "Gute Wahl — <b>{city}</b>! 🌍\n\n"
            "<b>Wie viele Tage</b> dauert die Reise?\n"
            "<i>Tippe eine Zahl, z. B.: 3</i>"
        ),
        "city_wrong_type": (
            "Bitte tippe den Städtenamen als <b>Text</b> 🙂\n"
            "<i>Sprachnachrichten verstehe ich noch nicht — tippe einfach die Stadt, z. B.: Rom.</i>"
        ),
        "days_invalid": "Bitte tippe eine Zahl von 1 bis 30 🙂",
        "ask_interests": "Super! Wähle nun, <b>was dich interessiert</b> (mehrere möglich):",
        "days_wrong_type": "Bitte tippe die <b>Anzahl</b> der Tage als Text 🙂 (z. B.: 3)",
        "ask_budget": "Und zuletzt — <b>wie hoch ist dein Budget</b>?",
        "building": (
            "🧭 Ich erstelle deinen Plan für <b>{city}</b>, {days} Tag(e).\n"
            "Das dauert einen Moment — Route planen, Orte suchen und Karten zeichnen…"
        ),
        "error": (
            "😔 Ups, beim Erstellen des Plans ist etwas schiefgelaufen.\n"
            "Bitte versuch es erneut: /start"
        ),
        "done": (
            "Fertig! 🎒 Eine wunderbare Reise!\n"
            "Speichere die Karten — sie funktionieren auch offline.\n\n"
            "Noch eine Route? Tippe /start"
        ),
        "btn_done": "➡️ Fertig",
        "choose_language": "🌍 Wähle deine Sprache / Choose your language:",
        "language_set": "Fertig! Ich spreche jetzt Deutsch mit dir 🇩🇪",
        "card_day": "Tag",
        "card_transport": "Transport",
    },
    "fr": {
        "start": (
            "✈️ <b>Salut ! Je suis ton planificateur de voyage.</b>\n\n"
            "Je te prépare un plan détaillé jour par jour — avec des lieux, "
            "des restaurants, des itinéraires et de jolies cartes.\n\n"
            "C'est parti ! <b>Où aimerais-tu aller ?</b>\n"
            "<i>Écris une ville, p. ex. : Prague, Barcelone, Rome…</i>"
        ),
        "cancel": "Annulé. Tape /start pour recommencer.",
        "city_too_short": "Hmm, écris à nouveau le nom de la ville, s'il te plaît 🙂",
        "city_not_found": (
            "Hmm, je ne trouve pas cette ville 🤔\n"
            "Vérifie l'orthographe et réessaie — p. ex. : <b>Rome</b>, <b>Barcelone</b>."
        ),
        "city_ok": (
            "Excellent choix — <b>{city}</b> ! 🌍\n\n"
            "<b>Combien de jours</b> dure ce voyage ?\n"
            "<i>Écris un nombre, p. ex. : 3</i>"
        ),
        "city_wrong_type": (
            "Écris le nom de la ville en <b>texte</b>, s'il te plaît 🙂\n"
            "<i>Je ne comprends pas encore les messages vocaux — tape simplement la ville, p. ex. : Rome.</i>"
        ),
        "days_invalid": "Écris un nombre de 1 à 30, s'il te plaît 🙂",
        "ask_interests": "Super ! Choisis maintenant <b>ce qui t'intéresse</b> (plusieurs possibles) :",
        "days_wrong_type": "Écris le <b>nombre</b> de jours en texte, s'il te plaît 🙂 (p. ex. : 3)",
        "ask_budget": "Et pour finir — <b>quel est ton budget</b> ?",
        "building": (
            "🧭 Je prépare ton plan pour <b>{city}</b>, {days} jour(s).\n"
            "Ça prendra une minute — itinéraire, recherche des lieux et création des cartes…"
        ),
        "error": (
            "😔 Oups, une erreur est survenue lors de la création du plan.\n"
            "Réessaie : /start"
        ),
        "done": (
            "Terminé ! 🎒 Excellent voyage !\n"
            "Enregistre les cartes — elles fonctionnent aussi hors ligne.\n\n"
            "Un autre itinéraire ? Tape /start"
        ),
        "btn_done": "➡️ Terminé",
        "choose_language": "🌍 Choisis ta langue / Choose your language:",
        "language_set": "Terminé ! Je te parle maintenant en français 🇫🇷",
        "card_day": "Jour",
        "card_transport": "Transport",
    },
    "it": {
        "start": (
            "✈️ <b>Ciao! Sono il tuo travel planner.</b>\n\n"
            "Ti preparo un piano dettagliato giorno per giorno — con luoghi, "
            "ristoranti, itinerari e belle card.\n\n"
            "Iniziamo! <b>Dove vorresti andare?</b>\n"
            "<i>Scrivi una città, es.: Praga, Barcellona, Roma…</i>"
        ),
        "cancel": "Annullato. Scrivi /start per ricominciare.",
        "city_too_short": "Mmm, scrivi di nuovo il nome della città, per favore 🙂",
        "city_not_found": (
            "Mmm, non trovo questa città 🤔\n"
            "Controlla il nome e riprova — es.: <b>Roma</b>, <b>Barcellona</b>."
        ),
        "city_ok": (
            "Ottima scelta — <b>{city}</b>! 🌍\n\n"
            "<b>Quanti giorni</b> dura il viaggio?\n"
            "<i>Scrivi un numero, es.: 3</i>"
        ),
        "city_wrong_type": (
            "Scrivi il nome della città come <b>testo</b>, per favore 🙂\n"
            "<i>Non capisco ancora i messaggi vocali — scrivi solo la città, es.: Roma.</i>"
        ),
        "days_invalid": "Scrivi un numero da 1 a 30, per favore 🙂",
        "ask_interests": "Perfetto! Ora scegli <b>cosa ti interessa</b> (puoi sceglierne più di uno):",
        "days_wrong_type": "Scrivi il <b>numero</b> di giorni come testo, per favore 🙂 (es.: 3)",
        "ask_budget": "E per ultimo — <b>qual è il tuo budget</b>?",
        "building": (
            "🧭 Sto preparando il tuo piano per <b>{city}</b>, {days} giorno/i.\n"
            "Ci vorrà un minuto — itinerario, ricerca dei luoghi e creazione delle card…"
        ),
        "error": (
            "😔 Ops, qualcosa è andato storto durante la creazione del piano.\n"
            "Riprova: /start"
        ),
        "done": (
            "Fatto! 🎒 Buon viaggio!\n"
            "Salva le card — funzionano anche offline.\n\n"
            "Vuoi un altro itinerario? Scrivi /start"
        ),
        "btn_done": "➡️ Fatto",
        "choose_language": "🌍 Scegli la tua lingua / Choose your language:",
        "language_set": "Fatto! Ora ti parlo in italiano 🇮🇹",
        "card_day": "Giorno",
        "card_transport": "Trasporti",
    },
    "pl": {
        "start": (
            "✈️ <b>Cześć! Jestem twoim planerem podróży.</b>\n\n"
            "Przygotuję ci szczegółowy plan dzień po dniu — z miejscami, "
            "restauracjami, trasami i ładnymi kartami.\n\n"
            "Zaczynamy! <b>Dokąd chcesz pojechać?</b>\n"
            "<i>Wpisz miasto, np.: Praga, Barcelona, Rzym…</i>"
        ),
        "cancel": "Anulowano. Wpisz /start, aby zacząć od nowa.",
        "city_too_short": "Hmm, wpisz jeszcze raz nazwę miasta 🙂",
        "city_not_found": (
            "Hmm, nie mogę znaleźć takiego miasta 🤔\n"
            "Sprawdź pisownię i spróbuj ponownie — np.: <b>Rzym</b>, <b>Barcelona</b>."
        ),
        "city_ok": (
            "Świetny wybór — <b>{city}</b>! 🌍\n\n"
            "<b>Ile dni</b> potrwa ta podróż?\n"
            "<i>Wpisz liczbę, np.: 3</i>"
        ),
        "city_wrong_type": (
            "Wpisz nazwę miasta jako <b>tekst</b> 🙂\n"
            "<i>Nie rozumiem jeszcze wiadomości głosowych — po prostu wpisz miasto, np.: Rzym.</i>"
        ),
        "days_invalid": "Wpisz liczbę od 1 do 30 🙂",
        "ask_interests": "Super! Teraz wybierz, <b>co cię interesuje</b> (możesz kilka):",
        "days_wrong_type": "Wpisz <b>liczbę</b> dni jako tekst 🙂 (np.: 3)",
        "ask_budget": "I na koniec — <b>jaki masz budżet</b>?",
        "building": (
            "🧭 Przygotowuję twój plan dla <b>{city}</b>, {days} dzień/dni.\n"
            "To zajmie chwilę — układam trasę, szukam miejsc i rysuję karty…"
        ),
        "error": (
            "😔 Ups, coś poszło nie tak podczas tworzenia planu.\n"
            "Spróbuj ponownie: /start"
        ),
        "done": (
            "Gotowe! 🎒 Udanej podróży!\n"
            "Zapisz karty — działają też offline.\n\n"
            "Chcesz kolejną trasę? Wpisz /start"
        ),
        "btn_done": "➡️ Gotowe",
        "choose_language": "🌍 Wybierz język / Choose your language:",
        "language_set": "Gotowe! Teraz rozmawiam z tobą po polsku 🇵🇱",
        "card_day": "Dzień",
        "card_transport": "Transport",
    },
    "ru": {
        "start": (
            "✈️ <b>Привет! Я твой тревел-планер.</b>\n\n"
            "Составлю тебе подробный план путешествия по дням — с местами, "
            "ресторанами, маршрутами и красивыми карточками.\n\n"
            "Начнём! <b>Куда планируешь поехать?</b>\n"
            "<i>Напиши город, напр.: Прага, Барселона, Рим…</i>"
        ),
        "cancel": "Отменено. Напиши /start, чтобы начать заново.",
        "city_too_short": "Хм, напиши, пожалуйста, название города ещё раз 🙂",
        "city_not_found": (
            "Хм, не могу найти такой город 🤔\n"
            "Проверь название и напиши ещё раз — напр.: <b>Рим</b>, <b>Барселона</b>."
        ),
        "city_ok": (
            "Отличный выбор — <b>{city}</b>! 🌍\n\n"
            "<b>На сколько дней</b> это путешествие?\n"
            "<i>Напиши число, напр.: 3</i>"
        ),
        "city_wrong_type": (
            "Напиши, пожалуйста, название города <b>текстом</b> 🙂\n"
            "<i>Голосовые я пока не понимаю — просто напечатай город, напр.: Рим.</i>"
        ),
        "days_invalid": "Напиши число от 1 до 30, пожалуйста 🙂",
        "ask_interests": "Супер! Теперь выбери, <b>что тебе интересно</b> (можно несколько):",
        "days_wrong_type": "Напиши, пожалуйста, <b>число</b> дней текстом 🙂 (напр.: 3)",
        "ask_budget": "И последнее — <b>какой бюджет</b>?",
        "building": (
            "🧭 Готовлю твой план по <b>{city}</b> на {days} дн.\n"
            "Это займёт минуту — составляю маршрут, ищу места и рисую карточки…"
        ),
        "error": (
            "😔 Ой, что-то пошло не так при построении плана.\n"
            "Попробуй ещё раз: /start"
        ),
        "done": (
            "Готово! 🎒 Хорошего путешествия!\n"
            "Сохрани карточки — они работают и офлайн.\n\n"
            "Хочешь ещё один маршрут? Напиши /start"
        ),
        "btn_done": "➡️ Готово",
        "choose_language": "🌍 Выбери язык / Choose your language:",
        "language_set": "Готово! Теперь общаюсь с тобой на русском 🇷🇺",
        "card_day": "День",
        "card_transport": "Транспорт",
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