"""
Tests for StartupAnalysisHistoryService.

Sprint 3.7.5.5.4
----------------

The history service is a read-only application boundary.

These tests verify:

    - repository delegation
    - pagination forwarding
    - exact result preservation
    - historical detail lookup
    - startup isolation
    - no write/persistence behavior

These tests intentionally do not test:

    - SQL query construction
    - pagination implementation
    - API schemas
    - HTTP behavior
    - analysis orchestration
    - financial metrics
    - LLM execution
"""

from __future__ import annotations

from unittest.mock import Mock
from uuid import uuid4

from app.models.analysis import StartupAnalysis
from app.repositories.startup_analysis import StartupAnalysisRepository
from app.services.startup_analysis_history import (
    StartupAnalysisHistoryService,
)


# =============================================================================
# Fixtures
# =============================================================================


def make_service():
    """Create history service with a mocked repository."""

    repository = Mock(
        spec=StartupAnalysisRepository,
    )

    service = StartupAnalysisHistoryService(
        repository=repository,
    )

    return service, repository


# =============================================================================
# List history
# =============================================================================


def test_list_history_delegates_to_repository():
    """
    History listing must delegate directly to the repository.
    """

    startup_id = uuid4()

    analyses = [
        Mock(spec=StartupAnalysis),
        Mock(spec=StartupAnalysis),
    ]

    repository_result = (
        analyses,
        2,
    )

    service, repository = make_service()

    repository.list_by_startup.return_value = repository_result

    result = service.list_history(
        startup_id,
        page=1,
        per_page=20,
    )

    repository.list_by_startup.assert_called_once_with(
        startup_id,
        page=1,
        per_page=20,
    )

    assert result is repository_result


def test_list_history_forwards_pagination():
    """
    Page and per_page must be forwarded unchanged.
    """

    startup_id = uuid4()

    service, repository = make_service()

    repository.list_by_startup.return_value = (
        [],
        0,
    )

    service.list_history(
        startup_id,
        page=3,
        per_page=10,
    )

    repository.list_by_startup.assert_called_once_with(
        startup_id,
        page=3,
        per_page=10,
    )


def test_list_history_preserves_empty_result():
    """
    Empty history must be returned unchanged.
    """

    startup_id = uuid4()

    service, repository = make_service()

    repository.list_by_startup.return_value = (
        [],
        0,
    )

    items, total_items = service.list_history(
        startup_id,
        page=1,
        per_page=20,
    )

    assert items == []
    assert total_items == 0


def test_list_history_preserves_repository_result():
    """
    The service must return the exact repository objects without
    rebuilding or copying them.
    """

    startup_id = uuid4()

    analysis = Mock(
        spec=StartupAnalysis,
    )

    repository_result = (
        [analysis],
        1,
    )

    service, repository = make_service()

    repository.list_by_startup.return_value = repository_result

    result = service.list_history(
        startup_id,
        page=1,
        per_page=20,
    )

    assert result is repository_result
    assert result[0][0] is analysis


# =============================================================================
# Get history
# =============================================================================


def test_get_history_delegates_to_repository():
    """
    Detail lookup must delegate to the startup-scoped repository query.
    """

    startup_id = uuid4()
    analysis_id = uuid4()

    analysis = Mock(
        spec=StartupAnalysis,
    )

    service, repository = make_service()

    repository.get_by_startup_and_id.return_value = analysis

    result = service.get_history(
        startup_id,
        analysis_id,
    )

    repository.get_by_startup_and_id.assert_called_once_with(
        startup_id,
        analysis_id,
    )

    assert result is analysis


def test_get_history_returns_none_when_not_found():
    """
    Missing historical analysis is represented as None.

    HTTP 404 translation belongs to the API layer.
    """

    startup_id = uuid4()
    analysis_id = uuid4()

    service, repository = make_service()

    repository.get_by_startup_and_id.return_value = None

    result = service.get_history(
        startup_id,
        analysis_id,
    )

    assert result is None


def test_get_history_enforces_startup_scope():
    """
    startup_id must always be passed to the repository together with
    analysis_id.

    This prevents the service from accidentally introducing an
    unscoped analysis lookup.
    """

    startup_id = uuid4()
    analysis_id = uuid4()

    service, repository = make_service()

    repository.get_by_startup_and_id.return_value = None

    service.get_history(
        startup_id,
        analysis_id,
    )

    repository.get_by_startup_and_id.assert_called_once_with(
        startup_id,
        analysis_id,
    )


# =============================================================================
# Read-only behavior
# =============================================================================


def test_history_service_has_no_write_operations():
    """
    History service must remain read-only.

    This is intentionally a structural test: the service should not
    expose persistence operations.
    """

    service, _ = make_service()

    assert not hasattr(service, "create")
    assert not hasattr(service, "update")
    assert not hasattr(service, "delete")
    assert not hasattr(service, "persist")
