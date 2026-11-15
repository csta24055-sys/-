"""Round 10 (bridge / server / estimate): a fresh result is not stale; 適用外 refrigerant life is no replacement; inputs
that cannot change the total are not estimates (equipment reach, choices the engine never reads, a factor or a partner
without its quantity); the waste rate's range direction follows the quantity basis; a deciding input whose range crosses
T keeps its partner; the A4 gap under ORDERED / AS_BUILT names the distance; the single steel estimate says why.

Run: cd whole-life-carbon-jcat-study && python3 -B -m unittest discover -s 23_WLC_STUDIO_APP/tests -q
"""
from __future__ import annotations

import itertools
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

from wlcstudio import bridge, estimate, fields as FL  # noqa: E402
from wlcstudio import server as server_mod  # noqa: E402
from wlcstudio.provenance import Uncertainty, Value  # noqa: E402
from wlcstudio.server import App  # noqa: E402

REFSET = json.loads((HERE.parent / "12_APP_BASE" / "samples" / "refset_fictional.json").read_text(encoding="utf-8"))


def V(fid, value=None, state="confirmed", unit=None, **kw):
    F = FL.FIELDS[fid]
    kw.setdefault("method", "test")
    return Value(fid, state, value, unit if unit is not None else F.get("unit", ""), **kw)


def R(fid, value, lo, hi, unit=None):
    """An assumed value with a stated interval."""
    return V(fid, value, "assumption", unit, uncertainty=Uncertainty("interval", lo, hi, 0.8))


