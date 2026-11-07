#!/usr/bin/env python3
"""SPI英語（11/7 GS受検）の順位推定と、INPEXへの提出戦略比較。

!!! 重要 !!!
SPI英語の得点分布・項目難易度・識別力・信頼性係数・長文の題数と得点の関係は、
いずれも公開された実測データがない。本コードのパラメータは「全て仮定」であり、
単一の値を当てにせず、幅広いシナリオの感度分析として結果を見ること。

尺度: η = 受検当日の実力（受検者集団で標準化, N(0,1)）。
      θ = 本来の実力（日ごとにブレない部分）, η = θ + e, Var(θ)=r, Var(e)=1-r（r=信頼性）。
"""
import itertools, json, os
import numpy as np
from scipy.stats import norm

HERE = os.path.dirname(os.path.abspath(__file__))
G = np.linspace(-4, 4, 1601)          # η のグリッド
rng = np.random.default_rng(20261107)


# ---------- IRT（3PL）と「手応え」観測モデル ----------
def p3pl(eta, a, b, c):
    return c + (1 - c) / (1 + np.exp(-1.7 * a * (eta - b)))


def poisson_binomial(ps):
    """ps: (n_items, n_grid) → 確信あり回答数 k の分布 (n_items+1, n_grid)"""
    dist = np.zeros((ps.shape[0] + 1, ps.shape[1])); dist[0] = 1
    for p in ps:
        dist[1:] = dist[1:] * (1 - p) + dist[:-1] * p
        dist[0] *= (1 - p)
    return dist


def lik_confident(bs, a, c, lam, cal, kset):
    """bs: 項目難易度（非適応時の値）。lam: 適応度（0=固定難易度, 1=完全に実力に合わせて出題）。
    cal=(s,f): P(確信|正答)=s, P(確信|誤答)=f。kset: 観測された「確信あり」の個数の集合。"""
    s, f = cal
    b_eff = lam * G[None, :] + (1 - lam) * np.asarray(bs)[:, None]
    pc = p3pl(G[None, :], a, b_eff, c)
    pconf = pc * s + (1 - pc) * f
    dist = poisson_binomial(pconf)
    return dist[list(kset)].sum(0)


# ---------- シナリオ ----------
PRIORS = {"集団平均(N(0,1))": (0.0, 1.0), "弱い悲観(N(-0.5,1))": (-0.5, 1.0)}
LAMBDA = {"固定難易度": 0.0, "半適応": 0.5, "完全適応": 1.0}
B0 = {"易しめ": -0.5, "中": 0.0, "難しめ": 0.5}
A = {"低識別": 0.8, "高識別": 1.3}
CAL = {"適正": (0.8, 0.10), "自信控えめ": (0.6, 0.05), "過信": (0.9, 0.30)}
PASSAGE = {"情報なし": None, "弱い正の情報": (0.6, -1.0)}   # P(長文3題|η)=logit(α(η-τ)) 仮定

N_VOCAB = 18          # 語彙・文法の問題数（仮定。20分で約30問・長文9問・整序数問から逆算）


def posterior(prior, lam, b0, a, cal, passage):
    m, sd = prior
    post = norm.pdf(G, m, sd)
    # 語彙・文法: 確信ありが4割以下
    bv = np.full(N_VOCAB, b0)
    post *= lik_confident(bv, a, 0.2, lam, cal, range(0, int(0.4 * N_VOCAB) + 1))
    # 長文9問: 1-2題目は易しめ(b0-0.5)、3題目はやや難(b0+0.3)、確信あり4〜6問
    br = [b0 - 0.5] * 6 + [b0 + 0.3] * 3
    post *= lik_confident(br, a, 0.2, lam, cal, {4, 5, 6})
    # 整序1問目: 本人が誤答を自覚（確信して誤答とみなす）
    post *= 1 - p3pl(G, a, lam * G + (1 - lam) * (b0 + 0.3), 0.1)
    if passage:
        al, tau = passage
        post *= 1 / (1 + np.exp(-al * 1.7 * (G - tau)))
    return post / np.trapezoid(post, G)


BINS = [(0, 10), (10, 20), (20, 35), (35, 50), (50, 65), (65, 80), (80, 100)]


def summarize(post):
    cdf = np.cumsum(post) * (G[1] - G[0])
    top = 100 * (1 - norm.cdf(G))           # 上位%（η→集団内順位）
    out = {}
    for lo, hi in BINS:
        mask = (top >= lo) & (top < hi)
        out[f"上位{lo}-{hi}%"] = float(np.trapezoid(post * mask, G))
    def P(cond): return float(np.trapezoid(post * cond, G))
    out["平均以上"] = P(G >= 0)
    out["下位30%"] = P(norm.cdf(G) <= 0.30)
    out["下位20%"] = P(norm.cdf(G) <= 0.20)
    out["下位10%"] = P(norm.cdf(G) <= 0.10)
    out["下位5%(極端)"] = P(norm.cdf(G) <= 0.05)
    q = lambda p: float(np.interp(p, cdf, G))
    out["上位%_中央値"] = 100 * (1 - norm.cdf(q(0.5)))
    out["上位%_95%区間"] = [100 * (1 - norm.cdf(q(0.975))), 100 * (1 - norm.cdf(q(0.025)))]
    return out


