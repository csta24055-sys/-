"""Tests of the reference calculation (stdlib unittest).

Run:  cd research_code && python3 -m unittest tests.test_refcalc -v
"""
import collections
import copy
import json
import math
import unittest
from pathlib import Path

import synth
from refcalc import base, registry, units_c_sum
from synth import model, population

registry.load_all()
LEDGER = Path(__file__).resolve().parents[2] / "01_LEDGER" / "units.json"
SMALL = {"n_materials": 12, "n_equipment": 6, "n_refrigerants": 4}
NAN, INF = float("nan"), float("inf")


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


def make(seed=11, period=60.0, **options):
    opts = dict(SMALL)
    opts.update(options)
    return synth.make_scenario(seed, "RC", "office", "S", period, **opts)


class DefinitionTests(unittest.TestCase):
    """The rules fixed after the second independent re-check."""

    def test_ledger_text_is_the_docstring(self):
        units = {u["id"]: u for u in json.loads(LEDGER.read_text(encoding="utf-8"))["units"]}
        for uid, ref in registry.UNITS.items():
            self.assertEqual(units[uid]["reference_semantics"], "".join(line.strip() for line in ref.doc.splitlines()), uid)
            self.assertEqual(units[uid]["depends_on"], sorted(ref.depends_on), uid)

    def test_units_read_only_their_declared_dependencies(self):
        """The completeness rule follows the declared data flow, so the declarations must be true."""
        class Recording(dict):
            def __init__(self, data):
                super().__init__(data)
                self.read = set()

            def __getitem__(self, key):
                self.read.add(key)
                return super().__getitem__(key)

            def get(self, key, default=None):
                self.read.add(key)
                return super().get(key, default)

        scenarios = [population.standard_benchmark()[0], make(included_stages=["B6"]), make(dirty=True)]
        scenarios.append(make(replacement_cycle=25.0, reconstruction_scenario="REBUILD_IDENTICAL", profile_kind="TABLE"))
        for scn in scenarios:
            base.check_period(scn)
            res = {}
            for uid in registry.order():
                view = Recording(res)
                res[uid] = registry.UNITS[uid].fn(scn, view)
                self.assertTrue(view.read <= set(registry.UNITS[uid].depends_on), (uid, sorted(view.read - set(registry.UNITS[uid].depends_on))))

    def test_x02_reads_exactly_the_units_that_flow_into_a_stage(self):
        everything = set()
        for stage in base.STAGES:
            everything |= set(units_c_sum.stage_upstream(stage))
        self.assertEqual(set(registry.UNITS["X-02"].depends_on), everything)
        self.assertNotIn("B2-01", units_c_sum.stage_upstream("B6", b2_included=False))
        self.assertIn("B2-01", units_c_sum.stage_upstream("B6"))
        for uid in ("A13-01", "A13-03", "X-01", "A13-05", "X-15", "B4-01", "B4-03"):
            self.assertIn(uid, units_c_sum.stage_upstream("B3"))
        for uid in ("A13-04", "A5-01", "C1-01", "X-14", "A4-02"):
            self.assertIn(uid, units_c_sum.stage_upstream("B5"))

    def test_period_1_000000001_follows_the_written_rule(self):
        """In exact arithmetic event n of this period lies in year n + 1: 59 events, 59 distinct years for T = 60."""
        scn = make(1, service_life_choices=[1.000000001], explicit_event_share=0.0, change_list_share=0.0)
        res = registry.run_all(scn)
        self.assertEqual(set(res["B4-03"]["by_item"]), {59})
        for years in res["B4-01"]["events"]:
            self.assertEqual(years, list(range(2, 61)))
        # repairs: only year 1 is free of a renewal
        e0 = sum(res["A13-01"]["by_item"][i] + res["A13-03"]["by_item"][i] for i in range(len(scn.materials)))
        rate_sum = sum((res["A13-01"]["by_item"][i] + res["A13-03"]["by_item"][i]) * row.repair_rate
                       for i, row in enumerate(scn.materials))
        rate_sum += sum(res["X-01"]["by_item"][j] * eq.repair_rate for j, eq in enumerate(scn.equipment))
        self.assertGreater(e0, 0.0)
        self.assertTrue(close(res["B3-01"]["value"], rate_sum * 1.0))
        self.assertTrue(res["QA-01"]["ok"])
        self.assertTrue(close(sum(res["B3-01"]["by_year"]), res["B3-01"]["value"]))

    def test_invalid_cycles_are_counted_and_missing_ones_are_not(self):
        scn = make(replacement_cycle=25.0, reconstruction_scenario="REBUILD_IDENTICAL", explicit_event_share=0.0,
                   change_list_share=0.0)
        clean = registry.run_all(scn)
        self.assertTrue(clean["X-02"]["complete"])
        self.assertEqual((clean["B4-01"]["n_invalid"], clean["B4-03"]["n_invalid"]), (0, 0))
        scn.materials[0].refresh_cycle = None                      # "not renewed": nothing is counted
        scn.equipment[0].service_life = None
        res = registry.run_all(scn)
        self.assertEqual((res["B4-01"]["n_invalid"], res["B4-03"]["n_invalid"]), (0, 0))
        self.assertEqual(res["B4-03"]["by_item"][0], 0)
        self.assertTrue(res["X-02"]["complete"])
        self.assertIn("materials[0].refresh_cycle", res["SYS-01"]["violations"])
        for bad in (-5.0, 0.0, NAN, INF):
            scn.materials[1].refresh_cycle = bad
            scn.equipment[1].service_life = bad
            scn.refrigerants[0].service_life, scn.refrigerants[0].change_years = bad, None
            res = registry.run_all(scn)
            self.assertEqual((res["B4-01"]["n_invalid"], res["B4-03"]["n_invalid"]), (1, 1), bad)
            self.assertEqual(res["B4-03"]["by_item"][1], 0)
            self.assertEqual(res["B4-01"]["events"][1], [])
            self.assertEqual(res["B1-02"]["n_skipped"], 1, bad)
            self.assertFalse(res["X-02"]["complete"])
            for uid in ("B4-01", "B4-03", "B1-02", "B1-03", "B1-04"):
                self.assertIn(uid, res["X-02"]["incomplete_units"], (uid, bad))
        for bad in (None, -25.0, 0.0, NAN, INF):                   # a rebuild scenario needs a finite positive cycle
            scn.boundary.replacement_cycle = bad
            res = registry.run_all(scn)
            self.assertFalse(res["B5-01"]["computed"], bad)
            self.assertIn("B5-01", res["X-02"]["incomplete_units"])
        scn.boundary.reconstruction_scenario = "NONE"              # without a rebuild the cycle is not used at all
        self.assertTrue(registry.run_all(scn)["B5-01"]["computed"])

    def test_explicit_lists_with_missing_or_repeated_entries(self):
        scn = make(explicit_event_share=1.0, change_list_share=1.0)
        scn.equipment[0].replacement_event_list = [None, 10, NAN, 20]
        scn.equipment[1].replacement_event_list = [15, 15, 15.0]
        scn.equipment[2].replacement_event_list = [0, 30]
        scn.refrigerants[0].change_years = [INF, 7]
        res = registry.run_all(scn)
        self.assertEqual(res["B4-01"]["events"][0], [10, 20])
        self.assertEqual(res["B4-01"]["events"][1], [15, 15, 15])        # listed three times: counted three times
        self.assertEqual(res["B4-01"]["events"][2], [30])
        self.assertIn("equipment[0].replacement_event_list", res["QA-02"]["violations"])
        self.assertIn("refrigerants[0].change_years", res["QA-02"]["violations"])
        self.assertNotIn("equipment[1].replacement_event_list", res["QA-02"]["violations"])
        self.assertIn("equipment[1].replacement_event_list", res["QA-02"]["warnings"])
        self.assertIn("equipment[2].replacement_event_list", res["QA-02"]["warnings"])
        self.assertEqual(len(res["QA-02"]["warnings"]), len(set(res["QA-02"]["warnings"])))

    def test_unusable_factor_values_and_conversions_are_skipped_and_counted(self):
        for bad in (NAN, INF, -5.0, None):
            scn = make(composite_share=0.0, epd_share=0.0)
            fid = scn.materials[2].factor_id
            users = [i for i, row in enumerate(scn.materials) if row.factor_id == fid]
            scn.factors[fid].value = bad
            res = registry.run_all(scn)
            self.assertEqual(res["A13-01"]["n_skipped"], len(users), bad)
            self.assertTrue(all(res["A13-01"]["by_item"][i] == 0.0 for i in users))
            self.assertFalse(res["X-02"]["complete"])
            self.assertTrue(math.isfinite(res["SUM-03"]["value"]))
            scn = make(composite_share=0.0, epd_share=0.0)
            scn.factors[fid].gas_amounts["CH4"] = bad                    # a gas amount counts like the value
            res = registry.run_all(scn)
            self.assertEqual(res["A13-01"]["n_skipped"], len(users), bad)
            self.assertTrue(res["QA-01"]["ok"])
        for bad in (NAN, INF, -2.0, 0.0, None):
            scn = make(composite_share=1.0, epd_share=0.0)
            row = next(r for r in scn.materials if r.conversions)
            i = scn.materials.index(row)
            row.conversions[0].factor = bad
            res = registry.run_all(scn)
            self.assertIsNone(res["X-15"]["conv"][i], bad)
            self.assertGreaterEqual(res["A13-01"]["n_skipped"], 1)
            self.assertIn(f"materials[{i}].quantity_unit", res["SYS-02"]["violations"])
            self.assertTrue(math.isfinite(res["SUM-03"]["value"]))
        self.assertIsNone(model.conversion_factor([model.UnitConversion("a", "b", NAN, "")], "a", "b"))
        table = [model.UnitConversion("a", "b", 2.0, "")]
        self.assertEqual(model.conversion_factor(table, "a", "b"), 2.0)
        self.assertIsNone(model.conversion_factor(table, "a", "b", [model.UnitConversion("a", "b", -1.0, "")]))  # no fall-through

    def test_unusable_annual_series_are_skipped_and_counted(self):
        for bad in (NAN, INF, -1.0):
            scn = make(profile_kind="LINEAR_TREND")
            scn.operation.gas.base = bad
            scn.water_waste.sewage.slope = bad if bad != -1.0 else -1e9
            res = registry.run_all(scn)
            self.assertEqual(res["B6-02"]["n_skipped"], 1, bad)
            self.assertEqual(res["B7-02"]["n_skipped"], 1, bad)
            self.assertFalse(res["X-02"]["complete"])
            self.assertTrue(math.isfinite(res["SUM-03"]["value"]))
            scn = make(profile_kind="LINEAR_TREND")
            scn.operation.electricity.base = bad
            res = registry.run_all(scn)
            self.assertFalse(res["B6-04"]["computed"])
            self.assertFalse(res["B6-01"]["computed"])
            self.assertFalse(res["B2-01"]["computed"])
            self.assertEqual(res["B2-01"]["value"], 0.0)
            for uid in ("B6-04", "B6-01", "B2-01"):
                self.assertIn(uid, res["X-02"]["incomplete_units"])
        scn = make(profile_kind="TABLE")
        scn.operation.gas.table = scn.operation.gas.table[:30]            # shorter than the 60 study years
        scn.water_waste.water.table[59] = None
        scn.water_waste.municipal_waste.table[60] = NAN                   # beyond the period: not used
        res = registry.run_all(scn)
        self.assertEqual(res["B6-02"]["n_skipped"], 1)
        self.assertEqual(res["B7-01"]["n_skipped"], 1)
        self.assertEqual(res["B7-03"]["n_skipped"], 0)
        scn = make(profile_kind="CONSTANT")
        scn.operation.gas.table = scn.operation.gas.table[:30]            # only a copy: reported, the descriptor is used
        res = registry.run_all(scn)
        self.assertEqual(res["B6-02"]["n_skipped"], 0)
        self.assertFalse(res["B6-02"]["descriptors_match_tables"])
        self.assertTrue(res["X-02"]["complete"])

    def test_purchased_electricity_clamp_is_a_definition_not_a_repair(self):
        scn = make(profile_kind="CONSTANT")
        op = scn.operation
        op.onsite_generation.base = op.electricity.base * 3.0             # valid inputs, generation above consumption
        op.onsite_generation.table = [op.onsite_generation.base] * len(op.onsite_generation.table)
        op.onsite_export.base = 0.0
        op.onsite_export.table = [0.0] * len(op.onsite_export.table)
        res = registry.run_all(scn)
        self.assertTrue(res["B6-04"]["computed"])
        self.assertEqual(set(res["B6-04"]["by_year"]), {0.0})
        self.assertTrue(res["X-02"]["complete"])

    def test_grid_factor_rules(self):
        for kind, attr in (("LINEAR_DECLINE_TO_FLOOR", "start"), ("LINEAR_DECLINE_TO_FLOOR", "floor"),
                           ("LINEAR_DECLINE_TO_FLOOR", "annual_decline"), ("CONSTANT", "start")):
            for bad in (NAN, INF, -INF, -0.1, None):
                scn = make(grid_kind=kind)
                setattr(scn.operation.grid, attr, bad)
                res = registry.run_all(scn)                               # falls back to the (valid) year table
                self.assertEqual(res["X-06"]["source"], "TABLE", (kind, attr, bad))
                self.assertTrue(res["X-06"]["computed"])
                self.assertTrue(res["X-02"]["complete"])
        scn = make(grid_kind="STEPWISE")
        scn.operation.grid.steps = [model.GridStep(0, 0.5), model.GridStep(3.0, 0.3)]     # index of the wrong type
        self.assertEqual(registry.run_all(scn)["X-06"]["source"], "TABLE")
        for mutate in (lambda g: g.table.__setitem__(4, NAN), lambda g: g.table.__setitem__(0, None),
                       lambda g: g.table.__setitem__(59, -1.0), lambda g: setattr(g, "table", g.table[:59])):
            scn = make(grid_kind="TABLE")
            mutate(scn.operation.grid)
            res = registry.run_all(scn)                                   # no descriptor and no usable table
            self.assertEqual(res["X-06"]["source"], "NONE")
            self.assertFalse(res["X-06"]["computed"])
            self.assertFalse(res["B6-01"]["computed"])
            self.assertFalse(res["B2-01"]["computed"])
            self.assertIsNone(res["X-11"]["value"])
            self.assertFalse(res["X-02"]["complete"])
            self.assertIn("X-06", res["X-02"]["incomplete_units"])
            self.assertTrue(res["A5-01"]["computed"])                     # the construction value is a separate input
        for bad in (NAN, INF, -1.0, None):
            scn = make()
            scn.operation.grid.construction_value = bad
            res = registry.run_all(scn)
            self.assertFalse(res["A5-01"]["computed"], bad)
            self.assertEqual(res["A5-01"]["value"], 0.0)
            self.assertIn("A5-01", res["X-02"]["incomplete_units"])
        scn = make(grid_kind="STEPWISE")
        scn.operation.grid.table = scn.operation.grid.table[:10]          # a short copy never raises
        res = registry.run_all(scn)
        self.assertEqual(res["X-06"]["source"], "DESCRIPTOR")
        self.assertFalse(res["X-06"]["matches_table"])
        self.assertTrue(res["X-02"]["complete"])

    def test_only_an_invalid_study_period_raises(self):
        for bad in (0.0, -5.0, NAN, INF, -INF, None, True):
            scn = make()
            scn.boundary.study_period = bad
            with self.assertRaises(ValueError):
                registry.run_all(scn)
        scn = make(profile_kind="TABLE", grid_kind="TABLE")
        scn.boundary.study_period = 500.0                                  # longer than every year table
        res = registry.run_all(scn)
        self.assertEqual(res["X-06"]["source"], "NONE")
        self.assertFalse(res["X-02"]["complete"])
        self.assertEqual(res["B6-02"]["n_skipped"], 3)

    def test_gates_do_not_raise_on_missing_values(self):
        scn = make()
        scn.materials[0].end_of_life.routes[0].fraction = None
        scn.materials[1].end_of_life.routes[1].fraction = NAN
        scn.materials[2].end_of_life.routes[2].fraction = -0.2
        scn.materials[3].end_of_life.mass_kg = -1.0
        scn.materials[4].end_of_life.mass_kg = NAN
        scn.materials[5].end_of_life.mass_kg = None
        clean = registry.run_all(make())
        res = registry.run_all(scn)
        for i in (0, 1, 2):
            self.assertIn(f"materials[{i}].end_of_life.routes", res["C-05"]["violations"])
        self.assertEqual(res["C-05"]["n_mass_unchecked"], clean["C-05"]["n_mass_unchecked"] + 3)
        self.assertEqual(res["C3-01"]["n_routes_skipped"], clean["C3-01"]["n_routes_skipped"] + 3)
        scn = make(multi_use=True)
        key = sorted(scn.project.use_area_breakdown)[0]
        for bad in (None, NAN, INF, -3.0):
            scn.project.use_area_breakdown[key] = bad
            res = registry.run_all(scn)
            self.assertEqual((res["SYS-04"]["status"], res["SYS-04"]["sum"]), ("INVALID", None), bad)
            self.assertEqual(res["QA-04"]["status"], "NOT_EVALUATED")
        scn = make()
        scn.project.gross_floor_area = INF
        res = registry.run_all(scn)
        self.assertEqual(res["SYS-04"]["status"], "INVALID")
        self.assertIsNone(res["SUM-04"]["value"])
        self.assertIsNone(res["SUM-05"]["value"])
        self.assertIsNone(res["X-11"]["value"])

    def test_summary_classes_without_a_positive_quantity(self):
        scn = population.standard_benchmark()[0]
        res = registry.run_all(scn)
        classes = res["X-17"]["by_class"]
        positive = [k for k, v in classes.items() if v["fbar"] is not None]
        self.assertEqual(res["X-17"]["n_classes_skipped"], 6 - len(positive))
        self.assertGreater(len(positive), 2)
        again = {k: 0.0 for k in classes}
        from refcalc.units_pre_a import simple_class
        for i, row in enumerate(scn.materials):
            k = simple_class(row)
            if k is not None:
                again[k] += res["A13-01"]["by_item"][i] + res["A13-03"]["by_item"][i]
        for k in positive:                                                  # the identity of the text, class by class
            self.assertTrue(close(classes[k]["emission"], again[k]), k)
        for bad in (None, NAN, INF, 0.0, -4.0):
            scn.summary_quantities.concrete_m3 = bad
            r2 = registry.run_all(scn)["X-17"]
            self.assertEqual(r2["n_classes_skipped"], res["X-17"]["n_classes_skipped"] + (1 if "CONCRETE" in positive else 0))
            self.assertIsNone(r2["by_class"]["CONCRETE"]["fbar"])
            self.assertEqual(r2["by_class"]["CONCRETE"]["emission"], 0.0)

    def test_net_order_quantity_counts_its_skipped_rows(self):
        scn = make()
        scn.materials[0].reuse_rate = 1.5
        scn.materials[1].quantity = None
        res = registry.run_all(scn)
        self.assertEqual(res["X-13"]["n_skipped"], 2)
        self.assertEqual(res["X-13"]["by_item"][:2], [None, None])

    def test_state_gate_reports_non_finite_values(self):
        scn = make()
        scn.materials[2].quantity = NAN
        scn.equipment[0].end_of_life_mass_kg = INF
        scn.materials[3].quantity = None
        res = registry.run_all(scn)["SYS-01"]
        self.assertFalse(res["ok"])
        self.assertEqual(res["not_finite"], ["materials[2].quantity", "equipment[0].end_of_life_mass_kg"])
        self.assertEqual(res["counts"]["NOT_FINITE"], 2)
        self.assertEqual(set(res["violations"]), {"materials[2].quantity", "materials[3].quantity", "equipment[0].end_of_life_mass_kg"})

    def test_licence_gate_requires_the_equipment_disposal_factor(self):
        scn = make()
        self.assertTrue(registry.run_all(scn)["SYS-03"]["ok"])
        scn.equipment[0].eol_factor_id = None
        res = registry.run_all(scn)
        self.assertIn("equipment[0].eol_factor_id (no factor)", res["SYS-03"]["violations"])
        self.assertEqual(res["X-14"]["n_skipped"], 1)
        self.assertFalse(res["X-02"]["complete"])

    def test_stage_subset_with_a_defect_in_an_upstream_row_is_incomplete(self):
        def scenario(stages):
            scn = make(included_stages=stages, replacement_cycle=25.0, reconstruction_scenario="REBUILD_IDENTICAL")
            for row in sorted(scn.materials, key=lambda r: -r.quantity)[:3]:
                row.quantity = None
            scn.equipment[0].factor_id = "F-NOT-IN-TABLE"
            return scn

        for stages, expected in ((["B3"], {"A13-01", "A13-05", "X-01"}), (["B5"], {"A13-01", "A13-05", "X-01"}),
                                 (["B3", "B5"], {"A13-01", "X-01"}), (["B4"], {"B4-02", "A13-01", "X-01"})):
            res = registry.run_all(scenario(stages))
            self.assertFalse(res["X-02"]["complete"], stages)
            self.assertFalse(res["SUM-03"]["complete"], stages)
            self.assertTrue(expected <= set(res["X-02"]["incomplete_units"]), (stages, res["X-02"]["incomplete_units"]))
        res = registry.run_all(scenario(["B6", "B7", "C1"]))                # nothing of the defect flows into these
        self.assertTrue(res["X-02"]["complete"])
        scn = make(included_stages=["B5"], replacement_cycle=25.0, reconstruction_scenario="REBUILD_IDENTICAL")
        scn.factors[scn.materials[2].factor_id].licence_status = "RESTRICTED"
        res = registry.run_all(scn)
        self.assertFalse(res["X-02"]["complete"])
        self.assertIn("A13-01", res["X-02"]["incomplete_units"])
        scn = make(included_stages=["B6"])                                   # B6 without B2: the share is not needed
        scn.operation.facility_management_ratio = None
        res = registry.run_all(scn)
        self.assertFalse(res["B2-01"]["computed"])
        self.assertTrue(res["X-02"]["complete"])
        scn.boundary.included_lifecycle_stages = ["B2", "B6"]
        self.assertEqual(registry.run_all(scn)["X-02"]["incomplete_units"], ["B2-01"])

    def test_gas_breakdown_is_checked_against_the_stage_total(self):
        scn = make(composite_share=0.0, epd_share=0.0)
        res = registry.run_all(scn)
        self.assertTrue(res["X-04"]["matches_stage_total"])
        self.assertEqual(res["X-04"]["n_gases_skipped"], 0)
        scn.factors[scn.materials[2].factor_id].gas_amounts["CO2"] *= 3.0
        res = registry.run_all(scn)
        self.assertFalse(res["X-04"]["matches_stage_total"])
        self.assertEqual(res["QA-01"]["violations"], ["gas breakdown total"])
        scn = make()
        scn.gwp["CH4"] = None
        res = registry.run_all(scn)
        self.assertEqual(res["X-04"]["n_gases_skipped"], 1)

    def test_gas_list_defects(self):
        scn = make(composite_share=0.5)
        clean = registry.run_all(scn)
        scn.gases = scn.gases + ["CO2", "CH4"]
        res = registry.run_all(scn)
        self.assertEqual(res["X-04"]["value"], clean["X-04"]["value"])
        self.assertEqual(list(res["X-04"]["by_gas"]), list(clean["X-04"]["by_gas"]))
        scn.gases = [g for g in clean["X-04"]["by_gas"] if g != "CO2"]
        res = registry.run_all(scn)
        self.assertEqual(res["X-05"]["value"], clean["X-05"]["value"])        # CO2 need not be listed for the CO2 result
        self.assertNotIn("CO2", res["X-04"]["by_gas"])
        self.assertFalse(res["X-04"]["matches_stage_total"])

    def test_repairs_keep_their_gas_amounts_when_the_factor_value_is_zero(self):
        scn = make(1, composite_share=0.0, epd_share=0.0)
        scn.equipment[0].repair_rate = 0.02
        before = registry.run_all(scn)
        scn.factors[scn.equipment[0].factor_id].value = 0.0                   # the gas amounts stay as they are
        res = registry.run_all(scn)
        j_lines = res["B3-01"]["_eq_lines"][0]
        self.assertEqual(len(j_lines), 1)
        self.assertGreater(j_lines[0][1], 0.0)
        self.assertFalse(res["X-04"]["matches_stage_total"])                  # value and gas amounts contradict each other
        self.assertEqual(before["B3-01"]["n_skipped"], res["B3-01"]["n_skipped"])

    def test_factor_ids_cannot_collide_with_the_pseudo_lines(self):
        for name in ("GRID", "REFRIGERANT"):
            scn = make(1, composite_share=0.0, epd_share=0.0)
            clean = registry.run_all(scn)
            row = scn.materials[0]
            rec = copy.deepcopy(scn.factors[row.factor_id])
            rec.factor_id = name
            scn.factors[name] = rec
            row.factor_id = name
            res = registry.run_all(scn)
            self.assertTrue(close(res["SUM-03"]["value"], clean["SUM-03"]["value"]), name)
            self.assertTrue(close(res["X-04"]["value"], clean["X-04"]["value"]), name)
            self.assertTrue(close(res["X-04"]["grid_co2e"], clean["X-04"]["grid_co2e"]), name)
            self.assertTrue(res["QA-01"]["ok"], res["QA-01"])
        self.assertIsNot(base.GRID, "GRID")
        self.assertNotEqual(base.GRID, "GRID")
        self.assertIs(copy.deepcopy(base.GRID), base.GRID)
        self.assertEqual(repr(base.REFRIGERANT), "<REFRIGERANT>")

    def test_unit_named_None_is_a_unit(self):
        scn = make()
        op = scn.operation
        op.electricity.unit = op.onsite_generation.unit = op.onsite_export.unit = "None/year"
        op.grid.unit = "kgCO2e/None"
        res = registry.run_all(scn)
        self.assertEqual(res["SYS-02"]["violations"], ["construction.electricity"])
        self.assertTrue(res["B6-01"]["computed"])

    def test_baseline_comparison_statuses(self):
        scn = make(22, n_materials=8, n_equipment=4, n_refrigerants=2)
        self.assertEqual(registry.run_all(scn)["SUM-08"]["status"], "NO_BASELINE")
        scn.boundary.baseline_scenario = "NO-SUCH-SCENARIO"
        self.assertEqual(registry.run_all(scn)["SUM-08"], {"status": "BASELINE_NOT_FOUND", "delta": None, "saving": None})
        base_scn = population.attach_baseline(scn)
        res = registry.run_all(scn)["SUM-08"]
        self.assertEqual((res["status"], res["proposal_complete"], res["baseline_complete"]), ("COMPARED", True, True))
        self.assertGreater(res["saving"], 0.0)
        for row in sorted(base_scn.materials, key=lambda r: -r.quantity)[:4]:
            row.quantity = None
        res = registry.run_all(scn)["SUM-08"]
        self.assertEqual(res, {"status": "INCOMPLETE", "delta": None, "saving": None, "proposal_complete": True,
                               "baseline_complete": False})
        scn.materials[0].quantity = None
        res = registry.run_all(scn)["SUM-08"]
        self.assertEqual((res["status"], res["proposal_complete"], res["baseline_complete"]), ("INCOMPLETE", False, False))
        base_scn.boundary.study_period = 50.0
        self.assertEqual(registry.run_all(scn)["SUM-08"]["status"], "NOT_COMPARABLE")


if __name__ == "__main__":
    unittest.main()
