#!/usr/bin/env python3
"""Research-only statistical routing. No false gate pass or inferred demographics.
Usage: python3 scripts/market_stat_router.py registry/quant_results.csv --output research/stat_routing.json
Python standard library only. Not a substitute for raw-data analysis.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math
from collections import Counter, defaultdict
from pathlib import Path

SCHEMA = "market-stat-router/1"
MISSING = {"", "UNKNOWN", "N/A", "—", "NON_IDENTIFIABLE", "NA", "null"}
ENGINES = ("DuckDB", "NumPy", "SciPy", "SymPy", "mpmath", "SageMath", "MATLAB")

def number(v):
    try:
        s = str(v or "").strip().replace(",", "")
        if s in MISSING or "〜" in s or "/" in s:
            return None
        x = float(s)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError, OverflowError):
        return None

def classify(row):
    category = (row.get("evidence_category") or "").strip()
    metric = row.get("metric") or ""
    unit = row.get("unit") or ""
    estimate = (row.get("estimate") or "").strip()
    n, value = number(row.get("sample_n")), number(estimate)
    allowed = ["source_dependency_audit"]
    blocked = []
    engines = ["DuckDB"]
    if category == "NON_IDENTIFIABLE" or estimate == "NON_IDENTIFIABLE":
        state = "NON_IDENTIFIABLE"
        blocked.extend(["mean", "median", "confidence_interval", "Bayesian_posterior", "forecast"])
    elif category == "ASSUMPTION_ONLY":
        state = "ASSUMPTION_ONLY"
        allowed.append("conditional_scenario_only_with_all_inputs")
        blocked.extend(["present_as_observed", "present_as_success_probability"])
        engines.append("SymPy")
    elif category == "OBSERVED":
        if unit == "%" and value is not None and not 0 <= value <= 100:
            state = "INVALID_PERCENT_REVIEW"
            blocked.extend(["invalid_percentage_out_of_range", "automatic_quantitative_inference"])
        elif unit == "%" and value is not None and 0 <= value <= 100:
            state = "OBSERVED_RATE_NOT_RAW_SAMPLE"
            allowed.extend(["describe_reported_proportion", "stratify_only_by_compatible_sources"])
            if n and n.is_integer() and n > 0 and (row.get("model_id") or "").startswith("M_WILSON95"):
                allowed.append("approximate_Wilson_check_from_rounded_percent")
                engines.append("SciPy")
                blocked.extend(["exact_binomial_interval_without_success_count",
                                "infer_national_rate_without_sampling_design"])
            else:
                blocked.append("binomial_interval_without_verified_unit_and_denominator")
        elif value is not None:
            state = "OBSERVED_POINT_OR_SUMMARY"
            allowed.append("preserve_reported_point_without_reconstruction")
        else:
            state = "OBSERVED_RANGE_OR_TEXT"
            blocked.append("convert_text_or_range_to_scalar")
        blocked.extend(["recompute_mean_or_median_from_aggregate_only",
                        "Bayesian_posterior_without_counts_likelihood_and_prior"])
    elif category in {"MIXED", "MODEL_BASED"}:
        state = category
        engines.append("SymPy")
        allowed.append("recalculate_only_with_explicit_model_and_data")
        blocked.append("present_as_raw_observation")
    else:
        state = "UNCLASSIFIED_REVIEW"
        blocked.append("automatic_quantitative_inference")
    if "中央値" in metric or "median" in metric.lower():
        blocked.append("recompute_median_without_microdata")
    if "平均" in metric or "mean" in metric.lower():
        blocked.append("recompute_mean_without_microdata")
    return {
        "result_id": row.get("result_id", ""), "metric": metric,
        "segment": row.get("segment", ""), "geography": row.get("geography", ""),
        "period": row.get("period", ""), "unit": unit,
        "sample_n": row.get("sample_n", ""), "source_ids": [
            s.strip() for s in (row.get("source_ids") or "").split(";") if s.strip()
        ], "evidence_category": category, "route_state": state,
        "allowed_methods": sorted(set(allowed)), "blocked_methods": sorted(set(blocked)),
        "candidate_engines": sorted(set(engines)), "engines_actually_run": [],
    }

def route(path):
    raw = Path(path).read_bytes()
    rows = list(csv.DictReader(raw.decode("utf-8-sig").splitlines()))
    ids = [r.get("result_id", "") for r in rows]
    if not ids or not all(ids) or len(ids) != len(set(ids)):
        raise ValueError("Empty input, missing or duplicate result_id: fail closed")
    records = [classify(r) for r in rows]
    origin = defaultdict(set)
    for r in records:
        for sid in r["source_ids"]:
            origin[sid].add(r["result_id"])
    return {
        "schema": SCHEMA, "input_sha256": hashlib.sha256(raw).hexdigest(),
        "input_rows": len(rows), "state": "PRE_S2_READ_ONLY_CLASSIFICATION",
        "research_gate_modified": False, "all_seven_engines_executed": False,
        "available_engine_names_not_runtime_verified": list(ENGINES),
        "classification_counts": dict(Counter(r["route_state"] for r in records)),
        "shared_source_ids": {
            k: sorted(v) for k, v in origin.items() if len(v) > 1
        },
        "never_auto_pool_by": [
            "source_origin", "population", "segment", "geography", "period",
            "measurement_definition", "unit", "selection_method"
        ],
        "engine_routes": {
            "DuckDB": "joins/source dedup/stratified counts of verified records",
            "NumPy": "mean median variance quantiles ONLY from validated microdata",
            "SciPy": "intervals tests likelihood optimization after method eligibility",
            "SymPy": "exact formula and rational arithmetic via safe Math IR",
            "mpmath": "high precision on demand only",
            "SageMath": "selective independent check for supported high-risk exact cases",
            "MATLAB": "selective further independent check for supported cases"
        },
        "Bayesian_rule": "Require actual success/failure counts, source independence, likelihood, documented prior and sensitivity; otherwise NON_IDENTIFIABLE",
        "records": records,
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("input_csv", type=Path)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = route(a.input_csv)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rows": result["input_rows"],
                      "classes": result["classification_counts"]}, ensure_ascii=False))

if __name__ == "__main__":
    main()
