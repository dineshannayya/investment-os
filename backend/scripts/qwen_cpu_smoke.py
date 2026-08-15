"""
Qwen3 CPU inference benchmark.

Runs the same investment-analysis prompt in both Qwen3 modes:

    1. Thinking enabled  -> /think
    2. Thinking disabled -> /no_think

The benchmark intentionally uses the real Qwen GGUF model through
QwenProvider and does not form part of the normal pytest suite.
"""

from __future__ import annotations

import gc
import os
import resource
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.llm.models import LLMMessage, LLMRequest
from app.llm.providers.qwen import QwenProvider

BENCHMARK_MAX_TOKENS = 512
BENCHMARK_TEMPERATURE = 0.0

def has_thinking_content(text: str) -> bool:
    """Return True when Qwen produced non-empty thinking content."""

    if not text:
        return False

    start = text.find("<think>")
    if start == -1:
        return False

    thinking = text[start + len("<think>"):]

    end = thinking.find("</think>")
    if end != -1:
        thinking = thinking[:end]

    return bool(thinking.strip())

@dataclass
class BenchmarkResult:
    """Result of one Qwen benchmark run."""

    mode: str
    thinking_enabled: bool
    load_time_seconds: float
    finish_reason: str | None
    inference_time_seconds: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    tokens_per_second: float
    response_text: str
    thinking_content: bool


def get_peak_memory_mb() -> float:
    """Return process peak RSS in MB on Linux."""

    usage = resource.getrusage(resource.RUSAGE_SELF)

    # Linux reports ru_maxrss in KiB.
    return usage.ru_maxrss / 1024.0


def build_request() -> LLMRequest:
    """Build the fixed benchmark request."""

    return LLMRequest(
        messages=(
            LLMMessage(
                role="system",
                content=(
                    "You are an investment analysis assistant. "
                    "Answer clearly and concisely using business language."
                ),
            ),
            LLMMessage(
                role="user",
                content=(
                    "A startup has ₹10 crore revenue, ₹2 crore EBITDA, "
                    "40% year-over-year revenue growth, and is seeking "
                    "a ₹40 crore valuation. Identify the key valuation "
                    "metrics, calculate the revenue and EBITDA multiples, "
                    "and give a concise preliminary view of what additional "
                    "information an investor should verify before investing."
                ),
            ),
        ),
        temperature=BENCHMARK_TEMPERATURE,
        max_tokens=BENCHMARK_MAX_TOKENS,
    )


def run_benchmark(
    *,
    thinking_enabled: bool,
) -> BenchmarkResult:
    """Run one real Qwen inference benchmark."""

    mode = "THINKING ON" if thinking_enabled else "THINKING OFF"

    print()
    print("-" * 72)
    print(f"Qwen3 benchmark: {mode}")
    print("-" * 72)

    # Make the benchmark independent of the current .env value.
    benchmark_settings = settings.model_copy(
        update={
            "qwen_enable_thinking": thinking_enabled,
        }
    )

    model_path = Path(benchmark_settings.qwen_model_path)

    print(f"Thinking enabled : {thinking_enabled}")
    print(f"Threads          : {benchmark_settings.qwen_threads}")
    print(f"Context size     : {benchmark_settings.qwen_context_size}")
    print(f"Temperature      : {BENCHMARK_TEMPERATURE}")
    print(f"Max tokens       : {BENCHMARK_MAX_TOKENS}")

    print(f"Model            : {model_path}")

    provider = QwenProvider(config=benchmark_settings)

    print()
    print("Loading model...")

    load_start = time.perf_counter()

    try:
        # Explicitly load once so model-loading time is measured
        # separately from inference time.
        provider._get_model()
    except Exception as exc:
        print()
        print("ERROR: Failed to load Qwen model.")
        print(f"       {type(exc).__name__}: {exc}")
        raise

    load_time = time.perf_counter() - load_start

    print(f"Model load time  : {load_time:.2f} sec")

    request = build_request()

    print()
    print("Running inference...")

    inference_start = time.perf_counter()

    try:
        response = provider.generate(request)
    except Exception as exc:
        print()
        print("ERROR: Qwen inference failed.")
        print(f"       {type(exc).__name__}: {exc}")
        raise

    inference_time = time.perf_counter() - inference_start
    thinking_content = has_thinking_content(response.text)
    finish_reason = response.finish_reason

    prompt_tokens = response.usage.prompt_tokens
    completion_tokens = response.usage.completion_tokens
    total_tokens = response.usage.total_tokens

    tokens_per_second = (
        completion_tokens / inference_time
        if completion_tokens > 0 and inference_time > 0
        else 0.0
    )

    print()
    print("Response:")
    print(response.text)

    print()
    print("Metrics:")
    print(f"  Prompt tokens     : {prompt_tokens}")
    print(f"  Completion tokens : {completion_tokens}")
    print(f"  Total tokens      : {total_tokens}")
    print(f"  Inference time    : {inference_time:.2f} sec")
    print(f"  Effective tok/s   : {tokens_per_second:.2f}")
    print(
        f"  Thinking content  : "
        f"{'YES' if thinking_content else 'NO'}"
    )
    print(
        f"  Finish reason    : {finish_reason}",
        flush=True,
    )
    print(f"  Peak process RSS  : {get_peak_memory_mb():.1f} MB")

    return BenchmarkResult(
        mode=mode,
        thinking_enabled=thinking_enabled,
        load_time_seconds=load_time,
        finish_reason=finish_reason,
        inference_time_seconds=inference_time,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        tokens_per_second=tokens_per_second,
        response_text=response.text,
        thinking_content=thinking_content,
    )



