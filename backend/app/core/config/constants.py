"""
Application constants.

This module contains immutable constants that are shared across the
application. These values should NOT depend on environment variables.
"""

from typing import Final

# =============================================================================
# Application
# =============================================================================

APP_NAME: Final[str] = "Investment OS"
APP_VERSION: Final[str] = "0.1.0"

# =============================================================================
# Environment
# =============================================================================

DEFAULT_ENVIRONMENT: Final[str] = "development"

# =============================================================================
# Health Status
# =============================================================================

STATUS_OK: Final[str] = "ok"
STATUS_READY: Final[str] = "ready"
STATUS_NOT_CONFIGURED: Final[str] = "not_configured"

# =============================================================================
# Service Names
# =============================================================================

SERVICE_DATABASE: Final[str] = "database"
SERVICE_REDIS: Final[str] = "redis"
SERVICE_LLM: Final[str] = "llm"

# ===========================================================
# Security
# ==========================================================
DEFAULT_JWT_SECRET_KEY: Final[str] = "development-only-secret-key-change-before-production"

DEFAULT_JWT_ALGORITHM: Final[str] = "HS256"

DEFAULT_JWT_ACCESS_TOKEN_EXPIRE_MINUTES: Final[int] = 30

DEFAULT_JWT_REFRESH_TOKEN_EXPIRE_DAYS: Final[int] = 30

DEFAULT_JWT_ISSUER: Final[str] = "investment-os"
# =============================================================================
# LLM
# =============================================================================

DEFAULT_LLM_PROVIDER: Final[str] = "qwen"

DEFAULT_LLM_MODEL: Final[str] = "qwen3-8b-q4"

DEFAULT_LLM_TEMPERATURE: Final[float] = 0.0

DEFAULT_LLM_MAX_TOKENS: Final[int] = 2048

# =============================================================================
# Qwen / Local LLM
# =============================================================================

DEFAULT_QWEN_MODEL_PATH: Final[str] = (
    "/models/qwen3/Qwen3-8B-Q4_K_M.gguf"
)

DEFAULT_QWEN_CONTEXT_SIZE: Final[int] = 8192

DEFAULT_QWEN_THREADS: Final[int] = 8

DEFAULT_QWEN_ENABLE_THINKING: Final[bool] = True

# =============================================================================
# OpenAI
# =============================================================================

DEFAULT_OPENAI_MODEL: Final[str] = "gpt-5.4-mini"
