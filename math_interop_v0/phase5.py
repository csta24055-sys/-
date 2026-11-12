"""Unified seven-engine integration smoke test.

One traceable, content-addressed *execution record* for Python's 5 engines and
the external SageMath -> MATLAB sequence. GitHub Actions executes remote jobs.
This is intentionally NOT a generic cross-run remote DAG scheduler.
Only synthetic Math IR 0.1 inputs; never eval untrusted source strings.
"""
from __future__ import annotations

import copy
import json
import shutil
import sys
from pathlib import Path

import phase1
import phase2
import phase3
import phase4

SCHEMA = "math-ir-unified/1"
VERSION = "unified-seven-v1"
ENGINES = {"SymPy", "NumPy", "SciPy", "mpmath", "DuckDB", "SageMath", "MATLAB"}
PYTHON_ENGINES = {"Source", "SymPy", "NumPy", "SciPy", "mpmath", "DuckDB"}


def check(test, message):
    if not test:
        raise ValueError(message)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


def save(path, obj):
    phase4.write_json(path, obj)


def exact_fields(obj, expected, where):
    phase1.exact_fields(obj, expected, where)


def prepare(folder):
    p = Path(folder)
    p.mkdir(parents=True, exist_ok=True)
    check(not (p / "plan.json").exists(), "Refusing to overwrite a prior plan")
    # Reuse verified phase 3 JSON and phase 4 27-node cache, not clone the algorithms.
    phase3.prepare(p)
    report = phase4.build(p / "cache", "base", "default")
    check(len(report["cache_keys"]) == 27 and len(report["computed"]) == 27,
          "Python DAG was not cold-built with 27 real nodes")
    check(report["reused"] == [], "Unexpected warm cache during preparation")
    save(p / "python_dag.json", report)
    bundle = load(p / "input.json")
    plan = {
        "schema": SCHEMA,
        "algorithm_version": VERSION,
        "source_sha256": phase1.digest(bundle),
        "python_dag_sha256": phase1.digest(report),
        "engines_expected": sorted(ENGINES),
        "case_ids": [c["case_id"] for c in bundle["cases"]],
        "remote": ["SageMath", "MATLAB"],
        "execution_policy": "synthetic_only; GitHub job needs; fail_closed",
    }
    save(p / "plan.json", plan)
    print("UNIFIED PREPARE: PASS 5 Python libraries, 27 DAG nodes, 5 exact cases")


def add_external(nodes, index, name, engine, operation, deps, payload, version, case_hash):
    check(name not in index, "Duplicate unified node: " + name)
    check(engine in ENGINES or engine in {"Verifier"}, "Unsupported engine")
    check(all(x in index for x in deps), "Unresolved external dependencies")
    descriptor = {
        "schema": SCHEMA,
        "algorithm_version": VERSION,
        "name": name,
        "engine": engine,
        "engine_version": version,
        "operation": operation,
        "dependencies": {k: index[k]["key"] for k in deps},
        "case_sha256": case_hash,
    }
    row = {
        "name": name,
        "descriptor": descriptor,
        "key": phase1.digest(descriptor),
        "payload": copy.deepcopy(payload),
        "payload_sha256": phase1.digest(payload),
    }
    nodes.append(row)
    index[name] = row


