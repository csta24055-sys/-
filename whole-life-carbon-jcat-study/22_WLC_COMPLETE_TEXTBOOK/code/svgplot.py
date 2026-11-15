"""Minimal static SVG charts (copied from 17_WHOLE_BUILDING_TIME_THEORY/code/svgplot.py; font list starts with IPAGothic) (no plotting library is installed; static figures for GitHub).
Palette: the validated reference categorical order (blue, orange, aqua, yellow, magenta, ...), light surface,
text in text tokens, thin marks, recessive grid, legend for >= 2 series plus direct labels at line ends."""
import math

SURFACE, TEXT, TEXT2, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#8a8984"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
FONT = "font-family='IPAGothic, Noto Sans CJK JP, Hiragino Sans, Yu Gothic, sans-serif'"


def nice_ticks(lo, hi, n=5):
    if hi <= lo:
        hi = lo + 1
    span = hi - lo
    step = 10 ** math.floor(math.log10(span / n))
    for m in (1, 2, 2.5, 5, 10):
        if span / (step * m) <= n:
            step *= m
            break
    t = math.ceil(lo / step) * step
    out = []
    while t <= hi + 1e-12 * span:
        out.append(round(t, 12))
        t += step
    return out


def fmt(v):
    a = abs(v)
    if a == 0:
        return "0"
    if a >= 1e4 or a < 1e-3:
        e = int(math.floor(math.log10(a)))
        m = v / 10 ** e
        return ("%g" % round(m, 2)) + "e" + str(e)
    return "%g" % round(v, 3)


