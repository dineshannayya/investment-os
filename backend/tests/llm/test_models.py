"""
Tests for provider-independent LLM domain models.
"""

from __future__ import annotations

from types import MappingProxyType

import pytest

from app.llm.models import (
    LLMMessage,
    LLMRequest,
    LLMResponse,
    LLMUsage,
)


class TestLLMMessage:
    """Tests for LLMMessage."""

    def test_create(self):

        message = LLMMessage(
            role="user",
            content="Analyze this startup.",
        )

        assert message.role == "user"
        assert message.content == "Analyze this startup."

    @pytest.mark.parametrize(
        "role",
        [
            "system",
            "user",
            "assistant",
        ],
    )
    def test_supported_roles(self, role):

        message = LLMMessage(
            role=role,
            content="Example",
        )

        assert message.role == role

    def test_invalid_role(self):

        with pytest.raises(
            ValueError,
            match="Unsupported message role",
        ):
            LLMMessage(
                role="developer",
                content="Example",
            )

    def test_empty_content(self):

        with pytest.raises(
            ValueError,
            match="Message content must not be empty",
        ):
            LLMMessage(
                role="user",
                content="",
            )

    def test_frozen(self):

        message = LLMMessage(
            role="user",
            content="Example",
        )

        with pytest.raises(AttributeError):
            message.content = "Changed"


class TestLLMUsage:
    """Tests for LLMUsage."""

    def test_defaults(self):

        usage = LLMUsage()

        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0

    def test_create(self):

        usage = LLMUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )

        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150

    @pytest.mark.parametrize(
        "field",
        [
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
        ],
    )
    def test_negative_usage_is_rejected(self, field):

        with pytest.raises(
            ValueError,
            match="must be non-negative",
        ):
            LLMUsage(
                **{
                    field: -1,
                }
            )

    def test_frozen(self):

        usage = LLMUsage(
            prompt_tokens=10,
        )

        with pytest.raises(AttributeError):
            usage.prompt_tokens = 20


class TestLLMRequest:
    """Tests for LLMRequest."""

    @staticmethod
    def create_message():

        return LLMMessage(
            role="user",
            content="Analyze this startup.",
        )

    def test_create(self):

        message = self.create_message()

        request = LLMRequest(
            messages=(message,),
        )

        assert request.messages == (message,)
        assert request.model is None
        assert request.temperature == 0.0
        assert request.max_tokens is None

    def test_create_with_parameters(self):

        message = self.create_message()

        request = LLMRequest(
            messages=(message,),
            model="test-model",
            temperature=0.7,
            max_tokens=1000,
        )

        assert request.model == "test-model"
        assert request.temperature == pytest.approx(0.7)
        assert request.max_tokens == 1000

    def test_empty_messages(self):

        with pytest.raises(
            ValueError,
            match="at least one message",
        ):
            LLMRequest(
                messages=(),
            )

    @pytest.mark.parametrize(
        "temperature",
        [
            -0.1,
            2.1,
        ],
    )
    def test_invalid_temperature(
        self,
        temperature,
    ):

        with pytest.raises(
            ValueError,
            match="temperature must be between",
        ):
            LLMRequest(
                messages=(self.create_message(),),
                temperature=temperature,
            )

    def test_temperature_boundaries(self):

        low = LLMRequest(
            messages=(self.create_message(),),
            temperature=0.0,
        )

        high = LLMRequest(
            messages=(self.create_message(),),
            temperature=2.0,
        )

        assert low.temperature == 0.0
        assert high.temperature == 2.0

    def test_invalid_max_tokens(self):

        with pytest.raises(
            ValueError,
            match="max_tokens must be greater than zero",
        ):
            LLMRequest(
                messages=(self.create_message(),),
                max_tokens=0,
            )

        with pytest.raises(
            ValueError,
            match="max_tokens must be greater than zero",
        ):
            LLMRequest(
                messages=(self.create_message(),),
                max_tokens=-1,
            )

    def test_metadata_default_is_immutable(self):

        request = LLMRequest(
            messages=(self.create_message(),),
        )

        assert request.metadata == {}
        assert isinstance(
            request.metadata,
            MappingProxyType,
        )

        with pytest.raises(TypeError):
            request.metadata["key"] = "value"

    def test_metadata_is_immutable(self):

        request = LLMRequest(
            messages=(self.create_message(),),
            metadata={
                "request_type": "startup_analysis",
            },
        )

        assert (
            request.metadata["request_type"]
            == "startup_analysis"
        )

        with pytest.raises(TypeError):
            request.metadata["request_type"] = "changed"

    def test_metadata_is_detached_from_source(self):

        metadata = {
            "request_type": "startup_analysis",
        }

        request = LLMRequest(
            messages=(self.create_message(),),
            metadata=metadata,
        )

        metadata["request_type"] = "changed"

        assert (
            request.metadata["request_type"]
            == "startup_analysis"
        )

    def test_frozen(self):

        request = LLMRequest(
            messages=(self.create_message(),),
        )

        with pytest.raises(AttributeError):
            request.temperature = 1.0


class TestLLMResponse:
    """Tests for LLMResponse."""

    def test_create(self):

        response = LLMResponse(
            text="The startup has moderate investment risk.",
        )

        assert (
            response.text
            == "The startup has moderate investment risk."
        )
        assert response.model is None
        assert isinstance(
            response.usage,
            LLMUsage,
        )
        assert response.usage == LLMUsage()

    def test_create_with_model_and_usage(self):

        usage = LLMUsage(
            prompt_tokens=500,
            completion_tokens=200,
            total_tokens=700,
        )

        response = LLMResponse(
            text="Analysis result",
            model="test-model",
            usage=usage,
        )

        assert response.text == "Analysis result"
        assert response.model == "test-model"
        assert response.usage is usage

    def test_empty_text(self):

        with pytest.raises(
            ValueError,
            match="LLMResponse text must not be empty",
        ):
            LLMResponse(
                text="",
            )

    def test_metadata_default_is_immutable(self):

        response = LLMResponse(
            text="Analysis result",
        )

        assert response.metadata == {}
        assert isinstance(
            response.metadata,
            MappingProxyType,
        )

        with pytest.raises(TypeError):
            response.metadata["key"] = "value"

    def test_metadata_is_immutable(self):

        response = LLMResponse(
            text="Analysis result",
            metadata={
                "finish_reason": "stop",
            },
        )

        assert (
            response.metadata["finish_reason"]
            == "stop"
        )

        with pytest.raises(TypeError):
            response.metadata["finish_reason"] = "length"

    def test_metadata_is_detached_from_source(self):

        metadata = {
            "provider": "test",
        }

        response = LLMResponse(
            text="Analysis result",
            metadata=metadata,
        )

        metadata["provider"] = "changed"

        assert (
            response.metadata["provider"]
            == "test"
        )

    def test_frozen(self):

        response = LLMResponse(
            text="Analysis result",
        )

        with pytest.raises(AttributeError):
            response.text = "Changed"
