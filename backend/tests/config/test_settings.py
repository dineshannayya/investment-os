import pytest
from pydantic import ValidationError

from app.core.config.settings import (
    LLMProviderType,
    Settings,
    get_settings,
)

# ============================================================
# Default Configuration
# ============================================================
#   
#   tests/config/test_settings.py
#   ├── Default Configuration
#   ├── Environment Overrides
#   ├── Validation
#   ├── Singleton
#   ├── Log Level
#   ├── Storage
#   ├── Allowed MIME Types
#   │
#   └── LLM
#       ├── default LLM settings
#       ├── default Qwen settings
#       ├── default OpenAI settings
#       ├── LLM environment override
#       ├── Qwen environment override
#       ├── OpenAI environment override
#       ├── temperature validation
#       ├── max tokens validation
#       ├── context-size validation
#       ├── thread-count validation
#       └── provider enum validation
# ============================================================

def test_default_settings():
    settings = Settings(database_url="postgresql://test", redis_url="redis://localhost")

    assert settings.app_name == "Investment OS"
    assert settings.port == 8000
    assert settings.debug is False


# ============================================================
# Environment Overrides
# ============================================================


def test_env_override(monkeypatch):
    monkeypatch.setenv("APP_NAME", "Investment OS Test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost")

    settings = Settings()

    assert settings.app_name == "Investment OS Test"


# ============================================================
# Validation
# ============================================================


def test_missing_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        Settings()


# ============================================================
# Singleton
# ============================================================


def test_singleton():
    assert get_settings() is get_settings()


# ============================================================
# log level
# ============================================================


def test_default_log_level():
    settings = Settings(database_url="postgresql://test", redis_url="redis://localhost")

    assert settings.log_level == "INFO"

# ============================================================
# Storage
# ============================================================

def test_default_storage_settings():
    settings = Settings(
        database_url="postgresql://test",
        redis_url="redis://localhost",
    )

    assert settings.storage_provider == "local"
    assert settings.storage_root == "./storage"
    assert settings.max_upload_size == 100 * 1024 * 1024

def test_storage_env_override(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test")
    monkeypatch.setenv("STORAGE_PROVIDER", "local")
    monkeypatch.setenv("STORAGE_ROOT", "/tmp/storage")

    settings = Settings()

    assert settings.storage_provider == "local"
    assert settings.storage_root == "/tmp/storage"

def test_allowed_mime_types():
    settings = Settings(
        database_url="postgresql://test",
        redis_url="redis://localhost",
    )

    assert "application/pdf" in settings.allowed_mime_types
    assert "image/png" in settings.allowed_mime_types

# ============================================================
# LLM
# ============================================================
# LLM default configuration tests
def test_default_llm_settings():
    settings = Settings(
        database_url="postgresql://test",
        redis_url="redis://localhost",
    )

    assert settings.llm_provider == LLMProviderType.QWEN
    assert settings.llm_model == "qwen3-8b-q4"
    assert settings.llm_temperature == 0.0
    assert settings.llm_max_tokens == 2048

# Test Qwen runtime defaults
def test_default_qwen_settings():
    settings = Settings(
        database_url="postgresql://test",
        redis_url="redis://localhost",
    )

    assert (
        settings.qwen_model_path
        == "/models/qwen3/Qwen3-8B-Q4_K_M.gguf"
    )

    assert settings.qwen_context_size == 8192
    assert settings.qwen_threads == 8

# Test OpenAI benchmark defaults
def test_default_openai_settings():
    settings = Settings(
        database_url="postgresql://test",
        redis_url="redis://localhost",
    )

    assert settings.openai_api_key is None
    assert settings.openai_model == "gpt-5.4-mini"


# Test environment overrides
def test_llm_env_override(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://test",
    )
    monkeypatch.setenv(
        "REDIS_URL",
        "redis://localhost",
    )
    monkeypatch.setenv(
        "LLM_PROVIDER",
        "openai",
    )
    monkeypatch.setenv(
        "LLM_MODEL",
        "gpt-5.4-mini",
    )

    settings = Settings()

    assert settings.llm_provider == LLMProviderType.OPENAI
    assert settings.llm_model == "gpt-5.4-mini"

# Test Qwen environment overrides
def test_qwen_env_override(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://test",
    )
    monkeypatch.setenv(
        "REDIS_URL",
        "redis://localhost",
    )
    monkeypatch.setenv(
        "QWEN_MODEL_PATH",
        "/opt/models/qwen/test.gguf",
    )
    monkeypatch.setenv(
        "QWEN_CONTEXT_SIZE",
        "16384",
    )
    monkeypatch.setenv(
        "QWEN_THREADS",
        "16",
    )

    settings = Settings()

    assert (
        settings.qwen_model_path
        == "/opt/models/qwen/test.gguf"
    )
    assert settings.qwen_context_size == 16384
    assert settings.qwen_threads == 16

# Test OpenAI environment override
def test_openai_env_override(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://test",
    )
    monkeypatch.setenv(
        "REDIS_URL",
        "redis://localhost",
    )
    monkeypatch.setenv(
        "OPENAI_API_KEY",
        "test-api-key",
    )
    monkeypatch.setenv(
        "OPENAI_MODEL",
        "gpt-5.4-mini",
    )

    settings = Settings()

    assert settings.openai_api_key == "test-api-key"
    assert settings.openai_model == "gpt-5.4-mini"

# 8. Validation tests

@pytest.mark.parametrize(
    "temperature",
    [-0.1, 2.1],
)
def test_invalid_llm_temperature(
    temperature,
):
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://test",
            redis_url="redis://localhost",
            llm_temperature=temperature,
        )

