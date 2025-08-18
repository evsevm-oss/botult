from __future__ import annotations

import base64
import json
from typing import Any

from core.config import settings


VISION_PROMPT = (
    "Распознайте блюдо(а) на фото и верните JSON со списком items: "
    "[{name, amount, unit: g|ml|piece, kcal, protein_g, fat_g, carb_g, confidence}]. "
    "Если есть неопределенность — needs_clarification=true и список clarifications."
)


def infer_foods_from_image_bytes(image_bytes: bytes) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    b64 = base64.b64encode(image_bytes).decode("ascii")
    msgs = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": VISION_PROMPT},
                {"type": "input_image", "image_data": b64},
            ],
        }
    ]
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=msgs,
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    txt = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(txt)
    except Exception:
        data = {"items": [], "needs_clarification": True, "clarifications": ["Не удалось распознать блюдо"]}
    return data


def infer_foods_from_images_bytes(images: list[bytes]) -> dict[str, Any]:
    from openai import OpenAI

    if not images:
        return {"items": [], "needs_clarification": True}
    client = OpenAI(api_key=settings.openai_api_key)
    content = [{"type": "text", "text": VISION_PROMPT}]
    for b in images[:5]:  # cap at 5
        b64 = base64.b64encode(b).decode("ascii")
        content.append({"type": "input_image", "image_data": b64})
    msgs = [{"role": "user", "content": content}]
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=msgs,
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    txt = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(txt)
    except Exception:
        data = {"items": [], "needs_clarification": True}
    return data


