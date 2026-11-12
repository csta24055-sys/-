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


def _footing_poly(f):
    from shapely.geometry import Polygon, box
    pm = f.get("plan_mm") or {}
    if "polygon" in pm:
        return Polygon(pm["polygon"])
    if "x" in pm and "y" in pm:
        return box(pm["x"][0], pm["y"][0], pm["x"][1], pm["y"][1])
    return None


def _patch(ax, g, **kw):
    for p in getattr(g, "geoms", [g]):
        if p.is_empty or p.geom_type != "Polygon":
            continue
        ax.add_patch(MplPoly(list(p.exterior.coords), closed=True, **kw))


def plan(site, zones, out_base, watermark=None):
    from shapely.ops import unary_union
    from .calculation import widen
    gx, gy = site.grid_x, site.grid_y
    ret = site.raw["retaining"]
    n = ret.get("slope_ratio") or 0
    east = ret.get("soldier_pile_x_mm")
    bottom = unary_union([z[3] for z in zones])
    top = unary_union([widen(z[3], n * z[2] * 1000, east) for z in zones])
    minx, miny, maxx, maxy = top.bounds
    x_lo, x_hi = minx - 3800, maxx + 3600
    y_lo, y_hi = miny - 3600, maxy + 3800
    fig, ax = _fig_true_scale(x_hi - x_lo, y_hi - y_lo, site.raw["meta"]["scale"])
    ax.set_xlim(x_lo, x_hi); ax.set_ylim(y_lo, y_hi)

    # 法面（法肩〜法尻）
    _patch(ax, top.difference(bottom), fc="#efe2c8", ec="none", hatch="|||", lw=0, zorder=1)
    _patch(ax, top, fill=False, ec="k", lw=0.5, ls="--", zorder=3)
    # 根切り底（深さ別）
    for depth, g in final_depth_pieces(zones):
        fc, hatch = DEPTH_STYLE.get(round(depth, 2), ("#eeeeee", ".."))
        _patch(ax, g, fc=fc, ec="k", lw=0.35, hatch=hatch, zorder=2)
    _patch(ax, bottom, fill=False, ec="k", lw=0.9, zorder=5)
    # 基礎（参考：破線）
    for f in site.raw.get("footings", []):
        fp = _footing_poly(f)
        if fp is None:
            continue
        _patch(ax, fp, fill=False, ec="0.25", lw=0.4, ls=(0, (3, 2)), zorder=6)
        c = fp.representative_point()
        ax.text(c.x, c.y, f"{f['name']}\nGL{f['subgrade_GL_mm']:,}", ha="center", va="center", fontsize=3.6, zorder=7,
                bbox=dict(fc="white", ec="none", alpha=0.7, pad=0.2))
    ax.text((gx["X2"] + gx["X3"]) / 2, (gy["Y2"] + gy["Y3"]) / 2, "FS1\n根切り底 GL-1,650", ha="center", va="center", fontsize=5, zorder=7)

    # 東面 親杭横矢板
    if east is not None:
        y0, y1 = bottom.bounds[1], bottom.bounds[3]
        ax.plot([east, east], [y0, y1], color="k", lw=1.6, zorder=8)
        yy = y0
        while yy <= y1 + 1:
            ax.plot([east - 150, east + 150], [yy, yy], "k-", lw=0.6, zorder=8)
            yy += 1000
        ax.text(east + 450, (y0 + y1) / 2, "東面：親杭横矢板（H形鋼 @1,000 程度・図示）", rotation=90, fontsize=4, va="center")
    ax.text(minx - 300, (miny + maxy) / 2, f"西面：オープンカット（法 1:{n}）", rotation=90, fontsize=4, va="center", ha="right")
    ax.text((minx + maxx) / 2, miny - 350, f"南面：オープンカット（法 1:{n}）", fontsize=4, ha="center", va="top")
    ax.text((minx + maxx) / 2, maxy + 350, f"北面：オープンカット（法 1:{n}）", fontsize=4, ha="center", va="bottom")

    # 通り芯・符号・寸法
    for k, x in gx.items():
        ax.plot([x, x], [y_lo + 1300, y_hi - 1300], color="0.35", lw=0.3, ls="-.", zorder=9)
        ax.add_patch(Circle((x, y_hi - 900), 400, fill=False, lw=0.4)); ax.text(x, y_hi - 900, k, ha="center", va="center", fontsize=4)
    for k, y in gy.items():
        ax.plot([x_lo + 1300, x_hi - 1300], [y, y], color="0.35", lw=0.3, ls="-.", zorder=9)
        ax.add_patch(Circle((x_lo + 900, y), 400, fill=False, lw=0.4)); ax.text(x_lo + 900, y, k, ha="center", va="center", fontsize=4)
    xs = sorted(gx.values()); ys = sorted(gy.values())
    for a, b in zip(xs, xs[1:]):
        _dim_h(ax, a, b, y_hi - 1900, f"{b-a:,.0f}")
    _dim_h(ax, xs[0], xs[-1], y_hi - 2500, f"{xs[-1]-xs[0]:,.0f}")
    bx0, by0, bx1, by1 = zones[0][3].bounds
    _dim_h(ax, bx0, xs[0], miny - 1100, f"{xs[0]-bx0:,.0f}")
    _dim_h(ax, xs[-1], bx1, miny - 1100, f"{bx1-xs[-1]:,.0f}")
    _dim_h(ax, bx0, bx1, miny - 1700, f"根切り底（FS1）{bx1-bx0:,.0f}")
    for a, b in zip(ys, ys[1:]):
        _dim_v(ax, x_hi - 1900, a, b, f"{b-a:,.0f}")
    _dim_v(ax, x_hi - 1200, by0, ys[0], f"{ys[0]-by0:,.0f}")
    _dim_v(ax, x_hi - 1200, ys[-1], by1, f"{by1-ys[-1]:,.0f}")
    # 凡例
    lx, ly = x_lo + 400, y_lo + 300
    for i, (d, lab) in enumerate([(1.65, "GL-1,650 (FS1)"), (1.85, "GL-1,850 (F3・F4・F5)"), (2.10, "GL-2,100 (F4A)"), (2.20, "GL-2,200 (F3A)")]):
        fc, hatch = DEPTH_STYLE[d]
        ax.add_patch(Rectangle((lx + i * 4200, ly), 700, 450, fc=fc, ec="k", lw=0.3, hatch=hatch))
        ax.text(lx + i * 4200 + 850, ly + 225, "根切り底 " + lab, fontsize=3.6, va="center")
    ax.add_patch(Rectangle((lx + 4 * 4200, ly), 700, 450, fc="#efe2c8", ec="k", lw=0.3, hatch="|||"))
    ax.text(lx + 4 * 4200 + 850, ly + 225, f"法面（法幅=0.3h）", fontsize=3.6, va="center")
    ax.text(x_lo + 400, y_hi - 400, "根切り図 1/100", fontsize=6, va="top")
    _watermark(ax, watermark)
    for ext in ("png", "pdf", "svg"):
        fig.savefig(f"{out_base}.{ext}", dpi=400)
    plt.close(fig)


