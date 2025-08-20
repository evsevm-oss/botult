from __future__ import annotations

from typing import Any

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from infra.db.models import Image


class ImageRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_or_get(
        self,
        *,
        user_id: int | None,
        object_key: str,
        sha256: str,
        width: int | None,
        height: int | None,
        content_type: str,
        meal_id: int | None = None,
    ) -> int:
        res = await self.session.execute(select(Image.id).where(Image.sha256 == sha256))
        row = res.first()
        if row:
            return int(row[0])
        stmt = (
            insert(Image)
            .values(
                user_id=user_id,
                meal_id=meal_id,
                object_key=object_key,
                width=width or 0,
                height=height or 0,
                content_type=content_type,
                sha256=sha256,
            )
            .returning(Image.id)
        )
        res = await self.session.execute(stmt)
        await self.session.commit()
        return int(res.scalar_one())

    async def attach_to_meal(self, *, image_id: int, meal_id: int) -> None:
        await self.session.execute(update(Image).where(Image.id == image_id).values(meal_id=meal_id))
        await self.session.commit()

    async def list_by_meal(self, *, meal_id: int) -> list[dict[str, Any]]:
        res = await self.session.execute(select(Image).where(Image.meal_id == meal_id))
        return [
            dict(
                id=i.id,
                object_key=i.object_key,
                width=i.width,
                height=i.height,
                content_type=i.content_type,
                sha256=i.sha256,
            )
            for i in res.scalars().all()
        ]

    async def get_by_ids(self, image_ids: list[int]) -> list[dict[str, Any]]:
        if not image_ids:
            return []
        res = await self.session.execute(select(Image).where(Image.id.in_(image_ids)))
        return [
            dict(
                id=i.id,
                user_id=i.user_id,
                object_key=i.object_key,
                width=i.width,
                height=i.height,
                content_type=i.content_type,
                sha256=i.sha256,
            )
            for i in res.scalars().all()
        ]


