from __future__ import annotations

from aiogram import BaseMiddleware
from aiogram.types import Update


class LocaleMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data):  # type: ignore[override]
        data["locale"] = "ru"
        return await handler(event, data)


