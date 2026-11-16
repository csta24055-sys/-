"""Round 11 (bridge / server): moot rules are applied independently (a waste rate of 0 under ORDERED / AS_BUILT); the
shared material inputs follow the rows that can act; 想定しない (NONE) is judged like an active scenario; a required factor
(or route) whose partner is also unknown no longer blocks; the ledger uses the period of the last run; every screen
field has one row in the reflection table; a life or cycle whose stated range lies at or above T is not counted.

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


def R(fid, value, lo, hi, unit=None):
    """An assumed value with a stated interval."""
    return V(fid, value, "assumption", unit, uncertainty=Uncertainty("interval", lo, hi, 0.8))


def NA(fid):
    return V(fid, None, "not_applicable")


def minimal(**over) -> dict:
    v = {"b_use": V("b_use", "office"), "b_gfa": V("b_gfa", 1000.0), "a_stages": V("a_stages", "ALL"),
         "a_eol_route": V("a_eol_route", "LANDFILL"), "m_rebar": V("m_rebar", 10.0, unit="t"),
         "m_waste_rate": NA("m_waste_rate"), "m_reuse_rate": NA("m_reuse_rate"),
         "o_grid_value": V("o_grid_value", 0.4), "o_grid_construction": V("o_grid_construction", 0.4),
         "o_water_m3": V("o_water_m3", 1000.0), "o_sewage_m3": V("o_sewage_m3", 900.0), "o_waste_kg": V("o_waste_kg", 5000.0)}
    v.update(over)
    return {k: x for k, x in v.items() if x is not None}


def full(**over) -> dict:
    """The complete baseline of tests/test_wlcstudio.py (ReviewFixTests.full)."""
    v = minimal(m_quantity_basis=V("m_quantity_basis", "DESIGN"), m_repair_rate=V("m_repair_rate", 0.01),
                m_refresh_cycle=V("m_refresh_cycle", 30.0), a_eol_haul_km=V("a_eol_haul_km", 20.0),
                a_reconstruction=V("a_reconstruction", "NONE"), c_site_electricity=V("c_site_electricity", 1000.0),
                c_diesel=V("c_diesel", 500.0), e_repair_rate=V("e_repair_rate", 0.01),
                r_charge_kg=V("r_charge_kg", 20.0), r_gwp=V("r_gwp", 2000.0), r_leak_rate=V("r_leak_rate", 0.03),
                r_loss_rate=V("r_loss_rate", 0.05), r_recovery_rate=V("r_recovery_rate", 0.5), r_life=V("r_life", 15.0),
                r_top_up=V("r_top_up", "yes"), o_elec_kwh=V("o_elec_kwh", 100000.0), o_fm_ratio=V("o_fm_ratio", 0.1),
                m_transport_km=V("m_transport_km", 50.0), m_transport_mode=V("m_transport_mode", "TRUCK_LARGE"))
    for t, _ in FL.TRADES:
        k = t.lower()
        v["e_%s_count" % k] = V("e_%s_count" % k, 2.0)
        v["e_%s_life" % k] = V("e_%s_life" % k, 15.0)
        v["e_%s_mass" % k] = V("e_%s_mass" % k, 100.0)
    for f in ("o_gas_m3", "o_oil_l", "o_dheat_mj", "o_pv_kwh", "o_export_kwh"):
        v[f] = NA(f)
    for f, *_ in FL.MATERIALS:
        v.setdefault(f, NA(f))
    v.update(over)
    return {k: x for k, x in v.items() if x is not None}


def complete(**over) -> dict:
    """full() plus every remaining field (the round-11 sweep baseline): building data, the waste rate, more mass
    materials, a refurbishment cycle and share (with 想定しない), fuels."""
    v = full(b_name=V("b_name", "r11"), b_address=V("b_address", "somewhere"), b_structure=V("b_structure", "RC"),
             b_floors_above=V("b_floors_above", 5), b_floors_below=V("b_floors_below", 1), b_height=V("b_height", 20.0),
             b_footprint=V("b_footprint", 300.0), b_completion_year=V("b_completion_year", 2026),
             b_project_type=V("b_project_type", "NEW_BUILD"), g_foundation=V("g_foundation", "PILE"),
             g_borehole=V("g_borehole", "note"), a_replacement_cycle=V("a_replacement_cycle", 40.0),
             a_recon_fraction=V("a_recon_fraction", 0.5), o_source=V("o_source", "BILLS"),
             m_waste_rate=V("m_waste_rate", 0.05), m_reuse_rate=V("m_reuse_rate", 0.1), m_steel=V("m_steel", 5.0, unit="t"),
             m_aluminium=V("m_aluminium", 1.0, unit="t"), m_plastic=V("m_plastic", 0.5, unit="t"),
             m_mortar=V("m_mortar", 3.0, unit="t"), o_gas_m3=V("o_gas_m3", 2000.0), o_oil_l=V("o_oil_l", 100.0),
             o_dheat_mj=V("o_dheat_mj", 5000.0))
    v.update(over)
    return {k: x for k, x in v.items() if x is not None}


def drop(vals: dict, *fids) -> dict:
    return {k: v for k, v in vals.items() if k not in fids}


def refl(rep_or_out) -> dict:
    return {f["field"]: f["reflected"] for f in rep_or_out["fields"]}


def detail(rep_or_out, fid) -> str:
    rows = rep_or_out["fields"] if "detail" in (rep_or_out["fields"] or [{}])[0] else bridge.reflection_table(rep_or_out)
    return {r["field"]: r["detail"] for r in rows}[fid]


VOLUME_ONLY = dict(m_concrete=V("m_concrete", 500.0, unit="m3"), m_glass=V("m_glass", 300.0, unit="m2"),
                   **{f: NA(f) for f in MASS})


class EleventhRoundBridgeTests(unittest.TestCase):
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

    def calc(self, vals, T=60):
        pid = self.app.projects.create("r11", "RC")
        for v in vals.values():
            self.app.projects.put(pid, v)
        _, out = self.app.handle("POST", "/api/projects/%d/calculate" % pid, {"period": T})
        return pid, out

    def stages(self, out):
        return {x["stage"]: x for x in out["summary"]["stages"]}

    def total(self, vals, T=60.0):
        doc, rep = bridge.build(vals, REFSET, period=T)
        self.assertEqual(rep["missing_required"], [])
        return self.E.run(doc, None, T)["results"]["SUM-03"]["value"]

    def estimated(self, rep):
        return {f["field"] for f in rep["fields"] if f["reflected"] and f["state"] in ("statistical", "assumption")
                and f["field"] not in bridge.TOTAL_NEUTRAL}

    def assertNotCounted(self, vals, fids, T=60):
        """The fields are reported not reflected, nothing is counted as an estimate, and the range names no unknown width
        and no zero-width 「範囲のある」 item."""
        _, rep = bridge.build(vals, REFSET, period=T)
        r = refl(rep)
        for f in fids:
            self.assertFalse(r[f], (f, detail(rep, f)))
        self.assertEqual(self.estimated(rep), set())
        self.assertEqual(rep["n_estimated"], 0)
        _, out = self.calc(vals, T)
        self.assertEqual(out["status"], "ok")
        self.assertFalse((out["range"] or {}).get("unknown_fields"))
        self.assertFalse((out["range"] or {}).get("n_values_with_range"))
        return rep, out

    def assertSameTotal(self, variants, T=60.0):
        totals = [self.total(v, T) for v in variants]
        for t in totals[1:]:
            self.assertAlmostEqual(t, totals[0], delta=1e-6 * abs(totals[0]))
        return totals[0]

    # --- sweep#0: the two waste-rate rules are independent
    def test_zero_waste_rate_under_ordered_is_not_an_estimate(self):
        for preset, extra in (("EMBODIED", {}), ("ALL", VOLUME_ONLY)):
            def ctx(w, basis="ORDERED"):
                return complete(a_stages=V("a_stages", preset), m_quantity_basis=V("m_quantity_basis", basis),
                                m_waste_rate=w, **extra)
            rep, out = self.assertNotCounted(ctx(V("m_waste_rate", 0.0, "assumption")), ["m_waste_rate", "m_quantity_basis"])
            self.assertIn("廃棄率の値は合計を変えない", detail(rep, "m_waste_rate"))
            self.assertIn("廃棄率が 0 なので", detail(rep, "m_quantity_basis"))
            self.assertIsNone(out["range"])
            # 適用外 (= 0) is moot the same way; and no rate in the range changes the total
            _, rep = bridge.build(ctx(NA("m_waste_rate")), REFSET, period=60)
            self.assertFalse(refl(rep)["m_waste_rate"], preset)
            self.assertSameTotal([ctx(V("m_waste_rate", x, "assumption")) for x in (0.0, 0.05, 0.3, 0.9)])
            # the AS_BUILT basis follows the same rule
            self.assertNotCounted(ctx(V("m_waste_rate", 0.0, "assumption"), "AS_BUILT"), ["m_waste_rate"])
        # control: with mass rows and the end-of-life stages, a rate of 0 is the installed mass Q(1-w): it is counted
        vals = complete(m_quantity_basis=V("m_quantity_basis", "ORDERED"), m_waste_rate=V("m_waste_rate", 0.0, "assumption"))
        _, rep = bridge.build(vals, REFSET, period=60)
        self.assertEqual(self.estimated(rep), {"m_waste_rate"})
        self.assertFalse(refl(rep)["m_quantity_basis"])
        self.assertNotAlmostEqual(self.total(vals), self.total(dict(vals, m_waste_rate=V("m_waste_rate", 0.3))), places=0)

    # --- sibling of sweep#0: two inputs that each make B1 zero by themselves — the branch order must not count one
    def test_two_reasons_for_b1_zero_count_neither(self):
        b1z = dict(r_leak_rate=V("r_leak_rate", 0.0, "assumption"), r_loss_rate=V("r_loss_rate", 0.0, "assumption"),
                   r_recovery_rate=V("r_recovery_rate", 1.0, "assumption"))
        cases = [("GWP 0, B1 surely 0", dict(b1z, r_gwp=V("r_gwp", 0.0, "assumption")), "r_gwp", 2000.0),
                 ("charge 0, GWP 0", dict(r_charge_kg=V("r_charge_kg", 0.0, "assumption"), r_gwp=V("r_gwp", 0.0)), "r_charge_kg", 20.0),
                 ("charge 0, B1 surely 0", dict(b1z, r_charge_kg=V("r_charge_kg", 0.0, "assumption")), "r_charge_kg", 20.0)]
        for name, over, fid, other in cases:
            vals = complete(**over)
            self.assertNotCounted(vals, [fid])
            self.assertSameTotal([vals, dict(vals, **{fid: V(fid, other)})])
        # inside the B1-surely-0 rule: a loss rate of 0 AND no replacement inside T (life 15 at T 14) — neither the
        # rate nor the life decides alone; the leak and the recovery still do
        vals = complete(r_life=V("r_life", 15.0, "assumption"), **b1z)
        _, rep = bridge.build(vals, REFSET, period=14)
        self.assertFalse(refl(rep)["r_loss_rate"] or refl(rep)["r_life"])
        self.assertEqual(self.estimated(rep), {"r_leak_rate", "r_recovery_rate"})
        t0 = self.assertSameTotal([vals, dict(vals, r_loss_rate=V("r_loss_rate", 0.05)), dict(vals, r_life=V("r_life", 5.0))], 14.0)
        self.assertGreater(self.total(dict(vals, r_leak_rate=V("r_leak_rate", 0.03)), 14.0), t0 + 1.0)
        _, rep = bridge.build(vals, REFSET, period=60)                 # a replacement inside T: the rate decides
        self.assertTrue(refl(rep)["r_loss_rate"])
        self.assertFalse(refl(rep)["r_life"])
        # control: one reason alone: the value that decides it is counted and moves the total
        vals = complete(r_gwp=V("r_gwp", 0.0, "assumption"))
        _, rep = bridge.build(vals, REFSET, period=60)
        self.assertEqual(self.estimated(rep), {"r_gwp"})
        self.assertGreater(self.total(dict(vals, r_gwp=V("r_gwp", 2000.0))), self.total(vals) + 1.0)

    # --- sweep#1: shared material inputs follow the rows that can act
    def test_shared_material_inputs_follow_the_rows_that_can_act(self):
        # case A: only m3 / m2 rows, the waste rate unknown: no basis lets a row act
        a = drop(complete(m_quantity_basis=V("m_quantity_basis", "ORDERED", "assumption"),
                          m_refresh_cycle=V("m_refresh_cycle", 30.0, "assumption"), **VOLUME_ONLY), "m_waste_rate")
        rep, out = self.assertNotCounted(a, ["m_concrete", "m_glass", "m_refresh_cycle", "m_quantity_basis"])
        self.assertIn("材料の行が無いので", detail(rep, "m_refresh_cycle"))
        self.assertIn("m_waste_rate", {m["field"] for m in rep["omitted_inputs"]})      # the real gap stays
        self.assertTrue(out["summary"]["lower_bound"])
        self.assertSameTotal([dict(a, m_refresh_cycle=V("m_refresh_cycle", x, "assumption")) for x in (5.0, 30.0, 70.0, 200.0)]
                             + [dict(a, m_quantity_basis=V("m_quantity_basis", b, "assumption")) for b in ("DESIGN", "AS_BUILT")])
        # case B: mass rows, ORDERED, the distance and the waste rate unknown: DESIGN would give the installed mass
        b = drop(complete(m_quantity_basis=V("m_quantity_basis", "ORDERED", "assumption"),
                          m_refresh_cycle=V("m_refresh_cycle", 30.0, "assumption")), "m_waste_rate", "m_transport_km")
        _, rep = bridge.build(b, REFSET, period=60)
        r = refl(rep)
        self.assertFalse(r["m_refresh_cycle"] or r["m_rebar"])
        self.assertTrue(r["m_quantity_basis"])
        self.assertEqual(self.estimated(rep), {"m_quantity_basis"})
        self.assertSameTotal([dict(b, m_refresh_cycle=V("m_refresh_cycle", x, "assumption")) for x in (5.0, 70.0, 200.0)])
        self.assertGreater(self.total(dict(b, m_quantity_basis=V("m_quantity_basis", "DESIGN"))), self.total(b) + 1.0)
        # no repair can be over-counted when no row computes A1-A3: no 「更新周期（修繕 B3 への影響）」
        _, rep = bridge.build(drop(b, "m_refresh_cycle"), REFSET, period=60)
        self.assertNotIn("m_refresh_cycle@B3", {m["field"] for m in rep["missing_inputs"]})
        self.assertIn("m_refresh_cycle", {m["field"] for m in rep["omitted_inputs"]})
        _, rep = bridge.build(drop(complete(), "m_refresh_cycle"), REFSET, period=60)
        self.assertIn("m_refresh_cycle@B3", {m["field"] for m in rep["missing_inputs"]})      # rows compute repairs
        # a distance of 0 km with no acting row stays counted when another distance would let a row act (tonne-km on
        # the ordered mass) ...
        c = complete(m_quantity_basis=V("m_quantity_basis", "ORDERED"), m_transport_km=V("m_transport_km", 0.0, "assumption"),
                     m_waste_rate=None)
        _, rep = bridge.build(c, REFSET, period=60)
        self.assertEqual(self.estimated(rep), {"m_transport_km"})
        self.assertGreater(self.total(dict(c, m_transport_km=V("m_transport_km", 50.0))), self.total(c) + 1.0)
        # ... but not when no distance can (design quantities: the ordered mass needs the waste rate), although the
        # rows act in other stages; the 0 km still keeps A4 complete
        k = complete(m_transport_km=V("m_transport_km", 0.0, "assumption"), m_waste_rate=None)
        rep, out = self.assertNotCounted(k, ["m_transport_km"])
        self.assertTrue(refl(rep)["m_rebar"])
        self.assertIn("0 km 以外の距離でも", detail(rep, "m_transport_km"))
        self.assertTrue(self.stages(out)["A4"]["complete"])
        self.assertSameTotal([k, dict(k, m_transport_km=V("m_transport_km", 50.0))])
        # ... and a disposal distance of 0 km without any end-of-life mass is not (no distance can make C2 act)
        h = complete(a_eol_haul_km=V("a_eol_haul_km", 0.0, "assumption"), **VOLUME_ONLY)
        _, rep = bridge.build(h, REFSET, period=60)
        self.assertFalse(refl(rep)["a_eol_haul_km"])
        self.assertNotIn("a_eol_haul_km", self.estimated(rep))
        self.assertSameTotal([h, dict(h, a_eol_haul_km=V("a_eol_haul_km", 100.0))])
        _, out = self.calc(h)
        self.assertTrue(self.stages(out)["C2"]["complete"])           # the 0 km still keeps C2 complete (its own rule)

    # --- sweep#2: 想定しない (NONE) is judged by the same test as an active scenario
    def test_no_reconstruction_is_moot_by_the_same_test(self):
        cases = [("cycle 70, T 60", dict(a_replacement_cycle=V("a_replacement_cycle", 70.0)), 60),
                 ("cycle 40, T 30", {}, 30),
                 ("share 0", dict(a_recon_fraction=V("a_recon_fraction", 0.0)), 60),
                 ("cycle unknown", dict(a_replacement_cycle=None), 60),
                 ("share unknown", dict(a_recon_fraction=None), 60)]
        for name, over, T in cases:
            for sc in ("NONE", "MAJOR_REFURBISHMENT", "REBUILD_IDENTICAL"):
                vals = complete(a_reconstruction=V("a_reconstruction", sc, "assumption"), **over)
                _, rep = bridge.build(vals, REFSET, period=T)
                self.assertFalse(refl(rep)["a_reconstruction"], (name, sc))
                self.assertNotIn("a_reconstruction", self.estimated(rep), (name, sc))
            self.assertIn("どの想定でも B5 は 0 か計算できない",
                          detail(bridge.build(complete(a_reconstruction=V("a_reconstruction", "NONE", "assumption"), **over),
                                              REFSET, period=T)[1], "a_reconstruction"), name)
            self.assertSameTotal([complete(a_reconstruction=V("a_reconstruction", sc), **over)
                                  for sc in ("NONE", "MAJOR_REFURBISHMENT", "REBUILD_IDENTICAL")], T)
        self.assertNotCounted(complete(a_reconstruction=V("a_reconstruction", "NONE", "assumption"),
                                       a_replacement_cycle=V("a_replacement_cycle", 70.0)), ["a_reconstruction"])
        _, rep = bridge.build(complete(a_reconstruction=NA("a_reconstruction"), a_replacement_cycle=V("a_replacement_cycle", 70.0)),
                              REFSET, period=60)
        self.assertFalse(refl(rep)["a_reconstruction"])
        # control: a refurbishment can fall inside T with a share: the choice changes B5 and NONE is counted
        vals = complete(a_reconstruction=V("a_reconstruction", "NONE", "assumption"))
        _, rep = bridge.build(vals, REFSET, period=60)
        self.assertEqual(self.estimated(rep), {"a_reconstruction"})
        self.assertGreater(self.total(dict(vals, a_reconstruction=V("a_reconstruction", "MAJOR_REFURBISHMENT"))),
                           self.total(vals) + 1.0)

    # --- sweep#3: a required factor (or route) whose partner is also unknown does not block
    def test_factor_with_its_partner_unknown_does_not_block(self):
        for factor, partner, stage in (("o_grid_value", "o_elec_kwh", "B6"), ("o_grid_construction", "c_site_electricity", "A5")):
            only_partner = drop(complete(), partner)
            both = drop(complete(), partner, factor)
            _, out = self.calc(both)
            self.assertEqual(out["status"], "ok", (factor, out.get("message")))
            self.assertEqual(out["missing_required"], [])
            self.assertTrue(out["summary"]["lower_bound"])
            self.assertIn(stage, out["summary"]["incomplete_stages"])
            gaps = {m["field"]: m for m in out["omitted_inputs"]}
            self.assertIn(partner, gaps)
            self.assertIn(factor, gaps)
            self.assertIn(stage, gaps[factor]["stages"])
            hint = {h["stage"]: h for h in out["summary"]["hints"]}[stage]
            self.assertIn(FL.FIELDS[factor]["label"], hint["note"])
            self.assertIn(FL.FIELDS[partner]["label"], hint["note"])
            self.assertFalse(refl(out)[factor])
            # the fill cannot act: the same total as with the factor known
            self.assertAlmostEqual(out["summary"]["total_kg"], self.total(only_partner), delta=1e-6 * self.total(only_partner))
            if factor == "o_grid_value":
                self.assertIn("B2", out["summary"]["incomplete_stages"])
            # control: the factor alone unknown still blocks, and names the factor
            _, out = self.calc(drop(complete(), factor))
            self.assertEqual(out["status"], "blocked")
            self.assertIn(FL.FIELDS[factor]["label"], out["message"])
        # sibling: the route is required per material row, but acts only through an end-of-life mass
        for name, over in (("ORDERED, waste rate unknown", dict(m_quantity_basis=V("m_quantity_basis", "ORDERED"), m_waste_rate=None)),
                           ("only m3 / m2 rows", dict(VOLUME_ONLY))):
            vals = complete(**over)
            _, out = self.calc(drop(vals, "a_eol_route"))
            self.assertEqual(out["status"], "ok", name)
            gaps = {m["field"]: m for m in out["omitted_inputs"]}
            self.assertEqual(set(gaps["a_eol_route"]["stages"]) & {"C3", "C4"}, {"C3", "C4"}, name)
            self.assertTrue({"C3", "C4"} <= set(out["summary"]["incomplete_stages"]), name)
            self.assertAlmostEqual(out["summary"]["total_kg"], self.total(vals), delta=1e-6 * self.total(vals))
        _, out = self.calc(drop(complete(), "a_eol_route"))                  # design quantities: the mass is known
        self.assertEqual(out["status"], "blocked")
        self.assertIn("解体後の処理シナリオ", out["message"])

    # --- sweep#4: the ledger uses the period of the last run (also a blocked one)
    def test_ledger_uses_the_period_of_the_last_run(self):
        vals = complete(r_leak_rate=V("r_leak_rate", 0.0), r_recovery_rate=V("r_recovery_rate", 1.0), r_life=V("r_life", 70.0))
        pid, out = self.calc(vals, 60)
        self.assertEqual(out["status"], "ok")
        rf = ("r_charge_kg", "r_gwp", "r_loss_rate")
        self.assertFalse(any(refl(out)[f] for f in rf))
        self.app.handle("PUT", "/api/projects/%d/fields/o_grid_value" % pid, {"state": "not_obtained"})
        _, out = self.app.handle("POST", "/api/projects/%d/calculate" % pid, {"period": 100})
        self.assertEqual(out["status"], "blocked")
        self.assertTrue(all(refl(out)[f] for f in rf))               # a replacement falls inside 100 years
        _, res = self.app.handle("GET", "/api/projects/%d/result" % pid, None)
        _, led = self.app.handle("GET", "/api/projects/%d/ledger" % pid, None)
        self.assertEqual(res["period"], 100.0)
        self.assertFalse(res["stale"])
        self.assertEqual(refl(led), refl(res))
        _, view = self.app.handle("GET", "/api/projects/%d" % pid, None)
        self.assertEqual(view["last_period"], 100.0)                   # the screen shows the period it last calculated
        # a project never calculated: the ledger is still built (no period)
        pid2 = self.app.projects.create("r11-new", "RC")
        _, led = self.app.handle("GET", "/api/projects/%d/ledger" % pid2, None)
        self.assertEqual(sorted(r["field"] for r in led["fields"]), sorted(FL.FIELDS))

    # --- sweep#5: every screen field has exactly one row in the reflection table
    def test_every_field_has_exactly_one_reflection_row(self):
        zero = {f: V(f, 0.0, unit="t") for f in MASS}
        contexts = {
            "complete": complete(), "full": full(), "minimal": minimal(), "nothing": {},
            "materials 0 t": complete(**zero), "materials 適用外": complete(**{f: NA(f) for f in MASS}),
            "materials 0 t, route unknown": drop(complete(**zero), "a_eol_route"),
            "materials unknown, route unknown": drop(complete(), "a_eol_route", *MASS),
            "route unknown (blocked)": drop(complete(), "a_eol_route"),
            "route unknown, volume rows": drop(complete(**VOLUME_ONLY), "a_eol_route"),
            "embodied, route unknown": drop(complete(a_stages=V("a_stages", "EMBODIED")), "a_eol_route"),
            "stages unknown": drop(complete(), "a_stages"),
            "everything unknown but stages": {"a_stages": V("a_stages", "ALL")},
            "equipment 適用外": complete(**{"e_%s_count" % t.lower(): NA("e_%s_count" % t.lower()) for t, _ in FL.TRADES}),
            "no refrigerant": complete(r_charge_kg=NA("r_charge_kg")),
            "rebuild": complete(a_reconstruction=V("a_reconstruction", "REBUILD_IDENTICAL")),
        }
        for name, vals in contexts.items():
            for preset in ("ALL", "EMBODIED", "NO_OPERATION", "UPFRONT_EOL"):
                if "a_stages" in vals:
                    vals = dict(vals, a_stages=V("a_stages", preset))
                for T in (None, 60.0, 14.0):
                    _, rep = bridge.build(vals, REFSET, period=T)
                    ids = [r["field"] for r in bridge.reflection_table(rep)]
                    self.assertEqual(len(ids), len(set(ids)), (name, preset, T))
                    self.assertEqual(sorted(ids), sorted(FL.FIELDS), (name, preset, T, sorted(set(FL.FIELDS) - set(ids))))
        # the route with no material row says why it does not act; the result and the ledger have the same rows
        vals = complete(**zero)
        pid, out = self.calc(vals)
        self.assertEqual(out["status"], "ok")
        self.assertIn("材料の行が無い", detail(out, "a_eol_route"))
        _, led = self.app.handle("GET", "/api/projects/%d/ledger" % pid, None)
        self.assertEqual([r["field"] for r in led["fields"]], [r["field"] for r in out["fields"]])
        self.assertEqual(len(out["fields"]), len(FL.FIELDS))

    # --- sweep#6: a life or cycle whose stated range lies at or above T cannot change the total
    def test_life_whose_range_lies_beyond_t_is_not_counted(self):
        rec = dict(a_reconstruction=V("a_reconstruction", "MAJOR_REFURBISHMENT"), a_recon_fraction=V("a_recon_fraction", 0.5))
        cases = [("e_hvac_life", {}), ("e_conveyance_life", {}), ("m_refresh_cycle", {}), ("r_life", {}),
                 ("a_replacement_cycle", rec)]
        for fid, over in cases:
            for lo, hi, T in ((70.0, 90.0, 60), (60.0, 90.0, 60), (15.0, 30.0, 14)):
                vals = complete(**dict(over, **{fid: R(fid, (lo + hi) / 2, lo, hi)}))
                rep, out = self.assertNotCounted(vals, [fid], T)
                self.assertIn("範囲のどの値でも評価期間の内に", detail(rep, fid))
                self.assertSameTotal([dict(vals, **{fid: V(fid, x, "assumption")}) for x in (lo, (lo + hi) / 2, hi)], float(T))
            # control: a range that reaches below T is moved and gives a real width
            vals = complete(**dict(over, **{fid: R(fid, 80.0, 30.0, 90.0)}))
            _, out = self.calc(vals)
            self.assertTrue(refl(out)[fid], fid)
            self.assertEqual(out["range"]["n_values_with_range"], 1, fid)
            self.assertGreater(out["range"]["high_t"] - out["range"]["low_t"], 1e-6, fid)
            # a value at or above T WITHOUT a stated range keeps counting (its unknown range may reach below T)
            _, rep = bridge.build(complete(**dict(over, **{fid: V(fid, 80.0, "assumption")})), REFSET, period=60)
            self.assertTrue(refl(rep)[fid], fid)
            self.assertIn(fid, self.estimated(rep))

    def test_distance_with_delivery_factor_rows_is_reflected_when_it_may_be_zero(self):
        # only m3 / m2 rows (the per-quantity delivery factor carries A4): the distance's value is not used, but 0 km
        # makes A4 0 — so a distance that may be 0 can change the total and is reflected; a range above 0 cannot
        base = complete(**VOLUME_ONLY)
        t50 = self.total(dict(base, m_transport_km=V("m_transport_km", 50.0)))
        t0 = self.total(dict(base, m_transport_km=V("m_transport_km", 0.0)))
        self.assertNotEqual(t50, t0)
        _, rep = bridge.build(dict(base, m_transport_km=V("m_transport_km", 50.0)), REFSET, period=60)
        self.assertTrue(refl(rep)["m_transport_km"])
        self.assertIn("配送原単位", detail(rep, "m_transport_km"))
        _, rep = bridge.build(dict(base, m_transport_km=R("m_transport_km", 50.0, 10.0, 80.0)), REFSET, period=60)
        self.assertFalse(refl(rep)["m_transport_km"])
        self.assertIn("0 km を含まない", detail(rep, "m_transport_km"))
        self.assertEqual(self.total(dict(base, m_transport_km=R("m_transport_km", 10.0, 10.0, 80.0))), t50)


if __name__ == "__main__":
    unittest.main()
