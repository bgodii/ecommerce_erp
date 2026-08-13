from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ERP Shopee"
    environment: str = "development"

    # postgresql+asyncpg://user:pass@host:5432/db  (driver asyncpg)
    database_url: str = "postgresql+asyncpg://erp:erp@localhost:5432/erp"

    jwt_secret: str = "dev-secret-change-me-in-production-please-use-32b+"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:8080"]
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
