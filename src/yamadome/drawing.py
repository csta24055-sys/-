"""根切り平面図・Y3通り根切り断面図の作図（Matplotlib ベクター出力）。

図は実寸 1/100 で作る: 1000 mm（実長）= 10 mm（紙上）。PNG と PDF(ベクター) を出力する。
"""
from __future__ import annotations
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Polygon as MplPoly, Rectangle, Circle
from .geometry import final_depth_pieces, section_profile

for _f in ("/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",):
    try:
        font_manager.fontManager.addfont(_f)
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=_f).get_name()
    except Exception:
        pass

DEPTH_STYLE = {   # 深さ別の塗り・ハッチ（色だけに頼らずハッチでも区別）
    1.65: ("#dfeaf6", ""),
    1.85: ("#bcd5ee", "//"),
    2.10: ("#f6e3b4", "\\\\"),
    2.20: ("#f2c09a", "xx"),
}
MM_PER_INCH = 25.4


def _fig_true_scale(w_mm, h_mm, scale):
    w_in = w_mm / scale / MM_PER_INCH
    h_in = h_mm / scale / MM_PER_INCH
    fig = plt.figure(figsize=(w_in, h_in))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax


def _watermark(ax, text):
    if text:
        ax.text(0.5, 0.5, text, transform=ax.transAxes, ha="center", va="center",
                fontsize=22, color="red", alpha=0.25, rotation=20, zorder=50)


def _dim_h(ax, x0, x1, y, label, fs=5):
    ax.annotate("", (x0, y), (x1, y), arrowprops=dict(arrowstyle="<->", lw=0.4, shrinkA=0, shrinkB=0))
    ax.text((x0 + x1) / 2, y, label, ha="center", va="bottom", fontsize=fs)


def _dim_v(ax, x, y0, y1, label, fs=5):
    ax.annotate("", (x, y0), (x, y1), arrowprops=dict(arrowstyle="<->", lw=0.4, shrinkA=0, shrinkB=0))
    ax.text(x, (y0 + y1) / 2, label, ha="left", va="center", fontsize=fs, rotation=90)


