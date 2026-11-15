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
        self.assertEqual(row["states"]["end_of_life.mass_kg"], "DERIVED")
        self.assertEqual(items(doc)["project.states"]["gross_floor_area"], "OBSERVED")
        self.assertEqual({p["value_state"] for p in tables(doc)["provenance"]}, {"OBSERVED", "DERIVED", "ESTIMATE"})

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
        httpd.server_close()

    def test_refuses_non_loopback_bind(self):
        from wlcstudio import server
        with self.assertRaises(SystemExit):
            server.serve(self.td.name, host="0.0.0.0", port=0)


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
