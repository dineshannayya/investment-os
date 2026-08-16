"""
Qwen local LLM provider.

Provides local Qwen inference through llama-cpp-python.
"""

from __future__ import annotations

from typing import Any

from llama_cpp import Llama

from app.core.config import Settings, settings
from app.llm.base import LLMProvider
from app.llm.models import (
    LLMRequest,
    LLMResponse,
    LLMUsage,
)


class QwenProvider(LLMProvider):
    """
    Local Qwen provider backed by llama.cpp.
    """

    NAME = "qwen"

    def __init__(
        self,
        *,
        config: Settings | None = None,
    ) -> None:
        self._settings = config or settings
        self._model: Llama | None = None

    @property
    def name(self) -> str:
        """Return provider name."""
        return self.NAME

    def _get_model(self) -> Llama:
        """
        Lazily load and cache the Qwen GGUF model.
        """

        if self._model is None:
            self._model = Llama(
                model_path=self._settings.qwen_model_path,
                n_ctx=self._settings.qwen_context_size,
                n_threads=self._settings.qwen_threads,
                verbose=False,
            )

        return self._model


    def _is_thinking_enabled(
        self,
        request: LLMRequest,
    ) -> bool:
        """Return the effective thinking mode for this request."""

        value = request.metadata.get("thinking_enabled")

        if value is None:
            return self._settings.qwen_enable_thinking

        return bool(value)

    def _apply_thinking_mode(
        self,
        messages: list[dict[str, str]],
        *,
        thinking_enabled: bool,
    ) -> list[dict[str, str]]:
        """Apply Qwen3 thinking mode to the latest user message."""

        directive = "/think" if thinking_enabled else "/no_think"

        result = [message.copy() for message in messages]

        for message in reversed(result):
            if message["role"] != "user":
                continue

            content = message["content"].rstrip()

            if content.endswith("/think"):
                content = content[: -len("/think")].rstrip()
            elif content.endswith("/no_think"):
                content = content[: -len("/no_think")].rstrip()

            message["content"] = f"{content}\n{directive}"
            break

        return result

    def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """
        Generate a response from the local Qwen model.
        """

        model = self._get_model()

        messages: list[dict[str, str]] = [
            {
                "role": message.role,
                "content": message.content,
            }
            for message in request.messages
        ]

        thinking_enabled = self._is_thinking_enabled(request)
        
        messages = self._apply_thinking_mode(
            messages,
            thinking_enabled=thinking_enabled,
        )

        response: dict[str, Any] = model.create_chat_completion(
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        choice = response["choices"][0]
        message = choice.get("message", {})

        text = message.get("content") or ""

        usage_data = response.get("usage", {})

        usage = LLMUsage(
            prompt_tokens=usage_data.get(
                "prompt_tokens",
                0,
            ),
            completion_tokens=usage_data.get(
                "completion_tokens",
                0,
            ),
            total_tokens=usage_data.get(
                "total_tokens",
                0,
            ),
        )

        finish_reason = response["choices"][0].get("finish_reason")

        return LLMResponse(
            text=text,
            model=request.model or self._settings.llm_model,
            usage=usage,
            finish_reason=finish_reason,
            metadata={
                "provider": self.NAME,
                "thinking_enabled": thinking_enabled,
            }

        )
