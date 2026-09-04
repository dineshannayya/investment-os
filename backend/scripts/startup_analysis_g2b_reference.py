"""
G.2-B Production Reference
--------------------------

Purpose:
    Reference implementation for validating the production startup-analysis
    source-of-truth, extraction, 10-point investment baseline, 3.7.x analysis,
    persistence, evidence contract, and provenance.

This is a verification/reference script, NOT the application entry point.

Canonical production paths:
    - Existing 10-point investment runner:
        scripts.run_startup_investment_analysis.run_analysis()

    - New 3.7.x analysis:
        StartupAnalysisApplicationService

Important:
    The established JSON-driven 10-point score remains the investment
    scorecard source of truth. The 3.7.x analysis is validated separately.
"""

from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from app.core.database.session import create_session
from app.models.analysis import StartupAnalysisMode
from app.models.startup import Startup
from app.services.source_discovery import SourceDiscoveryService
from app.services.source_extraction_persistence import (
    SourceExtractionPersistenceService,
)
from app.services.startup_analysis_application import (
    StartupAnalysisApplicationService,
)

from scripts.run_startup_investment_analysis import run_analysis


STARTUP_ID = UUID(
    "dbb520d7-0979-4db3-8464-523f5710455f"
)

STARTUP_KEY = "restomart"

DATA_ROOT = Path(
    "/opt/investment-os/data/real_startups"
)

BASE = DATA_ROOT / STARTUP_KEY

SCORECARD_PATH = (
    BASE / "investment_scorecard.json"
)

EVIDENCE_PATH = (
    BASE / "dimension_evidence.json"
)

EXPECTED_SOURCES = 18
EXPECTED_DIMENSIONS = 10
EXPECTED_WEIGHT = 100
EXPECTED_SCORE = 78.05
EXPECTED_DECISION = "conditional"
EXPECTED_EVIDENCE = 48


