"""Round 11 of the independent review: the importer (relative names, the walk's budget, copies of per-floor numbers,
classification of supply-and-fix items, price notes, headings, hidden sheets, evidence with quantities)."""
from __future__ import annotations

import base64
import os
import sys
import tempfile
import time
import unittest

sys.dont_write_bytecode = True
os.environ.setdefault("WLCSTUDIO_OFFLINE", "1")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

from wlcstudio import documents  # noqa: E402
from wlcstudio.importers import tabular  # noqa: E402

try:
    from tests.test_round10_importer import DETAIL, HDR, csv_read, mrow, n, read, reasons, row, t, xlsx  # noqa: E402
except ImportError:
    from test_round10_importer import DETAIL, HDR, csv_read, mrow, n, read, reasons, row, t, xlsx  # noqa: E402

OK = {("m_concrete", "m3"): 150.0, ("m_rebar", "t"): 12.0}


def perfloor_detail(qty_formula=None):
    """明細: 名称|規格|1F|2F|3F|数量|単位 with typed per-floor numbers (a values-only export), or a formula in 数量."""
    head = row(1, t("A1", "名称"), t("B1", "規格"), t("C1", "1F"), t("D1", "2F"), t("E1", "3F"), t("F1", "数量"), t("G1", "単位"))
    out = head
    for r, name, per, unit in ((2, "コンクリート", 40, "m3"), (3, "鉄筋", 5, "t")):
        f = qty_formula(r) if qty_formula else None
        out += row(r, t("A%d" % r, name), t("B%d" % r, "Fc24" if r == 2 else "SD345"), n("C%d" % r, per), n("D%d" % r, per),
                   n("E%d" % r, per), n("F%d" % r, per * 3, f), t("G%d" % r, unit))
    return out


def perfloor_summary():
    """集計: 名称|1F|2F|3F|数量|単位 — the floors copied from 明細, the quantity their sum."""
    head = row(1, t("A1", "名称"), t("B1", "1F"), t("C1", "2F"), t("D1", "3F"), t("E1", "数量"), t("F1", "単位"))
    out = head
    for r, name, per, unit in ((2, "コンクリート", 40, "m3"), (3, "鉄筋", 5, "t")):
        out += row(r, t("A%d" % r, name), n("B%d" % r, per, "明細!C%d" % r), n("C%d" % r, per, "明細!D%d" % r),
                   n("D%d" % r, per, "明細!E%d" % r), n("E%d" % r, per * 3, "SUM(B%d:D%d)" % (r, r)), t("F%d" % r, unit))
    return out


PF = {("m_concrete", "m3"): 120.0, ("m_rebar", "t"): 15.0}


