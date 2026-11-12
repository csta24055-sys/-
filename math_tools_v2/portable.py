"""Portable restricted Math IR: variable case count, one-job Python/full verification.

Only the safe Math IR 0.1 AST is supported. No arbitrary expressions or commands.
Reuses existing phase1, phase2 and phase4 implementation.
"""
from __future__ import annotations
from fractions import Fraction
import json
from pathlib import Path
import sys

CORE = Path(__file__).resolve().parents[1] / "math_interop_v0"
sys.path.insert(0, str(CORE))
import phase1
import phase2
import phase4

SCHEMA = "math-ir-portable/1"
MAX_BYTES = 65536
MAX_CASES = 20
ENGINES = ("SymPy", "NumPy", "SciPy", "mpmath", "DuckDB")


def check(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    p = Path(path)
    check(p.stat().st_size <= MAX_BYTES * 30, "Input/result too large")
    return json.loads(p.read_text(encoding="utf8"))


def save(path, value):
    phase4.write_json(path, value)


def validate_bundle(bundle):
    phase1.exact_fields(bundle, {"schema", "cases"}, "portable input")
    check(bundle["schema"] == phase1.SCHEMA, "Unsupported Math IR schema")
    cases = bundle["cases"]
    check(type(cases) is list and 1 <= len(cases) <= MAX_CASES, "Case count must be 1..20")
    seen = set()
    for case in cases:
        phase1.check_envelope(case)
        check(case["case_id"] not in seen, "Duplicate case ID")
        seen.add(case["case_id"])
    return cases


def make_manifest(bundle):
    return {
        "schema": "math-ir-phase3/1",
        "bundle_sha256": phase1.digest(bundle),
        "cases": [
            {"case_id": c["case_id"], "input_sha256": phase1.digest(c),
             "metadata_sha256": phase1.digest({
                 "unit": c["unit"], "symbols": c["symbols"],
                 "substitution": c["substitution"], "exact": c["exact"]}),
             "unit": c["unit"]}
            for c in bundle["cases"]
        ],
    }


def python_dag(cases, cache):
    dag = phase4.CalcDAG(cache)
    for case in cases:
        cid = case["case_id"]
        src, exact, np, mp, validated = [
            prefix + cid for prefix in
            ("source_", "exact_", "numpy_", "mpmath_", "validated_")]
        dag.eval(src, "canonical_source", "Source", [], {"case": case},
                 lambda d, c=case: c)
        dag.eval(exact, "exact_sympy", "SymPy", [src], {},
                 lambda d, s=src: phase1.sympy_eval(d[s]))
        dag.eval(np, "explicit_binary64", "NumPy", [exact], {"dtype": "float64"},
                 lambda d, e=exact: phase2.numpy_repr(phase2.fraction_of(d[e])))
        dag.eval(mp, "explicit_high_precision", "mpmath", [exact],
                 {"work_dps": phase2.WORK_DPS, "digits": phase2.OUTPUT_DIGITS},
                 lambda d, e=exact: phase2.mpmath_repr(phase2.fraction_of(d[e])))

        def compare(d, s=src, e=exact, n=np, m=mp):
            expected = phase2.case_record(d[s])
            check(d[e] == expected["exact"], "Exact source changed")
            check(d[n] == expected["numpy"], "NumPy precision record changed")
            check(d[m] == expected["mpmath"], "mpmath precision record changed")
            return expected

        dag.eval(validated, "validate_exact_and_approx", "SymPy",
                 [src, exact, np, mp], {}, compare)
    dag.eval("scipy_reference", "quadrature_reference", "SciPy", [],
             {"integral": "x^2 on [0,1]"}, lambda d: phase2.scipy_record())
    ids = ["validated_" + c["case_id"] for c in cases]

    def aggregate(dep):
        # DuckDB does grouping; exact summation uses Fraction, not DOUBLE.
        con = phase2.duckdb.connect(":memory:")
        try:
            con.execute(
                "CREATE TABLE t (case_id VARCHAR, unit VARCHAR, "
                "numerator VARCHAR, denominator VARCHAR)")
            for c in cases:
                r = dep["validated_" + c["case_id"]]
                n, d = r["exact"]["numerator"], r["exact"]["denominator"]
                con.execute("INSERT INTO t VALUES (?, ?, ?, ?)",
                            [c["case_id"], r["unit"], n, d])
            rows = con.execute(
                "SELECT unit,numerator,denominator FROM t ORDER BY unit,case_id"
            ).fetchall()
        finally:
            con.close()
        grouped = {}
        for unit, n, d in rows:
            g = grouped.setdefault(unit, {"count": 0, "total": Fraction()})
            g["count"] += 1
            g["total"] += Fraction(int(n), int(d))
        check(sum(g["count"] for g in grouped.values()) == len(cases),
              "DuckDB row loss")
        return {
            unit: {"count": g["count"],
                   "exact_sum": phase1.rat_node(g["total"].numerator,
                                               g["total"].denominator)}
            for unit, g in sorted(grouped.items())
        }

    groups = dag.eval("duckdb_summary", "grouped_exact_sum", "DuckDB",
                      ids + ["scipy_reference"], {}, aggregate)
    return {
        "schema": SCHEMA, "case_count": len(cases),
        "cache_keys": dag.nodes, "computed": dag.computed,
        "reused": dag.reused, "groups": groups,
        "groups_sha256": phase1.digest(groups),
        "engine_versions": {e: phase4.version(e, "default") for e in ENGINES},
    }


def prepare(source, folder):
    p = Path(folder)
    p.mkdir(parents=True, exist_ok=True)
    check(not (p / "plan.json").exists(), "Refusing to overwrite prior plan")
    source_file = Path(source)
    check(source_file.stat().st_size <= MAX_BYTES, "Input JSON too large")
    bundle = read(source_file)
    cases = validate_bundle(bundle)
    manifest = make_manifest(bundle)
    plan = {
        "schema": SCHEMA, "algorithm": "portable-v1",
        "input_sha256": phase1.digest(bundle),
        "manifest_sha256": phase1.digest(manifest),
        "case_ids": [c["case_id"] for c in cases],
        "case_count": len(cases),
    }
    graph = python_dag(cases, p / "cache")
    check(len(graph["computed"]) == 5 * len(cases) + 2,
          "Python DAG did not execute expected nodes")
    save(p / "input.json", bundle)
    save(p / "manifest.json", manifest)
    save(p / "plan.json", plan)
    save(p / "python_graph.json", graph)
    print(f"PORTABLE PREPARE: PASS {len(cases)} cases, "
          f"{len(graph['computed'])} Python nodes")


def check_remote(bundle, manifest, sage, matlab):
    cases = validate_bundle(bundle)
    check(sage["schema"] == phase1.SCHEMA and
          sage["engine"] == "SageMath", "Bad SageMath schema/engine")
    check(sage["source"] == bundle and
          sage["source_sha256"] == phase1.digest(bundle), "Sage source changed")
    check(matlab["schema"] == "math-ir-phase3/1" and
          matlab["engine"] == "MATLAB", "Bad MATLAB schema/engine")
    check(matlab["bundle_sha256"] == phase1.digest(bundle), "MATLAB source hash changed")
    for rows in (sage["results"], matlab["results"], manifest["cases"]):
        check(type(rows) is list and len(rows) == len(cases),
              "Remote/manifest result count mismatch")
    check(manifest == make_manifest(bundle), "Source metadata manifest changed")
    for c, m, s, t in zip(cases, manifest["cases"],
                           sage["results"], matlab["results"]):
        phase1.exact_fields(s, {"case_id", "input_sha256", "result"}, "sage row")
        phase1.exact_fields(
            t, {"case_id", "input_sha256", "metadata_sha256", "unit",
                "upstream_result", "result"}, "matlab row")
        check(s["case_id"] == t["case_id"] == m["case_id"] == c["case_id"],
              "Result ID/order mismatch")
        check(s["input_sha256"] == t["input_sha256"] ==
              m["input_sha256"] == phase1.digest(c), "Input lineage mismatch")
        check(t["metadata_sha256"] == m["metadata_sha256"] and
              t["unit"] == m["unit"] == c["unit"], "Metadata lost")
        expected = phase1.sympy_eval(c)
        for value in (s["result"], t["upstream_result"], t["result"]):
            phase1.check_node(value, set())
            check(value["op"] == "rational" and value == expected,
                  "Remote exact value mismatch")
    return True


def verify(folder, full, save_output=True):
    p = Path(folder)
    plan, bundle, manifest, initial = [
        read(p / n) for n in
        ("plan.json", "input.json", "manifest.json", "python_graph.json")]
    cases = validate_bundle(bundle)
    check(phase1.digest(bundle) == plan["input_sha256"] and
          phase1.digest(manifest) == plan["manifest_sha256"],
          "Source or manifest hash changed")
    check(plan["case_count"] == len(cases) and
          plan["case_ids"] == [c["case_id"] for c in cases] and
          plan["algorithm"] == "portable-v1", "Source plan changed")
    check(manifest == make_manifest(bundle), "Metadata manifest invalid")
    warm = python_dag(cases, p / "cache")
    check(not warm["computed"] and
          len(warm["reused"]) == 5 * len(cases) + 2,
          "Expected complete Python cache reuse")
    check(warm["cache_keys"] == initial["cache_keys"] and
          warm["groups"] == initial["groups"] and
          initial["groups_sha256"] == phase1.digest(initial["groups"]),
          "Python DAG changed")
    exact_groups = {}
    for c in cases:
        x = phase2.fraction_of(phase1.sympy_eval(c))
        exact_groups[c["unit"]] = exact_groups.get(c["unit"], Fraction()) + x
    check({u: phase2.fraction_of(row["exact_sum"])
           for u, row in warm["groups"].items()} == exact_groups,
          "Independent exact group sum changed")
    if full:
        check_remote(bundle, manifest, read(p / "sage_result.json"),
                     read(p / "matlab_result.json"))
    result = {
        "schema": SCHEMA, "mode": "full-seven" if full else "python-five",
        "case_count": len(cases),
        "input_sha256": phase1.digest(bundle),
        "engine_coverage": list(ENGINES) +
                           (["SageMath", "MATLAB"] if full else []),
        "python_nodes": 5 * len(cases) + 2,
        "python_cache_reused": len(warm["reused"]),
        "groups": warm["groups"],
        "cases": [
            {"case_id": c["case_id"], "unit": c["unit"],
             "exact": phase1.sympy_eval(c),
             "metadata_sha256": manifest["cases"][i]["metadata_sha256"]}
            for i, c in enumerate(cases)
        ],
        "numeric_error_policy": (
            "source exact; NumPy/mpmath errors observed, not certified"),
    }
    result["sha256"] = phase1.digest(result)
    if save_output:
        save(p / "result.json", result)
    print(f"PORTABLE VERIFY: PASS {len(cases)} cases, "
          f"{len(result['engine_coverage'])} engines, "
          f"{len(warm['reused'])} Python cache hits")
    return result


def audit(folder, full):
    p = Path(folder)
    expected = verify(folder, full, False)
    check(read(p / "result.json") == expected,
          "Saved result differs from independently rebuilt source")
    if full:
        for label, filename, modify in [
            ("sage_value", "sage_result.json",
             lambda x: x["results"][0]["result"].update(numerator="999")),
            ("matlab_value", "matlab_result.json",
             lambda x: x["results"][0]["result"].update(numerator="999")),
            ("metadata_unit", "matlab_result.json",
             lambda x: x["results"][0].update(unit="invalid")),
        ]:
            target = p / filename
            original = target.read_bytes()
            try:
                altered = read(target)
                modify(altered)
                save(target, altered)
                try:
                    verify(folder, True, False)
                except (ValueError, KeyError, TypeError):
                    print("PASS tamper rejected:", label)
                else:
                    raise AssertionError("Tamper accepted: " + label)
            finally:
                target.write_bytes(original)
    print("PORTABLE AUDIT: PASS full source reconstruction")


def main():
    args = sys.argv[1:]
    if len(args) == 3 and args[0] == "prepare":
        prepare(args[1], args[2])
    elif len(args) == 2 and args[0] in {
        "verify-full", "verify-python", "audit-full", "audit-python"
    }:
        action, folder = args
        (audit if action.startswith("audit") else verify)(
            folder, action.endswith("full"))
    else:
        raise SystemExit(
            "Usage: portable.py prepare REPO_JSON DIR | "
            "verify-full|verify-python|audit-full|audit-python DIR")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, TypeError, KeyError, OSError, ArithmeticError) as exc:
        print("PORTABLE_ERROR:", str(exc), file=sys.stderr)
        sys.exit(2)