def run_grid():
    rows = []
    for (pn, pr), (ln, l), (bn, b), (an, a), (cn, c), (sn, s) in itertools.product(
            PRIORS.items(), LAMBDA.items(), B0.items(), A.items(), CAL.items(), PASSAGE.items()):
        post = posterior(pr, l, b, a, c, s)
        rows.append({"prior": pn, "adapt": ln, "b0": bn, "a": an, "cal": cn, "passage": sn,
                     "post": post, **summarize(post)})
    return rows


# ---------- 戦略比較（モンテカルロ） ----------
def simulate(post, r, g2, g3, n=200_000, sig_q=0.5, strat_cut=None, regress=True):
    """post: η1(GS当日)の事後分布。r: 信頼性。g2/g3: JAL/INPEX時の平均的な上昇（集団SD単位）。
    戻り値: 各戦略の提出スコア(集団内の上位%)のサンプル。"""
    w = post / post.sum()
    eta1 = rng.choice(G, size=n, p=w) + rng.uniform(-0.0025, 0.0025, n)
    if regress:   # θ~N(0,r)を事前とする標準モデル: 低い当日成績は一部が不運 → 平均へ回帰
        theta = rng.normal(r * eta1, np.sqrt(r * (1 - r)))
    else:         # 保守的モデル: GS当日は平常の出来（実力そのものが低い）とみなし回帰させない
        theta = eta1 - rng.normal(0, np.sqrt(1 - r), n)
    e2, e3 = rng.normal(0, np.sqrt(1 - r), (2, n))
    eta2, eta3 = theta + g2 + e2, theta + g3 + e3
    top = lambda x: 100 * (1 - norm.cdf(x))
    res = {"A:GS送信": top(eta1), "B:JAL送信": top(eta2), "C:INPEX受検": top(eta3)}
    # B*: JALの手応え(η2 + ノイズ)が悪ければINPEXで受け直す、良ければJALを送る
    sig = eta2 + rng.normal(0, sig_q, n)
    cut = np.median(sig) if strat_cut is None else strat_cut
    res["B*:JAL手応えで判断"] = np.where(sig >= cut, top(eta2), top(eta3))
    return res


