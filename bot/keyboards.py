"""Інлайн-клавіатури для діалогу (кнопки під повідомленнями)."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from planner.i18n import (
    budget_label,
    interest_label,
    language_native_name,
    offered_languages,
    t,
)
from planner.models import Budget, Interest

# callback_data префікси
CB_INTEREST = "int:"
CB_INTEREST_DONE = "int_done"
CB_BUDGET = "bud:"
CB_LANG = "lang:"


def interests_keyboard(selected: set[str], lang: str) -> InlineKeyboardMarkup:
    """Мультивибір інтересів: галочка біля обраних + кнопка 'Готово'."""
    builder = InlineKeyboardBuilder()
    for interest in Interest:
        mark = "✅ " if interest.value in selected else "▫️ "
        builder.button(
            text=f"{mark}{interest_label(interest, lang)}",
            callback_data=f"{CB_INTEREST}{interest.value}",
        )
    builder.adjust(2)
    builder.row(
        InlineKeyboardButton(text=t("btn_done", lang), callback_data=CB_INTEREST_DONE)
    )
    return builder.as_markup()


def budget_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    icons = {Budget.LOW: "💸", Budget.MEDIUM: "💰", Budget.HIGH: "💎"}
    for budget in Budget:
        builder.button(
            text=f"{icons[budget]} {budget_label(budget, lang)}",
            callback_data=f"{CB_BUDGET}{budget.value}",
        )
    builder.adjust(1)
    return builder.as_markup()


def language_keyboard() -> InlineKeyboardMarkup:
    """Вибір мови інтерфейсу (рідні назви з прапорцями)."""
    builder = InlineKeyboardBuilder()
    for code in offered_languages():
        builder.button(
            text=language_native_name(code), callback_data=f"{CB_LANG}{code}"
        )
    builder.adjust(2)
    return builder.as_markup()