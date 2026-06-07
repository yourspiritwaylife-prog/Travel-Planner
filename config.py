"""
Налаштування Travel Planner бота.

Усе читається з .env (див. .env.example). Travel Planner — окремий бот зі
СВОЇМ токеном, який використовує існуючий Hermes Agent (через CLI) як «мозок».
Він НЕ чіпає інший (AI-News) бот і його конфігурацію.
"""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Telegram: ОКРЕМИЙ токен саме для Travel Planner ---
    travel_telegram_bot_token: str = Field(
        default="", alias="TRAVEL_TELEGRAM_BOT_TOKEN"
    )
    # Сумісність зі старим іменем (якщо лишилось у .env) — необовʼязково.
    legacy_telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")

    # --- Який «мозок»: "hermes" (основний) | "mock" (офлайн-демо карток) ---
    brain: str = Field(default="hermes", alias="BRAIN")

    # --- Hermes Agent (викликається через встановлений CLI) ---
    hermes_bin: str = Field(default="hermes", alias="HERMES_BIN")
    hermes_flag: str = Field(default="-z", alias="HERMES_FLAG")
    hermes_timeout: int = Field(default=180, alias="HERMES_TIMEOUT")
    # Тільки для запуску з ІНШОЇ машини (розробка): викликати hermes через SSH,
    # напр. "root@144.126.206.226". Порожнє = бот працює на тому ж сервері,
    # що й Hermes, і кличе його напряму. (Це CLI, а не HTTP — без URL/ключів.)
    hermes_ssh: str = Field(default="", alias="HERMES_SSH")
    # Шлях до приватного SSH-ключа для passwordless-доступу (тільки SSH-режим).
    hermes_ssh_key: str = Field(default="", alias="HERMES_SSH_KEY")

    # --- Безкоштовні джерела даних (ключі НЕ потрібні) ---
    osm_contact_email: str = Field(default="", alias="OSM_CONTACT_EMAIL")

    @property
    def telegram_token(self) -> str:
        """Токен Travel Planner бота (з фолбеком на старе імʼя)."""
        return self.travel_telegram_bot_token or self.legacy_telegram_bot_token

    def validate_ready(self) -> list[str]:
        """Список проблем, якщо чогось бракує для запуску."""
        problems: list[str] = []
        if not self.telegram_token:
            problems.append(
                "Немає TRAVEL_TELEGRAM_BOT_TOKEN — окремий токен Travel Planner бота "
                "(отримай у @BotFather для НОВОГО бота, не плутай з AI-News)."
            )
        if self.brain == "hermes" and not self.hermes_bin:
            problems.append("BRAIN=hermes, але не задано HERMES_BIN")
        return problems


settings = Settings()
