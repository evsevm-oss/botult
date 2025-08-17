from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message


meal_router = Router()


class AddMealStates(StatesGroup):
    waiting_text = State()


@meal_router.message(Command("addmeal"))
async def cmd_addmeal(message: Message, state: FSMContext) -> None:
    await state.set_state(AddMealStates.waiting_text)
    await message.answer("Введите прием пищи в формате: 'куриная грудка 150 г, рис 120 г, масло 5 г'")


@meal_router.message(AddMealStates.waiting_text, F.text)
async def on_meal_text(message: Message, state: FSMContext) -> None:
    # Заглушка: просто подтверждаем приём
    await message.answer("Принято. На следующих этапах я разберу текст и оценю нутриенты.")
    await state.clear()


