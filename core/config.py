from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = Field("development", alias="APP_ENV")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    # Telegram
    telegram_bot_token: str | None = Field(None, alias="TELEGRAM_BOT_TOKEN")
    telegram_webhook_url: str | None = Field(None, alias="TELEGRAM_WEBHOOK_URL")

    # AI providers (minimal)
    openai_api_key: str | None = Field(None, alias="OPENAI_API_KEY")
    openai_tts_voice: str = Field("alloy", alias="OPENAI_TTS_VOICE")
    openai_model_normalize: str = Field("gpt-4o-mini", alias="OPENAI_MODEL_NORMALIZE")
    openai_cost_input_per_1k: float = Field(0.0005, alias="OPENAI_COST_INPUT_PER_1K")
    openai_cost_output_per_1k: float = Field(0.0015, alias="OPENAI_COST_OUTPUT_PER_1K")
    moderation_enabled: bool = Field(True, alias="MODERATION_ENABLED")
    did_api_key: str | None = Field(None, alias="DID_API_KEY")

    # Cost approximations for metrics (USD)
    openai_cost_vision_per_image: float = Field(0.003, alias="OPENAI_COST_VISION_PER_IMAGE")
    openai_cost_normalize_per_req: float = Field(0.0008, alias="OPENAI_COST_NORMALIZE_PER_REQ")

    # Storage / DB / Cache
    database_url: str = Field(..., alias="DATABASE_URL")
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    celery_broker_url: str | None = Field(None, alias="CELERY_BROKER_URL")
    celery_result_backend: str | None = Field(None, alias="CELERY_RESULT_BACKEND")

    s3_endpoint_url: str | None = Field(None, alias="S3_ENDPOINT_URL")
    s3_bucket: str | None = Field(None, alias="S3_BUCKET")
    s3_access_key_id: str | None = Field(None, alias="S3_ACCESS_KEY_ID")
    s3_secret_access_key: str | None = Field(None, alias="S3_SECRET_ACCESS_KEY")
    vision_daily_limit: int = Field(100, alias="VISION_DAILY_LIMIT")
    max_image_px: int = Field(1600, alias="MAX_IMAGE_PX")

    # CORS / Web
    allowed_origins: str = Field("http://localhost:5173,http://localhost:3000", alias="ALLOWED_ORIGINS")

    # Telegram WebApp URL (optional)
    webapp_url: str | None = Field(None, alias="WEBAPP_URL")

    # WebApp JWT
    webapp_jwt_secret: str = Field("dev-webapp-secret", alias="WEBAPP_JWT_SECRET")
    webapp_jwt_ttl_minutes: int = Field(45, alias="WEBAPP_JWT_TTL_MINUTES")

    # Internal API base for bot to call FastAPI
    api_base_url: str = Field("http://127.0.0.1:8000", alias="API_BASE")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()


