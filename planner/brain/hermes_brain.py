"""
Мозок на базі існуючого Hermes-агента (DigitalOcean).

⚠️  ПОКИ ЩО — ЗАГОТОВКА.
Ми ще не знаємо точної адреси та формату Hermes. Цей адаптер написаний
гнучко: він підтримує два найпоширеніші формати HTTP-API. Коли зʼясуємо,
як саме приймає запити Hermes, лишиться тільки:
  1) у .env вписати HERMES_URL (і HERMES_API_KEY, якщо є);
  2) за потреби — обрати HERMES_FORMAT нижче.

Решта бота при цьому НЕ змінюється.
"""
from __future__ import annotations

import httpx

from config import settings

from .base import Brain

# Якщо Hermes сумісний з OpenAI (.../v1/chat/completions) — лиши "openai".
# Якщо це простий ендпоінт, що приймає {"prompt": "..."} і
# повертає {"response": "..."} — постав "simple".
HERMES_FORMAT = "openai"


class HermesBrain(Brain):
    name = "hermes"

    def __init__(self) -> None:
        if not settings.hermes_url:
            raise RuntimeError(
                "Немає HERMES_URL. Спочатку треба зʼясувати адресу Hermes "
                "на сервері DigitalOcean (тимчасово став BRAIN=gemini у .env)."
            )
        self._url = settings.hermes_url.rstrip("/")
        self._headers = {"Content-Type": "application/json"}
        if settings.hermes_api_key:
            self._headers["Authorization"] = f"Bearer {settings.hermes_api_key}"

    async def complete(self, prompt: str) -> str:
        if HERMES_FORMAT == "openai":
            return await self._complete_openai(prompt)
        return await self._complete_simple(prompt)

    async def _complete_openai(self, prompt: str) -> str:
        payload = {
            "model": "hermes",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                self._url, headers=self._headers, json=payload
            )
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def _complete_simple(self, prompt: str) -> str:
        payload = {"prompt": prompt}
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                self._url, headers=self._headers, json=payload
            )
            resp.raise_for_status()
            data = resp.json()
        # пробуємо найпоширеніші ключі
        for key in ("response", "text", "output", "result", "content"):
            if key in data:
                return str(data[key])
        return str(data)
