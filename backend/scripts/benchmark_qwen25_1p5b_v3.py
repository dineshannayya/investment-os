#!/usr/bin/env python3
"""
Qwen2.5-1.5B-Instruct Q4_K_M — V3.0 Direct Semantic Extraction Benchmark.

V3.0 tests a different evidence-generation strategy from V2:

    current persisted source extraction
        |
        v
    structural text segmentation only
        |
        v
    Qwen2.5-1.5B
        |
        v
    direct semantic extraction across all 10 investment dimensions
        |
        v
    deterministic Python validation / provenance / dedup

The model is NOT given Python-generated evidence candidates.

The model is asked to inspect document context and directly extract
investment-relevant facts. Python remains responsible for:
- exact source-version identity
- structural chunking
- provenance
- JSON/schema validation
- duplicate detection
- basic output normalization

V3.0 is observational. It does not modify production dimension evidence,
signals.py, DimensionEvidenceBuilder, scorecard evaluation, or analysis.

Default startup:
    RestoMart

Default output:
    /opt/investment-os/generated/restomart/benchmark_qwen25_1p5b_v3.json

Exit codes:
    0 = benchmark completed; all model responses valid JSON
    1 = data/output validation failure
    2 = model/runtime configuration failure
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any
from uuid import UUID

from app.core.config.settings import settings
from app.core.database.session import create_session
from app.services.source_discovery import SourceDiscoveryService
from app.services.source_extraction_persistence import (
    SourceExtractionPersistenceService,
)
from app.services.startup import StartupService


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
MAX_TOKENS = 384
SEED = 42

BENCHMARK_VERSION = "V3.0"
PROMPT_VERSION = "direct-document-semantic-extraction-v1"

DEFAULT_DATA_ROOT = Path("/opt/investment-os/data/real_startups")
DEFAULT_GENERATED_ROOT = Path("/opt/investment-os/generated")
DEFAULT_CHUNK_CHARS = 6000
DEFAULT_OVERLAP_CHARS = 500
DEFAULT_MAX_CHUNKS = 0  # 0 = all chunks


DIMENSIONS = (
    "founder_team",
    "market_tam",
    "product_pmf",
    "technology_ip_moat",
    "commercial_traction",
    "unit_economics_margins",
    "financial_health",
    "governance_cap_table",
    "valuation_deal_terms",
    "risk_exit_potential",
)

FIELD_DEFINITIONS = {
    "founder_team": (
        "Founder and leadership evidence: founder identity, roles, relevant "
        "background, prior experience, ownership, commitment, and team structure."
    ),
    "market_tam": (
        "Target market evidence: market size, TAM/SAM/SOM, market structure, "
        "addressable opportunity, geography, target customer population, or market growth."
    ),
    "product_pmf": (
        "Product/service and product-market-fit evidence: product capabilities, "
        "customer problem solved, adoption, usage, orders, retention, engagement, "
        "customer growth, or product/customer fit."
    ),
    "technology_ip_moat": (
        "Technology and moat evidence: proprietary technology, software, technical "
        "architecture, technical capability, IP, technology investment, differentiation, "
        "or technology roadmap."
    ),
    "commercial_traction": (
        "Commercial traction evidence: revenue, sales, customers, orders, AOV, growth, "
        "churn, customer concentration, repeat business, or operating traction."
    ),
    "unit_economics_margins": (
        "Unit economics and margin evidence: CAC, gross margin, contribution margin, "
        "contribution profit, payback, retention economics, or revenue/cost per customer, "
        "order, or transaction."
    ),
    "financial_health": (
        "Overall financial health: revenue, gross profit, EBITDA, EBITDA margin, "
        "operating expenses, cash, burn, profitability, liquidity, or financial trends."
    ),
    "governance_cap_table": (
        "Governance and ownership: cap table, shareholding, board rights, observer rights, "
        "reserved matters, information rights, investor rights, or control rights."
    ),
    "valuation_deal_terms": (
        "Financing and transaction terms: round size, valuation, issue price, instrument, "
        "conversion, dilution, anti-dilution, subscription terms, or financing projections."
    ),
    "risk_exit_potential": (
        "Investment risk/downside/exit evidence: customer concentration, churn, negative "
        "unit economics, execution risk, working-capital risk, contractual exit/liquidity "
        "mechanisms, or other explicit downside factors."
    ),
}


SYSTEM_PROMPT = """You are a factual evidence extraction engine for an investment analysis system.

