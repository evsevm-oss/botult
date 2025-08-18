from __future__ import annotations

import os
from typing import Optional

from core.config import settings


class ObjectStorage:
    def __init__(self) -> None:
        # Simple local fallback; if MINIO configured, could extend here
        base_dir = os.path.abspath(os.path.join(os.getcwd(), "data", "objects"))
        os.makedirs(base_dir, exist_ok=True)
        self.base_dir = base_dir

    def put_bytes(self, object_key: str, data: bytes) -> str:
        path = os.path.join(self.base_dir, object_key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return object_key

    def get_path(self, object_key: str) -> str:
        return os.path.join(self.base_dir, object_key)


