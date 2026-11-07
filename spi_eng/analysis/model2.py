#!/usr/bin/env python3
"""修正版：語彙・文法の正答率 p_v を未知変数として扱い、「確信が持てない」という自己申告の情報量を
較正モデル A/B/C で感度分析する。前回の model.py は (s,f)=(0.8,0.1) という強い較正で
「自信がない ≒ 不正解」に近い扱いになっていた。それを改めるためのもの。

!!! パラメータは全て仮定。SPI英語の項目統計・較正データは公開されていない。!!!

較正の根拠（定性的）：
- 多肢選択式では、自信が最も低い回答でも偶然以上の確率で正答する（部分的な知識）。McMaster 2023「Dissecting Knowledge, Guessing, and Blunder」。
- 多肢選択式では、当て推量のせいで「確信と正誤の相関（resolution）」が低く出やすく、成績が低いほどその傾向が強い（Vuorre & Metcalfe 2021）。
- 第二言語の学習者が「勘で答えた」と申告した回答も、偶然以上に正答することがある（Dienes の guessing criterion を用いた研究）。
→ resolution = s − f（正答時と誤答時の確信率の差）を、A=0.10 / B=0.35 / C=0.70 の3水準で置く。
   C は前回モデルと同じ強さで、上の研究から見ると「強すぎる」側の上限として扱う。
"""
import itertools, json, os
import numpy as np
from scipy.stats import norm
from model import G, p3pl, poisson_binomial, simulate, BINS

HERE = os.path.dirname(os.path.abspath(__file__))
N_V = 18                       # 語彙・文法の問題数（仮定）
K_V_MAX = 8                    # 「確信できたのは4割程度以下」→ 18問中8問以下（申告のあいまいさを考え 0.45 まで許容）
CALIB = {"A 手応えほぼ無情報": (0.35, 0.25), "B 弱い情報": (0.55, 0.20), "C 強い情報": (0.80, 0.10)}
PROPENSITY = {"確信しやすさ 普通": 1.0, "確信しにくい性格": 0.75}   # s,f をまとめて縮める
B0 = {"易しめ": -0.5, "中": 0.0, "難しめ": 0.5}
LAM = {"固定": 0.0, "半適応": 0.5}


def lik(bs, a, c, lam, s, f, kset):
    b_eff = lam * G[None, :] + (1 - lam) * np.asarray(bs)[:, None]
    pc = p3pl(G[None, :], a, b_eff, c)
    return poisson_binomial(pc * s + (1 - pc) * f)[list(kset)].sum(0)


def post_one(cal, prop, b0, lam, a=0.8, use_vocab=True, use_read=True):
    s, f = (x * prop for x in cal)
    p = norm.pdf(G)
    if use_vocab:
        p *= lik([b0] * N_V, a, 0.2, lam, s, f, range(0, K_V_MAX + 1))
    if use_read:
        p *= lik([b0 - 0.5] * 6 + [b0 + 0.3] * 3, a, 0.2, lam, s, f, {4, 5, 6})
    p *= 1 - p3pl(G, a, lam * G + (1 - lam) * (b0 + 0.3), 0.1)   # 整序1問目は本人が誤答を自覚
    return p / np.trapezoid(p, G)


def pv_of_eta(b0, lam, a=0.8):
    """語彙・文法での期待正答率 p_v(η)。"""
    return p3pl(G, a, lam * G + (1 - lam) * b0, 0.2)


def metrics(p):
    top = 100 * (1 - norm.cdf(G))
    P = lambda m: float(np.trapezoid(p * m, G))
    cdf = np.cumsum(p) * (G[1] - G[0])
    q = lambda x: 100 * (1 - norm.cdf(float(np.interp(x, cdf, G))))
    return {"平均順位(上位%)": float(np.trapezoid(p * top, G)), "上位35%以内": P(top <= 35),
            "平均以上": P(G >= 0), "下位35%": P(top >= 65), "下位20%": P(top >= 80),
            "下位10%": P(top >= 90), "95%区間(上位%)": [q(0.975), q(0.025)]}


def pv_dist(p, b0, lam):
    pv = pv_of_eta(b0, lam)
    edges = [0, 0.3, 0.5, 0.7, 0.85, 1.01]
    return {f"{lo:.2f}-{min(hi,1):.2f}": float(np.trapezoid(p * ((pv >= lo) & (pv < hi)), G))
            for lo, hi in zip(edges[:-1], edges[1:])}


