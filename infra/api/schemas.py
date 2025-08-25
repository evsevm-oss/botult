from __future__ import annotations

from typing import Literal

from datetime import date, datetime
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
    amount: float = Field(..., gt=0)
    kcal: float = Field(..., ge=0)
    protein_g: float = Field(..., ge=0)
    fat_g: float = Field(..., ge=0)
    carb_g: float = Field(..., ge=0)
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
    amount: float = Field(..., gt=0)
    kcal: float = Field(..., ge=0)
    protein_g: float = Field(..., ge=0)
    fat_g: float = Field(..., ge=0)
    carb_g: float = Field(..., ge=0)


class MealCreate(BaseModel):
    at: datetime
    type: Literal["breakfast", "lunch", "dinner", "snack"] | None = None
    items: list[MealItemIn]
    notes: str | None = None
    status: Literal["draft", "confirmed"] | None = None
    source_chat_id: int | None = None
    source_message_id: int | None = None
    source_update_id: int | None = None


class MealUpdate(BaseModel):
    at: datetime | None = None
    type: Literal["breakfast", "lunch", "dinner", "snack"] | None = None
    items: list[MealItemIn] | None = None
    notes: str | None = None
    status: Literal["draft", "confirmed"] | None = None


class MealOutput(BaseModel):
    id: int
    at: datetime
    type: Literal["breakfast", "lunch", "dinner", "snack"]
    status: Literal["draft", "confirmed"]
    notes: str | None = None
    items: list[MealItemIn]


class UserSettingsDTO(BaseModel):
    # Minimal settings for warnings/preferences; can be extended later
    allergies: list[str] | None = None
    diet_mode: Literal["none", "keto", "vegan", "vegetarian", "low_fat", "high_protein"] | None = None
    preferred_units: Literal["metric", "imperial"] | None = None
    specialist_id: str | None = None
    timezone: str | None = None
    locale: Literal["ru", "en"] | None = None
    notify_enabled: bool | None = None
    notify_times: list[str] | None = None
    comm_channels: dict | None = None  # {journal_reminders: bool, ai_diet: bool, extra_content: bool}
    newsletter_opt_in: bool | None = None
    favorites_enabled: bool | None = None
    allow_personal_recipes: bool | None = None
    export_requested_at: datetime | None = None
    delete_requested_at: datetime | None = None
    communication_mode: Literal["journal_only", "journal_plus_ai", "proactive_ai"] | None = None


# BodyFat
class BodyFatEstimateInput(BaseModel):
    gender: Literal["male", "female", "other"]
    height_cm: float
    weight_kg: float
    waist_cm: float
    neck_cm: float


class BodyFatInput(BaseModel):
    date: date
    percent: float

