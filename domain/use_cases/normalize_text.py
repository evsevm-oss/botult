from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional
import json
import hashlib
import re

from infra.cache.redis import redis_client
from core.config import settings
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
        # поддержка форматов: "название N unit", "название Nunit", просто "название"
        def parse_amount_unit_token(tok: str) -> Tuple[Optional[float], Optional[str]]:
            m = re.match(r"^(\d+(?:[\.,]\d+)?)([a-zA-Zа-яА-Я]*)$", tok)
            if not m:
                return None, None
            num = float(m.group(1).replace(",", "."))
            suf = (m.group(2) or "").lower()
            if suf in {"g", "гр", "г", "г.", "gram", "grams"}:  # граммы
                return num, "g"
            if suf in {"kg", "кг"}:  # килограммы → граммы
                return num * 1000.0, "g"
            if suf in {"ml", "мл", "миллилитров"}:  # миллилитры
                return num, "ml"
            if suf in {"pc", "pcs", "шт", "штук"}:
                return num, "piece"
            if suf in {"к"}:  # частый ввод: "200к" → 200 г
                return num, "g"
            # нераспознанный суффикс
            return num, None

        if len(tokens) >= 2:
            amt, unit = parse_amount_unit_token(tokens[-1])
            if amt is not None:
                name = " ".join(tokens[:-1])
                items.append(RawItem(name=name, amount=amt, unit=unit))
                continue
        if len(tokens) >= 3:
            # классический вариант: "название N unit"
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


# Простая база известных продуктов (на 100 г): kкал и макросы
FOOD_DB: dict[str, tuple[float, float, float, float]] = {
    # name_lower: (kcal, protein_g, fat_g, carb_g)
    "капуста": (28.0, 1.8, 0.1, 6.6),
    "котлета": (250.0, 15.0, 18.0, 8.0),  # усреднённо для жареной котлеты
}


def _macros_for_known(name_lower: str) -> Optional[tuple[float, float, float, float]]:
    for key, vals in FOOD_DB.items():
        if key in name_lower:
            return vals
    return None


