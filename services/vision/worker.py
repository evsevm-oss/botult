from __future__ import annotations

import asyncio
import os
from typing import Any

from infra.cache.redis import redis_client
from core.config import settings
from services.vision.queue import QUEUE_KEY, set_status
from services.vision.openai_vision import infer_foods_from_image_bytes, infer_foods_from_images_bytes
from infra.storage.object_storage import ObjectStorage
from infra.db.session import get_session
from infra.db.repositories.image_repo import ImageRepo
from infra.db.repositories.user_settings_repo import UserSettingsRepo
from infra.db.repositories.meal_repo import MealRepo
from infra.db.repositories.vision_inference_repo import VisionInferenceRepo
from services.vision.portion_heuristics import apply_portion_heuristics
from services.vision.qc import validate_items
from services.vision.cache import get_cached_vision, set_cached_vision


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
            user_id_for_img = img.get("user_id")
        # Run vision inference via OpenAI (supports multi‑image aggregation)
        try:
            # TODO: group by media_group_id; for now single image inference
            with open(path, "rb") as f:
                img_bytes = f.read()
            cached = await get_cached_vision(img_bytes)
            if cached:
                result = cached
            else:
                result = infer_foods_from_images_bytes([img_bytes])
                await set_cached_vision(img_bytes, result)
                try:
                    # metrics: cost and counts
                    await redis_client.incr("metrics:vision:count")
                    await redis_client.incrbyfloat("metrics:vision:cost_total", settings.openai_cost_vision_per_image)
                except Exception:
                    pass
            items = result.get("items", [])
            # Load user-specific priors if available
            user_priors = {}
            try:
                if user_id_for_img is not None:
                    async with get_session() as session2:  # type: ignore
                        srepo = UserSettingsRepo(session2)
                        prefs = await srepo.get(int(user_id_for_img)) or {}
                        user_priors = prefs.get("portion_priors") or {}
            except Exception:
                user_priors = {}
            items = apply_portion_heuristics(items, user_priors=user_priors)
            # QC validation and clarifications merge
            qc = validate_items(items)
            quality = result.get("quality") or {}
            merged_quality = {
                "not_food_probability": float(quality.get("not_food_probability", 0.0) or 0.0),
                "unrealistic_scene_probability": float(quality.get("unrealistic_scene_probability", 0.0) or 0.0),
                "needs_clarification": bool(quality.get("needs_clarification", False)) or bool(qc.get("needs_clarification", False)),
                "clarifications": list(set([*(quality.get("clarifications") or []), *(qc.get("clarifications") or [])])),
                "issues": list(set([*(quality.get("issues") or []), *(qc.get("issues") or [])])),
            }
            result["items"] = items
            result["quality"] = merged_quality
            async with get_session() as session:  # type: ignore
                vrepo = VisionInferenceRepo(session)
                await vrepo.create(image_id=int(image_id), provider="openai", model="gpt-4o-mini", response=result, confidence=result.get("confidence"))
            await set_status(int(image_id), "ready")
        except Exception:
            await set_status(int(image_id), "failed")


def run_worker_forever() -> None:
    asyncio.run(worker_loop())