def minimal(**over) -> dict:
    v = {"b_use": V("b_use", "office"), "b_gfa": V("b_gfa", 1000.0), "a_stages": V("a_stages", "ALL"),
         "a_eol_route": V("a_eol_route", "LANDFILL"), "m_rebar": V("m_rebar", 10.0, unit="t"),
         "m_waste_rate": V("m_waste_rate", None, "not_applicable"), "m_reuse_rate": V("m_reuse_rate", None, "not_applicable"),
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
        v[f] = V(f, None, "not_applicable")
    for f, *_ in FL.MATERIALS:
        v.setdefault(f, V(f, None, "not_applicable"))
    v.update(over)
    return {k: x for k, x in v.items() if x is not None}


def everything(**over) -> dict:
    """full() plus every other field with a value (building data, waste, more materials, a refurbishment inside T)."""
    v = full(b_structure=V("b_structure", "RC"), b_floors_above=V("b_floors_above", 5), b_floors_below=V("b_floors_below", 1),
             b_height=V("b_height", 20.0), b_footprint=V("b_footprint", 300.0), b_completion_year=V("b_completion_year", 2026),
             b_project_type=V("b_project_type", "NEW_BUILD"), g_foundation=V("g_foundation", "PILE"),
             a_reconstruction=V("a_reconstruction", "MAJOR_REFURBISHMENT"), a_replacement_cycle=V("a_replacement_cycle", 40.0),
             a_recon_fraction=V("a_recon_fraction", 0.5), o_source=V("o_source", "BILLS"),
             m_waste_rate=V("m_waste_rate", 0.05), m_reuse_rate=V("m_reuse_rate", 0.1), m_steel=V("m_steel", 5.0, unit="t"),
             m_concrete=V("m_concrete", 500.0, unit="m3"), m_aluminium=V("m_aluminium", 1.0, unit="t"),
             o_gas_m3=V("o_gas_m3", 2000.0), o_oil_l=V("o_oil_l", 100.0), o_dheat_mj=V("o_dheat_mj", 5000.0))
    v.update(over)
    return {k: x for k, x in v.items() if x is not None}


def drop(vals: dict, *fids) -> dict:
    return {k: v for k, v in vals.items() if k not in fids}


def refl(rep_or_out) -> dict:
    return {f["field"]: f["reflected"] for f in rep_or_out["fields"]}


def tables(doc):
    out = {}
    for c in doc["categories"].values():
        out.update(c["tables"])
    return out


def perturbed(v: Value) -> Value:
    """Another admissible value of the same field (one perturbation that changes the counts of lives and cycles)."""
    F = FL.FIELDS[v.field_id]
    if F["type"] == "enum":
        x = next(k for k, _ in F["enum"] if k != v.value)
    else:
        lo, hi = F.get("range", (0, 1e12))
        x = min(hi, max(lo, float(v.value) * 1.7 + 1.0))
        if F["type"] == "integer":
            x = int(round(x))
    return Value(v.field_id, v.state, x, v.unit, method="test")


class TenthRoundBridgeTests(unittest.TestCase):
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
        pid = self.app.projects.create("r10", "RC")
        for v in vals.values():
            self.app.projects.put(pid, v)
        _, out = self.app.handle("POST", "/api/projects/%d/calculate" % pid, {"period": T})
        return pid, out

    def stages(self, out):
        return {x["stage"]: x for x in out["summary"]["stages"]}

    def total(self, vals, T=60.0):
        doc, rep = bridge.build(vals, self.app.refset, period=T)
        self.assertEqual(rep["missing_required"], [])
        return self.E.run(doc, None, T)["results"]["SUM-03"]["value"]

    def corners(self, vals, fids, T=60.0):
        out = []
        for ends in itertools.product((0, 1), repeat=len(fids)):
            vv = dict(vals)
            for f, e in zip(fids, ends):
                u = vals[f].uncertainty
                vv[f] = V(f, float(u.low if e == 0 else u.high), "assumption", vals[f].unit)
            out.append(self.total(vv, T) / 1000.0)
        return min(out), max(out)

    def estimated(self, rep):
        return {f["field"] for f in rep["fields"] if f["reflected"] and f["state"] in ("statistical", "assumption")
                and f["field"] not in bridge.TOTAL_NEUTRAL}

    # --- sweep-1: GET /result and /ledger rebuild for the period of the run
    def test_fresh_result_is_not_stale_and_ledger_agrees(self):
        b1zero = dict(r_leak_rate=V("r_leak_rate", 0.0), r_recovery_rate=V("r_recovery_rate", 1.0))
        for life, T in ((70.0, 60), (15.0, 14)):
            pid, out = self.calc(full(r_life=V("r_life", life), **b1zero), T)
            self.assertEqual(out["status"], "ok")
            self.assertTrue(self.stages(out)["B1"]["complete"])
            for _ in range(2):                                # also after calculating again
                _, res = self.app.handle("GET", "/api/projects/%d/result" % pid, None)
                self.assertFalse(res["stale"], (life, T))
                self.app.handle("POST", "/api/projects/%d/calculate" % pid, {"period": T})
            _, led = self.app.handle("GET", "/api/projects/%d/ledger" % pid, None)
            self.assertEqual(refl(led), refl(out), (life, T))
            self.assertFalse(refl(led)["r_charge_kg"])
        # a real change is still flagged
        self.app.projects.put(pid, V("r_life", 10.0))
        _, res = self.app.handle("GET", "/api/projects/%d/result" % pid, None)
        self.assertTrue(res["stale"])

    def test_fingerprint_follows_the_stated_range(self):
        a = full(m_rebar=R("m_rebar", 10.0, 9.0, 11.0, "t"))
        b = full(m_rebar=R("m_rebar", 10.0, 5.0, 15.0, "t"))
        ha = bridge.build(a, REFSET, period=60)[1]["input_hash"]
        self.assertNotEqual(ha, bridge.build(b, REFSET, period=60)[1]["input_hash"])
        self.assertEqual(ha, bridge.build(dict(a), REFSET, period=60)[1]["input_hash"])

    # --- sweep-2 / regressions-4: 適用外 refrigerant life = no replacement in the B1-surely-0 rule
    def test_refrigerant_life_not_applicable_is_no_replacement(self):
        base = dict(r_leak_rate=V("r_leak_rate", 0.0), r_recovery_rate=V("r_recovery_rate", 1.0),
                    r_life=V("r_life", None, "not_applicable"))
        for name, gone in (("a", ("r_charge_kg",)), ("b", ("r_gwp",)), ("c", ("r_loss_rate", "r_charge_kg"))):
            vals = drop(full(**base), *gone)
            doc, rep = bridge.build(vals, REFSET, period=60)
            self.assertEqual(tables(doc)["refrigerants"], [], name)
            self.assertFalse({m["field"] for m in rep["missing_inputs"] if m["field"].startswith("r_")}, name)
            self.assertTrue(refl(rep)["r_life"], name)                     # 交換しない decides that B1 is 0
            _, out = self.calc(vals)
            self.assertTrue(self.stages(out)["B1"]["complete"], name)
            self.assertNotIn("B1", out["summary"]["incomplete_stages"], name)
        # with a leak B1 is not surely 0: the missing charge still leaves B1 incomplete
        vals = drop(full(**dict(base, r_leak_rate=V("r_leak_rate", 0.03))), "r_charge_kg")
        _, out = self.calc(vals)
        self.assertFalse(self.stages(out)["B1"]["complete"])

    # --- sweep-3a / regressions-5: the equipment parts have their own reach
    def test_equipment_life_and_mass_have_their_own_reach(self):
        self.assertEqual(bridge.FIELD_REACH["e_hvac_count"], ("A1-A3", "B3", "B4", "B5", "C3"))
        self.assertEqual(bridge.FIELD_REACH["e_hvac_life"], ("B3", "B4"))
        self.assertEqual(bridge.FIELD_REACH["e_hvac_mass"], ("B4", "B5", "C3"))
        for fid, x in (("e_hvac_life", 15.0), ("e_hvac_mass", 100.0)):
            vals = full(a_stages=V("a_stages", "EMBODIED"), **{fid: V(fid, x, "assumption")})
            _, rep = bridge.build(vals, REFSET, period=60)
            self.assertFalse(refl(rep)[fid], fid)
            self.assertEqual(rep["n_estimated"], 0, fid)
            _, out = self.calc(vals)
            self.assertFalse((out["range"] or {}).get("unknown_fields"), fid)
        _, out = self.calc(full(a_stages=V("a_stages", "EMBODIED"), e_hvac_life=R("e_hvac_life", 15.0, 10.0, 20.0)))
        self.assertFalse((out["range"] or {}).get("n_values_with_range"))      # no zero-width 「範囲のある 1 項目」
        # 建設時と解体時: the life still cannot act, the mass can (C3)
        vals = full(a_stages=V("a_stages", "UPFRONT_EOL"), e_hvac_life=V("e_hvac_life", 15.0, "assumption"),
                    e_hvac_mass=V("e_hvac_mass", 100.0, "assumption"))
        _, rep = bridge.build(vals, REFSET, period=60)
        self.assertFalse(refl(rep)["e_hvac_life"])
        self.assertTrue(refl(rep)["e_hvac_mass"])
        self.assertEqual(self.estimated(rep), {"e_hvac_mass"})

    def test_reach_is_a_superset_of_what_moves_the_total(self):
        """Every input reported not reflected (or total-neutral) is perturbed; none may move the total. One engine run
        per boundary and context perturbs them together; a move is then traced to the field one at a time."""
        contexts = {
            "complete": everything(),
            # partners unknown, and ORDERED quantities with only volume rows (no end-of-life mass)
            "partners unknown": drop(everything(a_recon_fraction=V("a_recon_fraction", None, "not_obtained"),
                                                m_quantity_basis=V("m_quantity_basis", "ORDERED"),
                                                **{f: V(f, None, "not_applicable") for f in ("m_rebar", "m_steel", "m_aluminium")}),
                                     "o_elec_kwh", "c_site_electricity", "r_gwp"),
            # the waste rate unknown (no A1-A3 for the materials), nothing leaks, no replacement inside T, recovery unknown
            "waste and recovery unknown": drop(everything(r_leak_rate=V("r_leak_rate", 0.0), r_life=V("r_life", 70.0)),
                                               "m_waste_rate", "r_recovery_rate"),
        }
        for cname, base in contexts.items():
            for preset in ("ALL", "EMBODIED", "UPFRONT_EOL", "NO_OPERATION"):
                vals = dict(base, a_stages=V("a_stages", preset))
                _, rep = bridge.build(vals, REFSET, period=60)
                r = refl(rep)
                quiet = [f for f, v in vals.items() if FL.FIELDS[f]["type"] in ("number", "integer", "enum")
                         and v.state in ("confirmed", "assumption") and f != "a_stages"
                         and (not r.get(f, True) or f in bridge.TOTAL_NEUTRAL)]
                if preset == "ALL" and cname == "complete":
                    self.assertTrue({"b_use", "b_structure", "g_foundation", "o_source", "b_project_type"} <= set(quiet))
                vv = dict(vals, **{f: perturbed(vals[f]) for f in quiet})
                if "o_pv_kwh" in quiet or cname == "complete":
                    vv.update(o_pv_kwh=V("o_pv_kwh", 30000.0), o_export_kwh=V("o_export_kwh", 10000.0))
                t0, t1 = self.total(vals), self.total(vv)
                if abs(t1 - t0) > 1e-6 * max(1.0, abs(t0)):
                    moved = [f for f in quiet if abs(self.total(dict(vals, **{f: perturbed(vals[f])})) - t0) > 1e-6 * abs(t0)]
                    self.fail("%s / %s: not reflected but moves the total: %s" % (cname, preset, moved))

    # --- sweep-3b: choices the engine never reads are recorded but not counted
    def test_choices_the_engine_never_reads_are_not_estimates(self):
        fids = ("b_use", "b_structure", "b_project_type", "g_foundation", "o_source")
        vals = full(b_use=V("b_use", "office", "assumption"), b_structure=V("b_structure", "RC", "assumption"),
                    b_project_type=V("b_project_type", "NEW_BUILD", "assumption"),
                    g_foundation=V("g_foundation", "PILE", "assumption"), o_source=V("o_source", "BILLS", "assumption"))
        _, rep = bridge.build(vals, REFSET, period=60)
        self.assertEqual(rep["n_estimated"], 0)
        rows = {r["field"]: r for r in bridge.reflection_table(rep)}
        for f in fids:
            self.assertTrue(rows[f]["reflected"], f)                         # still passed and shown
            self.assertIn("推定の数・範囲には数えない", rows[f]["detail"], f)
            self.assertIn(f, bridge.TOTAL_NEUTRAL)

    # --- sweep-3c: a factor (or a partner) whose quantity is unknown cannot change the total
    def test_a_factor_without_its_quantity_is_not_an_estimate(self):
        m3 = {f: V(f, None, "not_applicable") for f, *_ in FL.MATERIALS}
        m3["m_concrete"] = V("m_concrete", 500.0, unit="m3")
        cases = [
            ("o_grid_value", drop(full(o_grid_value=R("o_grid_value", 0.4, 0.2, 0.8)), "o_elec_kwh"), "o_elec_kwh"),
            ("o_grid_construction", drop(full(o_grid_construction=R("o_grid_construction", 0.4, 0.2, 0.8)), "c_site_electricity"),
             "c_site_electricity"),
            ("a_eol_haul_km", full(a_eol_haul_km=R("a_eol_haul_km", 20.0, 5.0, 100.0), **m3), None),
            ("a_eol_route", full(a_eol_route=V("a_eol_route", "RECYCLE", "assumption"), **m3), None),
            ("r_charge_kg", drop(full(r_charge_kg=V("r_charge_kg", 20.0, "assumption")), "r_gwp"), "r_gwp"),
            ("r_charge_kg", drop(full(r_charge_kg=V("r_charge_kg", 20.0, "assumption")), "r_leak_rate"), "r_leak_rate"),
            ("a_replacement_cycle", drop(full(a_reconstruction=V("a_reconstruction", "MAJOR_REFURBISHMENT"),
                                              a_replacement_cycle=V("a_replacement_cycle", 40.0, "assumption")), "a_recon_fraction"),
             "a_recon_fraction"),
            ("a_recon_fraction", full(a_reconstruction=V("a_reconstruction", "MAJOR_REFURBISHMENT"),
                                      a_recon_fraction=V("a_recon_fraction", 0.5, "assumption")), "a_replacement_cycle"),
            ("m_quantity_basis", full(m_quantity_basis=V("m_quantity_basis", "ORDERED", "assumption")), None),
            ("m_waste_rate", full(m_quantity_basis=V("m_quantity_basis", "ORDERED"), m_waste_rate=R("m_waste_rate", 0.05, 0.01, 0.3), **m3),
             None),
            ("m_waste_rate", full(a_stages=V("a_stages", "EMBODIED"), m_quantity_basis=V("m_quantity_basis", "AS_BUILT"),
                                  m_waste_rate=V("m_waste_rate", 0.05, "assumption")), None),
            ("m_rebar", drop(full(a_stages=V("a_stages", "EMBODIED"), m_rebar=V("m_rebar", 10.0, "assumption", "t")), "m_waste_rate"),
             "m_waste_rate"),
            ("m_repair_rate", drop(full(m_repair_rate=V("m_repair_rate", 0.01, "assumption")), "m_waste_rate"), "m_waste_rate"),
            ("r_top_up", full(r_leak_rate=V("r_leak_rate", 0.0), r_top_up=V("r_top_up", "no", "assumption")), None),
            ("r_charge_kg", drop(full(r_leak_rate=V("r_leak_rate", 0.0), r_life=V("r_life", 70.0),
                                      r_charge_kg=V("r_charge_kg", 20.0, "assumption")), "r_recovery_rate"), "r_recovery_rate"),
        ]
        for fid, vals, gap in cases:
            _, rep = bridge.build(vals, REFSET, period=60)
            row = {r["field"]: r for r in bridge.reflection_table(rep)}[fid]
            self.assertFalse(row["reflected"], fid)
            self.assertTrue(any(w in row["detail"] for w in ("合計を変えない", "使われない", "効かない")), (fid, row["detail"]))
            self.assertEqual(rep["n_estimated"], 0, fid)
            if gap:                                                      # the partner is still the named gap
                self.assertIn(gap, {m["field"] for m in rep["missing_inputs"]}, fid)
        # the range: no 範囲が不明 and no zero-width 範囲のある 1 項目
        _, out = self.calc(cases[0][1])
        self.assertFalse((out["range"] or {}).get("n_values_with_range"))
        _, out = self.calc(drop(full(o_grid_value=V("o_grid_value", 0.4, "assumption")), "o_elec_kwh"))
        self.assertFalse((out["range"] or {}).get("unknown_fields"))
        # with the quantity the factor counts again; with a grid factor of 0 it is what makes the purchase moot
        _, rep = bridge.build(full(o_grid_value=V("o_grid_value", 0.4, "assumption")), REFSET, period=60)
        self.assertEqual(self.estimated(rep), {"o_grid_value"})
        _, rep = bridge.build(drop(full(o_grid_value=V("o_grid_value", 0.0)), "o_elec_kwh"), REFSET, period=60)
        self.assertTrue(refl(rep)["o_grid_value"])

    def test_all_assumed_embodied_counts_only_what_can_move(self):
        vals = {k: (V(k, v.value, "assumption", v.unit) if v.state == "confirmed" else v)
                for k, v in everything(a_stages=V("a_stages", "EMBODIED")).items()}
        vals["a_stages"] = V("a_stages", "EMBODIED")
        _, rep = bridge.build(vals, REFSET, period=60)
        est = self.estimated(rep)
        never = {"b_use", "b_structure", "b_project_type", "g_foundation", "o_source"} | \
            {"e_%s_%s" % (t.lower(), p) for t, _ in FL.TRADES for p in ("life", "mass")}
        self.assertFalse(est & never, est & never)
        self.assertEqual(rep["n_estimated"], len(est))
        self.assertTrue({"m_rebar", "e_hvac_count", "c_diesel"} <= est)

    # --- sweep-4: the waste rate's direction follows the quantity basis
    def test_waste_rate_range_direction_follows_the_basis(self):
        self.assertTrue(bridge.decreasing("m_waste_rate", {"m_quantity_basis": V("m_quantity_basis", "ORDERED")}))
        self.assertFalse(bridge.decreasing("m_waste_rate", {"m_quantity_basis": V("m_quantity_basis", "DESIGN")}))
        for basis in ("ORDERED", "DESIGN"):
            vals = full(m_quantity_basis=V("m_quantity_basis", basis), m_waste_rate=R("m_waste_rate", 0.05, 0.01, 0.30),
                        m_rebar=R("m_rebar", 10.0, 9.0, 11.0, "t"))
            _, out = self.calc(vals)
            lo, hi = self.corners(vals, ["m_waste_rate", "m_rebar"])
            self.assertAlmostEqual(out["range"]["low_t"], lo, places=6, msg=basis)
            self.assertAlmostEqual(out["range"]["high_t"], hi, places=6, msg=basis)

    # --- sweep-5 / regressions-6: a deciding input whose range crosses T keeps its partner
    def test_a_range_across_t_keeps_the_partner(self):
        rec = dict(a_reconstruction=V("a_reconstruction", "MAJOR_REFURBISHMENT"))
        cases = [
            ("cycle 65 [50,70]", full(a_replacement_cycle=R("a_replacement_cycle", 65.0, 50.0, 70.0),
                                      a_recon_fraction=R("a_recon_fraction", 0.5, 0.3, 0.7), **rec),
             ["a_replacement_cycle", "a_recon_fraction"]),
            ("cycle 70 [40,80]", full(a_replacement_cycle=R("a_replacement_cycle", 70.0, 40.0, 80.0),
                                      a_recon_fraction=R("a_recon_fraction", 0.5, 0.3, 0.7), **rec),
             ["a_replacement_cycle", "a_recon_fraction"]),
            ("life 70 [40,80]", full(r_life=R("r_life", 70.0, 40.0, 80.0), r_loss_rate=R("r_loss_rate", 0.05, 0.03, 0.2)),
             ["r_life", "r_loss_rate"]),
            ("life 70 [40,80], B1 0 at the stored life", full(r_life=R("r_life", 70.0, 40.0, 80.0),
                                                              r_loss_rate=R("r_loss_rate", 0.05, 0.03, 0.2),
                                                              r_leak_rate=V("r_leak_rate", 0.0), r_recovery_rate=V("r_recovery_rate", 1.0)),
             ["r_life", "r_loss_rate"]),
        ]
        for name, vals, fids in cases:
            _, out = self.calc(vals)
            r = refl(out)
            self.assertTrue(all(r[f] for f in fids), (name, r))
            self.assertEqual(out["range"]["n_values_with_range"], 2, name)
            lo, hi = self.corners(vals, fids)
            self.assertAlmostEqual(out["range"]["low_t"], lo, places=6, msg=name)
            self.assertAlmostEqual(out["range"]["high_t"], hi, places=6, msg=name)
        # the range of the life reaches 40 years, where B1 is not 0: a missing charge leaves B1 incomplete
        vals = drop(full(r_life=R("r_life", 70.0, 40.0, 80.0), r_leak_rate=V("r_leak_rate", 0.0),
                         r_recovery_rate=V("r_recovery_rate", 1.0)), "r_charge_kg")
        _, out = self.calc(vals)
        self.assertFalse(self.stages(out)["B1"]["complete"])
        self.assertIn("r_charge_kg", {m["field"] for m in out["missing_inputs"]})
        # a range that stays beyond T still makes the partner moot
        _, rep = bridge.build(full(r_life=R("r_life", 70.0, 65.0, 80.0), r_loss_rate=V("r_loss_rate", 0.05, "assumption")),
                              REFSET, period=60)
        self.assertFalse(refl(rep)["r_loss_rate"])

    # --- sweep-6: under ORDERED / AS_BUILT the distance completes A4
    def test_a4_gap_under_ordered_names_the_distance_and_the_waste_rate(self):
        for basis in ("ORDERED", "AS_BUILT"):
            for gone, label in (("m_transport_km", "材料の運搬距離"), ("m_transport_mode", "材料の運搬手段")):
                vals = drop(full(m_quantity_basis=V("m_quantity_basis", basis)), "m_waste_rate", gone)
                _, out = self.calc(vals)
                gaps = {m["field"]: m for m in out["missing_inputs"]}
                self.assertIn("A4", gaps[gone]["stages"], (basis, gone))
                self.assertNotIn("A4", gaps["m_waste_rate"]["stages"], (basis, gone))
                hint = {h["stage"]: h for h in out["summary"]["hints"]}["A4"]
                self.assertIn(label, hint["note"])
                self.assertIn("廃棄率だけを入れると", hint["note"])           # the other (assumed) way
                reasons = [u["reason"] for u in out["unconnected"] if u["label"].endswith("の運搬（A4）")]
                self.assertTrue(reasons and all("発注量（運搬する量）が決まらない" not in x for x in reasons), reasons)
            # the distance alone completes A4
            _, out = self.calc(drop(full(m_quantity_basis=V("m_quantity_basis", basis)), "m_waste_rate"))
            self.assertTrue(self.stages(out)["A4"]["complete"])
        # under DESIGN the ordered mass itself needs the waste rate
        _, out = self.calc(drop(full(), "m_waste_rate", "m_transport_km"))
        gaps = {m["field"]: m for m in out["missing_inputs"]}
        self.assertIn("A4", gaps["m_waste_rate"]["stages"])
        self.assertTrue(any(u["reason"] == "廃棄率が未取得で発注量（運搬する量）が決まらない" for u in out["unconnected"]))

    # --- regressions-7: single-field estimate of the steel field that the structure does not use
    def test_single_steel_estimate_says_where_the_steel_goes(self):
        for structure, fid, other in (("S", "m_rebar", "m_steel"), ("SRC", "m_rebar", "m_steel"),
                                      ("RC", "m_steel", "m_rebar"), ("W", "m_steel", "m_rebar")):
            pid = self.app.projects.create("r10e", structure)
            for v in (V("b_use", "office"), V("b_gfa", 5000.0), V("b_structure", structure)):
                self.app.projects.put(pid, v)
            _, out = self.app.handle("POST", "/api/projects/%d/estimate" % pid, {"screen": "material", "field": fid})
            self.assertEqual(out["n_proposals"], 0)
            self.assertIn("鉄の全量（鉄筋＋鉄骨）", out["message"], structure)
            self.assertIn("「%s」の欄の候補になる" % FL.FIELDS[other]["label"], out["message"], structure)
            self.assertNotIn("条件が合わない", out["message"])
        # the field the structure uses still gets the candidates
        estimate._mlit = {"RC": {"鋼材": (1.3, "t")}}
        try:
            ranges = {("steel", "NR", "C", "OECD_JPN"): {"p_0": 0, "p_5": 10.0, "p_25": 30, "p_50": 50.0, "p_75": 70,
                                                         "p_95": 150.0, "p_100": 300, "raw": 0, "n": 40, "iterations": 2}}
            vals = {"b_gfa": V("b_gfa", 2000.0), "b_use": V("b_use", "office")}
            props, _ = estimate.estimate_materials(vals, "RC", only="m_rebar", ranges=ranges)
            self.assertEqual({v.field_id for v in props}, {"m_rebar"})
            self.assertEqual(len(props), 2)
        finally:
            estimate._mlit = None


if __name__ == "__main__":
    unittest.main()
