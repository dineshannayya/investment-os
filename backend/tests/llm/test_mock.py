"""
Tests for MockLLMProvider.
"""

from __future__ import annotations

import pytest

from app.llm.mock import MockLLMProvider
from app.llm.models import (
    LLMMessage,
    LLMRequest,
    LLMResponse,
)

from app.llm.base import LLMProvider


class TestMockLLMProvider:
    """Tests for MockLLMProvider."""

    @staticmethod
    def create_request(
        model: str | None = None,
    ) -> LLMRequest:
        return LLMRequest(
            messages=(
                LLMMessage(
                    role="user",
                    content="Analyze this startup.",
                ),
            ),
            model=model,
        )

    def test_default_response(self):

        provider = MockLLMProvider()

        assert (
            provider.response_text
            == "Mock LLM response."
        )

    def test_custom_response(self):

        provider = MockLLMProvider(
            response_text="Custom test response.",
        )

        assert (
            provider.response_text
            == "Custom test response."
        )

    def test_empty_response_is_rejected(self):

        with pytest.raises(
            ValueError,
            match="response_text must not be empty",
        ):
            MockLLMProvider(
                response_text="",
            )

    def test_generate_returns_llm_response(self):

        provider = MockLLMProvider(
            response_text="Test analysis.",
        )

        response = provider.generate(
            self.create_request(),
        )

        assert isinstance(
            response,
            LLMResponse,
        )

        assert response.text == "Test analysis."

    def test_generate_preserves_requested_model(self):

        provider = MockLLMProvider(
            response_text="Test analysis.",
        )

        response = provider.generate(
            self.create_request(
                model="test-model",
            ),
        )

        assert response.model == "test-model"

    def test_generate_without_model(self):

        provider = MockLLMProvider(
            response_text="Test analysis.",
        )

        response = provider.generate(
            self.create_request(),
        )

        assert response.model is None

    def test_generate_returns_zero_usage(self):

        provider = MockLLMProvider(
            response_text="Test analysis.",
        )

        response = provider.generate(
            self.create_request(),
        )

        assert response.usage.prompt_tokens == 0
        assert response.usage.completion_tokens == 0
        assert response.usage.total_tokens == 0

    def test_generate_marks_mock_provider(self):

        provider = MockLLMProvider(
            response_text="Test analysis.",
        )

        response = provider.generate(
            self.create_request(),
        )

        assert response.metadata["provider"] == "mock"

    def test_multiple_requests_are_deterministic(self):

        provider = MockLLMProvider(
            response_text="Deterministic response.",
        )

        first = provider.generate(
            self.create_request(),
        )

        second = provider.generate(
            self.create_request(),
        )

        assert first == second

    def test_different_requests_use_same_configured_response(
        self,
    ):

        provider = MockLLMProvider(
            response_text="Configured response.",
        )

        first_request = LLMRequest(
            messages=(
                LLMMessage(
                    role="user",
                    content="Analyze financials.",
                ),
            ),
        )

        second_request = LLMRequest(
            messages=(
                LLMMessage(
                    role="user",
                    content="Analyze founders.",
                ),
            ),
        )

        first = provider.generate(first_request)
        second = provider.generate(second_request)

        assert first.text == "Configured response."
        assert second.text == "Configured response."

    def test_implements_llm_provider(self):
    
        provider = MockLLMProvider()
    
        assert isinstance(
            provider,
            LLMProvider,
        )

