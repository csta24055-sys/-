"""Round 16 (bridge / server): with an equipment count 未取得, the hint names the 未取得 life (B4) and mass (C3) of the same
row at once, and with the rebuild scenario 未取得 the 未取得 cycle and share (B5), as the refrigerant parts of B1 since
round 13 — the stages stay as marked, only the named inputs grow; with no range ends to show, the range note does not
speak of ends; the evaluation boundary, the use and the floor area cannot be 適用外 (refused on save; a stored one is
read as 未取得 by the bridge and the progress of the inputs); a text over 500 characters is refused with the reason
instead of being cut.

Run: cd whole-life-carbon-jcat-study && python3 -B -m unittest discover -s 23_WLC_STUDIO_APP/tests -q
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
os.environ.setdefault("WLCSTUDIO_OFFLINE", "1")
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from wlcstudio import bridge, fields as FL  # noqa: E402
from wlcstudio.project import ProjectError  # noqa: E402
from wlcstudio.provenance import Uncertainty, Value  # noqa: E402
from wlcstudio.server import ApiError, App, AppWorker, make_handler  # noqa: E402

REFSET = json.loads((HERE.parent / "12_APP_BASE" / "samples" / "refset_fictional.json").read_text(encoding="utf-8"))


def V(fid, value=None, state="confirmed", unit=None, **kw):
    F = FL.FIELDS[fid]
    kw.setdefault("method", "test")
    return Value(fid, state, value, unit if unit is not None else F.get("unit", ""), **kw)


def A(fid, value, unit=None, **kw):
    """An assumed value (no stated range unless given)."""
    return V(fid, value, "assumption", unit, **kw)


def NA(fid):
    return V(fid, None, "not_applicable")


def complete(**over) -> dict:
    """The round-11 complete baseline (every screen field, all confirmed; the materials not named are 適用外); `over`
    replaces or (None) drops fields (a dropped field is 未取得)."""
    v = {"b_use": V("b_use", "office"), "b_gfa": V("b_gfa", 1000.0), "a_stages": V("a_stages", "ALL"),
         "a_eol_route": V("a_eol_route", "LANDFILL"), "m_rebar": V("m_rebar", 10.0, unit="t"),
         "m_waste_rate": V("m_waste_rate", 0.05), "m_reuse_rate": V("m_reuse_rate", 0.1),
         "o_grid_value": V("o_grid_value", 0.4), "o_grid_construction": V("o_grid_construction", 0.4),
         "o_water_m3": V("o_water_m3", 1000.0), "o_sewage_m3": V("o_sewage_m3", 900.0), "o_waste_kg": V("o_waste_kg", 5000.0),
         "m_quantity_basis": V("m_quantity_basis", "DESIGN"), "m_repair_rate": V("m_repair_rate", 0.01),
         "m_refresh_cycle": V("m_refresh_cycle", 30.0), "a_eol_haul_km": V("a_eol_haul_km", 20.0),
         "a_reconstruction": V("a_reconstruction", "NONE"), "c_site_electricity": V("c_site_electricity", 1000.0),
         "c_diesel": V("c_diesel", 500.0), "e_repair_rate": V("e_repair_rate", 0.01),
         "r_charge_kg": V("r_charge_kg", 20.0), "r_gwp": V("r_gwp", 2000.0), "r_leak_rate": V("r_leak_rate", 0.03),
         "r_loss_rate": V("r_loss_rate", 0.05), "r_recovery_rate": V("r_recovery_rate", 0.5), "r_life": V("r_life", 15.0),
         "r_top_up": V("r_top_up", "yes"), "o_elec_kwh": V("o_elec_kwh", 100000.0), "o_fm_ratio": V("o_fm_ratio", 0.1),
         "m_transport_km": V("m_transport_km", 50.0), "m_transport_mode": V("m_transport_mode", "TRUCK_LARGE"),
         "b_name": V("b_name", "r16"), "b_address": V("b_address", "somewhere"), "b_structure": V("b_structure", "RC"),
         "b_floors_above": V("b_floors_above", 5), "b_floors_below": V("b_floors_below", 1), "b_height": V("b_height", 20.0),
         "b_footprint": V("b_footprint", 300.0), "b_completion_year": V("b_completion_year", 2026),
         "b_project_type": V("b_project_type", "NEW_BUILD"), "g_foundation": V("g_foundation", "PILE"),
         "g_borehole": V("g_borehole", "note"), "a_replacement_cycle": V("a_replacement_cycle", 40.0),
         "a_recon_fraction": V("a_recon_fraction", 0.5), "o_source": V("o_source", "BILLS"),
         "m_steel": V("m_steel", 5.0, unit="t"), "m_aluminium": V("m_aluminium", 1.0, unit="t"),
         "m_plastic": V("m_plastic", 0.5, unit="t"), "m_mortar": V("m_mortar", 3.0, unit="t"),
         "o_gas_m3": V("o_gas_m3", 2000.0), "o_oil_l": V("o_oil_l", 100.0), "o_dheat_mj": V("o_dheat_mj", 5000.0),
         "o_pv_kwh": NA("o_pv_kwh"), "o_export_kwh": NA("o_export_kwh")}
    for t, _ in FL.TRADES:
        k = t.lower()
        v["e_%s_count" % k] = V("e_%s_count" % k, 2.0)
        v["e_%s_life" % k] = V("e_%s_life" % k, 15.0)
        v["e_%s_mass" % k] = V("e_%s_mass" % k, 100.0)
    for f, *_ in FL.MATERIALS:
        v.setdefault(f, NA(f))
    v.update(over)
    return {k: x for k, x in v.items() if x is not None}


def detail(rep_or_out, fid) -> str:
    rows = rep_or_out["fields"] if "detail" in (rep_or_out["fields"] or [{}])[0] else bridge.reflection_table(rep_or_out)
    return {r["field"]: r["detail"] for r in rows}[fid]


def gaps(rep) -> dict:
    return {m["field"]: m["stages"] for m in rep["missing_inputs"]}


def hint(out, stage) -> list:
    return ({h["stage"]: h for h in out["summary"]["hints"]}.get(stage) or {}).get("fields", [])


class SixteenthRoundBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.TemporaryDirectory()
        cls.app = App(cls.td.name)
        cls.E = cls.app.engine

    @classmethod
    def tearDownClass(cls):
        cls.app.engine.close()
        cls.app.projects.close()
        cls.td.cleanup()

    def project(self, vals):
        pid = self.app.projects.create("r16", "RC")
        for v in vals.values():
            self.app.projects.put(pid, v)
        return pid

    def calc(self, vals, T=60):
        pid = self.project(vals)
        _, out = self.app.handle("POST", "/api/projects/%d/calculate" % pid, {"period": T})
        return pid, out

    def put(self, pid, fid, body):
        return self.app.handle("PUT", "/api/projects/%d/fields/%s" % (pid, fid), body)

    def total(self, vals, T=60.0):
        doc, rep = bridge.build(vals, REFSET, period=T)
        self.assertEqual(rep["missing_required"], [])
        return self.E.run(doc, None, T)["results"]["SUM-03"]["value"]

    def assertSameMarks(self, a, b, T=60.0):
        """Two value sets give the same document (the same total) and the same stage marks; only the gaps may differ."""
        doc_a, rep_a = bridge.build(a, REFSET, period=T, today="2026-01-01")
        doc_b, rep_b = bridge.build(b, REFSET, period=T, today="2026-01-01")
        for k in ("incomplete_stages", "assumed_stages", "split_stages", "expand", "missing_required"):
            self.assertEqual(rep_a[k], rep_b[k], k)
        return rep_a, rep_b

    # --- sweep#0: an equipment count 未取得 names the 未取得 life and mass that its stages need as well
    def test_equipment_count_unknown_names_its_life_and_mass_at_once(self):
        L = {p: FL.FIELDS["e_hvac_%s" % p]["label"] for p in ("count", "life", "mass")}
        vals = complete(e_hvac_count=None, e_hvac_life=None, e_hvac_mass=None)
        _, rep = bridge.build(vals, REFSET, period=60.0)
        g = gaps(rep)
        self.assertEqual(g["e_hvac_count"], ["A1-A3", "B3", "B4", "C3"])
        self.assertEqual(g["e_hvac_life"], ["B4"])
        self.assertEqual(g["e_hvac_mass"], ["B4", "C3"])
        for f in ("e_hvac_life", "e_hvac_mass"):                    # still not passed (no count): said so on the row
            self.assertEqual(detail(rep, f), "台数が無いので渡していない")
        _, out = self.calc(vals)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(hint(out, "B4"), [L["count"], L["life"], L["mass"]])
        self.assertEqual(hint(out, "C3"), [L["count"], L["mass"]])
        self.assertEqual({m["field"] for m in out["omitted_inputs"]} >= {"e_hvac_count", "e_hvac_life", "e_hvac_mass"}, True)
        # the stages stay as the count marks them: the same marks as with the life and the mass known
        self.assertSameMarks(vals, complete(e_hvac_count=None))
        # entering what the hints name changes B4 and C3 (entering only the count did not complete them)
        only_count = dict(vals, e_hvac_count=V("e_hvac_count", 2.0))
        _, rep1 = bridge.build(only_count, REFSET, period=60.0)
        self.assertEqual(gaps(rep1)["e_hvac_life"], ["B4"])
        self.assertEqual(gaps(rep1)["e_hvac_mass"], ["B4", "C3"])
        self.assertGreater(self.total(complete()), self.total(only_count) + 1.0)
        # each part only when it is missing and its stage can act: a life 適用外 (never renewed) is no gap and keeps B4
        # out of the count's stages; a mass known (also 0) is no gap; outside the boundary nothing is named
        for name, over, life, mass in (
                ("life known", dict(e_hvac_life=V("e_hvac_life", 15.0)), None, ["B4", "C3"]),
                ("life 適用外", dict(e_hvac_life=NA("e_hvac_life")), None, ["C3"]),
                ("mass known", dict(e_hvac_mass=V("e_hvac_mass", 100.0)), ["B4"], None),
                ("mass 0", dict(e_hvac_mass=V("e_hvac_mass", 0.0)), ["B4"], None),
                ("both known", dict(e_hvac_life=V("e_hvac_life", 15.0), e_hvac_mass=V("e_hvac_mass", 100.0)), None, None),
                ("life 計算不能", dict(e_hvac_life=V("e_hvac_life", None, "not_computable")), ["B4"], ["B4", "C3"])):
            with self.subTest(name):
                v2 = dict(vals, **over)
                _, rep2 = bridge.build(v2, REFSET, period=60.0)
                g2 = gaps(rep2)
                self.assertEqual(g2.get("e_hvac_life"), life)
                self.assertEqual(g2.get("e_hvac_mass"), mass)
                if name == "life 計算不能":
                    self.assertIn("計算不能", next(m["reason"] for m in rep2["missing_inputs"] if m["field"] == "e_hvac_life"))
        for preset, life, mass in (("EMBODIED", None, None), ("UPFRONT_EOL", None, ["C3"]), ("NO_OPERATION", ["B4"], ["B4", "C3"])):
            with self.subTest(preset=preset):
                _, rep3 = bridge.build(dict(vals, a_stages=V("a_stages", preset)), REFSET, period=60.0)
                self.assertEqual(gaps(rep3).get("e_hvac_life"), life)
                self.assertEqual(gaps(rep3).get("e_hvac_mass"), mass)
        # a count 適用外 (no such equipment) names nothing of the row
        _, rep4 = bridge.build(dict(vals, e_hvac_count=NA("e_hvac_count")), REFSET, period=60.0)
        self.assertFalse({"e_hvac_count", "e_hvac_life", "e_hvac_mass"} & set(gaps(rep4)))

    # --- sweep#0: the rebuild scenario 未取得 names the 未取得 cycle and share that B5 needs as well
    def test_rebuild_scenario_unknown_names_its_cycle_and_share_at_once(self):
        L = {f: FL.FIELDS[f]["label"] for f in ("a_reconstruction", "a_replacement_cycle", "a_recon_fraction")}
        vals = complete(a_reconstruction=None, a_replacement_cycle=None, a_recon_fraction=None)
        _, rep = bridge.build(vals, REFSET, period=60.0)
        g = gaps(rep)
        for f in L:
            self.assertEqual(g[f], ["B5"], f)
        for f in ("a_replacement_cycle", "a_recon_fraction"):           # still not passed (no scenario)
            self.assertIn("想定が未取得", detail(rep, f))
        _, out = self.calc(vals)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(hint(out, "B5"), list(L.values()))
        self.assertSameMarks(vals, complete(a_reconstruction=None))
        # what the hint names completes B5 (entering only the scenario left the total as it was)
        only_rec = dict(vals, a_reconstruction=V("a_reconstruction", "REBUILD_IDENTICAL"))
        self.assertAlmostEqual(self.total(only_rec), self.total(vals), delta=1e-6)
        self.assertGreater(self.total(complete(a_reconstruction=V("a_reconstruction", "REBUILD_IDENTICAL"))), self.total(vals) + 1.0)
        # only what is missing, and only while the cycle can fall inside T and the share is not 0
        for name, over, T, need in (
                ("cycle known", dict(a_replacement_cycle=V("a_replacement_cycle", 40.0)), 60.0, {"a_reconstruction", "a_recon_fraction"}),
                ("share known", dict(a_recon_fraction=V("a_recon_fraction", 0.5)), 60.0, {"a_reconstruction", "a_replacement_cycle"}),
                ("cycle beyond T", dict(a_replacement_cycle=V("a_replacement_cycle", 80.0)), 60.0, set()),
                ("share 0", dict(a_recon_fraction=V("a_recon_fraction", 0.0)), 60.0, set()),
                ("share 適用外", dict(a_recon_fraction=NA("a_recon_fraction")), 60.0, set()),
                ("short study period, cycle unknown", {}, 14.0, set(L))):
            with self.subTest(name):
                _, rep2 = bridge.build(dict(vals, **over), REFSET, period=T)
                self.assertEqual(set(gaps(rep2)) & set(L), need)
        _, rep3 = bridge.build(dict(vals, a_stages=V("a_stages", "EMBODIED")), REFSET, period=60.0)
        self.assertFalse(set(gaps(rep3)) & set(L))
        # the scenario given: the cycle and the share are named by the rule for an active scenario (as before)
        _, rep4 = bridge.build(only_rec, REFSET, period=60.0)
        self.assertEqual(set(gaps(rep4)) & set(L), {"a_replacement_cycle", "a_recon_fraction"})

    # --- sweep#1: with no range ends, the range note does not speak of two ends or of an upper end
    def test_range_note_speaks_of_ends_only_when_ends_are_shown(self):
        typed = {k: (A(k, v.value, v.unit) if v.state == "confirmed" and k != "a_stages" and v.value is not None else v)
                 for k, v in complete(m_steel=None).items()}
        _, out = self.calc(typed)
        self.assertTrue(out["summary"]["lower_bound"])
        rg = out["range"]
        self.assertIsNone(rg["low_t"])
        self.assertTrue(rg["lower_bound"])
        self.assertTrue(rg["note"].endswith("入っていない入力があるので、合計は下限。"), rg["note"])
        self.assertNotIn("両端", rg["note"])
        self.assertNotIn("上端", rg["note"])
        # with ends shown, the screen labels them 「範囲（両端とも下限）」: the note adds only what the label does not say
        ranged = dict(typed, m_rebar=A("m_rebar", 10.0, "t", uncertainty=Uncertainty("scenario", 8.0, 12.0)))
        _, out = self.calc(ranged)
        rg = out["range"]
        self.assertIsNotNone(rg["low_t"])
        self.assertLess(rg["low_t"], rg["high_t"])
        self.assertTrue(rg["lower_bound"])
        self.assertTrue(rg["note"].endswith("入っていない入力があるので、本当の合計は上端より大きいことがある。"), rg["note"])
        self.assertNotIn("両端とも下限", rg["note"])
        # an end that cannot be computed (no ends either): the same words as with no range
        pid = self.project(typed)
        orig = self.app._range
        self.app._range = lambda *a, **k: {"low_t": None, "high_t": None, "n_values_with_range": 1, "n_values_range_unknown": 0,
                                           "unknown_fields": [], "note": "範囲のある 1 項目を下端にすると計算できない（x）ので、合計の幅は示せない。"}
        try:
            _, out = self.app.handle("POST", "/api/projects/%d/calculate" % pid, {"period": 60})
        finally:
            self.app._range = orig
        self.assertEqual(out["range"]["note"], "範囲のある 1 項目を下端にすると計算できない（x）ので、合計の幅は示せない。"
                                               "入っていない入力があるので、合計は下限。")

    # --- sweep#2: the boundary, the use and the floor area cannot be 適用外
    def test_required_fields_cannot_be_not_applicable(self):
        meta = self.app.meta()["fields"]
        for fid in ("a_stages", "b_use", "b_gfa"):
            with self.subTest(fid):
                self.assertTrue(FL.FIELDS[fid].get("na_never"))
                self.assertTrue(meta[fid]["na_never"])                  # the screen offers no 適用外 button
                pid = self.project(complete())
                p0 = self.app.projects.progress(pid)
                with self.assertRaises(ApiError) as e:
                    self.put(pid, fid, {"state": "not_applicable"})
                self.assertEqual(e.exception.status, 400)
                self.assertEqual(str(e.exception), "「%s」は「適用外」にできない（無いということが無い項目）。分からないときは"
                                                   "「未取得」のままにする" % FL.FIELDS[fid]["label"])
                self.assertNotEqual(self.app.projects.current(pid, fid).state, "not_applicable")
                # 未取得 is still accepted
                self.assertEqual(self.put(pid, fid, {"state": "not_obtained"})[0], 200)
                p1 = self.app.projects.progress(pid)
                # a 適用外 stored before the refusal (an older project) is read as 未取得: not filled, calculation blocked
                self.app.projects.put(pid, NA(fid))
                p2 = self.app.projects.progress(pid)
                self.assertEqual(p2["filled"], p0["filled"] - 1)
                self.assertEqual(p2["filled"], p1["filled"])
                self.assertEqual(p2["not_obtained"], p1["not_obtained"])
                self.assertEqual(p2["not_applicable"], p0["not_applicable"])
                self.assertEqual(p2["by_screen"]["basic"], p1["by_screen"]["basic"])
                _, out = self.app.handle("POST", "/api/projects/%d/calculate" % pid, {"period": 60})
                self.assertEqual(out["status"], "blocked")
                self.assertEqual(out["missing_required"], ["評価範囲（ライフサイクル段階）"] if fid == "a_stages"
                                 else ["用途と延床面積（用途別面積はエンジンの必須入力）"])
                row = detail(out, fid)
                self.assertTrue(row.startswith(bridge.NA_NEVER_WORD), row)
                self.assertNotIn("未設定", row)
        # the other fields that cannot be absent: a stored 適用外 is not counted as filled either
        pid = self.project(complete())
        p0 = self.app.projects.progress(pid)
        for fid in ("m_transport_km", "a_eol_haul_km", "r_gwp"):
            self.app.projects.put(pid, NA(fid))
        self.assertEqual(self.app.projects.progress(pid)["filled"], p0["filled"] - 3)
        # a field whose 適用外 is a real state is still counted as filled
        self.app.projects.put(pid, NA("b_floors_below"))
        self.assertEqual(self.app.projects.progress(pid)["filled"], p0["filled"] - 3)
        # the rebuild cycle (cannot be absent) stored as 適用外 with a rebuild assumed: missing, said as such
        _, rep = bridge.build(complete(a_reconstruction=V("a_reconstruction", "REBUILD_IDENTICAL"),
                                       a_replacement_cycle=NA("a_replacement_cycle")), REFSET, period=60.0)
        self.assertTrue(detail(rep, "a_replacement_cycle").startswith(bridge.NA_NEVER_WORD))
        self.assertEqual(gaps(rep)["a_replacement_cycle"], ["B5"])

    # --- ui-flows#2 (server side): a text over 500 characters is refused with the reason, not cut
    def test_long_text_is_refused_with_the_reason_not_cut(self):
        pid = self.project(complete())
        for fid in ("b_name", "b_address", "g_borehole"):
            with self.subTest(fid):
                label = FL.FIELDS[fid]["label"]
                before = self.app.projects.current(pid, fid).value
                with self.assertRaises(ProjectError) as e:
                    self.put(pid, fid, {"state": "confirmed", "value": "あ" * 501})
                self.assertEqual(str(e.exception), "「%s」は 500 字までで入れる（いまは 501 字）" % label)
                self.assertEqual(self.app.projects.current(pid, fid).value, before)          # nothing stored
                _, out = self.put(pid, fid, {"state": "confirmed", "value": "い" * 500})
                self.assertEqual(out["value"], "い" * 500)
                # the spaces at both ends are not part of the text (as before)
                _, out = self.put(pid, fid, {"state": "assumption", "value": "  " + "う" * 500 + "\n"})
                self.assertEqual(out["value"], "う" * 500)
        # a candidate with a text over the limit is not proposed (the check before storing names the reason)
        with self.assertRaises(ProjectError):
            self.app.projects.validate(V("b_address", "x" * 600, method="plateau_attribute"))
        # over HTTP the refusal is a 400 with the reason as the error (as the other refusals)
        import http.client
        import threading
        from http.server import HTTPServer
        w = AppWorker(Path(self.td.name) / "http")
        try:
            _, made = w.handle("POST", "/api/projects", {"name": "r16", "structure": "RC"})
            httpd = HTTPServer(("127.0.0.1", 0), make_handler(w, 0))
            port = httpd.server_address[1]
            httpd.RequestHandlerClass = make_handler(w, port)
            th = threading.Thread(target=httpd.handle_request)
            th.start()
            try:
                c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
                body = json.dumps({"state": "confirmed", "value": "え" * 691}).encode("utf-8")
                c.request("PUT", "/api/projects/%d/fields/g_borehole" % made["id"], body=body,
                          headers={"Host": "127.0.0.1:%d" % port, "Content-Type": "application/json"})
                r = c.getresponse()
                status, payload = r.status, json.loads(r.read().decode("utf-8"))
                c.close()
            finally:
                th.join()
                httpd.server_close()
        finally:
            w.stop()
        self.assertEqual(status, 400)
        self.assertEqual(payload, {"error": "「%s」は 500 字までで入れる（いまは 691 字）" % FL.FIELDS["g_borehole"]["label"]})


if __name__ == "__main__":
    unittest.main()
