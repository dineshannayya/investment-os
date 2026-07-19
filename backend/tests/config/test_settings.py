import pytest
from pydantic import ValidationError
from app.config.settings import Settings,get_settings

# ============================================================
# Default Configuration
# ============================================================

def test_default_settings():
    settings = Settings(
        database_url="postgresql://test",
        redis_url="redis://localhost"
    )

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
    settings = Settings(
        database_url="postgresql://test",
        redis_url="redis://localhost"
    )

    assert settings.log_level == "INFO"