def _estimate_macros(name_lower: str, amount_g: float) -> tuple[float, float, float, float]:
    """Вернуть (kcal, protein_g, fat_g, carb_g) для массы в граммах по простым эвристикам.

    Фрукты (на 100 г): ~52 ккал, Б 0.5 г, Ж 0.2 г, У 13 г.
    Общий фолбэк: грубое распределение P=15%, F=10%, C=20% от массы.
    """
    known = _macros_for_known(name_lower)
    if known is not None:
        kcal100, p100, f100, c100 = known
        scale = amount_g / 100.0
        return round(kcal100 * scale, 0), round(p100 * scale, 1), round(f100 * scale, 1), round(c100 * scale, 1)
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
    """Эвристическая нормализация без LLM.

    ВАЖНО: больше не используем дефолт 100 г, если масса не указана.
    Такие позиции пропускаем, чтобы не выдавать неверные «100 г ≈ 230 ккал».
    """
    result: List[NormalizedItem] = []
    names = [it.name.strip().lower() for it in raw]
    # Спец-обработка: "капуста, качан" → одна позиция капусты с массой качана по умолчанию
    if any("капуст" in n for n in names) and any("качан" in n for n in names):
        # удалим строку "качан" из сырых и добавим массу качана к капусте
        raw = [it for it in raw if "качан" not in it.name.strip().lower()]
        for it in raw:
            if "капуст" in it.name.strip().lower():
                it.amount = it.amount or 1200.0  # дефолтная масса качана
                it.unit = it.unit or "g"
    for it in raw:
        # Если масса не указана — пропускаем позицию (попросим уточнение на верхнем уровне)
        if it.amount is None:
            continue
        unit = (it.unit or "g").lower()
        if unit in {"гр", "грамм", "г."}:
            unit = "g"
        if unit in {"миллилитров", "мл", "ml"}:
            unit = "ml"
        if unit not in {"g", "ml", "piece"}:
            unit = "g"
        amount = float(it.amount)
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
    # быстрый детект «не еда» для коротких слов без чисел
    t = text.strip()
    if t and not re.search(r"\d", t):
        nl = t.lower()
        maybe_not_food = {"кошка", "кот", "собака", "телефон", "книга", "стол", "окно", "машина"}
        if nl in maybe_not_food:
            return NormalizeOutput(items=[], needs_clarification=True, clarifications=["Похоже, это не еда."])
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
    cacheable = False
    if llm:
        def _canon_unit_and_amount(unit_raw: str, amount_val: float) -> tuple[str, float]:
            u = (unit_raw or "").strip().lower()
            amt = float(amount_val)
            # grams and synonyms
            if u in {"g", "гр", "г", "г.", "gram", "grams"}:
                return "g", amt
            if u in {"kg", "кг"}:
                return "g", amt * 1000.0
            # milliliters and synonyms
            if u in {"ml", "мл", "миллилитров"}:
                return "ml", amt
            if u in {"l", "литр", "литра", "литров", "л"}:
                return "ml", amt * 1000.0
            # spoons → milliliters (approx.)
            if u in {"ч.л.", "ч.л", "tsp", "teaspoon"}:
                return "ml", amt * 5.0
            if u in {"ст.л.", "ст.л", "tbsp", "tablespoon"}:
                return "ml", amt * 15.0
            # piece synonyms (шт)
            if u in {"pc", "pcs", "шт", "штук", "piece", "тарелка", "plate"}:
                return "piece", amt
            # fallback
            return "g", amt

        items_norm: List[NormalizedItem] = []
        for i in llm["items"]:
            unit_raw = i.get("unit")
            amt_raw = i.get("amount", 0)
            unit_c, amount_c = _canon_unit_and_amount(str(unit_raw or ""), float(amt_raw))
            items_norm.append(
                NormalizedItem(
                    name=i["name"],
                    category=i.get("category"),
                    unit=unit_c,
                    amount=float(amount_c),
                    kcal=float(i["kcal"]),
                    protein_g=float(i["protein_g"]),
                    fat_g=float(i["fat_g"]),
                    carb_g=float(i["carb_g"]),
                    confidence=float(i.get("confidence", 0.8)),
                    assumptions=(i.get("assumptions") if isinstance(i.get("assumptions"), list) else ([i.get("assumptions")] if i.get("assumptions") is not None else None)),
                )
            )
        out = NormalizeOutput(
            items=items_norm,
            needs_clarification=bool(llm.get("needs_clarification", False)),
            clarifications=llm.get("clarifications"),
        )
        try:
            await redis_client.incr("metrics:normalize:count")
            await redis_client.incrbyfloat("metrics:normalize:cost_total", settings.openai_cost_normalize_per_req)
        except Exception:
            pass
        # Если пользователь не указывал числа, а модель вернула ровно 100 г —
        # заменим на стандартную порцию по категории/названию, масштабировав БЖУ и ккал.
        if not re.search(r"\d", t):
            def _default_portion(category: str | None, name: str) -> tuple[str, float]:
                n = (name or "").lower()
                cat = (category or "").lower()
                if cat == "fruit":
                    return "g", 150.0
                if cat == "vegetable":
                    return "g", 200.0
                if cat == "protein":
                    return "g", 180.0
                if cat == "carbohydrate":
                    return "g", 150.0
                if cat == "dairy":
                    if any(k in n for k in ["йогурт", "кефир", "milk", "молок", "ряженк"]):
                        return "ml", 200.0
                    return "g", 150.0
                if cat == "dessert":
                    return "g", 60.0
                if cat == "beverage":
                    return "ml", 250.0
                return "g", 150.0

            new_items: List[NormalizedItem] = []
            changed = False
            for it in out.items:
                if it.unit == "g" and abs(it.amount - 100.0) < 1e-6:
                    new_unit, new_amount = _default_portion(it.category, it.name)
                    ratio = new_amount / 100.0
                    it = NormalizedItem(
                        name=it.name,
                        category=it.category,
                        unit=new_unit,
                        amount=new_amount,
                        kcal=round(it.kcal * ratio, 1),
                        protein_g=round(it.protein_g * ratio, 1),
                        fat_g=round(it.fat_g * ratio, 1),
                        carb_g=round(it.carb_g * ratio, 1),
                        confidence=it.confidence,
                        assumptions=(it.assumptions or []) + ["default-portion-applied"],
                    )
                    changed = True
                new_items.append(it)
            if changed:
                out.items = new_items
        cacheable = True
    else:
        # Без ответа от LLM не делаем грубых эвристик по умолчанию.
        # Просим пользователя уточнить массу/объём, чтобы избежать неверного «100 г ≈ 230 ккал».
        raw = parse_text_to_raw_items(text)
        items = normalize_items(raw)
        if items:
            out = NormalizeOutput(items=items, needs_clarification=False, clarifications=None)
        else:
            out = NormalizeOutput(
                items=[],
                needs_clarification=True,
                clarifications=["Уточните массу/объём (например: 150 г, 200 мл или 1 шт)"],
            )

    # Кэшируем только валидные LLM‑ответы, чтобы не залипали эвристики/пустые ответы
    if cacheable:
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


