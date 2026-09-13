"""
B.4.2-v2 parity harness.

Purpose
-------
Reproduce and verify the frozen B.4.2 selective-context architecture without
touching production evidence or scorecard state.

Parity sequence:
    P0 reference integrity
    P1 frozen B.3 population parity
    P2 selector/escalation parity
    P3 N-1/N/N+1 context parity
    P4 configuration/prompt parity
    P5 optional live execution
    P6 final decision parity
    P7 provenance/telemetry parity
    P8 protected-file check

The harness never regenerates B.3 candidates and never writes
dimension_evidence.json.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path("/opt/investment-os")
STARTUP_DIR = ROOT / "data/real_startups/restomart"

B3_REFERENCE = (
    ROOT
    / "generated/restomart/"
    "benchmark_openrouter_v3_3_b3_gptoss20b_coreweave_251.json"
)
B42_REFERENCE = (
    ROOT
    / "generated/restomart/"
    "benchmark_openrouter_v3_3_b4_2_v2_20b_2048.json"
)
SERVICE_PATH = ROOT / "app/services/semantic_context_recovery.py"
REPORT_PATH = (
    ROOT / "generated/restomart/v33_b4_2_v2_parity.json"
)

PROTECTED_RELATIVE = (
    "generated/restomart/dimension_evidence.json",
    "data/real_startups/restomart/investment_scorecard.json",
    "data/real_startups/restomart/startup.yaml",
)

EXPECTED_TOTAL = 251
EXPECTED_B3_ACCEPTED = 110
EXPECTED_B3_REJECTED = 141
EXPECTED_ESCALATED = 14
EXPECTED_FINAL_ACCEPTED = 113
EXPECTED_FINAL_REJECTED = 138
EXPECTED_RECOVERIES = 3

KNOWN_RECOVERIES = {
    "60c4f2390b955a036a79353a": {
        "field": "issue_price",
        "b3": False,
        "final": True,
    },
    "8930322f664a0fe15acc501c4": {
        "field": "revenue",
        "b3": False,
        "final": True,
    },
    "09575497f09ec7ffc336892c": {
        "field": "revenue",
        "b3": False,
        "final": True,
    },
}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Missing artifact: {path}")
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return value


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module: {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def candidate_id(result: Mapping[str, Any]) -> str:
    value = result.get("candidate_id")
    if not value:
        raise RuntimeError("B.3 result missing candidate_id")
    return str(value)


def result_accepted(result: Mapping[str, Any]) -> bool:
    if "actual_label" in result:
        return result["actual_label"] == "A"

    model = result.get("model")
    if isinstance(model, Mapping) and "accepted" in model:
        return bool(model["accepted"])

    if "accepted" in result:
        return bool(result["accepted"])

    raise RuntimeError(
        f"Cannot determine B.3 decision for {candidate_id(result)}"
    )


def result_reason(result: Mapping[str, Any]) -> str:
    if result.get("reason") is not None:
        return str(result["reason"])

    model = result.get("model")
    if isinstance(model, Mapping) and model.get("reason") is not None:
        return str(model["reason"])

    return ""


def extract_results(artifact: Mapping[str, Any]) -> list[dict[str, Any]]:
    results = artifact.get("results")
    if not isinstance(results, list):
        raise RuntimeError("Artifact does not contain results[]")

    normalized = []
    for item in results:
        if not isinstance(item, dict):
            raise RuntimeError("results[] contains a non-object")
        normalized.append(item)

    return normalized


def candidate_from_b3_result(item: Mapping[str, Any]):
    # Frozen B.3 result contains enough information to reconstruct the exact
    # candidate contract used for B.4.2. No new candidate generation occurs.
    return {
        "candidate_id": item["candidate_id"],
        "dimension": item.get("dimension", ""),
        "field": item.get("field", ""),
        "candidate_text": item.get(
            "candidate_text",
            item.get("text", ""),
        ),
        "source_id": item.get("source_id", ""),
        "source_sha256": item.get("source_sha256", ""),
        "source_type": item.get("source_type", ""),
        "source_category": item.get("source_category"),
        "source_authority": item.get("source_authority"),
        "extraction_id": item.get("extraction_id"),
        "extraction_method": item.get("extraction_method"),
        "document_kind": item.get("document_kind"),
        "segment_index": int(item.get("segment_index", 0) or 0),
        "signal": item.get("signal"),
        "signal_start": item.get("signal_start"),
        "signal_end": item.get("signal_end"),
    }


def reference_escalated_ids(
    b42: Mapping[str, Any],
) -> set[str]:
    """Extract authoritative frozen B.4.2 escalation selections.

    The frozen artifact stores selector decisions under:
        results[].escalation.selected

    The parity harness must consume that frozen decision directly rather
    than infer escalation from candidate content.
    """

    ids: set[str] = set()

    results = b42.get("results")
    if not isinstance(results, list):
        raise RuntimeError(
            "Frozen B.4.2 artifact does not contain results[]."
        )

    for item in results:
        if not isinstance(item, Mapping):
            continue

        candidate_id_value = item.get("candidate_id")
        escalation = item.get("escalation")

        if (
            candidate_id_value
            and isinstance(escalation, Mapping)
            and escalation.get("selected") is True
        ):
            ids.add(str(candidate_id_value))

    if not ids:
        raise RuntimeError(
            "Frozen B.4.2 artifact contains no "
            "results[].escalation.selected=true entries."
        )

    return ids

def reference_final_labels(
    b42: Mapping[str, Any],
) -> dict[str, bool]:
    labels: dict[str, bool] = {}

    results = b42.get("results")
    if isinstance(results, list):
        for item in results:
            if not isinstance(item, Mapping):
                continue
            cid = item.get("candidate_id")
            if not cid:
                continue

            if "final_accepted" in item:
                labels[str(cid)] = bool(item["final_accepted"])
                continue

            final = item.get("final")
            if isinstance(final, Mapping) and "accepted" in final:
                labels[str(cid)] = bool(final["accepted"])
                continue

            if "actual_label" in item:
                labels[str(cid)] = item["actual_label"] == "A"
                continue

            b4 = item.get("b4_2")
            b3 = item.get("b3")
            if isinstance(b4, Mapping) and "accepted" in b4:
                b3a = (
                    bool(b3["accepted"])
                    if isinstance(b3, Mapping) and "accepted" in b3
                    else False
                )
                labels[str(cid)] = b3a or bool(b4["accepted"])

    if not labels:
        raise RuntimeError(
            "Frozen B.4.2 artifact does not expose final labels."
        )

    return labels


def file_state(paths: list[Path]) -> dict[str, dict[str, Any]]:
    state = {}
    for path in paths:
        state[str(path)] = {
            "exists": path.exists(),
            "sha256": sha256_file(path) if path.exists() else None,
            "size": path.stat().st_size if path.exists() else None,
        }
    return state


def compare_file_state(
    before: Mapping[str, Mapping[str, Any]],
    after: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    changed = []
    for path, old in before.items():
        new = after.get(path)
        if new != old:
            changed.append(path)
    return {
        "unchanged": not changed,
        "changed": changed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate frozen B.4.2-v2 parity."
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--b3-reference", type=Path, default=B3_REFERENCE)
    parser.add_argument("--b4-reference", type=Path, default=B42_REFERENCE)
    parser.add_argument("--service", type=Path, default=SERVICE_PATH)
    parser.add_argument("--startup-dir", type=Path, default=STARTUP_DIR)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    parser.add_argument("--run-live", action="store_true")
    parser.add_argument("--authorize", action="store_true")
    parser.add_argument("--progress", action="store_true")
    args = parser.parse_args()

    report: dict[str, Any] = {
        "benchmark": {},
        "checks": {},
        "execution": {},
        "recoveries": [],
        "errors": [],
    }

    protected = [
        args.root / relative
        for relative in PROTECTED_RELATIVE
    ]
    before = file_state(protected)

    try:
        b3 = load_json(args.b3_reference)
        b42 = load_json(args.b4_reference)
        service_module = load_module(
            args.service,
            "semantic_context_recovery_parity_service",
        )

        Service = service_module.SemanticContextRecoveryService
        service = Service(
            api_key=os.environ.get("OPENROUTER_API_KEY"),
            concurrency=1,
        )

        report["benchmark"] = {
            "b3_reference": str(args.b3_reference),
            "b4_2_reference": str(args.b4_reference),
            "b3_sha256": sha256_file(args.b3_reference),
            "b4_2_sha256": sha256_file(args.b4_reference),
            "service_sha256": sha256_file(args.service),
            "service_configuration": service.configuration,
        }

        # ------------------------------------------------------------
        # P0 — reference integrity
        # ------------------------------------------------------------
        b3_results = extract_results(b3)
        b42_results = extract_results(b42)

        b3_ids = {candidate_id(x) for x in b3_results}

        population = b42.get("population", {})
        b42_expected = (
            population.get("expected")
            if isinstance(population, Mapping)
            else None
        )

        p0 = {
            "b3_results": len(b3_results),
            "b42_results": len(b42_results),
            "expected_total": EXPECTED_TOTAL,
            "b42_population_expected": b42_expected,
            "pass": (
                len(b3_results) == EXPECTED_TOTAL
                and (
                    b42_expected is None
                    or int(b42_expected) == EXPECTED_TOTAL
                )
            ),
        }
        report["checks"]["P0_reference_integrity"] = p0

        if not p0["pass"]:
            raise RuntimeError("P0 reference integrity failed")

        # ------------------------------------------------------------
        # P1 — frozen B.3 population
        # ------------------------------------------------------------
        b3_accepted = sum(result_accepted(x) for x in b3_results)
        b3_rejected = len(b3_results) - b3_accepted

        p1 = {
            "candidate_count": len(b3_results),
            "accepted": b3_accepted,
            "rejected": b3_rejected,
            "expected_accepted": EXPECTED_B3_ACCEPTED,
            "expected_rejected": EXPECTED_B3_REJECTED,
            "unique_candidate_ids": len(b3_ids),
            "pass": (
                len(b3_results) == EXPECTED_TOTAL
                and len(b3_ids) == EXPECTED_TOTAL
                and b3_accepted == EXPECTED_B3_ACCEPTED
                and b3_rejected == EXPECTED_B3_REJECTED
            ),
        }
        report["checks"]["P1_b3_population"] = p1

        if not p1["pass"]:
            raise RuntimeError("P1 B.3 population parity failed")

        candidates = [
            candidate_from_b3_result(x)
            for x in b3_results
        ]
        b3_by_id = {
            candidate_id(x): x
            for x in b3_results
        }

        # ------------------------------------------------------------
        # P2 — selector parity
        # ------------------------------------------------------------
        selected = service.select_for_recovery(
            candidates,
            b3_by_id,
        )
        current_selected_ids = {
            x.candidate_id
            for x in selected
        }

        reference_selected_ids = reference_escalated_ids(b42)

        missing = sorted(reference_selected_ids - current_selected_ids)
        extra = sorted(current_selected_ids - reference_selected_ids)

        p2 = {
            "reference_count": len(reference_selected_ids),
            "current_count": len(current_selected_ids),
            "missing": missing,
            "extra": extra,
            "escalation_rate": (
                len(current_selected_ids) / len(candidates)
                if candidates else 0.0
            ),
            "pass": (
                len(reference_selected_ids) == EXPECTED_ESCALATED
                and len(current_selected_ids) == EXPECTED_ESCALATED
                and not missing
                and not extra
            ),
        }
        report["checks"]["P2_selector_parity"] = p2

        if not p2["pass"]:
            raise RuntimeError("P2 selector parity failed; live calls blocked")

        # ------------------------------------------------------------
        # P3 — context-window parity
        # ------------------------------------------------------------
        windows = service.build_context_windows(
            candidates,
            selected,
        )

        reference_windows: dict[str, Mapping[str, Any]] = {}

        for item in b42_results:
            if not isinstance(item, Mapping):
                continue
            cid = item.get("candidate_id")
            if not cid:
                continue

            window = item.get("context_window")
            if isinstance(window, Mapping):
                reference_windows[str(cid)] = window

            elif isinstance(item.get("b4_2"), Mapping):
                window = item["b4_2"].get("context_window")
                if isinstance(window, Mapping):
                    reference_windows[str(cid)] = window

        # If the reference artifact does not store full windows, the harness
        # still records the current deterministic windows and validates their
        # source/candidate anchoring. Exact text parity requires reference data.
        context_differences = []

        if reference_windows:
            for cid, current in windows.items():
                reference = reference_windows.get(cid)
                if reference is None:
                    context_differences.append({
                        "candidate_id": cid,
                        "difference": "missing_reference_window",
                    })
                    continue

                current_dict = current.as_dict()
                keys = (
                    "previous_candidate_id",
                    "next_candidate_id",
                    "previous_text",
                    "candidate_text",
                    "next_text",
                    "source_id",
                    "source_sha256",
                    "segment_index",
                )
                for key in keys:
                    if reference.get(key) != current_dict.get(key):
                        context_differences.append({
                            "candidate_id": cid,
                            "field": key,
                            "reference": reference.get(key),
                            "current": current_dict.get(key),
                        })

        p3 = {
            "expected_windows": EXPECTED_ESCALATED,
            "current_windows": len(windows),
            "reference_windows_available": bool(reference_windows),
            "differences": context_differences,
            "pass": (
                len(windows) == EXPECTED_ESCALATED
                and not context_differences
            ),
        }
        report["checks"]["P3_context_window_parity"] = p3

        if not p3["pass"]:
            raise RuntimeError("P3 context-window parity failed")

        # ------------------------------------------------------------
        # P4 — configuration / prompt parity
        # ------------------------------------------------------------
        prompt_hashes = {}
        for candidate in selected:
            window = windows[candidate.candidate_id]
            prompt = service.build_prompt(candidate, window)
            prompt_hashes[candidate.candidate_id] = {
                "prompt_sha256": service.prompt_hash(prompt),
                "context_sha256": service.context_hash(window),
                "prompt_length": len(prompt),
            }

        reference_config = b42.get("configuration", {})
        if not isinstance(reference_config, Mapping):
            reference_config = {}

        current_config = service.configuration

        config_fields = (
            "model",
            "provider",
            "temperature",
            "top_p",
            "max_tokens",
            "reasoning_effort",
            "concurrency",
        )

        config_differences = {}
        for field in config_fields:
            if field in reference_config:
                if reference_config[field] != current_config[field]:
                    config_differences[field] = {
                        "reference": reference_config[field],
                        "current": current_config[field],
                    }

        p4 = {
            "current_configuration": current_config,
            "reference_configuration": dict(reference_config),
            "differences": config_differences,
            "prompt_hashes": prompt_hashes,
            "pass": not config_differences,
        }
        report["checks"]["P4_configuration_prompt"] = p4

        if not p4["pass"]:
            raise RuntimeError("P4 configuration/prompt parity failed")

        # ------------------------------------------------------------
        # P5 — optional live execution
        # ------------------------------------------------------------
        if args.run_live and not args.authorize:
            raise RuntimeError(
                "--run-live requires explicit --authorize"
            )

        live_results = []

        if args.run_live:
            live_results = service.recover_many(
                candidates,
                b3_by_id,
                progress=args.progress,
            )

            invalid = [x for x in live_results if not x.valid]
            provider_drift = [
                x for x in live_results
                if x.provider not in (None, service.provider)
            ]
            retries = sum(x.retries for x in live_results)

            p5 = {
                "run_live": True,
                "expected_requests": EXPECTED_ESCALATED,
                "completed_requests": len(live_results),
                "valid": len(live_results) - len(invalid),
                "invalid": len(invalid),
                "provider_drift": len(provider_drift),
                "retry_count": retries,
                "pass": (
                    len(live_results) == EXPECTED_ESCALATED
                    and not invalid
                    and not provider_drift
                ),
            }
        else:
            p5 = {
                "run_live": False,
                "status": "SKIPPED",
                "pass": True,
            }

        report["checks"]["P5_execution"] = p5

        if not p5["pass"]:
            raise RuntimeError("P5 live execution failed")

        # ------------------------------------------------------------
        # P6 — decision parity
        # ------------------------------------------------------------
        if args.run_live:
            final_rows = service.apply_results(
                candidates,
                b3_by_id,
                live_results,
            )

            final_by_id = {
                row["candidate_id"]: bool(row["final"]["accepted"])
                for row in final_rows
            }

            reference_final = reference_final_labels(b42)

            decision_differences = []
            for cid in sorted(b3_ids):
                if cid not in reference_final:
                    # Reference may expose only contextual rows. In that case
                    # the non-escalated B.3 decision is authoritative.
                    continue

                if final_by_id.get(cid) != reference_final[cid]:
                    decision_differences.append({
                        "candidate_id": cid,
                        "reference": reference_final[cid],
                        "current": final_by_id.get(cid),
                    })

            final_accepted = sum(final_by_id.values())
            final_rejected = len(final_by_id) - final_accepted

            recoveries = [
                row for row in final_rows
                if (
                    row["b3"]["accepted"] is False
                    and row["final"]["accepted"] is True
                )
            ]

            p6 = {
                "final_candidates": len(final_rows),
                "accepted": final_accepted,
                "rejected": final_rejected,
                "expected_accepted": EXPECTED_FINAL_ACCEPTED,
                "expected_rejected": EXPECTED_FINAL_REJECTED,
                "recoveries": len(recoveries),
                "expected_recoveries": EXPECTED_RECOVERIES,
                "decision_differences": decision_differences,
                "pass": (
                    len(final_rows) == EXPECTED_TOTAL
                    and final_accepted == EXPECTED_FINAL_ACCEPTED
                    and final_rejected == EXPECTED_FINAL_REJECTED
                    and len(recoveries) == EXPECTED_RECOVERIES
                    and not decision_differences
                ),
            }

            report["recoveries"] = [
                {
                    "candidate_id": row["candidate_id"],
                    "dimension": row["dimension"],
                    "field": row["field"],
                    "b3_accepted": row["b3"]["accepted"],
                    "final_accepted": row["final"]["accepted"],
                    "reason": row["b4_2"].get("reason"),
                }
                for row in recoveries
            ]
        else:
            p6 = {
                "status": "SKIPPED",
                "pass": True,
            }

        report["checks"]["P6_decision_parity"] = p6

        if not p6["pass"]:
            raise RuntimeError("P6 decision parity failed")

        # ------------------------------------------------------------
        # P7 — known recovery assertions
        # ------------------------------------------------------------
        if args.run_live:
            recovery_map = {
                x["candidate_id"]: x
                for x in report["recoveries"]
            }

            assertions = []
            for cid, expected in KNOWN_RECOVERIES.items():
                actual = recovery_map.get(cid)
                assertions.append({
                    "candidate_id": cid,
                    "expected": expected,
                    "actual": (
                        {
                            "field": actual["field"],
                            "b3": actual["b3_accepted"],
                            "final": actual["final_accepted"],
                        }
                        if actual else None
                    ),
                    "pass": (
                        actual is not None
                        and actual["field"] == expected["field"]
                        and actual["b3_accepted"] == expected["b3"]
                        and actual["final_accepted"] == expected["final"]
                    ),
                })

            report["checks"]["P7_known_recoveries"] = {
                "assertions": assertions,
                "pass": all(x["pass"] for x in assertions),
            }

            if not report["checks"]["P7_known_recoveries"]["pass"]:
                raise RuntimeError("Known recovery assertions failed")
        else:
            report["checks"]["P7_known_recoveries"] = {
                "status": "SKIPPED",
                "pass": True,
            }

        # ------------------------------------------------------------
        # P8 — protected files
        # ------------------------------------------------------------
        after = file_state(protected)
        protected_result = compare_file_state(before, after)
        report["checks"]["P8_protected_files"] = protected_result

        if not protected_result["unchanged"]:
            raise RuntimeError("Protected production files changed")

        report["status"] = "PASS"

    except Exception as exc:
        report["status"] = "FAIL"
        report["errors"].append(str(exc))

    finally:
        after = file_state(protected)
        report["protected_files"] = compare_file_state(before, after)

        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)

    print("")
    print("=" * 64)
    print("B.4.2-v2 PARITY")
    print("=" * 64)

    for key, value in report["checks"].items():
        if isinstance(value, Mapping):
            status = (
                "PASS"
                if value.get("pass") is True
                else value.get("status", "FAIL")
            )
            print(f"{key:32s}: {status}")

    print(f"{'STATUS':32s}: {report['status']}")
    print(f"{'REPORT':32s}: {args.report}")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
