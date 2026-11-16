"""Round 14 of the independent review: the tables (UoM and joined money headers, the unit column, pivot tables, a row's
own parts versus its dimensions, lookups keyed on the bill, the bounded check of a copy on another sheet, a copy of
another material that is already counted)."""
from __future__ import annotations

import io
import os
import sys
import time
import unittest
import zipfile

sys.dont_write_bytecode = True
os.environ.setdefault("WLCSTUDIO_OFFLINE", "1")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

from wlcstudio import documents  # noqa: E402
from wlcstudio.importers import tabular  # noqa: E402

try:
    from tests.test_round10_importer import HDR, NS, RNS, csv_read, mrow, n, read, reasons, row, t, xlsx  # noqa: E402
except ImportError:
    from test_round10_importer import HDR, NS, RNS, csv_read, mrow, n, read, reasons, row, t, xlsx  # noqa: E402

BOQ = (("Ready mixed concrete C30/37 in slabs", 120, "m3"), ("High yield steel reinforcement bars", 14.5, "t"))
TWO = {("m_concrete", "m3"): 120.0, ("m_rebar", "t"): 14.5}
PR = "http://schemas.openxmlformats.org/package/2006/relationships"
OR = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def boq(heads: str) -> str:
    """A CSV bill with these headers: the description, quantity and unit go to the columns so named; every other column
    holds a number (a code, a rate, an amount)."""
    hs = heads.split(",")
    out = [heads]
    for i, (name, q, u) in enumerate(BOQ):
        cells = []
        for h in hs:
            k = h.strip().lower()
            cells.append('"%s"' % name if k == "description" else str(q) if k in ("qty", "netqty") else
                         u if k in ("uom", "unit", "u/m", "units") else str(100 + 10 * i + len(cells)))
        out.append(",".join(cells))
    return "\n".join(out) + "\n"


def left(r, fid):
    return r.get("left_out", {}).get(fid) or {}


def excluded(r, fid):
    ev = r["evidence"].get(fid) or {}
    return ev.get("excluded") or left(r, fid).get("excluded") or []


def pivot_book(source, loc="A3:B6", pages=0, data=1, hidden_source=False, rel=True, cache=True, names=None):
    """明細 (a bill) and 集計 (a pivot table of it) written as minimal ECMA-376 parts: location, page fields, data
    fields, a cache whose worksheetSource is `source` (attributes) or none."""
    detail = HDR + mrow(2, "コンクリート", "Fc24", n("C2", 100), "m3") + mrow(3, "コンクリート", "Fc27", n("C3", 50), "m3") + \
        mrow(4, "鉄筋", "SD345", n("C4", 12), "t")
    top = 3
    piv = (row(1, t("A1", "規格"), t("B1", "(すべて)")) if pages else "") + \
        row(top, t("A3", "名称"), t("B3", "数量の合計"), t("C3", "単位")) + \
        row(4, t("A4", "コンクリート"), n("B4", 150), t("C4", "m3")) + row(5, t("A5", "鉄筋"), n("B5", 12), t("C5", "t")) + \
        row(6, t("A6", "総計"), n("B6", 162))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("xl/workbook.xml", '<workbook %s %s><sheets><sheet name="明細" sheetId="1" r:id="rId1"%s/><sheet name="集計" '
                   'sheetId="2" r:id="rId2"/></sheets>%s%s</workbook>'
                   % (NS, RNS, ' state="hidden"' if hidden_source else "",
                      "<definedNames>%s</definedNames>" % "".join('<definedName name="%s">%s</definedName>' % kv for kv in names)
                      if names else "", '<pivotCaches><pivotCache cacheId="3" r:id="rId3"/></pivotCaches>' if cache else ""))
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="%s"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/>'
                   '<Relationship Id="rId2" Target="worksheets/sheet2.xml"/>%s</Relationships>'
                   % (PR, '<Relationship Id="rId3" Type="%s/pivotCacheDefinition" Target="pivotCache/pivotCacheDefinition1.xml"/>'
                      % OR if cache else ""))
        for i, rows in ((1, detail), (2, piv)):
            z.writestr("xl/worksheets/sheet%d.xml" % i, "<worksheet %s %s><sheetData>%s</sheetData></worksheet>" % (NS, RNS, rows))
        z.writestr("xl/worksheets/_rels/sheet2.xml.rels", '<Relationships xmlns="%s"><Relationship Id="rP" Type="%s/pivotTable" '
                   'Target="../pivotTables/pivotTable1.xml"/></Relationships>' % (PR, OR))
        dfs = "".join('<dataField name="%s" fld="%d"/>' % x for x in (("数量の合計", 2), ("金額の合計", 4))[:data])
        z.writestr("xl/pivotTables/pivotTable1.xml",
                   '<pivotTableDefinition %s name="ピボット表" cacheId="3"><location ref="%s" firstHeaderRow="1" firstDataRow="1" '
                   'firstDataCol="1"%s/><rowFields count="1"><field x="0"/></rowFields>%s<dataFields count="%d">%s</dataFields>'
                   '</pivotTableDefinition>' % (NS, loc, ' rowPageCount="%d" colPageCount="1"' % pages if pages else "",
                                                 '<pageFields count="1"><pageField fld="1"/></pageFields>' if pages else "",
                                                 data, dfs))
        if rel:
            z.writestr("xl/pivotTables/_rels/pivotTable1.xml.rels", '<Relationships xmlns="%s"><Relationship Id="rC" '
                       'Type="%s/pivotCacheDefinition" Target="../pivotCache/pivotCacheDefinition1.xml"/></Relationships>' % (PR, OR))
        if cache:
            z.writestr("xl/pivotCache/pivotCacheDefinition1.xml",
                       '<pivotCacheDefinition %s %s><cacheSource type="worksheet">%s</cacheSource><cacheFields count="4">'
                       '<cacheField name="名称"/><cacheField name="規格"/><cacheField name="数量"/><cacheField name="単位"/>'
                       '</cacheFields></pivotCacheDefinition>'
                       % (NS, RNS, "<worksheetSource %s/>" % " ".join('%s="%s"' % kv for kv in source.items()) if source else ""))
    return buf.getvalue()


