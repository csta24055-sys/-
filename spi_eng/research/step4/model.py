#!/usr/bin/env python3
"""STEP4：口コミの実データから、長文3題の意味と本人の英語の順位帯を推定する。

【実データから推定するもの】
  q_rep = 報告者のうち長文3題以上だった割合（step2/verified_records.csv の passages 列。独立単位で数える）
【仮定（識別不能）として感度分析するもの】
  s   : 報告の偏り。3題以上の人が、2題以下の人より s 倍報告しやすい（1, 2, 4）
  q_H : 各仮説のもとでの、受検者全体で3題以上が出る割合（主張の文言から：高得点=上位20%→0.2、平均以上→0.5、平均的/無関係→0.8）
  slope: 題数と能力の関係の鋭さ（0.5, 1.0）
  rho : 基礎能力と英語の相関（0, 0.3, 0.5）。基礎能力は本人申告の上位25%以内を条件とする
仮説の事前確率は STEP3 の統合結果（主張の分布）を使う。
"""
import csv, json, math, os, itertools
import numpy as np
from scipy.stats import norm, binom
H = os.path.dirname(os.path.abspath(__file__))
HYP = ["H_none", "H_avg", "H_above", "H_high"]
Q_H = {"H_none": 0.8, "H_avg": 0.8, "H_above": 0.5, "H_high": 0.2}
# 3題以上が出る能力の閾値（集団の z）。H_none は題数が能力と無関係
TAU = {"H_avg": None, "H_none": None, "H_above": 0.0, "H_high": norm.ppf(0.8)}
G = np.linspace(-4, 4, 1601)

def load_counts(path=None, exclude_media=()):
    path = path or os.path.join(H, "../step2/verified_records.csv")
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    med = {r["report_id"]: r["medium"] for r in csv.DictReader(open(os.path.join(H, "../step1/eng_records.csv"), encoding="utf-8"))}
    units = {}
    for r in rows:
        if not r["passages"] or med.get(r["report_id"]) in exclude_media: continue
        units.setdefault(r["independence_unit"], []).append(int(r["passages"]))
    k3 = sum(1 for v in units.values() if max(v) >= 3)
    return k3, len(units), sorted(units)

def fusion_prior(key="r_scale=1.0|rho=0.5"):
    fr = json.load(open(os.path.join(H, "../step3/fusion_results.json"), encoding="utf-8"))
    return fr["sensitivity"][key]

def posterior_hyp(k3, n, s, prior):
    w = {}
    for h in HYP:
        q = Q_H[h]; pi = s * q / (s * q + 1 - q)     # 報告者の中での3題以上の割合
        w[h] = prior[h] * binom.pmf(k3, n, pi)
    z = sum(w.values()); return {h: w[h] / z for h in HYP}

def eta_unnorm(hyp, slope, rho):
    """本人：長文3題。基礎能力は上位25%以内（集団の順位で一様＝集団の事前分布を条件づけたもの）。
    戻り値は正規化前の P(η) * P(3題以上 | η, 仮説)。積分値が仮説の周辺尤度になる。"""
    zb = norm.ppf(1 - np.linspace(0.005, 0.245, 49))
    prior = np.mean([norm.pdf(G, rho * z, math.sqrt(1 - rho ** 2)) for z in zb], axis=0)
    lik = np.full_like(G, Q_H[hyp]) if TAU[hyp] is None else norm.cdf((G - TAU[hyp]) / slope)
    return prior * lik

def summarize(p):
    top = 100 * (1 - norm.cdf(G)); cdf = np.cumsum(p) * (G[1] - G[0])
    q = lambda x: float(100 * (1 - norm.cdf(np.interp(x, cdf, G))))
    P = lambda m: float(np.trapezoid(p * m, G))
    return {"中央値(上位%)": q(0.5), "平均(上位%)": float(np.trapezoid(p * top, G)), "50%区間": [q(0.75), q(0.25)],
            "80%区間": [q(0.9), q(0.1)], "95%区間": [q(0.975), q(0.025)], "上位35%以内": P(top <= 35),
            "平均以上": P(top <= 50), "下位20%": P(top >= 80), "下位10%": P(top >= 90)}

def run(counts_path=None, exclude_media=(), fusion_key="r_scale=1.0|rho=0.5"):
    k3, n, units = load_counts(counts_path, exclude_media)
    prior = fusion_prior(fusion_key)
    out = {"data": {"k3": k3, "n_units": n, "units": units}, "grid": {}}
    for s, slope, rho in itertools.product([1, 2, 4], [0.5, 1.0], [0.0, 0.3, 0.5]):
        ph = posterior_hyp(k3, n, s, prior)
        un = {h: eta_unnorm(h, slope, rho) for h in HYP}
        w = {h: ph[h] * np.trapezoid(un[h], G) for h in HYP}      # 本人の「3題」でも仮説を更新する
        z = sum(w.values()); post_h = {h: float(w[h] / z) for h in HYP}
        mix = sum(post_h[h] * un[h] / np.trapezoid(un[h], G) for h in HYP)
        out["grid"][f"s={s}|slope={slope}|rho={rho}"] = {"hyp_from_reports": ph, "hyp": post_h, "rank": summarize(mix)}
    return out

if __name__ == "__main__":
    main = run()
    json.dump(main, open(os.path.join(H, "results.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sens = {
        "exclude_chiebukuro": run(exclude_media=("chiebukuro",)),
        "exclude_gaishishukatsu_blogs_note": run(exclude_media=("gaishishukatsu", "blogs", "note")),
        "fusion_low_r_high_rho": run(fusion_key="r_scale=0.5|rho=0.9"),
        "fusion_high_r_low_rho": run(fusion_key="r_scale=1.5|rho=0.5"),
        "uniform_hyp_prior": None,
    }
    # 主張(STEP3)を使わず、仮説の事前確率を一様にした場合
    k3, n, _ = load_counts(); u = {h: .25 for h in HYP}
    sens["uniform_hyp_prior"] = {f"s={s}": posterior_hyp(k3, n, s, u) for s in (1, 2, 4)}
    json.dump(sens, open(os.path.join(H, "sensitivity.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("data:", main["data"])
    for k in ["s=1|slope=1.0|rho=0.0", "s=2|slope=1.0|rho=0.3", "s=4|slope=0.5|rho=0.5"]:
        g = main["grid"][k]; print(k, {h: round(v, 3) for h, v in g["hyp"].items()}, {a: (round(b, 1) if isinstance(b, float) else [round(x, 1) for x in b]) for a, b in g["rank"].items()})
    print("uniform prior:", {k: {h: round(x, 3) for h, x in v.items()} for k, v in sens["uniform_hyp_prior"].items()})
    for k in ["exclude_chiebukuro", "exclude_gaishishukatsu_blogs_note"]:
        g = sens[k]["grid"]["s=2|slope=1.0|rho=0.3"]; print(k, sens[k]["data"]["k3"], "/", sens[k]["data"]["n_units"], {h: round(v, 3) for h, v in g["hyp"].items()}, round(g["rank"]["中央値(上位%)"], 1))
