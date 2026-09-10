#!/usr/bin/env python3
"""
Qwen2.5-1.5B-Instruct Q4_K_M — V1.1 semantic evidence benchmark.

V1.1 is a controlled experiment over V1:
- Same model and GGUF
- Same llama.cpp runtime
- Same 8 CPU threads
- Same six benchmark cases
- Same generation settings
- Fragment-aware + field-aware semantic prompt
- Explicit result/failure classification
- V1 baseline comparison

This script is intentionally standalone. It does not access the
Investment OS database, source extraction services, evidence builder,
scorecard, or production analysis pipeline.

Exit codes:
    0 = benchmark PASS
    1 = benchmark completed but semantic/JSON criteria failed
    2 = environment/model configuration failure
"""

from __future__ import annotations

import json
import platform
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any


MODEL_PATH = Path(
    "/models/Qwen2.5-1.5B-Instruct/"
    "qwen2.5-1.5b-instruct-q4_k_m.gguf"
)

N_THREADS = 8
N_THREADS_BATCH = 8
N_CTX = 4096
N_GPU_LAYERS = 0

TEMPERATURE = 0.0
TOP_P = 1.0
MAX_TOKENS = 128
SEED = 42

BENCHMARK_VERSION = "V1.2"
PROMPT_VERSION = "fragment-aware-field-examples-v1"

RESULT_PATH = Path("benchmark_qwen25_1p5b_v12.json")


FIELD_DEFINITIONS = {
    "business_model": (
        "How the company creates and delivers value, including "
        "marketplace, SaaS, B2B/B2C, transaction, subscription, "
        "or other revenue/business models."
    ),
    "industry": (
        "The company's actual operating industry or sector. "
        "Incidental references to another industry's activities "
        "do not establish the company's industry."
    ),
    "governance": (
        "Corporate governance information including board rights, "
        "investor rights, observer rights, reserved matters, "
        "management/control rights, and shareholder rights."
    ),
    "unit_economics": (
        "Information directly relevant to per-customer, per-order, "
        "per-transaction, or other unit-level economics, including "
        "customer acquisition cost, contribution margin, gross "
        "margin, retention, payback, or similar metrics."
    ),
}


FIELD_EXAMPLES = {
    "business_model": (
        "Examples of direct business-model evidence include marketplace, "
        "SaaS, subscription, transaction-based, B2B, or B2C operating models."
    ),
    "industry": (
        "Examples of direct industry evidence include a statement that "
        "the company operates as a healthcare, fintech, semiconductor, "
        "retail, or other sector company. Incidental references to another "
        "industry do not establish the company's industry."
    ),
    "governance": (
        "Examples of direct governance evidence include board appointment "
        "rights, investor observer rights, reserved matters, shareholder "
        "rights, or management/control rights."
    ),
    "unit_economics": (
        "Examples of direct unit-economics evidence include customer "
        "acquisition cost (CAC), contribution margin, gross margin, "
        "customer retention, payback period, or revenue/cost per "
        "customer, order, or transaction."
    ),
}