def floors(head3, qty_formula, summary_formula, summary_name="コンクリート", summary_unit="m3"):
    """明細: 名称|規格|<three per-type / per-floor columns>|数量|単位, row 2 コンクリート 40/30/30; 集計: one row."""
    h = row(1, t("A1", "名称"), t("B1", "規格"), t("C1", head3[0]), t("D1", head3[1]), t("E1", head3[2]), t("F1", "数量"),
            t("G1", "単位"))
    det = h + row(2, t("A2", "コンクリート"), t("B2", "Fc24"), n("C2", 40), n("D2", 30), n("E2", 30),
                  n("F2", 100, qty_formula), t("G2", "m3"))
    summ = row(1, t("A1", "名称"), t("B1", "数量"), t("C1", "単位"), t("E1", "割増率"), n("F1", 0.05)) + \
        row(2, t("A2", summary_name), n("B2", 105, summary_formula), t("C2", summary_unit))
    return xlsx([("明細", det), ("集計", summ)])


class FourteenthRoundTableTests(unittest.TestCase):
    # --- headers
    def test_uom_joined_money_and_the_unit_column(self):
        for heads in ("Item,Description,Qty,UoM,Rate,Amount", "Item,Description,Qty,UOM,Unit Rate,Amount",
                      "Item,Description,Qty,U/M,Unit Cost,Total", "Item,Description,Qty,UOM,Unit Price,Amount",
                      "ITEM,DESCRIPTION,QTY,UNIT,LABOURRATE,MATERIALRATE,AMOUNT",
                      "Item,Description,Qty,Unit,Labourcost,Materialcost,Total", "Item,Description,Qty,UoM,LabourRate,MaterialRate,Amount",
                      "Item,Description,NetQTY,UoM,Rate", "Item No,Description,UOM,QTY,UNITPRICE,TOTALAMOUNT"):
            got, r = csv_read(boq(heads))
            self.assertEqual(got, TWO, heads)
        forms = tabular._head_forms
        self.assertEqual(forms("UoM")[0], "uom")                       # split only before Upper+lower: UoM stays whole
        self.assertEqual(forms("MaterialCost")[0], "material cost")
        for w in ("MATERIALRATE", "Materialcost", "LABOURCOST", "UNITPRICE", "TOTALAMOUNT", "ALLINRATE", "unit_rate",
                  "Material Rate", "materialRates"):
            self.assertTrue(tabular._money_head(forms(w)), w)
        for w in ("Substrate", "Separate", "Corporate", "Accurate", "Concentrate", "Paramount", "Devalue", "Integrate",
                  "Description", "Material", "Item", "Crate", "Pirate", "Accost", "MaterialSubstrate"):
            self.assertFalse(tabular._money_head(forms(w)), w)
        hm = lambda h: {k: h[v] for k, v in tabular._header_map(h).items()}   # noqa: E731
        self.assertEqual(hm(["Item", "Description", "Unit Weight", "Qty", "Unit"])["unit"], "Unit")
        self.assertEqual(hm(["名称", "単位質量", "数量", "単位"])["unit"], "単位")
        self.assertEqual(hm(["名称", "数量", "単位重量", "単位"])["unit"], "単位")
        self.assertNotIn("unit", hm(["Description", "Qty", "Unit Rate", "Unit Weight"]))   # no unit column: said, not guessed
        self.assertEqual(hm(["Description", "Qty", "Units", "Unit Price"])["unit"], "Units")
        self.assertEqual(tabular._factor_cols(["名称", "長さ", "単重", "数量", "重量換算"]), [2])   # 単重 is a factor word

    def test_a_name_column_of_numbers_gives_way(self):
        # a rate column whose header names no money word in a known form (MATERIALCHARGE) holds numbers: the next name
        # column (Description) is the name
        got, r = csv_read("Ref,MATERIALCHARGE,Description,Qty,Unit\n1,110,Ready mixed concrete C30,120,m3\n"
                          "2,600,High yield steel reinforcement bars,14.5,t\n")
        self.assertEqual(got, TWO)
        # item codes in the only name column stay the name (no other column to take)
        hi, m = tabular._find_header([["Item", "Qty", "Unit"], ["1.1", "3", "m3"]])
        self.assertEqual(m["name"], 0)

    # --- pivot tables
    def test_pivot_table_cells_are_a_summary_not_a_second_bill(self):
        OK = {("m_concrete", "m3"): 150.0, ("m_rebar", "t"): 12.0}
        for kw in ({}, {"pages": 1}, {"data": 2}, {"pages": 1, "data": 2}, {"rel": False}):
            got, r = read(pivot_book({"ref": "A1:D4", "sheet": "明細"}, **kw))
            self.assertEqual(got, OK, kw)
            ex = [x for x in excluded(r, "m_concrete") if "ピボット" in x["reason"]]
            self.assertEqual(len(ex), 1, kw)
            self.assertIn("ピボット表", ex[0]["reason"])
            self.assertIn("明細", ex[0]["reason"])
            self.assertFalse(ex[0]["maybe"])                         # its source is read here: surely a copy
            self.assertTrue(any("ピボットテーブル" in w for w in r["warnings"]))
        # the source by a defined name or a table is resolved; an unknown source is refused as unchecked (maybe)
        got, r = read(pivot_book({"name": "元表"}, names=[("元表", "明細!$A$1:$D$4")]))
        self.assertEqual(got, OK)
        for src in ({"name": "無い名前"}, {"ref": "A1:D4"}, {"ref": "A1:D4", "sheet": "明細", "r:id": "rX"}, None):
            got, r = read(pivot_book(src))
            self.assertEqual(got, OK, src)
            ex = [x for x in excluded(r, "m_concrete") if "ピボット" in x["reason"]]
            self.assertTrue(ex and ex[0]["maybe"] and "確かめられない" in ex[0]["reason"], src)
        got, r = read(pivot_book({"ref": "A1:D4", "sheet": "明細"}, cache=False, rel=False))
        self.assertEqual(got, OK)
        self.assertTrue(excluded(r, "m_concrete")[0]["maybe"])
        # a pivot of a hidden sheet: its values are not read, so the pivot rows may belong (not silently added)
        got, r = read(pivot_book({"ref": "A1:D4", "sheet": "明細"}, hidden_source=True))
        self.assertEqual(got, {})
        self.assertEqual(left(r, "m_concrete").get("n_maybe"), 1)
        # a pivot whose place is not told: the whole sheet is unsure
        got, r = read(pivot_book({"ref": "A1:D4", "sheet": "明細"}, loc="nonsense"))
        self.assertEqual(got, OK)
        self.assertIn("場所が分からない", reasons(r))

    # --- a row's own parts and its dimensions
    def test_summed_per_type_columns_are_parts_whatever_their_header(self):
        for head3 in (("Unit A", "Unit B", "Unit C"), ("B1/1F", "2F/3F", "4F/RF"), ("1F", "2F", "3F"), ("Type A", "Type B", "Type C")):
            for qf in ("SUM(C2:E2)", "C2+D2+E2", "ROUND(SUM(C2:E2),1)"):
                for sf in ("SUM(明細!C2:E2)*1.05", "SUM(明細!C2:E2)", "明細!C2+明細!D2+明細!E2", "SUM(明細!C2:E2)*(1+$F$1)"):
                    got, r = read(floors(head3, qf, sf))
                    self.assertEqual(got, {("m_concrete", "m3"): 100.0}, (head3, qf, sf))
                    self.assertIn("別のシート（明細）の材料の行（2 行目）", reasons(r))

    def test_a_reused_dimension_of_another_row_is_not_a_copy(self):
        h = row(1, t("A1", "名称"), t("B1", "規格"), t("C1", "面積"), t("D1", "厚さ"), t("E1", "数量"), t("F1", "単位"))
        slab = h + row(2, t("A2", "スラブ コンクリート"), t("B2", "Fc24"), n("C2", 400), n("D2", 0.2), n("E2", 80, "C2*D2"), t("F2", "m3"))
        got, _ = read(xlsx([("数量", slab + row(3, t("A3", "土間コンクリート"), t("B3", "Fc24"), n("C3", 300),
                                                  n("E3", 60, "C3*$D$2"), t("F3", "m3")))]))
        self.assertEqual(got, {("m_concrete", "m3"): 140.0})
        en = row(1, t("A1", "Description"), t("B1", "Area"), t("C1", "Depth"), t("D1", "Qty"), t("E1", "Unit")) + \
            row(2, t("A2", "Concrete slab C30"), n("B2", 400), n("C2", 0.2), n("D2", 80, "B2*C2"), t("E2", "m3")) + \
            row(3, t("A3", "Concrete topping"), n("B3", 300), n("D3", 60, "B3*$C$2"), t("E3", "m3"))
        got, _ = read(xlsx([("BoQ", en)]))
        self.assertEqual(got, {("m_concrete", "m3"): 140.0})
        for tanju in ("単重", "重さ", ""):              # a factor word or not: the row's own product says it is a factor
            rb = row(1, t("A1", "名称"), t("B1", "規格"), t("C1", "長さ(m)"), t("D1", tanju), t("E1", "数量"), t("F1", "単位")) + \
                row(2, t("A2", "異形鉄筋"), t("B2", "D13 1F"), n("C2", 1000), n("D2", 0.995), n("E2", 0.995, "C2*D2/1000"), t("F2", "t")) + \
                row(3, t("A3", "異形鉄筋"), t("B3", "D13 2F"), n("C3", 800), n("E3", 0.796, "C3*$D$2/1000"), t("F3", "t"))
            got, _ = read(xlsx([("鉄筋", rb)]))
            self.assertAlmostEqual(got[("m_rebar", "t")], 1.791, msg=tanju)
            # a summary that recomputes the row from its length and unit mass is still a copy of it
            summ = row(1, t("A1", "名称"), t("B1", "数量"), t("C1", "単位")) + \
                row(2, t("A2", "異形鉄筋"), n("B2", 0.995, "鉄筋!C2*鉄筋!D2/1000"), t("C2", "t"))
            got, r = read(xlsx([("鉄筋", rb), ("集計", summ)]))
            self.assertAlmostEqual(got[("m_rebar", "t")], 1.791, msg=tanju)
            self.assertIn("別のシート（鉄筋）の材料の行（2 行目）", reasons(r))
        # still copies: the dimension summed alone, two numbers of the row (the product recomputed), a dimension of the
        # row together with another row's, and a cell the row's quantity sums
        for f, why in (("$D$2*1000", "summed"), ("$C$2*$D$2", "recomputed"), ("C3*$D$2*$D$4", "two rows"), ("C3+$C$2", "part")):
            rows = slab + row(3, t("A3", "土間コンクリート"), t("B3", "Fc24"), n("C3", 300), n("E3", 60, f), t("F3", "m3")) + \
                row(4, t("A4", "防水コンクリート"), t("B4", "Fc24"), n("C4", 10), n("D4", 0.1), n("E4", 1, "C4*D4"), t("F4", "m3"))
            got, r = read(xlsx([("数量", rows)]))
            self.assertEqual(got, {("m_concrete", "m3"): 81.0}, why)
            self.assertIn("同じシートのほかの材料の行", reasons(r), why)
        summ = row(1, t("A1", "名称"), t("B1", "数量"), t("C1", "単位")) + \
            row(2, t("A2", "コンクリート"), n("B2", 80, "数量!C2*数量!D2"), t("C2", "m3"))
        got, r = read(xlsx([("数量", slab), ("集計", summ)]))
        self.assertEqual(got, {("m_concrete", "m3"): 80.0})

    # --- lookups
    def test_a_lookup_keyed_on_the_bill_returns_a_rows_own_number(self):
        det = row(1, t("A1", "名称"), t("B1", "規格"), t("C1", "1F"), t("D1", "2F"), t("E1", "3F"), t("F1", "数量"), t("G1", "単位")) + \
            row(2, t("A2", "コンクリート"), t("B2", "Fc24"), n("C2", 40), n("D2", 30), n("E2", 30), n("F2", 100), t("G2", "m3"))
        for f in ('XLOOKUP("コンクリート",明細!A:A,明細!%s:%s)*(1+$F$1)',
                  'IFERROR(VLOOKUP("コンクリート",明細!$A$2:$E$9,%s,FALSE),0)*(1+$F$1)',
                  'INDEX(明細!%s:%s,MATCH("コンクリート",明細!A:A,0))*(1+$F$1)', 'XLOOKUP("Fc24",明細!B:B,明細!%s:%s)*(1+$F$1)'):
            summ = row(1, t("A1", "名称"), t("B1", "階"), t("C1", "数量"), t("D1", "単位"), t("E1", "割増率"), n("F1", 0.05))
            for r_, col in ((2, "C"), (3, "D"), (4, "E")):
                ff = f % ((col, col) if f.count("%s") == 2 else (str(ord(col) - 64),))
                summ += row(r_, t("A%d" % r_, "コンクリート"), t("B%d" % r_, "%dF" % (r_ - 1)), n("C%d" % r_, 40, ff), t("D%d" % r_, "m3"))
            got, r = read(xlsx([("明細", det), ("集計", summ)]))
            self.assertEqual(got, {("m_concrete", "m3"): 100.0}, f)
        summ = row(1, t("A1", "名称"), t("B1", "数量"), t("C1", "単位"), t("E1", "割増率"), n("F1", 0.05)) + \
            row(2, t("A2", "コンクリート"), n("B2", 105, '(INDEX(明細!C:C,MATCH("コンクリート",明細!A:A,0))+INDEX(明細!D:D,MATCH('
                                                     '"コンクリート",明細!A:A,0))+INDEX(明細!E:E,MATCH("コンクリート",明細!A:A,0)))*(1+$F$1)'),
                t("C2", "m3"))
        got, _ = read(xlsx([("明細", det), ("集計", summ)]))
        self.assertEqual(got, {("m_concrete", "m3"): 100.0})
        # unit masses looked up stay factors: from a 早見表 beside the bill, from a factor sheet, from the bill's own
        # rows by 規格 (each row's quantity looks its own unit mass up there)
        for f in ("E%d*VLOOKUP(B%d,$H$2:$I$3,2,0)/1000", "E%d*VLOOKUP(B%d,係数!$A$1:$B$2,2,0)/1000",
                  "E%d*INDEX($F$2:$F$3,MATCH(B%d,$B$2:$B$3,0))/1000"):
            rows = HDR.replace("</row>", t("E1", "長さ(m)") + t("F1", "重さ") + "</row>")
            rows += mrow(2, "異形鉄筋", "D10", n("C2", 0.56, f % (2, 2)), "t", n("E2", 1000), n("F2", 0.56), t("H2", "D10"), n("I2", 0.56))
            rows += mrow(3, "異形鉄筋", "D13", n("C3", 1.99, f % (3, 3)), "t", n("E3", 2000), n("F3", 0.995), t("H3", "D13"), n("I3", 0.995))
            fac = row(1, t("A1", "D10"), n("B1", 0.56)) + row(2, t("A2", "D13"), n("B2", 0.995))
            got, _ = read(xlsx([("鉄筋", rows), ("係数", fac)]))
            self.assertAlmostEqual(got[("m_rebar", "t")], 2.55, msg=f)

    # --- copies on another sheet
    def test_a_copy_of_another_material_is_sure_when_its_own_material_is_counted(self):
        det = HDR + mrow(2, "コンクリート", "Fc24", n("C2", 100), "m3") + mrow(3, "鉄筋", "SD345 D13", n("C3", 12), "t")
        est = row(1, t("A1", "名称"), t("B1", "規格"), t("C1", "数量"), t("D1", "単位"), t("E1", "鉄筋比"), n("F1", 0.12)) + \
            mrow(2, "鉄筋", "概算（コンクリート×鉄筋比）", n("C2", 12, "明細!C2*$F$1"), "t")
        got, r = read(xlsx([("明細", det), ("検算", est)]))
        self.assertEqual(got, {("m_concrete", "m3"): 100.0, ("m_rebar", "t"): 12.0})
        ex = r["evidence"]["m_rebar"]
        self.assertEqual(ex["n_maybe"], 0)
        self.assertIn("その材料は 明細 の 3 行目で数えている", ex["excluded"][0]["reason"])
        self.assertFalse(ex["excluded"][0]["maybe"])
        self.assertNotIn("足すべき行かもしれない", [p.note for p in r["proposals"] if p.field_id == "m_rebar"][0])
        # without a counted rebar row it may belong (the round-13 rule)
        got, r = read(xlsx([("明細", HDR + mrow(2, "コンクリート", "Fc24", n("C2", 100), "m3")), ("検算", est)]))
        self.assertEqual(left(r, "m_rebar").get("n_maybe"), 1)
        # foundation concrete and concrete are one material: a copy of it is surely not added
        fdn = row(1, t("A1", "区分"), t("B1", "名称"), t("C1", "規格"), t("D1", "数量"), t("E1", "単位")) + \
            row(2, t("A2", "基礎"), t("B2", "コンクリート"), t("C2", "Fc24"), n("D2", 50), t("E2", "m3")) + \
            row(3, t("A3", "基礎"), t("B3", "コンクリート"), t("C3", "Fc27"), n("D3", 30), t("E3", "m3"))
        summ = HDR + mrow(2, "コンクリート", "", n("C2", 80, "SUM(基礎!D2:D3)"), "m3")
        got, r = read(xlsx([("基礎", fdn), ("集計", summ)]))
        self.assertEqual(got, {("m_concrete_fdn", "m3"): 80.0})
        self.assertEqual(left(r, "m_concrete").get("n_maybe"), 0)
        self.assertIn("別のシート（基礎）の材料の行（2 行目）の数量を参照した値は足さない", reasons(r))

    def test_the_check_of_a_copy_on_another_sheet_is_bounded(self):
        # every row of 概算 copies all of 明細 many times over: the check reads each block once per material (bisection)
        N, M = 3000, 40
        det = HDR + "".join(mrow(i, "コンクリート", "Fc24", n("C%d" % i, 1), "m3") for i in range(2, N + 2))
        took = {}
        for K in (1, 60):
            f = "SUM(%s)*0.12" % ",".join(["明細!C:C"] * K)
            est = HDR + "".join(mrow(i, "鉄筋", "SD345", n("C%d" % i, 1, f), "t") for i in range(2, M + 2))
            data = xlsx([("明細", det), ("概算", est)])
            t0 = time.perf_counter()
            got, r = read(data)
            took[K] = time.perf_counter() - t0
            self.assertEqual(got, {("m_concrete", "m3"): float(N)})
            self.assertEqual(left(r, "m_rebar").get("n_excluded"), M)
        # 60 copies of the column cost about what one does (round 13: 12 times as much, growing as rows × blocks × rows)
        self.assertLess(took[60], 3 * took[1] + 0.5, took)
        f = "SUM(%s)*0.12" % ",".join(["明細!C:C"] * 60)
        # when the budget runs out the answer is the conservative one (a copy of that sheet's own material)
        cells = documents._Cells({"cells": {"概算": {2: {2: (f, 0, False, 0)}}}, "sheet_names": {"概算": "概算", "明細": "明細"}})
        cells.targets["明細"] = [2]
        cells.left = 0
        self.assertTrue(cells.reaches_same("概算", 2, 2, "m_rebar", {("明細", 2): "m_concrete"}))


if __name__ == "__main__":
    unittest.main()
