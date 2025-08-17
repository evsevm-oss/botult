from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message


coach_router = Router()


@coach_router.message(Command("coach"))
async def cmd_coach(message: Message) -> None:
    await message.answer("Режим AI‑коуча будет подключён на Этапе 10.")


