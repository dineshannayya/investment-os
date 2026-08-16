"""
Real Qwen startup-analysis benchmark.

Adaptive token-budget benchmark:

    256 -> 512 -> 768 -> 1024

The token budget is increased only when Qwen reports
finish_reason == "length".

This is a benchmark/diagnostic script and does not change
production StartupAnalysisService behavior.
"""

from __future__ import annotations

import gc
import time
from dataclasses import dataclass

from app.core.config import settings
from app.llm.models import LLMRequest
from app.llm.providers.qwen import QwenProvider
from app.prompt.startup_analysis import build_startup_analysis_messages
from app.services.financial_metrics import FinancialMetricsService
from app.services.startup_analysis_parser import (
    StartupAnalysisParseError,
    StartupAnalysisParser,
)
from scripts.startup_analysis_qwen_smoke import build_smoke_input


# ---------------------------------------------------------------------------
# Benchmark configuration
# ---------------------------------------------------------------------------

TOKEN_START = 256
TOKEN_STEP = 256
TOKEN_MAX = 1024

CONTEXT_SIZE = 4096
TEMPERATURE = 0.0


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


@dataclass
class TokenAttempt:
    """Result of one generation attempt."""

    max_tokens: int
    inference_time: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    finish_reason: str | None
    status: str

    @property
    def effective_tokens_per_second(self) -> float:
        if self.inference_time <= 0:
            return 0.0

        return self.completion_tokens / self.inference_time


@dataclass
class ModeBenchmarkResult:
    """Complete benchmark result for one thinking mode."""

    thinking: bool
    provider_load_time: float
    attempts: list[TokenAttempt]

    successful_attempt: TokenAttempt | None = None

    recommendation: str | None = None
    strengths: int = 0
    risks: int = 0
    missing_information: int = 0

    response_text: str | None = None

    @property
    def minimum_successful_tokens(self) -> int | None:
        if self.successful_attempt is None:
            return None

        return self.successful_attempt.max_tokens

    @property
    def total_inference_time(self) -> float:
        return sum(
            attempt.inference_time
            for attempt in self.attempts
        )


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def build_settings(thinking: bool):
    """Build isolated settings for one benchmark mode."""

    return settings.model_copy(
        update={
            "qwen_enable_thinking": thinking,
            "qwen_context_size": CONTEXT_SIZE,
        }
    )


# ---------------------------------------------------------------------------
# Prompt / request preparation
# ---------------------------------------------------------------------------


def build_benchmark_request(
    *,
    max_tokens: int,
) -> tuple[LLMRequest, object]:
    """
    Build the same startup-analysis prompt for every token attempt.

    Only max_tokens changes between attempts.
    """

    analysis_input = build_smoke_input()

    metrics_service = FinancialMetricsService()

    metrics = metrics_service.calculate(
        financials=analysis_input.financials,
        fundraising=analysis_input.fundraising,
        business_model=analysis_input.business_model,
    )

    messages = build_startup_analysis_messages(
        analysis_input=analysis_input,
        metrics=metrics,
    )

    request = LLMRequest(
        messages=messages,
        temperature=TEMPERATURE,
        max_tokens=max_tokens,
    )

    return request, analysis_input


# ---------------------------------------------------------------------------
# Single attempt
# ---------------------------------------------------------------------------


def run_single_attempt(
    *,
    provider: QwenProvider,
    request: LLMRequest,
    max_tokens: int,
) -> tuple[TokenAttempt, str]:
    """Run one Qwen generation attempt."""

    print()
    print(f"Attempt max tokens : {max_tokens}")
    print("Running inference...", flush=True)

    start = time.perf_counter()

    response = provider.generate(request)

    elapsed = time.perf_counter() - start

    usage = response.usage

    if response.finish_reason == "length":
        status = "TRUNCATED"
    else:
        status = "GENERATED"

    attempt = TokenAttempt(
        max_tokens=max_tokens,
        inference_time=elapsed,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,
        finish_reason=response.finish_reason,
        status=status,
    )

    print(f"Inference time    : {elapsed:.2f} sec")
    print(f"Prompt tokens     : {usage.prompt_tokens}")
    print(f"Completion tokens : {usage.completion_tokens}")
    print(f"Total tokens      : {usage.total_tokens}")
    print(f"Finish reason     : {response.finish_reason}")
    print(
        f"Effective tok/s   : "
        f"{attempt.effective_tokens_per_second:.2f}"
    )
    print(f"Status            : {status}")

    return attempt, response.text


