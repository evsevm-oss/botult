from __future__ import annotations

from datetime import date as Date, datetime
from typing import Any, Iterable

from sqlalchemy import insert, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from infra.db.models import Meal, MealItem, MealTypeEnum


class MealRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_meal(
        self,
        *,
        user_id: int,
        at: datetime,
        meal_type: str,
        items: Iterable[dict[str, Any]],
        notes: str | None = None,
    ) -> int:
        res = await self.session.execute(
            insert(Meal)
            .values(user_id=user_id, at=at, type=meal_type, notes=notes)
            .returning(Meal.id)
        )
        meal_id = int(res.scalar_one())
        # bulk items
        values = [
            dict(
                meal_id=meal_id,
                name=i["name"],
                amount=float(i["amount"]),
                unit=i["unit"],
                kcal=float(i["kcal"]),
                protein_g=float(i["protein_g"]),
                fat_g=float(i["fat_g"]),
                carb_g=float(i["carb_g"]),
                source="manual",
            )
            for i in items
        ]
        if values:
            await self.session.execute(insert(MealItem).values(values))
        await self.session.commit()
        return meal_id

    async def delete_meal(self, *, meal_id: int, user_id: int) -> None:
        await self.session.execute(delete(MealItem).where(MealItem.meal_id == meal_id))
        await self.session.execute(delete(Meal).where(Meal.id == meal_id, Meal.user_id == user_id))
        await self.session.commit()

    async def list_by_date(self, *, user_id: int, on_date: Date) -> list[dict[str, Any]]:
        start = datetime.combine(on_date, datetime.min.time()).astimezone()
        end = datetime.combine(on_date, datetime.max.time()).astimezone()
        res = await self.session.execute(
            select(Meal).where(Meal.user_id == user_id, Meal.at >= start, Meal.at <= end).order_by(Meal.at.asc())
        )
        meals: list[dict[str, Any]] = []
        rows = res.scalars().all()
        if not rows:
            return []
        meal_ids = [m.id for m in rows]
        items_map: dict[int, list[dict[str, Any]]] = {mid: [] for mid in meal_ids}
        res_it = await self.session.execute(select(MealItem).where(MealItem.meal_id.in_(meal_ids)))
        for it in res_it.scalars().all():
            items_map[it.meal_id].append(
                dict(
                    id=it.id,
                    name=it.name,
                    amount=it.amount,
                    unit=it.unit,
                    kcal=it.kcal,
                    protein_g=it.protein_g,
                    fat_g=it.fat_g,
                    carb_g=it.carb_g,
                    source=it.source,
                )
            )
        for m in rows:
            meals.append(
                dict(
                    id=m.id,
                    at=m.at.isoformat(),
                    type=m.type,
                    notes=m.notes,
                    items=items_map.get(m.id, []),
                )
            )
        return meals

    @staticmethod
    def suggest_meal_type(dt: datetime) -> str:
        h = dt.hour
        if 5 <= h < 11:
            return MealTypeEnum.breakfast.value
        if 11 <= h < 16:
            return MealTypeEnum.lunch.value
        if 16 <= h < 21:
            return MealTypeEnum.dinner.value
        return MealTypeEnum.snack.value


