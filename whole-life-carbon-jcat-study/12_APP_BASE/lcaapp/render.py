"""HTML of the result screen and of the two small management pages (standard library only).

Pages are rendered on the server from stored data; the charts are inline SVG drawn here, so
they are complete without JavaScript. A few lines of script add the hover read-out. Every
number on the result page comes from the stored display model (``view.build``), which in turn
only reads the engine's results.
"""
from __future__ import annotations

import html
import json
import math
from typing import Any

from . import APP_VERSION
from .common import STATE_LABELS

e = html.escape

CSS = """
:root{color-scheme:light;--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;
--grid:#e1e0d9;--axis:#c3c2b7;--border:rgba(11,11,11,.10);--s1:#2a78d6;--s2:#eb6834;--wash:rgba(42,120,214,.10);
--good:#0ca30c;--warn:#fab219;--serious:#ec835a;--critical:#d03b3b;--goodtext:#006300}
@media (prefers-color-scheme:dark){:root{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;
--muted:#898781;--grid:#2c2c2a;--axis:#383835;--border:rgba(255,255,255,.10);--s1:#3987e5;--s2:#d95926;
--wash:rgba(57,135,229,.10);--goodtext:#0ca30c}}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font:15px/1.6 system-ui,-apple-system,"Segoe UI","Hiragino Sans","Noto Sans JP",sans-serif}
main{max-width:1040px;margin:0 auto;padding:20px 16px 56px}
a{color:inherit}
header.top{display:flex;gap:12px;align-items:baseline;flex-wrap:wrap;margin-bottom:8px}
header.top .app{font-weight:600}
nav.crumbs{color:var(--ink2);font-size:13px;margin-bottom:12px}
h1{font-size:22px;line-height:1.35;margin:4px 0 4px;text-wrap:balance}
h2{font-size:16px;margin:0 0 10px}
p{margin:6px 0}
.sub{color:var(--ink2);font-size:13px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px;margin:14px 0}
.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(270px,1fr))}
.tile{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px 14px}
.tile .label{color:var(--ink2);font-size:13px}
.tile .value{font-size:24px;font-weight:600;line-height:1.3;overflow-wrap:anywhere}
.tile .unit{color:var(--ink2);font-size:13px;font-weight:400;margin-left:4px}
.tile .src{color:var(--muted);font-size:11.5px;margin-top:2px}
.hero .value{font-size:48px;line-height:1.15}
@media (max-width:560px){.hero .value{font-size:34px}}
.badge{display:inline-block;border:1px solid var(--border);border-radius:999px;padding:0 9px;font-size:12.5px;color:var(--ink2);white-space:nowrap}
.st{white-space:nowrap}
.st i{font-style:normal;font-weight:700;margin-right:4px}
.st.good i{color:var(--good)}.st.warn i{color:var(--serious)}.st.bad i{color:var(--critical)}.st.none i{color:var(--muted)}
.none-value{color:var(--ink2)}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--grid);vertical-align:top}
th{color:var(--ink2);font-weight:500;font-size:13px}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.scroll{overflow-x:auto}
.chart{overflow-x:auto}.chart svg{min-width:560px}
table.rec td{overflow-wrap:anywhere}
svg{display:block;width:100%;height:auto;font:12px system-ui,-apple-system,"Segoe UI","Hiragino Sans","Noto Sans JP",sans-serif}
svg text{fill:var(--ink2)}
svg .tick{fill:var(--muted);font-variant-numeric:tabular-nums}
svg .val{fill:var(--ink);font-variant-numeric:tabular-nums}
svg .gridline{stroke:var(--grid);stroke-width:1}
svg .axisline{stroke:var(--axis);stroke-width:1}
svg .line{fill:none;stroke:var(--s1);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
svg .area{fill:var(--wash)}
svg .bar{fill:var(--s1)}
svg .dot{fill:var(--s1);stroke:var(--surface);stroke-width:2}
svg .hit{fill:transparent}
svg .hit:hover+.mark,svg .hot{opacity:.75}
svg .cross{stroke:var(--axis);stroke-width:1}
.split{display:flex;gap:2px;height:28px;margin:8px 0}
.split div{border-radius:4px;color:#fff;font-size:13px;line-height:28px;padding:0 8px;white-space:nowrap;overflow:visible;min-width:0}
.split .a{background:var(--s1)}.split .b{background:var(--s2)}
.legend{display:flex;gap:18px;flex-wrap:wrap;font-size:13px;color:var(--ink2)}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px}
ul.notes{margin:0;padding-left:20px}
ul.notes li{margin:4px 0}
ul.notes li.warning{font-weight:500}
details{margin-top:8px}
summary{cursor:pointer;color:var(--ink2);font-size:13px}
form.row{display:flex;gap:10px;flex-wrap:wrap;align-items:end}
label{display:block;font-size:13px;color:var(--ink2)}
input,select,textarea,button{font:inherit;color:inherit;background:var(--surface);border:1px solid var(--axis);border-radius:6px;padding:6px 9px}
textarea{width:100%;min-height:120px;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12.5px}
button{background:var(--s1);border-color:var(--s1);color:#fff;cursor:pointer}
button.quiet{background:var(--surface);color:var(--ink);border-color:var(--axis)}
.msg{border-left:3px solid var(--serious);padding:8px 12px;background:var(--surface);margin:12px 0}
.tip{position:fixed;z-index:10;pointer-events:none;background:var(--surface);border:1px solid var(--border);border-radius:8px;
padding:6px 10px;font-size:12.5px;box-shadow:0 4px 14px rgba(0,0,0,.14);max-width:260px}
.tip .v{font-weight:600;color:var(--ink);font-variant-numeric:tabular-nums}.tip .l{color:var(--ink2)}
code{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12.5px}
footer{color:var(--muted);font-size:12px;margin-top:28px}
"""

