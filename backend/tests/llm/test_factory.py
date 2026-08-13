"""
Tests for the LLM provider factory.
"""

from __future__ import annotations

import pytest

from app.llm.base import LLMProvider
from app.llm.factory import LLMFactory
from app.llm.mock import MockLLMProvider


class TestLLMFactory:
    """Tests for LLMFactory."""

    def test_create_mock_provider(self):

        provider = LLMFactory.create(
            "mock",
        )

        assert isinstance(
            provider,
            MockLLMProvider,
        )

    def test_created_provider_implements_interface(
        self,
    ):

        provider = LLMFactory.create(
            "mock",
        )

        assert isinstance(
            provider,
            LLMProvider,
        )

    @pytest.mark.parametrize(
        "provider_name",
        [
            "MOCK",
            "Mock",
            " mock ",
            "MoCk",
        ],
    )
    def test_provider_name_is_normalized(
        self,
        provider_name,
    ):

        provider = LLMFactory.create(
            provider_name,
        )

        assert isinstance(
            provider,
            MockLLMProvider,
        )

    def test_unknown_provider_is_rejected(self):

        with pytest.raises(
            ValueError,
            match="Unsupported LLM provider",
        ):
            LLMFactory.create(
                "unknown",
            )

    def test_empty_provider_is_rejected(self):

        with pytest.raises(
            ValueError,
            match="provider name must not be empty",
        ):
            LLMFactory.create("")

    def test_whitespace_provider_is_rejected(self):

        with pytest.raises(
            ValueError,
            match="provider name must not be empty",
        ):
            LLMFactory.create("   ")

    def test_each_create_returns_new_instance(self):

        first = LLMFactory.create("mock")
        second = LLMFactory.create("mock")

        assert isinstance(
            first,
            MockLLMProvider,
        )

        assert isinstance(
            second,
            MockLLMProvider,
        )

        assert first is not second
