"""Tests of the reference calculation (stdlib unittest).

Run:  cd research_code && python3 -m unittest tests.test_refcalc -v
"""
import collections
import json
import math
import unittest
from pathlib import Path

import synth
from refcalc import registry
from synth import population

registry.load_all()
LEDGER = Path(__file__).resolve().parents[2] / "01_LEDGER" / "units.json"


def close(a, b, tol=1e-9):
    return abs(a - b) <= tol * max(abs(a), abs(b), 1.0)


class ReferenceTests(unittest.TestCase):
    def test_every_computable_ledger_unit_is_registered(self):
        units = json.loads(LEDGER.read_text(encoding="utf-8"))["units"]
        computable = {u["id"] for u in units if u["computable_in_reference"]}
        self.assertEqual(computable, set(registry.UNITS))

    def check_identities(self, scn, res):
        total = res["SUM-03"]["value"]
        everything = sum(res["X-02"]["by_stage_all"].values())
        self.assertTrue(close(res["X-07"]["value"], total), "cumulative series ends at the total")
        self.assertTrue(close(res["X-04"]["value"], everything), "gas breakdown adds up")
        self.assertTrue(close(res["X-08"]["value"], res["B4-02"]["value"]), "cycle groups add up to B4")
        self.assertTrue(close(res["X-09"]["value"], res["C3-01"]["value"] + res["C4-01"]["value"]))
        self.assertTrue(res["X-06"]["matches_table"])
        self.assertTrue(res["QA-01"]["ok"], res["QA-01"]["violations"][:3])
        self.assertLessEqual(res["B3-01"]["value"], res["B3-02"]["value"] * (1 + 1e-12))
        self.assertLessEqual(res["X-05"]["value"], total * (1 + 1e-12))

    def test_edge_cases(self):
        for name, scn in population.edge_cases():
            with self.subTest(case=name):
                res = registry.run_all(scn)
                self.check_identities(scn, res)
                for gate in ("SYS-01", "SYS-02", "SYS-03", "SYS-04", "QA-02", "QA-03", "QA-04", "C-05"):
                    self.assertTrue(res[gate]["ok"], (gate, res[gate]))
                self.assertTrue(res["X-02"]["complete"], res["X-02"]["incomplete_units"])
                self.assertTrue(res["B6-04"]["descriptors_match_tables"])

    def test_benchmark_small(self):
        scn = population.standard_benchmark()[0]
        res = registry.run_all(scn)
        self.check_identities(scn, res)
        self.assertEqual(res["SUM-08"]["status"], "COMPARED")
        self.assertGreater(res["SUM-08"]["saving"], 0.0)

    def test_hand_calculation(self):
        """Tiny case worked by hand: one device, one renewal count, year weights."""
        scn = synth.make_scenario(1, "RC", "office", "S", 10.5, n_materials=1, n_equipment=0, n_refrigerants=1,
                                  composite_share=0.0, epd_share=0.0, profile_kind="CONSTANT", grid_kind="CONSTANT")
        dev = scn.refrigerants[0]
        dev.charge_mass_kg, dev.gwp, dev.annual_leak_rate = 10.0, 100.0, 0.1
        dev.replacement_loss_rate, dev.end_of_life_recovery_rate = 0.5, 0.75
        dev.top_up, dev.change_years, dev.service_life = False, [4], None
        row = scn.materials[0]
        row.refresh_cycle = 3.5   # renewals at 3.5, 7.0 (10.5 is excluded) -> 2
        res = registry.run_all(scn)
        self.assertEqual(res["B4-03"]["by_item"], [2])
        # years 1-4: 10 * (1 - 0.9**4) leaked; change at the end of year 4; years 5-10 plus half of year 11
        first = 10.0 * (1 - 0.9 ** 4)
        m10 = 10.0 * 0.9 ** 6
        second = 10.0 * (1 - 0.9 ** 6) + m10 * 0.1 * 0.5
        self.assertTrue(close(res["B1-02"]["value"], (first + second) * 100.0))
        self.assertTrue(close(res["B1-03"]["value"], 10.0 * 0.9 ** 4 * 0.5 * 100.0))
        self.assertTrue(close(res["B1-04"]["value"], (m10 - m10 * 0.05) * 0.25 * 100.0))
        op = scn.operation
        net = max(0.0, op.electricity.base - (op.onsite_generation.base - op.onsite_export.base))
        self.assertTrue(close(res["B6-03"]["value"] - sum(a * scn.factors[f].value for f, a in res["B6-02"]["_lines"]),
                              net * op.grid.start * 10.5))
        e0 = res["A13-01"]["by_item"][0]
        # repairs skip the renewal years 4 and 7: 10.5 - 2 effective years
        self.assertTrue(close(res["B3-01"]["value"], e0 * row.repair_rate * 8.5))

    def test_nothing_falls_between_b2_and_b6(self):
        """With B2 outside the boundary the facility-management share stays in B6."""
        scn = synth.make_scenario(7, "RC", "office", "S", 60.0, n_materials=12, n_equipment=6, n_refrigerants=4,
                                  included_stages=["A1-A3", "A4", "A5", "B6"])
        res = registry.run_all(scn)
        self.assertGreater(res["B2-01"]["value"], 0.0)
        self.assertTrue(close(res["X-02"]["by_stage"]["B6"], res["B6-03"]["value"]))
        both = synth.make_scenario(7, "RC", "office", "S", 60.0, n_materials=12, n_equipment=6, n_refrigerants=4,
                                   included_stages=["B2", "B6"])
        r2 = registry.run_all(both)
        self.assertTrue(close(r2["X-02"]["by_stage"]["B6"] + r2["X-02"]["by_stage"]["B2"], r2["B6-03"]["value"]))
        self.assertTrue(close(r2["SUM-03"]["value"], res["X-02"]["by_stage"]["B6"]))

    def test_decimal_period_boundary(self):
        scn = synth.make_scenario(21, "S", "retail", "S", 99.9, service_life_choices=[33.3], explicit_event_share=0.0,
                                  change_list_share=0.0, replacement_cycle=33.3, reconstruction_scenario="REBUILD_IDENTICAL",
                                  n_materials=6, n_equipment=3, n_refrigerants=2)
        res = registry.run_all(scn)
        self.assertEqual(set(res["B4-03"]["by_item"]), {2})
        self.assertEqual(res["B5-01"]["n_events"], 2)
        self.assertTrue(all(len(ev) == 2 for ev in res["B4-01"]["events"]))

    def test_wrong_unit_stage_or_range_is_skipped_and_reported(self):
        scn = synth.make_scenario(9, "RC", "office", "S", 60.0, n_materials=12, n_equipment=6, n_refrigerants=4,
                                  composite_share=0.0, epd_share=0.0)
        clean = registry.run_all(scn)
        self.assertTrue(clean["X-02"]["complete"])
        row = scn.materials[0]
        haul = row.end_of_life.haul_factor_id
        scn.factors[haul].unit = "kgkm"                 # no conversion from tkm
        scn.factors[row.transport.factor_id or row.transport.delivery_factor_id].stages = ["A1-A3"]
        scn.materials[1].quantity = -5.0
        scn.operation.gas.unit = "m3/month"
        res = registry.run_all(scn)
        self.assertFalse(res["SYS-02"]["ok"])
        self.assertTrue(res["SYS-02"]["violations"] and res["SYS-02"]["stage_mismatches"])
        self.assertIn("operation.gas", res["SYS-02"]["violations"])
        self.assertGreater(res["C2-01"]["n_skipped"], 0)
        self.assertGreater(res["A13-05"]["n_skipped"], 0)
        self.assertEqual(res["B6-02"]["n_skipped"], 1)
        self.assertFalse(res["X-02"]["complete"])
        self.assertFalse(res["SUM-03"]["complete"])
        self.assertIn("C2-01", res["X-02"]["incomplete_units"])
        self.assertLess(res["C2-01"]["value"], clean["C2-01"]["value"])

    def test_defects_are_detected(self):
        scn = synth.make_scenario(3, "RC", "office", "S", dirty=True)
        res = registry.run_all(scn)
        truth = collections.defaultdict(set)
        for d in scn.meta.injected_defects:
            truth[d.kind].add(d.path)
        self.assertEqual(set(res["SYS-01"]["violations"]), truth["MISSING_VALUE"])
        self.assertEqual(set(res["SYS-02"]["violations"]), truth["UNIT_MISMATCH"])
        self.assertEqual(set(res["SYS-03"]["violations"]), truth["UNKNOWN_LICENCE"])
        self.assertEqual(set(res["C-05"]["violations"]) | set(res["C-05"]["under_allocated"]), truth["ROUTE_FRACTION_SUM"])
        self.assertEqual(set(res["QA-02"]["violations"]), truth["EVENT_OUTSIDE_PERIOD"])
        self.assertEqual(res["A13-02"]["n_invalid"], len(truth["COMPOSITE_FRACTION_SUM"]))
        if truth["NON_POSITIVE_AREA"]:
            self.assertIsNone(res["SUM-04"]["value"])
            self.assertFalse(res["SYS-04"]["ok"])
        self.assertTrue(res["QA-03"]["ok"], "no unlicensed factor may reach a result")
        self.assertTrue(res["QA-01"]["ok"])


if __name__ == "__main__":
    unittest.main()
