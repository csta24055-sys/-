"""Tests of the approximation study (stdlib unittest, fictional data only).

They check the measuring instrument, not any candidate: that the collectors count what they
drop, that a scenario rewritten for a propagated total is restored, that the kernels called
"exact" reproduce the reference calculation, and that the result of a small run has the
declared shape (what each candidate was measured on).

Run:  cd research_code && python3 -B -m unittest tests.test_approx_study -v
"""
import json
import random
import unittest

import synth
from bench import approx_measures as measures
from bench import approx_study as study
from bench import approx_support as sp
from bench.approx_meta import DECL, IN_SAMPLE, PROPAGATED, SPLIT, evidence_scope, order_key
from fastcalc import closed_forms as cf
from refcalc import registry
from refcalc.base import periodic_events, year_weights


class SupportTests(unittest.TestCase):
    def test_series_counts_the_cases_it_drops(self):
        s = sp.Series()
        self.assertEqual(s.add(2.0, 3.0), 0.5)
        self.assertIsNone(s.add(0.0, 0.0))
        self.assertIsNone(s.add(0.0, 4.0))
        r = s.result()
        self.assertEqual((r["n"], r["n_reference_zero"], r["n_reference_zero_candidate_nonzero"]), (1, 2, 1))
        self.assertFalse(sp.within(r, 1.0))           # a candidate that books something where the reference has nothing
        empty = sp.Series().result()
        self.assertEqual(empty, {"n": 0, "n_reference_zero": 0, "n_reference_zero_candidate_nonzero": 0})

    def test_class_pairs_with_zero_reference_are_counted(self):
        col = sp.Collector()
        col.add_classes({"A": 1.0, "B": 0.0, "C": 0.0}, {"A": 1.5, "B": 2.0})
        by_class, zero = col.class_result()
        self.assertEqual(zero, {"n_pairs": 3, "n_reference_zero": 2, "n_reference_zero_candidate_nonzero": 1})
        self.assertEqual(by_class["B"]["n_reference_zero_candidate_nonzero"], 1)
        self.assertEqual(by_class["C"]["n_reference_zero_candidate_nonzero"], 0)

    def test_coarse_table_and_its_kernels(self):
        rng = random.Random(3)
        for T in (1.0, 0.5, 2.0, 5.0, 6.0, 11.0, 30.0, 42.5, 60.0, 61.0, 99.9):
            Y = cf.n_years(T)
            values = [rng.uniform(1.0, 2.0) for _ in range(Y)]
            w = year_weights(T)
            for step in (5, 10):
                c = sp.coarse(values, step)
                nodes_at = sorted({(k // step) * step for k in range(Y)} | {Y - 1})
                self.assertEqual(len(nodes_at), sp.n_nodes(Y, step))
                for k in nodes_at:                     # the kept years are exact
                    self.assertEqual(c[k], values[k])
                nodes = [values[k] for k in nodes_at]
                want = sum(w[y] * c[y - 1] for y in range(1, Y + 1))
                self.assertAlmostEqual(sp.weighted_from_nodes(T, Y, step, nodes), want, delta=1e-12 * want)
                G, H = sp.moments_from_nodes(T, Y, step, nodes)
                self.assertAlmostEqual(G, want, delta=1e-12 * want)
            self.assertAlmostEqual(sp.weighted_table(T, values), sum(w[y] * values[y - 1] for y in range(1, Y + 1)), delta=1e-12 * Y)

    def test_safe_side_repair_years_do_not_exclude_too_much_for_cycles_of_a_year_or_more(self):
        rng = random.Random(5)
        worst = 0.0
        for _ in range(4000):
            T = rng.choice((30.0, 42.5, 50.0, 60.0, 62.5, 99.9, round(rng.uniform(1.0, 120.0), 3)))
            c = rng.choice((round(rng.uniform(1.0, 130.0), 2), float(rng.randint(1, 120)), rng.uniform(1.0, 5.0)))
            w = year_weights(T)
            excluded = sum(w[y] for y in set(periodic_events(T, c)))
            worst = min(worst, excluded - min(T, max(0.0, T / c - 1.0)))
            self.assertAlmostEqual(sp.years_exact(T, c), T - excluded, delta=1e-9)
        self.assertGreater(worst, -1e-7)               # equal up to the relative 1e-9 boundary tolerance
        # below one year the guarantee fails: several events of a year exclude that year only once
        T, c = 10.5, 0.9
        w = year_weights(T)
        self.assertLess(sum(w[y] for y in set(periodic_events(T, c))), min(T, T / c - 1.0))

    def test_patch_is_undone(self):
        scn = synth.make_scenario(21, "RC", "office", "S", 30.0, n_materials=8, n_equipment=4, n_refrigerants=2)
        before = json.dumps(synth.to_dict(scn), sort_keys=True)
        registry.load_all()

        def edit(p):
            p.set(scn.boundary, "study_period", 45.0)
            p.set(scn.materials[0], "waste_rate", 0.5)
            p.put(scn.factors, "NEW", next(iter(scn.factors.values())))
            p.put(scn.factors, next(iter(scn.factors)), None)
            raise RuntimeError("stop")

        with self.assertRaises(RuntimeError):
            sp.rerun(scn, edit, ["SUM-03"])
        self.assertEqual(json.dumps(synth.to_dict(scn), sort_keys=True), before)

    def test_explicit_lists_are_continued_beyond_the_own_period(self):
        scn = synth.make_scenario(22, "S", "office", "S", 30.0, n_materials=4, n_equipment=6, n_refrigerants=4,
                                  explicit_event_share=1.0, change_list_share=1.0)
        p = sp.Patch()
        try:
            failed = sp.continue_lists(p, scn, 30.0, 75.0)
            for eq in scn.equipment:
                tail = [t for t in eq.replacement_event_list if t >= 30.0]
                self.assertTrue(tail and max(tail) <= 76.0 and max(tail) + max(1.0, round(eq.service_life)) >= 76.0)
            self.assertEqual(failed, sum(1 for d in scn.refrigerants if not d.change_years))
        finally:
            p.undo()
        self.assertTrue(all(max(eq.replacement_event_list, default=0) < 30.0 for eq in scn.equipment))


class KernelTests(unittest.TestCase):
    """The kernels measured as "exact closed form" give the reference values on the rows they are called on."""

    @classmethod
    def setUpClass(cls):
        registry.load_all()
        cls.scn = synth.make_scenario(31, "SRC", "hospital", "S", 62.5, service_life_mode="MIXED", top_up=None)
        cls.S = measures.One(cls.scn, registry.run_all(cls.scn))

    def test_count_and_repair_kernels(self):
        S, T = self.S, self.S.T
        rows = [(r["cycle"], r["u"]) for r in S.rows if not r["explicit"] and cf.valid_period(r["cycle"])]
        explicit = sum(r["n"] * r["u"] for r in S.rows if r["explicit"])
        self.assertAlmostEqual(sp.k_count(cf.renewal_count, T, rows) + explicit, S.stage["B4"], delta=1e-9 * S.stage["B4"])
        rep = measures.repairs_by_class(S)
        self.assertAlmostEqual(sum(rep["ref"].values()), S.stage["B3"], delta=1e-9 * S.stage["B3"])
        pairs = [(r["cycle"], r["e0"] * r["r"]) for r in S.rows if r["e0"] * r["r"] and not r["explicit"]]
        fixed = sum(rep["fixed"].values())
        self.assertAlmostEqual(sp.k_repair(sp.years_exact, T, pairs) + fixed, S.stage["B3"], delta=1e-9 * S.stage["B3"])
        # the candidates: AP-04 never below the safe-side form, the safe-side form never below the reference
        self.assertGreaterEqual(sp.k_repair(sp.years_ap04, T, pairs), sp.k_repair(sp.years_ap23, T, pairs))
        self.assertGreaterEqual(sp.k_repair(sp.years_ap23, T, pairs), sp.k_repair(sp.years_exact, T, pairs) * (1 - 1e-9))
        self.assertGreaterEqual(sum(rep["cls"].values()), sum(rep["row"].values()) * (1 - 1e-12))

    def test_refrigerant_kernels(self):
        S, T = self.S, self.S.T
        devices = self.scn.refrigerants
        exact = sp.k_devices(sp.device_exact, T, devices)
        self.assertAlmostEqual(exact, S.stage["B1"], delta=1e-9 * S.stage["B1"])
        a, b = sp.k_devices(sp.device_ap05a, T, devices), sp.k_devices(sp.device_ap05b, T, devices)
        self.assertGreaterEqual(a, exact * (1 - 1e-12))      # both linear variants are on the safe side,
        self.assertGreaterEqual(b, a * (1 - 1e-12))          # "treated as topped up" is the cruder one
        for dev, st in zip(devices, S.res["B1-02"]["_state"]):
            years = [y for y, _ in st["before_events"]]
            self.assertEqual(sp.device_years(T, dev), years)
            leak, before, end = sp.linear_refrigerant(T, dev, years, False)
            self.assertEqual((before, end), (len(years) * dev.charge_mass_kg, dev.charge_mass_kg))
            if dev.top_up:
                self.assertEqual(sp.linear_refrigerant(T, dev, years, True), (leak, before, end))


class RunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = study.run(8, load_every=4, stress_seeds=1, n_period_scenarios=2)
        cls.C = cls.result["candidates"]

    def test_every_declared_candidate_is_reported_in_order(self):
        self.assertEqual(list(self.C), sorted(DECL, key=order_key))
        json.dumps(self.result)                        # the result is plain JSON data

    def test_attachment_is_declared_and_measured(self):
        units = set(registry.load_all())
        for cid, c in self.C.items():
            d = DECL[cid]
            self.assertIn(c["scope"], ("UNIT", "STAGE", "BUILDING"), cid)
            self.assertEqual(c["units"], d["units"], cid)
            self.assertEqual(list(c["by_unit"]), d["units"], cid)          # units = exactly the units measured on their own output
            self.assertFalse(set(d["units"]) & set(d["units_stage_level"]), cid)
            self.assertLessEqual(set(d["units"]) | set(d["units_stage_level"]), units, cid)
            self.assertEqual(c["evidence_scope"], evidence_scope(d), cid)
            self.assertEqual(set(c["evidence_scope"]), set(d["units"]) | set(d["units_stage_level"]), cid)
            if c["scope"] == "STAGE":
                self.assertFalse(c["units"], cid)
            self.assertIn(c["parameters_from"], (None, IN_SAMPLE, SPLIT), cid)
            self.assertIsInstance(c["inputs_measured"], bool, cid)
            self.assertIsInstance(c["load"]["measured"], bool, cid)
            self.assertIn("local_total_error", c, cid)
            self.assertNotIn("total_error", c, cid)
            if c["by_material_class"] is None:
                self.assertTrue(c["by_material_class_reason"], cid)
            else:
                self.assertIn("n_reference_zero_candidate_nonzero", c["by_material_class_zero_reference"], cid)
        for cid in ("AP-18a", "AP-18b", "AP-18c", "AP-18", "AP-19a", "AP-23b"):
            self.assertEqual(self.C[cid]["parameters_from"], IN_SAMPLE)
        for cid in ("AP-10", "AP-10b", "AP-11", "AP-15", "AP-16", "AP-18d", "AP-21", "AP-22b", "AP-23c"):
            self.assertEqual(self.C[cid]["parameters_from"], SPLIT)
        self.assertIs(self.C["AP-19a"]["keeps_row_membership"], True)
        self.assertIs(self.C["AP-19c"]["keeps_row_membership"], False)

    def test_propagated_totals(self):
        for cid, c in self.C.items():
            if DECL[cid]["downstream_reuse"] == PROPAGATED:
                p = c["propagation"]
                self.assertTrue(p["measured"], cid)
                self.assertEqual(c["total_error_kind"], "PROPAGATED", cid)
                # the rewritten scenario makes the reference compute the candidate's own value
                self.assertLess(p["rewrite_reproduces_local_candidate_max_rel_diff"], 1e-9, cid)
            else:
                self.assertIsNone(c["propagated_total_error"], cid)
        a = self.C["AP-06"]
        self.assertGreater(a["propagated_total_error"]["max_abs"], a["local_total_error"]["max_abs"])
        self.assertAlmostEqual(a["propagation"]["stage_error"]["A1-A3"]["max_under"], a["stage_error"]["max_under"], delta=1e-12)

    def test_electricity_candidates_are_judged_on_the_worst_stage(self):
        c = self.C["AP-08"]
        self.assertEqual(set(c["by_stage"]), {"B6", "B2"})
        self.assertEqual(c["stage_error"], c["by_stage"]["B6"])
        self.assertGreaterEqual(c["by_stage"]["B2"]["max_abs"], c["by_stage"]["B6"]["max_abs"])
        self.assertEqual(c["worst_stage"]["stage"], "B2")
        self.assertEqual(c["by_unit"]["B2-01"]["値（= 段階 B2）"]["error"], c["by_stage"]["B2"])
        self.assertTrue(any(k.startswith("B6-03") for k in c["other_targets"]))
        self.assertEqual(self.C["AP-18c"]["worst_stage"]["measured_in"] in ("by_stage", "propagation"), True)
        self.assertEqual(set(self.C["AP-18c"]["by_stage"]), {"C3", "C4"})

    def test_safe_side_repairs_and_the_two_refrigerant_variants(self):
        for cid in ("AP-23a", "AP-23b"):
            c = self.C[cid]
            self.assertFalse(c["under_estimates"], cid)
            self.assertGreater(c["stage_error"]["max_under"], -1e-9, cid)
            self.assertLessEqual(c["stage_error"]["max_over"], self.C["AP-04"]["stage_error"]["max_over"], cid)
            self.assertEqual(len(c["stress_scenarios"]["cases"]), len(measures.STRESS_CASES), cid)
            self.assertFalse(c["stress_scenarios"]["within_stage_target"], cid)       # lives near the period exceed the stage target
            self.assertFalse(c["within_stage_target"], cid)                           # ... and that decides the flag
            self.assertIn("within_stage_target_on_population", c, cid)
            self.assertLess(c["sign_guarantee"]["counter_example_below_one_year"]["stage_error"]["max_under"], 0.0, cid)
        a, b = self.C["AP-05a"], self.C["AP-05b"]
        self.assertEqual(b["renamed_from"], "AP-05")
        self.assertLessEqual(a["stage_error"]["mean_signed"], b["stage_error"]["mean_signed"])
        self.assertFalse(a["under_estimates"] or b["under_estimates"])
        self.assertEqual(a["by_unit"]["B1-02"], b["by_unit"]["B1-02"])    # the leak itself is the same in both
        # the consistent form under-states the mass that remains, so the units B1-03 and B1-04 are under-estimated
        # although the stage B1 is not; "treated as topped up" over-states every part
        self.assertEqual(a["units_under_estimated"], ["B1-03", "B1-04"])
        self.assertEqual(b["units_under_estimated"], [])

    def test_bound_of_the_count_forms_under_the_time_rule(self):
        case = self.C["AP-20"]["bound"]["near_boundary_scenario"]
        self.assertEqual(case["reference_counts"], [2])
        self.assertFalse(case["inside_with_lower_bound_T_over_c_minus_1"])      # T/c - 1 exceeds the reference count here
        self.assertTrue(case["inside_with_lower_bound_T_c0_over_c_minus_1"])
        self.assertTrue(case["upper_bound_holds"])
        self.assertGreater(case["ap01_error_on_B4"], 0.0)
        self.assertLess(case["ap01_error_on_B4"], 1e-8)

    def test_table_candidates_equal_the_reference_run_on_the_coarse_tables(self):
        """AP-24a computes its value locally; overwriting the year tables and re-running the reference must give the same."""
        from refcalc.base import profile_uses_descriptor
        scn = synth.make_scenario(41, "W", "school", "S", 42.5, profile_kind="TABLE", n_materials=6, n_equipment=3, n_refrigerants=1)
        S = measures.One(scn, registry.run_all(scn))
        X = measures.Study()
        measures.m_annual_tables(S, X)
        measures.m_electricity(S, X)
        op, ww = scn.operation, scn.water_waste

        def edit(profiles):
            def change(p):
                for profile in profiles:
                    self.assertFalse(profile_uses_descriptor(profile))
                    table = list(profile.table)
                    table[:S.Y] = sp.coarse(table[:S.Y], 5)
                    p.set(profile, "table", table)
            return change

        new = sp.rerun(scn, edit((op.gas, op.oil, op.district_heat, ww.water, ww.sewage, ww.municipal_waste)), ["X-02"])["X-02"]["by_stage_all"]
        for stage in ("B6", "B7"):
            self.assertAlmostEqual(X.C["AP-24a"].stages[stage].errors[0], (new[stage] - S.stage[stage]) / S.stage[stage], delta=1e-12)
        new = sp.rerun(scn, edit((op.electricity, op.onsite_generation, op.onsite_export)), ["X-02"])["X-02"]["by_stage_all"]
        for stage in ("B6", "B2"):
            self.assertAlmostEqual(X.C["AP-24b"].stages[stage].errors[0], (new[stage] - S.stage[stage]) / S.stage[stage], delta=1e-12)

    def test_load_is_measured_on_the_same_rows(self):
        for cid in ("AP-01", "AP-02", "AP-03", "AP-04", "AP-05a", "AP-05b", "AP-06", "AP-06b", "AP-07a", "AP-07b", "AP-23a"):
            load = self.C[cid]["load"]
            self.assertTrue(load["measured"], cid)
            self.assertGreater(load["candidate_instructions"], 0, cid)
            self.assertGreater(load["exact_closed_form_instructions"], 0, cid)
            if load["exact_kernel_max_rel_diff_to_reference"] is not None:
                self.assertLess(load["exact_kernel_max_rel_diff_to_reference"], 1e-9, cid)
        self.assertEqual(self.C["AP-06"]["load"]["ratio_candidate_to_exact"], 1.0)
        self.assertTrue(self.C["AP-08"]["load"]["cases"])


if __name__ == "__main__":
    unittest.main()
