"""
Налаштування проєкту.

Усе читається з файлу .env (див. .env.example).
Нічого хардкодити не треба — тільки заповнити .env.
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

    # --- Telegram ---
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")

    # --- Який "мозок": "gemini" | "hermes" ---
    brain: str = Field(default="gemini", alias="BRAIN")

    # --- Gemini ---
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")

    # --- Hermes (DigitalOcean) ---
    hermes_url: str = Field(default="", alias="HERMES_URL")
    hermes_api_key: str = Field(default="", alias="HERMES_API_KEY")

    # --- Безкоштовні джерела даних ---
    osm_contact_email: str = Field(default="", alias="OSM_CONTACT_EMAIL")

    def validate_ready(self) -> list[str]:
        """Повертає список проблем, якщо чогось бракує для запуску."""
        problems: list[str] = []
        if not self.telegram_bot_token:
            problems.append("Немає TELEGRAM_BOT_TOKEN (отримай у @BotFather)")
        if self.brain == "gemini" and not self.gemini_api_key:
            problems.append("BRAIN=gemini, але немає GEMINI_API_KEY")
        if self.brain == "hermes" and not self.hermes_url:
            problems.append("BRAIN=hermes, але немає HERMES_URL")
        return problems


settings = Settings()
