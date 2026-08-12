"""
Context construction and prompt-context models.

This package provides the components required to transform
retrieved document chunks into bounded, structured context
for downstream AI services.
"""

from app.context.builder import ContextBuilder
from app.context.models import (
    ContextBlock,
    ContextDocument,
    PromptContext,
)

__all__ = [
    "ContextBlock",
    "ContextDocument",
    "PromptContext",
    "ContextBuilder",
]
