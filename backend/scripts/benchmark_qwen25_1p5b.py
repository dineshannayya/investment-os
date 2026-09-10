#!/usr/bin/env python3
"""Qwen2.5-1.5B-Instruct Q4_K_M — V3.2 Candidate Generation + Semantic Validation.

Experimental benchmark only. Production signals/evidence/scoring are untouched.

Pipeline:
  canonical current extractions
    -> deterministic cleaning
    -> deterministic field-specific candidate generation
    -> Qwen semantic validation of each candidate
    -> Python-owned observation/support/provenance/dedup
    -> benchmark JSON

The LLM does NOT discover evidence. Python proposes a candidate and field; the
LLM only answers whether the supplied text explicitly supports that field.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
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

from app.core.database.session import create_session
from app.services.source_discovery import SourceDiscoveryService
from app.services.source_extraction_persistence import SourceExtractionPersistenceService
from app.services.startup import StartupService

MODEL_PATH = Path("/models/Qwen2.5-1.5B-Instruct/qwen2.5-1.5b-instruct-q4_k_m.gguf")
N_THREADS = 8
N_THREADS_BATCH = 8
N_CTX = 4096
N_GPU_LAYERS = 0
TEMPERATURE = 0.0
TOP_P = 1.0
MAX_TOKENS = 96
SEED = 42
BENCHMARK_VERSION = "V3.2"
PROMPT_VERSION = "candidate-semantic-validation-v1"
DEFAULT_DATA_ROOT = Path("/opt/investment-os/data/real_startups")
DEFAULT_GENERATED_ROOT = Path("/opt/investment-os/generated")
DEFAULT_CONTEXT_CHARS = 700
DEFAULT_MIN_CANDIDATE_CHARS = 35
DEFAULT_MAX_CANDIDATES = 0

DIMENSIONS = (
    "founder_team", "market_tam", "product_pmf", "technology_ip_moat",
    "commercial_traction", "unit_economics_margins", "financial_health",
    "governance_cap_table", "valuation_deal_terms", "risk_exit_potential",
)

FIELD_DEFINITIONS = {
    "founder_team": "Founder/team identity, role, background, experience, ownership or team structure.",
    "market_tam": "Market size, TAM/SAM/SOM, target customers, addressable opportunity, geography or market growth.",
    "product_pmf": "Product/service capability, customer problem, adoption, usage, retention, engagement or product fit.",
    "technology_ip_moat": "Explicit proprietary technology, software, architecture, AI/ML, algorithm, IP, patents or technical differentiation.",
    "commercial_traction": "Revenue, sales, customers, orders, GMV, AOV, growth, repeat business or operating traction.",
    "unit_economics_margins": "CAC, LTV, gross/contribution margin, payback or revenue/cost per customer/order/transaction.",
    "financial_health": "Revenue/profitability, gross profit, EBITDA, expenses, cash, burn, liquidity or financial trends.",
    "governance_cap_table": "Cap table, shareholding, board/observer rights, reserved matters, voting, investor/control or information rights.",
    "valuation_deal_terms": "Round size, valuation, issue price, instrument, conversion, dilution, anti-dilution, subscription or financing terms.",
    "risk_exit_potential": "Explicit risk, concentration, churn, negative economics, execution/working-capital risk or exit/liquidity mechanisms.",
}

ROUTE_BY_KIND = {
    "legal": ("founder_team", "governance_cap_table", "valuation_deal_terms", "risk_exit_potential"),
    "financial": ("commercial_traction", "unit_economics_margins", "financial_health", "valuation_deal_terms", "risk_exit_potential"),
    "product_tech": ("market_tam", "product_pmf", "technology_ip_moat", "commercial_traction", "unit_economics_margins", "risk_exit_potential"),
    "founder": ("founder_team",),
    "market": ("market_tam", "product_pmf", "commercial_traction", "technology_ip_moat"),
    "pitch": DIMENSIONS,
    "general": DIMENSIONS,
}

# Candidate signals are intentionally narrower than the old V3.1 extraction prompt.
# Each entry is (dimension, field, regex). Regexes identify a local region only;
# semantic acceptance remains the LLM's job.
SIGNALS = [
    ("valuation_deal_terms", "valuation", r"\b(?:pre[- ]money|post[- ]money)?\s*valuation\b|\bvaluation\b"),
    ("valuation_deal_terms", "round_size", r"\b(?:round size|round|fundraise|raising|raise|investment)\b.{0,100}(?:₹|rs\.?|inr|\$|usd)\s*[\d,.]+|(?:₹|rs\.?|inr|\$|usd)\s*[\d,.]+.{0,100}\b(?:round|fundraise|raising|raise|investment)\b"),
    ("valuation_deal_terms", "issue_price", r"\b(?:issue price|subscription price|price per share)\b"),
    ("valuation_deal_terms", "instrument", r"\b(?:ccps|ccps?|equity shares?|convertible|debenture|preference shares?)\b"),
    ("governance_cap_table", "shareholding", r"\b(?:shareholding|shareholders?|cap table|equity holding|ownership)\b"),
    ("governance_cap_table", "board_rights", r"\b(?:board|director|observer|board observer)\b.{0,160}\b(?:right|appointment|nominate|seat|consent)\b"),
    ("governance_cap_table", "reserved_matters", r"\b(?:reserved matters?|affirmative vote|consent matters?|investor consent)\b"),
    ("governance_cap_table", "voting_rights", r"\b(?:voting rights?|vote|voting)\b.{0,100}\b(?:shares?|investor|holder|rights?)\b"),
    ("founder_team", "founder_identity", r"\b(?:founder|co-founder|promoter)\b"),
    ("founder_team", "founder_role", r"\b(?:founder|co-founder)\b.{0,80}\b(?:ceo|cto|cfo|director|chief|head)\b"),
    ("founder_team", "founder_background", r"\b(?:founder|co-founder)\b.{0,180}\b(?:experience|years|previously|background|worked|founded)\b"),
    ("financial_health", "revenue", r"\b(?:revenue|sales|turnover|net sales)\b"),
    ("financial_health", "gross_profit", r"\b(?:gross profit|gross margin)\b"),
    ("financial_health", "ebitda", r"\b(?:ebitda|ebit)\b"),
    ("financial_health", "profit_loss", r"\b(?:net profit|net loss|profit after tax|loss after tax|pbt|pat|profit|loss)\b"),
    ("financial_health", "cash_burn", r"\b(?:cash|burn|cash burn|monthly burn|liquidity|working capital)\b"),
    ("financial_health", "expenses", r"\b(?:operating expenses?|opex|expenses?)\b"),
    ("commercial_traction", "customers", r"\b(?:customers?|restaurants?|clients?|accounts?)\b"),
    ("commercial_traction", "orders", r"\b(?:orders?|transactions?|deliveries?)\b"),
    ("commercial_traction", "gmv", r"\b(?:gmv|gross merchandise value)\b"),
    ("commercial_traction", "monthly_revenue", r"\b(?:revenue|sales)\b.{0,60}\b(?:per month|monthly|/month)\b|\b(?:per month|monthly|/month)\b.{0,60}\b(?:revenue|sales)\b"),
    ("commercial_traction", "growth", r"\b(?:growth|grew|grew by|cagr|year[- ]on[- ]year|yoy|mom)\b"),
    ("commercial_traction", "recurring_revenue", r"\b(?:mrr|arr|annual recurring revenue|monthly recurring revenue)\b"),
    ("commercial_traction", "repeat", r"\b(?:repeat|retention|renewal|churn)\b"),
    ("unit_economics_margins", "cac", r"\b(?:cac|customer acquisition cost)\b"),
    ("unit_economics_margins", "ltv", r"\b(?:ltv|lifetime value|customer lifetime value)\b"),
    ("unit_economics_margins", "margin", r"\b(?:gross margin|contribution margin|contribution)\b"),
    ("unit_economics_margins", "payback", r"\b(?:payback|payback period)\b"),
    ("unit_economics_margins", "unit_cost", r"\b(?:cost per order|cost per customer|fulfillment cost|delivery cost|transaction cost)\b"),
    ("market_tam", "market_size", r"\b(?:tam|sam|som|market size|market opportunity|addressable market)\b"),
    ("market_tam", "market_growth", r"\b(?:market growth|market grew|cagr|growth rate)\b"),
    ("market_tam", "target_customers", r"\b(?:restaurants?|target customers?|addressable customers?|potential customers?)\b"),
    ("technology_ip_moat", "proprietary_technology", r"\b(?:proprietary technology|proprietary platform|proprietary software)\b"),
    ("technology_ip_moat", "ai_ml", r"\b(?:ai|artificial intelligence|machine learning|ml model|deep learning)\b"),
    ("technology_ip_moat", "algorithm", r"\b(?:algorithm|prediction model|predictive model|computer vision|optimization engine)\b"),
    ("technology_ip_moat", "patent_ip", r"\b(?:patent|patents|intellectual property|ip portfolio)\b"),
    ("technology_ip_moat", "platform_architecture", r"\b(?:platform architecture|technical architecture|software architecture|technology stack)\b"),
    ("product_pmf", "product_capability", r"\b(?:platform|product|solution|service|procurement|marketplace|application|app)\b"),
    ("product_pmf", "adoption_usage", r"\b(?:adoption|usage|active users?|engagement|retention|customers? using|orders?)\b"),
    ("product_pmf", "customer_problem", r"\b(?:problem|pain point|stockout|wastage|procurement challenge|customer need)\b"),
    ("risk_exit_potential", "risk", r"\b(?:risk|risks|risk factor|risk factors|concern|challenge)\b"),
    ("risk_exit_potential", "concentration", r"\b(?:customer concentration|supplier concentration|concentration risk)\b"),
    ("risk_exit_potential", "working_capital", r"\b(?:working capital|cash conversion|inventory risk|liquidity risk)\b"),
    ("risk_exit_potential", "exit_liquidity", r"\b(?:exit|liquidity|buyback|drag[- ]along|tag[- ]along|put option|redemption)\b"),
]

ADMIN_PATTERNS = (r"\bPAN\b", r"\bGST(?:IN)?\b", r"\bCIN\b", r"\bregistered office\b", r"\bsignature", r"\bwitness", r"\bgovernment of india\b")

@dataclass
class Candidate:
    candidate_id: str
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
    document_kind: str
    dimension: str
    field: str
    text: str
    signal: str
    signal_start: int
    signal_end: int

@dataclass
class ValidationResult:
    candidate_id: str
    source_path: str
    dimension: str
    field: str
    accepted: bool
    json_valid: bool
    reason: str
    latency_sec: float
    input_tokens: int
    output_tokens: int
    generation_tok_per_sec: float | None
    raw_response: str
    error: str | None

SYSTEM_PROMPT = """You are a strict semantic validator for investment evidence.

