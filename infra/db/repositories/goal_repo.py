from __future__ import annotations

from typing import Any

from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from infra.db.models import Goal


class GoalRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_user(self, user_id: int) -> list[dict[str, Any]]:
        stmt = select(Goal).where(Goal.user_id == user_id).order_by(Goal.id.desc())
        res = await self.session.execute(stmt)
        return [self._row_to_dict(row.Goal) for row in res]

    async def create(
        self,
        *,
        user_id: int,
        target_type: str,
        target_value: float,
        pace: float | None,
        active: bool = True,
    ) -> int:
        if active:
            # make others inactive
            await self.session.execute(
                update(Goal).where(Goal.user_id == user_id).values(active=False)
            )
        res = await self.session.execute(
            insert(Goal)
            .values(
                user_id=user_id,
                target_type=target_type,
                target_value=target_value,
                pace=pace,
                active=active,
            )
            .returning(Goal.id)
        )
        await self.session.commit()
        return int(res.scalar_one())

    async def update_goal(
        self,
        *,
        goal_id: int,
        user_id: int,
        data: dict[str, Any],
    ) -> None:
        allowed = {k: v for k, v in data.items() if k in {"target_type", "target_value", "pace", "active"}}
        if not allowed:
            return
        if allowed.get("active") is True:
            await self.session.execute(
                update(Goal).where(Goal.user_id == user_id).values(active=False)
            )
        await self.session.execute(
            update(Goal).where(Goal.id == goal_id, Goal.user_id == user_id).values(**allowed)
        )
        await self.session.commit()

    async def delete_goal(self, *, goal_id: int, user_id: int) -> None:
        await self.session.execute(delete(Goal).where(Goal.id == goal_id, Goal.user_id == user_id))
        await self.session.commit()

    def _row_to_dict(self, g: Goal) -> dict[str, Any]:
        return {
            "id": g.id,
            "user_id": g.user_id,
            "target_type": g.target_type,
            "target_value": g.target_value,
            "pace": g.pace,
            "active": g.active,
        }