def make_graph(folder):
    p = Path(folder)
    bundle, manifest = load(p / "input.json"), load(p / "manifest.json")
    sage, matlab = load(p / "sage_result.json"), load(p / "matlab_result.json")
    plan = load(p / "plan.json")
    cold = load(p / "python_dag.json")
    exact_fields(plan, {"schema", "algorithm_version", "source_sha256",
                        "python_dag_sha256", "engines_expected", "case_ids",
                        "remote", "execution_policy"}, "unified plan")
    check(plan["schema"] == SCHEMA and plan["algorithm_version"] == VERSION,
          "Unrecognized integration plan")
    check(plan["source_sha256"] == phase1.digest(bundle), "Source changed after prepare")
    check(plan["python_dag_sha256"] == phase1.digest(cold), "Python DAG report changed")
    check(plan["engines_expected"] == sorted(ENGINES), "Declared engine set was altered")
    check(plan["remote"] == ["SageMath", "MATLAB"], "Remote order changed")
    check(plan["execution_policy"] == "synthetic_only; GitHub job needs; fail_closed",
          "Execution policy altered")
    check(plan["case_ids"] == [c["case_id"] for c in bundle["cases"]], "Cases changed")
    check(bundle == phase1.make_cases(), "Integration test is restricted to synthetic cases")
    check(cold["schema"] == phase4.SCHEMA and cold["scenario"] == "base",
          "Unexpected Python DAG")
    check(cold["numpy_salt"] == "default", "Python engine version override")
    check(len(cold["cache_keys"]) == 27 and len(cold["computed"]) == 27 and cold["reused"] == [],
          "Invalid baseline DAG graph")
    check(cold["result_sha256"] == phase1.digest(cold["result"]), "DAG output digest changed")

    # Full original Phase 3 independent math and lineage validation.
    phase3.verify(p)
    # Reconstruct in a fresh process and REQUIRE 27 actual cache hits. Because
    # phase4.build revalidates summary, corrupted or stale outputs fail closed.
    warm = phase4.build(p / "cache", "base", "default")
    check(warm["cache_keys"] == cold["cache_keys"] and
          warm["result"] == cold["result"] and warm["computed"] == [],
          "Stage 4 source/cache mismatch")
    check(set(warm["reused"]) == set(cold["cache_keys"]), "Cache did not persist between jobs")

    nodes, index = [], {}
    # Serialized canonical JSON sorts dictionary keys alphabetically. Reconstruct
    # execution order from actual dependencies, never from JSON object ordering.
    pending = dict(cold["cache_keys"])
    while pending:
        progressed = False
        for name, key in list(pending.items()):
            row = load(p / "cache" / (key + ".json"))
            exact_fields(row, {"descriptor", "key", "payload", "payload_sha256"}, "DAG cache")
            desc = row["descriptor"]
            check(row["key"] == key and phase1.digest(desc) == key, "Cache key invalid")
            check(row["payload_sha256"] == phase1.digest(row["payload"]), "Cache payload corrupted")
            check(desc["schema"] == phase4.SCHEMA and desc["name"] == name,
                  "Cache descriptor invalid")
            check(desc["engine"] in PYTHON_ENGINES, "Unknown cached engine")
            check(desc["engine_version"] == phase4.version(desc["engine"], "default"),
                  "Python engine version mismatch")
            check(type(desc["dependencies"]) is dict, "Invalid DAG dependencies")
            if not set(desc["dependencies"]).issubset(index):
                continue
            check(desc["dependencies"] == {dep: index[dep]["key"]
                  for dep in desc["dependencies"]}, "Stale/inconsistent DAG dependency")
            entry = {"name": name, "descriptor": desc, "key": key,
                     "payload": row["payload"], "payload_sha256": row["payload_sha256"]}
            nodes.append(entry)
            index[name] = entry
            del pending[name]
            progressed = True
        check(progressed, "DAG has a cycle, unresolved dependency, or invalid cache node")

    # Critical distinction: SageMath independently computes from source; MATLAB
    # consumes SageMath *actual JSON* and independently computes from source.
    for i, case in enumerate(bundle["cases"]):
        cid = case["case_id"]
        src = "source_" + cid
        sage_name = "sage_" + cid
        matlab_name = "matlab_" + cid
        sage_row = sage["results"][i]
        matlab_row = matlab["results"][i]
        check(sage_row["result"] == phase1.sympy_eval(case), "Sage exact mismatch")
        check(matlab_row["result"] == sage_row["result"] and
              matlab_row["upstream_result"] == sage_row["result"],
              "MATLAB did not preserve SageMath exact result")
        check(matlab_row["input_sha256"] == phase1.digest(case),
              "MATLAB source lineage mismatch")
        check(matlab_row["metadata_sha256"] == manifest["cases"][i]["metadata_sha256"],
              "MATLAB metadata lineage mismatch")
        add_external(nodes, index, sage_name, "SageMath", "exact_from_source",
                     [src], sage_row, "10.10-docker-tag", phase1.digest(case))
        add_external(nodes, index, matlab_name, "MATLAB", "independent_exact_and_sage_compare",
                     [src, sage_name], matlab_row, "setup-matlab@v3-runtime-unrecorded",
                     phase1.digest(case))

    # Five reconciliation nodes join remote proofs with NumPy/mpmath approximations.
    for case in bundle["cases"]:
        cid = case["case_id"]
        src = "source_" + cid
        sage_name, matlab_name = "sage_" + cid, "matlab_" + cid
        exact_name = "exact_" + cid
        np_name, mp_name = "numpy_" + cid, "mpmath_" + cid
        validated_name = "validated_" + cid
        exact = index[exact_name]["payload"]
        validated = index[validated_name]["payload"]
        check(exact == index[sage_name]["payload"]["result"] ==
              index[matlab_name]["payload"]["result"], "Cross-engine exact mismatch")
        check(validated["unit"] == case["unit"] and
              validated["assumptions"] == case["symbols"] and
              validated["source_sha256"] == phase1.digest(case),
              "Canonical mathematical metadata not preserved")
        check(validated["numpy"] == index[np_name]["payload"] and
              validated["mpmath"] == index[mp_name]["payload"],
              "Approximation detached from its exact source")
        result = {
            "case_id": cid,
            "exact": exact,
            "unit": case["unit"],
            "assumptions": case["symbols"],
            "source_sha256": phase1.digest(case),
            "verified_with": ["SymPy", "NumPy", "mpmath", "SageMath", "MATLAB"],
            "comparison": "exact_rational_equality; noncertified_numeric_error_recorded",
        }
        add_external(nodes, index, "reconciled_" + cid, "Verifier",
                     "cross_engine_reconciliation",
                     [src, exact_name, np_name, mp_name, validated_name,
                      sage_name, matlab_name], result, VERSION, phase1.digest(case))

    summary = {
        "engine_coverage": sorted(ENGINES),
        "case_count": len(bundle["cases"]),
        "exact_groups": cold["result"]["groups"],
        "scipy_reference_sha256": phase1.digest(index["scipy_reference"]["payload"]),
        "duckdb_summary_sha256": phase1.digest(index["duckdb_summary"]["payload"]),
        "source_sha256": plan["source_sha256"],
        "verified_case_sha256": {c["case_id"]: index["reconciled_" + c["case_id"]]["payload_sha256"]
                                 for c in bundle["cases"]},
        "precision_claim": "exact rational tested; binary64/decimal observed error only; no universal proof",
    }
    deps = ["reconciled_" + c["case_id"] for c in bundle["cases"]]
    deps += ["scipy_reference", "duckdb_summary"]
    add_external(nodes, index, "unified_summary", "Verifier", "all_engines_joined",
                 deps, summary, VERSION, phase1.digest(bundle))

    seen = {n["descriptor"]["engine"] for n in nodes}
    check(ENGINES <= seen, "Not all seven engines executed")
    check(len(nodes) == 43, "Expected 27 Python + 10 remote + 5 reconciliation + 1 summary nodes")
    doc = {
        "schema": SCHEMA,
        "algorithm_version": VERSION,
        "plan_sha256": phase1.digest(plan),
        "python_dag_sha256": phase1.digest(cold),
        "sage_output_sha256": phase1.digest(sage),
        "matlab_output_sha256": phase1.digest(matlab),
        "engine_coverage": sorted(ENGINES),
        "nodes": nodes,
        "root": index["unified_summary"]["key"],
        "summary": summary,
    }
    doc["graph_sha256"] = phase1.digest(doc)
    return doc


