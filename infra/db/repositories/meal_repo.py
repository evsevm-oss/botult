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
        status: str | None = None,
        source_chat_id: int | None = None,
        source_message_id: int | None = None,
        source_update_id: int | None = None,
        autocommit: bool = True,
    ) -> int:
        res = await self.session.execute(
            insert(Meal)
            .values(
                user_id=user_id,
                at=at,
                type=meal_type,
                status=status or 'draft',
                notes=notes,
                source_chat_id=source_chat_id,
                source_message_id=source_message_id,
                source_update_id=source_update_id,
            )
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
        if autocommit:
            await self.session.commit()
        return meal_id

    async def delete_meal(self, *, meal_id: int, user_id: int, autocommit: bool = True) -> None:
        await self.session.execute(delete(MealItem).where(MealItem.meal_id == meal_id))
        await self.session.execute(delete(Meal).where(Meal.id == meal_id, Meal.user_id == user_id))
        if autocommit:
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
                    status=m.status,
                    notes=m.notes,
                    items=items_map.get(m.id, []),
                )
            )
        return meals

    async def get_by_id(self, *, meal_id: int, user_id: int) -> dict[str, Any] | None:
        res = await self.session.execute(select(Meal).where(Meal.id == meal_id, Meal.user_id == user_id))
        m = res.scalar_one_or_none()
        if not m:
            return None
        res_it = await self.session.execute(select(MealItem).where(MealItem.meal_id == meal_id))
        items = [
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
            for it in res_it.scalars().all()
        ]
        return dict(id=m.id, at=m.at.isoformat(), type=m.type, status=m.status, notes=m.notes, items=items)

    async def update_meal(
        self,
        *,
        meal_id: int,
        user_id: int,
        at: datetime | None = None,
        meal_type: str | None = None,
        status: str | None = None,
        items: Iterable[dict[str, Any]] | None = None,
        notes: str | None = None,
        autocommit: bool = True,
    ) -> None:
        # update meal row
        values: dict[str, Any] = {}
        if at is not None:
            values["at"] = at
        if meal_type is not None:
            values["type"] = meal_type
        if status is not None:
            values["status"] = status
        if notes is not None:
            values["notes"] = notes
        if values:
            from sqlalchemy import update
            await self.session.execute(update(Meal).where(Meal.id == meal_id, Meal.user_id == user_id).values(**values))
        if items is not None:
            await self.session.execute(delete(MealItem).where(MealItem.meal_id == meal_id))
            if items:
                await self.session.execute(insert(MealItem).values([
                    dict(
                        meal_id=meal_id,
                        name=i["name"],
                        amount=float(i["amount"]),
                        unit=i["unit"],
                        kcal=float(i["kcal"]),
                        protein_g=float(i["protein_g"]),
                        fat_g=float(i["fat_g"]),
                        carb_g=float(i["carb_g"]),
                        source=i.get("source", "manual"),
                    ) for i in items
                ]))
        if autocommit:
            await self.session.commit()

    async def sum_macros_for_date(self, *, user_id: int, on_date: Date) -> dict[str, float]:
        start = datetime.combine(on_date, datetime.min.time()).astimezone()
        end = datetime.combine(on_date, datetime.max.time()).astimezone()
        from sqlalchemy import func, and_
        from infra.db.models import Meal, MealItem
        res = await self.session.execute(
            select(
                func.coalesce(func.sum(MealItem.kcal), 0.0),
                func.coalesce(func.sum(MealItem.protein_g), 0.0),
                func.coalesce(func.sum(MealItem.fat_g), 0.0),
                func.coalesce(func.sum(MealItem.carb_g), 0.0),
            )
            .select_from(MealItem)
            .join(Meal, Meal.id == MealItem.meal_id)
            .where(and_(Meal.user_id == user_id, Meal.at >= start, Meal.at <= end))
        )
        row = res.first()
        kcal, protein, fat, carb = (float(row[0]), float(row[1]), float(row[2]), float(row[3])) if row else (0.0, 0.0, 0.0, 0.0)
        return {"kcal": kcal, "protein_g": protein, "fat_g": fat, "carb_g": carb}

    async def find_by_source(
        self,
        *,
        user_id: int,
        source_chat_id: int | None = None,
        source_message_id: int | None = None,
        source_update_id: int | None = None,
    ) -> dict[str, Any] | None:
        q = select(Meal).where(Meal.user_id == user_id)
        if source_update_id is not None:
            q = q.where(Meal.source_update_id == source_update_id)
        if source_chat_id is not None and source_message_id is not None:
            q = q.where(Meal.source_chat_id == source_chat_id, Meal.source_message_id == source_message_id)
        res = await self.session.execute(q)
        m = res.scalar_one_or_none()
        if not m:
            return None
        return {"id": m.id}

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


