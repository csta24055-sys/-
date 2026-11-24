"""Probe which constructs restricted Math IR 0.1 accepts, by running the real
`math7 prepare` (= main:math_tools_v2/portable.py prepare) on one-case inputs.

Usage: math7-py -B code/probe_ops.py SCRATCH_DIR
Writes probes/*.json (the probe inputs) and results/probes.json (outcomes).
Each probe is a single-case bundle derived from a valid base case.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ir import R, S, add, mul, pw, case  # noqa: E402

F = HERE.parent
x = S("x")


def un(op, *a):
    return {"op": op, "args": list(a)}


BASE = case("probe", add(x, R("1/3")), {"x": 2})


def with_expr(e, **kw):
    c = copy.deepcopy(BASE)
    c["expression"] = e
    c.update(kw)
    return {"schema": "math-ir/0.1", "cases": [c]}


def deep(n):
    e = x
    for _ in range(n):
        e = add(e, R(1))
    return e


PROBES = {
    # ---- expected accepted
    "integer": with_expr(R(7)),
    "rational": with_expr(R("2/7")),
    "negative_rational": with_expr(R("-5/3")),
    "symbol_add": with_expr(add(x, R("1/3"))),
    "mul": with_expr(mul(x, R("9/11"))),
    "pow_int_0": with_expr(pw(x, 0)),
    "pow_int_8": with_expr(pw(x, 8)),
    "subtraction_as_add_mul_minus1": with_expr(add(x, mul(R(-1), R(5)))),
    "division_by_rational_constant": with_expr(mul(x, R("1/3"))),
    "depth_18": with_expr(deep(18)),
    "twenty_cases": {"schema": "math-ir/0.1",
                     "cases": [dict(copy.deepcopy(BASE), case_id=f"c{i}") for i in range(20)]},
    # ---- expected rejected
    "sub": with_expr(un("sub", x, R(1))),
    "div": with_expr(un("div", x, R(3))),
    "neg": with_expr(un("neg", x)),
    "pow_negative_exponent": with_expr({"op": "pow", "args": [x, R(-1)]}),
    "pow_exponent_9": with_expr(pw(x, 9)),
    "pow_rational_exponent_sqrt": with_expr({"op": "pow", "args": [x, R("1/2")]}),
    "pow_symbol_exponent": with_expr({"op": "pow", "args": [R(2), x]}),
    "sqrt": with_expr(un("sqrt", x)),
    "sin": with_expr(un("sin", x)),
    "cos": with_expr(un("cos", x)),
    "exp": with_expr(un("exp", x)),
    "pi_constant": with_expr({"op": "pi"}),
    "floor": with_expr(un("floor", x)),
    "frac": with_expr(un("frac", x)),
    "min": with_expr(un("min", x, R(10))),
    "max": with_expr(un("max", x, R(10))),
    "abs": with_expr(un("abs", x)),
    "lt_comparison": with_expr(un("lt", x, R(10))),
    "piecewise": with_expr({"op": "piecewise", "args": [[R(1), un("lt", x, R(10))], [R(2), True]]}),
    "integral": with_expr({"op": "integral", "args": [x, "x", R(0), R(1)]}),
    "sum_masked": with_expr({"op": "sum", "args": [x]}),
    "add_ternary": with_expr({"op": "add", "args": [x, R(1), R(2)]}),
    "float_literal": with_expr({"op": "float", "value": "0.5"}),
    "noncanonical_rational_2_4": with_expr({"op": "rational", "numerator": "2", "denominator": "4"}),
    "depth_19": with_expr(deep(19)),
    "unit_J": with_expr(add(x, R(1)), unit="J"),
    "unit_kg": with_expr(add(x, R(1)), unit="kg"),
    "exact_false": with_expr(add(x, R(1)), exact=False),
    "symbol_domain_real": None,
    "negative_substitution": None,
    "missing_substitution": None,
    "twenty_one_cases": {"schema": "math-ir/0.1",
                         "cases": [dict(copy.deepcopy(BASE), case_id=f"c{i}") for i in range(21)]},
    "extra_field_expected": None,
}
p = with_expr(add(x, R(1)))
p["cases"][0]["symbols"][0]["domain"] = "real"
PROBES["symbol_domain_real"] = p
p = with_expr(add(x, R(1)))
p["cases"][0]["substitution"]["x"] = R(-2)
PROBES["negative_substitution"] = p
p = with_expr(add(x, R(1)))
p["cases"][0]["substitution"] = {}
PROBES["missing_substitution"] = p
p = with_expr(add(x, R(1)))
p["cases"][0]["expected"] = R(3)
PROBES["extra_field_expected"] = p


def main(scratch: str):
    pdir = F / "probes"
    pdir.mkdir(exist_ok=True)
    out = {}
    for name, bundle in PROBES.items():
        src = pdir / f"{name}.json"
        src.write_text(json.dumps(bundle, indent=1) + "\n")
        od = Path(scratch) / ("probe_" + name)
        r = subprocess.run(["math7", "prepare", str(src), str(od)],
                           capture_output=True, text=True)
        msg = (r.stdout + r.stderr).strip()
        out[name] = {"accepted": r.returncode == 0, "exit": r.returncode,
                     "output": msg, "command": f"math7 prepare probes/{name}.json <scratch>/probe_{name}"}
        print(f"{'ACCEPT' if r.returncode == 0 else 'REJECT'} {name}: {msg}")
    (F / "results").mkdir(exist_ok=True)
    (F / "results" / "probes.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main(sys.argv[1])
