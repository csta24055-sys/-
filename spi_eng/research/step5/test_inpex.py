import os, sys, csv, tempfile
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
import inpex_fusion as f
base = f.run()
assert abs(base["drop_official_faq"]["H3"] - base["sensitivity"]["r_scale=1.0|rho=0.9"]["H3"]) > 0.05, "公式FAQの有無が結果に反映されない"
# 対策サイトの3件は同一系統：3件を100件に複製しても効果はほぼ増えない
its = f.items()
site = [i for i in its if i["lineage"] == "inpex_spi_sites"][0]
many = f.fuse(its + [dict(site, id=f"x{k}") for k in range(100)], rho=0.9)["H3"]
assert many - f.fuse(its, rho=0.9)["H3"] < 0.05, many
# レコードの型を書き換えると結果が変わる(実データの反映)
rows = list(csv.DictReader(open(os.path.join(H, "inpex_records.csv"), encoding="utf-8")))
for r in rows:
    if r["id"] == "IO1": r["hyp_type"] = "H3_H4"
fd, p = tempfile.mkstemp(suffix=".csv"); os.close(fd)
with open(p, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
alt = f.run(p); os.remove(p)
assert alt["sensitivity"]["r_scale=1.0|rho=0.9"]["H3"] > base["sensitivity"]["r_scale=1.0|rho=0.9"]["H3"] + 0.1
print("INPEX TESTS PASSED")
