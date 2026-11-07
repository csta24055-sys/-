#!/usr/bin/env python3
"""第11部：基礎能力が上位25%以内という条件の下での、英語の順位推定・再受検の時系列モデル・
INPEX適性検査段階の仮想選考モデル・A〜E戦略の比較。

区分（出力のどの数値にも当てはまる）：
- 実測：本人の受検内容(長文3題・各3問など)、口コミ集計(data/*.csv)、INPEX公式FAQの文言。
- 本人の申告条件：基礎能力が上位25%以内（数値的な裏付けは見つかっていない）。
- 仮定：較正(s,f)、長文仮説(τ,σ)、相関ρ、信頼性r、練習効果g、応募者集団、評価制度、通過率π。
"""
import itertools, json, os
import numpy as np
from scipy.stats import norm
from model import G
from model2 import post_one, CALIB, PROPENSITY, B0, LAM

HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(1110)
N = 80_000
DX = G[1] - G[0]
TOP = lambda z: 100 * (1 - norm.cdf(z))

# ---------------- 1. 基礎能力（G1：上位25%以内） ----------------
BANDS = [(0, 5), (5, 10), (10, 15), (15, 20), (20, 25)]
G1 = {  # 帯ごとの重み
    "G1-集団": [0.2] * 5,               # 「上位25%以内」以外の情報がないとき、集団の事前分布から自動的に出る分布（各帯20%）
    "G1-上位寄り": [0.30, 0.25, 0.20, 0.15, 0.10],   # 本人の「さらに上位の可能性が十分ある」を反映（重みの形は仮定）
    "G1-境界寄り": [0.10, 0.15, 0.20, 0.25, 0.30],   # 最も保守的（上位25%付近に集中）
}


def sample_basic(weights, n):
    b = rng.choice(5, size=n, p=weights)
    lo = np.array([BANDS[i][0] for i in b]); hi = np.array([BANDS[i][1] for i in b])
    pct = rng.uniform(lo, hi)
    return norm.ppf(1 - pct / 100)   # z_B


# ---------------- 2. 英語の尤度（model2 の較正モデル × 長文仮説） ----------------
PASS_H = {"N0": None, "K1": (0.0, 1.0), "K2": (0.0, 0.5)}


def likelihood(cal, ph):
    ps = [post_one(CALIB[cal], pr, b0, lam) for pr, b0, lam in
          itertools.product(PROPENSITY.values(), B0.values(), LAM.values())]
    L = np.mean(ps, 0) / norm.pdf(G)          # post_one は N(0,1) の事前分布を掛けたもの → 割って尤度に戻す
    if ph:
        L = L * norm.cdf((G - ph[0]) / ph[1])
    return L / L.max()


INTEG = {   # 証拠をどう統合するかの3通り
    "保守": dict(cal="B 弱い情報", ph="N0", rho=0.0, prior_shift=-0.3, g1="G1-境界寄り"),
    "標準": dict(cal="B 弱い情報", ph="K1", rho=0.3, prior_shift=0.0, g1="G1-集団"),
    "楽観": dict(cal="A 手応えほぼ無情報", ph="K2", rho=0.5, prior_shift=0.0, g1="G1-上位寄り"),
}


def joint_sample(cfg, n):
    """z_B と η1 を同時にサンプリングする。η の事前分布は N(ρ z_B + shift, 1−ρ²)。"""
    L = likelihood(cfg["cal"], PASS_H[cfg["ph"]])
    zb = sample_basic(G1[cfg["g1"]], n)
    qs = np.quantile(zb, np.linspace(0, 1, 41))
    idx = np.clip(np.searchsorted(qs, zb) - 1, 0, 39)
    eta = np.empty(n)
    rho = cfg["rho"]
    for k in range(40):
        m = idx == k
        if not m.any():
            continue
        zc = zb[m].mean()
        post = L * norm.pdf(G, rho * zc + cfg["prior_shift"], np.sqrt(1 - rho ** 2))
        post /= post.sum()
        eta[m] = rng.choice(G, size=m.sum(), p=post) + rng.uniform(-DX / 2, DX / 2, m.sum())
    return zb, eta


def summarize_eta(eta):
    top = TOP(eta)
    # 最頻領域：幅20ポイントの窓のうち、確率が最大のもの
    best = max(((lo, float(((top >= lo) & (top < lo + 20)).mean())) for lo in range(0, 81)), key=lambda x: x[1])
    q = lambda p: float(np.percentile(top, p))
    return {"最頻領域(幅20pt)": f"上位{best[0]}〜{best[0]+20}%（確率{best[1]:.0%}）",
            "中央値(上位%)": q(50), "平均(上位%)": float(top.mean()),
            "50%区間": [q(25), q(75)], "80%区間": [q(10), q(90)], "95%区間": [q(2.5), q(97.5)],
            "下位20%": float((top >= 80).mean()), "下位10%": float((top >= 90).mean()),
            "平均以上": float((top <= 50).mean()), "上位65%以内": float((top <= 65).mean())}


