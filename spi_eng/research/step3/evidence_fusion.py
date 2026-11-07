#!/usr/bin/env python3
"""STEP3：信頼性・独立性の評価と、非線形な証拠統合。

統合する仮説（長文3題の意味）：
  H_none : 長文の題数と成績はほぼ無関係
  H_avg  : 長文3題は平均的な出題数
  H_above: 長文3題は平均以上を示唆
  H_high : 長文3題は比較的高得点を示唆

モデル（情報源 i が「X」と主張したとき）：
  P(X | H) = r_i * 1[X が H と整合] / |整合する主張の数|  +  (1 - r_i) * f(X)
  r_i : 情報源の主張が本当の知識に基づいている確率（信頼性）。**データから識別できない → 仮定（感度分析）**
  f(X): 真偽と無関係に、噂としてその主張が出回る確率。ここでは一様（主張の種類数の逆数）と置く（仮定）
同じ系統（転載・同一運営・同じ噂）の情報源は独立でないので、系統ごとに1回だけ数え、追加のn件は
  実効件数 n_eff = n / (1 + (n-1) * rho)   （rho：系統内の相関。仮定）
として、対数尤度比を n_eff 倍する（1件目と同じ証拠の焼き直しなので、増え方は頭打ちになる）。
独立な系統どうしは尤度比を掛け合わせる（確率空間では非線形に強まる）。
"""
import csv, json, math, os, itertools
H = os.path.dirname(os.path.abspath(__file__))
HYP = ["H_none", "H_avg", "H_above", "H_high"]
# 主張の型 → 整合する仮説
CONSISTENT = {
 "three_high":        ["H_high"],
 "three_above":       ["H_above"],
 "three_above_or_high": ["H_above", "H_high"],
 "three_not_low":     ["H_avg", "H_above", "H_high"],
 "count_unrelated":   ["H_none"],
 "three_standard":    ["H_none", "H_avg"],
}
TYPES = list(CONSISTENT)

def load_claim_map():
    """各主張・受検報告の「型」を、根拠つきで返す（eng_claims_verified.csv / verified_records.csv の実データを読む）。"""
    rows = list(csv.DictReader(open(os.path.join(H, "reliability.csv"), encoding="utf-8")))
    return [r for r in rows if r["claim_type"]]

def lineage_of(rid):
    dep = list(csv.DictReader(open(os.path.join(H, "../step2/dependency_graph.csv"), encoding="utf-8")))
    for d in dep:
        if d["from"] == rid and d["to"] != "CB01":
            return d["to"]
    return rid

def lik(claim_type, hyp, r):
    cons = CONSISTENT[claim_type]
    p_true = (1.0 / len(cons)) if hyp in cons else 0.0
    return r * p_true + (1 - r) * (1.0 / len(TYPES))

def fuse(items, r_scale=1.0, rho=0.7, prior=None, drop=None):
    """items: [{'id','claim_type','reliability'(0-1),'lineage'}]。戻り値：仮説の事後確率"""
    prior = prior or {h: 1 / len(HYP) for h in HYP}
    logp = {h: math.log(prior[h]) for h in HYP}
    groups = {}
    for it in items:
        if drop and drop(it): continue
        groups.setdefault(it["lineage"], []).append(it)
    for lin, its in groups.items():
        n = len(its)
        n_eff = n / (1 + (n - 1) * rho)
        # 系統内の代表：信頼性の最も高い情報源
        best = max(its, key=lambda x: x["reliability"])
        r = min(0.95, best["reliability"] * r_scale)
        for h in HYP:
            logp[h] += n_eff * math.log(lik(best["claim_type"], h, r))
    m = max(logp.values()); z = sum(math.exp(v - m) for v in logp.values())
    return {h: math.exp(logp[h] - m) / z for h in HYP}

def run():
    items = []
    for r in load_claim_map():
        items.append({"id": r["id"], "claim_type": r["claim_type"], "reliability": float(r["r_base"]), "lineage": lineage_of(r["id"])})
    out = {"n_items": len(items), "n_lineages": len({i['lineage'] for i in items}), "sensitivity": {}}
    for rs, rho in itertools.product([0.5, 1.0, 1.5], [0.5, 0.9]):
        out["sensitivity"][f"r_scale={rs}|rho={rho}"] = fuse(items, rs, rho)
    # 情報源群を除いた場合
    out["drop_spi_sites"] = fuse(items, drop=lambda x: x["id"].startswith("C0") or x["id"].startswith("C1") and x["id"] not in ("C13", "C14"))
    out["drop_test_takers"] = fuse(items, drop=lambda x: not x["id"].startswith("C"))
    out["drop_C04_lineage"] = fuse(items, drop=lambda x: x["lineage"] == "C04")
    out["limitations"] = [
        "r（情報源の信頼性）は、主張の正誤を検証した実測データがないため識別できない。r_base は規則にもとづく相対評価で、絶対的な確率ではない",
        "f（噂として出回る確率）は一様と仮定した。実際には『長文が多い＝高得点』という噂が流布しているため、その方向の主張の尤度比は過大評価になっている可能性がある",
        "rho（系統内の相関）は識別できない。0.5〜0.9で感度分析した",
        "長文の題数と客観的な得点が両方分かるデータは0件。この統合は『主張の分布』をまとめたもので、得点との関係を実測したものではない",
    ]
    json.dump(out, open(os.path.join(H, "fusion_results.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return out

if __name__ == "__main__":
    o = run()
    for k, v in o["sensitivity"].items():
        print(k, {h: round(p, 3) for h, p in v.items()})
    for k in ["drop_spi_sites", "drop_test_takers", "drop_C04_lineage"]:
        print(k, {h: round(p, 3) for h, p in o[k].items()})
