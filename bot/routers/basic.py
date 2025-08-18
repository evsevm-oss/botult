from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
import httpx
from core.config import settings

from domain.use_cases import CalculateBudgetsInput, calculate_budgets
from infra.cache.redis import redis_client


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
    # идемпотентность: отметим update_id как увиденный
    if message.update_id:
        await redis_client.setex(f"seen:update:{message.from_user.id}:{message.update_id}", 3600, "1")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Сохранить", callback_data="meal_confirm"), InlineKeyboardButton(text="Отменить", callback_data="meal_cancel")]])
    await message.answer("Фото получено. Создан черновик приема. Распознавание будет выполнено на этапе 9.", reply_markup=kb)


@basic_router.message(Command("photo"))
async def cmd_photo(message: Message) -> None:
    await message.answer("Пришлите фото блюда одним сообщением — я подтвержу получение и позже распознаю.")


@basic_router.message(F.voice | F.audio)
async def on_audio(message: Message) -> None:
    if message.update_id:
        await redis_client.setex(f"seen:update:{message.from_user.id}:{message.update_id}", 3600, "1")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Сохранить", callback_data="meal_confirm"), InlineKeyboardButton(text="Отменить", callback_data="meal_cancel")]])
    await message.answer("Голосовое сообщение получено. Распознавание речи будет добавлено в рамках этапа 8.", reply_markup=kb)


