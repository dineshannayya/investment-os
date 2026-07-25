"""
Tests for timing middleware.
"""

import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.middleware import register_middlewares


def create_app(delay: float = 0.0) -> FastAPI:

    app = FastAPI()

    register_middlewares(app)

    @app.get("/health")
    async def health():
        if delay:
            time.sleep(delay)

        return {"status": "ok"}

    return app


class TestTimingMiddleware:
    """Tests for timing middleware."""

    def test_response_contains_timing_header(self):

        client = TestClient(create_app())

        response = client.get("/health")

        assert response.status_code == 200
        assert "X-Response-Time" in response.headers

    def test_response_time_is_numeric(self):

        client = TestClient(create_app())

        response = client.get("/health")

        duration = response.headers["X-Response-Time"]

        assert duration.endswith(" ms")

        value = float(duration.removesuffix(" ms"))

        assert value >= 0.0

    def test_response_time_is_positive(self):

        client = TestClient(create_app())

        response = client.get("/health")

        duration = float(response.headers["X-Response-Time"].removesuffix(" ms"))

        assert duration >= 0.0

    def test_longer_request_reports_longer_time(self):

        fast_client = TestClient(create_app())
        slow_client = TestClient(create_app(delay=0.05))

        fast = float(fast_client.get("/health").headers["X-Response-Time"].removesuffix(" ms"))

        slow = float(slow_client.get("/health").headers["X-Response-Time"].removesuffix(" ms"))

        assert slow > fast

    def test_timing_header_exists_for_multiple_requests(self):

        client = TestClient(create_app())

        for _ in range(20):
            response = client.get("/health")

            assert "X-Response-Time" in response.headers
