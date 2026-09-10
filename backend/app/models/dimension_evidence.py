"""
Structured startup evidence used for dimension-level investment evaluation.

This module contains evidence only.

It does not contain:
    - scores
    - confidence
    - weights
    - risks
    - missing information
    - investment conclusions
    - LLM logic
    - scorecard logic
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DimensionEvidenceItem(BaseModel):
    """One canonical evidence item assigned to an investment dimension."""

    model_config = ConfigDict(extra="forbid")

    evidence_ref: str = Field(min_length=1)
    observation: str = Field(min_length=1)
    source_type: str = Field(min_length=1)

    @field_validator("evidence_ref", "observation", "source_type")
    @classmethod
    def _reject_blank_strings(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value


class DimensionEvidence(BaseModel):
    """Evidence assigned to one investment scorecard dimension."""

    model_config = ConfigDict(extra="forbid")

    evidence: list[DimensionEvidenceItem] = Field(default_factory=list)

    @field_validator("evidence")
    @classmethod
    def _validate_unique_evidence_refs(
        cls,
        value: list[DimensionEvidenceItem],
    ) -> list[DimensionEvidenceItem]:
        refs = [item.evidence_ref for item in value]

        if len(refs) != len(set(refs)):
            raise ValueError(
                "duplicate evidence_ref within a dimension is not allowed"
            )

        return value


class DimensionEvidenceSet(BaseModel):
    """
    Complete dimension-scoped evidence set for one startup.

    Evidence may legitimately appear in multiple dimensions. The same
    evidence_ref is therefore only required to be unique within an
    individual dimension.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(min_length=1)
    startup: str = Field(min_length=1)
    dimensions: dict[str, DimensionEvidence] = Field(
        default_factory=dict
    )

    @field_validator("schema_version", "startup")
    @classmethod
    def _reject_blank_metadata(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value

    @field_validator("dimensions")
    @classmethod
    def _validate_dimension_ids(
        cls,
        value: dict[str, DimensionEvidence],
    ) -> dict[str, DimensionEvidence]:
        for dimension_id in value:
            if not dimension_id.strip():
                raise ValueError(
                    "dimension_id must not be blank"
                )

        return value


__all__ = [
    "DimensionEvidence",
    "DimensionEvidenceItem",
    "DimensionEvidenceSet",
]
