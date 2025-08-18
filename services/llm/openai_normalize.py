from __future__ import annotations

from typing import Any, Dict
import structlog

from core.config import settings

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional import guard
    OpenAI = None  # type: ignore


log = structlog.get_logger(__name__)


JSON_SCHEMA: Dict[str, Any] = {
    "name": "normalize_result",
    "schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "category": {
                            "type": "string",
                            "enum": [
                                "protein",
                                "carbohydrate",
                                "fat",
                                "vegetable",
                                "fruit",
                                "dairy",
                                "beverage",
                                "dessert",
                                "other",
                            ],
                        },
                        "unit": {"type": "string", "enum": ["g", "ml", "piece"]},
                        "amount": {"type": "number"},
                        "kcal": {"type": "number"},
                        "protein_g": {"type": "number"},
                        "fat_g": {"type": "number"},
                        "carb_g": {"type": "number"},
                        "confidence": {"type": "number"},
                        "assumptions": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "name",
                        "category",
                        "unit",
                        "amount",
                        "kcal",
                        "protein_g",
                        "fat_g",
                        "carb_g",
                    ],
                    "additionalProperties": False,
                },
            },
            "needs_clarification": {"type": "boolean"},
            "clarifications": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["items", "needs_clarification"],
        "additionalProperties": False,
    },
}


SYSTEM_PROMPT_EN = (
    "You are a nutrition normalizer. Parse the user input into food items with amounts and macronutrients."
    " Output strictly JSON matching the provided schema. If amount is missing or ambiguous, set"
    " needs_clarification=true and include short clarification prompts. Units must be one of g/ml/piece."
)

SYSTEM_PROMPT_RU = (
    "Ты нормализатор рациона. Разбери текст пользователя на позиции с количеством и БЖУ."
    " Верни строго JSON по схеме. Если количество отсутствует или неоднозначно — needs_clarification=true"
    " и добавь короткие вопросы для уточнения. Единицы только g/ml/piece."
)


FEW_SHOTS_RU = [
    "куриная грудка 150 г, рис 120 г, масло 5 г",
    "йогурт 200 мл, банан 1 шт",
]

FEW_SHOTS_EN = [
    "chicken breast 150 g, rice 120 g, oil 5 g",
    "yogurt 200 ml, banana 1 piece",
]


def normalize_with_openai(text: str, locale: str = "ru") -> dict | None:
    if not settings.openai_api_key or OpenAI is None:
        return None
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        system = SYSTEM_PROMPT_RU if locale == "ru" else SYSTEM_PROMPT_EN
        few = FEW_SHOTS_RU if locale == "ru" else FEW_SHOTS_EN
        prompt = (
            f"Examples: {few[0]} | {few[1]}\n"
            f"Input: {text}\n"
            "Respond with JSON only."
        )
        resp = client.responses.create(
            model=settings.openai_model_normalize,
            input=prompt,
            system=system,
            response_format={
                "type": "json_schema",
                "json_schema": JSON_SCHEMA,
            },
        )
        content = resp.output_json()  # type: ignore[attr-defined]
        if isinstance(content, dict) and "items" in content:
            return content
    except Exception as e:  # pragma: no cover - network exceptions
        log.warning("openai_normalize_failed", error=str(e))
    return None


