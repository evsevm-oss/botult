from __future__ import annotations

import asyncio
import os
from typing import Any

from infra.cache.redis import redis_client
from services.vision.queue import QUEUE_KEY, set_status
from services.vision.openai_vision import infer_foods_from_image_bytes
from infra.storage.object_storage import ObjectStorage
from infra.db.session import get_session
from infra.db.repositories.image_repo import ImageRepo
from infra.db.repositories.meal_repo import MealRepo
from infra.db.repositories.vision_inference_repo import VisionInferenceRepo


async def worker_loop(poll_interval: float = 1.0) -> None:
    storage = ObjectStorage()
    while True:
        image_id = await redis_client.lpop(QUEUE_KEY)
        if not image_id:
            await asyncio.sleep(poll_interval)
            continue
        await set_status(int(image_id), "processing")
        # Fetch image info
        async with get_session() as session:  # type: ignore
            repo = ImageRepo(session)
            imgs = await repo.get_by_ids([int(image_id)])
            if not imgs:
                await set_status(int(image_id), "failed")
                continue
            img = imgs[0]
            path = storage.get_path(img["object_key"])
        # Run vision inference via OpenAI
        try:
            with open(path, "rb") as f:
                img_bytes = f.read()
            result = infer_foods_from_image_bytes(img_bytes)
            async with get_session() as session:  # type: ignore
                vrepo = VisionInferenceRepo(session)
                await vrepo.create(image_id=int(image_id), provider="openai", model="gpt-4o-mini", response=result, confidence=result.get("confidence"))
            await set_status(int(image_id), "ready")
        except Exception:
            await set_status(int(image_id), "failed")


def run_worker_forever() -> None:
    asyncio.run(worker_loop())


