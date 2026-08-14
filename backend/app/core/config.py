from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_ENV: Literal["development", "production", "test"] = "development"
    CORS_ORIGINS: str = "http://localhost:5173"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://warehaven:warehaven@localhost:5432/warehaven"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET: str = "change-me"
    JWT_ACCESS_TTL_MIN: int = 30
    JWT_REFRESH_TTL_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"

    # File storage
    LAYOUT_STORAGE_PATH: str = "/data/layout-imports"

    # Seed admin
    SEED_ADMIN_EMAIL: str = "admin@warehaven.local"
    SEED_ADMIN_PASSWORD: str = "change-me"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v: str) -> str:
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
