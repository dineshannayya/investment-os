"""
Tests for provider-independent prompt domain models.
"""

from __future__ import annotations

from types import MappingProxyType

import pytest

from app.prompt.models import (
    Prompt,
    PromptTemplate,
)


class TestPromptTemplate:
    """Tests for PromptTemplate."""

    def test_create(self):

        template = PromptTemplate(
            system_instruction=(
                "You are an investment analyst."
            ),
            user_template=(
                "Question:\n{query}\n\n"
                "Context:\n{context}"
            ),
        )

        assert (
            template.system_instruction
            == "You are an investment analyst."
        )

        assert (
            template.user_template
            == "Question:\n{query}\n\n"
            "Context:\n{context}"
        )

    def test_empty_system_instruction(self):

        with pytest.raises(
            ValueError,
            match="system_instruction must not be empty",
        ):
            PromptTemplate(
                system_instruction="",
                user_template="Analyze {context}",
            )

    def test_empty_user_template(self):

        with pytest.raises(
            ValueError,
            match="user_template must not be empty",
        ):
            PromptTemplate(
                system_instruction="You are an analyst.",
                user_template="",
            )

    def test_metadata_default_is_immutable(self):

        template = PromptTemplate(
            system_instruction="You are an analyst.",
            user_template="Analyze {context}",
        )

        assert template.metadata == {}

        assert isinstance(
            template.metadata,
            MappingProxyType,
        )

        with pytest.raises(TypeError):
            template.metadata["key"] = "value"

    def test_metadata_is_immutable(self):

        template = PromptTemplate(
            system_instruction="You are an analyst.",
            user_template="Analyze {context}",
            metadata={
                "version": "v1",
            },
        )

        assert template.metadata["version"] == "v1"

        with pytest.raises(TypeError):
            template.metadata["version"] = "v2"

    def test_metadata_is_detached_from_source(self):

        metadata = {
            "version": "v1",
        }

        template = PromptTemplate(
            system_instruction="You are an analyst.",
            user_template="Analyze {context}",
            metadata=metadata,
        )

        metadata["version"] = "v2"

        assert template.metadata["version"] == "v1"

    def test_frozen(self):

        template = PromptTemplate(
            system_instruction="You are an analyst.",
            user_template="Analyze {context}",
        )

        with pytest.raises(AttributeError):
            template.system_instruction = "Changed"


class TestPrompt:
    """Tests for Prompt."""

    def test_create(self):

        prompt = Prompt(
            system_instruction=(
                "You are an investment analyst."
            ),
            user_content=(
                "Analyze this startup."
            ),
        )

        assert (
            prompt.system_instruction
            == "You are an investment analyst."
        )

        assert (
            prompt.user_content
            == "Analyze this startup."
        )

    def test_empty_system_instruction(self):

        with pytest.raises(
            ValueError,
            match="system_instruction must not be empty",
        ):
            Prompt(
                system_instruction="",
                user_content="Analyze this startup.",
            )

    def test_empty_user_content(self):

        with pytest.raises(
            ValueError,
            match="user_content must not be empty",
        ):
            Prompt(
                system_instruction="You are an analyst.",
                user_content="",
            )

    def test_frozen(self):

        prompt = Prompt(
            system_instruction="You are an analyst.",
            user_content="Analyze this startup.",
        )

        with pytest.raises(AttributeError):
            prompt.user_content = "Changed"
