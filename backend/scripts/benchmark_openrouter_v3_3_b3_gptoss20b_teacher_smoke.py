#!/usr/bin/env python3
"""V3.3-B.3 GPT-OSS 20B teacher smoke benchmark.

Frozen 16-case B.2.2 population. No production artifact is modified.
"""
from __future__ import annotations
import concurrent.futures, json, os, random, socket, ssl, time
import urllib.error, urllib.request
from pathlib import Path
from typing import Any

BENCHMARK_VERSION = "V3.3-B.3-GPTOSS20B-TEACHER-SMOKE"
PROMPT_VERSION = "candidate-semantic-validation-v7-gptoss20b-teacher"
INPUT_PATH = Path(os.getenv("B3_GPTOSS_INPUT",
    "/opt/investment-os/generated/restomart/benchmark_qwen25_1p5b_v3_3_b2_1_smoke.json"))
OUTPUT_PATH = Path(os.getenv("B3_GPTOSS_OUTPUT",
    "/opt/investment-os/generated/restomart/benchmark_openrouter_v3_3_b3_gptoss20b_teacher_smoke.json"))
MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b")
API_URL = "https://openrouter.ai/api/v1/chat/completions"
CONCURRENCY = int(os.getenv("B3_GPTOSS_CONCURRENCY", "2"))
TIMEOUT_SEC = int(os.getenv("B3_GPTOSS_TIMEOUT", "120"))
RETRIES = int(os.getenv("B3_GPTOSS_RETRIES", "2"))
MAX_TOKENS = int(os.getenv("B3_GPTOSS_MAX_TOKENS", "256"))
REASONING_EFFORT = os.getenv("B3_GPTOSS_REASONING_EFFORT", "medium")
BACKOFF_INITIAL_SEC = float(os.getenv("B3_GPTOSS_BACKOFF_INITIAL", "5"))
BACKOFF_MAX_SEC = float(os.getenv("B3_GPTOSS_BACKOFF_MAX", "30"))
EXPECTED_CASES, EXPECTED_POSITIVE, EXPECTED_NEGATIVE = 16, 8, 8
MIN_ACCURACY = MIN_POSITIVE_ACCURACY = MIN_NEGATIVE_ACCURACY = 0.875

FIELD_DEFINITIONS = {
    "cash_burn": "Explicit cash consumption, cash burn rate, cash depletion, or cash runway over a stated period.",
    "customers": "Actual customers, customer count, named customers, customer relationships, deployments, or explicit actual customer traction. A target customer segment or business description alone is insufficient.",
    "adoption_usage": "Actual product/service usage or adoption, including users, orders, transactions, deployments, utilization, or usage volume. A target, break-even threshold, or merely described business model is insufficient.",
    "board_rights": "An explicit investor/shareholder right to appoint, nominate, designate, or otherwise have board representation.",
    "market_size": "Explicit TAM, SAM, SOM, addressable market size, market value, or quantified market opportunity.",
    "instrument": "An explicitly stated financing/security instrument such as CCPS, equity, debt, SAFE, convertible instrument, or another named investment security.",
    "valuation": "An explicit company valuation, including pre-money, post-money, valuation cap, or another stated valuation amount.",
    "gmv": "Explicit Gross Merchandise Value or GMV.",
    "growth": "Explicit historical or projected growth rate, growth trajectory, or quantified growth.",
    "founder_background": "Explicit founder identity, experience, education, prior company, professional history, or other substantive founder background.",
    "revenue": "Explicit actual or projected company revenue, sales revenue, or revenue amount/rate.",
    "generic": "Direct, substantive evidence supporting the requested investment-analysis field.",
}

SYSTEM_PROMPT = """You are a strict investment evidence validation teacher.
Determine whether the candidate text provides DIRECT, EXPLICIT evidence for the requested investment-analysis field.
Rules:
1. Accept only if the candidate directly supports the requested field.
2. Do not infer information that is not stated.
3. A keyword or phrase alone is insufficient.
4. Reject incidental mentions.
5. Reject legal, administrative, accounting, or boilerplate text unless it directly provides evidence.
6. Reject formulas, ratios, headings, labels, or related metrics when they do not establish the field.
7. Related business information is not necessarily evidence for the field.
8. Distinguish actual evidence from targets, plans, projections, thresholds, definitions, and generic descriptions.
9. Be conservative when ambiguous.
Return a concise reason identifying the decisive evidence boundary.
Use only the supplied candidate text."""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "accepted": {"type": "boolean"},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "reason": {"type": "string"},
    },
    "required": ["accepted", "confidence", "reason"],
    "additionalProperties": False,
}

