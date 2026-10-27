"""Application settings, loaded from environment variables / .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration — every value can be overridden by an env var."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- General ---
    PROJECT_NAME: str = "Festiva AI"

    # --- Database ---
    DATABASE_URL: str = "postgresql://festiva:festiva_dev@localhost:5432/festiva"
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Auth / JWT ---
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- LLM ---
    LLM_PROVIDER: str = "fake"  # fake | openai | gemini
    LLM_API_KEY: str = ""


settings = Settings()
