"""
Обробники діалогу Telegram-бота.

Сценарій: /start -> місто -> дні -> інтереси -> бюджет -> готові картки.
Мова: визначається автоматично (збережений вибір → локаль Telegram → текст),
змінюється будь-коли командою /language. План і картки — мовою користувача.
"""
from __future__ import annotations

import logging
from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message, User
from aiogram.utils.chat_action import ChatActionSender

from bot import userprefs
from bot.keyboards import (
    CB_BUDGET,
    CB_INTEREST,
    CB_INTEREST_DONE,
    CB_LANG,
    budget_keyboard,
    interests_keyboard,
    language_keyboard,
)
from bot.states import Planning
from planner.enrich import geocode_query
from planner.i18n import detect_language, t
from planner.models import Budget, Interest, TripRequest
from planner.pipeline import run_pipeline

logger = logging.getLogger(__name__)
router = Router()


# --------------------------------------------------------------------------- #
#  Мова користувача (одне джерело правди для всіх обробників)
# --------------------------------------------------------------------------- #
async def get_lang(state: FSMContext, user: User | None) -> str:
    """Мова з памʼяті діалогу; якщо ще нема — визначаємо й запамʼятовуємо."""
    data = await state.get_data()
    lang = data.get("lang")
    if not lang:
        tg_lang = user.language_code if user else None
        lang = userprefs.resolve_lang(user.id if user else 0, tg_lang)
        await state.update_data(lang=lang)
    return lang


# --------------------------------------------------------------------------- #
#  /start  і  /help
# --------------------------------------------------------------------------- #
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    # збережений вибір переживає clear() (лежить у userprefs), локаль — запасна
    lang = userprefs.resolve_lang(
        message.from_user.id, message.from_user.language_code
    )
    await state.update_data(lang=lang)
    await message.answer(t("start", lang))
    await state.set_state(Planning.city)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    lang = await get_lang(state, message.from_user)
    await state.clear()
    await message.answer(t("cancel", lang))


# --------------------------------------------------------------------------- #
#  /language — змінити мову будь-коли (працює у будь-якому стані)
# --------------------------------------------------------------------------- #
@router.message(Command("language"))
async def cmd_language(message: Message, state: FSMContext) -> None:
    lang = await get_lang(state, message.from_user)
    await message.answer(t("choose_language", lang), reply_markup=language_keyboard())


@router.callback_query(F.data.startswith(CB_LANG))
async def set_language(call: CallbackQuery, state: FSMContext) -> None:
    lang = call.data.removeprefix(CB_LANG)
    userprefs.set_lang(call.from_user.id, lang)
    await state.update_data(lang=lang)
    with suppress(TelegramBadRequest):
        await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(t("language_set", lang))
    await call.answer()


# --------------------------------------------------------------------------- #
#  Крок 1: місто
# --------------------------------------------------------------------------- #
@router.message(Planning.city, F.text)
async def got_city(message: Message, state: FSMContext) -> None:
    lang = await get_lang(state, message.from_user)
    city = message.text.strip()
    if len(city) < 2:
        await message.answer(t("city_too_short", lang))
        return

    # Якщо текст явно іншою мовою (кирилиця uk/ru) — підлаштовуємо мову.
    detected = detect_language(city, default=lang)
    if detected != lang:
        lang = detected
        await state.update_data(lang=lang)
        userprefs.set_lang(message.from_user.id, lang)

    # Перевіряємо, що це справді існуюче місце (через OpenStreetMap),
    # щоб не будувати план для випадкового тексту чи питання.
    found = True
    try:
        async with ChatActionSender.typing(
            bot=message.bot, chat_id=message.chat.id
        ):
            found = await geocode_query(city) is not None
    except Exception:
        logger.warning("Не вдалося перевірити місто '%s', приймаю як є", city)
        found = True

    if not found:
        await message.answer(t("city_not_found", lang))
        return

    await state.update_data(city=city)
    await message.answer(t("city_ok", lang, city=city))
    await state.set_state(Planning.days)


