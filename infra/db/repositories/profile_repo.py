from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from infra.db.models import Profile


class ProfileRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: int) -> dict[str, Any] | None:
        stmt = select(
            Profile.user_id,
            Profile.sex,
            Profile.birth_date,
            Profile.height_cm,
            Profile.weight_kg,
            Profile.activity_level,
            Profile.goal,
        ).where(Profile.user_id == user_id)
        res = await self.session.execute(stmt)
        row = res.mappings().first()
        return dict(row) if row else None

    async def upsert_profile(
        self,
        *,
        user_id: int,
        sex: str,
        birth_date: date | None,
        height_cm: float,
        weight_kg: float,
        activity_level: str,
        goal: str,
    ) -> None:
        exists = await self.get_by_user_id(user_id)
        if exists is None:
            stmt = insert(Profile).values(
                user_id=user_id,
                sex=sex,
                birth_date=birth_date,
                height_cm=height_cm,
                weight_kg=weight_kg,
                activity_level=activity_level,
                goal=goal,
            )
            await self.session.execute(stmt)
        else:
            stmt = (
                update(Profile)
                .where(Profile.user_id == user_id)
                .values(
                    sex=sex,
                    birth_date=birth_date,
                    height_cm=height_cm,
                    weight_kg=weight_kg,
                    activity_level=activity_level,
                    goal=goal,
                )
            )
            await self.session.execute(stmt)
        await self.session.commit()


