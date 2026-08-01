"""
Tests for System API endpoints.
"""

from uuid import UUID

import pytest

from app.core.config import API_PREFIX, settings


def assert_middleware_headers(response) -> None:
    """Assert middleware response headers."""

    assert "X-Request-ID" in response.headers
    assert "X-Response-Time" in response.headers

    uuid = UUID(response.headers["X-Request-ID"])

    assert str(uuid) == response.headers["X-Request-ID"]


@pytest.mark.parametrize(
    "endpoint",
    [
        "/health",
        "/ready",
        "/version",
    ],
)
def test_all_system_endpoints_have_middleware_headers(
    client,
    endpoint,
):
    response = client.get(f"{API_PREFIX}{endpoint}")

    assert response.status_code == 200

    assert_middleware_headers(response)


class TestHealth:
    """Tests for /health endpoint."""

    def test_health(self, client):
        response = client.get(f"{API_PREFIX}/health")

        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
        }

    def test_health_request_id_header(self, client):
        response = client.get(f"{API_PREFIX}/health")

        assert "X-Request-ID" in response.headers

        uuid = UUID(response.headers["X-Request-ID"])

        assert str(uuid) == response.headers["X-Request-ID"]

    def test_health_response_time_header(self, client):
        response = client.get(f"{API_PREFIX}/health")

        assert "X-Response-Time" in response.headers

        assert response.headers["X-Response-Time"]


class TestReady:
    """Tests for /ready endpoint."""

    def test_ready(self, client):
        response = client.get(f"{API_PREFIX}/ready")

        assert response.status_code == 200

        body = response.json()

        assert body == {
            "status": "ready",
            "services": {
                "database": "not_configured",
                "redis": "not_configured",
                "llm": "not_configured",
            },
        }

    def test_ready_headers(self, client):
        response = client.get(f"{API_PREFIX}/ready")

        assert_middleware_headers(response)


class TestVersion:
    """Tests for /version endpoint."""

    def test_version(self, client):
        response = client.get(f"{API_PREFIX}/version")

        assert response.status_code == 200

        body = response.json()

        assert body["application"] == settings.app_name
        assert body["version"] == settings.app_version
        assert body["environment"] == settings.environment

    def test_version_headers(self, client):
        response = client.get(f"{API_PREFIX}/version")

        assert_middleware_headers(response)


class TestMiddleware:
    """Middleware integration tests."""

    def test_request_id_is_unique(self, client):
        response1 = client.get(f"{API_PREFIX}/health")
        response2 = client.get(f"{API_PREFIX}/health")

        assert response1.headers["X-Request-ID"] != response2.headers["X-Request-ID"]

    def test_request_id_is_valid_uuid(self, client):
        response = client.get(f"{API_PREFIX}/health")

        UUID(response.headers["X-Request-ID"])

    def test_response_time_present(self, client):
        response = client.get(f"{API_PREFIX}/health")

        assert response.headers["X-Response-Time"]

    def test_response_time_is_positive(self, client):
        response = client.get(f"{API_PREFIX}/health")

        value = response.headers["X-Response-Time"]

        value = value.replace(" ms", "")

        assert value != ""

        assert float(value) >= 0.0


class TestErrors:
    """Error path tests."""

    def test_404_contains_middleware_headers(self, client):
        response = client.get("/invalid-endpoint")

        assert response.status_code == 404

        assert_middleware_headers(response)


class TestOpenAPI:
    """OpenAPI integration tests."""

    def test_openapi_contains_system_endpoints(self, client):
        response = client.get("/openapi.json")

        assert response.status_code == 200

        paths = response.json()["paths"]

        assert "get" in paths[f"{API_PREFIX}/health"]
        assert "get" in paths[f"{API_PREFIX}/ready"]
        assert "get" in paths[f"{API_PREFIX}/version"]
