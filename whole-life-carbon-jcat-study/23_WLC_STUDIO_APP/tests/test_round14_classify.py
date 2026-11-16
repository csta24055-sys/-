"""Round 14 of the independent review: the classification of quantity rows (X用…ボード is a board unless X comes as
boards; cut out / off / back / on / at / in are work; incl. / inc. / excl. / exc. with their dot; 既存撤去後 新設 in the
摘要 is the new material; price and reference notes in the 摘要 are no deduction or breakdown, and a mark only in the
摘要 is a "maybe"; のみ / 工 / 作業 / 手間 after a method word with its okurigana is labour)."""
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

try:
    from tests.test_round10_importer import csv_read  # noqa: E402
    from tests.test_wlcstudio import _pdf  # noqa: E402
except ImportError:
    from test_round10_importer import csv_read  # noqa: E402
    from test_wlcstudio import _pdf  # noqa: E402


def head(name):
    return documents._head(documents._prep(name))[0]


def cls(name, spec="", unit="m2"):
    return documents._row_class(documents._Prep(), {"name": name, "specification": spec, "division": "", "unit": unit})


def excluded(r):
    """{name or name|spec quantity: (reason head, maybe)} of the rows left out, on candidates and in the summary."""
    out = []
    for ev in list(r["evidence"].values()) + list(r.get("left_out", {}).values()):
        out += [(x["name"], x.get("quantity"), x["reason"][:12], x["maybe"]) for x in ev["excluded"]]
    return sorted(out)