def plan(site, zones, out_base, watermark=None):
    gx, gy = site.grid_x, site.grid_y
    a0 = zones[0][3]
    minx, miny, maxx, maxy = a0.bounds
    ret = site.raw["retaining"]
    n = ret.get("slope_ratio")
    slope_w = (n or 0) * site.base_depth * 1000
    m = 4000 + slope_w
    x_lo, x_hi = min(minx, min(gx.values())) - m, max(maxx, max(gx.values())) + m
    y_lo, y_hi = min(miny, min(gy.values())) - m, max(maxy, max(gy.values())) + m
    fig, ax = _fig_true_scale(x_hi - x_lo, y_hi - y_lo, site.raw["meta"]["scale"])
    ax.set_xlim(x_lo, x_hi); ax.set_ylim(y_lo, y_hi)

    for depth, g in final_depth_pieces(zones):
        fc, hatch = DEPTH_STYLE.get(round(depth, 2), ("#eeeeee", ".."))
        for p in getattr(g, "geoms", [g]):
            ax.add_patch(MplPoly(list(p.exterior.coords), closed=True, fc=fc, ec="k",
                                 lw=0.3, hatch=hatch, zorder=2))
            c = p.representative_point()
            ax.text(c.x, c.y, f"根切り底\nGL-{depth*1000:,.0f}", ha="center", va="center",
                    fontsize=4, zorder=6)
    ax.add_patch(MplPoly(list(a0.exterior.coords), closed=True, fill=False, ec="k", lw=0.9, zorder=5))

    # 法面（オープンカット）: 天端線を破線、法尻〜法肩をケバ線で表現
    if n:
        for side in ("west", "south", "north"):
            if ret[side] != "open_cut":
                continue
            if side == "west":
                ax.plot([minx - slope_w] * 2, [miny - slope_w, maxy + slope_w], "k--", lw=0.5)
                for yy in range(int(miny), int(maxy), 600):
                    ax.plot([minx - slope_w, minx], [yy, yy], "k-", lw=0.2)
            else:
                yb = miny if side == "south" else maxy
                yt = yb - slope_w if side == "south" else yb + slope_w
                ax.plot([minx - slope_w, maxx], [yt, yt], "k--", lw=0.5)
                for xx in range(int(minx), int(maxx), 600):
                    ax.plot([xx, xx], [yt, yb], "k-", lw=0.2)
        ax.text(minx - slope_w / 2, (miny + maxy) / 2, f"法面 1:{n}", rotation=90,
                ha="center", va="center", fontsize=4, bbox=dict(fc="w", ec="none", pad=0.3))
    else:
        ax.text(minx - 1500, (miny + maxy) / 2, "オープンカット\n（法勾配 未確定）", rotation=90,
                ha="center", va="center", fontsize=4, color="red")
    for side, (xx, yy) in {"西": (minx - 3000, maxy), "南": ((minx + maxx) / 2, miny - slope_w - 2000),
                           "北": ((minx + maxx) / 2, maxy + slope_w + 300)}.items():
        ax.text(xx, yy, f"{side}面 オープンカット", fontsize=4, ha="center")

    # 東面 親杭横矢板
    px = ret.get("soldier_pile_x_mm") or maxx
    ax.plot([px, px], [miny, maxy], color="k", lw=1.4, zorder=7)
    for yy in range(int(miny), int(maxy) + 1, 1000):
        ax.plot([px - 150, px + 150], [yy, yy], "k-", lw=0.6, zorder=7)
        ax.plot([px, px], [yy - 150, yy + 150], "k-", lw=0.6, zorder=7)
    ax.text(px + 400, (miny + maxy) / 2, "東面 親杭横矢板", rotation=90, fontsize=4, va="center")

    # 通り芯・符号・寸法
    for k, x in gx.items():
        ax.plot([x, x], [y_lo + 1200, y_hi - 1200], color="0.3", lw=0.3, ls="-.", zorder=8)
        ax.add_patch(Circle((x, y_hi - 800), 400, fill=False, lw=0.4)); ax.text(x, y_hi - 800, k, ha="center", va="center", fontsize=4)
    for k, y in gy.items():
        ax.plot([x_lo + 1200, x_hi - 1200], [y, y], color="0.3", lw=0.3, ls="-.", zorder=8)
        ax.add_patch(Circle((x_lo + 800, y), 400, fill=False, lw=0.4)); ax.text(x_lo + 800, y, k, ha="center", va="center", fontsize=4)
    xs = sorted(gx.values()); ys = sorted(gy.values())
    for a, b in zip(xs, xs[1:]):
        _dim_h(ax, a, b, y_hi - 1800, f"{b-a:,.0f}")
    _dim_h(ax, xs[0], xs[-1], y_hi - 2400, f"{xs[-1]-xs[0]:,.0f}")
    _dim_h(ax, minx, maxx, miny - 1200, f"根切り底 {maxx-minx:,.0f}")
    for a, b in zip(ys, ys[1:]):
        _dim_v(ax, x_hi - 1800, a, b, f"{b-a:,.0f}")
    _dim_v(ax, maxx + 1200, miny, maxy, f"根切り底 {maxy-miny:,.0f}")
    ax.text(x_lo + 300, y_lo + 300, "根切り図 1/100", fontsize=6)
    _watermark(ax, watermark)
    for ext in ("png", "pdf", "svg"):
        fig.savefig(f"{out_base}.{ext}", dpi=400)
    plt.close(fig)


