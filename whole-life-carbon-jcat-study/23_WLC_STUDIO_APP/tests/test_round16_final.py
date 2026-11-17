"""Round 16, the last fixes before the verification was ended: a row whose material is named only where it may not be
the item (after an excluding word, in a part of place) is listed with its quantity as "may belong" on that material's
card (the safety net; on IFC only after the status check); less / ex joined by a hyphen to a word are part of it; a name
or division cell that is only a space-justified 内 word is "maybe", not a sure breakdown; the removal phrases are whole
words, and a room or place named by one (break-out area) is no sure removal; the inputs named with a missing count or
scenario come after the real gaps in the list of what the total lacks.

Run: cd whole-life-carbon-jcat-study && python3 -B -m unittest discover -s 23_WLC_STUDIO_APP/tests -q
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
os.environ.setdefault("WLCSTUDIO_OFFLINE", "1")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

from wlcstudio import bridge, documents, fields as FL  # noqa: E402

try:
    from tests.test_round10_importer import csv_read, read  # noqa: E402
    from tests.test_round15_classify import cls, ifc_text, pdf_read  # noqa: E402
    from tests.test_round16_bridge import complete  # noqa: E402
except ImportError:
    from test_round10_importer import csv_read, read  # noqa: E402
    from test_round15_classify import cls, ifc_text, pdf_read  # noqa: E402
    from test_round16_bridge import complete  # noqa: E402

REFSET = json.loads((Path(HERE).parents[1] / "12_APP_BASE" / "samples" / "refset_fictional.json").read_text(encoding="utf-8"))
NO_FIELD = "どの材料の欄にも当てはまらない"


def cards(r):
    """{(field, name): (quantity, reason, maybe)} of the rows left out, on candidates and in the summary."""
    out = {}
    for k in ("evidence", "left_out"):
        for fid, ev in r.get(k, {}).items():
            for x in ev["excluded"]:
                out[(fid, x["name"])] = (x.get("quantity"), x["reason"], x["maybe"])
    return out


class SixteenthRoundFinalTests(unittest.TestCase):
    # --- A1. the safety net: a material named only in an excluded or uncertain part is listed with its quantity
    def test_a1_material_named_only_in_an_excluded_part_is_listed_as_maybe(self):
        got, r = csv_read('Item,Description,Qty,Unit\n'
                          '1,"Partition type P1 excluding finishes\nPlasterboard 12.5mm on metal studs, both sides",500,m2\n'
                          '2,Plasterboard 12.5mm to ceilings,300,m2\n'
                          '3,"Ground floor slab excl. reinforcement\nConcrete C30/37, 150mm thick",120,m3\n'
                          '4,Concrete C30/37 in upper floor slabs,200,m3\n'
                          '5,Internal walls without decoration: blockwork 100mm dense,800,m2\n'
                          '6,Roof covering excluding insulation - single ply membrane 1.5mm,600,m2\n'
                          '7,Metal stud partition excl. plasterboard,12,nr\n'
                          '8,鉄筋用スペーサー,0.5,t\n')
        # nothing is added that was not added before (the sure totals stay); the four rows are no longer lost silently:
        # each is on the card of the material it names, "may belong", with its quantity
        self.assertEqual(got, {("m_board", "m2"): 300.0, ("m_concrete", "m3"): 200.0})
        c = cards(r)
        for fid, q in (("m_board", 500.0), ("m_concrete", 120.0), ("m_masonry", 800.0), ("m_membrane", 600.0)):
            hit = [v for (f, _n), v in c.items() if f == fid]
            self.assertEqual(hit, [(q, documents.R_PART_MAYBE, True)], fid)
        self.assertEqual(r["left_out"]["m_masonry"]["n_maybe"], 1)
        self.assertEqual(r["evidence"]["m_board"]["n_maybe"], 1)
        # a unit the material does not take, or a product of no field: only among the rows not used, as before
        why = {u["name"]: u["reason"] for u in r["unused"]}
        self.assertEqual(why["Metal stud partition excl. plasterboard"], NO_FIELD)
        self.assertEqual(why["鉄筋用スペーサー"], NO_FIELD)
        # the net reads each row once more within the row's own bounds; it is not charged to the document's budget (a
        # long bill is read to its end as before)
        p = documents._Prep(1000)
        name = "Metal stud partition excl. plasterboard"
        c1 = documents._row_class(p, {"name": name, "specification": "", "division": "", "unit": "m2"})
        self.assertEqual((c1["fid"], c1["net"]), (None, "m_board"))
        self.assertEqual(p.left, 1000 - len(name))
        # a row with a mark keeps its own reason (no net)
        self.assertIsNone(cls("Existing partition excl. plasterboard; removal", "", "m2")["net"])
        # IFC: the net comes after the status check
        txt = ifc_text([("IFCCOVERING", "Underlay to carpet tiles", "Felt underlay", "AREA", 200.0, "EXISTING",
                         "IFCPROPERTYSINGLEVALUE", "Pset_CoveringCommon"),
                        ("IFCCOVERING", "Underlay to carpet tiles L3", "Felt underlay", "AREA", 150.0, None, "", ""),
                        ("IFCCOVERING", "Floor finish L2", "Carpet tiles", "AREA", 500.0, None, "", ""),
                        ("IFCSLAB", "Hardcore bed under concrete slab", "Hardcore", "VOLUME", 40.0, "DEMOLISH",
                         "IFCPROPERTYSINGLEVALUE", "Pset_SlabCommon")])
        got, r = read(txt.encode(), "n.ifc")
        self.assertEqual(got, {("m_finish", "m2"): 500.0})
        c = cards(r)
        # no status: on the finish card as "may belong" with its quantity
        self.assertEqual(c[("m_finish", "IFCCOVERING Underlay to carpet tiles L3")], (150.0, documents.R_PART_MAYBE, True))
        # EXISTING and DEMOLISH: not on any card (among the elements not used, as before)
        self.assertEqual(r["evidence"]["m_finish"]["n_maybe"], 1)
        self.assertNotIn("m_concrete", r["left_out"])
        why = {u["name"]: u["reason"] for u in r["unused"]}
        self.assertTrue(why["IFCCOVERING Underlay to carpet tiles"].startswith("材料名から分類できない"))
        self.assertTrue(why["IFCSLAB Hardcore bed under concrete slab"].startswith("材料名から分類できない"))

    # --- A2. less / ex joined by a hyphen to a word of letters are part of that word
    def test_a2_hyphenated_less_and_ex_are_part_of_the_word(self):
        got, r = csv_read("Description,Qty,Unit\nFrame-less glass balustrade 12mm toughened,40,m2\n"
                          "Toughened glass 10mm to screens,60,m2\nSeam-less vinyl sheet flooring 2mm,500,m2\n"
                          "Carpet tiles 500x500,800,m2\n")
        self.assertEqual(got, {("m_glass", "m2"): 100.0, ("m_finish", "m2"): 1300.0})
        for nm, fid in (("Co-ex membrane 300 micron below slab", "m_membrane"), ("Stain-less steel sheet 1.5mm", "m_steel"),
                        ("Joint-less resin floor finish", "m_finish"), ("Head-less timber stud partition", "m_timber"),
                        ("Rim-less glass shower screen 8mm", "m_glass"), ("Frameless glass balustrade", "m_glass"),
                        ("Concrete C30 - less than 1m2", "m_concrete"), ("Concrete C30 -excluding formwork", "m_concrete")):
            self.assertEqual(documents._field_for(nm), fid, nm)
        # the other excluding words after a dash, and less / ex with a space, still exclude
        for nm in ("Metal stud partition-excl. plasterboard", "Partition,less plasterboard", "Hardcore ex concrete"):
            self.assertIsNone(documents._field_for(nm), nm)
        got, _ = pdf_read(["Frame-less glass balustrade 12mm toughened   40 m2"])
        self.assertEqual(got, [("m_glass", 40.0)])

    # --- A3. a name or division cell that is only a space-justified 内 word is "maybe", not a sure breakdown
    def test_a3_justified_nai_word_in_name_or_division_is_maybe(self):
        got, r = csv_read("名称,摘要,数量,単位\n内　　壁,石膏ボード t12.5 GL工法,800,m2\n天　　井,石膏ボード t9.5,600,m2\n"
                          "内　　壁,グラスウール t50,300,m2\n")
        self.assertEqual(got, {("m_board", "m2"): 600.0})
        c = cards(r)
        self.assertEqual(c[("m_board", "内  壁")], (800.0, documents.R_AGAIN_NAI_MAYBE, True))
        self.assertEqual(c[("m_insulation", "内  壁")], (300.0, documents.R_AGAIN_NAI_MAYBE, True))
        got, r = csv_read("区分,名称,摘要,数量,単位\n内　部,石膏ボード,t12.5 GL工法,800,m2\n外　部,押出成形セメント板,t60,300,m2\n"
                          "内　部,ビニル床シート,t2.0,600,m2\n内部,石膏ボード,t9.5,400,m2\n内　装　材,石膏ボード,t9.5,50,m2\n")
        self.assertEqual(got, {("m_board", "m2"): 400.0, ("m_masonry", "m2"): 300.0})
        self.assertEqual(sorted((x.get("quantity"), x["reason"], x["maybe"]) for x in r["evidence"]["m_board"]["excluded"]),
                         [(q, documents.R_AGAIN_NAI_MAYBE, True) for q in (50.0, 800.0)])
        self.assertIn({"name": "ビニル床シート", "reason": documents.R_AGAIN_NAI_MAYBE},
                      [{k: u[k] for k in ("name", "reason")} for u in r["unused"]])   # (a sheet names no field)
        # explicit marks stay sure, also in the same justified run; other 内 runs keep their reading
        got, r = csv_read("名称,摘要,数量,単位\n石膏ボード,t12.5 GL工法,1000,m2\n内　壁　内　訳,石膏ボード t12.5,400,m2\n"
                          "内　部　う　ち,石膏ボード t12.5,300,m2\n内　訳,石膏ボード t12.5,200,m2\n内　　柱,石膏ボード t12.5,100,m2\n")
        self.assertEqual(got, {("m_board", "m2"): 1000.0})
        self.assertEqual(sorted((v[0], v[1], v[2]) for v in cards(r).values()),
                         [(q, documents.R_AGAIN, False) for q in (100.0, 200.0, 300.0, 400.0)])
        # a 内 note in the specification, a one-column name and a PDF line: as before (maybe, sure, refused)
        got, r = csv_read("名称,摘要,数量,単位\n普通コンクリート,Fc24 S18,300,m3\n普通コンクリート,Fc24 S18 内 壁,120,m3\n"
                          "石膏ボード,t12.5,900,m2\n石膏ボード,t12.5 内 壁,500,m2\n")
        self.assertEqual(got, {("m_concrete", "m3"): 300.0, ("m_board", "m2"): 900.0})
        self.assertEqual(sorted(v[1] for v in cards(r).values()), [documents.R_AGAIN_MAYBE] * 2)
        self.assertEqual(cls("普通コンクリート Fc24 内 壁", "", "m3")["again"], documents.SURE)
        self.assertTrue(documents._not_added("内　　壁 石膏ボード t12.5"))

    # --- A4. the removal phrases: whole words, and a room or place named by one is no sure removal
    def test_a4_removal_phrases_are_whole_words_and_not_room_names(self):
        got, r = csv_read("Description,Qty,Unit\nCarpet tiles 500x500 to offices,800,m2\n"
                          "Carpet tiles 500x500 to break-out area,250,m2\nPlasterboard partition 12.5mm to break-out room,120,m2\n"
                          "Plasterboard 12.5mm to offices,400,m2\nBreak-out area: carpet tiles 500x500,60,m2\n"
                          "Plasterboard 12.5mm; take down ceiling,30,m2\nBreak out existing concrete slab,25,m3\n")
        self.assertEqual(got, {("m_finish", "m2"): 1050.0, ("m_board", "m2"): 520.0})
        c = cards(r)
        self.assertEqual(c[("m_finish", "Break-out area: carpet tiles 500x500")],
                         (60.0, documents.R_DEMOLISH_PLACE_MAYBE, True))           # (perhaps new carpet there)
        self.assertEqual(c[("m_board", "Plasterboard 12.5mm; take down ceiling")], (30.0, documents.R_DEMOLISH_MAYBE, True))
        self.assertEqual(c[("m_concrete", "Break out existing concrete slab")], (25.0, documents.R_DEMOLISH, False))
        for nm in ("aluminium strip outer frame", "carpet tiles take downstairs"):
            self.assertIsNone(documents._demolish(nm), nm)
        self.assertEqual(documents._demolish("strip outs of existing carpet"), documents.SURE)
        # IFC names follow the same rule
        txt = ifc_text([("IFCCOVERING", "Floor finish - Break-out area L2", "Carpet tiles", "AREA", 250.0, None, "", ""),
                        ("IFCCOVERING", "Floor finish - Office L2", "Carpet tiles", "AREA", 800.0, None, "", ""),
                        ("IFCSLAB", "Slab - Strip out zone", "Concrete C30/37", "VOLUME", 60.0, None, "", ""),
                        ("IFCSLAB", "Existing slab - break out", "Concrete C30/37", "VOLUME", 25.0, None, "", "")])
        got, r = read(txt.encode(), "b.ifc")
        self.assertEqual(got, {("m_finish", "m2"): 1050.0})
        c = cards(r)
        self.assertEqual(c[("m_concrete", "IFCSLAB Slab - Strip out zone")], (60.0, documents.R_DEMOLISH_PLACE_MAYBE, True))
        self.assertEqual(c[("m_concrete", "IFCSLAB Existing slab - break out")], (25.0, documents.R_DEMOLISH, False))

    # --- B1. the inputs named with a missing count or scenario do not push the real gaps out of the notice
    def test_b1_inputs_named_with_a_count_or_the_scenario_come_after_the_other_gaps(self):
        co = [("a_replacement_cycle", "a_reconstruction"), ("a_recon_fraction", "a_reconstruction")]
        co += [("e_%s_%s" % (t.lower(), p), "e_%s_count" % t.lower()) for t, _ in FL.TRADES for p in ("life", "mass")]
        primary = ["a_reconstruction"] + ["e_%s_count" % t.lower() for t, _ in FL.TRADES] + [
            "r_charge_kg", "r_gwp", "o_elec_kwh"]
        vals = complete(**{f: None for f in primary + [f for f, _w in co]})
        _, rep = bridge.build(vals, REFSET, period=60.0)
        _, rep0 = bridge.build(complete(**{f: None for f in primary}), REFSET, period=60.0)
        before = [m["field"] for m in rep0["omitted_inputs"]]          # (what the list held before the inputs named with)
        self.assertEqual(before[:len(primary)], primary)
        # the list of what the total lacks: every gap it held before, first and in the same order, then the inputs
        # named with them, each marked with the gap it goes with
        self.assertEqual([(m["field"], m.get("with")) for m in rep["omitted_inputs"]],
                         [(f, None) for f in before] + co)
        self.assertLess([m["field"] for m in rep["omitted_inputs"]].index("o_elec_kwh"), 12)   # (the screen shows 12)
        # the bridge's note names the same first gaps as before
        note = next(n for n in rep["notes"] if n.startswith("入っていない入力"))
        note0 = next(n for n in rep0["notes"] if n.startswith("入っていない入力"))
        self.assertEqual(note.split("（", 1)[1][:60], note0.split("（", 1)[1][:60])
        # the gaps themselves keep their order (the hint names the count, then its life and mass) and the stage marks
        fields = [m["field"] for m in rep["missing_inputs"]]
        self.assertLess(fields.index("e_hvac_count"), fields.index("e_hvac_life"))
        self.assertLess(fields.index("e_hvac_life"), fields.index("e_hvac_mass"))
        self.assertEqual(rep["incomplete_stages"], rep0["incomplete_stages"])


if __name__ == "__main__":
    unittest.main()
