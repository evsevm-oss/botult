from __future__ import annotations

from fastapi import FastAPI

from core.config import settings
from domain.use_cases import CalculateBudgetsInput, calculate_budgets
from .schemas import APIResponse, BudgetsSchema, ProfileInputSchema


def create_app() -> FastAPI:
    app = FastAPI(title="Ultima Calories API", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/budgets", response_model=APIResponse)
    def budgets(payload: ProfileInputSchema) -> APIResponse:
        inp = CalculateBudgetsInput(
            sex=payload.sex,
            age=payload.age,
            height_cm=payload.height_cm,
            weight_kg=payload.weight_kg,
            activity_level=payload.activity_level,
            goal=payload.goal,
        )
        out = calculate_budgets(inp)
        return APIResponse(ok=True, data=BudgetsSchema(**out.__dict__).model_dump())

    return app


app = create_app()


