"""
Runtime application settings.

All values in this file may be overridden through environment variables.
"""

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)

from app.core.config.constants import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_ENVIRONMENT,
    DEFAULT_JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    DEFAULT_JWT_ALGORITHM,
    DEFAULT_JWT_ISSUER,
    DEFAULT_JWT_REFRESH_TOKEN_EXPIRE_DAYS,
    DEFAULT_JWT_SECRET_KEY,
    DEFAULT_LLM_MAX_TOKENS,
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_TEMPERATURE,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_QWEN_CONTEXT_SIZE,
    DEFAULT_QWEN_ENABLE_THINKING,
    DEFAULT_QWEN_MODEL_PATH,
    DEFAULT_QWEN_THREADS,
)
from app.core.config.logging import (
    DEFAULT_LOG_LEVEL,
)


class StorageProviderType(StrEnum):
    LOCAL = "local"
    S3 = "s3"
    AZURE = "azure"
    GCS = "gcs"

class LLMProviderType(StrEnum):
    QWEN = "qwen"
    OPENAI = "openai"
    MOCK = "mock"

# ---------------------------------------
#   Settings
#   │
#   ├── Application
#   ├── API Server
#   ├── Redis
#   │
#   ├── LLM
#   │   ├── llm_provider
#   │   ├── llm_model
#   │   ├── llm_temperature
#   │   └── llm_max_tokens
#   ├── Qwen / Local LLM
#   │   ├── qwen_model_path
#   │   ├── qwen_context_size
#   │   └── qwen_threads
#   ├── OpenAI
#   │   ├── openai_api_key
#   │   └── openai_model
#   ├── Logging
#   ├── Database
#   ├── Security
#   └── Storage
# -------------------------------------------

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
    # Redis
    # =========================================================================

    redis_url: str | None = Field(default=None)

    # =========================================================================
    # LLM
    # =========================================================================

    llm_provider: LLMProviderType = Field( default=LLMProviderType.QWEN,)
    
    llm_model: str = Field( default=DEFAULT_LLM_MODEL,)
    
    llm_temperature: float = Field( default=DEFAULT_LLM_TEMPERATURE, ge=0.0, le=2.0,)
    
    llm_max_tokens: int = Field( default=DEFAULT_LLM_MAX_TOKENS, gt=0,)

    # =========================================================================
    # Qwen / Local LLM
    # =========================================================================
    
    qwen_model_path: str = Field(
        default=DEFAULT_QWEN_MODEL_PATH,
    )
    
    qwen_context_size: int = Field( default=DEFAULT_QWEN_CONTEXT_SIZE, gt=0,)
    
    qwen_threads: int = Field( default=DEFAULT_QWEN_THREADS, gt=0,)

    qwen_enable_thinking: bool = Field( default=DEFAULT_QWEN_ENABLE_THINKING,) 
    # =========================================================================
    # OpenAI
    # =========================================================================
    
    openai_api_key: str | None = Field(default=None)
    
    
    @field_validator("openai_api_key", mode="before")
    @classmethod
    def normalize_openai_api_key(
        cls,
        value: str | None,
    ) -> str | None:
        """Normalize blank OpenAI API keys to None."""
    
        if value is None:
            return None
    
        if isinstance(value, str) and not value.strip():
            return None
    
        return value

    
    openai_model: str = Field(
        default=DEFAULT_OPENAI_MODEL,
    )


    # =========================================================================
    # Logging
    # =========================================================================

    log_level: str = Field(
        default=DEFAULT_LOG_LEVEL,
    )

    # =========================================================================
    # Database
    # =========================================================================
    database_url: str
    database_echo: bool = False
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout: int = 30
    database_pool_recycle: int = 1800

    # =========================================================================
    # Security
    # =========================================================================
    jwt_secret_key: str = Field(
        default=DEFAULT_JWT_SECRET_KEY,
    )

    jwt_algorithm: str = Field(
        default=DEFAULT_JWT_ALGORITHM,
    )

    jwt_issuer: str = Field(
        default=DEFAULT_JWT_ISSUER,
    )

    jwt_access_token_expire_minutes: int = Field(
        default=DEFAULT_JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    )

    jwt_refresh_token_expire_days: int = Field(
        default=DEFAULT_JWT_REFRESH_TOKEN_EXPIRE_DAYS,
    )

    # =========================================================================
    # Storage
    # =========================================================================

    storage_provider: StorageProviderType = Field(
        default=StorageProviderType.LOCAL,
    )

    storage_root: str = Field(
        default="./storage",
    )

    max_upload_size: int = Field(
        default=100 * 1024 * 1024,  # 100 MB
    )

    allowed_mime_types: list[str] = Field(
        default_factory=lambda: [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "text/plain",
            "image/jpeg",
            "image/png",
        ],
    )

# ------------------------------------------------

@field_validator("openai_api_key", mode="before")
@classmethod
def normalize_openai_api_key(
    cls,
    value: str | None,
) -> str | None:
    if value is None:
        return None

    if isinstance(value, str) and not value.strip():
        return None

    return value


@lru_cache
def get_settings() -> Settings:
    """
    Return singleton application settings.
    """
    return Settings()


settings = get_settings()
