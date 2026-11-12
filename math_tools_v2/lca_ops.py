"""LCA math operators v0.2: integrals, piecewise time, masked products, event spectra.

A bounded, non-eval, documented *candidate* time model; not the research's
proved node-spectrum theorem. Coefficients originate solely from input factors.
The old Math IR 0.1 workflows are intentionally unchanged.
"""
from __future__ import annotations

from fractions import Fraction
import hashlib
import json
import math
import re
import sys
import warnings
from pathlib import Path

import mpmath as mp
import scipy.integrate as si
from scipy.integrate import IntegrationWarning
import sympy as sp

SCHEMA = "lca-math-operators/0.2"
TOKEN = re.compile(r"-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?\Z")
ID = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,39}\Z")
MAX_CASES, MAX_NODES, MAX_DEPTH = 40, 128, 16
T = sp.Symbol("t", real=True)
UNITS = {"1", "kg", "kgCO2e", "year", "kgCO2e/kg",
         "kgCO2e/year", "m2", "m3", "kgCO2e/m2", "kgCO2e/m3"}


def need(yes, why):
    if not yes:
        raise ValueError(why)


def exact_keys(x, keys, where):
    need(type(x) is dict and set(x) == set(keys), f"{where}: unexpected or missing fields")


def digest(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode()).hexdigest()


def rational(s):
    need(type(s) is str and TOKEN.fullmatch(s) is not None, "Expected exact rational string")
    v = Fraction(s)
    need(v.numerator.bit_length() <= 256 and v.denominator.bit_length() <= 256,
         "Rational exceeds 256 bit limit")
    need(abs(v) <= 10**12, "Rational magnitude exceeds limit")
    return sp.Rational(v.numerator, v.denominator)


def rat_dict(x):
    x = sp.Rational(x)
    return {"numerator": str(x.p), "denominator": str(x.q)}


def unit_dims(unit):
    need(type(unit) is str and unit in UNITS, "Unsupported unit: " + str(unit))
    if unit == "1":
        return {}
    if "/" in unit:
        num, den = unit.split("/")
        a, b = unit_dims(num), unit_dims(den)
        for k, v in b.items():
            a[k] = a.get(k, 0) - v
    else:
        a = {unit: 1}
    return {k: v for k, v in a.items() if v}


def mul_dims(*units):
    result = {}
    for unit in units:
        for k, power in unit_dims(unit).items():
            result[k] = result.get(k, 0) + power
    return {k: v for k, v in result.items() if v}


def expression(tree, depth=0, counter=None):
    if counter is None:
        counter = [0]
    counter[0] += 1
    need(counter[0] <= MAX_NODES and depth <= MAX_DEPTH, "Expression too large/deep")
    need(type(tree) is dict and type(tree.get("op")) is str, "Invalid expression AST")
    op = tree["op"]
    if op == "rational":
        exact_keys(tree, {"op", "value"}, op)
        return rational(tree["value"])
    if op == "integer":
        exact_keys(tree, {"op", "value"}, op)
        return rational(tree["value"])
    if op == "symbol":
        exact_keys(tree, {"op", "name"}, op)
        need(tree["name"] == "t", "Only symbolic time t is supported")
        return T
    if op == "pi":
        exact_keys(tree, {"op"}, op)
        return sp.pi
    if op in {"add", "mul", "sub", "div", "pow"}:
        exact_keys(tree, {"op", "args"}, op)
        args = tree["args"]
        need(type(args) is list and len(args) == 2, "Binary AST operation required")
        a, b = (expression(v, depth+1, counter) for v in args)
        if op == "add":
            return a + b
        if op == "mul":
            return a*b
        if op == "sub":
            return a-b
        if op == "div":
            need(b != 0, "Zero divisor")
            return a/b
        need(b.is_Integer is True and -8 <= int(b) <= 8,
             "Only integer exponents -8..8 supported")
        need(not (a == 0 and b < 0), "Zero negative power")
        return a**b
    if op in {"sin", "cos", "exp", "log", "sqrt", "abs", "neg"}:
        exact_keys(tree, {"op", "arg"}, op)
        a = expression(tree["arg"], depth+1, counter)
        return {"sin": sp.sin, "cos": sp.cos, "exp": sp.exp,
                "log": sp.log, "sqrt": sp.sqrt,
                "abs": sp.Abs, "neg": lambda x: -x}[op](a)
    raise ValueError("Unsupported AST operation: " + str(op))


