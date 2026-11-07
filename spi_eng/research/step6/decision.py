#!/usr/bin/env python3
"""STEP6：SPI英語の推定(STEP4) × INPEXの評価制度(STEP5) を統合し、受検戦略 A〜E を比較する。

【実データ由来】η1(GS当日の英語)の分布 = step4.model（口コミの題数データで更新）
               評価制度の仮説の確率   = step5/hypotheses.json（公式FAQ・体験談・主張の統合）
【仮定(識別不能) — 条件付きシミュレーション】
  r     : ENGの信頼性 0.8 / 0.9
  g2,g3 : 再受検の効果(JAL, INPEX) {なし, 小(+0.1,+0.15), 中(+0.2,+0.3), 疲労(-0.1,-0.1)}  ※SPI英語の実測なし
  各仮説の具体化: H1=英語不使用 / H2=下位5%・10%で足切り / H3=下位20%・35%で足切り / H4=総合点の重み5%・10%
  応募者集団: 基礎能力の平均 μ∈{0, 0.5}、適性検査段階の通過率 π∈{0.3, 0.5}
  E の手応え: JALの得点を誤差SD 0.5 / 1.0 で知覚し、中央値未満なら INPEX で再受検
  基礎能力: 本人申告の上位25%以内(順位で一様)
制度上の制約：送信できるのは最新の結果だけ。最高点を選ぶことはできない。
"""
import itertools, json, math, os, sys
import numpy as np
from scipy.stats import norm
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(H, "../step4")); import model as m4
rng = np.random.default_rng(20261108)
N = 40000
STRATS = ["A", "B", "C", "D", "E"]

def eta1_samples(key, n):
    s, slope, rho = key
    k3, nu, _ = m4.load_counts(); prior = m4.fusion_prior()
    ph = m4.posterior_hyp(k3, nu, s, prior)
    un = {h: m4.eta_unnorm(h, slope, rho) for h in m4.HYP}
    w = {h: ph[h] * np.trapezoid(un[h], m4.G) for h in m4.HYP}; z = sum(w.values())
    dens = sum(w[h] / z * un[h] / np.trapezoid(un[h], m4.G) for h in m4.HYP)
    p = dens / dens.sum()
    return rng.choice(m4.G, size=n, p=p) + rng.uniform(-0.0025, 0.0025, n)

def basic_samples(n):
    return norm.ppf(1 - rng.uniform(0.0, 0.25, n))

def systems():
    yield "H1", "none", 0
    for q in (5, 10): yield "H2", "floor", q
    for q in (20, 35): yield "H3", "floor", q
    for w in (0.05, 0.10): yield "H4", "w", w

_TH = {}
_POOL = np.random.default_rng(777)
_ZA = _POOL.normal(size=400000); _ZE = _POOL.normal(size=400000)

def threshold(kind, par, pi, mu, rho):
    """応募者集団の合格ライン。全戦略で共有する(共通乱数法)。乱数は固定の母集団標本を使う。"""
    key = (kind, par, pi, mu, rho)
    if key not in _TH:
        zb_a = mu + _ZA; ze_a = rho * _ZA + math.sqrt(1 - rho ** 2) * _ZE
        if kind == "w":
            _TH[key] = (np.quantile((1 - par) * zb_a + par * ze_a, 1 - pi), None)
        else:
            floor = norm.ppf(par / 100) if kind == "floor" else -np.inf
            ok = ze_a >= floor
            _TH[key] = (np.quantile(zb_a[ok], max(0.0, 1 - pi / ok.mean())), floor)
    return _TH[key]

def pass_prob(zb, ze, kind, par, pi, mu, rho):
    c, floor = threshold(kind, par, pi, mu, rho)
    if kind == "w":
        return float(((1 - par) * zb + par * ze >= c).mean())
    return float(((zb >= c) & (ze >= floor)).mean())

