"""Independent coefficient database: merge the research agents' CSVs, map every row to the demand ledger, classify by
rights, split public/private, and compute the coverage indicators.

Usage: python3 -I tools/build_factor_db.py <agents_out_dir> <demand.csv> <out_dir> [estimates.csv]

Public repository rule (the repository is public): numeric values are written to the PUBLIC files only for rights
class 1 (embeddable, open licence) and class 3 (individual value cited with attribution from a primary document).
Class 2 (research only), 4 (terms not confirmed) and 5 (not usable) keep their metadata in public, their value only in
<out_dir>/private/ (git-ignored).
"""
import collections
import csv
import glob
import json
import os
import re
import sys

COLS = ["factor_key", "item", "category", "value", "unit", "declared_unit", "ghg_basis", "modules", "region",
        "technology_or_route", "reference_year", "data_type", "source_org", "source_title", "edition_version", "url",
        "retrieved", "licence_name", "licence_url", "cite_single_value", "research_use", "db_incorporation",
        "commercial_use", "redistribution", "rights_class", "notes"]

# demand_key -> regex on (factor_key + ' ' + item) (lower case). Order matters: first match wins.
SYN = [
    ("mat_concrete_ready_mix", r"concrete(?!.*(crush|block|carbonat|uptake|recycl|landfill|waste))|ready.?mix|生コン|コンクリート(?!.*破砕)"),
    ("mat_cement", r"cement|clinker|セメント"),
    ("mat_rebar", r"rebar|reinforc|鉄筋|棒鋼"),
    ("mat_steel_sheet_galvanised", r"galvan|steel.?sheet|coil|めっき"),
    ("mat_structural_steel", r"struct.*steel|steel.*section|steel.*(plate|beam|profile)|heavy.?plate|^steel|形鋼|鋼材"),
    ("mat_timber_clt", r"\bclt\b|cross.?lam|brettsperr"),
    ("mat_timber_glulam", r"glulam|glue.?lam|brettschicht|集成材"),
    ("mat_plywood", r"plywood|osb|合板"),
    ("mat_timber_sawn", r"sawn|softwood|lumber|timber|wood(?!.*(wool|fibre|incin|landfill|waste|densit|carbon))|製材|木材"),
    ("mat_glass_igu", r"insulat\w* glass|igu|glazing unit|double.?glaz|triple|複層"),
    ("mat_glass_float", r"glass(?!.*(wool|fib))|ガラス(?!ウール)"),
    ("mat_aluminium_window", r"(alu\w*).*(window|frame)|サッシ"),
    ("mat_aluminium", r"alumin|アルミ"),
    ("mat_gypsum_board", r"gypsum|plasterboard|石膏"),
    ("mat_glass_wool", r"glass.?wool|グラスウール"),
    ("mat_mineral_wool", r"mineral.?wool|stone.?wool|rock.?wool|ロックウール"),
    ("mat_xps", r"\bxps\b"),
    ("mat_eps", r"\beps\b|expanded polystyrene"),
    ("mat_pur_pir", r"\bpur\b|\bpir\b|polyuret|ウレタン"),
    ("mat_pvc_pipe", r"pvc|塩ビ"),
    ("mat_pe_pipe", r"\bpe\b|polyethyl|hdpe"),
    ("mat_paint", r"paint|coating|塗料"),
    ("mat_copper", r"copper|銅"),
    ("mat_ceramic_tile", r"ceramic|tile|タイル"),
    ("mat_brick", r"brick|れんが"),
    ("mat_aggregate", r"aggregate|gravel|sand|骨材"),
    ("mat_mortar", r"mortar|screed|モルタル"),
    ("mat_bitumen_membrane", r"bitumen|membrane|防水"),
    ("rf_gwp_r1234ze", r"1234ze"), ("rf_gwp_r1234yf", r"1234yf"), ("rf_gwp_r410a", r"410a"), ("rf_gwp_r404a", r"404a"),
    ("rf_gwp_r407c", r"407c"), ("rf_gwp_r134a", r"134a"), ("rf_gwp_r513a", r"513a"), ("rf_gwp_r454b", r"454b"),
    ("rf_gwp_r32", r"r.?32\b|hfc.?32"), ("rf_gwp_r22", r"r.?22\b|hcfc.?22"), ("rf_gwp_r290", r"r.?290|propane(?!.*fuel)"),
    ("rf_gwp_r744", r"r.?744"), ("rf_gwp_r717", r"r.?717|ammonia"),
    ("rf_leak_rate", r"leak|漏え?洩|漏えい"), ("rf_recovery_rate", r"recover|回収"), ("rf_replacement_loss", r"servic\w* loss|replacement.?loss|installation emission"),
    ("rf_charge_per_kw", r"charge"),
    ("eq_chiller", r"chiller|チラー"), ("eq_heat_pump_vrf", r"heat.?pump|vrf|split|air.?condition|エアコン|パッケージ"),
    ("eq_ahu", r"air.?handl|\bahu\b|ventilation unit|lüftung"), ("eq_boiler", r"boiler|ボイラ"), ("eq_water_heater", r"water heater|給湯"),
    ("eq_transformer", r"transformer|変圧"), ("eq_switchboard", r"switch|配電盤"), ("eq_cable", r"cable|ケーブル|電線"),
    ("eq_luminaire", r"lumin|light|led|照明"), ("eq_lift", r"lift|elevator|昇降"), ("eq_sanitary_ware", r"\bwc\b|toilet|wash.?basin|sanitary ware|衛生陶器"),
    ("eq_pv_panel", r"photovolt|\bpv\b|solar"), ("eq_mep_per_m2", r"per.?m2|installation per|設備一式|building services"),
    ("tr_truck", r"truck|lorry|hgv|road freight|トラック"), ("tr_rail", r"rail|鉄道"), ("tr_ship", r"ship|vessel|sea freight|船"),
    ("tr_load_factor", r"load factor|積載率"),
    ("en_electricity_grid_jp", r"electric|grid|電力|電気事業"), ("en_city_gas", r"natural gas|city gas|都市ガス|gaz naturel"),
    ("en_lpg", r"lpg|liquefied petroleum|propane"), ("en_kerosene", r"kerosene|burning oil|灯油"), ("en_heavy_oil_a", r"heavy.?oil|fuel oil|heating oil|重油"),
    ("en_diesel", r"diesel|gas.?oil|軽油"), ("en_gasoline", r"gasoline|petrol|ガソリン"), ("en_district_heat", r"district|steam|heat network|fernwärme|地域熱"),
    ("en_heat_content", r"calorific|heating value|発熱量"),
    ("wt_water_supply", r"water supply|drinking|potable|上水|水道(?!.*下)"), ("wt_wastewater", r"waste.?water|sewage|water treatment|下水"),
    ("wa_concrete_crushing", r"crush|recycl\w* concrete|破砕"), ("wa_incineration_wood", r"incin\w*.*wood|wood.*(incin|combust)"),
    ("wa_incineration_plastic", r"incin\w*.*plast|plast\w*.*(incin|combust)"), ("wa_landfill_inert", r"inert|安定型"),
    ("wa_landfill_mixed", r"landfill|埋立"), ("wa_construction_waste_mixed", r"construction.*waste|c&d|建設.*廃棄"),
    ("wa_metal_recycling", r"metal.*recycl|scrap"), ("wa_sorting", r"sort"), ("wt_municipal_waste", r"municipal|household waste|一般廃棄物"),
    ("wa_waste_rate", r"waste rate|wastage|spill|端材"), ("dm_demolition", r"demoli|解体"),
    ("st_carbon_fraction", r"carbon fraction|炭素含有"), ("st_timber_density", r"density.*(wood|timber|softwood)|basic density|全乾"),
    ("st_carbonation", r"carbonat|uptake|炭酸化"), ("gwp_ch4", r"\bch4\b|methane"), ("gwp_n2o", r"n2o|nitrous"), ("gwp_co2", r"^gwp_co2|carbon dioxide"),
    ("eeio_construction", r"eeio|useeio|3eid|per usd|per million yen|産業連関|/usd|/円"), ("eui_per_m2", r"kwh/m2|eui|energy use intensity|原単位.*m2"),
    ("ren_cycle", r"renovat|refurb|改修"),
]
LIFE = [("life_structure", r"struct|frame|躯体|foundation"), ("life_roof", r"roof|屋根|防水"), ("life_facade", r"facade|cladding|external wall|外壁"),
        ("life_window", r"window|door|建具|窓"), ("life_interior_finish", r"finish|floor cover|ceiling|partition|内装|paint"),
        ("life_hvac", r"hvac|heat|cool|ventil|chiller|boiler|空調|冷暖房|air"), ("life_electrical", r"electr|light|電気"),
        ("life_sanitary", r"sanit|plumb|water|給排水|衛生"), ("life_lift", r"lift|elevat|昇降"), ("life_pv", r"photovolt|\bpv\b|solar")]


