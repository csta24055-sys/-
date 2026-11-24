"""CF5-style audits runnable in stage A: AST import check, engine vocabulary check, static
adapter checks, full-solution residuals for a CF3 scenario, and mutation tests (each
mutation of a rule must make at least one independent check fail)."""
import ast
import os
import re
import unittest
from fractions import Fraction as F

from _util import ROOT, audit_dump, save

from model import simulate
from test_cf3 import EPS, inside, schedule, total, year_of
from test_pilot import PILOT, ledger as pilot_ledger

FORBIDDEN = {"refcalc", "msp", "canon", "tstudy", "synth", "routes", "integration", "units_b",
             "units_pre_a", "units_c_sum", "registry"}
CODE = [os.path.join(ROOT, "engine", f) for f in sorted(os.listdir(os.path.join(ROOT, "engine"))) if f.endswith(".py")] + \
       [os.path.join(ROOT, "adapter.py"), os.path.join(ROOT, "model.py")]


def imports(path):
    with open(path) as fh:
        tree = ast.parse(fh.read())
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            if n.module:
                out.add(n.module.split(".")[0])
    return out


class Audit(unittest.TestCase):
    def test_ast_imports(self):
        allowed = {"__future__", "fractions", "math", "dataclasses", "typing", "engine", "adapter",
                   "netlist", "linalg", "logic", "mna", "sim", "audit"}
        rep = {}
        for p in CODE:
            im = imports(p)
            rep[os.path.relpath(p, ROOT)] = sorted(im)
            self.assertFalse(im & FORBIDDEN, (p, im & FORBIDDEN))
            self.assertTrue(im <= allowed, (p, im - allowed))
        save("audit_imports.json", rep)

    def test_engine_has_no_domain_vocabulary(self):
        pat = re.compile(r"carbon|emission|wlc|kgco2|building|refrig|renovat|repair|replac|stage|lifecycle|gamma", re.I)
        hits = []
        for p in CODE:
            if os.sep + "engine" + os.sep in p:
                with open(p) as fh:
                    lines = fh.readlines()
                for k, line in enumerate(lines, 1):
                    if pat.search(line):
                        hits.append((os.path.basename(p), k, line.strip()))
        self.assertEqual(hits, [])

    def test_adapter_static_rules(self):
        src = {}
        for p in CODE:
            if os.sep + "engine" + os.sep not in p:
                with open(p) as fh:
                    src[p] = fh.read()
        rep = {}
        for p, s in src.items():
            tree = ast.parse(s)
            whiles = sum(isinstance(n, ast.While) for n in ast.walk(tree))
            ranges = sum(isinstance(n, ast.Call) and getattr(n.func, "id", None) == "range" for n in ast.walk(tree))
            floors = len(re.findall(r"floor|ceil|isqrt", s))
            rep[os.path.basename(p)] = {"while": whiles, "range": ranges, "floor_ceil": floors,
                                        "dot_value_uses": len(re.findall(r"\.value\b", s))}
            self.assertEqual(whiles, 0, p)
            self.assertEqual(ranges, 0, p)
            self.assertEqual(floors, 0, p)
        save("audit_adapter_static.json", rep)

    def test_full_solution_cf3(self):
        scn = {"initial": [{"id": "i", "amount": 100, "stage": "A"}],
               "flows": [{"id": "op", "rate": 4, "rate_after": 3, "switch_on": "A", "stage": "B6"},
                         {"id": "dg", "rate": 0, "stage": "B6", "degradation": {"item": "B", "slope": F(1, 2)}}],
               "items": [{"id": "A", "amount": 20, "period": F(5, 2), "explicit": [7], "stage": "B4",
                          "repair": {"base": 20, "rate": F(1, 20), "stage": "B3"}},
                         {"id": "B", "amount": 35, "period": F(10, 3), "stage": "B4"}],
               "renovations": [{"id": "R", "amount": 50, "years": [25], "replaces": ["A", "B"], "policy": "substituted", "stage": "B5"}]}
        r = simulate(scn, [F(12), F("25.5"), F(30)], "original", record=True)
        d = r["sim"].dump()
        s = audit_dump(self, d)
        # Joule audit: with amplitudes as voltages and negative packets, E != V0*Q (shown, not hidden)
        jt = {str(T): {"datapath_heat": str(v["datapath_heat"]), "V0_Q": str(v["V0_Q"])} for T, v in r["by_T"].items()}
        self.assertNotEqual(r["by_T"][F(30)]["datapath_heat"], r["by_T"][F(30)]["V0_Q"])
        save("cf3_full_solution_original.json", {"audit": s, "joule_audit_fails_here": jt,
                                                  "C": {str(T): str(v["C"]) for T, v in r["by_T"].items()}, "dump": d})


