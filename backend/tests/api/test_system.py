import pytest

# Root Endpoint
def test_root_returns_200(client):
    """GET / returns HTTP 200."""

def test_root_response_schema(client):
    """Response contains application, version, environment and status."""

def test_root_application_name(client):
    """Application name matches settings."""

def test_root_version(client):
    """Version matches settings."""

def test_root_environment(client):
    """Environment matches settings."""

def test_root_status(client):
    """Status should be 'running'."""

# Health Endpoint
def test_health_returns_200(client):
    """GET /health returns HTTP 200."""

def test_health_response_schema(client):
    """Health endpoint returns expected schema."""

def test_health_status(client):
    """Health status should be 'healthy'."""

# OpenAPI
def test_docs_available(client):
    """Swagger UI should be accessible."""

def test_redoc_available(client):
    """ReDoc should be accessible."""

def test_openapi_available(client):
    """OpenAPI schema should be available."""