JS = """
(function(){
  var tip=document.createElement('div');tip.className='tip';tip.hidden=true;document.body.appendChild(tip);
  function show(el,ev){
    var parts=(el.getAttribute('data-tip')||'').split('|');tip.textContent='';
    parts.forEach(function(t,i){var d=document.createElement('div');d.className=i===1?'v':'l';d.textContent=t;tip.appendChild(d);});
    tip.hidden=false;
    var r=el.getBoundingClientRect(),x=(ev&&ev.clientX!=null)?ev.clientX:r.left+r.width/2,y=(ev&&ev.clientY!=null)?ev.clientY:r.top;
    var w=tip.offsetWidth,h=tip.offsetHeight,left=x+14,top=y-h-10;
    if(left+w>window.innerWidth-8)left=x-w-14;if(left<8)left=8;if(top<8)top=y+16;
    tip.style.left=left+'px';tip.style.top=top+'px';
    var svg=el.ownerSVGElement,cx=el.getAttribute('data-cx');
    if(svg&&cx!==null){var c=svg.querySelector('.cross');if(c){c.setAttribute('x1',cx);c.setAttribute('x2',cx);c.style.display='';}
      var d=svg.querySelector('.focus');if(d&&el.hasAttribute('data-cy')){d.setAttribute('cx',cx);d.setAttribute('cy',el.getAttribute('data-cy'));d.style.display='';}}
  }
  function hide(el){tip.hidden=true;var svg=el.ownerSVGElement;if(svg){['.cross','.focus'].forEach(function(s){var n=svg.querySelector(s);if(n)n.style.display='none';});}}
  document.querySelectorAll('[data-tip]').forEach(function(el){
    el.addEventListener('pointermove',function(ev){show(el,ev);});el.addEventListener('pointerleave',function(){hide(el);});
    el.addEventListener('focus',function(){show(el,null);});el.addEventListener('blur',function(){hide(el);});});
})();
"""

NOT_COMPUTED = "未計算"
KIND_LABELS = {"fictional": "架空データ（検証用）", "real": "実データ（利用者の申告）", "unknown": "種別未申告"}
RUN_STATUS = {"ok": ("good", "✓", "計算済み"), "blocked": ("warn", "!", "計算していない"), "failed": ("bad", "×", "計算できなかった")}


# --------------------------------------------------------------------------------------------
# Numbers
# --------------------------------------------------------------------------------------------

def fmt(v: Any, digits: int | None = None) -> str:
    """A number as text; None is shown as 未計算, never as a number."""
    if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
        return NOT_COMPUTED
    a = abs(v)
    if a == 0:
        return "0"
    if digits is None:
        digits = 0 if a >= 1000 else 1 if a >= 100 else 2 if a >= 1 else 4
    text = f"{v:,.{digits}f}"
    if text.startswith("-") and not text.strip("-0.,"):
        text = text[1:]
    return text


def percent(v: Any) -> str:
    return NOT_COMPUTED if not isinstance(v, (int, float)) or isinstance(v, bool) else f"{v * 100:.1f}%"


def _axis_format(biggest: float):
    """One style for all ticks of an axis: in full below 10,000, compact above."""
    for limit, suffix in ((1e9, "G"), (1e6, "M"), (1e3, "k")):
        if biggest >= 10000 and biggest >= limit:
            return lambda v, limit=limit, suffix=suffix: (f"{v / limit:.2f}".rstrip("0").rstrip(".") if v else "0") + (suffix if v else "")
    return lambda v: f"{v:,.6g}"


def nice_ticks(lo: float, hi: float, n: int = 5) -> list[float]:
    if not (hi > lo):
        hi = lo + 1.0
    raw = (hi - lo) / max(1, n)
    power = 10.0 ** math.floor(math.log10(raw))
    step = next(m * power for m in (1, 2, 2.5, 5, 10) if m * power >= raw)
    first, last = math.floor(lo / step), math.ceil(hi / step)
    return [k * step for k in range(first, last + 1)]


# --------------------------------------------------------------------------------------------
# Charts (inline SVG)
# --------------------------------------------------------------------------------------------

W, PAD_L, PAD_R, PAD_T, PAD_B = 720, 64, 20, 22, 40


def _frame(values: list[float], height: int):
    lo, hi = min(0.0, min(values)), max(0.0, max(values))
    ticks = nice_ticks(lo, hi)
    lo, hi = ticks[0], ticks[-1]
    plot_h = height - PAD_T - PAD_B
    y = lambda v: PAD_T + plot_h * (hi - v) / (hi - lo)
    label = _axis_format(max(abs(lo), abs(hi)))
    parts = []
    for t in ticks:
        cls = "axisline" if t == 0 else "gridline"
        parts.append(f'<line class="{cls}" x1="{PAD_L}" x2="{W - PAD_R}" y1="{y(t):.1f}" y2="{y(t):.1f}"/>')
        parts.append(f'<text class="tick" x="{PAD_L - 8}" y="{y(t) + 4:.1f}" text-anchor="end">{e(label(t))}</text>')
    return y, parts


