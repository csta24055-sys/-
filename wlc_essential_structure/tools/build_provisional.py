"""Provisional coefficients that close the remaining demand rows (final instruction: fill 100 %, mark low reliability).

Reliability flags (column data_type = "provisional:<flag>"):
  DEF  definition / physical property (GWP of CO2 = 1, densities): not uncertain, but not taken from a dataset row
  P1   proxy derived from REAL data already in the database (similar material, foreign value used for Japan, ratio)
  P2   general web / technical source / press report, value not checked against a primary document
  P3   assumption set by this study (no source for the value itself); a reasoning is given
No J-CAT value is used (the J-CAT kinds 工事分倍率・更新周期・修繕率・フロン漏洩率 are set independently).
Usage: python3 -I tools/build_provisional.py <out.csv>
"""
import csv
import sys

COLS = ["factor_key", "item", "category", "value", "unit", "declared_unit", "ghg_basis", "modules", "region",
        "technology_or_route", "reference_year", "data_type", "source_org", "source_title", "edition_version", "url",
        "retrieved", "licence_name", "licence_url", "cite_single_value", "research_use", "db_incorporation",
        "commercial_use", "redistribution", "rights_class", "notes"]

# demand_key, item, category, value, unit, modules, flag, source/url, uncertainty (low, high), reasoning
P = [
    ("mat_mortar", "モルタル（セメント:砂=1:3）", "material", 0.19, "kgCO2e/kg", "A1-A3", "P1", "derived: セメント協会 OPC 741.3 g/kg", (0.12, 0.25),
     "cement mass share ~25 % x 0.741 + sand ~75 % x 0.005 (UK aggregates) ≈ 0.19; blast-furnace cement would give ~0.11"),
    ("mat_bitumen_membrane", "改質アスファルト防水シート（1 層）", "material", 5.8, "kgCO2e/m2", "A1-A3", "P2",
     "General Membrane SBS bituminous membrane EPD (EPDItaly), A1 4.99 + A2 0.529 + A3 0.285, via web search https://www.epditaly.it/wp-content/uploads/2016/12/EPD-SBS-bituminous-membrane.pdf", (4.0, 9.0),
     "single foreign product EPD, sum of modules read from a search snippet; multi-layer systems multiply by layers"),
    ("eq_eol", "設備機器の廃棄時（製造に対する比）", "equipment", 0.14, "ratio to A1-A3 of the equipment", "C3-C4", "P1",
     "derived: KBOB office MEP per m2, disposal/production = 6.6/48.4", (0.05, 0.25), "ratio of KBOB Entsorgung to Herstellung for electrical+sanitary+ventilation+heat generation"),
    ("tr_load_factor", "トラックの積載効率", "transport", 0.39, "—", "A4;C2", "P2",
     "国交省 自動車輸送統計年報 FY2025 営業用普通貨物 積載効率 39.08 %（日本食糧新聞の報道経由） https://news.nissyoku.co.jp/news/yokotah20260929092159763", (0.30, 0.50),
     "press report of the official statistic; original table not read"),
    ("en_grid_future_path", "電力係数の将来経路：開始値", "energy", 0.423, "kgCO2e/kWh", "B6", "P1", "全国平均係数 FY2024 (環境省・経産省)", (0.40, 0.45), "start of the path = latest real value"),
    ("en_grid_future_path", "電力係数の将来経路：年間低下量（2024→2040 線形）", "energy", 0.0133, "kgCO2e/kWh/年", "B6", "P3",
     "assumption from the 第7次エネルギー基本計画 2040 mix (renewables 40-50 %, nuclear ~20 %, thermal 30-40 %) https://www.meti.go.jp/press/2024/02/20250218001/20250218001-3.pdf", (0.0, 0.02),
     "thermal share ~0.35 x ~0.6 kg/kWh ≈ 0.21 kg/kWh in FY2040 -> (0.423-0.21)/16; the plan itself states no factor"),
    ("en_grid_future_path", "電力係数の将来経路：下限", "energy", 0.05, "kgCO2e/kWh", "B6", "P3", "assumption (2050 net-zero target)", (0.0, 0.21), "residual factor after 2050"),
    ("wa_construction_waste_mixed", "建設混合廃棄物の処理（日本の代用）", "waste", 87, "kgCO2e/t", "A5;C3-C4", "P1", "ADEME Base Carbone (France) mixed non-hazardous construction waste", (23, 120), "foreign value used for Japan; Japan mixed-waste recycling 63.2 % (国交省 FY2018) is similar order"),
    ("wa_landfill_inert", "安定型埋立（日本の代用）", "waste", 13, "kgCO2e/t", "C4", "P1", "ADEME inert construction waste", (5, 30), "foreign value used for Japan"),
    ("wa_incineration_wood", "木くずの焼却（日本の代用、化石分のみ）", "waste", 30, "kgCO2e/t", "C3", "P3", "assumption: biogenic CO2 excluded, CH4/N2O + transport/handling", (10, 122), "ADEME wood end-of-life 122 kg/t is the upper bound"),
    ("wa_concrete_crushing", "コンクリート塊の破砕・再生（日本の代用）", "waste", 26, "kgCO2e/t", "C3", "P1", "ADEME concrete/brick/tile end of life", (8, 30), "foreign value; Japan recycling rate 99.3 % (国交省 FY2018)"),
    ("wa_metal_recycling", "金属の再資源化の処理（日本の代用）", "waste", 12.2, "kgCO2e/t", "C3", "P1", "KBOB disposal of reinforcing steel 0.0122 kg/kg", (5, 30), "foreign value used for Japan"),
    ("wa_sorting", "選別（建設廃棄物の中間処理）", "waste", 4.2, "kgCO2e/t", "C3", "P3", "assumption: ~10 kWh/t x 0.423 kg/kWh", (2, 15), "physical estimate of sorting-plant electricity"),
    ("wa_waste_rate", "端材率（日本の代用、材料別）", "waste", 0.05, "—", "A5", "P1", "Boverket construction waste factors (concrete 1.03, rebar 1.09, timber 1.10, gypsum 1.12)", (0.03, 0.12), "material-specific Swedish factors used for Japan; 0.05 is the representative mid value"),
    ("wa_reuse_rate", "端材の再使用率", "waste", 0.0, "—", "A5", "P3", "assumption: no on-site reuse unless the project declares it", (0.0, 0.3), "conservative default"),
    ("dm_demolition", "解体作業（RC、重機の軽油）", "waste", 7.9, "kgCO2e/m2", "C1", "P3",
     "assumption 3 L diesel/m2 x 2.62 kgCO2/L (軽油、環境省 算定方法)", (3.0, 20.0), "method: 建設機械等損料表の燃料消費 × 稼働 ÷ 床面積; value not from a survey"),
    ("rf_charge_per_kw", "冷媒充填量（冷房能力当たり）", "refrigerant", 0.3, "kg/kW", "B1", "P1",
     "derived from EPD refrigerant charges (Trane GVAF ~0.12 kg/kW, Daikin Sky Air ~0.3 kg/kW) and 環境省 ビル用マルチ 18 kg/台", (0.12, 0.6), "ratio of stated charge to rated capacity"),
    ("rf_device_life", "冷媒機器（空調）の交換周期", "refrigerant", 20, "年", "B1;B4", "P1", "国交省 官庁営繕 BIMMS-N 空調機の更新周期 20 年（実データ、対応付けの代用）", (13, 20), "statutory life 13-15 years is the lower bound"),
    ("repair_roof", "年間修繕率：屋根・防水", "repair", 0.015, "1/年", "B3", "P3", "anchored on the statistical B3 (2.67 kg/m2·yr ≈ 0.7 %/yr of A1-A3)", (0.005, 0.03), "roof and waterproofing weather fastest"),
    ("repair_facade", "年間修繕率：外壁・外装", "repair", 0.01, "1/年", "B3", "P3", "same anchor; 長期修繕計画ガイドライン 外壁塗装 13.6 % of repair cost", (0.005, 0.02), ""),
    ("repair_window", "年間修繕率：建具・窓", "repair", 0.005, "1/年", "B3", "P3", "same anchor", (0.002, 0.01), ""),
    ("repair_interior_finish", "年間修繕率：内装仕上げ", "repair", 0.01, "1/年", "B3", "P3", "same anchor", (0.005, 0.02), ""),
    ("repair_hvac", "年間修繕率：空調設備", "repair", 0.005, "1/年", "B3", "P3", "same anchor (replacements are in B4)", (0.002, 0.01), ""),
    ("repair_electrical", "年間修繕率：電気設備", "repair", 0.005, "1/年", "B3", "P3", "same anchor", (0.002, 0.01), ""),
    ("repair_sanitary", "年間修繕率：給排水衛生設備", "repair", 0.005, "1/年", "B3", "P3", "same anchor", (0.002, 0.01), ""),
    ("repair_lift", "年間修繕率：昇降機", "repair", 0.01, "1/年", "B3", "P3", "same anchor; 長期修繕計画ガイドライン 昇降機 4.3 %", (0.005, 0.02), ""),
    ("repair_pv", "年間修繕率：太陽光発電", "repair", 0.005, "1/年", "B3", "P3", "same anchor", (0.002, 0.01), ""),
    ("ren_cycle", "大規模改修の周期", "lifetime", 30, "年", "B5", "P3", "assumption (common LCC planning horizon for a major renewal)", (25, 40), ""),
    ("ren_fraction", "大規模改修の割合 φ", "lifetime", 0.25, "—", "B5", "P3", "assumption: share of initial A1-A5 + C renewed at a major renovation", (0.1, 0.4), "overlaps B4 if building-part replacements are also entered"),
    ("onTop_ratio", "未数量工事の上乗せ率（独立の仮定、J-CAT の工事分倍率は不使用）", "other", 0.10, "—", "A1-A3", "P3",
     "assumption in the spirit of design-stage contingency factors used in WLC guidance (value itself not taken from a source)", (0.05, 0.20), "use 0 when a complete bill of quantities is given"),
    ("gwp_co2", "GWP100 CO2", "other", 1, "—", "all", "DEF", "definition (IPCC)", (1, 1), ""),
    ("price_index", "建設工事費の価格比（2020→2025）", "eeio", 1.2, "—", "B3;X-16", "P3", "assumption (建設工事費デフレーターの値は未取得)", (1.1, 1.3), "used to convert 2025 spending to 2020 IO prices"),
    ("density_concrete", "コンクリートの密度", "other", 2350, "kg/m3", "conversion", "DEF", "Boverket conversion factor for C30/37 (2350 kg/m3)", (2300, 2400), ""),
    ("density_steel", "鋼の密度", "other", 7850, "kg/m3", "conversion", "DEF", "Boverket conversion factor for rebar (7850 kg/m3)", (7850, 7850), ""),
    # quantities that the statistics do not give (input variables of a building; provisional defaults for the representative office)
    ("qty_glazing_m2_per_m2", "ガラス・サッシの面積（延床当たり、既定値）", "quantity", 0.15, "m2/m2", "input", "P3", "assumption for a mid-rise office (窓面積 ≈ 外壁の 30 %)", (0.08, 0.30), "replace by project data"),
    ("qty_gypsum_m2_per_m2", "石膏ボードの面積（延床当たり、既定値）", "quantity", 2.0, "m2/m2", "input", "P3", "assumption: partitions both sides + ceilings", (1.0, 3.0), "12.5 mm, 710 kg/m3 -> 8.9 kg/m2"),
    ("qty_insulation_kg_per_m2", "断熱材の質量（延床当たり、既定値）", "quantity", 1.2, "kg/m2", "input", "P3", "assumption: EPS/XPS on roof and walls", (0.5, 3.0), ""),
    ("qty_waterproof_m2_per_m2", "防水の面積（延床当たり、既定値）", "quantity", 0.17, "m2/m2", "input", "P3", "assumption: roof area / floor area of a 6-storey office", (0.08, 0.35), ""),
    ("qty_mep_cooling_kw_per_m2", "冷房能力（延床当たり、既定値）", "quantity", 0.12, "kW/m2", "input", "P3", "assumption: 120 W/m2 typical office cooling load", (0.08, 0.18), "with rf_charge_per_kw gives the refrigerant charge"),
    ("a5_site_energy_ratio", "施工時のエネルギー（A1-A3 に対する比）", "energy", 0.04, "—", "A5", "P3", "assumption (literature range 2-8 % of A1-A3, not checked)", (0.02, 0.08), ""),
]


def main(out):
    w = csv.DictWriter(open(out, "w", encoding="utf-8", newline=""), fieldnames=COLS)
    w.writeheader()
    for k, item, cat, v, unit, mod, flag, src, (lo, hi), why in P:
        w.writerow(dict(factor_key=k, item=item, category=cat, value=v, unit=unit, declared_unit="", ghg_basis="CO2e",
                        modules=mod, region="Japan (provisional)", technology_or_route="", reference_year="2026",
                        data_type="provisional:" + flag, source_org="this study (provisional fill)", source_title=src[:200],
                        edition_version="2026-11-28", url=src if src.startswith("http") else (src.split(" ")[-1] if "http" in src else ""),
                        retrieved="2026-11-28", licence_name="value set by this study; cited single values with attribution",
                        licence_url="", cite_single_value="yes", research_use="yes", db_incorporation="yes", commercial_use="yes",
                        redistribution="yes", rights_class=1 if flag in ("DEF", "P3") else 3,
                        notes="reliability=%s; range [%s, %s]; %s" % (flag, lo, hi, why)))
    print(len(P), "provisional rows")


if __name__ == "__main__":
    main(sys.argv[1])
