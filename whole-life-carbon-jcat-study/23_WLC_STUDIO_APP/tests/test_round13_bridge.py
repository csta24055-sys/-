"""Round 13 (bridge / server): a value that is surely 0 (or a choice) whose required partner is 未取得 / 適用外 is not
counted when every other value of it would refuse the calculation — a purchase of 0 or a site electricity of 0 with its
factor not given, a material quantity of 0 or the quantity basis with the route not given; a quantity of 0 next to a
whole-building / all-steel figure (any other value is dropped as double counting) is not counted; an accepted 適用外 of
the grid factors is not described as impossible, and the help texts say the cases the save accepts; with the
refrigerant charge unknown, every unknown part that B1 needs is named; an assumption that appears only at one end of a
range is said in the range; a save that makes a stored 適用外 unusable says so in its response (warnings).

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
from wlcstudio.provenance import Uncertainty, Value  # noqa: E402
from wlcstudio.server import App  # noqa: E402

REFSET = json.loads((HERE.parent / "12_APP_BASE" / "samples" / "refset_fictional.json").read_text(encoding="utf-8"))
MASS = ("m_rebar", "m_steel", "m_aluminium", "m_plastic", "m_mortar")


def V(fid, value=None, state="confirmed", unit=None, **kw):
    F = FL.FIELDS[fid]
    kw.setdefault("method", "test")
    return Value(fid, state, value, unit if unit is not None else F.get("unit", ""), **kw)


def A(fid, value, unit=None):
    """An assumed value (no stated range)."""
    return V(fid, value, "assumption", unit)


def R(fid, value, lo, hi, unit=None):
    """An assumed value with a stated scenario range."""
    return V(fid, value, "assumption", unit, uncertainty=Uncertainty("scenario", lo, hi))


def NA(fid):
    return V(fid, None, "not_applicable")


def WHOLE(fid, value, lo, hi, scope, unit="t"):
    """A statistical estimate that covers more than its field (whole building / all steel)."""
    return Value(fid, "statistical", value, unit, method="test_estimate", source_id="TEST", factor_version="v", scope=scope,
                 uncertainty=Uncertainty("interval", lo, hi, 0.9))


def complete(**over) -> dict:
    """The round-11 complete baseline (every screen field, all confirmed); `over` replaces or (None) drops fields."""
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
         "b_name": V("b_name", "r13"), "b_address": V("b_address", "somewhere"), "b_structure": V("b_structure", "RC"),
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


VOLUME_ONLY = dict(m_concrete=V("m_concrete", 500.0, unit="m3"), m_glass=V("m_glass", 300.0, unit="m2"),
                   m_timber=V("m_timber", 20.0, unit="m3"), **{f: NA(f) for f in MASS})
OTHER_MASS_NA = {f: NA(f) for f in MASS if f != "m_rebar"}


class ThirteenthRoundBridgeTests(unittest.TestCase):
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
        pid = self.app.projects.create("r13", "RC")
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

    def estimated(self, rep):
        return {f["field"] for f in rep["fields"] if f["reflected"] and f["state"] in ("statistical", "assumption")
                and f["field"] not in bridge.TOTAL_NEUTRAL}

    def assertNotCounted(self, vals, fids, T=60, partner=None):
        """The fields are reported not reflected (naming the unknown partner when given), nothing is counted as an
        estimate, and the range names no unknown width and no 「範囲のある」 item."""
        _, rep = bridge.build(vals, REFSET, period=T)
        r = refl(rep)
        for f in fids:
            self.assertFalse(r[f], (f, detail(rep, f)))
            if partner:
                self.assertIn(partner, detail(rep, f), f)
        self.assertEqual(self.estimated(rep), set())
        self.assertEqual(rep["n_estimated"], 0)
        _, out = self.calc(vals, T)
        self.assertEqual(out["status"], "ok", out.get("message"))
        self.assertFalse((out["range"] or {}).get("unknown_fields"))
        self.assertFalse((out["range"] or {}).get("n_values_with_range"))
        self.assertIn("統計推定・仮定が 0 項目", out["reflection"]["summary"])
        return rep, out

    def assertRefused(self, vals, why):
        """Every such value refuses the calculation (a required input is missing), naming why."""
        _, rep = bridge.build(vals, REFSET, period=60.0)
        self.assertTrue(rep["missing_required"])
        self.assertIn(why, "、".join(rep["missing_required"]))

    def assertSameTotal(self, variants, T=60.0):
        totals = [self.total(v, T) for v in variants]
        for t in totals[1:]:
            self.assertAlmostEqual(t, totals[0], delta=1e-6 * abs(totals[0]))
        return totals[0]

    # --- sweep#1: a 0 / a choice whose required partner is not given, when every other value refuses the calculation
    def test_zero_decider_whose_required_partner_is_not_given_is_not_counted(self):
        # (a) / (b) a purchase / site electricity of 0 with its factor 未取得 or 適用外 (the mirror of round 12)
        for qty, factor, presets, partner, why in (
                ("o_elec_kwh", "o_grid_value", ("ALL",), "運用時の電力の排出係数", "運用時の電力の排出係数"),
                ("c_site_electricity", "o_grid_construction", ("EMBODIED", "ALL"), "工事中の電力の排出係数", "工事中の電力の排出係数")):
            for preset in presets:
                for fstate in (None, NA(factor)):
                    with self.subTest(qty=qty, preset=preset, factor=fstate and fstate.state):
                        vals = complete(**{"a_stages": V("a_stages", preset), qty: A(qty, 0.0), factor: fstate})
                        self.assertNotCounted(vals, [qty], partner=partner)
                        for x in (1.0, 100000.0):
                            self.assertRefused(dict(vals, **{qty: V(qty, x)}), why)
        # (c) a material quantity of 0 with the route not given, and no row with an end-of-life mass
        for preset in ("ALL", "NO_OPERATION", "UPFRONT_EOL"):
            for route in (None, NA("a_eol_route")):
                with self.subTest(preset=preset, route=route and route.state):
                    vals = complete(a_stages=V("a_stages", preset), m_rebar=A("m_rebar", 0.0, "t"), a_eol_route=route,
                                    **OTHER_MASS_NA)
                    self.assertNotCounted(vals, ["m_rebar"], partner="解体後の処理シナリオ")
                    self.assertRefused(dict(vals, m_rebar=V("m_rebar", 10.0, unit="t")), "解体後の処理シナリオ")
        # (d) the quantity basis with the waste rate and the route not given: DESIGN refuses, AS_BUILT reads as ORDERED
        vals = complete(m_quantity_basis=A("m_quantity_basis", "ORDERED"), m_waste_rate=None, a_eol_route=None)
        self.assertNotCounted(vals, ["m_quantity_basis"], partner="解体後の処理シナリオ")
        self.assertRefused(dict(vals, m_quantity_basis=V("m_quantity_basis", "DESIGN")), "解体後の処理シナリオ")
        self.assertSameTotal([vals, dict(vals, m_quantity_basis=V("m_quantity_basis", "AS_BUILT"))])
        # controls: with the partner given the same values decide and move the total
        for vals, fid, other in ((complete(o_elec_kwh=A("o_elec_kwh", 0.0)), "o_elec_kwh", V("o_elec_kwh", 100000.0)),
                                 (complete(c_site_electricity=A("c_site_electricity", 0.0)), "c_site_electricity",
                                  V("c_site_electricity", 1000.0)),
                                 (complete(m_rebar=A("m_rebar", 0.0, "t"), **OTHER_MASS_NA), "m_rebar",
                                  V("m_rebar", 10.0, unit="t")),
                                 (complete(m_quantity_basis=A("m_quantity_basis", "ORDERED"), m_waste_rate=None),
                                  "m_quantity_basis", V("m_quantity_basis", "DESIGN"))):
            with self.subTest(control=fid):
                _, rep = bridge.build(vals, REFSET, period=60)
                self.assertEqual(self.estimated(rep), {fid})
                self.assertNotAlmostEqual(self.total(vals), self.total(dict(vals, **{fid: other})), places=0)

    # --- sweep#2: a quantity of 0 whose every other value would be dropped as double counting
    def test_zero_quantity_inside_a_whole_building_or_all_steel_figure_is_not_counted(self):
        cases = [("m_concrete_fdn", "m3", 100.0, {"m_concrete": WHOLE("m_concrete", 1200.0, 800.0, 1500.0, "whole_building")}),
                 ("m_steel", "t", 5.0, {"m_rebar": WHOLE("m_rebar", 40.0, 30.0, 50.0, "all_steel")}),
                 ("m_rebar", "t", 10.0, {"m_steel": WHOLE("m_steel", 40.0, 30.0, 50.0, "all_steel")})]
        for fid, unit, other, whole in cases:
            with self.subTest(fid):
                vals = complete(**dict(whole, **{fid: A(fid, 0.0, unit)}))
                _, rep = bridge.build(vals, REFSET, period=60)
                self.assertFalse(refl(rep)[fid], detail(rep, fid))
                self.assertIn("二重計上", detail(rep, fid))
                self.assertNotIn(fid, self.estimated(rep))
                _, out = self.calc(vals)
                self.assertEqual(out["status"], "ok")
                self.assertNotIn(fid, out["range"]["unknown_fields"])
                self.assertSameTotal([vals, dict(vals, **{fid: V(fid, other, unit=unit)})])
        # control: next to a figure of the field alone, the 0 decides that the material is absent and moves the total
        vals = complete(m_concrete=V("m_concrete", 1200.0, unit="t"), m_concrete_fdn=A("m_concrete_fdn", 0.0, "m3"))
        _, rep = bridge.build(vals, REFSET, period=60)
        self.assertEqual(self.estimated(rep), {"m_concrete_fdn"})
        self.assertNotAlmostEqual(self.total(vals), self.total(dict(vals, m_concrete_fdn=V("m_concrete_fdn", 100.0, unit="m3"))),
                                  places=0)

    # --- sweep#3: an accepted 適用外 is not described as impossible; the help texts say what the save accepts
    def test_accepted_not_applicable_is_described_as_accepted(self):
        for qty, factor, stage in (("o_elec_kwh", "o_grid_value", "B6"), ("c_site_electricity", "o_grid_construction", "A5")):
            pid = self.project(complete())
            self.assertEqual(self.put(pid, qty, {"state": "not_obtained"})[0], 200)
            self.assertEqual(self.put(pid, factor, {"state": "not_applicable"})[0], 200, factor)
            _, out = self.app.handle("POST", "/api/projects/%d/calculate" % pid, {"period": 60})
            self.assertEqual(out["status"], "ok")
            gap = {m["field"]: m for m in out["missing_inputs"]}[factor]
            self.assertNotIn("0 にできない", gap["reason"])
            self.assertIn("0・適用外でなければ係数が要る", gap["reason"])
            note = {h["stage"]: h["note"] for h in out["summary"]["hints"]}[stage]
            self.assertNotIn("0 にできない", note)
        # every case named in the help texts is one the save accepts
        self.assertIn("未取得", FL.FIELDS["o_grid_value"]["help"])
        self.assertIn("未取得", FL.FIELDS["o_grid_construction"]["help"])
        self.assertIn("m3・m2", FL.FIELDS["a_eol_route"]["help"])
        self.assertIn("廃棄率が未取得", FL.FIELDS["a_eol_route"]["help"])
        for factor, ctx in (("o_grid_value", dict(o_elec_kwh=None)), ("o_grid_value", dict(o_elec_kwh=NA("o_elec_kwh"))),
                            ("o_grid_value", dict(a_stages=V("a_stages", "EMBODIED"))),
                            ("o_grid_construction", dict(c_site_electricity=None)),
                            ("o_grid_construction", dict(c_site_electricity=NA("c_site_electricity"))),
                            ("a_eol_route", dict(a_stages=V("a_stages", "EMBODIED"))),
                            ("a_eol_route", dict(VOLUME_ONLY)),
                            ("a_eol_route", dict(m_quantity_basis=V("m_quantity_basis", "ORDERED"), m_waste_rate=None))):
            with self.subTest(factor=factor, ctx=sorted(ctx)):
                pid = self.project(complete(**ctx))
                self.assertEqual(self.put(pid, factor, {"state": "not_applicable"})[0], 200)

    # --- sweep#4: with the refrigerant charge unknown, every unknown part that B1 needs is named at once
    def test_refrigerant_charge_unknown_names_every_part_b1_needs(self):
        cases = [("GWP", dict(r_gwp=None), {"r_charge_kg", "r_gwp"}),
                 ("leak rate", dict(r_leak_rate=None), {"r_charge_kg", "r_leak_rate"}),
                 ("loss and recovery", dict(r_leak_rate=V("r_leak_rate", 0.0), r_loss_rate=None, r_recovery_rate=None,
                                            r_top_up=V("r_top_up", "no")), {"r_charge_kg", "r_loss_rate", "r_recovery_rate"})]
        for name, over, need in cases:
            with self.subTest(name):
                vals = complete(r_charge_kg=None, **over)
                _, out = self.calc(vals)
                self.assertEqual(out["status"], "ok")
                b1 = {m["field"] for m in out["omitted_inputs"] if "B1" in m["stages"]}
                self.assertEqual(b1, need)
                hint = {h["stage"]: h for h in out["summary"]["hints"]}["B1"]
                self.assertEqual(set(hint["fields"]), {FL.FIELDS[f]["label"] for f in need})
                # entering what the hint names completes B1 (entering only the charge did not change it)
                filled = dict(vals, **{f: complete()[f] for f in need})
                self.assertGreater(self.total(filled), self.total(vals) + 1.0)
        # control: the charge known, the GWP unknown: only the GWP is named (as before)
        _, out = self.calc(complete(r_gwp=None))
        self.assertEqual({m["field"] for m in out["omitted_inputs"] if "B1" in m["stages"]}, {"r_gwp"})

    # --- sweep#0: an assumption that appears only at one end of a range is said in the range
    def test_zero_km_range_says_the_assumption_at_its_upper_end(self):
        for name, extra, mode_named in (("mass rows, mode unknown", {"m_transport_mode": None}, True),
                                        ("m3 / m2 rows, mode given", VOLUME_ONLY, False)):
            with self.subTest(name):
                _, out = self.calc(complete(m_transport_km=R("m_transport_km", 0.0, 0.0, 100.0), **extra))
                self.assertEqual(out["summary"]["assumed_stages"], [])          # the value is 0 km: A4 = 0, nothing assumed
                gaps = out["range"]["end_gaps"]
                self.assertEqual(len(gaps), 1, gaps)
                self.assertTrue(gaps[0].startswith("上端では仮定で計算した分がある"), gaps)
                self.assertIn("配送原単位", gaps[0])
                self.assertEqual("運搬手段が未取得" in gaps[0], mode_named, gaps)
                self.assertIn(gaps[0], out["range"]["note"])
        # control: with the mode given, the mass rows are carried by tonne-km at the upper end: nothing is assumed
        _, out = self.calc(complete(m_transport_km=R("m_transport_km", 0.0, 0.0, 100.0)))
        self.assertEqual(out["range"]["end_gaps"], [])
        self.assertGreater(out["range"]["high_t"], out["range"]["low_t"])

    # --- ui-flows#1: a save that makes a stored 適用外 unusable says so (the response carries warnings)
    def test_put_warns_when_a_stored_not_applicable_becomes_unusable(self):
        cases = [("o_grid_value", dict(o_elec_kwh=V("o_elec_kwh", 0.0)), "o_elec_kwh", {"state": "confirmed", "value": 1000},
                  "購入電力がある"),
                 ("o_grid_construction", dict(c_site_electricity=V("c_site_electricity", 0.0)), "c_site_electricity",
                  {"state": "confirmed", "value": 500}, "工事中の電力がある"),
                 ("a_eol_route", dict(VOLUME_ONLY), "m_rebar", {"state": "confirmed", "value": 10, "unit": "t"},
                  "質量が分かる材料の行があり")]
        for fid, ctx, other, body, why in cases:
            with self.subTest(fid):
                pid = self.project(complete(**ctx))
                st, out = self.put(pid, fid, {"state": "not_applicable"})
                self.assertEqual(st, 200)
                self.assertNotIn("warnings", out)
                st, out = self.put(pid, other, body)
                self.assertEqual(st, 200)
                self.assertEqual(self.app.projects.current(pid, other).state, "confirmed")       # the save itself is kept
                self.assertEqual(len(out["warnings"]), 1, out.get("warnings"))
                w = out["warnings"][0]
                self.assertTrue(w.startswith("「%s」の「適用外」は、いまの入力では使えない" % FL.FIELDS[fid]["label"]), w)
                self.assertIn(why, w)
                self.assertIn("計算は止まる", w)
                # the calculation stops for the same reason
                _, res = self.app.handle("POST", "/api/projects/%d/calculate" % pid, {"period": 60})
                self.assertEqual(res["status"], "blocked")
                # a save that makes it usable again carries no warning
                self.put(pid, other, {"state": "not_applicable"})
                st, out = self.put(pid, "o_gas_m3", {"state": "confirmed", "value": 2100})
                self.assertNotIn("warnings", out)
        # no stored 適用外: no warnings key at all (the response is the stored value as before)
        pid = self.project(complete())
        st, out = self.put(pid, "o_elec_kwh", {"state": "confirmed", "value": 123})
        self.assertEqual((st, out["value"]), (200, 123))
        self.assertNotIn("warnings", out)


if __name__ == "__main__":
    unittest.main()
