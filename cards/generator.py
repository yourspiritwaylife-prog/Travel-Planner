"""
Генератор карток: HTML-шаблон + дані -> PNG-картинка для кожного дня.

Використовуємо Playwright (Chromium) як "браузер", який рендерить нашу
красиву HTML-картку і робить її знімок. Один день = одна PNG.
"""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import async_playwright

from planner.i18n import kind_label, t, time_label
from planner.models import DayPlan, PlaceKind, TimeOfDay, TripPlan

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_OUTPUT_DIR = Path("output")

# Емодзі для типу місця (заповнювач, коли немає фото)
_EMOJI = {
    PlaceKind.ATTRACTION: "🏛️",
    PlaceKind.MUSEUM: "🖼️",
    PlaceKind.RESTAURANT: "🍽️",
    PlaceKind.CAFE: "☕",
    PlaceKind.PARK: "🌳",
    PlaceKind.VIEWPOINT: "🌄",
    PlaceKind.OTHER: "📍",
}

# Природний порядок дня — щоб сніданок завжди був першим, вечеря останньою
_TIME_ORDER = {
    TimeOfDay.BREAKFAST: 0,
    TimeOfDay.MORNING: 1,
    TimeOfDay.LUNCH: 2,
    TimeOfDay.NOON: 3,
    TimeOfDay.EVENING: 4,
    TimeOfDay.DINNER: 5,
}

# Іконка часу доби (для кружечка на доріжці таймлайну)
_TIME_ICON = {
    TimeOfDay.BREAKFAST: "🥐",
    TimeOfDay.MORNING: "🌅",
    TimeOfDay.LUNCH: "🍴",
    TimeOfDay.NOON: "☀️",
    TimeOfDay.EVENING: "🌆",
    TimeOfDay.DINNER: "🍷",
}


def _emoji(kind: PlaceKind) -> str:
    return _EMOJI.get(kind, "📍")


def _time_icon(t: TimeOfDay) -> str:
    return _TIME_ICON.get(t, "•")


def _ordered_places(day: DayPlan) -> list:
    """Місця дня у природному порядку часу (стабільно: рівні — як прийшли)."""
    return sorted(day.places, key=lambda p: _TIME_ORDER.get(p.time_of_day, 99))


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    env.globals["emoji"] = _emoji
    env.globals["time_icon"] = _time_icon
    # локалізовані підписи типу місця / часу доби (мовою плану)
    env.globals["kind_label"] = kind_label
    env.globals["time_label"] = time_label
    return env


# Мальовничі типи — їхні фото в Wikipedia найнадійніші, тому вони кращі
# для великої обкладинки (заклади їжі часто дають випадкове фото).
_SCENIC = (
    PlaceKind.ATTRACTION,
    PlaceKind.VIEWPOINT,
    PlaceKind.PARK,
    PlaceKind.MUSEUM,
)


def _pick_collage(ordered: list) -> list:
    """До 5 фото для колажу: обкладинка — мальовниче місце, решта по порядку."""
    photos = [p for p in ordered if p.photo_url] or ordered
    if not photos:
        return []
    hero = next((p for p in photos if p.kind in _SCENIC), photos[0])
    rest = [p for p in photos if p is not hero][:4]
    return [hero, *rest]


def _render_html(plan: TripPlan, day: DayPlan, total_days: int) -> str:
    template = _env().get_template("day_card.html")
    ordered = _ordered_places(day)
    collage = _pick_collage(ordered)
    lang = plan.language or "uk"
    return template.render(
        city=plan.city,
        day=day,
        total_days=total_days,
        places=ordered,
        collage=collage,
        lang=lang,
        day_label=t("card_day", lang),
        transport_label=t("card_transport", lang),
    )


async def generate_cards(plan: TripPlan) -> list[Path]:
    """Згенерувати по одній PNG на кожен день. Повертає шляхи до файлів."""
    _OUTPUT_DIR.mkdir(exist_ok=True)
    paths: list[Path] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1350})

        for day in plan.days:
            html = _render_html(plan, day, len(plan.days))
            await page.set_content(html, wait_until="networkidle")
            card = await page.query_selector(".card")
            out = _OUTPUT_DIR / f"{_safe(plan.city)}_day_{day.day_number}.png"
            if card:
                await card.screenshot(path=str(out))
            else:
                await page.screenshot(path=str(out), full_page=True)
            paths.append(out)

        await browser.close()

    return paths


def _safe(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name).strip("_") or "trip"
