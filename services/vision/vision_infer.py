from __future__ import annotations

from typing import Any


async def run_vision_inference(object_path: str) -> dict[str, Any]:
    # Placeholder: integrate OpenAI Vision or similar
    # For now, return a stub result to unblock the pipeline
    return {
        "items": [],
        "needs_clarification": True,
        "clarifications": ["Пока распознавание фото не подключено. Уточните состав вручную."],
        "confidence": 0.0,
    }


