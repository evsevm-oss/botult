from __future__ import annotations

from typing import Any

from sqlalchemy import insert, select
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

    async def get_latest_by_image(self, *, image_id: int) -> dict | None:
        res = await self.session.execute(
            select(VisionInference).where(VisionInference.image_id == image_id).order_by(VisionInference.id.desc()).limit(1)
        )
        row = res.scalars().first()
        if not row:
            return None
        return {
            "id": row.id,
            "image_id": row.image_id,
            "provider": row.provider,
            "model": row.model,
            "response": row.response,
            "confidence": row.confidence,
        }


