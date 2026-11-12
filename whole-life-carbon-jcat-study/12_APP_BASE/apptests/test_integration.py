"""The three systems together: input -> conversion -> existing engine -> storage -> display -> reload."""
import copy
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request

from lcaapp import enginepath, render, service, store, web
from . import helpers as H

ENV = dict(os.environ, PYTHONPATH=enginepath.APP_ROOT, PYTHONDONTWRITEBYTECODE="1")


def cli(db, *args):
    """One run of the command line in a fresh Python process."""
    done = subprocess.run([sys.executable, "-B", "-m", "lcaapp", "--db", db, *map(str, args)], env=ENV,
                          capture_output=True, text=True, timeout=300)
    if done.returncode != 0:
        raise AssertionError("command %r failed:\n%s\n%s" % (args, done.stdout, done.stderr))
    return done.stdout


class ChainTest(unittest.TestCase):
    def test_whole_chain_in_one_process(self):
        doc, ref, md = H.building(rows=None)
        text = json.dumps(doc, ensure_ascii=False)                                       # 1. the input arrives as JSON text
        with H.TempStore() as t:
            t.service.register_refset(json.loads(json.dumps(ref)))
            imported = t.service.import_document(web.parse_json(text))                   # 2. common format, stored
            self.assertEqual(imported["summary"]["stats"]["invalid"], 0)
            run = t.service.calculate(imported["project_id"], 62.5)                      # 3. existing engine
            self.assertEqual(run["status"], "ok")
            direct = H.direct_results(md, 62.5)
            stored = t.store.get_run(run["id"], with_results=True)["results"]            # 5. stored
            self.assertEqual(stored, direct)                                             # the engine's own numbers, unchanged
            self.assertEqual(len(stored), 70)
            tables = run["report"]["engine_tables"]                                      # the column tables the engine was given
            self.assertEqual(tables["rows"]["materials"], len(md["materials"]))
            self.assertEqual(tables["rows"]["equipment"], len(md["equipment"]))
            self.assertEqual(tables["rows"]["factors"], len(md["factors"]))
            self.assertEqual(tables["rows"]["operation.grid.table"], 130)
            self.assertEqual(tables["n_knot_spectra"], 23)
            self.assertGreater(tables["n_columns"], 2000)
            html = render.run_page(t.service.run_page(run["id"]))                        # 4. shown
            self.assertIn(render.fmt(direct["SUM-03"]["value"]), html)
            t.reopen()                                                                   # 6. read again from the file
            self.assertEqual(render.run_page(t.service.run_page(run["id"])), html)
            self.assertEqual(t.store.get_run(run["id"], with_results=True)["results"], direct)

    def test_preparation_is_reused(self):
        doc, ref, md = H.building()
        with H.TempStore() as t:
            t.service.register_refset(ref)
            out = t.service.import_document(H.through_json(doc))
            pid = out["project_id"]
            for period in (60, 30.0, "45.5", 100):
                run = t.service.calculate(pid, period)
                self.assertEqual(run["status"], "ok")
                self.assertEqual(t.store.get_run(run["id"], with_results=True)["results"], H.direct_results(md, float(period)))
            self.assertEqual(t.service.prepared, 1)                                      # converted and prepared once
            doc2 = copy.deepcopy(doc)
            H.set_item(doc2, "project", "project.gross_floor_area", 5000.0)
            t.service.import_document(H.through_json(doc2), project_id=pid)
            run2 = t.service.calculate(pid, 60)                                          # the new version is used by default
            self.assertEqual(t.service.prepared, 2)
            self.assertNotEqual(run2["view"]["indicators"][4]["value"], run["view"]["indicators"][4]["value"])
            old = t.service.calculate(pid, 60, input_version_id=out["input_version_id"])  # the old version still computes
            self.assertEqual(t.store.get_run(old["id"], with_results=True)["results"], H.direct_results(md, 60.0))

    def test_restart_keeps_inputs_conditions_and_results(self):
        doc, ref, md = H.building(rows=None)
        with tempfile.TemporaryDirectory() as folder:
            db = os.path.join(folder, "app.sqlite3")
            files = {}
            for name, obj in (("input.json", doc), ("refset.json", ref)):
                files[name] = os.path.join(folder, name)
                with open(files[name], "w", encoding="utf-8") as fh:
                    json.dump(obj, fh, ensure_ascii=False)
            cli(db, "refset", "add", files["refset.json"])                               # each call is a new process
            self.assertIn("建物プロジェクト 1、入力の版 1", cli(db, "import", files["input.json"], "--name", "再起動の試験"))
            out = cli(db, "calc", 1, "--period", "62.5")
            direct = H.direct_results(md, 62.5)
            self.assertIn("計算結果 1：ok", out)
            self.assertIn(render.fmt(direct["SUM-03"]["value"]), out)
            first = cli(db, "show", 1, "--html", os.path.join(folder, "a.html"), "--json", os.path.join(folder, "a.json"))
            again = cli(db, "show", 1, "--html", os.path.join(folder, "b.html"))         # after another restart
            self.assertEqual(first.splitlines()[:8], again.splitlines()[:8])
            with open(os.path.join(folder, "a.html"), encoding="utf-8") as a, open(os.path.join(folder, "b.html"), encoding="utf-8") as b:
                page = a.read()
                self.assertEqual(page, b.read())                                         # the same page, read from the file
            self.assertIn(render.fmt(direct["SUM-03"]["value"]), page)
            with open(os.path.join(folder, "a.json"), encoding="utf-8") as fh:
                self.assertEqual(json.load(fh), direct)
            self.assertIn("再起動の試験", cli(db, "projects"))
            self.assertIn("T=62.5", cli(db, "runs", 1))
            cli(db, "calc", 1, "--period", "62.5")                                        # computing again after a restart
            cli(db, "show", 2, "--json", os.path.join(folder, "c.json"))
            with open(os.path.join(folder, "c.json"), encoding="utf-8") as fh:
                self.assertEqual(json.load(fh), direct)
            check = store.Store(db)                                                       # and from this process
            try:
                self.assertEqual(len(check.list_runs(1)), 2)
                self.assertEqual(check.get_input(1)["document"], H.through_json(doc))
                self.assertEqual(check.get_condition(1)["study_period"], 62.5)
            finally:
                check.close()

    def test_command_line_demo_and_sample_files(self):
        with tempfile.TemporaryDirectory() as folder:
            db = os.path.join(folder, "app.sqlite3")
            cli(db, "demo", "--rows", 6)
            self.assertIn("計算結果 1：ok", cli(db, "calc", 1, "--period", 50))
            self.assertIn("blocked", cli(db, "calc", 1, "--period", "ten"))
            cli(db, "sample", "--out", folder, "--rows", 4)
            with open(os.path.join(folder, "input_fictional.json"), encoding="utf-8") as fh:
                self.assertEqual(json.load(fh)["data_kind"], "fictional")
            self.assertIn('"unbound": []', cli(db, "binding").replace("\n", ""))
            tree = os.path.join(folder, "tree.json")
            with open(tree, "w", encoding="utf-8") as fh:
                json.dump([{"name": "建物", "children": [{"name": "面積"}, {"name": "その他"}]}], fh, ensure_ascii=False)
            self.assertIn('"n_leaves": 2', cli(db, "tree", tree))

    def test_baseline_comparison_uses_engine_results(self):
        doc, ref, md = H.building()
        base_doc = copy.deepcopy(doc)
        row = base_doc["categories"]["materials"]["tables"]["materials"][0]
        row["quantity"] = row["quantity"] * 3.0
        with H.TempStore() as t:
            t.service.register_refset(ref)
            a = t.service.import_document(H.through_json(doc), name="改善案")
            b = t.service.import_document(H.through_json(base_doc), name="基準案")
            own = t.service.calculate(b["project_id"], 60)
            run = t.service.calculate(a["project_id"], 60, baseline_input_version_id=b["input_version_id"])
            comparison = run["view"]["comparison"]
            self.assertEqual(comparison["status"], "COMPARED")
            self.assertEqual(comparison["baseline"], own["view"]["indicators"][0]["value"])
            self.assertAlmostEqual(comparison["delta"], run["view"]["indicators"][0]["value"] - comparison["baseline"],
                                   delta=1e-6 * abs(comparison["baseline"]))
            html = render.run_page(t.service.run_page(run["id"]))
            self.assertIn(render.fmt(comparison["baseline"]), html)
            self.assertIn("SUM-08.delta", html)
            plain = t.service.calculate(a["project_id"], 60)
            self.assertEqual(plain["view"]["comparison"]["status"], "NO_BASELINE")
            self.assertEqual(plain["view"]["indicators"][0]["value"], run["view"]["indicators"][0]["value"])
            gone = t.service.calculate(a["project_id"], 60, baseline_input_version_id=12345)   # unknown baseline: ignored
            self.assertEqual(gone["view"]["comparison"]["status"], "NO_BASELINE")

    def test_reference_data_must_be_known(self):
        doc, ref, _ = H.building()
        with H.TempStore() as t:
            out = t.service.import_document(H.through_json(doc))                          # nothing registered yet
            run = t.service.calculate(out["project_id"], 60)
            self.assertEqual(run["status"], "blocked")
            self.assertIn("参照データ", run["message"])
            t.service.register_refset(ref)
            self.assertEqual(t.service.calculate(out["project_id"], 60)["status"], "ok")
            self.assertEqual(t.service.calculate(out["project_id"], 60, reference_set_id=77)["status"], "blocked")


