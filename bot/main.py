from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from core.config import settings
from bot.routers import make_root_router
from bot.middlewares.logging import LoggingMiddleware
from bot.middlewares.trace import TraceMiddleware
from bot.middlewares.locale import LocaleMiddleware


async def main() -> None:
    if not settings.telegram_bot_token:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN не задан. Укажите токен в .env и повторите."
        )

    logging.basicConfig(level=settings.log_level)
    # Частые ошибки: лишние кавычки/пробелы вокруг токена. Подчистим.
    token = (settings.telegram_bot_token or "").strip().strip("'").strip('"')
    bot = Bot(token=token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(TraceMiddleware())
    dp.update.middleware(LoggingMiddleware())
    dp.update.middleware(LocaleMiddleware())
    dp.include_router(make_root_router())

    # Команды бота
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Запуск"),
            BotCommand(command="help", description="Помощь"),
            BotCommand(command="profile", description="Профиль"),
            BotCommand(command="addmeal", description="Добавить приём пищи"),
            BotCommand(command="photo", description="Подсказка по фото"),
            BotCommand(command="coach", description="AI‑коуч"),
            BotCommand(command="stats", description="Статистика"),
            BotCommand(command="settings", description="Настройки"),
        ]
    )

    # Поллинг без вебхуков для простого запуска на VPS
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())


