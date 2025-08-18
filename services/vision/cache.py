from __future__ import annotations

import hashlib
import json
from typing import Any

from infra.cache.redis import redis_client


def _key_for_image_bytes(b: bytes) -> str:
    h = hashlib.sha256(b).hexdigest()[:32]
    return f"vision:img:{h}"


async def get_cached_vision(b: bytes) -> dict | None:
    key = _key_for_image_bytes(b)
    raw = await redis_client.get(key)
    return json.loads(raw) if raw else None


async def set_cached_vision(b: bytes, data: dict[str, Any], ttl_sec: int = 60 * 60 * 6) -> None:
    key = _key_for_image_bytes(b)
    try:
        await redis_client.setex(key, ttl_sec, json.dumps(data))
    except Exception:
        pass


