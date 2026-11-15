"""教材の図（SVG・HTML を作り、figshot で PNG にする）。数値はすべて説明用の架空の値。

図の値は教材の例題と同じ式から計算する（例題 4.2・5.1・6.2・7.1）。描いた数値は figures/<名前>.csv にも保存する。
"""
from __future__ import annotations

import csv
import math
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import svgplot as sp  # noqa: E402
from figshot import to_png  # noqa: E402

OUT = HERE.parent / "figures"
INK, MUTED, LINE = "#111111", "#555555", "#999999"


def _svg(chart: sp.Chart, note: str = "") -> str:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "c.svg"
        chart.render(str(p), note=note)
        return p.read_text(encoding="utf-8")


def _csv(name: str, header: list[str], rows: list[list]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def n_events(T, L):
    return max(math.ceil(T / L) - 1, 0)


# ---------------------------------------------------------------- 図 4.1：C(T) = a + bT + R N(T)
def fig_steps():
    a, b, R, L, H = 500, 20, 40, 15, 70
    xs, ys = [], []
    pts = sorted(set([i / 10 for i in range(1, H * 10 + 1)] + [k * L + d for k in range(1, 5) for d in (-1e-6, 1e-6)]))
    for T in pts:
        if 0 < T <= H:
            xs.append(T)
            ys.append(a + b * T + R * n_events(T, L))
    ch = sp.Chart(w=720, h=380, title="評価期間 T と WLC の合計 C(T)", xlabel="評価期間 T（年）", ylabel="C(T)（tCO2e）")
    ch.line(xs, ys, "C(T) = a + bT + R·N(T)")
    ch.line(xs, [a + b * T for T in xs], "交換なし a + bT", color=LINE, width=1.5)
    _csv("F4-1_steps", ["T", "C(T)", "a+bT"], [[x, y, a + b * x] for x, y in zip(xs, ys)][::10])
    return _svg(ch, note="a = 500、b = 20 /年、R = 40、L = 15 年（架空）。交換の時刻 15・30・45・60 年で跳ぶ。")


# ---------------------------------------------------------------- 図 4.2：核の五つの形
def kernel(T, s, l, g):
    gate = 1.0 if g is None or g < T else 0.0
    if l == 0:
        return gate
    return gate * min(l, max(0.0, T - s))


def fig_kernels():
    forms = [("定数 (0, 0, −∞)", 0, 0, None), ("原子 (3, 0, 3)", 3, 0, 3), ("年セル (2, 1, −∞)", 2, 1, None),
             ("ゲート付き年セル (2, 1, 2.4)", 2, 1, 2.4), ("密度 (0, 6, −∞)", 0, 6, None)]
    cells, rows = [], []
    for title, s, l, g in forms:
        xs = sorted(set([i / 50 for i in range(1, 301)] + ([g - 1e-6, g + 1e-6] if g else []) + ([s - 1e-6, s + 1e-6] if l == 0 else [])))
        xs = [x for x in xs if 0 < x <= 6]
        ys = [kernel(x, s, l, g) for x in xs]
        rows += [[title, x, y] for x, y in zip(xs[::25], ys[::25])]
        ch = sp.Chart(w=330, h=210, title=title, xlabel="T", ylabel="")
        ch.mr = 24
        ch.line(xs, ys, "")          # 1 系列なので線の名前は付けない（題が名前）
        cells.append(_svg(ch))
    _csv("F4-2_kernels", ["形", "T", "κ"], rows)
    return "<div style='display:grid;grid-template-columns:repeat(3,330px);gap:4px;background:#fff'>" + "".join(cells) + "</div>"


# ---------------------------------------------------------------- 図 6.1：冷媒の残存量（例題 6.2）
def fig_refrigerant():
    m0, r, c, Y = 10.0, 0.1, 10, 30
    u = [m0]
    for k in range(1, Y):
        chi = 1 if (k - 1) % c == c - 1 else 0
        u.append(chi * m0 + (1 - chi) * (1 - r) * u[-1])
    xs, ys = [], []
    for k, v in enumerate(u):
        xs += [k + 1e-6, k + 1 - 1e-6]
        ys += [v, v]
    ch = sp.Chart(w=720, h=340, title="冷媒の年初の残存量（補充なし、10 年ごとに交換）", xlabel="実時間 t（年）", ylabel="残存量（kg）")
    ch.line(xs, ys, "残存量")
    _csv("F6-1_refrigerant", ["k", "u_k"], [[k, round(v, 6)] for k, v in enumerate(u)])
    return _svg(ch, note="m0 = 10 kg、漏洩率 r = 0.1/年、補充なし。年 9・19 の終わりの交換で翌年は満タンに戻る（架空）。")


# ---------------------------------------------------------------- 図 7.1：C(T) = M([0,T]) + Z(T)（例題 7.1）
def fig_mz():
    A, Z, b, R, L, H = 600, 40, 25, 60, 15, 60
    xs = sorted(set([i / 10 for i in range(1, H * 10 + 1)] + [k * L + d for k in range(1, 5) for d in (-1e-6, 1e-6)]))
    xs = [x for x in xs if 0 < x <= H]
    M = [A + b * T + R * n_events(T, L) for T in xs]
    C = [m + Z for m in M]
    ch = sp.Chart(w=720, h=380, title="評価期間の合計 C(T) と、実際に出た量の累積 M([0,T])", xlabel="T（年）", ylabel="tCO2e")
    ch.line(xs, C, "C(T) = M + Z")
    ch.line(xs, M, "M([0,T])（実際の累積）")
    _csv("F7-1_MZ", ["T", "C", "M"], [[x, c, m] for x, c, m in zip(xs[::10], C[::10], M[::10])])
    return _svg(ch, note="初期 600、運用 25/年、15 年ごとの交換 60、解体 Z = 40（架空）。差はいつも Z（評価の終わりに数える解体）。")


# ---------------------------------------------------------------- 図 0.1・1.1・5.1：構成図（HTML）
BOX = "border:1.5px solid #111;border-radius:6px;padding:8px 10px;background:#fff;font-size:15px;line-height:1.45"


def fig_principles():
    def box(t, s, w=210):
        return f"<div style='{BOX};width:{w}px'><b style='font-size:16px'>{t}</b><br><span style='color:#444;font-size:13.5px'>{s}</span></div>"
    arrow = "<div style='font-size:24px;color:#555;padding:0 6px;align-self:center'>→</div>"
    row1 = ("<div style='display:flex;align-items:stretch'>" + box("P1 量 × 係数 の和", "第 2 章：どの段階も Σ f·m") + arrow +
            box("P2 条件は 0/1 の掛け算", "第 3 章：マスク付き積和") + arrow + box("P3 時間は節点で区切る", "第 4・5 章：区分一次関数、全体方程式") + "</div>")
    row2 = ("<div style='display:flex;align-items:stretch;margin-top:14px;margin-left:240px'>" +
            box("P4 状態を持つ量は漸化式", "第 6 章：冷媒、畳み込みの成否") + arrow + box("P5 評価期間と実時間", "第 7 章：動的 LCA、再合成") + "</div>")
    row3 = ("<div style='margin-top:14px;" + BOX + ";width:690px'><b>E 主張の強さを区別する</b>　"
            "<span style='color:#444;font-size:13.5px'>第 8・9 章：証明・照合・測定・統計・仮定・未解決</span></div>")
    return f"<div style='padding:12px;background:#fff;font-family:IPAGothic'>{row1}{row2}{row3}</div>"


def fig_stages():
    groups = [("A1–A3", "製品", "原材料・運搬・製造"), ("A4", "運搬", "工場→現場"), ("A5", "施工", "電力・燃料・廃棄物"),
              ("B1–B7", "使用", "冷媒の漏洩・維持管理・修繕・交換・改修・運用エネルギー・水"), ("C1–C4", "解体・処理", "解体・運搬・処理・処分")]
    cells = "".join(f"<div style='{BOX};flex:{3 if g[0] == 'B1–B7' else 1};text-align:center'><b style='font-size:17px'>{g[0]}</b><br>{g[1]}<br>"
                    f"<span style='font-size:12.5px;color:#444'>{g[2]}</span></div>" for g in groups)
    axis = ("<div style='display:flex;justify-content:space-between;margin-top:6px;font-size:13px;color:#333'>"
            "<span>建てる（t &lt; 0〜t = 0）</span><span>使う（0 ≤ t &lt; T）</span><span>壊す（t = T）</span></div>"
            "<div style='border-top:2px solid #111;margin-top:2px;position:relative'></div>")
    d = (f"<div style='{BOX};margin-top:10px;width:260px;font-size:13px'><b>D</b> 境界外（再利用・リサイクルの効果）：合計とは別に示す</div>")
    return f"<div style='padding:12px;width:820px;background:#fff;font-family:IPAGothic'><div style='display:flex;gap:6px'>{cells}</div>{axis}{d}</div>"


def fig_assembly():
    i = lambda x: f"<i style='font-family:FreeSerif'>{x}</i>"  # noqa: E731
    steps = [("① 入力", "数量・係数・周期・表・範囲"),
             (f"② 振幅 {i('a')}<sub>{i('j')}</sub>", "マスク付き積和（P2・P1）。<br>評価期間 T によらない"),
             (f"③ 単位の値 {i('V')}<sub>{i('u')}</sub>({i('T')})", f"Σ {i('a')}<sub>{i('j')}</sub> κ<sub>{i('j')}</sub>({i('T')})（P3）"),
             (f"④ 段階の値 {i('S')}<sub>{i('s')}</sub>({i('T')})", f"ι<sub>{i('s')}</sub> Σ σ β {i('V')}<sub>{i('u')}</sub>（P2）"),
             (f"⑤ 合計 {i('C')}({i('T')})", f"Σ<sub>{i('s')}</sub> {i('S')}<sub>{i('s')}</sub>（P1）"),
             ("⑥ 節点形", f"{i('A')}<sub>0</sub> ＋ 節点ごとの一次式<br>（{i('P')}＋{i('Q')}{i('T')}、{i('p')}＋{i('q')}{i('T')}）の和")]
    def box(t, s_):
        return f"<div style='{BOX};width:230px;text-align:center'><b>{t}</b><br><span style='font-size:13.5px;color:#333'>{s_}</span></div>"
    arr = "<div style='font-size:24px;color:#555;align-self:center;padding:0 4px'>→</div>"
    r1 = arr.join(box(*x) for x in steps[:3])
    larr = "<div style='font-size:24px;color:#555;align-self:center;padding:0 4px'>←</div>"
    r2 = larr.join(box(*x) for x in reversed(steps[3:]))   # 2 段目は右から左へ（③ の下に ④）
    turn = "<div style='text-align:right;font-size:22px;color:#555;padding-right:120px'>↓</div>"
    return (f"<div style='padding:12px;background:#fff;font-family:IPAGothic'><div style='display:flex'>{r1}</div>{turn}"
            f"<div style='display:flex'>{r2}</div><div style='font-size:12.5px;color:#444;margin-top:6px'>どの段からも、前の段（寄与した単位・段階・入力の行）へ戻せる。</div></div>")


def build() -> dict[str, Path]:
    figs = {
        "F0-1_principles": ("html", fig_principles()),
        "F1-1_stages": ("html", fig_stages()),
        "F4-1_steps": ("svg", fig_steps()),
        "F4-2_kernels": ("html", fig_kernels()),
        "F5-1_assembly": ("html", fig_assembly()),
        "F6-1_refrigerant": ("svg", fig_refrigerant()),
        "F7-1_MZ": ("svg", fig_mz()),
    }
    return to_png(figs, OUT)


if __name__ == "__main__":
    for k, v in build().items():
        print(k, v)
