"""Round 15 of the independent review: the tables (a reference to a pivot table's cells, a hidden column of a bill row,
cells of a helper sheet summed twice, 内訳書による decided by the rows actually counted, the bounded header search, the
pivot table warnings)."""
from __future__ import annotations

import io
import os
import sys
import unittest
from unittest import mock
import zipfile

sys.dont_write_bytecode = True
os.environ.setdefault("WLCSTUDIO_OFFLINE", "1")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

from wlcstudio import documents  # noqa: E402
from wlcstudio.importers import tabular  # noqa: E402

try:
    from tests.test_round10_importer import HDR, NS, RNS, mrow, n, read, row, t, xlsx  # noqa: E402
    from tests.test_round14_tables import OR, PR, excluded, left  # noqa: E402
except ImportError:
    from test_round10_importer import HDR, NS, RNS, mrow, n, read, row, t, xlsx  # noqa: E402
    from test_round14_tables import OR, PR, excluded, left  # noqa: E402

OK = {("m_concrete", "m3"): 150.0, ("m_rebar", "t"): 12.0}
DETAIL = HDR + mrow(2, "コンクリート", "Fc24", n("C2", 100), "m3") + mrow(3, "コンクリート", "Fc27", n("C3", 50), "m3") + \
    mrow(4, "鉄筋", "SD345", n("C4", 12), "t")
# Excel's compact layout (行ラベル | 合計 / 数量: no name or quantity header) and the tabular one with the unit as a field
COMPACT = row(3, t("A3", "行ラベル"), t("B3", "合計 / 数量")) + row(4, t("A4", "コンクリート"), n("B4", 150)) + \
    row(5, t("A5", "鉄筋"), n("B5", 12)) + row(6, t("A6", "総計"), n("B6", 162))
WITH_UNIT = row(3, t("A3", "名称"), t("B3", "数量の合計"), t("C3", "単位")) + \
    row(4, t("A4", "コンクリート"), n("B4", 150), t("C4", "m3")) + row(5, t("A5", "鉄筋"), n("B5", 12), t("C5", "t"))
SUMMARY_HDR = row(1, t("A1", "名称"), t("B1", "数量"), t("C1", "単位"))


def summary(*rows):
    """まとめ: 名称 | 数量 (formula) | 単位, one row per (name, formula, cached value, unit)."""
    out = SUMMARY_HDR
    for i, (nm, f, v, u) in enumerate(rows, 2):
        out += row(i, t("A%d" % i, nm), n("B%d" % i, v, f), t("C%d" % i, u))
    return out


def pivot_book(piv, loc="A3:B6", more=None, hidden_source=False, source=("sheet", "明細"), names=(), detail=DETAIL):
    """明細 (a bill), 集計 (a pivot table of it with these cells at `loc`) and, when given, まとめ (`more`)."""
    buf = io.BytesIO()
    sheets = [("明細", detail), ("集計", piv)] + ([("まとめ", more)] if more else [])
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("xl/workbook.xml", '<workbook %s %s><sheets>%s</sheets>%s<pivotCaches><pivotCache cacheId="3" r:id="rC"/>'
                   '</pivotCaches></workbook>'
                   % (NS, RNS, "".join('<sheet name="%s" sheetId="%d" r:id="rId%d"%s/>'
                                       % (nm, i + 1, i + 1, ' state="hidden"' if hidden_source and i == 0 else "")
                                       for i, (nm, _) in enumerate(sheets)),
                      "<definedNames>%s</definedNames>" % "".join('<definedName name="%s">%s</definedName>' % kv for kv in names)
                      if names else ""))
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="%s">%s<Relationship Id="rC" Type="%s/pivotCacheDefinition" '
                   'Target="pivotCache/pivotCacheDefinition1.xml"/></Relationships>'
                   % (PR, "".join('<Relationship Id="rId%d" Target="worksheets/sheet%d.xml"/>' % (i + 1, i + 1)
                                  for i in range(len(sheets))), OR))
        for i, (_nm, rows) in enumerate(sheets):
            z.writestr("xl/worksheets/sheet%d.xml" % (i + 1), "<worksheet %s %s><sheetData>%s</sheetData></worksheet>" % (NS, RNS, rows))
        z.writestr("xl/worksheets/_rels/sheet2.xml.rels", '<Relationships xmlns="%s"><Relationship Id="rP" Type="%s/pivotTable" '
                   'Target="../pivotTables/pivotTable1.xml"/></Relationships>' % (PR, OR))
        z.writestr("xl/pivotTables/pivotTable1.xml", '<pivotTableDefinition %s name="ピボット表" cacheId="3"><location ref="%s" '
                   'firstHeaderRow="1" firstDataRow="1" firstDataCol="1"/></pivotTableDefinition>' % (NS, loc))
        z.writestr("xl/pivotTables/_rels/pivotTable1.xml.rels", '<Relationships xmlns="%s"><Relationship Id="rC" Type="%s/'
                   'pivotCacheDefinition" Target="../pivotCache/pivotCacheDefinition1.xml"/></Relationships>' % (PR, OR))
        z.writestr("xl/pivotCache/pivotCacheDefinition1.xml", '<pivotCacheDefinition %s %s><cacheSource type="worksheet">'
                   '<worksheetSource ref="A1:D4" %s="%s"/></cacheSource></pivotCacheDefinition>' % ((NS, RNS) + source))
    return buf.getvalue()


def reasons_of(r, prefix):
    return [x for fid in ("m_concrete", "m_rebar", "m_steel", "m_concrete_fdn") for x in excluded(r, fid)
            if x["trace"].startswith("d:" + prefix)]


