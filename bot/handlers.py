"""
Обробники діалогу Telegram-бота.

Сценарій: /start -> місто -> дні -> інтереси -> бюджет -> готові картки.
"""
from __future__ import annotations

import logging
from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message
from aiogram.utils.chat_action import ChatActionSender

from bot.keyboards import (
    CB_BUDGET,
    CB_INTEREST,
    CB_INTEREST_DONE,
    budget_keyboard,
    interests_keyboard,
)
from bot.states import Planning
from planner.enrich import geocode_query
from planner.models import Budget, Interest, TripRequest
from planner.pipeline import run_pipeline

logger = logging.getLogger(__name__)
router = Router()


# --------------------------------------------------------------------------- #
#  /start  і  /help
# --------------------------------------------------------------------------- #
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "✈️ <b>Привіт! Я твій тревел-планер.</b>\n\n"
        "Складу тобі детальний план подорожі по днях — з місцями, "
        "ресторанами, маршрутами і гарними картками.\n\n"
        "Почнемо! <b>Куди плануєш поїхати?</b>\n"
        "<i>Напиши місто, напр.: Прага, Барселона, Рим…</i>"
    )
    await state.set_state(Planning.city)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Скасовано. Напиши /start, щоб почати спочатку.")


# --------------------------------------------------------------------------- #
#  Крок 1: місто
# --------------------------------------------------------------------------- #
@router.message(Planning.city, F.text)
async def got_city(message: Message, state: FSMContext) -> None:
    city = message.text.strip()
    if len(city) < 2:
        await message.answer("Хм, напиши, будь ласка, назву міста ще раз 🙂")
        return

    # Перевіряємо, що це справді існуюче місце (через OpenStreetMap),
    # щоб не будувати план для випадкового тексту чи питання.
    # Показуємо "друкує…", поки шукаємо.
    found = True
    try:
        async with ChatActionSender.typing(
            bot=message.bot, chat_id=message.chat.id
        ):
            found = await geocode_query(city) is not None
    except Exception:
        # збій мережі — не блокуємо користувача, приймаємо як є
        logger.warning("Не вдалося перевірити місто '%s', приймаю як є", city)
        found = True

    if not found:
        await message.answer(
            "Хм, не можу знайти такого міста 🤔\n"
            "Перевір назву і напиши ще раз — напр.: <b>Рим</b>, <b>Барселона</b>."
        )
        return

    await state.update_data(city=city)
    await message.answer(
        f"Чудовий вибір — <b>{city}</b>! 🌍\n\n"
        "<b>На скільки днів</b> ця подорож?\n"
        "<i>Напиши число, напр.: 3</i>"
    )
    await state.set_state(Planning.days)


# Будь-яке НЕтекстове повідомлення на цьому кроці (голосове, фото, стікер…)
@router.message(Planning.city)
async def city_wrong_type(message: Message) -> None:
    await message.answer(
        "Напиши, будь ласка, назву міста <b>текстом</b> 🙂\n"
        "<i>Голосові повідомлення я поки не розумію — просто надрукуй місто, "
        "напр.: Рим.</i>"
    )


# --------------------------------------------------------------------------- #
#  Крок 2: кількість днів
# --------------------------------------------------------------------------- #
@router.message(Planning.days, F.text)
async def got_days(message: Message, state: FSMContext) -> None:
    raw = message.text.strip()
    if not raw.isdigit() or not (1 <= int(raw) <= 30):
        await message.answer("Напиши число від 1 до 30, будь ласка 🙂")
        return
    await state.update_data(days=int(raw), interests=[])
    await message.answer(
        "Супер! Тепер обери, <b>що тобі цікаво</b> (можна кілька):",
        reply_markup=interests_keyboard(set()),
    )
    await state.set_state(Planning.interests)


# Будь-яке НЕтекстове повідомлення на кроці вибору днів
@router.message(Planning.days)
async def days_wrong_type(message: Message) -> None:
    await message.answer(
        "Напиши, будь ласка, <b>число</b> днів текстом 🙂 (напр.: 3)"
    )


# --------------------------------------------------------------------------- #
#  Крок 3: інтереси (мультивибір)
# --------------------------------------------------------------------------- #
@router.callback_query(Planning.interests, F.data.startswith(CB_INTEREST))
async def toggle_interest(call: CallbackQuery, state: FSMContext) -> None:
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
            reply_markup=interests_keyboard(selected)
        )
    await call.answer()


@router.callback_query(Planning.interests, F.data == CB_INTEREST_DONE)
async def interests_done(call: CallbackQuery, state: FSMContext) -> None:
    with suppress(TelegramBadRequest):
        await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(
        "І останнє — <b>який бюджет</b>?",
        reply_markup=budget_keyboard(),
    )
    await state.set_state(Planning.budget)
    await call.answer()


# --------------------------------------------------------------------------- #
#  Крок 4: бюджет -> запускаємо побудову плану
# --------------------------------------------------------------------------- #
@router.callback_query(Planning.budget, F.data.startswith(CB_BUDGET))
async def got_budget(call: CallbackQuery, state: FSMContext) -> None:
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
    )
    await state.clear()

    status = await call.message.answer(
        f"🧭 Готую твій план по <b>{request.city}</b> на {request.days} дн.\n"
        "Це займе хвилинку — складаю маршрут, шукаю місця і малюю картки…"
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
        await status.edit_text(
            "😔 Ой, щось пішло не так під час побудови плану.\n"
            "Спробуй ще раз: /start"
        )
        return

    if plan.intro:
        await call.message.answer(f"✨ {plan.intro}")

    # відправляємо картки по днях (згори видно "надсилає фото…")
    async with ChatActionSender.upload_photo(bot=bot, chat_id=chat_id):
        for path in cards:
            await call.message.answer_photo(FSInputFile(path))

    await call.message.answer(
        "Готово! 🎒 Гарної подорожі!\n"
        "Збережи картки собі — вони працюють і офлайн.\n\n"
        "Хочеш ще один маршрут? Напиши /start"
    )
    await status.delete()