def _x_axis(n: int, x, height: int) -> list[str]:
    step = 5 if n <= 30 else 10 if n <= 80 else 20
    parts = [f'<text class="tick" x="{x(k):.1f}" y="{height - PAD_B + 16}" text-anchor="middle">{k}</text>'
             for k in range(0, n, step)]
    parts.append(f'<text x="{W - PAD_R}" y="{height - 6}" text-anchor="end">経過年（年）</text>')
    return parts


def chart_cumulative(series: dict, unit: str) -> str:
    """Cumulative emissions over the years: one series, a line with a light wash below it."""
    values, yearly = series["cumulative"], series["by_year"]
    n, height = len(values), 300
    y, parts = _frame(values, height)
    span = max(1, n - 1)
    x = lambda k: PAD_L + (W - PAD_L - PAD_R) * k / span
    points = " ".join(f"{x(k):.1f},{y(v):.1f}" for k, v in enumerate(values))
    parts.append(f'<polygon class="area" points="{x(0):.1f},{y(0):.1f} {points} {x(n - 1):.1f},{y(0):.1f}"/>')
    parts.append(f'<polyline class="line" points="{points}"/>')
    parts.append(f'<circle class="dot" cx="{x(n - 1):.1f}" cy="{y(values[-1]):.1f}" r="4.5"/>')
    parts.append(f'<text class="val" x="{x(n - 1) - 10:.1f}" y="{max(14.0, y(values[-1]) - 10):.1f}" text-anchor="end">'
                 f'{e(fmt(values[-1]))} {e(unit)}</text>')
    parts += _x_axis(n, x, height)
    parts.append(f'<line class="cross" x1="0" x2="0" y1="{PAD_T}" y2="{height - PAD_B}" style="display:none"/>')
    parts.append('<circle class="dot focus" r="4.5" style="display:none"/>')
    half = (W - PAD_L - PAD_R) / span / 2
    for k, v in enumerate(values):
        tip = f"経過年 {k} 年|累積 {fmt(v)} {unit}|この年 {fmt(yearly[k])} {unit}"
        parts.append(f'<rect class="hit" x="{x(k) - half:.1f}" y="{PAD_T}" width="{2 * half:.1f}" height="{height - PAD_T - PAD_B}" '
                     f'data-cx="{x(k):.1f}" data-cy="{y(v):.1f}" data-tip="{e(tip, quote=True)}"/>')
    return (f'<svg viewBox="0 0 {W} {height}" role="img" aria-label="累積排出量の推移（{e(unit)}）。値は下の表にもある">'
            f'<text x="{PAD_L}" y="12">{e(unit)}</text>' + "".join(parts) + "</svg>")


def _column(x0: float, w: float, y_base: float, y_end: float) -> str:
    """A column from the baseline to its value: rounded at the data end, square at the baseline."""
    r = min(4.0, w / 2, abs(y_end - y_base))
    s = 1 if y_end < y_base else -1                              # 1: column goes up
    return (f"M{x0:.2f},{y_base:.2f}V{y_end + s * r:.2f}Q{x0:.2f},{y_end:.2f} {x0 + r:.2f},{y_end:.2f}"
            f"H{x0 + w - r:.2f}Q{x0 + w:.2f},{y_end:.2f} {x0 + w:.2f},{y_end + s * r:.2f}V{y_base:.2f}Z")


def chart_yearly(series: dict, unit: str) -> str:
    """Emissions of each year as thin columns on one baseline."""
    values = series["by_year"]
    n, height = len(values), 260
    y, parts = _frame(values, height)
    band = (W - PAD_L - PAD_R) / n
    width = max(1.0, min(24.0, band - 2.0))
    x = lambda k: PAD_L + band * (k + 0.5)
    for k, v in enumerate(values):
        tip = f"経過年 {k} 年|{fmt(v)} {unit}"
        parts.append(f'<rect class="hit" x="{x(k) - band / 2:.2f}" y="{PAD_T}" width="{band:.2f}" height="{height - PAD_T - PAD_B}" '
                     f'data-cx="{x(k):.1f}" data-tip="{e(tip, quote=True)}"/>')
        if v:
            parts.append(f'<path class="bar mark" d="{_column(x(k) - width / 2, width, y(0), y(v))}" pointer-events="none"/>')
    top = max(range(n), key=lambda k: abs(values[k]))
    anchor, dx = ("start", width / 2 + 6) if x(top) < W / 2 else ("end", -width / 2 - 6)
    parts.append(f'<text class="val" x="{x(top) + dx:.1f}" y="{min(height - PAD_B - 4, max(14.0, y(values[top]) + 12)):.1f}" '
                 f'text-anchor="{anchor}">{e(fmt(values[top]))} {e(unit)}</text>')
    parts += _x_axis(n, x, height)
    parts.append(f'<line class="cross" x1="0" x2="0" y1="{PAD_T}" y2="{height - PAD_B}" style="display:none"/>')
    return (f'<svg viewBox="0 0 {W} {height}" role="img" aria-label="年ごとの排出量（{e(unit)}）。値は下の表にもある">'
            f'<text x="{PAD_L}" y="12">{e(unit)}</text>' + "".join(parts) + "</svg>")


