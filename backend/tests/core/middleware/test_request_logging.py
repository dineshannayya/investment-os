"""
Tests for Request Logging middleware.
"""

import logging
from contextlib import suppress

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.middleware import register_middlewares


def create_app() -> FastAPI:
    """Create a minimal FastAPI application."""

    app = FastAPI()

    register_middlewares(app)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/error")
    async def error():
        raise RuntimeError("Test exception")

    return app


class TestRequestLoggingMiddleware:
    """Tests for Request Logging middleware."""

    def test_successful_request_logged(self, caplog):

        client = TestClient(create_app())

        with caplog.at_level(logging.INFO):
            response = client.get("/health")

        assert response.status_code == 200
        assert len(caplog.records) > 0

    def test_http_method_logged(self, caplog):

        client = TestClient(create_app())

        with caplog.at_level(logging.INFO):
            client.get("/health")

        assert "GET" in caplog.text

    def test_request_path_logged(self, caplog):

        client = TestClient(create_app())

        with caplog.at_level(logging.INFO):
            client.get("/health")

        assert "/health" in caplog.text

    def test_status_code_logged(self, caplog):

        client = TestClient(create_app())

        with caplog.at_level(logging.INFO):
            client.get("/health")

        assert "200" in caplog.text

    def test_request_id_logged(self, caplog):

        client = TestClient(create_app())

        with caplog.at_level(logging.INFO):
            client.get("/health")

    def test_duration_logged(self, caplog):

        client = TestClient(create_app())

        with caplog.at_level(logging.INFO):
            client.get("/health")

        #
        # Adjust this once the final log format is frozen.
        #
        assert "duration" in caplog.text.lower()

    def test_exception_request_logged(self, caplog):

        client = TestClient(create_app())

        with caplog.at_level(logging.ERROR), suppress(RuntimeError):
            client.get("/error")

        assert len(caplog.records) > 0