if __name__ == "__main__":
    out = {"models": {}}
    mix = {}
    for cn, cal in CALIB.items():
        posts, pvs, pvs_prior = [], [], []
        for (pn, pr), (bn, b0), (ln, lam) in itertools.product(PROPENSITY.items(), B0.items(), LAM.items()):
            p = post_one(cal, pr, b0, lam); posts.append(p)
            pvs.append(pv_dist(p, b0, lam)); pvs_prior.append(pv_dist(norm.pdf(G), b0, lam))
        pm = np.mean(posts, 0)            # シナリオを等しい重みで平均（重みも仮定）
        mix[cn] = pm
        # 語彙の手応えを外した場合と比べ、語彙情報がどれだけ効いているか
        nov = np.mean([post_one(cal, pr, b0, lam, use_vocab=False)
                       for pr, b0, lam in itertools.product(PROPENSITY.values(), B0.values(), LAM.values())], 0)
        avg = lambda ds: {k: float(np.mean([d[k] for d in ds])) for k in ds[0]}
        out["models"][cn] = {"混合事後": metrics(pm), "語彙の手応えなし": metrics(nov),
                             "p_v事後": avg(pvs), "p_v事前": avg(pvs_prior),
                             "シナリオ別の平均順位の範囲": [min(metrics(x)["平均順位(上位%)"] for x in posts),
                                                         max(metrics(x)["平均順位(上位%)"] for x in posts)]}
    out["完全適応型(参考)"] = metrics(norm.pdf(G))

    # ---- 戦略比較 ----
    GAINS = {"なし": (0.0, 0.0), "小": (0.10, 0.15), "中": (0.20, 0.30), "疲労": (-0.10, -0.10)}
    strat = {}
    for cn, pm in mix.items():
        for reg in [True, False]:
            for r in [0.75, 0.85, 0.90]:
                for gn, (g2, g3) in GAINS.items():
                    res = simulate(pm, r, g2, g3, n=150_000, regress=reg)
                    strat[f"{cn}|{'回帰あり' if reg else '回帰なし'}|r={r}|練習効果{gn}"] = {
                        k: {"平均順位": float(v.mean()), "下振れ90%点": float(np.percentile(v, 90)),
                            "P(下位15%回避)": float((v <= 85).mean()), "P(下位35%回避)": float((v <= 65).mean()),
                            "P(上位50%以内)": float((v <= 50).mean())}
                        for k, v in res.items() if not k.startswith("B*")}
    out["strategies"] = strat

    # 勝率の集計（仮定の格子のうち、その戦略が勝つ割合。確率ではない）
    tally = {}
    for cn in CALIB:
        for reg in ["回帰あり", "回帰なし"]:
            sub = [v for k, v in strat.items() if k.startswith(cn) and f"|{reg}|" in k]
            t = {}
            for x, y in [("B:JAL送信", "A:GS送信"), ("C:INPEX受検", "A:GS送信"), ("C:INPEX受検", "B:JAL送信")]:
                t[f"{x[0]}>{y[0]}"] = {
                    "平均順位": np.mean([v[x]["平均順位"] < v[y]["平均順位"] for v in sub]),
                    "下位15%回避": np.mean([v[x]["P(下位15%回避)"] > v[y]["P(下位15%回避)"] for v in sub]),
                    "下位35%回避": np.mean([v[x]["P(下位35%回避)"] > v[y]["P(下位35%回避)"] for v in sub]),
                    "下振れ90%点": np.mean([v[x]["下振れ90%点"] < v[y]["下振れ90%点"] for v in sub]),
                    "平均順位の差(ポイント,範囲)": [float(min(v[y]["平均順位"] - v[x]["平均順位"] for v in sub)),
                                                float(max(v[y]["平均順位"] - v[x]["平均順位"] for v in sub))],
                    "下位15%回避の差(範囲)": [float(min(v[x]["P(下位15%回避)"] - v[y]["P(下位15%回避)"] for v in sub)),
                                            float(max(v[x]["P(下位15%回避)"] - v[y]["P(下位15%回避)"] for v in sub))]}
            tally[f"{cn}|{reg}"] = t
    out["tally"] = json.loads(json.dumps(tally, default=float))
    json.dump(out, open(os.path.join(HERE, "results2.json"), "w"), ensure_ascii=False, indent=1, default=float)

    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "IPAGothic"
    top = 100 * (1 - norm.cdf(G)); edges = np.arange(0, 101, 2)
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
    for cn, pm in mix.items():
        mass = [np.trapezoid(pm * ((top >= lo) & (top < lo + 2)), G) for lo in edges[:-1]]
        ax[0].plot(edges[:-1] + 1, np.array(mass) * 50, label=cn)
    ax[0].axhline(1, color="gray", ls=":", lw=1, label="事前分布（情報なし）")
    ax[0].invert_xaxis(); ax[0].set_xlabel("集団内の位置（上位%） ←上位"); ax[0].set_ylabel("確率（順位1%幅あたり, %）")
    ax[0].set_title("較正モデル別：GS英語当日の位置の事後分布"); ax[0].legend(fontsize=8)
    labs = list(out["models"]["A 手応えほぼ無情報"]["p_v事後"].keys()); x = np.arange(len(labs))
    ax[1].bar(x - 0.3, [out["models"]["A 手応えほぼ無情報"]["p_v事前"][k] * 100 for k in labs], 0.15, label="事前", color="lightgray")
    for i, cn in enumerate(CALIB):
        ax[1].bar(x - 0.15 + 0.15 * i, [out["models"][cn]["p_v事後"][k] * 100 for k in labs], 0.15, label=cn)
    ax[1].set_xticks(x, labs); ax[1].set_xlabel("語彙・文法の正答率 p_v"); ax[1].set_ylabel("確率(%)")
    ax[1].set_title("p_v の事前分布と事後分布（シナリオ平均）"); ax[1].legend(fontsize=8)
    plt.tight_layout(); plt.savefig(os.path.join(HERE, "fig2_calibration.png"), dpi=130)
    print("done")
