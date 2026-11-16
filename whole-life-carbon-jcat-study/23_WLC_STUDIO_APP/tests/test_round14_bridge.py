"""Round 14 (bridge / server): a material quantity of 0 is judged over every unit the field accepts (0 t and 0 m3 are the
same nil quantity: it is not counted only when no accepted unit would let a value other than 0 act); adopting a
candidate says the same warnings as a PUT; a warning is said only by the save that makes a stored 適用外 unusable; a
whole-building / all-steel figure that is surely 0 covers nothing (it drops no value typed in the other field); with the
boundary unknown, a stored 適用外 of the grid factors and the route is described as depending on the boundary, not as
impossible.

Run: cd whole-life-carbon-jcat-study && python3 -B -m unittest discover -s 23_WLC_STUDIO_APP/tests -q
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
os.environ.setdefault("WLCSTUDIO_OFFLINE", "1")
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from wlcstudio import bridge, fields as FL  # noqa: E402
from wlcstudio.provenance import Uncertainty, Value  # noqa: E402
from wlcstudio.server import App  # noqa: E402

REFSET = json.loads((HERE.parent / "12_APP_BASE" / "samples" / "refset_fictional.json").read_text(encoding="utf-8"))
MASS = ("m_rebar", "m_steel", "m_aluminium", "m_plastic", "m_mortar")
VOLUME_FIELDS = [f for f, *_ in FL.MATERIALS if FL.FIELDS[f]["unit"] in ("m3", "m2")]


def V(fid, value=None, state="confirmed", unit=None, **kw):
    F = FL.FIELDS[fid]
    kw.setdefault("method", "test")
    return Value(fid, state, value, unit if unit is not None else F.get("unit", ""), **kw)


def A(fid, value, unit=None, **kw):
    """An assumed value (no stated range)."""
    return V(fid, value, "assumption", unit, **kw)


def NA(fid):
    return V(fid, None, "not_applicable")


def complete(**over) -> dict:
    """The round-11 complete baseline (every screen field, all confirmed; the materials not named are 適用外); `over`
    replaces or (None) drops fields."""
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
         "b_name": V("b_name", "r14"), "b_address": V("b_address", "somewhere"), "b_structure": V("b_structure", "RC"),
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


def refl(rep_or_out) -> dict:
    return {f["field"]: f["reflected"] for f in rep_or_out["fields"]}


def detail(rep_or_out, fid) -> str:
    rows = rep_or_out["fields"] if "detail" in (rep_or_out["fields"] or [{}])[0] else bridge.reflection_table(rep_or_out)
    return {r["field"]: r["detail"] for r in rows}[fid]


ALL_MATERIALS_NA = {f: NA(f) for f, *_ in FL.MATERIALS}
VOLUME_ONLY = dict(m_concrete=V("m_concrete", 500.0, unit="m3"), m_glass=V("m_glass", 300.0, unit="m2"),
                   m_timber=V("m_timber", 20.0, unit="m3"), **{f: NA(f) for f in MASS})


class FourteenthRoundBridgeTests(unittest.TestCase):
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
        pid = self.app.projects.create("r14", "RC")
        for v in vals.values():
            self.app.projects.put(pid, v)
        return pid

    def calc(self, vals, T=60):
        pid = self.project(vals)
        _, out = self.app.handle("POST", "/api/projects/%d/calculate" % pid, {"period": T})
        return pid, out

    def put(self, pid, fid, body):
        return self.app.handle("PUT", "/api/projects/%d/fields/%s" % (pid, fid), body)

    def accept(self, pid, fid, v):
        cid = self.app.projects.propose(pid, v, "test")
        return self.app.handle("POST", "/api/projects/%d/fields/%s/accept" % (pid, fid), {"id": cid})

    def total(self, vals, T=60.0):
        doc, rep = bridge.build(vals, REFSET, period=T)
        if rep["missing_required"]:
            return None
        return self.E.run(doc, None, T)["results"]["SUM-03"]["value"]

    def estimated(self, rep):
        return {f["field"] for f in rep["fields"] if f["reflected"] and f["state"] in ("statistical", "assumption")
                and f["field"] not in bridge.TOTAL_NEUTRAL}

    # --- sweep#0: a nil material quantity is judged over every unit the field accepts, not by the unit stored with it
    def test_nil_material_quantity_is_judged_over_every_accepted_unit(self):
        # (a) round 13's rule (the route not given and no row with an end-of-life mass): a value in t / kg would need the
        # route, but a value in the field's m3 / m2 runs and moves the total, so a 0 in any unit counts
        ctx_a = dict(ALL_MATERIALS_NA, m_glass=V("m_glass", 300.0, unit="m2"), a_eol_route=None)
        # (b) the round-12 mirror (the waste rate not given, DESIGN): a value in m3 / m2 acts on no stage, one in t does
        ctx_b = dict(ALL_MATERIALS_NA, m_waste_rate=None)
        for name, ctx, acting, blocked in (("route not given", ctx_a, "m3", "t"), ("waste rate not given", ctx_b, "t", "m3")):
            for fid in VOLUME_FIELDS:
                if fid == "m_glass" and ctx is ctx_a:
                    continue
                own = FL.FIELDS[fid]["unit"]
                for u0 in FL.FIELDS[fid]["units"]:
                    with self.subTest(name, fid=fid, unit=u0):
                        vals = complete(**dict(ctx, **{fid: A(fid, 0.0, u0)}))
                        _, rep = bridge.build(vals, REFSET, period=60)
                        self.assertTrue(refl(rep)[fid], detail(rep, fid))
                        self.assertIn(fid, self.estimated(rep))
                        # the reason names the unit that acts
                        self.assertIn("%s なら合計に効く" % (own if acting == "m3" else "t・kg"), detail(rep, fid))
        # the totals behind it (one field of each kind): the acting unit moves the total, the other does not
        for name, ctx, fid, act, other in (("route not given", ctx_a, "m_concrete", "m3", "t"),
                                           ("route not given", ctx_a, "m_finish", "m2", "kg"),
                                           ("waste rate not given", ctx_b, "m_concrete", "t", "m3"),
                                           ("waste rate not given", ctx_b, "m_glass", "t", "m2")):
            with self.subTest(name, fid=fid):
                vals = complete(**dict(ctx, **{fid: A(fid, 0.0, other)}))
                base = self.total(vals)
                self.assertGreater(self.total(dict(vals, **{fid: V(fid, 10.0, unit=act)})), base + 1.0)
                t_other = self.total(dict(vals, **{fid: V(fid, 10.0, unit=other)}))
                self.assertTrue(t_other is None or abs(t_other - base) < 1e-6 * base, (t_other, base))
                # the same nil quantity stored in either unit is counted the same way
                _, rep1 = bridge.build(vals, REFSET, period=60)
                _, rep2 = bridge.build(dict(vals, **{fid: A(fid, 0.0, act)}), REFSET, period=60)
                self.assertEqual(self.estimated(rep1), self.estimated(rep2))
                _, out = self.calc(vals)
                self.assertEqual(out["status"], "ok")
                self.assertIn(fid, out["range"]["unknown_fields"])
        # (c) no accepted unit acts: still not counted, whatever the unit stored with the 0 (one reason per unit kind)
        for name, ctx, why in (
                ("EMBODIED, waste rate not given", dict(ALL_MATERIALS_NA, m_waste_rate=None, a_stages=V("a_stages", "EMBODIED")),
                 "0 でない数量でもこの材料の行は評価範囲のどの段階も計算できない"),
                ("route not given, waste rate not given", dict(ctx_a, m_waste_rate=None),
                 "0 でない数量はどの単位でも、合計を変えないか計算が止まる")):
            for u0 in ("m3", "t"):
                with self.subTest(name, unit=u0):
                    vals = complete(**dict(ctx, m_concrete=A("m_concrete", 0.0, u0)))
                    _, rep = bridge.build(vals, REFSET, period=60)
                    self.assertFalse(refl(rep)["m_concrete"], detail(rep, "m_concrete"))
                    self.assertIn(why, detail(rep, "m_concrete"))
                    self.assertNotIn("m_concrete", self.estimated(rep))
                    base = self.total(vals)
                    for u in FL.FIELDS["m_concrete"]["units"]:
                        t1 = self.total(dict(vals, m_concrete=V("m_concrete", 10.0, unit=u)))
                        self.assertTrue(t1 is None or abs(t1 - base) < 1e-6 * base, (u, t1, base))
        # control: a mass field (t / kg only) whose units all need the route is not counted, as in round 13
        vals = complete(m_rebar=A("m_rebar", 0.0, "kg"), a_eol_route=None, **{f: NA(f) for f in MASS if f != "m_rebar"})
        _, rep = bridge.build(vals, REFSET, period=60)
        self.assertFalse(refl(rep)["m_rebar"])
        self.assertIn("解体後の処理シナリオ", detail(rep, "m_rebar"))

    # --- sweep#1: adopting a candidate says the warnings of a save
    def test_accepting_a_candidate_says_the_warnings_of_a_save(self):
        # the route: only m3 / m2 rows, 適用外 accepted; a document candidate of rebar in t makes it unusable
        pid = self.project(complete(**VOLUME_ONLY))
        st, out = self.put(pid, "a_eol_route", {"state": "not_applicable"})
        self.assertEqual(st, 200)
        self.assertNotIn("warnings", out)
        st, out = self.accept(pid, "m_rebar", Value("m_rebar", "from_drawing", 30.0, "t", method="document",
                                                     source_id="doc1-test.csv", source_detail="Sheet1!B5"))
        self.assertEqual(st, 200)
        self.assertEqual((out["value"], out["state"]), (30.0, "from_drawing"))          # the accept itself is kept
        self.assertEqual(len(out.get("warnings") or []), 1, out.get("warnings"))
        self.assertTrue(out["warnings"][0].startswith("「解体後の処理（シナリオ）」の「適用外」は、いまの入力では使えない"))
        _, res = self.app.handle("POST", "/api/projects/%d/calculate" % pid, {"period": 60})
        self.assertEqual(res["status"], "blocked")
        # the grid factor: 適用外 with the purchase unknown; a statistical purchase makes it unusable
        pid = self.project(complete(o_elec_kwh=None))
        self.assertEqual(self.put(pid, "o_grid_value", {"state": "not_applicable"})[0], 200)
        st, out = self.accept(pid, "o_elec_kwh", Value("o_elec_kwh", "statistical", 120000.0, "kWh/年", method="stat_test",
                                                       source_id="test-src", factor_version="v",
                                                       uncertainty=Uncertainty("interval", 80000.0, 160000.0, 0.9)))
        self.assertEqual(st, 200)
        self.assertEqual(len(out.get("warnings") or []), 1, out.get("warnings"))
        self.assertTrue(out["warnings"][0].startswith("「運用時の電力の排出係数」の「適用外」は、いまの入力では使えない"))
        # an adoption that leaves the stored 適用外 usable says nothing
        pid = self.project(complete(**VOLUME_ONLY))
        self.assertEqual(self.put(pid, "a_eol_route", {"state": "not_applicable"})[0], 200)
        st, out = self.accept(pid, "m_glass", Value("m_glass", "from_drawing", 320.0, "m2", method="document",
                                                     source_id="doc1-test.csv", source_detail="Sheet1!B6"))
        self.assertEqual(st, 200)
        self.assertNotIn("warnings", out)

    # --- sweep#2: the warning is said by the save that makes the 適用外 unusable, not by every later save
    def test_the_warning_is_said_only_by_the_save_that_makes_it_unusable(self):
        pid = self.project(complete(o_elec_kwh=V("o_elec_kwh", 0.0)))
        self.assertNotIn("warnings", self.put(pid, "o_grid_value", {"state": "not_applicable"})[1])
        st, out = self.put(pid, "o_elec_kwh", {"state": "confirmed", "value": 1000})
        self.assertEqual(len(out["warnings"]), 1)
        # later saves that leave it unusable (it was so before them) say nothing, by PUT or by adopting a candidate
        for fid, body in (("b_name", {"state": "confirmed", "value": "renamed"}), ("o_gas_m3", {"state": "confirmed", "value": 2100}),
                          ("m_rebar", {"state": "confirmed", "value": 11, "unit": "t"}),
                          ("o_elec_kwh", {"state": "confirmed", "value": 1001}), ("b_name", {"state": "not_obtained"})):
            with self.subTest(fid=fid, body=body):
                st, out = self.put(pid, fid, body)
                self.assertEqual(st, 200)
                self.assertNotIn("warnings", out)
        st, out = self.accept(pid, "m_steel", Value("m_steel", "from_drawing", 6.0, "t", method="document",
                                                     source_id="doc1-test.csv", source_detail="Sheet1!B7"))
        self.assertEqual(st, 200)
        self.assertNotIn("warnings", out)
        # usable again, then unusable again: said again
        self.assertNotIn("warnings", self.put(pid, "o_elec_kwh", {"state": "confirmed", "value": 0})[1])
        self.assertEqual(len(self.put(pid, "o_elec_kwh", {"state": "confirmed", "value": 5})[1]["warnings"]), 1)
        # with two stored 適用外, only the one this save makes unusable is said
        pid = self.project(complete(o_elec_kwh=V("o_elec_kwh", 0.0), c_site_electricity=V("c_site_electricity", 0.0)))
        for f in ("o_grid_value", "o_grid_construction"):
            self.assertEqual(self.put(pid, f, {"state": "not_applicable"})[0], 200)
        self.assertEqual(len(self.put(pid, "o_elec_kwh", {"state": "confirmed", "value": 1000})[1]["warnings"]), 1)
        out = self.put(pid, "c_site_electricity", {"state": "confirmed", "value": 500})[1]
        self.assertEqual(len(out["warnings"]), 1)
        self.assertTrue(out["warnings"][0].startswith("「工事中の電力の排出係数」"), out["warnings"])
        # the cost: a save with stored 適用外 builds the bridge twice (before and after); it stays a few ms
        t0 = time.perf_counter()
        for i in range(20):
            self.put(pid, "o_gas_m3", {"state": "confirmed", "value": 2001 + i})
        self.assertLess((time.perf_counter() - t0) / 20, 0.5)

    # --- sweep#3: a whole-building / all-steel figure that is surely 0 covers nothing
    def test_a_whole_figure_of_zero_covers_nothing(self):
        for whole_f, scope, other, unit, x in (("m_concrete", "whole_building", "m_concrete_fdn", "m3", 100.0),
                                               ("m_rebar", "all_steel", "m_steel", "t", 5.0),
                                               ("m_steel", "all_steel", "m_rebar", "t", 10.0)):
            with self.subTest(whole_f):
                zero_whole = A(whole_f, 0.0, unit, scope=scope)
                zero_field = A(whole_f, 0.0, unit)
                vals = complete(**{whole_f: zero_whole, other: A(other, x, unit)})
                _, rep = bridge.build(vals, REFSET, period=60)
                self.assertTrue(refl(rep)[other], detail(rep, other))
                self.assertEqual(rep["double_count"], [])
                self.assertTrue(any("0 なのに" in s for s in rep["inconsistent_inputs"]), rep["inconsistent_inputs"])
                # the value typed in the other field is in the total, as next to a 0 of the field alone
                self.assertAlmostEqual(self.total(vals), self.total(dict(vals, **{whole_f: zero_field})), places=3)
                self.assertGreater(self.total(vals), self.total(dict(vals, **{other: NA(other)})) + 1.0)
                # a 0 next to it is counted (a value other than 0 is not dropped), and an unknown is a gap, not covered
                vals0 = dict(vals, **{other: A(other, 0.0, unit)})
                _, rep = bridge.build(vals0, REFSET, period=60)
                self.assertTrue(refl(rep)[other], detail(rep, other))
                self.assertNotIn("二重計上", detail(rep, other))
                valsu = complete(**{whole_f: zero_whole, other: None})
                _, rep = bridge.build(valsu, REFSET, period=60)
                self.assertIn(other, {m["field"] for m in rep["omitted_inputs"]})
                # control: a whole figure whose range reaches above 0 still covers the other field
                ranged = A(whole_f, 0.0, unit, scope=scope, uncertainty=Uncertainty("scenario", 0.0, 1000.0))
                _, rep = bridge.build(dict(vals, **{whole_f: ranged}), REFSET, period=60)
                self.assertFalse(refl(rep)[other])
                self.assertIn("二重計上", detail(rep, other))

    # --- ui-flows#7: with the boundary unknown, a stored 適用外 is described as depending on the boundary
    def test_not_applicable_with_the_boundary_unknown_depends_on_the_boundary(self):
        cases = [("o_grid_value", dict(o_elec_kwh=V("o_elec_kwh", 1000.0)), "ALL", "EMBODIED", "評価範囲で決まる"),
                 ("o_grid_construction", dict(c_site_electricity=V("c_site_electricity", 1000.0)), "EMBODIED", None,
                  "まだ判定していない"),
                 ("a_eol_route", dict(m_rebar=V("m_rebar", 10.0, unit="t")), "ALL", "EMBODIED", "評価範囲で決まる"),
                 ("a_eol_route", dict(VOLUME_ONLY), None, "ALL", "まだ判定していない")]
        for fid, ctx, refusing, accepting, says in cases:
            with self.subTest(fid=fid, ctx=sorted(ctx)):
                pid = self.project(complete(**ctx))
                self.assertEqual(self.put(pid, "a_stages", {"state": "not_obtained"})[0], 200)
                st, out = self.put(pid, fid, {"state": "not_applicable"})
                self.assertEqual(st, 200)                                   # the save keeps accepting it
                self.assertNotIn("warnings", out)
                _, res = self.app.handle("POST", "/api/projects/%d/calculate" % pid, {"period": 60})
                self.assertEqual(res["status"], "blocked")
                d = detail(res, fid)
                self.assertNotIn("適用外にはできない", d)
                self.assertTrue(d.startswith("評価範囲が未取得なので、この適用外"), d)
                self.assertIn(says, d)
                _, rep = bridge.build(self.app.projects.values(pid), REFSET)
                self.assertEqual(rep["na_refused"], {})
                # setting the boundary: a warning exactly when that boundary makes it unusable
                for preset in (accepting, refusing):
                    if preset is None:
                        continue
                    st, out = self.put(pid, "a_stages", {"state": "confirmed", "value": preset})
                    self.assertEqual(st, 200)
                    self.assertEqual(bool(out.get("warnings")), preset == refusing, (preset, out.get("warnings")))
                    if preset == refusing:
                        self.assertIn("いまの入力では使えない", out["warnings"][0])
        # the help texts say that the save accepts it while the boundary is unknown
        for f in ("o_grid_value", "o_grid_construction", "a_eol_route"):
            self.assertIn("評価範囲が未取得の間も受け", FL.FIELDS[f]["help"])
        # control: with the boundary known, the calculation still says it cannot be 適用外 (and the save refuses it)
        pid = self.project(complete(o_elec_kwh=V("o_elec_kwh", 0.0)))
        self.put(pid, "o_grid_value", {"state": "not_applicable"})
        self.put(pid, "o_elec_kwh", {"state": "confirmed", "value": 1000})
        _, res = self.app.handle("POST", "/api/projects/%d/calculate" % pid, {"period": 60})
        self.assertTrue(detail(res, "o_grid_value").startswith("適用外にはできない（購入電力があるので"))


if __name__ == "__main__":
    unittest.main()
