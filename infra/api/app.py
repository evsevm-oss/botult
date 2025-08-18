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
from .schemas import (
    APIResponse,
    BudgetsSchema,
    ProfileInputSchema,
    ProfileDTO,
    GoalDTO,
    WeightInput,
    NormalizeInput,
    NormalizeResponse,
    MealCreate,
    MealUpdate,
    MealOutput,
    UserSettingsDTO,
)
from domain.use_cases.normalize_text import normalize_text_async
from infra.db.repositories.meal_repo import MealRepo
from infra.db.repositories.user_repo import UserRepo
from infra.db.repositories.profile_repo import ProfileRepo
from infra.db.repositories.goal_repo import GoalRepo
from infra.db.repositories.weight_repo import WeightRepo
from infra.db.repositories.user_settings_repo import UserSettingsRepo
from infra.cache.redis import redis_client


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
        settings_repo = UserSettingsRepo(session)
        user_id = await users.get_by_telegram_id(telegram_id)
        if user_id is None:
            return APIResponse(ok=True, data=None)
        prof = await profiles.get_by_user_id(user_id)
        prefs = await settings_repo.get(user_id) or {}
        return APIResponse(ok=True, data={"profile": prof, "settings": prefs})

    @app.post("/api/profile", response_model=APIResponse)
    async def upsert_profile(
        telegram_id: int,
        payload: ProfileDTO,
        session: AsyncSession = Depends(get_session),
    ) -> APIResponse:
        users = UserRepo(session)
        profiles = ProfileRepo(session)
        settings_repo = UserSettingsRepo(session)
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
        # Триггерим пересчет дневных бюджетов на сегодня
        out = await recalc_and_store_daily_budgets(
            DailySummaryRepo(session),
            RecalcBudgetsInput(
                user_id=user_id,
                sex=payload.sex,
                age=30,  # возраст может быть уточнен по birth_date на сервере на следующих этапах
                height_cm=payload.height_cm,
                weight_kg=payload.weight_kg,
                activity_level=payload.activity_level,
                goal=payload.goal,
            ),
        )
        # Ensure settings record exists
        await settings_repo.upsert(user_id, data={})
        return APIResponse(ok=True, data={"user_id": user_id})

    # User settings
    @app.get("/api/settings", response_model=APIResponse)
    async def get_settings(telegram_id: int, session: AsyncSession = Depends(get_session)) -> APIResponse:
        users = UserRepo(session)
        settings_repo = UserSettingsRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        prefs = await settings_repo.get(user_id) or {}
        return APIResponse(ok=True, data=prefs)

    @app.post("/api/settings", response_model=APIResponse)
    async def upsert_settings(telegram_id: int, payload: UserSettingsDTO, session: AsyncSession = Depends(get_session)) -> APIResponse:
        users = UserRepo(session)
        settings_repo = UserSettingsRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        await settings_repo.upsert(user_id, data=payload.model_dump(exclude_none=True))
        return APIResponse(ok=True, data={"ok": True})

    # Goals CRUD
    @app.get("/api/goals", response_model=APIResponse)
    async def list_goals(telegram_id: int, session: AsyncSession = Depends(get_session)) -> APIResponse:
        users = UserRepo(session)
        goals = GoalRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        items = await goals.list_by_user(user_id)
        return APIResponse(ok=True, data={"items": items})

    @app.post("/api/goals", response_model=APIResponse)
    async def create_goal(
        telegram_id: int, payload: GoalDTO, session: AsyncSession = Depends(get_session)
    ) -> APIResponse:
        users = UserRepo(session)
        goals = GoalRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        goal_id = await goals.create(
            user_id=user_id,
            target_type=payload.target_type,
            target_value=payload.target_value,
            pace=payload.pace,
            active=payload.active,
        )
        return APIResponse(ok=True, data={"id": goal_id})

    @app.post("/api/goals/{goal_id}", response_model=APIResponse)
    async def update_goal(
        goal_id: int,
        telegram_id: int,
        payload: GoalDTO,
        session: AsyncSession = Depends(get_session),
    ) -> APIResponse:
        users = UserRepo(session)
        goals = GoalRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        await goals.update_goal(goal_id=goal_id, user_id=user_id, data=payload.model_dump())
        return APIResponse(ok=True, data={"updated": True})

    @app.delete("/api/goals/{goal_id}", response_model=APIResponse)
    async def delete_goal(goal_id: int, telegram_id: int, session: AsyncSession = Depends(get_session)) -> APIResponse:
        users = UserRepo(session)
        goals = GoalRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        await goals.delete_goal(goal_id=goal_id, user_id=user_id)
        return APIResponse(ok=True, data={"deleted": True})

    # Weights
    @app.post("/api/weights", response_model=APIResponse)
    async def add_weight(telegram_id: int, payload: WeightInput, session: AsyncSession = Depends(get_session)) -> APIResponse:
        users = UserRepo(session)
        weights = WeightRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        await weights.add_weight(user_id=user_id, on_date=payload.date, weight_kg=payload.weight_kg)
        # Триггерим пересчет на эту дату
        # Простой подход: используем текущий профиль для рекалькуляции
        prof = await ProfileRepo(session).get_by_user_id(user_id)
        if prof:
            out = await recalc_and_store_daily_budgets(
                DailySummaryRepo(session),
                RecalcBudgetsInput(
                    user_id=user_id,
                    sex=prof["sex"],
                    age=30,
                    height_cm=prof["height_cm"],
                    weight_kg=payload.weight_kg,
                    activity_level=prof["activity_level"],
                    goal=prof["goal"],
                    when=payload.date,
                ),
            )
        # Вернем актуальные бюджеты на дату, если есть
        ds = await DailySummaryRepo(session).get_by_user_date(user_id=user_id, on_date=payload.date)
        return APIResponse(ok=True, data={"ok": True, "budgets": ds})

    # Meals CRUD (subset)
    @app.get("/api/meals", response_model=APIResponse)
    async def list_meals(telegram_id: int, date: str, session: AsyncSession = Depends(get_session)) -> APIResponse:
        users = UserRepo(session)
        repo = MealRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        on_date = date  # YYYY-MM-DD
        from datetime import date as D
        meals = await repo.list_by_date(user_id=user_id, on_date=D.fromisoformat(on_date))
        return APIResponse(ok=True, data={"items": meals})

    @app.post("/api/meals", response_model=APIResponse)
    async def create_meal(telegram_id: int, payload: MealCreate, session: AsyncSession = Depends(get_session)) -> APIResponse:
        users = UserRepo(session)
        repo = MealRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        # transactional create + summary recompute
        # transactional section below uses autocommit=False and explicit session.commit()
        from datetime import date as D
        d = D.fromisoformat(payload.at.date().isoformat())
        try:
            meal_id = await repo.create_meal(
                user_id=user_id,
                at=payload.at,
                meal_type=payload.type or MealRepo.suggest_meal_type(payload.at),
                items=[i.model_dump() for i in payload.items],
                notes=payload.notes,
                status=payload.status or "draft",
                source_chat_id=payload.source_chat_id,
                source_message_id=payload.source_message_id,
                source_update_id=payload.source_update_id,
                autocommit=False,
            )
        except Exception as e:
            from sqlalchemy.exc import IntegrityError
            if isinstance(e, IntegrityError):
                await session.rollback()
                raise HTTPException(status_code=409, detail="E_DUPLICATE_MEAL_SOURCE")
            raise
        sums = await repo.sum_macros_for_date(user_id=user_id, on_date=d)
        await DailySummaryRepo(session).upsert_daily_summary(
            user_id=user_id, on_date=d, kcal=sums["kcal"], protein_g=sums["protein_g"], fat_g=sums["fat_g"], carb_g=sums["carb_g"], autocommit=False
        )
        await session.commit()
        # metrics
        try:
            await redis_client.incr("metrics:meals:create")
            await redis_client.incr("metrics:meals:total")
            if (payload.status or "draft") == "confirmed":
                await redis_client.incr("metrics:meals:confirmed")
        except Exception:
            pass
        # warnings based on user settings
        warnings: list[str] = []
        try:
            prefs = await UserSettingsRepo(session).get(user_id) or {}
            if prefs:
                lower_items = " ".join([i.model_dump()["name"].lower() for i in payload.items])
                for allergen in (prefs.get("allergies") or []):
                    if isinstance(allergen, str) and allergen.lower() in lower_items:
                        warnings.append(f"Предупреждение: найден аллерген — {allergen}")
                diet = prefs.get("diet_mode")
                if diet in {"vegan", "vegetarian", "keto", "low_fat"}:
                    # очень грубые эвристики
                    banned = {
                        "vegan": ["молоко", "сыр", "яйц", "мяс", "рыб"],
                        "vegetarian": ["мяс", "рыб"],
                        "keto": ["сахар", "слад", "хлеб", "круп", "рис", "макарон"],
                        "low_fat": ["масло", "жир", "сливк"],
                    }[diet]
                    if any(b in lower_items for b in banned):
                        warnings.append("Блюдо может противоречить выбранному режиму питания")
        except Exception:
            pass
        return APIResponse(ok=True, data={"id": meal_id, "warnings": warnings or None})

    @app.get("/api/meals/{meal_id}", response_model=APIResponse)
    async def get_meal(meal_id: int, telegram_id: int, session: AsyncSession = Depends(get_session)) -> APIResponse:
        users = UserRepo(session)
        repo = MealRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        meal = await repo.get_by_id(meal_id=meal_id, user_id=user_id)
        if not meal:
            raise HTTPException(status_code=404, detail="Meal not found")
        return APIResponse(ok=True, data=meal)

    @app.patch("/api/meals/{meal_id}", response_model=APIResponse)
    async def update_meal(meal_id: int, telegram_id: int, payload: MealUpdate, session: AsyncSession = Depends(get_session)) -> APIResponse:
        from datetime import datetime as DT
        users = UserRepo(session)
        repo = MealRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        # transactional update + summary recompute
        from datetime import date as D
        d = D.fromisoformat((payload.at or DT.utcnow()).date().isoformat())
        try:
            await repo.update_meal(
                meal_id=meal_id,
                user_id=user_id,
                at=payload.at,
                meal_type=payload.type,
                status=payload.status,
                items=[i.model_dump() for i in payload.items] if payload.items is not None else None,
                notes=payload.notes,
                autocommit=False,
            )
        except Exception as e:
            from sqlalchemy.exc import IntegrityError
            if isinstance(e, IntegrityError):
                await session.rollback()
                raise HTTPException(status_code=409, detail="E_DUPLICATE_MEAL_SOURCE")
            raise
        sums = await repo.sum_macros_for_date(user_id=user_id, on_date=d)
        await DailySummaryRepo(session).upsert_daily_summary(
            user_id=user_id, on_date=d, kcal=sums["kcal"], protein_g=sums["protein_g"], fat_g=sums["fat_g"], carb_g=sums["carb_g"], autocommit=False
        )
        await session.commit()
        # metrics
        try:
            await redis_client.incr("metrics:meals:update")
            # confirm ratio if became confirmed
            after = await repo.get_by_id(meal_id=meal_id, user_id=user_id)
            if after and after.get("status") == "confirmed":
                await redis_client.incr("metrics:meals:confirmed")
        except Exception:
            pass
        # warnings
        warnings: list[str] = []
        try:
            prefs = await UserSettingsRepo(session).get(user_id) or {}
            if prefs and payload.items:
                lower_items = " ".join([i.model_dump()["name"].lower() for i in payload.items])
                for allergen in (prefs.get("allergies") or []):
                    if isinstance(allergen, str) and allergen.lower() in lower_items:
                        warnings.append(f"Предупреждение: найден аллерген — {allergen}")
        except Exception:
            pass
        return APIResponse(ok=True, data={"updated": True, "warnings": warnings or None})

    @app.delete("/api/meals/{meal_id}", response_model=APIResponse)
    async def delete_meal(meal_id: int, telegram_id: int, session: AsyncSession = Depends(get_session)) -> APIResponse:
        users = UserRepo(session)
        repo = MealRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        from datetime import date as D
        # get date before delete to recompute
        m = await repo.get_by_id(meal_id=meal_id, user_id=user_id)
        await repo.delete_meal(meal_id=meal_id, user_id=user_id, autocommit=False)
        if m:
            d = D.fromisoformat(m["at"][:10])
            sums = await repo.sum_macros_for_date(user_id=user_id, on_date=d)
            await DailySummaryRepo(session).upsert_daily_summary(
                user_id=user_id, on_date=d, kcal=sums["kcal"], protein_g=sums["protein_g"], fat_g=sums["fat_g"], carb_g=sums["carb_g"], autocommit=False
            )
        await session.commit()
        try:
            await redis_client.incr("metrics:meals:delete")
        except Exception:
            pass
        return APIResponse(ok=True, data={"deleted": True})

    @app.post("/api/webapp/verify", response_model=APIResponse)
    def webapp_verify(initData: str) -> APIResponse:
        from core.config import settings as cfg
        if not cfg.telegram_bot_token:
            raise HTTPException(status_code=500, detail="Bot token is not configured")
        if verify_init_data(initData, cfg.telegram_bot_token):
            return APIResponse(ok=True, data={"valid": True})
        return APIResponse(ok=False, error={"code": "E_INVALID_INITDATA", "message": "Invalid initData"})

    # Stage 7: normalization endpoint (text based MVP)
    @app.post("/api/normalize", response_model=NormalizeResponse)
    async def normalize(payload: NormalizeInput) -> NormalizeResponse:
        out = await normalize_text_async(payload.text, locale=payload.locale)
        return NormalizeResponse(**out.__dict__)

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


