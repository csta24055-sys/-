"""V2 audit of the building adapter (snapshot 80ec2de).

1. AST import graph of adapter_building.py, model_building.py, adapter_nmax.py, engine/dc.py,
   engine/hybrid.py (and the rest of the engine): forbidden roots, dynamic imports.
2. AST scan of adapter_building.py: every `.value` read (escape from the counting type), every
   loop with its iterable, every comparison/arithmetic on raw scenario fields.
3. Raw-input probe: every float/int field of the scenario is replaced by a logging subclass;
   any arithmetic, comparison, conversion done on a RAW field (before wrapping) is recorded
   with the adapter line that did it.
4. Netlist-derived counts for h: virtual-ground additions, comparators, diodes, sequencer
   phase steps, priority classes, gates; compared with the builder's ledger.
5. Structure census: elements and op-amps per input row, inverters, products required by L1.
"""
from __future__ import annotations

import ast
import copy
import dataclasses
import json
import os
import sys
import traceback
from collections import Counter
from fractions import Fraction as Fr

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import SNAP, save  # noqa: E402

STUDY = "/home/user/-/whole-life-carbon-jcat-study"
sys.path.insert(0, os.path.join(STUDY, "10_TRANSFORM_STUDY", "research_code"))
from tstudy import baseline, scenarios  # noqa: E402

FROZEN = baseline.assert_frozen()
sys.path.insert(0, SNAP)
import adapter_building as ab  # noqa: E402
import model_building as mb  # noqa: E402

FORBIDDEN = {"refcalc", "msp", "canon", "tstudy", "synth", "routes", "integration", "registry", "units_b",
             "units_pre_a", "units_c_sum", "compare_refcalc", "compare_stageB_e", "numpy", "scipy", "sympy",
             "subprocess", "importlib", "pickle"}
FILES = ["adapter_building.py", "model_building.py", "adapter_nmax.py", "adapter.py", "model.py"] + \
        [os.path.join("engine", f) for f in sorted(os.listdir(os.path.join(SNAP, "engine"))) if f.endswith(".py")]


def ast_part():
    graph, bad, scan = {}, [], Counter()
    detail = []
    for rel in FILES:
        p = os.path.join(SNAP, rel)
        if not os.path.exists(p):
            continue
        tree = ast.parse(open(p).read())
        imps = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imps += [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom):
                imps.append("." * n.level + (n.module or ""))
            elif isinstance(n, ast.Call) and getattr(n.func, "id", None) in ("__import__", "exec", "eval", "compile"):
                bad.append((rel, n.lineno, "dynamic"))
            elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "__import__":
                pass
        # __import__("engine") used inside adapter_building (VCCS construction): record
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "__import__":
                arg = ast.unparse(n.args[0]) if n.args else ""
                bad.append((rel, n.lineno, f"__import__({arg})"))
        graph[rel] = imps
        for name in imps:
            if name.lstrip(".").split(".")[0] in FORBIDDEN:
                bad.append((rel, None, f"forbidden import {name}"))
        if rel == "adapter_building.py":
            for n in ast.walk(tree):
                if isinstance(n, ast.Attribute) and n.attr == "value":
                    scan[".value"] += 1
                    detail.append((n.lineno, ".value", ast.unparse(n)[:60]))
                elif isinstance(n, (ast.For, ast.comprehension)):
                    it = ast.unparse(n.iter)[:70]
                    scan["loop"] += 1
                    detail.append((getattr(n, "lineno", getattr(n.iter, "lineno", None)), "loop", it))
                elif isinstance(n, ast.While):
                    scan["while"] += 1
                    detail.append((n.lineno, "while", ""))
                elif isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Mod, ast.FloorDiv, ast.Pow, ast.RShift, ast.BitAnd)):
                    detail.append((n.lineno, "binop", ast.unparse(n)[:60]))
    return graph, bad, scan, sorted(detail, key=lambda x: (x[0] or 0))


LOG = Counter()
SITES = Counter()


def _site():
    for fr in reversed(traceback.extract_stack()[:-2]):
        if "cf_snapshot" in fr.filename:
            return f"{os.path.basename(fr.filename)}:{fr.lineno}"
    return "other"


