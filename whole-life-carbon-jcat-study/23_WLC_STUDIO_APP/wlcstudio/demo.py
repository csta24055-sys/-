"""Reproducible fictional demo project (kept apart from any real benchmark).

Every value is read from the frozen fictional sample of 12_APP_BASE (generator seed 4201, RC office, size S)
and aggregated to the four screens: material rows are summed per class and unit, equipment rows counted per
trade, year tables averaged. Nothing here describes a real building; the project is stored with
data_kind='fictional_demo' and every value says so in its note.
"""
from __future__ import annotations

import json
import statistics

from . import fields as FL
from .engine import APP_BASE
from .project import Projects
from .provenance import Uncertainty, Value

SAMPLE = APP_BASE / "samples" / "input_fictional.json"
NOTE = "架空デモ：凍結済みの生成器（seed 4201）の値から集計。実在の建物ではない。"


def demo_values() -> dict[str, Value]:
    doc = json.loads(SAMPLE.read_text(encoding="utf-8"))
    items, tables = {}, {}
    for c in doc["categories"].values():
        items.update(c.get("items", {}))
        tables.update(c.get("tables", {}))
    out: dict[str, Value] = {}

    def put(fid, value, state="confirmed", unit=None, **kw):
        F = FL.FIELDS[fid]
        out[fid] = Value(fid, state, value, unit if unit is not None else F.get("unit", ""), method="fictional_sample",
                         source_id="fictional_sample_seed4201", source_detail=kw.pop("detail", ""), note=NOTE, **kw)

    put("b_use", items["project.building_use"], detail="project.building_use")
    put("b_structure", items["project.structure_type"], detail="project.structure_type")
    put("b_gfa", items["project.gross_floor_area"], detail="project.gross_floor_area")
    put("b_floors_above", items["project.floors_above"], detail="project.floors_above")
    put("b_floors_below", items["project.floors_below"], detail="project.floors_below")
    put("b_height", items["project.building_height"], detail="project.building_height")
    put("b_footprint", items["project.building_footprint"], detail="project.building_footprint")
    put("b_completion_year", items["project.completion_year"], detail="project.completion_year")
    put("b_project_type", items["project.project_type"], detail="project.project_type")
    put("a_stages", "ALL", detail="boundary.included_lifecycle_stages（14 段階）")
    put("a_reconstruction", items["boundary.reconstruction_scenario"], detail="boundary.reconstruction_scenario")
    put("a_replacement_cycle", items["boundary.replacement_cycle"], detail="boundary.replacement_cycle")
    put("a_eol_route", "RECYCLE", state="assumption", detail="生成器の経路の割合を 1 つのシナリオにまとめた（仮定）")

    mats = tables["materials"]
    to_kg = {"kg": 1.0, "t": 1000.0}
    for fid, cls, label, unit, units, div, grp in FL.MATERIALS:
        fdn = div == "FOUNDATION"
        rows = [r for r in mats if r["material_class"] == cls
                and ((r["construction_division"] == "FOUNDATION") == fdn if cls == "CONCRETE" else True)
                and r["quantity_unit"] in units]
        if not rows:
            out[fid] = Value(fid, "not_applicable", note=NOTE + "（この分類の行が無い）", method="fictional_sample")
            continue
        # one value per field: the rows of the field's own unit, or (if there are more of them) the mass rows in t.
        # The choice is deterministic (no set order), and rows of the other dimension are named in the note.
        mass_rows = [r for r in rows if r["quantity_unit"] in to_kg]
        own_rows = [r for r in rows if r["quantity_unit"] == unit and unit not in to_kg]
        if unit in to_kg or len(mass_rows) > len(own_rows):
            used, u = mass_rows, ("t" if "t" in units else unit)
            q = sum(r["quantity"] * to_kg[r["quantity_unit"]] for r in used) / to_kg[u]
        else:
            used, u = own_rows, unit
            q = sum(r["quantity"] for r in used)
        left = len(rows) - len(used)
        put(fid, round(q, 6), unit=u, detail="materials[] の %s を %s で合計（%d 行%s）"
            % (cls, u, len(used), "、単位の違う %d 行は入れていない" % left if left else ""))
    put("m_waste_rate", round(statistics.fmean(r["waste_rate"] for r in mats), 6), state="assumption", detail="materials[].waste_rate の平均")
    put("m_reuse_rate", round(statistics.fmean(r["reuse_rate"] for r in mats), 6), state="assumption", detail="materials[].reuse_rate の平均")
    put("m_repair_rate", round(statistics.fmean(r["repair_rate"] for r in mats), 6), state="assumption", detail="materials[].repair_rate の平均")
    put("m_refresh_cycle", round(statistics.fmean(r["refresh_cycle"] for r in mats), 3), state="assumption", detail="materials[].refresh_cycle の平均")
    put("m_quantity_basis", "DESIGN", state="assumption", detail="設計数量とみなした")
    put("a_eol_haul_km", round(statistics.fmean(r["end_of_life.haul_distance_km"] for r in mats), 3), state="assumption",
        detail="materials[].end_of_life.haul_distance_km の平均")
    put("c_site_electricity", items["construction.electricity_kwh"], detail="construction.electricity_kwh")
    fuels = [r for r in tables["construction.fuels"] if r["kind"] == "DIESEL"]
    if fuels:
        put("c_diesel", sum(r["quantity"] for r in fuels), detail="construction.fuels の DIESEL")

    eq = tables["equipment"]
    for trade, _ in FL.TRADES:
        t = trade.lower()
        rows = [r for r in eq if r["trade"] == trade]
        if not rows:
            out["e_%s_count" % t] = Value("e_%s_count" % t, "not_applicable", note=NOTE, method="fictional_sample")
            continue
        n = sum(r["quantity"] for r in rows)
        put("e_%s_count" % t, n, detail="equipment[] の %s の台数" % trade)
        put("e_%s_life" % t, round(statistics.fmean(r["service_life"] for r in rows), 3), detail="service_life の平均")
        put("e_%s_mass" % t, round(sum(r["end_of_life_mass_kg"] for r in rows) / n, 3), detail="end_of_life_mass_kg ÷ 台数")
    put("e_repair_rate", round(statistics.fmean(r["repair_rate"] for r in eq), 6), state="assumption", detail="repair_rate の平均")
    ref = tables["refrigerants"]
    if ref:
        put("r_charge_kg", round(sum(r["charge_mass_kg"] for r in ref), 6), detail="refrigerants[] の充填量の合計")
        w = sum(r["charge_mass_kg"] for r in ref)
        for fid, col in (("r_gwp", "gwp"), ("r_leak_rate", "annual_leak_rate"), ("r_loss_rate", "replacement_loss_rate"),
                         ("r_recovery_rate", "end_of_life_recovery_rate"), ("r_life", "service_life")):
            put(fid, round(sum(r[col] * r["charge_mass_kg"] for r in ref) / w, 6), state="assumption",
                detail="充填量で重みづけた平均")
        put("r_top_up", "yes" if any(r["top_up"] for r in ref) else "no", detail="top_up")

    put("o_source", "PHYSICS", detail="operation.energy_simulation_basis（設計計算とみなす）")
    for fid, name in (("o_elec_kwh", "electricity"), ("o_gas_m3", "gas"), ("o_oil_l", "oil"), ("o_dheat_mj", "district_heat"),
                      ("o_pv_kwh", "onsite_generation"), ("o_export_kwh", "onsite_export")):
        base = items["operation.%s.base" % name]
        if base == 0:
            out[fid] = Value(fid, "not_applicable", note=NOTE + "（使用なし）", method="fictional_sample")
        else:
            put(fid, base, detail="operation.%s.base" % name)
    put("o_fm_ratio", items["operation.facility_management_ratio"], detail="operation.facility_management_ratio")
    put("o_grid_value", round(statistics.fmean(items["operation.grid.table"][:60]), 6), state="assumption",
        detail="operation.grid.table の最初の 60 年の平均を一定値とした（仮定）")
    put("o_grid_construction", items["operation.grid.construction_value"], detail="operation.grid.construction_value")
    for fid, name in (("o_water_m3", "water"), ("o_sewage_m3", "sewage"), ("o_waste_kg", "municipal_waste")):
        tab = items["water_waste.%s.table" % name][:60]
        mean = statistics.fmean(tab)
        put(fid, round(mean, 3), state="statistical", detail="water_waste.%s.table の最初の 60 年の平均" % name,
            uncertainty=Uncertainty("interval", round(min(tab), 3), round(max(tab), 3), 0.99, False,
                                    "架空の年表の最小〜最大（校正していない）"))
    return out


def create_demo(projects: Projects) -> int:
    pid = projects.create("架空デモ（RC・事務所・seed 4201）", "RC", data_kind="fictional_demo")
    for v in demo_values().values():
        projects.put(pid, v)
    return pid
