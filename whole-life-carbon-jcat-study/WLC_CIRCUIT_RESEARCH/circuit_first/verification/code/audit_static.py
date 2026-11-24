"""V1 black-box / white-box audit of the snapshot (engine, adapter, model).

1. AST import graph (every import of engine/*.py, adapter.py, model.py) and forbidden roots.
2. AST scan for hidden computation in adapter/model: loops, range/while, floor/ceil/round/
   int()/% on data, float()/Fraction() escapes, `.value` reads, comparisons on data.
3. Raw-input probe: the scenario's numbers are replaced by a Fraction subclass that logs
   every arithmetic/comparison/conversion applied to it before the adapter wraps it.
4. Independent re-count of operations inside the counting type (monkeypatch of Tracked._bin
   with the verifier's own W1/GREY classification).
5. Hiddenness h recomputed with the verifier's own counter from the NETLIST (data elements
   found by perturbing each primitive input; summing-node additions at virtual grounds only;
   data-path switches only), compared with the builder's numbers.
6. Netlist-derived structural signatures (Weisfeiler-Lehman colour refinement, names and
   values removed) vs the builder's self-declared cell signature.
7. Level classification (P0/P1/H/F) and state census of the pilot netlist.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import os
from collections import Counter
from fractions import Fraction as F

from common import SNAP, builder, fstr, save

model, adapter = builder()

PILOT = {"initial": [{"id": "init", "amount": 100, "stage": "A1-A3"}],
         "flows": [{"id": "op", "rate": 4, "stage": "B6"}],
         "items": [{"id": "A", "amount": 20, "period": 10, "stage": "B4"},
                   {"id": "B", "amount": 35, "period": 20, "stage": "B4"}]}
FULL = {"initial": [{"id": "i", "amount": 100, "stage": "A"}],
        "flows": [{"id": "op", "rate": 4, "rate_after": 3, "switch_on": "A", "stage": "B6"},
                  {"id": "dg", "rate": 0, "stage": "B6", "degradation": {"item": "B", "slope": F(1, 2)}}],
        "items": [{"id": "A", "amount": 20, "period": F(5, 2), "explicit": [7], "stage": "B4",
                   "repair": {"base": 20, "rate": F(1, 20), "stage": "B3"}},
                  {"id": "B", "amount": 35, "period": F(10, 3), "stage": "B4"}],
        "renovations": [{"id": "R", "amount": 50, "years": [25], "replaces": ["A", "B"], "policy": "substituted", "stage": "B5"}]}

FILES = [os.path.join(SNAP, "engine", f) for f in sorted(os.listdir(os.path.join(SNAP, "engine"))) if f.endswith(".py")] + \
        [os.path.join(SNAP, "adapter.py"), os.path.join(SNAP, "model.py")]
STDLIB_OK = {"__future__", "fractions", "math", "dataclasses", "typing"}
FORBIDDEN = {"refcalc", "msp", "canon", "tstudy", "synth", "routes", "integration", "registry", "units_b",
             "units_pre_a", "units_c_sum", "psi_compose", "int_common", "numpy", "scipy", "sympy", "subprocess",
             "os", "sys", "importlib", "pickle", "json"}


# ----------------------------------------------------------------- 1/2 AST
def ast_audit():
    graph, findings = {}, []
    for p in FILES:
        src = open(p).read()
        tree = ast.parse(src)
        rel = os.path.relpath(p, SNAP)
        imps = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imps += [(a.name, n.lineno) for a in n.names]
            elif isinstance(n, ast.ImportFrom):
                imps.append(((("." * n.level) + (n.module or "")), n.lineno))
            elif isinstance(n, ast.Call) and getattr(n.func, "id", None) in ("__import__", "exec", "eval", "compile", "open"):
                findings.append({"file": rel, "line": n.lineno, "what": f"dynamic call {n.func.id}"})
        graph[rel] = imps
        for name, ln in imps:
            root = name.lstrip(".").split(".")[0]
            if root in FORBIDDEN:
                findings.append({"file": rel, "line": ln, "what": f"forbidden import {name}"})
            if not name.startswith(".") and root not in STDLIB_OK | {"engine", "adapter", "model"}:
                findings.append({"file": rel, "line": ln, "what": f"non-whitelisted import {name}"})
        if rel in ("adapter.py", "model.py"):
            for n in ast.walk(tree):
                tag = None
                if isinstance(n, (ast.For, ast.While, ast.comprehension)):
                    it = n.iter if hasattr(n, "iter") else None
                    tag = f"loop over {ast.unparse(it)[:60]}" if it is not None else "while loop"
                elif isinstance(n, ast.Call):
                    fn = ast.unparse(n.func)
                    if fn.split(".")[-1] in ("floor", "ceil", "round", "int", "float", "range", "divmod", "Fraction", "max", "min", "sum", "abs"):
                        tag = f"call {fn}({ast.unparse(n)[len(fn)+1:][:50]}"
                elif isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Mod, ast.FloorDiv, ast.Pow)):
                    tag = f"binop {ast.unparse(n)[:60]}"
                elif isinstance(n, ast.Attribute) and n.attr == "value":
                    tag = f".value read: {ast.unparse(n)[:60]}"
                if tag:
                    findings.append({"file": rel, "line": getattr(n, "lineno", None), "what": tag, "kind": "scan"})
    return graph, findings


# ----------------------------------------------------------------- 3 raw-input probe
LOG = []


class Probe(F):
    def _l(self, op, other=None):
        LOG.append((op, str(self), str(other)))

    def __add__(s, o): s._l("+", o); return F.__add__(s, o)
    def __radd__(s, o): s._l("r+", o); return F.__radd__(s, o)
    def __sub__(s, o): s._l("-", o); return F.__sub__(s, o)
    def __rsub__(s, o): s._l("r-", o); return F.__rsub__(s, o)
    def __mul__(s, o): s._l("*", o); return F.__mul__(s, o)
    def __rmul__(s, o): s._l("r*", o); return F.__rmul__(s, o)
    def __truediv__(s, o): s._l("/", o); return F.__truediv__(s, o)
    def __rtruediv__(s, o): s._l("r/", o); return F.__rtruediv__(s, o)
    def __lt__(s, o): s._l("<", o); return F.__lt__(s, o)
    def __le__(s, o): s._l("<=", o); return F.__le__(s, o)
    def __gt__(s, o): s._l(">", o); return F.__gt__(s, o)
    def __ge__(s, o): s._l(">=", o); return F.__ge__(s, o)
    def __float__(s): s._l("float"); return F.__float__(s)
    def __int__(s): s._l("int"); return F.__int__(s)
    def __floor__(s): s._l("floor"); return F.__floor__(s)
    def __ceil__(s): s._l("ceil"); return F.__ceil__(s)
    def __mod__(s, o): s._l("%", o); return F.__mod__(s, o)
    def __neg__(s): s._l("neg"); return F.__neg__(s)
    def __abs__(s): s._l("abs"); return F.__abs__(s)
    def __bool__(s): s._l("bool"); return F.__bool__(s)


def probe(scn):
    def conv(o):
        if isinstance(o, dict):
            return {k: conv(v) for k, v in o.items()}
        if isinstance(o, list):
            return [conv(v) for v in o]
        if isinstance(o, (int, F)) and not isinstance(o, bool):
            return Probe(o)
        return o
    LOG.clear()
    built = adapter.build(conv(scn), adapter.Units(), "original")
    return list(LOG), built


# ----------------------------------------------------------------- 4 own op count inside Tracked
def recount(scn, conv="original"):
    ops = []
    orig = adapter.Tracked._bin

    def spy(self, other, op, rev=False):
        ops.append((self.kind, op, rev, isinstance(other, adapter.Tracked)))
        return orig(self, other, op, rev)
    adapter.Tracked._bin = spy
    try:
        b = adapter.build(scn, adapter.Units(), conv)
    finally:
        adapter.Tracked._bin = orig
    mine = Counter()
    for kind, op, rev, both in ops:
        if both:
            mine["GREY(data op data)"] += 1
        elif kind == "primitive" and op in ("*", "/") and not rev:
            mine["W1"] += 1
        elif kind == "primitive" and op == "*" and rev:
            mine["W1"] += 1
        else:
            mine[f"GREY({kind} {op} rev={rev})"] += 1
    return dict(mine), dict(b.ledger.counts), b


# ----------------------------------------------------------------- 5 hiddenness
def data_elements(scn, conv="right"):
    """Elements whose value changes when ONE primitive numeric input is perturbed."""
    base = {e.name: e for e in adapter.build(scn, adapter.Units(), conv).netlist.elements}

    def paths(o, pre=()):
        if isinstance(o, dict):
            for k, v in o.items():
                yield from paths(v, pre + (k,))
        elif isinstance(o, list):
            for i, v in enumerate(o):
                yield from paths(v, pre + (i,))
        elif isinstance(o, (int, F)) and not isinstance(o, bool):
            yield pre
    changed = {}
    for p in paths(scn):
        s2 = copy.deepcopy(scn)
        o = s2
        for k in p[:-1]:
            o = o[k]
        o[p[-1]] = F(o[p[-1]]) * F(7, 5)
        nl2 = adapter.build(s2, adapter.Units(), conv).netlist
        for e in nl2.elements:
            b = base.get(e.name)
            if b is None:
                continue
            for attr in ("G", "C", "V", "I", "v0"):
                if hasattr(e, attr) and getattr(e, attr) != getattr(b, attr):
                    changed.setdefault(e.name, set()).add("/".join(map(str, p)))
    return changed


def hidden_ratio_mine(built, data_els):
    nl = built.netlist
    by = nl.by_name
    # summing nodes = op-amp inverting inputs (virtual grounds); inputs = non-feedback branches
    adds = 0
    detail = {}
    for oa in [e for e in nl.elements if e.kind == "OA"]:
        x = oa.inn
        ins = [e.name for e in nl.analog() if e.kind in ("R", "SW") and x in e.nodes()
               and not (e.kind == "R" and oa.out in e.nodes())]
        k = max(0, len(ins) - 1)
        adds += k
        detail[x] = len(ins)
    cmps = sum(1 for e in nl.digital() if e.kind == "CMP")
    diodes = sum(1 for e in nl.analog() if e.kind == "D")
    dsw = sum(1 for e in nl.analog() if e.kind == "SW" and e.name in built.datapath)
    W_in = len(data_els) + adds + cmps + diodes + dsw
    return {"W_in": W_in, "parts": {"data_elements": len(data_els), "virtual_ground_additions": adds,
                                    "comparators": cmps, "diodes": diodes, "datapath_switches": dsw},
            "summing_inputs": detail}


# ----------------------------------------------------------------- 6 WL signature
def wl_signature(netlist_json, rounds=5):
    V = {}
    adj = {}

    def vert(k, label):
        V.setdefault(k, label)
        adj.setdefault(k, [])

    def edge(a, b, lab):
        adj[a].append((b, lab)); adj[b].append((a, lab))
    for e in netlist_json:
        k = e["kind"]
        lab = k
        if k == "SW":
            lab += f":inv={e['invert']}"
        if k in ("CMP", "POR"):
            lab += f":p={e['priority']}"
        if k == "GATE":
            lab += f":{e['op']}:{len(e['inputs'])}"
        if k == "CNT":
            lab += f":{e['nbits']}"
        if k == "SEQ":
            lab += f":steps={len(e['steps'])}"
        ev = ("E", e["name"])
        vert(ev, lab)

        def nv(n):
            key = ("N", n)
            vert(key, "GND" if n == "0" else "node")
            return key

        def sv(s):
            key = ("S", s)
            vert(key, "ONE" if s == "ONE" else "ZERO" if s == "ZERO" else "sig")
            return key
        if k == "OA":
            for role in ("inp", "inn", "out"):
                edge(ev, nv(e[role]), role)
        elif k in ("R", "C", "V", "I", "SW", "D", "L"):
            edge(ev, nv(e["a"]), "a"); edge(ev, nv(e["b"]), "b")
            if k == "SW":
                edge(ev, sv(e["ctrl"]), "ctrl")
        elif k == "CMP":
            edge(ev, nv(e["plus"]), "+"); edge(ev, nv(e["minus"]), "-"); edge(ev, sv(e["out"]), "out")
        elif k == "GATE":
            for i in e["inputs"]:
                edge(ev, sv(i), "in")
            edge(ev, sv(e["out"]), "out")
        elif k == "SR":
            edge(ev, sv(e["set"]), "S"); edge(ev, sv(e["reset"]), "R"); edge(ev, sv(e["q"]), "Q")
        elif k == "DFF":
            edge(ev, sv(e["d"]), "D"); edge(ev, sv(e["clk"]), "clk"); edge(ev, sv(e["q"]), "Q")
        elif k == "CNT":
            edge(ev, sv(e["clk"]), "clk")
        elif k == "SEQ":
            edge(ev, sv(e["trigger"]), "trig")
            for s, v in e["idle"].items():
                edge(ev, sv(s), f"idle={v}")
            for i, st in enumerate(e["steps"]):
                for s, v in st.items():
                    edge(ev, sv(s), f"step{i}={v}")
        elif k == "POR":
            edge(ev, sv(e["out"]), "out")
    col = dict(V)
    for _ in range(rounds):
        new = {}
        for v in col:
            nb = sorted(f"{lab}|{col[u]}" for u, lab in adj[v])
            new[v] = hashlib.sha1((col[v] + "#" + ",".join(nb)).encode()).hexdigest()[:16]
        col = new
    ms = Counter(col.values())
    return hashlib.sha1(str(sorted(ms.items())).encode()).hexdigest()[:16], \
        hashlib.sha1(str(sorted(set(col.values()))).encode()).hexdigest()[:16]


# ----------------------------------------------------------------- 7 levels / census
def census(built):
    nl = built.netlist
    caps = [e for e in nl.elements if e.kind == "C"]
    by_cell = Counter((c.tags.get("cell"), c.name.split(".")[-1]) for c in caps)
    kinds = Counter(e.kind for e in nl.elements)
    return {"elements": len(nl.elements), "kinds": dict(kinds), "capacitors_by_cell": {f"{a}/{b}": n for (a, b), n in by_cell.items()}}


def main():
    out = {}
    graph, findings = ast_audit()
    out["import_graph"] = {k: [f"{n}@{l}" for n, l in v] for k, v in graph.items()}
    out["ast_findings_hard"] = [f for f in findings if f.get("kind") != "scan"]
    out["ast_scan_adapter_model"] = [f for f in findings if f.get("kind") == "scan"]
    for nm, scn in (("pilot", PILOT), ("full", FULL)):
        log, built = probe(scn)
        arith = [x for x in log if x[0] not in ("bool",)]
        out[f"raw_input_ops_{nm}"] = {"n": len(log), "ops": Counter(x[0] for x in log), "examples": log[:12]}
        mine, theirs, b = recount(scn)
        out[f"op_recount_{nm}"] = {"verifier": mine, "builder_ledger": theirs}
        de = data_elements(scn)
        h_b = model.hiddenness(b)
        h_m = hidden_ratio_mine(b, de)
        grey = sum(v for k, v in mine.items() if k.startswith("GREY"))
        out[f"hiddenness_{nm}"] = {"builder": {k: (fstr(v) if isinstance(v, F) else v) for k, v in h_b.items()},
                                   "verifier": dict(h_m, W_out=grey, h=fstr(F(grey, h_m["W_in"] + grey))),
                                   "data_elements": {k: sorted(v) for k, v in de.items()}}
    # signatures
    sigs = {}
    U2 = adapter.Units(gamma=F(3), V0=F(2), tau_y=F(5))
    variants = {"pilot/right": (PILOT, "right", adapter.Units()), "pilot/left": (PILOT, "left", adapter.Units()),
                "pilot/original": (PILOT, "original", adapter.Units()), "pilot/right/units2": (PILOT, "right", U2),
                "pilot/original/units2": (PILOT, "original", U2),
                "pilot/right/items_reversed": (dict(PILOT, items=list(reversed(PILOT["items"]))), "right", adapter.Units()),
                "pilot/right/other_values": ({"initial": [{"id": "init", "amount": 7, "stage": "A1-A3"}],
                                             "flows": [{"id": "op", "rate": F(9, 2), "stage": "B6"}],
                                             "items": [{"id": "A", "amount": 3, "period": F(7, 3), "stage": "B4"},
                                                       {"id": "B", "amount": 11, "period": F(11, 5), "stage": "B4"}]},
                                            "right", adapter.Units()),
                "pilot/right/equal_periods": ({"initial": [{"id": "init", "amount": 100, "stage": "A1-A3"}],
                                              "flows": [{"id": "op", "rate": 4, "stage": "B6"}],
                                              "items": [{"id": "A", "amount": 20, "period": 10, "stage": "B4"},
                                                        {"id": "B", "amount": 35, "period": 10, "stage": "B4"}]},
                                             "right", adapter.Units()),
                "full/original": (FULL, "original", adapter.Units()), "full/right": (FULL, "right", adapter.Units())}
    for k, (scn, conv, u) in variants.items():
        b = adapter.build(scn, u, conv)
        exact, schema = wl_signature(b.netlist.to_json())
        sigs[k] = {"wl_multiset": exact, "wl_set(count-free)": schema,
                   "builder_cell_signature": hashlib.sha1(str(sorted(map(str, model.schema_signature(b)))).encode()).hexdigest()[:16],
                   "n_elements": len(b.netlist.elements)}
    out["signatures"] = sigs
    out["census_pilot"] = census(adapter.build(PILOT, adapter.Units(), "right"))
    out["census_pilot_original"] = census(adapter.build(PILOT, adapter.Units(), "original"))
    save("audit_static.json", out)
    return out


if __name__ == "__main__":
    import json
    o = main()
    print(json.dumps({k: o[k] for k in ("ast_findings_hard", "signatures")}, indent=1, default=str))
    for nm in ("pilot", "full"):
        print(nm, json.dumps(o[f"hiddenness_{nm}"]["builder"], default=str)[:400])
        print(nm, json.dumps(o[f"hiddenness_{nm}"]["verifier"], default=str)[:600])
        print(nm, o[f"raw_input_ops_{nm}"]["ops"], o[f"op_recount_{nm}"])
