from __future__ import annotations

from dataclasses import dataclass
from typing import List
import json
import hashlib

from infra.cache.redis import redis_client
from services.llm.openai_normalize import normalize_with_openai


@dataclass
class RawItem:
    name: str
    amount: float | None = None
    unit: str | None = None


@dataclass
class NormalizedItem:
    name: str
    category: str | None
    unit: str  # g|ml|piece
    amount: float
    kcal: float
    protein_g: float
    fat_g: float
    carb_g: float
    confidence: float | None = None
    assumptions: List[str] | None = None


@dataclass
class NormalizeOutput:
    items: List[NormalizedItem]
    needs_clarification: bool = False
    clarifications: List[str] | None = None


def parse_text_to_raw_items(text: str) -> List[RawItem]:
    parts = [p.strip() for p in text.replace(";", ",").split(",") if p.strip()]
    items: List[RawItem] = []
    for p in parts:
        tokens = p.split()
        # очень простая эвристика: "название количество единица" или только "название"
        if len(tokens) >= 3:
            try:
                amount = float(tokens[-2].replace(",", "."))
                unit = tokens[-1].lower()
                name = " ".join(tokens[:-2])
                items.append(RawItem(name=name, amount=amount, unit=unit))
                continue
            except ValueError:
                pass
        items.append(RawItem(name=p))
    return items


def _is_fruit(name_lower: str) -> bool:
    fruits = [
        "яблок", "банан", "апельс", "груш", "киви", "персик", "слив",
        "виноград", "гранат", "грейпфрут", "манго", "ананас", "вишн",
        "черешн", "клубник", "малина", "ежевик", "голубик", "черник",
        "абрикос", "дын", "арбуз", "мандарин", "лимон", "лайм", "нектарин",
    ]
    return any(tok in name_lower for tok in fruits)


def _estimate_macros(name_lower: str, amount_g: float) -> tuple[float, float, float, float]:
    """Вернуть (kcal, protein_g, fat_g, carb_g) для массы в граммах по простым эвристикам.

    Фрукты (на 100 г): ~52 ккал, Б 0.5 г, Ж 0.2 г, У 13 г.
    Общий фолбэк: грубое распределение P=15%, F=10%, C=20% от массы.
    """
    if _is_fruit(name_lower):
        kcal = round(0.52 * amount_g, 0)
        protein_g = round(0.005 * amount_g, 1)
        fat_g = round(0.002 * amount_g, 1)
        carb_g = round(0.13 * amount_g, 1)
        return kcal, protein_g, fat_g, carb_g

    protein_g = round(0.15 * amount_g, 1)
    fat_g = round(0.10 * amount_g, 1)
    carb_g = round(0.20 * amount_g, 1)
    kcal = round(protein_g * 4 + fat_g * 9 + carb_g * 4, 0)
    return kcal, protein_g, fat_g, carb_g


def normalize_items(raw: List[RawItem]) -> List[NormalizedItem]:
    result: List[NormalizedItem] = []
    for it in raw:
        unit = (it.unit or "g").lower()
        if unit in {"гр", "грамм", "г."}:
            unit = "g"
        if unit in {"миллилитров", "мл", "ml"}:
            unit = "ml"
        if unit not in {"g", "ml", "piece"}:
            unit = "g"
        amount = it.amount or 100.0
        # Приведём объём к граммам (грубо 1 мл ≈ 1 г)
        amount_g = amount if unit != "ml" else amount
        kcal, protein_g, fat_g, carb_g = _estimate_macros(it.name.lower(), amount_g)
        result.append(
            NormalizedItem(
                name=it.name,
                category=None,
                unit="g" if unit in {"g", "ml"} else unit,
                amount=amount_g if unit in {"g", "ml"} else amount,
                kcal=kcal,
                protein_g=protein_g,
                fat_g=fat_g,
                carb_g=carb_g,
                confidence=0.7 if _is_fruit(it.name.lower()) else 0.5,
                assumptions=["evristic-fruit" if _is_fruit(it.name.lower()) else "evristic-defaults"],
            )
        )
    return result


def _cache_key(text: str, locale: str) -> str:
    h = hashlib.sha256(f"{locale}::{text}".encode()).hexdigest()[:24]
    return f"normalize:{locale}:{h}"


async def normalize_text_async(text: str, locale: str = "ru") -> NormalizeOutput:
    key = _cache_key(text, locale)
    cached = await redis_client.get(key)
    if cached:
        await redis_client.incr("metrics:normalize:cache_hit")
        data = json.loads(cached)
        return NormalizeOutput(
            items=[
                NormalizedItem(
                    name=i["name"],
                    category=i.get("category"),
                    unit=i["unit"],
                    amount=i["amount"],
                    kcal=i["kcal"],
                    protein_g=i["protein_g"],
                    fat_g=i["fat_g"],
                    carb_g=i["carb_g"],
                    confidence=i.get("confidence"),
                    assumptions=i.get("assumptions"),
                )
                for i in data["items"]
            ],
            needs_clarification=data.get("needs_clarification", False),
            clarifications=data.get("clarifications"),
        )

    await redis_client.incr("metrics:normalize:cache_miss")
    llm = normalize_with_openai(text, locale=locale)
    if llm:
        out = NormalizeOutput(
            items=[
                NormalizedItem(
                    name=i["name"],
                    category=i.get("category"),
                    unit=i["unit"],
                    amount=float(i["amount"]),
                    kcal=float(i["kcal"]),
                    protein_g=float(i["protein_g"]),
                    fat_g=float(i["fat_g"]),
                    carb_g=float(i["carb_g"]),
                    confidence=float(i.get("confidence", 0.8)),
                    assumptions=i.get("assumptions"),
                )
                for i in llm["items"]
            ],
            needs_clarification=bool(llm.get("needs_clarification", False)),
            clarifications=llm.get("clarifications"),
        )
    else:
        raw = parse_text_to_raw_items(text)
        items = normalize_items(raw)
        out = NormalizeOutput(items=items, needs_clarification=False, clarifications=None)

    try:
        await redis_client.setex(
            key,
            60 * 60 * 12,
            json.dumps(
                {
                    "items": [i.__dict__ for i in out.items],
                    "needs_clarification": out.needs_clarification,
                    "clarifications": out.clarifications,
                }
            ),
        )
    except Exception:
        pass

    return out


