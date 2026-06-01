"""
Загальний інтерфейс мозку + спільна логіка розбору відповіді.

Будь-який мозок (Gemini, Hermes, ...) має вміти одне:
взяти TripRequest і повернути TripPlan.
"""
from __future__ import annotations

import abc
import json

from planner.models import (
    DayPlan,
    Place,
    PlaceKind,
    TimeOfDay,
    TripPlan,
    TripRequest,
)


class Brain(abc.ABC):
    """Базовий клас "мозку". Конкретні реалізації лише дають сирий текст."""

    name: str = "brain"

    @abc.abstractmethod
    async def complete(self, prompt: str) -> str:
        """Надіслати prompt у LLM і повернути сирий текст-відповідь."""
        raise NotImplementedError

    async def plan_trip(self, request: TripRequest) -> TripPlan:
        """Головний метод: запит користувача -> структурований план."""
        from .prompt import build_planning_prompt

        prompt = build_planning_prompt(request)
        raw = await self.complete(prompt)
        data = _extract_json(raw)
        return _parse_plan(request, data)


# --------------------------------------------------------------------------- #
#  Допоміжне: дістати JSON з відповіді LLM (буває обгорнутий у ```json ... ```)
# --------------------------------------------------------------------------- #
def _extract_json(raw: str) -> dict:
    text = raw.strip()

    # прибрати markdown-огортку ```json ... ```
    if text.startswith("```"):
        text = text.split("```", 2)[1] if "```" in text[3:] else text
        text = text.removeprefix("json").strip("` \n")

    # на випадок зайвого тексту до/після — вирізати від першої { до останньої }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Мозок повернув не-JSON відповідь. Початок: {raw[:300]!r}"
        ) from exc


def _parse_plan(request: TripRequest, data: dict) -> TripPlan:
    """Перетворити сирий dict від LLM у строгі моделі (з мʼякими дефолтами)."""
    days: list[DayPlan] = []

    for i, raw_day in enumerate(data.get("days", []), start=1):
        places: list[Place] = []
        for raw_place in raw_day.get("places", []):
            places.append(
                Place(
                    name=str(raw_place.get("name", "")).strip() or "Місце",
                    kind=_safe_enum(PlaceKind, raw_place.get("kind"), PlaceKind.OTHER),
                    time_of_day=_safe_enum(
                        TimeOfDay, raw_place.get("time_of_day"), TimeOfDay.NOON
                    ),
                    note=str(raw_place.get("note", "")).strip(),
                    travel_hint=str(raw_place.get("travel_hint", "")).strip(),
                )
            )

        days.append(
            DayPlan(
                day_number=int(raw_day.get("day_number", i)),
                title=str(raw_day.get("title", "")).strip(),
                summary=str(raw_day.get("summary", "")).strip(),
                transport_hint=str(raw_day.get("transport_hint", "")).strip(),
                places=places,
            )
        )

    return TripPlan(
        city=request.city,
        intro=str(data.get("intro", "")).strip(),
        days=days,
    )


def _safe_enum(enum_cls, value, default):
    """Безпечно перетворити рядок у Enum (LLM може дати укр/англ варіант)."""
    if value is None:
        return default
    value_str = str(value).strip().lower()
    for member in enum_cls:
        if value_str in (member.value.lower(), member.name.lower()):
            return member
    return default
