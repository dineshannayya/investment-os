"""
Base abstractions for LLM providers.

This module defines the provider-independent interface used by
the LLM service layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.llm.models import LLMRequest, LLMResponse


class LLMProvider(ABC):
    """
    Abstract interface for an LLM provider.

    Concrete providers implement ``generate`` without exposing
    provider-specific details to the application layer.
    """

    @abstractmethod
    def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """
        Generate an LLM response for the supplied request.

        Args:
            request: Provider-independent LLM request.

        Returns:
            Normalized LLM response.

        Raises:
            NotImplementedError:
                If a concrete provider does not implement this method.
        """

        raise NotImplementedError
