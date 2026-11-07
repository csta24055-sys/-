#!/usr/bin/env python3
"""8つの観点の評価を規則で付ける（人の印象で点数を振らない）。r_base は統合用の相対的な信頼性（仮定。識別不能）。"""
import csv, os
H = os.path.dirname(os.path.abspath(__file__))
recs = list(csv.DictReader(open(os.path.join(H, "../step2/verified_records.csv"), encoding="utf-8")))
src = {r["report_id"]: r for r in csv.DictReader(open(os.path.join(H, "../step1/eng_records.csv"), encoding="utf-8"))}
claims = list(csv.DictReader(open(os.path.join(H, "../step1/eng_claims_verified.csv"), encoding="utf-8")))
# 長文の題数の意味について何かを主張している項目と、その型（根拠は eng_claims_verified.csv / eng_records.csv の引用）
CLAIM_TYPE = {"C01": "three_above", "C02": "three_not_low", "C03": "three_high", "C04": "three_above", "C05": "three_above",
              "C06": "three_above", "C07": "three_above", "C08": "three_high", "C09": "three_above_or_high",
              "C10": "count_unrelated", "C11": "three_standard", "C13": "count_unrelated", "C14": "three_not_low",
              "G13": "three_above", "P02": "count_unrelated"}
# 情報源の種類ごとの相対的な信頼性（仮定）
R_BY_KIND = {"lecturer": 0.4, "site_nodata": 0.3, "promo": 0.3, "rumor": 0.15, "individual_multi": 0.4,
             "individual_single": 0.25, "answer_opinion": 0.2, "book": 0.6, "test_taker_self": 0.25}
KIND = {"C01": "site_nodata", "C02": "promo", "C03": "site_nodata", "C04": "site_nodata", "C05": "site_nodata", "C06": "site_nodata",
        "C07": "lecturer", "C08": "rumor", "C09": "site_nodata", "C10": "individual_multi", "C11": "site_nodata", "C12": "book",
        "C13": "individual_single", "C14": "answer_opinion"}
SAME_DAY = {"CB01", "CB02"}       # 受検当日・翌日の投稿
LONG_GAP = {"CB08"}               # 受検から5年後
rows = []
for r in recs:
    rid = r["report_id"]; s = src[rid]
    direct = r["original_status"]
    acc = {"原文(公開部分を含む)": "high", "原文の公開部分のみ": "medium", "検索要約のみ": "low"}[direct]
    mem = "high" if rid in SAME_DAY or rid == "P01" else ("low" if rid in LONG_GAP else "medium")
    score = "self_estimate" if any(k in (s["feel"] + s["score_statement"]) for k in ["割", "レベル", "平均", "解け", "手応え", "できは", "出来"]) else "none"
    sel = "high(通過者が書くレポート)" if s["medium"] in ("gaishishukatsu", "onecareer") else ("medium(不安な人が質問する)" if s["medium"] == "chiebukuro" else "medium")
    ct = CLAIM_TYPE.get(rid, "")
    rows.append({"id": rid, "kind": "test_report", "accuracy": acc, "memory": mem, "score_reliability": score,
                 "direct_experience": "yes", "common_source": "経験則を利用" if rid == "G13" else "none",
                 "selection_bias": sel, "agreement": "", "counter_consistency": "", "claim_type": ct,
                 "r_base": R_BY_KIND["test_taker_self"] if ct else "", "notes": s["notes"]})
for c in claims:
    cid = c["claim_id"]; kind = KIND[cid]
    rows.append({"id": cid, "kind": "claim:" + kind, "accuracy": "high" if c["original_verified"] == "yes" else "low",
                 "memory": "n/a", "score_reliability": "none",
                 "direct_experience": "yes" if kind in ("individual_multi", "individual_single") else "no",
                 "common_source": c["lineage"], "selection_bias": "商業サイトは注目を集める主張を選びやすい" if kind in ("site_nodata", "promo") else "不明(個人・講師・書籍の投稿)",
                 "agreement": "", "counter_consistency": "", "claim_type": CLAIM_TYPE.get(cid, ""),
                 "r_base": R_BY_KIND[kind] if CLAIM_TYPE.get(cid) else "", "notes": c["claim_detail"][:80]})
# 7・8：他の証拠との一致と、反対の証拠との整合（型の集計から機械的に）
from collections import Counter
cnt = Counter(r["claim_type"] for r in rows if r["claim_type"])
for r in rows:
    if r["claim_type"]:
        same = cnt[r["claim_type"]] - 1
        r["agreement"] = f"同型{same}件"
        r["counter_consistency"] = ("反例P02(長文4題・TOEIC500・手応えなし)と矛盾" if r["claim_type"] in ("three_high", "three_above_or_high", "three_above")
                                   else "反例と矛盾しない")
with open(os.path.join(H, "reliability.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(len(rows), "rows;", dict(cnt))