SYSTEM_PROMPT = """You are a semantic evidence validator for an investment analysis system.

The supplied source text is an extracted fragment from a larger
investment document. It may come from a PDF, DOCX, HTML, or XLSX file.

The fragment may:
- begin or end in the middle of a sentence,
- omit the company name,
- refer to the company indirectly,
- refer to investors, shareholders, board members, management,
  MIS, financial statements, or transaction documents.

Your task is to determine whether the supplied fragment provides
valid evidence for the proposed investment field.

IMPORTANT RULES:

1. Evaluate the meaning of the fragment, not just individual keywords.

2. The company/startup name does NOT need to appear in the fragment.

3. Do NOT reject evidence merely because the company name is absent.

4. A fragment may provide valid evidence through direct references
   to investors, shareholders, board members, management, MIS,
   financial statements, transaction documents, or corporate records.

5. A keyword occurrence alone is NOT sufficient evidence.

6. Legal boilerplate, incidental mentions, unrelated expertise,
   and references to unrelated third parties are NOT sufficient
   evidence.

7. Do not invent facts that are not present in the supplied fragment.

8. Use the proposed field definition to determine relevance.

9. Accept evidence when the fragment itself directly supports the
   proposed field.

10. Reject evidence when the fragment only contains terminology
    associated with the field but does not actually support it.

11. The field examples supplied in the user prompt are illustrative
    examples of what can constitute direct evidence. They are not
    automatic keyword rules.

12. The fragment may be incomplete. Do not penalize it merely for
    being incomplete.

13. Return JSON only.

Required JSON:
{
  "accepted": true or false,
  "confidence": number between 0 and 1,
  "reason": "short explanation"
}"""


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    name: str
    category: str
    field: str
    source_text: str
    question: str
    expected_accepted: bool
    source_type: str
    is_fragment: bool


@dataclass
class CaseResult:
    case_id: str
    name: str
    category: str
    field: str
    source_type: str
    is_fragment: bool
    expected_accepted: bool
    actual_accepted: bool | None
    semantic_result: str
    failure_type: str
    json_valid: bool
    confidence: float | None
    reason: str | None
    input_tokens: int
    output_tokens: int
    total_latency_sec: float
    prompt_eval_time_sec: float | None
    generation_time_sec: float | None
    generation_tok_per_sec: float | None
    raw_response: str


CASES = [
    BenchmarkCase(
        case_id="01",
        name="Valid marketplace evidence",
        category="positive",
        field="business_model",
        source_text=(
            "RestoMart operates a technology-driven, single-window "
            "marketplace for restaurant procurement."
        ),
        question=(
            "Does this fragment provide valid evidence for RestoMart's "
            "business model?"
        ),
        expected_accepted=True,
        source_type="extracted_document_fragment",
        is_fragment=True,
    ),
    BenchmarkCase(
        case_id="02",
        name="Healthcare consulting false positive",
        category="negative",
        field="industry",
        source_text=(
            "expertise spanning investment, supply chain, and healthcare "
            "consulting, and supported by Vimalraj, a"
        ),
        question=(
            "Does this fragment provide valid evidence that RestoMart "
            "operates in the healthcare industry?"
        ),
        expected_accepted=False,
        source_type="extracted_document_fragment",
        is_fragment=True,
    ),
    BenchmarkCase(
        case_id="03",
        name="Payment legal false positive",
        category="negative",
        field="industry",
        source_text=(
            "one certificate for all his shares without payment of any"
        ),
        question=(
            "Does this fragment provide valid evidence that RestoMart "
            "operates in the fintech or payment industry?"
        ),
        expected_accepted=False,
        source_type="extracted_document_fragment",
        is_fragment=True,
    ),
    BenchmarkCase(
        case_id="04",
        name="Governance evidence",
        category="positive",
        field="governance",
        source_text=(
            "Investors acting through the Investor Representative have "
            "the right to appoint, remove and substitute one non-voting "
            "Investor Observer to the Board."
        ),
        question=(
            "Does this fragment provide valid governance evidence "
            "for RestoMart?"
        ),
        expected_accepted=True,
        source_type="extracted_document_fragment",
        is_fragment=True,
    ),
    BenchmarkCase(
        case_id="05",
        name="Unit economics evidence",
        category="positive",
        field="unit_economics",
        source_text=(
            "MIS provides customer-acquisition-cost information relevant "
            "to assessing the cost of acquiring customers."
        ),
        question=(
            "Does this fragment provide valid evidence relevant to "
            "RestoMart's unit economics?"
        ),
        expected_accepted=True,
        source_type="extracted_document_fragment",
        is_fragment=True,
    ),
    BenchmarkCase(
        case_id="06",
        name="Legal financial noise",
        category="negative",
        field="industry",
        source_text=(
            "PAN is now mandatory for quoting of securities transactions "
            "and other applicable financial transactions."
        ),
        question=(
            "Does this fragment provide valid evidence that RestoMart "
            "operates in the fintech or financial-services industry?"
        ),
        expected_accepted=False,
        source_type="extracted_document_fragment",
        is_fragment=True,
    ),
]