if __name__ == "__main__":
    rows = run_grid()
    keys = ["平均以上", "下位30%", "下位20%", "下位10%", "下位5%(極端)", "上位%_中央値"]
    env = {k: [min(r_[k] for r_ in rows), float(np.median([r_[k] for r_ in rows])), max(r_[k] for r_ in rows)]
           for k in keys + [f"上位{lo}-{hi}%" for lo, hi in BINS]}
    base = next(r_ for r_ in rows if r_["prior"].startswith("集団") and r_["adapt"] == "固定難易度"
                and r_["b0"] == "中" and r_["a"] == "低識別" and r_["cal"] == "適正" and r_["passage"] == "情報なし")
    sel = {
        "S1 基準(固定難易度・中・適正・情報なし)": base,
        "S2 問題が易しめだった": next(r_ for r_ in rows if r_["prior"].startswith("集団") and r_["adapt"] == "固定難易度" and r_["b0"] == "易しめ" and r_["a"] == "低識別" and r_["cal"] == "適正" and r_["passage"] == "情報なし"),
        "S3 問題が難しめだった": next(r_ for r_ in rows if r_["prior"].startswith("集団") and r_["adapt"] == "固定難易度" and r_["b0"] == "難しめ" and r_["a"] == "低識別" and r_["cal"] == "適正" and r_["passage"] == "情報なし"),
        "S4 自信控えめな性格": next(r_ for r_ in rows if r_["prior"].startswith("集団") and r_["adapt"] == "固定難易度" and r_["b0"] == "中" and r_["a"] == "低識別" and r_["cal"] == "自信控えめ" and r_["passage"] == "情報なし"),
        "S5 半適応型出題": next(r_ for r_ in rows if r_["prior"].startswith("集団") and r_["adapt"] == "半適応" and r_["b0"] == "中" and r_["a"] == "低識別" and r_["cal"] == "適正" and r_["passage"] == "情報なし"),
        "S6 完全適応型(手応え無情報)": next(r_ for r_ in rows if r_["prior"].startswith("集団") and r_["adapt"] == "完全適応" and r_["b0"] == "中" and r_["a"] == "低識別" and r_["cal"] == "適正" and r_["passage"] == "情報なし"),
        "S7 S1+長文3題に弱い正の情報": next(r_ for r_ in rows if r_["prior"].startswith("集団") and r_["adapt"] == "固定難易度" and r_["b0"] == "中" and r_["a"] == "低識別" and r_["cal"] == "適正" and r_["passage"] == "弱い正の情報"),
    }
    out = {"n_scenarios": len(rows), "envelope_min_median_max": env,
           "selected": {k: {kk: vv for kk, vv in v.items() if kk != "post"} for k, v in sel.items()}}

    # 戦略比較
    REL = [0.75, 0.85, 0.90]
    GAINS = {"練習効果なし(g2=0,g3=0)": (0.0, 0.0), "小(g2=0.10,g3=0.15)": (0.10, 0.15),
             "中(g2=0.20,g3=0.30)": (0.20, 0.30), "疲労・不調(g2=-0.10,g3=-0.10)": (-0.10, -0.10)}
    CUTS = [50, 65, 75, 85]
    strat = {}
    for sname in ["S1 基準(固定難易度・中・適正・情報なし)", "S2 問題が易しめだった", "S3 問題が難しめだった", "S6 完全適応型(手応え無情報)"]:
        for r in REL:
            for gname, (g2, g3) in GAINS.items():
                res = simulate(sel[sname]["post"], r, g2, g3)
                strat[f"{sname}|r={r}|{gname}"] = {
                    k: {"上位%_平均": float(v.mean()), "上位%_90パーセンタイル(下振れ)": float(np.percentile(v, 90)),
                        **{f"P(上位{c}%以内)": float((v <= c).mean()) for c in CUTS}}
                    for k, v in res.items()}
    out["strategies"] = strat
    # 保守的モデル（回帰なし）
    cons = {}
    for sname in ["S1 基準(固定難易度・中・適正・情報なし)", "S3 問題が難しめだった", "S4 自信控えめな性格"]:
        for r in REL:
            for gname, (g2, g3) in GAINS.items():
                res = simulate(sel[sname]["post"], r, g2, g3, regress=False)
                cons[f"{sname}|r={r}|{gname}"] = {
                    k: {"上位%_平均": float(v.mean()), "上位%_90パーセンタイル(下振れ)": float(np.percentile(v, 90)),
                        **{f"P(上位{c}%以内)": float((v <= c).mean()) for c in CUTS}}
                    for k, v in res.items()}
    out["strategies_no_regression"] = cons
    json.dump(out, open(os.path.join(HERE, "results.json"), "w"), ensure_ascii=False, indent=1)

    # 図
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "IPAGothic"
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.8))
    top = 100 * (1 - norm.cdf(G)); edges = np.arange(0, 101, 2)
    for k, v in sel.items():
        mass = [np.trapezoid(v["post"] * ((top >= lo) & (top < lo + 2)), G) for lo in edges[:-1]]
        ax[0].plot(edges[:-1] + 1, np.array(mass) * 100 / 2, label=k)
    ax[0].set_xlim(0, 100); ax[0].invert_xaxis(); ax[0].set_xlabel("集団内の位置（上位%）  ←上位"); ax[0].set_ylabel("確率（順位1%幅あたり, %）")
    ax[0].set_title("GS英語当日の位置の事後分布（仮定別）"); ax[0].legend(fontsize=7)
    labs = [f"{lo}-{hi}" for lo, hi in BINS]
    vals = np.array([[r_[f"上位{lo}-{hi}%"] for lo, hi in BINS] for r_ in rows])
    ax[1].boxplot(vals * 100, tick_labels=labs); ax[1].set_xlabel("上位%の区間"); ax[1].set_ylabel("その区間に入る確率(%)")
    ax[1].set_title(f"全{len(rows)}シナリオでの区間確率のばらつき")
    plt.tight_layout(); plt.savefig(os.path.join(HERE, "fig_posterior.png"), dpi=130)

    # 戦略図: S1, r=0.85, 各ゲイン
    fig, ax = plt.subplots(1, len(GAINS), figsize=(15, 4), sharey=True)
    for i, (gname, (g2, g3)) in enumerate(GAINS.items()):
        res = simulate(sel["S1 基準(固定難易度・中・適正・情報なし)"]["post"], 0.85, g2, g3)
        for k, v in res.items():
            xs = np.sort(v); ax[i].plot(xs, np.arange(1, len(xs) + 1) / len(xs), label=k)
        ax[i].set_title(gname, fontsize=9); ax[i].set_xlabel("提出される結果（上位%）")
        for c in CUTS: ax[i].axvline(c, color="gray", lw=0.5, ls=":")
    ax[0].set_ylabel("累積確率  P(上位x%以内)"); ax[0].legend(fontsize=7)
    plt.suptitle("戦略別の提出スコア分布（S1基準・信頼性0.85）  ※全パラメータ仮定")
    plt.tight_layout(); plt.savefig(os.path.join(HERE, "fig_strategies.png"), dpi=130)
    print("done", len(rows))
