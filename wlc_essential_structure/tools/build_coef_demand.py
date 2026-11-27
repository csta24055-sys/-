"""Coefficient DEMAND ledger: every coefficient the independent model needs, derived backwards from the 70 units'
inputs (WLC_THEORY_RESEARCH_BASE/data/units70_inputs.csv, 149 paths) and their formulas (UNITS_70.md).

Each demand row = one physical quantity that must come from outside the project (a factor, a rate, a life, a density),
at the granularity the formulas need. Project data (quantities, areas, distances) are NOT coefficients and are listed
separately as 'project inputs' only for completeness. 'jcat_restricted_kind' marks the kinds whose J-CAT values may not
be reused (use condition 5): they must come from independent sources.

Usage: python3 -I tools/build_coef_demand.py <out.csv>
"""
import csv
import sys

# key, item (ja), category, expected unit, symbol/path, family, units, granularity, jcat_restricted_kind
D = []


def add(key, item, cat, unit, sym, fam, units, gran="", restricted=""):
    D.append(dict(demand_key=key, item=item, category=cat, unit=unit, symbol_path=sym, family=fam, units=units,
                  granularity=gran, jcat_restricted_kind=restricted))


M = "materials.factor_id → factors (A1-A3)"
for k, n, u in [("concrete_ready_mix", "レディーミクストコンクリート（強度別）", "kgCO2e/m3"), ("cement", "セメント（普通・高炉・フライアッシュ）", "kgCO2e/t"),
                ("rebar", "鉄筋（電炉・高炉）", "kgCO2e/t"), ("structural_steel", "構造用鋼材（形鋼・鋼板）", "kgCO2e/t"),
                ("steel_sheet_galvanised", "溶融亜鉛めっき鋼板", "kgCO2e/t"), ("timber_sawn", "製材（針葉樹）", "kgCO2e/m3"),
                ("timber_glulam", "集成材", "kgCO2e/m3"), ("timber_clt", "CLT", "kgCO2e/m3"), ("plywood", "合板", "kgCO2e/m3"),
                ("glass_float", "フロートガラス", "kgCO2e/kg"), ("glass_igu", "複層ガラス", "kgCO2e/m2"),
                ("aluminium", "アルミニウム（一次・押出）", "kgCO2e/kg"), ("aluminium_window", "アルミサッシ", "kgCO2e/m2"),
                ("gypsum_board", "石膏ボード", "kgCO2e/m2"), ("mineral_wool", "ロックウール", "kgCO2e/kg"), ("glass_wool", "グラスウール", "kgCO2e/kg"),
                ("eps", "EPS", "kgCO2e/kg"), ("xps", "XPS", "kgCO2e/kg"), ("pur_pir", "硬質ウレタン・PIR", "kgCO2e/kg"),
                ("pvc_pipe", "塩ビ管", "kgCO2e/kg"), ("pe_pipe", "PE 管", "kgCO2e/kg"), ("paint", "塗料（水性・溶剤）", "kgCO2e/kg"),
                ("copper", "銅（管・ケーブル）", "kgCO2e/kg"), ("ceramic_tile", "陶磁器質タイル", "kgCO2e/m2"), ("brick", "れんが", "kgCO2e/kg"),
                ("aggregate", "骨材", "kgCO2e/t"), ("mortar", "モルタル", "kgCO2e/kg"), ("bitumen_membrane", "アスファルト防水", "kgCO2e/m2")]:
    add("mat_" + k, n, "material", u, M, "F2", "A13-01;A13-02;A13-03;B3-01;B4-02;B5-01", "材料区分・製法・地域", "排出原単位")
E = "equipment.factor_id (A1-A3 of equipment)"
for k, n, u in [("chiller", "チラー", "kgCO2e/台 or /kW"), ("heat_pump_vrf", "パッケージ・VRF・ヒートポンプ", "kgCO2e/台 or /kW"),
                ("ahu", "空調機（AHU）", "kgCO2e/台"), ("boiler", "ボイラー", "kgCO2e/台"), ("water_heater", "給湯器", "kgCO2e/台"),
                ("transformer", "変圧器", "kgCO2e/台 or /kVA"), ("switchboard", "配電盤", "kgCO2e/面"), ("cable", "電線・ケーブル", "kgCO2e/m or /kg"),
                ("luminaire", "照明器具（LED）", "kgCO2e/台"), ("lift", "昇降機", "kgCO2e/台"), ("sanitary_ware", "衛生陶器", "kgCO2e/個"),
                ("pv_panel", "太陽光パネル", "kgCO2e/kWp"), ("mep_per_m2", "設備一式（床面積当たり）", "kgCO2e/m2")]:
    add("eq_" + k, n, "equipment", u, E, "F2", "X-01;X-14;B3-01;B4-02;B5-01", "機器種別・容量", "排出原単位")
