#!/usr/bin/env python3
"""Optional research-only bridge to existing main/math_interop_v0/phase4.py.

Requires an existing, independently checked-out math core worktree:
  python3 scripts/market_math_dag_adapter.py registry/quant_results.csv \
    --math-core /tmp/market-math-main/math_interop_v0 \
    --cache /tmp/market-stat-cache --output research/market_dag_summary.json

Run only once math_tools_v2/requirements.txt have been installed.
This does not run SageMath or MATLAB, nor claim a full seven-engine benchmark.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
import sys

from market_stat_router import classify, SCHEMA as ROUTER_SCHEMA

ADAPTER_SCHEMA = "market-dag-bridge/1"

def run(input_csv: Path, math_core: Path, cache: Path):
    core = math_core.resolve()
    if not (core / "phase4.py").is_file() or not (core / "phase1.py").is_file():
        raise FileNotFoundError("Math core not checked out; do not silently copy missing engine")
    sys.path.insert(0, str(core))
    import duckdb
    import phase4
    rows = list(csv.DictReader(input_csv.read_text(encoding="utf-8-sig").splitlines()))
    ids = [r.get("result_id", "") for r in rows]
    if not ids or not all(ids) or len(set(ids)) != len(ids):
        raise ValueError("Missing or duplicate result ID")
    dag = phase4.CalcDAG(cache)
    route_names = []
    for r in rows:
        rid = r["result_id"]
        source = "source_" + rid
        routed = "classified_" + rid
        # The full summary row (including source provenance) is in the node input hash.
        dag.eval(source, "observed_registry_summary", "Source", [],
                 {"version": ADAPTER_SCHEMA, "record": r}, lambda deps, r=r: r)
        dag.eval(routed, "stat_method_classification", "Source", [source],
                 {"schema": ROUTER_SCHEMA}, lambda deps, src=source: classify(deps[src]))
        route_names.append(routed)

    def aggregate(deps):
        con = duckdb.connect(":memory:")
        try:
            con.execute("CREATE TABLE t(result_id VARCHAR, route_state VARCHAR, source_id VARCHAR)")
            for name in route_names:
                v = deps[name]
                source_ids = v["source_ids"] or [""]
                for sid in source_ids:
                    con.execute("INSERT INTO t VALUES (?,?,?)",
                                (v["result_id"], v["route_state"], sid))
            groups = con.execute("""
                SELECT route_state, COUNT(DISTINCT result_id)
                FROM t GROUP BY route_state ORDER BY route_state
            """).fetchall()
            overlaps = con.execute("""
                SELECT source_id, COUNT(DISTINCT result_id)
                FROM t WHERE source_id <> ''
                GROUP BY source_id HAVING COUNT(DISTINCT result_id) > 1
                ORDER BY source_id
            """).fetchall()
        finally:
            con.close()
        return {"classifications": {k: n for k, n in groups},
                "shared_source_counts": {k: n for k, n in overlaps},
                "input_result_rows": len(rows)}

    summary = dag.eval("source_summary", "duckdb_source_dependency_check",
                       "DuckDB", route_names, {"schema": ADAPTER_SCHEMA}, aggregate)
    if sum(summary["classifications"].values()) != len(rows):
        raise RuntimeError("Source count mismatch; fail closed")
    return {
        "schema": ADAPTER_SCHEMA,
        "input_sha256": hashlib.sha256(input_csv.read_bytes()).hexdigest(),
        "status": "PRE_S2_ROUTING_ONLY",
        "gate_changed": False,
        "engines_actually_run": ["DuckDB"],  # Source and Python router are not math engines
        "not_run": ["NumPy", "SciPy", "SymPy", "mpmath", "SageMath", "MATLAB"],
        "computed_nodes": dag.computed, "reused_nodes": dag.reused,
        "summary": summary,
        "warning": "Matching number computations is not validating original research evidence"
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("input_csv", type=Path)
    p.add_argument("--math-core", required=True, type=Path)
    p.add_argument("--cache", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    result = run(args.input_csv, args.math_core, args.cache)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf8")
    print(json.dumps({"rows": result["summary"]["input_result_rows"],
                      "computed": len(result["computed_nodes"]),
                      "reused": len(result["reused_nodes"])}, ensure_ascii=False))

if __name__ == "__main__":
    main()
