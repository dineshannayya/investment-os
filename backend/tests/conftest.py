import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app as fastapi_app


@pytest.fixture(scope="session")
def app() -> FastAPI:
    """Return FastAPI application."""
    return fastapi_app


@pytest.fixture(scope="session")
def client(app: FastAPI) -> TestClient:
    """Return FastAPI TestClient."""
    return TestClient(app)


@pytest.fixture(scope="session")
def settings_fixture():
    """Return application settings."""
    return settings


@pytest.fixture
def root_response(client):
    """GET /"""
    return client.get("/")


@pytest.fixture
def health_response(client):
    """GET /health"""
    return client.get("/health")


@pytest.fixture
def openapi_response(client):
    """GET /openapi.json"""
    return client.get("/openapi.json")