def load_json(path): return json.loads(path.read_text(encoding="utf-8"))

def extract_cases(data):
    by_id = {str(r["candidate_id"]): r for r in data.get("results", [])}
    cases = []
    for item in data.get("smoke_selection", []):
        cid = str(item["candidate_id"])
        if cid not in by_id: raise RuntimeError(f"Candidate {cid} missing from results[]")
        r = by_id[cid]
        cases.append({
            "index": item["index"], "candidate_id": cid,
            "dimension": r["dimension"], "field": r["field"],
            "candidate_text": r["candidate_text"],
            "expected_label": r.get("smoke_expected_label"),
            "challenge_type": r.get("smoke_challenge_type"),
            "source_path": r.get("source_path", item.get("source_path")),
            "extraction_id": r.get("extraction_id"),
        })
    if len(cases) != EXPECTED_CASES: raise RuntimeError(f"Expected {EXPECTED_CASES} cases, got {len(cases)}")
    if sum(c["expected_label"] == "A" for c in cases) != EXPECTED_POSITIVE or sum(c["expected_label"] == "R" for c in cases) != EXPECTED_NEGATIVE:
        raise RuntimeError("Frozen smoke label distribution mismatch")
    return cases

def user_prompt(field, text):
    return f"Requested field: {field}\n\nField definition:\n{FIELD_DEFINITIONS.get(field, FIELD_DEFINITIONS['generic'])}\n\nCandidate text:\n{text}\n\nClassify only the candidate text. Do not infer unstated facts."

