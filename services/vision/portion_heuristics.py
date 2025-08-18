from __future__ import annotations

from typing import Any


def apply_portion_heuristics(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Very rough: if unit missing, default to g and adjust kcal/macros proportionally to 100g baseline
    out: list[dict[str, Any]] = []
    for i in items:
        unit = i.get("unit") or "g"
        amount = float(i.get("amount", 100.0))
        kcal = float(i.get("kcal", 0.0))
        protein = float(i.get("protein_g", 0.0))
        fat = float(i.get("fat_g", 0.0))
        carb = float(i.get("carb_g", 0.0))
        if unit not in {"g", "ml", "piece"}:
            unit = "g"
        if amount <= 0:
            amount = 100.0
        # If kcal likely per 100g (very small numbers), scale up to amount
        scale = amount / 100.0
        if kcal and kcal < 50:
            kcal *= scale
            protein *= scale
            fat *= scale
            carb *= scale
        out.append({
            **i,
            "unit": unit,
            "amount": amount,
            "kcal": round(kcal, 1),
            "protein_g": round(protein, 1),
            "fat_g": round(fat, 1),
            "carb_g": round(carb, 1),
        })
    return out


