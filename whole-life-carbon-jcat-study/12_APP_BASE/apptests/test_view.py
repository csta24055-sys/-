"""System 4: result display. Every figure shown must come from the engine's results."""
import copy
import re
import unittest

from lcaapp import render, view
from . import helpers as H


def page_for(t, run_id):
    return render.run_page(t.service.run_page(run_id))


class ViewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc, cls.ref, cls.md = H.building(rows=None)
        cls.results = H.direct_results(cls.md, 62.5)
        cls.view = view.build(cls.results, 62.5, {"data_kind": "fictional", "included_stages": cls.md["boundary"]["included_lifecycle_stages"]})

    def test_indicators_are_read_from_the_results(self):
        ind = {i["key"]: i for i in self.view["indicators"]}
        r = self.results
        self.assertEqual(ind["whole_life"]["value"], r["SUM-03"]["value"])
        self.assertEqual(ind["upfront"]["value"], r["SUM-01"]["value"])
        self.assertEqual(ind["embodied"]["value"], r["SUM-02"]["value"])
        self.assertEqual(ind["operational"]["value"], r["X-02"]["by_stage"]["B6"] + r["X-02"]["by_stage"]["B7"])
        self.assertAlmostEqual(ind["operational"]["value"] + ind["embodied"]["value"], ind["whole_life"]["value"],
                               delta=1e-9 * ind["whole_life"]["value"])
        self.assertEqual(ind["per_area"]["value"], r["SUM-04"]["value"])
        self.assertEqual(ind["per_area_year"]["value"], r["SUM-05"]["value"])
        self.assertEqual(ind["tonnes"]["value"], r["SUM-06"]["value"])
        self.assertTrue(all(i["status"] == "ok" and i["source"] for i in self.view["indicators"]))
        self.assertEqual([s["stage"] for s in self.view["stages"]], list(r["X-02"]["by_stage"]))
        self.assertEqual([s["value"] for s in self.view["stages"]], list(r["X-02"]["by_stage"].values()))
        self.assertEqual([s["share"] for s in self.view["stages"]], list(r["SUM-07"]["by_stage"].values()))
        self.assertEqual(self.view["series"]["by_year"], r["X-07"]["by_year"])
        self.assertEqual(self.view["series"]["cumulative"], r["X-07"]["cumulative"])
        self.assertEqual(len(self.view["series"]["by_year"]), 64)                       # years 0 .. ceil(62.5)
        self.assertEqual(self.view["study_period"], 62.5)

    def test_missing_results_are_shown_as_not_computed(self):
        r = copy.deepcopy(self.results)
        r["SUM-04"]["value"] = None
        r["SUM-05"] = {}
        del r["SUM-06"]
        del r["X-07"]
        r["X-02"]["by_stage"]["B6"] = None
        r["SUM-07"]["defined"] = False
        shown = view.build(r, 62.5, {})
        ind = {i["key"]: i for i in shown["indicators"]}
        for key in ("per_area", "per_area_year", "tonnes", "operational"):
            self.assertEqual((ind[key]["status"], ind[key]["value"]), ("not_computed", None), key)
        self.assertIsNone(shown["series"])
        self.assertTrue(all(s["share"] is None for s in shown["stages"]))
        empty = view.build({}, 10.0, {})                                                # nothing at all: nothing is shown as a number
        self.assertTrue(all(i["status"] == "not_computed" for i in empty["indicators"]))
        self.assertEqual((empty["stages"], empty["series"]), ([], None))
        for bad in ("12", True, float("nan"), [1]):
            self.assertEqual(view._indicator("k", "l", bad, "u", "s")["status"], "not_computed")
        self.assertEqual(render.fmt(None), "未計算")
        self.assertEqual(render.fmt(float("nan")), "未計算")
        self.assertEqual(render.percent(None), "未計算")

    def test_incomplete_totals_are_marked(self):
        doc, ref, md = H.building(seed=77, structure="W", use="residential", dirty=True, rows=None)
        results = H.direct_results(md, 60.0)
        self.assertFalse(results["SUM-03"]["complete"])
        shown = view.build(results, 60.0, {"data_kind": "fictional"})
        ind = {i["key"]: i for i in shown["indicators"]}
        self.assertEqual(ind["whole_life"]["status"], "incomplete")
        self.assertEqual(ind["whole_life"]["value"], results["SUM-03"]["value"])
        self.assertFalse(shown["complete"])
        self.assertTrue(shown["skipped"])
        self.assertTrue(any("不完全" in n["text"] for n in shown["notes"]))
        failed = [c for c in shown["checks"] if c["ok"] is False]
        self.assertTrue(failed)
        self.assertTrue(all(c["n"] is None or c["n"] > 0 for c in failed))
        self.assertTrue(any(c["n"] for c in failed))

    def test_number_formatting(self):
        self.assertEqual(render.fmt(14056668.52824422), "14,056,669")
        self.assertEqual(render.fmt(80.33942896473725), "80.34")
        self.assertEqual(render.fmt(0.0), "0")
        self.assertEqual(render.fmt(-0.00001, 2), "0.00")
        self.assertEqual(render.fmt(-1234.5), "-1,234")
        self.assertEqual(render.percent(0.3213198649503485), "32.1%")
        self.assertEqual(render.nice_ticks(0, 14056668)[-1], 15000000)
        self.assertEqual(render.nice_ticks(0, 20840262)[-1], 25000000)
        flat = render.nice_ticks(0, 0)                                                    # a flat series still gets an axis
        self.assertEqual((flat[0], round(flat[-1], 9), len(flat)), (0.0, 1.0, 6))

    def test_result_page_shows_the_stored_figures(self):
        with H.TempStore() as t:
            t.service.register_refset(self.ref)
            out = t.service.import_document(H.through_json(self.doc), name="表示の試験 <script>alert(1)</script>")
            run = t.service.calculate(out["project_id"], 62.5)
            html = page_for(t, run["id"])
            r = self.results
            for value in (r["SUM-03"]["value"], r["SUM-01"]["value"], r["SUM-02"]["value"], r["SUM-04"]["value"],
                          r["SUM-05"]["value"], r["SUM-06"]["value"]):
                self.assertIn(render.fmt(value), html)
            for stage, value in r["X-02"]["by_stage"].items():
                self.assertIn(render.fmt(value), html, stage)
            for value in r["X-07"]["cumulative"]:
                self.assertIn(render.fmt(value), html)                                   # table view of the time series
            self.assertEqual(html.count("<svg"), 3)
            self.assertEqual(len(re.findall(r'class="hit"[^>]*data-cy=', html)), 64)     # one read-out per year
            self.assertIn("評価期間 62.5 年", html)
            self.assertIn("架空データ（検証用）", html)
            self.assertIn("独立概念モデル", html)
            self.assertNotIn("<script>alert(1)</script>", html)                          # text from the input is escaped
            self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
            self.assertIn("未計算。基準案を指定していない", html)

    def test_page_of_a_run_without_results_shows_no_numbers(self):
        doc, ref, _ = H.building()
        H.set_item(doc, "project", "project.use_area_breakdown", None)
        with H.TempStore() as t:
            t.service.register_refset(ref)
            out = t.service.import_document(H.through_json(doc))
            run = t.service.calculate(out["project_id"], 60)
            self.assertEqual((run["status"], run["view"], run["has_results"]), ("blocked", None, False))
            html = page_for(t, run["id"])
            self.assertIn("計算していない", html)
            self.assertIn("project.use_area_breakdown", html)
            self.assertIn("すべて未計算", html)
            self.assertNotIn("<svg", html)
            self.assertNotIn("kg-CO2e/m2", html)

    def test_charts_handle_edge_series(self):
        for by_year in ([5.0], [0.0, 0.0], [10.0, -4.0, 3.0], [1e-9, 2e-9], [3.0] * 131):
            cumulative = [sum(by_year[:k + 1]) for k in range(len(by_year))]
            series = {"by_year": by_year, "cumulative": cumulative}
            for svg in (render.chart_cumulative(series, "kg-CO2e"), render.chart_yearly(series, "kg-CO2e")):
                self.assertTrue(svg.startswith("<svg") and svg.endswith("</svg>"))
                self.assertNotIn("nan", svg.lower())
                self.assertNotIn("inf", svg.lower())
        stages = [{"stage": "A1-A3", "label": "x", "value": -5.0, "share": None, "included": True},
                  {"stage": "B6", "label": "y", "value": 0.0, "share": None, "included": False},
                  {"stage": "C4", "label": "z", "value": None, "share": None, "included": None}]
        svg = render.chart_stages(stages, "kg-CO2e")
        self.assertIn("未計算", svg)
        self.assertIn("（対象外）", svg)
        self.assertNotIn("nan", svg.lower())
        self.assertEqual(render.chart_stages([dict(stages[2])], "kg-CO2e"), "")
        self.assertIn("負の値", render.split_bar({"value": -1.0}, {"value": 2.0}))
        self.assertIn("未計算", render.split_bar({"value": None}, {"value": 2.0}))


if __name__ == "__main__":
    unittest.main()
