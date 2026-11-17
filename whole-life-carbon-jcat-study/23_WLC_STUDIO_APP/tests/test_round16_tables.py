"""Round 16 of the independent review: the tables (rows of one material that read a take-off's pivot table, the cost of
that check, helper cells reused by another item of the same material, copies of rows decided once every row is read,
and the name checks of a row that reads a take-off's pivot table)."""
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

try:
    from tests.test_round10_importer import HDR, mrow, n, read, row, t, xlsx  # noqa: E402
    from tests.test_round14_tables import excluded  # noqa: E402
    from tests.test_round15_tables import book, summary  # noqa: E402
except ImportError:
    from test_round10_importer import HDR, mrow, n, read, row, t, xlsx  # noqa: E402
    from test_round14_tables import excluded  # noqa: E402
    from test_round15_tables import book, summary  # noqa: E402

FIDS = ("m_concrete", "m_concrete_fdn", "m_rebar", "m_steel", "m_finish", "m_masonry", "m_board")
# a take-off with no bill header (部位｜材料｜体積) and a pivot table of it by member, with the grand total
TAKE = row(1, t("A1", "部位"), t("B1", "材料"), t("C1", "体積")) + "".join(
    row(i, t("A%d" % i, p), t("B%d" % i, "コンクリート"), n("C%d" % i, q))
    for i, (p, q) in enumerate((("基礎", 40), ("柱", 30), ("梁", 40), ("スラブ", 40)), 2))
PIV = row(3, t("A3", "行ラベル"), t("B3", "合計 / 体積")) + "".join(
    row(i, t("A%d" % i, p), n("B%d" % i, q)) for i, (p, q) in enumerate((("基礎", 40), ("柱", 30), ("梁", 40), ("スラブ", 40),
                                                                         ("総計", 150)), 4))
PV = (1, "ピボット1", "A3:B8", "拾い", "A1:C5")
AREA = row(1, t("A1", "室名"), t("B1", "床面積")) + row(2, t("A2", "事務室"), n("B2", 120)) + \
    row(3, t("A3", "会議室"), n("B3", 40)) + row(4, t("A4", "廊下"), n("B4", 60))


def ex(r, sheet):
    return [x for fid in FIDS for x in excluded(r, fid) if x["trace"].startswith("d:%s!" % sheet)]


def pivot_reads(sheets, pivots=(PV,)):
    return read(book([("拾い", TAKE), ("集計", PIV)] + sheets, list(pivots)))


