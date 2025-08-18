from __future__ import annotations

from typing import Any

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from infra.db.models import UserSettings


class UserSettingsRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: int) -> dict | None:
        res = await self.session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
        row = res.scalars().first()
        return dict(row.data) if row else None

    async def upsert(self, user_id: int, data: dict[str, Any]) -> None:
        res = await self.session.execute(select(UserSettings.id).where(UserSettings.user_id == user_id))
        row = res.first()
        if row is None:
            await self.session.execute(insert(UserSettings).values(user_id=user_id, data=data))
        else:
            await self.session.execute(update(UserSettings).where(UserSettings.user_id == user_id).values(data=data))
        await self.session.commit()
