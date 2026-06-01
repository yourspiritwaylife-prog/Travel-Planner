"""Інлайн-клавіатури для діалогу (кнопки під повідомленнями)."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from planner.models import Budget, Interest

# callback_data префікси
CB_INTEREST = "int:"
CB_INTEREST_DONE = "int_done"
CB_BUDGET = "bud:"


def interests_keyboard(selected: set[str]) -> InlineKeyboardMarkup:
    """Мультивибір інтересів: галочка біля обраних + кнопка 'Готово'."""
    builder = InlineKeyboardBuilder()
    for interest in Interest:
        mark = "✅ " if interest.value in selected else "▫️ "
        builder.button(
            text=f"{mark}{interest.value.capitalize()}",
            callback_data=f"{CB_INTEREST}{interest.value}",
        )
    builder.adjust(2)
    builder.row(
        InlineKeyboardButton(text="➡️ Готово", callback_data=CB_INTEREST_DONE)
    )
    return builder.as_markup()


def budget_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    labels = {
        Budget.LOW: "💸 Економний",
        Budget.MEDIUM: "💰 Середній",
        Budget.HIGH: "💎 Преміум",
    }
    for budget in Budget:
        builder.button(
            text=labels[budget], callback_data=f"{CB_BUDGET}{budget.value}"
        )
    builder.adjust(1)
    return builder.as_markup()