def demand_of(row, demand_keys):
    fk = (row["factor_key"] or "").lower()
    if fk in demand_keys:
        return fk
    text = (fk + " " + (row["item"] or "")).lower()
    cat = (row["category"] or "").lower()
    if cat in ("lifetime", "repair") or re.search(r"service.?life|lifespan|nutzungsdauer|耐用|周期|repair|maint|修繕", text):
        pref = "repair_" if (cat == "repair" or re.search(r"repair|maint|修繕", text)) else "life_"
        if re.search(r"refrigerant|冷媒", text):
            return "rf_device_life"
        for k, rx in LIFE:
            if re.search(rx, text):
                return pref + k.split("_", 1)[1]
        return pref + "structure" if re.search(r"build|建物", text) else None
    if cat == "quantity" or cat == "energy_use" or cat == "water_use":
        return "PROJECT:" + cat
    for k, rx in SYN:
        if re.search(rx, text):
            if k.startswith("en_") and cat in ("material", "equipment"):
                continue
            return k
    return None


def num(v):
    try:
        x = float(str(v).replace(",", ""))
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def main(src, demand_csv, out, est=None):
    demand = list(csv.DictReader(open(demand_csv, encoding="utf-8")))
    dkeys = {d["demand_key"] for d in demand}
    rows, bad = [], []
    files = sorted(glob.glob(os.path.join(src, "*.csv")))
    if est:
        files.append(est)
    for fp in files:
        with open(fp, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                r = {c: (r.get(c) or "").strip() for c in COLS}
                r["batch"] = os.path.basename(fp)
                r["value_num"] = num(r["value"])
                try:
                    r["rights_class"] = int(float(r["rights_class"]))
                except ValueError:
                    r["rights_class"] = 4
                r["demand_key"] = demand_of(r, dkeys) or ""
                is_est = "estimate" in r["data_type"].lower() or r["batch"] == os.path.basename(est or "")
                r["kind"] = ("ESTIMATE" if is_est else "REAL") if r["value_num"] is not None else "NOT_OBTAINED"
                rows.append(r)
    os.makedirs(os.path.join(out, "private"), exist_ok=True)
    with open(os.path.join(out, "private", ".gitignore"), "w") as f:
        f.write("*\n!.gitignore\n")
    pub_cols = ["demand_key", "kind"] + COLS + ["batch"]
    with open(os.path.join(out, "factor_db_public.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=pub_cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            rr = dict(r)
            if r["rights_class"] not in (1, 3):
                rr["value"] = "（非公開：区分%d）" % r["rights_class"] if r["value_num"] is not None else ""
            w.writerow(rr)
    with open(os.path.join(out, "private", "factor_db_all.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=pub_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    # ---- indicators per demand row ------------------------------------------------------------------------
    by = collections.defaultdict(list)
    for r in rows:
        if r["demand_key"] in dkeys:
            by[r["demand_key"]].append(r)
    status = []
    for d in demand:
        rs = [r for r in by.get(d["demand_key"], []) if r["value_num"] is not None]
        real = [r for r in rs if r["kind"] == "REAL"]
        estm = [r for r in rs if r["kind"] == "ESTIMATE"]
        tried = by.get(d["demand_key"], [])
        st = ("REAL" if real else "ESTIMATE" if estm else "NOT_OBTAINED")
        status.append(dict(demand_key=d["demand_key"], item=d["item"], category=d["category"], status=st,
                           n_real=len(real), n_estimate=len(estm), n_sources=len({r["source_org"] for r in rs}),
                           n_regions=len({r["region"] for r in rs}), best_class=min([r["rights_class"] for r in rs], default=""),
                           class1=sum(r["rights_class"] == 1 for r in real), class2=sum(r["rights_class"] == 2 for r in real),
                           class3=sum(r["rights_class"] == 3 for r in real), class4=sum(r["rights_class"] == 4 for r in real),
                           class5=sum(r["rights_class"] == 5 for r in real), japan_value=any(r["region"].lower().startswith(("jp", "japan", "日本")) for r in rs),
                           tried_sources=";".join(sorted({r["source_org"] for r in tried}))[:300],
                           not_obtained_reasons=" | ".join(sorted({r["notes"][:120] for r in tried if r["value_num"] is None}))[:600]))
    with open(os.path.join(out, "coverage_by_demand.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(status[0]))
        w.writeheader()
        w.writerows(status)
    n = len(status)
    ind = dict(
        demand_rows=n, rows_total=len(rows), rows_with_value=sum(r["value_num"] is not None for r in rows),
        rows_unmapped=sum(1 for r in rows if not r["demand_key"]),
        rows_by_class={k: sum(1 for r in rows if r["value_num"] is not None and r["rights_class"] == k) for k in range(1, 6)},
        real_data_rate=sum(s["status"] == "REAL" for s in status) / n,
        commercial_usable_rate=sum(1 for s in status if s["class1"] > 0) / n,
        estimate_only_rate=sum(s["status"] == "ESTIMATE" for s in status) / n,
        not_obtained_rate=sum(s["status"] == "NOT_OBTAINED" for s in status) / n,
        japan_specific_rate=sum(1 for s in status if s["japan_value"]) / n,
        multi_source_rate=sum(1 for s in status if s["n_sources"] >= 2) / n,
        by_category={c: dict(collections.Counter(s["status"] for s in status if s["category"] == c)) for c in sorted({s["category"] for s in status})},
    )
    json.dump(ind, open(os.path.join(out, "coverage_indicators.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(ind, ensure_ascii=False, indent=1))
    unm = collections.Counter((r["category"], r["factor_key"]) for r in rows if not r["demand_key"])
    print("UNMAPPED sample", unm.most_common(25))


if __name__ == "__main__":
    main(*sys.argv[1:5])
