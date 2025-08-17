from __future__ import annotations

from dataclasses import dataclass
from datetime import date as Date

from domain.calculations import (
    MacroTargets,
    bmr_katch_mcardle,
    bmr_mifflin,
    distribute_macros,
    estimate_lbm_from_bf,
    target_kcal_from_goal,
    tdee_from_activity,
)


@dataclass
class RecalcBudgetsInput:
    user_id: int
    sex: str
    age: int
    height_cm: float
    weight_kg: float
    activity_level: str
    goal: str  # lose|maintain|gain
    bf_percent: float | None = None
    when: Date | None = None  # по умолчанию сегодня


async def recalc_and_store_daily_budgets(
    repo: "DailySummaryWriter",
    inp: RecalcBudgetsInput,
) -> MacroTargets:
    # 1) BMR
    if inp.bf_percent is not None:
        lbm = estimate_lbm_from_bf(inp.weight_kg, inp.bf_percent)
        bmr = bmr_katch_mcardle(lbm)
    else:
        lbm = None
        bmr = bmr_mifflin(inp.sex, inp.age, inp.height_cm, inp.weight_kg)

    # 2) TDEE и целевые калории
    tdee = tdee_from_activity(bmr, inp.activity_level)
    target_kcal = target_kcal_from_goal(tdee, inp.goal)

    # 3) Распределение макросов
    macros = distribute_macros(
        weight_kg=inp.weight_kg, target_kcal=target_kcal, lbm_kg=lbm
    )

    # 4) Сохранить/обновить дневную сводку
    await repo.upsert_daily_summary(
        user_id=inp.user_id,
        on_date=inp.when or Date.today(),
        kcal=macros.kcal,
        protein_g=macros.protein_g,
        fat_g=macros.fat_g,
        carb_g=macros.carb_g,
    )

    return macros


class DailySummaryWriter:
    async def upsert_daily_summary(
        self,
        *,
        user_id: int,
        on_date: Date,
        kcal: float,
        protein_g: float,
        fat_g: float,
        carb_g: float,
    ) -> None:  # pragma: no cover - интерфейс
        raise NotImplementedError


