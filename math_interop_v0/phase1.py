"""Math IR v0.1: exact JSON transfer between SymPy and SageMath.

Experimental, restricted IR. Unknown inputs must fail closed.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path

SCHEMA = "math-ir/0.1"
INTEGER = re.compile(r"(?:0|-?[1-9][0-9]*)\Z")
IDENT = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,31}\Z")
MAX_BITS = 4096


def require(condition, message):
    if not condition:
        raise ValueError(message)


def exact_fields(obj, fields, location):
    require(type(obj) is dict and set(obj) == set(fields), f"Invalid fields at {location}")


def parse_int(value):
    require(type(value) is str and INTEGER.fullmatch(value) is not None, "Noncanonical integer")
    n = int(value)
    require(n.bit_length() <= MAX_BITS, "Integer exceeds limit")
    return n


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(obj):
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def rat_node(num, den=1):
    num, den = int(num), int(den)
    require(den > 0, "Denominator must be positive")
    g = math.gcd(num, den)
    return {"op": "rational", "numerator": str(num // g), "denominator": str(den // g)}


def integer_node(n):
    return {"op": "integer", "value": str(n)}


def symbol_node(name):
    return {"op": "symbol", "name": name}


def calc_node(op, *args):
    return {"op": op, "args": list(args)}


def check_node(node, symbols, depth=0):
    require(depth <= 18, "Expression too deep")
    require(type(node) is dict and type(node.get("op")) is str, "Invalid AST node")
    op = node["op"]
    if op == "integer":
        exact_fields(node, {"op", "value"}, op)
        parse_int(node["value"])
    elif op == "rational":
        exact_fields(node, {"op", "numerator", "denominator"}, op)
        n, d = parse_int(node["numerator"]), parse_int(node["denominator"])
        require(d > 0 and math.gcd(n, d) == 1, "Noncanonical rational")
    elif op == "symbol":
        exact_fields(node, {"op", "name"}, op)
        require(type(node["name"]) is str and node["name"] in symbols, "Unknown symbol")
    elif op in {"add", "mul", "pow"}:
        exact_fields(node, {"op", "args"}, op)
        args = node["args"]
        require(type(args) is list and len(args) == 2, "Only binary operations supported")
        for arg in args:
            check_node(arg, symbols, depth + 1)
        if op == "pow":
            require(args[1].get("op") == "integer", "Only integer exponents supported")
            require(0 <= parse_int(args[1]["value"]) <= 8, "Exponent outside 0..8")
    else:
        raise ValueError(f"Unsupported AST operation: {op}")


def exact_rational(node):
    if node["op"] == "integer":
        return parse_int(node["value"]), 1
    require(node["op"] == "rational", "Expected rational")
    return parse_int(node["numerator"]), parse_int(node["denominator"])


def check_envelope(env):
    exact_fields(env, {"schema", "case_id", "expression", "symbols", "substitution", "unit", "exact"}, "envelope")
    require(env["schema"] == SCHEMA, "Unsupported schema")
    require(type(env["case_id"]) is str and IDENT.fullmatch(env["case_id"]), "Invalid case ID")
    require(env["exact"] is True, "Exact arithmetic required")
    require(env["unit"] in {"1", "kgCO2e"}, "Unknown unit; fail closed")
    require(type(env["symbols"]) is list and len(env["symbols"]) <= 8, "Invalid symbol list")
    names = set()
    for sym in env["symbols"]:
        exact_fields(sym, {"name", "domain", "constraints"}, "symbol metadata")
        require(type(sym["name"]) is str and IDENT.fullmatch(sym["name"]), "Invalid symbol name")
        require(sym["name"] not in names, "Duplicate symbol")
        names.add(sym["name"])
        require(sym["domain"] == "rational", "Unsupported variable domain")
        require(sym["constraints"] == ["nonnegative"], "Unsupported constraints")
    check_node(env["expression"], names)
    require(type(env["substitution"]) is dict and set(env["substitution"]) == names, "Substitution mismatch")
    for value in env["substitution"].values():
        check_node(value, set())
        require(value["op"] in {"integer", "rational"}, "Substitution must be rational")
        require(exact_rational(value)[0] >= 0, "Nonnegative assumption violated")


def make_cases():
    x = {"name": "x", "domain": "rational", "constraints": ["nonnegative"]}

    def case(case_id, expr, value, with_x=False, unit="1"):
        return {"schema": SCHEMA, "case_id": case_id, "expression": expr,
                "symbols": [x] if with_x else [],
                "substitution": {"x": value} if with_x else {},
                "unit": unit, "exact": True}

    cases = [
        case("third_exact", rat_node(1, 3), None, unit="kgCO2e"),
        case("negative_exact", calc_node("add", rat_node(2, 7), rat_node(-5, 3)), None),
        case("boundary_zero", calc_node("pow", calc_node("add", symbol_node("x"), rat_node(1, 3)), integer_node(2)), integer_node(0), True),
        case("rational_input", calc_node("pow", calc_node("add", symbol_node("x"), rat_node(1, 3)), integer_node(2)), rat_node(1, 7), True),
        case("large_integer", calc_node("add", calc_node("mul", integer_node(10**45), symbol_node("x")), rat_node(1, 7)), rat_node(1, 11), True),
    ]
    for one in cases:
        check_envelope(one)
    return {"schema": SCHEMA, "cases": cases}


def sympy_eval(case):
    import sympy as sp
    syms = {s["name"]: sp.Symbol(s["name"], rational=True, nonnegative=True) for s in case["symbols"]}

    def expr(n):
        op = n["op"]
        if op in {"integer", "rational"}:
            a, b = exact_rational(n)
            return sp.Rational(a, b)
        if op == "symbol":
            return syms[n["name"]]
        a, b = (expr(z) for z in n["args"])
        return {"add": lambda: a+b, "mul": lambda: a*b, "pow": lambda: a**b}[op]()

    values = {syms[k]: expr(v) for k, v in case["substitution"].items()}
    out = expr(case["expression"]).subs(values)
    require(out.is_Rational is True, "SymPy result is not exact rational")
    return rat_node(int(out.p), int(out.q))


def sage_eval(case):
    from sage.all import Integer, QQ, var
    syms = {s["name"]: var(s["name"]) for s in case["symbols"]}

    def expr(n):
        op = n["op"]
        if op in {"integer", "rational"}:
            a, b = exact_rational(n)
            return QQ(Integer(a)) / QQ(Integer(b))
        if op == "symbol":
            return syms[n["name"]]
        a, b = (expr(z) for z in n["args"])
        return {"add": lambda: a+b, "mul": lambda: a*b, "pow": lambda: a**b}[op]()

    values = {syms[k]: expr(v) for k, v in case["substitution"].items()}
    result = expr(case["expression"]).subs(values) if values else expr(case["expression"])
    exact = QQ(result)
    return rat_node(exact.numerator(), exact.denominator())


def produce(path):
    bundle = make_cases()
    Path(path).write_text(canonical(bundle) + "\n", encoding="utf-8")
    for case in bundle["cases"]:
        print(case["case_id"], canonical(sympy_eval(case)))


def execute_sage():
    original = json.load(sys.stdin)
    require(type(original) is dict and set(original) == {"schema", "cases"}, "Invalid bundle")
    require(original["schema"] == SCHEMA, "Invalid schema")
    require(type(original["cases"]) is list and 0 < len(original["cases"]) <= 20, "Invalid cases")
    ids, results = set(), []
    for case in original["cases"]:
        check_envelope(case)
        require(case["case_id"] not in ids, "Duplicate case ID")
        ids.add(case["case_id"])
        results.append({"case_id": case["case_id"], "input_sha256": digest(case), "result": sage_eval(case)})
    print(canonical({"schema": SCHEMA, "source": original, "source_sha256": digest(original),
                     "engine": "SageMath", "results": results}))


def verify(input_path, output_path):
    input_obj = json.loads(Path(input_path).read_text(encoding="utf-8"))
    output_obj = json.loads(Path(output_path).read_text(encoding="utf-8"))
    exact_fields(output_obj, {"schema", "source", "source_sha256", "engine", "results"}, "output")
    require(output_obj["engine"] == "SageMath" and output_obj["schema"] == SCHEMA, "Wrong output format")
    require(output_obj["source"] == input_obj, "Original math/assumptions/unit data lost or changed")
    require(output_obj["source_sha256"] == digest(input_obj), "Source digest mismatch")
    require(type(output_obj["results"]) is list, "Missing result list")
    by_id = {r["case_id"]: r for r in output_obj["results"]}
    require(len(by_id) == len(input_obj["cases"]) == len(output_obj["results"]), "Missing/duplicate result")
    for case in input_obj["cases"]:
        check_envelope(case)
        r = by_id[case["case_id"]]
        exact_fields(r, {"case_id", "input_sha256", "result"}, "result")
        require(r["input_sha256"] == digest(case), "Case hash mismatch")
        check_node(r["result"], set())
        require(r["result"]["op"] == "rational", "Float/type corruption detected")
        expected = sympy_eval(case)
        require(r["result"] == expected, f"Mathematical loss in {case['case_id']}")
        print(f"PASS {case['case_id']}: exact {expected['numerator']}/{expected['denominator']}")
    print(f"PHASE 1: PASS {len(by_id)} exact cross-engine cases with metadata/hash checks")


def self_test():
    original = make_cases()["cases"][0]
    corruptions = [
        lambda c: c["expression"].update(denominator="0"),
        lambda c: c.update(expression={"op": "unsafe_eval", "command": "print('bad')"}),
        lambda c: c["expression"].update(numerator="01"),
    ]
    for corrupt in corruptions:
        case = json.loads(canonical(original))
        corrupt(case)
        try:
            check_envelope(case)
        except ValueError:
            continue
        raise AssertionError("Corrupted input accepted")
    print("PASS negative tests: denominator, unknown op, noncanonical integer")


def tamper_test(input_path, output_path):
    """Confirm verifier detects semantic, metadata and lineage corruption."""
    import copy
    import tempfile
    obj = json.loads(Path(output_path).read_text(encoding="utf-8"))
    mutations = {
        "unit": lambda r: r["source"]["cases"][0].update(unit="1"),
        "assumptions": lambda r: r["source"]["cases"][2]["symbols"][0].update(constraints=[]),
        "rational_result": lambda r: r["results"][0]["result"].update(numerator="2"),
        "sha256": lambda r: r.update(source_sha256="0" * 64),
    }
    with tempfile.TemporaryDirectory() as folder:
        candidate = Path(folder) / "tampered.json"
        for label, mutate in mutations.items():
            bad = copy.deepcopy(obj)
            mutate(bad)
            candidate.write_text(canonical(bad), encoding="utf-8")
            try:
                verify(input_path, candidate)
            except (ValueError, KeyError, TypeError):
                print(f"PASS tamper detected: {label}")
            else:
                raise AssertionError(f"Tampering was accepted: {label}")


if __name__ == "__main__":
    try:
        mode = sys.argv[1]
        if mode == "produce" and len(sys.argv) == 3:
            produce(sys.argv[2])
        elif mode == "sage" and len(sys.argv) == 2:
            execute_sage()
        elif mode == "verify" and len(sys.argv) == 4:
            verify(sys.argv[2], sys.argv[3])
        elif mode == "self-test" and len(sys.argv) == 2:
            self_test()
        elif mode == "tamper-test" and len(sys.argv) == 4:
            tamper_test(sys.argv[2], sys.argv[3])
        else:
            raise ValueError("Usage: phase1.py {produce PATH|sage|verify IN OUT|self-test}")
    except (ValueError, KeyError, TypeError) as exc:
        print(f"MATH_IR_ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