# ----------------------------------------------------------------- mutation tests

B3_25 = {"items": [{"id": "A", "amount": 20, "period": F(5, 2), "stage": "B4",
                    "repair": {"base": 20, "rate": F(1, 20), "stage": "B3"}}]}
B3_05 = {"items": [{"id": "A", "amount": 1, "period": F(1, 2), "stage": "B4",
                    "repair": {"base": 20, "rate": F(1, 20), "stage": "B3"}}]}
RENO = {"initial": [{"id": "i", "amount": 100, "stage": "A"}], "flows": [{"id": "op", "rate": 4, "stage": "B6"}],
        "items": [{"id": "A", "amount": 20, "period": 10, "stage": "B4"}, {"id": "B", "amount": 35, "period": 20, "stage": "B4"}],
        "renovations": [{"id": "R", "amount": 50, "years": [20], "replaces": ["A", "B"], "policy": "substituted", "stage": "B5"}]}
DEG = {"flows": [{"id": "op", "rate": 4, "stage": "B6", "degradation": {"item": "A", "slope": F(1, 2)}}],
       "items": [{"id": "A", "amount": 20, "period": 10, "stage": "B4"}]}


def repair_ledger(T, conv, period, e0r):
    import math
    T = F(T)
    pk, _ = schedule(F(period))
    skip = {year_of(t, conv) for t in pk if inside(t, T, conv)}
    return sum((e0r * min(F(1), T - (y - 1)) for y in range(1, math.ceil(T) + 1) if y not in skip), F(0))


MUTATIONS = {
    # name: (scenario, convention, T, observable, independent expected value)
    "clock_slope_one": (PILOT, "original", F(10) + F(5, 10 ** 9), "C", pilot_ledger(F(10) + F(5, 10 ** 9), "original")),
    "no_lookahead": (B3_25, "original", F(21, 2), "B3", repair_ledger(F(21, 2), "original", F(5, 2), 1)),
    "exclusion_per_event": (B3_05, "original", F(7, 2), "B3", repair_ledger(F(7, 2), "original", F(1, 2), 1)),
    "sequential_simultaneous": (RENO, "right", F(20), "C", total(20, "right", init=100, rate=4,
                                items=[(20, schedule(F(10), subs=[20])[0]), (35, schedule(F(20), subs=[20])[0]), (50, [F(20)])])),
    "lookahead_strict": (B3_25, "right", F(25), "B3", repair_ledger(25, "right", F(5, 2), 1)),
    "age_not_reset": (DEG, "right", F(25), "B6", 4 * 25 + F(1, 2) * (100 + 100 + 25) / 2),
    "readout_order_swapped": (PILOT, "left", F(10), "C", pilot_ledger(10, "left")),
}


class Mutations(unittest.TestCase):
    def _obs(self, r, T, obs):
        v = r["by_T"][T]
        return v["C"] if obs == "C" else v["stages"][obs]

    def test_mutations_detected(self):
        rep = {}
        detected = 0
        for name, (scn, conv, T, obs, exp) in MUTATIONS.items():
            good = self._obs(simulate(scn, [T], conv), T, obs)
            bad = self._obs(simulate(scn, [T], conv, mutations=(name,)), T, obs)
            self.assertEqual(good, exp, name)           # unmutated circuit passes the check
            caught = bad != exp
            detected += caught
            rep[name] = {"T": str(T), "conv": conv, "observable": obs, "expected": str(exp),
                         "unmutated": str(good), "mutated": str(bad), "detected": caught}
        self.assertEqual(detected, len(MUTATIONS), rep)
        save("audit_mutations.json", rep)


if __name__ == "__main__":
    unittest.main()
