import csv, os, json
H = os.path.dirname(os.path.abspath(__file__))
rows = []
ver = list(csv.DictReader(open(os.path.join(H, "../step2/verified_records.csv"), encoding="utf-8")))
for r in ver:
    if r["passages"]:
        rows.append(["q_rep(報告者の3題以上の割合)", r["report_id"], r["url"], r["passages"], "実データ"])
for r in csv.DictReader(open(os.path.join(H, "../step3/reliability.csv"), encoding="utf-8")):
    if r["claim_type"]:
        rows.append(["仮説の事前確率(STEP3の統合)", r["id"], "", r["claim_type"], "主張(信頼性は仮定)"])
for p, v in [("s(報告の偏り)", "1,2,4"), ("Q_H(仮説ごとの3題以上の割合)", "0.2/0.5/0.8"), ("slope", "0.5,1.0"), ("rho(基礎能力と英語の相関)", "0,0.3,0.5"), ("基礎能力 上位25%以内", "本人申告")]:
    rows.append([p, "-", "", v, "仮定(識別不能)" if "本人" not in v else "本人申告の条件"])
with open(os.path.join(H, "trace.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["quantity", "source_id", "url", "value", "type"]); w.writerows(rows)
print(len(rows))