You will receive a bounded excerpt from a real startup document. Extract ONLY
investment-relevant facts that are explicitly supported by that excerpt.

This is DIRECT EXTRACTION, not keyword matching.

IMPORTANT:
1. Read the meaning and context of the excerpt.
2. Do not require the startup name to appear in the excerpt.
3. Extract facts for ANY of the ten dimensions when the excerpt supports them.
4. Do not invent, infer, calculate, or assume facts not explicitly present.
5. A keyword alone is not evidence.
6. Ignore legal boilerplate, addresses, PAN/tax identifiers, registration numbers,
   signatures, page headers, generic administrative text, and unrelated third-party
   references unless they directly contain investment evidence.
7. A document may contain several useful facts and may support multiple dimensions.
8. Preserve important numeric values, units, periods, names, percentages, and terms.
9. Supporting text must be copied or closely reproduced from the supplied excerpt.
10. If the excerpt contains no useful investment evidence, return an empty list.
11. Do not produce investment opinions, scores, recommendations, or risks unless
    the document explicitly states the underlying fact.
12. Return JSON only. No markdown and no commentary.

Return exactly:
{
  "evidence": [
    {
      "dimension": "one of the ten dimensions",
      "field": "specific field name",
      "observation": "concise factual statement",
      "supporting_text": "text from the supplied excerpt",
      "confidence": 0.0
    }
  ]
}

Confidence is your confidence that the extracted item is explicitly supported
and relevant. It is NOT investment confidence.

