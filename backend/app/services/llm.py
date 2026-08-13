"""
Application service for LLM interactions.

This module coordinates prompt conversion, provider selection,
and LLM invocation without exposing provider-specific details
to the rest of the application.
"""

from __future__ import annotations

from app.llm import (
    LLMMessage,
    LLMRequest,
    LLMResponse,
)
from app.llm.factory import LLMFactory
from app.llm.base import LLMProvider
from app.prompt import Prompt


class LLMService:
    """
    Application service for generating LLM responses.
    """

    def __init__(
        self,
        provider: LLMProvider | None = None,
        *,
        provider_name: str = "mock",
    ) -> None:
        """
        Initialize the LLM service.

        Args:
            provider:
                Optional pre-configured provider. Primarily useful
                for dependency injection and testing.

            provider_name:
                Provider name used when no provider instance is
                supplied.
        """

        if provider is not None:
            self._provider = provider
        else:
            self._provider = LLMFactory.create(
                provider_name,
            )

    @property
    def provider(self) -> LLMProvider:
        """Return the configured LLM provider."""
        return self._provider

    def generate(
        self,
        prompt: Prompt,
        *,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """
        Generate an LLM response from a rendered prompt.

        Args:
            prompt:
                Fully rendered provider-independent prompt.

            model:
                Optional model override.

            temperature:
                Sampling temperature.

            max_tokens:
                Optional maximum output token count.

        Returns:
            Normalized LLM response.
        """

        request = LLMRequest(
            messages=(
                LLMMessage(
                    role="system",
                    content=prompt.system_instruction,
                ),
                LLMMessage(
                    role="user",
                    content=prompt.user_content,
                ),
            ),
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return self._provider.generate(
            request,
        )
