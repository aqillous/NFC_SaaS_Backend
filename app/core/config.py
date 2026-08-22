"""
Application configuration.

All values are loaded from environment variables (see .env.example).
Never hardcode secrets here.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "NFC Review SaaS"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = True

    # --- Database ---
    DATABASE_URL: str = "postgresql+psycopg2://nfc_user:nfc_password@localhost:5432/nfc_reviews"
    # Hosted Postgres providers (Supabase, RDS, etc.) require SSL. Local dev DBs
    # usually don't have it configured, so default to False and set True in .env
    # for any environment pointing at Supabase.
    DB_SSL_REQUIRE: bool = False

    # --- Security / JWT ---
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours

    # --- CORS ---
    # Comma-separated list of allowed origins, e.g. "http://localhost:5173,https://admin.mydomain.com"
    CORS_ORIGINS: str = "http://localhost:5173"

    # --- Public redirect base (used to build NFC URLs returned by the API) ---
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # --- Rate limiting (public redirect endpoint) ---
    REDIRECT_RATE_LIMIT: str = "30/minute"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance so we don't re-read env vars on every call."""
    return Settings()


settings = get_settings()
