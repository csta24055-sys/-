"""Tests of WLC Studio (run: cd 23_WLC_STUDIO_APP && WLCSTUDIO_OFFLINE=1 python3 -B -m unittest discover -s tests -t .).

No network: connectors are exercised with fixtures; the engine is the real one (12_APP_BASE → 10_TRANSFORM_STUDY).
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
os.environ.setdefault("WLCSTUDIO_OFFLINE", "1")
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from wlcstudio import bridge, demo, documents, estimate, fields as FL, matrix, research, validate  # noqa: E402
from wlcstudio.engine import Engine  # noqa: E402
from wlcstudio.project import ProjectError, Projects  # noqa: E402
from wlcstudio.provenance import ProvenanceError, Uncertainty, Value, best, conflicts  # noqa: E402
from wlcstudio.server import ApiError, App, make_handler  # noqa: E402

REFSET = json.loads((HERE.parent / "12_APP_BASE" / "samples" / "refset_fictional.json").read_text(encoding="utf-8"))


def V(fid, value=None, state="confirmed", unit=None, **kw):
    F = FL.FIELDS[fid]
    kw.setdefault("method", "test")
    return Value(fid, state, value, unit if unit is not None else F.get("unit", ""), **kw)


def minimal(**over) -> dict:
    """The smallest set of values with which the engine runs (one material, explicit stages)."""
    v = {"b_use": V("b_use", "office"), "b_gfa": V("b_gfa", 1000.0), "a_stages": V("a_stages", "ALL"),
         "a_eol_route": V("a_eol_route", "LANDFILL"), "m_rebar": V("m_rebar", 10.0, unit="t"),
         "m_waste_rate": V("m_waste_rate", None, "not_applicable"), "m_reuse_rate": V("m_reuse_rate", None, "not_applicable"),
         "o_grid_value": V("o_grid_value", 0.4), "o_grid_construction": V("o_grid_construction", 0.4),
         "o_water_m3": V("o_water_m3", 1000.0), "o_sewage_m3": V("o_sewage_m3", 900.0), "o_waste_kg": V("o_waste_kg", 5000.0)}
    v.update(over)
    return {k: x for k, x in v.items() if x is not None}


def items(doc):
    out = {}
    for c in doc["categories"].values():
        out.update(c["items"])
    return out


def tables(doc):
    out = {}
    for c in doc["categories"].values():
        out.update(c["tables"])
    return out


class ProvenanceTests(unittest.TestCase):
    def test_states_are_kept_apart_and_missing_is_not_zero(self):
        with self.assertRaises(ProvenanceError):
            Value("b_gfa", "not_obtained", 0.0, method="x").check()          # a missing value cannot hold 0
        with self.assertRaises(ProvenanceError):
            Value("b_gfa", "confirmed", None, method="x").check()           # a confirmed value needs a value
        with self.assertRaises(ProvenanceError):
            Value("b_gfa", "statistical", 1.0, method="x", source_id="s").check()   # statistical needs an interval
        with self.assertRaises(ProvenanceError):
            Value("b_gfa", "statistical", 1.0, method="x", uncertainty=Uncertainty("interval", 0, 2, 0.9)).check()  # and a source
        with self.assertRaises(ProvenanceError):
            Value("b_gfa", "from_drawing", 1.0, method="x").check()         # drawing values need their document
        Value("b_gfa", "statistical", 1.0, method="x", source_id="s", uncertainty=Uncertainty("interval", 0, 2, 0.9)).check()
        Value("b_gfa", "not_applicable").check()
        with self.assertRaises(ProvenanceError):
            Uncertainty("interval", 3, 2, 0.9).check()

    def test_best_and_conflicts(self):
        a = Value("b_gfa", "statistical", 1000.0, method="m", source_id="s", uncertainty=Uncertainty("interval", 1, 2, .9), updated_at=2)
        b = Value("b_gfa", "from_drawing", 1200.0, method="m", source_id="d", updated_at=1)
        self.assertIs(best([a, b]), b)
        self.assertEqual(len(conflicts([a, b])), 1)
        self.assertEqual(conflicts([a, Value("b_gfa", "confirmed", 1010.0, method="m")]), [])


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.P = Projects(Path(self.td.name) / "p.sqlite3", upload_dir=Path(self.td.name) / "up", keep_uploads=True)

    def tearDown(self):
        self.P.close()
        self.td.cleanup()

    def test_create_sets_structure_and_explicit_boundary(self):
        pid = self.P.create("x", "S")
        vals = self.P.values(pid)
        self.assertEqual(vals["b_structure"].value, "S")
        self.assertEqual(vals["a_stages"].state, "assumption")        # explicit, not silently "all"
        with self.assertRaises(ProjectError):
            self.P.create("x", "XX")

    def test_history_is_kept_and_latest_is_used(self):
        pid = self.P.create("x", "RC")
        self.P.put(pid, V("e_hvac_mass", 100.0))
        self.P.put(pid, V("e_hvac_mass", 120.0, note="メーカー仕様の改訂"))   # a product spec update
        self.assertEqual([h.value for h in self.P.history(pid, "e_hvac_mass")], [100.0, 120.0])
        self.assertEqual(self.P.current(pid, "e_hvac_mass").value, 120.0)

    def test_type_unit_range_checks(self):
        pid = self.P.create("x", "RC")
        with self.assertRaises(ProjectError):
            self.P.put(pid, V("b_gfa", -5.0))
        with self.assertRaises(ProjectError):
            self.P.put(pid, V("b_gfa", 100.0, unit="ft2"))
        with self.assertRaises(ProjectError):
            self.P.put(pid, V("b_use", "hotel"))                      # not in the engine vocabulary
        with self.assertRaises(ProjectError):
            self.P.put(pid, V("b_floors_above", 3.5))                 # integer field
        self.P.put(pid, V("m_rebar", 5000.0, unit="kg"))              # an accepted alternative unit

    def test_candidates_need_acceptance(self):
        pid = self.P.create("x", "RC")
        cid = self.P.propose(pid, V("b_gfa", 900.0, "assumption", note="plateau"), "plateau")
        self.assertEqual(self.P.propose(pid, V("b_gfa", 900.0, "assumption", note="plateau"), "plateau"), cid)  # no duplicate
        self.assertNotIn("b_gfa", self.P.values(pid))                  # a candidate is not a value
        v = self.P.accept(pid, "b_gfa", 0)
        self.assertEqual((v.value, v.state), (900.0, "assumption"))
        self.assertEqual(self.P.candidates(pid, "b_gfa"), [])

    def test_progress_is_fill_ratio(self):
        pid = self.P.create("x", "RC")
        pr = self.P.progress(pid)
        self.assertEqual(pr["filled"], 2)
        self.assertEqual(pr["total"], len(FL.FIELDS))
        self.assertIn("精度ではない", pr["note"])

    def test_delete_removes_everything(self):
        pid = self.P.create("x", "RC")
        self.P.put(pid, V("b_gfa", 100.0))
        self.P.add_document(pid, "a.csv", "csv", b"abc", {})
        f = self.P.documents(pid)
        self.assertTrue(f[0]["kept"])
        out = self.P.delete(pid)
        self.assertEqual(out["deleted_files"], 1)
        self.assertEqual(list((Path(self.td.name) / "up").iterdir()), [])
        with self.assertRaises(ProjectError):
            self.P.get(pid)


class BridgeTests(unittest.TestCase):
    def test_missing_is_not_passed_as_zero(self):
        doc, rep = bridge.build(minimal(b_gfa=None), REFSET)
        it = items(doc)
        self.assertNotIn("project.gross_floor_area", it)
        self.assertNotIn("project.use_area_breakdown", it)
        self.assertTrue(any("延床面積" in m for m in rep["missing_required"]))
        doc, rep = bridge.build(minimal(b_gfa=V("b_gfa", None, "not_computable")), REFSET)
        self.assertNotIn("project.gross_floor_area", items(doc))

    def test_stages_are_always_explicit(self):
        doc, rep = bridge.build(minimal(), REFSET)
        self.assertEqual(len(items(doc)["boundary.included_lifecycle_stages"]), 14)
        doc, rep = bridge.build(minimal(a_stages=V("a_stages", None, "not_obtained")), REFSET)
        self.assertIn("評価範囲（ライフサイクル段階）", rep["missing_required"])

    def test_not_applicable_meanings(self):
        doc, _ = bridge.build(minimal(b_floors_below=V("b_floors_below", None, "not_applicable"),
                                      m_steel=V("m_steel", None, "not_applicable"),
                                      o_oil_l=V("o_oil_l", None, "not_applicable")), REFSET)
        it = items(doc)
        self.assertEqual(it["project.floors_below"], 0)                 # na="zero": nothing there
        self.assertEqual(it["operation.oil.base"], 0.0)
        self.assertEqual(it["operation.states"]["oil"], "EXPLICIT_ZERO")
        self.assertFalse(any(r["material_class"] == "STRUCTURAL_STEEL" for r in tables(doc)["materials"]))  # na="absent"

    def test_engine_states_for_sys01(self):
        doc, _ = bridge.build(minimal(m_rebar=V("m_rebar", 10.0, "statistical", "t", source_id="s",
                                                uncertainty=Uncertainty("interval", 5, 20, 0.9))), REFSET)
        row = tables(doc)["materials"][0]
        self.assertEqual(row["states"]["quantity"], "ESTIMATE")
        self.assertEqual(row["states"]["end_of_life.mass_kg"], "ESTIMATE")     # computed from an estimate: still an estimate
        self.assertEqual(row["provenance_id"], "WLC-ESTIMATE")
        doc2, _ = bridge.build(minimal(), REFSET)
        self.assertEqual(tables(doc2)["materials"][0]["states"]["end_of_life.mass_kg"], "DERIVED")
        self.assertEqual(items(doc)["project.states"]["gross_floor_area"], "OBSERVED")
        self.assertEqual({p["value_state"] for p in tables(doc)["provenance"]}, {"OBSERVED", "DERIVED", "ESTIMATE", "MISSING"})

    def test_no_address_or_name_in_engine_document(self):
        vals = minimal(b_name=V("b_name", "秘密ビル"), b_address=V("b_address", "東京都どこか1-2-3"))
        doc, rep = bridge.build(vals, REFSET)
        text = json.dumps(doc, ensure_ascii=False)
        self.assertNotIn("秘密ビル", text)
        self.assertNotIn("どこか", text)

    def test_units_select_factor_and_conversion(self):
        d1, _ = bridge.build(minimal(m_concrete=V("m_concrete", 100.0, unit="m3")), REFSET)
        d2, _ = bridge.build(minimal(m_concrete=V("m_concrete", 230.0, unit="t")), REFSET)
        c1 = [r for r in tables(d1)["materials"] if r["material_class"] == "CONCRETE"][0]
        c2 = [r for r in tables(d2)["materials"] if r["material_class"] == "CONCRETE"][0]
        self.assertEqual(c1["factor_id"], "F-MAT-CONCRETE-01")       # m3 factor
        self.assertEqual(c2["factor_id"], "F-MATKG-CONCRETE-01")     # mass factor, t converted by the set's definition
        self.assertIsNone(c1["end_of_life.mass_kg"])                  # no density is assumed
        self.assertEqual(c2["end_of_life.mass_kg"], 230000.0)

    def test_double_counting_whole_concrete_and_foundation(self):
        whole = V("m_concrete", 2000.0, "statistical", "t", method="rasmi_mi_x_gfa", source_id="rasmi",
                  uncertainty=Uncertainty("interval", 1000, 3000, 0.9))
        doc, rep = bridge.build(minimal(m_concrete=whole, m_concrete_fdn=V("m_concrete_fdn", 300.0, unit="m3")), REFSET)
        conc = [r for r in tables(doc)["materials"] if r["material_class"] == "CONCRETE"]
        self.assertEqual(len(conc), 1)
        self.assertTrue(rep["double_count"])

    def test_reflection_report_and_unconnected_ledger(self):
        doc, rep = bridge.build(minimal(), REFSET)
        rows = {r["field"]: r for r in bridge.reflection_table(rep)}
        self.assertTrue(rows["b_gfa"]["reflected"])
        self.assertFalse(rows["b_address"]["reflected"])
        self.assertIn("記録のみ", rows["b_address"]["detail"])
        self.assertFalse(rows["m_timber"]["reflected"])
        self.assertIn("合計に入っていない", rows["m_timber"]["detail"])
        self.assertIn("木材（構造材）", rep["missing_materials"])
        self.assertTrue(any("EPD" in u["reason"] for u in rep["unconnected"]))

    def test_excluded_stage_fills_required_table_with_flagged_zero(self):
        vals = minimal(a_stages=V("a_stages", "EMBODIED"), o_water_m3=None, o_sewage_m3=None, o_waste_kg=None, o_grid_value=None)
        doc, rep = bridge.build(vals, REFSET)
        self.assertEqual(rep["missing_required"], [])
        self.assertEqual(items(doc)["water_waste.water.base"], 0.0)
        self.assertEqual(items(doc)["water_waste.states"]["water"], "EXPLICIT_ZERO")
        vals = minimal(o_water_m3=None)                                  # B7 included: water is really missing
        doc, rep = bridge.build(vals, REFSET)
        self.assertIn("上水の使用量", rep["missing_required"])

    def test_binding_coverage_counts(self):
        cov = bridge.binding_coverage()
        self.assertEqual(cov["n_binding"], 241)
        self.assertGreater(cov["n_reached"], 100)
        self.assertEqual(cov["n_reached"] + len(cov["not_reached"]), 241)


class EngineTests(unittest.TestCase):
    """The real 70-unit engine through the existing app (nothing re-implemented)."""

    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.TemporaryDirectory()
        cls.E = Engine(Path(cls.td.name) / "e.sqlite3")
        cls.ref = cls.E.refset_dict()

    @classmethod
    def tearDownClass(cls):
        cls.E.close()
        cls.td.cleanup()

    def run_vals(self, vals, T=60.0, pid=None):
        doc, rep = bridge.build(vals, self.ref)
        self.assertEqual(rep["missing_required"], [], rep["missing_required"])
        return self.E.run(doc, pid, T), doc, rep

    def test_minimal_runs_and_total_is_not_zero(self):
        r, _, _ = self.run_vals(minimal())
        self.assertEqual(r["run"]["status"], "ok", r["run"]["message"])
        self.assertGreater(r["results"]["SUM-03"]["value"], 0)
        self.assertTrue(r["run"]["versions"]["engine_is_verified_version"])

    def test_versioned_recalculation_reuses_prepared_system(self):
        r1, doc, _ = self.run_vals(minimal())
        pid = r1["lca_project_id"]
        n = self.E.svc.prepared
        r2 = self.E.run(doc, pid, 30.0)                                 # only T changes
        self.assertTrue(r2["reused_input_version"])
        self.assertEqual(self.E.svc.prepared, n)                        # System(scenario) not rebuilt
        self.assertNotEqual(r2["results"]["SUM-03"]["value"], r1["results"]["SUM-03"]["value"])
        r3, _, _ = self.run_vals(minimal(m_rebar=V("m_rebar", 12.0, unit="t")), pid=pid)
        self.assertFalse(r3["reused_input_version"])                   # changed input -> a new input version
        self.assertNotEqual(r3["input_version_id"], r1["input_version_id"])

    def test_period_ends(self):
        for T in (1.0, 130.0):
            r, _, _ = self.run_vals(minimal(), T=T)
            self.assertEqual(r["run"]["status"], "ok")
        doc, _ = bridge.build(minimal(), self.ref)
        r = self.E.run(doc, None, 131.0)
        self.assertEqual(r["run"]["status"], "blocked")

    def test_tonnes_and_kilograms_give_the_same_a13(self):
        a, _, _ = self.run_vals(minimal(m_rebar=V("m_rebar", 10.0, unit="t")))
        b, _, _ = self.run_vals(minimal(m_rebar=V("m_rebar", 10000.0, unit="kg")))
        self.assertAlmostEqual(a["results"]["A13-01"]["value"], b["results"]["A13-01"]["value"], delta=1e-9 * a["results"]["A13-01"]["value"])

    def test_refrigerant_states(self):
        base = dict(r_charge_kg=V("r_charge_kg", 50.0), r_gwp=V("r_gwp", 2000.0), r_loss_rate=V("r_loss_rate", 0.05),
                    r_recovery_rate=V("r_recovery_rate", 0.5), r_life=V("r_life", 15.0), r_top_up=V("r_top_up", "yes"))
        full, _, _ = self.run_vals(minimal(**base, r_leak_rate=V("r_leak_rate", 0.05)))
        zero, _, _ = self.run_vals(minimal(**base, r_leak_rate=V("r_leak_rate", None, "not_applicable")))
        miss, _, rep = self.run_vals(minimal(**base))
        self.assertGreater(full["results"]["B1-02"]["value"], 0)
        self.assertEqual(zero["results"]["B1-02"]["value"], 0.0)       # explicit "no leak"
        self.assertIn("B1-02", miss["results"]["X-02"]["incomplete_units"])   # missing leak rate: incomplete, not 0
        none, _, _ = self.run_vals(minimal(r_charge_kg=V("r_charge_kg", None, "not_applicable")))
        self.assertEqual(none["results"]["B1-04"]["value"], 0.0)

    def test_ground_scenarios_do_not_change_the_total(self):
        totals = set()
        for g in ("DIRECT", "PILE", "IMPROVEMENT", "UNKNOWN"):
            r, _, _ = self.run_vals(minimal(g_foundation=V("g_foundation", g)))
            totals.add(round(r["results"]["SUM-03"]["value"], 6))
        self.assertEqual(len(totals), 1)                                # record only: no structural decision is made

    def test_vectorised_a13_equals_engine(self):
        vals = minimal(m_concrete=V("m_concrete", 120.0, unit="m3"), m_glass=V("m_glass", 300.0, unit="m2"),
                       m_mortar=V("m_mortar", 2.5, unit="t"), m_quantity_basis=V("m_quantity_basis", "DESIGN"),
                       m_waste_rate=V("m_waste_rate", 0.04))
        r, doc, _ = self.run_vals(vals)
        vec = matrix.a13_vectors(doc, self.ref)
        eng = r["results"]["A13-01"]["by_item"]
        self.assertEqual(len(vec["e"]), len(eng))
        for a, b in zip(vec["e"], eng):
            self.assertAlmostEqual(a, b, delta=1e-9 * max(1.0, abs(b)))
        lo, hi = matrix.a13_bounds(vec, vec["q"] * 0.5, vec["q"] * 2.0)
        self.assertAlmostEqual(lo, vec["total"] * 0.5)
        self.assertAlmostEqual(hi, vec["total"] * 2.0)

    def test_demo_is_fictional_and_runs(self):
        doc, rep = bridge.build(demo.demo_values(), self.ref)
        self.assertEqual(doc["data_kind"], "fictional")
        r = self.E.run(doc, None, 60.0)
        self.assertEqual(r["run"]["status"], "ok")


class MatrixTests(unittest.TestCase):
    def test_masks_partition_and_unknown_is_not_zero(self):
        vals = minimal(m_steel=V("m_steel", None, "not_applicable"))
        inc = matrix.incidence(vals)
        self.assertTrue(((inc["has"] + inc["na"] + inc["unknown"]) == 1).all())
        self.assertIn("project.gross_floor_area", inc["reached"])
        self.assertNotIn("project.building_height", inc["reached"])
        self.assertIn("project.building_height", inc["only_unknown"])


class ImportTests(unittest.TestCase):
    def test_csv_total_rows_and_non_numbers(self):
        csv = "名称,数量,単位,区分\nコンクリート,100,m3,躯体\nコンクリート,20,m3,基礎\n鉄筋,5,t,躯体\n合計,125,m3,\n鉄骨,未定,t,躯体\nガラス,30,ft2,外装\n".encode("utf-8")
        r = documents.read("q.csv", base64.b64encode(csv).decode(), "doc1")
        got = {(v.field_id, v.unit): v.value for v in r["proposals"]}
        self.assertEqual(got[("m_concrete", "m3")], 100.0)
        self.assertEqual(got[("m_concrete_fdn", "m3")], 20.0)
        self.assertEqual(got[("m_rebar", "t")], 5.0)
        reasons = " ".join(u["reason"] for u in r["unused"])
        self.assertIn("合計", reasons)
        self.assertIn("0 として読まない", reasons)
        self.assertIn("単位", reasons)
        self.assertTrue(all(v.state == "from_drawing" and v.source_id == "doc1" for v in r["proposals"]))
        self.assertIn("doc1:csv!R2C2", next(v for v in r["proposals"] if v.field_id == "m_concrete").source_detail)

    def test_ifc_quantities_and_missing_quantity_sets(self):
        ifc = """ISO-10303-21;
