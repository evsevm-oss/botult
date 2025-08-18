from __future__ import annotations

from typing import Literal

from datetime import date
from typing import Literal
from pydantic import BaseModel, Field


class ProfileInputSchema(BaseModel):
    sex: Literal["male", "female"] = Field(..., examples=["male"]) 
    age: int = Field(..., ge=10, le=100, examples=[30])
    height_cm: float = Field(..., ge=100, le=230, examples=[180])
    weight_kg: float = Field(..., ge=30, le=250, examples=[80])
    activity_level: Literal["low", "medium", "high"] = Field(..., examples=["medium"]) 
    goal: Literal["lose", "maintain", "gain"] = Field(..., examples=["maintain"]) 


class BudgetsSchema(BaseModel):
    kcal: float
    protein_g: float
    fat_g: float
    carb_g: float


class APIResponse(BaseModel):
    ok: bool = True
    data: dict | None = None
    error: dict | None = None


class ProfileDTO(BaseModel):
    sex: Literal["male", "female"]
    birth_date: date | None = None
    height_cm: float
    weight_kg: float
    activity_level: Literal["low", "medium", "high"]
    goal: Literal["lose", "maintain", "gain"]


class GoalDTO(BaseModel):
    target_type: Literal["weight", "bodyfat"]
    target_value: float
    pace: float | None = None
    active: bool = True


class WeightInput(BaseModel):
    date: date
    weight_kg: float


class NormalizedItem(BaseModel):
    name: str
    category: str | None = None
    unit: Literal["g", "ml", "piece"]
    amount: float
    kcal: float
    protein_g: float
    fat_g: float
    carb_g: float
    confidence: float | None = None
    assumptions: list[str] | None = None


class NormalizeInput(BaseModel):
    text: str = Field(..., min_length=1)
    locale: Literal["ru", "en"] = "ru"
    telegram_id: int | None = None
    allow_ambiguity: bool = False


class NormalizeResponse(BaseModel):
    items: list[NormalizedItem]
    needs_clarification: bool = False
    clarifications: list[str] | None = None


class MealItemIn(BaseModel):
    name: str
    unit: Literal["g", "ml", "piece"]
    amount: float
    kcal: float
    protein_g: float
    fat_g: float
    carb_g: float


class MealCreate(BaseModel):
    at: datetime
    type: Literal["breakfast", "lunch", "dinner", "snack"]
    items: list[MealItemIn]
    notes: str | None = None


