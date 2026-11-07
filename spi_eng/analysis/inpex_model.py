#!/usr/bin/env python3
"""口コミデータ（data/*.csv）の集計と、INPEXでの英語評価に関する条件付きシナリオ分析。

区別の徹底：
- data/*.csv の中身＝実際に確認できた情報（ほとんどは検索結果の抜粋レベル）。架空の行はない。
- 以下の τ, σ, 足切り q, 重み w, 練習効果 g, 信頼性 r は全て【仮定】であり、SPIやINPEXの実際の値ではない。
"""
import csv, json, os, itertools
import numpy as np
from scipy.stats import norm
from model import G, simulate
from model2 import post_one, CALIB, PROPENSITY, B0, LAM, metrics

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data")
load = lambda f: list(csv.DictReader(open(os.path.join(D, f), encoding="utf-8")))

# ---------- 1. 口コミデータの集計（記述統計のみ） ----------
eng, claims, cases, srcs = load("eng_reports.csv"), load("eng_claims.csv"), load("inpex_cases.csv"), load("inpex_sources.csv")
eng_valid = [r for r in eng if r["test_confirmed_ENG"].startswith("yes") and r["id"] != "U0"]
with_passages = [r for r in eng_valid if r["n_passages"].strip().isdigit()]
desc = {
    "SPI英語_報告総数(除外分を含む)": len(eng) - 1,
    "SPI英語と確認できた報告": len(eng_valid),
    "長文の題数が分かる英語の報告": len(with_passages),
    "長文の題数の内訳": {r["id"]: int(r["n_passages"]) for r in with_passages},
    "得点や結果と出題パターンを両方含む報告": 0,
    "対策サイトの主張(独立性を問わない件数)": len(claims),
    "INPEXの情報源": len(srcs),
    "INPEXの事例": len(cases),
    "INPEX_結果が分かる事例": sum(1 for c in cases if not c["result"].startswith("不明")),
    "INPEX_英語資格(TOEIC等)が分かる事例": sum(1 for c in cases if c["english_cert"] != "不明"),
    "INPEX_SPIの手応えと結果が両方分かる事例": [c["case_id"] for c in cases
                                       if c["spi_eng_feel"] != "不明" and not c["result"].startswith("不明")],
}

# ---------- 2. 「長文の題数」を尤度に入れる仮説（対策サイトの主張を形にしたもの） ----------
# P(長文3題以上 | η) = Φ((η−τ)/σ)。主張のどれにも一次データはない → 「主張が正しいとしたら」という条件付きの扱い。
PASSAGE_H = {
    "N0 題数は能力と無関係(速度などで決まる)": None,
    "K1 3題=平均以上で出やすい(弱)": (0.0, 1.0),
    "K2 3題=やや上位(K3/K4系：4題が高得点・1題が平均)": (0.0, 0.5),
    "K3 3題=高得点(K2/K5系)": (0.5, 0.5),
}


def posterior(cal, ph):
    ps = [post_one(cal, pr, b0, lam) for pr, b0, lam in
          itertools.product(PROPENSITY.values(), B0.values(), LAM.values())]
    p = np.mean(ps, 0)
    if ph:
        tau, sig = ph
        p = p * norm.cdf((G - tau) / sig)
    return p / np.trapezoid(p, G)


def bins(p):
    top = 100 * (1 - norm.cdf(G))
    P = lambda m: float(np.trapezoid(p * m, G))
    return {"上位10%以内": P(top <= 10), "上位20%以内": P(top <= 20), "上位35%以内": P(top <= 35),
            "平均以上": P(top <= 50), "上位65%以内": P(top <= 65), "下位20%": P(top >= 80),
            "下位10%": P(top >= 90), "平均順位(上位%)": float(np.trapezoid(p * top, G))}


post_tab, posts = {}, {}
for cn in ["A 手応えほぼ無情報", "B 弱い情報", "C 強い情報"]:
    for hn, ph in PASSAGE_H.items():
        p = posterior(CALIB[cn], ph)
        posts[(cn, hn)] = p
        post_tab[f"{cn} × {hn}"] = bins(p)