The Python system has already selected ONE candidate text and ONE proposed field.
Your job is ONLY to decide whether the candidate text explicitly supports that field.

Rules:
1. Accept only explicit, relevant evidence in the supplied text.
2. Reject keyword-only matches, incidental mentions, legal boilerplate, addresses,
   identifiers, labels without a fact, and unrelated references.
3. Do not infer, calculate, or add facts.
4. The candidate may be accepted even if the startup name is absent.
5. A financial metric is valid only when the text actually states the metric/fact;
   a generic occurrence of a word such as revenue, bank, payment or technology is not enough.
6. Return JSON only: {\"accepted\":true/false,\"reason\":\"brief reason\"}.
"""

def parse_args():
    p = argparse.ArgumentParser(description="Qwen2.5-1.5B V3.2 candidate generation + semantic validation benchmark.")
    p.add_argument("--startup", default="restomart")
    p.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    p.add_argument("--output", default=None)
    p.add_argument("--context-chars", type=int, default=DEFAULT_CONTEXT_CHARS)
    p.add_argument("--min-candidate-chars", type=int, default=DEFAULT_MIN_CANDIDATE_CHARS)
    p.add_argument("--max-candidates", type=int, default=DEFAULT_MAX_CANDIDATES)
    return p.parse_args()

def normalize_startup_key(v): return v.strip().lower().replace(" ", "_")

def resolve_startup_directory(data_root, identifier):
    p = data_root / normalize_startup_key(identifier)
    if not p.is_dir(): raise FileNotFoundError(f"Startup directory not found: {p}")
    return p

def resolve_startup(service, identifier):
    try: sid = UUID(identifier.strip())
    except ValueError: sid = None
    if sid:
        obj = service.get_startup(sid)
        if obj is None: raise ValueError(f"Startup not found: {sid}")
        return obj
    key = normalize_startup_key(identifier)
    matches = [x for x in service.list_startups() if normalize_startup_key(x.name) == key]
    if not matches: raise ValueError(f"Startup not found: {identifier}")
    if len(matches) > 1: raise ValueError(f"Multiple startups matched {identifier}")
    return matches[0]

def resolve_current_source_extractions(startup, source_root, discovery, persistence):
    sources = discovery.discover(startup_id=str(startup.id), source_root=source_root)
    records = []
    missing = []
    for source in sources:
        if source.sha256 is None: continue
        record = persistence.get_by_source_version(source_id=source.source_id, source_sha256=source.sha256)
        if record is None: missing.append(source.relative_path)
        else: records.append((source, record))
    if missing: raise RuntimeError("Missing current persisted extractions: " + ", ".join(missing))
    return tuple(records)

def clean_text(v):
    if v is None: return ""
    return str(v).replace("\x00", "").strip()

def segment_text(seg):
    if isinstance(seg, str): return clean_text(seg)
    if not isinstance(seg, dict): return ""
    for k in ("text", "content", "value", "body", "raw_text"):
        x = clean_text(seg.get(k))
        if x: return x
    return ""

def segment_metadata(seg):
    if not isinstance(seg, dict): return {}
    return {k: seg[k] for k in ("id","segment_id","page","page_number","section","heading","type","kind","sheet","row","column","cell") if k in seg}

def classify_document_kind(path, source_type, category):
    v = f"{path} {source_type} {category}".lower()
    if any(x in v for x in ("shareholder","shareholders","sha","aoa","articles","memorandum","mou","agreement","legal","cap_table","cap table")): return "legal"
    if any(x in v for x in ("mis","financial","finance","p&l","profit","loss","balance","cashflow","cash_flow","projection","revenue","ebitda","accounts")) or Path(path).suffix.lower() in {".xlsx",".xls",".csv"}: return "financial"
    if any(x in v for x in ("founder","team","promoter","leadership","profile","resume","cv")): return "founder"
    if any(x in v for x in ("product","technology","tech","architecture","platform","solution","prd","ip","technical")): return "product_tech"
    if any(x in v for x in ("pitch","deck","investor","investment","fundraise","funding","overview","business")): return "pitch"
    if any(x in v for x in ("market","industry","customer","website",".html",".htm")): return "market"
    return "general"

def allowed(kind): return set(ROUTE_BY_KIND.get(kind, DIMENSIONS))

def normalized(v):
    v = v.lower().replace("\u00a0", " ")
    v = re.sub(r"[\u2018\u2019\u201c\u201d]", "'", v)
    v = re.sub(r"\s+", " ", v)
    return v.strip()

def looks_admin(text):
    x = normalized(text)
    if len(x) < 80 and sum(bool(re.search(p, x, re.I)) for p in ADMIN_PATTERNS) >= 2: return True
    if re.fullmatch(r"(?:page|pg)\s+\d+(?:\s+of\s+\d+)?", x, re.I): return True
    return False

def clean_segments(record):
    segs = getattr(record, "segments", None) or []
    out = []
    for i, seg in enumerate(segs):
        text = re.sub(r"[ \t]+", " ", segment_text(seg))
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if text: out.append((i, segment_metadata(seg), text))
    if out: return out
    text = clean_text(getattr(record, "text", ""))
    return [(None, {}, text)] if text else []

def candidate_regions(text, dimension, field, context_chars):
    regions = []
    for d, f, pattern in SIGNALS:
        if d != dimension or f != field: continue
        for m in re.finditer(pattern, text, re.I | re.S):
            start = max(0, m.start() - context_chars)
            end = min(len(text), m.end() + context_chars)
            # Prefer sentence/paragraph boundaries around the raw window.
            left = text.rfind("\n", 0, m.start())
            right = text.find("\n", m.end())
            if left >= 0 and m.start() - left < 350: start = left + 1
            if right >= 0 and right - m.end() < 350: end = right
            regions.append((start, end, m.group(0)))
    return regions

def build_candidates(records, context_chars, min_chars):
    candidates=[]; seen=set(); stats=Counter()
    for source, record in records:
        kind=classify_document_kind(source.relative_path, getattr(source,"source_type","") or "", getattr(source,"category","") or "")
        dims=allowed(kind)
        for idx, meta, text in clean_segments(record):
            stats["segments_seen"] += 1
            for d,f,pattern in SIGNALS:
                if d not in dims: continue
                for m in re.finditer(pattern, text, re.I | re.S):
                    start=max(0,m.start()-context_chars); end=min(len(text),m.end()+context_chars)
                    left=text.rfind("\n",0,m.start()); right=text.find("\n",m.end())
                    if left>=0 and m.start()-left<350: start=left+1
                    if right>=0 and right-m.end()<350: end=right
                    candidate_text=text[start:end].strip()
                    if len(candidate_text)<min_chars: continue
                    if looks_admin(candidate_text) and not d in {"governance_cap_table","valuation_deal_terms"}: continue
                    # Collapse repeated candidates from multiple regex signals in same segment.
                    key=(str(source.source_id),idx,d,f,normalized(candidate_text))
                    if key in seen: continue
                    seen.add(key)
                    cid=hashlib.sha256("|".join(map(str,key)).encode()).hexdigest()[:24]
                    candidates.append(Candidate(
                        cid,str(source.source_id),source.sha256,source.relative_path,
                        getattr(source,"source_type","") or "",getattr(source,"category","") or "",
                        getattr(source,"authority","") or "",str(getattr(record,"extraction_id","")),
getattr(getattr(record,"provenance",None),"method","") or "",
getattr(getattr(record,"provenance",None),"processor_name","") or "",getattr(record,"title",None),getattr(record,"page_count",None),idx,meta,kind,d,f,candidate_text,m.group(0),m.start(),m.end()))
                    stats["raw_candidates"] += 1
    stats["unique_candidates"] = len(candidates)
    return candidates, dict(stats)

def parse_json(raw):
    x=raw.strip()
    if x.startswith("```") and x.endswith("```"):
        lines=x.splitlines(); x="\n".join(lines[1:-1]).strip()
    return json.loads(x)

def validate_response(payload):
    if not isinstance(payload,dict): raise ValueError("root is not object")
    if not isinstance(payload.get("accepted"),bool): raise ValueError("accepted must be boolean")
    reason=payload.get("reason","")
    if not isinstance(reason,str): raise ValueError("reason must be string")
    return payload["accepted"], reason.strip()[:500]

def run_validation(llm, c):
    user=f"FIELD: {c.dimension}\nFIELD DEFINITION: {FIELD_DEFINITIONS[c.dimension]}\nPROPOSED FIELD: {c.field}\nCANDIDATE TEXT:\n<<<\n{c.text}\n>>>\n\nDoes the candidate explicitly support the proposed field?"
    start=time.perf_counter(); raw=""; inp=out=0; rate=None
    try:
        response=llm.create_chat_completion(messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":user}],temperature=TEMPERATURE,top_p=TOP_P,max_tokens=MAX_TOKENS,seed=SEED,response_format={"type":"json_object"})
        raw=str(response["choices"][0]["message"]["content"])
        usage=response.get("usage") or {}; inp=int(usage.get("prompt_tokens") or 0); out=int(usage.get("completion_tokens") or 0)
        timing=(response.get("timings") or {}).get("predicted_ms")
        if timing and out: rate=out/(float(timing)/1000)
        accepted,reason=validate_response(parse_json(raw))
        return ValidationResult(c.candidate_id,c.source_path,c.dimension,c.field,accepted,True,reason,time.perf_counter()-start,inp,out,rate,raw,None)
    except Exception as exc:
        return ValidationResult(c.candidate_id,c.source_path,c.dimension,c.field,False,False,"",time.perf_counter()-start,inp,out,rate,raw,f"{type(exc).__name__}: {exc}")

def evidence_from(c,v):
    eid=hashlib.sha256(f"{c.source_id}|{c.dimension}|{c.field}|{normalized(c.text)}".encode()).hexdigest()[:24]
    return {"evidence_id":eid,"candidate_id":c.candidate_id,"source_id":c.source_id,"source_sha256":c.source_sha256,"source_path":c.source_path,"source_type":c.source_type,"source_category":c.source_category,"source_authority":c.source_authority,"extraction_id":c.extraction_id,"extraction_method":c.extraction_method,"processor_name":c.processor_name,"title":c.title,"page_count":c.page_count,"segment_index":c.segment_index,"segment_metadata":c.segment_metadata,"document_kind":c.document_kind,"dimension":c.dimension,"field":c.field,"observation":c.text,"supporting_text":c.text,"model_accept_reason":v.reason,"grounding_status":"python_candidate_text","model_latency_sec":v.latency_sec,"raw_response":v.raw_response}

def dedup(evs):
    out=[]; seen=set()
    for e in evs:
        k=(e["source_id"],e["dimension"],e["field"],normalized(e["supporting_text"]))
        if k in seen: continue
        seen.add(k); out.append(e)
    return out,len(evs)-len(out)

def main():
    args=parse_args()
    print("="*100); print("QWEN2.5-1.5B-INSTRUCT — V3.2 CANDIDATE GENERATION + SEMANTIC VALIDATION"); print("="*100)
    if not MODEL_PATH.is_file(): print(f"ERROR: model not found: {MODEL_PATH}"); return 2
    if args.context_chars<=0 or args.min_candidate_chars<=0 or args.max_candidates<0: print("ERROR: invalid candidate configuration"); return 1
    try:
        from llama_cpp import Llama,__version__ as llama_cpp_version
    except Exception as exc: print(f"ERROR: llama-cpp-python unavailable: {exc}"); return 2
    data_root=Path(args.data_root); startup_dir=resolve_startup_directory(data_root,args.startup); source_root=startup_dir/"sources"
    session=create_session()
    try:
        startup=resolve_startup(StartupService(session),args.startup)
        output=Path(args.output) if args.output else DEFAULT_GENERATED_ROOT/normalize_startup_key(startup.name)/"benchmark_qwen25_1p5b_v3_2.json"
        if not output.is_absolute(): output=Path.cwd()/output
        print(f"DATA ROOT          : {data_root}\nSTARTUP DIRECTORY  : {startup_dir}\nSOURCE ROOT        : {source_root}\nOUTPUT             : {output}\nPERSISTED STARTUP  : {startup.name}\nCANONICAL UUID     : {startup.id}\nMODEL              : {MODEL_PATH}\nMAX TOKENS         : {MAX_TOKENS}\nCONTEXT CHARS      : {args.context_chars}")
        discovery=SourceDiscoveryService(); persistence=SourceExtractionPersistenceService(session=session)
        records=resolve_current_source_extractions(startup,source_root,discovery,persistence)
        print(f"CURRENT SOURCES    : {len(records)}\nCURRENT EXTRACTS   : {len(records)}")
        t=time.perf_counter(); candidates,candidate_stats=build_candidates(records,args.context_chars,args.min_candidate_chars); clean_time=time.perf_counter()-t
        if args.max_candidates>0: candidates=candidates[:args.max_candidates]
        print(f"CANDIDATES         : {len(candidates)}\nCANDIDATE BUILD    : {clean_time:.3f} sec")
        bydim=Counter(c.dimension for c in candidates); print("CANDIDATES/DIMENSION:"); [print(f"  {d:28s}: {bydim.get(d,0)}") for d in DIMENSIONS]
        load_start=time.perf_counter(); llm=Llama(model_path=str(MODEL_PATH),n_ctx=N_CTX,n_threads=N_THREADS,n_threads_batch=N_THREADS_BATCH,n_gpu_layers=N_GPU_LAYERS,verbose=False); load=time.perf_counter()-load_start
        print(f"MODEL LOAD TIME    : {load:.3f} sec")
        warm=time.perf_counter(); llm.create_chat_completion(messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":"FIELD: unit_economics_margins\nFIELD DEFINITION: CAC or margin metrics.\nPROPOSED FIELD: cac\nCANDIDATE TEXT:\nCustomer acquisition cost (CAC) is INR 500.\nDoes the candidate explicitly support the proposed field?"}],temperature=TEMPERATURE,top_p=TOP_P,max_tokens=MAX_TOKENS,seed=SEED,response_format={"type":"json_object"}); warm=time.perf_counter()-warm
        print(f"WARM-UP TIME       : {warm:.3f} sec\n\n"+"="*100+"\nSEMANTIC VALIDATION\n"+"="*100)
        validations=[]; evidences=[]
        for i,c in enumerate(candidates,1):
            v=run_validation(llm,c); validations.append(v)
            if v.json_valid and v.accepted: evidences.append(evidence_from(c,v))
            print(f"[{i:03d}/{len(candidates)}] {'ACCEPT' if v.accepted and v.json_valid else ('REJECT' if v.json_valid else 'JSON_FAIL')} {v.latency_sec:.2f}s {c.dimension}/{c.field} {c.source_path}")
        unique,dups=dedup(evidences)
        valid=sum(v.json_valid for v in validations); accepted=sum(v.accepted and v.json_valid for v in validations)
        lats=[v.latency_sec for v in validations]
        dimstats={d:{"candidates":0,"accepted":0} for d in DIMENSIONS}
        for c in candidates: dimstats[c.dimension]["candidates"]+=1
        for e in unique: dimstats[e["dimension"]]["accepted"]+=1
        payload={"benchmark":"Qwen2.5-1.5B-Instruct","benchmark_version":BENCHMARK_VERSION,"prompt_version":PROMPT_VERSION,"benchmark_type":"candidate_generation_semantic_validation","observational":True,"production_pipeline_modified":False,"startup":{"id":str(startup.id),"name":startup.name},"input":{"data_root":str(data_root),"source_root":str(source_root),"source_count":len(records),"source_extraction_identity":"source_id + source_sha256","dimensions":list(DIMENSIONS)},"model":{"path":str(MODEL_PATH),"format":"GGUF","quantization":"Q4_K_M","size_bytes":MODEL_PATH.stat().st_size},"runtime":{"python":sys.version,"python_version":platform.python_version(),"platform":platform.platform(),"llama_cpp_python":llama_cpp_version},"configuration":{"threads":N_THREADS,"threads_batch":N_THREADS_BATCH,"context":N_CTX,"gpu_layers":N_GPU_LAYERS,"temperature":TEMPERATURE,"top_p":TOP_P,"max_tokens":MAX_TOKENS,"seed":SEED,"candidate_context_chars":args.context_chars,"min_candidate_chars":args.min_candidate_chars,"semantic_validation_only":True},"candidate_generation":{"signal_count":len(SIGNALS),"stats":candidate_stats,"routing":{k:list(v) for k,v in ROUTE_BY_KIND.items()}},"timing":{"candidate_build_sec":clean_time,"model_load_sec":load,"warmup_sec":warm,"average_validation_latency_sec":mean(lats) if lats else None,"minimum_validation_latency_sec":min(lats) if lats else None,"maximum_validation_latency_sec":max(lats) if lats else None,"total_inference_sec":sum(lats),"total_inference_min":sum(lats)/60 if lats else 0,"projected_35_candidates_sec":mean(lats)*35 if lats else None,"projected_35_candidates_min":mean(lats)*35/60 if lats else None},"population":{"sources":len(records),"candidates":len(candidates),"json_valid":valid,"json_invalid":len(validations)-valid,"accepted":accepted,"rejected":len(validations)-accepted,"accepted_before_dedup":len(evidences),"unique_evidence":len(unique),"duplicate_evidence":dups},"dimension_statistics":dimstats,"candidates":[asdict(c) for c in candidates],"validations":[asdict(v) for v in validations],"evidence":unique}
        output.parent.mkdir(parents=True,exist_ok=True); tmp=output.with_suffix(output.suffix+".tmp"); tmp.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8"); tmp.replace(output)
        print("\n"+"="*100); print("V3.2 SUMMARY"); print("="*100); print(f"Sources              : {len(records)}"); print(f"Candidates           : {len(candidates)}"); print(f"JSON valid           : {valid}/{len(validations)}"); print(f"Accepted             : {accepted}"); print(f"Rejected             : {len(validations)-accepted}"); print(f"Unique evidence      : {len(unique)}"); print(f"Duplicate evidence   : {dups}")
        if lats: print(f"Average latency      : {mean(lats):.3f} sec\nMinimum latency      : {min(lats):.3f} sec\nMaximum latency      : {max(lats):.3f} sec\nTotal inference      : {sum(lats):.1f} sec ({sum(lats)/60:.2f} min)\nProjected 35         : {mean(lats)*35:.1f} sec ({mean(lats)*35/60:.2f} min)")
        print("\nDIMENSION RESULTS"); [print(f"  {d:28s}: {dimstats[d]['candidates']} candidates, {dimstats[d]['accepted']} accepted") for d in DIMENSIONS]
        status="PASS" if valid==len(validations) and len(candidates)>0 else "FAIL"; print(f"\nSTATUS               : {status}")
        return 0 if status=="PASS" else 1
    finally: session.close()

if __name__=="__main__": raise SystemExit(main())
