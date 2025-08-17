from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal


@dataclass
class MealItemDTO:
    name: str
    amount: float
    unit: Literal["g", "ml", "piece"]
    kcal: float
    protein_g: float
    fat_g: float
    carb_g: float
    confidence: float | None = None


@dataclass
class MealDTO:
    user_id: int
    type: Literal["breakfast", "lunch", "dinner", "snack"]
    items: List[MealItemDTO]


@dataclass
class BudgetsDTO:
    kcal: float
    protein_g: float
    fat_g: float
    carb_g: float


