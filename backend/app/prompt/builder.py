"""
Prompt builder.

Renders a provider-independent Prompt from a PromptTemplate
and structured PromptContext.
"""

from __future__ import annotations

from app.context.models import PromptContext
from app.prompt.models import Prompt, PromptTemplate


class PromptBuilder:
    """
    Build a deterministic Prompt from a template and context.

    The builder is provider-independent and does not perform
    retrieval or LLM invocation.
    """

    def __init__(
        self,
        template: PromptTemplate,
    ) -> None:
        self._template = template

    @property
    def template(self) -> PromptTemplate:
        """Return the configured prompt template."""
        return self._template

    def build(
        self,
        context: PromptContext,
    ) -> Prompt:
        """
        Render a prompt from the supplied context.
        """

        rendered_context = self._render_context(
            context,
        )

        user_content = self._render_user_template(
            context=context,
            rendered_context=rendered_context,
        )

        return Prompt(
            system_instruction=(
                self._template.system_instruction
            ),
            user_content=user_content,
        )

    def _render_user_template(
        self,
        *,
        context: PromptContext,
        rendered_context: str,
    ) -> str:
        """
        Render supported template placeholders.
        """

        try:
            return self._template.user_template.format(
                query=context.query,
                context=rendered_context,
            )
        except KeyError as exc:
            raise ValueError(
                f"Unsupported prompt template placeholder: "
                f"{exc.args[0]!r}"
            ) from exc

    @staticmethod
    def _render_context(
        context: PromptContext,
    ) -> str:
        """
        Render context blocks while preserving provenance.
        """

        if not context.blocks:
            return ""

        rendered_blocks: list[str] = []

        for block in context.blocks:
            rendered_blocks.append(
                "\n".join(
                    (
                        (
                            "[Document: "
                            f"{block.document_id} | "
                            "Chunk: "
                            f"{block.chunk_id} | "
                            "Relevance: "
                            f"{block.relevance:.4f}]"
                        ),
                        block.text,
                    )
                )
            )

        return "\n\n".join(
            rendered_blocks,
        )
