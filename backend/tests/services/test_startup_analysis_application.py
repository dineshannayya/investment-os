"""
Tests for StartupAnalysisApplicationService.

3.7.5.4.3
----------

The application service is responsible for coordinating:

    StartupService
        ->
    StartupAnalysisOrchestrator
        ->
    StartupAnalysisPersistenceService

These tests intentionally mock those collaborators.

They do not test:
    - financial calculations
    - prompt construction
    - Qwen execution
    - structured parsing
    - persistence mapping
    - repository behavior
    - database transactions
"""

from __future__ import annotations

from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.models.analysis import (
    StartupAnalysis,
    StartupAnalysisMode,
)
from app.models.startup import Startup
from app.services.startup_analysis_application import (
    StartupAnalysisApplicationService,
)
from app.services.startup_analysis_execution import (
    StartupAnalysisExecution,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def startup_id():
    """Representative startup identifier."""
    return uuid4()


@pytest.fixture
def startup(startup_id):
    """Minimal Startup object for application-service tests."""
    return Startup(
        id=startup_id,
        name="Test Startup",
    )


@pytest.fixture
def execution():
    """
    Mock StartupAnalysisExecution.

    The application service should treat the execution as an opaque
    result from the orchestrator and pass the exact object to persistence.
    """
    return Mock(
        spec=StartupAnalysisExecution,
    )


@pytest.fixture
def persisted_analysis(startup_id):
    """
    Mock persisted StartupAnalysis.

    The application service should return the exact object produced by
    StartupAnalysisPersistenceService.
    """
    return Mock(
        spec=StartupAnalysis,
        startup_id=startup_id,
    )


@pytest.fixture
def startup_service():
    """Mock StartupService."""
    return Mock()


@pytest.fixture
def orchestrator():
    """Mock StartupAnalysisOrchestrator."""
    return Mock()


@pytest.fixture
def persistence_service():
    """Mock StartupAnalysisPersistenceService."""
    return Mock()


@pytest.fixture
def service(
    startup_service,
    orchestrator,
    persistence_service,
):
    """
    Application service with all collaborators injected.

    This prevents the test from constructing real repositories,
    orchestrators, or persistence infrastructure.
    """
    return StartupAnalysisApplicationService(
        session=Mock(),
        startup_service=startup_service,
        orchestrator=orchestrator,
        persistence_service=persistence_service,
    )


# ---------------------------------------------------------------------------
# Startup resolution
# ---------------------------------------------------------------------------


def test_analyze_resolves_startup(
    service,
    startup_service,
    startup,
    startup_id,
    orchestrator,
    execution,
    persistence_service,
    persisted_analysis,
):
    """
    The application service must resolve the startup before analysis.
    """

    startup_service.get_startup.return_value = startup
    orchestrator.analyze.return_value = execution
    persistence_service.persist.return_value = persisted_analysis

    result = service.analyze(
        startup_id,
        mode=StartupAnalysisMode.STANDARD,
    )

    startup_service.get_startup.assert_called_once_with(
        startup_id,
    )

    assert result is persisted_analysis


def test_analyze_raises_when_startup_does_not_exist(
    service,
    startup_service,
    startup_id,
    orchestrator,
    persistence_service,
):
    """
    A missing startup must stop the workflow before expensive analysis
    execution begins.
    """

    startup_service.get_startup.return_value = None

    with pytest.raises(ValueError, match="Startup not found"):
        service.analyze(
            startup_id,
            mode=StartupAnalysisMode.STANDARD,
        )

    startup_service.get_startup.assert_called_once_with(
        startup_id,
    )

    orchestrator.analyze.assert_not_called()
    persistence_service.persist.assert_not_called()


# ---------------------------------------------------------------------------
# Orchestrator invocation
# ---------------------------------------------------------------------------


def test_analyze_passes_exact_startup_to_orchestrator(
    service,
    startup_service,
    startup,
    startup_id,
    orchestrator,
    execution,
    persistence_service,
    persisted_analysis,
):
    """
    The exact Startup object returned by StartupService must be passed
    to the orchestrator.
    """

    startup_service.get_startup.return_value = startup
    orchestrator.analyze.return_value = execution
    persistence_service.persist.return_value = persisted_analysis

    service.analyze(
        startup_id,
        mode=StartupAnalysisMode.STANDARD,
    )

    orchestrator.analyze.assert_called_once_with(
        startup,
        mode=StartupAnalysisMode.STANDARD,
    )


def test_analyze_preserves_standard_mode(
    service,
    startup_service,
    startup,
    startup_id,
    orchestrator,
    execution,
    persistence_service,
    persisted_analysis,
):
    """STANDARD mode must reach the orchestrator unchanged."""

    startup_service.get_startup.return_value = startup
    orchestrator.analyze.return_value = execution
    persistence_service.persist.return_value = persisted_analysis

    service.analyze(
        startup_id,
        mode=StartupAnalysisMode.STANDARD,
    )

    orchestrator.analyze.assert_called_once_with(
        startup,
        mode=StartupAnalysisMode.STANDARD,
    )


def test_analyze_preserves_deep_mode(
    service,
    startup_service,
    startup,
    startup_id,
    orchestrator,
    execution,
    persistence_service,
    persisted_analysis,
):
    """DEEP mode must reach the orchestrator unchanged."""

    startup_service.get_startup.return_value = startup
    orchestrator.analyze.return_value = execution
    persistence_service.persist.return_value = persisted_analysis

    service.analyze(
        startup_id,
        mode=StartupAnalysisMode.DEEP,
    )

    orchestrator.analyze.assert_called_once_with(
        startup,
        mode=StartupAnalysisMode.DEEP,
    )


def test_analyze_defaults_to_standard_mode(
    service,
    startup_service,
    startup,
    startup_id,
    orchestrator,
    execution,
    persistence_service,
    persisted_analysis,
):
    """
    Omitting mode at the application boundary must use STANDARD.
    """

    startup_service.get_startup.return_value = startup
    orchestrator.analyze.return_value = execution
    persistence_service.persist.return_value = persisted_analysis

    service.analyze(startup_id)

    orchestrator.analyze.assert_called_once_with(
        startup,
        mode=StartupAnalysisMode.STANDARD,
    )


# ---------------------------------------------------------------------------
# Persistence invocation
# ---------------------------------------------------------------------------


def test_analyze_passes_exact_execution_to_persistence(
    service,
    startup_service,
    startup,
    startup_id,
    orchestrator,
    execution,
    persistence_service,
    persisted_analysis,
):
    """
    The exact StartupAnalysisExecution returned by the orchestrator must
    be passed to persistence.
    """

    startup_service.get_startup.return_value = startup
    orchestrator.analyze.return_value = execution
    persistence_service.persist.return_value = persisted_analysis

    service.analyze(
        startup_id,
        mode=StartupAnalysisMode.STANDARD,
    )

    persistence_service.persist.assert_called_once_with(
        execution,
    )


def test_analyze_returns_exact_persisted_analysis(
    service,
    startup_service,
    startup,
    startup_id,
    orchestrator,
    execution,
    persistence_service,
    persisted_analysis,
):
    """
    The application service must return exactly what the persistence
    service returns.
    """

    startup_service.get_startup.return_value = startup
    orchestrator.analyze.return_value = execution
    persistence_service.persist.return_value = persisted_analysis

    result = service.analyze(
        startup_id,
        mode=StartupAnalysisMode.STANDARD,
    )

    assert result is persisted_analysis


# ---------------------------------------------------------------------------
# Workflow ordering
# ---------------------------------------------------------------------------


def test_analyze_executes_in_correct_order(
    service,
    startup_service,
    startup,
    startup_id,
    orchestrator,
    execution,
    persistence_service,
    persisted_analysis,
):
    """
    Verify the application workflow ordering:

        startup lookup
            ->
        orchestrator
            ->
        persistence
    """

    startup_service.get_startup.return_value = startup
    orchestrator.analyze.return_value = execution
    persistence_service.persist.return_value = persisted_analysis

    parent = Mock()

    parent.attach_mock(
        startup_service.get_startup,
        "get_startup",
    )
    parent.attach_mock(
        orchestrator.analyze,
        "analyze",
    )
    parent.attach_mock(
        persistence_service.persist,
        "persist",
    )

    result = service.analyze(
        startup_id,
        mode=StartupAnalysisMode.DEEP,
    )

    assert parent.mock_calls == [
        (
            "get_startup",
            (startup_id,),
            {},
        ),
        (
            "analyze",
            (
                startup,
            ),
            {
                "mode": StartupAnalysisMode.DEEP,
            },
        ),
        (
            "persist",
            (
                execution,
            ),
            {},
        ),
    ]

    assert result is persisted_analysis


# ---------------------------------------------------------------------------
# Exception propagation
# ---------------------------------------------------------------------------


def test_analyze_propagates_orchestrator_exception(
    service,
    startup_service,
    startup,
    startup_id,
    orchestrator,
    persistence_service,
):
    """
    Orchestrator failures must propagate unchanged.

    The application service should not swallow or translate analysis
    execution exceptions. HTTP translation belongs at the API boundary.
    """

    startup_service.get_startup.return_value = startup

    error = RuntimeError(
        "Qwen analysis failed",
    )

    orchestrator.analyze.side_effect = error

    with pytest.raises(
        RuntimeError,
        match="Qwen analysis failed",
    ):
        service.analyze(
            startup_id,
            mode=StartupAnalysisMode.DEEP,
        )

    persistence_service.persist.assert_not_called()


def test_analyze_propagates_persistence_exception(
    service,
    startup_service,
    startup,
    startup_id,
    orchestrator,
    execution,
    persistence_service,
):
    """
    Persistence failures must propagate unchanged.

    Transaction rollback remains the responsibility of
    StartupAnalysisPersistenceService.
    """

    startup_service.get_startup.return_value = startup
    orchestrator.analyze.return_value = execution

    error = RuntimeError(
        "Database persistence failed",
    )

    persistence_service.persist.side_effect = error

    with pytest.raises(
        RuntimeError,
        match="Database persistence failed",
    ):
        service.analyze(
            startup_id,
            mode=StartupAnalysisMode.STANDARD,
        )


# ---------------------------------------------------------------------------
# Short-circuit behavior
# ---------------------------------------------------------------------------


def test_analyze_does_not_persist_when_orchestration_fails(
    service,
    startup_service,
    startup,
    startup_id,
    orchestrator,
    persistence_service,
):
    """
    Persistence must never be attempted when orchestration fails.
    """

    startup_service.get_startup.return_value = startup
    orchestrator.analyze.side_effect = RuntimeError(
        "Analysis failed",
    )

    with pytest.raises(RuntimeError, match="Analysis failed"):
        service.analyze(startup_id)

    persistence_service.persist.assert_not_called()


def test_analyze_does_not_orchestrate_missing_startup(
    service,
    startup_service,
    startup_id,
    orchestrator,
):
    """
    A missing startup must short-circuit before orchestration.
    """

    startup_service.get_startup.return_value = None

    with pytest.raises(ValueError, match="Startup not found"):
        service.analyze(startup_id)

    orchestrator.analyze.assert_not_called()
