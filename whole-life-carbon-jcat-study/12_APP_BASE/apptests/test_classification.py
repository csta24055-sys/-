"""The received input classification (five categories) and the ledger built from the originals."""
import csv
import json
import os
import re
import unittest

from lcaapp import binding, convert, enginepath, sample, service
from . import helpers as H

FOLDER = os.path.join(enginepath.STUDY_ROOT, "13_INPUT_CLASSIFICATION")
FIVE = ["building", "construction", "equipment", "operation", "assessment"]
STATES = {"分類済み", "その他", "不明・未分類", "空欄等"}
# what the column "value or setting in the originals" may say: counts and kinds, never a value of the originals
DESCRIPTOR = re.compile(
    r"^(入力セル \d+ 個（値あり \d+、空欄 \d+）(・選択リストあり)?|定数 \d+ 個(・すべて同じ値)?(・連番)?|文字列 \d+ 個(（\d+ 種）)?|"
    r"数式 \d+ セル（式の型 \d+ 種）|見出し・説明の文字列 \d+ 個|選択リスト（(直接指定 \d+ 択|INDIRECT による可変の参照|セル範囲または名前の参照)）|"
    r"入力規則（種類の指定なし）|使用範囲の外を指す範囲指定 \d+ セル分（旧形式の折り返しに由来するとみられる）|#REF! を含む数式 \d+ セル|"
    r"外部ブック参照を含む数式 \d+ セル|コメント \d+ 件（内容は非掲載）|(マクロ起動ボタン|チェックボックス) \d+ 個（リンク先セルの指定 \d+ 個）|"
    r"名前定義（(参照切れ #REF!|参照先あり)(・非表示)?）|vbaProject.bin あり（内容は読んでいない）)$")


def load(name):
    with open(os.path.join(FOLDER, name), encoding="utf-8") as fh:
        return json.load(fh)