def real_numeric(x, precision=40):
    z = sp.N(x, precision)
    need(z.is_real is True and z.is_finite is True, "Nonfinite/complex result")
    return str(z)


def result_value(x, unit, approximate=False, extra=None):
    unit_dims(unit)
    data = {"unit": unit}
    if approximate:
        data.update({"kind": "numerical_approximation",
                     "decimal": real_numeric(x)})
    else:
        x = sp.simplify(x)
        if x.is_Rational:
            data.update({"kind": "exact_rational", "value": rat_dict(x)})
        else:
            data.update({"kind": "exact_symbolic", "expression": str(x),
                         "decimal": real_numeric(x)})
    if extra:
        data.update(extra)
    return data


def bounds(item):
    exact_keys(item, {"start", "end"}, "bounds")
    a, b = rational(item["start"]), rational(item["end"])
    need(a < b, "Time/integral interval must be strictly positive")
    return a, b


def supported_domain(expr, a, b):
    # Reject any known real pole/singularity in the closed interval, even
    # if an improper integral might converge. No silent principal values.
    try:
        singular = sp.calculus.util.singularities(expr, T)
        if singular.is_FiniteSet:
            for point in singular:
                if point.is_real and (point-a).is_nonnegative and (b-point).is_nonnegative:
                    raise ValueError("Integral has a singularity in interval")
        elif singular != sp.S.EmptySet:
            raise ValueError("Cannot certify singularity-free finite interval")
    except (NotImplementedError, TypeError) as exc:
        raise ValueError("Cannot analyze integral singularities") from exc
    for t in [a, b, (a+b)/2, a + (b-a)/4, a + 3*(b-a)/4]:
        real_numeric(expr.subs(T, t))


def integrate(expr, a, b):
    need(expr.free_symbols <= {T}, "Unknown symbol in integrand")
    supported_domain(expr, a, b)
    exact = sp.integrate(expr, (T, a, b))
    symbolic = not exact.has(sp.Integral) and exact.is_finite is True
    if symbolic:
        real_numeric(exact)
    try:
        import numpy as np
        numeric_fun = sp.lambdify(T, expr, modules=["numpy"])
        with warnings.catch_warnings():
            warnings.simplefilter("error", IntegrationWarning)
            q, error = si.quad(lambda z: float(numeric_fun(z)),
                               float(a), float(b), epsabs=1e-10, epsrel=1e-10,
                               limit=150)
        need(math.isfinite(q) and math.isfinite(error), "Nonfinite SciPy integral")
        mp.mp.dps = 55
        mp_fun = sp.lambdify(T, expr, modules=["mpmath"])
        mp_result = mp.quad(mp_fun, [mp.mpf(str(a)), mp.mpf(str(b))])
        need(abs(mp.im(mp_result)) < mp.mpf("1e-35"),
             "Complex mpmath result")
        mp_value = float(mp.re(mp_result))
        need(math.isfinite(mp_value) and abs(q-mp_value) <=
             max(1e-8, 1e-8*abs(mp_value)),
             "SciPy/mpmath disagreement; numerical integral not trusted")
    except (OverflowError, ZeroDivisionError, ValueError, TypeError,
            IntegrationWarning) as exc:
        raise ValueError("Unsafe/failed quadrature: " + str(exc)) from exc
    details = {"scipy_quad": format(q, ".17g"),
               "scipy_error_estimate": format(error, ".8g"),
               "mpmath_decimal": mp.nstr(mp_result, 45),
               "precision_note": "Independent numeric check, not certified error bound"}
    if symbolic:
        details["symbolic_method"] = "SymPy definite integral"
        return exact, False, details
    details["symbolic_method"] = "No closed form returned; numeric fallback"
    return sp.Float(mp.nstr(mp_result, 45), 45), True, details


