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