def section(site, zones, out_base, axis="Y3", watermark=None):
    from shapely.geometry import LineString
    y = site.grid_y[axis]
    segs = section_profile(zones, y)
    gx = site.grid_x
    lv = site.raw["levels"]
    ret = site.raw["retaining"]
    n = ret.get("slope_ratio") or 0
    x0 = segs[0][0]; x1 = segs[-1][1]
    dmax = max(s[2] for s in segs) * 1000
    sw = n * segs[0][2] * 1000
    xl, xr = x0 - sw - 2600, x1 + 2600
    yb, yt = -dmax - 2200, lv["1FL"] + 2400
    fig, ax = _fig_true_scale(xr - xl, yt - yb, site.raw["meta"]["scale"])
    ax.set_xlim(xl, xr); ax.set_ylim(yb, yt)

    prof = [(x0 - sw, 0), (x0, -segs[0][2] * 1000)]
    for a, b, d in segs:
        prof += [(a, -d * 1000), (b, -d * 1000)]
    east_vertical = ret["east"] != "open_cut"
    prof += [(x1, 0)] if east_vertical else [(x1 + n * segs[-1][2] * 1000, 0)]
    ground = [(xl, 0)] + prof + [(xr, 0), (xr, -dmax - 900), (xl, -dmax - 900)]
    ax.add_patch(MplPoly(ground, closed=True, fc="#eee6d4", ec="none", hatch="..", lw=0, zorder=1))
    ax.plot(*zip(*prof), "k-", lw=1.0, zorder=4)
    ax.plot([xl, x0 - sw], [0, 0], "k-", lw=0.6); ax.plot([x1, xr], [0, 0], "k-", lw=0.6)
    if east_vertical:
        ax.add_patch(Rectangle((x1, -dmax - 1200), 200, dmax + 1500, fc="0.5", ec="k", lw=0.4, zorder=5))
        ax.text(x1 + 300, -400, "親杭（H形鋼）\n横矢板\n根入れ長さは\n資料になし", fontsize=3.4, va="top")
    ax.text(x0 - sw / 2 - 150, -segs[0][2] * 500, f"法面 1:{n}\n法幅 {sw:,.0f}", fontsize=3.6, ha="right", va="center")
    _dim_h(ax, x0 - sw, x0, -segs[0][2] * 1000 - 350, f"{sw:,.0f}", fs=3.6)

    # FS1・捨てコン/砕石 （参考表示）
    for f in site.raw.get("footings", []):
        fp = _footing_poly(f)
        if fp is None:
            continue
        cut = fp.intersection(LineString([(xl, y), (xr, y)]))
        if cut.is_empty:
            continue
        a, _, b, _ = cut.bounds
        bot = f["bottom_GL_mm"]
        ax.add_patch(Rectangle((a, bot), b - a, 900, fc="0.88", ec="k", lw=0.5, zorder=6))
        ax.add_patch(Rectangle((a, f["subgrade_GL_mm"]), b - a, 100, fc="0.6", ec="k", lw=0.3, hatch="xx", zorder=6))
        ax.text((a + b) / 2, bot + 450, f["name"] + "\n(参考)", ha="center", va="center", fontsize=3.6, zorder=7)
        ax.text((a + b) / 2, f["subgrade_GL_mm"] - 120, f"床付 GL{f['subgrade_GL_mm']:,}", ha="center", va="top", fontsize=3.3, zorder=7)
    ax.add_patch(Rectangle((x0, -1650), x1 - x0, 100, fc="none", ec="0.4", lw=0.3, hatch="////", zorder=3))
    ax.text((gx["X1"] + gx["X2"]) / 2 + 600, -1450, "FS1 下：捨てコン50＋砕石50\n床付 GL-1,650", fontsize=3.4, ha="center", va="bottom", zorder=8)

    # レベル
    for name, lvl, ls in (("GL±0", 0, "-"), ("1FL = GL+500", lv["1FL"], "--")):
        ax.plot([xl + 200, xr - 200], [lvl, lvl], color="0.3", lw=0.4, ls=ls)
        ax.text(xl + 300, lvl + 60, name, fontsize=4)
    for k, x in gx.items():
        ax.plot([x, x], [yb + 200, yt - 1000], color="0.35", lw=0.3, ls="-.")
        ax.add_patch(Circle((x, yt - 600), 380, fill=False, lw=0.4)); ax.text(x, yt - 600, k, ha="center", va="center", fontsize=4)
    xs = sorted(gx.values())
    for a, b in zip(xs, xs[1:]):
        _dim_h(ax, a, b, yt - 1350, f"{b-a:,.0f}")
    # 深さ寸法・区間寸法
    done = set()
    for a, b, d in segs:
        xm = (a + b) / 2
        if d not in done:
            done.add(d)
            _dim_v(ax, a + 250, -d * 1000, 0, f"{d*1000:,.0f}", fs=3.6)
    edges = sorted({round(v) for a, b, _ in segs for v in (a, b)})
    for a, b in zip(edges, edges[1:]):
        _dim_h(ax, a, b, yb + 600, f"{b-a:,.0f}", fs=3.0)
    ax.text(xl + 300, yt - 300, f"根切り断面図（{axis}通り） 1/100", fontsize=6, va="top")
    ax.text(xl + 300, yb + 150, "基礎の高さ900は参考表示（設計図の基礎リスト未確認）", fontsize=3.2)
    _watermark(ax, watermark)
    for ext in ("png", "pdf", "svg"):
        fig.savefig(f"{out_base}.{ext}", dpi=400)
    plt.close(fig)
    return segs
