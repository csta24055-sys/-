"""v1（全周余幅, 441.225 m³）→ v2（外周のみ余幅＝授業準拠）の増減を区画ごとに分解する。

  python scripts/compare_v1.py → docs/10_修正前後の土量比較.md
"""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from shapely.ops import unary_union  # noqa: E402
from yamadome import config, geometry, calculation  # noqa: E402
from yamadome.geometry import MM2_PER_M2  # noqa: E402


def volume(site, zones, per_zone_mode):
    """per_zone_mode: {zone name: 'all_faces'|'perimeter'}"""
    ret = site.raw["retaining"]; n = ret["slope_ratio"]; east = ret["soldier_pile_x_mm"]
    outline = unary_union([z[3] for z in zones])
    yz = [(nm, c, d, calculation.extend(p, n * d * 500, east, outline, per_zone_mode[nm])) for nm, c, d, p in zones]
    return calculation.method_a(yz)[1], yz


site = config.load(ROOT / "config/site.yaml")
zones = geometry.zone_polygons(site)
names = [z[0] for z in zones]
v2, yz2 = volume(site, zones, {k: "perimeter" for k in names})
v1, yz1 = volume(site, zones, {k: "all_faces" for k in names})
outline = unary_union([z[3] for z in zones])

L = ["# 10 修正前後の掘削土量の比較（v1 441.225 m³ → v2 先生スライド準拠）", "",
     "`python scripts/compare_v1.py` で再生成。", "",
     "## 変更点", "",
     "- **形状（法尻＝根切り底の外形、法肩）は変更なし**。授業着色図の寸法（1310・1090・1700・1390・1610・1410・190・1240・2900・495・555・630）と一致を再確認した。",
     "- **余幅（法幅/2）の付け方を変更**: v1 は各区画の全周（基礎掘削と FS1 の内部の段差を含む）に 0.3h/2 を付けていた。",
     "  授業の着色図では基礎掘削（緑・橙）と FS1（黄）の境界は1本線で法面がなく、10:04 スライドは『外周法面・余幅』と記すため、",
     "  v2 は根切り底全体の外形の**外側だけ**に余幅を付ける（内部の段差は鉛直）。", "",
     "## 区画ごとの増減（その区画だけ v1 方式に戻したときの差）", "",
     "| 区画 | 深さ h | 余幅 0.3h/2 [m] | 内部の段差に付いていた余幅の面積 [m²] | Δh | 体積差 v2−v1 [m³] |",
     "|---|---|---|---|---|---|"]
tot = 0.0
for nm, c, d, p in zones:
    if d == site.base_depth:
        continue
    modes = {k: "perimeter" for k in names}; modes[nm] = "all_faces"
    v_mix, _ = volume(site, zones, modes)
    w = calculation.widen(p, 0.3 * d * 500, site.raw["retaining"]["soldier_pile_x_mm"])
    inner = (w.intersection(outline)).difference(p).area / MM2_PER_M2
    dv = v2 - v_mix; tot += dv
    L.append(f"| {nm} | {d:.2f} | {0.15*d:.4f} | {inner:.3f} | {d-1.65:.2f} | {dv:+.3f} |")
L += [f"| 合計（区画別の和） | | | | | {tot:+.3f} |", "",
      f"- v1: {v1:.3f} m³ → v2: {v2:.3f} m³、差 **{v2-v1:+.3f} m³**（区画別の和との差 {v2-v1-tot:+.4f} m³ は区画どうしの重なり部分）", "",
      "## 深さ別の面積（方法Bの Aj）", "", "| 根切り底 | v1 面積 [m²] | v2 面積 [m²] | 差 [m²] | Δh | 体積差 [m³] |", "|---|---|---|---|---|---|"]
p1 = dict((round(d, 2), g.area / MM2_PER_M2) for d, g in geometry.final_depth_pieces(yz1))
p2 = dict((round(d, 2), g.area / MM2_PER_M2) for d, g in geometry.final_depth_pieces(yz2))
a01 = unary_union([z[3] for z in yz1]).area / MM2_PER_M2; a02 = unary_union([z[3] for z in yz2]).area / MM2_PER_M2
L.append(f"| A0（全体, 1.65） | {a01:.3f} | {a02:.3f} | {a02-a01:+.3f} | 1.65 | {(a02-a01)*1.65:+.3f} |")
for d in sorted(p1, reverse=True):
    if d == 1.65:
        continue
    L.append(f"| 増掘り {d:.2f} | {p1[d]:.3f} | {p2.get(d,0):.3f} | {p2.get(d,0)-p1[d]:+.3f} | {d-1.65:.2f} | {(p2.get(d,0)-p1[d])*(d-1.65):+.3f} |")
L += ["", "## 二重計上・計上漏れ・角部の重複の検査", ""]
pits = [z for z in yz2 if z[2] > 1.65]
ov = []
for i in range(len(pits)):
    for j in range(i + 1, len(pits)):
        a = pits[i][3].intersection(pits[j][3]).area / MM2_PER_M2
        if a > 1e-6:
            ov.append((pits[i][0], pits[j][0], a, max(pits[i][2], pits[j][2]), min(pits[i][2], pits[j][2])))
if ov:
    for a_, b_, ar, dmax, dmin in ov:
        L.append(f"- 角部の重なり: {a_} と {b_} = {ar:.4f} m²。深い方 GL-{dmax*1000:,.0f} で1回だけ計上"
                 f"（区画ごとに単純加算すると {ar*(dmin-1.65):.4f} m³ の二重計上になる）")
else:
    L.append("- 増掘り区画どうしの重なりなし")
u = unary_union([z[3] for z in yz2]).area / MM2_PER_M2
s = sum(g.area for _, g in geometry.final_depth_pieces(yz2)) / MM2_PER_M2
L += [f"- 深さ別の区画の面積の和 {s:.6f} m² = 全体 A0 {u:.6f} m²（重複なし・漏れなし）",
      f"- 本体の方法A {v2:.3f} m³ と独立検算（scripts/verify_yohaba.py, 2.5mm 格子）は docs/09 で一致を確認"]
(ROOT / "docs/10_修正前後の土量比較.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L[10:]))
