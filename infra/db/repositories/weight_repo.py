from __future__ import annotations

from datetime import date

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from infra.db.models import Weight


class WeightRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_weight(self, *, user_id: int, on_date: date, weight_kg: float) -> None:
        await self.session.execute(
            insert(Weight)
            .values(user_id=user_id, date=on_date, weight_kg=weight_kg)
            .on_conflict_do_nothing(index_elements=[Weight.user_id, Weight.date])
        )
        await self.session.commit()

    async def get_last(self, *, user_id: int) -> float | None:
        stmt = select(Weight.weight_kg).where(Weight.user_id == user_id).order_by(Weight.date.desc()).limit(1)
        res = await self.session.execute(stmt)
        row = res.first()
        return float(row[0]) if row else None


