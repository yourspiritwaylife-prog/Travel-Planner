""""Мозок" бота — окремий модуль-перехідник (adapter).

Уся решта коду НЕ знає, що саме «думає» всередині. Основний мозок —
існуючий Hermes Agent (через CLI). `mock` лишається для офлайн-перевірки
карток без Hermes.
"""
from __future__ import annotations

from config import settings

from .base import Brain
from .prompt import build_planning_prompt  # noqa: F401  (зручний реекспорт)


def get_brain() -> Brain:
    """Фабрика: повертає потрібний мозок залежно від .env (BRAIN=...)."""
    choice = (settings.brain or "hermes").strip().lower()

    if choice == "hermes":
        from .hermes_brain import HermesBrain

        return HermesBrain()

    if choice == "mock":
        from .mock_brain import MockBrain

        return MockBrain()

    raise ValueError(
        f"Невідомий BRAIN={choice!r}. Допустимі: 'hermes', 'mock'."
    )


__all__ = ["Brain", "get_brain", "build_planning_prompt"]
