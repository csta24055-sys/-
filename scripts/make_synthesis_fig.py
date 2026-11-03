"""研究の系統・因果関係図（docs/figures/synthesis_lineage.png）"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
for f in ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",):
    if Path(f).exists():
        font_manager.fontManager.addfont(f)
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=f).get_name()

N = {  # id: (x=年度, y=系統, ラベル, 検証状態)
    "2018": (2018, 2, "2018 空調室EPで\n住宅全体を除塵", "一部"),
    "2019": (2019, 2, "2019 臭気・粗大粒子\nと扉開閉", "一部"),
    "2020": (2020, 2, "2020 線香発生量\n多室モデル", "済"),
    "2021": (2021, 2, "2021 β・Mの同定\n落下粉塵", "一部"),
    "2022": (2022, 2, "2022 中間粒径の\n行方（シミュ）", "済"),
    "2023": (2023, 1, "2023 生活行動\n発塵量同定", "一部"),
    "2024": (2024, 1, "2024 空調方式×\n8住宅の実態", "済"),
    "2025": (2025, 1, "2025 西日本の外気\nI/O・年間予測", "一部"),
    "2026": (2026, 0, "2026 EP単体特性\nバイパス・CADR", "一部"),
    "2013": (2018, 0, "2013 EP付着粉塵\nの組成分析", "一部"),
}
E = [("2018", "2019", "大粒径へ"), ("2019", "2020", "再現性"), ("2020", "2021", "沈着の同定"), ("2021", "2022", "β→入力"),
     ("2022", "2023", "実生活へ"), ("2023", "2024", "多点測定"), ("2024", "2025", "高外気地域"), ("2025", "2026", "装置の最適化"),
     ("2018", "2026", "EP効率 96%→82〜92%"), ("2013", "2026", "副生成物・組成は未接続")]
COL = {"済": "#0f5b5c", "一部": "#b07a12"}
fig, ax = plt.subplots(figsize=(13, 5.4))
for a, b, lab in E:
    xa, ya = N[a][0], N[a][1]; xb, yb = N[b][0], N[b][1]
    ax.annotate("", xy=(xb - 0.32, yb), xytext=(xa + 0.32, ya), arrowprops=dict(arrowstyle="->", color="#777", lw=1.2, connectionstyle="arc3,rad=0.12" if ya != yb else "arc3"))
    ax.text((xa + xb) / 2, (ya + yb) / 2 + 0.22, lab, fontsize=7.5, ha="center", color="#555")
for k, (x, y, lab, st) in N.items():
    ax.text(x, y, lab, ha="center", va="center", fontsize=8.5, color="white", bbox=dict(boxstyle="round,pad=0.4", fc=COL[st], ec="none"))
for y, name in ((2, "制御実験系（実験BOX・実験住宅・シミュレーション）"), (1, "実住宅の観測系（多点センサー・I/O・回帰）"), (0, "装置工学系・組成分析")):
    ax.text(2017.25, y, name, fontsize=8.5, ha="left", va="center", rotation=0, color="#333")
ax.set_xlim(2017.2, 2026.7); ax.set_ylim(-0.7, 2.7); ax.axis("off")
ax.set_title("井口研究室 空気清浄度研究の系統と因果関係（色: 濃緑=主要結論を原データで検証済み, 茶=一部検証）", fontsize=10)
fig.tight_layout()
out = ROOT / "docs" / "figures" / "synthesis_lineage.png"
fig.savefig(out, dpi=130)
print(out)
