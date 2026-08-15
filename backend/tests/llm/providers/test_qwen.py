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
from scripts.qwen_cpu_smoke import has_thinking_content


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
            qwen_enable_thinking=False,
            llm_model="test-qwen",
        )
        
        provider = QwenProvider(config=config)
        
        assert provider._settings is config
        assert provider._settings.qwen_model_path == "/test/model.gguf"
        assert provider._settings.qwen_context_size == 4096
        assert provider._settings.qwen_threads == 4
        assert provider._settings.qwen_enable_thinking is False


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
                "content": "Analyze this startup.\n/think",
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
            "Follow-up question\n/think",
        ]


    # Test 1 — thinking enabled
    @patch("app.llm.providers.qwen.Llama")
    def test_thinking_mode_adds_think_directive(self, mock_llama):
        """Thinking mode should append /think to the latest user message."""
    
        mock_model = MagicMock()
        mock_model.create_chat_completion.return_value = (
            self.mock_llama_response()
        )
        mock_llama.return_value = mock_model
    
        from app.core.config import Settings
    
        config = Settings(
            database_url="postgresql://test",
            redis_url="redis://localhost",
            qwen_enable_thinking=True,
        )
    
        provider = QwenProvider(config=config)
    
        provider.generate(
            self.make_request(
                messages=(
                    LLMMessage(
                        role ="user",
                        content = "Analyze this startup.",
                    ),
                ),
            )
        )
    
        messages = (
            mock_model.create_chat_completion.call_args
            .kwargs["messages"]
        )
    
        assert messages[-1]["content"] == (
            "Analyze this startup.\n/think"
        )
    
    # Test 2 — thinking disabled
    @patch("app.llm.providers.qwen.Llama")
    def test_non_thinking_mode_adds_no_think_directive(self, mock_llama):
        """Non-thinking mode should append /no_think."""
    
        mock_model = MagicMock()
        mock_model.create_chat_completion.return_value = (
            self.mock_llama_response()
        )
        mock_llama.return_value = mock_model
    
        from app.core.config import Settings
    
        config = Settings(
            database_url="postgresql://test",
            redis_url="redis://localhost",
            qwen_enable_thinking=False,
        )
    
        provider = QwenProvider(config=config)
    
        provider.generate(self.make_request())
    
        messages = (
            mock_model.create_chat_completion.call_args
            .kwargs["messages"]
        )
    
        assert messages[-1]["content"] == (
            "What is EBITDA?\n/no_think"
        )
    
    # 4. Test replacement of an existing directive
    
    @patch("app.llm.providers.qwen.Llama")
    def test_existing_think_directive_is_replaced(
        self,
        mock_llama,
    ):
        """An existing /think directive should be replaced when disabled."""
    
        mock_model = MagicMock()
        mock_model.create_chat_completion.return_value = (
            self.mock_llama_response()
        )
        mock_llama.return_value = mock_model
    
        from app.core.config import Settings
    
        config = Settings(
            database_url="postgresql://test",
            redis_url="redis://localhost",
            qwen_enable_thinking=False,
        )
    
        provider = QwenProvider(config=config)
    
        provider.generate(
            self.make_request(
                messages=(
                    LLMMessage(
                        role="user",
                        content="Analyze this startup.\n/think",
                    ),
                ),
            )
        )
    
        messages = (
            mock_model.create_chat_completion.call_args
            .kwargs["messages"]
        )
    
        assert messages[-1]["content"] == (
            "Analyze this startup.\n/no_think"
        )
    
    @patch("app.llm.providers.qwen.Llama")
    def test_existing_no_think_directive_is_replaced(
        self,
        mock_llama,
    ):
        """An existing /no_think directive should be replaced when enabled."""
    
        mock_model = MagicMock()
        mock_model.create_chat_completion.return_value = (
            self.mock_llama_response()
        )
        mock_llama.return_value = mock_model
    
        from app.core.config import Settings
    
        config = Settings(
            database_url="postgresql://test",
            redis_url="redis://localhost",
            qwen_enable_thinking=True,
        )
    
        provider = QwenProvider(config=config)
    
        provider.generate(
            self.make_request(
                messages=(
                    LLMMessage(
                        role="user",
                        content="Analyze this startup.\n/no_think",
                    ),
                ),
            )
        )
    
        messages = (
            mock_model.create_chat_completion.call_args
            .kwargs["messages"]
        )
    
        assert messages[-1]["content"] == (
            "Analyze this startup.\n/think"
        )
    
    # 5. Test only the latest user message is modified
    @patch("app.llm.providers.qwen.Llama")
    def test_thinking_mode_modifies_only_latest_user_message(
        self,
        mock_llama,
    ):
        """Only the latest user message should receive the directive."""
    
        mock_model = MagicMock()
        mock_model.create_chat_completion.return_value = (
            self.mock_llama_response()
        )
        mock_llama.return_value = mock_model
    
        provider = QwenProvider()
    
        messages = (
            LLMMessage(
                role="system",
                content="You are an investment analyst.",
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
    
        provider.generate(
            self.make_request(messages=messages),
        )
    
        forwarded = (
            mock_model.create_chat_completion.call_args
            .kwargs["messages"]
        )
    
        assert forwarded[1]["content"] == "First question"
    
        assert forwarded[3]["content"] == (
            "Follow-up question\n/think"
        )
    
    # 6. Test system/assistant messages remain unchanged
    
    @patch("app.llm.providers.qwen.Llama")
    def test_thinking_mode_preserves_non_user_messages(
        self,
        mock_llama,
    ):
        """System and assistant messages must remain unchanged."""
    
        mock_model = MagicMock()
        mock_model.create_chat_completion.return_value = (
            self.mock_llama_response()
        )
        mock_llama.return_value = mock_model
    
        provider = QwenProvider()
    
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
    
        provider.generate(
            self.make_request(messages=messages),
        )
    
        forwarded = (
            mock_model.create_chat_completion.call_args
            .kwargs["messages"]
        )
    
        assert forwarded[0] == {
            "role": "system",
            "content": "You are an investment analyst.",
        }
    
        assert forwarded[2] == {
            "role": "assistant",
            "content": "I need more information.",
        }

    @patch("app.llm.providers.qwen.Llama")
    def test_response_metadata_contains_thinking_mode(
        self,
        mock_llama,
    ):
        """Response metadata should record the Qwen thinking mode."""
    
        mock_model = MagicMock()
        mock_model.create_chat_completion.return_value = (
            self.mock_llama_response()
        )
        mock_llama.return_value = mock_model
    
        from app.core.config import Settings
    
        config = Settings(
            database_url="postgresql://test",
            redis_url="redis://localhost",
            qwen_enable_thinking=False,
        )
    
        provider = QwenProvider(config=config)
    
        response = provider.generate(
            self.make_request(),
        )
    
        assert response.metadata["provider"] == "qwen"
        assert response.metadata["thinking_enabled"] is False

def test_has_thinking_content_with_reasoning():
    text = """<think>
This is the model's reasoning.
It contains multiple lines.
</think>

Final answer.
"""

    assert has_thinking_content(text) is True

def test_has_thinking_content_with_empty_block():
    text = """<think>

</think>

Final answer.
"""

    assert has_thinking_content(text) is False

def test_has_thinking_content_without_tags():
    text = "Final answer without thinking tags."

    assert has_thinking_content(text) is False

def test_has_thinking_content_inline():
    text = "<think>short reasoning</think>Final answer."

    assert has_thinking_content(text) is True

    