Ten dimensions:
- founder_team
- market_tam
- product_pmf
- technology_ip_moat
- commercial_traction
- unit_economics_margins
- financial_health
- governance_cap_table
- valuation_deal_terms
- risk_exit_potential
"""


@dataclass
class Chunk:
    chunk_id: str
    source_id: str
    source_sha256: str
    source_path: str
    source_type: str
    source_category: str
    source_authority: str
    extraction_id: str
    extraction_method: str
    processor_name: str
    title: str | None
    page_count: int | None
    segment_index: int | None
    segment_metadata: dict[str, Any]
    text: str


@dataclass
class ExtractedEvidence:
    evidence_id: str
    chunk_id: str
    source_id: str
    source_sha256: str
    source_path: str
    source_type: str
    source_category: str
    source_authority: str
    extraction_id: str
    extraction_method: str
    processor_name: str
    dimension: str
    field: str
    observation: str
    supporting_text: str
    confidence: float
    model_latency_sec: float
    raw_response: str


@dataclass
class ChunkResult:
    chunk_id: str
    source_id: str
    source_path: str
    chunk_chars: int
    json_valid: bool
    evidence_count: int
    latency_sec: float
    input_tokens: int
    output_tokens: int
    generation_tok_per_sec: float | None
    error: str | None
    raw_response: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Qwen2.5-1.5B V3.0 direct semantic extraction benchmark."
    )
    parser.add_argument("--startup", default="restomart")
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--output", default=None)
    parser.add_argument(
        "--chunk-chars",
        type=int,
        default=DEFAULT_CHUNK_CHARS,
        help=f"Structural chunk size in characters [{DEFAULT_CHUNK_CHARS}]",
    )
    parser.add_argument(
        "--overlap-chars",
        type=int,
        default=DEFAULT_OVERLAP_CHARS,
        help=f"Chunk overlap in characters [{DEFAULT_OVERLAP_CHARS}]",
    )
    parser.add_argument(
        "--max-chunks",
        type=int,
        default=DEFAULT_MAX_CHUNKS,
        help="Maximum chunks to process; 0 means all.",
    )
    return parser.parse_args()


def normalize_startup_key(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def resolve_startup_directory(
    data_root: Path,
    startup_identifier: str,
) -> Path:
    startup_dir = data_root / normalize_startup_key(startup_identifier)
    if not startup_dir.is_dir():
        raise FileNotFoundError(f"Startup directory not found: {startup_dir}")
    return startup_dir


def resolve_startup(
    startup_service: StartupService,
    startup_identifier: str,
):
    identifier = startup_identifier.strip()
    try:
        startup_id = UUID(identifier)
    except ValueError:
        startup_id = None

    if startup_id is not None:
        startup = startup_service.get_startup(startup_id)
        if startup is None:
            raise ValueError(f"Startup not found for UUID: {startup_id}")
        return startup

    normalized = normalize_startup_key(identifier)
    matches = [
        startup
        for startup in startup_service.list_startups()
        if normalize_startup_key(startup.name) == normalized
    ]
    if not matches:
        raise ValueError(f"Startup not found for identifier: {identifier}")
    if len(matches) > 1:
        ids = ", ".join(str(item.id) for item in matches)
        raise ValueError(
            f"Multiple startups matched '{identifier}': {ids}"
        )
    return matches[0]


def resolve_current_source_extractions(
    *,
    startup,
    source_root: Path,
    source_discovery: SourceDiscoveryService,
    extraction_persistence: SourceExtractionPersistenceService,
):
    sources = source_discovery.discover(
        startup_id=str(startup.id),
        source_root=source_root,
    )

    records = []
    missing = []

    for source in sources:
        if source.sha256 is None:
            continue

        record = extraction_persistence.get_by_source_version(
            source_id=source.source_id,
            source_sha256=source.sha256,
        )

        if record is None:
            missing.append(source.relative_path)
            continue

        records.append((source, record))

    if missing:
        raise RuntimeError(
            "Missing current persisted extractions for: "
            + ", ".join(missing)
        )

    return tuple(records)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\x00", "").strip()


def _segment_text(segment: Any) -> str:
    if isinstance(segment, str):
        return _clean_text(segment)

    if not isinstance(segment, dict):
        return ""

    for key in (
        "text",
        "content",
        "value",
        "body",
        "raw_text",
    ):
        text = _clean_text(segment.get(key))
        if text:
            return text

    return ""


def _segment_metadata(segment: Any) -> dict[str, Any]:
    if not isinstance(segment, dict):
        return {}
    metadata: dict[str, Any] = {}
    for key in (
        "id",
        "segment_id",
        "page",
        "page_number",
        "section",
        "heading",
        "type",
        "kind",
        "sheet",
        "row",
        "column",
        "cell",
    ):
        if key in segment:
            metadata[key] = segment[key]
    return metadata


def _build_structural_units(record: Any) -> list[tuple[int | None, dict[str, Any], str]]:
    units: list[tuple[int | None, dict[str, Any], str]] = []

    segments = getattr(record, "segments", None) or []
    for index, segment in enumerate(segments):
        text = _segment_text(segment)
        if text:
            units.append((index, _segment_metadata(segment), text))

    if units:
        return units

    text = _clean_text(getattr(record, "text", ""))
    if text:
        return [(None, {}, text)]

    return []


def _split_text(
    text: str,
    *,
    chunk_chars: int,
    overlap_chars: int,
) -> list[str]:
    if len(text) <= chunk_chars:
        return [text]

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = min(start + chunk_chars, len(text))

        if end < len(text):
            boundary = max(
                text.rfind("\n\n", start, end),
                text.rfind("\n", start, end),
                text.rfind(". ", start, end),
            )
            if boundary > start + int(chunk_chars * 0.60):
                end = boundary + (2 if text[boundary:boundary + 2] == "\n\n" else 1)

        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)

        if end >= len(text):
            break

        next_start = max(end - overlap_chars, start + 1)
        start = next_start

    return chunks


def build_chunks(
    source_records,
    *,
    chunk_chars: int,
    overlap_chars: int,
) -> list[Chunk]:
    chunks: list[Chunk] = []

    for source, record in source_records:
        units = _build_structural_units(record)
        source_path = source.relative_path

        for segment_index, metadata, text in units:
            pieces = _split_text(
                text,
                chunk_chars=chunk_chars,
                overlap_chars=overlap_chars,
            )

            for piece_index, piece in enumerate(pieces):
                location = (
                    f"segment={segment_index}"
                    if segment_index is not None
                    else "document_text"
                )
                if len(pieces) > 1:
                    location += f":part={piece_index}"

                raw_key = (
                    f"{source.source_id}|{source.sha256}|"
                    f"{location}|{piece}"
                )
                chunk_id = hashlib.sha256(
                    raw_key.encode("utf-8")
                ).hexdigest()[:24]

                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        source_id=str(source.source_id),
                        source_sha256=str(source.sha256),
                        source_path=source_path,
                        source_type=source.source_type.value,
                        source_category=source.source_category.value,
                        source_authority=source.source_authority.value,
                        extraction_id=str(record.extraction_id),
                        extraction_method=record.provenance.method.value,
                        processor_name=record.provenance.processor_name,
                        title=record.title,
                        page_count=record.page_count,
                        segment_index=segment_index,
                        segment_metadata=metadata,
                        text=piece,
                    )
                )

    return chunks


def strip_code_fence(text: str) -> str:
    value = text.strip()
    if value.startswith("```") and value.endswith("```"):
        lines = value.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return value


def validate_model_payload(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise ValueError("Root JSON must be an object.")

    evidence = payload.get("evidence")
    if not isinstance(evidence, list):
        raise ValueError("'evidence' must be a list.")

    validated = []

    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            raise ValueError(f"evidence[{index}] must be an object.")

        dimension = item.get("dimension")
        field = item.get("field")
        observation = item.get("observation")
        supporting_text = item.get("supporting_text")
        confidence = item.get("confidence")

        if dimension not in DIMENSIONS:
            raise ValueError(
                f"evidence[{index}] invalid dimension: {dimension!r}"
            )

        if not isinstance(field, str) or not field.strip():
            raise ValueError(f"evidence[{index}] invalid field.")

        if not isinstance(observation, str) or not observation.strip():
            raise ValueError(f"evidence[{index}] invalid observation.")

        if (
            not isinstance(supporting_text, str)
            or not supporting_text.strip()
        ):
            raise ValueError(
                f"evidence[{index}] invalid supporting_text."
            )

        if isinstance(confidence, bool):
            raise ValueError(f"evidence[{index}] invalid confidence.")

        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"evidence[{index}] confidence is not numeric."
            ) from exc

        if not 0.0 <= confidence_value <= 1.0:
            raise ValueError(
                f"evidence[{index}] confidence outside [0,1]."
            )

        validated.append(
            {
                "dimension": dimension,
                "field": field.strip(),
                "observation": observation.strip(),
                "supporting_text": supporting_text.strip(),
                "confidence": confidence_value,
            }
        )

    return validated


def evidence_fingerprint(
    *,
    source_id: str,
    dimension: str,
    field: str,
    supporting_text: str,
) -> str:
    normalized = re.sub(
        r"\s+",
        " ",
        supporting_text.strip().lower(),
    )
    raw = (
        f"{source_id}|{dimension}|{field.strip().lower()}|{normalized}"
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def run_chunk(llm, chunk: Chunk) -> tuple[ChunkResult, list[dict[str, Any]]]:
    user_prompt = f"""Extract all explicitly supported investment evidence from this document excerpt.

