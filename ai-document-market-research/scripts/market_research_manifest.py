#!/usr/bin/env python3
"""Compact manifest of ALL research IDs. No source or topic is dropped.

Replaces copying full multi-MB ledgers into a Claude prompt with a verified ID
index. Completeness of INDEX is not completeness of RESEARCH.
"""
from __future__ import annotations
import argparse, csv, hashlib, json
from collections import Counter, defaultdict
from pathlib import Path

EXPECTED = {
    "topic_execution_status.csv": 325,
    "query_execution_status.csv": 896,
    "competitor_execution_status.csv": 80,
    "additional_topic_status.csv": 7,
}

def rows(path):
    b = path.read_bytes()
    with path.open(encoding="utf-8-sig", newline="") as f:
        records = list(csv.DictReader(f))
    if not records or len(records[0]) < 3:
        raise ValueError("Invalid CSV: " + str(path))
    return records, {"sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b),
                     "rows": len(records), "path": str(path)}

def unique_ids(data, col):
    x = [r.get(col, "").strip() for r in data]
    if not all(x) or len(set(x)) != len(x):
        raise ValueError("Missing or duplicate " + col)
    return x

def build(registry):
    registry = Path(registry)
    required = {
        "topics": ("topic_execution_status.csv", "topic_id"),
        "queries": ("query_execution_status.csv", "suggestion_id"),
        "competitors": ("competitor_execution_status.csv", "competitor_id"),
        "additional": ("additional_topic_status.csv", "topic_id"),
        "sources": ("source_evidence.csv", "source_id"),
        "quantitative": ("quant_results.csv", "result_id"),
    }
    data, files = {}, {}
    for key, (name, id_col) in required.items():
        vals, details = rows(registry / name)
        unique_ids(vals, id_col)
        if name in EXPECTED and len(vals) != EXPECTED[name]:
            raise ValueError("Fail closed on changed scope: " + name)
        data[key], files[key] = vals, details
    axes = defaultdict(lambda: {"total": 0, "s1_done": 0, "unresolved": []})
    for r in data["topics"]:
        a = axes[r["axis_id"]]
        a["total"] += 1
        if r["gate_state"] == "S1_DONE":
            a["s1_done"] += 1
        else:
            a["unresolved"].append(r["topic_id"])
    source_origin = defaultdict(list)
    for r in data["sources"]:
        source_origin[r.get("origin_group_id") or "UNKNOWN"].append(r["source_id"])
    out = {
        "schema": "market-evidence-index/1",
        "status": "INCOMPLETE",
        "first_unmet_gate": "S1",
        "NO_FINAL_INFERENCE": True,
        "not_all_sources_S2_verified": True,
        "input_registry_hashes": files,
        "counts": {
            "topics_by_gate": dict(Counter(r["gate_state"] for r in data["topics"])),
            "legacy_queries_by_state": dict(Counter(r["state"] for r in data["queries"])),
            "competitors_by_gate": dict(Counter(r["gate_state"] for r in data["competitors"])),
            "extra_topics_by_gate": dict(Counter(r["gate_state"] for r in data["additional"])),
            "total_sources": len(data["sources"]),
            "source_origins_non_unknown": len([k for k in source_origin if k != "UNKNOWN"]),
            "quantitative_results": len(data["quantitative"]),
        },
        "axes": dict(sorted(axes.items())),
        "competitor_unresolved_ids": [
            r["competitor_id"] for r in data["competitors"] if r["gate_state"] != "S1_DONE"
        ],
        "extra_topic_unresolved_ids": [
            r["topic_id"] for r in data["additional"] if r["gate_state"] != "S1_DONE"
        ],
        "search_execution_ids_are_in_original_csv": True,
        "source_ids_are_in_original_csv": True,
        "individual_records_not_removed": True,
        "interpretation": "Index only. Fetch raw records and original evidence by ID before statistical inference.",
    }
    if len(out["axes"]) != 32:
        raise ValueError("Expected exactly 32 original research axes")
    return out

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--registry", type=Path, default=Path("registry"))
    p.add_argument("--output", type=Path, required=True)
    x = p.parse_args()
    result = build(x.registry)
    x.output.parent.mkdir(parents=True, exist_ok=True)
    x.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf8")
    print(json.dumps(result["counts"], ensure_ascii=False))

if __name__ == "__main__":
    main()
