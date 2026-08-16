"""
Tests for production startup-analysis execution configuration.
"""

from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import pytest

from app.models.analysis import StartupAnalysisMode
from app.services.startup_analysis_config import (
    ANALYSIS_VERSION,
    DEEP_MAX_TOKENS,
    STANDARD_MAX_TOKENS,
    StartupAnalysisConfig,
    get_startup_analysis_config,
)


@pytest.fixture
def settings():
    """Minimal settings required by the startup-analysis config."""
    return SimpleNamespace(
        llm_model="Qwen3-8B-Q4_K_M",
        startup_analysis_temperature=0.0,
    )


# ---------------------------------------------------------------------------
# Mode configuration
# ---------------------------------------------------------------------------


def test_standard_mode(settings):
    config = get_startup_analysis_config(
        StartupAnalysisMode.STANDARD,
        config=settings,
    )

    assert config.mode == StartupAnalysisMode.STANDARD
    assert config.model_name == "Qwen3-8B-Q4_K_M"
    assert config.thinking_enabled is False
    assert config.max_tokens == STANDARD_MAX_TOKENS
    assert config.temperature == 0.0
    assert config.analysis_version == ANALYSIS_VERSION


def test_deep_mode(settings):
    config = get_startup_analysis_config(
        StartupAnalysisMode.DEEP,
        config=settings,
    )

    assert config.mode == StartupAnalysisMode.DEEP
    assert config.model_name == "Qwen3-8B-Q4_K_M"
    assert config.thinking_enabled is True
    assert config.max_tokens == DEEP_MAX_TOKENS
    assert config.temperature == 0.0
    assert config.analysis_version == ANALYSIS_VERSION


def test_standard_mode_uses_768_max_tokens(settings):
    config = get_startup_analysis_config(
        StartupAnalysisMode.STANDARD,
        config=settings,
    )

    assert config.max_tokens == 768


def test_deep_mode_uses_1024_max_tokens(settings):
    config = get_startup_analysis_config(
        StartupAnalysisMode.DEEP,
        config=settings,
    )

    assert config.max_tokens == 1024


def test_standard_mode_disables_thinking(settings):
    config = get_startup_analysis_config(
        StartupAnalysisMode.STANDARD,
        config=settings,
    )

    assert config.thinking_enabled is False


def test_deep_mode_enables_thinking(settings):
    config = get_startup_analysis_config(
        StartupAnalysisMode.DEEP,
        config=settings,
    )

    assert config.thinking_enabled is True


# ---------------------------------------------------------------------------
# Application settings
# ---------------------------------------------------------------------------


def test_model_name_comes_from_settings(settings):
    settings.llm_model = "Qwen3-8B-Q4_K_M"

    config = get_startup_analysis_config(
        StartupAnalysisMode.STANDARD,
        config=settings,
    )

    assert config.model_name == settings.llm_model


def test_temperature_comes_from_settings(settings):
    settings.startup_analysis_temperature = 0.25

    config = get_startup_analysis_config(
        StartupAnalysisMode.STANDARD,
        config=settings,
    )

    assert config.temperature == 0.25


def test_temperature_is_shared_by_standard_and_deep(settings):
    settings.startup_analysis_temperature = 0.0

    standard = get_startup_analysis_config(
        StartupAnalysisMode.STANDARD,
        config=settings,
    )
    deep = get_startup_analysis_config(
        StartupAnalysisMode.DEEP,
        config=settings,
    )

    assert standard.temperature == deep.temperature == 0.0


# ---------------------------------------------------------------------------
# Configuration metadata
# ---------------------------------------------------------------------------


def test_analysis_version_is_production_version(settings):
    standard = get_startup_analysis_config(
        StartupAnalysisMode.STANDARD,
        config=settings,
    )
    deep = get_startup_analysis_config(
        StartupAnalysisMode.DEEP,
        config=settings,
    )

    assert standard.analysis_version == "3.7.5"
    assert deep.analysis_version == "3.7.5"


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------


def test_configuration_is_immutable(settings):
    config = get_startup_analysis_config(
        StartupAnalysisMode.STANDARD,
        config=settings,
    )

    with pytest.raises(FrozenInstanceError):
        config.max_tokens = 4096


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rejects_empty_model_name():
    with pytest.raises(
        ValueError,
        match="model_name must not be empty",
    ):
        StartupAnalysisConfig(
            mode=StartupAnalysisMode.STANDARD,
            model_name="",
            thinking_enabled=False,
            max_tokens=768,
            temperature=0.0,
        )


def test_rejects_non_positive_max_tokens():
    with pytest.raises(
        ValueError,
        match="max_tokens must be greater than zero",
    ):
        StartupAnalysisConfig(
            mode=StartupAnalysisMode.STANDARD,
            model_name="Qwen3-8B-Q4_K_M",
            thinking_enabled=False,
            max_tokens=0,
            temperature=0.0,
        )


@pytest.mark.parametrize(
    "temperature",
    [-0.1, 2.1],
)
def test_rejects_invalid_temperature(temperature):
    with pytest.raises(
        ValueError,
        match="temperature must be between 0.0 and 2.0",
    ):
        StartupAnalysisConfig(
            mode=StartupAnalysisMode.STANDARD,
            model_name="Qwen3-8B-Q4_K_M",
            thinking_enabled=False,
            max_tokens=768,
            temperature=temperature,
        )


def test_rejects_empty_analysis_version():
    with pytest.raises(
        ValueError,
        match="analysis_version must not be empty",
    ):
        StartupAnalysisConfig(
            mode=StartupAnalysisMode.STANDARD,
            model_name="Qwen3-8B-Q4_K_M",
            thinking_enabled=False,
            max_tokens=768,
            temperature=0.0,
            analysis_version="",
        )


# ---------------------------------------------------------------------------
# Unsupported mode
# ---------------------------------------------------------------------------


def test_rejects_unsupported_mode(settings):
    with pytest.raises(
        ValueError,
        match="Unsupported startup analysis mode",
    ):
        get_startup_analysis_config(
            "unsupported",
            config=settings,
        )
