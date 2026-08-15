"""
Provider-independent LLM domain models.

These models define the application-level contract between
the prompt/LLM service layer and concrete LLM providers.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any


@dataclass(slots=True, frozen=True)
class LLMMessage:
    """
    A single message in an LLM conversation.
    """

    role: str
    content: str

    def __post_init__(self) -> None:
        if self.role not in {
            "system",
            "user",
            "assistant",
        }:
            raise ValueError(
                f"Unsupported message role: {self.role!r}"
            )

        if not self.content:
            raise ValueError(
                "Message content must not be empty."
            )


@dataclass(slots=True, frozen=True)
class LLMUsage:
    """
    Token usage reported by an LLM provider.
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __post_init__(self) -> None:
        if self.prompt_tokens < 0:
            raise ValueError(
                "prompt_tokens must be non-negative."
            )

        if self.completion_tokens < 0:
            raise ValueError(
                "completion_tokens must be non-negative."
            )

        if self.total_tokens < 0:
            raise ValueError(
                "total_tokens must be non-negative."
            )


@dataclass(slots=True, frozen=True)
class LLMRequest:
    """
    Provider-independent LLM generation request.
    """

    messages: tuple[LLMMessage, ...]

    model: str | None = None

    temperature: float = 0.0

    max_tokens: int | None = None

    metadata: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({}),
    )

    def __post_init__(self) -> None:
        if not self.messages:
            raise ValueError(
                "LLMRequest must contain at least one message."
            )

        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(
                "temperature must be between 0.0 and 2.0."
            )

        if (
            self.max_tokens is not None
            and self.max_tokens <= 0
        ):
            raise ValueError(
                "max_tokens must be greater than zero."
            )

        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata)),
        )


@dataclass(slots=True, frozen=True)
class LLMResponse:
    """
    Normalized response returned by an LLM provider.
    """

    text: str

    model: str | None = None

    finish_reason: str | None = None

    usage: LLMUsage = field(
        default_factory=LLMUsage,
    )

    metadata: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({}),
    )

    def __post_init__(self) -> None:
        if not self.text:
            raise ValueError(
                "LLMResponse text must not be empty."
            )

        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata)),
        )
