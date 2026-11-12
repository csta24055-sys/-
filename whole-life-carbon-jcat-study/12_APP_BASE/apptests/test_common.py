"""System 2: common input data and conversion for the engine."""
import copy
import unittest

from lcaapp import binding, common, convert, schema
from . import helpers as H


class StatesTest(unittest.TestCase):
    def setUp(self):
        self.doc, self.ref, self.md = H.building()

    def test_missing_zero_absent_are_told_apart(self):
        doc = self.doc
        H.set_item(doc, "project", "project.gross_floor_area", 1500.5)                 # entered
        H.set_item(doc, "construction", "construction.electricity_kwh", 0)             # zero
        H.set_item(doc, "project", "project.building_height", None)                    # missing (null)
        del doc["categories"]["project"]["items"]["project.maximum_span"]              # missing (left out)
        H.set_item(doc, "project", "project.typical_floor_area", "")                   # missing (blank field)
        H.set_item(doc, "project", "project.building_footprint", {"state": "absent"})  # absent
        data = H.to_common(doc, self.ref)
        get = lambda name: H.cell_at(data, "project", name)
        self.assertEqual((get("gross_floor_area")["s"], get("gross_floor_area")["v"]), ("entered", 1500.5))
        zero = H.cell_at(data, "construction", "electricity_kwh")
        self.assertEqual((zero["s"], zero["v"]), ("zero", 0))
        for name in ("building_height", "maximum_span", "typical_floor_area"):
            self.assertEqual((get(name)["s"], get(name)["v"]), ("missing", None), name)
        self.assertEqual(get("building_footprint")["s"], "absent")
        model, report = convert.to_model(data, self.ref, "T")
        self.assertEqual(model["project"]["gross_floor_area"], 1500.5)
        self.assertEqual(model["construction"]["electricity_kwh"], 0)                  # a zero stays a zero
        for name in ("building_height", "maximum_span", "typical_floor_area", "building_footprint"):
            self.assertIsNone(model["project"][name], name)                             # never turned into 0
        self.assertIn("project.building_footprint", report["not_passed"]["absent"])
        self.assertIn("project.building_height", report["not_passed"]["missing"])

    def test_value_with_unit_is_kept_or_converted(self):
        doc = self.doc
        H.set_item(doc, "project", "project.building_height", {"value": 31.5, "unit": "m"})
        H.set_item(doc, "project", "project.maximum_span", {"value": 0.012, "unit": "km"})       # km -> m is documented
        H.set_item(doc, "project", "project.gross_floor_area", {"value": 3, "unit": "furlong"})  # no conversion
        doc["categories"]["materials"]["tables"]["materials"][0]["quantity"] = {"value": 12.5, "unit": "m3"}
        doc["categories"]["materials"]["tables"]["materials"][0]["quantity_unit"] = None
        doc["categories"]["materials"]["tables"]["materials"][1]["quantity"] = {"value": 7, "unit": "definitely-not-" + str(
            doc["categories"]["materials"]["tables"]["materials"][1]["quantity_unit"])}
        data = H.to_common(doc, self.ref)
        self.assertEqual(H.cell_at(data, "project", "building_height")["v"], 31.5)
        span = H.cell_at(data, "project", "maximum_span")
        self.assertAlmostEqual(span["v"], 12.0)
        self.assertEqual(span["raw"], {"value": 0.012, "unit": "km"})                  # what was typed is kept
        area = H.cell_at(data, "project", "gross_floor_area")
        self.assertEqual((area["s"], area["v"]), ("invalid", None))
        self.assertEqual(area["raw"], {"value": 3, "unit": "furlong"})
        row0 = H.cell_at(data, "materials", 0)
        self.assertEqual(row0["f"]["quantity_unit"]["v"], "m3")                        # unit travelled with the value
        self.assertEqual(H.cell_at(data, "materials", 1)["f"]["quantity"]["s"], "invalid")   # contradicting units
        codes = {i["code"] for i in data["issues"]}
        self.assertTrue({"unit_converted", "unit_mismatch", "unit_conflict"} <= codes)

    def test_bad_values_are_reported_not_computed(self):
        doc = self.doc
        bad = {"project.gross_floor_area": "abc", "project.building_height": "NaN", "project.maximum_span": True,
               "project.floors_above": 3.5, "project.structure_type": "PAPER", "project.use_area_breakdown": [1, 2],
               "project.completion_year": {"value": [2030]}}
        for item_id, value in bad.items():
            H.set_item(doc, "project", item_id, value)
        H.set_item(doc, "boundary", "boundary.included_lifecycle_stages", ["A1-A3", "Z9"])
        data = H.to_common(doc, self.ref)
        for item_id in bad:
            cell = H.cell_at(data, "project", item_id.split(".", 1)[1])
            self.assertEqual(cell["s"], "invalid", item_id)
            self.assertIn("raw", cell)
        self.assertEqual(H.cell_at(data, "boundary", "included_lifecycle_stages")["s"], "invalid")
        self.assertEqual(data["stats"]["invalid"], len(bad) + 1)
        model, report = convert.to_model(data, self.ref, "T")
        self.assertIsNone(model["project"]["gross_floor_area"])
        self.assertEqual(model["project"]["use_area_breakdown"], {})
        self.assertTrue(any(b["path"] == "project.use_area_breakdown" for b in report["blocking"]))

    def test_numbers_given_as_text_are_read_and_noted(self):
        H.set_item(self.doc, "project", "project.gross_floor_area", " 2916.0 ")
        H.set_item(self.doc, "project", "project.floors_above", 8.0)
        data = H.to_common(self.doc, self.ref)
        self.assertEqual(H.cell_at(data, "project", "gross_floor_area")["v"], 2916.0)
        self.assertEqual(H.cell_at(data, "project", "floors_above")["v"], 8)
        self.assertEqual(sum(1 for i in data["issues"] if i["code"] == "coerced"), 2)

    def test_other_entries_are_kept(self):
        doc = self.doc
        for cat in doc["categories"]:
            doc["categories"][cat]["others"] = [{"label": "特記 " + cat, "value": 12.5, "unit": "kg", "note": "メモ"},
                                                "自由記述だけの項目", 42, {"anything": ["goes", 1]}]
        data = H.to_common(doc, self.ref)
        self.assertEqual(len(data["others"]), 4 * len(doc["categories"]))
        first = data["others"][0]
        self.assertEqual((first["label"], first["value"], first["unit"], first["note"]), ("特記 project", 12.5, "kg", "メモ"))
        self.assertEqual(data["others"][3]["raw"], {"anything": ["goes", 1]})
        base = H.to_common(H.building()[0], self.ref)
        self.assertEqual(convert.to_model(data, self.ref, "T")[0], convert.to_model(base, self.ref, "T")[0])   # never computed

    def test_unknown_and_malformed_parts_are_reported(self):
        doc = self.doc
        doc["categories"]["project"]["items"]["no.such.item"] = 5
        doc["categories"]["project"]["tables"]["no_such_table"] = [{"a": 1}]
        doc["categories"]["materials"]["tables"]["materials"][0]["no_such_column"] = "x"
        doc["categories"]["materials"]["tables"]["materials"].append("not a row")
        doc["categories"]["broken"] = "not an object"
        doc["categories"]["half"] = {"items": [1, 2, 3], "tables": "x", "surprise": 1}
        doc["categories"]["equipment"]["tables"]["equipment"] = {"not": "a list"}
        data = H.to_common(doc, self.ref)
        kinds = [u["kind"] for u in data["unsupported"]]
        for kind in ("unknown_item", "unknown_table", "unknown_column", "invalid_row", "invalid_category", "invalid_items",
                     "invalid_tables", "unknown_key"):
            self.assertIn(kind, kinds)
        self.assertEqual(data["sections"]["equipment"]["s"], "invalid")
        self.assertEqual(data["sections"]["equipment"]["raw"], {"not": "a list"})
        model, _ = convert.to_model(data, self.ref, "T")
        self.assertEqual(model["equipment"], [])
        self.assertEqual(len(model["materials"]), 12)

    def test_tables_missing_absent_and_absent_rows(self):
        doc = self.doc
        del doc["categories"]["refrigerants"]["tables"]["refrigerants"]                 # not given
        doc["categories"]["equipment"]["tables"]["equipment"] = []                      # there are none
        doc["categories"]["materials"]["tables"]["materials"][2]["@state"] = "absent"
        data = H.to_common(doc, self.ref)
        self.assertEqual(data["sections"]["refrigerants"]["s"], "missing")
        self.assertEqual(data["sections"]["equipment"]["s"], "absent")
        model, report = convert.to_model(data, self.ref, "T")
        self.assertEqual((model["refrigerants"], model["equipment"]), ([], []))
        self.assertEqual(len(model["materials"]), 11)
        self.assertEqual(report["dropped_rows"], ["materials[2]"])
        self.assertIn("refrigerants", report["not_passed"]["missing"])

    def test_not_an_object(self):
        for doc in (None, [], "text", 3):
            with self.assertRaises(common.InputError):
                common.build(doc, binding.provisional())
        data = common.build({}, binding.provisional())                                 # an empty object is just empty
        self.assertEqual(data["stats"]["entered"], 0)
        self.assertGreater(data["stats"]["missing"], 50)