add("eq_eol", "設備機器の廃棄時", "equipment", "kgCO2e/kg", "equipment.eol_factor_id", "F2", "X-14;B4-02", "", "排出原単位")
for k, n in [("truck", "トラック（t·km）"), ("rail", "鉄道貨物（t·km）"), ("ship", "船舶（t·km）")]:
    add("tr_" + k, n, "transport", "kgCO2e/t·km", "materials.transport.factor_id;end_of_life.waste_hauls.factor_id", "F2", "A4-01;A4-02;C2-01;X-12", "積載率・車格", "排出原単位")
add("tr_load_factor", "積載率", "transport", "—", "materials.transport.load_factor", "F1", "X-12", "車格", "")
add("tr_delivery_product", "製品別の搬入係数", "transport", "kgCO2e/単位量", "materials.transport.delivery_factor_id", "F2", "A4-02", "製品", "排出原単位")
for k, n, u in [("electricity_grid_jp", "電力（日本の系統、年度別・事業者別）", "kgCO2e/kWh"), ("city_gas", "都市ガス", "kgCO2e/m3 or /GJ"),
                ("lpg", "LPG", "kgCO2e/kg"), ("kerosene", "灯油", "kgCO2e/L"), ("heavy_oil_a", "A 重油", "kgCO2e/L"), ("diesel", "軽油", "kgCO2e/L"),
                ("gasoline", "ガソリン", "kgCO2e/L"), ("district_heat", "地域熱供給", "kgCO2e/MJ")]:
    add("en_" + k, n, "energy", u, "operation.*_factor_id;construction.fuels.factor_id;operation.grid.*", "F1/F2/F3",
        "A5-01;A5-02;B6-01;B6-02;B6-03;B2-01;C1-01;X-06;X-11", "年度・算定方法（基礎/調整後、燃焼/上流）", "排出原単位")
add("en_grid_future_path", "系統係数の将来経路（start・decline・floor）", "energy", "kgCO2e/kWh, /年", "operation.grid.start;annual_decline;floor", "F1", "X-06;B6-01", "政策シナリオ", "")
add("en_heat_content", "単位発熱量（燃料別）", "energy", "GJ/単位", "unit_conversions.factor", "F1", "B6-02;A5-02", "燃料", "")
for k, n, u in [("water_supply", "上水", "kgCO2e/m3"), ("wastewater", "下水処理", "kgCO2e/m3"), ("municipal_waste", "一般廃棄物（運用時）", "kgCO2e/kg")]:
    add("wt_" + k, n, "water", u, "water_waste.*_factor_id", "F2/F3", "B7-01;B7-02;B7-03;B7-04", "地域・処理方式", "排出原単位")
for k, n in [("construction_waste_mixed", "建設混合廃棄物の処理"), ("landfill_inert", "安定型埋立"), ("landfill_mixed", "管理型埋立"),
             ("incineration_wood", "木くずの焼却"), ("incineration_plastic", "廃プラの焼却"), ("concrete_crushing", "コンクリート破砕・再生"),
             ("metal_recycling", "金属の再資源化（処理）"), ("sorting", "選別")]:
    add("wa_" + k, n, "waste", "kgCO2e/t", "construction.waste_streams.factor_id;materials.end_of_life.routes.factor_id", "F2", "A5-03;C3-01;C4-01;X-09", "処理経路", "排出原単位")
add("wa_waste_rate", "端材率（材料ロス率）", "waste", "—", "materials.waste_rate", "F1", "A13-05;X-13;X-10", "材料", "（J-CAT の端材率は LCA 指針由来：流用しない）")
add("wa_reuse_rate", "端材の再使用率", "waste", "—", "materials.reuse_rate", "F1", "X-13", "材料", "")
add("wa_eol_route_fraction", "廃棄経路の比率（再資源化率など）", "waste", "—", "materials.end_of_life.routes.fraction", "F2", "C3-01;C4-01;X-09", "材料・地域", "")
add("dm_demolition", "解体作業（重機燃料）", "waste", "kgCO2e/m2 or L/m2", "end_of_life.demolition_activities.factor_id", "F2", "C1-01", "構造種別", "排出原単位")
for g in ["r32", "r410a", "r134a", "r404a", "r407c", "r22", "r1234ze", "r1234yf", "r290", "r744", "r717", "r513a", "r454b"]:
    add("rf_gwp_" + g, "GWP100 " + g.upper(), "refrigerant", "kgCO2e/kg", "refrigerants.gwp", "F2/F4", "B1-01;B1-02;B1-03;B1-04", "評価報告書の版", "")
