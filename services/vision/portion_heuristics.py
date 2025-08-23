from __future__ import annotations

from typing import Any
from pathlib import Path
import json


# Basic portion priors (very small subset; extend incrementally)
_DEFAULT_PRIORS = {
    "pizza": {
        "slice_small_g": 90,
        "slice_medium_g": 120,
        "slice_large_g": 160,
        "whole_30cm_g": 950,
    },
    "egg": {"piece_g": 55},
    "banana": {"piece_g": 130},
    "burger": {"piece_g": 220},
    "sushi_roll": {"piece_g": 30, "roll_8_pcs_g": 240},
    "salad": {"portion_g": 200},
    "soup": {"bowl_ml": 300},
    "meat": {"portion_g": 180},
    "fish": {"portion_g": 180},
    "bakery": {"croissant_g": 60},
}


def _is_likely_per_100g(kcal: float, amount: float) -> bool:
    # Heuristic: if kcal is very small compared to amount, assume per 100g
    return kcal > 0 and kcal < 50 and amount >= 80


def _load_priors() -> dict:
    try:
        root = Path(__file__).resolve().parents[2]
        p = root / "data" / "portion_priors.json"
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return _DEFAULT_PRIORS


def apply_portion_heuristics(items: list[dict[str, Any]], user_priors: dict | None = None) -> list[dict[str, Any]]:
    """Apply simple, explainable portion heuristics to normalize units/amounts and kcal scaling.

    - Default unknown units to grams.
    - If amount <= 0, default to 100 g.
    - If it looks like kcal per 100 g, scale macros by (amount/100).
    - Map common pieces (egg/banana) to grams for consistency.
    """
    priors = _load_priors()
    # merge user overrides if provided
    if user_priors:
        try:
            for k, v in user_priors.items():
                base = priors.get(k) or {}
                if isinstance(base, dict) and isinstance(v, dict):
                    base.update(v)
                    priors[k] = base
        except Exception:
            pass
    out: list[dict[str, Any]] = []
    extras: list[dict[str, Any]] = []
    for i in items:
        name = str(i.get("name") or "").lower()
        unit = i.get("unit") or "g"
        amount = float(i.get("amount", 100.0))
        kcal = float(i.get("kcal", 0.0))
        protein = float(i.get("protein_g", 0.0))
        fat = float(i.get("fat_g", 0.0))
        carb = float(i.get("carb_g", 0.0))

        # Normalize unit
        if unit not in {"g", "ml", "piece"}:
            unit = "g"
        if amount <= 0:
            amount = 100.0

        # Piece→grams conversion for common items
        if unit == "piece":
            if "egg" in name or "яйц" in name:
                grams = (priors.get("egg", {}).get("piece_g") or _DEFAULT_PRIORS["egg"]["piece_g"]) * amount
                unit, amount = "g", grams
            elif "banana" in name or "банан" in name:
                grams = (priors.get("banana", {}).get("piece_g") or _DEFAULT_PRIORS["banana"]["piece_g"]) * amount
                unit, amount = "g", grams
            elif "бургер" in name or "burger" in name:
                grams = (priors.get("burger", {}).get("piece_g") or _DEFAULT_PRIORS["burger"]["piece_g"]) * amount
                unit, amount = "g", grams
            elif "ролл" in name or "roll" in name or "суши" in name:
                grams = (priors.get("sushi_roll", {}).get("piece_g") or _DEFAULT_PRIORS["sushi_roll"]["piece_g"]) * amount
                unit, amount = "g", grams

        # Pizza geometry by diameter in name (e.g., "пицца 30 см"), slice detection
        if ("пицц" in name or "pizza" in name):
            import re, math
            m = re.search(r"(\d{2})\s*см", name)
            if m:
                d_cm = float(m.group(1))
                area_cm2 = math.pi * (d_cm / 2.0) ** 2
                density = float(priors.get("pizza", {}).get("density_g_per_cm2", 0.95) or 0.95)
                whole_g = area_cm2 * density
            else:
                whole_g = float(priors.get("pizza", {}).get("whole_30cm_g", _DEFAULT_PRIORS["pizza"]["whole_30cm_g"]))
            # slices
            slices = 0
            s = re.search(r"(\d+)\s*(кус|slice)", name)
            if s:
                slices = max(1, int(s.group(1)))
            if unit == "piece" and amount >= 1 and slices == 0:
                slices = int(amount)
            if slices > 0:
                grams = whole_g * (slices / 8.0)
                unit, amount = "g", grams
            elif unit == "g" and amount < 50:
                # likely 1 slice without explicit count
                unit, amount = "g", whole_g / 8.0

        # Scale kcal/macros if likely per 100 g
        if _is_likely_per_100g(kcal, amount):
            scale = amount / 100.0
            kcal *= scale
            protein *= scale
            fat *= scale
            carb *= scale

        # Cooking method adjustments (very simple heuristics)
        if ("жарен" in name or "fried" in name) and amount >= 80:
            # add 1 tsp oil per 150 g of product
            import math
            tsp = max(1, math.ceil(amount / 150.0))
            oil_g = 5.0 * tsp
            extras.append({
                "name": "растительное масло (жарка)",
                "unit": "g",
                "amount": round(oil_g, 1),
                "kcal": round(9.0 * oil_g, 1),
                "protein_g": 0.0,
                "fat_g": round(oil_g, 1),
                "carb_g": 0.0,
                "confidence": 0.5,
                "sources": ["heuristic"],
            })
        if ("паниров" in name or "breaded" in name) and amount >= 80:
            crumbs_g = max(10.0, amount * 0.05)
            extras.append({
                "name": "панировка",
                "unit": "g",
                "amount": round(crumbs_g, 1),
                "kcal": round(3.5 * crumbs_g, 1),
                "protein_g": 1.0,
                "fat_g": 0.5,
                "carb_g": round(0.7 * crumbs_g, 1),
                "confidence": 0.4,
                "sources": ["heuristic"],
            })

        out.append({
            **i,
            "unit": unit,
            "amount": round(amount, 1),
            "kcal": round(kcal, 1),
            "protein_g": round(protein, 1),
            "fat_g": round(fat, 1),
            "carb_g": round(carb, 1),
        })
    return out + extras


