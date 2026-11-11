"""Tests of the two measurement scripts: the operation probe and the membership check.

Besides "the statements hold on a small scenario" the tests break the unified model on
purpose and require the probe to notice: a measurement that cannot fail is no evidence.

Run:  cd research_code && python3 -m unittest tests.test_mechanism_probe -v
"""
import ast
import contextlib
import inspect
import unittest

import synth
from bench import mechanism_probe as probe
from bench import membership_check as membership
from fastcalc import closed_forms as cf
from fastcalc import engine
from synth import population

ROWS = {"n_materials": 40, "n_equipment": 16, "n_refrigerants": 5, "composite_share": 0.3, "epd_share": 0.3,
        "explicit_event_share": 0.3, "change_list_share": 0.4}


def parametric():
    return synth.make_scenario(5, "RC", "office", "S", 60.0, profile_kind="LINEAR_TREND", grid_kind="LINEAR_DECLINE_TO_FLOOR",
                               replacement_cycle=25.0, reconstruction_scenario="REBUILD_IDENTICAL", **ROWS)


def year_tables():
    return synth.make_scenario(5, "RC", "office", "S", 42.5, profile_kind="TABLE", grid_kind="TABLE", **ROWS)


@contextlib.contextmanager
def replaced(owner, name, make):
    original = owner.__dict__[name] if isinstance(owner, type) else getattr(owner, name)
    setattr(owner, name, make(original))
    try:
        yield
    finally:
        setattr(owner, name, original)


class ProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scenarios = {"parametric": probe.measure(parametric()), "year_tables": probe.measure(year_tables())}
        cls.statements = probe.statements(cls.scenarios)

    def test_statements_hold_on_small_scenarios(self):
        for key in ("P1", "P2", "P3", "P4", "P5", "P6", "P7"):
            self.assertIs(self.statements[key]["holds"], True, key)
        self.assertEqual(self.statements["P4"]["scenarios_it_was_evaluated_on"], ["parametric"])
        self.assertFalse(self.statements["P6"]["refrigerant_rows_read_again"])
        self.assertTrue(probe.engine_counters_agree(self.scenarios)["all_agree"])
        for s in self.scenarios.values():
            self.assertTrue(s["results_identical_to_an_uninstrumented_run"])

    def test_counts_are_those_of_the_inputs(self):
        s = self.scenarios["parametric"]
        rows = s["input"]["rows"]
        t, f = s["totals_only"], s["full_outputs"]
        # rows: handed out once in the aggregation, never afterwards
        for kind in ("materials", "equipment", "refrigerants"):
            self.assertEqual(t["aggregate"]["row_lists"][kind]["rows_handed_out"], rows[kind])
            self.assertEqual(t["aggregate"]["row_lists"][kind]["distinct_rows_read"], rows[kind])
            self.assertEqual(sum(f["finish"]["row_lists"][kind].values()), 0)
        # factor values: per row only when per-row outputs are asked for
        agg = f["aggregate"]["multiplications"]["factor_value"]
        self.assertGreater(agg["while_reading_a_material_or_equipment_row"], rows["materials"] + rows["equipment"])
        self.assertEqual(t["aggregate"]["multiplications"]["factor_value"]["total"],
                         t["aggregate"]["multiplications"]["factor_value"]["in_recipe_builder"])
        # the table read-out multiplies once per entry with a factor record (pseudo keys have no record)
        fin = t["finish"]
        self.assertLessEqual(fin["multiplications"]["factor_value"]["in_table_read_out"], fin["table_read_out"]["entries"])
        self.assertGreater(fin["multiplications"]["factor_value"]["in_table_read_out"], 0.9 * fin["table_read_out"]["entries"])
        # one charge x GWP product per device, in the aggregation only
        self.assertEqual(t["aggregate"]["multiplications"]["device_gwp"]["total"], rows["refrigerants"])
        self.assertNotIn("device_gwp", fin["multiplications"])
        # event-year lists
        lists = fin["event_year_lists"]["lists_by_kind"]
        self.assertEqual(lists.get("explicit_equipment", 0), s["input"]["rows_with"]["explicit_event_list"])
        self.assertEqual(lists.get("refrigerant_explicit", 0) + lists.get("refrigerant_periodic", 0), rows["refrigerants"])
        self.assertGreater(f["finish"]["event_year_lists"]["lists_by_kind"]["periodic_material_equipment"], 0)
        self.assertEqual(f["finish"]["event_year_lists"]["lists_by_kind"]["rebuild"], 1)
        # yearly values: ten series are generated and compared (the consistency scan), nothing else
        Y = 60
        self.assertEqual(fin["year_loops"]["yearly_values_by_class"], {"copy_check": 10 * Y, "series_generation": 10 * Y})
        self.assertEqual(fin["year_table_values_read"], {"_same": 10 * Y})
        tab = self.scenarios["year_tables"]["totals_only"]["finish"]["year_loops"]["yearly_values_by_class"]
        self.assertEqual(tab["value_loop"], 8 * 43)            # 6 annual quantities, the grid moments, purchased electricity
        self.assertEqual(tab["validity_scan"], 10 * 43)
        self.assertNotIn("copy_check", tab)
        # the resolver
        agg = t["aggregate"]
        self.assertEqual(agg["record_checks"]["calls"], agg["record_checks"]["distinct_factor_stage_pairs"])
        self.assertEqual(agg["epd_applicability_checks"], s["input"]["rows_with"]["product_specific_factor"])
        self.assertGreater(agg["resolutions"]["per_row_with_row_conversions"]["calls"], 0)
        self.assertEqual(agg["recipes_computed"], s["input"]["distinct"]["compositions"])

    def test_the_observer_restores_everything(self):
        before = {name: getattr(owner, name) for name, (owner, _, _) in probe.YEAR_LOOPS.items()}
        before.update(tot=engine.tot, use=engine.Resolver.__dict__["use"], periodic=cf.periodic_years)
        probe.measure(parametric())
        after = {name: getattr(owner, name) for name, (owner, _, _) in probe.YEAR_LOOPS.items()}
        after.update(tot=engine.tot, use=engine.Resolver.__dict__["use"], periodic=cf.periodic_years)
        self.assertEqual(before, after)
        self.assertEqual(probe._S.phase, "idle")

    # ---- the probe must be able to say "false" ----

    def _statements_with(self, owner, name, make, scenario=parametric):
        with replaced(owner, name, make):
            return probe.statements({"case": probe.measure(scenario())})

    def test_p1_fails_when_a_factor_is_multiplied_per_row(self):
        def per_row_product(original):
            def use(self, fid, stage, unit, extra, path):
                hit = original(self, fid, stage, unit, extra, path)
                if hit is not None:
                    hit[1] * self.fval[hit[0]]                 # a row-wise product nobody needs
                return hit
            return use
        st = self._statements_with(engine.Resolver, "use", per_row_product)
        self.assertIs(st["P1"]["holds"], False)
        self.assertGreater(st["P1"]["evidence"]["case"]["factor_value_products_per_row"], 40)

    def test_p2_and_p6_fail_when_finish_reads_the_rows(self):
        def reads_rows(original):
            def finish(A, *args, **kwargs):
                for row in A.scn.materials:
                    row.quantity
                return original(A, *args, **kwargs)
            return finish
        st = self._statements_with(engine, "finish", reads_rows)
        self.assertIs(st["P2"]["holds"], False)
        self.assertIs(st["P6"]["holds"], False)

    def test_p3_fails_when_renewal_years_are_listed_in_totals_mode(self):
        def lists_years(original):
            def renewal_count(T, period):
                n = original(T, period)
                if n:
                    engine._renewal_years(period, n)
                return n
            return renewal_count
        st = self._statements_with(cf, "renewal_count", lists_years)
        self.assertIs(st["P3"]["holds"], False)
        self.assertGreater(st["P3"]["evidence"]["case"]["lists_by_kind"]["periodic_material_equipment"], 0)

    def test_p3_fails_for_a_list_built_outside_the_named_functions(self):
        def lists_years(original):
            def skip_weight_periodic(T, period, n):
                cf.periodic_years(period, n)
                return original(T, period, n)
            return skip_weight_periodic
        st = self._statements_with(cf, "skip_weight_periodic", lists_years)
        self.assertIs(st["P3"]["holds"], False)
        self.assertTrue(any(kind.startswith("other:") for kind in st["P3"]["evidence"]["case"]["lists_by_kind"]))

    def test_p4_fails_when_a_descriptor_is_summed_year_by_year(self):
        def by_scan(original):
            def linear_weighted_sum(T, base, slope):
                return cf.table_weighted_sum([base + slope * k for k in range(cf.n_years(T))], T)
            return linear_weighted_sum
        st = self._statements_with(cf, "linear_weighted_sum", by_scan)
        self.assertIs(st["P4"]["holds"], False)

    def test_p5_and_p7_fail_without_the_memos(self):
        def forgetful(original):
            def record(self, fid, stage):
                self.records.clear()
                return original(self, fid, stage)
            return record
        st = self._statements_with(engine.Resolver, "record", forgetful)
        self.assertIs(st["P7"]["holds"], False)

        class Forgetful(dict):
            def get(self, key, default=None):
                return None

        def no_recipe_memo(original):
            def init(self, scn, detail):
                original(self, scn, detail)
                self.recipes = Forgetful()                     # every composite row computes its factor again
            return init
        st = self._statements_with(engine.Aggregate, "__init__", no_recipe_memo)
        self.assertIs(st["P5"]["holds"], False)
        ev = st["P5"]["evidence"]["case"]
        self.assertEqual(ev["recipes_computed_totals_only"], ev["rows_with_a_composition"])


