"""
Global pytest fixtures.

This module contains fixtures shared across the entire test suite.

It intentionally contains only application-level fixtures.

Database fixtures belong in:
    tests/database.py

Model factories belong in:
    tests/fixtures.py
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.config.error_codes import ErrorCode
from app.main import app as fastapi_app
from app.schemas.error import ErrorDetail
from app.schemas.pagination import PaginationMeta
from app.schemas.response import ResponseMeta

pytest_plugins = [
    "tests.database",
    "tests.fixtures",
    "tests.investment_scenarios",
]

# =============================================================================
# FastAPI Application
# =============================================================================


@pytest.fixture(scope="session")
def app() -> FastAPI:
    """
    Return the FastAPI application.

    The application is created once for the entire test session.
    """
    return fastapi_app


# =============================================================================
# Test Client
# =============================================================================


@pytest.fixture(scope="session")
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    """
    Return a FastAPI TestClient.

    The client is shared across the entire test session.
    """
    with TestClient(app) as test_client:
        yield test_client


# =============================================================================
# Application Settings
# =============================================================================


@pytest.fixture(scope="session")
def app_settings():
    """
    Return application settings.

    Useful for configuration validation tests.
    """
    return settings


# =============================================================================
# Common API Responses
# =============================================================================


@pytest.fixture
def get_root_response(client: TestClient):
    """
    Execute GET /
    """
    return client.get("/")


@pytest.fixture
def get_health_response(client: TestClient):
    """
    Execute GET /health
    """
    return client.get("/health")


@pytest.fixture
def get_openapi_response(client: TestClient):
    """
    Execute GET /openapi.json
    """
    return client.get("/openapi.json")


# =============================================================================
# Common Schema Fixtures
# =============================================================================


@pytest.fixture
def request_id() -> str:
    """
    Sample request identifier.
    """
    return "test-request-id"


@pytest.fixture
def sample_error() -> ErrorDetail:
    """
    Standard validation error.
    """
    return ErrorDetail(
        code=ErrorCode.VALIDATION_ERROR,
        message="Validation failed.",
        field="email",
    )


@pytest.fixture
def sample_pagination() -> PaginationMeta:
    """
    Standard pagination metadata.
    """
    return PaginationMeta(
        page=1,
        per_page=20,
        total_items=100,
        total_pages=5,
        has_previous=False,
        has_next=True,
    )


@pytest.fixture
def response_meta(
    request_id: str,
    sample_pagination: PaginationMeta,
) -> ResponseMeta:
    """
    Standard response metadata.
    """
    return ResponseMeta(
        request_id=request_id,
        pagination=sample_pagination,
    )


@pytest.fixture
def sample_dict():
    """
    Generic dictionary payload.
    """
    return {
        "id": 1,
        "name": "Investment OS",
    }


@pytest.fixture
def sample_list():
    """
    Generic list payload.
    """
    return [
        "one",
        "two",
        "three",
    ]
