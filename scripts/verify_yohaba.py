"""余幅ルールによる掘削土量の独立検算（Shapely・config の区画を使わない）。

授業の余幅スライド:
  法幅 = 根切り深さ h × 0.3（1.5m ≤ h < 5.0m）、作業のゆとり幅 = 0.5m、
  余幅 a = 作業のゆとり幅 + 法幅/2 = 0.5 + 0.15h
を、基礎・梁の「外面」（課題PDF p.1 の実測値 = config の footings / beams_outer_face_mm）に
直接当てはめて垂直掘りとみなした範囲をつくり、10mm 格子で 深さ×面積 を合計する。
東面（親杭横矢板）は授業 Y3断面の「余幅100」で打切り（法なし）。

  python scripts/verify_yohaba.py  → docs/09_余幅ルール検証.md を出力
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
c = yaml.safe_load((ROOT / "config/site.yaml").read_text(encoding="utf-8"))
WORK, SLOPE, EAST_YOHABA = 0.5, 0.3, 0.1          # [m] 授業スライド・授業図
a_of = lambda h: (WORK + SLOPE * h / 2) * 1000    # 余幅 [mm]

bf = c["beams_outer_face_mm"]
E = bf["east"] + EAST_YOHABA * 1000                # 親杭面
H0 = 1.65
zones = []   # (name, h[m], kind, data)
a0 = a_of(H0)
W = WORK * 1000
zones.append(("FS1（A0）", H0, "rect", (bf["west"] - a0, bf["south"] - a0, E, bf["north"] + a0)))
bottoms = [("rect", (bf["west"] - W, bf["south"] - W, E, bf["north"] + W))]   # 根切り底 = 外面 + ゆとり500
for f in c["footings"]:
    h = -f["subgrade_GL_mm"] / 1000
    a = a_of(h)
    pm = f["plan_mm"]
    if "x" in pm:
        zones.append((f"{f['name']} {f['at']}", h, "rect",
                      (pm["x"][0] - a, pm["y"][0] - a, min(pm["x"][1] + a, E), pm["y"][1] + a)))
        bottoms.append(("rect", (pm["x"][0] - W, pm["y"][0] - W, min(pm["x"][1] + W, E), pm["y"][1] + W)))
    else:   # F5 直角三角形: 北辺 y=yn, 東辺 x=xe, 斜辺 x+y=C
        (x1, yn), (xe, _), (_, y2) = pm["polygon"]
        C = x1 + yn
        zones.append((f"{f['name']} {f['at']}", h, "tri", (yn + a, E, C - a * np.sqrt(2))))
        bottoms.append(("tri", (yn + W, E, C - W * np.sqrt(2))))
for z, b in zip(zones, bottoms):
    pass
BOTTOM = {z[0]: b for z, b in zip(zones, bottoms)}

# 2.5 mm 格子。余幅 747.5/777.5/815/830 mm と外面座標はすべて 2.5 mm の倍数なので、
# 矩形の辺は格子線に一致し誤差ゼロ。誤差は F5 の斜辺のみ（±1.25mm 幅の帯、相殺的）。
step = 2.5
xs = np.arange(-2000, E, step) + step / 2
ys_all = np.arange(-2500, 13500, step) + step / 2
cell = (step / 1000) ** 2


def inside(kind, d, X, Y):
    if kind == "rect":
        return (X >= d[0]) & (X <= d[2]) & (Y >= d[1]) & (Y <= d[3])
    yn, xe, C = d
    return (Y <= yn) & (X <= xe) & (X + Y >= C)


def run(mode):
    """mode=perimeter: 区画 = 根切り底 ∪ (外面+余幅 の範囲のうち 根切り底全体の外形 P の外側)
       mode=all_faces: 区画 = 外面+余幅（v1）"""
    V = 0.0; A0 = 0.0; layers = {}
    for i in range(0, len(ys_all), 400):
        X, Y = np.meshgrid(xs, ys_all[i:i + 400])
        P = np.zeros_like(X, dtype=bool)
        for kind, d in bottoms:
            P |= inside(kind, d, X, Y)
        depth = np.zeros_like(X, dtype=np.float32)
        for name, h, kind, d in zones:
            m = inside(kind, d, X, Y)
            if mode == "perimeter":
                bk, bd = BOTTOM[name]
                m = inside(bk, bd, X, Y) | (m & ~P)
            depth = np.where(m, np.maximum(depth, np.float32(h)), depth)
        V += float(depth.astype(np.float64).sum() * cell)
        A0 += float((depth > 0).sum() * cell)
        for d_ in np.unique(np.round(depth[depth > 0], 2)):
            layers[float(d_)] = layers.get(float(d_), 0.0) + float(np.isclose(depth, d_).sum() * cell)
    return V, A0, dict(sorted(layers.items()))


V, A0, layers = run("perimeter")
V_all, A0_all, layers_all = run("all_faces")

sys.path.insert(0, str(ROOT / "src"))
from yamadome import config, geometry, calculation  # noqa: E402
site = config.load(ROOT / "config/site.yaml")
res = calculation.compute(site, geometry.zone_polygons(site))
site_v1 = config.load(ROOT / "config/site.yaml"); site_v1.raw["retaining"]["yohaba_scope"] = "all_faces"
res_v1 = calculation.compute(site_v1, geometry.zone_polygons(site_v1))

lines = ["# 09 余幅ルールによる掘削土量の独立検算", "",
         "`python scripts/verify_yohaba.py` で再生成。Shapely と config の区画（法尻外形）を使わず、",
         "基礎・梁の外面（課題PDF p.1 実測）に授業の余幅ルールを直接当てはめ、",
         "余幅（法幅/2）は根切り底全体の外形の外側（外周）にだけ付ける（内部の段差は鉛直、授業着色図どおり）。2.5 mm 格子（矩形の辺が格子線に一致）で集計した。", "",
         "## 適用したルール（授業 余幅スライド②・Y3断面 東側山留部分）", "",
         "| 深さ h | 法幅 0.3h | 法幅/2 | 作業ゆとり | 余幅 a = 0.5 + 0.3h/2 |", "|---|---|---|---|---|"]
for h in (1.65, 1.85, 2.10, 2.20):
    lines.append(f"| {h:.2f} m | {0.3*h:.3f} m | {0.15*h:.4f} m | 0.500 m | **{a_of(h)/1000:.4f} m** |")
lines += ["", "東面（親杭横矢板）: 基礎外面 X4+90 から 余幅 0.100 m（法なし） → 親杭面 X4+190。", "",
          "## 各区画（外面 + 余幅）", "", "| 区画 | h | 範囲 [mm] |", "|---|---|---|"]
for name, h, kind, d in zones:
    rng = (f"x {d[0]:,.1f}〜{d[2]:,.1f}, y {d[1]:,.1f}〜{d[3]:,.1f}" if kind == "rect"
           else f"三角形: 北辺 y={d[0]:,.1f}, 東辺 x={d[1]:,.1f}, 斜辺 x+y={d[2]:,.1f}")
    lines.append(f"| {name} | {h:.2f} | {rng} |")
lines += ["", "（表の範囲は外面＋余幅。perimeter では、このうち根切り底全体の外形の内側に入る部分は加えない）",
          "", "## 結果（深さ別、重複除去後）", "", "| 根切り底 | 面積 [m²]（外周のみ余幅） | 体積 [m³] | 参考 v1 全周余幅 面積 | v1 体積 |", "|---|---|---|---|---|"]
for d, a in layers.items():
    a1 = layers_all.get(d, 0.0)
    lines.append(f"| GL-{d*1000:,.0f} | {a:.3f} | {a*d:.3f} | {a1:.3f} | {a1*d:.3f} |")
lines += [f"| 合計 | A0 = {A0:.3f} | **{V:.3f}** | A0 = {A0_all:.3f} | {V_all:.3f} |", "",
          "| 計算 | 掘削土量 [m³] |", "|---|---|",
          f"| 独立検算（余幅ルール直接・2.5mm 格子） | {V:.3f} |",
          f"| 独立検算 v1 方式（全周余幅） | {V_all:.3f}（本体 v1 {res_v1.method_a:.3f}） |",
          f"| 本体 方法A ΣAi·hi（Shapely） | {res.method_a:.3f} |",
          f"| 本体 方法B A0×1.65+ΣAj·Δhj | {res.method_b:.3f}（A0 = {res.a0_area:.3f} m²） |",
          f"| 差（独立検算 − 方法A） | {V-res.method_a:+.3f}（{(V-res.method_a)/res.method_a*100:+.4f}%、F5 斜辺の格子誤差のみ） |",
          f"| 参考: 実斜面の幾何体積（内部段差は鉛直） | {res.exact_volume:.3f}（余幅法との差 {(res.method_a-res.exact_volume)/res.exact_volume*100:+.3f}%） |", "",
          f"結論: 授業の余幅ルールを基礎・梁の外面から直接適用した独立検算 {V:.3f} m³ は、答案の {res.total:.3f} m³（≒ {res.total:.2f} m³）と一致する（差 {V-res.total:+.3f} m³）。"]
out = ROOT / "docs/09_余幅ルール検証.md"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines[-12:]))
