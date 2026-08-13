"""
Tests for PromptBuilder.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.context.models import (
    ContextBlock,
    PromptContext,
)
from app.prompt.builder import PromptBuilder
from app.prompt.models import (
    Prompt,
    PromptTemplate,
)


class TestPromptBuilder:
    """Tests for PromptBuilder."""

    @staticmethod
    def create_template(
        *,
        system_instruction: str = (
            "You are an investment analyst."
        ),
        user_template: str = (
            "Question:\n{query}\n\n"
            "Evidence:\n{context}"
        ),
    ) -> PromptTemplate:

        return PromptTemplate(
            system_instruction=system_instruction,
            user_template=user_template,
        )

    @staticmethod
    def create_block(
        *,
        text: str = "Revenue increased by 35%.",
        relevance: float = 0.92,
        document_id=None,
        chunk_id=None,
    ) -> ContextBlock:

        return ContextBlock(
            document_id=document_id or uuid4(),
            chunk_id=chunk_id or uuid4(),
            text=text,
            relevance=relevance,
        )

    @staticmethod
    def create_context(
        *,
        query: str = "What are the financial risks?",
        blocks: tuple[ContextBlock, ...] = (),
    ) -> PromptContext:

        return PromptContext(
            query=query,
            blocks=blocks,
        )

    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------

    def test_template_is_exposed(self):

        template = self.create_template()

        builder = PromptBuilder(
            template,
        )

        assert builder.template is template

    # ------------------------------------------------------------------
    # Basic rendering
    # ------------------------------------------------------------------

    def test_build_returns_prompt(self):

        builder = PromptBuilder(
            self.create_template(),
        )

        context = self.create_context()

        prompt = builder.build(context)

        assert isinstance(
            prompt,
            Prompt,
        )

    def test_system_instruction_is_preserved(self):

        template = self.create_template(
            system_instruction=(
                "You are a senior investment analyst."
            ),
        )

        builder = PromptBuilder(template)

        prompt = builder.build(
            self.create_context(),
        )

        assert (
            prompt.system_instruction
            == "You are a senior investment analyst."
        )

    def test_query_is_rendered(self):

        builder = PromptBuilder(
            self.create_template(),
        )

        context = self.create_context(
            query="Should we invest in this company?",
        )

        prompt = builder.build(context)

        assert (
            "Should we invest in this company?"
            in prompt.user_content
        )

    # ------------------------------------------------------------------
    # Context rendering
    # ------------------------------------------------------------------

    def test_context_is_rendered(self):

        block = self.create_block(
            text="Revenue increased by 35%.",
        )

        builder = PromptBuilder(
            self.create_template(),
        )

        prompt = builder.build(
            self.create_context(
                blocks=(block,),
            ),
        )

        assert (
            "Revenue increased by 35%."
            in prompt.user_content
        )

    def test_context_provenance_is_rendered(
        self,
    ):

        document_id = uuid4()
        chunk_id = uuid4()

        block = self.create_block(
            document_id=document_id,
            chunk_id=chunk_id,
            relevance=0.9234,
        )

        builder = PromptBuilder(
            self.create_template(),
        )

        prompt = builder.build(
            self.create_context(
                blocks=(block,),
            ),
        )

        assert (
            f"Document: {document_id}"
            in prompt.user_content
        )

        assert (
            f"Chunk: {chunk_id}"
            in prompt.user_content
        )

        assert (
            "Relevance: 0.9234"
            in prompt.user_content
        )

    def test_multiple_blocks_are_rendered_in_order(
        self,
    ):

        first = self.create_block(
            text="First evidence.",
            relevance=0.95,
        )

        second = self.create_block(
            text="Second evidence.",
            relevance=0.85,
        )

        third = self.create_block(
            text="Third evidence.",
            relevance=0.75,
        )

        builder = PromptBuilder(
            self.create_template(),
        )

        prompt = builder.build(
            self.create_context(
                blocks=(
                    first,
                    second,
                    third,
                ),
            ),
        )

        first_position = prompt.user_content.index(
            "First evidence.",
        )

        second_position = prompt.user_content.index(
            "Second evidence.",
        )

        third_position = prompt.user_content.index(
            "Third evidence.",
        )

        assert first_position < second_position
        assert second_position < third_position

    def test_multiple_blocks_are_separated(self):

        first = self.create_block(
            text="First evidence.",
        )

        second = self.create_block(
            text="Second evidence.",
        )

        builder = PromptBuilder(
            self.create_template(),
        )

        prompt = builder.build(
            self.create_context(
                blocks=(
                    first,
                    second,
                ),
            ),
        )

        assert (
            "First evidence.\n\n"
            in prompt.user_content
        )

    # ------------------------------------------------------------------
    # Empty context
    # ------------------------------------------------------------------

    def test_empty_context_renders_empty_context_value(
        self,
    ):

        template = self.create_template(
            user_template=(
                "Question: {query}\n"
                "Context: [{context}]"
            ),
        )

        builder = PromptBuilder(template)

        prompt = builder.build(
            self.create_context(
                blocks=(),
            ),
        )

        assert (
            prompt.user_content
            == "Question: What are the financial risks?\n"
            "Context: []"
        )

    # ------------------------------------------------------------------
    # Determinism
    # ------------------------------------------------------------------

    def test_build_is_deterministic(self):

        document_id = uuid4()
        chunk_id = uuid4()

        block = self.create_block(
            document_id=document_id,
            chunk_id=chunk_id,
            text="Deterministic evidence.",
            relevance=0.91,
        )

        context = self.create_context(
            query="Analyze the company.",
            blocks=(block,),
        )

        builder = PromptBuilder(
            self.create_template(),
        )

        first = builder.build(context)
        second = builder.build(context)

        assert first == second

    # ------------------------------------------------------------------
    # Special characters
    # ------------------------------------------------------------------

    def test_special_characters_are_preserved(self):

        block = self.create_block(
            text=(
                "Revenue grew 35% & EBITDA improved "
                "from ₹10Cr to ₹14Cr."
            ),
        )

        builder = PromptBuilder(
            self.create_template(),
        )

        prompt = builder.build(
            self.create_context(
                query="Assess growth & profitability.",
                blocks=(block,),
            ),
        )

        assert (
            "Revenue grew 35% & EBITDA improved "
            "from ₹10Cr to ₹14Cr."
            in prompt.user_content
        )

        assert (
            "Assess growth & profitability."
            in prompt.user_content
        )

    # ------------------------------------------------------------------
    # Unsupported placeholders
    # ------------------------------------------------------------------

    def test_unsupported_placeholder_raises_value_error(
        self,
    ):

        template = self.create_template(
            user_template=(
                "Startup: {startup_name}\n"
                "Context: {context}"
            ),
        )

        builder = PromptBuilder(template)

        with pytest.raises(
            ValueError,
            match="Unsupported prompt template placeholder",
        ):
            builder.build(
                self.create_context(),
            )

    # ------------------------------------------------------------------
    # Prompt immutability
    # ------------------------------------------------------------------

    def test_result_is_immutable(self):

        builder = PromptBuilder(
            self.create_template(),
        )

        prompt = builder.build(
            self.create_context(),
        )

        with pytest.raises(AttributeError):
            prompt.user_content = "Changed"