class StructureTests(unittest.TestCase):
    """The probe counts named functions; these tests make sure nothing happens outside them."""

    def _functions(self, module):
        tree = ast.parse(inspect.getsource(module))
        out = {}

        def visit(node, name):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out[child.name if name is None else f"{name}.{child.name}"] = child
                    visit(child, child.name if name is None else f"{name}.{child.name}")
                elif isinstance(child, ast.ClassDef):
                    visit(child, child.name if name is None else f"{name}.{child.name}")
                else:
                    visit(child, name)
        visit(tree, None)
        return out

    def _own_nodes(self, fn):
        """Nodes of a function that are not inside a nested function."""
        stack = list(ast.iter_child_nodes(fn))
        while stack:
            node = stack.pop()
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            yield node
            stack.extend(ast.iter_child_nodes(node))

    def test_every_loop_over_range_is_in_a_counted_function(self):
        allowed = set(probe.YEAR_LOOPS) | set(probe.OTHER_RANGE_LOOPS)
        found = set()
        for module in (engine, cf):
            for name, fn in self._functions(module).items():
                for node in self._own_nodes(fn):
                    iters = [node.iter] if isinstance(node, (ast.For, ast.comprehension)) else []
                    for it in iters:
                        if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range":
                            found.add(name)
        self.assertEqual(found - allowed, set(), "a loop over range(...) outside the functions the probe counts")
        self.assertEqual(set(probe.YEAR_LOOPS) - found, {"_same"})      # _same walks the two series with zip
        self.assertEqual(set(probe.OTHER_RANGE_LOOPS) - found, set())
        for name in ("aggregate", "finish", "_detail", "_detail.years_of", "finish.gas_of", "finish.check_list"):
            self.assertNotIn(name, found)
        for name, (owner, _, _) in probe.YEAR_LOOPS.items():
            self.assertTrue(callable(getattr(owner, name)), name)

    def test_event_year_lists_are_built_only_by_the_named_functions(self):
        builders = {caller for (_, caller) in probe.EVENT_LIST_KINDS}
        for name, fn in self._functions(engine).items():
            for node in self._own_nodes(fn):
                if (isinstance(node, ast.Attribute) and node.attr in ("periodic_years", "explicit_years", "periodic_year")
                        and isinstance(node.value, ast.Name) and node.value.id == "cf"):
                    self.assertIn(name, builders, f"{name} builds a list of event years")
        # in closed_forms nothing but the two list functions themselves produces a list of years
        for name, fn in self._functions(cf).items():
            for node in self._own_nodes(fn):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("periodic_years", "explicit_years"):
                    self.fail(f"closed_forms.{name} calls {node.func.id}")

    def test_finish_and_detail_do_not_name_the_row_lists(self):
        fns = self._functions(engine)
        for name in ("finish", "_detail"):
            attrs = {node.attr for node in ast.walk(fns[name]) if isinstance(node, ast.Attribute)}
            self.assertEqual(attrs & {"materials", "equipment", "refrigerants"}, set(), name)


class MembershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = membership.run()

    def test_the_default_run_is_sound(self):
        r = self.result
        self.assertTrue(r["unbroken_run_agrees_with_reference"])
        self.assertTrue(r["every_branch_exercised"], r["branches_exercised"])
        self.assertEqual(r["faults_that_raised"], [])
        self.assertEqual(r["shared_objects_without_effect"], [])
        self.assertTrue(r["direct_outputs"]["results_unchanged_by_marking"])
        for name, entry in r["shared_objects"].items():
            self.assertTrue(entry["detection_equals_change"], name)
        self.assertEqual(len(r["units"]), 70)

    def test_units_react_to_the_shared_objects_they_are_built_from(self):
        obj, units = self.result["shared_objects"], self.result["units"]
        for mode in ("full", "totals"):
            self.assertLessEqual({"B1-01", "B1-02", "B1-03", "B1-04"}, set(obj["K4.device_table:scaled"]["units_changed_" + mode]))
            self.assertNotIn("B1-01", obj["K4.refrigerant_fractions"]["units_changed_" + mode])
            left_out = set(obj["K5.indicator:stage_left_out"]["units_changed_" + mode])
            self.assertLessEqual({f"SUM-0{i}" for i in range(1, 9)}, left_out)
            self.assertNotIn("SUM-07", obj["K5.indicator:scaled"]["units_changed_" + mode])     # a ratio: the factor cancels
            self.assertEqual(set(obj["K6._within"]["units_changed_" + mode]), {"SYS-04", "QA-04", "QA-01", "X-04"})
            self.assertIn("QA-03", obj["K1.tables:key_removed"]["units_changed_" + mode])
            self.assertEqual(obj["K7.licence_findings"]["units_changed_" + mode], ["QA-03"])
            self.assertIn("SYS-02", obj["K7.Resolver.convert:missing"]["units_changed_" + mode])
        # the closed form of an annual quantity is seen through the sums it enters, not through the unit itself
        for mode in ("full", "totals"):
            detected = self.result["closed_forms"]["linear_weighted_sum"]["detected_by_" + mode]
            self.assertLessEqual({"B6-03", "B7-04", "X-02", "SUM-03"}, set(detected))
            self.assertEqual({"B6-02", "B7-01", "B7-02", "B7-03"} & set(detected), set())
        # units that are not read from any shared table or function of a model
        for uid in ("A13-05", "X-13"):
            self.assertNotIn("K1", units[uid]["models_sensitive_to"])
        self.assertNotIn("K7", units["SYS-03"]["models_sensitive_to"])
        for uid in ("SYS-01", "STO-01"):
            self.assertEqual(units[uid]["sensitive_to"], [], uid)
        # flag-only units in totals mode
        for uid in ("B6-01", "B6-04", "X-06", "B4-03", "X-13"):
            self.assertTrue(units[uid]["flag_only_in_totals"], uid)
        self.assertFalse(units["A13-01"]["flag_only_in_totals"])
        self.assertEqual(units["B6-02"]["keys_in_totals"], ["descriptors_match_tables", "n_skipped"])

    def test_direct_outputs(self):
        direct = self.result["direct_outputs"]["by_function"]
        self.assertLessEqual({"A13-01", "X-02", "B4-02", "STO-02"}, set(direct["K1.tot"]["units_totals"]))
        self.assertEqual(set(direct["K5.indicator"]["units_totals"]), {f"SUM-0{i}" for i in range(1, 9)} | {"X-07"})
        self.assertEqual(direct["K3.linear_weighted_sum"]["units_totals"], [])
        self.assertEqual(direct["K2.periodic_years"]["units_totals"], [])
        self.assertIn("B4-01", direct["K2.periodic_years"]["units_full"])

    def test_claims_are_compared_with_the_measurement(self):
        claims = {"models": [{"id": "K1", "units": ["A13-01", "A13-05", "X-13"]}, {"id": "K4", "units": ["B1-01", "B1-02"]},
                             {"id": "K7", "units": ["SYS-02", "SYS-03"]}]}
        got = membership.against_claims(self.result, claims)
        self.assertEqual(got["claimed_members"], 7)
        self.assertEqual(got["not_sensitive_to_any_shared_object_of_their_model"], ["A13-05 (K1)", "SYS-03 (K7)", "X-13 (K1)"])
        self.assertEqual(got["per_model"]["K4"]["not_sensitive_to_any_shared_object_of_the_model"], [])

    def test_a_tiny_scenario_set_and_restoration(self):
        scn = synth.make_scenario(3, "S", "office", "S", 60.0, n_materials=12, n_equipment=6, n_refrigerants=4,
                                  profile_kind="CONSTANT", grid_kind="CONSTANT")
        population.attach_baseline(scn)
        before = (engine.tot, engine.indicator, cf.renewal_count, engine.Resolver.__dict__["convert"])
        r = membership.run({"tiny": scn})
        self.assertEqual(before, (engine.tot, engine.indicator, cf.renewal_count, engine.Resolver.__dict__["convert"]))
        self.assertTrue(r["unbroken_run_agrees_with_reference"])
        self.assertFalse(r["every_branch_exercised"])           # one constant scenario cannot exercise the year tables
        self.assertIn("A13-01", r["shared_objects"]["K1.tot"]["units_changed_totals"])
        self.assertEqual(r["shared_objects"]["K3.table_weighted_sum"]["units_changed_totals"], [])
        self.assertIn("K3.table_weighted_sum", r["shared_objects_without_effect"])


if __name__ == "__main__":
    unittest.main()
