#!/usr/bin/env python3
"""
V3.3-A.1 deterministic Candidate Quality Gate.

Experimental benchmark only. This script does NOT call an LLM and does NOT
modify the production evidence/scoring pipeline.

Pipeline:
    V3.2 benchmark candidates
        -> normalization
        -> generic structural gate
        -> negative/noise gate
        -> field-specific structural gate
        -> anchor/context gate
        -> PASS / REJECT
        -> auditable JSON report

Design principle:
    The gate does not decide whether evidence is semantically true.
    It decides whether a candidate has enough structural signal to justify
    an expensive semantic-validation call.

Input:
    benchmark_qwen25_1p5b_v3_2.json

Output:
    benchmark_qwen25_1p5b_v3_3_gate.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


BENCHMARK_VERSION = "V3.3-A.1.2"
GATE_VERSION = "candidate-quality-gate-v1.3"

DEFAULT_INPUT = Path(
    "/opt/investment-os/generated/restomart/"
    "benchmark_qwen25_1p5b_v3_2.json"
)
DEFAULT_OUTPUT = Path(
    "/opt/investment-os/generated/restomart/"
    "benchmark_qwen25_1p5b_v3_3_gate.json"
)

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


# ---------------------------------------------------------------------------
# Generic patterns
# ---------------------------------------------------------------------------

NUMBER_RE = re.compile(
    r"""
    (?:
        \d+(?:[.,]\d+)*\s*% |
        (?:₹|rs\.?|inr|usd|\$)\s*\d+(?:[.,]\d+)* |
        \d+(?:[.,]\d+)*\s*(?:cr|crore|crores|lakh|lakhs|million|billion|m|b|k) |
        \b\d+(?:[.,]\d+)*\b
    )
    """,
    re.I | re.X,
)

PERIOD_RE = re.compile(
    r"\b(?:fy\s*\d{2,4}|q[1-4]|monthly|per month|/month|weekly|daily|yearly|"
    r"annual|annually|quarterly|year[- ]on[- ]year|yoy|mom|since|from|to)\b",
    re.I,
)

MONEY_RE = re.compile(
    r"(?:₹|rs\.?|inr|usd|\$)\s*\d+(?:[.,]\d+)*"
    r"|\b\d+(?:[.,]\d+)*\s*(?:cr|crore|crores|lakh|lakhs|million|billion)\b",
    re.I,
)

PERCENT_RE = re.compile(r"\b\d+(?:\.\d+)?\s*%", re.I)

FORMULA_RE = re.compile(r"(?:^|\s)=\s*[A-Z0-9_$().:+*/,\- ]{3,}", re.I)

HEADING_ONLY_RE = re.compile(
    r"^[\s\W_]*[A-Za-z][A-Za-z0-9 &'()/,\-]{1,80}[\s\W_]*$"
)

PAGE_RE = re.compile(
    r"^(?:page|pg\.?)\s+\d+(?:\s+of\s+\d+)?$",
    re.I,
)

ADMIN_PATTERNS = {
    "administrative_identity": (
        r"\bpan\b",
        r"\bpermanent account number\b",
        r"\bgstin\b",
        r"\bcin\b",
        r"\bregistered office\b",
        r"\bregistered address\b",
        r"\bgovernment of india\b",
        r"\bincorporation certificate\b",
    ),
    "signature_witness": (
        r"\bsignature\b",
        r"\bsigned by\b",
        r"\bwitness\b",
        r"\bsigned in the presence\b",
    ),
}

ACCOUNTING_POLICY_PATTERNS = (
    r"\baccounted for on accrual basis\b",
    r"\baccounted for on cash basis\b",
    r"\baccounting polic(?:y|ies)\b",
    r"\brevenue (?:is|are) (?:recognised|recognized)\b",
    r"\brevenue recognition\b",
    r"\brecognition of revenue\b",
    r"\bdepreciation (?:is|was) provided\b",
    r"\bcharged to (?:the )?profit and loss\b",
    r"\bind[- ]?as\b",
    r"\bbasis of accounting\b",
    r"\baccrual basis\b",
)

LEGAL_ORDER_PATTERNS = (
    r"\border(?:s)? passed\b",
    r"\borders? passed by\b",
    r"\bcourt\b",
    r"\btribunal\b",
    r"\bregulator(?:s|y)?\b",
    r"\bregulatory authority\b",
    r"\blegal proceedings\b",
    r"\bproceedings\b",
    r"\bjudg(?:e|ment)\b",
)

LEGAL_BOILERPLATE_PATTERNS = (
    r"\bsubject to the provisions\b",
    r"\bnotwithstanding anything contained\b",
    r"\bfor the purposes of this article\b",
    r"\bhereinafter referred to as\b",
    r"\bin accordance with applicable law\b",
)

REPEATED_NOISE_PATTERNS = (
    r"\bpage\s+\d+\s+of\s+\d+\b",
    r"\bconfidential\b.{0,20}\bpage\b",
    r"\bwww\.[a-z0-9.-]+\.[a-z]{2,}\b",
)


# ---------------------------------------------------------------------------
# Field-specific positive/negative rules
# ---------------------------------------------------------------------------

FINANCIAL_FIELDS = {
    "revenue": (
        r"\brevenue\b",
        r"\bsales\b",
        r"\bturnover\b",
        r"\bnet sales\b",
    ),
    "gross_profit": (
        r"\bgross profit\b",
        r"\bgross margin\b",
    ),
    "ebitda": (
        r"\bebitda\b",
        r"\bebit\b",
    ),
    "profit_loss": (
        r"\bnet profit\b",
        r"\bnet loss\b",
        r"\bprofit after tax\b",
        r"\bloss after tax\b",
        r"\bpbt\b",
        r"\bpat\b",
        r"\bprofit\b",
        r"\bloss\b",
    ),
    "cash_burn": (
        r"\bcash burn\b",
        r"\bmonthly burn\b",
        r"\bburn rate\b",
        r"\brunway\b",
        r"\bcash balance\b",
        r"\bliquidity\b",
        r"\bworking capital\b",
    ),
    "expenses": (
        r"\boperating expenses?\b",
        r"\bopex\b",
        r"\bexpenses?\b",
        r"\bexpenditure\b",
    ),
}

COMMERCIAL_FIELDS = {
    "customers": (
        r"\bcustomers?\b",
        r"\brestaurants?\b",
        r"\bclients?\b",
        r"\baccounts?\b",
    ),
    "orders": (
        r"\borders?\b",
        r"\btransactions?\b",
        r"\bdeliveries?\b",
    ),
    "gmv": (
        r"\bgmv\b",
        r"\bgross merchandise value\b",
    ),
    "monthly_revenue": (
        r"\brevenue\b",
        r"\bsales\b",
    ),
    "growth": (
        r"\bgrowth\b",
        r"\bgrew\b",
        r"\bincreased\b",
        r"\bdecreased\b",
        r"\bcagr\b",
        r"\byoy\b",
        r"\bmom\b",
    ),
    "recurring_revenue": (
        r"\bmrr\b",
        r"\barr\b",
        r"\bannual recurring revenue\b",
        r"\bmonthly recurring revenue\b",
    ),
    "repeat": (
        r"\brepeat\b",
        r"\bretention\b",
        r"\brenewal\b",
        r"\bchurn\b",
    ),
}

UNIT_FIELDS = {
    "cac": (
        r"\bcac\b",
        r"\bcustomer acquisition cost\b",
    ),
    "ltv": (
        r"\bltv\b",
        r"\blifetime value\b",
        r"\bcustomer lifetime value\b",
    ),
    "margin": (
        r"\bgross margin\b",
        r"\bcontribution margin\b",
        r"\bcontribution\b",
    ),
    "payback": (
        r"\bpayback\b",
        r"\bpayback period\b",
    ),
    "unit_cost": (
        r"\bcost per order\b",
        r"\bcost per customer\b",
        r"\bfulfillment cost\b",
        r"\bdelivery cost\b",
        r"\btransaction cost\b",
    ),
}

MARKET_FIELDS = {
    "market_size": (
        r"\btam\b",
        r"\bsam\b",
        r"\bsom\b",
        r"\bmarket size\b",
        r"\bmarket opportunity\b",
        r"\baddressable market\b",
    ),
    "market_growth": (
        r"\bmarket growth\b",
        r"\bmarket grew\b",
        r"\bcagr\b",
        r"\bgrowth rate\b",
    ),
    "target_customers": (
        r"\brestaurants?\b",
        r"\btarget customers?\b",
        r"\baddressable customers?\b",
        r"\bpotential customers?\b",
    ),
}

TECH_FIELDS = {
    "proprietary_technology": (
        r"\bproprietary technology\b",
        r"\bproprietary platform\b",
        r"\bproprietary software\b",
    ),
    "ai_ml": (
        r"\bai\b",
        r"\bartificial intelligence\b",
        r"\bmachine learning\b",
        r"\bml model\b",
        r"\bdeep learning\b",
    ),
    "algorithm": (
        r"\balgorithm\b",
        r"\bprediction model\b",
        r"\bpredictive model\b",
        r"\bcomputer vision\b",
        r"\boptimization engine\b",
    ),
    "patent_ip": (
        r"\bpatent(?:s)?\b",
        r"\bintellectual property\b",
        r"\bip portfolio\b",
    ),
    "platform_architecture": (
        r"\bplatform architecture\b",
        r"\btechnical architecture\b",
        r"\bsoftware architecture\b",
        r"\btechnology stack\b",
    ),
}

GOVERNANCE_FIELDS = {
    "shareholding": (
        r"\bshareholding\b",
        r"\bshareholders?\b",
        r"\bcap table\b",
        r"\bequity holding\b",
        r"\bownership\b",
        r"\bshares?\b",
    ),
    "board_rights": (
        r"\bboard\b",
        r"\bdirector\b",
        r"\bobserver\b",
    ),
    "reserved_matters": (
        r"\breserved matters?\b",
        r"\baffirmative vote\b",
        r"\bconsent matters?\b",
        r"\binvestor consent\b",
    ),
    "voting_rights": (
        r"\bvoting rights?\b",
        r"\bvote\b",
        r"\bvoting\b",
    ),
}

VALUATION_FIELDS = {
    "valuation": (
        r"\bvaluation\b",
        r"\bpre[- ]money\b",
        r"\bpost[- ]money\b",
    ),
    "round_size": (
        r"\bround size\b",
        r"\bround\b",
        r"\bfundrais(?:e|ing)\b",
        r"\braising\b",
        r"\braise\b",
        r"\binvestment\b",
    ),
    "issue_price": (
        r"\bissue price\b",
        r"\bsubscription price\b",
        r"\bprice per share\b",
    ),
    "instrument": (
        r"\bccps\b",
        r"\bequity shares?\b",
        r"\bconvertible\b",
        r"\bdebenture\b",
        r"\bpreference shares?\b",
    ),
}

RISK_FIELDS = {
    "risk": (
        r"\brisk\b",
        r"\brisks\b",
        r"\brisk factor\b",
        r"\brisk factors\b",
        r"\bconcern\b",
        r"\bchallenge\b",
    ),
    "concentration": (
        r"\bcustomer concentration\b",
        r"\bsupplier concentration\b",
        r"\bconcentration risk\b",
    ),
    "working_capital": (
        r"\bworking capital\b",
        r"\bcash conversion\b",
        r"\binventory risk\b",
        r"\bliquidity risk\b",
    ),
    "exit_liquidity": (
        r"\bexit\b",
        r"\bliquidity\b",
        r"\bbuyback\b",
        r"\bdrag[- ]along\b",
        r"\btag[- ]along\b",
        r"\bput option\b",
        r"\bredemption\b",
    ),
}


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="V3.3-A.1.1 deterministic candidate quality gate."
    )
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--min-chars", type=int, default=35)
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=0,
        help="0 means all candidates.",
    )
    return parser.parse_args()


def normalize(text: Any) -> str:
    if text is None:
        return ""
    value = str(text).replace("\x00", "")
    value = value.replace("\u00a0", " ")
    value = re.sub(r"[\u2018\u2019\u201c\u201d]", "'", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def lower(text: str) -> str:
    return normalize(text).lower()


def matches_any(text: str, patterns: tuple[str, ...] | list[str]) -> bool:
    return any(re.search(pattern, text, re.I) for pattern in patterns)


def count_matches(text: str, patterns: tuple[str, ...] | list[str]) -> int:
    return sum(bool(re.search(pattern, text, re.I)) for pattern in patterns)


def has_number(text: str) -> bool:
    return bool(NUMBER_RE.search(text))


def has_money(text: str) -> bool:
    return bool(MONEY_RE.search(text))


def has_percent(text: str) -> bool:
    return bool(PERCENT_RE.search(text))


def has_period(text: str) -> bool:
    return bool(PERIOD_RE.search(text))


def formula_ratio(text: str) -> float:
    if not text:
        return 0.0
    formula_chars = sum(ch == "=" for ch in text)
    return formula_chars / max(len(text), 1)


def word_count(text: str) -> int:
    return len(re.findall(r"\b[A-Za-z][A-Za-z0-9'-]*\b", text))


def has_named_person_shape(text: str) -> bool:
    """
    Conservative name heuristic for founder evidence.

    We intentionally do not attempt entity recognition here. This only checks
    whether the candidate contains at least two title-case alphabetic tokens,
    or an explicit founder role + a likely personal name.
    """
    tokens = re.findall(r"\b[A-Z][a-z]{2,}\b", text)
    if len(tokens) >= 2:
        return True

    return bool(
        re.search(
            r"\b(?:founder|co-founder|promoter)\b.{0,100}"
            r"\b[A-Z][a-z]{2,}\b",
            text,
        )
    )


# ---------------------------------------------------------------------------
# V3.3-A.1 anchor/context gate helpers
# ---------------------------------------------------------------------------

FORMULA_FRAGMENT_RE = re.compile(r"(?:^|[|;\n])\s*=\s*[^|;\n]+", re.I)
RATIO_NOISE_PATTERNS = (
    r"\bturnover ratio\b", r"\btrade receivable turnover\b",
    r"\btrade payable turnover\b", r"\binventory turnover\b",
    r"\bworking capital turnover\b", r"\bcurrent ratio\b",
    r"\bquick ratio\b", r"\bdebt[- ]equity ratio\b",
)
EXIT_ACCOUNTING_NOISE = (
    r"\bcapital redemption reserve\b", r"\bsecurities premium account\b",
    r"\bcapital reserve\b", r"\bredemption reserve\b",
)
FINANCIAL_ANCHORS = {
    "revenue": (r"\brevenue\b", r"\bsales\b", r"\bnet sales\b", r"\btotal income\b"),
    "gross_profit": (r"\bgross profit\b", r"\bgross margin\b"),
    "ebitda": (r"\bebitda\b", r"\bebit\b"),
    "profit_loss": (r"\bnet profit\b", r"\bnet loss\b", r"\bprofit after tax\b", r"\bloss after tax\b", r"\bpat\b", r"\bpbt\b"),
    "expenses": (r"\boperating expenses?\b", r"\bopex\b", r"\bexpenses?\b", r"\bexpenditure\b"),
    "cash_burn": (r"\bcash burn\b", r"\bmonthly burn\b", r"\bburn rate\b", r"\brunway\b", r"\bcash balance\b", r"\bliquidity\b", r"\bworking capital\b"),
}
COMMERCIAL_ANCHORS = {
    "customers": (r"\bcustomers?\b", r"\brestaurants?\b", r"\bclients?\b", r"\baccounts?\b"),
    "orders": (r"\borders?\b", r"\btransactions?\b", r"\bdeliveries?\b"),
    "gmv": (r"\bgmv\b", r"\bgross merchandise value\b"),
    "monthly_revenue": (r"\brevenue\b", r"\bsales\b"),
    "growth": (r"\bgrowth\b", r"\bgrew\b", r"\bincreased\b", r"\bdecreased\b", r"\bcagr\b", r"\byoy\b", r"\bmom\b"),
    "recurring_revenue": (r"\bmrr\b", r"\barr\b", r"\bannual recurring revenue\b", r"\bmonthly recurring revenue\b"),
    "repeat": (r"\brepeat\b", r"\bretention\b", r"\brenewal\b", r"\bchurn\b"),
}
UNIT_ANCHORS = {
    "cac": (r"\bcac\b", r"\bcustomer acquisition cost\b"),
    "ltv": (r"\bltv\b", r"\blifetime value\b", r"\bcustomer lifetime value\b"),
    "margin": (r"\bgross margin\b", r"\bcontribution margin\b", r"\bcontribution\b"),
    "payback": (r"\bpayback\b", r"\bpayback period\b"),
    "unit_cost": (r"\bcost per order\b", r"\bcost per customer\b", r"\bfulfillment cost\b", r"\bdelivery cost\b", r"\btransaction cost\b"),
}
MARKET_ANCHORS = {
    "market_size": (r"\btam\b", r"\bsam\b", r"\bsom\b", r"\bmarket size\b", r"\bmarket opportunity\b", r"\baddressable market\b"),
    "market_growth": (r"\bmarket growth\b", r"\bmarket grew\b", r"\bcagr\b", r"\bgrowth rate\b"),
    "target_customers": (r"\brestaurants?\b", r"\btarget customers?\b", r"\baddressable customers?\b", r"\bpotential customers?\b"),
}

def _anchor_positions(text, patterns):
    return [m.start() for pat in patterns for m in re.finditer(pat, text, re.I)]

def _number_positions(text):
    return [m.start() for m in NUMBER_RE.finditer(text)]

def has_number_near_anchor(text, patterns, window=120):
    a=_anchor_positions(text, patterns); n=_number_positions(text)
    return bool(a and n and any(abs(x-y)<=window for x in a for y in n))

def has_money_near_anchor(text, patterns, window=160):
    a=_anchor_positions(text, patterns); n=[m.start() for m in MONEY_RE.finditer(text)]
    return bool(a and n and any(abs(x-y)<=window for x in a for y in n))

def has_percent_near_anchor(text, patterns, window=120):
    a=_anchor_positions(text, patterns); n=[m.start() for m in PERCENT_RE.finditer(text)]
    return bool(a and n and any(abs(x-y)<=window for x in a for y in n))

def formula_count(text): return len(FORMULA_FRAGMENT_RE.findall(normalize(text)))
def resolved_text(text): return FORMULA_FRAGMENT_RE.sub(" ", normalize(text))
def is_spreadsheet(candidate):
    p=str(candidate.get("source_path","")).lower(); t=str(candidate.get("source_type","")).lower()
    return p.endswith((".xlsx",".xls",".csv")) or t in {"xlsx","xls","csv"}
def is_formula_unresolved(text):
    r=resolved_text(text)
    return formula_count(text)>0 and not (MONEY_RE.search(r) or PERCENT_RE.search(r))

def a1_anchor_gate(candidate):
    x=lower(candidate.get("text","")); field=str(candidate.get("field", "")); dim=str(candidate.get("dimension", ""))
    if field == "exit_liquidity" and matches_any(x, EXIT_ACCOUNTING_NOISE) and not matches_any(x,(r"\binvestor\b",r"\bshareholder\b",r"\bbuyback\b",r"\bdrag[- ]along\b",r"\btag[- ]along\b",r"\bput option\b",r"\bexit\b")):
        return GateDecision(False,"anchor_context","accounting_reserve_not_exit","Accounting reserve terminology is not an investor exit/liquidity mechanism.")
    if dim == "financial_health":
        anchors=FINANCIAL_ANCHORS.get(field, FINANCIAL_FIELDS.get(field, ()))
        if field == "revenue" and matches_any(x,RATIO_NOISE_PATTERNS):
            return GateDecision(False,"anchor_context","financial_ratio_noise","Revenue candidate is embedded in an accounting ratio context.")
        if field in FINANCIAL_ANCHORS and not has_number_near_anchor(x,anchors):
            return GateDecision(False,"anchor_context","metric_value_not_near_anchor","No quantified value is sufficiently close to the financial metric anchor.")
        if is_spreadsheet(candidate) and is_formula_unresolved(x):
            return GateDecision(False,"anchor_context","unresolved_formula_fragment","Spreadsheet candidate has formulas without a resolved metric value.")
    elif dim == "commercial_traction":
        anchors=COMMERCIAL_ANCHORS.get(field, COMMERCIAL_FIELDS.get(field,()))
        if field in {"customers","orders","gmv","monthly_revenue","growth"} and not has_number_near_anchor(x,anchors):
            return GateDecision(False,"anchor_context","metric_value_not_near_anchor","Commercial metric lacks a quantified value near its semantic anchor.")
        if field == "orders" and matches_any(x,LEGAL_ORDER_PATTERNS):
            return GateDecision(False,"anchor_context","legal_order_context","Order candidate is associated with legal/regulatory context.")
    elif dim == "unit_economics_margins":
        anchors=UNIT_ANCHORS.get(field,UNIT_FIELDS.get(field,()))
        if not (has_number_near_anchor(x,anchors) or has_money_near_anchor(x,anchors) or has_percent_near_anchor(x,anchors)):
            return GateDecision(False,"anchor_context","unit_metric_value_not_near_anchor","Unit metric lacks a resolved value near its metric anchor.")
        if is_spreadsheet(candidate) and is_formula_unresolved(x):
            return GateDecision(False,"anchor_context","unresolved_formula_fragment","Spreadsheet unit metric contains unresolved formula content.")
    elif dim == "market_tam":
        anchors=MARKET_ANCHORS.get(field,MARKET_FIELDS.get(field,()))
        if field in {"market_size","market_growth","target_customers"} and not has_number_near_anchor(x,anchors):
            return GateDecision(False,"anchor_context","market_value_not_near_anchor","Market candidate lacks a quantified value near its market/customer anchor.")
    return None



# ---------------------------------------------------------------------------
# V3.3-A.1.2 working-capital-specific refinement
# ---------------------------------------------------------------------------

WORKING_CAPITAL_ACCOUNTING_RATIO_PATTERNS = (
    r"\bnet capital turnover ratio\b",
    r"\bnet capital tumover ratio\b",       # OCR/PDF extraction variant
    r"\bcapital turnover ratio\b",
    r"\btrade receivable turnover\b",
    r"\btrade receivables turnover\b",
    r"\btrade payable turnover\b",
    r"\btrade payables turnover\b",
    r"\binventory turnover\b",
    r"\bcurrent ratio\b",
    r"\bquick ratio\b",
    r"\bdebt[- ]equity ratio\b",
    r"\bdebt equity ratio\b",
)

WORKING_CAPITAL_EXPLICIT_CONTEXT_PATTERNS = (
    r"\bworking capital requirement\b",
    r"\bworking capital needs?\b",
    r"\bworking capital funding\b",
    r"\bworking capital gap\b",
    r"\bworking capital shortage\b",
    r"\bworking capital pressure\b",
    r"\bworking capital constraint\b",
    r"\bworking capital risk\b",
    r"\bworking capital cycle\b",
    r"\bcash conversion cycle\b",
)

WORKING_CAPITAL_RISK_CONTEXT_PATTERNS = (
    r"\bworking capital risk\b",
    r"\bliquidity risk\b",
    r"\bliquidity pressure\b",
    r"\bworking capital pressure\b",
    r"\bworking capital shortage\b",
    r"\bworking capital constraint\b",
    r"\bcash conversion cycle\b",
    r"\bworking capital gap\b",
)


def working_capital_accounting_ratio(text: str) -> bool:
    return matches_any(text, WORKING_CAPITAL_ACCOUNTING_RATIO_PATTERNS)


def working_capital_explicit_context(text: str) -> bool:
    return matches_any(text, WORKING_CAPITAL_EXPLICIT_CONTEXT_PATTERNS)


def working_capital_risk_context(text: str) -> bool:
    return matches_any(text, WORKING_CAPITAL_RISK_CONTEXT_PATTERNS)


def candidate_formula_driven(candidate: dict[str, Any]) -> bool:
    """Reuse existing gate features; fall back to conservative text detection."""
    gate = candidate.get("gate") or {}
    features = {}
    for key in ("gate_features", "v3_3_a1_1_features", "v3_3_a1_2_features"):
        value = gate.get(key)
        if isinstance(value, dict):
            features.update(value)

    formula_count = features.get("formula_count", 0)
    formula_ratio = features.get("formula_ratio", 0.0)
    unresolved = bool(features.get("unresolved_formula_fragment", False))

    if isinstance(formula_count, (int, float)) and formula_count > 0:
        return True
    if isinstance(formula_ratio, (int, float)) and formula_ratio > 0:
        return True
    if unresolved:
        return True

    text = normalize(candidate.get("text", ""))
    return bool(
        re.search(
            r"(?m)(?:^|[|;\n])\s*=\s*[A-Za-z0-9_$().+\-*/]+",
            text,
        )
    )


def candidate_has_resolved_numeric_value(candidate: dict[str, Any]) -> bool:
    """Prefer existing A.1.1 features; otherwise inspect formula-stripped text."""
    gate = candidate.get("gate") or {}
    features = {}
    for key in ("gate_features", "v3_3_a1_1_features", "v3_3_a1_2_features"):
        value = gate.get(key)
        if isinstance(value, dict):
            features.update(value)

    for key in (
        "resolved_numeric_count",
        "resolved_money_count",
        "resolved_percent_count",
        "resolved_value_count",
    ):
        value = features.get(key)
        if isinstance(value, (int, float)) and value > 0:
            return True

    text = normalize(candidate.get("text", ""))
    text = re.sub(r"(?m)(?:^|[|;\n])\s*=\s*[^|;\n]+", " ", text)

    return bool(
        re.search(r"(?:₹|rs\.?|inr|usd|\$|€|£)\s*\d[\d,]*(?:\.\d+)?", text, re.I)
        or re.search(r"\b\d+(?:\.\d+)?\s*%", text)
        or re.search(r"\b\d[\d,]*(?:\.\d+)?\b", text)
    )


def gate_working_capital_a1_2(candidate: dict[str, Any]) -> GateDecision | None:
    """Surgical A.1.2 gate; applies only to working_capital."""
    if str(candidate.get("field", "")).strip() != "working_capital":
        return None

    text = normalize(candidate.get("text", ""))
    ratio = working_capital_accounting_ratio(text)
    explicit_context = working_capital_explicit_context(text)
    explicit_risk = working_capital_risk_context(text)
    formula_driven = candidate_formula_driven(candidate)
    resolved_value = candidate_has_resolved_numeric_value(candidate)

    if ratio and not explicit_risk:
        return GateDecision(
            False,
            "negative_pattern",
            "accounting_ratio_not_working_capital_risk",
            "Accounting ratio lacks explicit working-capital or liquidity-risk interpretation.",
        )

    if formula_driven and not explicit_context and not explicit_risk:
        return GateDecision(
            False,
            "negative_pattern",
            "formula_working_capital_not_investment_evidence",
            "Formula-driven working-capital calculation lacks explicit investment-relevant context.",
        )

    if formula_driven and not resolved_value and not explicit_risk:
        return GateDecision(
            False,
            "anchor_context",
            "working_capital_without_resolved_value",
            "Formula-driven working-capital candidate lacks a resolved value or explicit risk interpretation.",
        )

    return None


# ---------------------------------------------------------------------------
# V3.3-A.1.1 deterministic false-positive refinements
# ---------------------------------------------------------------------------

ACCOUNTING_RATIO_PATTERNS = (
    r"\bnet capital turnover ratio\b",
    r"\bcapital turnover ratio\b",
    r"\btrade receivable turnover\b",
    r"\btrade payable turnover\b",
    r"\binventory turnover\b",
    r"\bcurrent ratio\b",
    r"\bquick ratio\b",
    r"\bdebt[- ]equity ratio\b",
    r"\bdebt equity ratio\b",
)

ADMINISTRATIVE_DOCUMENT_NAMES = (
    "pan.pdf",
    "gst.pdf",
    "gstin.pdf",
    "cin.pdf",
    "incorporation_certificate.pdf",
    "incorporation certificate.pdf",
)

FOUNDER_LEGAL_NOISE_PATTERNS = (
    r"\bcollectively referred to as the founders?\b",
    r"\bindividually referred to as a founder\b",
    r"\bfounder\s*[123]\b",
    r"\bbad leaver\b",
    r"\bgood leaver\b",
)

REAL_FOUNDER_CONTEXT_PATTERNS = (
    r"\b(?:founder|co-founder|promoter)\b.{0,120}"
    r"\b(?:ceo|chief executive officer|cto|cfo|coo|director|md|managing director)\b",
    r"\b(?:founder|co-founder|promoter)\b.{0,160}"
    r"\b(?:years?|experience|worked|career|education|degree|background)\b",
    r"\b(?:ceo|chief executive officer|cto|cfo|coo|director|md|managing director)\b.{0,120}"
    r"\b(?:founder|co-founder|promoter)\b",
)

def source_filename(candidate: dict[str, Any]) -> str:
    return Path(str(candidate.get("source_path", ""))).name.lower()


def administrative_document(candidate: dict[str, Any]) -> bool:
    return source_filename(candidate) in ADMINISTRATIVE_DOCUMENT_NAMES


def founder_legal_noise(text: str) -> bool:
    return matches_any(text, FOUNDER_LEGAL_NOISE_PATTERNS)


def explicit_real_founder_context(text: str) -> bool:
    return matches_any(text, REAL_FOUNDER_CONTEXT_PATTERNS)

# ---------------------------------------------------------------------------
# Gate implementation
# ---------------------------------------------------------------------------

class GateDecision:
    def __init__(
        self,
        passed: bool,
        stage: str,
        rule: str,
        reason: str,
    ) -> None:
        self.passed = passed
        self.stage = stage
        self.rule = rule
        self.reason = reason

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "stage": self.stage,
            "rule": self.rule,
            "reason": self.reason,
        }


def gate_basic(text: str, min_chars: int) -> GateDecision | None:
    x = normalize(text)

    if len(x) < min_chars:
        return GateDecision(
            False,
            "basic_structure",
            "too_short",
            f"Candidate is shorter than {min_chars} characters.",
        )

    if word_count(x) < 5:
        return GateDecision(
            False,
            "basic_structure",
            "too_few_words",
            "Candidate contains too little textual context.",
        )

    if PAGE_RE.fullmatch(x):
        return GateDecision(
            False,
            "basic_structure",
            "page_marker",
            "Candidate is only a page marker.",
        )

    # Formula-only or formula-dominated fragments.
    if FORMULA_RE.fullmatch(x) or (formula_ratio(x) > 0.015 and not has_number(x)):
        return GateDecision(
            False,
            "basic_structure",
            "formula_only",
            "Candidate is formula-only or formula-dominated without a resolved metric.",
        )

    # Obvious repeated document noise.
    if matches_any(x, REPEATED_NOISE_PATTERNS) and word_count(x) < 15:
        return GateDecision(
            False,
            "basic_structure",
            "document_noise",
            "Candidate is dominated by repeated document/header noise.",
        )

    return None


def gate_negative(
    text: str,
    dimension: str,
    field: str,
    candidate: dict[str, Any] | None = None,
) -> GateDecision | None:
    x = lower(text)
    candidate = candidate or {}

    # Administrative identity documents are not commercial/financial evidence.
    if administrative_document(candidate) and dimension in {
        "commercial_traction",
        "financial_health",
        "unit_economics_margins",
        "market_tam",
        "product_pmf",
        "technology_ip_moat",
        "risk_exit_potential",
    }:
        return GateDecision(
            False,
            "negative_pattern",
            "administrative_document_not_investment_evidence",
            "Administrative identity document is not a valid source for this investment-evidence dimension.",
        )

    # Accounting ratios are not working-capital risk evidence by themselves.
    if field == "working_capital" and matches_any(x, ACCOUNTING_RATIO_PATTERNS):
        if not matches_any(
            x,
            (
                r"working capital risk",
                r"liquidity risk",
                r"inventory risk",
                r"cash conversion cycle",
                r"working capital requirement",
                r"working capital shortage",
                r"working capital pressure",
            ),
        ):
            return GateDecision(
                False,
                "negative_pattern",
                "accounting_ratio_not_working_capital_risk",
                "Accounting turnover/ratio text is not itself working-capital risk evidence.",
            )

    # Accounting policy is one of the highest-value false-positive classes.
    if matches_any(x, ACCOUNTING_POLICY_PATTERNS):
        # Preserve an actual metric sentence that happens to mention accounting.
        metric_fields = {
            "revenue",
            "gross_profit",
            "ebitda",
            "profit_loss",
            "cash_burn",
            "expenses",
        }
        if field in metric_fields and (has_money(x) or has_percent(x)):
            pass
        else:
            return GateDecision(
                False,
                "negative_pattern",
                "accounting_policy_without_metric",
                "Accounting-policy language is present without a concrete financial metric.",
            )

    # "Orders" in audited/legal documents often means court/regulatory orders.
    if field == "orders" and matches_any(x, LEGAL_ORDER_PATTERNS):
        return GateDecision(
            False,
            "negative_pattern",
            "legal_order_context",
            "The order-related text is associated with legal, court, tribunal, or regulatory context.",
        )

    # Administrative identity noise.
    admin_hits = []
    for name, patterns in ADMIN_PATTERNS.items():
        if matches_any(x, patterns):
            admin_hits.append(name)

    if admin_hits:
        if dimension not in {"governance_cap_table", "valuation_deal_terms"}:
            return GateDecision(
                False,
                "negative_pattern",
                "administrative_noise",
                "Candidate contains administrative/corporate identity text: "
                + ", ".join(admin_hits),
            )

    # Generic legal boilerplate is not investment evidence by itself.
    if matches_any(x, LEGAL_BOILERPLATE_PATTERNS):
        governance_anchor = matches_any(
            x,
            (
                r"\bboard\b",
                r"\bvoting rights?\b",
                r"\breserved matters?\b",
                r"\bshareholding\b",
                r"\binvestor consent\b",
                r"\bshareholder approval\b",
            ),
        )
        if not governance_anchor:
            return GateDecision(
                False,
                "negative_pattern",
                "legal_boilerplate",
                "Candidate is dominated by generic legal boilerplate.",
            )

    # Generic headings/labels.
    if HEADING_ONLY_RE.fullmatch(x) and not has_number(x):
        if field not in {
            "shareholding",
            "board_rights",
            "reserved_matters",
            "voting_rights",
            "instrument",
        }:
            return GateDecision(
                False,
                "negative_pattern",
                "heading_or_label_only",
                "Candidate appears to be a heading or label rather than a factual statement.",
            )

    return None


def field_patterns(dimension: str, field: str) -> tuple[str, ...]:
    tables = {
        "financial_health": FINANCIAL_FIELDS,
        "commercial_traction": COMMERCIAL_FIELDS,
        "unit_economics_margins": UNIT_FIELDS,
        "market_tam": MARKET_FIELDS,
        "technology_ip_moat": TECH_FIELDS,
        "governance_cap_table": GOVERNANCE_FIELDS,
        "valuation_deal_terms": VALUATION_FIELDS,
        "risk_exit_potential": RISK_FIELDS,
    }
    return tuple(tables.get(dimension, {}).get(field, ()))


def gate_financial(field: str, x: str) -> GateDecision | None:
    if field in {
        "revenue",
        "gross_profit",
        "ebitda",
        "profit_loss",
        "expenses",
        "cash_burn",
    }:
        if not (has_number(x) or has_money(x) or has_percent(x)):
            return GateDecision(
                False,
                "field_specific",
                "financial_metric_without_value",
                "Financial metric is present but no quantified value, percentage, or period anchor was found.",
            )

    if field == "profit_loss":
        if not matches_any(
            x,
            (
                r"\bnet profit\b",
                r"\bnet loss\b",
                r"\bprofit after tax\b",
                r"\bloss after tax\b",
                r"\bpat\b",
                r"\bpbt\b",
                r"\bebitda\b",
                r"\bebit\b",
            ),
        ) and not has_money(x):
            return GateDecision(
                False,
                "field_specific",
                "weak_profit_loss_structure",
                "Profit/loss candidate lacks a strong profitability metric.",
            )

    return None


def gate_commercial(field: str, x: str) -> GateDecision | None:
    if field == "customers":
        meaningful = (
            has_number(x)
            or has_percent(x)
            or matches_any(
                x,
                (
                    r"\bactive customers?\b",
                    r"\bpaying customers?\b",
                    r"\brepeat customers?\b",
                    r"\bmonthly customers?\b",
                    r"\bserved \d+\b",
                    r"\bserving \d+\b",
                ),
            )
        )
        if not meaningful:
            return GateDecision(
                False,
                "field_specific",
                "weak_customer_context",
                "Customer keyword is present without a quantified or explicit traction context.",
            )

    elif field == "orders":
        if not (
            has_number(x)
            or matches_any(
                x,
                (
                    r"\borders? processed\b",
                    r"\borders? fulfilled\b",
                    r"\bcustomer orders?\b",
                    r"\border volume\b",
                    r"\borders? per (?:month|year|day)\b",
                ),
            )
        ):
            return GateDecision(
                False,
                "field_specific",
                "weak_order_context",
                "Order candidate lacks a quantified or explicit commercial-order context.",
            )

    elif field == "gmv":
        if not (has_money(x) or has_number(x)):
            return GateDecision(
                False,
                "field_specific",
                "gmv_without_value",
                "GMV candidate lacks a quantified value.",
            )

    elif field == "monthly_revenue":
        if not (has_money(x) or has_number(x)):
            return GateDecision(
                False,
                "field_specific",
                "monthly_revenue_without_value",
                "Monthly revenue candidate lacks a quantified value.",
            )

    elif field == "growth":
        if not (has_percent(x) or has_number(x)):
            return GateDecision(
                False,
                "field_specific",
                "growth_without_quantification",
                "Growth candidate lacks a numeric or percentage anchor.",
            )

    elif field == "recurring_revenue":
        if not (has_money(x) or has_number(x) or has_period(x)):
            return GateDecision(
                False,
                "field_specific",
                "recurring_revenue_without_metric",
                "Recurring-revenue candidate lacks a value or time anchor.",
            )

    elif field == "repeat":
        if not (
            has_number(x)
            or has_percent(x)
            or matches_any(x, (r"\brepeat rate\b", r"\bretention rate\b", r"\brenewal rate\b"))
        ):
            return GateDecision(
                False,
                "field_specific",
                "weak_repeat_context",
                "Repeat/retention candidate lacks a quantified or explicit rate/context.",
            )

    return None


def gate_unit(field: str, x: str) -> GateDecision | None:
    if not (has_money(x) or has_number(x) or has_percent(x) or has_period(x)):
        return GateDecision(
            False,
            "field_specific",
            "unit_metric_without_value",
            "Unit-economics candidate lacks a value, percentage, or time anchor.",
        )

    # Resolved business metrics are preferred over spreadsheet formulas.
    if formula_ratio(x) > 0.01 and not (
        re.search(r"\b(?:cac|ltv|margin|payback|cost)\b\s*(?:=|is|:)", x, re.I)
    ):
        return GateDecision(
            False,
            "field_specific",
            "unresolved_formula_fragment",
            "Unit-economics candidate appears to contain an unresolved spreadsheet formula.",
        )

    return None


def gate_market(field: str, x: str) -> GateDecision | None:
    if field in {"market_size", "market_growth"}:
        if not (
            has_money(x)
            or has_number(x)
            or has_percent(x)
            or matches_any(x, (r"\bbillion\b", r"\bmillion\b", r"\bcagr\b"))
        ):
            return GateDecision(
                False,
                "field_specific",
                "market_without_quantification",
                "Market candidate lacks a size, growth, percentage, or numeric anchor.",
            )

    elif field == "target_customers":
        if not (
            has_number(x)
            or matches_any(
                x,
                (
                    r"\bindependent restaurants?\b",
                    r"\brestaurant operators?\b",
                    r"\bcloud kitchens?\b",
                    r"\bfood service\b",
                    r"\brestaurant chains?\b",
                ),
            )
        ):
            return GateDecision(
                False,
                "field_specific",
                "weak_target_customer_context",
                "Target-customer candidate lacks a quantified population or explicit customer segment.",
            )

    return None


def gate_technology(field: str, x: str) -> GateDecision | None:
    if field == "patent_ip":
        if not matches_any(x, (r"\bpatent\b", r"\bintellectual property\b", r"\bip portfolio\b")):
            return GateDecision(
                False,
                "field_specific",
                "weak_ip_context",
                "IP candidate lacks an explicit patent/IP anchor.",
            )

    elif field in {"ai_ml", "algorithm", "proprietary_technology", "platform_architecture"}:
        technical_capability = matches_any(
            x,
            (
                r"\bpredict(?:ion|ive)?\b",
                r"\bforecast(?:ing)?\b",
                r"\baccuracy\b",
                r"\bautomated?\b",
                r"\bautomation\b",
                r"\boptimi[sz](?:e|ation)\b",
                r"\barchitecture\b",
                r"\bplatform\b",
                r"\bsoftware\b",
                r"\bmodel\b",
                r"\bengine\b",
                r"\balgorithm\b",
            ),
        )

        if field == "proprietary_technology":
            explicit = matches_any(
                x,
                (r"\bproprietary technology\b", r"\bproprietary platform\b", r"\bproprietary software\b"),
            )
            if not (explicit or technical_capability):
                return GateDecision(
                    False,
                    "field_specific",
                    "technology_without_capability",
                    "Technology candidate lacks an explicit technical capability or differentiation.",
                )

        elif field in {"ai_ml", "algorithm", "platform_architecture"} and not technical_capability:
            return GateDecision(
                False,
                "field_specific",
                "technology_without_capability",
                "Technical keyword is present without a capability, function, architecture, or measurable technical context.",
            )

    return None


def gate_governance(field: str, x: str) -> GateDecision | None:
    if field == "shareholding":
        if not (
            has_percent(x)
            or has_number(x)
            or matches_any(x, (r"\bheld by\b", r"\bowned by\b", r"\bownership\b"))
        ):
            return GateDecision(
                False,
                "field_specific",
                "shareholding_without_structure",
                "Shareholding candidate lacks ownership, share-count, or percentage structure.",
            )

    elif field == "board_rights":
        if not matches_any(
            x,
            (
                r"\bboard\b.{0,160}\b(?:right|appointment|nominate|seat|consent)\b",
                r"\bdirector\b.{0,160}\b(?:appointment|nominate|seat|consent)\b",
                r"\bboard observer\b",
                r"\bobserver right\b",
            ),
        ):
            return GateDecision(
                False,
                "field_specific",
                "weak_board_rights_context",
                "Board/director candidate lacks an appointment, nomination, observer, seat, right, or consent context.",
            )

    elif field == "reserved_matters":
        if not matches_any(
            x,
            (
                r"\breserved matters?\b",
                r"\binvestor consent\b",
                r"\bprior consent\b",
                r"\bshareholder approval\b",
                r"\baffirmative vote\b",
            ),
        ):
            return GateDecision(
                False,
                "field_specific",
                "weak_reserved_matters_context",
                "Reserved-matters candidate lacks an explicit consent/approval/control anchor.",
            )

    elif field == "voting_rights":
        if not matches_any(
            x,
            (
                r"\bvoting rights?\b",
                r"\bvoting\b.{0,120}\b(?:shares?|holder|investor|rights?)\b",
                r"\bvote\b.{0,120}\b(?:shares?|holder|investor|rights?)\b",
            ),
        ):
            return GateDecision(
                False,
                "field_specific",
                "weak_voting_context",
                "Voting candidate lacks an explicit voting-rights context.",
            )

    return None


def gate_valuation(field: str, x: str) -> GateDecision | None:
    if field in {"valuation", "round_size", "issue_price"}:
        if not has_money(x):
            return GateDecision(
                False,
                "field_specific",
                "financing_term_without_amount",
                "Financing candidate lacks a monetary value.",
            )

    elif field == "instrument":
        financing_context = matches_any(
            x,
            (
                r"\binvest(?:ment|or)\b",
                r"\bsubscription\b",
                r"\bissue\b",
                r"\bround\b",
                r"\braising\b",
                r"\bfundrais(?:e|ing)\b",
                r"\bconvertible\b",
            ),
        )
        instrument = matches_any(
            x,
            (
                r"\bccps\b",
                r"\bpreference shares?\b",
                r"\bconvertible\b",
                r"\bequity shares?\b",
                r"\bdebenture\b",
            ),
        )

        if not (instrument and financing_context):
            return GateDecision(
                False,
                "field_specific",
                "instrument_without_financing_context",
                "Instrument keyword is present without an explicit financing/subscription/issue context.",
            )

    return None


def gate_risk(field: str, x: str) -> GateDecision | None:
    if field == "risk":
        explicit = matches_any(
            x,
            (
                r"\brisk factor\b",
                r"\brisk factors\b",
                r"\bkey risk\b",
                r"\bmajor risk\b",
                r"\bconcentration risk\b",
                r"\bregulatory risk\b",
                r"\bexecution risk\b",
                r"\bliquidity risk\b",
            ),
        )
        quantified = has_percent(x) or has_money(x) or has_number(x)
        if not (explicit and (quantified or word_count(x) >= 12)):
            return GateDecision(
                False,
                "field_specific",
                "weak_risk_statement",
                "Risk candidate lacks explicit risk framing with sufficient supporting context.",
            )

    elif field == "concentration":
        if not (
            has_percent(x)
            and matches_any(x, (r"\bcustomer\b", r"\bsupplier\b", r"\brevenue\b"))
        ):
            return GateDecision(
                False,
                "field_specific",
                "concentration_without_metric",
                "Concentration candidate lacks customer/supplier/revenue context with a percentage.",
            )

    elif field == "working_capital":
        if not (
            has_money(x)
            or has_number(x)
            or matches_any(x, (r"\bcash conversion\b", r"\binventory risk\b", r"\bliquidity risk\b"))
        ):
            return GateDecision(
                False,
                "field_specific",
                "working_capital_without_metric",
                "Working-capital candidate lacks a quantified or explicit risk/cycle context.",
            )

    elif field == "exit_liquidity":
        if not matches_any(
            x,
            (
                r"\bexit\b.{0,160}\b(?:investor|shareholder|liquidity|proceeds)\b",
                r"\bliquidity\b.{0,160}\b(?:investor|shareholder|exit)\b",
                r"\bbuyback\b",
                r"\bdrag[- ]along\b",
                r"\btag[- ]along\b",
                r"\bput option\b",
                r"\bredemption\b",
            ),
        ):
            return GateDecision(
                False,
                "field_specific",
                "weak_exit_liquidity_context",
                "Exit/liquidity candidate lacks an explicit investor/shareholder mechanism.",
            )

    return None


def gate_field_specific(
    dimension: str,
    field: str,
    text: str,
    candidate: dict[str, Any] | None = None,
) -> GateDecision | None:
    x = lower(text)

    if dimension == "financial_health":
        return gate_financial(field, x)

    if dimension == "commercial_traction":
        return gate_commercial(field, x)

    if dimension == "unit_economics_margins":
        return gate_unit(field, x)

    if dimension == "market_tam":
        return gate_market(field, x)

    if dimension == "technology_ip_moat":
        return gate_technology(field, x)

    if dimension == "governance_cap_table":
        return gate_governance(field, x)

    if dimension == "valuation_deal_terms":
        return gate_valuation(field, x)

    if dimension == "risk_exit_potential":
        return gate_risk(field, x)

    if dimension == "founder_team":
        # Legal SHA/template references to "Founder" are not founder profiles.
        if founder_legal_noise(text) and not explicit_real_founder_context(text):
            return GateDecision(
                False,
                "negative_pattern",
                "founder_legal_boilerplate",
                "Founder keyword appears in legal/template language without identifiable founder profile context.",
            )

        if field == "founder_identity":
            if not has_named_person_shape(text):
                return GateDecision(
                    False,
                    "field_specific",
                    "founder_without_identity",
                    "Founder candidate lacks a likely person-name or identifiable founder context.",
                )
        elif field in {"founder_role", "founder_background"}:
            if not has_named_person_shape(text):
                return GateDecision(
                    False,
                    "field_specific",
                    "founder_without_identity",
                    "Founder role/background candidate lacks identifiable founder context.",
                )

    if dimension == "product_pmf":
        if field == "product_capability":
            capability = matches_any(
                x,
                (
                    r"\bplatform\b",
                    r"\bsolution\b",
                    r"\bmarketplace\b",
                    r"\bprocurement\b",
                    r"\bapplication\b",
                    r"\bservice\b",
                ),
            )
            action = matches_any(
                x,
                (
                    r"\bprovide\b",
                    r"\benable\b",
                    r"\bautomate\b",
                    r"\bdeliver\b",
                    r"\bpredict\b",
                    r"\bmanage\b",
                    r"\bconnect\b",
                    r"\bsource\b",
                    r"\bprocure\b",
                ),
            )
            if not (capability and action):
                return GateDecision(
                    False,
                    "field_specific",
                    "product_without_capability",
                    "Product candidate lacks a clear product/service capability.",
                )

        elif field == "adoption_usage":
            if not (
                has_number(x)
                or has_percent(x)
                or matches_any(
                    x,
                    (
                        r"\bactive users?\b",
                        r"\badopted\b",
                        r"\bused by\b",
                        r"\bretention\b",
                        r"\bengagement\b",
                    ),
                )
            ):
                return GateDecision(
                    False,
                    "field_specific",
                    "adoption_without_usage_anchor",
                    "Adoption/usage candidate lacks a quantified or explicit usage anchor.",
                )

        elif field == "customer_problem":
            if not matches_any(
                x,
                (
                    r"\bproblem\b",
                    r"\bpain point\b",
                    r"\bstockout\b",
                    r"\bwastage\b",
                    r"\bprocurement challenge\b",
                    r"\bcustomer need\b",
                    r"\bfragmented\b",
                    r"\bmanual\b",
                ),
            ):
                return GateDecision(
                    False,
                    "field_specific",
                    "problem_without_problem_context",
                    "Product-problem candidate lacks explicit problem language.",
                )

    # If a field has no dedicated rule, retain it conservatively after the
    # generic checks rather than silently inventing a semantic judgment.
    return None


def gate_candidate(candidate: dict[str, Any], min_chars: int) -> GateDecision:
    # V3.3-A.1.2: surgical working-capital refinement.
    wc_decision = gate_working_capital_a1_2(candidate)
    if wc_decision is not None:
        return wc_decision

    text = normalize(candidate.get("text", ""))

    decision = gate_basic(text, min_chars)
    if decision:
        return decision

    decision = gate_negative(
        text,
        str(candidate.get("dimension", "")),
        str(candidate.get("field", "")),
        candidate,
    )
    if decision:
        return decision

    decision = gate_field_specific(
        str(candidate.get("dimension", "")),
        str(candidate.get("field", "")),
        text,
        candidate,
    )
    if decision:
        return decision

    decision = a1_anchor_gate(candidate)
    if decision:
        return decision

    return GateDecision(
        True,
        "final",
        "structurally_qualified",
        "Candidate passed generic, negative-pattern, field-specific, and anchor/context structural checks.",
    )


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def load_candidates(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise ValueError("Input JSON root must be an object.")

    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("Input JSON does not contain a 'candidates' list.")

    return payload, candidates


def build_report(
    source_payload: dict[str, Any],
    candidates: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    elapsed_sec: float,
    min_chars: int,
) -> dict[str, Any]:
    raw_count = len(candidates)
    passed = [x for x in decisions if x["gate"]["passed"]]
    rejected = [x for x in decisions if not x["gate"]["passed"]]

    dimension_stats: dict[str, dict[str, int]] = {
        d: {"raw": 0, "passed": 0, "rejected": 0}
        for d in DIMENSIONS
    }

    reason_counts: Counter[str] = Counter()
    stage_counts: Counter[str] = Counter()

    for item in decisions:
        dimension = item["dimension"]
        if dimension not in dimension_stats:
            dimension_stats[dimension] = {
                "raw": 0,
                "passed": 0,
                "rejected": 0,
            }

        dimension_stats[dimension]["raw"] += 1
        if item["gate"]["passed"]:
            dimension_stats[dimension]["passed"] += 1
        else:
            dimension_stats[dimension]["rejected"] += 1
            reason_counts[item["gate"]["rule"]] += 1

        stage_counts[item["gate"]["stage"]] += 1

    startup = source_payload.get("startup", {})
    source_input = source_payload.get("input", {})

    return {
        "benchmark": "Qwen2.5-1.5B-Instruct",
        "benchmark_version": BENCHMARK_VERSION,
        "gate_version": GATE_VERSION,
        "benchmark_type": "deterministic_candidate_quality_gate",
        "observational": True,
        "production_pipeline_modified": False,
        "llm_inference_used": False,
        "startup": startup,
        "input": {
            "source_benchmark": source_payload.get("benchmark_version"),
            "source_prompt_version": source_payload.get("prompt_version"),
            "data_root": source_input.get("data_root"),
            "source_root": source_input.get("source_root"),
            "source_count": source_input.get("source_count"),
            "source_extraction_identity": source_input.get(
                "source_extraction_identity"
            ),
        },
        "configuration": {
            "min_candidate_chars": min_chars,
            "gate_stages": [
                "basic_structure",
                "negative_pattern",
                "field_specific",
                "anchor_context",
                "final",
            ],
            "refinements": [
                "administrative_document_filter",
                "accounting_ratio_working_capital_filter",
                "founder_legal_boilerplate_filter",
                "working_capital_formula_artifact_filter",
                "working_capital_ocr_ratio_filter",
            ],
        },
        "population": {
            "raw_candidates": raw_count,
            "gate_passed": len(passed),
            "gate_rejected": len(rejected),
            "pass_rate": (len(passed) / raw_count) if raw_count else 0.0,
            "reduction": (
                (len(rejected) / raw_count) if raw_count else 0.0
            ),
        },
        "dimension_statistics": dimension_stats,
        "rejection_reasons": dict(reason_counts),
        "gate_stage_statistics": dict(stage_counts),
        "timing": {
            "gate_execution_sec": elapsed_sec,
            "average_gate_sec": elapsed_sec / raw_count if raw_count else 0.0,
        },
        "candidates": decisions,
    }


def main() -> int:
    args = parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if args.min_chars <= 0:
        print("ERROR: --min-chars must be > 0")
        return 1

    if args.max_candidates < 0:
        print("ERROR: --max-candidates must be >= 0")
        return 1

    if not input_path.is_file():
        print(f"ERROR: input file not found: {input_path}")
        return 2

    try:
        source_payload, raw_candidates = load_candidates(input_path)
    except Exception as exc:
        print(f"ERROR: failed to load input: {type(exc).__name__}: {exc}")
        return 2

    candidates = raw_candidates
    if args.max_candidates > 0:
        candidates = candidates[: args.max_candidates]

    print("=" * 100)
    print("V3.3-A.1.2 DETERMINISTIC CANDIDATE QUALITY GATE")
    print("=" * 100)
    print(f"INPUT              : {input_path}")
    print(f"OUTPUT             : {output_path}")
    print(f"STARTUP            : {source_payload.get('startup', {}).get('name', '')}")
    print(f"BENCHMARK INPUT    : {source_payload.get('benchmark_version', '')}")
    print(f"RAW CANDIDATES     : {len(candidates)}")
    print(f"MIN CANDIDATE CHARS: {args.min_chars}")
    print("LLM INFERENCE      : NONE")
    print("PRODUCTION CHANGES : NONE")
    print()
    print("=" * 100)
    print("QUALITY GATE")
    print("=" * 100)

    decisions: list[dict[str, Any]] = []
    start = time.perf_counter()

    for index, candidate in enumerate(candidates, 1):
        decision = gate_candidate(candidate, args.min_chars)

        item = dict(candidate)
        item["gate"] = decision.as_dict()
        item["gate"]["candidate_index"] = index
        item["gate"]["v3_3_a1_1_features"] = {
            "source_filename": source_filename(candidate),
            "administrative_document": administrative_document(candidate),
            "accounting_ratio_context": matches_any(
                normalize(candidate.get("text", "")),
                ACCOUNTING_RATIO_PATTERNS,
            ),
            "founder_legal_noise": founder_legal_noise(
                normalize(candidate.get("text", ""))
            ),
        }
        normalized_candidate_text = normalize(candidate.get("text", ""))
        item["gate"]["working_capital_a1_2_features"] = {
            "applicable": str(candidate.get("field", "")).strip() == "working_capital",
            "accounting_ratio": working_capital_accounting_ratio(normalized_candidate_text),
            "explicit_context": working_capital_explicit_context(normalized_candidate_text),
            "explicit_risk_context": working_capital_risk_context(normalized_candidate_text),
            "formula_driven": candidate_formula_driven(candidate),
            "resolved_value": candidate_has_resolved_numeric_value(candidate),
        }
        decisions.append(item)

        status = "PASS" if decision.passed else "REJECT"
        print(
            f"[{index:04d}/{len(candidates):04d}] "
            f"{status:6s} "
            f"{str(candidate.get('dimension', '')):28s} "
            f"{str(candidate.get('field', '')):24s} "
            f"{decision.rule:40s}"
        )

    elapsed = time.perf_counter() - start

    report = build_report(
        source_payload,
        candidates,
        decisions,
        elapsed,
        args.min_chars,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    tmp_path.replace(output_path)

    population = report["population"]

    print()
    print("=" * 100)
    print("V3.3-A.1.2 SUMMARY")
    print("=" * 100)
    print(f"Raw candidates       : {population['raw_candidates']}")
    print(f"Gate passed          : {population['gate_passed']}")
    print(f"Gate rejected        : {population['gate_rejected']}")
    print(f"Pass rate            : {population['pass_rate'] * 100:.1f}%")
    print(f"Reduction            : {population['reduction'] * 100:.1f}%")
    print(f"Gate execution       : {elapsed:.3f} sec")
    print(f"Average/candidate    : {report['timing']['average_gate_sec']:.6f} sec")
    print()
    print("DIMENSION RESULTS")
    for dimension in DIMENSIONS:
        stats = report["dimension_statistics"][dimension]
        print(
            f"  {dimension:28s}: "
            f"{stats['raw']:4d} raw, "
            f"{stats['passed']:4d} pass, "
            f"{stats['rejected']:4d} reject"
        )

    print()
    print("TOP REJECTION REASONS")
    for reason, count in sorted(
        report["rejection_reasons"].items(),
        key=lambda item: (-item[1], item[0]),
    ):
        print(f"  {count:4d}  {reason}")

    print()
    print(f"OUTPUT              : {output_path}")
    print("STATUS              : PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
