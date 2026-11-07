#!/usr/bin/env python3
"""STEP5：INPEXの英語評価に関する仮説比較（STEP3と同じ統合方法）。
H1 参考程度 / H2 極端な低得点だけ除く緩い足切り / H3 平均以下の一部も不利になる足切り / H4 総合評価で連続的に加点・減点
H5（入社後の配属で英語が重要）は採用時の評価とは別の論点として、証拠の有無だけを記録する。"""
import csv, json, math, os, itertools
H = os.path.dirname(os.path.abspath(__file__))
HYP = ["H1", "H2", "H3", "H4"]
LINEAGE = {"IC03": "inpex_spi_sites", "IC04": "inpex_spi_sites", "IC05": "inpex_spi_sites"}
N_TYPES = 3  # 主張の型の数（H1_H2_H4 / H1_H2 / H3_H4）

def items(path=None, drop=()):
    rows = list(csv.DictReader(open(path or os.path.join(H, "inpex_records.csv"), encoding="utf-8")))
    out = []
    for r in rows:
        if not r["hyp_type"] or r["id"] in drop: continue
        lin = LINEAGE.get(r["id"], r["same_person_group"] or r["id"])
        out.append({"id": r["id"], "cons": r["hyp_type"].split("_"), "r": float(r["r_base"]), "lineage": lin})
    return out

def fuse(its, r_scale=1.0, rho=0.7):
    logp = {h: math.log(1 / len(HYP)) for h in HYP}
    groups = {}
    for it in its: groups.setdefault(it["lineage"], []).append(it)
    for lin, g in groups.items():
        n = len(g); n_eff = n / (1 + (n - 1) * rho)
        best = max(g, key=lambda x: x["r"]); r = min(0.95, best["r"] * r_scale)
        for h in HYP:
            p_true = (1 / len(best["cons"])) if h in best["cons"] else 0.0
            logp[h] += n_eff * math.log(r * p_true + (1 - r) / N_TYPES)
    m = max(logp.values()); z = sum(math.exp(v - m) for v in logp.values())
    return {h: math.exp(logp[h] - m) / z for h in HYP}

def run(path=None):
    its = items(path)
    out = {"items": [i["id"] for i in its], "sensitivity": {}}
    for rs, rho in itertools.product([0.5, 1.0, 1.3], [0.5, 0.9]):
        out["sensitivity"][f"r_scale={rs}|rho={rho}"] = fuse(its, rs, rho)
    out["drop_official_faq"] = fuse(items(path, drop=("IO1",)))
    out["drop_spi_sites"] = fuse(items(path, drop=("IC03", "IC04", "IC05")))
    out["drop_test_takers"] = fuse(items(path, drop=("IR01", "IR06", "IR08")))
    out["identifiability"] = {
        "H1_vs_H2": "識別できない：全ての証拠がH1とH2の両方と整合する(英語の得点と選考結果が両方分かる事例が0件)",
        "H4_weight": "識別できない：英語の配点・重みを示す一次資料も事例もない",
        "floor_location": "識別できない：足切りがあるとしても位置を示すデータがない",
        "selection_bias": "体験談は面接まで進んだ人のものが大半。適性検査段階で落ちた人の報告は0件(落ちた人は書かないため、足切りの不存在の証拠にはならない)",
    }
    out["H5"] = {"supported_by": ["IO1(公式FAQ：入社後は英語を使う業務が多い・英語研修や自己啓発の補助)"], "note": "採用時の評価方法とは独立の論点"}
    out["evaluation_points_in_reports"] = "外資就活・unistyle・転職会議の新卒報告で評価されたと書かれているのは、研究内容・論理性・志望度・協調性・履修履歴。新卒の面接で英語やTOEICについて問われた報告は0件(中途で1件)"
    return out

if __name__ == "__main__":
    o = run()
    json.dump(o, open(os.path.join(H, "hypotheses.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for k, v in o["sensitivity"].items(): print(k, {h: round(p, 3) for h, p in v.items()})
    for k in ["drop_official_faq", "drop_spi_sites", "drop_test_takers"]: print(k, {h: round(p, 3) for h, p in o[k].items()})
