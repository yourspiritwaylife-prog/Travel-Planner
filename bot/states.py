"""Стани діалогу (FSM) — щоб бот памʼятав, на якому кроці користувач."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class Planning(StatesGroup):
    city = State()        # чекаємо назву міста
    days = State()        # чекаємо кількість днів
    interests = State()   # обираємо інтереси (кілька)
    budget = State()      # обираємо бюджет
