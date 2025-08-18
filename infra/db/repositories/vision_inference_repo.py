from __future__ import annotations

from typing import Any

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from infra.db.models import VisionInference


class VisionInferenceRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, image_id: int, provider: str, model: str, response: dict, confidence: float | None = None) -> int:
        res = await self.session.execute(
            insert(VisionInference)
            .values(image_id=image_id, provider=provider, model=model, response=response, confidence=confidence)
            .returning(VisionInference.id)
        )
        vid = int(res.scalar_one())
        await self.session.commit()
        return vid


