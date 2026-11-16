"""Round 10 of the independent review: the importer (what a quantity formula reaches, classification, evidence)."""
from __future__ import annotations

import base64
import io
import os
import sys
import tempfile
import time
import unittest
import zipfile

sys.dont_write_bytecode = True
os.environ.setdefault("WLCSTUDIO_OFFLINE", "1")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from wlcstudio import documents, project as project_mod  # noqa: E402
from wlcstudio.importers import pdf as pdf_mod, tabular  # noqa: E402

NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
RNS = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def t(ref, text):
    return '<c r="%s" t="inlineStr"><is><t>%s</t></is></c>' % (ref, _esc(text))


def n(ref, v, f=None, fattr=""):
    return '<c r="%s">%s%s</c>' % (ref, "<f%s>%s</f>" % (fattr, _esc(f)) if f is not None else "",
                                   "<v>%s</v>" % v if v is not None else "")


def row(r, *cells, attrs=""):
    return '<row r="%d"%s>%s</row>' % (r, attrs, "".join(cells))


HDR = row(1, t("A1", "名称"), t("B1", "規格"), t("C1", "数量"), t("D1", "単位"))


def mrow(r, name, spec, qty_cell, unit, *extra, attrs=""):
    return row(r, t("A%d" % r, name), t("B%d" % r, spec) if spec else "", qty_cell, t("D%d" % r, unit), *extra, attrs=attrs)


DETAIL = HDR + mrow(2, "コンクリート", "Fc24", n("C2", 100), "m3") + mrow(3, "コンクリート", "Fc27", n("C3", 50), "m3") + \
    mrow(4, "鉄筋", "SD345", n("C4", 12), "t")


def xlsx(sheets, names=(), states=None, pre=None, tables=None):
    """sheets = [(name, rows xml)]; names = [(name, text, localSheetId or None)]; states = {sheet: hidden};
    pre = {sheet: xml before sheetData (cols)}; tables = {sheet: [(table name, ref, [column names])]}."""
    states, pre, tables = states or {}, pre or {}, tables or {}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        sh = "".join('<sheet name="%s" sheetId="%d" r:id="rId%d"%s/>' % (_esc(nm), i + 1, i + 1,
                     ' state="%s"' % states[nm] if nm in states else "") for i, (nm, _) in enumerate(sheets))
        dn = "".join('<definedName name="%s"%s>%s</definedName>' % (_esc(a), "" if lid is None else ' localSheetId="%d"' % lid, _esc(b))
                     for a, b, lid in names)
        z.writestr("xl/workbook.xml", "<workbook %s %s><sheets>%s</sheets>%s</workbook>"
                   % (NS, RNS, sh, "<definedNames>%s</definedNames>" % dn if dn else ""))
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">%s'
                   '</Relationships>' % "".join('<Relationship Id="rId%d" Target="worksheets/sheet%d.xml"/>' % (i + 1, i + 1)
                                                for i in range(len(sheets))))
        k = 0
        for i, (nm, rows) in enumerate(sheets):
            parts = ""
            if nm in tables:
                rels = []
                for tn, ref, cols in tables[nm]:
                    k += 1
                    z.writestr("xl/tables/table%d.xml" % k, '<table %s id="%d" name="%s" displayName="%s" ref="%s" headerRowCount="1">'
                               '<tableColumns count="%d">%s</tableColumns></table>'
                               % (NS, k, tn, tn, ref, len(cols), "".join('<tableColumn id="%d" name="%s"/>' % (j + 1, _esc(c))
                                                                         for j, c in enumerate(cols))))
                    rels.append('<Relationship Id="rT%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/table" '
                                'Target="../tables/table%d.xml"/>' % (k, k))
                z.writestr("xl/worksheets/_rels/sheet%d.xml.rels" % (i + 1),
                           '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">%s</Relationships>' % "".join(rels))
                parts = '<tableParts count="%d">%s</tableParts>' % (len(rels), "".join('<tablePart r:id="rT%d"/>' % (k - len(rels) + j + 1)
                                                                                       for j in range(len(rels))))
            z.writestr("xl/worksheets/sheet%d.xml" % (i + 1), "<worksheet %s %s>%s<sheetData>%s</sheetData>%s</worksheet>"
                       % (NS, RNS, pre.get(nm, ""), rows, parts))
    return buf.getvalue()


