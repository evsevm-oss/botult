from __future__ import annotations

import base64
import json
from typing import Any

from core.config import settings


VISION_PROMPT = (
    "Роль: Эксперт по распознаванию еды.\n"
    "Задача: Определи блюда/продукты на фото и оцени количество и БЖУ.\n"
    "Верни строго JSON объект вида: {\n"
    "  \"items\": [{\n"
    "    \"name\": string, \"unit\": one of g|ml|piece, \"amount\": number,\n"
    "    \"kcal\": number, \"protein_g\": number, \"fat_g\": number, \"carb_g\": number,\n"
    "    \"confidence\": number (0..1), \"sources\": [\"vision\"]\n"
    "  }...],\n"
    "  \"quality\": {\n"
    "    \"not_food_probability\": number 0..1,\n"
    "    \"unrealistic_scene_probability\": number 0..1,\n"
    "    \"needs_clarification\": boolean,\n"
    "    \"clarifications\": [string],\n"
    "    \"issues\": [string]\n"
    "  }\n"
    "}\n"
    "Правила: Единицы только g/ml/piece. Если масса/объём неясны — оцени разумную порцию и добавь clarifications.\n"
    "Если на фото нет еды — not_food_probability ≥ 0.8. Если сцена выглядит нереалистичной — unrealistic_scene_probability ≥ 0.7."
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
        data = {"items": [], "quality": {"not_food_probability": 0.0, "unrealistic_scene_probability": 0.0, "needs_clarification": True, "clarifications": ["Не удалось распознать блюдо"], "issues": ["parse_error"]}}
    # Post-process: ensure required fields present and sources
    items = []
    for it in data.get("items", []) or []:
        srcs = it.get("sources") or ["vision"]
        if not isinstance(srcs, list):
            srcs = ["vision"]
        items.append({
            "name": it.get("name", ""),
            "unit": it.get("unit", "g"),
            "amount": float(it.get("amount", 100.0)),
            "kcal": float(it.get("kcal", 0.0)),
            "protein_g": float(it.get("protein_g", 0.0)),
            "fat_g": float(it.get("fat_g", 0.0)),
            "carb_g": float(it.get("carb_g", 0.0)),
            "confidence": float(it.get("confidence", 0.0)),
            "sources": srcs,
        })
    quality = data.get("quality") or {}
    quality = {
        "not_food_probability": float(quality.get("not_food_probability", 0.0)),
        "unrealistic_scene_probability": float(quality.get("unrealistic_scene_probability", 0.0)),
        "needs_clarification": bool(quality.get("needs_clarification", False)),
        "clarifications": list(quality.get("clarifications", [])),
        "issues": list(quality.get("issues", [])),
    }
    return {"items": items, "quality": quality}


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
        data = {"items": [], "quality": {"not_food_probability": 0.0, "unrealistic_scene_probability": 0.0, "needs_clarification": True, "clarifications": ["Не удалось распознать блюдо"], "issues": ["parse_error"]}}
    # ensure sources present
    items = []
    for it in data.get("items", []) or []:
        srcs = it.get("sources") or ["vision"]
        if not isinstance(srcs, list):
            srcs = ["vision"]
        items.append({
            "name": it.get("name", ""),
            "unit": it.get("unit", "g"),
            "amount": float(it.get("amount", 100.0)),
            "kcal": float(it.get("kcal", 0.0)),
            "protein_g": float(it.get("protein_g", 0.0)),
            "fat_g": float(it.get("fat_g", 0.0)),
            "carb_g": float(it.get("carb_g", 0.0)),
            "confidence": float(it.get("confidence", 0.0)),
            "sources": srcs,
        })
    quality = data.get("quality") or {}
    quality = {
        "not_food_probability": float(quality.get("not_food_probability", 0.0)),
        "unrealistic_scene_probability": float(quality.get("unrealistic_scene_probability", 0.0)),
        "needs_clarification": bool(quality.get("needs_clarification", False)),
        "clarifications": list(quality.get("clarifications", [])),
        "issues": list(quality.get("issues", [])),
    }
    return {"items": items, "quality": quality}