def rows_of(name):
    with open(os.path.join(FOLDER, name), encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


class TreeTest(unittest.TestCase):
    def test_received_tree_is_read(self):
        tree = load("JCAT_入力分類ツリー_Claude引継ぎ.json")
        self.assertEqual([c["id"] for c in tree["categories"]], FIVE)
        for cat in tree["categories"]:                                                    # every category has its "other" branch
            self.assertEqual(cat["branches"][-1]["id"], "other")
            self.assertEqual(cat["branches"][-1]["handling"], "fallback")
        summary = binding.read_tree(tree, "v0.1")
        self.assertEqual(summary["n_categories"], 5)
        self.assertEqual([c["n_leaves"] for c in summary["categories"]], [27, 42, 33, 28, 29])
        self.assertEqual(summary["n_leaves"], 159)
        self.assertGreaterEqual(len(summary["others"]), 5)

    def test_complete_tree_keeps_the_received_one(self):
        v01, tree = load("JCAT_入力分類ツリー_Claude引継ぎ.json"), load("JCAT_input_categories_complete.json")
        self.assertEqual([c["id"] for c in tree["categories"]], FIVE + ["review"])
        for old, new in zip(v01["categories"], tree["categories"]):
            ids = [b["id"] for b in new["branches"]]
            for br in old["branches"]:
                self.assertIn("%s.%s" % (old["id"], br["id"]), ids)
            self.assertTrue(ids[-1].endswith(".other"))
            for br in new["branches"]:
                if br["from_v01"]:
                    source = next(b for b in old["branches"] if "%s.%s" % (old["id"], b["id"]) == br["id"])
                    self.assertEqual(br["v01_items"], source["items"])
        self.assertEqual([b["id"] for b in tree["categories"][-1]["branches"]],
                         ["review.unknown", "review.blank", "review.purpose_unknown", "review.broken_ref", "review.duplicate"])
        self.assertFalse(tree["summary"]["values_published"])
        nodes = binding.tree_nodes(tree)
        self.assertEqual(len([n for n in nodes if n.count(".") == 2]), 175)


class LedgerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = load("JCAT_input_categories_complete.json")
        cls.stats = load("JCAT_input_classification_stats.json")
        cls.rows = rows_of("JCAT_input_inventory.csv")
        cls.nodes = binding.tree_nodes(cls.tree)

    def test_every_row_has_one_state_and_a_known_node(self):
        self.assertEqual(len(self.rows), self.stats["summary"]["inventory_rows"])
        self.assertEqual(len({r["台帳ID"] for r in self.rows}), len(self.rows))
        for r in self.rows:
            self.assertIn(r["状態"], STATES)
            self.assertIn(r["分類ID"], self.nodes)
        counts = {s: sum(1 for r in self.rows if r["状態"] == s) for s in STATES}
        self.assertEqual(counts, {s: self.stats["summary"]["rows_by_status"].get(s, 0) for s in STATES})

    def test_cell_totals_agree_with_the_scan(self):
        cells = sum(int(r["セル数"]) for r in self.rows)
        self.assertEqual(cells, sum(self.stats["summary"]["cells_by_status"].values()))
        scan, role = self.stats["scan"], self.stats["role_cells"]
        self.assertEqual(role["F"], scan["formulas"])                                     # every formula cell is in the ledger
        self.assertEqual(cells, role["I"] + role["C"] + role["TD"] + role["L"] + role["F"])
        self.assertEqual(self.stats["role_rows"]["DV"], scan["validations"])
        self.assertEqual(self.stats["role_rows"]["NM"], scan["names"][0])
        self.assertEqual(scan["sheets"][0], 198)
        self.assertEqual(scan["formulas"], 3818483)                                       # the count recorded on 2026-11-11
        blanks = sum(int(r["うち空欄"]) for r in self.rows)
        self.assertEqual(blanks, self.stats["summary"]["editable_blank_cells"])

    def test_no_value_of_the_originals_is_in_the_public_files(self):
        for r in self.rows:
            self.assertRegex(r["原版での値または設定内容"], DESCRIPTOR, r["台帳ID"])
        data_tables = [r for r in self.rows if "データ表のため見出しは非掲載" in r["不明点・注意事項"]]
        self.assertGreater(len(data_tables), 5000)
        self.assertTrue(all(r["原版の見出し"] == "" for r in data_tables))                  # headings of data tables are not written
        text = json.dumps(self.tree, ensure_ascii=False)
        self.assertNotIn("sample", text)
        self.assertNotIn('"v"', text)

    def test_unclassified_file_is_the_rest(self):
        rest = rows_of("JCAT_input_unclassified.csv")
        expect = [r["台帳ID"] for r in self.rows if r["状態"] != "分類済み" or r["要確認の種類"]]
        self.assertEqual([r["台帳ID"] for r in rest], expect)
        self.assertEqual(len(rest), self.stats["unclassified_rows"])
        kinds = {r["要確認の種類"] for r in rest}
        self.assertTrue({"参照不明・参照切れ", "用途不明"} <= kinds)

    def test_duplicates_point_to_existing_rows(self):
        ids = {r["台帳ID"] for r in self.rows}
        dups = [r for r in self.rows if r["統合先（重複）"]]
        self.assertEqual(len(dups), self.stats["summary"]["duplicate_rows"])
        self.assertTrue(all(r["統合先（重複）"] in ids and r["統合先（重複）"] != r["台帳ID"] for r in dups))

    def test_tree_counts_match_the_ledger(self):
        per = {}
        for r in self.rows:
            per[r["分類ID"]] = per.get(r["分類ID"], 0) + 1
        for cat in self.tree["categories"]:
            for br in cat["branches"]:
                self.assertEqual(br["inventory"]["n_rows"], per.get(br["id"], 0), br["id"])
                for d in br["details"]:
                    self.assertEqual(d["inventory"]["n_rows"], per.get(d["id"], 0), d["id"])
        entries = [e for c in self.tree["categories"] for b in c["branches"] for n in [b] + b["details"]
                   for e in n["inventory"].get("input_entries", [])]
        self.assertEqual(len(entries), self.stats["input_entries"])
        self.assertTrue(all(set(e) == {"id", "row_group", "label", "data_kind", "data_type", "unit", "requirement", "workbooks", "n_cells"}
                            for e in entries))


class TreeBindingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = load("JCAT_input_categories_complete.json")
        cls.bind = binding.for_tree(cls.tree)

    def test_stored_binding_is_the_default_and_covers_the_engine(self):
        stored = binding.default()
        self.assertFalse(stored.provisional)
        self.assertEqual(stored.entries, self.bind.entries)                               # the file equals what the rules give
        self.assertEqual(stored.coverage()["unbound"], [])
        nodes = binding.tree_nodes(self.tree)
        self.assertTrue(all(e["node"] in nodes and e["category"] in FIVE for e in stored.entries.values()))
        self.assertEqual(sorted({e["category"] for e in stored.entries.values()}), sorted(FIVE))
        self.assertEqual(list(stored.categories), FIVE)
        cover = binding.tree_coverage_by_node(self.tree, stored)
        self.assertEqual(cover["details"], 175)
        self.assertEqual(len(cover["with_engine_input"]) + len(cover["without_engine_input"]), 175)
        self.assertGreater(len(cover["with_engine_input"]), 60)

    def test_input_in_five_categories_gives_the_same_engine_input_and_results(self):
        for kw in (dict(seed=4201), dict(seed=77, structure="W", use="residential", dirty=True)):
            _, ref, md = H.building(rows=None, **kw)
            doc = sample.document_from_model(md, self.bind, "5 大分類の試験", "fictional", ref)
            self.assertEqual(sorted(doc["categories"]), sorted(FIVE))
            data = H.to_common(doc, ref, self.bind)
            self.assertEqual((data["stats"]["invalid"], data["stats"]["unsupported"], data["stats"]["unbound"]), (0, 0, 0))
            model, report = convert.to_model(data, ref, md["meta"]["scenario_id"])
            for part in md:
                if part != "meta":
                    self.assertEqual(model[part], md[part], (kw, part))
            period = md["boundary"]["study_period"]
            app = H.through_json(enginepath.unified().System(convert.build_scenario(model)).at(period))
            self.assertEqual(app, H.direct_results(md, period))

    def test_whole_chain_with_the_real_categories_and_other_entries(self):
        _, ref, md = H.building()
        doc = sample.document_from_model(md, self.bind, "5 大分類・その他つき", "fictional", ref)
        for cat in FIVE:                                                                  # the four fields of the "other" branch of the tree
            doc["categories"][cat]["others"] = [{"label": "元の項目名 " + cat, "value": "入力値または説明", "unit": "単位", "note": "仮分類・メモ"}]
        with H.TempStore() as t:
            t.service = service.Service(t.store, self.bind)
            t.service.register_refset(ref)
            out = t.service.import_document(H.through_json(doc))
            run = t.service.calculate(out["project_id"], 60)
            self.assertEqual(run["status"], "ok")
            self.assertEqual(t.store.get_run(run["id"], with_results=True)["results"], H.direct_results(md, 60.0))
            self.assertEqual(run["versions"]["binding"]["classification"]["id"], "jcat-input-tree")
            self.assertFalse(run["versions"]["binding"]["provisional"])
            others = t.store.list_others(out["input_version_id"])
            self.assertEqual([o["category"] for o in others], FIVE)
            self.assertEqual((others[0]["label"], others[0]["value"], others[0]["unit"], others[0]["note"]),
                             ("元の項目名 building", "入力値または説明", "単位", "仮分類・メモ"))


if __name__ == "__main__":
    unittest.main()
