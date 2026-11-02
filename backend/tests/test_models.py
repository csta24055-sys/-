"""計算式の検算テスト。期待値は Box 資料の本文記載値（出典 ID をコメントに記載）または手計算。"""
import math

import numpy as np
import pytest

from aqros import analysis as A
from aqros import models as M


# --- 並列流路モデル: 2026年度中間梗概 (Box 2525808527679) の本文記載値の再現 ---

def test_ep_equation_roundtrip():
    for q in (100, 300, 750):
        assert M.ep_q_from_dp(M.ep_dp_from_q(q)) == pytest.approx(q, rel=1e-9)


def test_ep_dp_at_750_within_measured_range():
    # 図4 の横軸は 0〜18 Pa。式(2) で 750 m³/h → 約15 Pa（手計算: (750/78.611)^(1/0.828)=15.24）
    assert M.ep_dp_from_q(750) == pytest.approx(15.24, abs=0.05)


def test_five_units_zero_bypass_cadr_matches_paper():
    # 本文: 「5台運転では…バイパス開口率0%で最大値の約740m³/h」
    r = M.solve_bypass(0.0, 5, "中")
    assert r.q_total == pytest.approx(950)
    assert r.cadr == pytest.approx(740, rel=0.03)


def test_full_bypass_power_about_4w_per_unit():
    # 本文: 「バイパス開口率100%で最小（約4W/台）」
    for n in (5, 10, 15, 20):
        r = M.solve_bypass(1.0, n, "中", ep_law="quadratic_ext")
        assert 3.5 <= r.power_per_unit <= 6.5


def test_fit_law_does_not_reproduce_reported_dp():
    # 本文: 「多台数運転では、バイパス開口率0%で95〜350Pa程度」
    # 式(2) を全域適用すると 10台 1900 m³/h → 46.8 Pa しか生じない（= 本文と不一致, FINDINGS F-2026-03）
    assert M.ep_dp_from_q(1900, "fit") == pytest.approx(46.8, abs=0.2)
    # 750 m³/h 超で二乗則外挿すると 97 Pa / 390 Pa となり本文の 95〜350 Pa と整合
    assert M.ep_dp_from_q(1900, "quadratic_ext") == pytest.approx(97.4, abs=1)
    assert M.ep_dp_from_q(3800, "quadratic_ext") == pytest.approx(389.6, abs=3)


def test_bypass_relieves_pressure_to_reported_band():
    # 本文: 「バイパス開口率を25〜50%とすることで前後差圧が13〜47Pa程度に緩和」
    dps = [M.solve_bypass(r, n, "中", ep_law="quadratic_ext").dp for n, r in ((10, 0.25), (15, 0.5), (20, 0.5))]
    assert all(10 <= d <= 50 for d in dps)


def test_bypass_monotonic_power():
    res = M.bypass_sweep(10, "中", steps=11, ep_law="quadratic_ext")
    powers = [r.power_total for r in res if r.within_fan_limit]
    assert all(a >= b - 1e-9 for a, b in zip(powers, powers[1:]))


def test_mass_conservation_parallel_flow():
    r = M.solve_bypass(0.4, 12, "強", ep_law="quadratic_ext")
    assert r.q_ep + r.q_bp == pytest.approx(r.q_total, rel=1e-4)


def test_extrapolation_warning():
    r = M.solve_bypass(0.0, 10, "中")
    assert any("実測範囲" in w for w in r.warnings)


# --- 単室マスバランス ---

def test_steady_state_analytic_vs_numeric():
    p = M.ZoneParams(volume=250, q_oa=125, eta_oa_filter=0.45, q_recirc=950, eta_ep=0.8,
                     deposition=0.2, c_out=10, generation=2000, c0=30)
    ts = M.zone_time_series(p, hours=24, dt_h=1 / 60)
    assert ts[-1][1] == pytest.approx(M.zone_steady_state(p), rel=1e-3)
    # 解析解との比較（t=1h）
    num = [c for t, c in ts if abs(t - 1.0) < 1e-6][0]
    assert num == pytest.approx(M.zone_concentration(p, 1.0), rel=5e-3)


def test_io_ratio_without_cleaner_equals_filter_penetration():
    # 循環除塵・沈着・侵入なし → I/O = 1 − η_OA（2025年度 条件② の回帰係数解釈と一致）
    p = M.ZoneParams(q_recirc=0, deposition=0, eta_oa_filter=0.45, q_inf=0)
    assert M.zone_io_ratio(p) == pytest.approx(0.55)


def test_io_ratio_with_cleaner_hand_calc():
    # 手計算: S/C_out = 125·0.55 = 68.75; 除去 = 125 + 0.85·950 = 932.5 → I/O = 0.0737
    p = M.ZoneParams(volume=250, q_oa=125, eta_oa_filter=0.45, q_recirc=950, eta_ep=0.85, deposition=0)
    assert M.zone_io_ratio(p) == pytest.approx(68.75 / 932.5, rel=1e-9)


def test_jem_pulldown_time():
    # 換気1回/h・清浄機なし → 12% までの時間 = ln(1/0.12) = 2.12 h
    p = M.ZoneParams(volume=100, q_oa=100, q_recirc=0, deposition=0)
    assert M.time_to_fraction(p, 0.12) == pytest.approx(math.log(1 / 0.12))


# --- 沈着・換算 ---

