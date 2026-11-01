#!/usr/bin/env python3
"""図表の生成。使い方: python3 tools/make_figures.py MODEL_DIR CATALOG OUTDIR [ROUTES_EVAL]"""
import csv, sys, os, collections
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
font_manager.fontManager.addfont("/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf")
plt.rcParams["font.family"] = "IPAGothic"
model, catalog, out = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
names = {r["id"]: r["organization"][:14] for r in csv.DictReader(open(catalog, encoding="utf-8"))}
rk = collections.defaultdict(dict)
for r in csv.DictReader(open(os.path.join(model, "rankings_by_value_system.csv"), encoding="utf-8")):
    rk[r["system"]][r["id"]] = int(r["rank"])
systems = list(rk)
sens = list(csv.DictReader(open(os.path.join(model, "sensitivity_balanced.csv"), encoding="utf-8")))
ids = [r["id"] for r in sens[:16]]
# 図1 評価体系×選択肢の順位ヒートマップ
fig, ax = plt.subplots(figsize=(11, 6.5))
M = [[rk[s].get(i, 40) for s in systems] for i in ids]
im = ax.imshow(M, cmap="Blues_r", vmin=1, vmax=25, aspect="auto")
ax.set_xticks(range(len(systems))); ax.set_xticklabels([s.split("_", 1)[1] for s in systems], rotation=55, ha="right", fontsize=8)
ax.set_yticks(range(len(ids))); ax.set_yticklabels([f"{i} {names[i]}" for i in ids], fontsize=8)
for y, row in enumerate(M):
    for x, v in enumerate(row):
        ax.text(x, y, v, ha="center", va="center", fontsize=7, color="white" if v <= 6 else "#333")
ax.set_title("図1 評価体系別の順位（数値が小さいほど上位）")
fig.colorbar(im, ax=ax, label="順位"); fig.tight_layout(); fig.savefig(os.path.join(out, "fig1_rank_heatmap.png"), dpi=150)
# 図2 感度分析
fig, ax = plt.subplots(figsize=(9, 5))
top = sens[:14][::-1]
ax.barh([f'{r["id"]} {names[r["id"]]}' for r in top], [float(r["top5_frequency"]) for r in top], color="#3b6ea5")
ax.set_xlabel("重みを摂動させた4,000回のうち上位5位に入った割合"); ax.set_xlim(0, 1)
ax.set_title("図2 総合評価の重みに対する頑健性（感度分析）")
fig.tight_layout(); fig.savefig(os.path.join(out, "fig2_sensitivity.png"), dpi=150)
# 図3 ルートの期待値と最悪値
if len(sys.argv) > 4 and os.path.exists(sys.argv[4]):
    R = list(csv.DictReader(open(sys.argv[4], encoding="utf-8")))
    fig, ax = plt.subplots(figsize=(9, 6))
    for r in R:
        c = "#c0392b" if r["status"].startswith("有力") else ("#7f8c8d" if r["status"].startswith("不採用") else "#e1a23b")
        ax.scatter(float(r["worst"]), float(r["EV"]), color=c, s=30 + 120 * float(r["p_mid"]))
        ax.annotate(r["route_id"], (float(r["worst"]), float(r["EV"])), fontsize=7, xytext=(3, 2), textcoords="offset points")
    ax.set_xlabel("最悪ケースの効用（失敗時の到達先の総合スコア）"); ax.set_ylabel("期待効用（中央確率）")
    ax.set_title("図3 複合ルートの期待値と下限（赤=有力、橙=条件付き・補助、灰=不採用。円の大きさ=成功確率）")
    fig.tight_layout(); fig.savefig(os.path.join(out, "fig3_routes.png"), dpi=150)
print("figures ->", out)