class FifteenthRoundTableTests(unittest.TestCase):
    # --- a reference to a pivot table's cells
    def test_a_reference_to_a_pivot_tables_cell_reads_that_summary(self):
        GPD = 'GETPIVOTDATA("数量",集計!$A$3,"名称","コンクリート")'
        for piv, loc, b4 in ((COMPACT, "A3:B6", "集計!B4"), (WITH_UNIT, "A3:C5", "集計!B4")):
            for f, names in ((b4, ()), (b4 + "*1.05", ()), ("SUM(%s:%s)" % (b4, b4.split("!")[1]), ()), ("PV", (("PV", "集計!$B$4"),)),
                             ("PV", (("PV", GPD),)), ("LET(x,%s,x*1)" % GPD, ()), ("ROUND(%s,1)" % b4, ())):
                more = summary(("コンクリート", f, 150, "m3"))
                got, r = read(pivot_book(piv, loc, more, names=names))
                self.assertEqual(got, OK, (loc, f))
                ex = reasons_of(r, "まとめ")
                self.assertEqual(len(ex), 1, (loc, f))
                self.assertIn("ピボットテーブル（ピボット表）の値は足さない（元の表 明細 の集計", ex[0]["reason"])
                self.assertFalse(ex[0]["maybe"], (loc, f))
        # a reference next to the pivot table (outside its area) is read as before
        more = summary(("コンクリート", "集計!D4", 150, "m3"))
        got, r = read(pivot_book(COMPACT, "A3:B6", more))
        self.assertEqual(got, {("m_concrete", "m3"): 300.0, ("m_rebar", "t"): 12.0})
        # a formula that reaches the bill and the pivot table is a copy of the bill row (the material rows reached win)
        more = summary(("コンクリート", "明細!C2+集計!B4*0", 100, "m3"))
        got, r = read(pivot_book(COMPACT, "A3:B6", more))
        self.assertEqual(got, OK)
        self.assertIn("別のシート（明細）の材料の行（2 行目）", reasons_of(r, "まとめ")[0]["reason"])

    def test_a_copy_of_a_pivot_table_whose_source_is_not_read_may_belong(self):
        more = summary(("コンクリート", "集計!B4", 150, "m3"), ("鉄筋", "集計!B5", 12, "t"))
        for piv, loc in ((WITH_UNIT, "A3:C5"), (COMPACT, "A3:B6")):
            got, r = read(pivot_book(piv, loc, more, hidden_source=True))
            self.assertEqual(got, {}, loc)
            ex = reasons_of(r, "まとめ")
            self.assertEqual(len(ex), 2, loc)
            for x in ex:                          # not "a copy of what that sheet counts": nothing counts it
                self.assertTrue(x["maybe"], loc)
                self.assertNotIn("二重計上になる", x["reason"])
                self.assertIn("ピボットテーブル（ピボット表）", x["reason"])
            w = [x for x in r["warnings"] if "ピボットテーブル" in x]
            self.assertEqual(len(w), 1)
            self.assertIn("どこにも数えていない", w[0])
            self.assertNotIn("元の表の行を数える", w[0])
        # a source that cannot be told: unchecked, and the warning does not say the source rows are counted
        got, r = read(pivot_book(WITH_UNIT, "A3:C5", more, source=("sheet", "無いシート")))
        self.assertEqual(got, OK)
        ex = reasons_of(r, "まとめ")
        self.assertTrue(ex and all(x["maybe"] and "元の表が分からない" in x["reason"] for x in ex))
        w = [x for x in r["warnings"] if "ピボットテーブル" in x]
        self.assertTrue(w and "確かめられない" in w[0] and "元の表の行を数える" not in w[0])
        # a source read here: as in round 14
        got, r = read(pivot_book(WITH_UNIT, "A3:C5", more))
        self.assertEqual(got, OK)
        self.assertTrue(all(not x["maybe"] for x in reasons_of(r, "まとめ")))
        self.assertTrue(any("元の表の行を数える" in x for x in r["warnings"]))

    def test_a_value_read_from_a_pivot_table_of_a_material_counted_nowhere_may_belong(self):
        # 鉄骨 = the concrete pivot cell × 0.1: steel is counted nowhere, so it is not surely a repeat of the bill
        more = summary(("鉄骨", "集計!B4*0.1", 15, "t"))
        got, r = read(pivot_book(COMPACT, "A3:B6", more))
        self.assertEqual(got, OK)
        ex = left(r, "m_steel")["excluded"]
        self.assertTrue(ex[0]["maybe"])
        self.assertIn("この材料は資料のどこでも数えていない", ex[0]["reason"])

    # --- a hidden column of a bill row
    def test_a_hidden_column_of_a_bill_row_is_one_of_its_numbers(self):
        cols = '<cols><col min="5" max="5" hidden="1" width="0"/></cols>'
        bill = row(1, t("A1", "名称"), t("B1", "規格"), t("C1", "数量"), t("D1", "単位"), t("E1", "設計数量")) + \
            mrow(2, "普通コンクリート", "Fc24", n("C2", 105), "m3", n("E2", 100)) + \
            mrow(3, "異形鉄筋", "SD345", n("C3", 12.48), "t", n("E3", 12))
        want = {("m_concrete", "m3"): 105.0, ("m_rebar", "t"): 12.48}
        for f2, f3 in (("明細!E2", "明細!E3"), ("明細!E2*1.05", "ROUND(明細!E3,1)"), ("SUM(明細!E2:E2)", "明細!$E$3")):
            more = summary(("普通コンクリート", f2, 100, "m3"), ("異形鉄筋", f3, 12, "t"))
            for pre in ({"明細": cols}, {}):
                got, r = read(xlsx([("明細", bill), ("まとめ", more)], pre=pre))
                self.assertEqual(got, want, (f2, pre))
                ex = reasons_of(r, "まとめ")
                self.assertTrue(len(ex) == 2 and all("別のシート（明細）の材料の行" in x["reason"] and not x["maybe"] for x in ex))
        # the hidden column's value is still not read (the row's quantity is its visible one)
        got, r = read(xlsx([("明細", bill)], pre={"明細": cols}))
        self.assertEqual(got, want)
        self.assertTrue(any("非表示の列 1 列は読んでいない" in w for w in r["warnings"]))
        # only numbers count: a hidden text cell of the row is no number of it
        wb = tabular.xlsx_workbook(xlsx([("明細", bill.replace(n("E2", 100), t("E2", "旧")))], pre={"明細": cols}))
        self.assertEqual(wb["sheets"][0]["hidden_nums"], [(), (), (4,)])

    # --- cells of a helper sheet summed twice
    def test_two_quantities_summing_the_same_cells_of_a_helper_sheet(self):
        floors = row(1, t("A1", "部位"), t("B1", "1F"), t("C1", "2F"), t("D1", "3F")) + \
            row(2, t("A2", "コンクリート"), n("B2", 40), n("C2", 30), n("D2", 30)) + row(3, t("A3", "鉄筋"), n("B3", 4), n("C3", 3), n("D3", 3))
        bill = summary(("コンクリート", "SUM(階別!B2:D2)", 100, "m3"), ("鉄筋", "SUM(階別!B3:D3)", 10, "t"))
        want = {("m_concrete", "m3"): 100.0, ("m_rebar", "t"): 10.0}
        for f2, f3 in (("SUM(階別!B2:D2)", "階別!B3+階別!C3+階別!D3"), ("SUM(階別!B2:C2)", "階別!B3"),
                       ("SUM(階別!B2:D2)*(1+$E$1)", "ROUND(SUM(階別!B3:D3),1)")):
            for state in ({}, {"階別": "hidden"}):
                got, r = read(xlsx([("階別", floors), ("明細", bill), ("集計", summary(("コンクリート", f2, 100, "m3"), ("鉄筋", f3, 10, "t")))],
                                   states=state))
                self.assertEqual(got, want, (f2, state))
                ex = reasons_of(r, "集計")
                self.assertEqual(len(ex), 2, (f2, state))
                for x in ex:
                    if (x["name"] == "コンクリート" and f2 != "SUM(階別!B2:D2)") or (x["name"] == "鉄筋" and f3 == "階別!B3"):
                        # summed and multiplied by a cell of its own sheet ($E$1), or only some of the cells the
                        # counted row sums (B2:C2 of B2:D2, B3 of B3:D3): a waste allowance on the same quantity or a
                        # part of it, or another item worked out from the same cells — perhaps a copy (16 回目: it was
                        # sure, and the floor area × 2.5 for the walls was dropped surely; which of two rows was dropped
                        # surely depended on the order of the sheets)
                        self.assertTrue(x["maybe"], (f2, f3, x["reason"]))
                        self.assertIn("材料の行（明細 の %d 行目）が数量に使ったセル（階別 " % (2 if x["name"] == "コンクリート" else 3),
                                      x["reason"])
                        self.assertEqual(x["quantity"], 100 if x["name"] == "コンクリート" else 10)
                        continue
                    self.assertIn("別のシート（明細）の材料の行", x["reason"])
                    self.assertIn("が足し上げたセル（階別 ", x["reason"])
                    self.assertFalse(x["maybe"], (f2, x["reason"]))
        # more than those cells: perhaps a copy (shown with its quantity)
        got, r = read(xlsx([("階別", floors + row(4, t("A4", "追加"), n("B4", 5))), ("明細", bill),
                            ("集計", summary(("コンクリート", "SUM(階別!B2:D2)+階別!B4", 105, "m3")))]))
        self.assertEqual(got, want)
        x = reasons_of(r, "集計")[0]
        self.assertTrue(x["maybe"] and "の一部を足した値" in x["reason"] and x["quantity"] == 105)
        # the same sheet: perhaps a repeat
        got, r = read(xlsx([("階別", floors), ("明細", bill + row(4, t("A4", "コンクリート（再計算）"), n("B4", 100, "SUM(階別!B2:D2)"),
                                                                   t("C4", "m3")))]))
        self.assertEqual(got, want)
        x = reasons_of(r, "明細")[0]
        self.assertTrue(x["maybe"] and "同じシートの材料の行（2 行目）" in x["reason"])
        # another material worked out from the same cells, other cells, a typed row: added as before
        for more in (summary(("鉄骨", "SUM(階別!B2:D2)*0.5", 50, "t")), summary(("コンクリート", "SUM(階別!B5:D5)", 60, "m3")),
                     summary(("コンクリート", None, 60, "m3"))):
            got, r = read(xlsx([("階別", floors + row(5, n("B5", 20), n("C5", 20), n("D5", 20))), ("明細", bill), ("集計", more)]))
            self.assertEqual(len(got), 3 if "鉄骨" in more else 2)
            self.assertFalse(reasons_of(r, "集計"))
        # one area cell times thicknesses (面積 × 厚さ): a dimension of each row, not a part
        area = row(1, t("A1", "部位"), t("B1", "面積"), t("C1", "厚さ")) + row(2, t("A2", "基礎"), n("B2", 100), n("C2", 0.3))
        dama = SUMMARY_HDR + row(2, t("A2", "土間コンクリート"), n("B2", 15, "面積!B2*D2"), t("C2", "m3"), n("D2", 0.15))
        got, r = read(xlsx([("面積", area), ("明細", summary(("基礎コンクリート", "面積!B2*面積!C2", 30, "m3"))), ("集計", dama)]))
        self.assertEqual(got, {("m_concrete_fdn", "m3"): 30.0, ("m_concrete", "m3"): 15.0})

    def test_the_cells_counted_rows_sum_are_kept_within_the_budget(self):
        # (rewritten after the attack on the fix: the cells were kept and looked at one by one on the walk's budget;
        # now rectangles, on a budget of their own)
        S_, M_, C_ = documents.PART_SURE, documents.PART_MAYBE, documents.PART_CHOSEN
        h = documents._Helpers()
        h.add("c", ("明細", 2), [(("階別", 1, 3, 2, 2), S_)])                        # B2:D2
        h.add("c", ("明細", 3), [(("階別", 5, 5, 1, tabular.MAX_ROW_NUMBER), S_)])   # F:F
        h.add("c", ("明細", 4), [(("階別", 1, 1, 3, 3), S_), (("階別", 2, 2, 3, 3), S_), (("階別", 3, 3, 3, 3), S_)])
        h.add("c", ("明細", 5), [(("階別", 7, 7, 9, 9), M_)])                       # one cell: perhaps only
        h.add("c", ("明細", 6), [(("拾い", 2, 2, 2, 4), C_)])                       # SUMIF's sum range: chosen
        self.assertEqual(h.cover("c", ("階別", 1, 3, 2, 2)), ("all", ("明細", 2), S_))
        self.assertEqual(h.cover("c", ("階別", 2, 2, 2, 2)), ("all", ("明細", 2), S_))
        self.assertEqual(h.cover("c", ("階別", 1, 4, 2, 2)), ("some", ("明細", 2), C_))
        self.assertIsNone(h.cover("c", ("階別", 4, 4, 2, 2)))
        self.assertIsNone(h.cover("other", ("階別", 1, 3, 2, 2)))                  # another material
        self.assertEqual(h.cover("c", ("階別", 1, 1, 1, tabular.MAX_ROW_NUMBER))[0], "some")   # B:B
        self.assertEqual(h.cover("c", ("階別", 5, 5, 10, 20)), ("all", ("明細", 3), S_))
        self.assertEqual(h.cover("c", ("階別", 5, 6, 10, 10)), ("some", ("明細", 3), C_))
        self.assertEqual(h.cover("c", ("階別", 1, 3, 3, 3)), ("all", ("明細", 4), S_))      # B3+C3+D3 together
        self.assertEqual(h.cover("c", ("階別", 7, 7, 9, 9)), ("all", ("明細", 5), M_))
        # cells another criterion chose are no match for cells chosen by a criterion; a plain sum of them is
        self.assertIsNone(h.cover("c", ("拾い", 2, 2, 2, 4), picked=True))
        self.assertEqual(h.cover("c", ("拾い", 2, 2, 2, 4)), ("all", ("明細", 6), C_))
        # each rectangle kept and looked at costs steps of a budget of its own, not one per cell: a block of 4,000 cells
        # costs a few steps, a whole column too
        self.assertLess(documents.HELPER_STEPS - h.left, 150)
        for n_ in (1, 4, 4000, tabular.MAX_ROW_NUMBER - 1):
            h2 = documents._Helpers()
            h2.add("c", ("明細", 2), [(("拾い", 2, 2, 2, 1 + n_), S_)])
            h2.cover("c", ("拾い", 2, 2, 2, 1 + n_))
            h2.cover("c", ("拾い", 3, 3, 2, 1 + n_))
            self.assertLess(documents.HELPER_STEPS - h2.left, 12, n_)
        # 19,000 counted rows that each sum a cell of their own: each costs a few steps, not one per cell kept
        h3 = documents._Helpers()
        for i in range(19000):
            self.assertIsNone(h3.cover("c", ("拾い", 1, 1, i + 2, i + 2)))
            h3.add("c", ("明細", i + 2), [(("拾い", 1, 1, i + 2, i + 2), M_)])
        self.assertLess(documents.HELPER_STEPS - h3.left, 19000 * 4)
        big = documents._Helpers(budget=50)
        with self.assertRaises(documents._HelperBudget):
            for i in range(100):
                big.add("c", ("明細", i), [(("拾い", 2, 2, 2, 4001), S_)])
                big.cover("c", ("拾い", 2, 2, 100 + i, 100 + i))
        self.assertTrue(big.full)
        # a value looked up from a helper table is no part of the row that looks it up (two lookups with other keys
        # are not copies of each other)
        table = row(1, t("A1", "部位"), t("B1", "数")) + row(2, t("A2", "Fc24"), n("B2", 100)) + row(3, t("A3", "Fc27"), n("B3", 50))
        more = summary(("コンクリート", 'VLOOKUP("Fc24",拾い!A2:B3,2,0)', 100, "m3"), ("コンクリート", 'VLOOKUP("Fc27",拾い!A2:B3,2,0)', 50, "m3"))
        got, r = read(xlsx([("拾い", table), ("まとめ", more)]))
        self.assertEqual(got, {("m_concrete", "m3"): 150.0})

    def test_a_row_that_refers_to_detail_lines_a_material_row_sums(self):
        lines = HDR + mrow(2, "普通コンクリート", "Fc24", n("C2", 100, "SUM(C3:C5)"), "m3") + \
            row(3, t("A3", "1F"), n("C3", 40)) + row(4, t("A4", "2F"), n("C4", 30)) + row(5, t("A5", "3F"), n("C5", 30)) + \
            mrow(6, "異形鉄筋", "SD345", n("C6", 12), "t")
        hidden = lines.replace('<row r="3">', '<row r="3" hidden="1">').replace('<row r="4">', '<row r="4" hidden="1">') \
            .replace('<row r="5">', '<row r="5" hidden="1">')
        for bill in (lines, hidden):
            # (16 回目: one of the lines, or a row whose name and specification differ from the counted row's, is
            # perhaps another item from the same cells: "may belong" with its quantity, never added. The same item
            # summing the same lines stays a sure copy)
            for nm, f, sure in (("普通コンクリート", "明細!C4", False), ("普通コンクリート Fc24", "明細!C4", False),
                                ("普通コンクリート", "SUM(明細!C3:C5)", False), ("普通コンクリート Fc24", "SUM(明細!C3:C5)", True),
                                ("普通コンクリート Fc24", "明細!C3+明細!C4+明細!C5", True)):
                got, r = read(xlsx([("明細", bill), ("まとめ", summary((nm, f, 30, "m3")))]))
                self.assertEqual(got, {("m_concrete", "m3"): 100.0, ("m_rebar", "t"): 12.0})
                x = reasons_of(r, "まとめ")[0]
                self.assertEqual(x["maybe"], not sure, (nm, f))
                self.assertEqual(x["quantity"], 30)
                self.assertIn("別のシート（明細）の材料の行（2 行目）が足し上げたセル（明細 C" if sure else
                              "材料の行（明細 の 2 行目）が数量に使ったセル（明細 C", x["reason"])
        # a hidden row that no material row sums (an old revision) is read through as before
        old = HDR + mrow(2, "普通コンクリート", "Fc24", n("C2", 100), "m3") + \
            row(3, t("A3", "普通コンクリート"), t("B3", "旧"), n("C3", 90), t("D3", "m3"), attrs=' hidden="1"')
        got, r = read(xlsx([("明細", old), ("まとめ", summary(("普通コンクリート", "明細!C3", 90, "m3")))]))
        self.assertEqual(got, {("m_concrete", "m3"): 190.0})

    # --- 内訳書による / 別紙による
    def test_a_reference_note_is_decided_by_the_rows_counted_elsewhere(self):
        def sheet(rows):
            x = row(1, t("A1", "名称"), t("B1", "摘要"), t("C1", "数量"), t("D1", "単位"))
            for i, (nm, sp, q, u) in enumerate(rows, 2):
                x += row(i, t("A%d" % i, nm), t("B%d" % i, sp), n("C%d" % i, q[0], q[1]) if isinstance(q, tuple) else n("C%d" % i, q),
                         t("D%d" % i, u))
            return x
        for note in ("内訳書による", "別紙による", "別紙内訳"):
            top = sheet([("普通コンクリート", "Fc24 S18 " + note, 300, "m3"), ("異形鉄筋", "SD345 " + note, 30, "t")])
            want = {("m_concrete", "m3"): 300.0, ("m_rebar", "t"): 30.0}
            for other in ([("既存コンクリート", "はつり撤去", 40, "m3"), ("既存鉄筋", "撤去", 2, "t")],
                          [("コンクリート打設手間", "ポンプ打設", 300, "m3"), ("鉄筋加工組立", "", 30, "t")],
                          [("普通コンクリート", "再掲", 300, "m3")],
                          [("普通コンクリート", "", (300, "躯体!C2"), "m3"), ("異形鉄筋", "", (30, "SUM(躯体!C3:C3)"), "t")],
                          [("小計", "", 330, "m3")]):
                got, r = read(xlsx([("躯体", top), ("別表", sheet(other))]))
                self.assertEqual(got, want, (note, other[0]))
                self.assertFalse([x for x in reasons_of(r, "躯体") if x["maybe"]], (note, other[0]))
            # a real breakdown that is counted: perhaps the same quantity, named
            got, r = read(xlsx([("躯体", top), ("内訳明細", sheet([("普通コンクリート", "1 工区", 120, "m3"),
                                                                ("普通コンクリート", "2 工区", 180, "m3")]))]))
            self.assertEqual(got, {("m_concrete", "m3"): 300.0, ("m_rebar", "t"): 30.0}, note)
            x = [x for x in reasons_of(r, "躯体") if x["maybe"]]
            self.assertEqual(len(x), 1)
            self.assertIn("別のシート（内訳明細）で同じ材料の行（2 行目）を数えている", x[0]["reason"])
            # a pivot table of the sheet itself is no breakdown
        piv = row(3, t("A3", "名称"), t("B3", "数量の合計"), t("C3", "単位")) + row(4, t("A4", "コンクリート"), n("B4", 150), t("C4", "m3"))
        got, r = read(pivot_book(piv, "A3:C4", detail=DETAIL.replace("Fc24", "Fc24 配合は別紙による")))
        self.assertEqual(got, OK)
        self.assertFalse([x for x in reasons_of(r, "明細") if x["maybe"]])

    # --- the header search
    def test_the_header_search_is_bounded_and_done_once_per_sheet(self):
        width = 1500
        texts = ["MaterialCost名　称UnitRate数　量%05d" % i for i in range(width)]
        wide = "".join(row(r, *[t("%s%d" % (documents._col_letters(j), r), texts[(j + r) % width]) for j in range(width)])
                       for r in range(1, 31))
        work = tabular.HeaderWork()
        parsed = tabular.read_xlsx(xlsx([("S1", wide), ("S2", HDR + mrow(2, "コンクリート", "", n("C2", 100), "m3"))]), "d", work)
        self.assertEqual(work.searches, 2)                         # once per sheet
        # 30 rows of the wide sheet, each looked at in its first 1,024 non-empty cells, then the bill's header row
        # (+ the bill's header row: its header, quantity, size and factor columns)
        self.assertLessEqual(work.cells, 30 * tabular.MAX_HEADER_CELLS + 4 * 4)
        self.assertLessEqual(len(work.heads), width + 4)           # each distinct text worked out once
        self.assertEqual([s.get("error") for s in parsed["sheets"]], ["見出し行（名称・数量）が見つからない", None])
        self.assertFalse(hasattr(tabular._forms, "cache_info"))    # no global cache of header texts
        # a header within the first 1,024 non-empty cells of its row is found; one after them is not looked at
        for k, found in ((tabular.MAX_HEADER_CELLS - 3, True), (tabular.MAX_HEADER_CELLS, False)):
            head = ["x%d" % i for i in range(k)] + ["名称", "数量", "単位"]
            self.assertEqual(tabular._find_header([head, ["コンクリート"] * k + ["コンクリート", "1", "m3"]])[0] == 0, found, k)

        # (after the attack on the fix) the quantity / size / factor columns look at the same first cells of the header
        # row and work out no key scores; the cells of all sheets together are bounded (counted, not timed: the sheets are
        # given as read, without their XML)
        def workbook(sheets):
            return {"sheets": [{"name": nm, "rows": rows, "numbers": list(range(1, len(rows) + 1)), "formulas": [{}] * len(rows),
                                "hidden_rows": 0, "hidden_cols": 0, "hidden_nums": [()] * len(rows), "hidden_heads": []}
                               for nm, rows in sheets],
                    "hidden_sheets": [], "names": {}, "tables": {}, "fcells": {}, "sheet_names": {nm.casefold(): nm for nm, _ in sheets},
                    "cut_sheets": [], "pivots": [], "names_cut": False}
        # 30 sheets whose header row is 16,384 cells wide (名称｜数量｜単位 and 16,381 distinct texts), one material row each
        wide = [("S%d" % s, [["名称", "数量", "単位"] + ["Ab%dCd%d" % (s, j) for j in range(16381)], ["コンクリート", "1", "m3"]])
                for s in range(30)]
        work = tabular.HeaderWork()
        with mock.patch.object(tabular, "xlsx_workbook", lambda data: workbook(wide)):
            parsed = tabular.read_xlsx(b"", "d", work)
        self.assertEqual(sum(len(s["rows"]) for s in parsed["sheets"]), 30)
        self.assertLessEqual(work.cells, 30 * 4 * tabular.MAX_HEADER_CELLS)      # header, quantity, size, factor columns
        self.assertLessEqual(work.scored, 30 * tabular.MAX_HEADER_CELLS)         # key scores: the header map's cells only
        # 32 sheets of 30 rows × 1,024 distinct texts and no header: the search stops once MAX_HEADER_WORK cells are seen
        flat = [("S%d" % s, [["T%dx%dy%d" % (s, r, j) for j in range(1024)] for r in range(30)]) for s in range(32)]
        work = tabular.HeaderWork()
        with mock.patch.object(tabular, "xlsx_workbook", lambda data: workbook(flat)):
            parsed = tabular.read_xlsx(b"", "d", work)
        self.assertLessEqual(work.cells, tabular.MAX_HEADER_WORK + 30 * tabular.MAX_HEADER_CELLS)
        self.assertLess(work.searches, 32)
        skipped = [s for s in parsed["sheets"] if s.get("unsearched")]
        self.assertEqual(len(skipped) + work.searches, 32)
        self.assertTrue(any("見出しを探すセルが多すぎるので、残りの %d シート" % len(skipped) in w for w in parsed["warnings"]))

    # --- after the attack on the fix: conditional sums and scaled drivers are no cells a counted row sums
    def test_conditional_sums_and_scaled_drivers_are_no_cells_a_row_sums(self):
        take = row(1, t("A1", "部位"), t("B1", "種別"), t("C1", "体積")) + row(2, t("A2", "柱"), t("B2", "Fc24"), n("C2", 10)) + \
            row(3, t("A3", "梁"), t("B3", "Fc24"), n("C3", 20)) + row(4, t("A4", "基礎"), t("B4", "Fc21"), n("C4", 30))
        for a, b in (('SUMIF(拾い!B2:B4,"Fc24",拾い!C2:C4)', 'SUMIF(拾い!B2:B4,"Fc21",拾い!C2:C4)'),
                     ('SUMIF(拾い!B:B,"Fc24",拾い!C:C)', 'SUMIF(拾い!B:B,"Fc21",拾い!C:C)'),
                     ('SUMIFS(拾い!C2:C4,拾い!B2:B4,"Fc24")', 'SUMIFS(拾い!C2:C4,拾い!B2:B4,"Fc21")'),
                     ('SUMPRODUCT((拾い!B2:B4="Fc24")*拾い!C2:C4)', 'SUMPRODUCT((拾い!B2:B4="Fc21")*拾い!C2:C4)'),
                     ('SUMPRODUCT(--(拾い!B2:B4="Fc24"),拾い!C2:C4)', 'SUMPRODUCT(--(拾い!B2:B4="Fc21"),拾い!C2:C4)'),
                     ('SUM(FILTER(拾い!C2:C4,拾い!B2:B4="Fc24"))', 'SUM(FILTER(拾い!C2:C4,拾い!B2:B4="Fc21"))'),
                     ('SUMIF(拾い!B2:B4,B2,拾い!C2:C4)', 'SUMIF(拾い!B2:B4,B2,拾い!C2:C4)')):
            for name2, want in (("コンクリート", {("m_concrete", "m3"): 60.0}),
                                ("基礎コンクリート", {("m_concrete", "m3"): 30.0, ("m_concrete_fdn", "m3"): 30.0})):
                got, r = read(xlsx([("拾い", take), ("躯体", HDR + mrow(2, "コンクリート", "Fc24", n("C2", 30, a), "m3")),
                                    ("基礎", HDR + mrow(2, name2, "Fc21", n("C2", 30, b), "m3"))]))
                self.assertEqual(got, want, (a, name2))
                self.assertFalse(reasons_of(r, "基礎"), a)
            got, r = read(xlsx([("拾い", take), ("明細", HDR + mrow(2, "コンクリート", "Fc24", n("C2", 30, a), "m3") +
                                                 mrow(3, "コンクリート", "Fc21", n("C3", 30, b.replace("B2,", "B3,")), "m3"))]))
            self.assertEqual(got, {("m_concrete", "m3"): 60.0}, a)
        # a whole take-off summed again where a counted row chose some of its cells: perhaps a double count
        got, r = read(xlsx([("拾い", take), ("躯体", HDR + mrow(2, "コンクリート", "Fc24", n("C2", 30, 'SUMIF(拾い!B2:B4,"Fc24",拾い!C2:C4)'), "m3")),
                            ("集計", HDR + mrow(2, "コンクリート", "", n("C2", 60, "SUM(拾い!C2:C4)"), "m3"))]))
        self.assertEqual(got, {("m_concrete", "m3"): 30.0})
        x = reasons_of(r, "集計")[0]
        self.assertTrue(x["maybe"] and "数量に使ったセル（拾い C2:C4）" in x["reason"] and x["quantity"] == 60)
        # 4,000 take-off lines and 300 SUMIFs of distinct keys over them: every row is added (as before round 15), and
        # the bookkeeping does not use up the budget of the other rows (a copy on another sheet, a typed rebar row)
        mats = [("普通コンクリート", "m3", "m_concrete"), ("異形鉄筋", "t", "m_rebar"), ("鉄骨", "t", "m_steel")]
        lines = row(1, t("A1", "部位"), t("B1", "キー"), t("C1", "数量")) + "".join(
            row(i + 2, t("B%d" % (i + 2), "k%d" % (i % 300)), n("C%d" % (i + 2), 1)) for i in range(4000))
        summ = HDR + "".join(mrow(i + 2, mats[i % 3][0], "k%d" % i, n("C%d" % (i + 2), len(range(i, 4000, 300)),
                                                                         'SUMIF(拾い!$B$2:$B$4001,"k%d",拾い!$C$2:$C$4001)' % i), mats[i % 3][1])
                             for i in range(300))
        bill = HDR + mrow(2, "屋根鋼板", "t0.4", n("C2", 300), "m2") + mrow(3, "断熱材", "t50", n("C3", 300), "m2")
        last = HDR + mrow(2, "断熱材", "", n("C2", 300, "明細!C3*1"), "m2") + mrow(3, "異形鉄筋", "差し筋", n("C3", 2.5, "ROUND(2.5*1,1)"), "t")
        got, r = read(xlsx([("拾い", lines), ("集計", summ), ("明細", bill), ("まとめ", last)]))
        for k, (_nm, u, fid) in enumerate(mats):
            self.assertEqual(got[(fid, u)], sum(len(range(i, 4000, 300)) for i in range(k, 300, 3)) + (2.5 if fid == "m_rebar" else 0))
        self.assertFalse(reasons_of(r, "集計"))
        self.assertFalse([w for w in r["warnings"] if "多すぎる" in w])
        self.assertEqual([x["maybe"] for x in excluded(r, "m_insulation")], [False])          # まとめ!R2: a copy, as before
        # a shared area or factor cell scaled by a number (延床面積 × 0.6, 12.5 × 戸数, 1200 × 単位質量 / 1000) is a
        # driver, not a part: the other rows that scale it are added (as before round 15)
        cond = row(1, t("A1", "項目"), t("B1", "値")) + row(2, t("A2", "延床面積"), n("B2", 1000)) + row(3, t("A3", "戸数"), n("B3", 40))
        got, r = read(xlsx([("条件", cond), ("躯体", HDR + mrow(2, "普通コンクリート", "Fc24", n("C2", 600, "条件!B2*0.6"), "m3") +
                                              mrow(3, "鉄筋", "SD345", n("C3", 100, "条件!B2*0.1"), "t")),
                            ("基礎", HDR + mrow(2, "基礎コンクリート", "Fc21", n("C2", 150, "条件!B2*0.15"), "m3"))]))
        self.assertEqual(got, {("m_concrete", "m3"): 600.0, ("m_rebar", "t"): 100.0, ("m_concrete_fdn", "m3"): 150.0})
        got, r = read(xlsx([("条件", cond), ("住戸", HDR + mrow(2, "コンクリート", "住戸 床", n("C2", 500, "12.5*条件!B3"), "m3")),
                            ("共用", HDR + mrow(2, "コンクリート", "共用廊下", n("C2", 80, "2*条件!B3"), "m3"))]))
        self.assertEqual(got, {("m_concrete", "m3"): 580.0})
        haya = row(1, t("A1", "径"), t("B1", "単位質量")) + row(2, t("A2", "D10"), n("B2", 0.56)) + row(3, t("A3", "D13"), n("B3", 0.995))
        got, r = read(xlsx([("早見", haya), ("基礎", HDR + mrow(2, "異形鉄筋", "D13", n("C2", 1.194, "1200*早見!$B$3/1000"), "t")),
                            ("躯体", HDR + mrow(2, "異形鉄筋", "D13", n("C2", 0.796, "800*早見!$B$3/1000"), "t"))]))
        self.assertAlmostEqual(got[("m_rebar", "t")], 1.99)
        # a single cell summed as it is, or cells scaled by a number, are parts only perhaps: a second row "may belong"
        floors = row(1, t("A1", "部位"), t("B1", "1F"), t("C1", "2F"), t("D1", "3F")) + \
            row(2, t("A2", "躯体"), n("B2", 40), n("C2", 30), n("D2", 30))
        for f1, f2, q in (("階別!B2", "階別!B2", 40), ("SUM(階別!B2:D2)*1.05", "SUM(階別!B2:D2)", 100)):
            got, r = read(xlsx([("階別", floors), ("明細", HDR + mrow(2, "コンクリート", "", n("C2", 40, f1), "m3")),
                                ("集計", HDR + mrow(2, "コンクリート", "", n("C2", q, f2), "m3"))]))
            self.assertEqual(len(got), 1)
            x = reasons_of(r, "集計")[0]
            self.assertTrue(x["maybe"] and "数量に使ったセル" in x["reason"], (f1, x["reason"]))

    # --- after the attack on the fix: a hidden factor column
    def test_a_hidden_factor_or_money_column_is_no_number_of_its_row(self):
        cols = '<cols><col min="5" max="5" hidden="1" width="0"/></cols>'
        for head, f, q in (("割増率", "40*明細!E2", 42), ("単価", "ROUND(明細!E2/18000*40,0)", 40), ("単位質量", "明細!E2*40", 42)):
            e2 = 18000 if head == "単価" else 1.05
            bill = row(1, t("A1", "名称"), t("B1", "規格"), t("C1", "数量"), t("D1", "単位"), t("E1", head)) + \
                mrow(2, "コンクリート", "Fc24", n("C2", 100), "m3", n("E2", e2)) + mrow(3, "鉄筋", "D13", n("C3", 12), "t", n("E3", 1.04))
            out = HDR + mrow(2, "土間コンクリート", "Fc18", n("C2", q, f), "m3")
            for pre in ({"明細": cols}, {}):            # hidden or not, the same answer
                got, r = read(xlsx([("明細", bill), ("外構", out)], pre=pre))
                self.assertEqual(got, {("m_concrete", "m3"): 100.0 + q, ("m_rebar", "t"): 12.0}, (head, pre))
            same = bill + mrow(4, "土間コンクリート", "Fc18", n("C4", q, f.replace("明細!", "")), "m3")
            got, r = read(xlsx([("明細", same)], pre={"明細": cols}))
            self.assertEqual(got[("m_concrete", "m3")], 100.0 + q, head)
        # a hidden column whose header names no factor is still one of the row's numbers (設計数量: a copy)
        wb = tabular.xlsx_workbook(xlsx([("明細", row(1, t("A1", "名称"), t("C1", "数量"), t("D1", "単位"), t("E1", "割増率")) +
                                          mrow(2, "コンクリート", "", n("C2", 100), "m3", n("E2", 1.05)))], pre={"明細": cols}))
        self.assertEqual(wb["sheets"][0]["hidden_heads"][0], {4: "割増率"})
        self.assertEqual(wb["sheets"][0]["rows"][0][4:], [])                    # (its text is not a value of the row)

    # --- after the attack on the fix: pivot tables met while walking
    def test_a_pivot_tables_label_used_as_a_key_does_not_hide_the_copy(self):
        bill = HDR + mrow(2, "コンクリート", "Fc24", n("C2", 100), "m3") + mrow(3, "鉄筋", "D13", n("C3", 12), "t")
        old = HDR + mrow(2, "コンクリート", "Fc24", n("C2", 90), "m3")
        piv = row(3, t("A3", "行ラベル"), t("B3", "合計 / 数量")) + row(4, t("A4", "コンクリート"), n("B4", 90)) + \
            row(5, t("A5", "総計"), n("B5", 90))
        for f in ("SUMIF(明細!A:A,前回集計!A4,明細!C:C)", '明細!C2+0*COUNTIF(前回集計!A:A,"x")'):
            got, r = read(book([("明細", bill), ("旧明細", old, True), ("前回集計", piv), ("まとめ", summary(("コンクリート", f, 100, "m3")))],
                               [(2, "前回", "A3:B5", "旧明細")]))
            self.assertEqual(got, {("m_concrete", "m3"): 100.0, ("m_rebar", "t"): 12.0}, f)
            x = reasons_of(r, "まとめ")[0]
            self.assertFalse(x["maybe"], f)
            self.assertIn("別のシート（明細）の材料の行（2 行目）", x["reason"])

    def test_a_pivot_of_a_take_off_sheet_read_by_one_row_is_counted(self):
        take = row(1, t("A1", "部位"), t("B1", "材料"), t("C1", "体積")) + row(2, t("A2", "柱"), t("B2", "コンクリート"), n("C2", 60)) + \
            row(3, t("A3", "梁"), t("B3", "コンクリート"), n("C3", 90))
        piv = row(3, t("A3", "行ラベル"), t("B3", "合計 / 体積")) + row(4, t("A4", "コンクリート"), n("B4", 150))

        def go(rows, hidden=False, more=None):
            sheets = [("拾い", take, hidden), ("集計", piv), ("まとめ", summary(*rows))] + ([("明細", more)] if more else [])
            return read(book(sheets, [(1, "ピボット1", "A3:B4", "拾い", "A1:C3")]))
        for f in ("集計!B4", "集計!B4*1.05", "ROUND(集計!B4,0)"):
            got, r = go([("コンクリート", f, 150, "m3")])
            self.assertEqual(list(got), [("m_concrete", "m3")], f)
            self.assertFalse(reasons_of(r, "まとめ"))
            self.assertTrue(any("まとめ の 2 行目はピボットテーブル（ピボット1）の値を参照している" in w for w in r["warnings"]))
        # otherwise "may belong", with its quantity: two rows read the cell, the source is hidden, a counted row reaches
        # the source (whatever its material), another row counts the material, the row reads more than the cell
        for rows, hidden, more in (([("コンクリート", "集計!B4", 150, "m3"), ("コンクリート", "集計!B4", 150, "m3")], False, None),
                                   ([("コンクリート", "集計!B4", 150, "m3")], True, None),
                                   ([("コンクリート", "集計!B4", 150, "m3")], False, HDR + mrow(2, "コンクリート", "", n("C2", 150, "SUM(拾い!C2:C3)"), "m3")),
                                   ([("コンクリート", "集計!B4", 150, "m3")], False, HDR + mrow(2, "鉄筋", "", n("C2", 60, "拾い!C2"), "t")),
                                   ([("コンクリート", "集計!B4", 150, "m3")], False, HDR + mrow(2, "コンクリート", "Fc18", n("C2", 30), "m3")),
                                   ([("コンクリート", "集計!B4+拾い!C3", 240, "m3")], False, None)):
            got, r = go(rows, hidden, more)
            ex = reasons_of(r, "まとめ")
            self.assertTrue(ex and all(x["maybe"] and "ピボットテーブル（ピボット1）" in x["reason"] for x in ex), (rows, hidden, more))
            self.assertFalse([w for w in r["warnings"] if "足した" in w])

    def test_a_value_read_from_a_pivot_table_names_its_material_family(self):
        detail = HDR + mrow(2, "コンクリート", "Fc24", n("C2", 100), "m3") + mrow(3, "コンクリート", "Fc27", n("C3", 50), "m3") + \
            mrow(4, "鉄筋", "D13", n("C4", 12), "t")
        got, r = read(pivot_book(COMPACT, "A3:B6", summary(("基礎コンクリート", "集計!B4", 150, "m3")), detail=detail))
        self.assertEqual(got, OK)
        x = reasons_of(r, "まとめ")[0]
        self.assertFalse(x["maybe"])
        self.assertNotIn("どこでも数えていない", x["reason"])

    # --- after the attack on the fix: a copy of a row left out as "may belong"
    def test_a_copy_of_a_row_left_out_as_may_belong_may_belong_too(self):
        top = row(1, t("A1", "名称"), t("B1", "摘要"), t("C1", "数量"), t("D1", "単位")) + \
            row(2, t("A2", "普通コンクリート"), t("B2", "Fc24 S18 別紙による"), n("C2", 300), t("D2", "m3"))
        sub = row(1, t("A1", "名称"), t("B1", "摘要"), t("C1", "数量"), t("D1", "単位")) + \
            row(2, t("A2", "普通コンクリート"), n("C2", 300, "躯体!C2"), t("D2", "m3")) + \
            row(3, t("A3", "土間コンクリート"), t("B3", "Fc18"), n("C3", 40), t("D3", "m3"))
        got, r = read(xlsx([("躯体", top), ("内訳", sub)]))
        self.assertEqual(got, {("m_concrete", "m3"): 40.0})
        x = reasons_of(r, "内訳")[0]
        self.assertTrue(x["maybe"] and "別のシート（躯体）の材料の行（2 行目）" in x["reason"] and "足していない" in x["reason"])
        self.assertNotIn("二重計上になる", x["reason"])
        self.assertTrue(all(x["maybe"] for x in reasons_of(r, "躯体")))
        # a copy that also reaches a counted row stays a sure copy (異形鉄筋（割増 5%） = B2*1.05 copies the counted row 2)
        bill = row(1, t("A1", "名称"), t("B1", "数量"), t("C1", "単位")) + row(2, t("A2", "異形鉄筋"), n("B2", 10), t("C2", "t")) + \
            row(3, t("A3", "異形鉄筋（割増 5%）"), n("B3", 10.5, "B2*1.05"), t("C3", "t"))
        got, r = read(xlsx([("明細", bill), ("集計", row(1, t("A1", "名称"), t("B1", "数量"), t("C1", "単位")) +
                                              row(2, t("A2", "鉄筋"), n("B2", 10.5, "明細!B3"), t("C2", "t")))]))
        self.assertEqual(got, {("m_rebar", "t"): 10.0})
        self.assertFalse(reasons_of(r, "集計")[0]["maybe"])


