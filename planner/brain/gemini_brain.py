"""
Мозок на базі Google Gemini (безкоштовний тариф).

Ключ безкоштовно: https://aistudio.google.com/app/apikey
"""
from __future__ import annotations

import asyncio

import google.generativeai as genai

from config import settings

from .base import Brain


class GeminiBrain(Brain):
    name = "gemini"

    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise RuntimeError(
                "Немає GEMINI_API_KEY. Візьми безкоштовно на "
                "https://aistudio.google.com/app/apikey і додай у .env"
            )
        genai.configure(api_key=settings.gemini_api_key)
        self._model = genai.GenerativeModel(settings.gemini_model)

    async def complete(self, prompt: str) -> str:
        # SDK синхронний — виносимо у потік, щоб не блокувати бота
        def _call() -> str:
            resp = self._model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.7,
                    "response_mime_type": "application/json",
                },
            )
            return resp.text or ""

        return await asyncio.to_thread(_call)
