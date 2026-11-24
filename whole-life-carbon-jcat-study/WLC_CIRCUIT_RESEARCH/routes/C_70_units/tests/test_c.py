"""Route C tests.  Run:
  cd whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/routes/C_70_units
  PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B -m unittest discover -s tests -v
No network.  Uses the frozen refcalc oracle read-only (only the small S benchmark scenario).
"""
from __future__ import annotations

import copy
import csv
import json
import math
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "code"))
import common as C  # noqa: E402


class LedgerCounts(unittest.TestCase):
    def test_counts(self):
        us = C.units()
        self.assertEqual(len(us), 70)
        roles = {}
        for u in us:
            roles[u["role"]] = roles.get(u["role"], 0) + 1
        self.assertEqual(roles, {"DIRECT": 21, "AUXILIARY": 15, "DECISION": 9, "REFERENCE": 10, "AGGREGATE": 9,
                                 "BREAKDOWN": 6})

    def test_comp_rows(self):
        rows = C.comp_rows()
        self.assertEqual(len(rows), 22)
        self.assertEqual(len({r[0] for r in rows}), 21)
        self.assertEqual([r for r in rows if r[2] != 1 or r[3] != "1"], [("B2-01", "B6", -1, "iota_B2")])

    def test_blocks(self):
        direct = [u for u in C.units() if u["role"] == "DIRECT"]
        seen = set()
        for u in direct:
            b = C.blocks_from_text(u["time_form"])
            self.assertTrue(b, u["id"])
            self.assertNotIn("const_unplaced", b)
            seen |= set(b)
        self.assertEqual(seen, set(C.BLOCKS))


class Rebuild(unittest.TestCase):
    def test_beta_iota_b2(self):
        vals = {u["id"]: 0.0 for u in C.units() if u["role"] == "DIRECT"}
        vals.update({"B2-01": 3.0, "B6-03": 10.0, "A13-01": 100.0})
        all14 = {r[1] for r in C.comp_rows()}
        st, tot = C.rebuild(vals, all14)
        self.assertEqual((st["B2"], st["B6"], tot), (3.0, 7.0, 110.0))
        st, tot = C.rebuild(vals, all14 - {"B2"})
        self.assertEqual((st["B6"], tot), (10.0, 110.0))
        self.assertNotIn("B2", st)
        st, tot = C.rebuild(vals, all14 - {"B6"})
        self.assertEqual((st["B2"], tot), (3.0, 103.0))


class Rank(unittest.TestCase):
    def test_rank_mod_const(self):
        T = [0.1 * j for j in range(1, 101)]
        cols = [[t for t in T], [2 * t + 3 for t in T], [t * t for t in T], [5.0] * len(T)]
        self.assertEqual(C.rank_mod_const(cols, 1e-9)[0], 2)
        noisy = [[t + 1e-14 * math.sin(7 * t) for t in T]]
        self.assertEqual(C.rank_mod_const(cols + noisy, 1e-9)[0], 2)
        self.assertEqual(C.rank_mod_const([[5.0] * 10], 1e-9)[0], 0)


class Signature(unittest.TestCase):
    pc = 8
    grid = [k + (i + 0.5) / 8 for k in range(12) for i in range(8)]

    def sig(self, f, probes=True):
        V = [f(t) for t in self.grid]
        pr = [(f(k + 0.37), f(k + 0.37 + 1e-6)) for k in range(12)] if probes else None
        return set(C.block_signature(self.grid, V, self.pc, pr)["features"])

    def test_const(self):
        self.assertEqual(self.sig(lambda t: 7.0), {"const"})

    def test_year_cell(self):
        amp = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5, 8]
        f = lambda t: sum(amp[k] * min(max(t - k, 0.0), 1.0) for k in range(12))
        s = self.sig(f)
        self.assertEqual(s, {"slope", "int_kink"})
        self.assertTrue(C.fits(s, ["year_cell"]))
        self.assertFalse(C.fits(s, ["atom"]))

    def test_atom(self):
        f = lambda t: 10.0 * sum(1 for n in range(1, 5) if 2.6 * n < t * (1 - 1e-9))
        s = self.sig(f)
        self.assertNotIn("slope", s)
        self.assertTrue(C.fits(s, ["atom"]))
        self.assertFalse(C.fits(s, ["year_cell"]))

    def test_density_plus_gate(self):
        f = lambda t: 2.0 * t - (2.0 * min(max(t - 4, 0.0), 1.0) if t > 4.3 else 0.0)
        s = self.sig(f)
        self.assertTrue({"slope", "inner"} <= s)
        self.assertFalse(C.fits(s, ["density"]))
        self.assertTrue(C.fits(s, ["density", "gated_year_cell"]))