def book(sheets, pivots):
    """Sheets [(name, rows xml[, hidden])] and pivot tables [(sheet index, name, location, source sheet[, source ref])]."""
    sheets = [(s + (False,))[:3] for s in sheets]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("xl/workbook.xml", '<workbook %s %s><sheets>%s</sheets><pivotCaches>%s</pivotCaches></workbook>'
                   % (NS, RNS, "".join('<sheet name="%s" sheetId="%d" r:id="rId%d"%s/>' % (nm, i + 1, i + 1, ' state="hidden"' if h else "")
                                       for i, (nm, _r, h) in enumerate(sheets)),
                      "".join('<pivotCache cacheId="%d" r:id="rC%d"/>' % (k + 1, k + 1) for k in range(len(pivots)))))
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="%s">%s%s</Relationships>'
                   % (PR, "".join('<Relationship Id="rId%d" Target="worksheets/sheet%d.xml"/>' % (i + 1, i + 1) for i in range(len(sheets))),
                      "".join('<Relationship Id="rC%d" Type="%s/pivotCacheDefinition" Target="pivotCache/pivotCacheDefinition%d.xml"/>'
                              % (k + 1, OR, k + 1) for k in range(len(pivots)))))
        for i, (_nm, rows, _h) in enumerate(sheets):
            z.writestr("xl/worksheets/sheet%d.xml" % (i + 1), "<worksheet %s %s><sheetData>%s</sheetData></worksheet>" % (NS, RNS, rows))
        for k, pv in enumerate(pivots):
            si, name, loc, src = pv[:4]
            ref = pv[4] if len(pv) > 4 else "A1:D4"
            z.writestr("xl/worksheets/_rels/sheet%d.xml.rels" % (si + 1), '<Relationships xmlns="%s"><Relationship Id="rP" '
                       'Type="%s/pivotTable" Target="../pivotTables/pivotTable%d.xml"/></Relationships>' % (PR, OR, k + 1))
            z.writestr("xl/pivotTables/pivotTable%d.xml" % (k + 1), '<pivotTableDefinition %s name="%s" cacheId="%d"><location ref="%s" '
                       'firstHeaderRow="1" firstDataRow="1" firstDataCol="1"/></pivotTableDefinition>' % (NS, name, k + 1, loc))
            z.writestr("xl/pivotTables/_rels/pivotTable%d.xml.rels" % (k + 1), '<Relationships xmlns="%s"><Relationship Id="rC" Type="%s/'
                       'pivotCacheDefinition" Target="../pivotCache/pivotCacheDefinition%d.xml"/></Relationships>' % (PR, OR, k + 1))
            z.writestr("xl/pivotCache/pivotCacheDefinition%d.xml" % (k + 1), '<pivotCacheDefinition %s %s><cacheSource type="worksheet">'
                       '<worksheetSource ref="%s" sheet="%s"/></cacheSource></pivotCacheDefinition>' % (NS, RNS, ref, src))
    return buf.getvalue()


if __name__ == "__main__":
    unittest.main()