def chart_stages(stages: list[dict], unit: str) -> str:
    """Life-cycle stages in their own order, one horizontal bar each, value at the tip."""
    rows = [s for s in stages if s["value"] is not None]
    if not rows:
        return ""
    row_h, label_w, value_w = 28, 168, 132
    lo, hi = min(0.0, min(s["value"] for s in rows)), max(0.0, max(s["value"] for s in rows))
    if hi == lo:
        hi = lo + 1.0
    left = label_w + (value_w if lo < 0 else 0)
    right = W - value_w
    x = lambda v: left + (right - left) * (v - lo) / (hi - lo)
    height = row_h * len(stages) + 8
    parts = [f'<line class="axisline" x1="{x(0):.1f}" x2="{x(0):.1f}" y1="2" y2="{height - 4}"/>']
    for i, s in enumerate(stages):
        cy = 4 + row_h * i + row_h / 2
        name = s["stage"] + ("　" + s["label"] if s["label"] else "")
        parts.append(f'<text x="0" y="{cy + 4:.1f}">{e(name)}</text>')
        v = s["value"]
        if v is None:
            parts.append(f'<text x="{x(0) + 8:.1f}" y="{cy + 4:.1f}">{NOT_COMPUTED}</text>')
            continue
        share = "" if s["share"] is None else f"|全体の {percent(s['share'])}"
        note = "|評価の対象外" if s["included"] is False else ""
        tip = f"{name}|{fmt(v)} {unit}{share}{note}"
        x0, x1 = x(0), x(v)
        if v:
            r = min(4.0, abs(x1 - x0))
            sgn = 1 if v > 0 else -1
            y0, y1 = cy - 7, cy + 7
            d = (f"M{x0:.2f},{y0:.2f}H{x1 - sgn * r:.2f}Q{x1:.2f},{y0:.2f} {x1:.2f},{y0 + r:.2f}V{y1 - r:.2f}"
                 f"Q{x1:.2f},{y1:.2f} {x1 - sgn * r:.2f},{y1:.2f}H{x0:.2f}Z")
            parts.append(f'<path class="bar" d="{d}"/>')
        anchor, tx = ("start", max(x0, x1) + 8) if v >= 0 else ("end", x1 - 8)
        text = fmt(v) + ("（対象外）" if s["included"] is False else "")
        parts.append(f'<text class="val" x="{tx:.1f}" y="{cy + 4:.1f}" text-anchor="{anchor}">{e(text)}</text>')
        parts.append(f'<rect class="hit" x="0" y="{cy - row_h / 2:.1f}" width="{W}" height="{row_h}" tabindex="0" '
                     f'data-tip="{e(tip, quote=True)}"/>')
    return (f'<svg viewBox="0 0 {W} {height}" role="img" aria-label="ライフサイクル段階別の排出量（{e(unit)}）。値は表にもある">'
            + "".join(parts) + "</svg>")


def split_bar(embodied: dict, operational: dict) -> str:
    """One whole split into two parts (embodied / operational), with a legend of names."""
    a, b = embodied.get("value"), operational.get("value")
    legend = ('<div class="legend"><span><i style="background:var(--s1)"></i>エンボディド</span>'
              '<span><i style="background:var(--s2)"></i>オペレーショナル</span></div>')
    if a is None or b is None:
        return f'<p class="sub">内訳の図は、値がそろっていないため表示しない（{NOT_COMPUTED}の指標がある）。</p>'
    if a < 0 or b < 0 or a + b <= 0:
        return '<p class="sub">内訳の図は、負の値または合計 0 があるため表示しない。数値は上の指標を参照。</p>'
    blocks = []
    for cls, value, name in (("a", a, "エンボディド"), ("b", b, "オペレーショナル")):
        share = value / (a + b)
        if value > 0:
            text = percent(share) if share >= 0.12 else ""
            tip = f"{name}|{fmt(value)} kg-CO2e|全体の {percent(share)}"
            blocks.append(f'<div class="{cls}" style="flex:{share:.6f} 1 0" tabindex="0" data-tip="{e(tip, quote=True)}">{text}</div>')
    return f'<div class="split" role="img" aria-label="エンボディドとオペレーショナルの内訳">{"".join(blocks)}</div>{legend}'


# --------------------------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------------------------

def page(title: str, body: str, crumbs: list[tuple[str, str]] | None = None) -> str:
    trail = ""
    if crumbs:
        trail = '<nav class="crumbs">' + " › ".join(
            f'<a href="{e(href, quote=True)}">{e(text)}</a>' if href else e(text) for text, href in crumbs) + "</nav>"
    return ("<!doctype html><html lang=\"ja\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>{e(title)}</title><style>{CSS}</style></head><body><main>"
            "<header class=\"top\"><span class=\"app\">建築 LCA アプリ 基礎システム</span>"
            f"<span class=\"sub\">ベータ {e(APP_VERSION)} ・独立概念モデル（架空データで検証）</span></header>"
            f"{trail}{body}<footer>計算は既存の 2 構造エンジン（マスク付き積和・節点スペクトル）による。"
            "他の算定ツールの結果との一致や、実建築物に対する精度を示すものではない。</footer>"
            f"</main><script>{JS}</script></body></html>")


def _status(kind: str, icon: str, text: str) -> str:
    return f'<span class="st {kind}"><i aria-hidden="true">{e(icon)}</i>{e(text)}</span>'


