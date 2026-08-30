"""
Application service for production startup analysis.

This service is the application-layer entry point used by the API.

Responsibilities
----------------
- Resolve the requested Startup.
- Resolve the current source documents for the startup.
- Load persisted source extractions matching the current source versions.
- Invoke StartupAnalysisOrchestrator.
- Persist the resulting StartupAnalysisExecution.
- Return the persisted StartupAnalysis.

Non-responsibilities
--------------------
- Source extraction execution.
- OCR execution.
- Financial calculations.
- Analysis input construction.
- Prompt construction.
- LLM invocation.
- Structured response parsing.
- Persistence mapping.
- Transaction management.

Those responsibilities remain in their respective services.

Important source-extraction rule
---------------------------------
Startup analysis consumes persisted SourceExtractionRecord objects.

It does NOT execute source extraction itself.

The source version is identified by:

    source_id + source_sha256

Therefore a changed source file will not silently reuse an extraction
belonging to an older SHA256 version.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.chunking.text import TextChunker
from app.core.config.settings import settings
from app.intelligence.factory import create_intelligence_factory
from app.intelligence.models import InvestmentProfile
from app.models.analysis import StartupAnalysis, StartupAnalysisMode
from app.models.source_extraction_record import SourceExtractionRecord
from app.services.document import DocumentService
from app.services.document_processing import DocumentProcessingService
from app.services.financial_metrics import FinancialMetricsService
from app.services.investment_intelligence import (
    InvestmentIntelligenceService,
)
from app.services.source_discovery import SourceDiscoveryService
from app.services.source_extraction_persistence import (
    SourceExtractionPersistenceService,
)
from app.services.source_intelligence_reconciliation import (
    SourceIntelligenceReconciliationService,
)
from app.services.startup import StartupService
from app.services.startup_analysis import StartupAnalysisService
from app.services.startup_analysis_document_intelligence import (
    StartupAnalysisDocumentIntelligenceService,
)
from app.services.startup_analysis_orchestrator import (
    StartupAnalysisOrchestrator,
)
from app.services.startup_analysis_persistence import (
    StartupAnalysisPersistenceService,
)
from app.storage.local import LocalStorageProvider
from app.storage.service import StorageService

from app.processors.factory import create_processor_factory


class StartupAnalysisApplicationService:
    """
    Application-level coordinator for production startup analysis.

    The application service owns the composition of the production
    startup-analysis workflow.

    Source extraction is intentionally consumed as a persisted artifact.
    This service does not perform OCR/native extraction.
    """

    def __init__(
        self,
        session: Session,
        *,
        startup_service: StartupService | None = None,
        orchestrator: StartupAnalysisOrchestrator | None = None,
        persistence_service: StartupAnalysisPersistenceService | None = None,
        source_discovery: SourceDiscoveryService | None = None,
        source_extraction_persistence: (
            SourceExtractionPersistenceService | None
        ) = None,
    ) -> None:
        self._startup_service = (
            startup_service
            if startup_service is not None
            else StartupService(session)
        )

        self._source_discovery = (
            source_discovery
            if source_discovery is not None
            else SourceDiscoveryService()
        )

        self._source_extraction_persistence = (
            source_extraction_persistence
            if source_extraction_persistence is not None
            else SourceExtractionPersistenceService(
                session=session,
            )
        )

        self._orchestrator = (
            orchestrator
            if orchestrator is not None
            else StartupAnalysisOrchestrator(
                document_intelligence_service=(
                    self.create_startup_analysis_document_intelligence(
                        session,
                    )
                ),
            )
        )

        self._persistence_service = (
            persistence_service
            if persistence_service is not None
            else StartupAnalysisPersistenceService(
                session=session,
            )
        )

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def analyze(
        self,
        startup_id: UUID,
        *,
        mode: StartupAnalysisMode = StartupAnalysisMode.STANDARD,
    ) -> StartupAnalysis:
        """
        Execute and persist a startup analysis.

        Flow
        ----
        1. Resolve startup.
        2. Discover current startup sources.
        3. Load persisted extractions matching the current source versions.
        4. Execute production analysis orchestration.
        5. Persist StartupAnalysisExecution.
        6. Return persisted StartupAnalysis.

        Source extraction is NOT executed here.

        If a current source does not have a persisted extraction, it is
        omitted from the source-extraction input. Existing legacy
        ``startup.documents`` processing remains available through the
        document-intelligence service.
        """

        # ---------------------------------------------------------------------
        # 1. Resolve startup BEFORE starting expensive LLM execution.
        # ---------------------------------------------------------------------

        startup = self._startup_service.get_startup(
            startup_id,
        )

        if startup is None:
            raise ValueError(
                "Startup not found.",
            )

        # ---------------------------------------------------------------------
        # 2. Resolve persisted source extractions.
        # ---------------------------------------------------------------------

        source_extractions = (
            self._load_current_source_extractions(
                startup,
            )
        )

        # ---------------------------------------------------------------------
        # 3. Execute complete production analysis.
        # ---------------------------------------------------------------------

        execution = self._orchestrator.analyze(
            startup,
            mode=mode,
            source_extractions=source_extractions,
        )

        # ---------------------------------------------------------------------
        # 4. Persist execution.
        #
        # Transaction ownership remains inside
        # StartupAnalysisPersistenceService.
        # ---------------------------------------------------------------------

        analysis = self._persistence_service.persist(
            execution,
        )

        # ---------------------------------------------------------------------
        # 5. Return persisted historical analysis.
        # ---------------------------------------------------------------------

        return analysis

    # -------------------------------------------------------------------------
    # Source extraction consumption
    # -------------------------------------------------------------------------

    def _load_current_source_extractions(
        self,
        startup,
    ) -> tuple[SourceExtractionRecord, ...]:
        """
        Load persisted extractions matching the startup's current sources.
    
        The lookup is deliberately source-version exact:
    
            source_id + current sha256
    
        This prevents an older extraction from being used when the
        underlying source file has changed.
    
        Missing persisted extractions are skipped. Extraction itself is
        owned by the production source-extraction batch workflow.
        """
    
        startup_key = (
            startup.name
            .strip()
            .lower()
            .replace(" ", "_")
        )
    
        source_root = self._source_root(
            startup.name,
        )
    
        if not source_root.exists():
            return ()
    
        sources = self._source_discovery.discover(
            startup_id=startup_key,
            source_root=source_root,
        )
    
        records: list[SourceExtractionRecord] = []
    
        for source in sources:
            if source.sha256 is None:
                continue
    
            record = (
                self._source_extraction_persistence
                .get_by_source_version(
                    source_id=source.source_id,
                    source_sha256=source.sha256,
                )
            )
    
            if record is None:
                continue
    
            records.append(record)
    
        return tuple(records)


    # -------------------------------------------------------------------------
    # Source root
    # -------------------------------------------------------------------------

    @staticmethod
    def _source_root(
        startup_name: str,
    ) -> Path:
        """
        Resolve the production source root for a startup.
    
        Production layout:
    
            <storage_root>/real_startups/<startup_key>/sources
    
        Startup names are normalized to lowercase filesystem keys.
    
        Example:
    
            RestoMart
                ↓
            restomart
                ↓
            real_startups/restomart/sources
        """
    
        startup_key = (
            startup_name
            .strip()
            .lower()
            .replace(" ", "_")
        )
    
        return (
            Path(settings.real_startups_root)
            / startup_key
            / "sources"
        )

    # -------------------------------------------------------------------------
    # Document intelligence factory
    # -------------------------------------------------------------------------

    @staticmethod
    def create_startup_analysis_document_intelligence(
        session: Session,
        *,
        profile_observer: Callable[
            [InvestmentProfile],
            None,
        ] | None = None,
        source_facts_observer: Callable[
            [list],
            None,
        ] | None = None,
    ) -> StartupAnalysisDocumentIntelligenceService:
        """
        Construct the production document-intelligence service.

        Both legacy Document processing and persisted source-extraction
        processing converge through DocumentProcessingService.
        """

        documents = DocumentService(
            session,
        )

        storage = StorageService(
            LocalStorageProvider(
                settings.storage_root,
            )
        )

        source_extractions = (
            SourceExtractionPersistenceService(
                session=session,
            )
        )

        processing = DocumentProcessingService(
            documents=documents,
            storage=storage,
            processors=create_processor_factory(),
            chunker=TextChunker(),
            source_extractions=source_extractions,
        )

        intelligence = InvestmentIntelligenceService(
            factory=create_intelligence_factory(),
        )

        reconciliation = (
            SourceIntelligenceReconciliationService()
        )

        return StartupAnalysisDocumentIntelligenceService(
            document_processing=processing,
            intelligence=intelligence,
            reconciliation=reconciliation,
            profile_observer=profile_observer,
            source_facts_observer=source_facts_observer,
        )


__all__ = [
    "StartupAnalysisApplicationService",
]