def section(site, zones, out_base, axis="Y3", watermark=None):
    y = site.grid_y[axis]
    segs = section_profile(zones, y)
    gx = site.grid_x
    lv = site.raw["levels"]
    ret = site.raw["retaining"]
    n = ret.get("slope_ratio")
    x0 = segs[0][0]; x1 = segs[-1][1]
    dmax = max(s[2] for s in segs) * 1000
    slope_w = (n or 0) * segs[0][2] * 1000
    xl, xr = min(x0, min(gx.values())) - 3000 - slope_w, max(x1, max(gx.values())) + 3000
    yb, yt = -dmax - 2500, lv["1FL"] + 2200
    fig, ax = _fig_true_scale(xr - xl, yt - yb, site.raw["meta"]["scale"])
    ax.set_xlim(xl, xr); ax.set_ylim(yb, yt)

    # 地盤と掘削形状
    prof = [(x0 - slope_w, 0), (x0, -segs[0][2] * 1000)]
    for a, b, d in segs:
        prof += [(a, -d * 1000), (b, -d * 1000)]
    east_vertical = ret["east"] != "open_cut"
    prof += [(x1, 0)] if east_vertical else [(x1 + slope_w, 0)]
    ground = [(xl, 0)] + prof + [(xr, 0), (xr, yb + 300), (xl, yb + 300)]
    ax.add_patch(MplPoly(ground, closed=True, fc="#e9e2d0", ec="none", hatch="..", lw=0, zorder=1))
    ax.plot(*zip(*prof), "k-", lw=0.9, zorder=4)
    ax.plot([xl, x0 - slope_w], [0, 0], "k-", lw=0.6); ax.plot([x1, xr], [0, 0], "k-", lw=0.6)
    if east_vertical:
        ax.plot([x1, x1], [300, -dmax - 1500], "k-", lw=1.6, zorder=5)
        ax.text(x1 + 200, -dmax - 1300, "親杭横矢板", fontsize=4)
    if not n:
        ax.text(x0 - 300, -500, "法面（勾配未確定）", fontsize=4, color="red", ha="right")

    # レベル
    for name, lvl, ls in (("GL±0", 0, "-"), ("1FL=GL+500", lv["1FL"], "--")):
        ax.plot([xl + 300, xr - 300], [lvl, lvl], color="0.3", lw=0.4, ls=ls)
        ax.text(xl + 400, lvl + 60, name, fontsize=4)
    # 通り芯
    for k, x in gx.items():
        ax.plot([x, x], [yb + 300, yt - 1000], color="0.3", lw=0.3, ls="-.")
        ax.add_patch(Circle((x, yt - 600), 380, fill=False, lw=0.4)); ax.text(x, yt - 600, k, ha="center", va="center", fontsize=4)
    xs = sorted(gx.values())
    for a, b in zip(xs, xs[1:]):
        _dim_h(ax, a, b, yt - 1300, f"{b-a:,.0f}")
    # 深さ寸法
    done = set()
    for a, b, d in segs:
        if d in done:
            continue
        done.add(d)
        xm = (a + b) / 2
        _dim_v(ax, xm, -d * 1000, 0, f"{d*1000:,.0f}")
    # 基礎（寸法が分かるもののみ）
    for f in site.raw.get("footings", []):
        sz = f.get("size_mm")
        if not sz or f.get("section_x_mm") is None:
            continue
        w, depth_body = sz.get("width"), sz.get("height")
        if w is None or depth_body is None:
            continue
        xc = f["section_x_mm"]; bot = f["bottom_GL_mm"]
        ax.add_patch(Rectangle((xc - w / 2, bot), w, depth_body, fc="0.85", ec="k", lw=0.5, zorder=6))
        ax.add_patch(Rectangle((xc - w / 2 - 100, f["subgrade_GL_mm"]), w + 200, 100, fc="0.6", ec="k", lw=0.3, zorder=6))
        ax.text(xc, bot + depth_body / 2, f["name"], ha="center", va="center", fontsize=4, zorder=7)
    ax.text(xl + 300, yb + 500, f"根切り断面図（{axis}通り） 1/100", fontsize=6)
    _watermark(ax, watermark)
    for ext in ("png", "pdf", "svg"):
        fig.savefig(f"{out_base}.{ext}", dpi=400)
    plt.close(fig)
    return segs