class LF(float):
    def _l(self, op):
        LOG[op] += 1
        SITES[(op, _site())] += 1

    def __add__(s, o): s._l("+"); return float.__add__(s, o)
    def __radd__(s, o): s._l("+"); return float.__radd__(s, o)
    def __sub__(s, o): s._l("-"); return float.__sub__(s, o)
    def __rsub__(s, o): s._l("-"); return float.__rsub__(s, o)
    def __mul__(s, o): s._l("*"); return float.__mul__(s, o)
    def __rmul__(s, o): s._l("*"); return float.__rmul__(s, o)
    def __truediv__(s, o): s._l("/"); return float.__truediv__(s, o)
    def __rtruediv__(s, o): s._l("/"); return float.__rtruediv__(s, o)
    def __lt__(s, o): s._l("cmp"); return float.__lt__(s, o)
    def __le__(s, o): s._l("cmp"); return float.__le__(s, o)
    def __gt__(s, o): s._l("cmp"); return float.__gt__(s, o)
    def __ge__(s, o): s._l("cmp"); return float.__ge__(s, o)
    def __eq__(s, o): s._l("eq"); return float.__eq__(s, o)
    def __ne__(s, o): s._l("eq"); return float.__ne__(s, o)
    __hash__ = float.__hash__
    def __int__(s): s._l("int"); return float.__int__(s)
    def __round__(s, *a): s._l("round"); return float.__round__(s, *a)
    def __bool__(s): s._l("bool"); return float.__bool__(s)


class LI(int):
    def _l(self, op):
        LOG["int:" + op] += 1
        SITES[("int:" + op, _site())] += 1

    def __add__(s, o): s._l("+"); return int.__add__(s, o)
    def __radd__(s, o): s._l("+"); return int.__radd__(s, o)
    def __sub__(s, o): s._l("-"); return int.__sub__(s, o)
    def __rsub__(s, o): s._l("-"); return int.__rsub__(s, o)
    def __mul__(s, o): s._l("*"); return int.__mul__(s, o)
    def __rmul__(s, o): s._l("*"); return int.__rmul__(s, o)
    def __lt__(s, o): s._l("cmp"); return int.__lt__(s, o)
    def __le__(s, o): s._l("cmp"); return int.__le__(s, o)
    def __gt__(s, o): s._l("cmp"); return int.__gt__(s, o)
    def __ge__(s, o): s._l("cmp"); return int.__ge__(s, o)
    def __eq__(s, o): s._l("eq"); return int.__eq__(s, o)
    def __ne__(s, o): s._l("eq"); return int.__ne__(s, o)
    __hash__ = int.__hash__
    def __rshift__(s, o): s._l(">>"); return int.__rshift__(s, o)
    def __and__(s, o): s._l("&"); return int.__and__(s, o)


WRAPPED = Counter()


def wrap(o, seen=None):
    if isinstance(o, float) and not isinstance(o, LF):
        WRAPPED["float"] += 1
        return LF(o)
    if isinstance(o, int) and not isinstance(o, (bool, LI)):
        WRAPPED["int"] += 1
        return LI(o)
    if dataclasses.is_dataclass(o) and not isinstance(o, type):
        for f in dataclasses.fields(o):
            object.__setattr__(o, f.name, wrap(getattr(o, f.name)))
        return o
    if isinstance(o, list):
        return [wrap(x) for x in o]
    if isinstance(o, dict):
        return {k: wrap(v) for k, v in o.items()}
    return o


def probe(scn):
    LOG.clear(); SITES.clear(); WRAPPED.clear()
    s = wrap(copy.deepcopy(scn))
    LOG["_wrapped_float_fields"] = WRAPPED["float"]
    LOG["_wrapped_int_fields"] = WRAPPED["int"]
    LOG["_check_type_quantity"] = type(s.materials[0].quantity).__name__ if s.materials else None
    out = mb.simulate_building(s, [Fr(1, 2)], "original")
    return dict(LOG), {f"{op} @ {site}": n for (op, site), n in SITES.most_common(40)}, out