# ---------------------------------------------------------------------------
# Adaptive benchmark for one thinking mode
# ---------------------------------------------------------------------------


def run_mode_benchmark(
    *,
    thinking: bool,
) -> ModeBenchmarkResult:
    """Run adaptive 256/512/768/1024 benchmark."""

    benchmark_settings = build_settings(thinking)

    print()
    print("=" * 80)
    print(
        "QWEN STARTUP ANALYSIS — "
        f"THINKING {'ON' if thinking else 'OFF'}"
    )
    print("=" * 80)

    print(f"Thinking          : {thinking}")
    print(f"Threads           : {benchmark_settings.qwen_threads}")
    print(f"Context           : {CONTEXT_SIZE}")
    print(f"Temperature       : {TEMPERATURE}")
    print(
        f"Token range       : "
        f"{TOKEN_START} -> {TOKEN_MAX} "
        f"(step {TOKEN_STEP})"
    )

    # -----------------------------------------------------------------------
    # Build provider once.
    # -----------------------------------------------------------------------

    print()
    print("Building Qwen provider...")

    load_start = time.perf_counter()

    provider = QwenProvider(
        config=benchmark_settings,
    )

    # QwenProvider loads the model lazily.
    provider._get_model()

    provider_load_time = time.perf_counter() - load_start

    print(
        f"Model load time   : "
        f"{provider_load_time:.2f} sec"
    )

    # -----------------------------------------------------------------------
    # Build the common prompt once.
    # -----------------------------------------------------------------------

    analysis_input = build_smoke_input()

    metrics_service = FinancialMetricsService()

    metrics = metrics_service.calculate(
        financials=analysis_input.financials,
        fundraising=analysis_input.fundraising,
        business_model=analysis_input.business_model,
    )

    messages = build_startup_analysis_messages(
        analysis_input=analysis_input,
        metrics=metrics,
    )

    parser = StartupAnalysisParser()

    result = ModeBenchmarkResult(
        thinking=thinking,
        provider_load_time=provider_load_time,
        attempts=[],
    )

    # -----------------------------------------------------------------------
    # Adaptive token escalation.
    # -----------------------------------------------------------------------

    max_tokens = TOKEN_START

    while max_tokens <= TOKEN_MAX:
        request = LLMRequest(
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=max_tokens,
        )

        attempt, response_text = run_single_attempt(
            provider=provider,
            request=request,
            max_tokens=max_tokens,
        )

        result.attempts.append(attempt)

        # ---------------------------------------------------------------
        # Truncated response:
        # increase token budget if possible.
        # ---------------------------------------------------------------

        if attempt.finish_reason == "length":

            print(
                f"Token limit reached at {max_tokens}."
            )

            if max_tokens == TOKEN_MAX:
                print(
                    "Maximum token budget reached. "
                    "Stopping benchmark."
                )

                result.response_text = response_text
                break

            max_tokens += TOKEN_STEP

            print(
                f"Increasing token budget to {max_tokens}..."
            )

            continue

        # ---------------------------------------------------------------
        # Complete generation:
        # parse it.
        # ---------------------------------------------------------------

        try:
            parsed = parser.parse(response_text)

        except StartupAnalysisParseError as exc:
            attempt.status = "PARSE_ERROR"

            print()
            print("Generation       : COMPLETE")
            print("Parser            : PARSE_ERROR")
            print(
                f"Parser error      : "
                f"{type(exc).__name__}: {exc}"
            )

            result.response_text = response_text
            break

        # ---------------------------------------------------------------
        # Successful complete analysis.
        # ---------------------------------------------------------------

        attempt.status = "PASS"

        result.successful_attempt = attempt
        result.response_text = response_text

        result.recommendation = (
            parsed.preliminary_recommendation
        )

        result.strengths = len(parsed.strengths)
        result.risks = len(parsed.risks)
        result.missing_information = len(
            parsed.missing_information
        )

        print()
        print("Generation       : COMPLETE")
        print("Parser            : PASS")
        print(
            "Minimum successful "
            f"token budget     : {max_tokens}"
        )

        break

    # -----------------------------------------------------------------------
    # Cleanup before next thinking mode.
    # -----------------------------------------------------------------------

    del provider
    gc.collect()

    return result


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def print_attempt_summary(
    result: ModeBenchmarkResult,
) -> None:
    """Print all token-budget attempts."""

    print()
    print(
        f"Token attempts — "
        f"Thinking {'ON' if result.thinking else 'OFF'}"
    )

    print("-" * 80)

    print(
        f"{'Max':>8}"
        f"{'Time(s)':>12}"
        f"{'Prompt':>10}"
        f"{'Completion':>12}"
        f"{'Finish':>12}"
        f"{'Status':>16}"
    )

    print("-" * 80)

    for attempt in result.attempts:
        print(
            f"{attempt.max_tokens:>8}"
            f"{attempt.inference_time:>12.2f}"
            f"{attempt.prompt_tokens:>10}"
            f"{attempt.completion_tokens:>12}"
            f"{str(attempt.finish_reason):>12}"
            f"{attempt.status:>16}"
        )


