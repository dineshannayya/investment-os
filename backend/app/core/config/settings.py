"""
Runtime application settings.

All values in this file may be overridden through environment variables.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)

from app.core.config.constants import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_ENVIRONMENT,
    DEFAULT_LOG_LEVEL,
)


class Settings(BaseSettings):
    """
    Runtime application configuration.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # =========================================================================
    # Application
    # =========================================================================

    app_name: str = Field(default=APP_NAME)

    app_version: str = Field(default=APP_VERSION)

    environment: str = Field(
        default=DEFAULT_ENVIRONMENT,
    )

    debug: bool = Field(default=False)

    # =========================================================================
    # API Server
    # =========================================================================

    host: str = Field(default="0.0.0.0")

    port: int = Field(default=8000)

    # =========================================================================
    # Database
    # =========================================================================

    database_url: str | None = Field(default=None)

    # =========================================================================
    # Redis
    # =========================================================================

    redis_url: str | None = Field(default=None)

    # =========================================================================
    # LLM
    # =========================================================================

    llm_provider: str | None = Field(default=None)

    llm_model: str | None = Field(default=None)

    # =========================================================================
    # Logging
    # =========================================================================

    log_level: str = Field(
        default=DEFAULT_LOG_LEVEL,
    )


@lru_cache
def get_settings() -> Settings:
    """
    Return singleton application settings.
    """
    return Settings()


settings = get_settings()
