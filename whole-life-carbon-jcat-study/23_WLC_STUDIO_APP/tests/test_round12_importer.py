"""Round 12 of the independent review: the importer (copies through masks, IFS / SWITCH, lookups and LET; factor
headers as whole words; long sheet names; a LET shared by many cells; removal rows with price notes; labour-only English
rows; method words when the name names no material; 用; "in"; concrete blocks; copies on the card; maybe rows first)."""
from __future__ import annotations

import os
import sys
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
    from tests.test_round11_importer import PF, perfloor_detail  # noqa: E402
except ImportError:
    from test_round10_importer import DETAIL, HDR, csv_read, mrow, n, read, reasons, row, t, xlsx  # noqa: E402
    from test_round11_importer import PF, perfloor_detail  # noqa: E402


def summary(f):
    """集計: 名称|数量|単位 whose quantities are f(row) over 明細 (rows 2 concrete, 3 rebar)."""
    out = row(1, t("A1", "名称"), t("B1", "数量"), t("C1", "単位"))
    for r, name, q, unit in ((2, "コンクリート", 120, "m3"), (3, "鉄筋", 15, "t")):
        out += row(r, t("A%d" % r, name), n("B%d" % r, q, f(r)), t("C%d" % r, unit))
    return out


def classes(*lines, unit="m3"):
    prep = documents._Prep()
    out = {}
    for line in lines:
        name, spec = (line.split("|") + [""])[:2]
        c = documents._row_class(prep, {"name": name, "specification": spec, "division": "", "unit": unit})
        out[line] = None if not c["fid"] else (c["fid"], c["demolish"] or c["work"] or c["total"] or c["again"] or c["deduct"])
    return out