class Chart:
    def __init__(self, w=760, h=420, title="", xlabel="", ylabel="", logx=False, logy=False, xcats=None):
        """xcats: category labels for x = 1..n (categorical axis: ticks at the integers, half a step of padding)."""
        self.w, self.h, self.title, self.xlabel, self.ylabel = w, h, title, xlabel, ylabel
        self.xcats = xcats
        self.logx, self.logy = logx, logy
        self.ml, self.mr, self.mt, self.mb = 78, 150, 52, 56
        self.items = []

    def _tx(self, v):
        return math.log10(v) if self.logx else v

    def _ty(self, v):
        return math.log10(v) if self.logy else v

    def line(self, xs, ys, label, color=None, step=False, width=2, dots=False):
        """dots=True: markers only (no connecting line), for categorical x."""
        self.items.append(("line", xs, ys, label, color, step, width, dots))

    def bars(self, xs, stacks, labels, width=0.8):
        """stacks: list of series (same length as xs), stacked in order."""
        self.items.append(("bars", xs, stacks, labels, width))

    def render(self, path, note=""):
        xs_all, ys_all = [], []
        for it in self.items:
            if it[0] == "line":
                xs_all += [self._tx(x) for x in it[1]]
                ys_all += [self._ty(y) for y in it[2]]
            else:
                xs, stacks = it[1], it[2]
                xs_all += [x - it[4] / 2 for x in xs] + [x + it[4] / 2 for x in xs]
                pos = [sum(max(s[i], 0) for s in stacks) for i in range(len(xs))]
                neg = [sum(min(s[i], 0) for s in stacks) for i in range(len(xs))]
                ys_all += pos + neg + [0]
        x0, x1 = min(xs_all), max(xs_all)
        if self.xcats:
            x0, x1 = 0.5, len(self.xcats) + 0.5
        y0, y1 = min(ys_all), max(ys_all)
        if not self.logy:
            y0 = min(y0, 0)
        pad = (y1 - y0) * 0.04 or 1
        y1 += pad
        if self.logy:
            y0 -= pad
        X = lambda v: self.ml + (v - x0) / (x1 - x0) * (self.w - self.ml - self.mr)
        Y = lambda v: self.h - self.mb - (v - y0) / (y1 - y0) * (self.h - self.mt - self.mb)
        o = ["<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' viewBox='0 0 %d %d' %s>" % (self.w, self.h, self.w, self.h, FONT),
             "<rect width='100%%' height='100%%' fill='%s'/>" % SURFACE,
             "<text x='%d' y='26' font-size='16' font-weight='600' fill='%s'>%s</text>" % (self.ml, TEXT, self.title)]
        # grid and ticks
        if self.logy:
            yt = [math.log10(m * 10 ** k) for k in range(math.floor(y0) - 1, math.ceil(y1) + 1) for m in (1, 2, 5) if y0 <= math.log10(m * 10 ** k) <= y1]
            ylab = [fmt(10 ** t) for t in yt]
        else:
            yt = [t for t in nice_ticks(y0, y1) if y0 <= t <= y1]
            ylab = [fmt(t) for t in yt]
        for t, lab in zip(yt, ylab):
            o.append("<line x1='%.1f' x2='%.1f' y1='%.1f' y2='%.1f' stroke='%s' stroke-width='1'/>" % (self.ml, self.w - self.mr, Y(t), Y(t), GRID))
            o.append("<text x='%.1f' y='%.1f' font-size='11' fill='%s' text-anchor='end'>%s</text>" % (self.ml - 6, Y(t) + 4, TEXT2, lab))
        if self.logx:
            xt = [math.log10(m * 10 ** k) for k in range(math.floor(x0) - 1, math.ceil(x1) + 1) for m in (1, 2, 5) if x0 - 1e-9 <= math.log10(m * 10 ** k) <= x1 + 1e-9]
            xlab = ["%g" % round(10 ** t, 6) for t in xt]
        elif self.xcats:
            xt = list(range(1, len(self.xcats) + 1))
            xlab = list(self.xcats)
        else:
            xt = [t for t in nice_ticks(x0, x1, 8) if x0 <= t <= x1]
            xlab = [fmt(t) for t in xt]
        base = Y(max(y0, 0)) if not self.logy else Y(y0)
        o.append("<line x1='%.1f' x2='%.1f' y1='%.1f' y2='%.1f' stroke='%s' stroke-width='1'/>" % (self.ml, self.w - self.mr, base, base, AXIS))
        for t, lab in zip(xt, xlab):
            o.append("<text x='%.1f' y='%.1f' font-size='11' fill='%s' text-anchor='middle'>%s</text>" % (X(t), self.h - self.mb + 18, TEXT2, lab))
        o.append("<text x='%.1f' y='%.1f' font-size='12' fill='%s' text-anchor='middle'>%s</text>" % ((self.ml + self.w - self.mr) / 2, self.h - 14, TEXT2, self.xlabel))
        o.append("<text x='16' y='%.1f' font-size='12' fill='%s' text-anchor='middle' transform='rotate(-90 16 %.1f)'>%s</text>" % ((self.mt + self.h - self.mb) / 2, TEXT2, (self.mt + self.h - self.mb) / 2, self.ylabel))
        legend = []
        ci = 0
        for it in self.items:
            if it[0] == "bars":
                xs, stacks, labels, wd = it[1], it[2], it[3], it[4]
                for si, (s, lab) in enumerate(zip(stacks, labels)):
                    legend.append((lab, SERIES[ci + si]))
                for i, x in enumerate(xs):
                    up, dn = 0.0, 0.0
                    for si, s in enumerate(stacks):
                        v = s[i]
                        if v == 0:
                            continue
                        if v > 0:
                            a, b = up, up + v; up = b
                        else:
                            a, b = dn + v, dn; dn = a
                        ya, yb = Y(a), Y(b)
                        hh = abs(ya - yb) - 1.0                     # 1 px gap on each side: the 2 px spacer between fills
                        if hh <= 0.3:
                            continue
                        o.append("<rect x='%.2f' y='%.2f' width='%.2f' height='%.2f' fill='%s'/>" % (X(x - wd / 2), min(ya, yb) + 0.5, max(X(x + wd / 2) - X(x - wd / 2), 0.6), hh, SERIES[ci + si]))
                ci += len(stacks)
        ends = []
        for it in self.items:
            if it[0] != "line":
                continue
            _, xs, ys, lab, color, step, width, dots = it
            color = color or SERIES[ci]
            ci += 1
            legend.append((lab, color))
            pts = []
            for i, (x, y) in enumerate(zip(xs, ys)):
                px, py = X(self._tx(x)), Y(self._ty(y))
                if step and pts:
                    pts.append("%.2f,%.2f" % (px, float(pts[-1].split(",")[1])))
                pts.append("%.2f,%.2f" % (px, py))
            if dots:                                       # markers with a 2 px surface ring
                for x, y in zip(xs, ys):
                    o.append("<circle cx='%.2f' cy='%.2f' r='5' fill='%s' stroke='%s' stroke-width='2'/>" % (X(self._tx(x)), Y(self._ty(y)), color, SURFACE))
            else:
                o.append("<polyline points='%s' fill='none' stroke='%s' stroke-width='%g' stroke-linejoin='round'/>" % (" ".join(pts), color, width))
            ends.append([Y(self._ty(ys[-1])), lab, color])
        # direct labels at line ends (de-overlapped), legend at the right
        ends.sort()
        for i in range(1, len(ends)):
            if ends[i][0] - ends[i - 1][0] < 14:
                ends[i][0] = ends[i - 1][0] + 14
        for yy, lab, color in ends:
            o.append("<text x='%.1f' y='%.1f' font-size='11' fill='%s'>%s</text>" % (self.w - self.mr + 8, yy + 4, TEXT, lab))
        if len(legend) >= 2:
            lx, ly = self.ml, self.mt - 12
            for lab, color in legend:
                o.append("<rect x='%.1f' y='%.1f' width='12' height='4' rx='1' fill='%s'/>" % (lx, ly - 4, color))
                o.append("<text x='%.1f' y='%.1f' font-size='11' fill='%s'>%s</text>" % (lx + 16, ly + 1, TEXT, lab))
                lx += 22 + 11.5 * len(lab)
        if note:
            o.append("<text x='%d' y='%d' font-size='10' fill='%s'>%s</text>" % (self.ml, self.h - 2, TEXT2, note))
        o.append("</svg>")
        open(path, "w").write("\n".join(o))
