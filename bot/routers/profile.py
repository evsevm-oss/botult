from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.keyboards import main_menu_kb


profile_router = Router()


@profile_router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    await message.answer("Профиль: заполнение и обновление будет доступно на Этапе 5.", reply_markup=main_menu_kb())


