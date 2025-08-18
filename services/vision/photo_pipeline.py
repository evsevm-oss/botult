from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal, Optional

from infra.storage.object_storage import ObjectStorage


@dataclass
class PhotoIn:
    bytes: bytes
    content_type: str
    width: int | None = None
    height: int | None = None


@dataclass
class PhotoResult:
    object_key: str
    sha256: str
    width: int | None
    height: int | None


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_photo(user_id: int, photo: PhotoIn) -> PhotoResult:
    sha = compute_sha256(photo.bytes)
    ext = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }.get(photo.content_type, "bin")
    object_key = f"users/{user_id}/images/{sha[:2]}/{sha}.{ext}"
    storage = ObjectStorage()
    storage.put_bytes(object_key, photo.bytes)
    return PhotoResult(object_key=object_key, sha256=sha, width=photo.width, height=photo.height)


