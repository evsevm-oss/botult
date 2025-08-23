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
                        "sources": {"type": "array", "items": {"type": "string", "enum": ["vision", "text", "voice"]}},
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
            "quality": {
                "type": "object",
                "properties": {
                    "not_food_probability": {"type": "number"},
                    "unrealistic_scene_probability": {"type": "number"},
                    "needs_clarification": {"type": "boolean"},
                    "clarifications": {"type": "array", "items": {"type": "string"}},
                    "issues": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["needs_clarification"],
                "additionalProperties": False,
            },
        },
        "required": ["items", "quality"],
        "additionalProperties": False,
    },
}


# Step 1: Food check prompts
STEP1_PROMPT_EN = (
    "Role: Food input classifier. Determine if the user text is about food and whether it looks realistic.\n"
    "Return JSON only: {is_food: bool, not_food_probability: 0..1, unrealistic_scene_probability: 0..1,"
    " normalized_query: string, category_guess: 'protein|carbohydrate|fat|vegetable|fruit|dairy|beverage|dessert|other|null',"
    " reasons: [string], follow_up: string}. Ignore emojis and noise. Understand kg/g, '200k'→200 g, calories (kcal)."
)

STEP1_PROMPT_RU = (
    "Роль: Классификатор ввода еды. Определи, является ли текст о еде и реалистична ли формулировка.\n"
    "Верни ТОЛЬКО JSON вида: {\"is_food\":bool, \"not_food_probability\":0..1, \"unrealistic_scene_probability\":0..1,"
    " \"normalized_query\":string, \"category_guess\":'protein|carbohydrate|fat|vegetable|fruit|dairy|beverage|dessert|other|null',"
    " \"reasons\":[string], \"follow_up\":string}. Игнорируй эмодзи и шум. Понимай кг/г, '200к'→200 г, калории (ккал)."
)

# Step 2: Normalization prompts (produce items + quality)
STEP2_PROMPT_EN = (
    "Role: Nutrition normalizer. You get user_text and the result of step1 (FoodCheck)."
    " Return items with amount, kcal and macros. If amount is missing, estimate a reasonable portion for the category"
    " and set low confidence with assumptions. If only calories are given, infer mass from typical kcal/100g."
    " Convert kg→g and ml where appropriate. Keep energy consistency: 4*P + 9*F + 4*C ≈ kcal (±12%)."
    " Units only: g|ml|piece. Always reply with JSON: {items:[{name,category,unit,amount,kcal,protein_g,fat_g,carb_g,confidence,sources,assumptions}],"
    " quality:{not_food_probability,unrealistic_scene_probability,needs_clarification,clarifications,issues}}."
)

STEP2_PROMPT_RU = (
    "Роль: Нормализатор питания. На входе user_text и объект шага 1 (FoodCheck)."
    " Верни позиции с массой, калориями и БЖУ. Если масса не указана — оцени стандартную порцию для категории"
    " и отметь assumptions, понизь confidence. Если указаны только калории — оцени массу по типичным ккал/100 г."
    " Конвертируй кг→г, '200к'→200 г, мл при необходимости. Согласуй энергию: 4*Б + 9*Ж + 4*У ≈ ккал (±12%)."
    " Единицы: g|ml|piece. Ответ строго JSON: {items:[{name,category,unit,amount,kcal,protein_g,fat_g,carb_g,confidence,sources,assumptions}],"
    " quality:{not_food_probability,unrealistic_scene_probability,needs_clарification,clarifications,issues}}."
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
        # STEP 1: food check
        step1_sys = STEP1_PROMPT_RU if locale == "ru" else STEP1_PROMPT_EN
        ch1 = client.chat.completions.create(
            model=settings.openai_model_normalize,
            messages=[
                {"role": "system", "content": step1_sys},
                {"role": "user", "content": text},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        import json as _json
        s1_txt = (ch1.choices[0].message.content or "{}").strip()
        try:
            s1 = _json.loads(s1_txt)
        except Exception:
            s1 = {"is_food": True, "not_food_probability": 0.0, "unrealistic_scene_probability": 0.0, "normalized_query": text, "category_guess": None, "reasons": [], "follow_up": ""}

        if not s1.get("is_food", True):
            return {
                "items": [],
                "quality": {
                    "not_food_probability": float(s1.get("not_food_probability", 0.9) or 0.9),
                    "unrealistic_scene_probability": float(s1.get("unrealistic_scene_probability", 0.0) or 0.0),
                    "needs_clarification": True,
                    "clarifications": ["Опишите блюдо или продукт"],
                    "issues": ["not_food"],
                },
            }

        # STEP 2: normalization
        step2_sys = STEP2_PROMPT_RU if locale == "ru" else STEP2_PROMPT_EN
        user_payload = (
            "user_text: " + text + "\n" +
            "check_json: " + _json.dumps(s1, ensure_ascii=False)
        )
        ch2 = client.chat.completions.create(
            model=settings.openai_model_normalize,
            messages=[
                {"role": "system", "content": step2_sys},
                {"role": "user", "content": user_payload},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        s2_txt = (ch2.choices[0].message.content or "{}").strip()
        try:
            content = _json.loads(s2_txt)
        except Exception:
            # Сигнал на уточнение, если вторая стадия дала мусор
            return {
                "items": [],
                "quality": {"not_food_probability": float(s1.get("not_food_probability", 0.0) or 0.0), "unrealistic_scene_probability": float(s1.get("unrealistic_scene_probability", 0.0) or 0.0), "needs_clarification": True, "clarifications": [s1.get("follow_up") or "Уточните массу/объём"], "issues": ["invalid_json"]},
            }

        # Normalize shape
        q = content.get("quality") or {}
        content["quality"] = {
            "not_food_probability": float(q.get("not_food_probability", s1.get("not_food_probability", 0.0)) or 0.0),
            "unrealistic_scene_probability": float(q.get("unrealistic_scene_probability", s1.get("unrealistic_scene_probability", 0.0)) or 0.0),
            "needs_clarification": bool(q.get("needs_clarification", False)),
            "clarifications": list(q.get("clarifications", [])),
            "issues": list(q.get("issues", [])),
        }
        items = []
        for it in content.get("items", []) or []:
            srcs = it.get("sources") or ["text"]
            if not isinstance(srcs, list):
                srcs = ["text"]
            it["sources"] = srcs
            # assumptions must be a list per contract
            a = it.get("assumptions")
            if a is None:
                it["assumptions"] = []
            elif not isinstance(a, list):
                it["assumptions"] = [str(a)]
            items.append(it)
        content["items"] = items
        return content
    except Exception as e:  # pragma: no cover - network exceptions
        log.warning("openai_normalize_failed", error=str(e))
    return None


