#!/usr/bin/env python3
"""独立検算：model.py とは別の方法（モンテカルロ）で、仮説の事後確率と順位の中央値を再計算し、差が許容範囲内か確かめる。"""
import json, os, sys, math
import numpy as np
from scipy.stats import norm
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, H)
import model
rng = np.random.default_rng(7)
k3, n, _ = model.load_counts(); prior = model.fusion_prior()
s, slope, rho = 2, 1.0, 0.3
# 1) 仮説の事後確率：仮説→報告者の生成をシミュレーションし、観測(k3/n)と一致した割合で重み付け（ABC）
N = 400000
h_idx = rng.choice(4, size=N, p=[prior[h] for h in model.HYP])
q = np.array([model.Q_H[h] for h in model.HYP])[h_idx]
pi = s * q / (s * q + 1 - q)
k_sim = rng.binomial(n, pi)
acc = h_idx[k_sim == k3]
mc = {h: float(np.mean(acc == i)) for i, h in enumerate(model.HYP)}
an = model.posterior_hyp(k3, n, s, prior)
an_final = json.load(open(os.path.join(H, "results.json"), encoding="utf-8"))["grid"][f"s={s}|slope={slope}|rho={rho}"]["hyp"]
# 2) 順位の中央値：仮説→能力→「長文3題」を生成し、3題以上になった本人の能力の分布から中央値
M = 400000
hh = rng.choice(4, size=M, p=[an[h] for h in model.HYP])   # 口コミだけで更新した仮説の確率から出発
pct = rng.uniform(0.0, 0.25, M); zb = norm.ppf(1 - pct)
eta = rho * zb + math.sqrt(1 - rho ** 2) * rng.normal(size=M)
keep = np.ones(M, bool)
for i, h in enumerate(model.HYP):
    m = hh == i
    if model.TAU[h] is not None:
        keep[m] = rng.random(m.sum()) < norm.cdf((eta[m] - model.TAU[h]) / slope)
    else:
        keep[m] = rng.random(m.sum()) < model.Q_H[h]
mc_median = float(100 * (1 - norm.cdf(np.median(eta[keep]))))
an_median = json.load(open(os.path.join(H, "results.json"), encoding="utf-8"))["grid"][f"s={s}|slope={slope}|rho={rho}"]["rank"]["中央値(上位%)"]
diff_h = max(abs(mc[h] - an[h]) for h in model.HYP)
mc_final = {h: float(np.mean(hh[keep] == i)) for i, h in enumerate(model.HYP)}
diff_f = max(abs(mc_final[h] - an_final[h]) for h in model.HYP)
ok = diff_h < 0.02 and diff_f < 0.02 and abs(mc_median - an_median) < 1.0
json.dump({"analytic_hyp": an, "mc_hyp": mc, "max_diff_hyp": diff_h, "analytic_median": an_median, "mc_median": mc_median, "ok": ok},
          open(os.path.join(H, "independent_check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("max_diff_hyp", round(diff_h, 4), "max_diff_final", round(diff_f, 4), "median", round(an_median, 2), round(mc_median, 2), "OK" if ok else "MISMATCH")
sys.exit(0 if ok else 1)