def integrate_piecewise(pieces, a, b):
    need(type(pieces) is list and 1 <= len(pieces) <= 32,
         "Expected 1..32 time segments")
    cursor, total, numerical, rows = a, sp.Integer(0), False, []
    for piece in pieces:
        exact_keys(piece, {"start", "end", "expression"}, "time segment")
        lo, hi = bounds({"start": piece["start"], "end": piece["end"]})
        if hi <= a or lo >= b:
            continue
        left, right = max(a, lo), min(b, hi)
        need(left == cursor, "Overlapping or missing time segment")
        f = expression(piece["expression"])
        val, approx, details = integrate(f, left, right)
        total += val
        numerical = numerical or approx
        rows.append({"start": str(left), "end": str(right),
                     "integral": result_value(val, "1", approx),
                     "numerical_crosscheck": details})
        cursor = right
    need(cursor == b, "Time profile does not cover requested interval")
    return total, numerical, rows


def do_integral(task):
    exact_keys(task, {"id", "operation", "expression", "bounds",
                      "integrand_unit", "variable_unit", "result_unit"},
               "integral task")
    need(unit_dims(task["integrand_unit"]) | {} is not None, "Unexpected unit")
    need(mul_dims(task["integrand_unit"], task["variable_unit"]) ==
         unit_dims(task["result_unit"]), "Integral unit mismatch")
    a, b = bounds(task["bounds"])
    f = expression(task["expression"])
    v, approx, details = integrate(f, a, b)
    return {"result": result_value(v, task["result_unit"], approx),
            "crosscheck": details, "interval": task["bounds"]}


def do_time_function(task):
    exact_keys(task, {"id", "operation", "segments", "interval",
                      "samples", "rate_unit", "time_unit", "result_unit"},
               "time_function task")
    a, b = bounds(task["interval"])
    need(mul_dims(task["rate_unit"], task["time_unit"]) ==
         unit_dims(task["result_unit"]), "Time integral unit mismatch")
    v, approx, parts = integrate_piecewise(task["segments"], a, b)
    sample_rows = []
    need(type(task["samples"]) is list and len(task["samples"]) <= 30, "Invalid samples")
    for point in task["samples"]:
        x = rational(point)
        need(a <= x <= b, "Sample outside time interval")
        found = None
        for piece in task["segments"]:
            lo, hi = bounds({"start": piece["start"], "end": piece["end"]})
            if lo <= x < hi or (x == b and hi == b):
                found = expression(piece["expression"]).subs(T, x)
                break
        need(found is not None, "No time segment for sample")
        sample_rows.append({"t": point,
                            "rate": result_value(found, task["rate_unit"])})
    return {"integral": result_value(v, task["result_unit"], approx),
            "segments": parts, "samples": sample_rows,
            "convention": "Segments are [start,end); last endpoint sampled from last piece"}


