"""Route F: tiny helpers to write restricted Math IR 0.1 cases, plus an
INDEPENDENT exact evaluator (fractions.Fraction) that does not import SymPy or
any Math7 code.

Math IR 0.1 grammar as enforced by main:math_interop_v0/phase1.py check_node /
check_envelope (read-only copy at /opt/math7, byte-identical to origin/main
c354037): integer, rational (canonical, den>0), symbol (declared, rational,
nonnegative, substituted), binary add / mul, pow with integer exponent 0..8,
depth <= 18, unit in {"1","kgCO2e"}, exact=true, <= 8 symbols, 1..20 cases.
Nothing else (no sub/div/neg/sqrt/trig/pi/floor/min/max/compare/piecewise).
Subtraction is written as add(a, mul(-1, b)); division only by a rational constant.
"""
from __future__ import annotations

from fractions import Fraction
from math import gcd

SCHEMA = "math-ir/0.1"


def R(value) -> dict:
    """Canonical rational / integer node from int, str or Fraction."""
    f = Fraction(value)
    if f.denominator == 1:
        return {"op": "integer", "value": str(f.numerator)}
    g = gcd(f.numerator, f.denominator)
    return {"op": "rational", "numerator": str(f.numerator // g),
            "denominator": str(f.denominator // g)}


def S(name: str) -> dict:
    return {"op": "symbol", "name": name}


def add(*xs) -> dict:
    """Left-folded binary add (the IR only allows 2 arguments)."""
    out = xs[0]
    for x in xs[1:]:
        out = {"op": "add", "args": [out, x]}
    return out


def mul(*xs) -> dict:
    out = xs[0]
    for x in xs[1:]:
        out = {"op": "mul", "args": [out, x]}
    return out


def pw(x, k: int) -> dict:
    return {"op": "pow", "args": [x, {"op": "integer", "value": str(k)}]}


def neg(x) -> dict:
    return mul(R(-1), x)


def case(case_id: str, expr: dict, subs: dict | None = None, unit: str = "1") -> dict:
    subs = subs or {}
    return {
        "schema": SCHEMA, "case_id": case_id, "expression": expr,
        "symbols": [{"name": k, "domain": "rational", "constraints": ["nonnegative"]}
                    for k in subs],
        "substitution": {k: R(v) for k, v in subs.items()},
        "unit": unit, "exact": True,
    }


# ---------------------------------------------------------------- independent oracle
def eval_fraction(node: dict, env: dict) -> Fraction:
    """Exact evaluation with Python's Fraction; independent of SymPy/phase1."""
    op = node["op"]
    if op == "integer":
        return Fraction(int(node["value"]))
    if op == "rational":
        return Fraction(int(node["numerator"]), int(node["denominator"]))
    if op == "symbol":
        return env[node["name"]]
    a, b = (eval_fraction(x, env) for x in node["args"])
    if op == "add":
        return a + b
    if op == "mul":
        return a * b
    if op == "pow":
        return a ** int(b)
    raise ValueError("unsupported op " + op)


def eval_case_fraction(c: dict) -> Fraction:
    env = {k: eval_fraction(v, {}) for k, v in c["substitution"].items()}
    return eval_fraction(c["expression"], env)


def eval_case_mpmath(c: dict, dps: int = 60):
    """Second independent route: mpmath arbitrary precision (not exact)."""
    import mpmath
    with mpmath.workdps(dps):
        def ev(n, env):
            op = n["op"]
            if op == "integer":
                return mpmath.mpf(int(n["value"]))
            if op == "rational":
                return mpmath.mpf(int(n["numerator"])) / int(n["denominator"])
            if op == "symbol":
                return env[n["name"]]
            a, b = (ev(x, env) for x in n["args"])
            return {"add": lambda: a + b, "mul": lambda: a * b,
                    "pow": lambda: a ** int(b)}[op]()
        env = {k: ev(v, {}) for k, v in c["substitution"].items()}
        return ev(c["expression"], env)


def node_to_fraction(node: dict) -> Fraction:
    return eval_fraction(node, {})
