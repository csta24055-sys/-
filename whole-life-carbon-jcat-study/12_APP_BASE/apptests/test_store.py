"""System 5: storage and management (SQLite)."""
import copy
import json
import os
import sqlite3
import tempfile
import unittest

from lcaapp import refdata, store
from . import helpers as H


class StoreTest(unittest.TestCase):
    def test_project_input_versions_and_reload(self):
        doc, ref, md = H.building()
        with H.TempStore() as t:
            t.service.register_refset(ref)
            first = t.service.import_document(H.through_json(doc), name="建物 A")
            doc2 = copy.deepcopy(doc)
            H.set_item(doc2, "project", "project.gross_floor_area", 9999.0)
            second = t.service.import_document(H.through_json(doc2), project_id=first["project_id"])
            self.assertEqual(second["project_id"], first["project_id"])
            t.reopen()                                                                  # a new connection to the same file
            versions = t.store.list_inputs(first["project_id"])
            self.assertEqual([v["version_no"] for v in versions], [1, 2])
            v1, v2 = (t.store.get_input(v["id"]) for v in versions)
            self.assertEqual(v1["document"], H.through_json(doc))                       # an update never overwrites
            self.assertEqual(v2["document"], H.through_json(doc2))
            self.assertEqual(H.cell_at(v2["common"], "project", "gross_floor_area")["v"], 9999.0)
            self.assertNotEqual(v1["sha256"], v2["sha256"])
            project = t.store.get_project(first["project_id"])
            self.assertEqual((project["name"], project["data_kind"]), ("建物 A", "fictional"))
            self.assertEqual(t.store.list_projects()[0]["n_inputs"], 2)

    def test_other_items_are_stored(self):
        doc, ref, _ = H.building()
        doc["categories"]["materials"]["others"] = [{"label": "再生材の特記", "value": 3.2, "unit": "t", "note": "数量未確定"},
                                                    "分類できない記述"]
        doc["categories"]["operation"]["others"] = [{"label": "蓄電池", "value": {"容量": 100}, "unit": "kWh"}]
        with H.TempStore() as t:
            t.service.register_refset(ref)
            out = t.service.import_document(H.through_json(doc))
            t.reopen()
            others = t.store.list_others(out["input_version_id"])
            self.assertEqual([(o["category"], o["label"]) for o in others],
                             [("materials", "再生材の特記"), ("materials", ""), ("operation", "蓄電池")])
            self.assertEqual((others[0]["value"], others[0]["unit"], others[0]["note"]), (3.2, "t", "数量未確定"))
            self.assertEqual(others[1]["raw"], "分類できない記述")
            self.assertEqual(others[2]["value"], {"容量": 100})

    def test_reference_sets(self):
        _, ref, _ = H.building()
        with H.TempStore() as t:
            out = t.service.register_refset(ref)
            self.assertEqual(t.service.register_refset(copy.deepcopy(ref))["reference_set_id"], out["reference_set_id"])
            t.reopen()
            back = t.store.get_refset(out["reference_set_id"])
            checked, _ = refdata.check(ref)
            self.assertEqual(back["data"], checked["data"])                             # item by item, same content
            self.assertEqual(list(back["data"]["gwp"]), back["data"]["gases"])          # the order of the gas vector
            self.assertEqual(back["sha256"], checked["sha256"])
            self.assertEqual(t.store.list_refsets()[0]["n_factors"], len(ref["data"]["factors"]))
            changed = copy.deepcopy(ref)
            next(iter(changed["data"]["factors"].values()))["value"] += 1.0
            with self.assertRaises(store.StoreError):                                    # same name and version, other content
                t.service.register_refset(changed)
            changed["version"] = "another"
            self.assertNotEqual(t.service.register_refset(changed)["reference_set_id"], out["reference_set_id"])

    def test_reference_set_guards(self):
        _, ref, _ = H.building()
        untagged = copy.deepcopy(ref)
        next(iter(untagged["data"]["factors"].values()))["source_tag"] = "COPIED_FROM_SOMEWHERE"
        with self.assertRaises(refdata.RefsetError):                                     # not fictional: refused as fictional
            refdata.check(untagged)
        licensed = dict(copy.deepcopy(untagged), data_kind="licensed", licence_status="", source_note="")
        with self.assertRaises(refdata.RefsetError):                                     # no declaration, no source
            refdata.check(licensed)
        licensed.update(licence_status="PERMITTED_PUBLIC", source_note="試験用：利用者が許諾を確認したと宣言したデータ")
        checked, _ = refdata.check(licensed)
        self.assertEqual(checked["data_kind"], "licensed")
        for bad in (None, {}, dict(ref, format="x"), dict(ref, data_kind="jcat"), dict(ref, name=""), dict(ref, data=None)):
            with self.assertRaises(refdata.RefsetError):
                refdata.check(bad)
        broken = copy.deepcopy(ref)
        fid = next(iter(broken["data"]["factors"]))
        broken["data"]["factors"][fid]["value"] = None
        broken["data"]["unit_conversions"].append({"from_unit": "x"})
        checked, left_out = refdata.check(broken)
        self.assertNotIn(fid, checked["data"]["factors"])                                # left out and listed, not repaired
        self.assertEqual(sorted(x["kind"] for x in left_out), ["factor", "unit_conversion"])

    def test_conditions_results_and_versions_are_stored(self):
        doc, ref, md = H.building()
        with H.TempStore() as t:
            t.service.register_refset(ref)
            out = t.service.import_document(H.through_json(doc))
            run = t.service.calculate(out["project_id"], 45.5, name="45.5 年")
            self.assertEqual(run["status"], "ok")
            path = t.path
            t.reopen()
            back = t.store.get_run(run["id"], with_results=True)
            self.assertEqual(back["results"], H.direct_results(md, 45.5))                # exactly what the engine returned
            self.assertEqual(back["view"], run["view"])
            condition = t.store.get_condition(back["condition_id"])
            self.assertEqual((condition["study_period"], condition["name"]), (45.5, "45.5 年"))
            self.assertEqual(condition["reference_set_id"], 1)
            v = back["versions"]
            self.assertEqual(v["steps"], {"P1": 1528, "TIME": 95, "AGG": 166})
            self.assertEqual(len(v["engine_source_sha256"]), 64)
            self.assertEqual(v["reference_set"]["name"], ref["name"])
            self.assertEqual(v["input_sha256"], t.store.get_input(out["input_version_id"], with_data=False)["sha256"])
            self.assertTrue(v["binding"]["provisional"])
            self.assertEqual([r["id"] for r in t.store.list_runs(out["project_id"])], [run["id"]])
            self.assertGreater(os.path.getsize(path), 10000)

    def test_missing_things_and_wrong_file_version(self):
        with H.TempStore() as t:
            for call in (lambda: t.store.get_project(99), lambda: t.store.get_input(99), lambda: t.store.get_run(99),
                         lambda: t.store.get_refset(99), lambda: t.store.get_condition(99),
                         lambda: t.service.calculate(99, 60)):
                with self.assertRaises(store.StoreError):
                    call()
            pid = t.store.create_project("空の建物")
            with self.assertRaises(store.StoreError):                                    # no input yet
                t.service.calculate(pid, 60)
            path = t.path
            t.store.close()
            db = sqlite3.connect(path)
            db.execute("UPDATE app_meta SET value = '999' WHERE key = 'schema_version'")
            db.commit()
            db.close()
            with self.assertRaises(store.StoreError):
                store.Store(path)
            db = sqlite3.connect(path)
            db.execute("UPDATE app_meta SET value = '1' WHERE key = 'schema_version'")
            db.commit()
            db.close()
            t.store = store.Store(path)

    def test_non_finite_numbers_never_reach_the_file(self):
        safe, n = store.json_safe({"a": float("nan"), "b": [1.0, float("inf")], 3: {"c": -float("inf")}})
        self.assertEqual((safe, n), ({"a": None, "b": [1.0, None], "3": {"c": None}}, 3))
        with self.assertRaises(ValueError):
            store.pack({"x": float("nan")})
        doc, ref, _ = H.building()
        H.set_item(doc, "project", "project.gross_floor_area", float("nan"))
        with H.TempStore() as t:
            t.service.register_refset(ref)
            out = t.service.import_document(doc)                                         # stored, reported as unusable
            version = t.store.get_input(out["input_version_id"])
            self.assertEqual(H.item(version["document"], "project", "project.gross_floor_area"), "NaN")
            self.assertEqual(H.cell_at(version["common"], "project", "gross_floor_area")["s"], "invalid")


if __name__ == "__main__":
    unittest.main()