class SixteenthRoundTableTests(unittest.TestCase):
    # --- rows of one material that read a take-off's pivot table (attacks 4)
    def test_rows_of_one_material_reading_a_take_off_pivot_are_not_added(self):
        parts = summary(("基礎コンクリート", "集計!B4", 40, "m3"), ("柱コンクリート", "集計!B5", 30, "m3"),
                        ("梁コンクリート", "集計!B6", 40, "m3"), ("スラブコンクリート", "集計!B7", 40, "m3"))
        whole = summary(("コンクリート", "集計!B8", 150, "m3"))
        # the parts and the grand total (each the only reader of its cell): none is added, each is shown with its
        # quantity and names the others (94bf205 added 300 m3, twice the take-off)
        got, r = pivot_reads([("部位別", parts), ("総括", whole)])
        self.assertEqual(got, {})
        xs = ex(r, "部位別") + ex(r, "総括")
        self.assertEqual(sorted(x["quantity"] for x in xs), [30, 40, 40, 40, 150])
        for x in xs:
            self.assertTrue(x["maybe"], x)
            self.assertIn("ピボットテーブル（ピボット1）の値を参照した値は足さない", x["reason"])
            self.assertIn("同じ材料のほかの行（", x["reason"])
        self.assertIn("部位別 の 2 行目", ex(r, "総括")[0]["reason"])
        self.assertFalse([w for w in r["warnings"] if "足した" in w])
        # one sheet: the foundation part and the whole (94bf205: 40 + 150)
        got, r = pivot_reads([("まとめ", summary(("基礎コンクリート", "集計!B4", 40, "m3"), ("コンクリート", "集計!B8", 150, "m3")))])
        self.assertEqual(got, {})
        a, b = ex(r, "まとめ")
        self.assertTrue(a["maybe"] and b["maybe"])
        self.assertEqual(sorted((a["quantity"], b["quantity"])), [40, 150])
        self.assertIn("まとめ の 3 行目", (a if a["quantity"] == 40 else b)["reason"])
        self.assertIn("まとめ の 2 行目", (b if a["quantity"] == 40 else a)["reason"])
        # the parts alone: two or more readers of the material, the same
        got, r = pivot_reads([("部位別", parts)])
        self.assertEqual(got, {})
        self.assertEqual(len([x for x in ex(r, "部位別") if x["maybe"]]), 4)
        # two pivot tables of the same take-off, each read by one row: the same (either would repeat the other)
        got, r = read(book([("拾い", TAKE), ("集計", PIV), ("階別集計", PIV), ("まとめ", summary(("コンクリート", "集計!B8", 150, "m3"))),
                            ("総括", summary(("コンクリート", "階別集計!B8", 150, "m3")))],
                           [PV, (2, "ピボット2", "A3:B8", "拾い", "A1:C5")]))
        self.assertEqual(got, {})
        self.assertEqual([x["maybe"] for x in ex(r, "まとめ") + ex(r, "総括")], [True, True])
        # the only reader of the material is added as before (15 回目の攻撃), with one warning
        got, r = pivot_reads([("総括", whole)])
        self.assertEqual(got, {("m_concrete", "m3"): 150.0})
        self.assertEqual(len([w for w in r["warnings"] if "足した" in w]), 1)
        self.assertTrue(any("総括 の 2 行目はピボットテーブル（ピボット1）の値を参照している" in w for w in r["warnings"]))
        # one row of each of two materials: both added, one warning for the pivot table
        take2 = TAKE + row(6, t("A6", "柱"), t("B6", "鉄筋"), n("C6", 12))
        piv2 = row(3, t("A3", "行ラベル"), t("B3", "合計 / 数量")) + row(4, t("A4", "コンクリート"), n("B4", 150)) + \
            row(5, t("A5", "鉄筋"), n("B5", 12)) + row(6, t("A6", "総計"), n("B6", 162))
        got, r = read(book([("拾い", take2), ("集計", piv2), ("まとめ", summary(("コンクリート", "集計!B4", 150, "m3"),
                                                                             ("鉄筋", "集計!B5", 12, "t")))],
                           [(1, "ピボット1", "A3:B6", "拾い", "A1:C6")]))
        self.assertEqual(got, {("m_concrete", "m3"): 150.0, ("m_rebar", "t"): 12.0})
        ws = [w for w in r["warnings"] if "足した" in w]
        self.assertEqual(len(ws), 1)
        self.assertIn("ピボットテーブル（ピボット1）の値を参照している 2 行（まとめ の 2 行目、まとめ の 3 行目）", ws[0])

    # --- the cost of that check (attacks 5)
    def test_the_rows_reading_a_pivot_table_are_checked_once_each(self):
        N = 6000
        take = row(1, t("A1", "部位"), t("B1", "材料"), t("C1", "体積")) + row(2, t("A2", "基礎"), t("B2", "コンクリート"), n("C2", 40))
        piv = row(3, t("A3", "行ラベル"), t("B3", "合計 / 体積")) + "".join(row(k + 4, t("A%d" % (k + 4), "p%d" % k), n("B%d" % (k + 4), 1))
                                                                         for k in range(N))
        rows = summary(*[("コンクリート", "集計!B%d" % (k + 4), 1, "m3") for k in range(N)])
        sheets = [("拾い", take), ("集計", piv), ("まとめ", rows)]
        t0 = time.perf_counter()
        got, r = read(book(sheets, [(1, "ピボット1", "A3:B%d" % (N + 3), "拾い", "A1:C2")]))
        took = time.perf_counter() - t0
        self.assertEqual(got, {})
        self.assertEqual(r["left_out"]["m_concrete"]["n_maybe"], N)
        self.assertLess(len(r["warnings"]), 6)                     # one per pivot table, never one per row
        self.assertIn("ほか %d 行" % (N - 4), r["left_out"]["m_concrete"]["excluded"][0]["reason"])
        # the same formulas over the same cells with no pivot table (a helper sheet): about as long, not N times longer
        t0 = time.perf_counter()
        got, r = read(book(sheets, []))
        self.assertEqual(got, {("m_concrete", "m3"): float(N)})
        self.assertLess(took, 3 * (time.perf_counter() - t0) + 1.0)

    # --- helper cells reused by another item of the same material (regressions 0)
    def test_another_item_from_the_cells_a_counted_row_sums_may_belong(self):
        floor = HDR + mrow(2, "タイルカーペット", "t6.5", n("C2", 220, "SUM(室面積!B2:B4)"), "m2")
        wall = HDR + mrow(2, "EP塗装", "壁", n("C2", 550, "SUM(室面積!B2:B4)*2.5"), "m2")
        # the wall area worked out from the floor areas: perhaps another item, shown with its quantity, in either
        # order of the sheets (94bf205: a sure exclusion of 550 m2 in one order, "may belong" in the other)
        for sheets, kept, other, q in (([("室面積", AREA), ("床仕上", floor), ("壁仕上", wall)], 220.0, "壁仕上", 550),
                                       ([("室面積", AREA), ("壁仕上", wall), ("床仕上", floor)], 550.0, "床仕上", 220)):
            got, r = read(xlsx(sheets))
            self.assertEqual(got, {("m_finish", "m2"): kept})
            x, = ex(r, other)
            self.assertTrue(x["maybe"] and x["quantity"] == q, x)
            self.assertIn("が数量に使ったセル（室面積 B2:B4）", x["reason"])
            self.assertFalse([y for y in excluded(r, "m_finish") if not y["maybe"]])
        # the ceiling of the same rooms (the same cells, unscaled, another item): the same
        ceil = HDR + mrow(2, "EP塗装", "天井 下地処理共", n("C2", 220, "SUM(室面積!B2:B4)"), "m2")
        got, r = read(xlsx([("室面積", AREA), ("床仕上", floor), ("天井仕上", ceil)]))
        self.assertEqual(got, {("m_finish", "m2"): 220.0})
        x, = ex(r, "天井仕上")
        self.assertTrue(x["maybe"] and x["quantity"] == 220)
        # the same item summing the same cells again on another sheet stays a sure copy (as one column, too); scaled, or
        # only some of the cells (one room), it may belong
        for name, spec, f, sure in (("タイルカーペット", "t6.5", "SUM(室面積!B2:B4)", True), ("タイルカーペット t6.5", "", "SUM(室面積!B2:B4)", True),
                                    ("タイルカーペット", "t6.5", "室面積!B2+室面積!B3+室面積!B4", True),
                                    ("タイルカーペット", "t6.5", "室面積!B3", False), ("タイルカーペット", "t6.5", "SUM(室面積!B2:B4)*1.05", False)):
            got, r = read(xlsx([("室面積", AREA), ("床仕上", floor), ("集計", HDR + mrow(2, name, spec, n("C2", 220, f), "m2"))]))
            self.assertEqual(got, {("m_finish", "m2"): 220.0}, (name, f))
            x, = ex(r, "集計")
            self.assertEqual(x["maybe"], not sure, (name, f, x["reason"]))
            if sure:
                self.assertIn("別のシート（床仕上）の材料の行（2 行目）が足し上げたセル（室面積 ", x["reason"])
        # one room of the same item: "may belong" in either order of the sheets (94bf205: sure in one order)
        part = HDR + mrow(2, "タイルカーペット", "t6.5", n("C2", 40, "室面積!B3"), "m2")
        for sheets, kept, q in (([("室面積", AREA), ("床仕上", floor), ("会議室", part)], 220.0, 40),
                                ([("室面積", AREA), ("会議室", part), ("床仕上", floor)], 40.0, 220)):
            got, r = read(xlsx(sheets))
            self.assertEqual(got, {("m_finish", "m2"): kept})
            self.assertEqual([(y["maybe"], y["quantity"]) for y in excluded(r, "m_finish")], [(True, q)])

    # --- copies of rows decided once every row is read (regressions 4)
    def test_a_copy_of_a_row_decided_after_the_loop_may_belong_when_that_row_is_not_counted(self):
        def copy_of(r, sheet):
            x, = ex(r, sheet)
            return x
        # worked out from another material's row, its own material counted nowhere (the copy also reaches the
        # concrete row, which counts no rebar)
        rebar = HDR + mrow(2, "異形鉄筋", "概算 0.12t/m3", n("C2", 12, "明細!C2*0.12"), "t")
        summ = HDR + mrow(2, "鉄筋", "", n("C2", 12, "概算!C2"), "t")
        got, r = read(xlsx([("明細", HDR + mrow(2, "普通コンクリート", "Fc24", n("C2", 100), "m3")), ("概算", rebar), ("集計", summ)]))
        self.assertEqual(got, {("m_concrete", "m3"): 100.0})
        x = copy_of(r, "集計")
        self.assertTrue(x["maybe"] and "別のシート（概算）の材料の行（2 行目）" in x["reason"] and "足していない" in x["reason"], x)
        # … its material counted in the bill: still a sure copy
        got, r = read(xlsx([("明細", HDR + mrow(2, "普通コンクリート", "Fc24", n("C2", 100), "m3") + mrow(3, "異形鉄筋", "SD345", n("C3", 12), "t")),
                            ("概算", rebar), ("集計", summ)]))
        self.assertEqual(got, {("m_concrete", "m3"): 100.0, ("m_rebar", "t"): 12.0})
        self.assertFalse(copy_of(r, "集計")["maybe"])
        # read from a take-off's pivot table and left out; added as the only reader: the copy follows
        take = row(1, t("A1", "部位"), t("B1", "材料"), t("C1", "体積")) + row(2, t("A2", "柱"), t("B2", "コンクリート"), n("C2", 60)) + \
            row(3, t("A3", "梁"), t("B3", "コンクリート"), n("C3", 90))
        piv = row(3, t("A3", "行ラベル"), t("B3", "合計 / 体積")) + row(4, t("A4", "コンクリート"), n("B4", 150))
        for f, q, maybe in (("集計!B4+拾い!C3", 240, True), ("集計!B4", 150, False)):
            got, r = read(book([("拾い", take), ("集計", piv), ("まとめ", summary(("コンクリート", f, q, "m3"))),
                                ("総括", summary(("コンクリート", "まとめ!B2", q, "m3")))], [(1, "ピボット1", "A3:B4", "拾い", "A1:C3")]))
            self.assertEqual(got, {} if maybe else {("m_concrete", "m3"): 150.0})
            self.assertEqual(copy_of(r, "総括")["maybe"], maybe, f)
        # read from a pivot table of a bill whose row is left out (うち): the material is counted nowhere
        detail = HDR + mrow(2, "鉄筋", "SD345（うち基礎 2t）", n("C2", 12), "t")
        pv = row(3, t("A3", "行ラベル"), t("B3", "合計 / 数量")) + row(4, t("A4", "鉄筋"), n("B4", 12))
        got, r = read(book([("明細", detail), ("集計", pv), ("まとめ", summary(("鉄筋", "集計!B4", 12, "t"))),
                            ("総括", summary(("鉄筋", "まとめ!B2", 12, "t")))], [(1, "ピボット表", "A3:B4", "明細", "A1:D2")]))
        self.assertEqual(got, {})
        self.assertTrue(copy_of(r, "総括")["maybe"])
        # the cells a row sums, summed again by the same item on another sheet, while that row is not counted (t among
        # rows in m3): perhaps the only count; counted, a sure copy
        take = row(1, t("A1", "部位"), t("B1", "1F"), t("C1", "2F"), t("D1", "3F")) + row(2, t("A2", "柱"), n("B2", 10), n("C2", 10), n("D2", 10))
        pc = mrow(2, "普通コンクリート", "PC部材", n("C2", 30, "SUM(拾い!B2:D2)"), "t")
        m3 = mrow(3, "普通コンクリート", "Fc21", n("C3", 100), "m3") + mrow(4, "普通コンクリート", "Fc18", n("C4", 50), "m3")
        for more, want, maybe in ((m3, {("m_concrete", "m3"): 150.0}, True), ("", {("m_concrete", "t"): 30.0}, False)):
            got, r = read(xlsx([("拾い", take), ("細目", HDR + pc + more),
                                ("集計", HDR + mrow(2, "普通コンクリート", "PC部材", n("C2", 30, "SUM(拾い!B2:D2)"), "t"))]))
            self.assertEqual(got, want)
            x = copy_of(r, "集計")
            self.assertEqual(x["maybe"], maybe)
            self.assertIn("別のシート（細目）の材料の行（2 行目）が足し上げたセル（拾い B2:D2）を足した値は足さない", x["reason"])
            self.assertEqual("足していない" in x["reason"], maybe)

    # --- a row that reads a take-off's pivot table is checked for its name first (regressions 5)
    def test_a_row_reading_a_take_off_pivot_is_checked_for_its_name_first(self):
        take = row(1, t("A1", "部位"), t("B1", "材料"), t("C1", "体積")) + row(2, t("A2", "柱"), t("B2", "ブロック"), n("C2", 60)) + \
            row(3, t("A3", "梁"), t("B3", "ブロック"), n("C3", 90))
        piv = row(3, t("A3", "行ラベル"), t("B3", "合計 / 面積")) + row(4, t("A4", "ブロック"), n("B4", 150)) + row(5, t("A5", "総計"), n("B5", 150))

        def go(*rows):
            return read(book([("拾い", take), ("集計", piv), ("まとめ", summary(*rows))], [(1, "ピボット1", "A3:B5", "拾い", "A1:C3")]))
        for nm, u, why in (("Infill panels, without frames, blockwork 100mm", "m2", documents.R_ASIDE_MAYBE),
                           ("鉄　　骨", "t", documents.R_JUSTIFIED_MAYBE)):
            got, r = go((nm, "集計!B4", 150, u))
            self.assertEqual(got, {}, nm)
            x, = ex(r, "まとめ")
            self.assertTrue(x["maybe"] and x["reason"] == why and x["quantity"] == 150, x)
            self.assertFalse([w for w in r["warnings"] if "足した" in w])
        got, r = go(("コンクリートブロック", "集計!B4", 150, "m2"))
        self.assertEqual(got, {("m_masonry", "m2"): 150.0})
        # such a row is still one of the readers of its material: a plain row beside it is not added either
        got, r = go(("Infill panels, without frames, blockwork 100mm", "集計!B4", 150, "m2"), ("コンクリートブロック", "集計!B5", 150, "m2"))
        self.assertEqual(got, {})
        xs = ex(r, "まとめ")
        self.assertEqual([x["maybe"] for x in xs], [True, True])
        self.assertIn("同じ材料のほかの行（まとめ の 2 行目）", [x for x in xs if x["trace"].endswith("R3C2")][0]["reason"])

    # --- the attack on the round-16 fixes: the same cells added twice (the boards on both faces of a wall)
    def test_a_row_adding_the_cells_of_a_counted_row_twice_may_belong(self):
        wall = row(1, t("A1", "室名"), t("B1", "壁面積")) + row(2, t("A2", "事務室"), n("B2", 120)) + \
            row(3, t("A3", "会議室"), n("B3", 40)) + row(4, t("A4", "廊下"), n("B4", 60))
        a = ("間仕切A", HDR + mrow(2, "石膏ボード", "t12.5", n("C2", 220, "SUM(壁面積!B2:B4)"), "m2"))

        def board(f, q):
            return ("間仕切B", HDR + mrow(2, "石膏ボード", "t12.5", n("C2", q, f), "m2"))
        # the same item from the same cells with another quantity is perhaps another item: "may belong" with its
        # quantity in either order of the sheets, never dropped surely (the branch dropped 220 m2 or 440 m2 surely,
        # depending on the order of the sheets: the blocks met twice are met once)
        for f, q in (("SUM(壁面積!B2:B4)+SUM(壁面積!B2:B4)", 440), ("SUM(壁面積!B2:B4,壁面積!B2:B4)", 440),
                     ("壁面積!B2+壁面積!B3+壁面積!B4+壁面積!B2+壁面積!B3+壁面積!B4", 440), ("SUM(壁面積!B2:B4)+10", 230),
                     ("AVERAGE(壁面積!B2:B4)", 73.3), ("MAX(壁面積!B2:B4)", 120)):
            for sheets, kept, other, q_other in (([a, board(f, q)], 220.0, "間仕切B", q), ([board(f, q), a], float(q), "間仕切A", 220)):
                got, r = read(xlsx([("壁面積", wall)] + sheets))
                self.assertEqual(got, {("m_board", "m2"): kept}, f)
                x, = ex(r, other)
                self.assertTrue(x["maybe"], (f, x["reason"]))
                self.assertEqual(x["quantity"], q_other)
                self.assertIn("が数量に使ったセル（壁面積 B2:B4）", x["reason"])
        # the same quantity stays a sure copy (SUM, SUBTOTAL(9, …), the cells in another order)
        for f in ("SUM(壁面積!B2:B4)", "SUBTOTAL(9,壁面積!B2:B4)", "壁面積!B4+壁面積!B3+壁面積!B2"):
            got, r = read(xlsx([("壁面積", wall), a, board(f, 220)]))
            self.assertEqual(got, {("m_board", "m2"): 220.0}, f)
            x, = ex(r, "間仕切B")
            self.assertFalse(x["maybe"], (f, x["reason"]))
            self.assertIn("別のシート（間仕切A）の材料の行（2 行目）が足し上げたセル（壁面積 B2:B4）", x["reason"])
        # rounded to another value (220.875 → 221): perhaps another quantity; the value itself, a sure copy
        frac = row(1, t("A1", "室名"), t("B1", "壁面積")) + row(2, t("A2", "事務室"), n("B2", 120.25)) + \
            row(3, t("A3", "会議室"), n("B3", 40.5)) + row(4, t("A4", "廊下"), n("B4", 60.125))
        a2 = ("間仕切A", HDR + mrow(2, "石膏ボード", "t12.5", n("C2", 220.875, "SUM(壁面積!B2:B4)"), "m2"))
        for f, q, sure in (("ROUND(SUM(壁面積!B2:B4),0)", 221, False), ("SUM(壁面積!B2:B4)", 220.875, True)):
            got, r = read(xlsx([("壁面積", frac), a2, board(f, q)]))
            self.assertEqual(got, {("m_board", "m2"): 220.875}, f)
            x, = ex(r, "間仕切B")
            self.assertEqual(x["maybe"], not sure, (f, x["reason"]))

    # --- the attack on the round-16 fixes: a copy of a row reading a take-off's pivot table
    def test_a_copy_of_a_pivot_reading_row_is_sure_when_its_field_is_counted(self):
        take = row(1, t("A1", "部位"), t("B1", "材料"), t("C1", "体積")) + row(2, t("A2", "柱"), t("B2", "コンクリート"), n("C2", 60)) + \
            row(3, t("A3", "梁"), t("B3", "コンクリート"), n("C3", 90))
        piv = row(3, t("A3", "行ラベル"), t("B3", "合計 / 体積")) + row(4, t("A4", "コンクリート"), n("B4", 150)) + \
            row(5, t("A5", "総計"), n("B5", 150))

        def go(bill, readers, copy=("コンクリート", "まとめ!B2", 150, "m3")):
            sheets = [("拾い", take), ("集計", piv)] + ([("明細", HDR + bill)] if bill else []) + \
                [("まとめ", summary(*readers)), ("総括", summary(copy))]
            return read(book(sheets, [(1, "ピボット1", "A3:B5", "拾い", "A1:C3")]))
        one = [("コンクリート", "集計!B4", 150, "m3")]
        many = [("コンクリート", "集計!B4", 150, "m3"), ("コンクリート", "集計!B5", 150, "m3")]
        typed = mrow(2, "普通コンクリート", "Fc24", n("C2", 150), "m3")
        reach = mrow(2, "普通コンクリート", "Fc24", n("C2", 150, "SUM(拾い!C2:C3)"), "m3")
        # the field of the row read from the pivot table is counted in the bill (typed, or summing the take-off): the
        # pivot table's value may repeat that count, so the copy is a sure copy of the row left out, as in 94bf205 —
        # one row "may belong" on the card, not two (the branch said "add one of them by hand")
        for bill in (typed, reach):
            for readers in (one, many):
                for f in ("まとめ!B2", "まとめ!B2*1", "ROUND(まとめ!B2,0)"):
                    got, r = go(bill, readers, ("コンクリート", f, 150, "m3"))
                    self.assertEqual(got, {("m_concrete", "m3"): 150.0})
                    x, = ex(r, "総括")
                    self.assertFalse(x["maybe"], (f, x["reason"]))
                    self.assertIn("別のシート（まとめ）の材料の行（2 行目）の数量を参照した値は足さない（そのシートも読んでいる", x["reason"])
                    self.assertTrue(all(y["maybe"] for y in ex(r, "まとめ")))
                    self.assertEqual(r["evidence"]["m_concrete"]["n_maybe"], len(readers))
        # its field counted nowhere (only the other field of concrete, or another material from the take-off), or the
        # row reads the take-off too: the quantity may be counted nowhere, so the copy may belong (16 回目)
        for bill, readers in ((mrow(2, "基礎コンクリート", "Fc21", n("C2", 40), "m3"), one),
                              (mrow(2, "異形鉄筋", "SD345", n("C2", 18, "SUM(拾い!C2:C3)*0.12"), "t"), one),
                              (None, [("コンクリート", "集計!B4+拾い!C3", 240, "m3")])):
            got, r = go(bill, readers, ("コンクリート", "まとめ!B2", readers[0][2], "m3"))
            self.assertNotIn(("m_concrete", "m3"), got)
            x, = ex(r, "総括")
            self.assertTrue(x["maybe"] and "足していない" in x["reason"], x)

    # --- the attack on the round-16 fixes: a justified / aside row still reads the pivot table's cell
    def test_a_justified_or_aside_row_still_reads_the_cell_of_the_pivot_table(self):
        take = row(1, t("A1", "部位"), t("B1", "材料"), t("C1", "体積")) + row(2, t("A2", "柱"), t("B2", "コンクリート"), n("C2", 60)) + \
            row(3, t("A3", "梁"), t("B3", "コンクリート"), n("C3", 90))
        piv = row(3, t("A3", "行ラベル"), t("B3", "合計 / 体積")) + row(4, t("A4", "コンクリート"), n("B4", 150)) + \
            row(5, t("A5", "総計"), n("B5", 150))

        def go(*rows):
            return read(book([("拾い", take), ("集計", piv), ("まとめ", summary(*rows))], [(1, "ピボット1", "A3:B5", "拾い", "A1:C3")]))
        conc = ("コンクリート", "集計!B4", 150, "m3")
        # another row reads the same cell (or a block holding it): the concrete row is not the only reader of it, and
        # stays "may belong" as in 94bf205 (the branch added it and said the take-off was counted nowhere else)
        for other, why in ((("鉄　　筋", "集計!B4*0.12", 18, "t"), documents.R_JUSTIFIED_MAYBE),
                           (("鉄　　骨", "SUM(集計!B4:B5)", 300, "t"), documents.R_JUSTIFIED_MAYBE),
                           (("Infill panels, without frames, blockwork 100mm", "集計!B4", 150, "m2"), documents.R_ASIDE_MAYBE)):
            for rows in ((conc, other), (other, conc)):
                got, r = go(*rows)
                self.assertEqual(got, {}, other[0])
                xs = ex(r, "まとめ")
                self.assertEqual([x["maybe"] for x in xs], [True, True])
                self.assertEqual(sorted(x["reason"] == why for x in xs), [False, True])
                self.assertFalse([w for w in r["warnings"] if "足した" in w])
        # it reads another cell: the concrete row is still the only reader of its cell, added as before
        got, r = go(conc, ("鉄　　筋", "集計!B5*0.12", 18, "t"))
        self.assertEqual(got, {("m_concrete", "m3"): 150.0})


if __name__ == "__main__":
    unittest.main()
