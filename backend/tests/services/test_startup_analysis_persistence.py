"""
Tests for StartupAnalysisPersistenceService.

3.7.5.3.F
----------
Persist StartupAnalysisExecution through:

    StartupAnalysisExecution
        -> Mapper
        -> Repository
        -> explicit transaction ownership

Transaction ownership belongs to the persistence service:
    - commit on success
    - rollback on any persistence failure

The mapper and repository themselves must remain transaction-neutral.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import Mock, call
from uuid import uuid4

import pytest

from app.llm.models import LLMResponse, LLMUsage
from app.models.analysis import (
    StartupAnalysis,
    StartupAnalysisMode,
    StartupAnalysisStatus,
)
from app.repositories.startup_analysis import StartupAnalysisRepository
from app.schemas.analysis import (
    CompanyAnalysis,
    FinancialMetrics,
    StartupAnalysisInput,
    StartupAnalysisResult,
)
from app.services.startup_analysis_config import StartupAnalysisConfig
from app.services.startup_analysis_execution import (
    EXECUTION_STATUS_COMPLETED,
    StartupAnalysisExecution,
)
from app.services.startup_analysis_mapper import (
    map_startup_analysis_to_model,
)
from app.services.startup_analysis_persistence import (
    StartupAnalysisPersistenceService,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def startup_id():
    """Stable startup identifier for the execution."""
    return uuid4()


@pytest.fixture
def analysis_input(startup_id):
    """Representative normalized startup-analysis input."""
    return StartupAnalysisInput(
        startup_id=startup_id,
        company=CompanyAnalysis(
            name="Example Startup",
            description="Example startup",
            industry="SaaS",
            sector="Technology",
        ),
    )


@pytest.fixture
def metrics():
    """Representative deterministic financial metrics."""
    return FinancialMetrics(
        revenue_multiple=Decimal("3.4"),
        ebitda_multiple=Decimal("17"),
        valuation_to_growth=Decimal("10"),
        ebitda_margin=Decimal("20"),
        runway_months=Decimal("18"),
    )


@pytest.fixture
def result():
    """Representative qualitative analysis result."""
    return StartupAnalysisResult(
        company_overview="Strong company",
        founder_assessment="Experienced team",
        product_assessment="Good product",
        market_assessment="Large market",
        traction_assessment="Strong traction",
        financial_assessment="Healthy financials",
        valuation_assessment="Reasonable valuation",
        business_model_assessment="Scalable model",
        competitive_assessment="Strong position",
        strengths=[
            "Strong team",
            "Strong growth",
        ],
        risks=[
            "Competition",
        ],
        missing_information=[
            "Customer concentration",
        ],
        key_observations=[
            "Positive EBITDA",
        ],
        investment_thesis=(
            "Promising investment opportunity subject to diligence."
        ),
        preliminary_recommendation="promising",
    )


@pytest.fixture
def config():
    """Representative resolved startup-analysis configuration."""
    return StartupAnalysisConfig(
        mode=StartupAnalysisMode.DEEP,
        model_name="Qwen3-8B-Q4_K_M",
        thinking_enabled=True,
        max_tokens=1024,
        temperature=0.0,
    )


@pytest.fixture
def response():
    """Representative normalized LLM response."""
    return LLMResponse(
        text='{"preliminary_recommendation":"promising"}',
        model="Qwen3-8B-Q4_K_M",
        finish_reason="stop",
        usage=LLMUsage(
            prompt_tokens=1400,
            completion_tokens=500,
            total_tokens=1900,
        ),
    )


@pytest.fixture
def execution(
    analysis_input,
    metrics,
    result,
    config,
    response,
):
    """
    Complete StartupAnalysisExecution envelope.

    This mirrors the object returned by StartupAnalysisOrchestrator.
    """
    return StartupAnalysisExecution(
        input=analysis_input,
        metrics=metrics,
        result=result,
        config=config,
        response=response,
    )


@pytest.fixture
def mapped_analysis(
    startup_id,
    config,
    execution,
):
    """
    ORM persistence object returned by the mapper.

    The mapper itself is tested separately in
    test_startup_analysis_mapper.py.
    """
    return StartupAnalysis(
        startup_id=startup_id,
        mode=config.mode,
        status=StartupAnalysisStatus.COMPLETED,
        analysis_version=config.analysis_version,
        model_name=config.model_name,
        thinking_enabled=config.thinking_enabled,
        max_tokens=config.max_tokens,
        temperature=config.temperature,
        finish_reason=execution.response.finish_reason,
        prompt_tokens=execution.response.usage.prompt_tokens,
        completion_tokens=execution.response.usage.completion_tokens,
        total_tokens=execution.response.usage.total_tokens,
        inference_time_seconds=None,
        recommendation=execution.result.preliminary_recommendation,
        investment_thesis=execution.result.investment_thesis,
        input_snapshot=execution.input.model_dump(mode="json"),
        metrics_snapshot=execution.metrics.model_dump(mode="json"),
        result_snapshot=execution.result.model_dump(mode="json"),
        error_message=None,
    )


@pytest.fixture
def session():
    """
    Mock SQLAlchemy Session.

    The persistence service owns commit/rollback.
    """
    return Mock()


@pytest.fixture
def mapper():
    """
    Mapper dependency.

    The production mapper is currently a function, so the persistence
    service should support injection of this callable.
    """
    return Mock()


@pytest.fixture
def repository():
    """Repository dependency."""
    return Mock(spec=StartupAnalysisRepository)


@pytest.fixture
def persistence_service(
    session,
    mapper,
    repository,
):
    """Build the persistence service with explicit dependencies."""
    return StartupAnalysisPersistenceService(
        session=session,
        mapper=mapper,
        repository=repository,
    )


# ---------------------------------------------------------------------------
# Successful persistence
# ---------------------------------------------------------------------------


def test_persist_maps_execution(
    persistence_service,
    mapper,
    repository,
    execution,
    mapped_analysis,
):
    """
    Persistence must first map the execution envelope into the ORM model.
    """
    mapper.return_value = mapped_analysis
    repository.create.return_value = mapped_analysis

    result = persistence_service.persist(execution)

    mapper.assert_called_once_with(execution)
    repository.create.assert_called_once_with(mapped_analysis)

    assert result is mapped_analysis


def test_persist_commits_transaction(
    persistence_service,
    session,
    mapper,
    repository,
    execution,
    mapped_analysis,
):
    """
    Successful persistence must commit exactly once.
    """
    mapper.return_value = mapped_analysis
    repository.create.return_value = mapped_analysis

    persistence_service.persist(execution)

    session.commit.assert_called_once()
    session.rollback.assert_not_called()


def test_persist_returns_repository_result(
    persistence_service,
    session,
    mapper,
    repository,
    execution,
    mapped_analysis,
):
    """
    The persisted ORM object returned by the repository should be returned
    to the caller.
    """
    mapper.return_value = mapped_analysis
    repository.create.return_value = mapped_analysis

    result = persistence_service.persist(execution)

    assert result is mapped_analysis


# ---------------------------------------------------------------------------
# Explicit transaction ownership
# ---------------------------------------------------------------------------


def test_persist_rolls_back_when_mapping_fails(
    persistence_service,
    session,
    mapper,
    repository,
    execution,
):
    """
    Mapper failures must roll back the transaction.

    Repository persistence must not be attempted.
    """
    error = ValueError("invalid startup analysis")

    mapper.side_effect = error

    with pytest.raises(ValueError, match="invalid startup analysis"):
        persistence_service.persist(execution)

    session.rollback.assert_called_once()
    session.commit.assert_not_called()
    repository.create.assert_not_called()


def test_persist_rolls_back_when_repository_fails(
    persistence_service,
    session,
    mapper,
    repository,
    execution,
    mapped_analysis,
):
    """
    Repository failures must roll back the transaction.
    """
    mapper.return_value = mapped_analysis

    error = RuntimeError("database failure")
    repository.create.side_effect = error

    with pytest.raises(RuntimeError, match="database failure"):
        persistence_service.persist(execution)

    session.rollback.assert_called_once()
    session.commit.assert_not_called()


def test_persist_rolls_back_when_commit_fails(
    persistence_service,
    session,
    mapper,
    repository,
    execution,
    mapped_analysis,
):
    """
    Commit failures must also trigger rollback.

    This is important because commit itself belongs to the persistence
    service's transaction boundary.
    """
    mapper.return_value = mapped_analysis
    repository.create.return_value = mapped_analysis

    error = RuntimeError("commit failed")
    session.commit.side_effect = error

    with pytest.raises(RuntimeError, match="commit failed"):
        persistence_service.persist(execution)

    session.commit.assert_called_once()
    session.rollback.assert_called_once()


# ---------------------------------------------------------------------------
# Transaction ordering
# ---------------------------------------------------------------------------

def test_persist_executes_in_transaction_order(
    persistence_service,
    session,
    mapper,
    repository,
    execution,
    mapped_analysis,
):
    """
    Persistence ordering must be:

        mapper
          ->
        repository.create
          ->
        session.commit
    """
    mapper.return_value = mapped_analysis
    repository.create.return_value = mapped_analysis

    parent = Mock()

    parent.attach_mock(mapper, "map_execution")
    parent.attach_mock(repository.create, "create_analysis")
    parent.attach_mock(session.commit, "commit")

    persistence_service.persist(execution)

    assert parent.mock_calls == [
        call.map_execution(execution),
        call.create_analysis(mapped_analysis),
        call.commit(),
    ]



# ---------------------------------------------------------------------------
# Mapper / repository transaction neutrality
# ---------------------------------------------------------------------------


def test_repository_does_not_own_commit(
    persistence_service,
    session,
    mapper,
    repository,
    execution,
    mapped_analysis,
):
    """
    Repository must not be responsible for committing.

    The service explicitly owns session.commit().
    """
    mapper.return_value = mapped_analysis
    repository.create.return_value = mapped_analysis

    persistence_service.persist(execution)

    repository.create.assert_called_once_with(mapped_analysis)

    # Repository is only asked to create/save the object.
    # Transaction completion happens on the Session owned by the service.
    session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Real mapper compatibility
# ---------------------------------------------------------------------------


def test_persist_with_real_mapper(
    session,
    repository,
    execution,
):
    """
    Verify that the persistence service's default execution-to-model
    adapter correctly uses the real mapper.
    """
    repository.create.side_effect = lambda analysis: analysis

    persistence_service = StartupAnalysisPersistenceService(
        session=session,
        repository=repository,
    )

    result = persistence_service.persist(execution)

    repository.create.assert_called_once()

    assert result.startup_id == execution.input.startup_id
    assert result.mode == execution.config.mode
    assert result.status == StartupAnalysisStatus.COMPLETED
    assert result.analysis_version == execution.config.analysis_version
    assert result.model_name == execution.response.model
    assert result.thinking_enabled is True
    assert result.max_tokens == execution.config.max_tokens
    assert result.temperature == execution.config.temperature

    assert result.recommendation == (
        execution.result.preliminary_recommendation
    )
    assert result.investment_thesis == (
        execution.result.investment_thesis
    )

    session.commit.assert_called_once()
    session.rollback.assert_not_called()

# ---------------------------------------------------------------------------
# Execution contract
# ---------------------------------------------------------------------------


def test_execution_is_completed(
    execution,
):
    """
    Persistence should receive only a completed execution envelope.

    This verifies the current execution contract used by the orchestrator.
    """
    assert execution.status == EXECUTION_STATUS_COMPLETED
    assert execution.is_completed is True


def test_execution_contains_all_persistence_inputs(
    execution,
):
    """
    StartupAnalysisExecution must contain all inputs required by the mapper.
    """
    assert execution.input is not None
    assert execution.metrics is not None
    assert execution.result is not None
    assert execution.config is not None
    assert execution.response is not None
