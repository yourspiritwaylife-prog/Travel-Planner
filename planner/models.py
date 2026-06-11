"""
Моделі даних — "форма" подорожі.

Це структури, якими обмінюються всі частини бота:
користувач -> мозок -> джерела даних -> картки.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Interest(str, Enum):
    """Що користувачу цікаво в подорожі.

    Значення — СТАБІЛЬНІ англійські коди (не залежать від мови інтерфейсу).
    Людські назви цих кодів кожною мовою — у planner/i18n.py.
    """

    CULTURE = "culture"        # музеї, історія, архітектура
    FOOD = "food"              # ресторани, локальна кухня
    NATURE = "nature"          # парки, краєвиди, набережні
    NIGHTLIFE = "nightlife"    # бари, нічне життя
    SHOPPING = "shopping"
    RELAX = "relax"            # спокійний темп, спа


class Budget(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TripRequest(BaseModel):
    """Те, що ми зібрали від користувача в діалозі."""

    city: str
    days: int = Field(ge=1, le=30)
    interests: list[Interest] = Field(default_factory=list)
    budget: Budget = Budget.MEDIUM
    # мова, якою спілкується користувач (план і картки будуть нею ж).
    # Код мови (uk, en, es, …). Будь-яка мова — план генерує LLM.
    language: str = "uk"


class TimeOfDay(str, Enum):
    BREAKFAST = "breakfast"
    MORNING = "morning"
    LUNCH = "lunch"
    NOON = "noon"
    EVENING = "evening"
    DINNER = "dinner"


class PlaceKind(str, Enum):
    ATTRACTION = "attraction"
    MUSEUM = "museum"
    RESTAURANT = "restaurant"
    CAFE = "cafe"
    PARK = "park"
    VIEWPOINT = "viewpoint"
    OTHER = "other"


class Place(BaseModel):
    """Одна точка маршруту. Спочатку її пропонує мозок,
    потім ми збагачуємо реальними даними (адреса, фото, координати)."""

    name: str
    kind: PlaceKind = PlaceKind.OTHER
    time_of_day: TimeOfDay = TimeOfDay.NOON
    # короткий опис "чому варто" (від мозку)
    note: str = ""

    # збагачується з безкоштовних джерел (може лишитись порожнім):
    address: str | None = None
    lat: float | None = None
    lon: float | None = None
    photo_url: str | None = None
    rating: float | None = None

    # як дістатись від попередньої точки
    travel_hint: str = ""


class DayPlan(BaseModel):
    """План на один день подорожі."""

    day_number: int
    title: str = ""               # напр. "Історичний центр"
    summary: str = ""             # 1 речення про день
    places: list[Place] = Field(default_factory=list)
    transport_hint: str = ""      # загальна порада по транспорту на день


class TripPlan(BaseModel):
    """Готовий план усієї подорожі."""

    city: str
    days: list[DayPlan] = Field(default_factory=list)
    intro: str = ""               # привітальний абзац
    language: str = "uk"          # мова плану (для локалізації карток)