def verify_document(candidate, reference):
    exact_fields(candidate, {"schema", "algorithm_version", "plan_sha256",
                             "python_dag_sha256", "sage_output_sha256",
                             "matlab_output_sha256", "engine_coverage", "nodes",
                             "root", "summary", "graph_sha256"}, "unified graph")
    check(candidate["graph_sha256"] == phase1.digest(
          {k: v for k, v in candidate.items() if k != "graph_sha256"}), "Graph hash invalid")
    check(type(candidate["nodes"]) is list and len(candidate["nodes"]) == 43, "Invalid node count")
    by_name = {}
    for node in candidate["nodes"]:
        exact_fields(node, {"name", "descriptor", "key", "payload", "payload_sha256"}, "node")
        name = node["name"]
        check(type(name) is str and name not in by_name, "Duplicate node name")
        desc = node["descriptor"]
        check(desc["name"] == name and node["key"] == phase1.digest(desc), "Node descriptor corrupted")
        check(node["payload_sha256"] == phase1.digest(node["payload"]), "Node payload hash corrupted")
        check(desc["dependencies"] == {dep: by_name[dep]["key"] for dep in desc["dependencies"]},
              "Invalid dependency edge")
        by_name[name] = node
    check(candidate["root"] == by_name["unified_summary"]["key"], "Root node mismatch")
    # Hashes alone cannot authenticate a determined attacker; bind the graph
    # to independently reconstructed source + 7-engine calculations as well.
    check(candidate == reference, "Graph content does not match independently rebuilt evidence")
    return True


