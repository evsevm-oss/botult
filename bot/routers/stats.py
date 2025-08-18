from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

import httpx
from datetime import date

from core.config import settings


stats_router = Router()


@stats_router.message(Command("goal"))
async def cmd_goal(message: Message) -> None:
    # Пример: /goal weight 75 0.5
    parts = (message.text or "").split()
    if len(parts) < 3:
        await message.answer("Формат: /goal weight|bodyfat <значение> [pace]")
        return
    target_type = parts[1]
    try:
        target_value = float(parts[2])
    except ValueError:
        await message.answer("Значение цели должно быть числом")
        return
    pace = float(parts[3]) if len(parts) > 3 else None

    tg_id = message.from_user.id
    async with httpx.AsyncClient(base_url=settings.api_base_url, timeout=10.0) as client:
        resp = await client.post(
            "/api/goals",
            params={"telegram_id": tg_id},
            json={"target_type": target_type, "target_value": target_value, "pace": pace, "active": True},
        )
        if resp.status_code == 200 and resp.json().get("ok"):
            await message.answer("Цель сохранена")
        else:
            await message.answer("Не удалось сохранить цель")


@stats_router.message(Command("weight"))
async def cmd_weight(message: Message) -> None:
    # Пример: /weight 79.2 (считает сегодняшним числом)
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.answer("Формат: /weight <кг>")
        return
    try:
        w = float(parts[1])
    except ValueError:
        await message.answer("Вес должен быть числом")
        return

    tg_id = message.from_user.id
    today = date.today().isoformat()
    async with httpx.AsyncClient(base_url=settings.api_base_url, timeout=10.0) as client:
        resp = await client.post(
            "/api/weights",
            params={"telegram_id": tg_id},
            json={"date": today, "weight_kg": w},
        )
        if resp.status_code == 200 and resp.json().get("ok"):
            data = resp.json().get("data") or {}
            budgets = data.get("budgets")
            if budgets:
                await message.answer(
                    "Вес сохранён. Бюджеты на сегодня:\n"
                    f"Калории: {int(budgets['kcal'])} ккал\n"
                    f"Белки: {int(budgets['protein_g'])} г\n"
                    f"Жиры: {int(budgets['fat_g'])} г\n"
                    f"Углеводы: {int(budgets['carb_g'])} г"
                )
            else:
                await message.answer("Вес сохранён. Бюджеты обновлены")
        else:
            await message.answer("Не удалось сохранить вес")


