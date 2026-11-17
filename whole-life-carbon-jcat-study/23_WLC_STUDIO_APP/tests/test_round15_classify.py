"""Round 15 of the independent review: the classification of quantity rows (an inclusive word reaches only its own
part; 撤去後 新設 is the new material only when nothing else follows; a part after an excluding word gives no head;
space-justified Japanese text; the renovation status and removal names of IFC elements; a negated or given-away supply
word; scrap rows; price notes after 控除 and okurigana after a labour word)."""
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
from wlcstudio.importers import ifc  # noqa: E402

try:
    from tests.test_round10_importer import csv_read, n, read, row, t, xlsx  # noqa: E402
    from tests.test_wlcstudio import _pdf  # noqa: E402
except ImportError:
    from test_round10_importer import csv_read, n, read, row, t, xlsx  # noqa: E402
    from test_wlcstudio import _pdf  # noqa: E402


def cls(name, spec="", unit="m2"):
    return documents._row_class(documents._Prep(), {"name": name, "specification": spec, "division": "", "unit": unit})


def excluded(r):
    """[(name, quantity, reason head, maybe)] of the rows left out, on candidates and in the summary."""
    out = []
    for ev in list(r["evidence"].values()) + list(r.get("left_out", {}).values()):
        out += [(x["name"], x.get("quantity"), x["reason"][:12], x["maybe"]) for x in ev["excluded"]]
    return sorted(out)


def pdf_read(lines):
    r = documents.read("p.pdf", base64.b64encode(_pdf(lines)).decode(), "d")
    return sorted((p.field_id, p.value) for p in r["proposals"]), r


def _esc(s):
    return "".join(c if ord(c) < 128 else "\\X2\\%04X\\X0\\" % ord(c) for c in s)


def ifc_text(elements, schema="IFC4"):
    """elements: (type, name, material, quantity kind, value, status value or None, property entity, pset name)."""
    lines = ["ISO-10303-21;", "HEADER;FILE_SCHEMA(('%s'));ENDSEC;" % schema, "DATA;"]
    for k, (typ, nm, mat, qk, qv, st, ent, ps) in enumerate(elements):
        b = 100 * (k + 1)
        qn = {"VOLUME": "NetVolume", "AREA": "NetArea", "WEIGHT": "NetWeight"}[qk]
        lines += ["#%d=%s('g%d',$,'%s',$,$,$,$,$);" % (b, typ, k, _esc(nm)),
                  "#%d=IFCQUANTITY%s('%s',$,$,%s,$);" % (b + 1, qk, qn, qv),
                  "#%d=IFCELEMENTQUANTITY('q%d',$,'Qto',$,$,(#%d));" % (b + 2, k, b + 1),
                  "#%d=IFCRELDEFINESBYPROPERTIES('r%d',$,$,$,(#%d),#%d);" % (b + 3, k, b, b + 2),
                  "#%d=IFCMATERIAL('%s',$,$);" % (b + 4, mat),
                  "#%d=IFCRELASSOCIATESMATERIAL('m%d',$,$,$,(#%d),#%d);" % (b + 5, k, b, b + 4)]
        if st is not None:
            val = ("(IFCLABEL('%s'))" if ent == "IFCPROPERTYENUMERATEDVALUE" else "IFCLABEL('%s')") % st
            lines += ["#%d=%s('Status',$,%s,$);" % (b + 6, ent, val),
                      "#%d=IFCPROPERTYSET('p%d',$,'%s',$,(#%d));" % (b + 7, k, ps, b + 6),
                      "#%d=IFCRELDEFINESBYPROPERTIES('s%d',$,$,$,(#%d),#%d);" % (b + 8, k, b, b + 7)]
    lines += ["ENDSEC;", "END-ISO-10303-21;"]
    return "\n".join(lines) + "\n"