def netcounts(out):
    nl_a, nl_c = out["A"].nl, out["core"].nl
    def vg(nl):
        adds = 0
        for oa in [e for e in nl.elements if e.kind == "OA"]:
            ins = [e for e in nl.analog() if e.kind in ("R", "SW") and oa.inn in e.nodes() and not (oa.out in e.nodes())]
            adds += max(0, len(ins) - 1)
        return adds
    seqs = [e for e in nl_c.digital() if e.kind == "SEQ"]
    prios = sorted({e.priority for e in nl_c.digital() if e.kind in ("CMP", "POR")} | {0})
    return {"crossbar_elements": len(nl_a.elements), "crossbar_opamps": sum(e.kind == "OA" for e in nl_a.elements),
            "crossbar_inverters": sum(1 for e in nl_a.elements if e.kind == "OA" and e.tags.get("cell") == "inverter"),
            "crossbar_vg_additions": vg(nl_a), "core_elements": len(nl_c.elements),
            "core_vg_additions": vg(nl_c), "core_comparators": sum(e.kind == "CMP" for e in nl_c.digital()),
            "core_diodes": sum(e.kind == "D" for e in nl_c.analog()), "core_capacitors": sum(e.kind == "C" for e in nl_c.analog()),
            "core_opamps": sum(e.kind == "OA" for e in nl_c.analog()), "core_switches": sum(e.kind == "SW" for e in nl_c.analog()),
            "sequencers": len(seqs), "sequencer_phase_steps": sum(len(s.steps) for s in seqs),
            "gates": sum(e.kind == "GATE" for e in nl_c.digital()), "latches_dff": sum(e.kind in ("SR", "DFF") for e in nl_c.digital()),
            "priority_classes_incl_readout": prios + ["readout 0/100", "post phase"]}


def rows_census(scn):
    return {"materials": len(scn.materials), "equipment": len(scn.equipment), "refrigerants": len(scn.refrigerants),
            "fuels": len(scn.construction.fuels), "site_waste": len(scn.construction.waste_streams),
            "demolition": len(scn.end_of_life.demolition_activities), "hauls": len(scn.end_of_life.waste_hauls),
            "factors": len(scn.factors), "composite_rows": sum(1 for m in scn.materials if m.composition is not None),
            "numeric_fields": count_numeric(scn)}


def count_numeric(o):
    if isinstance(o, bool):
        return 0
    if isinstance(o, (int, float)):
        return 1
    if dataclasses.is_dataclass(o) and not isinstance(o, type):
        return sum(count_numeric(getattr(o, f.name)) for f in dataclasses.fields(o))
    if isinstance(o, (list, tuple)):
        return sum(count_numeric(x) for x in o)
    if isinstance(o, dict):
        return sum(count_numeric(x) for x in o.values())
    return 0


def main():
    res = {"frozen": FROZEN}
    graph, bad, scan, detail = ast_part()
    res["imports"] = graph
    res["import_findings"] = bad
    res["adapter_building_scan"] = dict(scan)
    res["adapter_building_scan_detail"] = detail
    bm = scenarios.benchmark()
    ev = scenarios.evaluation_set(10)
    for key, scn in (("S", bm[0]), ("E1", ev[1])):
        ops, sites, out = probe(scn)
        cnt = mb.audit_counts(out)
        res[key] = {"raw_field_ops": ops, "raw_field_op_sites": sites, "netlist_counts": netcounts(out),
                    "builder_counts": {k: cnt[k] for k in ("h", "h_amp", "h_time", "W_in_amp", "W_in_time", "W_out_amp", "W_out_time")},
                    "builder_ledger_by_layer": cnt["ops_by_layer"], "grey_by_kind": cnt["grey_by_kind"],
                    "control": cnt["control_not_counted_in_h"], "rows": rows_census(scn), "size": cnt["size"]}
        print(key, json.dumps({k: res[key][k] for k in ("raw_field_ops", "netlist_counts", "builder_counts", "grey_by_kind", "rows")}, default=str)[:2500], flush=True)
        print(key, "sites", json.dumps(sites)[:1500], flush=True)
    save("v2_audit.json", res)


if __name__ == "__main__":
    main()
