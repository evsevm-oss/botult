from __future__ import annotations

import asyncio
import os
from typing import Any

from infra.cache.redis import redis_client
from services.vision.queue import QUEUE_KEY, set_status
from services.vision.vision_infer import run_vision_inference
from infra.storage.object_storage import ObjectStorage
from infra.db.session import get_session
from infra.db.repositories.image_repo import ImageRepo
from infra.db.repositories.meal_repo import MealRepo


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
        # Run vision inference (stub)
        try:
            result = await run_vision_inference(path)
            # TODO: persist vision_inferences, attach to meal draft, notify user
            await set_status(int(image_id), "ready")
        except Exception:
            await set_status(int(image_id), "failed")


def run_worker_forever() -> None:
    asyncio.run(worker_loop())


