from __future__ import annotations

import structlog
from aiogram import BaseMiddleware
from aiogram.types import Update


log = structlog.get_logger(__name__)


class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data):  # type: ignore[override]
        log.info("tg_update", type=event.event_type, user_id=getattr(getattr(event, 'from_user', None), 'id', None))
        return await handler(event, data)


