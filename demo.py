"""
Демонстрація БЕЗ Telegram і БЕЗ ключів.

Генерує приклад карток (Прага, 2 дні) у папку output/.
Потрібно лише: pip install -r requirements.txt  +  playwright install chromium

Запуск:  python demo.py
"""
from __future__ import annotations

import asyncio

from planner.brain.mock_brain import MockBrain
from planner.enrich import enrich_plan
from planner.models import Budget, Interest, TripRequest
from cards.generator import generate_cards


async def main() -> None:
    request = TripRequest(
        city="Прага",
        days=2,
        interests=[Interest.CULTURE, Interest.FOOD],
        budget=Budget.MEDIUM,
    )

    print("1/3  Складаю план (демо-мозок)…")
    plan = await MockBrain().plan_trip(request)

    print("2/3  Шукаю реальні фото та координати (OSM/Wikipedia)…")
    try:
        plan = await enrich_plan(plan)
    except Exception as exc:  # інтернету може не бути — не страшно
        print(f"      (пропускаю збагачення: {exc})")

    print("3/3  Малюю картки…")
    cards = await generate_cards(plan)

    print("\nГотово! Картки збережено:")
    for path in cards:
        print(f"  • {path.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
