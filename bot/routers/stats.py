from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message


stats_router = Router()


@stats_router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    await message.answer("Статистика: графики и сводки появятся после интеграции БД (Этапы 2,11).")


