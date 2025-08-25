from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
import hmac
import hashlib
from urllib.parse import parse_qsl
from sqlalchemy import select, func  # global import for query builders

from core.config import settings
from domain.use_cases import (
    CalculateBudgetsInput,
    RecalcBudgetsInput,
    calculate_budgets,
    recalc_and_store_daily_budgets,
)
from infra.db.session import get_session
from infra.db.repositories.daily_summary_repo import DailySummaryRepo
from fastapi import Depends, Request, Body
import asyncio
import time
import structlog
from zoneinfo import ZoneInfo
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
    NormalizedItem,
    MealCreate,
    MealUpdate,
    MealOutput,
    UserSettingsDTO,
    BodyFatEstimateInput,
    BodyFatInput,
)
from domain.use_cases.normalize_text import normalize_text_async
from infra.db.repositories.meal_repo import MealRepo
from infra.db.repositories.user_repo import UserRepo
from infra.db.repositories.profile_repo import ProfileRepo
from infra.db.repositories.goal_repo import GoalRepo
from infra.db.repositories.weight_repo import WeightRepo
from infra.db.repositories.user_settings_repo import UserSettingsRepo
import uuid as _uuid
from infra.cache.redis import redis_client
from fastapi import Response
import json as _json
from services.vision.photo_pipeline import save_photo, PhotoIn
from services.vision.processing import preprocess_photo
from services.vision.queue import enqueue as enqueue_vision, VisionTask, get_status as get_vision_status
from infra.db.repositories.image_repo import ImageRepo
from infra.cache.redis import redis_client as _redis
from aiogram import Bot as TgBot
from aiogram.types import BufferedInputFile


