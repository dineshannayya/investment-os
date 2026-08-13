"""
Factory for creating LLM provider instances.

The factory maps provider names to concrete implementations
without exposing provider-specific details to callers.
"""

from __future__ import annotations

from typing import Final

from app.llm.base import LLMProvider
from app.llm.mock import MockLLMProvider


class LLMFactory:
    """
    Factory for creating configured LLM providers.
    """

    _PROVIDERS: Final = {
        "mock": MockLLMProvider,
    }

    @classmethod
    def create(
        cls,
        provider: str,
    ) -> LLMProvider:
        """
        Create an LLM provider by name.

        Args:
            provider: Provider identifier.

        Returns:
            Configured LLMProvider instance.

        Raises:
            ValueError:
                If the provider is not registered.
        """

        provider_name = provider.strip().lower()

        if not provider_name:
            raise ValueError(
                "LLM provider name must not be empty."
            )

        provider_class = cls._PROVIDERS.get(
            provider_name,
        )

        if provider_class is None:
            raise ValueError(
                f"Unsupported LLM provider: "
                f"{provider!r}"
            )

        return provider_class()
