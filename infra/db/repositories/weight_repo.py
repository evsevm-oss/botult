from __future__ import annotations

from datetime import date

from sqlalchemy import insert as sa_insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from infra.db.models import Weight


class WeightRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_weight(self, *, user_id: int, on_date: date, weight_kg: float) -> None:
        # Upsert: если запись за дату существует — обновляем weight_kg; иначе — вставляем
        stmt = pg_insert(Weight).values(user_id=user_id, date=on_date, weight_kg=weight_kg)
        stmt = stmt.on_conflict_do_update(
            index_elements=[Weight.user_id, Weight.date],
            set_={"weight_kg": weight_kg},
        )
        try:
            await self.session.execute(stmt)
        except Exception:
            # Fallback для нестандартных диалектов: попытка update → если 0 строк, то insert
            res = await self.session.execute(
                update(Weight)
                .where(Weight.user_id == user_id, Weight.date == on_date)
                .values(weight_kg=weight_kg)
                .returning(Weight.id)
            )
            if res.first() is None:
                await self.session.execute(sa_insert(Weight).values(user_id=user_id, date=on_date, weight_kg=weight_kg))
        await self.session.commit()

    async def get_last(self, *, user_id: int) -> float | None:
        stmt = select(Weight.weight_kg).where(Weight.user_id == user_id).order_by(Weight.date.desc()).limit(1)
        res = await self.session.execute(stmt)
        row = res.first()
        return float(row[0]) if row else None

    async def list_between(self, *, user_id: int, start: date, end: date) -> list[dict]:
        stmt = (
            select(Weight.date, Weight.weight_kg)
            .where(Weight.user_id == user_id, Weight.date >= start, Weight.date <= end)
            .order_by(Weight.date.asc())
        )
        res = await self.session.execute(stmt)
        return [{"date": d.isoformat(), "weight_kg": float(w)} for d, w in res.all()]