@pytest.mark.parametrize(
    "temperature",
    [0.0, 2.0],
)
def test_valid_llm_temperature(
    temperature,
):
    settings = Settings(
        database_url="postgresql://test",
        redis_url="redis://localhost",
        llm_temperature=temperature,
    )

    assert settings.llm_temperature == temperature

def test_invalid_llm_max_tokens():

    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://test",
            redis_url="redis://localhost",
            llm_max_tokens=0,
        )

def test_valid_llm_max_tokens():

    settings = Settings(
        database_url="postgresql://test",
        redis_url="redis://localhost",
        llm_max_tokens=4096,
    )

    assert settings.llm_max_tokens == 4096

def test_invalid_qwen_context_size():

    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://test",
            redis_url="redis://localhost",
            qwen_context_size=0,
        )

def test_invalid_qwen_threads():

    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://test",
            redis_url="redis://localhost",
            qwen_threads=0,
        )


def test_invalid_llm_provider():

    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://test",
            redis_url="redis://localhost",
            llm_provider="invalid-provider",
        )

@pytest.mark.parametrize(
    "provider",
    [
        LLMProviderType.QWEN,
        LLMProviderType.OPENAI,
        LLMProviderType.MOCK,
    ],
)
def test_valid_llm_providers(provider):

    settings = Settings(
        database_url="postgresql://test",
        redis_url="redis://localhost",
        llm_provider=provider,
    )

    assert settings.llm_provider == provider

def test_empty_openai_api_key_is_none(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://test",
    )
    monkeypatch.setenv(
        "REDIS_URL",
        "redis://localhost",
    )
    monkeypatch.setenv(
        "OPENAI_API_KEY",
        "",
    )

    settings = Settings()

    assert settings.openai_api_key is None

def test_openai_api_key_preserved(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://test",
    )
    monkeypatch.setenv(
        "REDIS_URL",
        "redis://localhost",
    )
    monkeypatch.setenv(
        "OPENAI_API_KEY",
        "test-api-key",
    )

    settings = Settings()

    assert settings.openai_api_key == "test-api-key"