# ---------------- 3. 再受検の時系列モデル ----------------
R = {   # (g2, g3, 第1回の当たり外れの補正 k)
    "R1 練習効果なし": (0.0, 0.0, 0.0),
    "R2 弱い練習効果": (0.10, 0.15, 0.0),
    "R3 中程度": (0.20, 0.30, 0.0),
    "R4 疲労・緊張": (-0.10, -0.10, 0.0),
    "R5 第1回は上振れ": (0.10, 0.15, +0.3),
    "R6 第1回は下振れ": (0.10, 0.15, -0.3),
}


def sequential(eta1, prior_mean, r, g2, g3, k, sig_signal):
    """S1=η1（GS当日）。θ=η1−e1、e1|η1 ~ N((1−r)(η1−m)+k, r(1−r))（事前平均 m へ縮小＋R5/R6の補正）。"""
    n = len(eta1)
    e1 = rng.normal((1 - r) * (eta1 - prior_mean) + k, np.sqrt(r * (1 - r)), n)
    theta = eta1 - e1
    s2 = theta + g2 + rng.normal(0, np.sqrt(1 - r), n)
    s3 = theta + g3 + rng.normal(0, np.sqrt(1 - r), n)
    signal = s2 + rng.normal(0, sig_signal, n)          # JAL後の本人の手応え（得点をどれくらい反映するかは仮定）
    e_rule = np.where(signal < np.median(signal), s3, s2)   # E：手応えが下半分ならINPEXで受け直す
    return {"A": eta1, "B": s2, "C": s3, "D": eta1, "E": e_rule}, (eta1, s2, s3)


# ---------------- 4. INPEX適性検査段階の仮想モデル ----------------
SYSTEMS = {"英語は不使用": ("none", 0), "英語 下位10%で足切り": ("floor", 10), "英語 下位20%で足切り": ("floor", 20),
           "英語 下位35%で足切り": ("floor", 35), "英語 重み5%": ("w", 0.05), "英語 重み10%": ("w", 0.10)}
PI = [0.3, 0.5]          # 適性検査段階の通過率（仮定。INPEXの実際の値は非公開）
MU_APP = [0.0, 0.5]      # 応募者集団の基礎能力の平均（SPI受検者全体との差。仮定）


def stage_pass(zb_user, ze_user, system, pi, mu, rho, n_app=200_000):
    kind, par = SYSTEMS[system]
    zb_a = rng.normal(mu, 1, n_app)
    ze_a = rho * zb_a + np.sqrt(1 - rho ** 2) * rng.normal(0, 1, n_app)
    if kind == "w":
        tot_a = (1 - par) * zb_a + par * ze_a
        c = np.quantile(tot_a, 1 - pi)
        return ((1 - par) * zb_user + par * ze_user >= c)
    floor = norm.ppf(par / 100) if kind == "floor" else -np.inf
    ok_a = ze_a >= floor
    c = np.quantile(zb_a[ok_a], 1 - pi / ok_a.mean()) if pi < ok_a.mean() else -np.inf
    return (zb_user >= c) & (ze_user >= floor)