class FifteenthRoundClassificationTests(unittest.TestCase):
    # --- 1. an inclusive word (incl., inc., including) reaches only the part that follows it (attacks 0)
    def test_incl_reaches_only_its_own_part(self):
        got, r = csv_read("Description,Qty,Unit\nPlasterboard 12.5mm; supply,500,m2\n\"Plasterboard 12.5mm incl. screws; fix\",500,m2\n"
                          "High yield reinforcement bars,30,t\n\"Reinforcement incl. tying wire; fix\",30,t\nBlockwork 100mm,800,m2\n"
                          "\"Blockwork 100mm incl. mortar; labour\",800,m2\n")
        self.assertEqual(got, {("m_board", "m2"): 500.0, ("m_rebar", "t"): 30.0, ("m_masonry", "m2"): 800.0})
        self.assertEqual(sum(1 for x in excluded(r) if x[3] and x[2] == documents.R_WORK[:12]), 3)
        for nm in ("Structural steelwork incl. bolts; erect", "Concrete C30/37 incl. additives; place and compact",
                   "Insulation 100mm incl. tape; lay", "Blockwork 100mm incl. mortar (labour)", "Blockwork 100mm incl. mortar - labour",
                   "Plasterboard 12.5mm incl. screws: install", "Plasterboard 12.5mm including screws; labour",
                   "Structural steelwork inc. bolts; erection and plumbing"):
            self.assertTrue(documents._is_work(nm), nm)
        # within its own part the inclusive word still reaches the work words (14 回目)
        for nm in ("Ready mixed concrete C30/37 incl. cube testing", "Concrete C30 Incl. placing and compacting",
                   "Concrete C30 including placing and compacting", "Ready mixed concrete; including placing",
                   "Concrete C30 incl. pump-placing"):
            self.assertFalse(documents._is_work(nm), nm)
        # the PDF path reads the same way
        got, _ = pdf_read(["Plasterboard 12.5mm incl. screws; fix   500 m2", "Reinforcement incl. tying wire; fix   12 t",
                           "Plasterboard 12.5mm   300 m2"])
        self.assertEqual(got, [("m_board", 300.0)])
        # … and so does the note of a spelled including on a removal word (15 回目)
        self.assertEqual(documents._demolish(documents._prep("Floor tiles including adhesive; take up and dispose")),
                         documents.MAYBE)
        self.assertFalse(documents._is_demolition("In situ concrete C30, including disposal"))
        # a line break in the cell (Alt+Enter) and a full stop that ends a sentence end the reach too (15 回目の攻撃)
        rows = [("Plasterboard 12.5mm; supply", 500, "m2"), ("Plasterboard 12.5mm incl. screws\nFix", 500, "m2"),
                ("High yield reinforcement bars", 30, "t"), ("Reinforcement incl. tying wire.\nFix", 30, "t"),
                ("Blockwork 100mm", 800, "m2"), ("Blockwork 100mm incl. mortar. Labour", 800, "m2")]
        x = row(1, t("A1", "Description"), t("B1", "Qty"), t("C1", "Unit"))
        for i, (nm, q, u) in enumerate(rows, 2):
            x += row(i, t("A%d" % i, nm), n("B%d" % i, q), t("C%d" % i, u))
        got, r = read(xlsx([("BoQ", x)]))
        self.assertEqual(got, {("m_board", "m2"): 500.0, ("m_rebar", "t"): 30.0, ("m_masonry", "m2"): 800.0})
        self.assertEqual(sorted((x[1], x[3]) for x in excluded(r) if x[2] == documents.R_WORK[:12]),
                         [(30.0, True), (500.0, True), (800.0, True)])
        got, _ = pdf_read(["Plasterboard 12.5mm incl. screws. Fix   500 m2", "Plasterboard 12.5mm   300 m2"])
        self.assertEqual(got, [("m_board", 300.0)])
        # (the dot of an abbreviation does not end it; and, &, / stay within it)
        for nm in ("Concrete C30 incl. approx. 5% waste and placing", "Concrete C30 incl. no. 3 pours and placing",
                   "Plasterboard 12.5mm incl. screws and fixing", "Plasterboard 12.5mm incl. screws & fixing",
                   "Plasterboard 12.5mm incl. screws / fixing", "Concrete C30 Incl. placing and compacting"):
            self.assertFalse(documents._is_work(nm), nm)

    # --- 2. 撤去後 新設 is the new material only when nothing but listed words follow it (attacks 1)
    def test_removal_then_new_installation_with_any_other_word_stays_removal(self):
        got, r = csv_read("名称,摘要,数量,単位\n石膏ボード,t12.5 既存撤去後 新設 次項,500,m2\n石膏ボード,t12.5 新設,500,m2\n"
                          "ビニル床タイル,既存撤去後新設 他工事,300,m2\nグラスウール,t100 既存撤去後 新規 B工事,200,m2\n")
        self.assertEqual(got, {("m_board", "m2"): 500.0})
        self.assertEqual(sorted((x[1], x[2], x[3]) for x in excluded(r)),
                         [(200.0, documents.R_DEMOLISH_MAYBE[:12], True), (300.0, documents.R_DEMOLISH_MAYBE[:12], True),
                          (500.0, documents.R_DEMOLISH_MAYBE[:12], True)])
        for nxt in ("他工事", "他工事による", "※他工事", "(他工事)", "B工事", "[B工事]", "C工事", "テナント工事", "次項", "(次項)", "次頁",
                    "下記", "No.12", "No12", "施主", "支給品", "他社", "未定", "しない", "計上せず", "未計上", "見積除外", "×", "-", "0",
                    "※別途", "他", "GL工法", "12.5", "工事"):
            self.assertEqual(cls("石膏ボード", "t12.5 既存撤去後 新設 " + nxt)["demolish"], documents.MAYBE, nxt)
        # a name marked as what is there stays removal
        for name in ("在来石膏ボード", "旧石膏ボード", "現況石膏ボード", "石膏ボード 現状"):
            self.assertEqual(cls(name, "撤去後 新設")["demolish"], documents.MAYBE, name)
        # nothing, an attached note, a size or grade, a disposal price note, or a listed longer form: the new material
        for spec in ("既存撤去後 新設", "既存撤去後 新設共", "既存撤去後 新設 共", "既存撤去後 新設 t12.5", "既存撤去後 新設 Fc24",
                     "既存撤去後 新設 3種b", "既存撤去後 新設 12.5mm", "既存撤去後 新設 処分共", "既存撤去後 新設（t12.5）",
                     "既存撤去の上 新規張り", "既存撤去の上 新規貼り", "既存撤去の上 新規施工", "既存撤去の上 新規設置",
                     "既存撤去の上 新規取付", "既存撤去の上 新規取付け", "既存撤去後 新設取付", "既存撤去後 張替え工事"):
            self.assertFalse(cls("石膏ボード", spec)["demolish"], spec)
        self.assertEqual(cls("石膏ボード", "既存撤去後 新規張替え")["demolish"], documents.MAYBE)    # (not a listed form)

        def sheet(rows):
            x = row(1, t("A1", "名称"), t("B1", "摘要"), t("C1", "数量"), t("D1", "単位"))
            for i, (nm, sp, q, u) in enumerate(rows, 2):
                x += row(i, t("A%d" % i, nm), t("B%d" % i, sp), n("C%d" % i, q), t("D%d" % i, u))
            return x
        got, _ = read(xlsx([("A工事", sheet([("石膏ボード", "t12.5 既存撤去後 新設 B工事", 500, "m2")])),
                            ("B工事", sheet([("石膏ボード", "t12.5 新設", 500, "m2")]))]))
        self.assertEqual(got, {("m_board", "m2"): 500.0})

    # --- 3. a part after an excluding word never gives the head (attacks 2)
    def test_a_part_after_an_excluding_word_gives_no_head(self):
        got, r = csv_read("Description,Qty,Unit\nMetal stud partition excl. plasterboard,400,m2\nPlasterboard 12.5mm,800,m2\n"
                          "Excavation for pile caps excl. concrete,60,m3\nConcrete C30/37 in pile caps,40,m3\n"
                          "Cavity wall excl. insulation,300,m2\nCavity insulation 100mm,300,m2\n"
                          "Metal stud partition excluding plasterboard,400,m2\n")
        self.assertEqual(got, {("m_board", "m2"): 800.0, ("m_concrete_fdn", "m3"): 40.0, ("m_insulation", "m2"): 300.0})
        # (16 回目：4 行は除いた材料の欄に「足すべきかもしれない」で数量とともに出る。前は使わなかった行にだけ
        # 「どの材料の欄にも当てはまらない」で出ていた)
        self.assertEqual(sum(1 for u in r["unused"] if u["reason"] == documents.R_PART_MAYBE), 4)
        for nm in ("Excavating trenches without concrete", "Excavation except concrete", "Excavation less concrete",
                   "Suspended ceiling system exc. boards", "Door frame excl. glass", "Earthworks exc concrete", "Hardcore ex concrete"):
            self.assertIsNone(documents._field_for(nm), nm)
        # the material before the excluding word stays the head; the excluded part does not choose the foundation card
        for nm, fid in (("Concrete C30/37 without plasterboard", "m_concrete"), ("Structural steelwork less insulation", "m_steel"),
                        ("Concrete C30 in slabs excluding foundations", "m_concrete"), ("Concrete C30 except pile caps", "m_concrete"),
                        ("Concrete C30 in pile caps", "m_concrete_fdn"), ("Timber ex 50x100", "m_timber")):
            self.assertEqual(documents._field_for(nm), fid, nm)
        got, _ = pdf_read(["Metal stud partition excl. plasterboard   400 m2", "Cavity wall excl. insulation   300 m2"])
        self.assertEqual(got, [])

    # --- 4. space-justified Japanese names and specifications (attacks 3)
    def test_space_justified_names_and_specifications(self):
        got, r = csv_read("名称,摘要,数量,単位\n異形鉄筋,SD345 D19,30,t\n加　工　組　立,異形鉄筋 SD345 D19,30,t\n運　　搬,異形鉄筋 SD345 D19,30,t\n"
                          "普通コンクリート,Fc24 S18,300,m3\n打　　設,普通コンクリート Fc24,300,m3\n撤　　去,既存コンクリート 土間 t150,40,m3\n"
                          "鉄　　骨,SN490B,50,t\n鉄　　筋,D13,5,t\n")
        self.assertEqual(got, {("m_rebar", "t"): 35.0, ("m_concrete", "m3"): 300.0, ("m_steel", "t"): 50.0})
        ex = excluded(r)
        self.assertIn(("撤  去", 40.0, documents.R_DEMOLISH[:12], False), ex)      # (the name is shown as written)
        self.assertEqual(sum(1 for x in ex if x[2] == documents.R_WORK[:12]), 3)
        for name, spec in (("既存コンクリート", "撤　去"), ("既存コンクリート", "は　つ　り")):
            self.assertEqual(cls(name, spec, "m3")["demolish"], documents.SURE, spec)
        for name, spec in (("石膏ボード", "t12.5 取　付　手　間"), ("石膏ボード", "t12.5 手　間"), ("鉄　筋　加　工　組　立", "SD345"),
                           ("コンクリート　打　設", "")):
            self.assertTrue(cls(name, spec)["work"], (name, spec))
        for name, fid in (("ガ　ラ　ス", "m_glass"), ("防　　水", "m_membrane"), ("断　熱　材", "m_insulation"), ("木　　材", "m_timber")):
            self.assertEqual(documents._field_for(name), fid, name)
        # words of two or more letters keep their spaces; a mark is never lost by closing up (内　柱: of which columns)
        self.assertEqual(documents._justify("既存 コンクリート 打 設"), "既存 コンクリート 打設")
        self.assertEqual(cls("鉄骨", "内　柱", "t")["again"], documents.MAYBE)
        c = cls("普通コンクリート", "内　杭", "m3")                    # (and the note does not choose the foundation card)
        self.assertEqual((c["fid"], c["again"]), ("m_concrete", documents.MAYBE))
        self.assertEqual(cls("基　礎　コンクリート", "内 柱", "m3")["fid"], "m_concrete_fdn")
        self.assertTrue(documents._is_total("設　計"))                                  # (as before: closing up adds marks only)
        # one name column, and the PDF path (the line's name is checked by the same functions)
        got, _ = csv_read("名称,数量,単位\n撤　　去 既存コンクリート 土間 t150,40,m3\n加　工　組　立 異形鉄筋 SD345,30,t\n")
        self.assertEqual(got, {})
        self.assertEqual(documents._field_for("鉄　　骨 SN490B"), "m_steel")
        self.assertTrue(documents._is_demolition("撤　　去 既存コンクリート 土間 t150"))
        self.assertTrue(documents._is_work("加　工　組　立 異形鉄筋 SD345"))

    # --- 5. IFC: the renovation status and removal names (attacks 7)
    def test_ifc_status_and_removal_names(self):
        txt = ifc_text([("IFCSLAB", "New slab", "Concrete C30/37", "VOLUME", 30.0, None, "", ""),
                        ("IFCSLAB", "Existing slab - to be demolished", "Concrete C30/37", "VOLUME", 25.0, "DEMOLISH",
                         "IFCPROPERTYENUMERATEDVALUE", "Pset_SlabCommon"),
                        ("IFCWALL", "既存壁 撤去", "Concrete C30/37", "VOLUME", 12.0, "DEMOLISH", "IFCPROPERTYSINGLEVALUE",
                         "Pset_WallCommon"),
                        ("IFCWALL", "Wall 200", "Concrete C30/37", "VOLUME", 9.0, "Existing", "IFCPROPERTYSINGLEVALUE",
                         "Pset_WallCommon"),
                        ("IFCWALL", "Hoarding", "Concrete C30/37", "VOLUME", 4.0, "TEMPORARY", "IFCPROPERTYSINGLEVALUE",
                         "Pset_WallCommon"),
                        ("IFCWALL", "Wall 300", "Concrete C30/37", "VOLUME", 7.0, "NEW", "IFCPROPERTYSINGLEVALUE", "Pset_WallCommon"),
                        ("IFCWALL", "Wall 400", "Concrete C30/37", "VOLUME", 6.0, "DEMOLISH", "IFCPROPERTYSINGLEVALUE",
                         "Pset_Custom"),
                        ("IFCBEAM", "Beam (remove)", "Steel S355", "WEIGHT", 1500.0, None, "", ""),
                        ("IFCBEAM", "Beam B1", "Steel S355", "WEIGHT", 2000.0, None, "", "")])
        got, r = read(txt.encode(), "m.ifc")
        self.assertEqual(got, {("m_concrete", "m3"): 43.0, ("m_steel", "t"): 2.0})       # 30 + 7 + 6 (not a Common set)
        ex = {x[0]: x for x in excluded(r)}
        self.assertEqual(ex["IFCSLAB Existing slab - to be demolished"][1:], (25.0, documents.R_IFC_DEMOLISH[:12], False))
        self.assertEqual(ex["IFCWALL 既存壁 撤去"][1:], (12.0, documents.R_IFC_DEMOLISH[:12], False))
        self.assertEqual(ex["IFCWALL Wall 200"][1:], (9.0, documents.R_IFC_EXISTING[:12], False))
        self.assertEqual(ex["IFCWALL Hoarding"][1:], (4.0, documents.R_IFC_TEMPORARY[:12], True))
        self.assertEqual(ex["IFCBEAM Beam (remove)"][1:], (1500.0, documents.R_DEMOLISH[:12], False))   # (kg, as the rows)
        # the name alone is read as a table row's name: removal of what is there, or perhaps a note
        got, r = read(ifc_text([("IFCSLAB", "既存床 撤去", "Concrete", "VOLUME", 20.0, None, "", ""),
                                ("IFCSLAB", "Floor slab", "Concrete", "VOLUME", 50.0, None, "", "")]).encode(), "n.ifc")
        self.assertEqual(got, {("m_concrete", "m3"): 50.0})
        parsed = ifc.parse(ifc_text([("IFCWALL", "W", "Brick", "AREA", 1.0, "demolished", "IFCPROPERTYSINGLEVALUE",
                                      "PSET_WALLCOMMON")], "IFC2X3"), "d")
        self.assertEqual(parsed["elements"][0]["status"], "DEMOLISH")

    # --- 6. a supply word that is negated or given to others (attacks 10)
    def test_negated_supply_does_not_make_a_material_row(self):
        for nm in ("Plasterboard 12.5mm; fix only, supply by others", "Plasterboard 12.5mm; supplied by others; fix",
                   "Concrete C30/37; placing excluding supply", "Concrete C30/37; place only (supply by others)",
                   "Reinforcement; fixing only, supply by client", "Reinforcement; fix only, free issue supply",
                   "Reinforcement; fix only, free-issue supply", "Reinforcement; client supplied, fix only",
                   "Structural steelwork; erect only, supply and fabrication by others", "Concrete; placing, excl. supply",
                   "Reinforcement; fix only, supply by the main contractor", "Reinforcement; fix only, supply measured elsewhere"):
            self.assertTrue(documents._is_work(nm), nm)
        for nm in ("Structural steelwork; supply only", "Structural steelwork; supply, fabricate and erect",
                   "Reinforcement; supply and fix", "Plasterboard 12.5mm; supply by others"):
            self.assertFalse(documents._is_work(nm), nm)
        self.assertTrue(documents._is_work("異形鉄筋", "加工組立 支給材料共"))
        self.assertFalse(documents._is_work("異形鉄筋", "加工組立 材料共"))
        got, r = csv_read("Description,Qty,Unit\nPlasterboard 12.5mm; supply only,500,m2\n\"Plasterboard 12.5mm; fix only, supply by others\",500,m2\n")
        self.assertEqual(got, {("m_board", "m2"): 500.0})

    # --- 7. scrap rows (attacks 11)
    def test_scrap_rows_are_deductions(self):
        got, r = csv_read("名称,摘要,数量,単位\n異形鉄筋,SD345 D13,30,t\nスクラップ,鉄筋 D13,1.2,t\n鉄筋スクラップ,売却,1.5,t\n"
                          "鉄骨,SN400B,50,t\nスクラップ買取,鉄骨,2,t\n鉄筋スクラップ,,0.8,t\n")
        self.assertEqual(got, {("m_rebar", "t"): 30.0, ("m_steel", "t"): 50.0})
        self.assertEqual(sorted((x[0], x[2], x[3]) for x in excluded(r)),
                         sorted([("スクラップ", documents.R_SCRAP_MAYBE[:12], True), ("スクラップ買取", documents.R_DEDUCT[:12], False),
                                 ("鉄筋スクラップ", documents.R_DEDUCT[:12], False),
                                 ("鉄筋スクラップ", documents.R_SCRAP_MAYBE[:12], True)]))
        for name, spec in (("鉄筋スクラップ", "評価"), ("鉄筋スクラップ", "引取り"), ("鉄くず", "有価物"), ("スクラップ評価", "鉄筋"),
                           ("スクラップ売却", "鉄筋")):
            self.assertEqual(cls(name, spec, "t")["deduct"], documents.SURE, (name, spec))
        # a sale word after the scrap in the specification of a material row may be a credit row: maybe
        self.assertEqual(cls("異形鉄筋", "SD345 スクラップ売却", "t")["deduct"], documents.MAYBE)
        # the disposal of the scrap is a price note on the work (14 回目)
        self.assertFalse(cls("異形鉄筋 スクラップ処分共", "控除後", "t")["deduct"])

    # --- 8. price notes after 控除, okurigana after a labour word, a price note as the next word (attacks 12)
    def test_price_notes_and_okurigana(self):
        got, r = csv_read("名称,摘要,数量,単位\n石膏ボード,t12.5 既存撤去の上 新規張り,500,m2\n普通コンクリート,Fc24 S18 打込み別途,300,m3\n"
                          "異形鉄筋,SD345 加工組立て 込み,30,t\n異形鉄筋,SD345 スクラップ控除は別途,20,t\n")
        self.assertEqual(got, {("m_board", "m2"): 500.0, ("m_concrete", "m3"): 300.0, ("m_rebar", "t"): 50.0})
        for spec in ("スクラップ控除は別途", "スクラップ控除せず", "スクラップ控除しない", "スクラップ控除済", "スクラップ控除済み",
                     "スクラップ控除含まず", "スクラップ控除を含む", "控除はなし"):
            self.assertFalse(cls("異形鉄筋", "SD345 " + spec, "t")["deduct"], spec)
        self.assertEqual(cls("異形鉄筋", "SD345 スクラップ控除", "t")["deduct"], documents.MAYBE)
        for spec in ("Fc24 打込み共", "Fc24 打込み別途", "Fc24 打込み手間共", "Fc24 打込み費込み"):
            self.assertFalse(documents._is_work("普通コンクリート", spec), spec)
        for name, spec in (("異形鉄筋", "SD345 加工組立て 込み"), ("鉄骨", "SN400B 製作 建方 共"), ("石膏ボード", "t12.5 取付け手間 込み")):
            self.assertFalse(documents._is_work(name, spec), (name, spec))
        # the labour itself stays work
        for name, spec in (("普通コンクリート", "Fc24 打込み"), ("普通コンクリート", "打込み手間"), ("異形鉄筋", "加工組立て"),
                           ("異形鉄筋", "加工組立て のみ"), ("鉄骨", "建方")):
            self.assertTrue(documents._is_work(name, spec), (name, spec))
        # cut to: only the listed objects (14 回目); "cut to shape" stays work so that cutting what is there is not added
        self.assertTrue(documents._is_work("Existing concrete slab; cut to shape and make good"))
        self.assertTrue(documents._is_work("High yield steel bars; cut to schedule"))

    # ===== the problems an independent attack found in the fixes above (15 回目の攻撃) =====

    # --- an excluding word right after a bracket or , ; : - , and the list after it (attacks 2, 15 回目の攻撃)
    def test_excluding_word_after_a_bracket_and_its_list(self):
        got, r = csv_read("Description,Qty,Unit\nMetal stud partition (excluding plasterboard),400,m2\nPlasterboard 12.5mm,800,m2\n"
                          "Excavation for pile caps (excl. concrete),60,m3\nConcrete C30/37 in pile caps,40,m3\n"
                          "Cavity wall (excl. insulation),300,m2\nCavity insulation 100mm,300,m2\n")
        self.assertEqual(got, {("m_board", "m2"): 800.0, ("m_concrete_fdn", "m3"): 40.0, ("m_insulation", "m2"): 300.0})
        got, r = csv_read("Description,Qty,Unit\n\"Metal stud partition excl. plasterboard, insulation\",400,m2\n"
                          "Plasterboard 12.5mm,800,m2\nMineral wool insulation 50mm,400,m2\n")
        self.assertEqual(got, {("m_board", "m2"): 800.0, ("m_insulation", "m2"): 400.0})
        for nm in ("Metal stud partition [excl. plasterboard]", "Metal stud partition,excl. plasterboard",
                   "Metal stud partition:excluding plasterboard", "Metal stud partition -excl. plasterboard",
                   "Metal stud partition; excl.: plasterboard", "Metal stud partition (excl.plasterboard)",
                   "Suspended ceiling grid excl. tiles, insulation", "Curtain walling framing excl. glass, insulation",
                   "Cavity wall excluding insulation, blockwork", "Metal stud partition (excl. plasterboard, insulation)",
                   "Excavation for pile caps excluding formwork, concrete and reinforcement"):
            self.assertIsNone(documents._field_for(nm), nm)
        # the bracket or ";" that closes the excluded part ends it; the excluded part does not choose the foundation card
        for nm, fid in (("Metal stud partition (excl. plasterboard), insulation 50mm", "m_insulation"),
                        ("Metal stud partition excl. plasterboard; insulation 50mm", "m_insulation"),
                        ("Concrete C30/37 in slabs (excluding foundations, pile caps)", "m_concrete"),
                        ("Plasterboard 12.5mm-excluding concrete, reinforcement", "m_board")):
            self.assertEqual(documents._field_for(nm), fid, nm)
        # an aside set off by commas: the material after it is perhaps the item, perhaps more of what is excluded
        got, r = csv_read("Description,Qty,Unit\n\"Infill panels, without frames, blockwork 100mm\",200,m2\n"
                          "Blockwork 100mm,300,m2\n")
        self.assertEqual(got, {("m_masonry", "m2"): 300.0})
        self.assertEqual([(x[1], x[2], x[3]) for x in excluded(r)], [(200.0, documents.R_ASIDE_MAYBE[:12], True)])

    # --- ex <size>, ex works, not less than, except as noted do not exclude (15 回目の攻撃)
    def test_ex_size_and_not_less_than_keep_the_material(self):
        got, r = csv_read("Description,Qty,Unit\nFloor joists ex 50 x 200 sawn softwood,12,m3\n"
                          "Rafters ex 50 x 150 treated softwood,8,m3\nLining of not less than 15mm plasterboard,500,m2\n"
                          "Topping not less than 75mm concrete,30,m3\n")
        self.assertEqual(got, {("m_timber", "m3"): 20.0, ("m_board", "m2"): 500.0, ("m_concrete", "m3"): 30.0})
        for nm, fid in (("Sections ex stock structural steel S355", "m_steel"), ("Units ex works precast concrete", "m_concrete"),
                        ("Bars ex mill high yield steel", "m_steel"), ("Panels less than 1m2 plasterboard", "m_board"),
                        ("Lintels except as noted precast concrete", "m_concrete"), ("Fascia board ex 25 x 225 softwood", "m_timber"),
                        ("Timber (ex 50x100)", "m_timber")):
            self.assertEqual(documents._field_for(nm), fid, nm)
        # the excluding senses stay as decided (15 回目)
        for nm in ("Hardcore ex concrete", "Excavation less concrete", "Excavation except concrete"):
            self.assertIsNone(documents._field_for(nm), nm)

    # --- a Japanese excluding ending after a material word (15 回目の攻撃)
    def test_japanese_excluding_ending_gives_no_head(self):
        got, r = csv_read("名称,摘要,数量,単位\n間仕切下地,LGS 65形（石膏ボード除く）,500,m2\n石膏ボード,t12.5,500,m2\n"
                          "外壁下地,胴縁（断熱材除く）,300,m2\nグラスウール,t50,300,m2\n根切り,基礎（コンクリート除く）,60,m3\n")
        self.assertEqual(got, {("m_board", "m2"): 500.0, ("m_insulation", "m2"): 300.0})
        self.assertEqual(sum(1 for u in r["unused"] if u["reason"] == documents.R_PART_MAYBE), 3)   # (16 回目)
        for name, spec in (("間仕切下地", "LGS 65形 石膏ボード別途"), ("間仕切下地", "押出法ポリスチレンフォームを除く"),
                           ("", "断熱材含まず")):
            self.assertIsNone(cls(name, spec)["fid"], (name, spec))
        self.assertEqual(cls("軽量鉄骨天井下地", "19形（ボード別途）")["fid"], "m_steel")     # (the name's own material)
        # another material of the part is the head; the endings not listed change nothing
        self.assertEqual(cls("外壁", "ALC 100 塗装別途")["fid"], "m_masonry")
        for spec in ("石膏ボード共", "石膏ボード込み", "石膏ボード t12.5", "石膏ボード 別途"):
            self.assertEqual(cls("間仕切下地", "LGS 65形 " + spec)["fid"], "m_board", spec)

    # --- a scrap word after the material in a one-column name is a note: maybe at most (15 回目の攻撃)
    def test_scrap_note_after_the_material_is_never_sure(self):
        got, r = csv_read("名称,数量,単位\n異形鉄筋 SD345 D13 スクラップ買取共,30,t\n鉄骨 SN490B スクラップ評価額別途,50,t\n"
                          "異形鉄筋 SD345 D19 スクラップ精算別途,20,t\n")
        self.assertEqual(got, {})
        self.assertEqual(sorted((x[1], x[2], x[3]) for x in excluded(r)),
                         [(20.0, documents.R_SCRAP_NOTE_MAYBE[:12], True), (30.0, documents.R_SCRAP_NOTE_MAYBE[:12], True),
                          (50.0, documents.R_SCRAP_NOTE_MAYBE[:12], True)])
        # (a PDF line is a candidate to check, as before 15 回目: the line's name is no deduction)
        self.assertFalse(documents._is_deduction("異形鉄筋 SD345 D13 スクラップ買取共"))
        self.assertTrue(documents._is_deduction("鉄筋スクラップ 売却"))
        # a price note with 評価額・売却額・有価物 … before 控除後 is the material row
        got, r = csv_read("名称,摘要,数量,単位\n異形鉄筋,SD345 D13 スクラップ評価額控除後,30,t\n鉄骨,SN490B スクラップ売却額控除後,50,t\n"
                          "異形鉄筋,SD345 D19 スクラップ評価控除後,20,t\n")
        self.assertEqual(got, {("m_rebar", "t"): 50.0, ("m_steel", "t"): 50.0})
        for spec in ("スクラップ有価物控除なし", "スクラップ買取価格控除後", "スクラップ引取額控除別途", "スクラップ売却代控除後"):
            self.assertFalse(cls("異形鉄筋", "SD345 " + spec, "t")["deduct"], spec)
        # the scrap itself stays the deduction (15 回目)
        for name in ("鉄筋スクラップ 売却", "スクラップ買取", "鋼材くず 売却"):
            self.assertEqual(cls(name, "", "t")["deduct"], documents.SURE, name)
        self.assertEqual(cls("異形鉄筋 SD345 D13 スクラップ控除後", "", "t")["deduct"], documents.SURE)   # (控除 in the name)

    # --- a spelled including keeps its last item when that is the disposal (15 回目の攻撃)
    def test_including_list_keeps_its_disposal_note(self):
        got, r = csv_read("Description,Qty,Unit\n\"Floor tiles 300x300 including adhesive, grout and disposal\",600,m2\n"
                          "\"Carpet tiles including underlay, gripper and disposal\",400,m2\n"
                          "Plasterboard 12.5mm includes screws - disposal,500,m2\n")
        self.assertEqual(got, {("m_finish", "m2"): 1000.0, ("m_board", "m2"): 500.0})
        for nm in ("Floor tiles including adhesive, disposal", "Floor tiles including adhesive: disposal",
                   "Plasterboard 12.5mm includes screws\ndisposal"):
            self.assertIsNone(documents._demolish(documents._prep(nm)), nm)
        self.assertEqual(documents._demolish(documents._prep("Floor tiles including adhesive (disposal)")), documents.MAYBE)

    # --- a space-justified material name alone, with no specification: perhaps a summary (15 回目の攻撃)
    def test_justified_name_alone_is_perhaps_a_summary(self):
        def sheet(rows):
            x = row(1, t("A1", "名称"), t("B1", "規格"), t("C1", "数量"), t("D1", "単位"))
            for i, (nm, sp, q, u) in enumerate(rows, 2):
                x += row(i, t("A%d" % i, nm), t("B%d" % i, sp) if sp else "", n("C%d" % i, q), t("D%d" % i, u))
            return x
        got, r = read(xlsx([("科目別", sheet([("鉄　　骨", "", 50, "t"), ("鉄　　筋", "", 30, "t")])),
                            ("細目", sheet([("鉄骨", "SN490B", 50, "t"), ("異形鉄筋", "SD345 D13", 30, "t")]))]))
        self.assertEqual(got, {("m_steel", "t"): 50.0, ("m_rebar", "t"): 30.0})
        self.assertEqual(sorted((x[1], x[2], x[3]) for x in excluded(r)),
                         [(30.0, documents.R_JUSTIFIED_MAYBE[:12], True), (50.0, documents.R_JUSTIFIED_MAYBE[:12], True)])
        self.assertFalse(cls("鉄　　骨", "SN490B", "t")["just"])        # (with a specification: the material row, 15 回目)

    # --- IFC: the status of the element's type, and of the whole it is part of (15 回目の攻撃)
    def test_ifc_status_of_the_type_and_of_the_whole(self):
        txt = "\n".join([
            "ISO-10303-21;", "HEADER;FILE_SCHEMA(('IFC4'));ENDSEC;", "DATA;",
            "#10=IFCCURTAINWALL('cw1',$,'Existing curtain wall',$,$,$,$,$,$);",
            "#11=IFCPLATE('pl1',$,'Panel',$,$,$,$,$,$);", "#12=IFCPLATE('pl2',$,'Panel',$,$,$,$,$,$);",
            "#14=IFCPLATE('pl3',$,'New panel',$,$,$,$,$,$);",
            "#13=IFCRELAGGREGATES('ag',$,$,$,#10,(#11,#12,#14));",
            "#20=IFCQUANTITYAREA('NetArea',$,$,40.0,$);", "#21=IFCELEMENTQUANTITY('q1',$,'Qto',$,$,(#20));",
            "#22=IFCRELDEFINESBYPROPERTIES('r1',$,$,$,(#11,#12,#14),#21);",
            "#40=IFCPROPERTYSINGLEVALUE('Status',$,IFCLABEL('DEMOLISH'),$);",
            "#41=IFCPROPERTYSET('p1',$,'Pset_CurtainWallCommon',$,(#40));",
            "#42=IFCRELDEFINESBYPROPERTIES('r4',$,$,$,(#10),#41);",
            "#43=IFCPROPERTYSINGLEVALUE('Status',$,IFCLABEL('NEW'),$);",
            "#44=IFCPROPERTYSET('p3',$,'Pset_PlateCommon',$,(#43));",
            "#45=IFCRELDEFINESBYPROPERTIES('r6',$,$,$,(#14),#44);",
            "#30=IFCMATERIAL('Glass',$,$);", "#31=IFCRELASSOCIATESMATERIAL('m1',$,$,$,(#10,#11,#12,#14),#30);",
            "#50=IFCWALL('w1',$,'Wall',$,$,$,$,$);", "#58=IFCWALL('w2',$,'Wall 2',$,$,$,$,$);",
            "#51=IFCWALLTYPE('wt1',$,'Wall type',$,$,(#53),$,$,$,.STANDARD.);",
            "#52=IFCPROPERTYSINGLEVALUE('Status',$,IFCLABEL('EXISTING'),$);",
            "#53=IFCPROPERTYSET('p2',$,'Pset_WallCommon',$,(#52));",
            "#54=IFCRELDEFINESBYTYPE('rt',$,$,$,(#50,#58),#51);",
            "#59=IFCPROPERTYSINGLEVALUE('Status',$,IFCLABEL('NEW'),$);",
            "#60=IFCPROPERTYSET('p4',$,'Pset_WallCommon',$,(#59));",
            "#61=IFCRELDEFINESBYPROPERTIES('r7',$,$,$,(#58),#60);",
            "#55=IFCQUANTITYVOLUME('NetVolume',$,$,12.0,$);", "#56=IFCELEMENTQUANTITY('q2',$,'Qto',$,$,(#55));",
            "#57=IFCRELDEFINESBYPROPERTIES('r5',$,$,$,(#50,#58),#56);",
            "#62=IFCMATERIAL('Concrete C30/37',$,$);", "#63=IFCRELASSOCIATESMATERIAL('m2',$,$,$,(#50,#58),#62);",
            "ENDSEC;", "END-ISO-10303-21;"]) + "\n"
        got, r = read(txt.encode(), "a.ifc")
        # the panel marked NEW is added; the wall whose own status is NEW is added (its type's EXISTING does not apply)
        self.assertEqual(got, {("m_glass", "m2"): 40.0, ("m_concrete", "m3"): 12.0})
        ex = excluded(r)
        self.assertEqual(sorted(x[1:] for x in ex if x[0] == "IFCPLATE Panel"),
                         [(40.0, documents.R_IFC_PART[:12], True)] * 2)
        self.assertIn(("IFCWALL Wall", 12.0, documents.R_IFC_EXISTING[:12], False), ex)
        parsed = ifc.parse(txt, "d")
        by = {e["step_id"]: e for e in parsed["elements"]}
        self.assertEqual((by[11]["part_of"]["status"], by[11]["part_of"]["step_id"]), ("DEMOLISH", 10))
        self.assertNotIn("part_of", by[14])
        self.assertEqual((by[50]["status"], by[58]["status"]), ("EXISTING", None))

    # --- the closed-up texts are read a second time: they are charged to the character budget (15 回目の攻撃)
    def test_closed_up_texts_are_charged_to_the_budget(self):
        p = documents._Prep(1000)
        documents._row_class(p, {"name": "鉄　　骨", "specification": "加　工", "division": "", "unit": "t"})
        self.assertEqual(p.left, 1000 - len("鉄　　骨") - len("加　工") - len("鉄骨") - len("加工"))
        p = documents._Prep(9)
        with self.assertRaises(documents._Budget):
            documents._row_class(p, {"name": "鉄　　骨", "specification": "加　工", "division": "", "unit": "t"})


if __name__ == "__main__":
    unittest.main()