def print_header(title: str) -> None:
    print()
    print("=" * 90)
    print(title)
    print("=" * 90)


def build_user_prompt(case: BenchmarkCase) -> str:
    definition = FIELD_DEFINITIONS.get(
        case.field,
        "Determine relevance using the proposed investment field.",
    )
    examples = FIELD_EXAMPLES.get(
        case.field,
        "Use direct semantic evidence relevant to the proposed field.",
    )

    return f"""Source type:
{case.source_type}

Fragment information:
The text may be incomplete and may not contain the company name.

Candidate field:
{case.field}

Field definition:
{definition}

Examples of direct evidence for this field:
{examples}

These examples are illustrative, not automatic keyword rules.

Source fragment:
"{case.source_text}"

Question:
{case.question}

Return JSON only."""


def parse_model_json(text: str) -> dict[str, Any]:
    """Parse model JSON, allowing only a simple markdown JSON fence."""
    cleaned = text.strip()

    if cleaned.startswith("```") and cleaned.endswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3:
            cleaned = "\n".join(lines[1:-1]).strip()

    value = json.loads(cleaned)

    if not isinstance(value, dict):
        raise ValueError("Model response is not a JSON object.")

    return value


def extract_timings(response: dict[str, Any]) -> tuple[float | None, float | None]:
    """
    Extract llama.cpp timing fields when available.

    Different llama.cpp versions can expose different timing information.
    Missing values remain None rather than being estimated.
    """
    timings = response.get("timings") or {}

    prompt_ms = timings.get("prompt_ms")
    generation_ms = timings.get("predicted_ms")

    prompt_time = (
        float(prompt_ms) / 1000.0
        if prompt_ms is not None
        else None
    )
    generation_time = (
        float(generation_ms) / 1000.0
        if generation_ms is not None
        else None
    )

    return prompt_time, generation_time


def classify_result(
    *,
    expected: bool,
    actual: bool | None,
    json_valid: bool,
    inference_error: bool = False,
) -> tuple[str, str]:
    if inference_error:
        return "FAIL", "INFERENCE_ERROR"

    if not json_valid:
        return "FAIL", "JSON_FORMAT_ERROR"

    if actual == expected:
        return "PASS", "NONE"

    if expected is True and actual is False:
        return "FAIL", "OVER_REJECTION"

    if expected is False and actual is True:
        return "FAIL", "OVER_ACCEPTANCE"

    return "FAIL", "UNKNOWN"


