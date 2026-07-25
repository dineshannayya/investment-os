"""
Tests for RequestContext.
"""

from uuid import uuid4

import pytest

from app.core.middleware.request_context import RequestContext


class TestRequestContext:
    """Tests for RequestContext."""

    def test_context_initialization(self):
        request_id = uuid4()

        context = RequestContext(
            request_id=request_id,
            method="GET",
            path="/health",
        )

        assert context.request_id == request_id
        assert context.method == "GET"
        assert context.path == "/health"

    def test_start_time_initialized(self):
        context = RequestContext(
            request_id=uuid4(),
            method="GET",
            path="/health",
        )

        assert context.start_time > 0

    def test_default_values(self):
        context = RequestContext(
            request_id=uuid4(),
            method="GET",
            path="/health",
        )

        assert context.status_code is None
        assert context.duration_ms is None
        assert context.exception is None
        assert context.user_id is None
        assert context.workspace is None

    def test_extra_defaults_to_empty_dict(self):
        context = RequestContext(
            request_id=uuid4(),
            method="GET",
            path="/health",
        )

        assert context.extra == {}

    def test_extra_not_shared_between_instances(self):
        ctx1 = RequestContext(
            request_id=uuid4(),
            method="GET",
            path="/one",
        )

        ctx2 = RequestContext(
            request_id=uuid4(),
            method="GET",
            path="/two",
        )

        ctx1.extra["user"] = "alice"

        assert ctx2.extra == {}

    def test_can_store_exception(self):
        context = RequestContext(
            request_id=uuid4(),
            method="GET",
            path="/health",
        )

        exc = RuntimeError("failure")

        context.exception = exc

        assert context.exception is exc

    def test_can_store_user_information(self):
        context = RequestContext(
            request_id=uuid4(),
            method="GET",
            path="/health",
        )

        context.user_id = "user-123"
        context.workspace = "workspace-1"

        assert context.user_id == "user-123"
        assert context.workspace == "workspace-1"

    def test_slots_prevent_dynamic_attributes(self):
        context = RequestContext(
            request_id=uuid4(),
            method="GET",
            path="/health",
        )

        with pytest.raises(AttributeError):
            context.random_field = "should fail"