def run(hyp_weights=None):
    hj = json.load(open(os.path.join(H, "../step5/hypotheses.json"), encoding="utf-8"))
    hw = hyp_weights or hj["sensitivity"]["r_scale=1.0|rho=0.9"]
    GAINS = {"なし": (0, 0), "小": (.10, .15), "中": (.20, .30), "疲労": (-.10, -.10)}
    rows = []
    for (s, slope, rho), r, (gn, (g2, g3)), sig in itertools.product(
            [(1, 1.0, 0.0), (2, 1.0, 0.3), (4, 0.5, 0.5)], [0.8, 0.9], GAINS.items(), [0.5, 1.0]):
        e1 = eta1_samples((s, slope, rho), N); zb = basic_samples(N)
        m0 = rho * 1.27                                   # 事前平均(基礎能力上位25%と相関ρ)
        e_1 = rng.normal((1 - r) * (e1 - m0), math.sqrt(r * (1 - r)))
        theta = e1 - e_1
        s2 = theta + g2 + rng.normal(0, math.sqrt(1 - r), N)
        s3 = theta + g3 + rng.normal(0, math.sqrt(1 - r), N)
        feel = s2 + rng.normal(0, sig, N)
        e_choice = np.where(feel < np.median(feel), s3, s2)
        out = {"A": e1, "B": s2, "C": s3, "D": e1, "E": e_choice}
        for pi, mu in itertools.product([0.3, 0.5], [0.0, 0.5]):
            U = {k: 0.0 for k in STRATS}; Uh = {}
            for h, kind, par in systems():
                nh = {"H1": 1, "H2": 2, "H3": 2, "H4": 2}[h]          # 仮説内の具体化は等重み
                for k, v in out.items():
                    p = pass_prob(zb, v, kind, par, pi, mu, rho)
                    U[k] += hw[h] / nh * p
                    Uh.setdefault(h, {}).setdefault(k, 0.0); Uh[h][k] += p / nh
            top = {k: 100 * (1 - norm.cdf(v)) for k, v in out.items()}
            rows.append({"scenario": f"s={s}|slope={slope}|rho={rho}|r={r}|gain={gn}|sig={sig}|pi={pi}|mu={mu}",
                         "integ": {1: "保守", 2: "標準", 4: "楽観"}[s], "EU": U, "U_by_h": Uh,
                         "rank_median": {k: float(np.median(t)) for k, t in top.items()},
                         "p_improve": {k: float((out[k] > e1 + 1e-9).mean()) for k in STRATS},
                         "p_worse": {k: float((out[k] < e1 - 1e-9).mean()) for k in STRATS},
                         "downside90": {k: float(np.percentile(t, 90)) for k, t in top.items()},
                         "p_bottom20": {k: float((t >= 80).mean()) for k, t in top.items()}})
    return rows, hw

def summarize(rows):
    res = {}
    for integ in ["保守", "標準", "楽観", "全体"]:
        sub = [r for r in rows if integ == "全体" or r["integ"] == integ]
        reg = {k: [max(r["EU"].values()) - r["EU"][k] for r in sub] for k in STRATS}
        res[integ] = {k: {"期待効用(平均)": float(np.mean([r["EU"][k] for r in sub])),
                          "期待後悔(平均)": float(np.mean(reg[k])), "最大後悔": float(np.max(reg[k])),
                          "最良になる割合": float(np.mean([r["EU"][k] >= max(r["EU"].values()) - 1e-6 for r in sub])),
                          "英語順位の中央値": float(np.median([r["rank_median"][k] for r in sub])),
                          "第1回より改善": float(np.mean([r["p_improve"][k] for r in sub])),
                          "第1回より悪化": float(np.mean([r["p_worse"][k] for r in sub])),
                          "下位20%の確率": float(np.mean([r["p_bottom20"][k] for r in sub])),
                          "下振れ(上位%の90%点)": float(np.mean([r["downside90"][k] for r in sub]))} for k in STRATS}
        pair = {}
        for x, y in [("A", "B"), ("B", "A"), ("C", "B"), ("E", "B"), ("A", "C"), ("A", "E")]:
            d = [r["EU"][x] - r["EU"][y] for r in sub]
            pair[f"{x}>{y}"] = {"有利なシナリオの割合": float(np.mean([v > 1e-4 for v in d])), "差の範囲(ポイント)": [100 * min(d), 100 * max(d)]}
        res[integ]["_pairwise"] = pair
    return res

if __name__ == "__main__":
    rows, hw = run()
    summ = summarize(rows)
    json.dump({"hyp_weights_used": hw, "summary": summ, "n_scenarios": len(rows)}, open(os.path.join(H, "results.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(rows, open(os.path.join(H, "scenarios.json"), "w", encoding="utf-8"), ensure_ascii=False)
    for integ in ["保守", "標準", "楽観", "全体"]:
        print("\n##", integ)
        for k in STRATS:
            v = summ[integ][k]; print(" ", k, {a: round(b, 4) if isinstance(b, float) else b for a, b in v.items()})
        for k, v in summ[integ]["_pairwise"].items(): print("   ", k, {a: (round(b, 3) if isinstance(b, float) else [round(x, 2) for x in b]) for a, b in v.items()})