class FourteenthRoundClassificationTests(unittest.TestCase):
    def test_x_yo_board_is_a_board_unless_x_comes_as_boards(self):
        expect = {
            # 13 回目 made ボード a form of every material: these went to finishes, steel, the membrane
            "タイル用下地ボード": "m_board", "クロス用下地ボード": "m_board", "防水用保護ボード": "m_board",
            "防水用下地ボード": "m_board", "鉄骨用耐火ボード": "m_board", "塗装用化粧ボード": "m_board",
            "コンクリート用型枠ボード": "m_board", "断熱用下地ボード": "m_board", "断熱用セメントボード": "m_board",
            # a purpose word before the form word names a product of its own (12 回目: no field)
            "防水用保護シート": None, "防水用目地シート": None, "防水用保護層": None, "防水用絶縁シート": None,
            # the forms of 13 回目 stay
            "断熱用フォームボード": "m_insulation", "断熱用押出発泡ボード": "m_insulation", "断熱用ボード": "m_insulation",
            "防水用改質アスファルトシート": "m_membrane", "防水用ウレタン塗膜": "m_membrane", "防水用アスファルト": "m_membrane",
            "鉄骨用鋼板": "m_steel", "鉄骨用ベースプレート": "m_steel", "断熱用ボード押え金物": None, "防水用シート押え金物": None,
        }
        self.assertEqual({k: head(k) for k in expect}, expect)
        got, r = csv_read("名称,摘要,数量,単位,単価,金額,備考\n石膏ボード,t12.5,1000,m2,,,\nタイル用下地ボード,,300,m2,,,\n"
                          "磁器質タイル,,300,m2,,,\nクロス用下地ボード,,500,m2,,,\nビニルクロス,,500,m2,,,\n"
                          "鉄骨用耐火ボード,,400,m2,,,\n防水用下地ボード,,200,m2,,,\n塩ビシート防水,,200,m2,,,\n")
        self.assertEqual(got, {("m_board", "m2"): 2400.0, ("m_finish", "m2"): 800.0, ("m_membrane", "m2"): 200.0})
        got, _ = csv_read("名称,規格,数量,単位\nアスファルト防水,,600,m2\n防水用保護ボード,,600,m2\n防水用保護シート,,600,m2\n")
        self.assertEqual(got, {("m_membrane", "m2"): 600.0, ("m_board", "m2"): 600.0})
        self.assertEqual(documents._field_for("タイル用下地ボード"), "m_board")        # (the PDF and IFC paths use it)

    def test_cut_out_off_back_on_at_in_are_work(self):
        for nm in ("Concrete piles; cut off to level", "Existing concrete slab; cut out for new opening",
                   "Concrete; cut back to sound concrete", "Reinforcement; cut on site", "Concrete cut at joints",
                   "Plasterboard cut in", "Timber boarding cut as necessary", "Rebar; cut off projecting bars"):
            self.assertTrue(documents._is_work(nm), nm)
        for nm in ("Reinforcement bars; cut to length", "Rebar; cut into lengths", "Steel; cut from plate",
                   "Reinforcement; cut, bent and fixed"):
            self.assertFalse(documents._is_work(nm), nm)
        got, r = csv_read("Description,Qty,Unit\nPrecast concrete piles 300x300,45,m3\n"
                          "Precast concrete piles; cut off to cut-off level,3,m3\nReinforced concrete C30 in slabs,250,m3\n"
                          "Reinforced concrete; cut out for new openings,6,m3\nBrickwork in cement mortar,400,m2\n"
                          "Brickwork; cut out and make good,25,m2\nReinforcement bars,30,t\nReinforcement; cut on site,30,t\n")
        self.assertEqual(got, {("m_concrete_fdn", "m3"): 45.0, ("m_concrete", "m3"): 250.0, ("m_masonry", "m2"): 400.0,
                               ("m_rebar", "t"): 30.0})
        self.assertEqual(sum(1 for x in excluded(r) if x[3] and x[2].startswith("作業の行")), 4)
        # the PDF path reads the same way (and incl. with its dot)
        r = documents.read("b.pdf", base64.b64encode(_pdf(["Concrete piles; cut off to level   6 m3",
                                                            "Existing concrete slab; cut out for new opening   12 m3",
                                                            "Ready mixed concrete C30/37 incl. cube testing   400 m3"])).decode(), "d")
        self.assertEqual(sorted((p.field_id, p.value) for p in r["proposals"]), [("m_concrete", 400.0)])

    def test_incl_and_excl_with_their_dot(self):
        for nm in ("Ready mixed concrete C30/37 incl. cube testing", "Concrete inc. testing", "Structural steelwork incl. NDT testing",
                   "Concrete C30 Incl. placing and compacting", "Concrete excl. placing", "Concrete C30 exc. placing"):
            self.assertFalse(documents._is_work(nm), nm)
        # only the listed abbreviations, and only with their dot; sampling and testing after the material stays work
        for nm in ("Concrete inc testing", "Concrete C30/37; sampling and testing as specification"):
            self.assertTrue(documents._is_work(nm), nm)
        self.assertFalse(documents._is_demolition("In situ concrete C30, incl. disposal of surplus"))
        got, r = csv_read("Description,Qty,Unit\nReady mixed concrete C30/37 incl. cube testing,400,m3\n"
                          "Structural steelwork incl. NDT testing,50,t\n"
                          "\"In situ concrete C30/37; sampling and testing as specification\",200,m3\n")
        self.assertEqual(got, {("m_concrete", "m3"): 400.0, ("m_steel", "t"): 50.0})
        self.assertEqual(r["evidence"]["m_concrete"]["n_maybe"], 1)

    def test_removal_then_new_installation_in_the_tekiyo_is_the_new_material(self):
        got, r = csv_read("名称,摘要,数量,単位,単価,金額,備考\n石膏ボード,t12.5 既存撤去後 新設,500,m2,,,\n"
                          "ビニル床タイル,既存撤去共,300,m2,,,\nグラスウール,t100 既存撤去後 新規,200,m2,,,\n"
                          "アスファルト防水,既存防水撤去後 新設,150,m2,,,\n既存石膏ボード撤去,処分共,500,m2,,,\n")
        self.assertEqual(got, {("m_board", "m2"): 500.0, ("m_insulation", "m2"): 200.0, ("m_membrane", "m2"): 150.0})
        ex = {x[0]: x[3] for x in excluded(r)}
        self.assertEqual(ex, {"ビニル床タイル": True, "既存石膏ボード撤去": False})   # 既存撤去共 stays removal (maybe)
        for spec in ("既存撤去の上 新設", "撤去後に張替え", "解体後 新設", "既存撤去後 取替"):
            self.assertFalse(cls("石膏ボード", spec)["demolish"], spec)
        # a name that is removal, or that names what is there, stays removal
        for name in ("既存石膏ボード", "石膏ボード撤去", "既存天井 石膏ボード"):
            self.assertEqual(cls(name, "撤去後 新設")["demolish"], documents.SURE, name)
        self.assertEqual(cls("石膏ボード", "既存撤去 新設")["demolish"], documents.MAYBE)    # no 後: as before

    def test_price_and_reference_notes_in_the_tekiyo(self):
        got, r = csv_read("名称,摘要,数量,単位,単価,金額,備考\n異形鉄筋,SD295 D10〜D16 スクラップ控除別途,30,t,95000,2850000,\n"
                          "異形鉄筋,SD345 D19〜D25 スクラップ控除なし,20,t,98000,1960000,\n"
                          "普通コンクリート,Fc24 S18 内訳書による,300,m3,16000,4800000,\n普通コンクリート,Fc21 S15 捨てコン,10,m3,,,\n")
        self.assertEqual(got, {("m_rebar", "t"): 50.0, ("m_concrete", "m3"): 310.0})
        for spec in ("スクラップ控除共", "スクラップ控除含む", "スクラップ控除込み", "スクラップ控除後", "控除なし", "内訳別紙",
                     "内訳書参照", "別紙内訳", "別紙による"):
            c = cls("異形鉄筋", spec, "t")
            self.assertFalse(c["deduct"] or c["again"], spec)
        # a deduction or a breakdown mark only in the specification may be a note: left out, but "maybe", with its quantity
        got, r = csv_read("名称,摘要,数量,単位,単価,金額,備考\n異形鉄筋,SD345 D19,20,t,,,\n異形鉄筋,スクラップ控除,1.5,t,,,\n"
                          "普通コンクリート,Fc24（うち基礎 40m3）,300,m3,,,\n普通コンクリート,Fc24 再掲,300,m3,,,\n"
                          "鉄筋スクラップ控除,,1.2,t,,,\n普通コンクリート,Fc21,10,m3,,,\n")
        self.assertEqual(got, {("m_rebar", "t"): 20.0, ("m_concrete", "m3"): 10.0})
        ex = excluded(r)
        self.assertIn(("異形鉄筋", 1.5, documents.R_DEDUCT_MAYBE[:12], True), ex)
        self.assertIn(("普通コンクリート", 300.0, documents.R_AGAIN_MAYBE[:12], True), ex)
        self.assertIn(("普通コンクリート", 300.0, documents.R_AGAIN[:12], False), ex)          # an explicit 再掲 is sure
        self.assertIn(("鉄筋スクラップ控除", 1.2, documents.R_DEDUCT[:12], False), ex)      # in the name: sure
        self.assertEqual(cls("鉄骨", "上記に含む", "t")["again"], documents.SURE)
        self.assertEqual(cls("鉄骨", "うち柱", "t")["again"], documents.MAYBE)
        # a "maybe" mark never hides a sure reason: a removal row, a negative quantity
        got, r = csv_read("名称,摘要,数量,単位\n石膏ボード,t12.5,500,m2\n既存石膏ボード撤去,うち天井,200,m2\n石膏ボード,開口部控除,-40,m2\n")
        self.assertEqual(got, {("m_board", "m2"): 500.0})
        self.assertEqual(sorted((x[1], x[2], x[3]) for x in excluded(r)),
                         [(-40.0, documents.R_NEG[:12], False), (200.0, documents.R_DEMOLISH[:12], False)])

    def test_labour_only_after_a_method_word_with_okurigana(self):
        for name, spec in (("押出法ポリスチレンフォーム", "打込みのみ"), ("押出法ポリスチレンフォーム", "打込み工"),
                           ("押出法ポリスチレンフォーム", "打ち込み手間"), ("押出法ポリスチレンフォーム", "3種b t50 打込み工"),
                           ("押出法ポリスチレンフォーム", "敷込みのみ"), ("押出法ポリスチレンフォーム", "床下 敷込のみ"),
                           ("石膏ボード", "取付け工"), ("土間コンクリート", "金ごて仕上げのみ"), ("デッキプレート", "溶接止め のみ"),
                           ("押出法ポリスチレンフォーム", "打込み")):
            self.assertTrue(documents._is_work(name, spec), spec)
        # with a size the method word says how the material is put in place (13 回目), and a price that includes the work
        for name, spec in (("押出法ポリスチレンフォーム", "t50 打込み"), ("押出法ポリスチレンフォーム", "3種b t25 打込み"),
                           ("押出法ポリスチレンフォーム", "床下敷込"), ("石膏ボード", "t12.5 取付け工共"),
                           ("石膏ボード", "t12.5 GL工法 取付")):
            self.assertFalse(documents._is_work(name, spec), spec)
        got, r = csv_read("名称,規格,数量,単位\n押出法ポリスチレンフォーム,3種b t25,1200,m2\n押出法ポリスチレンフォーム,打込みのみ,1200,m2\n")
        self.assertEqual(got, {("m_insulation", "m2"): 1200.0})
        self.assertEqual(r["evidence"]["m_insulation"]["n_maybe"], 1)


if __name__ == "__main__":
    unittest.main()
