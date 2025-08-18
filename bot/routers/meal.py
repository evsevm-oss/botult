from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
import httpx
from core.config import settings


meal_router = Router()


class AddMealStates(StatesGroup):
    waiting_text = State()


@meal_router.message(Command("addmeal"))
async def cmd_addmeal(message: Message, state: FSMContext) -> None:
    await state.set_state(AddMealStates.waiting_text)
    await message.answer("Введите прием пищи в формате: 'куриная грудка 150 г, рис 120 г, масло 5 г'")


@meal_router.message(AddMealStates.waiting_text, F.text)
async def on_meal_text(message: Message, state: FSMContext) -> None:
    text = message.text or ""
    async with httpx.AsyncClient(base_url=settings.api_base_url, timeout=10.0) as client:
        r = await client.post("/api/normalize", json={"text": text, "locale": "ru", "telegram_id": message.from_user.id})
        if r.status_code == 200:
            data = r.json()
            items = data.get("items", [])
            if not items:
                await message.answer("Не удалось распознать позиции. Попробуйте уточнить формулировки.")
            else:
                preview = "\n".join(
                    f"• {i['name']} — {int(i['amount'])}{i['unit']} ≈ {int(i['kcal'])} ккал"
                    for i in items
                )
                await message.answer(f"Предварительная нормализация:\n{preview}\n(подтверждение и сохранение — на следующем этапе)")
        else:
            await message.answer("Сервис нормализации временно недоступен")
    await state.clear()


