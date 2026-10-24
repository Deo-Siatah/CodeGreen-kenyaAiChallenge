import os
from pathlib import Path
from typing import Literal

from pydantic import ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str

    DATABASE_URL_POOLED: str
    DATABASE_URL_DIRECT: str
    DB_SCORING_ROLE: str = "app_scoring"
    DB_ANALYTICS_ROLE: str = "app_analytics"
    FARM_ACTIVITY_PROVIDER: Literal["null", "earth_engine"] = "null"
    EARTH_ENGINE_SERVICE_ACCOUNT_JSON: str
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "https://hifadhi-app-neon.vercel.app",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    # Test-only. Must be a DIRECT (non-pooler) URL to a throwaway Neon branch,
    # never main. Optional so the app boots without it.
    TEST_DATABASE_URL_DIRECT: str | None = None

    GEMINI_API_KEY: str
    GROQ_API_KEY: str
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GEMINI_MODEL: str = "gemini-3.5-flash"

    DEFAULT_EXPLANATION_MODE: Literal["expert", "farmer"] = "farmer"


try:
    settings = Settings()
    _settings_validation_error: ValidationError | None = None
except ValidationError as exc:
    settings = None
    _settings_validation_error = exc


def validate_configuration() -> Settings:
    """Validate settings and environment-dependent paths before app startup."""
    problems: list[str] = []
    global settings, _settings_validation_error

    if _settings_validation_error is not None:
        for error in _settings_validation_error.errors():
            field = str(error["loc"][0])
            problems.append(f"Missing or invalid setting: {field} (set in .env)")
    else:
        try:
            settings = Settings()
        except ValidationError as exc:
            _settings_validation_error = exc
            for error in exc.errors():
                field = str(error["loc"][0])
                problems.append(f"Missing or invalid setting: {field} (set in .env)")

    if settings is not None and settings.FARM_ACTIVITY_PROVIDER == "earth_engine":
        path = Path(settings.EARTH_ENGINE_SERVICE_ACCOUNT_JSON)
        if not os.path.isfile(path):
            problems.append(
                "EARTH_ENGINE_SERVICE_ACCOUNT_JSON must point to an existing "
                f"file when FARM_ACTIVITY_PROVIDER=earth_engine: {path}"
            )

    if problems:
        raise RuntimeError("Configuration validation failed:\n" + "\n".join(problems))
    return settings