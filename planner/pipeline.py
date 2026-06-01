"""
Конвеєр побудови подорожі — єдина точка, що обʼєднує всі етапи:

  запит користувача
      -> мозок (LLM) складає план
      -> збагачуємо реальними даними (OSM/Wikipedia)
      -> малюємо PNG-картки

Бот викликає лише run_pipeline(...) і отримує готові картинки.
"""
from __future__ import annotations

from pathlib import Path

from cards.generator import generate_cards
from planner.brain import get_brain
from planner.enrich import enrich_plan
from planner.models import TripPlan, TripRequest


async def run_pipeline(request: TripRequest) -> tuple[TripPlan, list[Path]]:
    """Повертає (готовий план, список шляхів до PNG-карток)."""
    brain = get_brain()
    plan = await brain.plan_trip(request)
    plan = await enrich_plan(plan)
    cards = await generate_cards(plan)
    return plan, cards