def do_masked(task):
    exact_keys(task, {"id", "operation", "groups"}, "masked_sum_product task")
    need(type(task["groups"]) is list and 1 <= len(task["groups"]) <= 24,
         "Expected 1..24 coefficient groups")
    output = {}
    total_terms = 0
    for group in task["groups"]:
        exact_keys(group, {"id", "output_unit", "terms"}, "masked group")
        gid = group["id"]
        need(type(gid) is str and ID.fullmatch(gid) and gid not in output,
             "Invalid/duplicate coefficient ID")
        need(type(group["terms"]) is list and 1 <= len(group["terms"]) <= 100,
             "Invalid number of masked terms")
        total = sp.Integer(0)
        trace = []
        for term in group["terms"]:
            exact_keys(term, {"id", "mask", "factors"}, "masked term")
            need(type(term["mask"]) is int and term["mask"] in (0, 1),
                 "Mask must be integer 0 or 1")
            need(type(term["factors"]) is list and 1 <= len(term["factors"]) <= 8,
                 "Invalid factor count")
            units = []
            product = sp.Integer(term["mask"])
            for factor in term["factors"]:
                exact_keys(factor, {"value", "unit"}, "factor")
                product *= rational(factor["value"])
                units.append(factor["unit"])
            need(mul_dims(*units) == unit_dims(group["output_unit"]),
                 "Masked factor dimensional mismatch")
            total += product
            trace.append({"term_id": term["id"], "mask": term["mask"],
                          "value": rat_dict(product)})
            total_terms += 1
        output[gid] = {"value": rat_dict(total), "unit": group["output_unit"],
                       "terms": trace}
    need(total_terms <= 250, "Too many masked terms")
    return {"coefficients": output, "rule": "Sum_i(mask_i * product_k(factor_ik))",
            "coefficients_source": "Original factor input, never back-fit from baseline"}


def coefficient(ref, computed):
    need(type(ref) is dict and set(ref) == {"task", "group"}, "Invalid coefficient reference")
    task = ref["task"]
    need(task in computed and "coefficients" in computed[task],
         "Coefficient must come from an earlier masked_sum_product task")
    groups = computed[task]["coefficients"]
    need(ref["group"] in groups, "Unknown coefficient group")
    row = groups[ref["group"]]
    node = row["value"]
    return sp.Rational(int(node["numerator"]), int(node["denominator"])), row["unit"]


def do_spectrum(task, computed):
    exact_keys(task, {"id", "operation", "interval", "include_start",
                      "include_end", "events", "periodic", "rates",
                      "result_unit"}, "node_spectrum task")
    a, b = bounds(task["interval"])
    need(type(task["include_start"]) is bool and type(task["include_end"]) is bool,
         "Endpoint inclusion must be boolean")
    output_unit = task["result_unit"]
    unit_dims(output_unit)
    total = sp.Integer(0)
    approx = False
    nodes = []
    components = []
    def inside(x):
        return (x > a or (x == a and task["include_start"])) and (
            x < b or (x == b and task["include_end"]))
    need(type(task["events"]) is list and len(task["events"]) <= 100,
         "Invalid event list")
    for event in task["events"]:
        exact_keys(event, {"id", "at", "coefficient"}, "event")
        date = rational(event["at"])
        amount, unit = coefficient(event["coefficient"], computed)
        need(unit_dims(unit) == unit_dims(output_unit), "Event emission unit mismatch")
        enabled = inside(date)
        if enabled:
            total += amount
            nodes.append({"id": event["id"], "at": str(date),
                          "value": rat_dict(amount), "kind": "event"})
        components.append({"id": event["id"], "included": enabled,
                           "value": rat_dict(amount) if enabled else rat_dict(0)})
    need(type(task["periodic"]) is list and len(task["periodic"]) <= 32,
         "Invalid periodic events")
    for item in task["periodic"]:
        exact_keys(item, {"id", "first", "period", "coefficient"}, "periodic event")
        first, period = rational(item["first"]), rational(item["period"])
        need(period > 0, "Period must be positive")
        need(first >= a, "Periodic start must not precede interval")
        amount, unit = coefficient(item["coefficient"], computed)
        need(unit_dims(unit) == unit_dims(output_unit), "Periodic emission unit mismatch")
        cap = int(sp.floor((b-first)/period))+2 if first <= b else 0
        need(cap <= 2048, "Event spectrum exceeds 2048 candidates")
        count = 0
        for k in range(max(cap, 0)):
            when = first + k*period
            if inside(when):
                total += amount
                nodes.append({"id": item["id"], "at": str(when),
                              "value": rat_dict(amount), "kind": "periodic",
                              "index": k})
                count += 1
        components.append({"id": item["id"], "count": count,
                           "value": rat_dict(amount*count)})
    need(type(task["rates"]) is list and len(task["rates"]) <= 32,
         "Invalid rate profile count")
    for rate in task["rates"]:
        exact_keys(rate, {"id", "coefficient", "profile"}, "continuous rate")
        amount, unit = coefficient(rate["coefficient"], computed)
        need(mul_dims(unit, "year") == unit_dims(output_unit),
             "Continuous rate unit mismatch; expected per-year coefficient")
        integral, estimated, parts = integrate_piecewise(rate["profile"], a, b)
        contribution = amount * integral
        total += contribution
        approx = approx or estimated
        components.append({"id": rate["id"], "kind": "continuous",
                           "coefficient": rat_dict(amount),
                           "profile_integral": result_value(integral, "year", estimated),
                           "contribution": result_value(contribution, output_unit, estimated),
                           "segments": parts})
    need(len(nodes) <= 2048, "Too many event nodes")
    return {"total": result_value(total, output_unit, approx),
            "events": nodes, "components": components,
            "interval": task["interval"],
            "endpoint_policy": {"start_included": task["include_start"],
                                "end_included": task["include_end"]},
            "interpretation": "Discrete event sum + continuous rate integral; candidate model, not proved research equivalence"}