class EleventhRoundImporterTests(unittest.TestCase):
    # --- what a formula reaches
    def test_relative_defined_name_follows_the_using_cell(self):
        summ = HDR + mrow(2, "コンクリート", "Fc24", n("C2", 100, "同行"), "m3")
        # Excel keeps a name's relative references relative to A1: 明細!$C1 and 明細!A1 used in 集計!C2 are 明細!C2
        # (checked with LibreOffice), a copy of the detail row, not added again
        for target in ("明細!$C1", "明細!A1"):
            got, r = read(xlsx([("明細", DETAIL), ("集計", summ)], names=[("同行", target, None)]))
            self.assertEqual(got, OK, target)
            self.assertIn("別のシート（明細）", reasons(r))
        got, _ = read(xlsx([("明細", DETAIL), ("集計", summ)], names=[("同行", "明細!$C$2", None)]))
        self.assertEqual(got, OK)

    def test_let_value_that_is_a_name_is_followed(self):
        for f in ("_xlfn.LET(_xlpm.q,明細数量,SUM(_xlpm.q))", "_xlfn.LET(q,明細数量,SUM(q))",
                  "_xlfn.LAMBDA(_xlpm.x,SUM(_xlpm.x))(明細数量)"):
            summ = HDR + mrow(2, "コンクリート", "全体", n("C2", 150, f), "m3")
            got, _ = read(xlsx([("集計", summ), ("明細", DETAIL)], names=[("明細数量", "明細!$C$2:$C$3", None)]))
            self.assertEqual(got, OK, f)

    def test_names_count_against_the_walk_budget(self):
        rows_n, names_n, refs = 300, 20, 300
        names = [("量%d" % k, ",".join("明細!$Z$%d" % (2000 + k * refs + j) for j in range(refs)), None) for k in range(names_n)]
        f = "SUM(%s)" % ",".join("量%d" % k for k in range(names_n))
        body = HDR + "".join(mrow(r, "コンクリート", "", n("C%d" % r, 1, f), "m3") for r in range(2, rows_n + 2))
        data = xlsx([("明細", body)], names=names)
        t0 = time.perf_counter()
        got, r = read(data)
        self.assertLess(time.perf_counter() - t0, 5.0)
        self.assertEqual(got, {})                       # rows not checked are not added
        self.assertTrue(any("数式のたどる先が多すぎる" in w for w in r["warnings"]))

    # --- a copy of another row's per-floor numbers is a copy
    def test_per_floor_copies_are_copies(self):
        for label, det in (("typed", perfloor_detail()),
                           ("sum", perfloor_detail(lambda r: "SUM(C%d:E%d)" % (r, r))),
                           ("plus", perfloor_detail(lambda r: "C%d+D%d+E%d" % (r, r, r))),
                           ("sumproduct", perfloor_detail(lambda r: "SUMPRODUCT(C%d:E%d)" % (r, r)))):
            got, r = read(xlsx([("明細", det), ("集計", perfloor_summary())]))
            self.assertEqual(got, PF, label)
            self.assertIn("別のシート（明細）", reasons(r), label)
        cols = ["名称", "規格", "1F", "2F", "3F", "数量", "単位"]
        for label, f in (("table sum", "SUM(明細表[@[1F]:[3F]])"), ("table plus", "[@1F]+[@2F]+[@3F]")):
            det = perfloor_detail(lambda r: f)
            got, _ = read(xlsx([("明細", det), ("集計", perfloor_summary())], tables={"明細": [("明細表", "A1:G3", cols)]}))
            self.assertEqual(got, PF, label)

    def test_factors_of_other_rows_are_still_not_copies(self):
        head = HDR.replace("</row>", t("E1", "長さ(m)") + t("F1", "単位質量(kg/m)") + "</row>")
        rows = head + mrow(2, "異形鉄筋", "D13", n("C2", 0.995, "E2*F2/1000"), "t", n("E2", 1000), n("F2", 0.995)) + \
            mrow(3, "異形鉄筋", "D13", n("C3", 1.99, "E3*$F$2/1000"), "t", n("E3", 2000)) + \
            mrow(4, "異形鉄筋", "D13", n("C4", 0.995, "$F$2*1000/1000"), "t")
        got, _ = read(xlsx([("鉄筋", rows)]))
        self.assertAlmostEqual(got[("m_rebar", "t")], 3.98)

    # --- classification
    def test_supply_and_fix_items_are_material(self):
        f, w = documents._field_for, documents._is_work
        for name, want in (("Plain in situ concrete C20; poured on or against earth; foundations", "m_concrete_fdn"),
                           ("Reinforced in situ concrete C30; poured in slabs", "m_concrete"),
                           ("Reinforcement; high yield steel bars to BS 4449; 12 mm; cut, bent and fixed", "m_rebar"),
                           ("Fabric reinforcement A393; laid in slabs", "m_rebar"),
                           ("Structural steelwork S355; fabricated and erected", "m_steel"),
                           ("Plasterboard 12.5 mm; fixed to metal studs", "m_board"),
                           ("Ready mixed concrete, delivered to site", "m_concrete"),
                           ("Insulation laid between joists", "m_insulation")):
            self.assertEqual(f(name), want, name)
            self.assertFalse(w(name), name)
        for name in ("Rebar fixing", "Steel erection", "Concrete pumping", "Placing of concrete in slabs",
                     "Place concrete in slabs", "Hoist and install steelwork", "Welding of steel"):
            self.assertTrue(w(name), name)
        got, r = csv_read("Item,Description,Qty,Unit\n1,Plain in situ concrete C20; poured on or against earth; foundations,45,m3\n"
                          "2,Reinforced in situ concrete C30; poured in slabs,120,m3\n"
                          "3,Reinforcement; high yield steel bars; 12 mm; cut bent and fixed,8.5,t\n"
                          "4,Structural steelwork S355; fabricated and erected,42,t\n5,Placing of concrete in slabs,120,m3\n")
        self.assertEqual(got, {("m_concrete_fdn", "m3"): 45.0, ("m_concrete", "m3"): 120.0, ("m_rebar", "t"): 8.5,
                               ("m_steel", "t"): 42.0})

    def test_method_words_in_a_specification_keep_the_material(self):
        got, _ = csv_read("名称,規格,数量,単位\n土間コンクリート,Fc21 t150 金ごて仕上,45,m3\n普通コンクリート,Fc24 S18 打放し,120,m3\n"
                          "コンクリート,Fc27 金ごて押え共,80,m3\n鋼管杭,試験杭 φ600,12,t\nデッキプレート,t1.2 溶接止め,3,t\n"
                          "押出法ポリスチレンフォーム,3種b t50 床下敷込,400,m2\n鉄骨,SN490B 製作・運搬・建方・残材処分共,50,t\n"
                          "コンクリート打設手間,ポンプ打設,245,m3\n鉄筋,加工組立,20,t\n")
        self.assertEqual(got, {("m_concrete", "m3"): 245.0, ("m_steel", "t"): 65.0, ("m_insulation", "m2"): 400.0})
        for name in ("デッキプレート敷込み", "床コンクリート金ごて仕上", "鉄骨 現場溶接", "鉄筋 ガス圧接"):
            self.assertTrue(documents._is_work(name), name)          # in the NAME they are the work

    def test_price_notes_are_not_removal_or_deduction(self):
        got, r = csv_read("名称,規格,数量,単位\n石膏ボード,t12.5 GB-R,800,m2\n石膏ボード,t9.5 端材処分共,400,m2\n"
                          "普通コンクリート,Fc24 S18,150,m3\n普通コンクリート,Fc27 S18 殻処分費別途,90,m3\n異形鉄筋,SD345 発生材処分別途,10,t\n"
                          "既存コンクリート撤去,,30,m3\nコンクリート殻処分,,30,m3\n")
        self.assertEqual(got, {("m_board", "m2"): 1200.0, ("m_concrete", "m3"): 240.0, ("m_rebar", "t"): 10.0})
        for name in ("In situ concrete C30, including disposal of surplus", "Plasterboard, including removal of offcuts",
                     "Rebar, supply only, disposal of offcuts by others"):
            self.assertFalse(documents._is_demolition(name), name)
        for name in ("既存コンクリート撤去", "Demolition of existing concrete slab", "Disposal of concrete rubble"):
            self.assertTrue(documents._is_demolition(name), name)
        # a removal word only after the material (in its specification) may be a note: left out, but "maybe"
        got, r = csv_read("名称,規格,数量,単位\n普通コンクリート,Fc24,150,m3\n普通コンクリート,殻処分,90,m3\n")
        self.assertEqual(r["evidence"]["m_concrete"]["n_maybe"], 1)

    def test_place_purpose_and_product_rules(self):
        f = documents._field_for
        for name, want in (("防水用シート", "m_membrane"), ("防水用塗膜 ウレタン", "m_membrane"), ("鉄骨上屋", "m_steel"),
                           ("鉄筋上端筋", "m_rebar"), ("鉄筋用スペーサー", None), ("コンクリート用混和剤", None),
                           ("鉄骨用錆止め塗料", None), ("砂利地業（土間コンクリート下）", None), ("断熱サッシ", None),
                           ("Mesh to slab A142", "m_rebar"), ("A142 mesh", "m_rebar"), ("Blockwork 140mm", "m_masonry"),
                           ("Concrete blockwork 200mm", "m_masonry"), ("Block walls 190mm", "m_masonry"), ("Chain link mesh fence", None),
                           ("Waterstop in concrete", None), ("Dowel bars in concrete", None), ("Foundations in concrete C25", "m_concrete_fdn"),
                           ("Walls in brickwork", "m_masonry"), ("Bed and surround in concrete", "m_concrete")):
            self.assertEqual(f(name), want, name)

    # --- headings, evidence
    def test_headings_are_not_rows_left_out(self):
        got, r = csv_read("名称,規格,数量,単位\nコンクリート工事,,,\n普通コンクリート,Fc24,120,m3\n普通コンクリート,Fc27,80,m3\n"
                          "鉄筋工事,,,\n異形鉄筋,SD345,15,t\nコンクリート,,一式,m3\n")
        self.assertEqual(got, {("m_concrete", "m3"): 200.0, ("m_rebar", "t"): 15.0})
        ev = r["evidence"]
        self.assertEqual(ev["m_rebar"]["n_excluded"], 0)
        self.assertEqual(ev["m_concrete"]["n_excluded"], 1)           # 一式: a row without a number (maybe)
        self.assertEqual(ev["m_concrete"]["excluded"][0]["quantity"], "一式")
        self.assertIn("見出し", reasons(r))

    def test_left_out_rows_carry_quantity_and_the_note_matches(self):
        got, r = csv_read("名称,数量,単位\nコンクリート Fc24,100,m3\nコンクリート 計,100,m3\nコンクリート打設,100,m3\n")
        ev = r["evidence"]["m_concrete"]
        self.assertEqual((ev["n_excluded"], ev["n_maybe"]), (2, 1))
        work = next(x for x in ev["excluded"] if "作業" in x["reason"])
        self.assertEqual((work["quantity"], work["unit"], work["maybe"]), (100.0, "m3", True))
        self.assertIn("足さなかった行 2 行。うち 1 行は足すべき行かもしれない", r["proposals"][0].note)
        # a field with no candidate: its left-out rows are counted and the import's summary names it
        got, r = csv_read("名称,規格,数量,単位\n鉄骨,建方,50,t\nコンクリート,Fc24,10,m3\n")
        self.assertEqual(r["left_out"]["m_steel"]["n_maybe"], 1)
        from wlcstudio.server import App
        with tempfile.TemporaryDirectory() as td:
            app = App(td)
            pid = app.projects.create("x", "RC")
            st, out = app.handle("POST", "/api/projects/%d/documents" % pid,
                                 {"name": "b.csv", "data_b64": base64.b64encode("名称,規格,数量,単位\n鉄骨,建方,50,t\n".encode()).decode()})
            self.assertEqual(st, 200)
            self.assertIn("足すべきかもしれない行がある材料：「鉄骨（構造用鋼材）」1 行", out["summary"])
            app.close()

    # --- hidden sheets
    def test_hidden_parts_have_their_own_budget(self):
        old = tabular.MAX_HIDDEN_FORMULA_CHARS, tabular.MAX_HIDDEN_CELLS
        try:
            tabular.MAX_HIDDEN_FORMULA_CHARS = 2000
            calc = "".join(row(r, n("A%d" % r, 1, "ROUND(B%d*1.05+VLOOKUP(B%d,$D$1:$E$100,2,FALSE),2)" % (r, r))) for r in range(1, 400))
            got, r = read(xlsx([("明細", DETAIL), ("計算", calc)], states={"計算": "hidden"}))
            self.assertEqual(got, OK)                   # the workbook is read; the hidden helper is cut
            self.assertTrue(any("途中から読んでいない" in w for w in r["warnings"]))
            # a quantity that reaches the cut sheet cannot be checked: not added
            summ = HDR + mrow(2, "コンクリート", "Fc24", n("C2", 7, "計算!A1"), "m3")
            got, r = read(xlsx([("明細", DETAIL), ("集計", summ), ("計算", calc)], states={"計算": "hidden"}))
            self.assertEqual(got, OK)
            self.assertIn("途中から読んでいない", reasons(r))
            tabular.MAX_HIDDEN_FORMULA_CHARS, tabular.MAX_HIDDEN_CELLS = old[0], 500
            master = "".join(row(r, *[n("%s%d" % (c, r), r) for c in "ABCDEFGHIJ"]) for r in range(1, 200))
            got, r = read(xlsx([("明細", DETAIL), ("単価", master)], states={"単価": "hidden"}))
            self.assertEqual(got, OK)                   # values only: not even parsed
            self.assertFalse(any("途中から読んでいない" in w for w in r["warnings"]))
        finally:
            tabular.MAX_HIDDEN_FORMULA_CHARS, tabular.MAX_HIDDEN_CELLS = old


if __name__ == "__main__":
    unittest.main()