if __name__ == "__main__":
    out = {"english_posterior": {}, "retake": {}, "strategy": {}, "matrix33": {}}
    samples = {}
    for name, cfg in INTEG.items():
        zb, eta = joint_sample(cfg, N)
        samples[name] = (zb, eta)
        out["english_posterior"][name] = summarize_eta(eta)
    # 感度分析：G2（基礎能力の順位を点で与えた場合）、標準モデルの他の条件は固定
    g2 = {}
    for p in [10, 25, 35, 50]:
        cfg = dict(INTEG["標準"]); L = likelihood(cfg["cal"], PASS_H[cfg["ph"]])
        zc = norm.ppf(1 - p / 100)
        post = L * norm.pdf(G, cfg["rho"] * zc, np.sqrt(1 - cfg["rho"] ** 2)); post /= post.sum()
        e = rng.choice(G, size=N, p=post)
        g2[f"基礎能力 上位{p}%"] = {k: v for k, v in summarize_eta(e).items() if k in ("中央値(上位%)", "平均以上", "下位20%")}
    out["G2_sensitivity"] = g2

    # 再受検と戦略
    rows = []
    for name, cfg in INTEG.items():
        zb, eta = samples[name]
        m = cfg["rho"] * zb.mean() + cfg["prior_shift"]
        for rn, (g2_, g3_, k) in R.items():
            for sig in [0.5, 1.0]:
                strat, (s1, s2, s3) = sequential(eta, m, 0.85, g2_, g3_, k, sig)
                key = f"{name}|{rn}|手応え精度σ={sig}"
                out["retake"][key] = {
                    "P(S2>S1)": float((s2 > s1).mean()), "P(S2<S1)": float((s2 < s1).mean()),
                    "P(S3>S2)": float((s3 > s2).mean()), "P(S3>S1)": float((s3 > s1).mean()),
                    "P(S2が下位10%)": float((TOP(s2) >= 90).mean()), "P(S3が下位10%)": float((TOP(s3) >= 90).mean()),
                    "P(S1が下位10%)": float((TOP(s1) >= 90).mean())}
                for sysn in SYSTEMS:
                    for pi in PI:
                        for mu in MU_APP:
                            U = {s: float(stage_pass(zb, v, sysn, pi, mu, cfg["rho"]).mean()) for s, v in strat.items()}
                            rows.append(dict(integ=name, R=rn, sig=sig, system=sysn, pi=pi, mu=mu, U=U,
                                             rank={s: float(TOP(v).mean()) for s, v in strat.items()},
                                             better=({s: float((v > s1).mean()) for s, v in strat.items()}),
                                             worse=({s: float((v < s1).mean()) for s, v in strat.items()}),
                                             p50={s: float((TOP(v) <= 50).mean()) for s, v in strat.items()},
                                             p65={s: float((TOP(v) <= 65).mean()) for s, v in strat.items()},
                                             b20={s: float((TOP(v) >= 80).mean()) for s, v in strat.items()},
                                             q90={s: float(np.percentile(TOP(v), 90)) for s, v in strat.items()}))
    S = ["A", "B", "C", "D", "E"]
    for name in INTEG:
        sub = [r for r in rows if r["integ"] == name]
        reg = {s: [] for s in S}
        for r in sub:
            best = max(r["U"].values())
            for s in S:
                reg[s].append(best - r["U"][s])
        agg = lambda f, s: float(np.mean([f(r)[s] for r in sub]))
        out["strategy"][name] = {s: {
            "推定英語順位の中央値(平均的な値)": float(np.median([r["rank"][s] for r in sub])),
            "上位50%以内": agg(lambda r: r["p50"], s), "上位65%以内": agg(lambda r: r["p65"], s),
            "下位20%": agg(lambda r: r["b20"], s),
            "第1回より改善": agg(lambda r: r["better"], s), "第1回より悪化": agg(lambda r: r["worse"], s),
            "適性検査段階の通過確率(仮想制度の平均)": agg(lambda r: r["U"], s),
            "下振れ(上位%の90パーセンタイル)": agg(lambda r: r["q90"], s),
            "期待後悔(平均)": float(np.mean(reg[s])), "最大後悔": float(np.max(reg[s])),
            "最良になるシナリオの割合": float(np.mean([r["U"][s] >= max(r["U"].values()) - 1e-9 for r in sub]))}
            for s in S}
        pair = {}
        for x, y in [("A", "B"), ("B", "A"), ("C", "B"), ("E", "B"), ("E", "C"), ("A", "C")]:
            pair[f"{x}>{y}"] = {
                "英語の得点(平均順位)": float(np.mean([r["rank"][x] < r["rank"][y] - 0.05 for r in sub])),
                "下位20%回避": float(np.mean([r["b20"][x] < r["b20"][y] - 1e-4 for r in sub])),
                "適性検査段階の通過": float(np.mean([r["U"][x] > r["U"][y] + 1e-4 for r in sub])),
                "通過確率の差(範囲)": [float(min(r["U"][x] - r["U"][y] for r in sub)), float(max(r["U"][x] - r["U"][y] for r in sub))]}
        out["strategy"][name]["_pairwise"] = pair
        # 評価制度ごとに分けた後悔
        out["strategy"][name]["_by_system"] = {
            sysn: {s: float(np.mean([max(r["U"].values()) - r["U"][s] for r in sub if r["system"] == sysn])) for s in S}
            for sysn in SYSTEMS}

    # 33. 基礎能力（上位25%以内）× 英語の順位を固定した場合の通過確率（標準モデルの基礎能力分布）
    zb = samples["標準"][0]
    for p in [20, 35, 50, 65, 75, 85, 95]:
        ze = np.full(len(zb), norm.ppf(1 - p / 100))
        out["matrix33"][f"英語 上位{p}%"] = {f"{sysn}|π={pi}|μ={mu}": float(stage_pass(zb, ze, sysn, pi, mu, 0.3).mean())
                                           for sysn in SYSTEMS for pi in PI for mu in MU_APP}
    json.dump(out, open(os.path.join(HERE, "results3.json"), "w"), ensure_ascii=False, indent=1, default=float)
    print("done")
