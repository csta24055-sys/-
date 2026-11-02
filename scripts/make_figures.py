"""出典付き図表（SVG）を docs/figures/ に生成する。外部ライブラリ不要。

  python scripts/make_figures.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from aqros import models as M  # noqa: E402

OUT = ROOT / "docs" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
COL = ["#0f5b5c", "#c8553d", "#3a6ea5", "#8a6d1e", "#6b4c9a"]


def svg_lines(name, title, series, xlabel, ylabel, source, xmax=None, ymax=None, logy=False, logx=False):
    import math
    W, H, L, R, T, B = 660, 420, 64, 140, 40, 84
    xs = [x for _, pts in series for x, _ in pts]
    ys = [y for _, pts in series for _, y in pts if y is not None]
    tx = (lambda v: math.log10(v)) if logx else (lambda v: v)
    ty = (lambda v: math.log10(v)) if logy else (lambda v: v)
    x0, x1 = tx(min(xs)), tx(xmax or max(xs))
    y0, y1 = (ty(min(ys)) if logy else 0), ty(ymax or max(ys) * 1.08)
    px = lambda v: L + (tx(v) - x0) / (x1 - x0) * (W - L - R)
    py = lambda v: H - B - (ty(v) - y0) / (y1 - y0) * (H - T - B)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="sans-serif" font-size="12">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>', f'<text x="{L}" y="24" font-size="14" font-weight="bold">{title}</text>',
         f'<line x1="{L}" y1="{H-B}" x2="{W-R}" y2="{H-B}" stroke="#333"/><line x1="{L}" y1="{T}" x2="{L}" y2="{H-B}" stroke="#333"/>']
    for i in range(6):
        fy = y0 + (y1 - y0) * i / 5
        yv = 10 ** fy if logy else fy
        o.append(f'<line x1="{L}" x2="{W-R}" y1="{py(yv):.1f}" y2="{py(yv):.1f}" stroke="#e5e5e5"/><text x="{L-6}" y="{py(yv)+4:.1f}" text-anchor="end">{(f'{yv:.3g}' if (logy or abs(yv) < 100) else f'{yv:.0f}')}</text>')
        fx = x0 + (x1 - x0) * i / 5
        xv = 10 ** fx if logx else fx
        o.append(f'<text x="{px(xv):.1f}" y="{H-B+16}" text-anchor="middle">{xv:.3g}</text>')
    o.append(f'<text x="{(L+W-R)/2}" y="{H-B+34}" text-anchor="middle">{xlabel}</text>')
    o.append(f'<text transform="translate(16,{(T+H-B)/2}) rotate(-90)" text-anchor="middle">{ylabel}</text>')
    for k, (label, pts) in enumerate(series):
        segs, pen = [], False
        for x, y in pts:
            if y is None:
                pen = False
                continue
            segs.append(f"{'L' if pen else 'M'}{px(x):.1f},{py(y):.1f}")
            pen = True
        d = " ".join(segs)
        o.append(f'<path d="{d}" fill="none" stroke="{COL[k % 5]}" stroke-width="2"/>')
        o.append(f'<rect x="{W-R+10}" y="{T+k*18}" width="12" height="3" fill="{COL[k % 5]}"/><text x="{W-R+26}" y="{T+k*18+5}">{label}</text>')
    lines = [source[i:i + 62] for i in range(0, len(source), 62)][:2]
    for j, ln in enumerate(lines):
        o.append(f'<text x="8" y="{H-24+j*13}" font-size="10" fill="#555">{ln}</text>')
    o.append('</svg>')
    (OUT / f"{name}.svg").write_text("\n".join(o), encoding="utf-8")


def main():
    rows = []
    for law, lab in (("fit", "式(2)全域"), ("quadratic_ext", "二乗則外挿")):
        series_c, series_p = [], []
        for n in (5, 10, 15, 20):
            res = M.bypass_sweep(n, "中", steps=21, ep_law=law)
            series_c.append((f"中×{n}台", [(r.opening_ratio * 100, r.cadr if r.within_fan_limit else None) for r in res]))
            series_p.append((f"中×{n}台", [(r.opening_ratio * 100, r.power_total) for r in res]))
            rows += [[law, n, r.opening_ratio, round(r.dp, 2), round(r.q_ep, 1), round(r.q_bp, 1), round(r.eta, 4), round(r.cadr, 1), round(r.power_total, 2), r.within_fan_limit] for r in res]
        src = f"【計算結果】本アプリ再実装（抵抗則: {lab}）。入力式・実測値の出典: 2026年度中間梗概 Box 2525808527679（S-2026-01）。定風量限界超過点は除外"
        svg_lines(f"fig_bypass_cadr_{law}", f"バイパス開口率とCADR（{lab}）", series_c, "バイパス開口率 [%]", "CADR [m³/h]", src)
        svg_lines(f"fig_bypass_power_{law}", f"バイパス開口率と送風機電力（{lab}）", series_p, "バイパス開口率 [%]", "電力 [W]", src)
    with open(OUT / "bypass_sweep.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["law", "n_units", "opening", "dp_Pa", "Q_EP", "Q_BP", "eta", "CADR", "power_W", "within_limit"]); w.writerows(rows)
    ds = [0.3 * 1.25 ** i for i in range(30)]
    svg_lines("fig_deposition", "粒径と重力沈降による沈着係数（H=2.4 m, ρp=1000）", [("重力沈降 β", [(d, M.deposition_coefficient(d) * 3600) for d in ds])],
              "粒径 [μm]", "β [1/h]", "【計算結果】式 β=U/H（2021年度梗概 S-2021-01 式(2)(4)）。参考: 2021年度BOX線香β=0.47 /h（1.3e-4 1/s）", logx=True, logy=True)
    ep = [("0.3-0.5 μm", [(q, M.ep_efficiency(q, "0.3-0.5") * 100) for q in range(100, 760, 10)]), ("5.0 μm-", [(q, M.ep_efficiency(q, "5.0-") * 100) for q in range(100, 760, 10)])]
    svg_lines("fig_ep_efficiency", "電気集塵機の風量と集塵効率（端点は実測、中間は線形補間）", ep, "通過風量 [m³/h]", "集塵効率 [%]",
              "端点【確認事実】S-2026-01 図3（100 m³/h ≥95%, 750 m³/h 82〜92%）。中間値は【仮定】", ymax=100)
    print("figures:", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
