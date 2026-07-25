"""
Tests for middleware registration.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.middleware import register_middlewares
from app.core.middleware.registration import MIDDLEWARE_PIPELINE


def test_registered_middlewares(app):
    assert len(app.user_middleware) == 3

    for middleware in app.user_middleware:
        print(middleware)

def create_test_app() -> FastAPI:
    """Create a minimal FastAPI application."""

    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    register_middlewares(app)

    return app


class TestMiddlewareRegistration:
    """Middleware registration tests."""

    def test_register_middlewares_does_not_raise(self):
        app = FastAPI()
        register_middlewares(app)

    def test_all_middlewares_registered(self):
        app = FastAPI()
        register_middlewares(app)

        #
        # Update this number whenever middleware are added.
        #
        assert len(app.user_middleware) == len(MIDDLEWARE_PIPELINE)


    def test_pipeline_adds_required_headers(self):
        client = TestClient(create_test_app())

        response = client.get("/health")

        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        assert "X-Response-Time" in response.headers

    def test_each_request_receives_unique_request_id(self):
        client = TestClient(create_test_app())

        first = client.get("/health")
        second = client.get("/health")

        assert (
            first.headers["X-Request-ID"]
            != second.headers["X-Request-ID"]
        )

    def test_pipeline_survives_multiple_requests(self):
        client = TestClient(create_test_app())

        for _ in range(20):
            response = client.get("/health")

            assert response.status_code == 200
            assert "X-Request-ID" in response.headers
            assert "X-Response-Time" in response.headers

    def test_pipeline_handles_exception(self):
        app = FastAPI()
    
        @app.get("/boom")
        async def boom():
            raise RuntimeError("boom")
    
        register_middlewares(app)
    
        client = TestClient(
            app,
            raise_server_exceptions=False,
        )
    
        response = client.get("/boom")
    
        #
        # Update expected status after ADR-0103
        # exception handling is implemented.
        #
        assert response.status_code == 500

