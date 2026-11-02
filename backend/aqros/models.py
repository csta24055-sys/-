"""Air Quality Research OS — 物理モデル群

すべての関数は SI 系ではなく、研究室資料で用いられている実務単位系を採用する。
  風量 Q        : m³/h
  濃度 C        : μg/m³ （質量濃度）または 個/m³（個数濃度）— 関数内では区別しない
  発塵率 G      : μg/h （濃度単位 × m³/h）
  室容積 V      : m³
  沈着係数 β    : 1/h （研究室資料の 1/s 値は ×3600 で換算）
  差圧 ΔP       : Pa

各モデルの根拠（Box 資料 ID）は MODEL_REGISTRY に記載し、アプリ画面に表示する。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Callable

RHO_AIR = 1.2  # kg/m³（2026年度中間梗概 式(4)の設定値）
G = 9.81
MU_AIR = 1.81e-5  # Pa·s（20℃空気の粘性係数, 一般値）
MEAN_FREE_PATH = 0.066e-6  # m（20℃, 1 atm）

# ---------------------------------------------------------------------------
# 1. 単室完全混合マスバランス（田中俊六ほか『最新建築環境工学』の換気式を拡張）
# ---------------------------------------------------------------------------


@dataclass
class ZoneParams:
    volume: float = 250.0  # m³ 住宅全体の気積（仮定値）
    q_oa: float = 125.0  # m³/h 機械換気外気量（0.5回/h 相当, 仮定値）
    eta_oa_filter: float = 0.45  # 外気フィルタ捕集率（2025年度 条件② 回帰係数0.55 → 1-0.55）
    q_inf: float = 0.0  # m³/h 隙間侵入量（フィルタを通らない外気）
    penetration_inf: float = 1.0  # 隙間通過時の粒子透過率 P
    q_recirc: float = 950.0  # m³/h 循環風量（空気清浄装置を通る全風量）
    bypass_ratio: float = 0.0  # 電気集塵機を通らない割合 0..1（流量比; 開口率ではない）
    eta_ep: float = 0.85  # 電気集塵機 1 パス捕集率
    deposition: float = 0.2  # 1/h 室内表面への沈着損失係数 β
    c_out: float = 7.0  # μg/m³ 外気濃度（2024年度 全国中央値）
    generation: float = 0.0  # μg/h 室内発塵率
    c0: float = 0.0  # μg/m³ 初期濃度


def zone_cadr(p: ZoneParams) -> float:
    """実効除塵風量 CADR = η·Q_EP （m³/h）。2026年度中間梗概の定義と同じ。"""
    q_ep = p.q_recirc * (1.0 - p.bypass_ratio)
    return p.eta_ep * q_ep


def zone_loss_rate(p: ZoneParams) -> float:
    """濃度減衰に寄与する総除去率 λ（1/h）"""
    return (p.q_oa + p.q_inf + zone_cadr(p)) / p.volume + p.deposition


def zone_source(p: ZoneParams) -> float:
    """室内への粒子供給速度 S（μg/h）"""
    return (
        p.q_oa * (1.0 - p.eta_oa_filter) * p.c_out
        + p.q_inf * p.penetration_inf * p.c_out
        + p.generation
    )


def zone_steady_state(p: ZoneParams) -> float:
    """定常濃度 C∞ = S / (V·λ)"""
    return zone_source(p) / (p.volume * zone_loss_rate(p))


def zone_io_ratio(p: ZoneParams) -> float:
    """発塵ゼロ時の定常 I/O 比（2025年度の『回帰係数』に対応する理論量）"""
    if p.c_out <= 0:
        return float("nan")
    q = ZoneParams(**{**asdict(p), "generation": 0.0})
    return zone_steady_state(q) / p.c_out


def zone_concentration(p: ZoneParams, t_hours: float) -> float:
    """解析解 C(t) = C∞ + (C0 − C∞)·exp(−λt)"""
    lam = zone_loss_rate(p)
    css = zone_steady_state(p)
    return css + (p.c0 - css) * math.exp(-lam * t_hours)


def zone_time_series(
    p: ZoneParams,
    hours: float,
    dt_h: float = 1 / 60,
    c_out_fn: Callable[[float], float] | None = None,
    gen_fn: Callable[[float], float] | None = None,
) -> list[tuple[float, float]]:
    """指数積分法による時系列（外気濃度・発塵率を時間関数で与えられる）。
    入力の時間変化を追うため dt は λ·dt < 0.2 となるよう自動で細分化する。"""
    lam = zone_loss_rate(p)
    sub = max(1, math.ceil(lam * dt_h / 0.2))
    h = dt_h / sub
    c = p.c0
    t = 0.0
    out = [(0.0, c)]
    n_steps = int(round(hours / dt_h))
    for _ in range(n_steps):
        for _ in range(sub):
            co = c_out_fn(t) if c_out_fn else p.c_out
            g = gen_fn(t) if gen_fn else p.generation
            s = p.q_oa * (1 - p.eta_oa_filter) * co + p.q_inf * p.penetration_inf * co + g
            # 区間内で入力一定とみなした厳密積分（指数積分法）。オイラー法より安定・高精度
            c_eq = s / (p.volume * lam)
            c = c_eq + (c - c_eq) * math.exp(-lam * h)
            t += h
        out.append((round(t, 10), c))
    return out


def time_to_fraction(p: ZoneParams, fraction: float) -> float:
    """発塵・外気ゼロ条件で初期濃度の fraction 倍まで下がる時間（h）。
    JEM1467 の適用床面積の考え方（1.25→0.15 mg/m³ = 12%）を参照。"""
    lam = zone_loss_rate(p)
    return math.log(1.0 / fraction) / lam


# ---------------------------------------------------------------------------
# 2. 電気集塵機 + バイパス 並列流路モデル（2026年度中間梗概 式(2)〜(4)）
# ---------------------------------------------------------------------------

# 式(2) 実測近似: Q = 78.611·ΔP^0.828（R²=0.9909, 測定範囲 Q=100〜750 m³/h, ΔP≈0〜17 Pa）
EP_COEF = 78.611
EP_EXP = 0.828
EP_Q_RANGE = (100.0, 750.0)

# 図3 の読み取り（粒径別集塵効率 η の風量依存）— 端点のみ本文に記載。中間は線形補間の【仮定】
EP_EFFICIENCY_ENDPOINTS = {
    # 粒径帯: (η@100 m³/h, η@750 m³/h)
    "0.3-0.5": (0.95, 0.82),
    "0.5-1.0": (0.96, 0.86),
    "1.0-2.0": (0.97, 0.89),
    "2.0-5.0": (0.98, 0.91),
    "5.0-": (0.99, 0.92),
}

# 送風機（風量一定制御 FAN, YUCACO 専用品）の実測特性（本文記載値）
FAN_SETTINGS = {
    # 設定: (一定風量 m³/h, 一定制御限界静圧 Pa, 0Pa時電力 W, 限界時電力 W)
    "弱": (130.0, 90.0, 2.5, 12.0),
    "中": (190.0, 80.0, 4.0, 13.5),
    "強": (230.0, 70.0, 5.0, 15.0),
}
FAN_SHUTOFF_FACTOR = 1.6  # 【仮定】限界静圧の1.6倍で風量ゼロになる直線降下（本文は定性的記述のみ）


EP_LAWS = ("fit", "quadratic_ext")
_DP_AT_QMAX = (EP_Q_RANGE[1] / EP_COEF) ** (1.0 / EP_EXP)  # ≈15.2 Pa


def ep_dp_from_q(q: float, law: str = "fit") -> float:
    """集塵機差圧 ΔP(Q)。
    law="fit"           : 式(2) の逆関数 ΔP = (Q/78.611)^(1/0.828) を全域に適用
    law="quadratic_ext" : 実測上限 750 m³/h までは式(2)、それ以上は ΔP ∝ Q² で外挿（乱流抵抗則の【仮定】）。
                          中間梗概本文の「0%で95〜350Pa」はこちらで再現される（FINDINGS F-2026-03 参照）。
    """
    if q <= 0:
        return 0.0
    if law == "quadratic_ext" and q > EP_Q_RANGE[1]:
        return _DP_AT_QMAX * (q / EP_Q_RANGE[1]) ** 2
    return (q / EP_COEF) ** (1.0 / EP_EXP)


def ep_q_from_dp(dp: float, law: str = "fit") -> float:
    dp = max(dp, 0.0)
    if law == "quadratic_ext" and dp > _DP_AT_QMAX:
        return EP_Q_RANGE[1] * math.sqrt(dp / _DP_AT_QMAX)
    return EP_COEF * dp**EP_EXP


def ep_efficiency(q: float, size_bin: str = "0.3-0.5") -> float:
    """風量 Q における集塵効率 η（0..1）。端点間は線形、範囲外は線形外挿し [0.3, 0.995] に制限。"""
    e100, e750 = EP_EFFICIENCY_ENDPOINTS[size_bin]
    slope = (e750 - e100) / (EP_Q_RANGE[1] - EP_Q_RANGE[0])
    eta = e100 + slope * (q - EP_Q_RANGE[0])
    return min(0.995, max(0.3, eta))


def bypass_q_from_dp(dp: float, opening_ratio: float, area_full: float = 0.25, alpha: float = 0.65) -> float:
    """式(4) Q_BP = 3600·α·A·√(2ΔP/ρ)  [m³/h]"""
    a = area_full * opening_ratio
    return 3600.0 * alpha * a * math.sqrt(2.0 * max(dp, 0.0) / RHO_AIR)


def fan_flow(dp: float, setting: str, n_units: int) -> float:
    """送風機群の総風量。限界静圧までは一定、それ以降は直線降下（【仮定】）。"""
    q_set, p_lim, _, _ = FAN_SETTINGS[setting]
    if dp <= p_lim:
        return q_set * n_units
    p_shut = p_lim * FAN_SHUTOFF_FACTOR
    frac = max(0.0, 1.0 - (dp - p_lim) / (p_shut - p_lim))
    return q_set * n_units * frac


def fan_power_per_unit(dp: float, setting: str) -> float:
    """図6 の傾向を直線近似（0Pa→限界静圧で W0→Wlim）。限界超過後は風量比で減少（本文の定性記述に整合）。"""
    q_set, p_lim, w0, wlim = FAN_SETTINGS[setting]
    if dp <= p_lim:
        return w0 + (wlim - w0) * dp / p_lim
    return wlim * fan_flow(dp, setting, 1) / q_set * 0.9 + w0 * 0.1


@dataclass
class BypassResult:
    opening_ratio: float
    dp: float
    q_total: float
    q_ep: float
    q_bp: float
    eta: float
    cadr: float
    power_total: float
    power_per_unit: float
    within_fan_limit: bool
    warnings: list[str] = field(default_factory=list)


def solve_bypass(
    opening_ratio: float,
    n_units: int = 5,
    setting: str = "中",
    size_bin: str = "0.3-0.5",
    area_full: float = 0.25,
    alpha: float = 0.65,
    extra_resistance: float = 0.0,
    ep_law: str = "fit",
) -> BypassResult:
    """送風機 P-Q 特性と（集塵機 ∥ バイパス）の合成抵抗が釣り合う静圧 ΔP を二分法で求める。

    extra_resistance: 並列部以外の系統抵抗係数 k（ΔP_extra = k·Q_total²; Pa/(m³/h)²）。
    中間梗概に記載がないため既定 0（感度分析用）。
    """
    def residual(dp: float) -> float:
        # 並列部の差圧 dp_par = dp − k Q² を内側で解くのは複雑なため、
        # 系統静圧 dp を与え、並列部差圧は固定点で近似する
        q_fan = fan_flow(dp, setting, n_units)
        dp_par = max(dp - extra_resistance * q_fan**2, 0.0)
        q_sys = ep_q_from_dp(dp_par, ep_law) + bypass_q_from_dp(dp_par, opening_ratio, area_full, alpha)
        return q_fan - q_sys

    lo, hi = 0.0, FAN_SETTINGS[setting][1] * FAN_SHUTOFF_FACTOR
    if residual(hi) > 0:  # 締切静圧でも流れる（理論上起こらない）
        hi *= 10
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if residual(mid) > 0:
            lo = mid
        else:
            hi = mid
    dp = 0.5 * (lo + hi)
    q_total = fan_flow(dp, setting, n_units)
    dp_par = max(dp - extra_resistance * q_total**2, 0.0)
    q_ep = ep_q_from_dp(dp_par, ep_law)
    q_bp = bypass_q_from_dp(dp_par, opening_ratio, area_full, alpha)
    eta = ep_efficiency(q_ep, size_bin)
    p_unit = fan_power_per_unit(dp, setting)
    warnings: list[str] = []
    p_lim = FAN_SETTINGS[setting][1]
    if q_ep > EP_Q_RANGE[1] * 1.05 or (q_ep < EP_Q_RANGE[0] * 0.95 and q_ep > 1):
        warnings.append(
            f"集塵機通過風量 {q_ep:.0f} m³/h は実測範囲 100〜750 m³/h 外（式(2)・η の外挿）"
        )
    if dp_par > 17.5:
        warnings.append(f"集塵機差圧 {dp_par:.1f} Pa は式(2)の実測範囲（≈0〜17 Pa）外")
    if dp > p_lim:
        warnings.append(f"静圧 {dp:.1f} Pa が風量一定制御限界 {p_lim:.0f} Pa を超過（送風機特性は仮定外挿）")
    return BypassResult(
        opening_ratio=opening_ratio,
        dp=dp,
        q_total=q_total,
        q_ep=q_ep,
        q_bp=q_bp,
        eta=eta,
        cadr=eta * q_ep,
        power_total=p_unit * n_units,
        power_per_unit=p_unit,
        within_fan_limit=dp <= p_lim,
        warnings=warnings,
    )


def bypass_sweep(n_units: int = 5, setting: str = "中", steps: int = 21, **kw) -> list[BypassResult]:
    return [solve_bypass(i / (steps - 1), n_units, setting, **kw) for i in range(steps)]


# ---------------------------------------------------------------------------
# 3. 沈着（重力沈降）: β = U/H, U = 2·Cc·(ρp−ρ)·g·r²/(9μ)  — 2021年度(浮遊)梗概 式(2)(4)
# ---------------------------------------------------------------------------


def cunningham(d_m: float) -> float:
    kn = 2 * MEAN_FREE_PATH / d_m
    return 1 + kn * (1.257 + 0.4 * math.exp(-1.1 / kn))


def settling_velocity(d_um: float, rho_p: float = 1000.0) -> float:
    """終末沈降速度 U [m/s]（Stokes 域）"""
    d = d_um * 1e-6
    r = d / 2
    return 2 * cunningham(d) * (rho_p - RHO_AIR) * G * r**2 / (9 * MU_AIR)


def deposition_coefficient(d_um: float, height_m: float = 2.4, rho_p: float = 1000.0) -> float:
    """沈着係数 β [1/s]（重力沈降のみ。拡散・乱流沈着は含まない）"""
    return settling_velocity(d_um, rho_p) / height_m


# ---------------------------------------------------------------------------
# 4. 個数濃度 → 質量濃度（2023年度梗概 式(1): Cm = 4/3·π·r³·N·ρ）
# ---------------------------------------------------------------------------


def count_to_mass(n_per_m3: float, d_um: float, rho_kg_m3: float = 1000.0) -> float:
    """個数濃度 [個/m³] → 質量濃度 [μg/m³]（球形・単一粒径を仮定）"""
    r = d_um * 1e-6 / 2
    mass_kg = 4 / 3 * math.pi * r**3 * rho_kg_m3
    return n_per_m3 * mass_kg * 1e9


# ---------------------------------------------------------------------------
# 5. 線香発生量（2020年度梗概 式(1): k = c·K·V/t）
# ---------------------------------------------------------------------------


def incense_generation(c_cpm: float, volume_m3: float, burn_time_s: float, k_factor: float = 1.3e-3) -> float:
    """発生量 k [mg/s]。K は質量濃度変換係数 [mg/m³/cpm]。
    注: 2020年度梗概は K=1.3 と記載、2018年度梗概は 1.3×10⁻³ と記載（単位表記の不一致）。"""
    return c_cpm * k_factor * volume_m3 / burn_time_s


# ---------------------------------------------------------------------------
# 6. モデル台帳（画面表示用）
# ---------------------------------------------------------------------------

MODEL_REGISTRY = [
    {
        "id": "zone_mass_balance",
        "name": "単室完全混合マスバランス",
        "equation": "V·dC/dt = Q_OA(1−η_OA)C_out + Q_inf·P·C_out + G − (Q_OA + Q_inf + η_EP·Q_EP)C − β·V·C",
        "units": "V[m³], Q[m³/h], C[μg/m³], G[μg/h], β[1/h]",
        "basis": "2018・2020年度梗概の換気式 V·dp=Q(p0−p)dt+k·dt を外気・集塵・沈着項で拡張【分析】",
        "sources": ["1516271027930", "1516272435953"],
        "validity": "住宅全体を1室とみなす瞬時一様拡散。室間濃度差・気流分布は表現しない（2020/2021年度に一様拡散仮定の誤差が報告）。",
    },
    {
        "id": "bypass_parallel",
        "name": "電気集塵機∥バイパス 並列流路モデル",
        "equation": "N·q_fan(ΔP) = 78.611·ΔP^0.828 + 3600·α·A·√(2ΔP/ρ),  CADR = η(Q_EP)·Q_EP",
        "units": "Q[m³/h], ΔP[Pa], A[m²], ρ[kg/m³]",
        "basis": "2026年度中間梗概 式(2)〜(4)【当事者の主張】を再実装【計算結果】",
        "sources": ["2525808527679"],
        "validity": "式(2)は Q=100〜750 m³/h・ΔP≈0〜17 Pa の単体実測。送風機の限界超過後特性と η の中間値は読み取り・仮定。",
    },
    {
        "id": "deposition",
        "name": "重力沈降による沈着係数",
        "equation": "β = U/H,  U = 2·Cc·(ρp−ρ)·g·r²/(9μ)",
        "units": "β[1/s], U[m/s], H[m], r[m]",
        "basis": "2021年度(浮遊)梗概 式(2)(4)",
        "sources": ["1516299546149"],
        "validity": "球形粒子・静穏空気。実住宅の階間・床下では BOX 比 2〜11 倍の β が報告（ダクト・表面積効果）。",
    },
    {
        "id": "decay_fit",
        "name": "発生・減衰の同定式",
        "equation": "C(t) = C0·e^(−βt) + M/(βV)·(1 − e^(−βt))",
        "units": "C[個/m³ or mg/m³], M[個/s or mg/s], V[m³]",
        "basis": "2021年度(浮遊)梗概 式(3)",
        "sources": ["1516299546149"],
        "validity": "閉鎖空間・一様濃度。換気がある場合 β は換気率を含む見かけ値。",
    },
    {
        "id": "count_to_mass",
        "name": "個数→質量濃度換算",
        "equation": "Cm = (4/3)·π·r³·N·ρ",
        "units": "Cm[mg/m³], N[個/m³], r[m], ρ[mg/m³]",
        "basis": "2023年度梗概 式(1)",
        "sources": ["1516369441999"],
        "validity": "球形・粒径帯代表径・密度仮定（コットンリンター）に強く依存。粒径帯幅の扱いで1桁程度変わり得る。",
    },
    {
        "id": "annual_regression",
        "name": "回帰係数による年間室内濃度予測",
        "equation": "C_in(t) = k·C_out(t)  （1時間平均, 原点通過回帰）",
        "units": "C[μg/m³]",
        "basis": "2025年度最終梗概 7・8章",
        "sources": ["2166150611661"],
        "validity": "室内発塵を無視。測定期間（秋季・数日〜2か月）の k を通年に適用する仮定。",
    },
]
