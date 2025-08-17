from __future__ import annotations

import uuid
import structlog
from aiogram import BaseMiddleware
from aiogram.types import Update


log = structlog.get_logger(__name__)


class TraceMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data):  # type: ignore[override]
        trace_id = uuid.uuid4().hex[:12]
        data["trace_id"] = trace_id
        log.bind(trace_id=trace_id).info("trace_start")
        try:
            return await handler(event, data)
        finally:
            log.bind(trace_id=trace_id).info("trace_end")


