"""
Real Qwen startup-analysis smoke test.

This script exercises the complete startup-analysis path using the
actual Qwen provider and GGUF model:

    StartupAnalysisInput
        -> StartupAnalysisService
        -> FinancialMetricsService
        -> Prompt Builder
        -> QwenProvider
        -> StartupAnalysisParser
        -> StartupAnalysisResult

This is intentionally separate from the unit-test suite.
"""

from __future__ import annotations

import time
from decimal import Decimal

from app.core.config import settings
from app.llm.providers.qwen import QwenProvider
from app.schemas.analysis import (
    CompanyAnalysis,
    FinancialAnalysis,
    FundraisingAnalysis,
    StartupAnalysisInput,
)
from app.services.startup_analysis import (
    StartupAnalysisGenerationError,
    StartupAnalysisService,
)

# ---------------------------------------------------------------------------
# Smoke-test configuration
# ---------------------------------------------------------------------------

SMOKE_MAX_TOKENS = 512
SMOKE_TEMPERATURE = 0.0
SMOKE_THINKING = False

# Keep the first real-Qwen test small.
SMOKE_CONTEXT_SIZE = 4096


# ---------------------------------------------------------------------------
# Representative startup input
# ---------------------------------------------------------------------------


def build_smoke_input() -> StartupAnalysisInput:
    """Build a compact but representative startup analysis input."""

    return StartupAnalysisInput(
        company=CompanyAnalysis(
            name="Example AI Technologies",
            description=(
                "B2B startup developing AI-powered edge analytics "
                "for surveillance applications."
            ),
        ),
        product={
            "target_customer": "Enterprise surveillance companies",
            "value_proposition": (
                "Low-power real-time AI analytics at the edge."
            ),
            "product_stage": "commercial",
            "technology": "Edge AI",
            "differentiation": (
                "Low-power real-time inference."
            ),
        },
        market={
            "market_description": "Edge AI surveillance market",
            "market_growth_rate": Decimal("25"),
            "geographic_market": "India",
            "competitors": [
                "Competitor A",
                "Competitor B",
            ],
        },
        traction={
            "revenue": Decimal("100000000"),
            "revenue_growth_yoy": Decimal("40"),
            "customers": 100,
            "paying_customers": 80,
            "key_traction_notes": (
                "Growing enterprise customer base."
            ),
        },
        financials=FinancialAnalysis(
            revenue=Decimal("100000000"),
            revenue_growth_yoy=Decimal("40"),
            gross_profit=Decimal("60000000"),
            gross_margin=Decimal("60"),
            ebitda=Decimal("20000000"),
            ebitda_margin=Decimal("20"),
            net_profit=Decimal("10000000"),
            cash=Decimal("50000000"),
            debt=Decimal("10000000"),
            burn_rate=Decimal("2000000"),
            runway_months=Decimal("25"),
        ),
        fundraising=FundraisingAnalysis(
            current_round="Seed",
            amount_raising=Decimal("40000000"),
            amount_raised=Decimal("20000000"),
            pre_money_valuation=Decimal("300000000"),
            post_money_valuation=Decimal("340000000"),
            instrument="CCPS",
            investor_commitments=Decimal("25000000"),
        ),
        business_model={
            "business_model": "B2B SaaS",
            "revenue_streams": [
                "Software subscription",
                "Analytics",
            ],
            "pricing_model": "Annual subscription",
            "gross_margin": Decimal("60"),
            "customer_acquisition_cost": Decimal("100000"),
            "lifetime_value": Decimal("500000"),
            "ltv_to_cac": Decimal("5"),
        },
    )


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def print_header() -> None:
    """Print smoke-test configuration."""

    print("=" * 80)
    print("REAL QWEN STARTUP ANALYSIS SMOKE TEST")
    print("=" * 80)

    print(f"Model path       : {settings.qwen_model_path}")
    print(f"Thinking         : {SMOKE_THINKING}")
    print(f"Threads          : {settings.qwen_threads}")
    print(f"Context          : {SMOKE_CONTEXT_SIZE}")
    print(f"Temperature      : {SMOKE_TEMPERATURE}")
    print(f"Max tokens       : {SMOKE_MAX_TOKENS}")
    print()


def main() -> int:
    """Run the real-Qwen startup-analysis smoke test."""

    print_header()

    print("-" * 80)
    print("Building Qwen provider")
    print("-" * 80)

    provider_start = time.perf_counter()

    smoke_settings = settings.model_copy(
        update={
            "qwen_enable_thinking": SMOKE_THINKING,
            "qwen_context_size": SMOKE_CONTEXT_SIZE,
            "startup_analysis_max_tokens": SMOKE_MAX_TOKENS,
            "startup_analysis_temperature": SMOKE_TEMPERATURE,
        }
    )

    provider = QwenProvider(
        config=smoke_settings,
    )

    provider_elapsed = time.perf_counter() - provider_start

    print(
        f"Provider construction : {provider_elapsed:.2f} sec"
    )

    print()
    print("-" * 80)
    print("Running startup analysis")
    print("-" * 80)

    analysis_input = build_smoke_input()

    service = StartupAnalysisService(
        config=smoke_settings,
        llm_provider=provider,
    )


    start = time.perf_counter()

    try:
        result = service.analyze(analysis_input)
    except StartupAnalysisGenerationError as exc:
        elapsed = time.perf_counter() - start
    
        print()
        print("Qwen startup analysis: FAILED")
        print(f"Elapsed time         : {elapsed:.2f} sec")
        print(f"Exception            : {type(exc).__name__}")
        print(f"Message              : {exc}")
    
        if exc.finish_reason is not None:
            print(f"Finish reason        : {exc.finish_reason}")
    
        if exc.usage:
            print(f"Usage                : {exc.usage}")
    
        if exc.response_text:
            print()
            print("Response tail:")
            print("-" * 80)
            print(exc.response_text[-2000:])
            print("-" * 80)
    
        return 1


    elapsed = time.perf_counter() - start

    print()
    print("-" * 80)
    print("RESULT")
    print("-" * 80)

    print(f"Analysis time        : {elapsed:.2f} sec")

    print()
    print("Deterministic metrics:")
    print(
        f"  Revenue multiple   : "
        f"{result.metrics.revenue_multiple}"
    )
    print(
        f"  EBITDA multiple    : "
        f"{result.metrics.ebitda_multiple}"
    )
    print(
        f"  Valuation / growth : "
        f"{result.metrics.valuation_to_growth}"
    )

    print()
    print("Qualitative analysis:")
    print(
        f"  Recommendation     : "
        f"{result.result.preliminary_recommendation}"
    )

    print(
        f"  Strengths          : "
        f"{len(result.result.strengths)}"
    )

    print(
        f"  Risks              : "
        f"{len(result.result.risks)}"
    )

    print(
        f"  Missing information: "
        f"{len(result.result.missing_information)}"
    )

    print()
    print("Investment thesis:")
    print(result.result.investment_thesis)

    print()
    print("=" * 80)
    print("REAL QWEN STARTUP ANALYSIS SMOKE TEST: PASS")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
