#!/usr/bin/env python3
"""STEP2：STEP1のレコードを検証し、同一人物の可能性・転載・共通情報源を整理して、独立した証拠の数を数える。"""
import csv, json, os
H = os.path.dirname(os.path.abspath(__file__))
recs = list(csv.DictReader(open(os.path.join(H, "../step1/eng_records.csv"), encoding="utf-8")))
# 同一人物の可能性があるグループ(同じ年度・同じ職種・同じ媒体、または近い投稿日で匿名)。根拠を明記する
SAME = {
 "SP-INPEX24-tech": (["P06", "P10"], "INPEX 24卒 技術系のインターン報告と本選考報告(同じ人が両方書いた可能性)"),
 "SP-INPEX24-office": (["P05", "P09"], "INPEX 24卒 事務系の本選考報告2件"),
 "SP-JAL20-tech": (["G07", "G08"], "JAL技術系 20卒の本選考報告とインターン報告"),
 "SP-CB-2023-04": (["CB04", "CB05"], "2023年4月5日と7日の投稿。片方は匿名で、どちらも英語の長文3つ"),
 "SP-OC-JAL": (["S02", "S03"], "ONE CAREER のJAL報告(検索要約のみ。URLとの対応が不確か)"),
}
grp_of = {rid: g for g, (ids, _) in SAME.items() for rid in ids}
rows = []
for r in recs:
    rid = r["report_id"]
    ev = r["eng_evidence"]
    conf = "yes" if any(k in ev for k in ["英語", "ENG"]) else "unclear"
    # 「テストセンター」かつ「SPI」の確認状況
    tc = ("テストセンター" in ev) or r["medium"] in ("chiebukuro", "blogs", "note")
    status = {"yes": "原文(公開部分を含む)", "no": "検索要約のみ"}[r["original_verified"]]
    if "公開部分" in r["verification_method"]:
        status = "原文の公開部分のみ"
    rows.append({
        "report_id": rid, "url": r["url"], "eng_confirmed": conf,
        "confusion_check": "言語の報告・C-GAB・玉手箱・GAB・自宅受検・ペーパーは STEP1 で除外済み",
        "tc_confirmed": "yes" if tc else "unclear",
        "original_status": status,
        "same_person_group": grp_of.get(rid, ""),
        "repost_suspected": "no",   # 体験談の本文が他サイトに転載されている例は確認されなかった
        "shared_source": "長文の題数の経験則(C系統)を参照" if rid == "G13" else "",
        "objective_score": "none",
        "passages": r["n_passages"].split("(")[0] if r["n_passages"][:1].isdigit() else "",
        "outcome": r["selection_result"],
        "independence_unit": grp_of.get(rid, rid),
    })
with open(os.path.join(H, "verified_records.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
# 主張の依存関係
DEP = [
 ("C02", "C01", "宣伝・同一運営(就活マップ／noahs-ark)"),
 ("C05", "C04", "同一の文言「長文問題が4つ以上」(転載または共通の出典)"),
 ("C06", "C04", "同一の文言「長文問題が4問以上」(転載または共通の出典)"),
 ("C08", "RUMOR", "九州商社会：「噂」と明記"),
 ("C09", "RUMOR", "個人：出典なしの経験則"),
 ("C03", "RUMOR", "理系days：出典なし"),
 ("G13", "RUMOR", "受検者本人が経験則(長文3問＝平均以上)を自己評価に利用"),
 ("C14", "CB01", "CB01への回答(回答者の意見)"),
]
with open(os.path.join(H, "dependency_graph.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["from", "to", "relation"]); w.writerows(DEP)
claims = list(csv.DictReader(open(os.path.join(H, "../step1/eng_claims_verified.csv"), encoding="utf-8")))
# 主張の独立系統：依存先(to)が他の主張なら同じ系統、RUMOR は1系統にまとめる
lineage = {}
for c in claims:
    cid = c["claim_id"]; root = cid
    for a, b, _ in DEP:
        if a == cid and b != "CB01": root = b
    lineage[cid] = root
units = {r["independence_unit"] for r in rows}
pass_units = {r["independence_unit"] for r in rows if r["passages"]}
summary = {
 "records": len(rows),
 "original_verified_or_public_part": sum(r["original_status"] != "検索要約のみ" for r in rows),
 "independent_units_lower_bound": len(units),
 "independent_units_upper_bound": len(rows),
 "records_with_passage_count": sum(bool(r["passages"]) for r in rows),
 "independent_units_with_passage_count": len(pass_units),
 "passage_count_distribution": {k: sum(r["passages"] == k for r in rows) for k in ["0", "1", "2", "3", "4"]},
 "records_with_objective_score": sum(r["objective_score"] != "none" for r in rows),
 "claims": len(claims),
 "claim_lineages": len(set(lineage.values())),
 "claim_lineage_map": lineage,
 "same_person_groups": {g: {"ids": ids, "reason": why} for g, (ids, why) in SAME.items()},
}
json.dump(summary, open(os.path.join(H, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in summary.items() if k not in ("claim_lineage_map", "same_person_groups")}, ensure_ascii=False))
