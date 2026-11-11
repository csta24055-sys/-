"""Tests of the unified model: agreement with the reference and the mechanisms it claims to use.

Run:  cd research_code && python3 -m unittest tests.test_engine -v
"""
import copy
import unittest

import synth
from bench import mutations
from common.compare import compare
from fastcalc import engine
from refcalc import registry, units_c_sum
from synth import model, population

registry.load_all()
SMALL = {"n_materials": 40, "n_equipment": 12, "n_refrigerants": 4}
TINY = {"n_materials": 12, "n_equipment": 6, "n_refrigerants": 4}
NAN, INF = float("nan"), float("inf")


def agree(testcase, scn, detail=True):
    """Every public leaf within a relative 1e-9 (no absolute floor), no leaf and no unit only on one side."""
    ref = registry.run_all(scn)
    got = engine.evaluate(scn, detail=detail)
    for uid in ref:
        c = compare(ref[uid], got.get(uid, {}), floor=0.0, ignore_missing=not detail)
        testcase.assertTrue(c.within(1e-9) and not c.extra, (uid, c.worst_path, c.max_abs_rel_error, c.mismatches[:2], c.missing[:2], c.extra[:2]))
    testcase.assertEqual([u for u in got if not u.startswith("_") and u not in ref], [])
    return ref, got


def agree_both(testcase, scn):
    ref, full = agree(testcase, scn, True)
    agree(testcase, scn, False)
    return ref, full


def tiny(seed=11, period=60.0, **options):
    opts = dict(TINY)
    opts.update(options)
    return synth.make_scenario(seed, "RC", "office", "S", period, **opts)