def _tile(ind: dict, hero: bool = False) -> str:
    if ind["status"] == "not_computed":
        value = f'<span class="none-value">{NOT_COMPUTED}</span>'
        extra = f'<div class="sub">{e(ind.get("reason", ""))}</div>'
    else:
        value = f'{e(fmt(ind["value"]))}<span class="unit">{e(ind["unit"])}</span>'
        extra = ""
        if ind["status"] == "incomplete":
            extra = '<div class="sub">' + _status("warn", "▲", "不完全") + "　" + e(ind.get("reason", "")) + "</div>"
    return (f'<div class="tile{" hero" if hero else ""}"><div class="label">{e(ind["label"])}</div>'
            f'<div class="value">{value}</div>{extra}<div class="src">出所：{e(ind["source"])}</div></div>')


def _notes(notes: list[dict]) -> str:
    return '<ul class="notes">' + "".join(
        f'<li class="{e(n.get("level", "info"), quote=True)}">{"【注意】" if n.get("level") == "warning" else ""}{e(n.get("text", ""))}</li>'
        for n in notes) + "</ul>"


def _tables_text(tables: Any) -> str:
    if not isinstance(tables, dict):
        return "なし（計算していない）"
    names = {"materials": "資材", "equipment": "設備", "refrigerants": "冷媒", "factors": "係数", "operation.grid.table": "年次表"}
    rows = "、".join("%s %s 行" % (names.get(k, k), f"{n:,}") for k, n in (tables.get("rows") or {}).items())
    return "共通表 %s 個・列 %s 本（%s）、節点スペクトル %s 本・節点 %s 個" % (
        tables.get("n_tables"), f'{tables.get("n_columns"):,}', rows, tables.get("n_knot_spectra"), f'{tables.get("n_knots"):,}')


def _versions(run: dict, page_data: dict) -> str:
    v = run["versions"]
    ref = v.get("reference_set") or {}
    rows = [
        ("アプリの版", v.get("app")),
        ("計算エンジン", v.get("engine")),
        ("エンジンのソースの SHA-256", "%s（%s）" % (v.get("engine_source_sha256"),
                                              "検証時と同じ" if v.get("engine_is_verified_version") else "検証時と異なる：再検証が必要")),
        ("入力モデルのソースの SHA-256", v.get("model_source_sha256")),
        ("積和のステップ数", "、".join(f"{k} {(v.get('steps') or {}).get(k)}" for k in ("P1", "TIME", "AGG"))),
        ("エンジンへ渡した表", _tables_text((run.get("report") or {}).get("engine_tables"))),
        ("Python / NumPy", f'{v.get("python")} / {v.get("numpy")}'),
        ("入力の版", f'第 {page_data["input"]["version_no"]} 版（SHA-256 {v.get("input_sha256")}）'),
        ("分類との結び付け", f'{(v.get("binding") or {}).get("id")}（版 {(v.get("binding") or {}).get("version")}）'
         + ("・仮の分類" if (v.get("binding") or {}).get("provisional") else "")),
        ("参照データ", f'{ref.get("name")}（版 {ref.get("version")}、種別 {ref.get("data_kind")}、SHA-256 {ref.get("sha256")}）' if ref else "なし"),
        ("計算日時（UTC）", run["created_at"]),
        ("計算時間", "%.0f ms" % run["elapsed_ms"] if run.get("elapsed_ms") is not None else ""),
    ]
    return '<div class="scroll"><table class="rec">' + "".join(f"<tr><th>{e(k)}</th><td>{e(str(val))}</td></tr>" for k, val in rows) + "</table></div>"


