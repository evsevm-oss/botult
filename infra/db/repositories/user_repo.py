from __future__ import annotations

from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from infra.db.models import User


class UserRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> int | None:
        stmt = select(User.id).where(User.telegram_id == telegram_id)
        res = await self.session.execute(stmt)
        row = res.first()
        return int(row[0]) if row else None

    async def get_or_create_by_telegram_id(self, telegram_id: int, lang: str = "ru", timezone: str = "UTC") -> int:
        user_id = await self.get_by_telegram_id(telegram_id)
        if user_id is not None:
            return user_id
        stmt = insert(User).values(telegram_id=telegram_id, lang=lang, timezone=timezone).returning(User.id)
        res = await self.session.execute(stmt)
        await self.session.commit()
        return int(res.scalar_one())


