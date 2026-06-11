"""
Памʼять мови по користувачу (проста, без БД).

Зберігаємо вибір мови у JSON-файлі поряд із ботом, щоб користувач не мусив
обирати її щоразу. Кеш у памʼяті + запис на диск при зміні. Цього достатньо
для одного процесу-бота; за потреби легко замінити на Redis/БД пізніше.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from planner.i18n import DEFAULT_LANG, normalize_lang

logger = logging.getLogger(__name__)

_PATH = Path("userprefs.json")
_cache: dict[str, str] | None = None


def _load() -> dict[str, str]:
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(_PATH.read_text("utf-8")) if _PATH.exists() else {}
        except Exception as exc:  # пошкоджений файл — не валимо бота
            logger.warning("Не зміг прочитати %s: %s", _PATH, exc)
            _cache = {}
    return _cache


def get_lang(user_id: int) -> str | None:
    """Збережена мова користувача або None, якщо ще не обирав."""
    return _load().get(str(user_id))


def set_lang(user_id: int, lang: str) -> None:
    """Запамʼятати мову користувача (нормалізуємо код)."""
    cache = _load()
    cache[str(user_id)] = normalize_lang(lang)
    try:
        _PATH.write_text(json.dumps(cache, ensure_ascii=False), "utf-8")
    except Exception as exc:
        logger.warning("Не зміг записати %s: %s", _PATH, exc)


def resolve_lang(user_id: int, telegram_lang: str | None) -> str:
    """Яку мову вживати: збережений вибір → локаль Telegram → DEFAULT_LANG.

    Якщо для визначеної мови ще немає перекладу інтерфейсу — діалог сам впаде
    на англійську (всередині t()), а ось ПЛАН усе одно буде мовою користувача.
    """
    saved = get_lang(user_id)
    return saved or normalize_lang(telegram_lang)