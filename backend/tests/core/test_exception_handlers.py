"""
Unit tests for global exception handlers.
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError

from app.core.config.error_codes import ErrorCode
from app.core.exception_handlers import (
    app_exception_handler,
    register_exception_handlers,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.exceptions import AppException

# =============================================================================
# TestRegisterExceptionHandlers
# =============================================================================


class TestRegisterExceptionHandlers:
    """Tests for register_exception_handlers()."""

    def test_registers_all_exception_handlers(self) -> None:
        """Should register all application exception handlers."""

        app = MagicMock(spec=FastAPI)

        register_exception_handlers(app)

        assert app.add_exception_handler.call_count == 3

        calls = app.add_exception_handler.call_args_list

        # AppException handler
        assert calls[0].args[0] is AppException
        assert calls[0].args[1] is app_exception_handler

        # Validation handler
        assert calls[1].args[0] is RequestValidationError
        assert calls[1].args[1] is validation_exception_handler

        # Catch-all handler
        assert calls[2].args[0] is Exception
        assert calls[2].args[1] is unhandled_exception_handler


class TestUnhandledExceptionHandler:
    """Tests for unhandled_exception_handler()."""

    def test_returns_internal_server_error(self) -> None:
        request = MagicMock(spec=Request)
        request.state.request_id = "req-123"

        exc = RuntimeError("unexpected failure")

        response = asyncio.run(
            unhandled_exception_handler(
                request,
                exc,
            )
        )

        assert response.status_code == 500

        payload = json.loads(response.body)

        assert payload["success"] is False
        assert payload["message"] == "Internal server error."
        assert payload["meta"]["request_id"] == "req-123"

        assert payload["errors"][0]["code"] == ErrorCode.INTERNAL_ERROR.value
        assert payload["errors"][0]["message"] == "Internal server error."

    def test_without_request_id(self) -> None:
        """Should handle requests without a request_id."""

        request = MagicMock(spec=Request)
        request.state = SimpleNamespace()

        # Simulate request.state without request_id
        if hasattr(request.state, "request_id"):
            delattr(request.state, "request_id")

        # request.state has no request_id attribute
        response = asyncio.run(
            unhandled_exception_handler(
                request,
                RuntimeError("boom"),
            )
        )

        assert response.status_code == 500

        payload = json.loads(response.body)

        assert payload["success"] is False
        assert payload["message"] == "Internal server error."
        assert payload["meta"]["request_id"] is None

        assert payload["errors"][0]["code"] == ErrorCode.INTERNAL_ERROR.value
