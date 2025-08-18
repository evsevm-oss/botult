from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from infra.cache.redis import redis_client


@dataclass
class VisionTask:
    image_id: int
    user_id: int
    status: Literal["queued", "processing", "ready", "failed"] = "queued"


QUEUE_KEY = "vision:queue"
TASK_KEY = "vision:task:{}"


async def enqueue(task: VisionTask) -> None:
    await redis_client.rpush(QUEUE_KEY, task.image_id)
    await redis_client.hset(TASK_KEY.format(task.image_id), mapping={
        "user_id": task.user_id,
        "status": task.status,
    })


async def set_status(image_id: int, status: str) -> None:
    await redis_client.hset(TASK_KEY.format(image_id), mapping={"status": status})


async def get_status(image_id: int) -> dict | None:
    data = await redis_client.hgetall(TASK_KEY.format(image_id))
    return data or None