def run_page(page_data: dict) -> str:
    run, project, condition = page_data["run"], page_data["project"], page_data["condition"]
    kind, icon, text = RUN_STATUS.get(run["status"], ("none", "—", run["status"]))
    crumbs = [("建物プロジェクト一覧", "/"), (project["name"], f'/project/{project["id"]}'), (f'計算結果 {run["id"]}', "")]
    period = condition["study_period"]
    head = (f'<h1>{e(project["name"])}</h1><p class="sub"><span class="badge">{e(KIND_LABELS.get(project["data_kind"], project["data_kind"]))}</span>　'
            f'評価期間 {e(fmt(period, 1) if period is not None else condition["study_period_text"])} 年　'
            f'入力 第 {page_data["input"]["version_no"]} 版　{_status(kind, icon, text)}</p>')
    view = run["view"]
    if run["status"] != "ok" or not view:
        body = (head + f'<div class="msg"><strong>{e(text)}。</strong> {e(run["message"])}</div>'
                '<div class="card"><h2>指標</h2><p>すべて' + NOT_COMPUTED + '。計算結果がないため、数値は表示しない。</p></div>'
                + _blocking(run) + '<div class="card"><h2>計算の記録</h2>' + _versions(run, page_data) + "</div>")
        return page(f'計算結果 {run["id"]}｜{project["name"]}', body, crumbs)
    ind = {i["key"]: i for i in view["indicators"]}
    unit = view["unit"]
    tiles = '<div class="grid" style="grid-template-columns:1fr">' + _tile(ind["whole_life"], hero=True) + "</div>"
    tiles += '<div class="grid" style="margin-top:12px">' + "".join(
        _tile(ind[k]) for k in ("upfront", "embodied", "operational", "per_area", "per_area_year", "tonnes")) + "</div>"
    split = ('<div class="card"><h2>エンボディドとオペレーショナルの内訳</h2>' + split_bar(ind["embodied"], ind["operational"]) + "</div>")
    stage_rows = "".join(
        f'<tr><td>{e(s["stage"])}</td><td>{e(s["label"])}</td><td class="n">{e(fmt(s["value"]))}</td>'
        f'<td class="n">{e(percent(s["share"]) if s["share"] is not None else NOT_COMPUTED)}</td>'
        f'<td>{"対象" if s["included"] else "対象外" if s["included"] is False else ""}</td></tr>' for s in view["stages"])
    stages = ('<div class="card"><h2>ライフサイクル段階別の排出量</h2>'
              f'<p class="sub">単位 {e(unit)}。出所：X-02.by_stage（割合は SUM-07.by_stage）。</p>'
              + '<div class="chart">' + chart_stages(view["stages"], unit) + "</div>" +
              '<details><summary>表で見る</summary><div class="scroll"><table><tr><th>段階</th><th>内容</th>'
              f'<th class="n">排出量（{e(unit)}）</th><th class="n">割合</th><th>評価範囲</th></tr>{stage_rows}</table></div></details></div>')
    series = view["series"]
    if series:
        start = series.get("start_year")
        year_rows = "".join(
            f'<tr><td class="n">{k}</td><td class="n">{e(str(start + k)) if isinstance(start, int) else ""}</td>'
            f'<td class="n">{e(fmt(v))}</td><td class="n">{e(fmt(series["cumulative"][k]))}</td></tr>'
            for k, v in enumerate(series["by_year"]))
        time_card = ('<div class="card"><h2>時間変化</h2>'
                     f'<p class="sub">出所：{e(series["source"])}。0 年目は建設時（A1〜A5）、最終年は解体・廃棄（C 段階）を含む。'
                     '評価期間が整数年でないとき、最終年は端数分。</p>'
                     "<h3 class=\"sub\" style=\"margin:10px 0 2px\">累積排出量</h3><div class=\"chart\">" + chart_cumulative(series, unit) + "</div>" +
                     "<h3 class=\"sub\" style=\"margin:14px 0 2px\">年ごとの排出量</h3><div class=\"chart\">" + chart_yearly(series, unit) + "</div>" +
                     '<details><summary>表で見る</summary><div class="scroll"><table><tr><th class="n">経過年</th><th class="n">暦年</th>'
                     f'<th class="n">その年（{e(unit)}）</th><th class="n">累積（{e(unit)}）</th></tr>{year_rows}</table></div></details></div>')
    else:
        time_card = f'<div class="card"><h2>時間変化</h2><p>{NOT_COMPUTED}。年次の系列（X-07）が得られなかった。</p></div>'
    comparison = _comparison(view.get("comparison"), unit)
    checks = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            e(c["id"]), e(c["label"]),
            _status("none", "—", NOT_COMPUTED) if c["ok"] is None else
            _status("good", "✓", "問題なし") if c["ok"] else _status("warn", "!", "要確認（%d 件）" % c["n"] if c["n"] else "要確認"),
            e("、".join(c.get("examples") or [])[:160]))
        for c in view["checks"])
    checks_card = ('<div class="card"><h2>入力と計算の点検（エンジンの検査単位）</h2><div class="scroll"><table>'
                   f'<tr><th>単位</th><th>内容</th><th>判定</th><th>例</th></tr>{checks}</table></div></div>')
    others = page_data.get("others") or []
    other_rows = "".join(
        f'<tr><td>{e(o["category"])}</td><td>{e(o["label"])}</td><td>{e(json.dumps(o["value"], ensure_ascii=False))}</td>'
        f'<td>{e(o["unit"] or "")}</td><td>{e(o["note"] or "")}</td></tr>' for o in others[:200])
    notes_card = '<div class="card"><h2>注記</h2>' + _notes(view["notes"])
    if others:
        notes_card += ('<details><summary>「その他」の入力（%d 件。計算には使っていない）</summary><div class="scroll"><table>'
                       '<tr><th>分類</th><th>名称</th><th>値</th><th>単位</th><th>備考</th></tr>%s</table></div></details>'
                       % (len(others), other_rows))
    notes_card += "</div>"
    record = ('<div class="card"><h2>計算の記録</h2>' + _versions(run, page_data) +
              f'<p class="sub"><a href="/run/{run["id"]}/results.json">70 評価単位の計算結果（JSON）</a></p></div>')
    body = head + tiles + split + stages + time_card + comparison + checks_card + notes_card + record
    return page(f'計算結果 {run["id"]}｜{project["name"]}', body, crumbs)


def _comparison(comparison: Any, unit: str) -> str:
    if not isinstance(comparison, dict):
        return ""
    status = comparison.get("status")
    if status == "COMPARED":
        return ('<div class="card"><h2>基準案との比較</h2><div class="grid">'
                + _tile({"label": "基準案のホールライフ", "value": comparison.get("baseline"), "unit": unit,
                         "status": "ok" if comparison.get("baseline") is not None else "not_computed", "source": "SUM-08.baseline"})
                + _tile({"label": "差（この案 − 基準案）", "value": comparison.get("delta"), "unit": unit,
                         "status": "ok" if comparison.get("delta") is not None else "not_computed", "source": "SUM-08.delta"})
                + '<div class="tile"><div class="label">削減率</div><div class="value">%s</div><div class="src">出所：SUM-08.saving</div></div>'
                % e(percent(comparison.get("saving")))
                + "</div></div>")
    text = "基準案を指定していない。" if status == "NO_BASELINE" else "比較できなかった（理由：%s）。" % "、".join(map(str, comparison.get("reasons") or []))
    return f'<div class="card"><h2>基準案との比較</h2><p>{NOT_COMPUTED}。{e(text)}</p></div>'