Document:
- path: {chunk.source_path}
- source type: {chunk.source_type}
- source category: {chunk.source_category}
- title: {chunk.title or ""}
- page count: {chunk.page_count}
- segment index: {chunk.segment_index}

Relevant field definitions:
{json.dumps(FIELD_DEFINITIONS, ensure_ascii=False, indent=2)}

EXCERPT:
<<<
{chunk.text}
>>>

Return JSON only."""

    start = time.perf_counter()
    raw_response = ""
    try:
        response = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
            max_tokens=MAX_TOKENS,
            seed=SEED,
        )

        raw_response = str(
            response["choices"][0]["message"]["content"]
        )
        elapsed = time.perf_counter() - start

        usage = response.get("usage") or {}
        input_tokens = int(usage.get("prompt_tokens") or 0)
        output_tokens = int(usage.get("completion_tokens") or 0)

        timings = response.get("timings") or {}
        generation_time = timings.get("predicted_ms")
        tok_per_sec = None
        if generation_time and output_tokens:
            tok_per_sec = output_tokens / (float(generation_time) / 1000.0)

        cleaned = strip_code_fence(raw_response)
        payload = json.loads(cleaned)
        evidence = validate_model_payload(payload)

        return (
            ChunkResult(
                chunk_id=chunk.chunk_id,
                source_id=chunk.source_id,
                source_path=chunk.source_path,
                chunk_chars=len(chunk.text),
                json_valid=True,
                evidence_count=len(evidence),
                latency_sec=elapsed,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                generation_tok_per_sec=tok_per_sec,
                error=None,
                raw_response=raw_response,
            ),
            evidence,
        )

    except Exception as exc:
        elapsed = time.perf_counter() - start
        return (
            ChunkResult(
                chunk_id=chunk.chunk_id,
                source_id=chunk.source_id,
                source_path=chunk.source_path,
                chunk_chars=len(chunk.text),
                json_valid=False,
                evidence_count=0,
                latency_sec=elapsed,
                input_tokens=0,
                output_tokens=0,
                generation_tok_per_sec=None,
                error=f"{type(exc).__name__}: {exc}",
                raw_response=raw_response,
            ),
            [],
        )


def make_evidence(
    *,
    chunk: Chunk,
    item: dict[str, Any],
    latency_sec: float,
) -> ExtractedEvidence:
    evidence_id = hashlib.sha256(
        (
            f"{chunk.chunk_id}|"
            f"{item['dimension']}|"
            f"{item['field']}|"
            f"{item['supporting_text']}"
        ).encode("utf-8")
    ).hexdigest()[:24]

    return ExtractedEvidence(
        evidence_id=evidence_id,
        chunk_id=chunk.chunk_id,
        source_id=chunk.source_id,
        source_sha256=chunk.source_sha256,
        source_path=chunk.source_path,
        source_type=chunk.source_type,
        source_category=chunk.source_category,
        source_authority=chunk.source_authority,
        extraction_id=chunk.extraction_id,
        extraction_method=chunk.extraction_method,
        processor_name=chunk.processor_name,
        dimension=item["dimension"],
        field=item["field"],
        observation=item["observation"],
        supporting_text=item["supporting_text"],
        confidence=item["confidence"],
        model_latency_sec=latency_sec,
        raw_response="",
    )


def write_output(
    *,
    output: Path,
    startup,
    source_records,
    chunks,
    chunk_results,
    evidences,
    load_time_sec,
    warmup_time_sec,
    llama_cpp_version,
    chunk_chars,
    overlap_chars,
):
    output.parent.mkdir(parents=True, exist_ok=True)

    duplicate_counts = Counter()
    unique_evidence: list[ExtractedEvidence] = []
    seen = set()

    for item in evidences:
        key = evidence_fingerprint(
            source_id=item.source_id,
            dimension=item.dimension,
            field=item.field,
            supporting_text=item.supporting_text,
        )
        duplicate_counts[key] += 1
        if key in seen:
            continue
        seen.add(key)
        unique_evidence.append(item)

    dimension_stats = {
        dimension: {
            "extracted": 0,
            "unique": 0,
        }
        for dimension in DIMENSIONS
    }

    for item in evidences:
        dimension_stats[item.dimension]["extracted"] += 1

    for item in unique_evidence:
        dimension_stats[item.dimension]["unique"] += 1

    latencies = [item.latency_sec for item in chunk_results]
    rates = [
        item.generation_tok_per_sec
        for item in chunk_results
        if item.generation_tok_per_sec is not None
    ]

    valid_count = sum(item.json_valid for item in chunk_results)
    invalid_count = len(chunk_results) - valid_count

    payload = {
        "benchmark": "Qwen2.5-1.5B-Instruct",
        "benchmark_version": BENCHMARK_VERSION,
        "prompt_version": PROMPT_VERSION,
        "benchmark_type": "direct_semantic_document_extraction",
        "startup": {
            "id": str(startup.id),
            "name": startup.name,
        },
        "input": {
            "data_root": str(DEFAULT_DATA_ROOT),
            "source_root": str(
                DEFAULT_DATA_ROOT
                / normalize_startup_key(startup.name)
                / "sources"
            ),
            "source_count": len(source_records),
            "chunk_count": len(chunks),
            "chunk_chars": chunk_chars,
            "overlap_chars": overlap_chars,
            "dimensions": list(DIMENSIONS),
            "source_extraction_identity": "source_id + source_sha256",
        },
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
            "average_chunk_latency_sec": mean(latencies) if latencies else None,
            "minimum_chunk_latency_sec": min(latencies) if latencies else None,
            "maximum_chunk_latency_sec": max(latencies) if latencies else None,
            "total_chunk_inference_sec": sum(latencies),
            "average_generation_tok_per_sec": mean(rates) if rates else None,
            "projected_100_chunks_sec": (
                mean(latencies) * 100 if latencies else None
            ),
        },
        "population": {
            "sources": len(source_records),
            "chunks": len(chunks),
            "json_valid": valid_count,
            "json_invalid": invalid_count,
            "raw_evidence": len(evidences),
            "unique_evidence": len(unique_evidence),
            "duplicate_evidence": len(evidences) - len(unique_evidence),
            "dimensions_with_evidence": sum(
                value["unique"] > 0
                for value in dimension_stats.values()
            ),
        },
        "dimension_statistics": dimension_stats,
        "source_statistics": {},
        "results": [asdict(item) for item in chunk_results],
        "evidence": [asdict(item) for item in unique_evidence],
    }

    source_stats: dict[str, dict[str, int]] = {}
    for item in unique_evidence:
        stats = source_stats.setdefault(
            item.source_path,
            {"evidence": 0},
        )
        stats["evidence"] += 1
    payload["source_statistics"] = source_stats

    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()

    print("=" * 100)
    print("QWEN2.5-1.5B-INSTRUCT — V3.0 DIRECT SEMANTIC EXTRACTION BENCHMARK")
    print("=" * 100)

    if not MODEL_PATH.is_file():
        print(f"ERROR: model not found: {MODEL_PATH}")
        return 2

    if args.chunk_chars <= 0:
        print("ERROR: --chunk-chars must be > 0")
        return 1

    if args.overlap_chars < 0 or args.overlap_chars >= args.chunk_chars:
        print("ERROR: --overlap-chars must be >= 0 and < --chunk-chars")
        return 1

    try:
        from llama_cpp import Llama, __version__ as llama_cpp_version
    except Exception as exc:
        print(f"ERROR: llama-cpp-python unavailable: {exc}")
        return 2

    data_root = Path(args.data_root)
    startup_dir = resolve_startup_directory(
        data_root,
        args.startup,
    )
    source_root = startup_dir / "sources"

    output = (
        Path(args.output)
        if args.output
        else DEFAULT_GENERATED_ROOT
        / normalize_startup_key(args.startup)
        / "benchmark_qwen25_1p5b_v3.json"
    )
    if not output.is_absolute():
        output = Path.cwd() / output

    print(f"DATA ROOT         : {data_root}")
    print(f"STARTUP DIRECTORY : {startup_dir}")
    print(f"SOURCE ROOT       : {source_root}")
    print(f"OUTPUT            : {output}")
    print(f"MODEL             : {MODEL_PATH}")
    print(f"CHUNK CHARS       : {args.chunk_chars}")
    print(f"OVERLAP CHARS     : {args.overlap_chars}")

    session = create_session()

    try:
        startup_service = StartupService(session)
        startup = resolve_startup(
            startup_service,
            args.startup,
        )

        print(f"PERSISTED STARTUP : {startup.name}")
        print(f"CANONICAL UUID    : {startup.id}")

        source_discovery = SourceDiscoveryService()
        extraction_persistence = SourceExtractionPersistenceService(
            session=session,
        )

        source_records = resolve_current_source_extractions(
            startup=startup,
            source_root=source_root,
            source_discovery=source_discovery,
            extraction_persistence=extraction_persistence,
        )

        print(f"CURRENT SOURCES   : {len(source_records)}")
        print(f"CURRENT EXTRACTS  : {len(source_records)}")

        chunks = build_chunks(
            source_records,
            chunk_chars=args.chunk_chars,
            overlap_chars=args.overlap_chars,
        )

        if args.max_chunks > 0:
            chunks = chunks[: args.max_chunks]

        print(f"STRUCTURAL CHUNKS : {len(chunks)}")

        load_start = time.perf_counter()
        llm = Llama(
            model_path=str(MODEL_PATH),
            n_ctx=N_CTX,
            n_threads=N_THREADS,
            n_threads_batch=N_THREADS_BATCH,
            n_gpu_layers=N_GPU_LAYERS,
            verbose=False,
        )
        load_time = time.perf_counter() - load_start
        print(f"MODEL LOAD TIME   : {load_time:.3f} sec")

        warmup_start = time.perf_counter()
        try:
            llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            "Extract evidence from this excerpt and return JSON only.\n"
                            "EXCERPT:\n"
                            "The company generated INR 2 Cr monthly revenue."
                        ),
                    },
                ],
                temperature=TEMPERATURE,
                top_p=TOP_P,
                max_tokens=MAX_TOKENS,
                seed=SEED,
            )
        except Exception as exc:
            print(f"ERROR: warm-up failed: {exc}")
            return 2

        warmup_time = time.perf_counter() - warmup_start
        print(f"WARM-UP TIME      : {warmup_time:.3f} sec")

        print()
        print("=" * 100)
        print("DIRECT SEMANTIC EXTRACTION")
        print("=" * 100)

        chunk_results: list[ChunkResult] = []
        evidences: list[ExtractedEvidence] = []

        for index, chunk in enumerate(chunks, start=1):
            print(
                f"[{index}/{len(chunks)}] "
                f"{chunk.source_path} "
                f"(segment={chunk.segment_index}, chars={len(chunk.text)})"
            )

            result, extracted = run_chunk(llm, chunk)
            chunk_results.append(result)

            for item in extracted:
                evidences.append(
                    make_evidence(
                        chunk=chunk,
                        item=item,
                        latency_sec=result.latency_sec,
                    )
                )

            status = (
                "JSON_OK"
                if result.json_valid
                else "JSON_FAIL"
            )
            print(
                f"  {status} | evidence={len(extracted)} | "
                f"latency={result.latency_sec:.3f}s"
            )

            if result.error:
                print(f"  ERROR: {result.error}")

        print()
        print("=" * 100)
        print("V3.0 SUMMARY")
        print("=" * 100)

        json_valid = sum(item.json_valid for item in chunk_results)
        json_invalid = len(chunk_results) - json_valid

        seen = set()
        unique_count = 0
        for item in evidences:
            key = evidence_fingerprint(
                source_id=item.source_id,
                dimension=item.dimension,
                field=item.field,
                supporting_text=item.supporting_text,
            )
            if key not in seen:
                seen.add(key)
                unique_count += 1

        latencies = [item.latency_sec for item in chunk_results]

        print(f"Sources            : {len(source_records)}")
        print(f"Chunks             : {len(chunks)}")
        print(f"JSON valid         : {json_valid}/{len(chunk_results)}")
        print(f"JSON invalid       : {json_invalid}")
        print(f"Raw evidence       : {len(evidences)}")
        print(f"Unique evidence    : {unique_count}")
        print(
            f"Duplicate evidence : "
            f"{len(evidences) - unique_count}"
        )

        if latencies:
            print(f"Average latency    : {mean(latencies):.3f} sec")
            print(f"Minimum latency    : {min(latencies):.3f} sec")
            print(f"Maximum latency    : {max(latencies):.3f} sec")
            print(
                f"Total inference    : "
                f"{sum(latencies):.1f} sec "
                f"({sum(latencies) / 60:.2f} min)"
            )

        by_dimension = Counter(item.dimension for item in evidences)
        print()
        print("DIMENSION EVIDENCE")
        for dimension in DIMENSIONS:
            print(
                f"  {dimension:28s}: "
                f"{by_dimension.get(dimension, 0)}"
            )

        write_output(
            output=output,
            startup=startup,
            source_records=source_records,
            chunks=chunks,
            chunk_results=chunk_results,
            evidences=evidences,
            load_time_sec=load_time,
            warmup_time_sec=warmup_time,
            llama_cpp_version=llama_cpp_version,
            chunk_chars=args.chunk_chars,
            overlap_chars=args.overlap_chars,
        )

        print()
        print(f"RESULTS JSON       : {output}")
        status = "PASS" if json_invalid == 0 else "FAIL"
        print(f"STATUS             : {status}")

        return 0 if status == "PASS" else 1

    except Exception as exc:
        print()
        print("=" * 100)
        print("V3.0 BENCHMARK FAILED")
        print("=" * 100)
        print(f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
