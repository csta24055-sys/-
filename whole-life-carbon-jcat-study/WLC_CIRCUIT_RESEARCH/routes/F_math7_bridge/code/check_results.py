"""Compare a math7 portable output directory with route F's expected-value sidecar.

Usage: math7-py -B code/check_results.py INPUT.json EXPECTED.json MATH7_OUT_DIR REPORT.json

Math7's portable pipeline has NO expected-value field (an extra envelope field is
rejected, see results/probes.json 'extra_field_expected'); it only proves that the
SymPy exact value, the NumPy float64 record, the mpmath decimal record, the fixed
SciPy reference and the DuckDB per-unit sum are mutually consistent and untampered.
This script adds the comparison against the routes' published values, per engine:

  SymPy   : result.json exact rational == expected
  NumPy   : cached float64 hex == float(expected)   (correctly rounded binary64)
  mpmath  : decimal - recorded difference == expected exactly
  SciPy   : N/A per case (Math7 runs ONE fixed x^2 quadrature reference only)
  DuckDB  : per-unit exact group sum == sum of expected values of that unit
  F-Fraction / F-mpmath : route F's own evaluators of the input AST (independent
            of SymPy and of Math7 code) == expected
Exit status 0 only if every case PASSes.
"""
from __future__ import annotations

import json
import sys
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ir import eval_case_fraction, eval_case_mpmath, node_to_fraction  # noqa: E402


def main(inp, side, outdir, report):
    out = Path(outdir)
    cases = json.loads(Path(inp).read_text())["cases"]
    expected = {e["case_id"]: e for e in json.loads(Path(side).read_text())}
    result = json.loads((out / "result.json").read_text())
    graph = json.loads((out / "python_graph.json").read_text())
    exact = {c["case_id"]: node_to_fraction(c["exact"]) for c in result["cases"]}
    rows, unit_expected = [], {}
    import mpmath
    for c in cases:
        cid = c["case_id"]
        e = Fraction(expected[cid]["expected"])
        unit_expected[c["unit"]] = unit_expected.get(c["unit"], Fraction()) + e
        key = graph["cache_keys"]["validated_" + cid]
        payload = json.loads((out / "cache" / f"{key}.json").read_text())["payload"]
        np_val = float.fromhex(payload["numpy"]["hex"])
        mp_dec = Fraction(Decimal(payload["mpmath"]["decimal"]))
        mp_diff = node_to_fraction(payload["mpmath"]["difference_from_exact"])
        f_frac = eval_case_fraction(c)
        with mpmath.workdps(60):
            f_mp = eval_case_mpmath(c)
            f_mp_ok = abs(f_mp - mpmath.mpf(e.numerator) / e.denominator) <= mpmath.mpf(10) ** -45 * max(1, abs(f_mp))
        per = {
            "SymPy": exact[cid] == e,
            "NumPy": np_val == float(e),
            "mpmath": (mp_dec - mp_diff) == e,
            "SciPy": "N/A",
            "F_Fraction": f_frac == e,
            "F_mpmath60": bool(f_mp_ok),
        }
        verdict = all(v is True for k, v in per.items() if k != "SciPy")
        rows.append({"case_id": cid, "unit": c["unit"], "expected": str(e),
                     "math7_exact": str(exact[cid]), "numpy_hex": payload["numpy"]["hex"],
                     "mpmath_decimal": payload["mpmath"]["decimal"][:40],
                     "per_engine": {k: ("PASS" if v is True else "FAIL" if v is False else v)
                                    for k, v in per.items()},
                     "verdict": "PASS" if verdict else "FAIL",
                     "source": expected[cid]["source"], "source_key": expected[cid]["key"]})
    duck = {u: node_to_fraction(g["exact_sum"]) for u, g in result["groups"].items()}
    duck_rows = {u: {"duckdb_exact_sum": str(duck.get(u)), "expected_sum": str(s),
                     "verdict": "PASS" if duck.get(u) == s else "FAIL"}
                 for u, s in unit_expected.items()}
    all_pass = all(r["verdict"] == "PASS" for r in rows) and \
        all(d["verdict"] == "PASS" for d in duck_rows.values())
    rep = {"input": Path(inp).name, "math7_result_sha256": result["sha256"],
           "math7_input_sha256": result["input_sha256"], "mode": result["mode"],
           "engine_coverage": result["engine_coverage"],
           "engine_versions": graph["engine_versions"],
           "cases": rows, "duckdb_groups": duck_rows,
           "overall": "PASS" if all_pass else "FAIL"}
    Path(report).write_text(json.dumps(rep, indent=1) + "\n")
    for r in rows:
        print(r["verdict"], r["case_id"], r["per_engine"])
    for u, d in duck_rows.items():
        print(d["verdict"], "DuckDB group", u, d)
    print("ROUTE-F EXPECTED-VALUE CHECK:", rep["overall"])
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:5]))
