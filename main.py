"""
Точка входу: запускає Telegram-бота.

Запуск:  python main.py
Перед цим: заповни .env (див. .env.example) і встанови залежності.
"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.handlers import router
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("travel-planner")


async def main() -> None:
    problems = settings.validate_ready()
    if problems:
        logger.error("Бот не може стартувати:")
        for p in problems:
            logger.error("  • %s", p)
        logger.error("Заповни .env (приклад у .env.example) і спробуй знову.")
        return

    bot = Bot(
        token=settings.telegram_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    hermes_mode = (
        f"SSH→{settings.hermes_ssh}" if settings.hermes_ssh else "локально"
    )
    logger.info(
        "Travel Planner | мозок=%s (%s, '%s %s') | Бот стартує…",
        settings.brain, hermes_mode, settings.hermes_bin, settings.hermes_flag,
    )
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот зупинено.")
