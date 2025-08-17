from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message


settings_router = Router()


@settings_router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    await message.answer("Настройки будут реализованы на Этапе 12 (единицы, уведомления, предпочтения).")


