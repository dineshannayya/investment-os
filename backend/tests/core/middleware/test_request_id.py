"""
Tests for Request ID middleware.
"""

from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.middleware.request_id import request_id_middleware


def create_app() -> FastAPI:
    app = FastAPI()

    @app.middleware("http")
    async def middleware(request, call_next):
        return await request_id_middleware(request, call_next)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


class TestRequestIdMiddleware:
    """Tests for Request ID middleware."""

    def test_response_contains_request_id_header(self):

        client = TestClient(create_app())

        response = client.get("/health")

        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

    def test_request_id_is_valid_uuid(self):

        client = TestClient(create_app())

        response = client.get("/health")

        UUID(response.headers["X-Request-ID"])

    def test_request_ids_are_unique(self):

        client = TestClient(create_app())

        ids = {client.get("/health").headers["X-Request-ID"] for _ in range(20)}

        assert len(ids) == 20

    def test_multiple_requests_do_not_share_request_id(self):

        client = TestClient(create_app())

        first = client.get("/health")
        second = client.get("/health")

        assert first.headers["X-Request-ID"] != second.headers["X-Request-ID"]

    def test_request_id_exists_even_for_multiple_requests(self):

        client = TestClient(create_app())

        for _ in range(50):
            response = client.get("/health")

            assert "X-Request-ID" in response.headers