def banner(title: str) -> None:
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def main() -> int:
    banner(
        "G.2-B PRODUCTION REFERENCE — "
        "10-POINT + 3.7.x SOURCE-OF-TRUTH VALIDATION"
    )

    session = create_session()

    try:
        # ------------------------------------------------------------------
        # 1. Investment source of truth
        # ------------------------------------------------------------------

        print()
        print("LOCAL INVESTMENT SOURCE-OF-TRUTH")
        print("-" * 100)

        print(f"Scorecard : {SCORECARD_PATH}")
        print(f"Evidence  : {EVIDENCE_PATH}")

        assert SCORECARD_PATH.exists(), (
            f"Missing scorecard: {SCORECARD_PATH}"
        )

        assert EVIDENCE_PATH.exists(), (
            f"Missing evidence: {EVIDENCE_PATH}"
        )

        # ------------------------------------------------------------------
        # 2. Resolve startup
        # ------------------------------------------------------------------

        startup = session.scalar(
            select(Startup).where(
                Startup.id == STARTUP_ID
            )
        )

        assert startup is not None, (
            f"Startup not found: {STARTUP_ID}"
        )

        print()
        print("STARTUP")
        print("-" * 100)
        print(f"Startup ID   : {startup.id}")
        print(f"Startup name : {startup.name}")

        # ------------------------------------------------------------------
        # 3. Current source baseline
        #
        # IMPORTANT:
        # Use canonical startup UUID for source identity.
        #
        # This is the identity convention now used by the production
        # StartupAnalysisApplicationService.
        # ------------------------------------------------------------------

        print()
        print("CURRENT SOURCE BASELINE")
        print("-" * 100)

        source_root = BASE / "sources"

        discovered = SourceDiscoveryService().discover(
            startup_id=str(STARTUP_ID),
            source_root=source_root,
        )

        current_source_ids = {
            str(document.source_id)
            for document in discovered
        }

        print(
            f"Current sources    : {len(discovered)}"
        )
        print(
            f"Current source IDs : {len(current_source_ids)}"
        )

        assert len(discovered) == EXPECTED_SOURCES
        assert len(current_source_ids) == EXPECTED_SOURCES

        # ------------------------------------------------------------------
        # 4. Current extraction baseline
        #
        # Exact source-version lookup:
        #     source_id + source_sha256
        #
        # Never use extraction timestamps/latest-row semantics here.
        # ------------------------------------------------------------------

        print()
        print("CURRENT EXTRACTION BASELINE")
        print("-" * 100)

        extraction_persistence = (
            SourceExtractionPersistenceService(
                session=session
            )
        )

        current_extractions = []

        for document in discovered:
            extraction = (
                extraction_persistence.get_by_source_version(
                    source_id=document.source_id,
                    source_sha256=document.sha256,
                )
            )

            assert extraction is not None, (
                "Missing current extraction for "
                f"{document.relative_path}"
            )

            current_extractions.append(extraction)

        current_extraction_ids = {
            str(extraction.extraction_id)
            for extraction in current_extractions
        }

        current_extraction_source_ids = {
            str(extraction.source_id)
            for extraction in current_extractions
        }

        print(
            f"Persisted matching rows : "
            f"{len(current_extractions)}"
        )

        print(
            f"Current extraction rows : "
            f"{len(current_extraction_source_ids)}"
        )

        print(
            f"Unique extraction IDs   : "
            f"{len(current_extraction_ids)}"
        )

        assert (
            current_extraction_source_ids
            == current_source_ids
        )

        assert (
            len(current_extraction_ids)
            == EXPECTED_SOURCES
        )

        # ------------------------------------------------------------------
        # 5. Legacy documents — informational only
        # ------------------------------------------------------------------

        print()
        print("LEGACY DOCUMENT BASELINE")
        print("-" * 100)

        legacy_documents = (
            getattr(startup, "documents", None)
            or []
        )

        print(
            f"Startup.documents : "
            f"{len(legacy_documents)}"
        )

        # ------------------------------------------------------------------
        # 6. Existing 10-point investment analysis
        #
        # This remains unchanged and remains the investment scorecard
        # source of truth.
        # ------------------------------------------------------------------

        banner(
            "FRESH PRODUCTION 10-POINT ANALYSIS"
        )

        print()
        print(
            "Calling existing production runner:"
        )
        print(
            "  scripts.run_startup_investment_analysis.run_analysis()"
        )

        print()
        print("Temperature : 0.0")
        print("Max tokens  : 2048")
        print("Thinking    : False")
        print()
        print("Running...")
        print("-" * 100)

        result = run_analysis(
            startup_identifier=STARTUP_KEY,
            data_root=DATA_ROOT,
            temperature=0.0,
            max_tokens=2048,
            thinking_enabled=False,
        )

        overall_score = float(
            result.aggregation.overall_score
        )

        decision = (
            result.decision.decision.value
        )

        print()
        print("10-POINT INVESTMENT RESULT")
        print("-" * 100)

        print(
            f"Startup       : "
            f"{result.evaluation.startup_name}"
        )

        print(
            f"Scorecard     : "
            f"{result.view.scorecard_name}"
        )

        print(
            f"Scorecard ver.: "
            f"{result.view.scorecard_version}"
        )

        print(
            f"Dimensions    : "
            f"{len(result.evaluation.evaluations)}"
        )

        print(
            f"Total weight  : "
            f"{result.aggregation.total_weight}"
        )

        print(
            f"Overall score : "
            f"{overall_score:.2f} / 100"
        )

        print(
            f"Decision      : "
            f"{decision}"
        )

        print()
        print("DIMENSION SCORES")
        print("-" * 100)

        for item in result.aggregation.dimension_scores:
            print(
                f"{item.dimension_id:<32} "
                f"score={item.score:<3} "
                f"weight={item.weight:<3} "
                f"contribution="
                f"{item.weighted_score:.2f}"
            )

        # ------------------------------------------------------------------
        # 7. Fresh canonical 3.7.x analysis
        # ------------------------------------------------------------------

        banner(
            "FRESH 3.7.x STARTUP ANALYSIS + PERSISTENCE"
        )

        application = (
            StartupAnalysisApplicationService(
                session=session
            )
        )

        print()
        print(
            "Production path : "
            "StartupAnalysisApplicationService"
        )
        print("Mode            : STANDARD")
        print(
            "Executing fresh production analysis..."
        )
        print("-" * 100)

        analysis = application.analyze(
            STARTUP_ID,
            mode=StartupAnalysisMode.STANDARD,
        )

        assert analysis is not None
        assert analysis.startup_id == STARTUP_ID

        print()
        print(f"Analysis ID      : {analysis.id}")
        print(
            f"Startup ID       : "
            f"{analysis.startup_id}"
        )
        print(
            f"Status           : "
            f"{analysis.status}"
        )
        print(
            f"Mode             : "
            f"{analysis.mode}"
        )
        print(
            f"Model            : "
            f"{analysis.model_name}"
        )
        print(
            f"Analysis version : "
            f"{analysis.analysis_version}"
        )

        # ------------------------------------------------------------------
        # 8. Persisted canonical evidence
        # ------------------------------------------------------------------

        snapshot = (
            analysis.input_snapshot
            or {}
        )

        persisted_evidence = (
            snapshot.get("evidence")
            or []
        )

        print()
        print("PERSISTED CANONICAL EVIDENCE")
        print("-" * 100)

        missing_source_text = 0
        missing_document_id = 0
        missing_confidence = 0
        invalid_confidence = 0

        provenance_ids = set()

        for evidence in persisted_evidence:

            if not evidence.get("source_text"):
                missing_source_text += 1

            document_id = evidence.get(
                "document_id"
            )

            if not document_id:
                missing_document_id += 1
            else:
                provenance_ids.add(
                    str(document_id)
                )

            confidence = evidence.get(
                "confidence"
            )

            if confidence is None:
                missing_confidence += 1
            else:
                try:
                    value = float(confidence)

                    if not (
                        0.0 <= value <= 1.0
                    ):
                        invalid_confidence += 1

                except (
                    TypeError,
                    ValueError,
                ):
                    invalid_confidence += 1

        print(
            f"Evidence records      : "
            f"{len(persisted_evidence)}"
        )

        print(
            f"Missing source_text   : "
            f"{missing_source_text}"
        )

        print(
            f"Missing document_id   : "
            f"{missing_document_id}"
        )

        print(
            f"Missing confidence    : "
            f"{missing_confidence}"
        )

        print(
            f"Invalid confidence    : "
            f"{invalid_confidence}"
        )

        # ------------------------------------------------------------------
        # 9. Evidence → current extraction provenance
        # ------------------------------------------------------------------

        current_provenance_ids = (
            provenance_ids
            & current_extraction_ids
        )

        invalid_provenance_ids = (
            provenance_ids
            - current_extraction_ids
        )

        print()
        print("PERSISTED PROVENANCE")
        print("-" * 100)

        print(
            f"Unique provenance IDs   : "
            f"{len(provenance_ids)}"
        )

        print(
            f"Current provenance IDs  : "
            f"{len(current_provenance_ids)}"
        )

        print(
            f"Invalid provenance IDs : "
            f"{len(invalid_provenance_ids)}"
        )

        # ------------------------------------------------------------------
        # 10. Assertions
        # ------------------------------------------------------------------

        banner("G.2-B ASSERTIONS")

        sources_ok = (
            len(current_source_ids)
            == EXPECTED_SOURCES
        )

        extractions_ok = (
            len(current_extraction_ids)
            == EXPECTED_SOURCES
        )

        ten_point_ok = (
            len(result.evaluation.evaluations)
            == EXPECTED_DIMENSIONS
            and result.aggregation.total_weight
            == EXPECTED_WEIGHT
        )

        baseline_score_ok = (
            abs(
                overall_score
                - EXPECTED_SCORE
            )
            < 0.01
        )

        decision_ok = (
            decision.lower()
            == EXPECTED_DECISION
        )

        evidence_contract_ok = (
            len(persisted_evidence)
            == EXPECTED_EVIDENCE
            and missing_source_text == 0
            and missing_document_id == 0
            and missing_confidence == 0
            and invalid_confidence == 0
        )

        provenance_ok = (
            len(current_extraction_ids)
            == EXPECTED_SOURCES
            and len(current_provenance_ids) > 0
            and len(invalid_provenance_ids) == 0
        )

        completed_ok = (
            str(analysis.status).lower()
            in {
                "completed",
                "startupanalysisstatus.completed",
            }
        )

        checks = {
            "Current sources = 18": sources_ok,
            "Current extractions = 18": extractions_ok,
            "10-point dimensions = 10": ten_point_ok,
            "Total weight = 100": (
                result.aggregation.total_weight
                == EXPECTED_WEIGHT
            ),
            "Overall score = 78.05": (
                baseline_score_ok
            ),
            "Decision = CONDITIONAL": (
                decision_ok
            ),
            "Persisted evidence = 48": (
                len(persisted_evidence)
                == EXPECTED_EVIDENCE
            ),
            "Evidence contract valid": (
                evidence_contract_ok
            ),
            "No invalid provenance": (
                len(invalid_provenance_ids) == 0
            ),
            "Analysis completed": completed_ok,
        }

        for name, passed in checks.items():
            print(
                f"{name:<32} : {passed}"
            )

        status = all(
            [
                sources_ok,
                extractions_ok,
                ten_point_ok,
                baseline_score_ok,
                decision_ok,
                evidence_contract_ok,
                provenance_ok,
                completed_ok,
            ]
        )

        banner("G.2-B RESULT")

        if status:
            print("STATUS : PASS")
            print()
            print(
                "Production source-of-truth, "
                "10-point investment baseline, "
                "3.7.x analysis, persistence, "
                "evidence contract, and "
                "current extraction provenance "
                "are aligned."
            )
            return 0

        print("STATUS : FAIL")
        print()
        print(
            "G.2-B production closure is not proven."
        )
        return 1

    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
