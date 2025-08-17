from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from core.config import settings
from bot.routers import make_root_router
from bot.middlewares.logging import LoggingMiddleware


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
    dp.update.middleware(LoggingMiddleware())
    dp.include_router(make_root_router())

    # Поллинг без вебхуков для простого запуска на VPS
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())


