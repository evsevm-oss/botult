from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Literal


MealType = Literal["breakfast", "lunch", "dinner", "snack"]


@dataclass
class User:
    id: int
    tg_id: int
    lang: str = "ru"
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Profile:
    user_id: int
    sex: Literal["male", "female"]
    age: int
    height_cm: float
    weight_kg: float
    activity_level: Literal["low", "medium", "high"]
    goal: Literal["lose", "maintain", "gain"]


@dataclass
class MealItem:
    name: str
    amount: float
    unit: Literal["g", "ml", "piece"]
    kcal: float
    protein_g: float
    fat_g: float
    carb_g: float
    confidence: float | None = None


@dataclass
class Meal:
    id: int
    user_id: int
    datetime: datetime
    type: MealType
    items: List[MealItem] = field(default_factory=list)
    notes: str | None = None


