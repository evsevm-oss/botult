from __future__ import annotations

from datetime import date as Date

from sqlalchemy import insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from infra.db.models import DailySummary


class DailySummaryRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_daily_summary(
        self,
        *,
        user_id: int,
        on_date: Date,
        kcal: float,
        protein_g: float,
        fat_g: float,
        carb_g: float,
    ) -> None:
        stmt = pg_insert(DailySummary).values(
            user_id=user_id,
            date=on_date,
            kcal=kcal,
            protein_g=protein_g,
            fat_g=fat_g,
            carb_g=carb_g,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[DailySummary.user_id, DailySummary.date],
            set_(dict(kcal=kcal, protein_g=protein_g, fat_g=fat_g, carb_g=carb_g)),
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_by_user_date(self, *, user_id: int, on_date: Date) -> dict | None:
        from infra.db.models import DailySummary
        stmt = select(
            DailySummary.kcal, DailySummary.protein_g, DailySummary.fat_g, DailySummary.carb_g
        ).where(DailySummary.user_id == user_id, DailySummary.date == on_date)
        res = await self.session.execute(stmt)
        row = res.first()
        if not row:
            return None
        return {
            "kcal": float(row[0]),
            "protein_g": float(row[1]),
            "fat_g": float(row[2]),
            "carb_g": float(row[3]),
        }


