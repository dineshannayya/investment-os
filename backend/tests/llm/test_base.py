"""
Tests for the LLM provider abstraction.
"""

from __future__ import annotations

import pytest

from app.llm.base import LLMProvider
from app.llm.models import (
    LLMMessage,
    LLMRequest,
    LLMResponse,
)


class TestLLMProvider:
    """Tests for LLMProvider."""

    @staticmethod
    def create_request() -> LLMRequest:
        return LLMRequest(
            messages=(
                LLMMessage(
                    role="user",
                    content="Analyze this startup.",
                ),
            ),
        )

    def test_provider_is_abstract(self):

        with pytest.raises(TypeError):
            LLMProvider()

    def test_concrete_provider_can_be_instantiated(self):

        class TestProvider(LLMProvider):

            def generate(
                self,
                request: LLMRequest,
            ) -> LLMResponse:
                return LLMResponse(
                    text="Test response",
                )

        provider = TestProvider()

        assert isinstance(
            provider,
            LLMProvider,
        )

    def test_generate_receives_request(self):

        received_request = None

        class TestProvider(LLMProvider):

            def generate(
                self,
                request: LLMRequest,
            ) -> LLMResponse:

                nonlocal received_request
                received_request = request

                return LLMResponse(
                    text="Test response",
                )

        provider = TestProvider()
        request = self.create_request()

        provider.generate(request)

        assert received_request is request

    def test_generate_returns_llm_response(self):

        expected_response = LLMResponse(
            text="Startup has moderate investment risk.",
        )

        class TestProvider(LLMProvider):

            def generate(
                self,
                request: LLMRequest,
            ) -> LLMResponse:
                return expected_response

        provider = TestProvider()

        response = provider.generate(
            self.create_request(),
        )

        assert response is expected_response

    def test_provider_can_use_request_content(self):

        class TestProvider(LLMProvider):

            def generate(
                self,
                request: LLMRequest,
            ) -> LLMResponse:

                content = request.messages[0].content

                return LLMResponse(
                    text=f"Received: {content}",
                )

        provider = TestProvider()

        response = provider.generate(
            LLMRequest(
                messages=(
                    LLMMessage(
                        role="user",
                        content="Evaluate founder risk.",
                    ),
                ),
            ),
        )

        assert response.text == (
            "Received: Evaluate founder risk."
        )

    def test_incomplete_provider_cannot_be_instantiated(
        self,
    ):

        class IncompleteProvider(LLMProvider):
            pass

        with pytest.raises(TypeError):
            IncompleteProvider()
