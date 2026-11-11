"""Tests of the unified model: agreement with the reference and the shared structure it is built from.

The operation counts (no factor multiplied per row, no yearly loop, ...) are measured from outside by
``bench/mechanism_probe.py`` and tested in ``tests/test_mechanism_probe.py``.

Run:  cd research_code && python3 -m unittest tests.test_engine -v
"""
import copy
import unittest

import synth
from bench import mutations
from common.compare import compare
from fastcalc import closed_forms as cf
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

    def test_the_counters_that_remain_count_memo_misses(self):
        """``_stats`` holds three counters, each incremented in the one function that does the work."""
        scn = synth.make_scenario(5, "RC", "office", "S", 60.0, profile_kind="LINEAR_TREND",
                                  grid_kind="LINEAR_DECLINE_TO_FLOOR", n_materials=400, n_equipment=120, n_refrigerants=10)
        for detail in (False, True):
            A = engine.aggregate(scn, detail)
            res = engine.finish(A, None, detail)
            st = res["_stats"]
            self.assertEqual(sorted(st), ["factor_records_resolved", "recipes_computed", "unit_pairs_resolved"])
            distinct = len({tuple((c.factor_id, c.mass_fraction) for c in row.composition) for row in scn.materials if row.composition})
            self.assertEqual(st["recipes_computed"], distinct)            # one composite factor per distinct composition
            self.assertEqual(st["recipes_computed"], len(A.recipes))
            self.assertEqual(st["factor_records_resolved"], len(A.resolver.records))   # one entry per (factor, stage)
            self.assertEqual(st["unit_pairs_resolved"], len(A.resolver.pairs))         # one entry per unit pair
            self.assertLess(st["factor_records_resolved"], res["SYS-02"]["n_checked"] / 5)
            n_lines = sum(len(t) for t in res["_tables"].values())
            self.assertLess(n_lines, 6 * len(scn.factors))                # the tables hold factor keys, not rows
            self.assertLess(len(A.groups), len(scn.materials) + len(scn.equipment))

    def test_table_inputs_fall_back_to_a_year_scan(self):
        """Year tables are summed by the scan functions, descriptors by the closed forms; both agree with the reference."""
        calls = {}

        def counting(name):
            original = getattr(cf, name)

            def wrapper(*args):
                calls[name] = calls.get(name, 0) + 1
                return original(*args)
            return original, wrapper

        for options, scans, closed in (({"profile_kind": "TABLE", "grid_kind": "TABLE"}, 7, 0),
                                       ({"profile_kind": "LINEAR_TREND", "grid_kind": "CONSTANT"}, 0, 7)):
            scn = synth.make_scenario(5, "RC", "office", "S", 60.0, **options, **SMALL)
            calls.clear()
            saved = {}
            try:
                for name in ("table_weighted_sum", "table_moments", "linear_weighted_sum", "segment_moments"):
                    saved[name], wrapper = counting(name)
                    setattr(cf, name, wrapper)
                engine.evaluate(scn, detail=False)
            finally:
                for name, original in saved.items():
                    setattr(cf, name, original)
            self.assertEqual(calls.get("table_weighted_sum", 0) + calls.get("table_moments", 0), scans, options)
            self.assertEqual(calls.get("linear_weighted_sum", 0) + calls.get("segment_moments", 0), closed, options)
            agree(self, scn, False)

    def test_year_scan_and_series_functions(self):
        """The two functions that took over loops which used to be written inside ``finish``."""
        self.assertEqual(cf.table_weighted_sum([1.0, 2.0, 3.0, 4.0, 99.0], 4.0), 10.0)
        self.assertEqual(cf.table_weighted_sum([1.0, 2.0, 3.0, 4.0, 99.0], 3.5), 1.0 + 2.0 + 3.0 + 0.5 * 4.0)
        self.assertEqual(cf.table_weighted_sum([7.0], 0.25), 1.75)
        self.assertEqual(cf.segment_values([(0, 2, 5.0, 0.0), (2, 5, 1.0, 0.5)]), [5.0, 5.0, 2.0, 2.5, 3.0])
        self.assertEqual(cf.segment_values([]), [])
        grid = synth.make_scenario(5, "RC", "office", "S", 42.5, grid_kind="LINEAR_DECLINE_TO_FLOOR", **TINY).operation.grid
        segments = cf.grid_segments(grid, 43)
        values = cf.segment_values(segments)
        self.assertEqual(len(values), 43)
        G = sum((0.5 if k == 42 else 1.0) * v for k, v in enumerate(values))
        self.assertAlmostEqual(cf.segment_moments(segments, 42.5)[0] / G, 1.0, places=12)
        self.assertAlmostEqual(cf.table_moments(values, 42.5)[0] / G, 1.0, places=12)
        self.assertEqual(cf.table_weighted_sum(values, 42.5), cf.table_moments(values, 42.5)[0])

    def test_indicators_come_from_one_function(self):
        """SUM-01..06 and the shares of SUM-07 are values of ``engine.indicator``; SUM-08 builds on the SUM-03 value."""
        scn = tiny(8, 42.5)
        population.attach_baseline(scn)
        for detail in (True, False):
            res = engine.evaluate(scn, detail=detail)
            stages = res["X-02"]["by_stage"]
            area, T = scn.project.gross_floor_area, scn.boundary.study_period
            total = engine.indicator(stages, engine.STAGES)
            self.assertEqual(res["SUM-01"]["value"], engine.indicator(stages, engine.UPFRONT))
            self.assertEqual(res["SUM-02"]["value"], engine.indicator(stages, engine.EMBODIED))
            self.assertEqual(res["SUM-03"]["value"], total)
            self.assertEqual(res["SUM-04"]["value"], engine.indicator(stages, engine.STAGES, area))
            self.assertEqual(res["SUM-05"]["value"], engine.indicator(stages, engine.STAGES, area * T))
            self.assertEqual(res["SUM-06"]["value"], engine.indicator(stages, engine.STAGES, 1000.0))
            self.assertEqual(res["SUM-07"]["by_stage"], {s: engine.indicator(stages, (s,), total) for s in stages})
            self.assertEqual(res["SUM-08"]["delta"], total - res["SUM-08"]["baseline"])
        seen = []
        original = engine.indicator
        engine.indicator = lambda by_stage, subset, divisor=1.0: seen.append((tuple(subset), divisor)) or original(by_stage, subset, divisor)
        try:
            engine.evaluate(tiny(8, 42.5), detail=False)
        finally:
            engine.indicator = original
        self.assertEqual(len([call for call in seen if call[0] == engine.STAGES]), 4)       # SUM-03, -04, -05, -06
        self.assertEqual(len([call for call in seen if len(call[0]) == 1]), len(engine.STAGES))   # the shares of SUM-07

    def test_refrigerant_terms_share_one_device_table(self):
        """B1-01 is the sum of the charge x GWP table; B1-02..04 multiply the same entries; finish reads no device row."""
        scn = tiny(3, 60.0, n_refrigerants=9, change_list_share=0.5)
        scn.refrigerants[0].gwp = None                     # one device without a usable charge in CO2e
        A = engine.aggregate(scn, True)
        expected = [d.charge_mass_kg * d.gwp if d.gwp is not None else None for d in scn.refrigerants]
        self.assertEqual(A.charges, expected)
        res = engine.finish(A, 60.0, True)
        self.assertEqual(res["B1-01"], {"value": sum(c for c in expected if c is not None), "n_skipped": 1})
        A2 = engine.aggregate(scn, True)
        A2.charges[:] = [c * 2.0 if c is not None else None for c in A2.charges]    # a power of two: exact
        scn.refrigerants = None                            # finish must not need the rows
        doubled = engine.finish(A2, 60.0, True)
        for uid in ("B1-01", "B1-02", "B1-03", "B1-04"):
            self.assertEqual(doubled[uid]["value"], 2.0 * res[uid]["value"], uid)
            self.assertGreater(res[uid]["value"], 0.0, uid)
        self.assertEqual(doubled["B1-02"]["by_year"], [2.0 * v for v in res["B1-02"]["by_year"]])

    def test_finish_reads_no_input_row(self):
        """Everything finish needs was copied by the aggregation: without the row lists it returns the same results."""
        for options in ({}, {"profile_kind": "TABLE", "grid_kind": "TABLE"}):
            for detail in (False, True):
                scn = synth.make_scenario(4, "S", "retail", "S", 60.0, explicit_event_share=0.4, change_list_share=0.5,
                                          replacement_cycle=25.0, reconstruction_scenario="REBUILD_IDENTICAL", **SMALL, **options)
                want = engine.evaluate(scn, detail=detail)
                A = engine.aggregate(scn, detail)
                scn.materials = scn.equipment = scn.refrigerants = None
                for T in (60.0, 30.0, 42.5):
                    got = engine.finish(A, T, detail, None, _compare=False)
                    if T == 60.0:
                        for uid in got:
                            if not uid.startswith("_") and uid != "SUM-08":
                                c = compare(want[uid], got[uid], floor=0.0)
                                self.assertTrue(c.within(0.0) and not c.extra, (uid, detail, c.worst_path))

    def test_record_part_of_a_factor_is_checked_once(self):
        """Rows with their own conversions, product-specific factors and recipes do not repeat the record check."""
        scn = synth.make_scenario(5, "RC", "office", "S", 60.0, n_materials=300, n_equipment=60, n_refrigerants=4,
                                  epd_share=0.3, composite_share=0.3)
        self.assertGreater(sum(1 for r in scn.materials if r.conversions), 20)
        seen = {}
        original = engine._record_ok

        def counting(rec, stage):
            seen[(id(rec), stage)] = seen.get((id(rec), stage), 0) + 1
            return original(rec, stage)

        engine._record_ok = counting
        try:
            A = engine.aggregate(scn, False)
            engine.finish(A, 60.0, False)
        finally:
            engine._record_ok = original
        self.assertEqual(set(seen.values()), {1})
        self.assertEqual(len(seen), sum(1 for rec, _ in A.resolver.records.values() if rec is not None))
        agree_both(self, scn)

    def test_used_factor_check_reads_the_licence_findings(self):
        """QA-03: the used factors are the keys of the stage tables, their licence finding is the one of SYS-03."""
        scn = tiny(2, composite_share=0.4, epd_share=0.2)
        used = sorted(k for k in engine.evaluate(scn, detail=False)["_tables"]["A13-01"] if isinstance(k, str))
        scn.factors[used[0]].source_url = ""
        unused = next(fid for fid in scn.factors if fid not in engine.aggregate(scn, False).resolver.fval)
        scn.factors[unused].source_url = ""
        ref, full = agree_both(self, scn)
        self.assertEqual(full["QA-03"]["violations"], [used[0]])
        A = engine.aggregate(scn, False)
        self.assertEqual(A.unlicensed, {used[0]})          # only referenced records are examined
        self.assertFalse(full["SYS-03"]["ok"])

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