def execute(bundle):
    exact_keys(bundle, {"schema", "tasks"}, "operator bundle")
    need(bundle["schema"] == SCHEMA, "Unsupported operator schema")
    tasks = bundle["tasks"]
    need(type(tasks) is list and 1 <= len(tasks) <= MAX_CASES, "Expected 1..40 tasks")
    computed, entries = {}, []
    for task in tasks:
        need(type(task) is dict, "Invalid task")
        tid = task.get("id")
        need(type(tid) is str and ID.fullmatch(tid) and tid not in computed,
             "Invalid/duplicate task ID")
        kind = task.get("operation")
        if kind == "integral":
            out = do_integral(task)
        elif kind == "time_function":
            out = do_time_function(task)
        elif kind == "masked_sum_product":
            out = do_masked(task)
        elif kind == "node_spectrum":
            out = do_spectrum(task, computed)
        else:
            raise ValueError("Unsupported operation: " + str(kind))
        computed[tid] = out
        entries.append({"id": tid, "operation": kind, "value": out,
                        "task_sha256": digest(task), "result_sha256": digest(out)})
    doc = {"schema": SCHEMA, "input_sha256": digest(bundle),
           "tasks": entries, "execution_order": [r["id"] for r in entries],
           "verification_level": "SymPy exact where available; SciPy and mpmath numerical crosscheck; no general theorem"}
    doc["result_sha256"] = digest(doc)
    return doc


def run(input_file, output_file):
    source = Path(input_file)
    need(source.stat().st_size <= 65536, "Operator input exceeds 64 KiB")
    bundle = json.loads(source.read_text(encoding="utf8"))
    doc = execute(bundle)
    path = Path(output_file)
    need(not path.exists(), "Refusing to overwrite existing result")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    print(f"LCA OPERATORS: PASS {len(doc['tasks'])} tasks, results {path.name}")
    return doc


def verify(input_file, output_file):
    bundle = json.loads(Path(input_file).read_text(encoding="utf8"))
    actual = json.loads(Path(output_file).read_text(encoding="utf8"))
    need(actual == execute(bundle), "Saved operator result differs from independently recomputed source")
    print("LCA OPERATORS VERIFY: PASS independent exact and numerical recomputation")


if __name__ == "__main__":
    try:
        action, *args = sys.argv[1:]
        if action == "run" and len(args) == 2:
            run(*args)
        elif action == "verify" and len(args) == 2:
            verify(*args)
        else:
            raise ValueError("Usage: lca_ops.py run INPUT OUTPUT | verify INPUT OUTPUT")
    except (ValueError, KeyError, TypeError, ArithmeticError, OverflowError) as exc:
        print("LCA_OPERATOR_ERROR:", str(exc), file=sys.stderr)
        sys.exit(2)
