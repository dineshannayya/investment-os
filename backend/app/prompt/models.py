"""
Provider-independent prompt domain models.

These models represent prompt templates and rendered prompts
without coupling the prompt layer to any specific LLM provider.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any


@dataclass(slots=True, frozen=True)
class PromptTemplate:
    """
    Template used to construct a prompt.

    ``user_template`` may contain placeholders that are resolved
    by PromptBuilder.
    """

    system_instruction: str

    user_template: str

    metadata: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({}),
    )

    def __post_init__(self) -> None:
        if not self.system_instruction:
            raise ValueError(
                "system_instruction must not be empty."
            )

        if not self.user_template:
            raise ValueError(
                "user_template must not be empty."
            )

        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata)),
        )


@dataclass(slots=True, frozen=True)
class Prompt:
    """
    A fully rendered prompt ready for conversion into
    provider-independent LLM messages.
    """

    system_instruction: str

    user_content: str

    def __post_init__(self) -> None:
        if not self.system_instruction:
            raise ValueError(
                "system_instruction must not be empty."
            )

        if not self.user_content:
            raise ValueError(
                "user_content must not be empty."
            )
