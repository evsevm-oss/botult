from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from domain.use_cases import CalculateBudgetsInput, calculate_budgets


basic_router = Router()


@basic_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Я бот‑коуч по питанию (MVP). Доступно: /help, /budget."
    )


@basic_router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer("Доступно: /start, /help, /budget — пример расчёта бюджета.")


@basic_router.message(Command("budget"))
async def cmd_budget(message: Message) -> None:
    # Заглушка профиля — позже возьмём из БД/профиля пользователя
    inp = CalculateBudgetsInput(
        sex="male",
        age=30,
        height_cm=180,
        weight_kg=80,
        activity_level="medium",
        goal="maintain",
    )
    out = calculate_budgets(inp)
    await message.answer(
        f"Дневной бюджет (пример):\n"
        f"Калории: {int(out.kcal)} ккал\n"
        f"Б: {int(out.protein_g)} г, Ж: {int(out.fat_g)} г, У: {int(out.carb_g)} г"
    )


@basic_router.message(F.photo)
async def on_photo(message: Message) -> None:
    await message.answer("Фото получено. Vision/LLM подключим на следующих этапах.")


@basic_router.message(Command("photo"))
async def cmd_photo(message: Message) -> None:
    await message.answer("Пришлите фото блюда одним сообщением — я подтвержу получение и позже распознаю.")


