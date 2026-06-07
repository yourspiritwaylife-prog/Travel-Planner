"""
Мозок на базі існуючого Hermes Agent (через CLI).

HermesBrain — це адаптер: він бере структурований промпт планувальника і
віддає його в Hermes через окремий CLI-клієнт (`planner/hermes_client.py`),
а назад отримує текст, з якого витягується JSON-план.

Уся транспортна логіка (запуск процесу, таймаут, помилки) — у CLI-клієнті.
Тут лише «переклад» між планувальником і Hermes.
"""
from __future__ import annotations

from planner.hermes_client import HermesCLIClient

from .base import Brain


class HermesBrain(Brain):
    name = "hermes"

    def __init__(self, client: HermesCLIClient | None = None) -> None:
        # Клієнт можна підмінити в тестах; за замовчуванням бере налаштування з .env
        self._cli = client or HermesCLIClient()

    async def complete(self, prompt: str) -> str:
        return await self._cli.run(prompt)