class RobustnessTest(unittest.TestCase):
    """Missing values, unusable values and "other" entries must never end the program."""

    BAD = ("text where a value belongs", -1, 1e308, [], {"k": None}, True, "NaN", {"value": 5, "unit": "no-such-unit"})

    def _places(self, doc):
        """(description, setter) for every item and for every column of the first row of every table."""
        places = []
        for cat, body in doc["categories"].items():
            for item_id in body["items"]:
                places.append(("%s/%s" % (cat, item_id), lambda d, v, c=cat, i=item_id: d["categories"][c]["items"].__setitem__(i, v)))
            for table_id, rows in body["tables"].items():
                places.append(("%s/%s (whole table)" % (cat, table_id),
                               lambda d, v, c=cat, t=table_id: d["categories"][c]["tables"].__setitem__(t, v)))
                if not rows:
                    continue
                for column in rows[0]:
                    if column == "@tables":
                        for nested_id, nested in rows[0]["@tables"].items():
                            for sub in (nested[0] if nested else {}):
                                places.append(("%s/%s[0]/%s[0]/%s" % (cat, table_id, nested_id, sub),
                                               lambda d, v, c=cat, t=table_id, n=nested_id, s=sub:
                                               d["categories"][c]["tables"][t][0]["@tables"][n][0].__setitem__(s, v)))
                    else:
                        places.append(("%s/%s[0]/%s" % (cat, table_id, column),
                                       lambda d, v, c=cat, t=table_id, k=column: d["categories"][c]["tables"][t][0].__setitem__(k, v)))
        return places

    def test_no_single_missing_or_bad_value_crashes(self):
        doc, ref, _ = H.building(rows=6)
        places = self._places(doc)
        self.assertGreater(len(places), 200)
        counts = {"missing": {"ok": 0, "blocked": 0, "failed": 0}, "absent": {"ok": 0, "blocked": 0, "failed": 0},
                  "bad": {"ok": 0, "blocked": 0, "failed": 0}}
        not_ok = {}
        with H.TempStore() as t:
            t.service.register_refset(ref)
            pid = t.store.create_project("頑健性の試験", "fictional")
            for n, (where, put) in enumerate(places):
                for kind, value in (("missing", None), ("absent", {"state": "absent"}), ("bad", self.BAD[n % len(self.BAD)])):
                    changed = copy.deepcopy(doc)
                    put(changed, value)
                    out = t.service.import_document(changed, project_id=pid)             # must not raise
                    run = t.service.calculate(pid, 60, input_version_id=out["input_version_id"])
                    self.assertIn(run["status"], ("ok", "blocked", "failed"), where)
                    counts[kind][run["status"]] += 1
                    if run["status"] == "ok":
                        self.assertEqual(len(run["view"]["indicators"]), 7)
                    else:
                        self.assertTrue(run["message"], where)
                        self.assertIsNone(run["view"])
                        not_ok.setdefault(where, {})[kind] = "%s: %s" % (run["status"], run["message"][:120])
                    render.run_page(t.service.run_page(run["id"]))                       # the page can always be made
        total = sum(sum(c.values()) for c in counts.values())
        self.assertEqual(total, 3 * len(places))
        report = os.environ.get("LCAAPP_TEST_REPORT")
        if report:
            with open(report, "w", encoding="utf-8") as fh:
                json.dump({"places": len(places), "runs": total, "counts": counts, "not_ok": not_ok}, fh, ensure_ascii=False, indent=1)

    def test_garbage_documents(self):
        _, ref, _ = H.building()
        with H.TempStore() as t:
            t.service.register_refset(ref)
            for doc in ({}, {"categories": None}, {"categories": []}, {"categories": {"x": 1}}, {"format": 7, "data_kind": [], "title": {}},
                        {"categories": {"project": {"items": {"project.gross_floor_area": {"value": {"value": 1}}}}}},
                        {"categories": {"materials": {"tables": {"materials": [None, 1, "a", [], {"@tables": 5, "@state": "?"}]}}}},
                        {"reference_set": "not an object", "conditions": 5, "categories": {"a": {"others": {"label": 1}}}}):
                out = t.service.import_document(doc)
                run = t.service.calculate(out["project_id"], 60)
                self.assertEqual(run["status"], "blocked", doc)                           # required values are missing
                self.assertIn("必須項目", run["message"])
                render.run_page(t.service.run_page(run["id"]))
            for doc in (None, 5, "text", [1, 2]):
                with self.assertRaises(H.common.InputError):
                    t.service.import_document(doc)
            self.assertEqual(len(t.store.list_projects()), 8)

    def test_extreme_numbers_are_stored_as_not_computed(self):
        doc, ref, _ = H.building()
        rows = doc["categories"]["materials"]["tables"]["materials"]
        rows[0]["quantity"], rows[1]["quantity"] = 1e308, -1e308
        with H.TempStore() as t:
            t.service.register_refset(ref)
            out = t.service.import_document(doc)
            for _ in range(2):                                                           # the second run reuses the preparation
                run = t.service.calculate(out["project_id"], 60)
                self.assertEqual(run["status"], "ok")
                whole = run["view"]["indicators"][0]
                self.assertEqual((whole["value"], whole["status"]), (None, "not_computed"))   # no made-up figure
                texts = " ".join(n["text"] for n in run["view"]["notes"])
                self.assertIn("有限でない値", texts)
                self.assertIn("数値の警告", texts)
                json.dumps(t.store.get_run(run["id"], with_results=True)["results"], allow_nan=False)
                self.assertIn("未計算", render.run_page(t.service.run_page(run["id"])))

    def test_other_entries_do_not_change_results(self):
        doc, ref, md = H.building()
        with_others = copy.deepcopy(doc)
        for cat, body in with_others["categories"].items():
            body["others"] = [{"label": "その他 " + cat, "value": 123456.0, "unit": "kgCO2e", "note": "計算に入れてほしい数値"},
                              {"label": "数量不明の資材", "value": None}, "メモだけ"]
        with H.TempStore() as t:
            t.service.register_refset(ref)
            out = t.service.import_document(H.through_json(with_others))
            run = t.service.calculate(out["project_id"], 60)
            self.assertEqual(run["status"], "ok")
            self.assertEqual(t.store.get_run(run["id"], with_results=True)["results"], H.direct_results(md, 60.0))
            n = 3 * len(with_others["categories"])
            self.assertEqual(len(t.store.list_others(out["input_version_id"])), n)
            self.assertTrue(any("「その他」の入力 %d 件" % n in note["text"] for note in run["view"]["notes"]))
            html = render.run_page(t.service.run_page(run["id"]))
            self.assertIn("その他 materials", html)
            self.assertIn("計算に入れてほしい数値", html)


class WebTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        ready: queue.Queue = queue.Queue()

        def run():                                                                       # the storage connection lives in this thread
            st = store.Store(os.path.join(cls.folder.name, "web.sqlite3"))
            server = web.serve(service.Service(st), "127.0.0.1", 0)
            ready.put(server)
            server.serve_forever()
            server.server_close()
            st.close()

        cls.thread = threading.Thread(target=run, daemon=True)
        cls.thread.start()
        cls.server = ready.get(timeout=30)
        cls.base = "http://127.0.0.1:%d" % cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=30)
        cls.folder.cleanup()

    def get(self, path):
        try:
            with urllib.request.urlopen(self.base + path, timeout=120) as r:
                return r.status, r.geturl(), r.read().decode("utf-8")
        except urllib.error.HTTPError as err:
            return err.code, path, err.read().decode("utf-8")

    def post(self, path, form=None, headers=None, body=None):
        data = body if body is not None else urllib.parse.urlencode(form or {}).encode("utf-8")
        request = urllib.request.Request(self.base + path, data=data, headers=headers or {}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=300) as r:
                return r.status, r.geturl(), r.read().decode("utf-8")
        except urllib.error.HTTPError as err:
            return err.code, path, err.read().decode("utf-8")

    def test_screen_from_import_to_result(self):
        status, _, html = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("建物プロジェクト一覧", html)
        doc, ref, md = H.building(seed=4201, rows=None)
        status, url, html = self.post("/demo", {"seed": "4201"})                          # fictional building + reference data
        self.assertEqual(status, 200)
        self.assertRegex(url, r"/project/\d+$")
        project = url.rsplit("/", 1)[1]
        self.assertIn("計算する", html)
        status, url, html = self.post("/project/%s/calculate" % project, {"study_period": "60", "reference_set_id": "",
                                                                          "baseline_input_version_id": ""})
        self.assertEqual(status, 200)
        self.assertRegex(url, r"/run/\d+$")
        run = url.rsplit("/", 1)[1]
        direct = H.direct_results(md, 60.0)
        self.assertIn(render.fmt(direct["SUM-03"]["value"]), html)                        # the engine's figure is on the screen
        self.assertIn(render.fmt(direct["SUM-04"]["value"]), html)
        self.assertEqual(html.count("<svg"), 3)
        status, _, body = self.get("/run/%s/results.json" % run)
        self.assertEqual(json.loads(body)["results"], direct)
        status, url, html = self.post("/project/%s/calculate" % project, {"study_period": "abc"})   # a bad condition is a stored outcome
        self.assertEqual(status, 200)
        self.assertIn("計算していない", html)
        self.assertIn("すべて未計算", html)
        changed = copy.deepcopy(doc)
        changed["categories"]["operation"]["others"] = [{"label": "画面から足したその他", "value": 1}]
        status, url, html = self.post("/project/%s/import" % project, {"document": json.dumps(changed, ensure_ascii=False)})
        self.assertEqual(status, 200)
        self.assertIn("入力（第 2 版）", html)
        self.assertIn("画面から足したその他", html)
        status, url, html = self.post("/import", body=json.dumps(doc).encode("utf-8"), headers={"Content-Type": "application/json"})
        self.assertRegex(url, r"/project/\d+$")
        other = url.rsplit("/", 1)[1]
        self.assertNotEqual(other, project)
        status, _, html = self.get("/")
        self.assertIn("/project/%s" % other, html)
        self.assertIn("fictional-demo", html)

    def test_bad_requests_do_not_stop_the_server(self):
        for path, form in (("/import", {"document": "{not json"}), ("/import", {"document": "[1, 2]"}), ("/import", {"document": ""}),
                           ("/demo", {"seed": "x"})):
            status, _, html = self.post(path, form)
            self.assertEqual(status, 400, (path, form))
            self.assertIn("msg", html)
        for path in ("/run/999", "/project/999", "/nope", "/run/1/other", "/project/abc"):
            self.assertEqual(self.get(path)[0], 404, path)
        self.assertEqual(self.post("/project/999/calculate", {"study_period": "60"})[0], 404)
        self.assertEqual(self.post("/project/999/import", {"document": "{}"})[0], 404)
        self.assertEqual(self.post("/import", {"document": "{}"}, headers={"Origin": "http://evil.example"})[0], 403)
        self.assertEqual(self.post("/import", {"document": '{"title": "NaN の入った入力", "categories": {"project": {"items": '
                                               '{"project.gross_floor_area": NaN}}}}'})[0], 200)
        self.assertEqual(self.get("/")[0], 200)                                            # still serving


if __name__ == "__main__":
    unittest.main()