def read(data, name="x.xlsx"):
    r = documents.read(name, base64.b64encode(data).decode(), "d")
    return {(p.field_id, p.unit): p.value for p in r["proposals"]}, r


def csv_read(text):
    return read(text.encode("utf-8"), "x.csv")


def reasons(r):
    return " ".join(u["reason"] for u in r["unused"])


class TenthRoundImporterTests(unittest.TestCase):
    OK = {("m_concrete", "m3"): 150.0, ("m_rebar", "t"): 12.0}

    # --- copies through cells whose values are not read
    def test_copies_through_hidden_helpers_are_found(self):
        summ = HDR + mrow(2, "コンクリート", "Fc24", n("C2", 100, "計算!A1"), "m3")
        got, r = read(xlsx([("明細", DETAIL), ("集計", summ), ("計算", row(1, n("A1", 100, "明細!C2")))], states={"計算": "hidden"}))
        self.assertEqual(got, self.OK)
        summ = HDR + mrow(2, "コンクリート", "Fc24", n("C2", 100, "H2"), "m3", n("H2", 100, "明細!C2"))
        got, _ = read(xlsx([("明細", DETAIL), ("集計", summ)], pre={"集計": '<cols><col min="8" max="8" hidden="1"/></cols>'}))
        self.assertEqual(got, self.OK)
        summ = HDR + mrow(2, "コンクリート", "Fc24", n("C2", 100, "Z50"), "m3") + row(50, n("Z50", 100, "明細!C2"), attrs=' hidden="1"')
        got, _ = read(xlsx([("明細", DETAIL), ("集計", summ)]))
        self.assertEqual(got, self.OK)
        # a filled-down formula whose first row was hidden later: the master is still in the file
        rows = HDR + "".join(mrow(i, "コンクリート", "Fc24", n("C%d" % i, 10, "E%d*F%d" % (i, i) if i == 2 else "",
                                                                    ' t="shared" ref="C2:C6" si="0"' if i == 2 else ' t="shared" si="0"'),
                                  "m3", n("E%d" % i, 2), n("F%d" % i, 5), attrs=' hidden="1"' if i == 2 else "") for i in range(2, 7))
        got, r = read(xlsx([("明細", rows)]))
        self.assertEqual(got, {("m_concrete", "m3"): 40.0})

    def test_array_formulas_spill_copies(self):
        summ = HDR + row(2, n("A2", None, "_xlfn._xlws.SORT(明細!A2:D4)", ' t="array" ref="A2:D4"'), t("B2", "Fc24"), n("C2", 100), t("D2", "m3")) + \
            row(3, t("A3", "コンクリート"), t("B3", "Fc27"), n("C3", 50), t("D3", "m3")) + row(4, t("A4", "鉄筋"), t("B4", "SD345"), n("C4", 12), t("D4", "t"))
        summ = summ.replace('<c r="A2"><f', '<c r="A2" t="str"><f').replace("</f></c>", "</f><v>コンクリート</v></c>", 1)
        got, _ = read(xlsx([("明細", DETAIL), ("集計", summ)]))
        self.assertEqual(got, self.OK)
        cse = HDR + mrow(2, "コンクリート", "Fc24", n("C2", 100, "明細!C2:C4", ' t="array" ref="C2:C4"'), "m3") + \
            mrow(3, "コンクリート", "Fc27", n("C3", 50), "m3") + mrow(4, "鉄筋", "SD345", n("C4", 12), "t")
        got, _ = read(xlsx([("明細", DETAIL), ("集計", cse)]))
        self.assertEqual(got, self.OK)

    # --- names and tables
    def test_tables_names_scopes_and_name_ranges(self):
        tab = {"明細": [("T明細", "A1:D4", ["名称", "規格", "数量", "単位"])]}
        summ = HDR + mrow(2, "コンクリート", "Fc24", n("C2", 100, 'VLOOKUP("Fc24",T明細,3,FALSE)'), "m3") + \
            mrow(3, "鉄筋", "D13", n("C3", 12, "INDEX(T明細[数量],3)"), "t")
        got, _ = read(xlsx([("明細", DETAIL), ("集計", summ)], tables=tab))
        self.assertEqual(got, self.OK)
        # a per-row calculation inside a table: [@列] is the row itself, not a copy
        own = HDR.replace("</row>", t("E1", "長さ") + "</row>") + "".join(
            mrow(i, "異形鉄筋", "D13", n("C%d" % i, i, "[@長さ]*0.001"), "t", n("E%d" % i, i * 1000)) for i in (2, 3, 4))
        got, _ = read(xlsx([("鉄筋", own)], tables={"鉄筋": [("T鉄筋", "A1:E4", ["名称", "規格", "数量", "単位", "長さ"])]}))
        self.assertEqual(got, {("m_rebar", "t"): 9.0})
        # a name defined after 2,000 others; an undefined name is not ignored
        junk = [("_旧印刷範囲%04d" % i, "#REF!$A$1:$B$2", None) for i in range(2000)]
        summ = HDR + mrow(2, "コンクリート", "Fc24", n("C2", 100, "数量_Fc24"), "m3")
        got, _ = read(xlsx([("明細", DETAIL), ("集計", summ)], names=junk + [("数量_Fc24", "明細!$C$2", None)]))
        self.assertEqual(got, self.OK)
        got, r = read(xlsx([("明細", DETAIL), ("集計", summ)]))
        self.assertEqual(got, self.OK)
        self.assertIn("名前 数量_FC24 の参照先が分からない", reasons(r))
        # sheet-scoped names: 集計's own QTY is used on 集計
        summ = HDR + mrow(2, "コンクリート", "Fc24", n("C2", 100, "QTY"), "m3")
        for nm in ([("QTY", "明細!$C$2", 1), ("QTY", "メモ!$A$1", 2)], [("QTY", "メモ!$A$1", None), ("QTY", "明細!$C$2", 1)]):
            got, _ = read(xlsx([("明細", DETAIL), ("集計", summ), ("メモ", row(1, n("A1", 1)))], names=nm))
            self.assertEqual(got, self.OK, nm)
        # a range between two names covers the block between their cells
        summ = HDR + mrow(2, "コンクリート", "全数", n("C2", 150, "SUM(開始:終了)"), "m3")
        got, _ = read(xlsx([("明細", DETAIL), ("集計", summ)], names=[("開始", "明細!$C$1", None), ("終了", "明細!$C$5", None)]))
        self.assertEqual(got, self.OK)
        # a computed end and another workbook are refused with their own reasons
        for f, why in (("SUM(明細!C2:INDEX(明細!C:C,4))", "範囲の端が数式で決まる"), ("[1]明細!C2", "別のブック")):
            got, r = read(xlsx([("明細", DETAIL), ("集計", HDR + mrow(2, "コンクリート", "Fc24", n("C2", 150, f), "m3"))]))
            self.assertEqual(got, self.OK, f)
            self.assertIn(why, reasons(r), f)

    # --- the walk: every cell once per document
    def test_follow_budget_is_per_cell_and_walks_are_kept(self):
        take = row(1, t("A1", "部位"), t("B1", "記号"), t("F1", "体積")) + "".join(
            row(i, t("A%d" % i, "柱"), t("B%d" % i, "C%d" % (i % 60)), n("C%d" % i, 1), n("D%d" % i, 1), n("E%d" % i, 0.6),
                n("F%d" % i, 0.6, "C%d*D%d*E%d" % (i, i, i))) for i in range(2, 2002))
        bill = HDR + "".join(mrow(i, "コンクリート Fc24", "C%d" % ((i - 2) % 60), n("C%d" % i, 20, "SUMIF(拾い!$B:$B,B%d,拾い!$F:$F)" % i), "m3")
                             for i in range(2, 62))
        t0 = time.time()
        got, r = read(xlsx([("明細", bill), ("拾い", take)]))
        self.assertEqual(got, {("m_concrete", "m3"): 1200.0})
        self.assertLess(time.time() - t0, 10)
        # a running total 30 rows deep reaches no material row
        run = "".join(row(i, n("F%d" % i, i, "F%d+1" % (i - 1) if i > 1 else None)) for i in range(1, 31))
        got, _ = read(xlsx([("内訳", HDR + mrow(2, "コンクリート", "Fc24", n("C2", 30, "拾い!F30"), "m3")), ("拾い", run)]))
        self.assertEqual(got, {("m_concrete", "m3"): 30.0})

    def test_crafted_workbooks_stay_fast(self):
        N = 16000
        def col(j):
            s = ""
            j += 1
            while j:
                j, rem = divmod(j - 1, 26)
                s = chr(65 + rem) + s
            return s
        r3 = '<row r="3">%s</row>' % "".join('<c r="%s3"><f>SUM($4:$4)</f><v>0</v></c>' % col(j) for j in range(4, 4 + N))
        r4 = '<row r="4">%s</row>' % "".join('<c r="%s4"><f>1+0</f><v>1</v></c>' % col(j) for j in range(4, 4 + N))
        rows = HDR + mrow(2, "コンクリート", "Fc24", n("C2", 1, "SUM($3:$3)"), "m3") + r3 + r4 + \
            "".join(mrow(i, "コンクリート", "Fc24", n("C%d" % i, 1, "SUM($3:$3)"), "m3") for i in (5, 6, 7))
        t0 = time.time()
        read(xlsx([("明細", rows)]))
        self.assertLess(time.time() - t0, 10)
        # hidden or repeated cell elements count against the cell limit
        hid = '<cols><col min="2" max="16384" hidden="1"/></cols>'
        big = "".join('<row r="%d"><c r="A%d"><v>1</v></c>%s</row>' % (i, i, "<c/>" * 8000) for i in range(1, 130))
        with self.assertRaises(ValueError) as cm:
            read(xlsx([("a", big), ("b", big)], pre={"a": hid, "b": hid}))
        self.assertIn("セルが多すぎる", str(cm.exception))
        dup = "".join('<row r="%d">%s</row>' % (i, '<c r="Z%d"/>' % i * 2000) for i in range(1, 520))
        with self.assertRaises(ValueError):
            read(xlsx([("a", dup)]))
        # names of many short parts: only the first parts are looked at for the head
        body = "名称,数量,単位\n" + "".join('"%d%s",1,m3\n' % (i, ",x" * 140) for i in range(4000))
        t0 = time.time()
        csv_read(body)
        self.assertLess(time.time() - t0, 10)

    # --- what is a material, what is work
    def test_classification_of_round_10_names(self):
        f = documents._field_for
        for name, want in (("グラスウールボード 32K 50mm", "m_insulation"), ("ロックウールボード", "m_insulation"), ("断熱ボード", "m_insulation"),
                           ("EPS insulation board 50mm", "m_insulation"), ("Mineral wool board", "m_insulation"),
                           ("Glass wool board", "m_insulation"), ("石膏ボード 12.5mm", "m_board"), ("アルミ断熱サッシ", "m_aluminium"),
                           ("アルミ断熱パネル", "m_aluminium"), ("ALC断熱パネル", "m_masonry"), ("断熱アルミサッシ", "m_aluminium"),
                           ("断熱サッシ", None), ("砂利地業（土間コンクリート下）", None), ("砕石地業（基礎コンクリート下）", None),
                           ("Hardcore under concrete slab", None), ("Granular fill beneath concrete ground slab", None),
                           ("押出法ポリスチレンフォーム 土間コンクリート下", "m_insulation"), ("Insulation between timber joists", "m_insulation"),
                           ("Rockwool insulation between steel studs", "m_insulation"), ("Sand for mortar", None),
                           ("High yield bars for concrete", "m_rebar"), ("Reinforcement steel bars Grade 60", "m_rebar"),
                           ("High yield steel bars", "m_rebar"), ("Mild steel bars", "m_rebar"), ("Deformed steel bars", "m_rebar"),
                           ("TMT steel bars Fe500", "m_rebar"), ("Reinforcement steel (Fe 500)", "m_rebar"), ("Rebar steel Grade 60", "m_rebar"),
                           ("Tor steel", "m_rebar"), ("Structural steel S355", "m_steel"), ("主筋 D22", "m_rebar"), ("帯筋 D10", "m_rebar"),
                           ("あばら筋", "m_rebar"), ("スラブ筋", "m_rebar"), ("鉄骨下地", "m_steel"),
                           ("Supply and installation of plasterboard", "m_board"), ("エポキシ樹脂塗装鉄筋", "m_rebar")):
            self.assertEqual(f(name), want, name)
        w = documents._is_work
        for name in ("鉄骨 搬入", "鉄骨 荷揚げ", "鉄骨 現場溶接", "鉄筋 ガス圧接", "デッキプレート敷込み", "床コンクリート金ごて仕上",
                     "Power float finish to slab", "Place concrete in slabs", "Hoist and install steelwork", "Laying concrete",
                     "Vibrating concrete", "Unloading reinforcement", "Welding of steel", "Assembly of steelwork", "Installing structural steel"):
            self.assertTrue(w(name), name)
        for name in ("鉄骨 ; 製作・建方共", "異形鉄筋 SD345 ; 加工組立共", "普通コンクリート Fc24 ; ポンプ打設共", "鉄骨 製作建方込み",
                     "鉄骨 製作・建方とも", "異形鉄筋 組立加工共", "鉄骨（建方別途）", "鉄筋 SD345 D19 運搬費込", "生コンクリート 打設費別",
                     "Ready mixed concrete C30/37, excluding placing", "Reinforcement excluding fixing", "Fabricated steelwork",
                     "Welded mesh A193", "Float glass 6mm", "打放しコンクリート Fc24", "床タイル張り"):
            self.assertFalse(w(name), name)
        for name in ("既存コンクリート撤去", "コンクリート殻処分", "Demolition of existing concrete slab", "Disposal of concrete rubble",
                     "Break out existing slab"):
            self.assertTrue(documents._is_demolition(name), name)

    def test_round_10_bills(self):
        got, r = csv_read("名称,数量,単位\n土間コンクリート,30,m3\n砂利地業（土間コンクリート下）,9,m3\n既存コンクリート撤去,30,m3\n"
                          "コンクリート殻処分,30,m3\n鉄骨 SN490B,20,t\n鉄骨 搬入,20,t\n鉄骨 現場溶接,20,t\n既存鉄骨撤去,8,t\n")
        self.assertEqual(got, {("m_concrete", "m3"): 30.0, ("m_steel", "t"): 20.0})
        self.assertIn("撤去・解体・処分", reasons(r))
        got, _ = csv_read("名称,規格,数量,単位\n鉄骨,製作・建方共,120,t\n異形鉄筋 SD345,加工組立共,80,t\n普通コンクリート Fc24,ポンプ打設共,900,m3\n"
                          "普通コンクリート Fc21,打設共,50,m3\n鉄骨 製作建方込み,,10,t\n")
        self.assertEqual(got, {("m_steel", "t"): 130.0, ("m_rebar", "t"): 80.0, ("m_concrete", "m3"): 950.0})
        got, _ = csv_read("名称,数量,単位\n石膏ボード 12.5mm,3000,m2\nグラスウールボード 32K 50mm,1500,m2\nアルミ断熱サッシ,200,m2\n"
                          "EPS insulation board 50mm,400,m2\n")
        self.assertEqual(got, {("m_board", "m2"): 3000.0, ("m_insulation", "m2"): 1900.0})
        got, _ = csv_read("名称,数量,単位\nConcrete C30/37 in slabs,120,m3\nHigh yield bars for concrete,12,t\n")
        self.assertEqual(got, {("m_concrete", "m3"): 120.0, ("m_rebar", "t"): 12.0})

    def test_mixed_dimensions_tie_is_not_proposed(self):
        got, r = csv_read("名称,数量,単位\nコンクリート,120,m3\nコンクリート 換算,288,t\n")
        self.assertEqual(got, {})
        self.assertIn("単位が混ざっていて", reasons(r))

    # --- legitimate rows are not copies
    def test_factors_in_material_rows_are_not_copies(self):
        head = HDR.replace("</row>", t("E1", "長さ(m)") + t("F1", "単位質量(kg/m)") + "</row>")
        rows = head + mrow(2, "異形鉄筋", "D13", n("C2", 0.995, "E2*F2/1000"), "t", n("E2", 1000), n("F2", 0.995)) + "".join(
            mrow(i, "異形鉄筋", "D13", n("C%d" % i, 0.995 * (i - 1), "E%d*$F$2/1000" % i), "t", n("E%d" % i, 1000 * (i - 1))) for i in (3, 4, 5))
        got, _ = read(xlsx([("鉄筋", rows)]))
        self.assertAlmostEqual(got[("m_rebar", "t")], 9.95)
        side = HDR.replace("</row>", t("E1", "長さ") + t("J1", "径") + t("K1", "単位重量") + "</row>") + "".join(
            mrow(i, "異形鉄筋", d, n("C%d" % i, 1, "E%d*VLOOKUP(B%d,$J$2:$K$4,2,FALSE)/1000" % (i, i)), "t", n("E%d" % i, 1000),
                 t("J%d" % i, d), n("K%d" % i, 1)) for i, d in ((2, "D10"), (3, "D13"), (4, "D16")))
        got, _ = read(xlsx([("明細", side)]))
        self.assertEqual(got, {("m_rebar", "t"): 3.0})
        conv = HDR + mrow(2, "モルタル塗り 床", "t=30", n("C2", 500), "m2") + mrow(3, "モルタル", "", n("C3", 31.5, "C2*0.03*2.1"), "t")
        got, _ = read(xlsx([("左官", conv)]))
        self.assertEqual(got, {("m_mortar", "t"): 31.5})
        # a total kept in a calculation column is still a copy
        calc = HDR + "".join(mrow(i, "普通コンクリート", "", n("C%d" % i, q, "ROUND(F%d,1)" % i), "m3", fx) for i, q, fx in
                             ((2, 100, n("F2", 100)), (3, 50, n("F3", 50)), (4, 150, n("F4", 150, "SUM(F2:F3)"))))
        got, _ = read(xlsx([("内訳", calc)]))
        self.assertEqual(got, {("m_concrete", "m3"): 150.0})

    # --- evidence on the candidate
    def test_candidate_carries_its_rows_and_left_out_rows(self):
        got, r = csv_read("名称,数量,単位\nコンクリート Fc24,100,m3\nコンクリート Fc27,50,m3\nコンクリート 計,150,m3\nコンクリート打設,150,m3\n"
                          "コンクリート,一式,m3\n")
        ev = r["evidence"]["m_concrete"]
        self.assertEqual(ev["n_rows"], 2)
        self.assertEqual([x["name"] for x in ev["rows"]], ["コンクリート Fc24", "コンクリート Fc27"])
        self.assertEqual(ev["n_excluded"], 3)
        self.assertEqual(ev["n_maybe"], 2)          # the work row and the row without a number; not the total
        self.assertIn("足さなかった行 3 行。うち 2 行は足すべき行かもしれない", r["proposals"][0].note)   # (round 11 wording)
        with tempfile.TemporaryDirectory() as td:
            P = project_mod.Projects(os.path.join(td, "p.sqlite3"))
            pid = P.create("x", "RC")
            P.propose(pid, r["proposals"][0], "document:d", extra=ev)
            c = P.candidates(pid, "m_concrete")[0]
            self.assertEqual(c["n_maybe"], 2)
            self.assertEqual(len(c["rows"]), 2)
            v = P.accept(pid, "m_concrete", cid=c["id"])
            self.assertEqual(v.value, 150.0)
            self.assertFalse(hasattr(v, "rows"))
            P.db.close()

    # --- PDF
    @unittest.skipUnless(pdf_mod.available(), "pdftotext is not installed")
    def test_pdf_two_columns_item_numbers_and_floors(self):
        try:
            from tests.test_wlcstudio import _pdf      # python3 -m unittest discover -s tests -t . (README)
        except ImportError:
            from test_wlcstudio import _pdf            # discover -s tests
        got = documents.read("s.pdf", base64.b64encode(_pdf(["Rebar D13   1.2 t      Concrete C30   120 m3",
                                                              "1   Concrete Fc24   80 m3", "3F slab concrete   45 m3"])).decode(), "d")
        vals = sorted((p.field_id, p.value) for p in got["proposals"])
        self.assertEqual(vals, [("m_concrete", 45.0), ("m_concrete", 80.0), ("m_concrete", 120.0), ("m_rebar", 1.2)])


if __name__ == "__main__":
    unittest.main()
