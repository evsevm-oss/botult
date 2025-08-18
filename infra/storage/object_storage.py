from __future__ import annotations

import os
from typing import Optional

from core.config import settings
from typing import Optional
try:
    import boto3  # type: ignore
except Exception:
    boto3 = None  # optional


class ObjectStorage:
    def __init__(self) -> None:
        # S3/MinIO if configured, else local
        self._use_s3 = bool(settings.s3_endpoint_url and settings.s3_bucket and boto3)
        if self._use_s3:
            self._s3 = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint_url,
                aws_access_key_id=settings.s3_access_key_id,
                aws_secret_access_key=settings.s3_secret_access_key,
            )
            self._bucket = settings.s3_bucket  # type: ignore
        else:
            base_dir = os.path.abspath(os.path.join(os.getcwd(), "data", "objects"))
            os.makedirs(base_dir, exist_ok=True)
            self.base_dir = base_dir

    def put_bytes(self, object_key: str, data: bytes) -> str:
        if self._use_s3:
            self._s3.put_object(Bucket=self._bucket, Key=object_key, Body=data)
            return object_key
        path = os.path.join(self.base_dir, object_key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return object_key

    def get_path(self, object_key: str) -> str:
        if self._use_s3:
            # For S3, download to temp or return signed URL (not implemented here)
            tmp = os.path.join("/tmp", object_key.replace("/", "_"))
            self._s3.download_file(self._bucket, object_key, tmp)
            return tmp
        return os.path.join(self.base_dir, object_key)


