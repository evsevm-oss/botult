from __future__ import annotations

from typing import Any, List, Dict
import math
import re


def _calc_kcal_from_macros(item: Dict[str, Any]) -> float:
    p = float(item.get("protein_g", 0.0) or 0.0)
    f = float(item.get("fat_g", 0.0) or 0.0)
    c = float(item.get("carb_g", 0.0) or 0.0)
    return 4.0 * p + 9.0 * f + 4.0 * c


def _kcal_per_100g(item: Dict[str, Any]) -> float | None:
    unit = (item.get("unit") or "").lower()
    amount = float(item.get("amount", 0.0) or 0.0)
    kcal = float(item.get("kcal", 0.0) or 0.0)
    if unit == "g" and amount > 0:
        return (kcal / amount) * 100.0
    return None


def _avg_confidence(items: List[Dict[str, Any]]) -> float:
    vals = [float(it.get("confidence", 0.7) or 0.7) for it in items]
    if not vals:
        return 0.0
    return sum(vals) / len(vals)


def validate_items(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    clarifications: List[str] = []
    issues: List[str] = []

    # Energy consistency per item
    for it in items:
        kcal = float(it.get("kcal", 0.0) or 0.0)
        kcal_from_macros = _calc_kcal_from_macros(it)
        base = max(1.0, max(abs(kcal), abs(kcal_from_macros)))
        mismatch = abs(kcal - kcal_from_macros) / base
        if mismatch > 0.25 and max(kcal, kcal_from_macros) > 50:  # ignore tiny values
            issues.append("energy_mismatch")
            clarifications.append(
                f"Проверьте макросы для ‘{it.get('name','') or 'позиции'}’: по формуле 4P+9F+4C≈{round(kcal_from_macros)} ккал, а указано {round(kcal)}."
            )
        k100 = _kcal_per_100g(it)
        if k100 is not None and (k100 < 10 or k100 > 1200):
            issues.append("kcal_per_100g_outlier")
            clarifications.append(
                f"Нестандартная калорийность на 100 г для ‘{it.get('name','')}’ (~{round(k100)} ккал/100г). Уточните массу."
            )

        name = (it.get("name") or "").lower()
        # Pizza diameter / slices
        if ("пицц" in name or "pizza" in name) and not re.search(r"\d{2}\s*см", name):
            clarifications.append("Укажите диаметр пиццы: 25/30/35 см. Сколько кусочков?")
        # Fried oil
        if ("жарен" in name or "fried" in name) and "масло" not in name:
            clarifications.append("Жарили на масле? Выберите: нет / 1 ч.л. / 1 ст.л.")
        # Volume for soups/beverages
        if any(k in name for k in ["суп", "soup", "напит", "juice", "смузи", "чай", "кофе"]) and (it.get("unit") != "ml"):
            clarifications.append("Объём стакана/чаши: 200/300/400 мл?")

    # Scale object suggestion if low confidence overall
    if _avg_confidence(items) < 0.5:
        clarifications.append("Сделайте ещё фото с объектом масштаба (ладонь/вилка/карта), желательно под другим углом.")

    needs = len(clarifications) > 0
    return {
        "not_food_probability": 0.0,  # delegated to vision model
        "unrealistic_scene_probability": 0.0,  # delegated to vision model
        "needs_clarification": needs,
        "clarifications": clarifications,
        "issues": sorted(list(set(issues))),
    }


