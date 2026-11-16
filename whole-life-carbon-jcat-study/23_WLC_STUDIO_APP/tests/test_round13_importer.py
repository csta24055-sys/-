"""Round 13 of the independent review: the importer (X用Y read by the end of Y; camelCase money headers; "cut to
length" as a participle; 摘要 / 形状・寸法 as the specification; 打込み for cast-in insulation; a cross-sheet row of
another material; unknown functions and products of references; testing rows; concrete blocks in any letter case and on
the PDF path)."""
from __future__ import annotations

import base64
import os
import sys
import unittest

sys.dont_write_bytecode = True
os.environ.setdefault("WLCSTUDIO_OFFLINE", "1")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

from wlcstudio import documents  # noqa: E402
from wlcstudio.importers import tabular  # noqa: E402

try:
    from tests.test_round10_importer import HDR, csv_read, mrow, n, read, reasons, row, t, xlsx  # noqa: E402
    from tests.test_round11_importer import PF, perfloor_detail  # noqa: E402
    from tests.test_round12_importer import summary  # noqa: E402
except ImportError:
    from test_round10_importer import HDR, csv_read, mrow, n, read, reasons, row, t, xlsx  # noqa: E402
    from test_round11_importer import PF, perfloor_detail  # noqa: E402
    from test_round12_importer import summary  # noqa: E402


def head(name):
    return documents._head(documents._prep(name))[0]


def left(r, fid):
    return r.get("left_out", {}).get(fid) or {}