class BindingTest(unittest.TestCase):
    def test_provisional_binding_covers_the_model(self):
        cover = binding.provisional().coverage()
        self.assertEqual(cover["unbound"], [])
        self.assertEqual(cover["model_leaves"], len(list(schema.leaves())))

    def test_another_classification_gives_the_same_engine_input(self):
        """A made-up tree of five categories with other ids: only the binding file changes."""
        doc, ref, md = H.building()
        five = {"project": "建物", "boundary": "建物", "provenance": "建物", "summary_quantities": "資材", "materials": "資材",
                "cost_items": "資材", "equipment": "設備", "refrigerants": "設備", "construction": "施工と解体",
                "end_of_life": "施工と解体", "operation": "運用", "water_waste": "運用"}
        base = binding.provisional()
        mapping = {path: {"id": "項目:" + entry["id"].replace(".", "／"), "category": five[entry["category"]]}
                   for path, entry in base.entries.items()}
        custom = binding.from_json({"format": binding.BINDING_FORMAT, "id": "test-five", "version": "t1",
                                    "classification": {"id": "made-up-test-tree", "version": "t1"},
                                    "categories": {c: c for c in set(five.values())}, "map": mapping})
        from lcaapp import sample
        doc5 = sample.document_from_model(md, custom, "five", "fictional", ref)
        self.assertEqual(set(doc5["categories"]), set(five.values()))
        self.assertEqual(len(doc5["categories"]), 5)
        model5, _ = convert.to_model(H.to_common(doc5, ref, custom), ref, "T")
        model1, _ = convert.to_model(H.to_common(doc, ref), ref, "T")
        self.assertEqual(model5, model1)
        # the document of one classification is not understood under the other binding: reported, not guessed
        crossed = H.to_common(doc5, ref)
        self.assertEqual(crossed["stats"]["entered"], 0)
        self.assertGreater(crossed["stats"]["unsupported"], 100)

    def test_partial_binding_leaves_the_rest_missing(self):
        doc, ref, md = H.building()
        base = binding.provisional()
        keep = {p: e for p, e in base.entries.items() if p.startswith(("project", "boundary", "materials"))}
        part = binding.from_json({"format": binding.BINDING_FORMAT, "id": "part", "version": "1", "map": keep})
        data = H.to_common(doc, ref, part)
        self.assertGreater(data["stats"]["unbound"], 50)
        self.assertEqual(part.coverage()["bound"], len(keep))
        model, report = convert.to_model(data, ref, "T")
        self.assertEqual(model["materials"], md["materials"])
        self.assertEqual(model["equipment"], [])
        self.assertTrue(report["blocking"])                                            # the grid data is not bound

    def test_binding_file_with_a_wrong_path_is_refused(self):
        with self.assertRaises(ValueError):
            binding.from_json({"format": binding.BINDING_FORMAT, "map": {"project.no_such_field": "x"}})
        with self.assertRaises(ValueError):
            binding.from_json({"format": "something else"})

    def test_classification_tree_reader(self):
        tree = {"version": "t", "categories": [
            {"name": "建物概要", "children": [{"name": "延べ床面積"}, {"name": "構造"}, {"name": "その他"}]},
            {"name": "資材", "children": [{"name": "躯体", "children": [{"name": "コンクリート量"}]}, {"name": "その他"}]},
            {"name": "設備", "children": [{"name": "その他"}]},
            {"name": "運用", "children": [{"name": "電力"}, {"name": "その他"}]},
            {"name": "解体", "children": [{"name": "その他"}]}]}
        out = binding.read_tree(tree, "made-up")
        self.assertEqual(out["n_categories"], 5)
        self.assertEqual([c["id"] for c in out["categories"]], ["建物概要", "資材", "設備", "運用", "解体"])
        self.assertEqual(len(out["others"]), 5)
        self.assertIn("コンクリート量", [leaf["id"] for leaf in out["leaves"]])
        nested = binding.read_tree({"A": {"x": {}, "その他": {}}, "B": {"y": {"z": {}}}})
        self.assertEqual(nested["n_categories"], 2)
        self.assertEqual(sorted(leaf["id"] for leaf in nested["leaves"]), ["x", "z", "その他"])
        cover = binding.tree_coverage(out, binding.provisional())
        self.assertEqual(cover["bound"], [])                                           # nothing is assumed to match


