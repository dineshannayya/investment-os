"""
Load and route startup-specific investment evidence.

This service is deliberately deterministic.

Responsibilities:
    - load dimension_evidence.json
    - validate the JSON through DimensionEvidenceSet
    - retrieve evidence for a dimension
    - optionally validate dimension coverage against InvestmentScorecard

It does not:
    - evaluate evidence
    - calculate scores
    - calculate weights
    - generate risks
    - generate missing information
    - call an LLM
"""

from __future__ import annotations

import json
from pathlib import Path

from app.models.dimension_evidence import (
    DimensionEvidence,
    DimensionEvidenceSet,
)
from app.models.investment_scorecard import (
    InvestmentScorecard,
)


class DimensionEvidenceLoader:
    """
    Load and route dimension-specific startup evidence.
    """

    @staticmethod
    def load(
        path: Path,
    ) -> DimensionEvidenceSet:
        """
        Load and validate a dimension evidence JSON file.
        """

        if not path.exists():
            raise FileNotFoundError(
                f"Dimension evidence file not found: {path}"
            )

        if not path.is_file():
            raise ValueError(
                f"Dimension evidence path is not a file: {path}"
            )

        try:
            with path.open(
                "r",
                encoding="utf-8",
            ) as handle:
                payload = json.load(handle)

        except json.JSONDecodeError as exc:
            raise ValueError(
                "Invalid JSON in dimension evidence file: "
                f"{path}"
            ) from exc

        try:
            return DimensionEvidenceSet.model_validate(
                payload,
            )

        except Exception as exc:
            raise ValueError(
                "Invalid dimension evidence structure: "
                f"{path}"
            ) from exc

    @staticmethod
    def get_dimension_evidence(
        evidence_set: DimensionEvidenceSet,
        dimension_id: str,
    ) -> DimensionEvidence:
        """
        Return evidence for one dimension.

        A dimension with no configured evidence is represented by
        an empty DimensionEvidence object.
        """

        if not dimension_id:
            raise ValueError(
                "dimension_id must not be empty."
            )

        return evidence_set.dimensions.get(
            dimension_id,
            DimensionEvidence(),
        )

    @staticmethod
    def validate_dimension_coverage(
        *,
        scorecard: InvestmentScorecard,
        evidence_set: DimensionEvidenceSet,
    ) -> None:
        """
        Validate that evidence does not contain unknown dimensions.

        Missing evidence for a scorecard dimension is allowed.

        Unknown evidence dimensions are rejected because they usually
        indicate a typo or stale evidence artifact.
        """

        expected = {
            dimension.id
            for dimension in scorecard.dimensions
        }

        actual = set(evidence_set.dimensions)

        unexpected = sorted(
            actual - expected
        )

        if unexpected:
            raise ValueError(
                "Unexpected dimension evidence: "
                f"{unexpected}"
            )

    @classmethod
    def load_for_scorecard(
        cls,
        *,
        path: Path,
        scorecard: InvestmentScorecard,
    ) -> DimensionEvidenceSet:
        """
        Load evidence and validate its dimension IDs against a scorecard.
        """

        evidence_set = cls.load(path)

        cls.validate_dimension_coverage(
            scorecard=scorecard,
            evidence_set=evidence_set,
        )

        return evidence_set
