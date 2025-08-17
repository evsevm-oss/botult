from __future__ import annotations

from fastapi import FastAPI

from core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title="Ultima Calories API", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/me/summary")
    def me_summary() -> dict:
        # Заглушка: вернём фиксированные данные
        return {
            "ok": True,
            "data": {"kcal": 2300, "protein_g": 144, "fat_g": 64, "carb_g": 290},
        }

    return app


app = create_app()


