"""
Tests for LLMService.
"""

from __future__ import annotations

from app.llm.base import LLMProvider
from app.llm.models import (
    LLMRequest,
    LLMResponse,
)
from app.llm.mock import MockLLMProvider
from app.prompt.models import Prompt
from app.services.llm import LLMService


class RecordingProvider(LLMProvider):
    """Test provider that records the received request."""

    def __init__(self) -> None:
        self.request: LLMRequest | None = None

    def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:

        self.request = request

        return LLMResponse(
            text="Recorded response.",
            model=request.model,
        )


class TestLLMService:
    """Tests for LLMService."""

    @staticmethod
    def create_prompt() -> Prompt:
        return Prompt(
            system_instruction=(
                "You are an investment analyst."
            ),
            user_content=(
                "Analyze this startup."
            ),
        )

    def test_default_provider_is_mock(self):

        service = LLMService()

        assert isinstance(
            service.provider,
            MockLLMProvider,
        )

    def test_provider_can_be_injected(self):

        provider = RecordingProvider()

        service = LLMService(
            provider=provider,
        )

        assert service.provider is provider

    def test_generate_returns_response(self):

        service = LLMService(
            provider=MockLLMProvider(
                response_text="Startup looks promising.",
            ),
        )

        response = service.generate(
            self.create_prompt(),
        )

        assert isinstance(
            response,
            LLMResponse,
        )

        assert response.text == (
            "Startup looks promising."
        )

    def test_prompt_is_converted_to_request(
        self,
    ):

        provider = RecordingProvider()

        service = LLMService(
            provider=provider,
        )

        service.generate(
            self.create_prompt(),
        )

        assert provider.request is not None

        assert len(provider.request.messages) == 2

        assert (
            provider.request.messages[0].role
            == "system"
        )

        assert (
            provider.request.messages[0].content
            == "You are an investment analyst."
        )

        assert (
            provider.request.messages[1].role
            == "user"
        )

        assert (
            provider.request.messages[1].content
            == "Analyze this startup."
        )

    def test_model_is_forwarded(self):

        provider = RecordingProvider()

        service = LLMService(
            provider=provider,
        )

        service.generate(
            self.create_prompt(),
            model="test-model",
        )

        assert provider.request is not None

        assert (
            provider.request.model
            == "test-model"
        )

    def test_temperature_is_forwarded(self):

        provider = RecordingProvider()

        service = LLMService(
            provider=provider,
        )

        service.generate(
            self.create_prompt(),
            temperature=0.7,
        )

        assert provider.request is not None

        assert (
            provider.request.temperature
            == 0.7
        )

    def test_max_tokens_is_forwarded(self):

        provider = RecordingProvider()

        service = LLMService(
            provider=provider,
        )

        service.generate(
            self.create_prompt(),
            max_tokens=1000,
        )

        assert provider.request is not None

        assert (
            provider.request.max_tokens
            == 1000
        )

    def test_provider_response_is_returned_unchanged(
        self,
    ):

        provider = MockLLMProvider(
            response_text="Exact provider response.",
        )

        service = LLMService(
            provider=provider,
        )

        response = service.generate(
            self.create_prompt(),
        )

        assert response.text == (
            "Exact provider response."
        )

    def test_provider_instance_takes_precedence_over_name(
        self,
    ):

        provider = RecordingProvider()

        service = LLMService(
            provider=provider,
            provider_name="mock",
        )

        assert service.provider is provider

    def test_factory_provider_name_is_used(self):

        service = LLMService(
            provider_name="mock",
        )

        assert isinstance(
            service.provider,
            MockLLMProvider,
        )
