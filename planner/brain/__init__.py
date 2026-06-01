"""
"Мозок" бота — окремий модуль-перехідник (adapter).

Уся решта коду НЕ знає, який саме LLM працює всередині.
Завдяки цьому можна міняти Gemini <-> Hermes, не переписуючи бота.
"""
from __future__ import annotations

from config import settings

from .base import Brain
from .prompt import build_planning_prompt  # noqa: F401  (зручний реекспорт)


def get_brain() -> Brain:
    """Фабрика: повертає потрібний мозок залежно від .env (BRAIN=...)."""
    choice = (settings.brain or "gemini").strip().lower()

    if choice == "mock":
        from .mock_brain import MockBrain

        return MockBrain()

    if choice == "hermes":
        from .hermes_brain import HermesBrain

        return HermesBrain()

    if choice == "gemini":
        from .gemini_brain import GeminiBrain

        return GeminiBrain()

    raise ValueError(
        f"Невідомий BRAIN={choice!r}. Допустимі: 'mock', 'gemini', 'hermes'."
    )


__all__ = ["Brain", "get_brain", "build_planning_prompt"]
