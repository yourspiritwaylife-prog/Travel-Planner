"""
Збагачення плану реальними даними з БЕЗКОШТОВНИХ джерел (без ключів):

- OpenStreetMap / Nominatim  -> координати + адреса місця
- Wikipedia REST API          -> фото + перевірка, що місце існує

Якщо джерело недоступне або нічого не знайшло — місце просто лишається
без фото/адреси, бот усе одно працює.
"""
from __future__ import annotations

import asyncio
import re

import httpx

from config import settings
from planner.models import Place, TripPlan

_NOMINATIM = "https://nominatim.openstreetmap.org/search"
_WIKI_API = "https://{lang}.wikipedia.org/w/api.php"

# Прибрати уточнення в дужках із назви: "Ратуша (оглядовий)" -> "Ратуша"
_PAREN = re.compile(r"\s*\([^)]*\)")


def _clean_name(name: str) -> str:
    """Чиста назва для пошуку: без дужок-уточнень і зайвих пробілів."""
    return " ".join(_PAREN.sub("", name).split()).strip(" -–—,")

# Nominatim вимагає чесний User-Agent з контактом і не більше ~1 запиту/сек.
_NOMINATIM_DELAY_SEC = 1.1


def _user_agent() -> str:
    email = settings.osm_contact_email or "anonymous@example.com"
    return f"TravelPlannerBot/1.0 ({email})"


async def geocode_query(query: str) -> tuple[float, float, str] | None:
    """Перевірити, чи існує таке місце/місто (OSM). None — якщо не знайдено.

    Використовується ботом, щоб не приймати випадковий текст замість міста.
    """
    async with httpx.AsyncClient(
        timeout=20, headers={"User-Agent": _user_agent()}
    ) as client:
        return await _geocode(client, query)


async def enrich_plan(plan: TripPlan) -> TripPlan:
    """Пройтись по всіх місцях плану і додати координати/адресу/фото."""
    async with httpx.AsyncClient(
        timeout=20, headers={"User-Agent": _user_agent()}
    ) as client:
        for day in plan.days:
            for place in day.places:
                await _enrich_place(client, place, plan.city)
                # бережемо ліміти Nominatim
                await asyncio.sleep(_NOMINATIM_DELAY_SEC)
    return plan


async def _enrich_place(client: httpx.AsyncClient, place: Place, city: str) -> None:
    clean = _clean_name(place.name)

    # 1) координати + адреса з OpenStreetMap
    try:
        coords = await _geocode(client, f"{clean}, {city}")
        if coords:
            place.lat, place.lon, place.address = coords
    except Exception:
        pass  # мовчки пропускаємо — місце лишається без координат

    # 2) фото з Wikipedia (пошук статті + її мініатюра)
    try:
        photo = await _wiki_photo(client, clean, city)
        if photo:
            place.photo_url = photo
    except Exception:
        pass


async def _geocode(
    client: httpx.AsyncClient, query: str
) -> tuple[float, float, str] | None:
    resp = await client.get(
        _NOMINATIM,
        params={"q": query, "format": "json", "limit": 1, "addressdetails": 1},
    )
    resp.raise_for_status()
    results = resp.json()
    if not results:
        return None
    top = results[0]
    return float(top["lat"]), float(top["lon"]), top.get("display_name", "")


async def _wiki_photo(
    client: httpx.AsyncClient, name: str, city: str
) -> str | None:
    """Фото місця з Wikipedia.

    Стратегія: спершу шукаємо ТОЧНУ статтю місця (її фото завжди правильне),
    і лише якщо такої нема — загальний пошук (ширше, але інколи дає фото
    зі схожої статті). Українська Вікіпедія в пріоритеті, далі англійська.
    """
    for lang in ("uk", "en"):  # 1) точна стаття — найточніше фото
        source = await _wiki_summary_photo(client, lang, name)
        if source:
            return source
    for lang in ("uk", "en"):  # 2) загальний пошук — ширше охоплення
        source = await _wiki_search_photo(client, lang, name, city)
        if source:
            return source
    return None


async def _wiki_summary_photo(
    client: httpx.AsyncClient, lang: str, name: str
) -> str | None:
    """Фото зі статті з точно такою назвою (REST summary)."""
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/"
    resp = await client.get(url + name.replace(" ", "_"))
    if resp.status_code != 200:
        return None
    data = resp.json()
    if data.get("type") != "standard":  # пропускаємо неоднозначності
        return None
    thumb = data.get("originalimage") or data.get("thumbnail") or {}
    return thumb.get("source")


async def _wiki_search_photo(
    client: httpx.AsyncClient, lang: str, name: str, city: str
) -> str | None:
    """Фото з першої знайденої пошуком статті, що має зображення."""
    params = {
        "action": "query",
        "format": "json",
        "prop": "pageimages",
        "piprop": "thumbnail",
        "pithumbsize": 1000,
        "generator": "search",
        "gsrsearch": f"{name} {city}".strip(),
        "gsrlimit": 4,
        "gsrnamespace": 0,
    }
    resp = await client.get(_WIKI_API.format(lang=lang), params=params)
    if resp.status_code != 200:
        return None
    pages = (resp.json().get("query") or {}).get("pages") or {}
    # поле "index" дає порядок релевантності пошуку
    for page in sorted(pages.values(), key=lambda p: p.get("index", 999)):
        source = (page.get("thumbnail") or {}).get("source")
        if source:
            return source
    return None