class ThirteenthRoundImporterTests(unittest.TestCase):
    # --- classification
    def test_x_yo_y_is_x_when_y_ends_in_a_form_of_x(self):
        expect = {
            "防水用改質アスファルトシート": "m_membrane", "防水用ウレタン塗膜": "m_membrane", "防水用加硫ゴムシート": "m_membrane",
            "防水用アスファルトルーフィング": "m_membrane", "防水用アスファルト": "m_membrane",
            "断熱用フォームボード": "m_insulation", "断熱用押出発泡ボード": "m_insulation", "断熱用ボード": "m_insulation",
            "鉄骨用鋼板": "m_steel", "鉄骨用ベースプレート": "m_steel", "鉄骨用デッキ": "m_steel",
            "防水用モルタル": "m_mortar", "石膏ボード": "m_board",
            # Y names a product of no field: no material (and a bare ボード after the purpose is no head of its own)
            "鉄筋用スペーサー": None, "鉄骨用高力ボルト": None, "断熱用ボード押え金物": None, "防水用シート押え金物": None,
            "石膏ボード用パテ": None,
        }
        self.assertEqual({k: head(k) for k in expect}, expect)
        got, r = csv_read("名称,規格,数量,単位\n防水用改質アスファルトシート,t4 トーチ工法,420,m2\n防水用ウレタン塗膜,X-2 t3,180,m2\n"
                          "断熱用フォームボード,t50,600,m2\n石膏ボード,t12.5,1200,m2\n")
        self.assertEqual(got, {("m_membrane", "m2"): 600.0, ("m_insulation", "m2"): 600.0, ("m_board", "m2"): 1200.0})

    def test_camel_case_money_and_quantity_headers(self):
        got, _ = csv_read("Ref,Description,Qty,Unit,MaterialRate,MaterialCost\nA1,Concrete C30 in slabs,120,m3,95,11400\n"
                          "A2,Reinforcement bars,12,t,800,9600\nA3,Structural steelwork,30,t,1500,45000\n")
        self.assertEqual(got, {("m_concrete", "m3"): 120.0, ("m_rebar", "t"): 12.0, ("m_steel", "t"): 30.0})
        h = ["Ref", "Description", "Qty", "Unit", "MaterialRate", "UnitPrice", "UnitWeight", "TotalCost", "TotalVolume",
             "NetArea"]
        self.assertEqual(h[tabular._header_map(h)["name"]], "Description")
        self.assertEqual([h[j] for j in tabular._qty_cols(h)], ["Qty", "TotalVolume", "NetArea"])
        self.assertEqual({h[j] for j in tabular._factor_cols(h)} >= {"MaterialRate", "UnitPrice", "UnitWeight", "TotalCost"},
                         True)

    def test_cut_to_length_is_a_participle(self):
        got, r = csv_read("Item,Description,Qty,Unit\n1,\"High yield steel bar reinforcement, 16 mm, cut to length\",12.5,t\n"
                          "2,\"Steel plates, 10 mm, cut to size\",3.2,t\n3,\"Softwood timber joists 50x200, sawn, cut to length\",4.8,m3\n"
                          "4,\"Mineral wool insulation 100 mm, cut to fit between joists\",420,m2\n")
        self.assertEqual(got, {("m_rebar", "t"): 12.5, ("m_steel", "t"): 3.2, ("m_timber", "m3"): 4.8,
                               ("m_insulation", "m2"): 420.0})
        self.assertTrue(documents._is_work("Reinforcement bars, cut only"))
        self.assertTrue(documents._is_work("Rebar cut and bend"))
        self.assertFalse(documents._is_work("Reinforcement bars, cut, bent and fixed"))

    def test_tekiyo_and_keijo_sunpo_are_the_specification(self):
        for col in ("摘要", "形状・寸法", "形状寸法", "品質・規格"):
            got, r = csv_read("名称,%s,数量,単位\n異形鉄筋,SD345 D19,30,t\n鉄筋,加工組立,30,t\n普通コンクリート,Fc24,100,m3\n"
                              "既存床コンクリート,はつり撤去 処分共,12,m3\n" % col)
            self.assertEqual(got, {("m_rebar", "t"): 30.0, ("m_concrete", "m3"): 100.0}, col)
        got, _ = csv_read("名称,摘要,数量,単位,単価,金額,備考\n普通コンクリート,Fc24 基礎,85,m3,,,\n普通コンクリート,Fc24,300,m3,,,\n")
        self.assertEqual(got, {("m_concrete_fdn", "m3"): 85.0, ("m_concrete", "m3"): 300.0})

    def test_cast_in_names_how_insulation_is_put_in_place(self):
        self.assertFalse(documents._is_work("押出法ポリスチレンフォーム", "3種b t50 打込み"))
        self.assertTrue(documents._is_work("普通コンクリート", "Fc24 打込み"))
        self.assertTrue(documents._is_work("コンクリート打込み"))

    def test_testing_rows_are_work(self):
        for nm in ("Testing of concrete cubes", "Concrete cube testing", "Concrete test cubes", "Concrete cube tests",
                   "Sampling and testing of concrete", "Slump testing of concrete"):
            self.assertTrue(documents._is_work(nm), nm)
        for nm in ("Concrete test piles 600 dia", "Concrete C30 tested to BS EN 206", "Concrete including testing",
                   "Concrete; testing by others"):
            self.assertFalse(documents._is_work(nm), nm)
        got, _ = csv_read("Description,Qty,Unit\nConcrete C30,100,m3\nTesting of concrete cubes,20,m3\n")
        self.assertEqual(got, {("m_concrete", "m3"): 100.0})

    def test_concrete_blocks_in_any_letter_case_and_on_the_pdf_path(self):
        prep = documents._Prep()
        for nm in ("Mass Concrete Anchor Blocks", "MASS CONCRETE ANCHOR BLOCKS", "mass concrete anchor blocks"):
            c = documents._row_class(prep, {"name": nm, "specification": "", "division": "Foundations", "unit": "m3"})
            self.assertEqual(c["fid"], "m_concrete_fdn", nm)
        try:
            from tests.test_wlcstudio import _pdf
        except ImportError:
            from test_wlcstudio import _pdf
        r = documents.read("b.pdf", base64.b64encode(_pdf(["Mass concrete anchor blocks   4.5 m3",
                                                            "Concrete C30 in slabs   120 m3"])).decode(), "d")
        got = sorted((p.field_id, p.value) for p in r["proposals"])
        self.assertEqual(got, [("m_concrete", 4.5), ("m_concrete", 120.0)])

    # --- copies
    def test_a_cross_sheet_row_of_another_material_may_belong(self):
        detail = HDR + mrow(2, "コンクリート", "Fc24", n("C2", 100), "m3")
        est = HDR + mrow(2, "鉄筋", "SD345", n("C2", 12, "明細!C2*0.12"), "t")
        got, r = read(xlsx([("明細", detail), ("概算", est)]))
        self.assertEqual(got, {("m_concrete", "m3"): 100.0})
        lo = left(r, "m_rebar")
        self.assertEqual((lo.get("n_excluded"), lo.get("n_maybe")), (1, 1))
        self.assertIn("ほかの材料の行", reasons(r))
        self.assertNotIn("そのシートも読んでいるので二重計上になる", reasons(r))
        # a copy of the same material on another sheet stays surely a copy (not a row that may belong)
        same = HDR + mrow(2, "コンクリート", "Fc24", n("C2", 100, "明細!C2"), "m3")
        got, r = read(xlsx([("明細", detail), ("集計", same)]))
        self.assertEqual(got, {("m_concrete", "m3"): 100.0})
        self.assertEqual(r["evidence"]["m_concrete"].get("n_maybe"), 0)
        self.assertIn("そのシートも読んでいるので二重計上になる", reasons(r))

    def test_unknown_functions_and_factor_cells_are_copies(self):
        forms = {
            "waste cell": "SUM(明細!C%(r)d:E%(r)d)*(1+係数!$A$1)",
            "MMULT": "SUM(MMULT(明細!C%(r)d:E%(r)d,{1;1;1}))",
            "PRODUCT": "PRODUCT(SUM(明細!C%(r)d:E%(r)d),1)",
            "REDUCE": "_xlfn.REDUCE(0,明細!C%(r)d:E%(r)d,_xlfn.LAMBDA(_xlpm.a,_xlpm.b,_xlpm.a+_xlpm.b))",
            "MAP": "SUM(_xlfn.MAP(明細!C%(r)d:E%(r)d,_xlfn.LAMBDA(_xlpm.v,_xlpm.v)))",
            "BYROW": "SUM(_xlfn.BYROW(明細!C%(r)d:E%(r)d,_xlfn.LAMBDA(_xlpm.q,SUM(_xlpm.q))))",
            "CONVERT": "CONVERT(SUM(明細!C%(r)d:E%(r)d),\"m^3\",\"m^3\")",
            "SUMPRODUCT of two arrays": "SUMPRODUCT(明細!C%(r)d:E%(r)d,係数!$A$2:$C$2)",
        }
        for label, f in forms.items():
            factors = row(1, n("A1", 0)) + row(2, n("A2", 1), n("B2", 1), n("C2", 1))
            got, r = read(xlsx([("明細", perfloor_detail()), ("集計", summary(lambda rr: f % {"r": rr})), ("係数", factors)]))
            self.assertEqual(got, PF, label)
            self.assertIn("別のシート（明細）", reasons(r), label)

    def test_a_looked_up_unit_mass_stays_a_factor(self):
        add = lambda f: sorted(k for k in tabular._formula_parts(f)[7] if k[0] == "ref")   # noqa: E731
        self.assertEqual(add("E7*VLOOKUP(B7,$H$2:$I$5,2,0)"), [("ref", 0)])
        self.assertEqual(add("E7*INDEX($I$2:$I$5,MATCH(B7,$H$2:$H$5,0))"), [("ref", 0)])
        self.assertEqual(add("VLOOKUP(A1,$H$2:$I$5,2,0)*1.05"), [("ref", 1)])        # one value scaled: added
        self.assertEqual(add("SUM(明細!C2:E2)*(1+$D$2)"), [("ref", 0), ("ref", 1)])
        self.assertEqual(add("A1*B1/C1"), [("ref", 0), ("ref", 1)])                  # a divisor is no part of it
        # a side table of unit masses on the rows of the bill (no header) is looked up, not copied
        rows = HDR.replace("</row>", t("E1", "長さ(m)") + "</row>")
        rows += mrow(2, "異形鉄筋", "D10", n("C2", 0.56, "E2*VLOOKUP(B2,$H$2:$I$3,2,0)/1000"), "t", n("E2", 1000),
                     t("H2", "D10"), n("I2", 0.56))
        rows += mrow(3, "異形鉄筋", "D13", n("C3", 1.99, "E3*VLOOKUP(B3,$H$2:$I$3,2,0)/1000"), "t", n("E3", 2000),
                     t("H3", "D13"), n("I3", 0.995))
        got, r = read(xlsx([("鉄筋", rows)]))
        self.assertEqual(list(got), [("m_rebar", "t")])
        self.assertAlmostEqual(got[("m_rebar", "t")], 2.55)


if __name__ == "__main__":
    unittest.main()