def print_comparison(
    off: ModeBenchmarkResult,
    on: ModeBenchmarkResult,
) -> None:
    """Print final OFF vs ON comparison."""

    print()
    print("=" * 80)
    print("QWEN STARTUP ANALYSIS BENCHMARK — COMPARISON")
    print("=" * 80)

    print()
    print(
        f"{'Metric':<30}"
        f"{'Thinking OFF':>18}"
        f"{'Thinking ON':>18}"
    )

    print("-" * 70)

    off_tokens = off.minimum_successful_tokens
    on_tokens = on.minimum_successful_tokens

    off_attempt = off.successful_attempt
    on_attempt = on.successful_attempt

    print(
        f"{'Model load (sec)':<30}"
        f"{off.provider_load_time:>18.2f}"
        f"{on.provider_load_time:>18.2f}"
    )

    print(
        f"{'Attempts':<30}"
        f"{len(off.attempts):>18}"
        f"{len(on.attempts):>18}"
    )

    print(
        f"{'Total inference (sec)':<30}"
        f"{off.total_inference_time:>18.2f}"
        f"{on.total_inference_time:>18.2f}"
    )

    print(
        f"{'Minimum successful tokens':<30}"
        f"{str(off_tokens):>18}"
        f"{str(on_tokens):>18}"
    )

    print(
        f"{'Final finish reason':<30}"
        f"{str(off.attempts[-1].finish_reason):>18}"
        f"{str(on.attempts[-1].finish_reason):>18}"
    )

    print(
        f"{'Final status':<30}"
        f"{off.attempts[-1].status:>18}"
        f"{on.attempts[-1].status:>18}"
    )

    print(
        f"{'Recommendation':<30}"
        f"{str(off.recommendation):>18}"
        f"{str(on.recommendation):>18}"
    )

    print(
        f"{'Strengths':<30}"
        f"{off.strengths:>18}"
        f"{on.strengths:>18}"
    )

    print(
        f"{'Risks':<30}"
        f"{off.risks:>18}"
        f"{on.risks:>18}"
    )

    print(
        f"{'Missing information':<30}"
        f"{off.missing_information:>18}"
        f"{on.missing_information:>18}"
    )

    print()
    print("=" * 80)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    """Run both thinking modes."""

    print("=" * 80)
    print("QWEN3-8B STARTUP ANALYSIS ADAPTIVE BENCHMARK")
    print("=" * 80)

    print(f"Model path : {settings.qwen_model_path}")
    print(f"Context    : {CONTEXT_SIZE}")
    print(f"Threads    : {settings.qwen_threads}")
    print(
        f"Token range: "
        f"{TOKEN_START} -> {TOKEN_MAX} "
        f"(step {TOKEN_STEP})"
    )

    # -----------------------------------------------------------------------
    # Thinking OFF
    # -----------------------------------------------------------------------

    off = run_mode_benchmark(
        thinking=False,
    )

    print_attempt_summary(off)

    # -----------------------------------------------------------------------
    # Thinking ON
    # -----------------------------------------------------------------------

    on = run_mode_benchmark(
        thinking=True,
    )

    print_attempt_summary(on)

    # -----------------------------------------------------------------------
    # Comparison
    # -----------------------------------------------------------------------

    print_comparison(
        off,
        on,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
