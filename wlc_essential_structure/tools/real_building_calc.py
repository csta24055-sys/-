"""Whole-life carbon of a STATISTICALLY REPRESENTATIVE Japanese RC office, computed with the five families and REAL
public coefficients (no J-CAT, no IDEA, no fictional data). Every term carries its data tier:

  R  real value from a primary source (rights class 1 or 3 only; class 2/4/5 values are not used)
  E  estimate computed from real data by an explicit physical/statistical relation (basis + uncertainty recorded)
  A  assumption (no data found): reported in a separate total, never mixed into the R+E total
  M  missing: module not counted (NOT zero)

Usage: python3 -I tools/real_building_calc.py <agents_out_dir> <tokyo_facility_csv> <out_dir> [T=60]
"""
import csv
import json
import math
import os
import statistics
import sys
from fractions import Fraction

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import five_families as ff  # noqa: E402

SEED = 20261128


def load(out_dir):
    rows = []
    for fn in sorted(os.listdir(out_dir)):
        if fn.endswith(".csv"):
            for r in csv.DictReader(open(os.path.join(out_dir, fn), encoding="utf-8-sig")):
                r["batch"] = fn
                rows.append(r)
    return rows


class DB:
    def __init__(self, rows):
        self.rows = rows
        self.used = []

    def pick(self, batch, key, **flt):
        """the unique row of (batch, factor_key) matching all substring filters; records the use."""
        c = [r for r in self.rows if r["batch"] == batch and r["factor_key"] == key and r["value"]]
        for f, v in flt.items():
            c = [r for r in c if v.lower() in (r.get(f) or "").lower()]
        if not c:
            raise KeyError((batch, key, flt))
        r = c[0]
        if int(float(r["rights_class"] or 4)) not in (1, 3):
            raise ValueError("class %s not allowed: %s" % (r["rights_class"], key))
        self.used.append(dict(batch=batch, factor_key=key, item=r["item"], value=r["value"], unit=r["unit"], region=r["region"],
                              year=r["reference_year"], source=r["source_org"], url=r["url"], rights_class=r["rights_class"]))
        return float(r["value"]), r


def tokyo_office_stats(path):
    """per-facility values from the Tokyo reporting system FY2024 (CC BY 4.0), offices (主たる用途 '1 事務所').
    Scope 1/2 are reported only by some facilities: they are kept where present (None otherwise)."""
    rd = csv.reader(open(path, encoding="cp932"))
    h = next(rd)
    ix = {n: i for i, n in enumerate(h)}
    out = []
    for row in rd:
        try:
            use = row[ix["事業所等の報告範囲の主たる用途"]]
            A = float(row[ix["事業所等の延床面積"]])
            e = float(row[ix["エネルギー消費原単位（公開用）"]])
            ci = float(row[ix["二酸化炭素排出原単位⑤"]])
        except (ValueError, KeyError, IndexError):
            continue
        if use.startswith("1 ") and A > 0 and e > 0:
            try:   # company-level totals (t-CO2/yr) repeated on every facility of the reporting company
                s12 = (float(row[ix["SCOPE別CO2排出量 SCOPE1"]]), float(row[ix["SCOPE別CO2排出量 SCOPE2"]]))
            except ValueError:
                s12 = None
            out.append(dict(A=A, E=e, s12=s12, ci=ci))
    return out