class ConversionTest(unittest.TestCase):
    def test_round_trip_is_exact_and_engine_results_agree(self):
        for kw in (dict(seed=4201), dict(seed=77, structure="W", use="residential", dirty=True),
                   dict(seed=9, structure="S", use="hospital", grid_kind="STEPWISE")):
            doc, ref, md = H.building(rows=None, **kw)
            checked, left_out = H.refdata.check(ref)
            self.assertEqual(left_out, [])
            data = H.to_common(doc, checked)
            self.assertEqual((data["stats"]["invalid"], data["stats"]["unsupported"], data["n_issues"]), (0, 0, 0), kw)
            model, report = convert.to_model(data, checked, md["meta"]["scenario_id"])
            for part in md:
                if part != "meta":
                    self.assertEqual(model[part], md[part], (kw, part))
            self.assertEqual(report["blocking"], [])
            period = md["boundary"]["study_period"]
            app = H.through_json(H.enginepath.unified().System(convert.build_scenario(model)).at(period))
            self.assertEqual(app, H.direct_results(md, period), kw)

    def test_year_tables_are_expanded_from_descriptors_only(self):
        for grid_kind in ("CONSTANT", "LINEAR_DECLINE_TO_FLOOR", "STEPWISE", "TABLE"):
            doc, ref, md = H.building(seed=31, grid_kind=grid_kind)
            removed = []
            for cat, names in (("operation", ("electricity", "gas", "oil", "district_heat", "onsite_generation", "onsite_export")),
                               ("water_waste", ("water", "sewage", "municipal_waste"))):
                for name in names:
                    if md[cat][name]["kind"] != "TABLE":
                        H.set_item(doc, cat, f"{cat}.{name}.table", None)
                        removed.append(f"{cat}.{name}.table")
            if grid_kind != "TABLE":
                H.set_item(doc, "operation", "operation.grid.table", None)
                removed.append("operation.grid.table")
            model, report = convert.to_model(H.to_common(doc, ref), ref, "T")
            self.assertEqual(sorted(report["expanded_tables"]), sorted(removed), grid_kind)
            self.assertEqual(model["operation"], md["operation"], grid_kind)           # the same numbers as the original tables
            self.assertEqual(model["water_waste"], md["water_waste"], grid_kind)
        doc, ref, md = H.building(seed=31, grid_kind="TABLE")                           # no closed form: nothing is made up
        H.set_item(doc, "operation", "operation.grid.table", None)
        model, report = convert.to_model(H.to_common(doc, ref), ref, "T")
        self.assertIsNone(model["operation"]["grid"]["table"])
        self.assertIn("operation.grid.table", [b["path"] for b in report["blocking"]])

    def test_nothing_is_invented_for_an_empty_input(self):
        _, ref, _ = H.building()
        data = common.build({"format": "lca-input/1", "data_kind": "unknown", "categories": {}}, binding.provisional())
        model, report = convert.to_model(data, ref, "T")
        numbers = []

        def walk(o, path=""):
            if isinstance(o, dict):
                for k, v in o.items():
                    walk(v, path + "." + str(k))
            elif isinstance(o, list):
                for v in o:
                    walk(v, path + "[]")
            elif isinstance(o, (int, float)) and not isinstance(o, bool):
                numbers.append(path)
        walk({k: v for k, v in model.items() if k not in schema.REFERENCE_PARTS and k != "meta"})
        self.assertEqual(numbers, [])                                                  # not one number appeared
        self.assertTrue(report["blocking"])
        self.assertEqual(model["meta"]["source_tag"], convert.USER_TAG)

    def test_optional_records_and_keyed_rows(self):
        doc, ref, md = H.building()
        rows = doc["categories"]["provenance"]["tables"]["provenance"]
        rows.append(dict(rows[0]))                                                     # duplicated key
        rows.append({k: v for k, v in rows[0].items() if k != "provenance_id"})        # no key
        data = H.to_common(doc, ref)
        model, report = convert.to_model(data, ref, "T")
        self.assertEqual(model["provenance"], md["provenance"])
        self.assertEqual(len(report["dropped_rows"]), 2)
        self.assertTrue(all(n["code"] == "row_key" for n in report["notes"] if n["level"] == "error"))
        with_epd = [r for r in md["materials"] if r["epd"] is not None]
        without = [r for r in md["materials"] if r["epd"] is None]
        self.assertTrue(without)
        self.assertEqual([r["epd"] for r in model["materials"]], [r["epd"] for r in md["materials"]])
        self.assertEqual(len(with_epd) + len(without), 12)

    def test_object_that_cannot_be_built_is_an_error_not_a_crash(self):
        with self.assertRaises(convert.ConversionError):
            convert.build_scenario({"project": 5})


if __name__ == "__main__":
    unittest.main()
