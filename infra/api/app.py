from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import hmac
import hashlib
from urllib.parse import parse_qsl

from core.config import settings
from domain.use_cases import (
    CalculateBudgetsInput,
    RecalcBudgetsInput,
    calculate_budgets,
    recalc_and_store_daily_budgets,
)
from infra.db.session import get_session
from infra.db.repositories.daily_summary_repo import DailySummaryRepo
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from .schemas import APIResponse, BudgetsSchema, ProfileInputSchema, ProfileDTO
from infra.db.repositories.user_repo import UserRepo
from infra.db.repositories.profile_repo import ProfileRepo


def create_app() -> FastAPI:
    app = FastAPI(title="Ultima Calories API", version="0.1.0")
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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

    @app.post("/api/recalculate", response_model=APIResponse)
    async def recalc(
        payload: ProfileInputSchema,
        user_id: int,
        session: AsyncSession = Depends(get_session),
    ) -> APIResponse:
        repo = DailySummaryRepo(session)
        inp = RecalcBudgetsInput(
            user_id=user_id,
            sex=payload.sex,
            age=payload.age,
            height_cm=payload.height_cm,
            weight_kg=payload.weight_kg,
            activity_level=payload.activity_level,
            goal=payload.goal,
        )
        out = await recalc_and_store_daily_budgets(repo, inp)
        return APIResponse(ok=True, data=BudgetsSchema(**out.__dict__).model_dump())

    @app.get("/api/profile", response_model=APIResponse)
    async def get_profile(telegram_id: int, session: AsyncSession = Depends(get_session)) -> APIResponse:
        users = UserRepo(session)
        profiles = ProfileRepo(session)
        user_id = await users.get_by_telegram_id(telegram_id)
        if user_id is None:
            return APIResponse(ok=True, data=None)
        prof = await profiles.get_by_user_id(user_id)
        return APIResponse(ok=True, data=prof)

    @app.post("/api/profile", response_model=APIResponse)
    async def upsert_profile(
        telegram_id: int,
        payload: ProfileDTO,
        session: AsyncSession = Depends(get_session),
    ) -> APIResponse:
        users = UserRepo(session)
        profiles = ProfileRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        await profiles.upsert_profile(
            user_id=user_id,
            sex=payload.sex,
            birth_date=payload.birth_date,
            height_cm=payload.height_cm,
            weight_kg=payload.weight_kg,
            activity_level=payload.activity_level,
            goal=payload.goal,
        )
        return APIResponse(ok=True, data={"user_id": user_id})

    @app.post("/api/webapp/verify", response_model=APIResponse)
    def webapp_verify(initData: str) -> APIResponse:
        from core.config import settings as cfg
        if not cfg.telegram_bot_token:
            raise HTTPException(status_code=500, detail="Bot token is not configured")
        if verify_init_data(initData, cfg.telegram_bot_token):
            return APIResponse(ok=True, data={"valid": True})
        return APIResponse(ok=False, error={"code": "E_INVALID_INITDATA", "message": "Invalid initData"})

    return app


app = create_app()


def verify_init_data(init_data: str, bot_token: str) -> bool:
    try:
        params = dict(parse_qsl(init_data, keep_blank_values=True))
        hash_value = params.pop("hash", None)
        if not hash_value:
            return False
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
        secret_key = hmac.new("WebAppData".encode(), bot_token.encode(), hashlib.sha256).digest()
        h = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        return h == hash_value
    except Exception:
        return False