HEADER;FILE_SCHEMA(('IFC4'));ENDSEC;
DATA;
#10=IFCSLAB('2abc',$,'Slab 1',$,$,$,$,$,$);
#11=IFCBEAM('3abc',$,'Beam 1',$,$,$,$,$,$);
#20=IFCQUANTITYVOLUME('NetVolume',$,$,12.5,$);
#21=IFCELEMENTQUANTITY('q1',$,'Qto_SlabBaseQuantities',$,$,(#20));
#22=IFCRELDEFINESBYPROPERTIES('r1',$,$,$,(#10),#21);
#30=IFCMATERIAL('Concrete C30/37',$,$);
#31=IFCRELASSOCIATESMATERIAL('m1',$,$,$,(#10,#11),#30);
ENDSEC;
END-ISO-10303-21;
"""
        r = documents.read("m.ifc", base64.b64encode(ifc.encode()).decode(), "doc2")
        self.assertEqual([(v.field_id, v.value, v.unit) for v in r["proposals"]], [("m_concrete", 12.5, "m3")])
        self.assertIn("doc2:#10/#20", r["proposals"][0].source_detail)
        self.assertTrue(any("3abc" in str(u) or "Beam" in u["name"] for u in r["unused"]))   # no quantity: not counted

    def test_unknown_format(self):
        with self.assertRaises(ValueError):
            documents.read("x.docx", base64.b64encode(b"PK..").decode(), "d")


class EstimateTests(unittest.TestCase):
    RANGES = {("concrete", "NR", "C", "OECD_JPN"): {"p_0": 0, "p_5": 400.0, "p_25": 700, "p_50": 1000.0, "p_75": 1300, "p_95": 2000.0, "p_100": 3000, "raw": 0, "n": 80, "iterations": 2},
              ("steel", "NR", "C", "OECD_JPN"): {"p_0": 0, "p_5": 10.0, "p_25": 30, "p_50": 50.0, "p_75": 70, "p_95": 150.0, "p_100": 300, "raw": 0, "n": 40, "iterations": 2}}

    def setUp(self):
        estimate._mlit = {"RC": {"生コンクリート": (7.0, "㎥"), "鋼材": (1.3, "t"), "木材": (0.4, "㎥")}}

    def tearDown(self):
        estimate._mlit = None

    def test_material_estimates_carry_source_interval_and_no_invention(self):
        vals = {"b_gfa": V("b_gfa", 2000.0), "b_use": V("b_use", "office")}
        props, msgs = estimate.estimate_materials(vals, "RC", ranges=self.RANGES)
        by = {(v.field_id, v.method): v for v in props}
        mlit = by[("m_concrete", "mlit_area_unit_x_gfa")]
        self.assertAlmostEqual(mlit.value, 7.0 * 2000 / 10)
        self.assertEqual(mlit.unit, "m3")
        self.assertAlmostEqual(mlit.uncertainty.low, 1400 * 0.4)        # RASMI relative spread applied
        self.assertFalse(mlit.uncertainty.calibrated)
        ras = by[("m_concrete", "rasmi_mi_x_gfa")]
        self.assertAlmostEqual(ras.value, 2000.0)                        # 1000 kg/m2 × 2000 m2 = 2000 t
        self.assertEqual(ras.permission, "CC-BY-4.0")
        self.assertTrue(all(v.state == "statistical" and v.source_id for v in props))
        self.assertNotIn(("m_glass", "rasmi_mi_x_gfa"), by)              # no range in the fixture -> no candidate

    def test_needs_area_and_use_and_respects_better_data(self):
        props, msgs = estimate.estimate_materials({}, "RC", ranges=self.RANGES)
        self.assertEqual(props, [])
        vals = {"b_gfa": V("b_gfa", 2000.0), "b_use": V("b_use", "office"),
                "m_concrete": V("m_concrete", 900.0, "from_drawing", "m3", source_id="doc")}
        props, msgs = estimate.estimate_materials(vals, "RC", ranges=self.RANGES)
        self.assertFalse(any(v.field_id == "m_concrete" for v in props))
        vals = {"b_gfa": V("b_gfa", 2000.0), "b_use": V("b_use", "office"), "m_concrete_fdn": V("m_concrete_fdn", 50.0, unit="m3")}
        props, msgs = estimate.estimate_materials(vals, "RC", ranges=self.RANGES)
        self.assertFalse(any(v.field_id == "m_concrete" for v in props))   # whole-building figure would double count

    def test_equipment_and_water_refuse_without_source(self):
        r = estimate.run({}, "RC", screen="equipment")
        self.assertEqual(r["proposals"], [])
        self.assertIn("概算しない", r["messages"][0])


class ResearchTests(unittest.TestCase):
    def test_plateau_candidate_mapping(self):
        c = {"plateau_building_id": "13101-bldg-1", "storeys_above": 8, "storeys_below": 0, "measured_height_m": 28.3,
             "address": "東京都千代田区", "usage": "商業施設", "roof_edge_area_m2": 500.0, "floor_area_factor": 1.0,
             "estimated_gross_floor_area_m2": 4000.0, "structure_type": "鉄骨造", "survey_year": "2021", "tile": "t.b3dm"}
        props, notes = research.plateau_proposals(c, "RC")
        by = {v.field_id: v for v in props}
        self.assertEqual(by["b_floors_above"].state, "confirmed")
        self.assertEqual(by["b_floors_below"].state, "not_applicable")
        self.assertEqual(by["b_gfa"].state, "assumption")               # an estimate, not the recorded floor area
        self.assertEqual(by["b_use"].value, "retail")
        self.assertTrue(any("違う" in n for n in notes))                # structure hint differs from the chosen one
        c2 = dict(c, total_floor_area_m2=3800.0)
        by2 = {v.field_id: v for v in research.plateau_proposals(c2, "S")[0]}
        self.assertEqual((by2["b_gfa"].state, by2["b_gfa"].value), ("confirmed", 3800.0))


class ValidationTests(unittest.TestCase):
    def test_holdout_never_uses_the_same_publication(self):
        mk = lambda i, g, c: {"id": str(i), "country": "Japan", "oecd": True, "function": "NR", "structure": "RC",
                              "group": (g, "2000"), "mi": {"concrete": c, "steel": None, "wood": None}}
        data = [mk(0, "A", 1000.0)] + [mk(i, "A", 5000.0) for i in range(1, 6)] + [mk(i, "B", 1000.0) for i in range(6, 11)]
        p = validate.holdout_predict(data[0], data, "concrete")
        self.assertEqual(p[0], 1000.0)                                   # group A (5000s) is excluded
        m = validate._metrics([(1.0, 1.0, 0.5, 2.0), (2.0, 1.0, 1.5, 2.5)])
        self.assertEqual(m["share_ape_le_10"], 0.5)
        self.assertEqual(m["coverage_p5_p95"], 0.5)


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.TemporaryDirectory()
        cls.app = App(cls.td.name)

    @classmethod
    def tearDownClass(cls):
        cls.app.engine.close()
        cls.app.projects.close()
        cls.td.cleanup()

    def test_full_api_flow(self):
        a = self.app
        _, r = a.handle("POST", "/api/projects", {"structure": "RC", "name": "t"})
        pid = r["id"]
        _, meta = a.handle("GET", "/api/meta", None)
        self.assertEqual(set(meta["states"]), {"confirmed", "from_drawing", "statistical", "assumption", "not_obtained", "not_applicable", "not_computable"})
        self.assertIn("J-CAT の複製・認定品・互換品ではありません", meta["disclaimer"])
        with self.assertRaises(ApiError):
            a.handle("PUT", "/api/projects/%d/fields/b_gfa" % pid, {"value": "", "state": "confirmed"})
        with self.assertRaises(ApiError):                                 # statistical only through candidates
            a.handle("PUT", "/api/projects/%d/fields/b_gfa" % pid, {"value": 5, "state": "statistical"})
        _, blocked = a.handle("POST", "/api/projects/%d/calculate" % pid, {"period": 60})
        self.assertEqual(blocked["status"], "blocked")
        for fid, v in minimal().items():
            body = {"state": v.state, "value": v.value, "unit": v.unit}
            a.handle("PUT", "/api/projects/%d/fields/%s" % (pid, fid), body)
        _, out = a.handle("POST", "/api/projects/%d/calculate" % pid, {"period": 60})
        self.assertEqual(out["status"], "ok", out.get("message"))
        self.assertIn("架空", out["factor_note"])
        self.assertTrue(out["summary"]["lower_bound"])                   # materials missing -> flagged as a lower bound
        for bad in (0, -1, 131, "abc"):
            with self.assertRaises(ApiError):
                a.handle("POST", "/api/projects/%d/calculate" % pid, {"period": bad})
        _, led = a.handle("GET", "/api/projects/%d/ledger" % pid, None)
        self.assertEqual(led["binding_coverage"]["n_binding"], 241)
        _, d = a.handle("DELETE", "/api/projects/%d" % pid, None)
        self.assertEqual(d["deleted_project"], pid)

    def test_document_twice_is_refused(self):
        _, r = self.app.handle("POST", "/api/projects", {"structure": "S"})
        body = {"name": "q.csv", "data_b64": base64.b64encode("名称,数量,単位\n鉄骨,10,t\n".encode()).decode()}
        _, out = self.app.handle("POST", "/api/projects/%d/documents" % r["id"], body)
        self.assertEqual(out["n_proposals"], 1)
        with self.assertRaises(ApiError) as e:
            self.app.handle("POST", "/api/projects/%d/documents" % r["id"], body)
        self.assertEqual(e.exception.status, 409)

    def test_http_guards(self):
        import http.client
        import threading
        from http.server import HTTPServer
        httpd = HTTPServer(("127.0.0.1", 0), make_handler(self.app, 0))
        port = httpd.server_address[1]
        httpd.RequestHandlerClass = make_handler(self.app, port)
        th = threading.Thread(target=httpd.handle_request)
        results = []

        def req(method, path, headers, body=None):
            th = threading.Thread(target=httpd.handle_request)
            th.start()
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
            c.request(method, path, body=body, headers=headers)
            r = c.getresponse()
            out = (r.status, dict(r.getheaders()), r.read())
            c.close()
            th.join()
            return out
        ok = req("GET", "/api/meta", {"Host": "127.0.0.1:%d" % port})
        self.assertEqual(ok[0], 200)
        self.assertIn("frame-ancestors 'none'", ok[1]["Content-Security-Policy"])
        self.assertEqual(req("GET", "/api/meta", {"Host": "evil.example:%d" % port})[0], 421)       # DNS rebinding
        self.assertEqual(req("POST", "/api/projects", {"Host": "127.0.0.1:%d" % port, "Origin": "http://evil.example",
                                                       "Content-Type": "application/json"}, b'{"structure":"RC"}')[0], 403)
        self.assertEqual(req("POST", "/api/projects", {"Host": "127.0.0.1:%d" % port, "Content-Type": "text/plain"},
                             b'{"structure":"RC"}')[0], 415)
        self.assertEqual(req("GET", "/../wlcstudio/server.py", {"Host": "127.0.0.1:%d" % port})[0], 404)   # no path escape
        self.assertEqual(req("POST", "/api/projects", {"Host": "127.0.0.1:%d" % port, "Content-Type": "application/json",
                                                       "Content-Length": "-5"}, None)[0], 400)
        httpd.server_close()

    def test_refuses_non_loopback_bind(self):
        from wlcstudio import server
        with self.assertRaises(SystemExit):
            server.serve(self.td.name, host="0.0.0.0", port=0)


class ReviewFixTests(unittest.TestCase):
    """Regression tests for the 31 findings of the adversarial review (docs/review_fixes.md)."""

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

    def run_vals(self, vals, T=60.0):
        doc, rep = bridge.build(vals, self.app.refset)
        self.assertEqual(rep["missing_required"], [])
        return self.E.run(doc, None, T), doc, rep

    def full(self, **over):
        """A value set with everything filled (equipment, refrigerant, fuel, profiles), so that it is complete."""
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

    # --- missing inputs make the total a lower bound (findings 0, 15, 24)
    def test_missing_equipment_refrigerant_fuel_are_flagged(self):
        base, _, rep0 = self.run_vals(self.full())
        self.assertEqual([m for m in rep0["missing_inputs"] if m["field"] in FL.FIELDS], [])
        # C1 demolition and A5 site waste have no screen field: always reported (the total is honestly a lower bound)
        self.assertEqual({m["field"] for m in rep0["missing_inputs"]}, {"end_of_life.demolition_activities", "construction.waste_streams"})
        vals = self.full()
        for t, _ in FL.TRADES:
            vals.pop("e_%s_count" % t.lower())
        vals.pop("r_charge_kg")
        vals.pop("c_diesel")
        r, doc, rep = self.run_vals(vals)
        fields = {m["field"] for m in rep["missing_inputs"]}
        self.assertTrue({"e_hvac_count", "r_charge_kg", "c_diesel"} <= fields)
        inc = r["results"]["X-02"]["incomplete_units"]
        self.assertIn("A5-02", inc)                                   # placeholder fuel row: the engine itself says so
        self.assertTrue(any(u.startswith("B1-") for u in inc))
        self.assertFalse(r["results"]["SUM-03"]["complete"])
        rows = tables(doc)["equipment"]
        self.assertTrue(all(r_["quantity"] is None for r_ in rows))

    def test_server_marks_lower_bound_and_stage(self):
        pid = self.app.projects.create("lb", "RC")
        vals = self.full()
        vals.pop("e_hvac_count")
        for fid, v in vals.items():
            self.app.projects.put(pid, v)
        _, out = self.app.handle("POST", "/api/projects/%d/calculate" % pid, {"period": 60})
        self.assertTrue(out["summary"]["lower_bound"])
        self.assertFalse(out["summary"]["complete"])
        st = {x["stage"]: x["complete"] for x in out["summary"]["stages"]}
        self.assertFalse(st["A1-A3"])
        self.assertTrue(any(m["field"] == "e_hvac_count" for m in out["missing_inputs"]))

    def test_nothing_counted_is_not_shown_as_a_number(self):
        pid = self.app.projects.create("zero", "RC")
        vals = minimal(m_rebar=V("m_rebar", None, "not_applicable"))
        for fid, v in vals.items():
            self.app.projects.put(pid, v)
        _, out = self.app.handle("POST", "/api/projects/%d/calculate" % pid, {"period": 60})
        self.assertTrue(out["summary"]["lower_bound"])

    # --- refrigerant top-up missing (16)
    def test_missing_top_up_does_not_silently_cut_b1(self):
        r, doc, rep = self.run_vals(self.full(r_top_up=None))
        self.assertIsNone(tables(doc)["refrigerants"][0]["charge_mass_kg"])
        self.assertTrue(any(u.startswith("B1-") for u in r["results"]["X-02"]["incomplete_units"]))
        self.assertTrue(any(m["field"] == "r_top_up" for m in rep["missing_inputs"]))

    # --- double counting with MLIT and all-steel estimates (2, 17)
    def test_double_counting_mlit_concrete_and_all_steel(self):
        unc = Uncertainty("interval", 1, 2000, 0.9)
        whole = V("m_concrete", 700.0, "statistical", "m3", method="mlit_area_unit_x_gfa", source_id="mlit", factor_version="r6", uncertainty=unc)
        doc, rep = bridge.build(self.full(m_concrete=whole, m_concrete_fdn=V("m_concrete_fdn", 50.0, unit="m3")), REFSET)
        self.assertEqual(len([r for r in tables(doc)["materials"] if r["material_class"] == "CONCRETE"]), 1)
        steel = V("m_rebar", 130.0, "statistical", "t", method="mlit_area_unit_x_gfa", source_id="mlit", factor_version="r6", uncertainty=unc)
        doc, rep = bridge.build(self.full(m_rebar=steel, m_steel=V("m_steel", 40.0, unit="t")), REFSET)
        classes = [r["material_class"] for r in tables(doc)["materials"]]
        self.assertIn("REBAR", classes)
        self.assertNotIn("STRUCTURAL_STEEL", classes)
        self.assertTrue(any("鉄" in x for x in rep["double_count"]))
        estimate._mlit = {"RC": {"鋼材": (1.3, "t")}}
        try:
            props, msgs = estimate.estimate_materials({"b_gfa": V("b_gfa", 1000.0), "b_use": V("b_use", "office"),
                                                       "m_steel": V("m_steel", 40.0, unit="t")}, "RC", ranges={})
            self.assertFalse(any(p.field_id == "m_rebar" for p in props))
        finally:
            estimate._mlit = None

    # --- end-of-life mass follows the quantity basis (19); installation factor unit (22); states (4, 20)
    def test_masses_follow_quantity_basis(self):
        for basis, expect in (("DESIGN", 10000.0), ("ORDERED", 9000.0)):
            doc, _ = bridge.build(self.full(m_rebar=V("m_rebar", 10.0, unit="t"), m_quantity_basis=V("m_quantity_basis", basis),
                                            m_waste_rate=V("m_waste_rate", 0.1)), REFSET)
            row = [r for r in tables(doc)["materials"] if r["material_class"] == "REBAR"][0]
            self.assertAlmostEqual(row["end_of_life.mass_kg"], expect)
        r, _, _ = self.run_vals(self.full(m_rebar=V("m_rebar", 10.0, unit="t"), m_waste_rate=V("m_waste_rate", 0.1)))
        self.assertTrue(r["results"]["C-05"]["ok"], r["results"]["C-05"])

    def test_installation_factor_unit_and_assumed_zero_state(self):
        doc, rep = bridge.build(self.full(m_concrete=V("m_concrete", 100.0, unit="t")), REFSET)
        row = [r for r in tables(doc)["materials"] if r["material_class"] == "CONCRETE"][0]
        self.assertIsNone(row["installation_factor_id"])              # F-INST-CONCRETE is per m3, the row is in t
        doc, _ = bridge.build(self.full(m_waste_rate=V("m_waste_rate", 0.0, "assumption")), REFSET)
        self.assertEqual(tables(doc)["materials"][0]["states"]["waste_rate"], "ESTIMATE")
        prov = tables(doc)["provenance"][0]
        self.assertIsNone(prov["measurement_year"])

    # --- presets (18)
    def test_no_operation_preset_excludes_b2(self):
        st = dict((k, s) for k, _, s in FL.STAGE_PRESETS)["NO_OPERATION"]
        self.assertNotIn("B2", st)

    # --- IFC units and cycles (3, 10)
    def test_ifc_millimetre_units_and_cycle(self):
        ifc = """ISO-10303-21;