class Oracle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline, cls.scenarios = C.oracle()
        cls.S = cls.scenarios.benchmark()[0]
        cls.direct = list(C.ledger()["role_members"]["DIRECT"])

    def test_frozen_and_registry(self):
        self.assertEqual(sorted(self.baseline.load().UNITS), sorted(u["id"] for u in C.units()))

    def test_hc1_small(self):
        stages = C.refcalc_stages()
        for T in (9.999999, 10.0, 10.000001):
            for inc in (stages, [s for s in stages if s != "B2"]):
                s = copy.deepcopy(self.S)
                s.boundary.study_period = T
                s.boundary.included_lifecycle_stages = list(inc)
                self.assertEqual(self.scenarios.valid_domain(s), [])
                r = self.baseline.run_reference(s, self.direct + ["SUM-03", "X-02"])
                st, tot = C.rebuild({u: r[u]["value"] for u in self.direct}, set(inc))
                self.assertLessEqual(C.rel_err(tot, r["SUM-03"]["value"]), 1e-9)
                self.assertEqual(set(st), set(r["X-02"]["by_stage"]))
                naive = sum(r[u]["value"] for u in self.direct)
                if "B2" in inc:
                    self.assertGreater(C.rel_err(naive, r["SUM-03"]["value"]), 1e-4)

    def test_hc4_small(self):
        clos = C.refcalc_closure("SUM-03")
        for u in ("SYS-01", "SYS-02", "SYS-03", "QA-01", "B3-02", "X-07", "SUM-03"):
            self.assertNotIn(u, clos)
        self.assertIn("A5-01", clos)
        r = self.baseline.run_reference(self.S)
        self.assertLessEqual(C.rel_err(r["X-07"]["value"], r["SUM-03"]["value"]), 1e-9)
        self.assertLessEqual(C.rel_err(r["A5-01"]["value"] + r["A5-02"]["value"] + r["A5-03"]["value"],
                                       r["A5-04"]["value"]), 1e-12)
        self.assertNotIn("value", r["SYS-01"])


class Artifacts(unittest.TestCase):
    def test_mapping(self):
        p = os.path.join(C.ROUTE, "MAPPING.csv")
        if not os.path.exists(p):
            self.skipTest("MAPPING.csv not generated (run code/build_mapping.py)")
        with open(p, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 70)
        self.assertEqual(sorted(r["claim_or_unit_id"] for r in rows), sorted(u["id"] for u in C.units()))
        for r in rows:
            self.assertIn(r["circuit_class"], list("abcde"))
            self.assertIn(r["status"], ("exact", "conditional", "approximate", "unsupported", "unverified"))
            self.assertTrue(r["validation"])
            self.assertTrue(r["state_tuple"].startswith("("))
            if r["role"] == "DIRECT":
                self.assertTrue(r["comp_rows"])
                self.assertIn("NOT_RUN", r["validation"])             # circuit simulation honestly NOT_RUN here
            else:
                self.assertEqual(r["comp_rows"], "")
            if "NOT_RUN" in r["validation"] and "PASS" not in r["validation"] and "CONSISTENT" not in r["validation"]:
                self.assertEqual(r["status"], "unverified")

    def test_mapping_full_time_form(self):
        p = os.path.join(C.ROUTE, "MAPPING.csv")
        if not os.path.exists(p):
            self.skipTest("MAPPING.csv not generated (run code/build_mapping.py)")
        with open(p, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 70)
        ub = C.unit_by_id()
        for r in rows:
            self.assertEqual(r["time_form_text"], ub[r["claim_or_unit_id"]]["time_form"], r["claim_or_unit_id"])
            self.assertTrue(r["construct_class_tuple_evidence"].startswith("[H]"))

    def test_results_verdicts(self):
        for n in ("hc1", "hc2", "hc3", "hc4"):
            p = os.path.join(C.RESULTS, f"{n}.json")
            if not os.path.exists(p):
                continue
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            self.assertIn(d["verdict"].split("(")[0], ("PASS", "FAIL", "PARTIAL"))

    def test_no_stray_pycache(self):
        self.assertEqual(C.stray_pycache(), [])


if __name__ == "__main__":
    unittest.main()