class TwelfthRoundImporterTests(unittest.TestCase):
    # --- what a formula adds into its value
    def test_masked_sums_choices_lookups_and_let_are_copies(self):
        forms = {
            "mask": "SUMPRODUCT((明細!$A$2:$A$3=A%(r)d)*明細!$C$2:$E$3)",
            "mask two args": "SUMPRODUCT(--(明細!$A$2:$A$3=A%(r)d),明細!$C$2:$C$3)+SUMPRODUCT(--(明細!$A$2:$A$3=A%(r)d),"
                             "明細!$D$2:$D$3)+SUMPRODUCT((明細!$A$2:$A$3=A%(r)d)*1,明細!$E$2:$E$3)",
            "isnumber mask": "SUMPRODUCT(ISNUMBER(SEARCH(A%(r)d,明細!$A$2:$A$3))*明細!$C$2:$E$3)",
            "IFS": "_xlfn.IFS(TRUE,SUM(明細!C%(r)d:E%(r)d))",
            "SWITCH": "_xlfn.SWITCH(1,1,SUM(明細!C%(r)d:E%(r)d))",
            "VLOOKUP": "SUM(VLOOKUP(A%(r)d,明細!$A$2:$E$3,{3,4,5},FALSE))",
            "INDEX": "SUM(INDEX(明細!$C$2:$E$3,MATCH(A%(r)d,明細!$A$2:$A$3,0),0))",
            "XLOOKUP": "SUM(_xlfn.XLOOKUP(A%(r)d,明細!$A$2:$A$3,明細!$C$2:$E$3))",
            "FILTER": "SUM(_xlfn._xlws.FILTER(明細!$C$2:$E$3,明細!$A$2:$A$3=A%(r)d))",
            "LET": "_xlfn.LET(_xlpm.r,明細!C%(r)d:E%(r)d,SUM(_xlpm.r))",
            "AVERAGE": "AVERAGE(明細!C%(r)d:E%(r)d)*3",
        }
        for label, f in forms.items():
            got, r = read(xlsx([("明細", perfloor_detail()), ("集計", summary(lambda rr: f % {"r": rr}))]))
            self.assertEqual(got, PF, label)
            self.assertIn("別のシート（明細）", reasons(r), label)

    def test_factors_and_conditions_stay_factors(self):
        add = lambda f: sorted(k for k in tabular._formula_parts(f)[7] if k[0] == "ref")   # noqa: E731
        # 13 回目: every factor of a product of references counts as added (SUM(明細!C2:E2)*(1+$E$1) copies the floors);
        # a unit mass is kept out by its column's header (単位質量) or by being looked up — see test_round13_importer
        self.assertEqual(add("SUMPRODUCT(B2:B9,C2:C9)"), [("ref", 0), ("ref", 1)])
        self.assertEqual(add("_xlfn.LET(_xlpm.f,係数!B2,D2*_xlpm.f)"), [("ref", 0), ("ref", 1)])
        self.assertEqual(add("_xlfn.LET(_xlpm.k,1.05,C2*_xlpm.k)"), [("ref", 0)])  # a number through LET
        self.assertEqual(add("IF(A1>0,1,0)*B1"), [("ref", 1)])                  # a 0/1 test scales B1
        self.assertEqual(add("A1=B1+C1"), [])                                    # a test is not a quantity
        self.assertEqual(add("-A1^2"), [])
        # the factor rule of round 10 still holds through the walk
        head = HDR.replace("</row>", t("E1", "長さ(m)") + t("F1", "単位質量(kg/m)") + "</row>")
        rows = head + mrow(2, "異形鉄筋", "D13", n("C2", 0.995, "SUMPRODUCT(E2,F2)/1000"), "t", n("E2", 1000), n("F2", 0.995)) + \
            mrow(3, "異形鉄筋", "D13", n("C3", 1.99, "E3*$F$2/1000"), "t", n("E3", 2000))
        got, _ = read(xlsx([("鉄筋", rows)]))
        self.assertAlmostEqual(got[("m_rebar", "t")], 2.985)

    def test_formulas_too_deep_or_of_an_unknown_shape_are_not_checked(self):
        for f in ("SUM(" * 70 + "C2" + ")" * 70, "C2 C2", "(" * 900 + "C2" + ")" * 900):
            body = HDR + mrow(2, "コンクリート", "", n("C2", 100), "m3") + mrow(3, "コンクリート", "別", n("C3", 100, f), "m3")
            got, r = read(xlsx([("明細", body)]))
            self.assertEqual(got, {("m_concrete", "m3"): 100.0}, f[:20])
            self.assertIn("数式の形を読めない", reasons(r))

    def test_a_sheet_name_with_a_middle_dot_is_read_unquoted(self):
        # Excel writes LCR･LCW集計!S77 without quotes (the halfwidth katakana middle dot is allowed in a name)
        for sheet in ("明細･A", "明細・A"):
            summ = HDR + mrow(2, "コンクリート", "全体", n("C2", 150, "SUM(%s!C2:C3)" % sheet), "m3")
            got, r = read(xlsx([(sheet, DETAIL), ("集計", summ)]))
            self.assertEqual(got, {("m_concrete", "m3"): 150.0, ("m_rebar", "t"): 12.0}, sheet)
            self.assertIn("別のシート（%s）" % sheet, reasons(r))

    def test_factor_headers_are_whole_words(self):
        self.assertEqual(tabular._factor_cols(["Description", "Ground floor", "Upper floors", "Superstructure", "Separate",
                                               "Qty", "Unit rate", "Rate", "kg/m", "単位質量", "Amount"]), [6, 7, 8, 9, 10])
        for h1, h2 in (("Ground floor", "Upper floors"), ("Substructure", "Superstructure"), ("Lower floors", "Upper levels")):
            det = row(1, t("A1", "Description"), t("B1", "Specification"), t("C1", h1), t("D1", h2), t("E1", "Qty"), t("F1", "Unit"))
            det += row(2, t("A2", "Reinforced concrete"), t("B2", "C30"), n("C2", 80), n("D2", 220), n("E2", 300), t("F2", "m3"))
            det += row(3, t("A3", "Reinforcement"), t("B3", "B500"), n("C3", 9), n("D3", 27), n("E3", 36), t("F3", "t"))
            summ = row(1, t("A1", "Description"), t("B1", "Qty"), t("C1", "Unit"))
            k = 2
            for name, src, unit in (("Concrete", 2, "m3"), ("Reinforcement", 3, "t")):
                for col in ("C", "D"):
                    summ += row(k, t("A%d" % k, "%s - %s" % (name, h1 if col == "C" else h2)), n("B%d" % k, 0, "Detail!%s%d" % (col, src)),
                                t("C%d" % k, unit))
                    k += 1
            got, _ = read(xlsx([("Detail", det), ("Summary", summ)]))
            self.assertEqual(got, {("m_concrete", "m3"): 300.0, ("m_rebar", "t"): 36.0}, h2)

    # --- attacks on the reader
    def test_a_long_sheet_name_is_cut_where_it_is_shown(self):
        name = "長" * 5000
        body = HDR + "".join(mrow(r, "コンクリート", "", n("C%d" % r, 1), "m3") for r in range(2, 302)) + \
            mrow(302, "コンクリート", "", n("C302", 1, "C2"), "m3")
        got, r = read(xlsx([(name, body)]))
        self.assertEqual(got, {("m_concrete", "m3"): 300.0})
        rows = r["evidence"]["m_concrete"]["rows"] + r["evidence"]["m_concrete"]["excluded"]
        self.assertTrue(rows and all(len(x["trace"]) < 60 for x in rows))
        self.assertTrue(all(len(x["reason"]) < 300 for x in r["unused"]))
        self.assertTrue(all(len(w) < 600 for w in r["warnings"]))

    def test_a_let_shared_by_many_cells_is_read_once(self):
        lets = ",".join("_xlpm.n%d,%d" % (k, k) for k in range(300))
        master = "_xlfn.LET(%s,E2*1)" % lets
        rows_n = 1500
        body = HDR.replace("</row>", t("E1", "補助") + "</row>")
        for r in range(2, rows_n + 2):
            q = n("C%d" % r, 1, master, ' t="shared" ref="C2:C%d" si="0"' % (rows_n + 1)) if r == 2 else \
                n("C%d" % r, 1, "", ' t="shared" si="0"')
            body += mrow(r, "コンクリート", "", q, "m3", n("E%d" % r, 1))
        before = tabular._let_params.cache_info().misses
        t0 = time.perf_counter()
        got, r = read(xlsx([("明細", body)]))
        self.assertLess(tabular._let_params.cache_info().misses - before, 5)
        self.assertLess(time.perf_counter() - t0, 10.0)
        self.assertEqual(got, {("m_concrete", "m3"): float(rows_n)})

    # --- classification (each list from the round-12 regression files)
    def test_removal_rows_with_a_price_note_are_removal(self):
        got, r = csv_read("名称,規格,数量,単位\n既存土間コンクリート,はつり撤去 処分共,35,m3\nコンクリート殻運搬・処分共,,35,m3\n"
                          "既存ブロック塀,撤去別途,48,m2\n既存防水層,撤去 処分別途,420,m2\n既存天井石膏ボード,撤去・処分費共,600,m2\n"
                          "土間コンクリート,Fc21,35,m3\nアスファルト防水,密着工法,420,m2\n石膏ボード,t12.5,600,m2\n"
                          "普通コンクリート,Fc27 殻処分費別途,50,m3\n石膏ボード,t9.5 端材処分共,100,m2\n")
        self.assertEqual(got, {("m_concrete", "m3"): 85.0, ("m_membrane", "m2"): 420.0, ("m_board", "m2"): 700.0})
        got = classes("既存ブロック塀|別途撤去", "既存コンクリート土間|撤去は別途", "既存鉄骨階段|解体撤去 別途", "既存ALC|撤去 処分費別",
                      "Existing blockwork|demolish; disposal by others", "Existing plasterboard partitions|removal by others", unit="m2")
        for k, v in got.items():
            self.assertEqual(v[1] if v else None, documents.SURE, k)

    def test_labour_only_english_rows_are_work(self):
        got, _ = csv_read("Item,Description,Specification,Qty,Unit\n1,Reinforcement,high yield bars B500B; supply only,16,t\n"
                          "2,Reinforcement,high yield bars B500B; fix only,16,t\n3,Ready mixed concrete,C32/40; supply only,240,m3\n"
                          "4,Concrete,C32/40; place and compact in slabs,240,m3\n5,Structural steelwork,S355; supply only,42,t\n"
                          "6,Structural steelwork,S355; erect only,42,t\n7,In situ concrete C20,thrust blocks to drainage bends,6,m3\n"
                          "8,Cast-in-place concrete grade C40,walls,300,m3\n")
        self.assertEqual(got, {("m_rebar", "t"): 16.0, ("m_concrete", "m3"): 546.0, ("m_steel", "t"): 42.0})
        for name in ("Rebar; fix only", "Steelwork; hoist and fix", "Precast concrete units; install", "Concrete; vibrate",
                     "Steel; weld on site", "Plasterboard; fix to studs"):
            self.assertTrue(documents._is_work(name), name)
        for name in ("Cast-in-place concrete C30", "In-place concrete", "Concrete; cast in place", "Concrete C20; poured against earth",
                     "Reinforcement; cut, bent and fixed", "Insulation laid between joists"):
            self.assertFalse(documents._is_work(name), name)

    def test_method_words_qualify_only_a_material_named_in_the_name(self):
        got, r = csv_read("名称,規格,数量,単位\n普通コンクリート,Fc24,320,m3\n土間コンクリート,Fc21 t150 金ごて仕上,45,m3\n"
                          "床,コンクリート金ごて仕上,820,m2\n外壁,打放し仕上,600,m2\n床直均し仕上げ,金ごて,300,m2\n"
                          "仕上塗材,外装薄塗材E,600,m2\nデッキプレート,t1.2 溶接止め,3,t\n鉄骨,現場溶接,50,t\n鉄筋,ガス圧接 D19,20,t\n")
        self.assertEqual(got, {("m_concrete", "m3"): 365.0, ("m_finish", "m2"): 600.0, ("m_steel", "t"): 3.0})
        self.assertIn("作業の行", reasons(r))

    def test_x_yo_y_is_y(self):
        got, r = csv_read("名称,規格,数量,単位\nコンクリート用砕石,2005,45,m3\nコンクリート用砂,洗い砂,30,m3\nモルタル用砂,,12,t\n"
                          "石膏ボード用パテ,,120,kg\nせっこうボード用ジョイントコンパウンド,,200,kg\n鉄骨用溶接材料,,350,kg\n"
                          "鉄骨用高力ボルト,S10T,2.1,t\n防水用シーリング材,,40,kg\n鉄筋用スペーサー,,300,kg\n")
        self.assertEqual(got, {})
        f = documents._field_for
        self.assertEqual(f("防水用シート"), "m_membrane")
        self.assertEqual(f("防水用塗膜"), "m_membrane")
        self.assertEqual(f("断熱用ボード"), "m_insulation")
        self.assertEqual(f("防水用モルタル"), "m_mortar")

    def test_in_names_what_it_sits_in_only_for_a_product(self):
        f = documents._field_for
        for name, want in (("Filling openings in brickwork; 102 mm thick", "m_masonry"), ("Pipe surround in concrete", "m_concrete"),
                           ("Manhole bases in concrete C20", "m_concrete"), ("Drainage bed in concrete", "m_concrete"),
                           ("Boxing in plasterboard", "m_board"), ("Box gutters in aluminium", "m_aluminium"),
                           ("Waterstop in concrete", None), ("Dowel bars in concrete", None), ("Holes in concrete", None)):
            self.assertEqual(f(name), want, name)
        got, _ = csv_read("Description,Qty,Unit\n\"Filling openings in brickwork; 102 mm thick; in cement mortar\",14,m2\n"
                          "\"Facing brickwork; half brick thick\",320,m2\n")
        self.assertEqual(got, {("m_masonry", "m2"): 334.0})

    def test_concrete_blocks_in_m3_are_concrete(self):
        got, _ = csv_read("Description,Qty,Unit\n\"Mass concrete anchor blocks; C25\",4.5,m3\n"
                          "\"In situ concrete C20; thrust blocks to drainage bends\",6,m3\n\"Reinforced concrete C32/40; slabs\",96,m3\n"
                          "\"Concrete blockwork; 140 mm\",80,m2\n")
        self.assertEqual(got, {("m_concrete", "m3"): 106.5, ("m_masonry", "m2"): 80.0})

    # --- what the card says
    def test_a_copy_of_another_sheet_is_not_a_row_that_may_belong(self):
        det = HDR + mrow(2, "普通コンクリート", "", n("C2", 300), "m3") + mrow(3, "異形鉄筋", "", n("C3", 30), "t")
        summ = HDR + mrow(2, "普通コンクリート", "", n("C2", 300, "明細!C2"), "m3") + mrow(3, "異形鉄筋", "", n("C3", 30, "明細!C3"), "t")
        got, r = read(xlsx([("明細", det), ("集計", summ)]))
        self.assertEqual(got, {("m_concrete", "m3"): 300.0, ("m_rebar", "t"): 30.0})
        for fid in ("m_concrete", "m_rebar"):
            ev = r["evidence"][fid]
            self.assertEqual((ev["n_excluded"], ev["n_maybe"]), (1, 0), fid)
            self.assertFalse(ev["excluded"][0]["maybe"])
        # a copy on the same sheet may still be a row to add by hand (a ratio of another material)
        same = HDR + mrow(2, "普通コンクリート", "", n("C2", 300), "m3") + mrow(3, "普通コンクリート", "割増", n("C3", 15, "C2*0.05"), "m3")
        _, r = read(xlsx([("明細", same)]))
        self.assertEqual(r["evidence"]["m_concrete"]["n_maybe"], 1)

    def test_rows_that_may_belong_are_listed_first(self):
        lines = ["名称,数量,単位"]
        for k in range(70):
            lines += ["普通コンクリート,100,m3", "%dF コンクリート 小計,100,m3" % (k + 1), "普通コンクリート 再掲,100,m3",
                      "既存コンクリート撤去,100,m3"]
        lines += ["コンクリート打設手間,7000,m3", "普通コンクリート Fc21,40,m2"]
        got, r = csv_read("\n".join(lines) + "\n")
        ev = r["evidence"]["m_concrete"]
        self.assertEqual(got, {("m_concrete", "m3"): 7000.0})
        self.assertEqual(ev["n_maybe"], 2)
        self.assertEqual(len(ev["excluded"]), documents.MAX_EVIDENCE)
        self.assertEqual([x["maybe"] for x in ev["excluded"][:3]], [True, True, False])
        self.assertEqual(sorted(x["quantity"] for x in ev["excluded"][:2]), [40, 7000])


if __name__ == "__main__":
    unittest.main()