HEADER;FILE_SCHEMA(('IFC4'));ENDSEC;
DATA;
#1=IFCSIUNIT(*,.LENGTHUNIT.,.MILLI.,.METRE.);
#2=IFCSIUNIT(*,.AREAUNIT.,.MILLI.,.SQUARE_METRE.);
#3=IFCSIUNIT(*,.VOLUMEUNIT.,.MILLI.,.CUBIC_METRE.);
#4=IFCUNITASSIGNMENT((#1,#2,#3));
#10=IFCSLAB('2abc',$,'Slab 1',$,$,$,$,$,$);
#20=IFCQUANTITYVOLUME('NetVolume',$,$,12500000000.,$);
#21=IFCELEMENTQUANTITY('q1',$,'Qto',$,$,(#20));
#22=IFCRELDEFINESBYPROPERTIES('r1',$,$,$,(#10),#21);
#30=IFCMATERIAL('Concrete',$,$);
#31=IFCRELASSOCIATESMATERIAL('m1',$,$,$,(#10),#30);
#40=IFCMATERIALLIST((#41));
#41=IFCMATERIALLIST((#40));
#42=IFCRELASSOCIATESMATERIAL('m2',$,$,$,(#10),#40);
ENDSEC;
END-ISO-10303-21;
"""
        r = documents.read("mm.ifc", base64.b64encode(ifc.encode()).decode(), "d")
        self.assertEqual(len(r["proposals"]), 1)
        self.assertAlmostEqual(r["proposals"][0].value, 12.5)          # 1.25e10 mm3 = 12.5 m3

    # --- xlsx zip bomb (11)
    def test_xlsx_expansion_limit(self):
        import io as _io
        import zipfile
        buf = _io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("xl/workbook.xml", "<x/>")
            z.writestr("xl/worksheets/sheet1.xml", b"\0" * 60_000_000)
        from wlcstudio.importers import tabular
        with self.assertRaises(tabular.ImportError_):
            tabular.read_xlsx(buf.getvalue(), "d")

    # --- saving (1, 26), unit-only change
    def test_unit_only_change_is_refused_and_assumption_can_be_saved(self):
        pid = self.app.projects.create("u", "RC")
        self.app.handle("PUT", "/api/projects/%d/fields/m_rebar" % pid, {"value": 12000, "unit": "kg", "state": "confirmed"})
        with self.assertRaises(ApiError):
            self.app.handle("PUT", "/api/projects/%d/fields/m_rebar" % pid, {"value": 12000, "unit": "t", "state": "confirmed"})
        _, v = self.app.handle("PUT", "/api/projects/%d/fields/m_rebar" % pid, {"value": 12, "unit": "t", "state": "assumption"})
        self.assertEqual((v["value"], v["unit"], v["state"]), (12.0, "t", "assumption"))
        _, v = self.app.handle("PUT", "/api/projects/%d/fields/m_rebar" % pid, {"value": None, "state": "not_obtained"})
        self.assertEqual(v["state"], "not_obtained")

    # --- documents validated before storing (6, 12)
    def test_document_bad_row_does_not_half_import(self):
        pid = self.app.projects.create("d", "RC")
        csv = "名称,数量,単位\nコンクリート,200000000,m3\n鉄筋,5,t\n".encode()
        body = {"name": "q.csv", "data_b64": base64.b64encode(csv).decode()}
        _, out = self.app.handle("POST", "/api/projects/%d/documents" % pid, body)
        self.assertEqual(out["n_proposals"], 1)                         # the out-of-range row is reported, not stored
        self.assertTrue(any("範囲" in w for w in out["warnings"]))

    # --- delete removes the engine copy (7)
    def test_delete_removes_engine_rows(self):
        pid = self.app.projects.create("del", "RC")
        for fid, v in minimal().items():
            self.app.projects.put(pid, v)
        self.app.handle("POST", "/api/projects/%d/calculate" % pid, {"period": 60})
        lca = self.app.projects.get(pid)["lca_project_id"]
        self.assertIsNotNone(lca)
        _, out = self.app.handle("DELETE", "/api/projects/%d" % pid, None)
        self.assertGreater(out["engine"]["engine_rows"], 0)
        n = self.E.store.db.execute("SELECT COUNT(*) FROM input_versions WHERE project_id=?", (lca,)).fetchone()[0]
        self.assertEqual(n, 0)

    # --- stale result (23)
    def test_stale_result_is_flagged(self):
        pid = self.app.projects.create("st", "RC")
        for fid, v in minimal().items():
            self.app.projects.put(pid, v)
        self.app.handle("POST", "/api/projects/%d/calculate" % pid, {"period": 60})
        _, r = self.app.handle("GET", "/api/projects/%d/result" % pid, None)
        self.assertFalse(r["stale"])
        self.app.projects.put(pid, V("b_gfa", 1200.0))
        _, r = self.app.handle("GET", "/api/projects/%d/result" % pid, None)
        self.assertTrue(r["stale"])

    # --- estimator values need an uncertainty and a version (5)
    def test_automated_assumption_needs_uncertainty(self):
        with self.assertRaises(ProvenanceError):
            Value("b_gfa", "assumption", 1000.0, "m2", method="plateau_roof_x_storeys", source_id="plateau", factor_version="x").check()
        props, _ = research.plateau_proposals({"plateau_building_id": "b", "storeys_above": 3, "roof_edge_area_m2": 100.0,
                                               "floor_area_factor": 1.0, "estimated_gross_floor_area_m2": 300.0, "dataset": "13101_bldg_lod1"}, "RC")
        g = [p for p in props if p.field_id == "b_gfa"][0]
        self.assertEqual(g.uncertainty.kind, "unknown")
        g.check()

    # --- personal queries are not cached (8)
    def test_address_queries_are_not_cached(self):
        from wlcstudio.sources import gsi
        seen = {}

        def fake(url, **kw):
            seen.update(kw)
            return [], {"fetched_at": "x", "from_cache": False}
        orig = gsi.get_json
        gsi.get_json = fake
        try:
            gsi.geocode("東京都千代田区")
        finally:
            gsi.get_json = orig
        self.assertIs(seen.get("use_cache"), False)

    # --- secure delete (9), timeout (13)
    def test_secure_delete_and_timeout(self):
        self.assertEqual(self.app.projects.db.execute("PRAGMA secure_delete").fetchone()[0], 1)
        self.assertEqual(self.E.store.db.execute("PRAGMA secure_delete").fetchone()[0], 1)
        self.assertEqual(make_handler(self.app, 1).timeout, 10)

    # --- reproducible demo (21)
    def test_demo_does_not_depend_on_hash_seed(self):
        code = ("import sys; sys.dont_write_bytecode=True; sys.path.insert(0, %r); from wlcstudio import demo; "
                "print(sorted((k, v.value, v.unit) for k, v in demo.demo_values().items() if k.startswith('m_')))" % str(HERE))
        outs = {subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True,
                               env=dict(os.environ, PYTHONHASHSEED=str(seed))).stdout for seed in (1, 2, 3)}
        self.assertEqual(len(outs), 1)


class SecondRoundTests(unittest.TestCase):
    """Regression tests for the re-verification of the fixes (docs/review_fixes.md, second round)."""
    setUpClass = ReviewFixTests.__dict__["setUpClass"]
    tearDownClass = ReviewFixTests.__dict__["tearDownClass"]
    run_vals = ReviewFixTests.run_vals
    full = ReviewFixTests.full

    def test_unchanged_save_keeps_estimate_and_guard(self):
        pid = self.app.projects.create("s2", "RC")
        unc = Uncertainty("interval", 100, 900, 0.9)
        est = V("m_concrete", 500.0, "statistical", "t", method="rasmi_mi_x_gfa", source_id="rasmi", factor_version="v",
                uncertainty=unc, scope="whole_building")
        self.app.projects.put(pid, est)
        with self.assertRaises(ApiError):          # same number, now as 仮定: refused (source, range, scope would be lost)
            self.app.handle("PUT", "/api/projects/%d/fields/m_concrete" % pid, {"value": 500, "unit": "t", "state": "assumption"})
        self.assertEqual(self.app.projects.current(pid, "m_concrete").scope, "whole_building")
        # the scope (not only the method) keeps the double-counting guard
        v2 = Value.from_json(est.to_json())
        v2.method = "something_else"
        doc, rep = bridge.build(self.full(m_concrete=v2, m_concrete_fdn=V("m_concrete_fdn", 30.0, unit="m3")), REFSET)
        self.assertEqual(len([r for r in tables(doc)["materials"] if r["material_class"] == "CONCRETE"]), 1)

    def test_explicit_unit_relabel(self):
        pid = self.app.projects.create("rl", "RC")
        self.app.handle("PUT", "/api/projects/%d/fields/m_rebar" % pid, {"value": 12000, "unit": "t", "state": "confirmed"})
        with self.assertRaises(ApiError):
            self.app.handle("PUT", "/api/projects/%d/fields/m_rebar" % pid, {"value": 12000, "unit": "kg", "state": "confirmed"})
        _, v = self.app.handle("PUT", "/api/projects/%d/fields/m_rebar" % pid, {"value": 12000, "unit": "kg", "state": "confirmed", "relabel": True})
        self.assertEqual(v["unit"], "kg")

    def test_stage_propagation_and_basis(self):
        _, rep = bridge.build(self.full(o_elec_kwh=None), REFSET)      # the purchase is the gap (round 6: not PV)
        st = {s_ for m in rep["missing_inputs"] for s_ in m["stages"]}
        self.assertTrue({"B6", "B2"} <= st)
        _, rep = bridge.build(self.full(m_quantity_basis=None, m_waste_rate=V("m_waste_rate", 0.05)), REFSET)
        self.assertTrue(any(m["field"] == "m_quantity_basis" for m in rep["missing_inputs"]))
        _, rep = bridge.build(self.full(m_rebar=None), REFSET)               # no rebuild assumed: B5 is a real 0
        self.assertNotIn("B5", {s_ for m in rep["missing_inputs"] for s_ in m["stages"]})
        self.assertIn("B3", {s_ for m in rep["missing_inputs"] for s_ in m["stages"]})
        _, rep = bridge.build(self.full(a_reconstruction=V("a_reconstruction", "MAJOR_REFURBISHMENT"),
                                        a_replacement_cycle=V("a_replacement_cycle", 40.0), a_recon_fraction=V("a_recon_fraction", 0.5),
                                        c_diesel=None), REFSET)
        self.assertIn("B5", [s_ for m in rep["missing_inputs"] if m["field"] == "c_diesel" for s_ in m["stages"]])

    def test_whole_figure_covers_the_other_field(self):
        unc = Uncertainty("interval", 1, 9000, 0.9)
        whole = V("m_concrete", 900.0, "statistical", "t", method="mlit_area_unit_x_gfa", source_id="m", factor_version="v",
                  uncertainty=unc, scope="whole_building")
        vals = self.full(m_concrete=whole)
        vals.pop("m_concrete_fdn")
        _, rep = bridge.build(vals, REFSET)
        self.assertNotIn("m_concrete_fdn", [m["field"] for m in rep["missing_inputs"]])
        self.assertNotIn("コンクリート（基礎・杭）", rep["missing_materials"])

    def test_confirmed_zero_count_and_charge(self):
        vals = self.full(e_hvac_count=V("e_hvac_count", 0.0), r_charge_kg=V("r_charge_kg", 0.0), r_top_up=None)
        vals.pop("e_hvac_life")
        vals.pop("e_hvac_mass")
        doc, rep = bridge.build(vals, REFSET)
        fields = [m["field"] for m in rep["missing_inputs"]]
        self.assertNotIn("e_hvac_life", fields)
        self.assertNotIn("r_top_up", fields)
        self.assertEqual(tables(doc)["refrigerants"], [])           # a confirmed zero makes no row (round 5)
        self.assertNotIn("HVAC", [r["trade"] for r in tables(doc)["equipment"]])

    def test_equipment_without_factor_is_flagged_either_way(self):
        ref = json.loads(json.dumps(REFSET))
        del ref["data"]["factors"]["F-EQ-CONVEYANCE-01"]
        for cnt in (V("e_conveyance_count", 3.0), None):
            _, rep = bridge.build(self.full(e_conveyance_count=cnt), ref)
            self.assertIn("e_conveyance_count", [m["field"] for m in rep["missing_inputs"]])

    def test_refrigerant_parts_not_reflected_without_b1_and_top_up_na(self):
        _, rep = bridge.build(self.full(r_top_up=None), REFSET)
        rows = {r["field"]: r for r in bridge.reflection_table(rep)}
        self.assertFalse(rows["r_gwp"]["reflected"])
        doc, _ = bridge.build(self.full(r_top_up=V("r_top_up", None, "not_applicable")), REFSET)
        self.assertIs(tables(doc)["refrigerants"][0]["top_up"], False)

    def test_install_unit_not_flagged_without_renewal(self):
        _, rep = bridge.build(self.full(m_concrete=V("m_concrete", 100.0, unit="t"),
                                        m_refresh_cycle=V("m_refresh_cycle", None, "not_applicable")), REFSET, period=60)
        self.assertNotIn("m_concrete", [m["field"] for m in rep["missing_inputs"]])

    def test_hash_does_not_change_with_the_date(self):
        _, a = bridge.build(minimal(), REFSET, today="2026-11-15")
        _, b = bridge.build(minimal(), REFSET, today="2026-11-16")
        self.assertEqual(a["input_hash"], b["input_hash"])

    def test_ifc_foot_and_shared_material_list(self):
        foot = """ISO-10303-21;