def main(src, tokyo_csv, out, T=60.0):
    db = DB(load(src))
    rng = np.random.default_rng(SEED)
    terms = []          # dict(module, stage, dest, tier, central, low, high, family, basis)

    def term(module, stage, tier, central, low, high, family, basis):
        terms.append(dict(module=module, stage=stage, tier=tier, central=central, low=min(low, high), high=max(low, high),
                          family=family, basis=basis))

    # ---------------- quantities per m2 (MLIT 建設資材・労働力需要実態調査 R5, RC, all uses) -------------------------
    q_conc = db.pick("jp_qty.csv", "qty_rc_allbldg_ready_mix_concrete_m3_per_10m2", reference_year="2023")[0] / 10
    q_steel = db.pick("jp_qty.csv", "qty_rc_allbldg_steel_t_per_10m2", reference_year="2023")[0] / 10
    q_timber = db.pick("jp_qty.csv", "qty_rc_allbldg_timber_m3_per_10m2", reference_year="2023")[0] / 10
    q_cement = db.pick("jp_qty.csv", "qty_rc_allbldg_cement_t_per_10m2", reference_year="2023")[0] / 10
    rho_conc = 2.35   # t/m3, Boverket conversion factor recorded with its C30/37 row (2350 kg/m3)
    db.pick("se_fr.csv", "a5_waste_factor_concrete_ready_mix_c30_37")

    # ---------------- A1-A3 (F2) ----------------------------------------------------------------------------------
    opc = db.pick("jp.csv", "cement_opc_jp")[0] / 1000            # kg/kg
    bb = db.pick("jp.csv", "cement_bfs_b_jp")[0] / 1000
    agg = db.pick("us_uk.csv", "aggregates")[0] / 1000             # kgCO2e/kg (UK primary aggregates, per tonne)
    cem_content = q_cement / q_conc * 1000                         # kg cement per m3 concrete (E: ratio of two R)
    m_agg = rho_conc * 1000 - cem_content - 180                    # kg aggregate per m3 (water ~180 kg: stoichiometric order)
    conc_E = cem_content * opc + m_agg * agg
    conc_E_bb = cem_content * bb + m_agg * agg
    conc_sc = db.pick("jp.csv", "eeio_jp_ready_mix_concrete", unit="m3")[0] * 1000
    conc_bov = db.pick("se_fr.csv", "concrete_ready_mix_c30_37", data_type="typ")[0] * rho_conc * 1000 \
        if any(r["factor_key"] == "concrete_ready_mix_c30_37" and "typ" in r["data_type"].lower() for r in db.rows) else None
    conc_kbob = db.pick("de_ch.csv", "concrete_ready_mix_generic", modules="Herstellung")[0] * rho_conc * 1000
    cands = [x for x in (conc_E_bb, conc_sc, conc_bov, conc_kbob) if x]
    a13_conc = ff.f2_sum_product([(1, Fraction(q_conc), Fraction(conc_E))])
    term("A1-A3 コンクリート", "A1-A3", "E", float(a13_conc), q_conc * min(cands + [conc_E]), q_conc * max(cands + [conc_E]), "F2",
         "セメント量 %.0f kg/m3（MLIT のセメント÷生コン、全セメントを生コンに帰属）× 普通セメント %.3f（セメント協会）＋骨材 × UK 骨材係数。幅：高炉 B・サプライチェーン DB・Boverket・KBOB" % (cem_content, opc))
    st_sc = db.pick("jp.csv", "eeio_jp_crude_steel_eaf", unit="eq/t")[0]          # t/t
    st_eaf = db.pick("jp.csv", "rebar_eaf_jp")[0]
    st_bf = db.pick("jp.csv", "steel_bf_bof_jp")[0]
    st_kbob = db.pick("de_ch.csv", "rebar", modules="Herstellung")[0]
    a13_steel = ff.f2_sum_product([(1, Fraction(q_steel), Fraction(st_sc) * 1000)])
    term("A1-A3 鋼材", "A1-A3", "R", float(a13_steel), q_steel * st_eaf * 1000, q_steel * (0.7 * st_sc + 0.3 * st_bf) * 1000, "F2",
         "電炉鋼 %.3f t/t（環境省サプライチェーン DB）。幅：電炉 ≈0.5（鉄連）〜 電炉 70%%・高炉 30%% の混合（KBOB 鉄筋 %.3f は参考）" % (st_sc, st_kbob))
    tw = db.pick("jp.csv", "plywood_formwork_jp")[0]
    tw_lo = db.pick("jp.csv", "timber_sawn_kd_jp")[0]
    tw_hi = db.pick("jp.csv", "eeio_jp_plywood_glulam", unit="m3")[0] * 1000
    term("A1-A3 木材（型枠など）", "A1-A3", "R", q_timber * tw, q_timber * tw_lo, q_timber * tw_hi, "F2", "型枠用合板 %.0f kg/m3（林野庁資料）。幅：製材 80〜合板・集成材 563（サプライチェーン DB）" % tw)
    # MEP embodied (KBOB office per m2, Switzerland, class 3): foreign real values, used as an estimate for Japan
    mep = {}
    for k, flt in (("electrical_installation_per_m2", "Büro"), ("sanitary_installation_per_m2", "Büro"),
                   ("ventilation_system_per_m2", "Luftmenge"), ("heat_generator_per_m2", "Wärmeerzeuger")):
        prod = [r for r in db.rows if r["batch"] == "de_ch.csv" and r["factor_key"] == k and flt in r["notes"] and "Herstell" in r["modules"]][0]
        eol = [r for r in db.rows if r["batch"] == "de_ch.csv" and r["factor_key"] == k and flt in r["notes"] and "Entsorg" in r["modules"]][0]
        for r in (prod, eol):
            db.used.append(dict(batch="de_ch.csv", factor_key=k, item=r["item"], value=r["value"], unit=r["unit"], region=r["region"],
                                year=r["reference_year"], source=r["source_org"], url=r["url"], rights_class=r["rights_class"]))
        mep[k] = (float(prod["value"]), float(eol["value"]))
    mep_a = sum(v[0] for v in mep.values())
    mep_c = sum(v[1] for v in mep.values())
    term("A1-A3 設備（電気・衛生・空調）", "A1-A3", "E", mep_a, 0.5 * mep_a, 1.5 * mep_a, "F2",
         "KBOB（スイス）事務所の床面積当たり値の和 %.1f kg/m2。日本の値は未取得：海外の実測ベースの値を日本に当てた推定（幅 ±50%% は判断）" % mep_a)
    a13 = sum(t["central"] for t in terms)

    # ---------------- A4 (F2): factor real (UK HGV average, OGL), distances ASSUMED ---------------------------
    hgv = db.pick("us_uk.csv", "transport_truck_freight", item="Average non-refrigerated HGVs")[0]
    hgv_wtt = db.pick("us_uk.csv", "transport_truck_freight_wtt", item="Average laden")[0]
    tkm = q_conc * rho_conc * 20 + q_steel * 100 + q_timber * 0.5 * 100
    term("A4 輸送", "A4", "A", tkm * (hgv + hgv_wtt), tkm * 0.0875, tkm * 0.19947, "F2",
         "距離は仮定（生コン 20 km、鋼材・木材 100 km）。係数 UK HGV 平均 %.4f＋WTT（OGL）、幅 ADEME 連結車〜UK 単車" % hgv)

    # ---------------- A5 (F1·F2): material waste on site (Boverket waste factors, class 1) --------------------
    k_c = db.pick("se_fr.csv", "a5_waste_factor_concrete_ready_mix_c30_37")[0]
    k_s = db.pick("se_fr.csv", "a5_waste_factor_rebar")[0]
    k_t = db.pick("se_fr.csv", "a5_waste_factor_timber_sawn_softwood")[0]
    a5w = (k_c - 1) * float(a13_conc) + (k_s - 1) * float(a13_steel) + (k_t - 1) * q_timber * tw
    term("A5 施工時の材料ロス", "A5", "E", a5w, 0.5 * a5w, 1.5 * a5w, "F1·F2", "Boverket の施工廃棄係数（コンクリート %.2f、鉄筋 %.2f、木材 %.2f）× A1-A3" % (k_c, k_s, k_t))
    terms.append(dict(module="A5 現場のエネルギー", stage="A5", tier="M", central=None, low=None, high=None, family="F2", basis="日本の施工エネルギー原単位は未取得（未計上。0 ではない）"))

    # ---------------- B6 (F3 year cells): operational energy, Tokyo FY2024 offices -----------------------------
    tk = tokyo_office_stats(tokyo_csv)
    ef_grid = db.pick("jp.csv", "grid_electricity_jp", reference_year="2024")[0] * 1000      # kg/kWh
    cg = db.pick("jp.csv", "fuel_city_gas_jp_substitute")[0]                                   # t/千m3
    cg_gj = db.pick("jp.csv", "fuel_city_gas_jp", unit="GJ")[0]                                # GJ/千m3
    ef_gas = cg / cg_gj                                                                          # kg/MJ
    E_med = statistics.median(f["E"] for f in tk)
    # fuel share of primary energy, from the facilities that report Scope 1 (fuel CO2 / city-gas factor)
    companies = {f["s12"] for f in tk if f["s12"] is not None and sum(f["s12"]) > 0}
    shares = []
    for s1, s2 in companies:            # primary-energy share of fuel: (S1/ef_gas) / (S1/ef_gas + S2/ef_grid * 9.76)
        fuel_mj, el_mj = s1 / ef_gas, s2 / ef_grid * 9.76
        shares.append(fuel_mj / (fuel_mj + el_mj))
    fs_med = statistics.median(shares) if shares else 0.0
    fs_p75 = float(np.percentile(shares, 75)) if shares else 0.0

    def b6_year_of(fs, conv):
        return E_med * (1 - fs) / conv * ef_grid + E_med * fs * ef_gas
    b6_year = b6_year_of(fs_med, 9.76)
    b6_lo, b6_hi = b6_year_of(0.0, 9.76), b6_year_of(fs_p75, 8.64)
    obs = statistics.median(f["ci"] for f in tk)
    b6_vals = {9.76: b6_year, 8.64: b6_year_of(fs_med, 8.64)}
    kern = [ff.Kernel(Fraction(b6_year), s=float(k), l=1.0) for k in range(int(math.ceil(T)))]
    b6 = float(ff.f3_value(kern, T))
    term("B6 運用エネルギー", "B6", "E", b6, b6 * b6_lo / b6_year, b6 * b6_hi / b6_year, "F3（年セル）",
         "東京都の報告書制度 FY2024 事務所 %d 事業所の一次エネルギー原単位の中央値 %.0f MJ/m2·年。燃料の割合 %.2f（Scope1・2 を報告した %d 社の一次エネルギー比の中央値、燃料は都市ガスとみなす）、残りを電気の一次換算 9.76 MJ/kWh で kWh にし全国平均係数 %.3f kg/kWh。年 %.1f kg/m2（東京都の報告値の中央値 %.1f と照合）。幅：燃料 0〜p75 %.2f・換算 8.64。係数は期間中一定（将来経路は未取得）" % (len(tk), E_med, fs_med, len(shares), ef_grid, b6_year, obs, fs_p75))

    # ---------------- B7 (F3): water ------------------------------------------------------------------------
    w = db.pick("jp_qty.csv", "water_jp_govoffice_all_mean_fy2011")[0]
    ws = db.pick("jp.csv", "water_supply_jp_tokyo", reference_year="2024")[0] / 1000
    ch4 = db.pick("jp.csv", "wastewater_treatment_ch4_jp")[0] * 1000
    n2o = db.pick("jp.csv", "wastewater_treatment_n2o_conventional_jp")[0] * 1000
    gwp_ch4 = db.pick("jp.csv", "gwp_ch4", ) [0] if any(r["batch"] == "jp.csv" and r["factor_key"] == "gwp_ch4" and r["value"] for r in db.rows) else 28
    gwp_n2o = db.pick("jp.csv", "gwp_n2o")[0] if any(r["batch"] == "jp.csv" and r["factor_key"] == "gwp_n2o" and r["value"] for r in db.rows) else 265
    ww_proc = ch4 * gwp_ch4 + n2o * gwp_n2o
    ww_fr = db.pick("se_fr.csv", "wastewater_treatment")[0]
    b7_lo = w * T * (ws + ww_proc)
    b7_c = w * T * (ws + ww_fr)
    term("B7 上下水", "B7", "E", b7_c, b7_lo, b7_c * 1.2, "F3（年セル）",
         "水量 %.2f m3/m2·年（国の庁舎 FY2011）× 上水 %.3f（東京都 FY2024）＋下水 %.3f（ADEME、日本のエネルギー分は未取得）。下限は日本の処理過程の CH4・N2O だけ（%.3f）" % (w, ws, ww_fr, ww_proc))

    # ---------------- B4 + C for MEP (F3 events): replacement cycles MLIT BIMMS-N (class 1) ---------------------
    c_ac = db.pick("jp.csv", "replacement_cycle_air_conditioner")[0]
    c_el = db.pick("jp.csv", "replacement_cycle_distribution_board")[0]
    c_sa = db.pick("jp.csv", "replacement_cycle_sanitary_fixtures")[0]
    groups = [("electrical_installation_per_m2", c_el), ("sanitary_installation_per_m2", c_sa),
              ("ventilation_system_per_m2", c_ac), ("heat_generator_per_m2", c_ac)]
    b4 = Fraction(0)
    nrep = {}
    for k, c in groups:
        taus = ff.f3_events(c, T)
        n = ff.f3_count(taus, T)
        nrep[k] = n
        b4 += ff.f3_value([ff.Kernel(Fraction(mep[k][0] + mep[k][1]), g=t) for t in taus], T)
    term("B4 設備の更新", "B4", "E", float(b4), 0.5 * float(b4), 1.5 * float(b4), "F3（原子）",
         "更新周期：空調 %g・電気 %g・衛生 %g 年（官庁営繕 BIMMS-N）。1 回あたり＝KBOB の製造＋廃棄。回数 %s" % (c_ac, c_el, c_sa, nrep))
    terms.append(dict(module="B4 建築部位の更新（防水・内装・サッシ）", stage="B4", tier="M", central=None, low=None, high=None, family="F3",
                      basis="周期は取得（BIMMS-N）したが、部位の数量が統計に無い（ガラス・サッシ・石膏ボード・断熱材は調査対象外）"))
    # B3 (F3 density): repair = annual maintenance spending per m2 of office stock x 3EID 建設補修 intensity (statistical E)
    sp_off = db.pick("jp_repair.csv", "rr_orders_office_total", reference_year="FY2025")[0] * 1e8          # JPY/yr
    sp_rep = db.pick("jp_repair.csv", "rr_orders_office_purpose_repair", reference_year="FY2025")[0] * 1e8
    nm = db.pick("jp_repair.csv", "rr_orders_nonres_maintenance", reference_year="FY2025")[0]
    nr = db.pick("jp_repair.csv", "rr_orders_nonres_renovation", reference_year="FY2025")[0]
    st_corp = db.pick("jp_repair.csv", "stock_office_floor_area_corporate")[0] * 1e6
    st_loc = db.pick("jp_repair.csv", "stock_office_floor_area_public_local")[0] * 1e4
    st_nat = db.pick("jp_repair.csv", "stock_office_floor_area_public_national")[0] * 1e4
    i_rep = db.pick("jp.csv", "eeio_jp_construction_repair")[0] * 1e-3                                    # kg per JPY
    stock = st_corp + st_loc + st_nat
    share_m = nm / (nm + nr)
    b3_year = sp_off / stock * share_m * i_rep
    b3_year_hi = sp_rep / stock * i_rep
    b3 = float(ff.f3_value([ff.Kernel(Fraction(b3_year), s=0.0, l=float(int(math.ceil(T))))], T)) / 1.0
    term("B3 修繕", "B3", "E", b3, b3 / 1.2, b3_year_hi * T, "F3（密度）",
         "事務所のリフォーム・リニューアル受注高 %.0f 億円（国交省 FY2025）÷ 事務所ストック %.3g m2（法人所有＋国＋地方）× 維持・修理の割合 %.3f（非住宅）× 3EID 建設補修 %.4f kg/円 → 年 %.2f kg/m2。下限：価格水準（2020→2025）の差を 1/1.2 と仮置き。上限：工事目的が劣化・修繕の全額（年 %.2f、B4 の設備更新と一部重複）" % (sp_off / 1e8, stock, share_m, i_rep, b3_year, b3_year_hi))
    terms.append(dict(module="B5 大規模改修", stage="B5", tier="M", central=None, low=None, high=None, family="F3", basis="改修周期・割合の資料なし（未計上）"))

    # ---------------- B1 (F4 state + F3): refrigerant; units per floor area ASSUMED ---------------------------
    m0 = db.pick("jp_qty.csv", "qty_refrig_charge_building_multi_pac_kg_per_unit")[0]
    lam = db.pick("jp.csv", "refrigerant_leak_rate_vrf_building")[0]
    rec = db.pick("jp.csv", "refrigerant_recovery_rate_commercial_ac")[0] / 100
    g32 = db.pick("jp.csv", "refrigerant_gwp_r32")[0]
    g410 = db.pick("jp.csv", "refrigerant_gwp_r410a")[0]
    units_per_m2 = 1 / 300.0          # ASSUMPTION: one building-multi outdoor unit per 300 m2 (no statistic found)

    def b1(gwp):
        # F4 with top-up (annual operating leak replaced): u_k = m0 for all k; leak = lam u_k w_k(T)
        u = ff.f4_closed(1, 0, m0, 0)
        leak = ff.f3_value([ff.Kernel(Fraction(u) * Fraction(lam) * Fraction(gwp), s=float(k), l=1.0) for k in range(int(math.ceil(T)))], T)
        taus = ff.f3_events(c_ac, T)
        disp = ff.f3_value([ff.Kernel(Fraction(u) * (1 - Fraction(rec)) * Fraction(gwp), g=t) for t in taus], T) + Fraction(u) * (1 - Fraction(rec)) * Fraction(gwp)
        return float((leak + disp) * Fraction(units_per_m2))
    term("B1・C 冷媒（漏洩＋廃棄時の未回収）", "B1", "A", b1(g32), b1(g32) * 0.5, b1(g410) * 2, "F4（状態）＋F3（事象・終端）",
         "ビル用マルチ 1 台 %g kg（環境省インベントリ）、年漏洩 %.3f（日本 2016 年以降）、回収率 %.0f%%、交換 %g 年。台数 1 台/300 m2 は仮定。R32 %g（幅：R410A %g、台数 ×0.5〜×2）" % (m0, lam, rec * 100, c_ac, g32, g410))

    # ---------------- C (F2): end of life of structure ---------------------------------------------------------
    c_con = db.pick("se_fr.csv", "waste_concrete_brick_ceramic")[0] / 1000
    c_kbob_c = db.pick("de_ch.csv", "waste_concrete")[0]
    c_reb = db.pick("de_ch.csv", "waste_rebar")[0]
    m_c = q_conc * rho_conc * 1000
    m_s = q_steel * 1000
    c34 = m_c * c_con + m_s * c_reb
    term("C3・C4 処理・処分（躯体）", "C3-C4", "E", c34, m_c * min(c_con, c_kbob_c) + m_s * c_reb, m_c * max(c_con, c_kbob_c) + m_s * c_reb, "F2",
         "コンクリート %.0f kg × ADEME 26 kg/t（幅 KBOB %.4f）、鋼材 × KBOB %.4f。日本の再資源化率（コンクリート塊 %.1f%%、国交省 建設副産物実態調査 FY2018）は処理の経路の確認に使い、処理の原単位は海外値" % (m_c, c_kbob_c, c_reb, db.pick("jp_repair.csv", "eol_recycling_rate_concrete_rubble")[0]))
    term("C 設備の廃棄（最終）", "C3-C4", "E", mep_c, 0.5 * mep_c, 1.5 * mep_c, "F2", "KBOB の廃棄 %.2f kg/m2" % mep_c)
    term("C2 搬出", "C2", "A", (m_c + m_s) / 1000 * 30 * (hgv + hgv_wtt), (m_c + m_s) / 1000 * 30 * 0.0875, (m_c + m_s) / 1000 * 30 * 0.19947, "F2", "距離 30 km は仮定。係数は A4 と同じ")
    terms.append(dict(module="C1 解体作業", stage="C1", tier="M", central=None, low=None, high=None, family="F2", basis="解体のエネルギー原単位は未取得（未計上）"))

    # ---------------- F5 aggregation & destinations ------------------------------------------------------------
    DEST = {"A1-A3": "D1", "A4": "D1", "A5": "D1", "B1": "D2", "B3": "D2", "B4": "D2", "B5": "D2", "B6": "D3", "B7": "D4",
            "C1": "D5", "C2": "D5", "C3-C4": "D5"}
    for t in terms:
        t["destination"] = DEST[t["stage"]]
    num = [t for t in terms if t["central"] is not None]
    vals = {i: t["central"] for i, t in enumerate(num)}
    comp = [(t["tier"], i, 1, 1) for i, t in enumerate(num)]
    by_tier, total_all = ff.f5_aggregate(vals, comp, {"R": 1, "E": 1, "A": 1})
    re_total = float(by_tier.get("R", 0) + by_tier.get("E", 0))
    # Monte Carlo (triangular low/central/high per term, independent): 90 % interval of the R+E total and of all
    N = 20000
    samp_re = np.zeros(N)
    samp_all = np.zeros(N)
    for t in num:
        lo, c, hi = t["low"], t["central"], t["high"]
        x = c * np.ones(N) if hi - lo <= 1e-12 * max(1, abs(c)) else rng.triangular(lo, min(max(c, lo), hi), hi, N)
        samp_all += x
        if t["tier"] in ("R", "E"):
            samp_re += x
    dest = {}
    for t in num:
        dest[t["destination"]] = dest.get(t["destination"], 0) + t["central"]
    res = dict(
        building="統計上の代表：RC 造・事務所・東京（数量は全国の RC 建築の床面積当たり平均、運用は東京都の事務所の中央値）",
        study_period_years=T, unit="kgCO2e/m2（延床面積）",
        quantities_per_m2=dict(ready_mix_m3=q_conc, steel_t=q_steel, timber_m3=q_timber, cement_t=q_cement, cement_content_kg_per_m3=cem_content),
        total_R_plus_E=re_total, total_R_plus_E_p05_p95=[float(np.percentile(samp_re, 5)), float(np.percentile(samp_re, 95))],
        total_including_assumptions=float(total_all), total_incl_A_p05_p95=[float(np.percentile(samp_all, 5)), float(np.percentile(samp_all, 95))],
        share_by_tier={k: float(v) / float(total_all) for k, v in by_tier.items()},
        upfront_A1_A5=sum(t["central"] for t in num if t["destination"] == "D1"),
        destinations=dest, b6_per_year=b6_year, b6_per_year_conv864=b6_vals[8.64], tokyo_reported_median_co2=obs, n_tokyo_offices=len(tk), tokyo_median_primary_MJ_per_m2=E_med, fuel_share_median=fs_med, n_scope1=len(shares),
        missing_modules=[t["module"] + "：" + t["basis"] for t in terms if t["tier"] == "M"],
        terms=terms, coefficients_used=db.used,
        notes=["J-CAT・IDEA・模擬データは使っていない。区分 2・4・5 の値は使っていない。",
               "海外の値（KBOB・Boverket・ADEME・UK）は地域補正をせず推定（E）として使い、地域を記録した。",
               "数量の統計にガラス・サッシ・石膏ボード・断熱材が無いため、それらの製造と更新は未計上。合計は下限側に偏る。"])
    os.makedirs(out, exist_ok=True)
    # coefficient-level ESTIMATES derived here (real inputs + explicit relation), written in the agents' schema
    cols = ["factor_key", "item", "category", "value", "unit", "declared_unit", "ghg_basis", "modules", "region", "technology_or_route",
            "reference_year", "data_type", "source_org", "source_title", "edition_version", "url", "retrieved", "licence_name",
            "licence_url", "cite_single_value", "research_use", "db_incorporation", "commercial_use", "redistribution", "rights_class", "notes"]
    base = dict(declared_unit="", ghg_basis="CO2e (inputs' basis)", technology_or_route="", data_type="estimate (derived from real data)",
                source_org="this study (wlc_essential_structure)", source_title="tools/real_building_calc.py", edition_version="2026-11-28",
                url="", retrieved="2026-11-28", licence_name="derived; inherits the most restrictive input class", licence_url="",
                cite_single_value="yes", research_use="yes", db_incorporation="unknown", commercial_use="unknown", redistribution="unknown")
    est = [dict(base, factor_key="mat_concrete_ready_mix", item="レディーミクストコンクリート（日本・推定）", category="material", value="%.1f" % conc_E,
                unit="kgCO2e/m3", modules="A1-A3", region="Japan", reference_year="FY2023 quantities, FY2024 cement LCI", rights_class="3",
                notes="cement content %.1f kg/m3 = MLIT cement/ready-mix ratio (R5, RC) x OPC %.4f (セメント協会) + aggregate %.0f kg x UK aggregate factor; range BB cement %.1f .. %.1f" % (cem_content, opc, m_agg, conc_E_bb, max(cands + [conc_E]))),
           dict(base, factor_key="eui_co2_tokyo_office", item="事務所の運用 CO2（東京・推定、年）", category="energy", value="%.2f" % b6_year,
                unit="kgCO2e/m2·year", modules="B6", region="Japan Tokyo", reference_year="FY2024", rights_class="1",
                notes="median primary energy %.0f MJ/m2 (n=%d) x fuel share %.3f (n=%d companies) / 9.76 MJ/kWh x grid %.3f; Tokyo-reported median %.1f" % (E_med, len(tk), fs_med, len(shares), ef_grid, obs)),
           dict(base, factor_key="wt_wastewater_jp_process_only", item="下水処理（日本、処理過程の CH4・N2O のみ：下限）", category="water", value="%.4f" % ww_proc,
                unit="kgCO2e/m3", modules="B7", region="Japan", reference_year="current inventory", rights_class="1",
                notes="CH4 %.2e t/m3 x %g + N2O %.2e t/m3 x %g; energy part not obtained (lower bound only)" % (ch4 / 1000, gwp_ch4, n2o / 1000, gwp_n2o))]
    with open(os.path.join(out, "estimates.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(est)
    json.dump(res, open(os.path.join(out, "representative_rc_office.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k not in ("terms", "coefficients_used")}, ensure_ascii=False, indent=1))
    for t in terms:
        print("%-28s %-6s %-2s %10s  [%s, %s]" % (t["module"], t["stage"], t["tier"], "—" if t["central"] is None else "%.1f" % t["central"],
                                              "" if t["low"] is None else "%.1f" % t["low"], "" if t["high"] is None else "%.1f" % t["high"]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], *(float(x) for x in sys.argv[4:5]))