def call_openrouter(api_key, field, candidate_text):
    payload = {
        "model": MODEL,
        "messages": [{"role":"system","content":SYSTEM_PROMPT},
                     {"role":"user","content":user_prompt(field, candidate_text)}],
        "temperature": 0.0, "top_p": 1.0, "max_tokens": MAX_TOKENS,
        "reasoning": {"effort": REASONING_EFFORT},
        "response_format": {"type":"json_schema","json_schema":{
            "name":"investment_evidence_validation","strict":True,"schema":RESPONSE_SCHEMA}},
        "provider": {"require_parameters": True},
    }
    headers = {"Authorization":f"Bearer {api_key}","Content-Type":"application/json",
               "Accept":"application/json","HTTP-Referer":"https://openrouter.ai/",
               "X-Title":"Investment OS GPT-OSS 20B Teacher Smoke"}
    body = json.dumps(payload).encode()
    for attempt in range(1, RETRIES + 1):
        started = time.perf_counter()
        req = urllib.request.Request(API_URL, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                data = json.loads(raw)
                choices = data.get("choices") or []
                content = (choices[0].get("message") or {}).get("content") if choices else None
                return {"raw_response":content, "http_status":resp.status,
                        "latency_sec":time.perf_counter()-started,
                        "usage":data.get("usage",{}),"attempt":attempt,
                        "provider":data.get("provider"),"model_id":data.get("model")}
        except urllib.error.HTTPError as exc:
            err = exc.read().decode("utf-8", errors="replace")[:4000]
            if exc.code == 429 and attempt < RETRIES:
                delay=min(BACKOFF_INITIAL_SEC*2**(attempt-1), BACKOFF_MAX_SEC)+random.uniform(0,1)
                print(f"    provider 429; backing off {delay:.1f}s", flush=True); time.sleep(delay); continue
            return {"error":"provider_rate_limited" if exc.code==429 else "http_error",
                    "http_status":exc.code,"latency_sec":time.perf_counter()-started,
                    "raw_response":None,"http_error":err,"attempt":attempt}
        except (socket.timeout, TimeoutError) as exc:
            if attempt < RETRIES: time.sleep(min(2**(attempt-1),8)); continue
            return {"error":"transport_timeout","http_status":None,"latency_sec":time.perf_counter()-started,
                    "raw_response":None,"exception":str(exc),"attempt":attempt}
        except (urllib.error.URLError, ssl.SSLError) as exc:
            if attempt < RETRIES: time.sleep(min(2**(attempt-1),8)); continue
            return {"error":"transport_network_error","http_status":None,"latency_sec":time.perf_counter()-started,
                    "raw_response":None,"exception":str(exc),"attempt":attempt}
        except Exception as exc:
            return {"error":"transport_error","http_status":None,"latency_sec":time.perf_counter()-started,
                    "raw_response":None,"exception":str(exc),"attempt":attempt}
    return {"error":"transport_error","raw_response":None,"latency_sec":0.0}

def validate(raw):
    if raw is None: return False,None,None,None,"response_empty"
    try: obj=json.loads(raw)
    except json.JSONDecodeError: return False,None,None,None,"response_not_json"
    if not isinstance(obj,dict) or set(obj) != {"accepted","confidence","reason"}:
        return False,None,None,None,"response_schema_invalid"
    if type(obj["accepted"]) is not bool: return False,None,None,None,"response_schema_invalid"
    c=obj["confidence"]
    if isinstance(c,bool) or not isinstance(c,(int,float)) or not 0<=float(c)<=1:
        return False,None,None,None,"response_schema_invalid"
    if not isinstance(obj["reason"],str) or not obj["reason"].strip():
        return False,None,None,None,"response_schema_invalid"
    return True,obj["accepted"],float(c),obj["reason"],None

def run_case(api_key, case):
    api=call_openrouter(api_key,case["field"],case["candidate_text"])
    valid,accepted,confidence,reason,err=validate(api.get("raw_response"))
    error=err or api.get("error")
    actual=("A" if accepted else "R") if valid else None
    return {**case,"model":MODEL,"valid":valid,"accepted":accepted,"actual_label":actual,
            "correct":bool(valid and actual==case["expected_label"]),"confidence":confidence,
            "reason":reason,"raw_response":api.get("raw_response"),"error":error,
            "http_status":api.get("http_status"),"http_error":api.get("http_error"),
            "exception":api.get("exception"),"provider":api.get("provider"),
            "provider_model_id":api.get("model_id"),
            "latency_sec":round(api.get("latency_sec",0),4),"attempt":api.get("attempt"),
            "usage":api.get("usage",{})}

def percentile(values,p):
    if not values:return None
    v=sorted(values)
    if len(v)==1:return v[0]
    x=(len(v)-1)*p; lo=int(x); hi=min(lo+1,len(v)-1); f=x-lo
    return v[lo]+(v[hi]-v[lo])*f

def main():
    key=os.getenv("OPENROUTER_API_KEY")
    if not key: raise SystemExit("OPENROUTER_API_KEY is not set")
    data=load_json(INPUT_PATH); cases=extract_cases(data)
    print(f"B.3-GPTOSS20B teacher smoke input : {INPUT_PATH}")
    print(f"Model                         : {MODEL}")
    print(f"Cases                         : {len(cases)}")
    print(f"Concurrency                   : {CONCURRENCY}")
    print(f"Reasoning effort              : {REASONING_EFFORT}")
    print(f"Max tokens                    : {MAX_TOKENS}")
    print("Response format               : strict json_schema")
    print("Provider require_parameters   : true")
    print("Production path               : NOT MODIFIED\n")
    started=time.perf_counter(); results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        fm={ex.submit(run_case,key,c):c for c in cases}
        for n,f in enumerate(concurrent.futures.as_completed(fm),1):
            c=fm[f]
            try:r=f.result()
            except Exception as exc:r={**c,"model":MODEL,"valid":False,"accepted":None,"actual_label":None,"correct":False,"confidence":None,"reason":None,"raw_response":None,"error":"transport_error","exception":str(exc),"latency_sec":0.0}
            results.append(r)
            print(f"[{n:02d}/{len(cases):02d}] {r['field']} expected={r['expected_label']} actual={r['actual_label']} valid={'yes' if r['valid'] else 'no'} confidence={r.get('confidence','-')} {r.get('latency_sec',0):.2f}s"+(f" error={r['error']}" if r.get('error') else ""),flush=True)
    results.sort(key=lambda x:x["index"]); wall=time.perf_counter()-started
    valid=[r for r in results if r["valid"]]; correct=[r for r in valid if r["correct"]]
    pos=[r for r in results if r["expected_label"]=="A"]; neg=[r for r in results if r["expected_label"]=="R"]
    pc=[r for r in pos if r["valid"] and r["correct"]]; nc=[r for r in neg if r["valid"] and r["correct"]]
    errors={}
    for r in results:
        if r.get("error"):errors[r["error"]]=errors.get(r["error"],0)+1
    accuracy=len(correct)/EXPECTED_CASES; pa=len(pc)/EXPECTED_POSITIVE; na=len(nc)/EXPECTED_NEGATIVE
    contract=len(valid)==EXPECTED_CASES; sg=accuracy>=MIN_ACCURACY; pg=pa>=MIN_POSITIVE_ACCURACY; ng=na>=MIN_NEGATIVE_ACCURACY
    status="BLOCKED" if any(r.get("error")=="provider_rate_limited" for r in results) else ("PASS" if contract and sg and pg and ng else "FAIL")
    lats=[r["latency_sec"] for r in results if r.get("latency_sec",0)>0]
    conf=[r["confidence"] for r in valid if r["confidence"] is not None]
    summary={"processed":len(results),"structured_valid":len(valid),"structured_valid_rate":len(valid)/EXPECTED_CASES,
             "expected_accepted":EXPECTED_POSITIVE,"expected_rejected":EXPECTED_NEGATIVE,
             "actual_accepted":sum(r["actual_label"]=="A" for r in valid),
             "actual_rejected":sum(r["actual_label"]=="R" for r in valid),
             "correct":len(correct),"accuracy":accuracy,"positive_correct":len(pc),"positive_accuracy":pa,
             "negative_correct":len(nc),"negative_accuracy":na,
             "average_confidence":sum(conf)/len(conf) if conf else None,
             "average_latency_sec":sum(lats)/len(lats) if lats else None,
             "p95_latency_sec":percentile(lats,.95),"total_wall_sec":wall,"error_counts":errors,
             "contract_gate":contract,"semantic_accuracy_gate":sg,"positive_accuracy_gate":pg,
             "negative_boundary_gate":ng,"status":status}
    output={"benchmark":{"version":BENCHMARK_VERSION,"prompt_version":PROMPT_VERSION,"observational":True,
             "production_pipeline_modified":False,"full_benchmark_authorized":False,"teacher_candidate":True},
            "input":{"path":str(INPUT_PATH),"source_benchmark_version":data.get("benchmark"),
                     "source_gate_version":data.get("source_gate_version"),"source_artifact_id":data.get("id"),
                     "cases":len(cases)},
            "model":{"provider":"openrouter","model":MODEL,"endpoint":API_URL,"temperature":0.0,"top_p":1.0,
                     "reasoning_effort":REASONING_EFFORT,"max_tokens":MAX_TOKENS,
                     "response_format":{"type":"json_schema","json_schema":{"name":"investment_evidence_validation","strict":True,"schema":RESPONSE_SCHEMA}},
                     "provider_require_parameters":True,"concurrency":CONCURRENCY,"timeout_sec":TIMEOUT_SEC,"retries":RETRIES,
                     "429_backoff_initial_sec":BACKOFF_INITIAL_SEC,"429_backoff_max_sec":BACKOFF_MAX_SEC},
            "population":{"candidate_count":len(cases),"expected_accepted":EXPECTED_POSITIVE,"expected_rejected":EXPECTED_NEGATIVE,
                          "candidate_population_frozen":True,"expected_labels_hidden_from_model":True},
            "quality_checks":{"provenance_owned_by_python":True,"expected_labels_hidden":True,
                              "response_schema_enforced_in_python":True,"provider_structured_output_requested":True,
                              "provider_require_parameters":True,"llm_response_repair":False,"production_unmodified":True,
                              "accuracy_threshold":MIN_ACCURACY,"positive_accuracy_threshold":MIN_POSITIVE_ACCURACY,
                              "negative_accuracy_threshold":MIN_NEGATIVE_ACCURACY,"teacher_thresholds_stricter_than_student":True},
            "timing":{"total_wall_sec":wall,"average_latency_sec":summary["average_latency_sec"],"p95_latency_sec":summary["p95_latency_sec"]},
            "summary":summary,"results":results,"status":status}
    OUTPUT_PATH.parent.mkdir(parents=True,exist_ok=True); OUTPUT_PATH.write_text(json.dumps(output,indent=2,ensure_ascii=False),encoding="utf-8")
    print("\nB.3-GPTOSS20B TEACHER SMOKE RESULT")
    print(f"  structured valid       : {len(valid)}/{EXPECTED_CASES}")
    print(f"  correct                : {len(correct)}/{EXPECTED_CASES}")
    print(f"  accuracy               : {accuracy:.2%}")
    print(f"  positive accuracy      : {pa:.2%}")
    print(f"  negative accuracy      : {na:.2%}")
    print(f"  average confidence     : {summary['average_confidence']:.3f}" if conf else "  average confidence     : N/A")
    print(f"  average latency        : {summary['average_latency_sec']:.3f}s" if lats else "  average latency        : N/A")
    print(f"  p95 latency            : {summary['p95_latency_sec']:.3f}s" if lats else "  p95 latency            : N/A")
    print(f"  total wall             : {wall:.2f}s")
    print(f"  contract gate          : {'PASS' if contract else 'FAIL'}")
    print(f"  semantic accuracy gate : {'PASS' if sg else 'FAIL'}")
    print(f"  positive accuracy gate : {'PASS' if pg else 'FAIL'}")
    print(f"  negative boundary gate : {'PASS' if ng else 'FAIL'}")
    print(f"  error counts           : {errors}")
    print(f"  status                 : {status}")
    print(f"  output                 : {OUTPUT_PATH}")
    return 0 if status=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
