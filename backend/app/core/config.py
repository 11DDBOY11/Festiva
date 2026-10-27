"""Application settings, loaded from environment variables / .env file."""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRETS = {
    "change-me-in-production",
    "change-me-to-a-random-string",
    "change-me-to-a-random-secret-key-32b",
    "",
}


class Settings(BaseSettings):
    """Central configuration — every value can be overridden by an env var."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- General / Environment ---
    PROJECT_NAME: str = "Festiva AI"
    ENV: str = "dev"  # dev | test | staging | prod

    # --- Database ---
    DATABASE_URL: str = "postgresql://festiva:festiva_dev@127.0.0.1:5432/festiva"
    TEST_DATABASE_URL: str = "postgresql://festiva:festiva_dev@127.0.0.1:5432/festiva_test"
    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    # --- Auth / JWT ---
    JWT_SECRET: str = "change-me-to-a-random-secret-key-32b"
    SECRET_KEY: str = "change-me-to-a-random-secret-key-32b"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- LLM ---
    LLM_PROVIDER: str = "fake"  # fake | openai | gemini
    LLM_API_KEY: str = ""

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """Fail startup if JWT_SECRET is the default value when ENV != dev."""
        default_marker = "change-me-to-a-random-secret-key-32b"
        if self.JWT_SECRET != default_marker and self.SECRET_KEY == default_marker:
            self.SECRET_KEY = self.JWT_SECRET
        elif self.SECRET_KEY != default_marker and self.JWT_SECRET == default_marker:
            self.JWT_SECRET = self.SECRET_KEY

        if self.ENV != "dev":
            if self.JWT_SECRET in DEFAULT_SECRETS or self.SECRET_KEY in DEFAULT_SECRETS:
                raise ValueError(
                    f"JWT_SECRET cannot be a default value in '{self.ENV}' environment. "
                    "Please configure a secure random key."
                )
        return self


settings = Settings()
