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
from app.main import app as fastapi_app

pytest_plugins = [
    # Infrastructure
    "tests.database",

    # Shared fixtures
    "tests.fixtures.orm",
    "tests.fixtures.auth",
    "tests.fixtures.responses",
    "tests.fixtures.role",

    # Test scenarios
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


