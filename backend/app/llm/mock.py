"""
Deterministic mock LLM provider.

This provider is intended for unit and integration testing.
It performs no network calls and has no dependency on a
specific LLM vendor.
"""

from __future__ import annotations

from app.llm.base import LLMProvider
from app.llm.models import (
    LLMRequest,
    LLMResponse,
    LLMUsage,
)


class MockLLMProvider(LLMProvider):
    """
    Deterministic LLM provider for testing.

    The provider returns a configured response regardless of
    the request content.
    """

    def __init__(
        self,
        response_text: str = "Mock LLM response.",
    ) -> None:
        if not response_text:
            raise ValueError(
                "response_text must not be empty."
            )

        self._response_text = response_text

    @property
    def response_text(self) -> str:
        """Return the configured mock response."""
        return self._response_text

    def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """
        Generate a deterministic mock response.

        The request is accepted to satisfy the LLMProvider
        contract but is not sent anywhere.
        """

        return LLMResponse(
            text=self._response_text,
            model=request.model,
            usage=LLMUsage(),
            metadata={
                "provider": "mock",
            },
        )
