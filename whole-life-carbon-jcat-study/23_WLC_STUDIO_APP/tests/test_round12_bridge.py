"""Round 12 (bridge / server): an input is counted as an estimate only when some value of it can change the total with the
other inputs as they are, and two inputs that make each other moot count neither — the waste rate with the quantity basis
unknown, the refrigerant values that make B1 0 with a partner unknown, a factor of 0 with its quantity unknown, a quantity
of 0 that could not act; a distance whose value is 0 gives A4 = 0 also with a range; a corrected estimate saved as
confirmed is not a 「範囲が不明」 item; the end-of-life hints of m3 / m2 rows name only what can complete them; 適用外 is
refused, with the reason, where the calculation needs the value; a record-only edit does not make the result stale.

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
from wlcstudio.server import ApiError, App  # noqa: E402

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
         "b_name": V("b_name", "r12"), "b_address": V("b_address", "somewhere"), "b_structure": V("b_structure", "RC"),
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


class TwelfthRoundBridgeTests(unittest.TestCase):
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
        pid = self.app.projects.create("r12", "RC")
        for v in vals.values():
            self.app.projects.put(pid, v)
        return pid

    def calc(self, vals, T=60):
        pid = self.project(vals)
        _, out = self.app.handle("POST", "/api/projects/%d/calculate" % pid, {"period": T})
        return pid, out

    def put(self, pid, fid, body):
        return self.app.handle("PUT", "/api/projects/%d/fields/%s" % (pid, fid), body)

    def result(self, pid):
        return self.app.handle("GET", "/api/projects/%d/result" % pid, None)[1]

    def stages(self, out):
        return {x["stage"]: x for x in out["summary"]["stages"]}

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

    def assertSameTotal(self, variants, T=60.0):
        totals = [self.total(v, T) for v in variants]
        for t in totals[1:]:
            self.assertAlmostEqual(t, totals[0], delta=1e-6 * abs(totals[0]))
        return totals[0]

    # --- sweep#0: the quantity basis unknown is read like ORDERED: the waste rate acts only through the installed mass
    def test_waste_rate_with_the_basis_unknown_is_not_an_estimate(self):
        for preset, extra in (("EMBODIED", {}), ("ALL", VOLUME_ONLY)):
            def ctx(w):
                return complete(a_stages=V("a_stages", preset), m_quantity_basis=None, m_waste_rate=w, **extra)
            rep, _ = self.assertNotCounted(ctx(A("m_waste_rate", 0.05)), ["m_waste_rate"], partner="数量の基準が未取得")
            self.assertIn("m_quantity_basis", {m["field"] for m in rep["omitted_inputs"]}, preset)    # the basis stays the gap
            self.assertNotCounted(ctx(A("m_waste_rate", 0.0)), ["m_waste_rate"])
            self.assertSameTotal([ctx(A("m_waste_rate", x)) for x in (0.0, 0.05, 0.3, 0.9)])
        # control: with design quantities the rate orders Q/(1-w): it is counted and moves the total
        vals = complete(a_stages=V("a_stages", "EMBODIED"), m_waste_rate=A("m_waste_rate", 0.05))
        _, rep = bridge.build(vals, REFSET, period=60)
        self.assertEqual(self.estimated(rep), {"m_waste_rate"})
        self.assertGreater(self.total(dict(vals, m_waste_rate=V("m_waste_rate", 0.3))), self.total(vals) + 1.0)
        # control: basis unknown with mass rows and the end-of-life stages: the installed mass Q(1-w) moves the total
        vals = complete(m_quantity_basis=None, m_waste_rate=A("m_waste_rate", 0.05))
        _, rep = bridge.build(vals, REFSET, period=60)
        self.assertIn("m_waste_rate", self.estimated(rep))
        self.assertNotAlmostEqual(self.total(vals), self.total(dict(vals, m_waste_rate=V("m_waste_rate", 0.3))), places=0)

    # --- sweep#1: a refrigerant value that makes B1 0 counts only when the inputs it multiplies are known
    def test_refrigerant_b1_zero_deciders_with_an_unknown_partner_are_not_counted(self):
        b1z = dict(r_leak_rate=A("r_leak_rate", 0.0), r_loss_rate=A("r_loss_rate", 0.0), r_recovery_rate=A("r_recovery_rate", 1.0))
        cases = [
            # (name, values, fields not counted, partner named, T, alternative values that give the same total)
            ("GWP 0, charge unknown", complete(r_gwp=A("r_gwp", 0.0), r_charge_kg=None), ["r_gwp"], "充填量", 60,
             [{"r_gwp": V("r_gwp", 500.0)}, {"r_gwp": V("r_gwp", 2000.0)}]),
            ("GWP 0, leak rate unknown", complete(r_gwp=A("r_gwp", 0.0), r_leak_rate=None), ["r_gwp"], "漏えい率", 60,
             [{"r_gwp": V("r_gwp", 2000.0)}]),
            ("GWP 0, top-up unknown", complete(r_gwp=A("r_gwp", 0.0), r_top_up=None), ["r_gwp"], "補充の有無", 60,
             [{"r_gwp": V("r_gwp", 2000.0)}]),
            ("charge 0, GWP unknown", complete(r_charge_kg=A("r_charge_kg", 0.0), r_gwp=None), ["r_charge_kg"], "GWP", 60,
             [{"r_charge_kg": V("r_charge_kg", 5.0)}, {"r_charge_kg": V("r_charge_kg", 20.0)}]),
            ("charge 0, leak rate unknown", complete(r_charge_kg=A("r_charge_kg", 0.0), r_leak_rate=None), ["r_charge_kg"],
             "漏えい率", 60, [{"r_charge_kg": V("r_charge_kg", 20.0)}]),
            ("B1-zero triple, GWP unknown", complete(r_gwp=None, **b1z), ["r_leak_rate", "r_loss_rate", "r_recovery_rate"],
             "GWP", 60, [{"r_leak_rate": V("r_leak_rate", 0.2)}, {"r_recovery_rate": V("r_recovery_rate", 0.0)},
                         {"r_loss_rate": V("r_loss_rate", 0.5)}]),
            ("B1-zero triple, charge unknown", complete(r_charge_kg=None, **b1z),
             ["r_leak_rate", "r_loss_rate", "r_recovery_rate"], "充填量", 60,
             [{"r_leak_rate": V("r_leak_rate", 0.2)}, {"r_loss_rate": V("r_loss_rate", 0.5)}]),
            ("no replacement inside T (life 15, T 14), loss rate unknown",
             complete(r_leak_rate=V("r_leak_rate", 0.0), r_recovery_rate=V("r_recovery_rate", 1.0), r_life=A("r_life", 15.0),
                      r_loss_rate=None), ["r_life"], "損失率が未取得", 14,
             [{"r_life": V("r_life", 5.0)}, {"r_life": V("r_life", 13.0)}]),
            ("row: loss rate unknown, life 70 at T 60", complete(r_loss_rate=None, r_life=A("r_life", 70.0)), ["r_life"],
             "損失率が未取得", 60, [{"r_life": V("r_life", 10.0)}, {"r_life": V("r_life", 30.0)}]),
            ("row: life unknown, loss rate 0.05", complete(r_life=None, r_loss_rate=A("r_loss_rate", 0.05)), ["r_loss_rate"],
             "交換周期が未取得", 60, [{"r_loss_rate": V("r_loss_rate", 0.0)}, {"r_loss_rate": V("r_loss_rate", 1.0)}]),
            ("B1-zero triple, life unknown", complete(r_life=None, r_leak_rate=V("r_leak_rate", 0.0),
                                                      r_recovery_rate=V("r_recovery_rate", 1.0), r_loss_rate=A("r_loss_rate", 0.0)),
             ["r_loss_rate"], "交換周期が未取得", 60, [{"r_loss_rate": V("r_loss_rate", 0.5)}]),
        ]
        for name, vals, fids, partner, T, alts in cases:
            with self.subTest(name):
                self.assertNotCounted(vals, fids, T, partner=partner)
                self.assertSameTotal([vals] + [dict(vals, **a) for a in alts], float(T))
        # controls: with the partners known the same values decide B1 and move the total
        vals = complete(r_loss_rate=A("r_loss_rate", 0.05))                        # a known life inside T
        _, rep = bridge.build(vals, REFSET, period=60)
        self.assertEqual(self.estimated(rep), {"r_loss_rate"})
        self.assertGreater(self.total(dict(vals, r_loss_rate=V("r_loss_rate", 0.5))), self.total(vals) + 1.0)
        vals = complete(**b1z)
        _, rep = bridge.build(vals, REFSET, period=60)
        self.assertEqual(self.estimated(rep), {"r_leak_rate", "r_loss_rate", "r_recovery_rate"})
        self.assertGreater(self.total(dict(vals, r_recovery_rate=V("r_recovery_rate", 0.5))), self.total(vals) + 1.0)
        vals = complete(r_leak_rate=V("r_leak_rate", 0.0), r_recovery_rate=V("r_recovery_rate", 1.0), r_life=A("r_life", 15.0))
        _, rep = bridge.build(vals, REFSET, period=14)                             # the loss rate known: the life decides
        self.assertEqual(self.estimated(rep), {"r_life"})
        self.assertGreater(self.total(dict(vals, r_life=V("r_life", 5.0)), 14.0), self.total(vals, 14.0) + 1.0)

    # --- sweep#2: a factor of 0 whose quantity is unknown: each makes the other moot
    def test_zero_factor_with_its_quantity_unknown_is_not_an_estimate(self):
        for factor, quantity, stage, partner in (("o_grid_value", "o_elec_kwh", "B6", "購入電力が未取得"),
                                                 ("o_grid_construction", "c_site_electricity", "A5", "工事中の電力が未取得")):
            vals = complete(**{factor: A(factor, 0.0), quantity: None})
            rep, out = self.assertNotCounted(vals, [factor], partner=partner)
            self.assertNotIn(quantity, {m["field"] for m in rep["omitted_inputs"]})       # the 0-fill of the quantity stays
            self.assertFalse(refl(rep)[quantity])
            if stage == "B6":
                self.assertTrue(self.stages(out)["B6"]["complete"])
                self.assertTrue(self.stages(out)["B2"]["complete"])
            self.assertSameTotal([vals] + [dict(vals, **{factor: V(factor, x)}) for x in (0.4, 1.0)])

    # --- sweep#3: a quantity of 0 counts only when a quantity other than 0 could act in the boundary
    def test_material_quantity_zero_that_could_not_act_is_not_counted(self):
        for preset, fid, unit, others, extra in (("EMBODIED", "m_rebar", "t", (10.0, 1000.0), {}),
                                                ("ALL", "m_finish", "m2", (100.0, 5000.0), {})):
            vals = complete(a_stages=V("a_stages", preset), m_waste_rate=None, **dict(extra, **{fid: A(fid, 0.0, unit)}))
            self.assertNotCounted(vals, [fid], partner="0 でない数量でも")
            self.assertSameTotal([vals] + [dict(vals, **{fid: V(fid, x, unit=unit)}) for x in others])
        # control: with the waste rate known the quantity 0 decides that the material is absent, and moves the total
        vals = complete(a_stages=V("a_stages", "EMBODIED"), m_rebar=A("m_rebar", 0.0, "t"))
        _, rep = bridge.build(vals, REFSET, period=60)
        self.assertEqual(self.estimated(rep), {"m_rebar"})
        self.assertGreater(self.total(dict(vals, m_rebar=V("m_rebar", 10.0, unit="t"))), self.total(vals) + 1.0)

    # --- sweep#4: a distance whose value is 0 gives A4 = 0 also when its range reaches above 0
    def test_zero_distance_with_a_range_gives_a4_zero(self):
        for name, extra in (("m3 / m2 rows (delivery factor)", VOLUME_ONLY), ("mass rows, mode unknown", {"m_transport_mode": None})):
            plain = complete(m_transport_km=V("m_transport_km", 0.0), **extra)
            ranged = complete(m_transport_km=R("m_transport_km", 0.0, 0.0, 100.0), **extra)
            self.assertAlmostEqual(self.total(ranged), self.total(plain), delta=1e-6 * self.total(plain), msg=name)
            _, out = self.calc(ranged)
            a4 = self.stages(out)["A4"]
            self.assertEqual(a4["value"], 0.0, name)
            self.assertTrue(a4["complete"], name)
            self.assertFalse(a4["assumed"], name)
            # the distance is a real range item: its low end is the computed total, its high end computes A4
            rg = out["range"]
            self.assertEqual(rg["n_values_with_range"], 1, name)
            self.assertAlmostEqual(rg["low_t"], out["summary"]["total_t"], delta=1e-9 * out["summary"]["total_t"], msg=name)
            self.assertGreater(rg["high_t"], rg["low_t"] + 1e-3, name)
        # 50 km with a range down to 0 (rows carried by the delivery factor): the low end is the 0 km total
        t0 = self.total(complete(m_transport_km=V("m_transport_km", 0.0), **VOLUME_ONLY))
        _, out = self.calc(complete(m_transport_km=R("m_transport_km", 50.0, 0.0, 100.0), **VOLUME_ONLY))
        self.assertAlmostEqual(out["range"]["low_t"], t0 / 1000.0, delta=1e-9 * t0)
        self.assertGreater(out["range"]["high_t"], out["range"]["low_t"] + 1e-3)

    # --- sweep#5: a corrected estimate saved as 取得・確認済み is not an estimate, nor a 「範囲が不明」 item
    def test_corrected_estimate_saved_as_confirmed_is_not_a_range_unknown_item(self):
        est = Value("m_rebar", "statistical", 40.0, "t", method="test_estimate", source_id="TEST", factor_version="v",
                    uncertainty=Uncertainty("interval", 30.0, 55.0, 0.9))
        pid = self.project(complete(m_rebar=est))
        self.put(pid, "m_rebar", {"state": "confirmed", "value": 42, "unit": "t", "from_estimate": True})
        cur = self.app.projects.current(pid, "m_rebar")
        self.assertEqual((cur.state, cur.uncertainty.kind), ("confirmed", "unknown"))      # the note 「元の範囲は使わない」 stays
        _, out = self.app.handle("POST", "/api/projects/%d/calculate" % pid, {"period": 60})
        self.assertEqual(out["status"], "ok")
        self.assertIn("統計推定・仮定が 0 項目", out["reflection"]["summary"])
        rg = out["range"] or {}
        self.assertNotIn("m_rebar", rg.get("unknown_fields") or [])
        self.assertFalse(rg.get("n_values_range_unknown"))
        # control: the same correction saved as an assumption is an estimate whose range is unknown
        self.put(pid, "m_rebar", {"state": "assumption", "value": 43, "unit": "t"})
        _, out = self.app.handle("POST", "/api/projects/%d/calculate" % pid, {"period": 60})
        self.assertIn("m_rebar", (out["range"] or {}).get("unknown_fields") or [])

    # --- sweep#7: with only m3 / m2 rows, the basis, the waste rate and the haul distance cannot complete C2〜C4
    def test_eol_hints_of_massless_rows_name_only_what_can_complete_them(self):
        eol = {"C2", "C3", "C4"}
        cases = [("basis unknown", dict(m_quantity_basis=None), "m_quantity_basis"),
                 ("ORDERED, waste rate unknown", dict(m_quantity_basis=V("m_quantity_basis", "ORDERED"), m_waste_rate=None),
                  "m_waste_rate"),
                 ("haul distance unknown", dict(a_eol_haul_km=None), "a_eol_haul_km")]
        for name, over, fid in cases:
            _, out = self.calc(complete(**dict(VOLUME_ONLY, **over)))
            self.assertEqual(out["status"], "ok", name)
            gaps = {m["field"]: m for m in out["omitted_inputs"]}
            self.assertFalse(set((gaps.get(fid) or {}).get("stages", ())) & eol, (name, gaps.get(fid)))
            hints = {h["stage"]: h for h in out["summary"]["hints"]}
            for st in ("C2", "C4"):
                self.assertIn(st, hints, name)                                 # the m3 / m2 rows still leave them incomplete
                self.assertNotIn(FL.FIELDS[fid]["label"], hints[st]["fields"], (name, st))
                self.assertIn("t か kg で入れると", hints[st]["note"], (name, st))
            if fid == "a_eol_haul_km":
                self.assertNotIn(fid, gaps)
            else:
                self.assertIn("A1-A3", gaps[fid]["stages"], name)               # still the gap of the ordered quantity
            # control: with a row in t the same input is a gap of the end-of-life stages
            _, out = self.calc(complete(**over))
            gaps = {m["field"]: m for m in out["omitted_inputs"]}
            self.assertIn("C2", gaps[fid]["stages"], name)

    # --- sweep#8: 適用外 is refused, with the reason, only where the calculation needs the value
    def test_not_applicable_is_refused_only_where_the_calculation_needs_the_value(self):
        cases = [("o_grid_value", {}, dict(o_elec_kwh=V("o_elec_kwh", 0.0)), "購入電力"),
                 ("o_grid_construction", {}, dict(c_site_electricity=V("c_site_electricity", 0.0)), "工事中の電力"),
                 ("a_eol_route", {}, dict(VOLUME_ONLY), "質量が分かる材料の行"),
                 ("a_eol_route", {}, dict(a_stages=V("a_stages", "EMBODIED")), "質量が分かる材料の行")]
        for fid, need, harmless, why in cases:
            pid = self.project(complete(**need))
            with self.assertRaises(ApiError) as cm:
                self.put(pid, fid, {"state": "not_applicable"})
            self.assertEqual(cm.exception.status, 400)
            self.assertIn("適用外", str(cm.exception))
            self.assertIn(why, str(cm.exception), fid)
            self.assertNotEqual(self.app.projects.current(pid, fid).state, "not_applicable")    # nothing stored
            # where it cannot act, 適用外 is accepted and the calculation runs
            pid = self.project(complete(**harmless))
            st, _ = self.put(pid, fid, {"state": "not_applicable"})
            self.assertEqual(st, 200, fid)
            _, out = self.app.handle("POST", "/api/projects/%d/calculate" % pid, {"period": 60})
            self.assertEqual(out["status"], "ok", (fid, out.get("message")))
        # the context changes after 適用外 was accepted: the calculation explains it in the same words
        pid = self.project(complete(o_elec_kwh=V("o_elec_kwh", 0.0)))
        self.put(pid, "o_grid_value", {"state": "not_applicable"})
        self.put(pid, "o_elec_kwh", {"state": "confirmed", "value": 100000})
        _, out = self.app.handle("POST", "/api/projects/%d/calculate" % pid, {"period": 60})
        self.assertEqual(out["status"], "blocked")
        d = detail(out, "o_grid_value")
        self.assertIn("購入電力がある", d)
        self.assertNotIn("電力を使わない建物でも", d)

    # --- sweep#9: the value of a record-only field does not make the result stale
    def test_record_only_edit_does_not_make_the_result_stale(self):
        pid, out = self.calc(complete())
        self.assertEqual(out["status"], "ok")
        self.assertFalse(self.result(pid)["stale"])
        for fid, value in (("b_name", "別の名前"), ("b_address", "別の所在地"), ("g_borehole", "別のメモ")):
            self.put(pid, fid, {"state": "confirmed", "value": value})
            self.assertFalse(self.result(pid)["stale"], fid)
        # the state of a record field is shown in the reflection table: a change of state still makes it stale
        self.put(pid, "b_name", {"state": "not_obtained"})
        self.assertTrue(self.result(pid)["stale"])
        self.app.handle("POST", "/api/projects/%d/calculate" % pid, {"period": 60})
        self.assertFalse(self.result(pid)["stale"])
        # control: a field that reaches the engine
        self.put(pid, "b_floors_above", {"state": "confirmed", "value": 6})
        self.assertTrue(self.result(pid)["stale"])


if __name__ == "__main__":
    unittest.main()
