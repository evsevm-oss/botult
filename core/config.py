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
    did_api_key: str | None = Field(None, alias="DID_API_KEY")

    # Storage / DB / Cache
    database_url: str = Field(..., alias="DATABASE_URL")
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    celery_broker_url: str | None = Field(None, alias="CELERY_BROKER_URL")
    celery_result_backend: str | None = Field(None, alias="CELERY_RESULT_BACKEND")

    s3_endpoint_url: str | None = Field(None, alias="S3_ENDPOINT_URL")
    s3_bucket: str | None = Field(None, alias="S3_BUCKET")
    s3_access_key_id: str | None = Field(None, alias="S3_ACCESS_KEY_ID")
    s3_secret_access_key: str | None = Field(None, alias="S3_SECRET_ACCESS_KEY")

    # CORS / Web
    allowed_origins: str = Field("http://localhost:3000", alias="ALLOWED_ORIGINS")

    # Telegram WebApp URL (optional)
    webapp_url: str | None = Field(None, alias="WEBAPP_URL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()