def test_settling_velocity_10um():
    # 10 μm, ρ=1000 kg/m³ の Stokes 沈降速度 ≈ 3.06e-3 m/s（Hinds, Aerosol Technology 表 3.1 ≈ 3.06e-3）
    assert M.settling_velocity(10.0) == pytest.approx(3.06e-3, rel=0.03)


def test_deposition_increases_with_size():
    b = [M.deposition_coefficient(d) for d in (0.5, 1, 5, 10, 30)]
    assert b == sorted(b)


def test_count_to_mass():
    # 1 μm, 1000 kg/m³ の粒子 1e6 個/m³ → 質量 5.236e-16 kg × 1e6 = 5.236e-10 kg/m³ = 0.5236 μg/m³
    assert M.count_to_mass(1e6, 1.0) == pytest.approx(0.5236, rel=1e-3)


def test_incense_generation_2020_order_of_magnitude():
    # 2020年度梗概: 平均 0.00695 mg/s（BOX 6.48 m³, 約1020 s）。cpm 換算 K=1.3e-3 mg/m³/cpm で
    # 必要な平均 cpm は 0.00695·1020/(1.3e-3·6.48) ≈ 841 cpm（逆算・整合性確認）
    k = M.incense_generation(841, 6.48, 1020)
    assert k == pytest.approx(0.00695, rel=0.01)


# --- 解析関数 ---

def test_regression_through_origin_recovers_slope():
    rng = np.random.default_rng(0)
    x = rng.uniform(1, 30, 500)
    y = 0.55 * x + rng.normal(0, 0.5, 500)
    r = A.regression_through_origin(x, y)
    assert r["k"] == pytest.approx(0.55, abs=0.01)
    assert r["ci_low"] < 0.55 < r["ci_high"]


def test_power_law_fit_recovers_eq2():
    dp = np.linspace(0.5, 17, 30)
    q = 78.611 * dp**0.828
    r = A.power_law_fit(dp, q)
    assert r["a"] == pytest.approx(78.611, rel=1e-6)
    assert r["b"] == pytest.approx(0.828, rel=1e-6)


def test_removal_efficiency():
    up = np.array([1000.0, 2000, 4000])
    dn = np.array([50.0, 100, 200])
    r = A.removal_efficiency(up, dn)
    assert r["eta_mean_of_ratios"] == pytest.approx(95.0)


def test_fit_decay():
    t = np.arange(0, 1800, 60.0)
    c = 5 + 100 * np.exp(-1.3e-4 * 10 * t)
    r = A.fit_decay(t, c, c_bg=5)
    assert r["beta_per_s"] == pytest.approx(1.3e-3, rel=1e-6)


def test_quality_report_flags_outlier_and_missing():
    import pandas as pd
    df = pd.DataFrame({"v": [1, 1.1, 0.9, 1.05, None, 50, 1.0, 0.95]})
    q = A.quality_report(df, ["v"])[0]
    assert q["missing"] == 1
    assert q["outliers"] == 1


# --- 多室モデル（SHASE 2021 その40 の回路網） ---

def test_shase2021_network_is_balanced():
    for s in ("弱", "強"):
        v, f = M.shase2021_network(s)
        bal = M.network_imbalance(v, f)
        assert max(abs(x) for x in bal.values()) < 1.0  # m³/h（表の丸め誤差のみ）


def test_shase2021_box_decay_58pct():
    # 論文: 減衰率 D=0.00015 /s は「1時間後に初期濃度の58.3%」
    assert (1 - 0.00015) ** 3600 == pytest.approx(0.583, abs=0.001)
    assert M.decay_rate_to_beta(0.00015) == pytest.approx(0.540, abs=0.001)


def test_multizone_uniform_steady_equals_outdoor_without_losses():
    v, f = M.shase2021_network("弱")
    r = M.multizone_simulate(v, f, hours=48, c_out=7.0, c0=0.0, record_every_s=3600)  # 時定数≈5.2 h
    for z, s in r["series"].items():
        assert s[-1] == pytest.approx(7.0, rel=0.02), z


def test_multizone_mass_conservation_closed_box():
    # 換気・沈着ゼロ・内部循環のみ → 総質量保存
    v = {"A": 10.0, "B": 30.0}
    f = [("A", "B", 100.0), ("B", "A", 100.0)]
    r = M.multizone_simulate(v, f, hours=2, c0={"A": 10.0, "B": 0.0}, record_every_s=600)
    m0 = 10 * 10.0
    m1 = sum(v[z] * r["series"][z][-1] for z in v)
    assert m1 == pytest.approx(m0, rel=1e-9)
    assert r["series"]["A"][-1] == pytest.approx(2.5, rel=1e-3)


def test_multizone_ep_lowers_all_rooms():
    v, f = M.shase2021_network("弱")
    kw = dict(hours=1.0, c_out=0.0, c0=0.0, sources={"LDK": 0.0144 * 3600}, source_hours=(0, 1020 / 3600),
              beta=M.decay_rate_to_beta(0.0003), record_every_s=60)
    off = M.multizone_simulate(v, f, **kw)
    on = M.multizone_simulate(v, f, ep_edge=M.SHASE2021_EP_EDGE, eta_ep=0.9, **kw)
    for z in ("洋室(大)", "2階廊下・レターン", "洗面所"):
        assert on["series"][z][-1] < 0.5 * off["series"][z][-1]