# Будь-яке НЕтекстове повідомлення на цьому кроці (голосове, фото, стікер…)
@router.message(Planning.city)
async def city_wrong_type(message: Message, state: FSMContext) -> None:
    lang = await get_lang(state, message.from_user)
    await message.answer(t("city_wrong_type", lang))


# --------------------------------------------------------------------------- #
#  Крок 2: кількість днів
# --------------------------------------------------------------------------- #
@router.message(Planning.days, F.text)
async def got_days(message: Message, state: FSMContext) -> None:
    lang = await get_lang(state, message.from_user)
    raw = message.text.strip()
    if not raw.isdigit() or not (1 <= int(raw) <= 30):
        await message.answer(t("days_invalid", lang))
        return
    await state.update_data(days=int(raw), interests=[])
    await message.answer(
        t("ask_interests", lang), reply_markup=interests_keyboard(set(), lang)
    )
    await state.set_state(Planning.interests)


# Будь-яке НЕтекстове повідомлення на кроці вибору днів
@router.message(Planning.days)
async def days_wrong_type(message: Message, state: FSMContext) -> None:
    lang = await get_lang(state, message.from_user)
    await message.answer(t("days_wrong_type", lang))


# --------------------------------------------------------------------------- #
#  Крок 3: інтереси (мультивибір)
# --------------------------------------------------------------------------- #
@router.callback_query(Planning.interests, F.data.startswith(CB_INTEREST))
async def toggle_interest(call: CallbackQuery, state: FSMContext) -> None:
    lang = await get_lang(state, call.from_user)
    value = call.data.removeprefix(CB_INTEREST)
    data = await state.get_data()
    selected = set(data.get("interests", []))

    if value in selected:
        selected.discard(value)
    else:
        selected.add(value)

    await state.update_data(interests=list(selected))
    # Якщо швидко тиснути ту саму кнопку, Telegram може повернути
    # "message is not modified" — це не помилка, просто ігноруємо.
    with suppress(TelegramBadRequest):
        await call.message.edit_reply_markup(
            reply_markup=interests_keyboard(selected, lang)
        )
    await call.answer()


@router.callback_query(Planning.interests, F.data == CB_INTEREST_DONE)
async def interests_done(call: CallbackQuery, state: FSMContext) -> None:
    lang = await get_lang(state, call.from_user)
    with suppress(TelegramBadRequest):
        await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(t("ask_budget", lang), reply_markup=budget_keyboard(lang))
    await state.set_state(Planning.budget)
    await call.answer()


# --------------------------------------------------------------------------- #
#  Крок 4: бюджет -> запускаємо побудову плану
# --------------------------------------------------------------------------- #
@router.callback_query(Planning.budget, F.data.startswith(CB_BUDGET))
async def got_budget(call: CallbackQuery, state: FSMContext) -> None:
    lang = await get_lang(state, call.from_user)
    budget_value = call.data.removeprefix(CB_BUDGET)
    data = await state.get_data()
    with suppress(TelegramBadRequest):
        await call.message.edit_reply_markup(reply_markup=None)
    await call.answer()

    request = TripRequest(
        city=data["city"],
        days=data["days"],
        interests=[Interest(v) for v in data.get("interests", [])],
        budget=Budget(budget_value),
        language=lang,
    )
    await state.clear()

    status = await call.message.answer(
        t("building", lang, city=request.city, days=request.days)
    )

    chat_id = call.message.chat.id
    bot = call.message.bot

    try:
        # Поки будуємо план, у чаті згори світиться "друкує…",
        # щоб було видно, що бот працює, а не завис.
        async with ChatActionSender.typing(bot=bot, chat_id=chat_id):
            plan, cards = await run_pipeline(request)
    except Exception:
        logger.exception("Помилка побудови плану")
        await status.edit_text(t("error", lang))
        return

    if plan.intro:
        await call.message.answer(f"✨ {plan.intro}")

    # відправляємо картки по днях (згори видно "надсилає фото…")
    async with ChatActionSender.upload_photo(bot=bot, chat_id=chat_id):
        for path in cards:
            await call.message.answer_photo(FSInputFile(path))

    await call.message.answer(t("done", lang))
    await status.delete()