def _blocking(run: dict) -> str:
    blocking = ((run.get("report") or {}).get("conversion") or {}).get("blocking") or []
    if not blocking:
        return ""
    rows = "".join(f'<tr><td><code>{e(b["path"])}</code></td><td>{e(b["message"])}</td></tr>' for b in blocking[:100])
    more = "" if len(blocking) <= 100 else f'<p class="sub">ほか {len(blocking) - 100} 件。</p>'
    return f'<div class="card"><h2>足りない必須項目</h2><div class="scroll"><table><tr><th>場所</th><th>内容</th></tr>{rows}</table></div>{more}</div>'


def _input_report(version: dict, detail: dict | None) -> str:
    stats = version["summary"]["stats"]
    counts = "　".join(f"{STATE_LABELS[s]} {stats.get(s, 0):,}" for s in ("entered", "zero", "missing", "absent", "invalid"))
    out = (f'<p>項目の状態：{e(counts)}　／　「その他」 {stats.get("others", 0)} 件　未対応 {stats.get("unsupported", 0)} 件'
           f'　分類に対応がない項目 {stats.get("unbound", 0)} 個</p>')
    if detail:
        issues = [i for i in detail["issues"] if i["level"] != "info"][:60]
        if issues:
            names = {"error": "使えない", "warning": "注意"}
            rows = "".join(f'<tr><td>{e(names.get(i["level"], i["level"]))}</td><td><code>{e(i["path"])}</code></td><td>{e(i["message"])}</td></tr>'
                           for i in issues)
            out += ('<details open><summary>確認が必要な点（先頭 %d 件）</summary><div class="scroll"><table><tr><th>種別</th><th>場所</th>'
                    '<th>内容</th></tr>%s</table></div></details>' % (len(issues), rows))
        if detail["unsupported"]:
            rows = "".join(f'<tr><td>{e(u["kind"])}</td><td><code>{e(u.get("where", ""))}</code></td><td>{e(str(u.get("id", "")))}</td>'
                           f'<td>{e(json.dumps(u.get("raw"), ensure_ascii=False)[:120])}</td></tr>' for u in detail["unsupported"][:60])
            out += ('<details><summary>未対応の入力（%d 件。保存はしている）</summary><div class="scroll"><table><tr><th>種類</th><th>場所</th>'
                    '<th>ID</th><th>値</th></tr>%s</table></div></details>' % (len(detail["unsupported"]), rows))
        if detail["others"]:
            rows = "".join(f'<tr><td>{e(o["category"])}</td><td>{e(o["label"])}</td><td>{e(json.dumps(o["value"], ensure_ascii=False)[:120])}</td>'
                           f'<td>{e(o["unit"] or "")}</td></tr>' for o in detail["others"][:60])
            out += ('<details><summary>「その他」の入力（%d 件）</summary><div class="scroll"><table><tr><th>分類</th><th>名称</th><th>値</th>'
                    '<th>単位</th></tr>%s</table></div></details>' % (len(detail["others"]), rows))
    return out