def print_summary(
    results: list[BenchmarkResult],
) -> None:
    """Print a compact comparison of both benchmark modes."""

    print()
    print()
    print("=" * 80)
    print("Qwen3-8B CPU BENCHMARK SUMMARY")
    print("=" * 80)

    print(
        f"{'Metric':<24}"
        f"{'THINK ON':>18}"
        f"{'THINK OFF':>18}"
    )
    print("-" * 60)

    for label, getter, formatter in [
        (
            "Load time (sec)",
            lambda result: result.load_time_seconds,
            lambda value: f"{value:.2f}",
        ),
        (
            "Inference time (sec)",
            lambda result: result.inference_time_seconds,
            lambda value: f"{value:.2f}",
        ),
        (
            "Prompt tokens",
            lambda result: result.prompt_tokens,
            lambda value: str(value),
        ),
        (
            "Completion tokens",
            lambda result: result.completion_tokens,
            lambda value: str(value),
        ),
        (
            "Total tokens",
            lambda result: result.total_tokens,
            lambda value: str(value),
        ),
        (
            "Effective tok/s",
            lambda result: result.tokens_per_second,
            lambda value: f"{value:.2f}",
        ),
        (
            "Thinking content",
            lambda result: "YES" if result.thinking_content else "NO",
            lambda value: value,
        ),
        (
            "Finish reason",
            lambda result: result.finish_reason or "UNKNOWN",
            lambda value: value,
        ),
    ]:
        values = [
            getter(result)
            for result in results
        ]

        print(
            f"{label:<24}"
            f"{formatter(values[0]):>18}"
            f"{formatter(values[1]):>18}"
        )

    print()
    print("Configuration:")
    print(f"  CPU              : {os.cpu_count()} logical CPUs")
    print(f"  Qwen threads     : {settings.qwen_threads}")
    print(f"  Context size     : {settings.qwen_context_size}")
    print(f"  Model            : {settings.qwen_model_path}")

    print()
    print("Benchmark completed successfully.")
    print("=" * 80)


def main() -> int:
    """Run both Qwen3 thinking modes."""

    model_path = Path(settings.qwen_model_path)

    print("=" * 80)
    print("Qwen3-8B CPU THINKING-MODE BENCHMARK")
    print("=" * 80)

    print(f"Model path : {model_path}")
    print(f"Model size : {model_path.stat().st_size / (1024**3):.2f} GiB")
    print(f"CPU count  : {os.cpu_count()}")
    print(f"Threads    : {settings.qwen_threads}")
    print(f"Context    : {settings.qwen_context_size}")

    if not model_path.exists():
        print()
        print("ERROR: Qwen model file does not exist.")
        print(f"       {model_path}")
        return 1

    results: list[BenchmarkResult] = []

    try:
        # Run thinking mode first.
        result = run_benchmark(thinking_enabled=True)
        results.append(result)

        # Release the model before loading the second instance.
        #
        # Qwen3-8B Q4_K_M is ~4.7 GiB and the runtime uses substantially
        # more memory than the GGUF file itself.
        gc.collect()

        # Run non-thinking mode.
        result = run_benchmark(thinking_enabled=False)
        results.append(result)

    except Exception:
        print()
        print("Qwen3 CPU benchmark: FAILED")
        return 1

    print_summary(results)

    print()
    print("=" * 80)
    print("Qwen3 CPU benchmark: PASS")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
