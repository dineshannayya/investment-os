"""
Tests for the local Qwen LLM provider.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.llm.models import (
    LLMMessage,
    LLMRequest,
    LLMResponse,
)
from app.llm.providers.qwen import QwenProvider


class TestQwenProvider:
    """Tests for QwenProvider."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def make_request(
        *,
        messages: tuple[LLMMessage, ...] | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = 128,
    ) -> LLMRequest:
        """Create a standard test request."""

        if messages is None:
            messages = (
                LLMMessage(
                    role="user",
                    content="What is EBITDA?",
                ),
            )

        return LLMRequest(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @staticmethod
    def mock_llama_response(
        *,
        text: str = "EBITDA is earnings before interest, taxes, depreciation and amortization.",
        prompt_tokens: int = 10,
        completion_tokens: int = 20,
        total_tokens: int = 30,
    ) -> dict:
        """Create a llama.cpp-compatible response."""

        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": text,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
        }

    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------

    def test_provider_initialization(self):
        """Provider should initialize without loading the model."""

        provider = QwenProvider()

        assert provider.name == "qwen"
        assert provider._model is None

    def test_custom_settings(self):
        """Provider should retain explicitly supplied settings."""

        from app.core.config import Settings

        config = Settings(
            database_url="postgresql://test",
            redis_url="redis://localhost",
            qwen_model_path="/test/model.gguf",
            qwen_context_size=4096,
            qwen_threads=4,
            llm_model="test-qwen",
        )

        provider = QwenProvider(config=config)

        assert provider._settings is config
        assert provider._settings.qwen_model_path == "/test/model.gguf"
        assert provider._settings.qwen_context_size == 4096
        assert provider._settings.qwen_threads == 4

    # ------------------------------------------------------------------
    # Lazy loading
    # ------------------------------------------------------------------

    @patch("app.llm.providers.qwen.Llama")
    def test_model_is_loaded_lazily(self, mock_llama):
        """Creating the provider must not load the GGUF model."""

        provider = QwenProvider()

        mock_llama.assert_not_called()
        assert provider._model is None

    @patch("app.llm.providers.qwen.Llama")
    def test_model_loaded_on_first_generate(self, mock_llama):
        """First generation should initialize the model."""

        mock_model = MagicMock()
        mock_model.create_chat_completion.return_value = (
            self.mock_llama_response()
        )
        mock_llama.return_value = mock_model

        provider = QwenProvider()

        provider.generate(self.make_request())

        mock_llama.assert_called_once()
        assert provider._model is mock_model

    # ------------------------------------------------------------------
    # Model configuration
    # ------------------------------------------------------------------

    @patch("app.llm.providers.qwen.Llama")
    def test_model_configuration(self, mock_llama):
        """Provider should pass configured runtime values to llama.cpp."""

        mock_model = MagicMock()
        mock_model.create_chat_completion.return_value = (
            self.mock_llama_response()
        )
        mock_llama.return_value = mock_model

        from app.core.config import Settings

        config = Settings(
            database_url="postgresql://test",
            redis_url="redis://localhost",
            qwen_model_path="/models/test.gguf",
            qwen_context_size=4096,
            qwen_threads=4,
        )

        provider = QwenProvider(config=config)

        provider.generate(self.make_request())

        mock_llama.assert_called_once_with(
            model_path="/models/test.gguf",
            n_ctx=4096,
            n_threads=4,
            verbose=False,
        )

    # ------------------------------------------------------------------
    # Message conversion
    # ------------------------------------------------------------------

    @patch("app.llm.providers.qwen.Llama")
    def test_messages_are_forwarded(self, mock_llama):
        """All provider-independent messages should reach llama.cpp."""

        mock_model = MagicMock()
        mock_model.create_chat_completion.return_value = (
            self.mock_llama_response()
        )
        mock_llama.return_value = mock_model

        messages = (
            LLMMessage(
                role="system",
                content="You are an investment analyst.",
            ),
            LLMMessage(
                role="user",
                content="Analyze this startup.",
            ),
            LLMMessage(
                role="assistant",
                content="I need more information.",
            ),
        )

        request = self.make_request(messages=messages)

        provider = QwenProvider()
        provider.generate(request)

        call = mock_model.create_chat_completion.call_args

        assert call.kwargs["messages"] == [
            {
                "role": "system",
                "content": "You are an investment analyst.",
            },
            {
                "role": "user",
                "content": "Analyze this startup.",
            },
            {
                "role": "assistant",
                "content": "I need more information.",
            },
        ]

    # ------------------------------------------------------------------
    # Generation parameters
    # ------------------------------------------------------------------

    @patch("app.llm.providers.qwen.Llama")
    def test_generation_parameters_are_forwarded(self, mock_llama):
        """Temperature and max_tokens should reach llama.cpp."""

        mock_model = MagicMock()
        mock_model.create_chat_completion.return_value = (
            self.mock_llama_response()
        )
        mock_llama.return_value = mock_model

        request = self.make_request(
            temperature=0.7,
            max_tokens=512,
        )

        provider = QwenProvider()
        provider.generate(request)

        call = mock_model.create_chat_completion.call_args

        assert call.kwargs["temperature"] == 0.7
        assert call.kwargs["max_tokens"] == 512

    # ------------------------------------------------------------------
    # Response normalization
    # ------------------------------------------------------------------

    @patch("app.llm.providers.qwen.Llama")
    def test_response_is_normalized(self, mock_llama):
        """llama.cpp response should become LLMResponse."""

        mock_model = MagicMock()
        mock_model.create_chat_completion.return_value = (
            self.mock_llama_response(
                text="Revenue is the top-line income of a company."
            )
        )
        mock_llama.return_value = mock_model

        provider = QwenProvider()

        response = provider.generate(
            self.make_request(),
        )

        assert isinstance(response, LLMResponse)
        assert response.text == (
            "Revenue is the top-line income of a company."
        )
        assert response.model == "qwen3-8b-q4"
        assert response.metadata["provider"] == "qwen"

    # ------------------------------------------------------------------
    # Usage
    # ------------------------------------------------------------------

    @patch("app.llm.providers.qwen.Llama")
    def test_usage_is_normalized(self, mock_llama):
        """Token usage should become LLMUsage."""

        mock_model = MagicMock()
        mock_model.create_chat_completion.return_value = (
            self.mock_llama_response(
                prompt_tokens=25,
                completion_tokens=50,
                total_tokens=75,
            )
        )
        mock_llama.return_value = mock_model

        provider = QwenProvider()

        response = provider.generate(
            self.make_request(),
        )

        assert response.usage.prompt_tokens == 25
        assert response.usage.completion_tokens == 50
        assert response.usage.total_tokens == 75

    # ------------------------------------------------------------------
    # Model override
    # ------------------------------------------------------------------

    @patch("app.llm.providers.qwen.Llama")
    def test_request_model_overrides_configured_model(
        self,
        mock_llama,
    ):
        """Request model should override the configured model identifier."""

        mock_model = MagicMock()
        mock_model.create_chat_completion.return_value = (
            self.mock_llama_response()
        )
        mock_llama.return_value = mock_model

        provider = QwenProvider()

        response = provider.generate(
            self.make_request(
                model="qwen3-custom",
            )
        )

        assert response.model == "qwen3-custom"

    # ------------------------------------------------------------------
    # Model caching
    # ------------------------------------------------------------------

    @patch("app.llm.providers.qwen.Llama")
    def test_model_loaded_only_once(self, mock_llama):
        """Multiple generations should reuse the same model instance."""

        mock_model = MagicMock()
        mock_model.create_chat_completion.return_value = (
            self.mock_llama_response()
        )
        mock_llama.return_value = mock_model

        provider = QwenProvider()

        provider.generate(self.make_request())
        provider.generate(self.make_request())

        mock_llama.assert_called_once()
        assert mock_model.create_chat_completion.call_count == 2

    # ------------------------------------------------------------------
    # Multiple messages
    # ------------------------------------------------------------------

    @patch("app.llm.providers.qwen.Llama")
    def test_conversation_messages_preserve_order(self, mock_llama):
        """Conversation message order must be preserved."""

        mock_model = MagicMock()
        mock_model.create_chat_completion.return_value = (
            self.mock_llama_response()
        )
        mock_llama.return_value = mock_model

        messages = (
            LLMMessage(
                role="system",
                content="System instruction",
            ),
            LLMMessage(
                role="user",
                content="First question",
            ),
            LLMMessage(
                role="assistant",
                content="First answer",
            ),
            LLMMessage(
                role="user",
                content="Follow-up question",
            ),
        )

        provider = QwenProvider()

        provider.generate(
            self.make_request(messages=messages),
        )

        forwarded = (
            mock_model.create_chat_completion.call_args
            .kwargs["messages"]
        )

        assert [message["role"] for message in forwarded] == [
            "system",
            "user",
            "assistant",
            "user",
        ]

        assert [message["content"] for message in forwarded] == [
            "System instruction",
            "First question",
            "First answer",
            "Follow-up question",
        ]