def project_page(project: dict, inputs: list[dict], runs: list[dict], detail: dict | None, refsets: list[dict],
                 baselines: list[dict], message: str = "") -> str:
    crumbs = [("建物プロジェクト一覧", "/"), (project["name"], "")]
    body = (f'<h1>{e(project["name"])}</h1><p class="sub"><span class="badge">{e(KIND_LABELS.get(project["data_kind"], project["data_kind"]))}</span>'
            f'　作成 {e(project["created_at"])}　更新 {e(project["updated_at"])}</p>')
    if message:
        body += f'<div class="msg">{e(message)}</div>'
    if inputs:
        latest = inputs[-1]
        declared = (latest["summary"].get("declared") or {}).get("conditions") or {}
        default_t = declared.get("study_period") if isinstance(declared.get("study_period"), (int, float)) else 60
        ref_options = "".join(f'<option value="{r["id"]}">{e(r["name"])}（版 {e(r["version"])}、{e(r["data_kind"])}）</option>' for r in refsets)
        base_options = '<option value="">なし</option>' + "".join(
            f'<option value="{b["id"]}">{e(b["label"])}</option>' for b in baselines)
        version_options = "".join(f'<option value="{v["id"]}"{" selected" if v is latest else ""}>第 {v["version_no"]} 版（{e(v["created_at"])}）</option>'
                                  for v in inputs)
        body += ('<div class="card"><h2>計算する</h2>'
                 f'<form class="row" method="post" action="/project/{project["id"]}/calculate">'
                 f'<div><label for="t">評価期間（年）</label><input id="t" name="study_period" value="{e(str(default_t), quote=True)}" size="8" inputmode="decimal"></div>'
                 f'<div><label for="v">入力の版</label><select id="v" name="input_version_id">{version_options}</select></div>'
                 f'<div><label for="r">参照データ（原単位など）</label><select id="r" name="reference_set_id"><option value="">入力の指定に従う</option>{ref_options}</select></div>'
                 f'<div><label for="b">基準案（比較する入力）</label><select id="b" name="baseline_input_version_id">{base_options}</select></div>'
                 '<div><button type="submit">計算する</button></div></form>'
                 '<p class="sub">計算は既存の 2 構造エンジンで行い、結果は保存される。</p></div>')
        body += f'<div class="card"><h2>入力（第 {latest["version_no"]} 版）</h2>' + _input_report(latest, detail) + "</div>"
    else:
        body += '<div class="card"><p>入力がまだない。下の欄から入力 JSON を取り込む。</p></div>'
    if runs:
        rows = ""
        for r in runs:
            kind, icon, text = RUN_STATUS.get(r["status"], ("none", "—", r["status"]))
            period = fmt(r["study_period"], 1) if r["study_period"] is not None else r["study_period_text"]
            rows += (f'<tr><td><a href="/run/{r["id"]}">計算結果 {r["id"]}</a></td><td class="n">{e(str(period))}</td><td>第 {r["version_no"]} 版</td>'
                     f'<td>{_status(kind, icon, text)}</td><td>{e(r["message"][:90])}</td><td>{e(r["created_at"])}</td></tr>')
        body += ('<div class="card"><h2>計算結果（保存済み）</h2><div class="scroll"><table><tr><th>結果</th><th class="n">評価期間（年）</th>'
                 f'<th>入力</th><th>状態</th><th>備考</th><th>日時（UTC）</th></tr>{rows}</table></div></div>')
    body += ('<div class="card"><h2>入力を更新する（開発者用）</h2><p class="sub">入力画面は今回の対象外。入力 JSON（lca-input/1）を貼り付けると、'
             '新しい版として保存する。前の版と、その計算結果は残る。</p>'
             f'<form method="post" action="/project/{project["id"]}/import"><textarea name="document" aria-label="入力 JSON"></textarea>'
             '<p><button type="submit" class="quiet">新しい版として保存</button></p></form></div>')
    return page(project["name"], body, crumbs)


def index_page(projects: list[dict], refsets: list[dict], message: str = "") -> str:
    body = "<h1>建物プロジェクト一覧</h1>"
    if message:
        body += f'<div class="msg">{e(message)}</div>'
    if projects:
        rows = "".join(
            f'<tr><td><a href="/project/{p["id"]}">{e(p["name"])}</a></td><td>{e(KIND_LABELS.get(p["data_kind"], p["data_kind"]))}</td>'
            f'<td class="n">{p["n_inputs"]}</td><td class="n">{p["n_runs"]}</td><td>{e(p["updated_at"])}</td></tr>' for p in projects)
        body += ('<div class="card"><div class="scroll"><table><tr><th>名称</th><th>データの種別</th><th class="n">入力の版数</th>'
                 f'<th class="n">計算結果の数</th><th>更新（UTC）</th></tr>{rows}</table></div></div>')
    else:
        body += '<div class="card"><p>保存されている建物プロジェクトはまだない。</p></div>'
    ref_rows = "".join(
        f'<tr><td>{e(r["name"])}</td><td>{e(r["version"])}</td><td>{e(r["data_kind"])}</td><td class="n">{r["n_factors"]}</td>'
        f'<td>{e(r["source_note"][:120])}</td></tr>' for r in refsets)
    body += ('<div class="card"><h2>参照データ（原単位・標準値）</h2>'
             + ('<div class="scroll"><table><tr><th>名称</th><th>版</th><th>種別</th><th class="n">係数の数</th><th>出典の説明</th></tr>'
                f'{ref_rows}</table></div>' if refsets else "<p>登録されていない。</p>")
             + '<p class="sub">登録できるのは、架空データ（fictional）と、使用許諾を自分で確認して宣言したデータ（licensed）だけ。'
             '他のツールの原単位などを無断で登録しないこと。登録はコマンド <code>python3 -m lcaapp refset add</code> で行う。</p></div>')
    body += ('<div class="card"><h2>検証用の架空データを作る（開発者用）</h2>'
             '<p class="sub">凍結済みの生成器から、架空の建物 1 棟と架空の参照データを作って保存する。実在の建物・原単位ではない。</p>'
             '<form class="row" method="post" action="/demo"><div><label for="seed">シード</label><input id="seed" name="seed" value="4201" size="8" inputmode="numeric"></div>'
             '<div><button type="submit" class="quiet">架空の建物を作る</button></div></form></div>')
    body += ('<div class="card"><h2>入力 JSON を取り込む（開発者用）</h2><p class="sub">入力画面は今回の対象外。入力 JSON（lca-input/1）を貼り付けて、'
             '新しい建物プロジェクトとして保存する。</p><form method="post" action="/import">'
             '<p><label for="name">名称（空なら入力文書の title）</label><input id="name" name="name" size="40"></p>'
             '<textarea name="document" aria-label="入力 JSON"></textarea><p><button type="submit" class="quiet">取り込む</button></p></form></div>')
    return page("建物プロジェクト一覧", body)


def error_page(status: int, message: str) -> str:
    return page("エラー", f'<h1>{status}</h1><div class="msg">{e(message)}</div><p><a href="/">一覧へ戻る</a></p>')
