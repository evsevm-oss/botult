from __future__ import annotations

from dataclasses import dataclass


ACTIVITY_MULTIPLIERS = {
    # поддерживаем синонимы
    "sedentary": 1.2,
    "light": 1.375,
    "low": 1.375,
    "moderate": 1.55,
    "medium": 1.55,
    "active": 1.725,
    "high": 1.725,
    "very_high": 1.9,
}


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def bmr_mifflin(sex: str, age: int, height_cm: float, weight_kg: float) -> float:
    sex = sex.lower().strip()
    if sex == "male":
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161


def bmr_katch_mcardle(lean_mass_kg: float) -> float:
    return 370 + 21.6 * lean_mass_kg


def estimate_lbm_from_bf(weight_kg: float, bf_percent: float) -> float:
    bf = clamp(bf_percent, 3.0, 65.0) / 100.0
    return max(0.0, weight_kg * (1.0 - bf))


def tdee_from_activity(bmr: float, activity_level: str) -> float:
    mult = ACTIVITY_MULTIPLIERS.get(activity_level.lower().strip(), 1.55)
    return bmr * mult


def target_kcal_from_goal(tdee: float, goal: str, weekly_rate_percent: float | None = None) -> float:
    goal = goal.lower().strip()
    if goal == "lose":
        # ориентир: 10–25% дефицит; по умолчанию 15%
        if weekly_rate_percent is None:
            deficit = 0.15
        else:
            deficit = clamp(weekly_rate_percent / 100.0 * 7.0 / 5.0, 0.10, 0.25)  # грубая привязка
        return tdee * (1.0 - deficit)
    if goal == "gain":
        # профицит 5–15%, по умолчанию 10%
        surplus = 0.10 if weekly_rate_percent is None else clamp(weekly_rate_percent / 100.0, 0.05, 0.15)
        return tdee * (1.0 + surplus)
    return tdee


@dataclass
class MacroTargets:
    kcal: float
    protein_g: float
    fat_g: float
    carb_g: float


def distribute_macros(
    *,
    weight_kg: float,
    target_kcal: float,
    lbm_kg: float | None = None,
    protein_per_kg_lbm: float = 1.8,
    fat_energy_fraction: float = 0.30,
) -> MacroTargets:
    if lbm_kg is None:
        lbm_kg = weight_kg
    protein_g = clamp(protein_per_kg_lbm, 1.4, 2.4) * lbm_kg
    fat_kcal = clamp(fat_energy_fraction, 0.25, 0.35) * target_kcal
    fat_g = fat_kcal / 9.0
    kcal_from_protein = protein_g * 4.0
    carb_kcal = max(0.0, target_kcal - kcal_from_protein - fat_kcal)
    carb_g = carb_kcal / 4.0
    return MacroTargets(
        kcal=round(target_kcal, 0),
        protein_g=round(protein_g, 0),
        fat_g=round(fat_g, 0),
        carb_g=round(carb_g, 0),
    )


def target_weight_from_bf(
    *,
    current_weight_kg: float,
    current_bf_percent: float,
    target_bf_percent: float,
) -> float:
    """Оценка целевого веса при неизменной тощей массе (LBM)."""
    lbm = estimate_lbm_from_bf(current_weight_kg, current_bf_percent)
    tgt = clamp(target_bf_percent, 3.0, 65.0) / 100.0
    if tgt >= 1.0:
        return current_weight_kg
    return round(lbm / (1.0 - tgt), 1)


