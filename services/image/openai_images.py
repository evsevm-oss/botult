from __future__ import annotations

import base64
from pathlib import Path
from typing import Literal

import httpx
from openai import OpenAI

from core.config import settings


ImageSize = Literal["256x256", "512x512", "1024x1024"]


def generate_image_bytes(
    prompt: str,
    *,
    size: ImageSize = "1024x1024",
    model: str = "gpt-image-1",
    api_key: str | None = None,
) -> bytes:
    client = OpenAI(api_key=api_key or settings.openai_api_key)
    result = client.images.generate(model=model, prompt=prompt, size=size)
    image_b64 = result.data[0].b64_json
    return base64.b64decode(image_b64)


def save_image_bytes(image_bytes: bytes, target_path: str | Path) -> Path:
    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(image_bytes)
    return target


def generate_and_save(
    prompt: str,
    target_path: str | Path,
    *,
    size: ImageSize = "1024x1024",
    model: str = "gpt-image-1",
    api_key: str | None = None,
) -> Path:
    data = generate_image_bytes(prompt, size=size, model=model, api_key=api_key)
    return save_image_bytes(data, target_path)