for k, n, u in [("leak_rate", "年間漏洩率（機器種別）", "1/年"), ("replacement_loss", "交換時の損失率", "—"), ("recovery_rate", "廃棄時の回収率", "—"),
                ("charge_per_kw", "冷媒充填量（容量当たり）", "kg/kW"), ("device_life", "冷媒機器の交換周期", "年")]:
    add("rf_" + k, n, "refrigerant", u, "refrigerants.*", "F4/F3", "B1-02;B1-03;B1-04", "機器種別", "フロン漏洩率" if k == "leak_rate" else "")
for k, n in [("structure", "躯体"), ("roof", "屋根・防水"), ("facade", "外壁・外装"), ("window", "建具・窓"), ("interior_finish", "内装仕上げ"),
             ("hvac", "空調設備"), ("electrical", "電気設備"), ("sanitary", "給排水衛生設備"), ("lift", "昇降機"), ("pv", "太陽光発電")]:
    add("life_" + k, "耐用年数・交換周期：" + n, "lifetime", "年", "materials.material_life;materials.refresh_cycle;equipment.service_life", "F3",
        "B4-01;B4-02;B4-03;B3-01;X-08;X-10", "部位・機器", "更新周期")
    add("repair_" + k, "年間修繕率：" + n, "repair", "1/年（初期排出に対する比）", "materials.repair_rate;equipment.repair_rate", "F3", "B3-01;B3-02", "部位・機器", "修繕率")
add("ren_cycle", "大型改修・建替の周期", "lifetime", "年", "boundary.replacement_cycle", "F3", "B5-01", "用途", "更新周期")
add("ren_fraction", "改修の割合 φ", "lifetime", "—", "boundary.reconstruction_scope_fraction", "F1", "B5-01", "改修の種類", "")
add("onTop_ratio", "未数量工事の上乗せ率", "other", "—", "materials.unquantified_cost_ratio", "F1", "A13-04", "工種", "工事分倍率")
add("st_timber_density", "木材の全乾密度", "storage", "kg/m3", "summary_quantities.timber_dry_density_kg_per_m3", "F1", "STO-01", "樹種", "")
add("st_carbon_fraction", "木材の炭素含有率", "storage", "—", "summary_quantities.timber_carbon_fraction", "F1", "STO-01", "", "")
add("st_carbonation", "コンクリートの炭酸化吸収係数", "storage", "kgCO2/m3 or /m2", "summary_quantities.concrete_uptake_factor_id", "F2", "STO-02", "曝露条件", "")
for g in ["co2", "ch4", "n2o"]:
    add("gwp_" + g, "GWP100 " + g.upper(), "other", "—", "gwp.value", "F2", "X-04;X-05", "評価報告書の版", "")
add("eeio_construction", "費用ベース係数（産業連関）", "eeio", "kgCO2e/通貨", "cost_items.factor_id", "F2", "X-16", "部門・基準年", "排出原単位")
add("price_index", "物価指数（基準年換算）", "eeio", "—", "price_index.value", "F1", "X-16", "年", "")
add("eui_per_m2", "床面積当たり電力原単位（用途別）", "energy", "kWh/m2·年", "operation.electricity_per_m2_per_year", "F1/F3", "X-11", "用途・地域", "")
add("density_concrete", "コンクリートの密度", "other", "kg/m3", "unit_conversions.factor", "F1", "換算全般", "", "")
add("density_steel", "鋼の密度", "other", "kg/m3", "unit_conversions.factor", "F1", "換算全般", "", "")

PROJECT = ["materials.quantity", "equipment.quantity", "materials.transport.mass_t", "materials.transport.distance_km",
           "construction.electricity_kwh", "construction.fuels.quantity", "operation.electricity.table", "operation.gas.table",
           "water_waste.water.table", "project.gross_floor_area", "refrigerants.charge_mass_kg", "operation.facility_management_ratio"]


def main(out):
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(D[0]))
        w.writeheader()
        w.writerows(D)
    print(len(D), "demand rows;", sum(1 for d in D if d["jcat_restricted_kind"].strip() and not d["jcat_restricted_kind"].startswith("（")),
          "of the J-CAT-restricted kinds; project inputs (not coefficients):", len(PROJECT))


if __name__ == "__main__":
    main(sys.argv[1])
