"""Tests for the Investment OS bootstrap application."""

from fastapi.testclient import TestClient

from app.main import APP_NAME, APP_VERSION


def test_root_endpoint(client: TestClient) -> None:
    """Verify the root endpoint returns application metadata."""

    response = client.get("/")

    assert response.status_code == 200

    payload = response.json()

    assert payload == {
        "name": APP_NAME,
        "version": APP_VERSION,
        "status": "running",
    }


def test_health_endpoint(client: TestClient) -> None:
    """Verify the health endpoint reports a healthy application."""

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
    }


def test_openapi_schema(client: TestClient) -> None:
    """Verify the generated OpenAPI schema."""

    response = client.get("/openapi.json")

    assert response.status_code == 200

    schema = response.json()

    assert schema["info"]["title"] == APP_NAME
    assert schema["info"]["version"] == APP_VERSION

    assert "/" in schema["paths"]
    assert "/health" in schema["paths"]


def test_swagger_ui_available(client: TestClient) -> None:
    """Verify Swagger UI is enabled."""

    response = client.get("/docs")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_redoc_available(client: TestClient) -> None:
    """Verify ReDoc UI is enabled."""

    response = client.get("/redoc")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_unknown_endpoint_returns_404(client: TestClient) -> None:
    """Verify unknown endpoints return HTTP 404."""

    response = client.get("/does-not-exist")

    assert response.status_code == 404

    payload = response.json()

    assert payload["detail"] == "Not Found"
