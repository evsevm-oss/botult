from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CalculateBudgetsInput:
    sex: str
    age: int
    height_cm: float
    weight_kg: float
    activity_level: str  # low|medium|high
    goal: str  # lose|maintain|gain


@dataclass
class CalculateBudgetsOutput:
    kcal: float
    protein_g: float
    fat_g: float
    carb_g: float


def _bmr_mifflin(sex: str, age: int, height_cm: float, weight_kg: float) -> float:
    if sex == "male":
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161


def _activity_multiplier(level: str) -> float:
    return {"low": 1.375, "medium": 1.55, "high": 1.725}.get(level, 1.55)


def _goal_adjustment(goal: str) -> float:
    return {"lose": 0.85, "maintain": 1.0, "gain": 1.1}.get(goal, 1.0)


def calculate_budgets(inp: CalculateBudgetsInput) -> CalculateBudgetsOutput:
    bmr = _bmr_mifflin(inp.sex, inp.age, inp.height_cm, inp.weight_kg)
    tdee = bmr * _activity_multiplier(inp.activity_level)
    target_kcal = tdee * _goal_adjustment(inp.goal)

    # Простое распределение БЖУ: белок 1.8 г/кг, жир 0.8 г/кг, остальное углеводы
    protein_g = max(1.4, min(2.2, 1.8)) * inp.weight_kg
    fat_g = max(0.6, min(1.0, 0.8)) * inp.weight_kg
    kcal_from_protein = protein_g * 4
    kcal_from_fat = fat_g * 9
    carb_g = max(0.0, (target_kcal - kcal_from_protein - kcal_from_fat) / 4)

    return CalculateBudgetsOutput(
        kcal=round(target_kcal, 0),
        protein_g=round(protein_g, 0),
        fat_g=round(fat_g, 0),
        carb_g=round(carb_g, 0),
    )