def run_case(llm: Any, case: BenchmarkCase) -> CaseResult:
    start = time.perf_counter()

    response = llm.create_chat_completion(
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": build_user_prompt(case),
            },
        ],
        temperature=TEMPERATURE,
        top_p=TOP_P,
        max_tokens=MAX_TOKENS,
        seed=SEED,
    )

    total_latency = time.perf_counter() - start

    choices = response.get("choices") or []
    raw_response = ""

    if choices:
        raw_response = (
            choices[0]
            .get("message", {})
            .get("content", "")
        )

    usage = response.get("usage") or {}
    input_tokens = int(usage.get("prompt_tokens") or 0)
    output_tokens = int(usage.get("completion_tokens") or 0)

    prompt_time, generation_time = extract_timings(response)

    generation_tok_per_sec = None
    if generation_time is not None and generation_time > 0:
        generation_tok_per_sec = output_tokens / generation_time

    json_valid = False
    actual_accepted: bool | None = None
    confidence: float | None = None
    reason: str | None = None

    try:
        parsed = parse_model_json(raw_response)

        if not isinstance(parsed.get("accepted"), bool):
            raise ValueError("'accepted' must be boolean.")

        confidence_value = parsed.get("confidence")
        try:
            confidence = float(confidence_value)
        except (TypeError, ValueError) as exc:
            raise ValueError("'confidence' must be numeric.") from exc

        if not 0.0 <= confidence <= 1.0:
            raise ValueError("'confidence' must be between 0 and 1.")

        reason_value = parsed.get("reason")
        if not isinstance(reason_value, str) or not reason_value.strip():
            raise ValueError("'reason' must be a non-empty string.")

        actual_accepted = parsed["accepted"]
        reason = reason_value.strip()
        json_valid = True

    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        reason = f"JSON validation error: {exc}"

    semantic_result, failure_type = classify_result(
        expected=case.expected_accepted,
        actual=actual_accepted,
        json_valid=json_valid,
    )

    return CaseResult(
        case_id=case.case_id,
        name=case.name,
        category=case.category,
        field=case.field,
        source_type=case.source_type,
        is_fragment=case.is_fragment,
        expected_accepted=case.expected_accepted,
        actual_accepted=actual_accepted,
        semantic_result=semantic_result,
        failure_type=failure_type,
        json_valid=json_valid,
        confidence=confidence,
        reason=reason,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_latency_sec=total_latency,
        prompt_eval_time_sec=prompt_time,
        generation_time_sec=generation_time,
        generation_tok_per_sec=generation_tok_per_sec,
        raw_response=raw_response,
    )


def build_inference_error_result(
    case: BenchmarkCase,
    error: Exception,
) -> CaseResult:
    return CaseResult(
        case_id=case.case_id,
        name=case.name,
        category=case.category,
        field=case.field,
        source_type=case.source_type,
        is_fragment=case.is_fragment,
        expected_accepted=case.expected_accepted,
        actual_accepted=None,
        semantic_result="FAIL",
        failure_type="INFERENCE_ERROR",
        json_valid=False,
        confidence=None,
        reason=f"Inference error: {error}",
        input_tokens=0,
        output_tokens=0,
        total_latency_sec=0.0,
        prompt_eval_time_sec=None,
        generation_time_sec=None,
        generation_tok_per_sec=None,
        raw_response="",
    )