def audit(folder):
    p = Path(folder)
    actual = load(p / "unified_graph.json")
    expected = make_graph(p)
    verify_document(actual, expected)
    print("PASS independently reopened 43-node seven-engine DAG")

    tests = {
        "exact_result": lambda d: d["nodes"][27]["payload"]["result"].update(numerator="999"),
        "matlab_result": lambda d: d["nodes"][32]["payload"]["result"].update(numerator="999"),
        "metadata_unit": lambda d: d["nodes"][37]["payload"].update(unit="invalid"),
        "engine": lambda d: d["nodes"][27]["descriptor"].update(engine="SymPy"),
        "engine_version": lambda d: d["nodes"][27]["descriptor"].update(engine_version="0"),
        "dependency_edge": lambda d: d["nodes"][32]["descriptor"].update(dependencies={}),
        "missing_node": lambda d: d["nodes"].pop(),
        "source_lineage": lambda d: d.update(plan_sha256="0" * 64),
        "graph_digest": lambda d: d.update(graph_sha256="0" * 64),
    }
    for title, change in tests.items():
        corrupt = copy.deepcopy(actual)
        change(corrupt)
        # Even if an adversary rehashes the changed document, reconstruction
        # against the actual mathematical sources must still reject it.
        if title != "graph_digest":
            corrupt["graph_sha256"] = phase1.digest(
                {k: v for k, v in corrupt.items() if k != "graph_sha256"})
        try:
            verify_document(corrupt, expected)
        except (ValueError, KeyError, TypeError):
            print("PASS unified tamper rejected:", title)
        else:
            raise AssertionError("Tampered unified graph accepted: " + title)
    print("UNIFIED SEVEN ENGINES: PASS 43 nodes, 7 engines, 9 tamper checks")


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: phase5.py prepare|finalize|audit DIR")
    mode, folder = sys.argv[1:]
    if mode == "prepare":
        prepare(folder)
    elif mode == "finalize":
        doc = make_graph(folder)
        save(Path(folder) / "unified_graph.json", doc)
        print("UNIFIED FINALIZE: PASS", len(doc["nodes"]), "nodes;",
              len(doc["engine_coverage"]), "engines; full lineage in JSON")
    elif mode == "audit":
        audit(folder)
    else:
        raise SystemExit("Unknown phase5 command")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, TypeError, KeyError, ArithmeticError, OSError) as exc:
        print("UNIFIED_ERROR:", str(exc), file=sys.stderr)
        sys.exit(2)