def create_app() -> FastAPI:
    app = FastAPI(title="Ultima Calories API", version="0.1.0")
    log = structlog.get_logger("api")
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Serve built WebApp (Vite) if present
    try:
        project_root = Path(__file__).resolve().parents[2]
        webapp_dist = project_root / "webapp" / "dist"
        if webapp_dist.exists():
            app.mount("/webapp", StaticFiles(directory=str(webapp_dist), html=True), name="webapp")
    except Exception:
        # optional mount; ignore failures
        pass

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        # Apply CSP for WebApp pages only
        if str(request.url.path).startswith("/webapp"):
            csp = (
                "default-src 'self'; "
                "img-src 'self' data: blob: https://*.telegram.org; "
                "script-src 'self' 'unsafe-inline' https://telegram.org https://*.telegram.org; "
                "style-src 'self' 'unsafe-inline'; "
                "connect-src 'self' https://*.telegram.org; "
                "font-src 'self' data:; "
                "object-src 'none'"
            )
            response.headers["Content-Security-Policy"] = csp
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
            # Disable caching of HTML to avoid stale index.html in Telegram WebView (mobile)
            ct = (response.headers.get("content-type") or "").lower()
            if "text/html" in ct:
                response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
        return response

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
        meals_repo = MealRepo(session)
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
        incoming = payload.model_dump(exclude_none=True)
        # Merge with existing prefs to avoid dropping other keys
        current = await settings_repo.get(user_id) or {}
        current.update(incoming)
        await settings_repo.upsert(user_id, data=current)
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
    @app.get("/api/weights", response_model=APIResponse)
    async def list_weights(
        telegram_id: int,
        start: str | None = None,
        end: str | None = None,
        session: AsyncSession = Depends(get_session),
    ) -> APIResponse:
        users = UserRepo(session)
        wrepo = WeightRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        from datetime import date as D, timedelta
        s = D.fromisoformat(start) if start else (D.today() - timedelta(days=30))
        e = D.fromisoformat(end) if end else D.today()
        items = await wrepo.list_between(user_id=user_id, start=s, end=e)
        return APIResponse(ok=True, data={"items": items})
    # Body fat
    @app.post("/api/bodyfat/estimate", response_model=APIResponse)
    def bodyfat_estimate(telegram_id: int, payload: BodyFatEstimateInput) -> APIResponse:
        # Navy tape method (approximate, consistent with UI)
        import math
        h_in = payload.height_cm / 2.54
        w_in = payload.waist_cm / 2.54
        n_in = payload.neck_cm / 2.54
        if h_in <= 0:
            raise HTTPException(status_code=400, detail="E_INVALID_INPUT")
        if payload.gender == 'female':
            weight_lb = payload.weight_kg * 2.2046226218
            if w_in <= 0 or weight_lb <= 0:
                raise HTTPException(status_code=400, detail="E_INVALID_INPUT")
            bf = ((w_in * 4.15) - (weight_lb * 0.082) - 76.76) / weight_lb * 100
        else:
            if (w_in - n_in) <= 0:
                raise HTTPException(status_code=400, detail="E_INVALID_INPUT")
            bf = 86.010 * (math.log10(w_in - n_in)) - 70.041 * (math.log10(h_in)) + 36.76
        return APIResponse(ok=True, data={"percent": float(bf)})

    @app.post("/api/bodyfat", response_model=APIResponse)
    async def bodyfat_save(telegram_id: int, payload: BodyFatInput, session: AsyncSession = Depends(get_session)) -> APIResponse:
        users = UserRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        # Store daily bodyfat in user_settings as per-day map + keep last_bodyfat
        settings_repo = UserSettingsRepo(session)
        current = await settings_repo.get(user_id) or {}
        # per-day map
        bf_map = dict(current.get("bodyfat_by_date") or {})
        bf_map[payload.date.isoformat()] = float(payload.percent)
        current["bodyfat_by_date"] = bf_map
        current["last_bodyfat"] = {"date": payload.date.isoformat(), "percent": float(payload.percent)}
        await settings_repo.upsert(user_id, data=current)
        return APIResponse(ok=True, data={"ok": True})

    @app.get("/api/bodyfat", response_model=APIResponse)
    async def bodyfat_list(
        telegram_id: int,
        start: str | None = None,
        end: str | None = None,
        session: AsyncSession = Depends(get_session),
    ) -> APIResponse:
        users = UserRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        settings_repo = UserSettingsRepo(session)
        current = await settings_repo.get(user_id) or {}
        bf_map: dict[str, float] = current.get("bodyfat_by_date") or {}
        from datetime import date as D, timedelta
        if start:
            s = D.fromisoformat(start)
        else:
            s = D.today() - timedelta(days=6)
        if end:
            e = D.fromisoformat(end)
        else:
            e = D.today()
        items: list[dict] = []
        d = s
        while d <= e:
            iso = d.isoformat()
            if iso in bf_map:
                items.append({"date": iso, "percent": float(bf_map[iso])})
            d = d + timedelta(days=1)
        return APIResponse(ok=True, data={"items": items})

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
    async def list_meals(telegram_id: int, date: str, tz: str | None = None, session: AsyncSession = Depends(get_session)) -> APIResponse:
        users = UserRepo(session)
        repo = MealRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        from datetime import date as D, datetime as DT
        tzname = tz or "UTC"
        z = ZoneInfo(tzname)
        local_date = D.fromisoformat(date)
        start_local = DT.combine(local_date, DT.min.time()).replace(tzinfo=z)
        end_local = DT.combine(local_date, DT.max.time()).replace(tzinfo=z)
        start_utc = start_local.astimezone(ZoneInfo("UTC"))
        end_utc = end_local.astimezone(ZoneInfo("UTC"))
        meals = await repo.list_between(user_id=user_id, start=start_utc, end=end_utc)
        return APIResponse(ok=True, data={"items": meals})

    @app.post("/api/meals", response_model=APIResponse)
    async def create_meal(telegram_id: int, payload: MealCreate, request: Request, tz: str | None = None, session: AsyncSession = Depends(get_session)) -> APIResponse:
        users = UserRepo(session)
        repo = MealRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        # transactional create + summary recompute
        # transactional section below uses autocommit=False and explicit session.commit()
        from datetime import date as D
        # Determine local date for summary using provided tz (default Europe/Madrid).
        try:
            tzname = tz or "Europe/Madrid"
            from zoneinfo import ZoneInfo as _ZI
            dt = payload.at
            if dt.tzinfo is None:
                # assume UTC if naive
                from datetime import timezone as _tz
                dt = dt.replace(tzinfo=_tz.utc)
            d = dt.astimezone(_ZI(tzname)).date()
        except Exception:
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
        sums = await repo.sum_macros_for_date(user_id=user_id, on_date=d, tz=(tz or "Europe/Madrid"))
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
            await redis_client.incrbyfloat("metrics:meals:items_total", float(sum(len(payload.items) for _ in [0])))
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
    async def update_meal(meal_id: int, telegram_id: int, payload: MealUpdate, request: Request, session: AsyncSession = Depends(get_session)) -> APIResponse:
        from datetime import datetime as DT
        users = UserRepo(session)
        repo = MealRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        # transactional update + summary recompute
        from datetime import date as D
        # get previous meal date for recompute
        prev = await repo.get_by_id(meal_id=meal_id, user_id=user_id)
        prev_d: D | None = None
        if prev:
            prev_d = D.fromisoformat(prev["at"][:10])
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
        if prev_d and prev_d != d:
            sums_prev = await repo.sum_macros_for_date(user_id=user_id, on_date=prev_d)
            await DailySummaryRepo(session).upsert_daily_summary(
                user_id=user_id, on_date=prev_d, kcal=sums_prev["kcal"], protein_g=sums_prev["protein_g"], fat_g=sums_prev["fat_g"], carb_g=sums_prev["carb_g"], autocommit=False
            )
        await session.commit()
        # metrics
        try:
            await redis_client.incr("metrics:meals:update")
            # confirm ratio if became confirmed
            after = await repo.get_by_id(meal_id=meal_id, user_id=user_id)
            if after and after.get("status") == "confirmed":
                await redis_client.incr("metrics:meals:confirmed")
            if payload.items is not None:
                await redis_client.incrbyfloat("metrics:meals:items_total", float(len(payload.items)))
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
    async def delete_meal(meal_id: int, telegram_id: int, request: Request, session: AsyncSession = Depends(get_session)) -> APIResponse:
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
        # log trace
        xtrace = request.headers.get("X-Trace-Id")
        if xtrace:
            log.bind(trace_id=xtrace).info("meal_deleted", meal_id=meal_id)
        try:
            await redis_client.incr("metrics:meals:delete")
        except Exception:
            pass
        return APIResponse(ok=True, data={"deleted": True})

    @app.post("/api/webapp/verify", response_model=APIResponse)
    async def webapp_verify(initData: str = Body(..., embed=True), session: AsyncSession = Depends(get_session)) -> APIResponse:
        from core.config import settings as cfg
        if not cfg.telegram_bot_token:
            raise HTTPException(status_code=500, detail="Bot token is not configured")
        if not verify_init_data(initData, cfg.telegram_bot_token):
            return APIResponse(ok=False, error={"code": "E_INVALID_INITDATA", "message": "Invalid initData"})
        # Parse initData to extract user info
        from urllib.parse import parse_qsl
        params = dict(parse_qsl(initData, keep_blank_values=True))
        import json as _json
        user = None
        try:
            if "user" in params:
                user = _json.loads(params["user"])  # telegram user object
        except Exception:
            user = None
        telegram_id = int((user or {}).get("id") or 0)
        if telegram_id <= 0:
            return APIResponse(ok=False, error={"code": "E_NO_USER", "message": "No user in initData"})
        # Ensure local user exists
        users = UserRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        # Issue short‑lived JWT
        import time
        import jwt
        now = int(time.time())
        exp = now + int(settings.webapp_jwt_ttl_minutes) * 60
        claims = {"sub": str(user_id), "tid": telegram_id, "iat": now, "exp": exp, "scope": "webapp"}
        token = jwt.encode(claims, settings.webapp_jwt_secret, algorithm="HS256")
        return APIResponse(ok=True, data={"token": token, "exp": exp})

    @app.post("/api/webapp/refresh", response_model=APIResponse)
    def webapp_refresh(token: str = Body(..., embed=True)) -> APIResponse:
        import jwt
        from jwt.exceptions import InvalidTokenError
        now = int(time.time())
        try:
            data = jwt.decode(token, settings.webapp_jwt_secret, algorithms=["HS256"])
            # Allow refresh only for webapp scope
            if data.get("scope") != "webapp":
                raise InvalidTokenError("bad scope")
            # re-issue new token with shifted exp
            exp = now + int(settings.webapp_jwt_ttl_minutes) * 60
            new_claims = {**data, "iat": now, "exp": exp}
            new_token = jwt.encode(new_claims, settings.webapp_jwt_secret, algorithm="HS256")
            return APIResponse(ok=True, data={"token": new_token, "exp": exp})
        except InvalidTokenError:
            return APIResponse(ok=False, error={"code": "E_BAD_TOKEN", "message": "Invalid token"})

    # Send strategy video after goal change (triggered from WebApp)
    @app.post("/api/goal-notify", response_model=APIResponse)
    async def goal_notify(telegram_id: int, mode: str = Body(..., embed=True)) -> APIResponse:
        try:
            log.info("goal_notify_call", telegram_id=int(telegram_id), mode=mode)
        except Exception:
            pass
        if not settings.telegram_bot_token:
            raise HTTPException(status_code=500, detail="Bot token is not configured")
        # rate-limit & dedupe per user/mode for 10 minutes
        key = f"goal_notify:{telegram_id}:{mode}"
        try:
            exist = await redis_client.get(key)
            if exist:
                return APIResponse(ok=True, data={"sent": False})
            await redis_client.setex(key, 600, "1")
        except Exception:
            pass
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
        bot = TgBot(settings.telegram_bot_token)
        web_url = settings.webapp_url or ""
        # add cache-busting to force fresh WebApp load in Telegram mobile WebView
        try:
            if web_url and web_url.startswith("https://"):
                import time as _t
                sep = '&' if ('?' in web_url) else '?'
                web_url = f"{web_url}{sep}v={int(_t.time())}"
        except Exception:
            pass
        base = Path(__file__).resolve().parents[2] / "data/content/templates/video/ready_video"
        caption = ""
        video_path = None
        # resolve filename robustly: support different dash variants and spacing
        def _resolve_video(base_dir: Path, index: str) -> Path | None:
            candidates = [
                f"Ultima — SecondVideo {index}.mp4",  # em dash
                f"Ultima – SecondVideo {index}.mp4",  # en dash
                f"Ultima - SecondVideo {index}.mp4",  # hyphen
                f"Ultima—SecondVideo {index}.mp4",
                f"Ultima–SecondVideo {index}.mp4",
                f"Ultima-SecondVideo {index}.mp4",
            ]
            for name in candidates:
                p = base_dir / name
                if p.exists():
                    return p
            # glob fallback
            try:
                for p in base_dir.glob(f"*SecondVideo*{index}*.mp4"):
                    if p.is_file():
                        return p
            except Exception:
                pass
            return None

        if mode == "loss":
            caption = "Новая стратегия — Снижение веса (похудение). Посмотри видео и введи нужные данные."
            video_path = _resolve_video(base, "1")
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Открыть Ultima App", web_app={"url": web_url}), InlineKeyboardButton(text="Заполнить позже", callback_data="goal_later")]])
        elif mode == "maint":
            caption = "Новая стратегия — Поддержание веса. Посмотри видео и введи нужные данные."
            video_path = _resolve_video(base, "2")
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Открыть Ultima App", web_app={"url": web_url}), InlineKeyboardButton(text="Заполнить позже", callback_data="goal_later")]])
        elif mode == "gain":
            caption = "Новая стратегия — Рост мышечной массы. Посмотри видео и введи нужные данные."
            video_path = _resolve_video(base, "3")
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Открыть Ultima App", web_app={"url": web_url}), InlineKeyboardButton(text="Заполнить позже", callback_data="goal_later")]])
        else:
            caption = "Новая стратегия — Контроль потребления (без целей по весу). Посмотри видео и введи нужные данные."
            video_path = _resolve_video(base, "4")
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Продолжить", callback_data="goal_continue")]])
        try:
            log.info("goal_notify_video_resolve", base=str(base), path=str(video_path) if video_path else None, exists=bool(video_path and video_path.exists()))
        except Exception:
            pass
        try:
            if video_path and video_path.exists():
                await bot.send_video(chat_id=int(telegram_id), video=FSInputFile(str(video_path)), caption=caption, reply_markup=kb)
            else:
                # fallback to message only
                await bot.send_message(chat_id=int(telegram_id), text=caption, reply_markup=kb)
        except Exception as e:
            try:
                log.error("goal_notify_send_error", error=str(e))
            except Exception:
                pass
            return APIResponse(ok=False, error={"code": "E_SEND", "message": "Failed to send"})
        return APIResponse(ok=True, data={"sent": True})

    # Stage 7: normalization endpoint (text based MVP)
    @app.post("/api/normalize", response_model=NormalizeResponse)
    async def normalize(payload: NormalizeInput, request: Request) -> NormalizeResponse:
        started = time.perf_counter()
        out = await normalize_text_async(payload.text, locale=payload.locale)
        took_ms = (time.perf_counter() - started) * 1000.0
        try:
            await redis_client.incr("metrics:normalize:count")
            await redis_client.incrbyfloat("metrics:normalize:ms_total", took_ms)
        except Exception:
            pass
        # log trace if header present
        xtrace = request.headers.get("X-Trace-Id")
        if xtrace:
            log.bind(trace_id=xtrace).info("normalize_done", took_ms=took_ms)
        # Convert domain dataclasses to Pydantic models for response validation
        items = [
            NormalizedItem(
                name=i.name,
                category=i.category,
                unit=i.unit,
                amount=i.amount,
                kcal=i.kcal,
                protein_g=i.protein_g,
                fat_g=i.fat_g,
                carb_g=i.carb_g,
                confidence=i.confidence,
                assumptions=i.assumptions,
            )
            for i in out.items
        ]
        return NormalizeResponse(
            items=items,
            needs_clarification=out.needs_clarification,
            clarifications=out.clarifications,
        )

    # Daily summary
    @app.get("/api/daily-summary", response_model=APIResponse)
    async def get_daily_summary(telegram_id: int, date: str, session: AsyncSession = Depends(get_session)) -> APIResponse:
        users = UserRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        from datetime import date as D
        d = D.fromisoformat(date)
        ds = await DailySummaryRepo(session).get_by_user_date(user_id=user_id, on_date=d)
        return APIResponse(ok=True, data=ds)

    # Stage 11: summaries & trends
    @app.get("/api/summary/daily", response_model=APIResponse)
    async def summary_daily(telegram_id: int, date: str, tz: str | None = None, no_cache: int = 0, session: AsyncSession = Depends(get_session)) -> APIResponse:
        users = UserRepo(session)
        profiles = ProfileRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        from datetime import date as D
        d = D.fromisoformat(date)
        # Cache key
        key = f"summary:daily:{user_id}:{d.isoformat()}"
        if not no_cache:
            try:
                cached = await redis_client.get(key)
                if cached:
                    import json as _json
                    return APIResponse(ok=True, data=_json.loads(cached))
            except Exception:
                pass
        # Consumed
        meals = MealRepo(session)
        sums = await meals.sum_macros_for_date(user_id=user_id, on_date=d, tz=tz)
        # top food items/categories for the day
        from sqlalchemy import func, select
        from infra.db.models import Meal, MealItem
        from datetime import datetime as DT
        if tz:
            from zoneinfo import ZoneInfo
            z = ZoneInfo(tz)
            start_local = DT.combine(d, DT.min.time()).replace(tzinfo=z)
            end_local = DT.combine(d, DT.max.time()).replace(tzinfo=z)
            start_utc = start_local.astimezone(ZoneInfo("UTC"))
            end_utc = end_local.astimezone(ZoneInfo("UTC"))
        else:
            start_utc = DT.combine(d, DT.min.time()).astimezone()
            end_utc = DT.combine(d, DT.max.time()).astimezone()
        q = (
            select(MealItem.name, func.sum(MealItem.kcal).label("k"))
            .select_from(MealItem)
            .join(Meal, Meal.id == MealItem.meal_id)
            .where(Meal.user_id == user_id, Meal.at >= start_utc, Meal.at <= end_utc)
            .group_by(MealItem.name)
            .order_by(func.sum(MealItem.kcal).desc())
            .limit(5)
        )
        top_items = [
            {"name": r[0], "kcal": float(r[1])} for r in (await session.execute(q)).all()
        ]
        # Target from profile
        prof = await profiles.get_by_user_id(user_id)
        from domain.calculations import bmr_mifflin, tdee_from_activity, target_kcal_from_goal, distribute_macros
        if prof:
            age = 30
            bmr = bmr_mifflin(prof["sex"], age, float(prof["height_cm"]), float(prof["weight_kg"]))
            tdee = tdee_from_activity(bmr, prof["activity_level"]) 
            target_kcal = target_kcal_from_goal(tdee, prof["goal"]) 
            targets = distribute_macros(weight_kg=float(prof["weight_kg"]), target_kcal=target_kcal)
        else:
            targets = None
        data = {
            "consumed": sums,
            "target": targets.__dict__ if targets else None,
            "delta": {
                k: (float(sums.get(k, 0.0)) - float(getattr(targets, k))) if targets else None
                for k in ["kcal", "protein_g", "fat_g", "carb_g"]
            },
            "remaining": {
                k: (float(getattr(targets, k)) - float(sums.get(k, 0.0))) if targets else None
                for k in ["kcal", "protein_g", "fat_g", "carb_g"]
            },
            "top_items": top_items or None,
        }
        if not no_cache:
            try:
                await redis_client.setex(key, 300, _json.dumps(data))
            except Exception:
                pass
        return APIResponse(ok=True, data=data)

    @app.get("/api/summary/weekly", response_model=APIResponse)
    async def summary_weekly(telegram_id: int, start: str | None = None, tz: str | None = None, no_cache: int = 0, session: AsyncSession = Depends(get_session)) -> APIResponse:
        users = UserRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        from datetime import date as D, timedelta
        if not start:
            s = D.today() - timedelta(days=6)
        else:
            s = D.fromisoformat(start)
        e = s + timedelta(days=6)
        repo = DailySummaryRepo(session)
        meals_repo = MealRepo(session)
        # Try cache
        cache_key = f"summary:weekly:{user_id}:{s.isoformat()}"
        cached = None
        if not no_cache:
            try:
                cached = await redis_client.get(cache_key)
            except Exception:
                cached = None
            if cached:
                return APIResponse(ok=True, data=_json.loads(cached))
        items = await repo.list_between(user_id=user_id, start=s, end=e)
        # Ensure contiguous daily items; fill gaps from meals if summaries missing
        from datetime import timedelta as _td
        existing = {it["date"]: it for it in items}
        filled: list[dict] = []
        cur = s
        while cur <= e:
            iso = cur.isoformat()
            if iso in existing:
                filled.append(existing[iso])
            else:
                sums = await meals_repo.sum_macros_for_date(user_id=user_id, on_date=cur, tz=tz)
                if any(v > 0 for v in sums.values()):
                    filled.append({
                        "date": iso,
                        "kcal": float(sums["kcal"]),
                        "protein_g": float(sums["protein_g"]),
                        "fat_g": float(sums["fat_g"]),
                        "carb_g": float(sums["carb_g"]),
                    })
            cur = cur + _td(days=1)
        # sort by date
        items = sorted(filled or items, key=lambda x: x["date"])  # prefer filled if any
        # averages
        n = max(1, len(items))
        avg = {
            "kcal": round(sum(float(i.get("kcal", 0.0)) for i in items) / n, 1) if items else 0.0,
            "protein_g": round(sum(float(i.get("protein_g", 0.0)) for i in items) / n, 1) if items else 0.0,
            "fat_g": round(sum(float(i.get("fat_g", 0.0)) for i in items) / n, 1) if items else 0.0,
            "carb_g": round(sum(float(i.get("carb_g", 0.0)) for i in items) / n, 1) if items else 0.0,
        }
        # variance (дисперсия)
        var = None
        if items:
            def _var(seq):
                m = sum(seq)/len(seq)
                return round(sum((x-m)**2 for x in seq)/len(seq), 1)
            var = {
                "kcal": _var([i["kcal"] for i in items]),
                "protein_g": _var([i["protein_g"] for i in items]),
                "fat_g": _var([i["fat_g"] for i in items]),
                "carb_g": _var([i["carb_g"] for i in items]),
            }
        # compliance: within +/-10% of daily target using current profile target
        profiles = ProfileRepo(session)
        prof = await profiles.get_by_user_id(user_id)
        comp = None
        weight_pace_kg_per_week = None
        if prof:
            from domain.calculations import bmr_mifflin, tdee_from_activity, target_kcal_from_goal
            age = 30
            bmr = bmr_mifflin(prof["sex"], age, float(prof["height_cm"]), float(prof["weight_kg"]))
            tdee = tdee_from_activity(bmr, prof["activity_level"]) 
            target_kcal = target_kcal_from_goal(tdee, prof["goal"]) 
            lo, hi = 0.9 * target_kcal, 1.1 * target_kcal
            within = sum(1 for i in items if lo <= i["kcal"] <= hi)
            comp = {"score": int(100 * within / n), "days_within": within, "total_days": n}
            # weight pace
            from infra.db.repositories.weight_repo import WeightRepo
            wrepo = WeightRepo(session)
            w = await wrepo.list_between(user_id=user_id, start=s, end=e)
            if len(w) >= 2:
                days = (e - s).days or 1
                weight_pace_kg_per_week = round((w[-1]["weight_kg"] - w[0]["weight_kg"]) / days * 7.0, 2)
        data = {"items": items, "avg": avg, "variance": var, "compliance": comp, "weight_pace_kg_per_week": weight_pace_kg_per_week}
        if not no_cache:
            try:
                await redis_client.setex(cache_key, 300, _json.dumps(data))
            except Exception:
                pass
        return APIResponse(ok=True, data=data)

    @app.get("/api/summary/monthly", response_model=APIResponse)
    async def summary_monthly(telegram_id: int, month: str | None = None, tz: str | None = None, session: AsyncSession = Depends(get_session)) -> APIResponse:
        users = UserRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        from datetime import date as D, timedelta
        if month:
            year, mon = month.split("-")
            s = D(int(year), int(mon), 1)
        else:
            today = D.today()
            s = D(today.year, today.month, 1)
        # compute end of month
        if s.month == 12:
            e = D(s.year + 1, 1, 1) - timedelta(days=1)
        else:
            e = D(s.year, s.month + 1, 1) - timedelta(days=1)
        repo = DailySummaryRepo(session)
        # Try cache
        cache_key = f"summary:monthly:{user_id}:{s.strftime('%Y-%m')}"
        try:
            cached = await redis_client.get(cache_key)
        except Exception:
            cached = None
        if cached:
            return APIResponse(ok=True, data=_json.loads(cached))
        items = await repo.list_between(user_id=user_id, start=s, end=e)
        # classify days
        profiles = ProfileRepo(session)
        prof = await profiles.get_by_user_id(user_id)
        classes = None
        monthly_compliance = None
        streaks = None
        if prof:
            from domain.calculations import bmr_mifflin, tdee_from_activity, target_kcal_from_goal
            age = 30
            bmr = bmr_mifflin(prof["sex"], age, float(prof["height_cm"]), float(prof["weight_kg"]))
            tdee = tdee_from_activity(bmr, prof["activity_level"]) 
            target_kcal = target_kcal_from_goal(tdee, prof["goal"]) 
            lo10, hi10 = 0.9 * target_kcal, 1.1 * target_kcal
            classes = []
            within_days = 0
            # sort items by date to compute streaks
            items_sorted = sorted(items, key=lambda x: x["date"]) if items else []
            current_streak = 0
            longest_streak = 0
            for it in items_sorted:
                kcal = it["kcal"]
                if kcal < lo10:
                    cls = "undereating"
                elif kcal > hi10:
                    cls = "overeating"
                else:
                    cls = "within"
                classes.append({"date": it["date"], "class": cls})
                if cls == "within":
                    within_days += 1
                    current_streak += 1
                    if current_streak > longest_streak:
                        longest_streak = current_streak
                else:
                    current_streak = 0
            total_days = max(1, len(items_sorted))
            monthly_compliance = {"score": int(100 * within_days / total_days), "days_within": within_days, "total_days": total_days}
            streaks = {"longest": int(longest_streak), "current": int(current_streak)}
        # monthly trends: MA7 and MA30 over kcal
        kcal_ma7: list[float] = []
        kcal_ma30: list[float] = []
        dates: list[str] = []
        if items:
            items_sorted = sorted(items, key=lambda x: x["date"])  # ensure order
            vals = [i["kcal"] for i in items_sorted]
            dates = [i["date"] for i in items_sorted]
            for i in range(len(vals)):
                win7 = vals[max(0, i-6): i+1]
                win30 = vals[max(0, i-29): i+1]
                kcal_ma7.append(round(sum(win7)/len(win7), 1) if win7 else 0.0)
                kcal_ma30.append(round(sum(win30)/len(win30), 1) if win30 else 0.0)
        data = {
            "items": items,
            "classes": classes,
            "compliance": monthly_compliance,
            "streaks": streaks,
            "trends": {"dates": dates or None, "kcal_ma7": kcal_ma7 or None, "kcal_ma30": kcal_ma30 or None},
        }
        try:
            await redis_client.setex(cache_key, 600, _json.dumps(data))
        except Exception:
            pass
        return APIResponse(ok=True, data=data)

    @app.get("/api/trends", response_model=APIResponse)
    async def trends(telegram_id: int, window: int = 7, session: AsyncSession = Depends(get_session)) -> APIResponse:
        users = UserRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        from datetime import date as D, timedelta
        e = D.today()
        s = e - timedelta(days=max(1, window - 1))
        repo = DailySummaryRepo(session)
        items = await repo.list_between(user_id=user_id, start=s, end=e)
        # moving averages (MA7) for kcal
        ma7 = []
        vals = [i["kcal"] for i in items]
        for i in range(len(vals)):
            win = vals[max(0, i-6):i+1]
            ma7.append(round(sum(win)/len(win), 1) if win else 0.0)
        # weight trend and forecast (linear slope) + MA7 & median7 with outlier filter (IQR)
        wrepo = WeightRepo(session)
        weights = await wrepo.list_between(user_id=user_id, start=s, end=e)
        # extract series
        w_vals = [w["weight_kg"] for w in weights]
        # IQR filter
        weights_filtered = weights
        if len(w_vals) >= 4:
            sorted_vals = sorted(w_vals)
            q1 = sorted_vals[len(sorted_vals)//4]
            q3 = sorted_vals[(len(sorted_vals)*3)//4]
            iqr = q3 - q1
            lo = q1 - 1.5 * iqr
            hi = q3 + 1.5 * iqr
            weights_filtered = [w for w in weights if lo <= w["weight_kg"] <= hi]
        # MA7 and median7 on filtered sequence order
        wf_vals = [w["weight_kg"] for w in weights_filtered]
        weight_ma7 = []
        weight_median7 = []
        for i in range(len(wf_vals)):
            win = wf_vals[max(0, i-6):i+1]
            if win:
                weight_ma7.append(round(sum(win)/len(win), 2))
                # median
                sw = sorted(win)
                m = sw[len(sw)//2] if len(sw) % 2 == 1 else (sw[len(sw)//2 - 1] + sw[len(sw)//2]) / 2
                weight_median7.append(round(m, 2))
            else:
                weight_ma7.append(0.0)
                weight_median7.append(0.0)
        weight_forecast_7d = None
        weight_forecast_ci95 = None
        if len(weights) >= 2:
            # Linear regression on day indices
            import math
            xs = [i for i in range(len(weights))]
            ys = [w["weight_kg"] for w in weights]
            n = len(xs)
            mean_x = sum(xs) / n
            mean_y = sum(ys) / n
            sxx = sum((x - mean_x) ** 2 for x in xs)
            if sxx == 0:
                slope = 0.0
                intercept = ys[-1]
            else:
                slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / sxx
                intercept = mean_y - slope * mean_x
            x_f = xs[-1] + 7  # forecast 7 days ahead in index units (approx.)
            y_hat = intercept + slope * x_f
            weight_forecast_7d = round(y_hat, 2)
            # 95% CI of prediction
            if n >= 3 and sxx > 0:
                residuals = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
                se = math.sqrt(max(1e-9, sum(r*r for r in residuals) / (n - 2)))
                s_pred = se * math.sqrt(1 + 1 / n + ((x_f - mean_x) ** 2) / sxx)
                lo = round(y_hat - 1.96 * s_pred, 2)
                hi = round(y_hat + 1.96 * s_pred, 2)
                weight_forecast_ci95 = [lo, hi]
        return APIResponse(ok=True, data={
            "items": items,
            "kcal_ma7": ma7,
            "weights": weights,
            "weights_filtered": weights_filtered,
            "weight_ma7": weight_ma7,
            "weight_median7": weight_median7,
            "weight_forecast_7d": weight_forecast_7d,
            "weight_forecast_ci95": weight_forecast_ci95,
        })

    @app.get("/api/alerts", response_model=APIResponse)
    async def alerts(telegram_id: int, range: str = "week", tz: str | None = None, session: AsyncSession = Depends(get_session)) -> APIResponse:
        users = UserRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        from datetime import date as D, timedelta
        from zoneinfo import ZoneInfo
        end_d = D.today()
        start_d = end_d - timedelta(days=6 if range == "week" else 29)
        # Fetch daily summaries and weights
        ds_repo = DailySummaryRepo(session)
        items = await ds_repo.list_between(user_id=user_id, start=start_d, end=end_d)
        wrepo = WeightRepo(session)
        weights = await wrepo.list_between(user_id=user_id, start=start_d, end=end_d)
        # Build expected dates
        expected = [(start_d + timedelta(days=i)).isoformat() for i in range((end_d - start_d).days + 1)]
        have = {it["date"]: it for it in items}
        missing_meal_days = [d for d in expected if d not in have or (have[d]["kcal"] <= 0.0)]
        # Outliers in kcal (IQR)
        kcal_vals = [it["kcal"] for it in items if it["kcal"] > 0]
        kcal_outliers = {"high": [], "low": []}
        if len(kcal_vals) >= 4:
            sv = sorted(kcal_vals)
            q1 = sv[len(sv)//4]
            q3 = sv[(len(sv)*3)//4]
            iqr = q3 - q1
            lo = q1 - 1.5 * iqr
            hi = q3 + 1.5 * iqr
            for it in items:
                if it["kcal"] > hi:
                    kcal_outliers["high"].append(it["date"])
                elif it["kcal"] > 0 and it["kcal"] < lo:
                    kcal_outliers["low"].append(it["date"])
        # Missing weights
        weight_dates = {w["date"] for w in weights}
        missing_weight_days = [d for d in expected if d not in weight_dates]
        # Nudges
        nudges: list[dict] = []
        if missing_weight_days:
            nudges.append({
                "code": "WEIGH_IN_REMINDER",
                "message": "Давно не взвешивались. Добавьте вес за сегодня для более точных прогнозов.",
                "days_missing": len(missing_weight_days),
            })
        if missing_meal_days:
            nudges.append({
                "code": "MEAL_LOG_REMINDER",
                "message": "Есть дни без записей приема пищи. Запишите хотя бы основные блюда.",
                "days_missing": len(missing_meal_days),
            })
        if kcal_outliers["high"]:
            nudges.append({
                "code": "HIGH_CAL_OUTLIER",
                "message": "Замечены дни с заметным перееданием. Проверьте порции и перекусы.",
                "dates": kcal_outliers["high"],
            })
        if kcal_outliers["low"]:
            nudges.append({
                "code": "LOW_CAL_OUTLIER",
                "message": "Некоторые дни выглядят как недоедание. Убедитесь, что это не пропуски записей.",
                "dates": kcal_outliers["low"],
            })
        data = {
            "range": range,
            "missing_meal_days": missing_meal_days or None,
            "missing_weight_days": missing_weight_days or None,
            "kcal_outliers": kcal_outliers,
            "nudges": nudges or None,
        }
        return APIResponse(ok=True, data=data)

    # Weekly digest broadcast (MVP): builds per-user summary and sends Telegram messages with CTA to WebApp
    @app.post("/api/digest/weekly/send", response_model=APIResponse)
    async def send_weekly_digest(secret: str, session: AsyncSession = Depends(get_session)) -> APIResponse:
        # Simple shared-secret guard (can move to env/config)
        if secret != (settings.webapp_jwt_secret or ""):
            raise HTTPException(status_code=401, detail="Unauthorized")
        # Select all users
        users = UserRepo(session)
        from sqlalchemy import select
        from infra.db.models import User as UserModel
        res = await session.execute(select(UserModel.id, UserModel.telegram_id))
        rows = res.all()
        # Compose bot
        if not settings.telegram_bot_token:
            raise HTTPException(status_code=500, detail="Bot token is not configured")
        bot = TgBot(settings.telegram_bot_token)
        sent = 0
        for uid, tg_id in rows:
            try:
                # Weekly summary for each user
                from datetime import date as D, timedelta
                start = D.today() - timedelta(days=6)
                repo = DailySummaryRepo(session)
                items = await repo.list_between(user_id=uid, start=start, end=D.today())
                n = max(1, len(items))
                kcal_avg = round(sum(i["kcal"] for i in items) / n, 0) if items else 0
                # compliance score via existing endpoint logic (reuse minimal calc)
                comp = None
                try:
                    profiles = ProfileRepo(session)
                    prof = await profiles.get_by_user_id(uid)
                    if prof:
                        from domain.calculations import bmr_mifflin, tdee_from_activity, target_kcal_from_goal
                        age = 30
                        bmr = bmr_mifflin(prof["sex"], age, float(prof["height_cm"]), float(prof["weight_kg"]))
                        tdee = tdee_from_activity(bmr, prof["activity_level"]) 
                        target_kcal = target_kcal_from_goal(tdee, prof["goal"]) 
                        lo, hi = 0.9 * target_kcal, 1.1 * target_kcal
                        within = sum(1 for i in items if lo <= i["kcal"] <= hi)
                        comp = int(100 * within / n)
                except Exception:
                    comp = None
                # Build message
                text = (
                    "Ваш недельный дайджест:\n"
                    f"Средние калории: {int(kcal_avg)} ккал/день\n"
                    + (f"Комплаенс: {comp}% дней в цели\n" if comp is not None else "")
                    + "Откройте WebApp для подробностей."
                )
                # WebApp CTA
                web_url = settings.webapp_url or ""
                kb = {
                    "inline_keyboard": [[{"text": "Открыть WebApp", "web_app": {"url": web_url}}]]
                }
                await bot.send_message(chat_id=int(tg_id), text=text, reply_markup=kb)
                sent += 1
            except Exception:
                pass
        return APIResponse(ok=True, data={"sent": sent})

    @app.get("/api/compliance", response_model=APIResponse)
    async def compliance(telegram_id: int, range: str = "week", session: AsyncSession = Depends(get_session)) -> APIResponse:
        users = UserRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        from datetime import date as D, timedelta
        e = D.today()
        s = e - timedelta(days=6 if range == "week" else 29)
        repo = DailySummaryRepo(session)
        items = await repo.list_between(user_id=user_id, start=s, end=e)
        profiles = ProfileRepo(session)
        prof = await profiles.get_by_user_id(user_id)
        score = 0
        details = []
        if prof:
            from domain.calculations import bmr_mifflin, tdee_from_activity, target_kcal_from_goal
            age = 30
            bmr = bmr_mifflin(prof["sex"], age, float(prof["height_cm"]), float(prof["weight_kg"]))
            tdee = tdee_from_activity(bmr, prof["activity_level"]) 
            target_kcal = target_kcal_from_goal(tdee, prof["goal"]) 
            lo, hi = 0.9 * target_kcal, 1.1 * target_kcal
            total = max(1, len(items))
            within = 0
            for it in items:
                kcal = it["kcal"]
                cls = "within" if lo <= kcal <= hi else ("undereating" if kcal < lo else "overeating")
                if cls == "within":
                    within += 1
                details.append({"date": it["date"], "kcal": kcal, "class": cls})
            score = int(100 * within / total)
        return APIResponse(ok=True, data={"score": score, "days": details})

    @app.get("/api/summary/weekly.csv")
    async def summary_weekly_csv(telegram_id: int, start: str | None = None, tz: str | None = None, session: AsyncSession = Depends(get_session)) -> Response:
        users = UserRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        from datetime import date as D, timedelta
        s = D.fromisoformat(start) if start else (D.today() - timedelta(days=6))
        e = s + timedelta(days=6)
        repo = DailySummaryRepo(session)
        items = await repo.list_between(user_id=user_id, start=s, end=e)
        lines = ["date,kcal,protein_g,fat_g,carb_g"] + [f"{i['date']},{i['kcal']},{i['protein_g']},{i['fat_g']},{i['carb_g']}" for i in items]
        csv = "\n".join(lines)
        return Response(content=csv, media_type="text/csv")

    # Export: full meals CSV for user
    @app.get("/api/meals/export.csv")
    async def meals_export_csv(telegram_id: int, tz: str | None = None, session: AsyncSession = Depends(get_session)) -> Response:
        users = UserRepo(session)
        repo = MealRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        # Load all meals for this user
        from sqlalchemy import select
        from infra.db.models import Meal, MealItem
        rows = (await session.execute(select(Meal).where(Meal.user_id == user_id).order_by(Meal.at.asc()))).scalars().all()
        if not rows:
            return Response(content="date,time,name,amount,unit,kcal,protein_g,fat_g,carb_g\n", media_type="text/csv")
        meal_ids = [m.id for m in rows]
        items_res = await session.execute(select(MealItem).where(MealItem.meal_id.in_(meal_ids)))
        items = items_res.scalars().all()
        # Map items per meal
        from zoneinfo import ZoneInfo as _ZI
        tzname = tz or "Europe/Madrid"
        z = None
        try:
            z = _ZI(tzname)
        except Exception:
            z = _ZI("UTC")
        lines = ["date,time,name,amount,unit,kcal,protein_g,fat_g,carb_g"]
        items_by_meal: dict[int, list] = {}
        for it in items:
            items_by_meal.setdefault(it.meal_id, []).append(it)
        for m in rows:
            local_dt = m.at.astimezone(z)
            d = local_dt.date().isoformat()
            t = local_dt.time().strftime("%H:%M:%S")
            for it in items_by_meal.get(m.id, []):
                lines.append(
                    f"{d},{t}," +
                    f"{(it.name or '').replace(',', ' ').strip()},{it.amount},{it.unit},{it.kcal},{it.protein_g},{it.fat_g},{it.carb_g}"
                )
        csv = "\n".join(lines) + "\n"
        headers = {"Content-Disposition": "attachment; filename=meals_export.csv"}
        return Response(content=csv, media_type="text/csv", headers=headers)

    # Export token for Google Sheets IMPORTDATA
    @app.post("/api/meals/export-token", response_model=APIResponse)
    async def meals_export_token(telegram_id: int) -> APIResponse:
        import time, jwt
        now = int(time.time())
        exp = now + 24 * 60 * 60  # 24h token
        claims = {"tid": int(telegram_id), "iat": now, "exp": exp, "scope": "export"}
        token = jwt.encode(claims, settings.webapp_jwt_secret, algorithm="HS256")
        return APIResponse(ok=True, data={"token": token, "exp": exp})

    # Public export by token (no auth header, for Google Sheets IMPORTDATA)
    @app.get("/api/meals/export.csv/public")
    async def meals_export_csv_public(token: str, tz: str | None = None, session: AsyncSession = Depends(get_session)) -> Response:
        import jwt
        try:
            claims = jwt.decode(token, settings.webapp_jwt_secret, algorithms=["HS256"])
            if claims.get("scope") != "export":
                raise HTTPException(status_code=403, detail="E_SCOPE")
            telegram_id = int(claims.get("tid") or 0)
            if telegram_id <= 0:
                raise HTTPException(status_code=400, detail="E_BAD_TID")
        except Exception:
            raise HTTPException(status_code=401, detail="E_TOKEN")
        # Reuse internal builder
        return await meals_export_csv(telegram_id=telegram_id, tz=tz, session=session)

    # Send CSV export to Telegram chat
    @app.post("/api/meals/export-send", response_model=APIResponse)
    async def meals_export_send(telegram_id: int, tz: str | None = None, session: AsyncSession = Depends(get_session)) -> APIResponse:
        users = UserRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        # Build CSV same as export.csv
        from sqlalchemy import select
        from infra.db.models import Meal, MealItem
        rows = (await session.execute(select(Meal).where(Meal.user_id == user_id).order_by(Meal.at.asc()))).scalars().all()
        tzname = tz or "Europe/Madrid"
        from zoneinfo import ZoneInfo as _ZI
        try:
            z = _ZI(tzname)
        except Exception:
            z = _ZI("UTC")
        lines = ["date,time,name,amount,unit,kcal,protein_g,fat_g,carb_g"]
        if rows:
            meal_ids = [m.id for m in rows]
            items_res = await session.execute(select(MealItem).where(MealItem.meal_id.in_(meal_ids)))
            items = items_res.scalars().all()
            items_by_meal: dict[int, list] = {}
            for it in items:
                items_by_meal.setdefault(it.meal_id, []).append(it)
            for m in rows:
                local_dt = m.at.astimezone(z)
                d = local_dt.date().isoformat()
                t = local_dt.time().strftime("%H:%M:%S")
                for it in items_by_meal.get(m.id, []):
                    lines.append(
                        f"{d},{t},{(it.name or '').replace(',', ' ').strip()},{it.amount},{it.unit},{it.kcal},{it.protein_g},{it.fat_g},{it.carb_g}"
                    )
        csv = "\n".join(lines) + "\n"
        # Send via bot in background to avoid blocking API
        async def _send_csv(chat_id: int, content: str) -> None:
            token = (settings.telegram_bot_token or "").strip().strip("'").strip('"')
            if not token:
                return
            bot = TgBot(token=token)
            try:
                buf = BufferedInputFile(bytes(content, encoding="utf-8"), filename="meals_export.csv")
                await bot.send_document(chat_id=int(chat_id), document=buf, caption="Экспорт дневника (CSV)")
            finally:
                try:
                    await bot.session.close()
                except Exception:
                    pass
        asyncio.create_task(_send_csv(int(telegram_id), csv))
        return APIResponse(ok=True, data={"scheduled": True})

    # Favorites (stored in user_settings.data.favorites)
    @app.get("/api/favorites", response_model=APIResponse)
    async def favorites_list(telegram_id: int, session: AsyncSession = Depends(get_session)) -> APIResponse:
        users = UserRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        us = UserSettingsRepo(session)
        data = await us.get(user_id) or {}
        favs = data.get("favorites") or []
        return APIResponse(ok=True, data={"items": favs})

    @app.post("/api/favorites", response_model=APIResponse)
    async def favorites_add(telegram_id: int, request: Request, session: AsyncSession = Depends(get_session)) -> APIResponse:
        payload = await request.json()
        item = {
            "id": payload.get("id") or _uuid.uuid4().hex,
            "name": payload.get("name"),
            "unit": payload.get("unit") or "g",
            "amount": float(payload.get("amount") or 0.0),
            "kcal": float(payload.get("kcal") or 0.0),
            "protein_g": float(payload.get("protein_g") or 0.0),
            "fat_g": float(payload.get("fat_g") or 0.0),
            "carb_g": float(payload.get("carb_g") or 0.0),
        }
        users = UserRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        us = UserSettingsRepo(session)
        data = await us.get(user_id) or {}
        favs = list(data.get("favorites") or [])
        # prevent exact duplicates by name+unit+amount+kcal
        if not any((f.get("name"), f.get("unit"), f.get("amount"), f.get("kcal")) == (item["name"], item["unit"], item["amount"], item["kcal"]) for f in favs):
            favs.append(item)
            data["favorites"] = favs
            await us.upsert(user_id, data)
        return APIResponse(ok=True, data={"id": item["id"]})

    @app.delete("/api/favorites/{fav_id}", response_model=APIResponse)
    async def favorites_delete(fav_id: str, telegram_id: int, session: AsyncSession = Depends(get_session)) -> APIResponse:
        users = UserRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        us = UserSettingsRepo(session)
        data = await us.get(user_id) or {}
        favs = list(data.get("favorites") or [])
        nfavs = [f for f in favs if str(f.get("id")) != str(fav_id)]
        if len(nfavs) != len(favs):
            data["favorites"] = nfavs
            await us.upsert(user_id, data)
        return APIResponse(ok=True, data={"deleted": True})

    # Stage 9: receive photo (raw MVP), store to object storage and index
    @app.post("/api/photos", response_model=APIResponse)
    async def upload_photo(telegram_id: int, content_type: str, data: bytes, session: AsyncSession = Depends(get_session)) -> APIResponse:
        users = UserRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        # rate limit per user per day
        from datetime import date as D
        today = D.today().isoformat()
        key = f"lim:vision:{user_id}:{today}"
        used = int(await redis_client.get(key) or 0)
        if used >= settings.vision_daily_limit:
            raise HTTPException(status_code=429, detail="E_VISION_LIMIT")
        # preprocess
        processed = preprocess_photo(data, content_type)
        res = save_photo(user_id, PhotoIn(bytes=processed.bytes, content_type=processed.content_type, width=processed.width, height=processed.height))
        # index in DB
        img_repo = ImageRepo(session)
        image_id = await img_repo.create_or_get(
            user_id=user_id,
            object_key=res.object_key,
            sha256=res.sha256,
            width=processed.width,
            height=processed.height,
            content_type=processed.content_type,
        )
        # enqueue vision task
        await enqueue_vision(VisionTask(image_id=image_id, user_id=user_id))
        await redis_client.incr(key)
        await redis_client.expire(key, 60 * 60 * 24)
        return APIResponse(ok=True, data={"image_id": image_id, "object_key": res.object_key, "sha256": res.sha256, "status": "queued"})

    @app.get("/api/photos/{image_id}/status", response_model=APIResponse)
    async def photo_status(image_id: int) -> APIResponse:
        status = await get_vision_status(image_id)
        return APIResponse(ok=True, data=status or {"status": "unknown"})

    # Aggregate mediagroup images and run multi‑image vision; return preview items
    @app.post("/api/photo-groups/commit", response_model=APIResponse)
    async def photo_group_commit(telegram_id: int, group_id: str, session: AsyncSession = Depends(get_session)) -> APIResponse:
        key = f"mediagroup:{telegram_id}:{group_id}"
        image_ids = []
        try:
            # consume all ids in the list
            while True:
                v = await _redis.lpop(key)
                if not v:
                    break
                image_ids.append(int(v))
        except Exception:
            pass
        if not image_ids:
            return APIResponse(ok=False, error={"code": "E_EMPTY_GROUP", "message": "No images in group"})
        # For MVP: pick handle image = last one; get latest inference for each and merge items
        from infra.db.repositories.vision_inference_repo import VisionInferenceRepo
        vrepo = VisionInferenceRepo(session)
        items: list[dict] = []
        clarifications: list[str] = []
        for iid in image_ids:
            inf = await vrepo.get_latest_by_image(image_id=iid)
            if inf and inf.get("response"):
                resp = inf["response"]
                items.extend(resp.get("items", []))
                try:
                    cl = (resp.get("quality") or {}).get("clarifications") or []
                    if isinstance(cl, list):
                        clarifications.extend([str(x) for x in cl if x])
                except Exception:
                    pass
        # naive fusion: group identical names and sum amounts/macros
        merged: dict[str, dict] = {}
        for it in items:
            key = (it.get("name") or "").strip().lower()
            if not key:
                continue
            if key not in merged:
                merged[key] = {**it}
            else:
                m = merged[key]
                try:
                    m["amount"] = float(m.get("amount", 0.0)) + float(it.get("amount", 0.0))
                    m["kcal"] = float(m.get("kcal", 0.0)) + float(it.get("kcal", 0.0))
                    m["protein_g"] = float(m.get("protein_g", 0.0)) + float(it.get("protein_g", 0.0))
                    m["fat_g"] = float(m.get("fat_g", 0.0)) + float(it.get("fat_g", 0.0))
                    m["carb_g"] = float(m.get("carb_g", 0.0)) + float(it.get("carb_g", 0.0))
                except Exception:
                    pass
        fused = list(merged.values()) or items
        # unique clarifications
        if clarifications:
            clarifications = sorted(list({c.strip(): None for c in clarifications}.keys()))
        return APIResponse(ok=True, data={"handle_image_id": image_ids[-1], "items": fused, "clarifications": clarifications, "images_count": len(image_ids)})

    # Save photo inference as meal
    @app.post("/api/photos/{image_id}/save", response_model=APIResponse)
    async def photo_save(image_id: int, telegram_id: int, tz: str | None = None, session: AsyncSession = Depends(get_session)) -> APIResponse:
        users = UserRepo(session)
        repo = MealRepo(session)
        from infra.db.repositories.vision_inference_repo import VisionInferenceRepo
        vrepo = VisionInferenceRepo(session)
        user_id = await users.get_or_create_by_telegram_id(telegram_id)
        inf = await vrepo.get_latest_by_image(image_id=image_id)
        if not inf:
            raise HTTPException(status_code=404, detail="Inference not found")
        items = inf["response"].get("items", [])
        from datetime import datetime as DT, date as D
        at = DT.now(ZoneInfo("UTC"))
        meal_id = await repo.create_meal(
            user_id=user_id,
            at=at,
            meal_type=MealRepo.suggest_meal_type(at),
            items=items,
            notes=f"photo:{image_id}",
            status="confirmed",
            autocommit=False,
        )
        try:
            tzname = tz or "Europe/Madrid"
            d = at.astimezone(ZoneInfo(tzname)).date()
        except Exception:
            d = D.fromisoformat(at.date().isoformat())
        sums = await repo.sum_macros_for_date(user_id=user_id, on_date=d)
        await DailySummaryRepo(session).upsert_daily_summary(
            user_id=user_id, on_date=d, kcal=sums["kcal"], protein_g=sums["protein_g"], fat_g=sums["fat_g"], carb_g=sums["carb_g"], autocommit=False
        )
        await session.commit()
        return APIResponse(ok=True, data={"meal_id": meal_id})

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


