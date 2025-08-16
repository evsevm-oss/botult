from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from core.config import settings


router = Router()


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    await message.answer(
        "Привет! Я бот‑коуч по питанию. Пока я в режиме MVP.\n\n"
        "Доступные команды:\n"
        "- /help — помощь\n"
        "- Отправь фото блюда — скоро научусь распознавать состав и калории"
    )


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    await message.answer(
        "Пока доступно: /start, /help.\n"
        "Следующие шаги: ввод блюд текстом и по фото."
    )


@router.message(F.photo)
async def handle_photo(message: Message) -> None:
    await message.answer(
        "Фото получено. На следующих этапах я распознаю блюдо и оценю калории."
    )


async def main() -> None:
    if not settings.telegram_bot_token:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN не задан. Укажите токен в .env и повторите."
        )

    logging.basicConfig(level=settings.log_level)
    # Частые ошибки: лишние кавычки/пробелы вокруг токена. Подчистим.
    token = (settings.telegram_bot_token or "").strip().strip("'").strip('"')
    bot = Bot(token=token)
    dp = Dispatcher()
    dp.include_router(router)

    # Поллинг без вебхуков для простого запуска на VPS
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())