class EngineTests(unittest.TestCase):
    def test_agrees_with_reference(self):
        for name, scn in population.edge_cases():
            with self.subTest(case=name):
                agree(self, scn, True)
                agree(self, scn, False)

    def test_totals_mode_multiplies_no_factor_per_row_and_runs_no_year_loop(self):
        """The mechanisms the unified model claims, counted."""
        scn = synth.make_scenario(5, "RC", "office", "S", 60.0, profile_kind="LINEAR_TREND",
                                  grid_kind="LINEAR_DECLINE_TO_FLOOR", n_materials=400, n_equipment=120, n_refrigerants=10)
        res = engine.evaluate(scn, detail=False)
        st = res["_stats"]
        self.assertEqual(st["row_factor_products"], 0)        # factors are applied to summed activities only
        self.assertEqual(st["year_loop_iterations"], 0)       # every year sum is a closed form here
        self.assertEqual(st["event_lists_built"], 0)          # renewal counts come from the count function
        A = engine.aggregate(scn, False)
        distinct = len({tuple((c.factor_id, c.mass_fraction) for c in row.composition) for row in scn.materials if row.composition})
        self.assertEqual(st["recipes_computed"], distinct)    # one composite factor per distinct composition
        self.assertLess(st["factor_resolutions"], res["SYS-02"]["n_checked"])
        n_lines = sum(len(t) for t in res["_tables"].values())
        self.assertLess(n_lines, 6 * len(scn.factors))        # the tables hold factor keys, not rows
        self.assertLess(len(A.groups), len(scn.materials) + len(scn.equipment))
        full = engine.evaluate(scn, detail=True)["_stats"]
        self.assertEqual(full["row_factor_products"], len(scn.materials) + len(scn.equipment))
        self.assertGreater(full["year_loop_iterations"], 0)   # the yearly series still need one value per year

    def test_table_inputs_fall_back_to_a_year_scan(self):
        scn = synth.make_scenario(5, "RC", "office", "S", 60.0, profile_kind="TABLE", grid_kind="TABLE", **SMALL)
        st = engine.evaluate(scn, detail=False)["_stats"]
        self.assertGreater(st["year_loop_iterations"], 0)
        agree(self, scn, False)

    def test_sweep_from_one_aggregation(self):
        scn = synth.make_scenario(6, "S", "retail", "S", 60.0, **SMALL)
        periods = (25.0, 60.0, 62.5, 99.9)
        got = engine.sweep(scn, periods)
        for T in periods:
            other = copy.deepcopy(scn)
            other.boundary.study_period = T
            ref = registry.run_all(other)
            for uid in ref:                              # every unit, without the comparison with a baseline
                if uid != "SUM-08":
                    c = compare(ref[uid], got[T].get(uid, {}), floor=0.0, ignore_missing=True)
                    self.assertTrue(c.within(1e-9) and not c.extra, (T, uid, c.worst_path))

    def test_baseline_needs_no_hidden_state(self):
        scn = synth.make_scenario(8, "RC", "office", "S", 60.0, **SMALL)
        base = population.attach_baseline(scn)
        first = engine.evaluate(scn, detail=False)["SUM-08"]
        for row in base.materials:
            row.quantity *= 2.0
        ref = registry.run_all(scn, ids=["SUM-08"])["SUM-08"]
        again = engine.evaluate(scn, detail=False)["SUM-08"]   # nothing was cached: the edit is seen
        self.assertTrue(compare(ref, again).within(1e-9))
        self.assertNotEqual(first["baseline"], again["baseline"])
        held = {}
        a = engine.evaluate(scn, detail=False, baseline_totals=held)["SUM-08"]
        b = engine.evaluate(scn, detail=False, baseline_totals=held)["SUM-08"]
        self.assertEqual(a, b)
        self.assertEqual(list(held), [scn.boundary.baseline_scenario])    # keyed by the input id
        self.assertEqual(held[scn.boundary.baseline_scenario], {"value": a["baseline"], "complete": True})

    def test_scenario_that_is_its_own_baseline(self):
        scn = synth.make_scenario(9, "RC", "office", "S", 60.0, **SMALL)
        population.BASELINES[scn.meta.scenario_id] = scn
        scn.boundary.baseline_scenario = scn.meta.scenario_id
        res = engine.evaluate(scn, detail=False)["SUM-08"]
        self.assertEqual(res["status"], "COMPARED")
        self.assertEqual(res["delta"], 0.0)

    def test_invalid_study_period_is_refused(self):
        for bad in mutations.INVALID_PERIODS + (True,):
            scn = synth.make_scenario(9, "RC", "office", "S", 60.0, **SMALL)
            scn.boundary.study_period = bad
            for detail in (True, False):
                with self.assertRaises(ValueError):
                    engine.evaluate(scn, detail=detail)
            with self.assertRaises(ValueError):
                registry.run_all(scn)
        scn = synth.make_scenario(9, "RC", "office", "S", 60.0, **SMALL)
        for bad in (0.0, NAN, INF, None):
            with self.assertRaises(ValueError):
                engine.sweep(scn, (30.0, bad))

    def test_a_period_longer_than_the_year_tables_is_not_refused(self):
        for options in ({"profile_kind": "TABLE", "grid_kind": "TABLE"}, {"profile_kind": "LINEAR_TREND", "grid_kind": "STEPWISE"}):
            scn = tiny(**options)
            scn.boundary.study_period = 500.0
            ref, full = agree_both(self, scn)
            self.assertEqual(ref["X-06"]["computed"], options["grid_kind"] != "TABLE")   # a descriptor needs no table
            self.assertEqual(ref["X-06"]["matches_table"], False)
            self.assertFalse(ref["X-02"]["complete"])      # year tables (or trends that turn negative) are unusable

    def test_completeness_table_equals_the_closure_of_the_registry(self):
        """The unified model restates which units flow into each stage; the registry's data flow is the source."""
        self.assertEqual(set(engine.STAGE_UPSTREAM), set(engine.STAGES))
        for stage in engine.STAGES:
            self.assertEqual(engine.STAGE_UPSTREAM[stage], units_c_sum.stage_upstream(stage), stage)
        self.assertEqual(engine.B6_UPSTREAM_WITHOUT_B2, units_c_sum.stage_upstream("B6", b2_included=False))
        from refcalc import base
        self.assertEqual(engine.EXCLUSION_COUNTS, base.EXCLUSION_COUNTS)

    def test_stage_subset_with_upstream_defect_is_incomplete_on_both_sides(self):
        n = 0
        for stages in mutations.UPSTREAM_DEFECT_SUBSETS:
            for name, mutate in mutations.UPSTREAM_DEFECTS.items():
                scn = tiny(61, included_stages=stages, replacement_cycle=25.0, reconstruction_scenario="REBUILD_IDENTICAL",
                           profile_kind="CONSTANT")
                mutate(scn)
                ref, full = agree_both(self, scn)
                self.assertEqual(full["X-02"]["incomplete_units"], ref["X-02"]["incomplete_units"])
                n += not ref["X-02"]["complete"]
        self.assertGreater(n, 20)
        for stages in (["B3"], ["B5"], ["B3", "B5"], ["B4"]):
            scn = tiny(11, included_stages=stages, replacement_cycle=25.0, reconstruction_scenario="REBUILD_IDENTICAL")
            mutations.UPSTREAM_DEFECTS["missing_quantity_and_unknown_factor"](scn)
            for detail in (True, False):
                res = engine.evaluate(scn, detail=detail)
                self.assertFalse(res["X-02"]["complete"], stages)
                self.assertFalse(res["SUM-03"]["complete"], stages)
                self.assertIn("A13-01", res["X-02"]["incomplete_units"])
                self.assertIn("X-01", res["X-02"]["incomplete_units"])

    def test_period_1_000000001_agrees_and_is_self_consistent(self):
        for T in (7.0, 30.0, 60.0, 99.9):
            scn = tiny(1, T, service_life_choices=[1.000000001], explicit_event_share=0.0, change_list_share=0.0,
                       replacement_cycle=1.000000001, reconstruction_scenario="REBUILD_IDENTICAL")
            ref, full = agree_both(self, scn)
            self.assertAlmostEqual(sum(full["B3-01"]["by_year"]) / full["B3-01"]["value"], 1.0, places=11)
            self.assertAlmostEqual(full["X-07"]["value"] / full["SUM-03"]["value"], 1.0, places=11)
            self.assertTrue(full["QA-01"]["ok"])
        scn = tiny(6, 60.0)
        for row in scn.materials[:3]:
            row.refresh_cycle = 1.000000001
        got = engine.sweep(scn, (7.0, 30.0, 60.0))
        for T in got:
            other = copy.deepcopy(scn)
            other.boundary.study_period = T
            ref = registry.run_all(other)
            self.assertTrue(compare(ref["B3-01"], got[T]["B3-01"], ignore_missing=True).within(1e-9), T)
            self.assertTrue(compare(ref["SUM-03"], got[T]["SUM-03"]).within(1e-9), T)

    def test_every_mutation_agrees(self):
        """All adversarial mutations of the verification list on one small scenario each, in both output modes."""
        n = 0
        for name, (mutate, options) in mutations.MUTATIONS.items():
            opts = dict(TINY)
            opts.update(options)
            scn = synth.make_scenario(12, "RC", "office", "S", 42.5, scenario_id=f"T-{name}", **opts)
            mutate(scn)
            with self.subTest(mutation=name):
                agree_both(self, scn)
            n += 1
        self.assertGreater(n, 200)

    def test_defects_found_by_the_second_review(self):
        # NaN in a grid descriptor: the table is used, nothing raises (NUM-2)
        scn = tiny(grid_kind="LINEAR_DECLINE_TO_FLOOR")
        scn.operation.grid.annual_decline = NAN
        ref, full = agree_both(self, scn)
        self.assertEqual(full["X-06"]["source"], "TABLE")
        # a factor whose value is 0 but whose gas amounts are not (NUM-3)
        scn = tiny(1, composite_share=0.0, epd_share=0.0)
        mutations.MUTATIONS["factor_value_zero_with_gas_amounts"][0](scn)
        ref, full = agree_both(self, scn)
        self.assertFalse(full["X-04"]["matches_stage_total"])
        # an annual table shorter than the period together with a second defect (NUM-4)
        scn = tiny(profile_kind="TABLE")
        mutations.MUTATIONS["short_annual_table_and_no_factor"][0](scn)
        ref, full = agree_both(self, scn)
        self.assertEqual(full["B7-01"]["n_skipped"], 1)
        # factor ids equal to the names of the pseudo lines (NUM-5)
        for name in ("GRID", "REFRIGERANT"):
            scn = tiny(1, composite_share=0.0, epd_share=0.0)
            clean = engine.evaluate(scn, detail=False)["A5-01"]["value"]
            mutations.MUTATIONS["factor_id_named_" + name][0](scn)
            ref, full = agree_both(self, scn)
            self.assertEqual(full["A5-01"]["value"], clean)
            self.assertTrue(full["QA-01"]["ok"])
        # gas list with repetitions / without CO2, with composite rows (NUM-6)
        scn = tiny(1, composite_share=0.5)
        clean = engine.evaluate(scn, detail=False)
        scn.gases = scn.gases + ["CO2"]
        ref, full = agree_both(self, scn)
        self.assertEqual(full["X-04"]["value"], clean["X-04"]["value"])
        scn.gases = [g for g in scn.gases if g != "CO2"]
        ref, full = agree_both(self, scn)
        self.assertEqual(full["X-05"]["value"], clean["X-05"]["value"])
        # a step index of the wrong type (NUM-7)
        scn = tiny(grid_kind="STEPWISE")
        scn.operation.grid.steps = [model.GridStep(0, 0.5), model.GridStep(3.0, 0.3)]
        ref, full = agree_both(self, scn)
        self.assertEqual(full["X-06"]["source"], "TABLE")
        # units literally called "None" (NUM-8)
        scn = tiny()
        mutations.MUTATIONS["units_named_None"][0](scn)
        ref, full = agree_both(self, scn)
        self.assertEqual(full["SYS-02"]["violations"], ["construction.electricity"])

    def test_held_baseline_totals_are_keyed_by_the_input_id(self):
        """Two baselines under different ids whose bookkeeping ids are equal must not be mixed (NUM-9)."""
        props = []
        for seed in (71, 72):
            prop = tiny(seed)
            base = population.attach_baseline(prop)
            base.meta.scenario_id = "N9-SAME-ID"
            props.append(prop)
        held = {}
        for prop in props:
            ref = registry.run_all(prop, ids=["SUM-08"])["SUM-08"]
            got = engine.evaluate(prop, detail=False, baseline_totals=held)["SUM-08"]
            self.assertTrue(compare(ref, got).within(1e-9), (ref, got))
        self.assertEqual(sorted(held), sorted(p.boundary.baseline_scenario for p in props))

    def test_baseline_comparison_statuses(self):
        scn = tiny(22)
        scn.boundary.baseline_scenario = "NO-SUCH-SCENARIO"
        self.assertEqual(engine.evaluate(scn, detail=False)["SUM-08"]["status"], "BASELINE_NOT_FOUND")
        base = population.attach_baseline(scn)
        agree_both(self, scn)
        base.materials[0].quantity = None
        held = {}
        for _ in range(2):                                # the second time from the held entry: same answer
            res = engine.evaluate(scn, detail=False, baseline_totals=held)["SUM-08"]
            self.assertEqual(res, {"status": "INCOMPLETE", "delta": None, "saving": None, "proposal_complete": True,
                                   "baseline_complete": False})
        self.assertFalse(held[scn.boundary.baseline_scenario]["complete"])
        agree_both(self, scn)
        got = engine.sweep(scn, (30.0, 60.0), compare=True)
        self.assertEqual(got[30.0]["SUM-08"]["status"], "NOT_COMPARABLE")
        self.assertEqual(got[60.0]["SUM-08"]["status"], "INCOMPLETE")
        self.assertNotIn("SUM-08", engine.sweep(scn, (30.0,))[30.0])

    def test_pseudo_keys_are_objects_not_strings(self):
        self.assertNotEqual(engine.GRID, "GRID")
        self.assertNotEqual(engine.REFRIGERANT, "REFRIGERANT")
        self.assertIs(copy.deepcopy(engine.GRID), engine.GRID)
        self.assertEqual((repr(engine.GRID), repr(engine.REFRIGERANT)), ("<GRID>", "<REFRIGERANT>"))
        res = engine.evaluate(tiny(), detail=False)
        self.assertIn(engine.GRID, res["_tables"]["B6"])
        self.assertNotIn("GRID", res["_tables"]["B6"])


if __name__ == "__main__":
    unittest.main()