HEADER;FILE_SCHEMA(('IFC4'));ENDSEC;
DATA;
#1=IFCDIMENSIONALEXPONENTS(1,0,0,0,0,0,0);
#2=IFCMEASUREWITHUNIT(IFCLENGTHMEASURE(0.3048),#3);
#3=IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);
#4=IFCCONVERSIONBASEDUNIT(#1,.LENGTHUNIT.,'FOOT',#2);
#5=IFCUNITASSIGNMENT((#4));
#10=IFCSLAB('2abc',$,'Slab',$,$,$,$,$,$);
#20=IFCQUANTITYVOLUME('NetVolume',$,$,3531.47,$);
#21=IFCELEMENTQUANTITY('q1',$,'Qto',$,$,(#20));
#22=IFCRELDEFINESBYPROPERTIES('r1',$,$,$,(#10),#21);
#30=IFCMATERIAL('Concrete',$,$);
#31=IFCRELASSOCIATESMATERIAL('m1',$,$,$,(#10),#30);
ENDSEC;
END-ISO-10303-21;
"""
        r = documents.read("ft.ifc", base64.b64encode(foot.encode()).decode(), "d")
        self.assertEqual(r["proposals"], [])                          # ft3 is never read as m3
        lines = ["ISO-10303-21;", "HEADER;FILE_SCHEMA(('IFC4'));ENDSEC;", "DATA;", "#1=IFCMATERIAL('Concrete',$,$);"]
        chain = list(range(2, 3000))
        for i in chain:
            lines.append("#%d=IFCMATERIALLIST((#%d));" % (i, i - 1))
        for k in range(3000):
            e = 10000 + 2 * k
            lines.append("#%d=IFCWALL('g%d',$,'W',$,$,$,$,$);" % (e, k))
            lines.append("#%d=IFCRELASSOCIATESMATERIAL('m%d',$,$,$,(#%d),#%d);" % (e + 1, k, e, chain[-1]))
        lines += ["ENDSEC;", "END-ISO-10303-21;"]
        import time as _t
        t0 = _t.time()
        documents.read("big.ifc", base64.b64encode("\n".join(lines).encode()).decode(), "d")
        self.assertLess(_t.time() - t0, 10)                            # memoised: one walk, not 3000

    def test_xlsx_far_column_and_negative_rows(self):
        import io as _io
        import zipfile
        buf = _io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                       'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                       '<sheet name="s" sheetId="1" r:id="rId1"/></sheets></workbook>')
            z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                       '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
            z.writestr("xl/worksheets/sheet1.xml", '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                       '<sheetData><row r="1"><c r="ZZZZZZ1"><v>1</v></c></row></sheetData></worksheet>')
        from wlcstudio.importers import tabular
        with self.assertRaises(tabular.ImportError_):
            tabular.read_xlsx(buf.getvalue(), "d")
        csv = "名称,数量,単位\n鉄筋,5,t\n鉄筋,-2,t\n".encode()
        r = documents.read("n.csv", base64.b64encode(csv).decode(), "d")
        self.assertEqual([p.value for p in r["proposals"]], [5.0])

    def test_legacy_plateau_candidate_can_be_accepted(self):
        pid = self.app.projects.create("lg", "RC")
        legacy = Value("b_gfa", "assumption", 4000.0, "m2", method="plateau_roof_x_storeys", source_id="plateau").to_json()
        self.app.projects.db.execute("INSERT INTO candidates (project_id, field_id, payload, origin, created_at) VALUES (?,?,?,?,0)",
                                     (pid, "b_gfa", json.dumps(legacy), "plateau"))
        self.app.projects.db.commit()
        v = self.app.projects.accept(pid, "b_gfa", 0)
        self.assertEqual(v.uncertainty.kind, "unknown")

    def test_sweep_removes_legacy_personal_cache(self):
        from wlcstudio.sources import net
        root = Path(self.td.name) / "c"
        orig = net.CACHE
        net.CACHE = root
        try:
            h = "a" * 64
            (root / "aa").mkdir(parents=True)
            (root / "aa" / h).write_bytes(b"x")
            (root / "aa" / (h + ".json")).write_text(json.dumps({"url": "https://msearch.gsi.go.jp/address-search/AddressSearch?q=X"}))
            (root / "notes.txt").write_text("keep")
            net.sweep()
            self.assertFalse((root / "aa" / h).exists())
            self.assertTrue((root / "notes.txt").exists())
        finally:
            net.CACHE = orig

    def test_slow_client_does_not_block_the_server(self):
        import http.client
        import socket
        import threading
        from http.server import ThreadingHTTPServer
        from wlcstudio.server import AppWorker
        w = AppWorker(Path(self.td.name) / "w")
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(w, 0))
        port = httpd.server_address[1]
        httpd.RequestHandlerClass = make_handler(w, port)
        th = threading.Thread(target=httpd.serve_forever, daemon=True)
        th.start()
        idle = socket.create_connection(("127.0.0.1", port))
        idle.send(b"GET /api/me")                                        # an unfinished request, then silence
        try:
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            c.request("GET", "/api/meta", headers={"Host": "127.0.0.1:%d" % port})
            self.assertEqual(c.getresponse().status, 200)
        finally:
            idle.close()
            httpd.shutdown()
            httpd.server_close()
            w.stop()


class ThirdRoundTests(unittest.TestCase):
    """Regression tests for the third verification round (systematic field sweep, UI flows, attacks)."""
    setUpClass = ReviewFixTests.__dict__["setUpClass"]
    tearDownClass = ReviewFixTests.__dict__["tearDownClass"]
    run_vals = ReviewFixTests.run_vals
    full = ReviewFixTests.full

    def screen_missing(self, rep):
        return [m["field"] for m in rep["missing_inputs"] if m["field"] in FL.FIELDS]

    def test_reconstruction_unknown_or_na_adds_no_rebuild(self):
        base = dict(a_replacement_cycle=V("a_replacement_cycle", 40.0), a_recon_fraction=V("a_recon_fraction", 0.5))
        doc, rep = bridge.build(self.full(a_reconstruction=None, **base), REFSET)
        self.assertNotIn("boundary.replacement_cycle", items(doc))      # an unknown scenario must not trigger B5
        r, _, _ = self.run_vals(self.full(a_reconstruction=V("a_reconstruction", None, "not_applicable"), **base))
        self.assertEqual(r["results"]["X-02"]["by_stage"]["B5"], 0.0)
        doc, _ = bridge.build(self.full(a_reconstruction=V("a_reconstruction", None, "not_applicable"), **base), REFSET)
        self.assertEqual(items(doc)["boundary.reconstruction_scenario"], "NONE")

    def test_na_never_fields(self):
        pid = self.app.projects.create("nv", "RC")
        with self.assertRaises(ApiError):
            self.app.handle("PUT", "/api/projects/%d/fields/m_quantity_basis" % pid, {"value": None, "state": "not_applicable"})
        _, rep = bridge.build(self.full(m_quantity_basis=V("m_quantity_basis", None, "not_applicable"),
                                        m_waste_rate=V("m_waste_rate", 0.05)), REFSET)
        self.assertIn("m_quantity_basis", self.screen_missing(rep))      # a stored 適用外 counts as missing

    def test_refresh_na_means_no_renewal(self):
        _, rep = bridge.build(self.full(m_refresh_cycle=V("m_refresh_cycle", None, "not_applicable")), REFSET, period=60)
        self.assertNotIn("m_refresh_cycle", self.screen_missing(rep))
        rows = {r["field"]: r for r in bridge.reflection_table(rep)}
        self.assertIn("更新しない", rows["m_refresh_cycle"]["detail"])

    def test_transport_fallback_is_reported(self):
        vals = self.full(m_rebar=V("m_rebar", 10.0, unit="t"), m_transport_km=None)
        _, rep = bridge.build(vals, REFSET)
        self.assertTrue(any("配送原単位" in n for n in rep["notes"]))

    def test_engine_flags_spread_to_dependent_stages(self):
        pid = self.app.projects.create("sp", "RC")
        vals = self.full(a_reconstruction=V("a_reconstruction", "MAJOR_REFURBISHMENT"), a_replacement_cycle=V("a_replacement_cycle", 40.0),
                         a_recon_fraction=V("a_recon_fraction", 0.5))
        vals.pop("a_eol_haul_km")
        for fid, v in vals.items():
            self.app.projects.put(pid, v)
        _, out = self.app.handle("POST", "/api/projects/%d/calculate" % pid, {"period": 60})
        st = {x["stage"]: x["complete"] for x in out["summary"]["stages"]}
        self.assertFalse(st["C2"])
        self.assertFalse(st["B5"])

    def test_b4_and_route_specific_c_stage(self):
        vals = self.full(m_refresh_cycle=V("m_refresh_cycle", 100.0), m_steel=None)
        _, rep = bridge.build(vals, REFSET, period=60)
        stages = [x for m in rep["missing_inputs"] if m["field"] == "m_steel" for x in m["stages"]]
        self.assertNotIn("B4", stages)                                    # no renewal inside 60 years
        self.assertIn("C4", stages)                                       # route LANDFILL -> C4
        self.assertNotIn("C3", stages)

    def test_grid_na_outside_boundary_does_not_block(self):
        vals = self.full(a_stages=V("a_stages", "EMBODIED"), o_grid_value=V("o_grid_value", None, "not_applicable"))
        _, rep = bridge.build(vals, REFSET)
        self.assertEqual(rep["missing_required"], [])
        rows = {r["field"]: r for r in bridge.reflection_table(rep)}
        self.assertFalse(rows["o_grid_value"]["reflected"])               # the zero fill is not "in the calculation"

    def test_fm_ratio_irrelevant_without_electricity(self):
        _, rep = bridge.build(self.full(o_elec_kwh=V("o_elec_kwh", None, "not_applicable"), o_fm_ratio=None), REFSET)
        self.assertNotIn("o_fm_ratio", self.screen_missing(rep))

    def test_stale_estimate_and_structure_edit(self):
        pid = self.app.projects.create("se", "RC")
        unc = Uncertainty("interval", 1, 9000, 0.9)
        est = V("m_concrete", 900.0, "statistical", "t", method="rasmi_mi_x_gfa", source_id="r", factor_version="v",
                uncertainty=unc, scope="whole_building", depends={"b_gfa": 5000.0, "b_use": "office", "b_structure": "RC"})
        vals = self.full(m_concrete=est, b_gfa=V("b_gfa", 2000.0), b_structure=V("b_structure", "RC"))
        _, rep = bridge.build(vals, REFSET)
        self.assertEqual(rep["stale_estimates"][0]["field"], "m_concrete")
        self.app.handle("PUT", "/api/projects/%d/fields/b_structure" % pid, {"value": "S", "state": "confirmed"})
        self.assertEqual(self.app.projects.get(pid)["structure"], "S")

    def test_plateau_select_validates_each_attribute(self):
        pid = self.app.projects.create("pl", "RC")
        c = {"plateau_building_id": "x", "storeys_above": 3, "storeys_below": 0, "measured_height_m": 5000.0,
             "address": "東京都", "usage": "業務施設", "dataset": "d"}
        _, out = self.app.handle("POST", "/api/projects/%d/research/plateau/select" % pid, {"candidate": c, "lat": 35.7, "lon": 139.7})
        self.assertGreater(out["n_proposals"], 0)
        self.assertTrue(any("高さ" in n for n in out["notes"]))

    def test_ifc_invalid_quantities_cannot_loop(self):
        K = 2500
        objs = ",".join(["#10"] * K)
        qids = ",".join(["#20"] * K)
        ifc = ("ISO-10303-21;\nHEADER;FILE_SCHEMA(('IFC4'));ENDSEC;\nDATA;\n#10=IFCSLAB('a',$,'S',$,$,$,$,$,$);\n"
               "#20=IFCQUANTITYVOLUME('V',$,$,$,$);\n#21=IFCELEMENTQUANTITY('q',$,'Q',$,$,(%s));\n"
               "#22=IFCRELDEFINESBYPROPERTIES('r',$,$,$,(%s),#21);\nENDSEC;\nEND-ISO-10303-21;\n" % (qids, objs))
        import time as _t
        t0 = _t.time()
        documents.read("k.ifc", base64.b64encode(ifc.encode()).decode(), "d")   # de-duplicated: one pair
        self.assertLess(_t.time() - t0, 3)

    def test_xlsx_shared_string_index_and_keywords(self):
        import io as _io
        import zipfile
        buf = _io.BytesIO()
        ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("xl/workbook.xml", '<workbook %s xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                       '<sheets><sheet name="s" sheetId="1" r:id="rId1"/></sheets></workbook>' % ns)
            z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                       '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
            z.writestr("xl/sharedStrings.xml", '<sst %s><si><t>a</t></si></sst>' % ns)
            z.writestr("xl/worksheets/sheet1.xml", '<worksheet %s><sheetData><row r="1"><c r="A1" t="s"><v>999</v></c></row>'
                       '</sheetData></worksheet>' % ns)
        from wlcstudio.importers import tabular
        with self.assertRaises(tabular.ImportError_):
            tabular.read_xlsx(buf.getvalue(), "d")
        csv = "名称,数量,単位\n鉄筋コンクリート（躯体）,850,m3\n鉄筋 D13,40,t\n鉄筋 D10,8000,kg\nGypsum board,30,m2\n設計数量 仕上,10,m2\n".encode()
        r = documents.read("k.csv", base64.b64encode(csv).decode(), "d")
        got = {(p.field_id, p.unit): p.value for p in r["proposals"]}
        self.assertEqual(got[("m_concrete", "m3")], 850.0)
        self.assertEqual(got[("m_rebar", "t")], 48.0)                   # 40 t + 8000 kg in one candidate
        self.assertIn(("m_board", "m2"), got)                           # 'Gypsum' is not a total row
        self.assertIn(("m_finish", "m2"), got)                          # '設計…' is not a total row

    def test_service_worker_is_network_first(self):
        sw = (HERE / "web" / "sw.js").read_text(encoding="utf-8")
        self.assertIn("skipWaiting", sw)
        self.assertIn("fetch(e.request).then", sw)

    def test_ipv6_loopback_server_class(self):
        import socket
        from http.server import ThreadingHTTPServer

        class S6(ThreadingHTTPServer):
            address_family = socket.AF_INET6
        try:
            srv = S6(("::1", 0), make_handler(self.app, 0))
        except OSError:
            self.skipTest("IPv6 loopback is not available here")
        srv.server_close()


class FourthRoundTests(unittest.TestCase):
    """Regression tests for the fourth verification round."""
    setUpClass = ReviewFixTests.__dict__["setUpClass"]
    tearDownClass = ReviewFixTests.__dict__["tearDownClass"]
    run_vals = ReviewFixTests.run_vals
    full = ReviewFixTests.full

    def summary(self, vals, T=60):
        pid = self.app.projects.create("r4", "RC")
        for fid, v in vals.items():
            self.app.projects.put(pid, v)
        _, out = self.app.handle("POST", "/api/projects/%d/calculate" % pid, {"period": T})
        return out, {x["stage"]: x["complete"] for x in out["summary"]["stages"]}

    def test_engine_unit_spread_by_kind(self):
        vals = self.full(m_refresh_cycle=V("m_refresh_cycle", 100.0))
        vals.pop("a_eol_haul_km")
        out, st = self.summary(vals)
        self.assertFalse(st["C2"])
        self.assertTrue(st["B4"])                                       # no material renewal inside 60 years

    def test_delivery_fallback_marks_a4(self):
        _, rep = bridge.build(self.full(m_transport_km=None), REFSET)
        self.assertIn("a4_delivery_fallback", [m["field"] for m in rep["missing_inputs"]])

    def test_b5_only_when_rebuild_inside_t(self):
        vals = self.full(a_reconstruction=V("a_reconstruction", "MAJOR_REFURBISHMENT"), a_replacement_cycle=V("a_replacement_cycle", 70.0),
                         a_recon_fraction=V("a_recon_fraction", 0.5), m_steel=None)
        _, rep = bridge.build(vals, REFSET, period=60)
        self.assertNotIn("B5", rep["incomplete_stages"])

    def test_waste_rate_gap_not_blamed_on_transport(self):
        vals = self.full(m_concrete=V("m_concrete", 100.0, unit="t"), m_waste_rate=None, m_quantity_basis=V("m_quantity_basis", "DESIGN"))
        _, rep = bridge.build(vals, REFSET)
        self.assertNotIn("m_transport_mode", [m["field"] for m in rep["missing_inputs"]])
        self.assertIn("m_waste_rate", [m["field"] for m in rep["missing_inputs"]])

    def test_loss_rate_irrelevant_without_replacement(self):
        out, st = self.summary(self.full(r_life=V("r_life", 70.0), r_loss_rate=None))
        self.assertNotIn("r_loss_rate", [m["field"] for m in out["missing_inputs"]])
        self.assertTrue(st["B1"])

    def test_route_aware_c_stages_from_engine_units(self):
        out, st = self.summary(self.full(m_concrete=V("m_concrete", 800.0, unit="m3")))
        self.assertFalse(st["C4"])                                     # LANDFILL: the row's treatment goes to C4
        self.assertTrue(st["C3"])

    def test_scope_kept_on_state_change_and_from_estimate(self):
        pid = self.app.projects.create("sc", "RC")
        self.app.handle("PUT", "/api/projects/%d/fields/m_concrete" % pid, {"value": 5400, "unit": "t", "state": "assumption", "scope": "whole_building"})
        _, v = self.app.handle("PUT", "/api/projects/%d/fields/m_concrete" % pid, {"value": 5400, "unit": "t", "state": "confirmed"})
        self.assertEqual(v["scope"], "whole_building")
        est = V("m_concrete", 900.0, "statistical", "t", method="rasmi_mi_x_gfa", source_id="r", factor_version="v",
                uncertainty=Uncertainty("interval", 1, 9000, 0.9), scope="whole_building", depends={"b_gfa": 5000.0})
        self.app.projects.put(pid, est)
        _, v = self.app.handle("PUT", "/api/projects/%d/fields/m_concrete" % pid, {"value": 950, "unit": "t", "state": "assumption", "from_estimate": True})
        self.assertEqual((v["scope"], v["depends"], v["uncertainty"]["kind"]), ("whole_building", {"b_gfa": 5000.0}, "unknown"))

    def test_fingerprint_follows_state_changes(self):
        _, a = bridge.build(self.full(m_glass=V("m_glass", None, "not_applicable")), REFSET)
        _, b = bridge.build(self.full(m_glass=None), REFSET)
        self.assertNotEqual(a["input_hash"], b["input_hash"])

    def test_csv_limits_and_parse_errors(self):
        from wlcstudio.importers import tabular
        with self.assertRaises(tabular.ImportError_):
            tabular.read_csv(b'name,quantity,unit\n"' + b"A" * 200000 + b'",5,t\n', "d")
        big = ("名称,数量,単位\n" + "鉄筋,1,t\n" * 120000).encode()
        with self.assertRaises(tabular.ImportError_):
            tabular.read_csv(big, "d")

    def test_totals_and_rebar_products(self):
        csv = "品目,数量,単位\n鉄筋 D13,5,t\n鉄筋 D16,7,t\n鉄筋計,12,t\nコンクリート Fc24,100,m3\nコンクリート 計,100,m3\n鉄筋コンクリート用棒鋼 SD345,3,t\n".encode()
        r = documents.read("t.csv", base64.b64encode(csv).decode(), "d")
        got = {(p.field_id, p.unit): p.value for p in r["proposals"]}
        self.assertEqual(got[("m_rebar", "t")], 15.0)                  # 5 + 7 + 3; the 鉄筋計 subtotal is not added
        self.assertEqual(got[("m_concrete", "m3")], 100.0)

    def test_new_premises_make_a_new_candidate_and_structure_needed(self):
        pid = self.app.projects.create("dp", "RC")
        unc = Uncertainty("interval", 1, 9, 0.9)
        a = V("m_rebar", 5.0, "statistical", "t", method="mlit_area_unit_x_gfa", source_id="m", factor_version="v", uncertainty=unc,
              depends={"b_gfa": 100.0, "b_structure": "RC"})
        b = Value.from_json(a.to_json())
        b.depends = {"b_gfa": 200.0, "b_structure": "RC"}
        i1 = self.app.projects.propose(pid, a, "x")
        i2 = self.app.projects.propose(pid, b, "x")
        self.assertNotEqual(i1, i2)
        self.app.projects.put(pid, V("b_structure", None, "not_obtained"))
        with self.assertRaises(ApiError):
            self.app.handle("POST", "/api/projects/%d/estimate" % pid, {"screen": "material"})


class FifthRoundTests(unittest.TestCase):
    """Regression tests for the fifth verification round (docs/review_fixes.md, round 5)."""
    setUpClass = ReviewFixTests.__dict__["setUpClass"]
    tearDownClass = ReviewFixTests.__dict__["tearDownClass"]
    run_vals = ReviewFixTests.run_vals
    full = ReviewFixTests.full
    summary = FourthRoundTests.summary

    # --- operation: purchased electricity, self-consumed PV, export
    def test_self_consumed_pv_is_not_subtracted_twice(self):
        vals = self.full(o_pv_kwh=V("o_pv_kwh", 30000.0), o_export_kwh=V("o_export_kwh", 10000.0))
        r, doc, rep = self.run_vals(vals)
        self.assertEqual(items(doc)["operation.electricity.base"], 120000.0)      # purchase 100000 + self-use 20000
        self.assertAlmostEqual(r["results"]["B6-04"]["by_year"][1], 100000.0)     # the engine nets back to the bills
        self.assertEqual(items(doc)["operation.states"]["electricity"], "DERIVED")
        row = {x["field"]: x for x in bridge.reflection_table(rep)}["o_elec_kwh"]
        self.assertIn("自家消費", row["detail"])

    def test_export_above_generation_is_reported_not_blocking(self):
        # round 6: with the purchase known, generation and export cannot act; the contradiction is reported
        vals = self.full(o_pv_kwh=V("o_pv_kwh", 1000.0), o_export_kwh=V("o_export_kwh", 5000.0))
        doc, rep = bridge.build(vals, REFSET)
        self.assertEqual(rep["missing_required"], [])
        self.assertTrue(any("より多い" in m for m in rep["inconsistent_inputs"]))
        self.assertEqual(items(doc)["operation.electricity.base"], 100000.0)
        self.assertEqual(items(doc)["operation.onsite_export.base"], 0.0)

    def test_no_purchase_makes_b2_and_grid_moot(self):
        vals = self.full(o_elec_kwh=V("o_elec_kwh", 0.0))
        vals.pop("o_fm_ratio")
        vals.pop("o_grid_value")
        doc, rep = bridge.build(vals, REFSET)
        self.assertEqual(rep["missing_required"], [])                           # the grid table is filled with 0
        self.assertNotIn("o_fm_ratio", [m["field"] for m in rep["missing_inputs"]])
        self.assertTrue(rep["expand"]["b2_moot"])
        out, st = self.summary(vals)
        self.assertEqual(out["status"], "ok")
        self.assertTrue(st["B2"])
        self.assertNotIn("B2-01", out["summary"]["incomplete_units"])

    def test_site_electricity_zero_fills_construction_grid(self):
        vals = self.full(c_site_electricity=V("c_site_electricity", None, "not_applicable"))
        vals.pop("o_grid_construction")
        doc, rep = bridge.build(vals, REFSET)
        self.assertNotIn(FL.FIELDS["o_grid_construction"]["label"], rep["missing_required"])
        self.assertEqual(items(doc)["operation.grid.construction_value"], 0.0)

    # --- confirmed zeros and B5
    def test_zero_count_makes_no_equipment_row(self):
        doc, rep = bridge.build(self.full(e_conveyance_count=V("e_conveyance_count", 0.0)), REFSET)
        self.assertNotIn("CONVEYANCE", [r["trade"] for r in tables(doc)["equipment"]])
        self.assertNotIn("e_conveyance_mass", [m["field"] for m in rep["missing_inputs"]])

    def test_b5_moot_with_zero_share(self):
        vals = self.full(a_reconstruction=V("a_reconstruction", "MAJOR_REFURBISHMENT"),
                         a_recon_fraction=V("a_recon_fraction", None, "not_applicable"))
        _, rep = bridge.build(vals, REFSET, period=60)
        fields = [m["field"] for m in rep["missing_inputs"]]
        self.assertNotIn("a_replacement_cycle", fields)                         # the share is a known 0
        self.assertFalse(rep["expand"]["b5"])
        out, st = self.summary(vals)
        self.assertTrue(st["B5"])
        self.assertNotIn("B5-01", out["summary"]["incomplete_units"])

    # --- assumed vs omitted
    def test_delivery_fallback_is_assumed_not_omitted(self):
        vals = self.full(m_transport_km=None)
        _, rep = bridge.build(vals, REFSET)
        m = {x["field"]: x for x in rep["missing_inputs"]}["a4_delivery_fallback"]
        self.assertEqual(m["gap"], "assumed")
        self.assertNotIn("a4_delivery_fallback", [x["field"] for x in rep["omitted_inputs"]])
        self.assertNotIn("A4", rep["incomplete_stages"])
        self.assertIn("A4", rep["assumed_stages"])
        out, st = self.summary(vals)
        self.assertIn("a4_delivery_fallback", [x["field"] for x in out["assumed_inputs"]])
        self.assertNotIn("a4_delivery_fallback", [x["field"] for x in out["omitted_inputs"]])
        self.assertIn("A4", out["summary"]["assumed_stages"])
        self.assertTrue([x for x in out["summary"]["stages"] if x["stage"] == "A4"][0]["assumed"])

    def test_hints_name_the_pseudo_entries_and_only_bad_stages(self):
        out, st = self.summary(self.full())
        hints = {h["stage"]: h for h in out["summary"]["hints"]}
        self.assertIn("C1", hints)
        self.assertNotIn("未取得の入力", hints["C1"]["note"])                    # no screen field for demolition
        for h in out["summary"]["hints"]:
            self.assertTrue(h["stage"] == "—" or not st.get(h["stage"], False), h)

    # --- range note
    def test_range_note_counts_assumed_grid_factor(self):
        unc = Uncertainty("interval", 8.0, 12.0, 0.8)
        vals = self.full(m_rebar=V("m_rebar", 10.0, "statistical", "t", source_id="s", factor_version="v", uncertainty=unc),
                         o_grid_value=V("o_grid_value", 0.4, "assumption"))
        out, _ = self.summary(vals)
        self.assertIn("o_grid_value", out["range"]["unknown_fields"])
        self.assertIn(FL.FIELDS["o_grid_value"]["label"], out["range"]["note"])

    # --- put_field keeps what a value covers
    def scoped(self):
        pid = self.app.projects.create("r5", "RC")
        unc = Uncertainty("interval", 800.0, 1200.0, 0.8)
        est = V("m_concrete", 1000.0, "statistical", "t", method="mlit_area_unit_x_gfa", source_id="mlit", factor_version="v",
                uncertainty=unc, scope="whole_building", depends={"b_gfa": 1000.0, "b_structure": "RC"})
        self.app.projects.put(pid, est)
        url = "/api/projects/%d/fields/m_concrete" % pid
        self.app.handle("PUT", url, {"value": 950, "unit": "t", "state": "confirmed", "from_estimate": True})
        return pid, url

    def test_state_change_keeps_scope_premises_source_and_unknown_range(self):
        pid, url = self.scoped()
        self.app.handle("PUT", url, {"value": 950, "unit": "t", "state": "assumption"})
        v = self.app.projects.current(pid, "m_concrete")
        self.assertEqual((v.state, v.scope, v.uncertainty.kind, v.source_id), ("assumption", "whole_building", "unknown", "mlit"))
        self.assertEqual(v.depends, {"b_gfa": 1000.0, "b_structure": "RC"})

    def test_new_value_over_scoped_value_must_say_its_scope(self):
        pid, url = self.scoped()
        with self.assertRaises(ApiError):
            self.app.handle("PUT", url, {"value": 700, "unit": "t", "state": "confirmed"})
        self.app.handle("PUT", url, {"value": 700, "unit": "t", "state": "confirmed", "scope": "field_only"})
        self.assertEqual(self.app.projects.current(pid, "m_concrete").scope, "")

    def test_comma_only_as_thousands_separator(self):
        pid = self.app.projects.create("r5c", "RC")
        url = "/api/projects/%d/fields/b_gfa" % pid
        with self.assertRaises((ApiError, ProjectError)):
            self.app.handle("PUT", url, {"value": "1,5", "unit": "m2", "state": "confirmed"})
        self.app.handle("PUT", url, {"value": "12,500", "unit": "m2", "state": "confirmed"})
        self.assertEqual(self.app.projects.current(pid, "b_gfa").value, 12500.0)

    # --- estimates
    def test_operation_estimate_does_not_need_structure(self):
        pid = self.app.projects.create("r5e", "RC")
        self.app.projects.put(pid, V("b_structure", None, "not_obtained"))
        st, out = self.app.handle("POST", "/api/projects/%d/estimate" % pid, {"screen": "operation"})
        self.assertEqual(st, 200)
        with self.assertRaises(ApiError):
            self.app.handle("POST", "/api/projects/%d/estimate" % pid, {"screen": "material"})

    def test_new_premises_dismiss_old_estimates(self):
        pid = self.app.projects.create("r5d", "RC")
        unc = Uncertainty("interval", 1.0, 2.0, 0.8)
        for gfa, val in ((1000.0, 1.5), (2000.0, 3.0)):
            self.app.projects.propose(pid, V("m_concrete", val, "statistical", "t", method="mlit_area_unit_x_gfa", source_id="m",
                                             factor_version="v", uncertainty=Uncertainty("interval", val * .8, val * 1.2, 0.8),
                                             depends={"b_gfa": gfa, "b_structure": "RC"}), "estimate")
        cs = self.app.projects.candidates(pid, "m_concrete")
        self.assertEqual([c["value"] for c in cs], [3.0])
        self.app.projects.propose(pid, V("m_concrete", 9.0, "from_drawing", "t", method="table_sum", source_id="d"), "document")
        self.app.projects.propose(pid, V("m_concrete", 8.0, "from_drawing", "t", method="table_sum", source_id="d2"), "document")
        self.assertEqual([c["value"] for c in self.app.projects.candidates(pid, "m_concrete")][:2], [8.0, 9.0])   # newest first

    # --- documents
    def test_reinforced_concrete_names_and_subtotals(self):
        f = documents._field_for
        self.assertEqual(f("Concrete, Reinforced"), "m_concrete")
        self.assertEqual(f("Concrete, Reinforced, C30/37"), "m_concrete")
        self.assertEqual(f("Reinforcement for concrete"), "m_rebar")
        self.assertEqual(f("Board d10"), "m_board")
        self.assertEqual(f("ＲＥＢＡＲ　Ｄ１３"), "m_rebar")
        for n in ("鉄筋計（SD345）", "コンクリート計 (m3)", "躯体小計 鉄筋"):
            self.assertTrue(documents._is_total(n), n)
        for n in ("設計数量 仕上", "温度計", "鉄筋 D13"):
            self.assertFalse(documents._is_total(n), n)

    def xlsx(self, rows_xml, shared=("名称", "数量", "単位")):
        import io, zipfile
        ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("xl/workbook.xml", '<workbook %s xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                       '<sheets><sheet name="S" sheetId="1" r:id="rId1"/></sheets></workbook>' % ns)
            z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                       '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
            z.writestr("xl/sharedStrings.xml", '<sst %s>%s</sst>' % (ns, "".join("<si><t>%s</t></si>" % x for x in shared)))
            z.writestr("xl/worksheets/sheet1.xml", '<worksheet %s><sheetData>%s</sheetData></worksheet>' % (ns, rows_xml))
        return buf.getvalue()

    HEAD = '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c><c r="C1" t="s"><v>2</v></c></row>'

    def test_xlsx_long_strings_and_empty_rows_are_bounded(self):
        from wlcstudio.importers import tabular
        with self.assertRaises(tabular.ImportError_):
            tabular.read_xlsx(self.xlsx(self.HEAD, shared=("名称", "数量", "x" * 40000)), "d")
        old = tabular.MAX_ROWS
        tabular.MAX_ROWS = 50
        try:
            with self.assertRaises(tabular.ImportError_):
                tabular.read_xlsx(self.xlsx(self.HEAD + "<row/>" * 60), "d")
        finally:
            tabular.MAX_ROWS = old
        with self.assertRaises(tabular.ImportError_):                       # rows must go down the sheet
            tabular.read_xlsx(self.xlsx(self.HEAD + '<row r="1"><c r="A1"><v>1</v></c></row>'), "d")

    def test_xlsx_trace_uses_sheet_row_and_formula_totals_are_not_added(self):
        rows = (self.HEAD +
                '<row r="5"><c r="A5" t="inlineStr"><is><t>鉄筋 D13</t></is></c><c r="B5"><v>5</v></c><c r="C5" t="inlineStr"><is><t>t</t></is></c></row>'
                '<row r="6"><c r="A6" t="inlineStr"><is><t>鉄筋 D16</t></is></c><c r="B6"><f>D6*0.001</f><v>7</v></c><c r="C6" t="inlineStr"><is><t>t</t></is></c><c r="D6"><v>7000</v></c></row>'
                '<row r="7"><c r="A7" t="inlineStr"><is><t>鉄筋（全体）</t></is></c><c r="B7"><f>SUM(B5:B6)</f><v>12</v></c><c r="C7" t="inlineStr"><is><t>t</t></is></c></row>'
                '<row r="8"><c r="A8" t="inlineStr"><is><t>鉄筋（再掲）</t></is></c><c r="B8"><f>B5</f><v>5</v></c><c r="C8" t="inlineStr"><is><t>t</t></is></c></row>')
        r = documents.read("q.xlsx", base64.b64encode(self.xlsx(rows)).decode(), "d")
        got = {(p.field_id, p.unit): p for p in r["proposals"]}
        self.assertEqual(got[("m_rebar", "t")].value, 12.0)                  # 5 + 7, not the SUM row nor the repeat
        self.assertIn("R5C2", got[("m_rebar", "t")].source_detail)
        reasons = " ".join(u["reason"] for u in r["unused"])
        self.assertIn("SUM", reasons)
        self.assertIn("同じ列", reasons)

    # --- the screen
    def test_ui_has_the_round5_guards(self):
        js = (HERE / "web" / "app.js").read_text(encoding="utf-8")
        for needle in ("function parseNumber", "function clearedInput", "function openProject", "state.seq",
                       '"field_only"', "function dependsHtml", "T <= 130", "assumed_inputs"):
            self.assertIn(needle, js, needle)
        proc = subprocess.run(["node", "-e", """
            const src = require('fs').readFileSync(process.argv[1], 'utf8');
            const m = src.match(/function parseNumber[\\s\\S]*?\\n}\\n/);
            eval(m[0]);
            const out = ['12,500', '1,5', '1,234.5', '１２３', 'abc', '1e3'].map((x) => JSON.stringify(parseNumber(x)));
            console.log(out.join('|'));""", str(HERE / "web" / "app.js")], capture_output=True, text=True)
        if proc.returncode != 0 and "not found" in (proc.stderr or ""):
            self.skipTest("node is not installed")
        parts = proc.stdout.strip().split("|")
        self.assertEqual(json.loads(parts[0])["value"], 12500)
        self.assertTrue(json.loads(parts[1])["bad"])
        self.assertEqual(json.loads(parts[2])["value"], 1234.5)
        self.assertEqual(json.loads(parts[3])["value"], 123)
        self.assertTrue(json.loads(parts[4])["bad"])
        self.assertEqual(json.loads(parts[5])["value"], 1000)


class SixthRoundTests(unittest.TestCase):
    """Regression tests for the sixth verification round (docs/review_fixes.md, round 6)."""
    setUpClass = ReviewFixTests.__dict__["setUpClass"]
    tearDownClass = ReviewFixTests.__dict__["tearDownClass"]
    run_vals = ReviewFixTests.run_vals
    full = ReviewFixTests.full
    summary = FourthRoundTests.summary
    xlsx = FifthRoundTests.xlsx
    HEAD = FifthRoundTests.HEAD

    # --- electricity: the purchase decides B6/B2; generation/export never drop it
    def test_unknown_pv_does_not_drop_known_purchase(self):
        base, _, _ = self.run_vals(self.full())
        for over in ({"o_pv_kwh": None}, {"o_export_kwh": None}, {"o_pv_kwh": None, "o_export_kwh": None},
                     {"o_pv_kwh": V("o_pv_kwh", 30000.0), "o_export_kwh": None}):
            vals = self.full()
            for k, x in over.items():
                if x is None:
                    vals.pop(k)
                else:
                    vals[k] = x
            r, doc, rep = self.run_vals(vals)
            self.assertEqual(items(doc)["operation.electricity.base"], 100000.0, over)
            self.assertAlmostEqual(r["results"]["SUM-03"]["value"], base["results"]["SUM-03"]["value"], 3)
            self.assertNotIn("B6-01", r["results"]["X-02"]["incomplete_units"])
            self.assertFalse({"o_pv_kwh", "o_export_kwh"} & {m["field"] for m in rep["missing_inputs"]})
            row = {x["field"]: x for x in bridge.reflection_table(rep)}["o_pv_kwh"]
            self.assertIn("効かない" if "o_pv_kwh" in over and over["o_pv_kwh"] is None else "", row["detail"])

    def test_zero_purchase_with_unknown_pv_needs_no_grid_factor(self):
        vals = self.full(o_elec_kwh=V("o_elec_kwh", None, "not_applicable"))
        for f in ("o_pv_kwh", "o_export_kwh", "o_fm_ratio", "o_grid_value"):
            vals.pop(f)
        _, rep = bridge.build(vals, REFSET)
        self.assertEqual(rep["missing_required"], [])
        self.assertTrue(rep["expand"]["b2_moot"])
        out, st = self.summary(vals)
        self.assertTrue(st["B2"] and st["B6"])

    def test_assumed_zero_with_a_range_keeps_the_factor_required(self):
        unc = Uncertainty("interval", 0.0, 150000.0, 0.8)
        vals = self.full(o_elec_kwh=V("o_elec_kwh", 0.0, "assumption", uncertainty=unc))
        vals.pop("o_grid_value")
        _, rep = bridge.build(vals, REFSET)
        self.assertIn(FL.FIELDS["o_grid_value"]["label"], rep["missing_required"])
        pid = self.app.projects.create("r6r", "RC")
        rng = self.app._range(vals, 60.0, None, pid)
        self.assertIsNotNone(rng)                                          # said, not silently dropped
        self.assertIsNone(rng["low_t"])
        self.assertIn("計算できない", rng["note"])

    def test_unknown_fm_share_is_a_split_not_an_omission(self):
        vals = self.full()
        vals.pop("o_fm_ratio")
        _, rep = bridge.build(vals, REFSET)
        m = {x["field"]: x for x in rep["missing_inputs"]}["o_fm_ratio"]
        self.assertEqual(m["gap"], "split")
        self.assertNotIn("o_fm_ratio", [x["field"] for x in rep["omitted_inputs"]])
        self.assertEqual(rep["split_stages"], ["B2", "B6"])
        out, st = self.summary(vals)
        self.assertTrue(st["B6"] and st["B2"])
        self.assertTrue([x for x in out["summary"]["stages"] if x["stage"] == "B6"][0]["split"])
        self.assertIn("o_fm_ratio", [x["field"] for x in out["assumed_inputs"]])

    # --- zeros, B5, B3
    def test_zero_volume_material_makes_no_row(self):
        doc, rep = bridge.build(self.full(m_concrete=V("m_concrete", 0.0, unit="m3")), REFSET)
        self.assertNotIn("M-m_concrete", [r["material_id"] for r in tables(doc)["materials"]])
        self.assertNotIn("a4_delivery_fallback", [m["field"] for m in rep["missing_inputs"]])
        self.assertNotIn("C2", rep["incomplete_stages"])

    def test_unknown_scenario_with_zero_share_leaves_b5_complete(self):
        vals = self.full(a_replacement_cycle=V("a_replacement_cycle", 40.0), a_recon_fraction=V("a_recon_fraction", 0.0))
        vals.pop("a_reconstruction")
        _, rep = bridge.build(vals, REFSET, period=60)
        self.assertNotIn("a_reconstruction", [m["field"] for m in rep["missing_inputs"]])

    def test_missing_cycle_marks_b3_as_not_determined_not_short(self):
        vals = self.full()
        vals.pop("m_refresh_cycle")
        _, rep = bridge.build(vals, REFSET, period=60)
        m = {x["field"]: x for x in rep["missing_inputs"]}
        self.assertNotIn("B3", m["m_refresh_cycle"]["stages"])
        self.assertEqual(m["m_refresh_cycle@B3"]["gap"], "assumed")
        self.assertNotIn("B3", rep["incomplete_stages"])

    def test_double_count_note_names_a_typed_whole_value(self):
        vals = self.full(m_concrete=V("m_concrete", 900.0, "assumption", "t", scope="whole_building"),
                         m_concrete_fdn=V("m_concrete_fdn", 100.0, unit="t"))
        _, rep = bridge.build(vals, REFSET)
        self.assertTrue(rep["double_count"])
        self.assertNotIn("統計", " ".join(rep["double_count"]))

    # --- saving keeps provenance; bad requests are 400
    def test_hand_corrected_estimate_keeps_its_provenance(self):
        pid = self.app.projects.create("r6p", "RC")
        unc = Uncertainty("interval", 800.0, 1200.0, 0.8)
        self.app.projects.put(pid, V("m_rebar", 1000.0, "statistical", "t", method="rasmi_mi_x_gfa", source_id="rasmi",
                                     factor_version="v1", source_detail="detail", permission="CC-BY-4.0",
                                     retrieved_at="2026-11-15", uncertainty=unc))
        url = "/api/projects/%d/fields/m_rebar" % pid
        self.app.handle("PUT", url, {"value": 950, "unit": "t", "state": "assumption", "from_estimate": True})
        v = self.app.projects.current(pid, "m_rebar")
        self.assertEqual((v.factor_version, v.source_detail, v.permission), ("v1", "detail", "CC-BY-4.0"))
        self.app.handle("PUT", url, {"value": 950, "unit": "t", "state": "confirmed"})
        v = self.app.projects.current(pid, "m_rebar")
        self.assertIn("手で直した", v.note)
        self.assertEqual(v.factor_version, "v1")

    def test_bad_values_and_requests_are_refused_not_500(self):
        pid = self.app.projects.create("r6b", "RC")
        url = "/api/projects/%d/fields/b_gfa" % pid
        for bad in (10 ** 400, "1 5", "1e309", True):
            with self.assertRaises((ApiError, ProjectError)):
                self.app.handle("PUT", url, {"value": bad, "unit": "m2", "state": "confirmed"})
        with self.assertRaises(ApiError):
            self.app.handle("POST", "/api/projects/%d/estimate" % pid, {"field": ["m_concrete"]})

    def test_whole_candidates_withdrawn_when_the_other_field_has_a_value(self):
        pid = self.app.projects.create("r6w", "RC")
        self.app.projects.propose(pid, V("m_concrete", 2000.0, "statistical", "m3", method="mlit_area_unit_x_gfa", source_id="m",
                                         factor_version="v", uncertainty=Uncertainty("interval", 1000.0, 3000.0, 0.9),
                                         scope="whole_building", depends={"b_gfa": 1.0, "b_structure": "RC"}), "estimate")
        self.app.projects.put(pid, V("m_concrete_fdn", 300.0, unit="m3"))
        self.assertEqual(self.app.projects.withdraw_whole_candidates(pid), ["m_concrete"])
        self.assertEqual(self.app.projects.candidates(pid, "m_concrete"), [])

    # --- documents
    def test_src_names_bars_and_repeat_rows(self):
        f = documents._field_for
        for n in ("Steel reinforced concrete (SRC) columns", "Steel-reinforced concrete slab", "Steel mesh reinforced concrete topping",
                  "Concrete, Reinforced"):
            self.assertEqual(f(n), "m_concrete", n)
        for n in ("Reinforced concrete bars", "Reinforcing steel", "Reinforcement for concrete", "Welded mesh", "鉄筋 D13"):
            self.assertEqual(f(n), "m_rebar", n)
        self.assertIsNone(f("Grab bar"))
        csv = "名称,数量,単位\nコンクリート,500,m3\nコンクリート（再掲）,120,m3\nうち基礎コンクリート,120,m3\n".encode()
        r = documents.read("r.csv", base64.b64encode(csv).decode(), "d")
        got = {(p.field_id, p.unit): p.value for p in r["proposals"]}
        self.assertEqual(got, {("m_concrete", "m3"): 500.0})
        self.assertEqual(sum("再掲" in u["reason"] for u in r["unused"]), 2)

    def test_classification_is_linear_on_hostile_names(self):
        import time
        for name in ("()" * 16000 + "x", "reinforc" * 4096, "コンクリート用" * 5000, "(" * 30000 + ")"):
            t0 = time.perf_counter()
            documents._field_for(name + " " + name)
            documents._is_total(name)
            documents._not_added(name)
            self.assertLess(time.perf_counter() - t0, 0.5)

    def test_document_numbers_follow_the_screen_rule(self):
        csv = '名称,数量,単位\n鉄筋,"1,5",t\nアルミ,"12,500",kg\n鉄骨,1 5,t\n'.encode()
        r = documents.read("n.csv", base64.b64encode(csv).decode(), "d")
        got = {(p.field_id, p.unit): p.value for p in r["proposals"]}
        self.assertEqual(got, {("m_aluminium", "t"): 12.5})            # 12,500 kg (masses are summed in t)
        reasons = " ".join(u["reason"] for u in r["unused"])
        self.assertIn("カンマ", reasons)
        self.assertIn("空白", reasons)

    def test_shared_formula_copies_are_shifted_and_masterless_copies_refused(self):
        H = ('<row r="1"><c r="A1" t="inlineStr"><is><t>名称</t></is></c><c r="B1" t="inlineStr"><is><t>備考</t></is></c>'
             '<c r="C1" t="inlineStr"><is><t>数量</t></is></c><c r="D1" t="inlineStr"><is><t>単位</t></is></c></row>')
        def row(r, name, b, c, unit="m3"):
            return ('<row r="%d"><c r="A%d" t="inlineStr"><is><t>%s</t></is></c>%s%s<c r="D%d" t="inlineStr"><is><t>%s</t></is></c></row>'
                    % (r, r, name, b, c, r, unit))
        rows = (H + row(2, "コンクリート", '<c r="B2"><v>100</v></c>', '<c r="C2"><v>100</v></c>')
                + row(3, "コンクリート 割増", '<c r="B3"><f t="shared" ref="B3:C3" si="0">B2*1.1</f><v>110</v></c>',
                      '<c r="C3"><f t="shared" si="0"/><v>110</v></c>')
                + row(4, "コンクリート", '', '<c r="C4"><f t="shared" si="7"/><v>100</v></c>')
                + row(5, "コンクリート", '', '<c r="C5"><f>IF(A1="%s",0,SUM(C2:C3))</f><v>150</v></c>' % ("x" * 2100)))
        r = documents.read("s.xlsx", base64.b64encode(self.xlsx(rows)).decode(), "d")
        got = {(p.field_id, p.unit): p.value for p in r["proposals"]}
        self.assertEqual(got, {("m_concrete", "m3"): 100.0})
        reasons = " ".join(u["reason"] for u in r["unused"])
        self.assertIn("同じ列", reasons)
        self.assertIn("共有の数式の元が無い", reasons)
        self.assertIn("SUM", reasons)

    # --- the screen
    def test_ui_has_the_round6_guards(self):
        js = (HERE / "web" / "app.js").read_text(encoding="utf-8")
        for needle in ("function ask(", "やめる", "saveField.reason", "inputValue(f).bad", "valueLabel", "inconsistent_inputs",
                       "h.also", "x.split", "locked", "dialog(\"自動概算の説明\""):
            self.assertIn(needle, js, needle)
        proc = subprocess.run(["node", "-e", """
            const src = require('fs').readFileSync(process.argv[1], 'utf8');
            const m = src.match(/function parseNumber[\\s\\S]*?\\n}\\n/);
            eval(m[0]);
            console.log(['1 5', ' 15 ', '12 500'].map((x) => JSON.stringify(parseNumber(x))).join('|'));""",
                               str(HERE / "web" / "app.js")], capture_output=True, text=True)
        if proc.returncode != 0 and "not found" in (proc.stderr or ""):
            self.skipTest("node is not installed")
        parts = proc.stdout.strip().split("|")
        self.assertTrue(json.loads(parts[0])["bad"])
        self.assertEqual(json.loads(parts[1])["value"], 15)
        self.assertTrue(json.loads(parts[2])["bad"])


class RegressionTests(unittest.TestCase):
    def test_research_folders_and_engine_unchanged(self):
        root = HERE.parents[1]
        out = subprocess.run(["git", "status", "--porcelain", "--", "whole-life-carbon-jcat-study"], cwd=root,
                             capture_output=True, text=True).stdout.splitlines()
        import re
        touched = [ln[3:] for ln in out
                   if re.match(r"whole-life-carbon-jcat-study/(\d\d)_", ln[3:]) and int(ln[3:].split("/")[1][:2]) < 23]
        self.assertEqual(touched, [], "the research folders 01-22 (engine, app base, classification) must not change: %s" % touched)

    def test_no_bytecode_written(self):
        self.assertEqual(list(HERE.rglob("__pycache__")), [])


if __name__ == "__main__":
    unittest.main()
