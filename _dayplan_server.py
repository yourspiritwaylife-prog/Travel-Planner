#!/usr/bin/env python3
"""
dayplan.py — побудувати ІНТЕРАКТИВНУ сторінку плану дня і надіслати в Telegram.

Працює БЕЗ браузера (легко для маленького сервера): тягне з Google Places реальні
фото (вшиває їх у файл як base64), рейтинги, години, ціни; будує HTML без JS
(тап на картку -> розгортається з деталями); надсилає документом у чат і ВИДАЛЯЄ
тимчасовий файл (нічого не зберігається).

Виклик:
  python3 dayplan.py --data /tmp/day.json [--chat <id>] [--caption "..."]

JSON одного дня:
{
  "city": "Рим", "day_label": "День 1 / 3",
  "day_title": "Давній Рим", "summary": "...",
  "foot": "Транспорт: пішки",
  "stops": [
    {"time":"Сніданок","name":"Caffè Oppio","query":"Caffe Oppio, Rome",
     "desc":"...","dish":"Карбонара","why":"...","travel":"метро 5 хв"}, ...
  ]
}
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import os
import subprocess
import urllib.parse
import urllib.request


def _env(keys):
    vals = {k: os.environ.get(k, "").strip() for k in keys}
    missing = [k for k in keys if not vals[k]]
    if missing:
        here = os.path.dirname(os.path.abspath(__file__))
        for up in ("../../../../.env", "../../../.env", "../../.env"):
            p = os.path.abspath(os.path.join(here, up))
            if not os.path.exists(p):
                continue
            try:
                with open(p, encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        for k in missing:
                            if line.startswith(k + "="):
                                vals[k] = line.split("=", 1)[1].strip().strip('"').strip("'")
            except OSError:
                pass
            break
    return vals


ENV = _env(["GOOGLE_PLACES_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_HOME_CHANNEL"])
KEY = ENV["GOOGLE_PLACES_API_KEY"]
PRICE = {"PRICE_LEVEL_INEXPENSIVE": "€", "PRICE_LEVEL_MODERATE": "€€",
         "PRICE_LEVEL_EXPENSIVE": "€€€", "PRICE_LEVEL_VERY_EXPENSIVE": "€€€€"}

# --- Локалізація ОБГОРТКИ сторінки (сталі підписи) ---------------------------
# Контент дня (назви, описи, час доби, day_label) дає сам агент МОВОЮ
# користувача; тут лише фіксовані підписи. Мова береться з day JSON: "lang".
# Невідома мова -> англійська; немає поля зовсім -> українська (сумісність).
L10N = {
    "uk": {
        "rating_tbd": "рейтинг уточнюється", "open": "Працює",
        "order": "Що замовити", "why": "Чому варто", "alt": "Альтернатива",
        "travel": "Як дістатись", "ticket": "Тур / квиток", "book": "забронювати →",
        "book_ahead": "Бронюй заздалегідь — місця/квитки часто розкуповують наперед",
        "site": "Офіційний сайт", "tap": "↓ натисни для деталей",
        "tap_short": "натисни ↓", "daytrips": "💡 Альтернативні варіанти",
        "daytrip_link": "Детальніше / забронювати →",
        "alert": "⚠️ У ЦЕЙ ДЕНЬ є що бронювати ЗАЗДАЛЕГІДЬ — шукай позначки 🎟 нижче",
        "around": "🚕 Пересування сьогодні", "culture": "🛕 Культура й традиції",
        "tips": "💡 Корисно знати", "foot_default": "Гарної подорожі! 🎒",
        "badge_ahead": "🎟 заздалегідь", "trip": "Подорож", "plan": "План",
        "pace_relaxed": "спокійний темп", "pace_balanced": "помірний темп",
        "pace_packed": "насичений темп", "budget": "💶 Бюджет дня",
        "weather": "🌦 Якщо дощ, спека чи втома",
    },
    "en": {
        "rating_tbd": "rating to be confirmed", "open": "Open",
        "order": "What to order", "why": "Why go", "alt": "Alternative",
        "travel": "How to get there", "ticket": "Tour / ticket", "book": "book →",
        "book_ahead": "Book ahead — spots/tickets often sell out in advance",
        "site": "Official site", "tap": "↓ tap for details",
        "tap_short": "tap ↓", "daytrips": "💡 Alternative options",
        "daytrip_link": "Details / book →",
        "alert": "⚠️ THIS DAY has things to book IN ADVANCE — look for the 🎟 marks below",
        "around": "🚕 Getting around today", "culture": "🛕 Culture & traditions",
        "tips": "💡 Good to know", "foot_default": "Have a wonderful trip! 🎒",
        "badge_ahead": "🎟 in advance", "trip": "Trip", "plan": "Plan",
        "pace_relaxed": "relaxed pace", "pace_balanced": "balanced pace",
        "pace_packed": "packed day", "budget": "💶 Day budget",
        "weather": "🌦 If it rains, gets hot, or you're tired",
    },
    "es": {
        "rating_tbd": "valoración por confirmar", "open": "Horario",
        "order": "Qué pedir", "why": "Por qué ir", "alt": "Alternativa",
        "travel": "Cómo llegar", "ticket": "Tour / entrada", "book": "reservar →",
        "book_ahead": "Reserva con antelación — las plazas/entradas suelen agotarse",
        "site": "Sitio oficial", "tap": "↓ toca para más detalles",
        "tap_short": "toca ↓", "daytrips": "💡 Opciones alternativas",
        "daytrip_link": "Más info / reservar →",
        "alert": "⚠️ ESTE DÍA hay cosas que reservar CON ANTELACIÓN — busca las marcas 🎟 abajo",
        "around": "🚕 Cómo moverse hoy", "culture": "🛕 Cultura y tradiciones",
        "tips": "💡 Bueno saber", "foot_default": "¡Buen viaje! 🎒",
        "badge_ahead": "🎟 con antelación", "trip": "Viaje", "plan": "Plan",
        "pace_relaxed": "ritmo relajado", "pace_balanced": "ritmo equilibrado",
        "pace_packed": "día intenso", "budget": "💶 Presupuesto del día",
        "weather": "🌦 Si llueve, hace calor o estás cansado",
    },
    "de": {
        "rating_tbd": "Bewertung folgt", "open": "Öffnungszeiten",
        "order": "Was bestellen", "why": "Warum hin", "alt": "Alternative",
        "travel": "Anfahrt", "ticket": "Tour / Ticket", "book": "buchen →",
        "book_ahead": "Frühzeitig buchen — Plätze/Tickets sind oft im Voraus ausverkauft",
        "site": "Offizielle Website", "tap": "↓ für Details tippen",
        "tap_short": "tippen ↓", "daytrips": "💡 Alternative Optionen",
        "daytrip_link": "Mehr / buchen →",
        "alert": "⚠️ AN DIESEM TAG gibt es Dinge, die man IM VORAUS buchen sollte — achte auf die 🎟 unten",
        "around": "🚕 Heute unterwegs", "culture": "🛕 Kultur & Traditionen",
        "tips": "💡 Gut zu wissen", "foot_default": "Gute Reise! 🎒",
        "badge_ahead": "🎟 im Voraus", "trip": "Reise", "plan": "Plan",
        "pace_relaxed": "entspanntes Tempo", "pace_balanced": "ausgewogenes Tempo",
        "pace_packed": "voller Tag", "budget": "💶 Tagesbudget",
        "weather": "🌦 Bei Regen, Hitze oder Müdigkeit",
    },
    "fr": {
        "rating_tbd": "note à confirmer", "open": "Horaires",
        "order": "Que commander", "why": "Pourquoi y aller", "alt": "Alternative",
        "travel": "Comment s'y rendre", "ticket": "Visite / billet", "book": "réserver →",
        "book_ahead": "Réservez à l'avance — les places/billets partent souvent vite",
        "site": "Site officiel", "tap": "↓ appuyez pour les détails",
        "tap_short": "appuyez ↓", "daytrips": "💡 Autres options",
        "daytrip_link": "En savoir plus / réserver →",
        "alert": "⚠️ CE JOUR-LÀ, il y a des choses à réserver À L'AVANCE — repérez les 🎟 ci-dessous",
        "around": "🚕 Se déplacer aujourd'hui", "culture": "🛕 Culture & traditions",
        "tips": "💡 Bon à savoir", "foot_default": "Bon voyage ! 🎒",
        "badge_ahead": "🎟 à l'avance", "trip": "Voyage", "plan": "Plan",
        "pace_relaxed": "rythme tranquille", "pace_balanced": "rythme équilibré",
        "pace_packed": "journée chargée", "budget": "💶 Budget du jour",
        "weather": "🌦 S'il pleut, fait chaud ou en cas de fatigue",
    },
    "it": {
        "rating_tbd": "valutazione da confermare", "open": "Orari",
        "order": "Cosa ordinare", "why": "Perché andarci", "alt": "Alternativa",
        "travel": "Come arrivare", "ticket": "Tour / biglietto", "book": "prenota →",
        "book_ahead": "Prenota in anticipo — posti/biglietti spesso si esauriscono",
        "site": "Sito ufficiale", "tap": "↓ tocca per i dettagli",
        "tap_short": "tocca ↓", "daytrips": "💡 Opzioni alternative",
        "daytrip_link": "Dettagli / prenota →",
        "alert": "⚠️ OGGI ci sono cose da prenotare IN ANTICIPO — cerca i segni 🎟 qui sotto",
        "around": "🚕 Spostarsi oggi", "culture": "🛕 Cultura e tradizioni",
        "tips": "💡 Buono a sapersi", "foot_default": "Buon viaggio! 🎒",
        "badge_ahead": "🎟 in anticipo", "trip": "Viaggio", "plan": "Piano",
        "pace_relaxed": "ritmo rilassato", "pace_balanced": "ritmo equilibrato",
        "pace_packed": "giornata intensa", "budget": "💶 Budget del giorno",
        "weather": "🌦 Se piove, fa caldo o sei stanco",
    },
    "pl": {
        "rating_tbd": "ocena do potwierdzenia", "open": "Godziny",
        "order": "Co zamówić", "why": "Dlaczego warto", "alt": "Alternatywa",
        "travel": "Jak dojechać", "ticket": "Wycieczka / bilet", "book": "rezerwuj →",
        "book_ahead": "Rezerwuj z wyprzedzeniem — miejsca/bilety często szybko się kończą",
        "site": "Oficjalna strona", "tap": "↓ dotknij, aby zobaczyć szczegóły",
        "tap_short": "dotknij ↓", "daytrips": "💡 Alternatywne opcje",
        "daytrip_link": "Więcej / rezerwuj →",
        "alert": "⚠️ TEGO DNIA są rzeczy do rezerwacji Z WYPRZEDZENIEM — szukaj znaków 🎟 poniżej",
        "around": "🚕 Poruszanie się dziś", "culture": "🛕 Kultura i tradycje",
        "tips": "💡 Warto wiedzieć", "foot_default": "Udanej podróży! 🎒",
        "badge_ahead": "🎟 z wyprzedzeniem", "trip": "Podróż", "plan": "Plan",
        "pace_relaxed": "spokojne tempo", "pace_balanced": "zrównoważone tempo",
        "pace_packed": "intensywny dzień", "budget": "💶 Budżet dnia",
        "weather": "🌦 Gdy deszcz, upał lub zmęczenie",
    },
    "ru": {
        "rating_tbd": "рейтинг уточняется", "open": "Часы работы",
        "order": "Что заказать", "why": "Почему стоит", "alt": "Альтернатива",
        "travel": "Как добраться", "ticket": "Тур / билет", "book": "забронировать →",
        "book_ahead": "Бронируй заранее — места/билеты часто разбирают наперёд",
        "site": "Официальный сайт", "tap": "↓ нажми для деталей",
        "tap_short": "нажми ↓", "daytrips": "💡 Альтернативные варианты",
        "daytrip_link": "Подробнее / забронировать →",
        "alert": "⚠️ В ЭТОТ ДЕНЬ есть что бронировать ЗАРАНЕЕ — ищи метки 🎟 ниже",
        "around": "🚕 Передвижение сегодня", "culture": "🛕 Культура и традиции",
        "tips": "💡 Полезно знать", "foot_default": "Хорошего путешествия! 🎒",
        "badge_ahead": "🎟 заранее", "trip": "Поездка", "plan": "План",
        "pace_relaxed": "спокойный темп", "pace_balanced": "умеренный темп",
        "pace_packed": "насыщенный день", "budget": "💶 Бюджет дня",
        "weather": "🌦 Если дождь, жара или усталость",
    },
}


def L(lang):
    """Підписи обгортки потрібною мовою (uk -> сумісність, інакше -> en)."""
    return L10N.get(lang) or L10N["en"]


def esc(s):
    return html.escape(str(s or ""))


def num(n):
    return f"{n:,}".replace(",", " ") if n else "0"


def safe_url(u, allow_data=False):
    """Лише http(s) (і data:image для фото) — щоб у href/src не пролізли
    схеми типу javascript:. Інакше повертаємо порожній рядок."""
    u = str(u or "").strip()
    low = u.lower()
    if low.startswith(("https://", "http://")):
        return u
    if allow_data and low.startswith("data:image/"):
        return u
    return ""


def fetch(query, lang="uk"):
    if not KEY:
        return {}
    body = {"textQuery": query, "languageCode": lang or "uk", "pageSize": 1}
    req = urllib.request.Request(
        "https://places.googleapis.com/v1/places:searchText",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "X-Goog-Api-Key": KEY,
                 "X-Goog-FieldMask": ("places.rating,places.userRatingCount,"
                 "places.priceLevel,places.currentOpeningHours.weekdayDescriptions,"
                 "places.photos,places.formattedAddress,places.websiteUri,places.addressComponents")},
        method="POST")
    try:
        p = (json.loads(urllib.request.urlopen(req, timeout=25).read().decode())
             .get("places") or [{}])[0]
    except Exception:  # noqa: BLE001
        p = {}
    photos = p.get("photos") or []
    purl = (f"https://places.googleapis.com/v1/{photos[0]['name']}/media"
            f"?maxWidthPx=520&maxHeightPx=420&key={KEY}") if photos else ""
    hrs = (p.get("currentOpeningHours") or {}).get("weekdayDescriptions") or []
    cc = ""
    loc = ""
    for _comp in (p.get("addressComponents") or []):
        _types = _comp.get("types") or []
        if "country" in _types:
            cc = (_comp.get("shortText") or "").upper()
        if not loc and ("locality" in _types or "postal_town" in _types):
            loc = _comp.get("longText") or _comp.get("shortText") or ""
    return {"rating": p.get("rating"), "reviews": p.get("userRatingCount"),
            "price": PRICE.get(p.get("priceLevel"), ""),
            "hours": (hrs[0].split(": ", 1)[-1] if hrs else ""),
            "addr": p.get("formattedAddress", ""), "cc": cc, "loc": loc,
            "website": p.get("websiteUri", ""), "purl": purl}


def photo_data(url):
    if not url:
        return ""
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            ct = r.headers.get("Content-Type", "image/jpeg").split(";")[0]
            raw = r.read()
        return f"data:{ct};base64," + base64.b64encode(raw).decode()
    except Exception:  # noqa: BLE001
        return ""


CSS = """*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
body{font-family:-apple-system,'Segoe UI',system-ui,Arial,sans-serif;background:#f1ecff;color:#232838;padding-bottom:26px}
.hero{background:linear-gradient(135deg,#ff7a59,#fc5c8d 45%,#7c5cff);color:#fff;padding:24px 20px 20px;border-radius:0 0 26px 26px}
.hero .city{letter-spacing:5px;font-size:13px;opacity:.9;text-transform:uppercase}
.hero .day{font-size:34px;font-weight:800;line-height:1.05;margin-top:6px}
.hero .ttl{font-size:20px;font-weight:700;margin-top:11px}
.hero .sum{font-size:14px;opacity:.95;margin-top:6px;line-height:1.4}
.hero .pace{display:inline-block;font-size:11px;font-weight:800;letter-spacing:.6px;text-transform:uppercase;background:rgba(255,255,255,.22);padding:4px 12px;border-radius:999px;margin-top:11px}
.info.bud h3{color:#2a7d4f}
.info.wx h3{color:#4b8fd8}
.list{padding:15px}
.stop{background:#fff;border-radius:18px;box-shadow:0 6px 16px rgba(80,60,160,.12);overflow:hidden;margin-bottom:13px}
.stop>summary{list-style:none;display:flex;cursor:pointer;align-items:stretch}
.stop>summary::-webkit-details-marker{display:none}
.th{width:110px;min-width:110px;height:116px;object-fit:cover;background:#e7e2f5}
.in{padding:11px 13px;flex:1;min-width:0}
.when{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.4px;text-transform:uppercase;color:#7c5cff;background:rgba(124,92,255,.12);padding:3px 10px;border-radius:999px}
.nm{font-size:17px;font-weight:700;margin-top:6px;line-height:1.2}
.mt{font-size:13px;color:#888;margin-top:5px}
.star{color:#f5a623;font-weight:700}
.tap{font-size:12px;color:#fc5c8d;margin-top:7px;font-weight:700}
.stop[open] .tap{color:#aaa}
.more{padding:2px 16px 18px;border-top:1px solid #f0ecf8}
.more .r{margin-top:12px;font-size:15px;line-height:1.5}
.more .r b{color:#7c5cff}
.chip{display:inline-block;background:#fff0f5;color:#fc5c8d;font-weight:700;font-size:14px;padding:6px 13px;border-radius:10px;margin-top:7px}
.more .addr{color:#9a93a8;font-size:13px;margin-top:12px}
.more .site{margin-top:12px;font-size:14px}
.more .site a{color:#7c5cff;font-weight:700;text-decoration:none}
.more .bk{margin-top:12px;background:#f3f0ff;border-radius:10px;padding:10px 12px;font-size:14px;line-height:1.5}
.more .bk a{color:#7c5cff;font-weight:700;text-decoration:none}
.more .alt{margin-top:12px;background:#eef6ff;border-radius:10px;padding:9px 12px;font-size:14px;line-height:1.5;color:#2a6da7}
.more .alt b{color:#2a6da7}
.more .entry{margin-top:11px}
.entrychip{display:inline-block;background:#eef7f0;color:#2a7d4f;font-weight:700;font-size:13px;padding:5px 11px;border-radius:9px}
.more .ahead{margin-top:9px;color:#d12b2b;font-weight:800;font-size:14px;background:#ffe8e8;border-radius:9px;padding:8px 11px}
.alert{margin:13px 15px 0;background:#ffe8e8;color:#d12b2b;border:1.6px solid #ff9b9b;border-radius:13px;padding:12px 14px;font-weight:800;font-size:14px;line-height:1.4;animation:pulse 1.6s ease-in-out infinite}
.taxi{margin:13px 15px 0;background:#fff;border-radius:16px;padding:12px 15px;box-shadow:0 5px 14px rgba(80,60,160,.10);font-size:14px;line-height:1.5;color:#3a3f4b;font-weight:600}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
.badge-book{display:inline-block;background:#ffe1e1;color:#d12b2b;font-size:11px;font-weight:800;padding:3px 9px;border-radius:999px;margin-left:6px;border:1px solid #ffb3b3;vertical-align:middle}
.dur{font-size:11px;color:#9a93a8;margin-left:8px;font-weight:600}
.info{margin:13px 15px 0;background:#fff;border-radius:16px;box-shadow:0 5px 14px rgba(80,60,160,.10);overflow:hidden}
.info>summary{list-style:none;display:flex;align-items:center;justify-content:space-between;cursor:pointer;padding:14px 15px}
.info>summary::-webkit-details-marker{display:none}
.info h3{font-size:14px;font-weight:800;color:#7c5cff}
.info.cult h3{color:#e0683f}
.info.tips h3{color:#2aa775}
.info .arr{color:#c3bdd4;font-size:13px;font-weight:700;margin-left:10px}
.info[open] .arr{color:#7c5cff}
.info .ibody{padding:0 15px 14px}
.info .li{font-size:14px;line-height:1.5;color:#3a3f4b;padding-left:18px;position:relative;margin-top:6px}
.info .li::before{content:"•";position:absolute;left:4px;color:#fc5c8d;font-weight:700}
.trip{margin:13px 15px 0;background:#fff;border-radius:16px;padding:13px 15px;box-shadow:0 5px 14px rgba(80,60,160,.10)}
.trip h3{font-size:14px;font-weight:800;color:#4bb6d8;margin-bottom:9px}
.trip .t{padding:9px 0;border-top:1px solid #f0ecf8}
.trip .t:first-of-type{border-top:none}
.trip .t .tn{font-size:15px;font-weight:700}
.trip .t .td{font-size:13px;color:#515767;line-height:1.45;margin-top:3px}
.trip .t a{display:inline-block;margin-top:6px;color:#7c5cff;font-weight:700;font-size:13px;text-decoration:none}
.foot{margin:14px 20px 0;font-size:13px;color:#7a7488;text-align:center}"""


def _dur_minutes(dur):
    """Тривалість у хвилинах із тексту («1 год 30 хв», «1 hr 30 min», …). 0 якщо не вдалось."""
    import re
    t = (dur or "").lower()
    hh = re.search(r"(\d+)\s*(?:год|годин|hours?|hrs?|h\b|heures?|ore|ora|stunden?|std|godz|saat|час|ч\b)", t)
    mm = re.search(r"(\d+)\s*(?:хвил\w*|хв|min\w*|мин\w*)", t)
    return (int(hh.group(1)) * 60 if hh else 0) + (int(mm.group(1)) if mm else 0)


def _end_time(start, dur):
    """Кінець = старт + тривалість (для діапазону «09:00–11:30»). '' якщо не вдалось."""
    import re
    m = re.match(r"\s*(\d{1,2}):(\d{2})", start or "")
    if not m:
        return ""
    add = _dur_minutes(dur)
    if add <= 0:
        return ""
    end = (int(m.group(1)) * 60 + int(m.group(2)) + add) % (24 * 60)
    return "%02d:%02d" % (end // 60, end % 60)


def ensure_schedule(stops):
    """ГАРАНТІЯ ГОДИН: якщо модель не дала час — будуємо розумний послідовний графік
    (день із 09:00, тривалості за замовч. 1.5 год, +30 хв на дорогу). Реальні часи від моделі НЕ чіпаємо."""
    import re
    if not stops or all(s.get("start") for s in stops):
        return
    cur = 9 * 60
    for s in stops:
        m = re.match(r"\s*(\d{1,2}):(\d{2})", s.get("start") or "")
        if m:
            cur = int(m.group(1)) * 60 + int(m.group(2))
        else:
            s["start"] = "%02d:%02d" % (cur // 60, cur % 60)
        dur = _dur_minutes(s.get("duration")) or 90
        s["_end_auto"] = "%02d:%02d" % (((cur + dur) % (24 * 60)) // 60, ((cur + dur) % (24 * 60)) % 60)
        cur = (cur + dur + 30) % (24 * 60)


def stop_block(s, lang="uk"):
    t = L(lang)
    star = (f'<span class="star">★ {s["rating"]}</span> ({num(s["reviews"])})'
            if s.get("rating") else f'<span style="color:#aaa">{t["rating_tbd"]}</span>')
    price = f' · {s["price"]}' if s.get("price") else ""
    rows = ""
    if s.get("hours"):
        rows += f'<div class="r">🕐 <b>{t["open"]}:</b> {esc(s["hours"])}</div>'
    if s.get("desc"):
        rows += f'<div class="r">{esc(s["desc"])}</div>'
    if s.get("dish"):
        rows += f'<div class="r">🍽 <b>{t["order"]}:</b></div><span class="chip">{esc(s["dish"])}</span>'
    if s.get("why"):
        rows += f'<div class="r">✨ <b>{t["why"]}:</b> {esc(s["why"])}</div>'
    if s.get("entry"):
        rows += f'<div class="r entry"><span class="entrychip">{esc(s["entry"])}</span></div>'
    if s.get("alt"):
        rows += f'<div class="r alt">🏨 <b>{t["alt"]}:</b> {esc(s["alt"])}</div>'
    if s.get("travel"):
        rows += f'<div class="r">🚕 <b>{t["travel"]}:</b> {esc(s["travel"])}</div>'
    if s.get("booking"):
        b = s["booking"]
        lbl = esc(b.get("label") or t["ticket"])
        blink = safe_url(b.get("link"))
        link = (f' <a href="{esc(blink)}" target="_blank" rel="noopener">'
                f'{t["book"]}</a>') if blink else ""
        note = f'<br>{esc(b["note"])}' if b.get("note") else ""
        rows += f'<div class="r bk">🎟 <b>{lbl}:</b>{link}{note}</div>'
    if s.get("book_ahead"):
        rows += f'<div class="r ahead">⏳ {t["book_ahead"]}</div>'
    wsite = safe_url(s.get("website"))
    if wsite:
        rows += (f'<div class="r site">🔗 <a href="{esc(wsite)}" '
                 f'target="_blank" rel="noopener">{t["site"]}</a></div>')
    if s.get("addr"):
        rows += f'<div class="addr">📍 {esc(s["addr"])}</div>'
    # час: показуємо ДІАПАЗОН «старт–кінець» (кінець = старт + тривалість).
    # Без тривалості — лише старт; без старту — словесний час доби.
    _end = _end_time(s.get("start"), s.get("duration")) if s.get("start") else ""
    if not _end:
        _end = s.get("_end_auto", "")
    if s.get("start") and _end:
        when = f'{esc(s["start"])}–{esc(_end)}'
    elif s.get("start"):
        when = esc(s["start"])
    else:
        when = esc(s.get("time", ""))
    dur = f'<span class="dur">⏱ {esc(s["duration"])}</span>' if s.get("duration") else ""
    badge = f'<span class="badge-book">{t["badge_ahead"]}</span>' if s.get("book_ahead") else ""
    img = safe_url(s.get("photo"), allow_data=True)
    return (f'<details class="stop"><summary><img class="th" src="{esc(img)}">'
            f'<div class="in"><span class="when">{when}</span>{dur}{badge}'
            f'<div class="nm">{esc(s["name"])}</div><div class="mt">{star}{price}</div>'
            f'<div class="tap">{t["tap"]}</div></div></summary>'
            f'<div class="more">{rows}</div></details>')


def info_box(title, items, lang="uk", cls=""):
    """Згортний блок-список (транспорт / культура / поради): тап -> розгортається.
    items — рядок або список рядків."""
    if not items:
        return ""
    if isinstance(items, str):
        items = [items]
    lis = "".join(f'<div class="li">{esc(it)}</div>' for it in items if it)
    if not lis:
        return ""
    return (f'<details class="info {cls}"><summary><h3>{esc(title)}</h3>'
            f'<span class="arr">{L(lang)["tap_short"]}</span></summary>'
            f'<div class="ibody">{lis}</div></details>')


# --- Авто-визначення таксі-додатку за КРАЇНОЮ (надійно, не залежить від ШІ) ----
TAXI_BY_CC = {
    "IT": "FreeNow / itTaxi", "ES": "FreeNow / Cabify", "FR": "FreeNow / G7",
    "DE": "FreeNow / Bolt", "GB": "Uber / Bolt", "IE": "FreeNow / Uber",
    "PT": "Bolt / FreeNow", "NL": "Uber / Bolt", "BE": "Bolt / Uber",
    "AT": "Bolt / FreeNow", "CH": "Uber / Bolt", "PL": "Bolt / Uber",
    "CZ": "Bolt / Uber", "SK": "Bolt", "HU": "Bolt", "RO": "Bolt / Uber",
    "GR": "FreeNow / Beat", "HR": "Bolt / Uber", "BG": "Bolt",
    "EE": "Bolt", "LV": "Bolt", "LT": "Bolt", "UA": "Bolt / Uklon",
    "GE": "Bolt / Yandex Go", "TR": "BiTaksi / iTaksi",
    "AE": "Careem / Uber", "SA": "Careem / Uber", "QA": "Careem / Uber",
    "EG": "Uber / Careem", "MA": "Careem / inDrive", "ZA": "Uber / Bolt",
    "US": "Uber / Lyft", "CA": "Uber / Lyft", "MX": "Uber / DiDi",
    "BR": "Uber / 99", "AR": "Cabify / Uber", "CL": "Uber / Cabify",
    "CO": "Uber / DiDi", "PE": "Uber / DiDi",
    "ID": "Grab / Gojek", "TH": "Grab / Bolt", "SG": "Grab / Gojek",
    "MY": "Grab", "VN": "Grab / Be", "PH": "Grab", "IN": "Uber / Ola",
    "JP": "Uber / GO", "KR": "Kakao T", "HK": "Uber / HKTaxi",
    "TW": "Uber / LINE Taxi", "AU": "Uber / DiDi", "NZ": "Uber",
}
TAXI_TPL = {
    "uk": "\U0001f695 \u0422\u0430\u043a\u0441\u0456: \u0432\u0438\u043a\u043b\u0438\u0447 \u0447\u0435\u0440\u0435\u0437 \u0437\u0430\u0441\u0442\u043e\u0441\u0443\u043d\u043e\u043a {app} (\u044f\u043a Uber) \u2014 \u0446\u0456\u043d\u0443 \u0432\u0438\u0434\u043d\u043e \u043d\u0430\u043f\u0435\u0440\u0435\u0434, \u043e\u043f\u043b\u0430\u0442\u0430 \u043a\u0430\u0440\u0442\u043a\u043e\u044e, \u043e\u0444\u0456\u0446\u0456\u0439\u043d\u0456 \u043c\u0430\u0448\u0438\u043d\u0438.",
    "en": "\U0001f695 Taxi: use the {app} app (like Uber) \u2014 price shown upfront, pay by card, official cars.",
    "es": "\U0001f695 Taxi: usa la app {app} (como Uber) \u2014 precio por adelantado, pago con tarjeta, coches oficiales.",
    "de": "\U0001f695 Taxi: nutze die App {app} (wie Uber) \u2014 Preis vorab, Kartenzahlung, offizielle Autos.",
    "fr": "\U0001f695 Taxi : utilise l'app {app} (comme Uber) \u2014 prix \u00e0 l'avance, paiement par carte, voitures officielles.",
    "it": "\U0001f695 Taxi: usa l'app {app} (come Uber) \u2014 prezzo in anticipo, pagamento con carta, auto ufficiali.",
    "pl": "\U0001f695 Taxi: u\u017cyj aplikacji {app} (jak Uber) \u2014 cena z g\u00f3ry, p\u0142atno\u015b\u0107 kart\u0105, oficjalne auta.",
    "ru": "\U0001f695 \u0422\u0430\u043a\u0441\u0438: \u0432\u044b\u0437\u044b\u0432\u0430\u0439 \u0447\u0435\u0440\u0435\u0437 \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u0435 {app} (\u043a\u0430\u043a Uber) \u2014 \u0446\u0435\u043d\u0430 \u0432\u0438\u0434\u043d\u0430 \u0437\u0430\u0440\u0430\u043d\u0435\u0435, \u043e\u043f\u043b\u0430\u0442\u0430 \u043a\u0430\u0440\u0442\u043e\u0439, \u043e\u0444\u0438\u0446\u0438\u0430\u043b\u044c\u043d\u044b\u0435 \u043c\u0430\u0448\u0438\u043d\u044b.",
}


ALT_FALLBACK = {
    "uk": "Якщо квитків нема — пошукай тур / вхід без черги",
    "en": "If sold out — find a skip-the-line tour",
    "es": "Si está agotado — busca un tour sin colas",
    "de": "Ausverkauft? — Skip-the-Line-Tour suchen",
    "fr": "Complet ? — cherche une visite coupe-file",
    "it": "Esaurito? — cerca un tour salta-fila",
    "pl": "Brak biletów? — poszukaj wycieczki bez kolejki",
    "ru": "Нет билетов — поищи тур / вход без очереди",
}


def _viator_search(name):
    """Пошукове посилання Viator (фолбек-альтернатива). З affiliate-трекінгом, якщо заданий VIATOR_PID."""
    q = urllib.parse.quote(name or "")
    pid = os.environ.get("VIATOR_PID", "").strip()
    track = ("&pid=%s&mcid=42383&medium=link" % urllib.parse.quote(pid)) if pid else ""
    return "https://www.viator.com/searchResults/all?text=" + q + track


def taxi_line(cc, lang):
    """Рядок про таксі-додаток країни — автоматично, без участі ШІ."""
    app = TAXI_BY_CC.get((cc or "").upper())
    if not app:
        return ""
    tpl = TAXI_TPL.get(lang if lang in TAXI_TPL else "en", TAXI_TPL["en"])
    return tpl.format(app=app)


def daytrips_box(trips, lang="uk"):
    """Секція «Виїзди поряд» з перевіреними посиланнями."""
    if not trips:
        return ""
    lbl = L(lang)
    rows = ""
    for t in trips:
        if not t.get("name"):
            continue
        tlink = safe_url(t.get("link"))
        link = (f'<a href="{esc(tlink)}" target="_blank" rel="noopener">'
                f'{lbl["daytrip_link"]}</a>') if tlink else ""
        why = f' {esc(t["why"])}' if t.get("why") else ""
        rows += (f'<div class="t"><div class="tn">{esc(t["name"])}</div>'
                 f'<div class="td">{esc(t.get("desc", ""))}{why}</div>{link}</div>')
    return f'<div class="trip"><h3>{lbl["daytrips"]}</h3>{rows}</div>' if rows else ""


def build_html(day):
    # мова: з поля "lang" дня. Немає -> "uk" (сумісність зі старими файлами).
    lang = (day.get("lang") or "uk").strip().lower() or "uk"
    t = L(lang)
    stops = day.get("stops", [])
    for s in stops:
        g = fetch(s.get("query", s.get("name", "")), lang)
        for k, v in g.items():
            if k != "purl" and not s.get(k):
                s[k] = v
        s["photo"] = photo_data(g.get("purl"))
    # місто для заголовка/назви: якщо агент не дав — беремо з Google Places (locality)
    if not (day.get("city") or "").strip():
        for _s in stops:
            if _s.get("loc"):
                day["city"] = _s["loc"]
                break
    ensure_schedule(stops)
    blocks = "\n".join(stop_block(s, lang) for s in stops)
    needs_book = any(s.get("book_ahead") for s in stops)
    alert = f'<div class="alert">{t["alert"]}</div>' if needs_book else ""
    # таксі-додаток — АВТОМАТИЧНО за країною (Google Places), ПЕРШИМ підпунктом у блоці
    _cc = ""
    for _s in stops:
        if _s.get("cc"):
            _cc = _s["cc"]
            break
    _taxi = taxi_line(_cc, lang) or (("\U0001f695 " + day.get("taxi")) if day.get("taxi") else "")
    _ga = day.get("getting_around")
    _ga_items = ([_taxi] if _taxi else []) + ([_ga] if isinstance(_ga, str) and _ga else (list(_ga) if _ga else []))
    around = info_box(t["around"], _ga_items, lang)
    budget = info_box(t["budget"], day.get("budget"), lang, "bud")
    # ОДИН блок «Корисно знати» = культура й традиції + дощ/спека/втома + поради
    # (раніше це були 3 окремі блоки — об'єднані, щоб займати менше місця).
    def _aslist(x):
        return [] if not x else ([x] if isinstance(x, str) else list(x))
    good_to_know = (_aslist(day.get("culture")) + _aslist(day.get("weather_plan"))
                    + _aslist(day.get("tips")))
    know = info_box(t["tips"], good_to_know, lang, "tips")
    # «Альтернативні варіанти» (блок унизу) будуємо ЛИШЕ з реального вмісту:
    #  • тури/виїзди за місто з лінком (поле `daytrips`);
    #  • заміна на випадок «нема квитків» для зупинок із book_ahead (поле `alt_if_soldout`).
    # Нема вмісту → блоку НЕМА (жодних «вибачень» — їх нема де взятися).
    _alts = []
    for _d in (day.get("daytrips") or []):
        if _d.get("name") and safe_url(_d.get("link")):
            _alts.append(_d)
    for _s in stops:
        if not _s.get("book_ahead"):
            continue
        if _s.get("alt_if_soldout"):
            _alts.append({"name": _s.get("name", ""), "desc": _s.get("alt_if_soldout"),
                          "link": _s.get("alt_link", "")})
        elif _s.get("name"):
            # СТРУКТУРНИЙ запас: блок альтернатив зʼявляється ЗАВЖДИ при 🎟,
            # навіть якщо модель не дала alt_if_soldout — пропонуємо тур/вхід без черги.
            _alts.append({"name": _s.get("name", ""),
                          "desc": ALT_FALLBACK.get(lang if lang in ALT_FALLBACK else "en", ALT_FALLBACK["en"]),
                          "link": _viator_search(_s.get("name", ""))})
    trips = daytrips_box(_alts, lang)
    foot = esc(day.get("foot", "")) or t["foot_default"]
    # темп дня (бейдж у шапці) + короткий вайб (необовʼязковий, рендеримо лише якщо є)
    pace_map = {"relaxed": t["pace_relaxed"], "balanced": t["pace_balanced"],
                "packed": t["pace_packed"]}
    pv = pace_map.get((day.get("pace") or "").strip().lower(), "")
    pace = f'<div class="pace">{esc(pv)}</div>' if pv else ""
    sm = esc(day.get("summary", ""))
    sum_html = f'<div class="sum">{sm}</div>' if sm else ""
    html_lang = lang if lang in L10N else "en"
    return f"""<!DOCTYPE html><html lang="{html_lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(day.get('city',''))}</title><style>{CSS}</style></head><body>
<div class="hero"><div class="city">{esc(day.get('city',''))}</div>
<div class="day">{esc(day.get('day_label',''))} · {esc(day.get('day_title',''))}</div>
{sum_html}{pace}</div>
{alert}{around}{budget}{know}
<div class="list">{blocks}</div>
{trips}
<div class="foot">{foot}</div></body></html>"""


def send(path, chat, caption, filename=""):
    token = ENV.get("TELEGRAM_BOT_TOKEN")
    chat = chat or ENV.get("TELEGRAM_HOME_CHANNEL")
    if not (token and chat):
        return "NO_TOKEN_OR_CHAT"
    doc = f"document=@{path};type=text/html"
    if filename:
        doc += f";filename={filename}"
    cmd = ["curl", "-sS", "-F", f"chat_id={chat}", "-F", doc]
    if caption:
        cmd += ["-F", f"caption={caption}"]
    cmd.append(f"https://api.telegram.org/bot{token}/sendDocument")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        return "SENT_OK" if '"ok":true' in r.stdout else f"SEND_FAIL: {r.stdout[:200]}"
    except Exception as e:  # noqa: BLE001
        return f"SEND_ERROR: {e}"


def _cleanup_old_pages(keep_path):
    """Прибрати старі згенеровані сторінки в /tmp (щоб не накопичувались),
    лишивши щойно створену. Нічого довго не зберігаємо."""
    import glob
    import time
    now = time.time()
    for f in glob.glob("/tmp/*.html"):
        if f == keep_path:
            continue
        try:
            if now - os.path.getmtime(f) > 1800:  # старші за 30 хв
                os.remove(f)
        except OSError:
            pass


def _build_and_write(day):
    """Збудувати HTML дня і записати у /tmp; повернути шлях до файлу."""
    page = build_html(day)
    # Назву даємо САМОМУ ФАЙЛУ — її показує і Telegram, і WhatsApp як назву документа.
    lang = (day.get("lang") or "uk").strip().lower() or "uk"
    t = L(lang)
    sep = " з " if lang == "uk" else " / "
    label = (day.get("day_label") or "").replace(" / ", sep).replace("/", "-")
    date = (day.get("date") or "").strip()
    name = day.get("city") or t["trip"]
    if label:
        name += f" — {label}"
    if date:
        name += f", {date}"
    name = "".join(c for c in name if c not in '/\\:*?"<>|;\n\r\t').strip() or t["plan"]
    out = f"/tmp/{name}.html"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(page)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="")
    ap.add_argument("--all", action="store_true",
                    help="зібрати ВСІ /tmp/day*.json за раз і вивести MEDIA-рядок на КОЖЕН день")
    ap.add_argument("--chat", default="")
    ap.add_argument("--caption", default="")
    ap.add_argument("--keep", action="store_true", help="не видаляти вхідний JSON (дебаг)")
    ap.add_argument("--send-telegram", action="store_true",
                    help="(легасі) пряма відправка в Telegram замість MEDIA-доставки")
    args = ap.parse_args()

    # --- Режим ВСІ ДНІ за раз: надійна доставка цілої поїздки одним викликом ---
    if args.all:
        import glob
        import re

        def _num(f):
            m = re.search(r"day(\d+)", os.path.basename(f))
            return int(m.group(1)) if m else 0

        files = sorted(glob.glob("/tmp/day*.json"), key=_num)
        if not files:
            print("NO_DAYS: немає /tmp/day*.json — спершу запиши дні")
            return
        built = []
        for f in files:
            try:
                with open(f, encoding="utf-8") as fh:
                    built.append(_build_and_write(json.load(fh)))
            except Exception as e:  # noqa: BLE001
                print(f"SKIP {f}: {e}")
        if not built:
            print("NO_DAYS: не вдалося зібрати жодного дня")
            return
        _cleanup_old_pages(built[-1])
        print(f"BUILT {len(built)} day page(s).")
        print("PAGE_READY — достав користувачу ВСІ рядки MEDIA нижче (РІВНО, по одному на день):")
        for b in built:
            print(f"MEDIA:{b} [[as_document]]")
        if not args.keep:
            for f in files:
                try:
                    os.remove(f)
                except OSError:
                    pass
        return

    if not args.data:
        ap.error("потрібно --data <файл> або --all")
    with open(args.data, encoding="utf-8") as fh:
        day = json.load(fh)
    out = _build_and_write(day)
    _cleanup_old_pages(out)
    print("BUILT:", out, f"({os.path.getsize(out)//1024} KB)")

    if args.send_telegram:
        # Легасі-режим: пряма відправка в Telegram (лишено для тестів/сумісності).
        print(send(out, args.chat, args.caption))
    else:
        # КАНАЛО-НЕЗАЛЕЖНА доставка: НЕ шлемо звідси. Агент доставляє сторінку
        # користувачу повідомленням із MEDIA-тегом — і Telegram, і WhatsApp.
        print("PAGE_READY — достав користувачу повідомленням РІВНО з цим рядком")
        print("(тег приховається автоматично, людина бачить лише сторінку):")
        print(f"MEDIA:{out} [[as_document]]")

    if not args.keep:
        try:
            os.remove(args.data)
        except OSError:
            pass


if __name__ == "__main__":
    main()