def write_results(
    *,
    results: list[CaseResult],
    load_time_sec: float,
    warmup_time_sec: float,
    status: str,
    llama_cpp_version: str,
) -> None:
    latencies = [r.total_latency_sec for r in results]
    rates = [
        r.generation_tok_per_sec
        for r in results
        if r.generation_tok_per_sec is not None
    ]

    positive_cases = [
        r for r in results if r.category == "positive"
    ]
    negative_cases = [
        r for r in results if r.category == "negative"
    ]

    semantic_correct = sum(
        r.semantic_result == "PASS" for r in results
    )
    json_valid = sum(r.json_valid for r in results)

    positive_acceptance = sum(
        r.category == "positive"
        and r.semantic_result == "PASS"
        for r in results
    )

    negative_rejection = sum(
        r.category == "negative"
        and r.semantic_result == "PASS"
        for r in results
    )

    over_rejection = sum(
        r.failure_type == "OVER_REJECTION"
        for r in results
    )

    over_acceptance = sum(
        r.failure_type == "OVER_ACCEPTANCE"
        for r in results
    )

    json_failures = sum(
        r.failure_type == "JSON_FORMAT_ERROR"
        for r in results
    )

    inference_failures = sum(
        r.failure_type == "INFERENCE_ERROR"
        for r in results
    )

    payload = {
        "benchmark": "Qwen2.5-1.5B-Instruct",
        "benchmark_version": BENCHMARK_VERSION,
        "prompt_version": PROMPT_VERSION,
        "model": {
            "path": str(MODEL_PATH),
            "format": "GGUF",
            "quantization": "Q4_K_M",
            "size_bytes": MODEL_PATH.stat().st_size,
        },
        "runtime": {
            "python": sys.version,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "llama_cpp_python": llama_cpp_version,
        },
        "configuration": {
            "threads": N_THREADS,
            "threads_batch": N_THREADS_BATCH,
            "context": N_CTX,
            "gpu_layers": N_GPU_LAYERS,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "max_tokens": MAX_TOKENS,
            "seed": SEED,
        },
        "timing": {
            "model_load_sec": load_time_sec,
            "warmup_sec": warmup_time_sec,
            "average_latency_sec": mean(latencies) if latencies else None,
            "minimum_latency_sec": min(latencies) if latencies else None,
            "maximum_latency_sec": max(latencies) if latencies else None,
            "average_generation_tok_per_sec": (
                mean(rates) if rates else None
            ),
            "minimum_generation_tok_per_sec": (
                min(rates) if rates else None
            ),
            "maximum_generation_tok_per_sec": (
                max(rates) if rates else None
            ),
        },
        "v1_baseline": {
            "json_valid": "6/6",
            "semantic_correct": "4/6",
            "positive_acceptance": "1/3",
            "negative_rejection": "3/3",
            "over_rejection": 2,
            "over_acceptance": 0,
            "average_latency_sec": 2.181,
            "maximum_latency_sec": 3.655,
            "projected_35_candidates_sec": 76.3,
        },
        "v1_1_baseline": {
            "json_valid": "6/6",
            "semantic_correct": "5/6",
            "positive_acceptance": "2/3",
            "negative_rejection": "3/3",
            "over_rejection": 1,
            "over_acceptance": 0,
            "average_latency_sec": 2.976,
            "maximum_latency_sec": 5.474,
            "projected_35_candidates_sec": 104.1,
        },
        "results": [asdict(result) for result in results],
        "summary": {
            "tests": len(results),
            "json_valid": json_valid,
            "semantic_correct": semantic_correct,
            "positive_cases": len(positive_cases),
            "positive_acceptance": positive_acceptance,
            "negative_cases": len(negative_cases),
            "negative_rejection": negative_rejection,
            "over_rejection": over_rejection,
            "over_acceptance": over_acceptance,
            "json_failures": json_failures,
            "inference_failures": inference_failures,
            "status": status,
        },
    }

    RESULT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> int:
    print_header(
        "QWEN2.5-1.5B-INSTRUCT — LLAMA.CPP SEMANTIC BENCHMARK V1.2"
    )

    print(f"Benchmark version : {BENCHMARK_VERSION}")
    print(f"Prompt version    : {PROMPT_VERSION}")
    print(f"Model path        : {MODEL_PATH}")
    print("Model format      : GGUF")
    print("Quantization      : Q4_K_M")
    print(f"CPU threads       : {N_THREADS}")
    print(f"Batch threads     : {N_THREADS_BATCH}")
    print(f"GPU layers        : {N_GPU_LAYERS}")
    print(f"Context           : {N_CTX}")
    print(f"Max output        : {MAX_TOKENS}")
    print(f"Temperature       : {TEMPERATURE}")
    print(f"Top-p             : {TOP_P}")
    print(f"Seed              : {SEED}")

    if not MODEL_PATH.exists():
        print()
        print(f"ERROR: Model not found: {MODEL_PATH}")
        return 2

    if not MODEL_PATH.is_file():
        print()
        print(f"ERROR: Model path is not a file: {MODEL_PATH}")
        return 2

    try:
        import llama_cpp
        from llama_cpp import Llama
    except ImportError as exc:
        print()
        print(f"ERROR: llama-cpp-python unavailable: {exc}")
        return 2

    llama_cpp_version = getattr(
        llama_cpp,
        "__version__",
        "unknown",
    )

    print(f"Python version    : {platform.python_version()}")
    print(f"llama-cpp-python  : {llama_cpp_version}")

    print_header("MODEL LOADING")

    load_start = time.perf_counter()

    try:
        llm = Llama(
            model_path=str(MODEL_PATH),
            n_ctx=N_CTX,
            n_threads=N_THREADS,
            n_threads_batch=N_THREADS_BATCH,
            n_gpu_layers=N_GPU_LAYERS,
            seed=SEED,
            verbose=False,
        )
    except Exception as exc:
        print(f"ERROR: Model load failed: {exc}")
        return 2

    load_time = time.perf_counter() - load_start
    print(f"Model load time   : {load_time:.3f} sec")

    print_header("WARM-UP")

    warmup_start = time.perf_counter()

    try:
        llm.create_chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": "Return JSON only.",
                },
                {
                    "role": "user",
                    "content": (
                        '{"accepted": true, "confidence": 1.0, '
                        '"reason": "warmup"}'
                    ),
                },
            ],
            temperature=0.0,
            top_p=1.0,
            max_tokens=16,
            seed=SEED,
        )
    except Exception as exc:
        print(f"ERROR: Warm-up failed: {exc}")
        return 2

    warmup_time = time.perf_counter() - warmup_start
    print(f"Warm-up time      : {warmup_time:.3f} sec")

    print_header("V1.2 SEMANTIC VALIDATION CASES")

    results: list[CaseResult] = []

    for case in CASES:
        print()
        print(f"CASE {case.case_id} — {case.name}")
        print("-" * 90)

        try:
            result = run_case(llm, case)
        except Exception as exc:
            result = build_inference_error_result(case, exc)

        results.append(result)

        print(f"Category           : {result.category}")
        print(f"Field              : {result.field}")
        print(f"Source type        : {result.source_type}")
        print(f"Fragment           : {result.is_fragment}")
        print(f"Expected accepted  : {result.expected_accepted}")
        print(f"Actual accepted    : {result.actual_accepted}")
        print(f"JSON valid         : {result.json_valid}")
        print(f"Semantic result    : {result.semantic_result}")
        print(f"Failure type       : {result.failure_type}")

        if result.confidence is not None:
            print(f"Confidence         : {result.confidence:.3f}")

        print(f"Reason             : {result.reason}")
        print(f"Input tokens       : {result.input_tokens}")
        print(f"Output tokens      : {result.output_tokens}")
        print(f"Total latency      : {result.total_latency_sec:.3f} sec")

        if result.prompt_eval_time_sec is not None:
            print(
                f"Prompt eval time   : "
                f"{result.prompt_eval_time_sec:.3f} sec"
            )

        if result.generation_time_sec is not None:
            print(
                f"Generation time    : "
                f"{result.generation_time_sec:.3f} sec"
            )

        if result.generation_tok_per_sec is not None:
            print(
                f"Generation tok/s   : "
                f"{result.generation_tok_per_sec:.2f}"
            )

        if result.raw_response:
            print(f"Raw response       : {result.raw_response}")

    total = len(results)
    json_valid_count = sum(r.json_valid for r in results)
    semantic_correct_count = sum(
        r.semantic_result == "PASS" for r in results
    )

    positive_cases = [
        r for r in results if r.category == "positive"
    ]
    negative_cases = [
        r for r in results if r.category == "negative"
    ]

    positive_acceptance = sum(
        r.semantic_result == "PASS"
        for r in positive_cases
    )

    negative_rejection = sum(
        r.semantic_result == "PASS"
        for r in negative_cases
    )

    over_rejection = sum(
        r.failure_type == "OVER_REJECTION"
        for r in results
    )

    over_acceptance = sum(
        r.failure_type == "OVER_ACCEPTANCE"
        for r in results
    )

    json_failures = sum(
        r.failure_type == "JSON_FORMAT_ERROR"
        for r in results
    )

    inference_failures = sum(
        r.failure_type == "INFERENCE_ERROR"
        for r in results
    )

    status = (
        "PASS"
        if (
            json_valid_count == total
            and semantic_correct_count == total
        )
        else "FAIL"
    )

    print_header("V1.2 SUMMARY")

    print(f"Tests                     : {total}")
    print(f"JSON valid                : {json_valid_count}/{total}")
    print(
        f"Semantic correct          : "
        f"{semantic_correct_count}/{total}"
    )
    print()
    print(
        f"Positive evidence         : "
        f"{positive_acceptance}/{len(positive_cases)}"
    )
    print(
        f"Negative evidence         : "
        f"{negative_rejection}/{len(negative_cases)}"
    )
    print()
    print(
        f"Valid-evidence acceptance : "
        f"{positive_acceptance}/{len(positive_cases)}"
    )
    print(
        f"False-positive rejection  : "
        f"{negative_rejection}/{len(negative_cases)}"
    )
    print()
    print(f"Over-rejection            : {over_rejection}")
    print(f"Over-acceptance           : {over_acceptance}")
    print(f"JSON failures             : {json_failures}")
    print(f"Inference failures        : {inference_failures}")

    latencies = [r.total_latency_sec for r in results]
    rates = [
        r.generation_tok_per_sec
        for r in results
        if r.generation_tok_per_sec is not None
    ]

    print_header("PERFORMANCE")

    print(f"Model load time           : {load_time:.3f} sec")
    print(f"Warm-up time              : {warmup_time:.3f} sec")

    if latencies:
        average_latency = mean(latencies)
        print(f"Average latency           : {average_latency:.3f} sec")
        print(f"Minimum latency           : {min(latencies):.3f} sec")
        print(f"Maximum latency           : {max(latencies):.3f} sec")

        projected = average_latency * 35
        print()
        print("PROJECTED 35-CANDIDATE WORKLOAD")
        print("-" * 90)
        print(
            f"Estimated sequential time : "
            f"{projected:.1f} sec "
            f"({projected / 60.0:.2f} min)"
        )

    if rates:
        print(
            f"Average generation tok/s : "
            f"{mean(rates):.2f}"
        )
        print(
            f"Minimum generation tok/s : "
            f"{min(rates):.2f}"
        )
        print(
            f"Maximum generation tok/s : "
            f"{max(rates):.2f}"
        )

    print_header("V1 vs V1.2")

    print("Metric                         V1          V1.1        V1.2")
    print("-" * 76)
    print(
        f"JSON valid                     6/6         6/6         "
        f"{json_valid_count}/{total}"
    )
    print(
        f"Semantic correct               4/6         5/6         "
        f"{semantic_correct_count}/{total}"
    )
    print(
        f"Positive acceptance            1/3         2/3         "
        f"{positive_acceptance}/{len(positive_cases)}"
    )
    print(
        f"Negative rejection             3/3         3/3         "
        f"{negative_rejection}/{len(negative_cases)}"
    )
    print(
        f"Over-rejection                 2           1           "
        f"{over_rejection}"
    )
    print(
        f"Over-acceptance                0           0           "
        f"{over_acceptance}"
    )

    if latencies:
        print()
        print(
            f"Average latency                2.181 s     2.976 s     "
            f"{mean(latencies):.3f} s"
        )
        print(
            f"Maximum latency                3.655 s     5.474 s     "
            f"{max(latencies):.3f} s"
        )

        projected = mean(latencies) * 35
        print(
            f"Projected 35 candidates        76.3 s      104.1 s     "
            f"{projected:.1f} s"
        )

    try:
        write_results(
            results=results,
            load_time_sec=load_time,
            warmup_time_sec=warmup_time,
            status=status,
            llama_cpp_version=llama_cpp_version,
        )
        print()
        print(f"Results JSON                  : {RESULT_PATH}")
    except OSError as exc:
        print()
        print(
            "WARNING: Could not write results JSON: "
            f"{exc}"
        )

    print_header("V1.2 RESULT")
    print(f"STATUS : {status}")

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