# ---------- 3. INPEXの仮説を事例で区別できるか（尤度比の計算例） ----------
# 事例C1(手応えが悪いのに通過)とC2(回答率6〜7割で通過)。足切りが下位q%にあるとき、
# 「手応えが悪い人が足切りを越える確率」を、較正Bの事後分布から計算する。
#   P(通過 | H_q) ∝ P(下位q%に入らない | 手応え悪い) × P(他の基準で通過)   ← 後者はどの仮説でも共通なので比では消える
#   LR(H1 : H_q) = 1 / P(下位q%に入らない | 手応え悪い)^2   (C1, C2が独立だと仮定)
pB = posts[("B 弱い情報", "N0 題数は能力と無関係(速度などで決まる)")]
top = 100 * (1 - norm.cdf(G))
lr = {}
for q in [5, 10, 20, 30, 40]:
    a = float(np.trapezoid(pB * (top < 100 - q), G))
    lr[f"下位{q}%足切り"] = {"P(足切りを越える|手応え悪い)": a, "LR(H1:H_q) 2事例": 1 / a ** 2}

# ---------- 4. 英語が上位p%のとき、仮想の足切り・仮想の重みでどれだけ不利か ----------
perc = [10, 20, 35, 50, 65, 75, 85, 90, 95]
penalty = {}
for p in perc:
    z = norm.ppf(1 - p / 100)
    row = {f"足切り下位{q}%で不合格": (p > 100 - q) for q in [5, 10, 20, 30, 40]}
    for w in [0.0, 0.05, 0.10, 0.20]:
        # 総合点 T=w·zE+(1−w)·zO。平均的な英語(zE=0)の人と比べて、他の評価で何SD補えばよいか
        row[f"重み{int(w*100)}%: 他の評価で補うべきSD"] = float(-w / (1 - w) * z) if w < 1 else None
    penalty[f"上位{p}%"] = row

# ---------- 5. 戦略比較：成績の不確実性 × INPEX基準の不確実性を分けて計算し、最後に統合 ----------
GAINS = {"なし": (0, 0), "小": (0.10, 0.15), "中": (0.20, 0.30), "疲労": (-0.10, -0.10)}
strat = {}
for (cn, hn), p in posts.items():
    if cn == "C 強い情報":
        continue
    for reg in [True, False]:
        for gn, (g2, g3) in GAINS.items():
            res = simulate(p, 0.85, g2, g3, n=100_000, regress=reg)
            key = f"{cn}|{hn}|{'回帰あり' if reg else '回帰なし'}|練習効果{gn}"
            strat[key] = {}
            for k, v in res.items():
                if k.startswith("B*"):
                    continue
                zE = norm.ppf(1 - np.clip(v, 0.01, 99.99) / 100)
                strat[key][k] = {**{f"P(下位{q}%を回避)": float((v <= 100 - q).mean()) for q in [5, 10, 20, 30, 40]},
                                 **{f"重み{int(w*100)}%の期待補正SD": float((w / (1 - w) * zE).mean()) for w in [0.05, 0.10, 0.20]},
                                 "平均順位": float(v.mean())}


def comp(x, y, metric, better="high"):
    vals = [(s[x][metric] - s[y][metric]) for s in strat.values()]
    if better == "low":
        vals = [-v for v in vals]
    return {"後者より有利なシナリオの割合": float(np.mean([v > 0 for v in vals])),
            "差の範囲": [float(min(vals)), float(max(vals))]}


summary = {}
for x, y in [("A:GS送信", "C:INPEX受検"), ("A:GS送信", "B:JAL送信"), ("C:INPEX受検", "B:JAL送信")]:
    summary[f"{x[0]} vs {y[0]}"] = {
        **{f"下位{q}%回避": comp(x, y, f"P(下位{q}%を回避)") for q in [5, 10, 20, 30, 40]},
        "重み10%の期待補正": comp(x, y, "重み10%の期待補正SD"),
        "平均順位": comp(x, y, "平均順位", better="low")}

out = {"descriptive": desc, "posterior_by_calibration_x_passage": post_tab, "inpex_LR_example": lr,
       "penalty_table_hypothetical": penalty, "strategy_summary": summary, "strategies": strat}
json.dump(out, open(os.path.join(HERE, "inpex_results.json"), "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: out[k] for k in ["descriptive", "posterior_by_calibration_x_passage", "inpex_LR_example", "strategy_summary"]},
                 ensure_ascii=False, indent=1, default=float))
print(json.dumps(penalty["上位65%"], ensure_ascii=False))
