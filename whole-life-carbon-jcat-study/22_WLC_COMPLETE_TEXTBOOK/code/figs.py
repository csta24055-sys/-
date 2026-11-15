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
    return _svg(ch)


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
    return _svg(ch)


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
    return _svg(ch)


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


def fig_derivations():
    """③ 導出のつながり：基本の式から建物全体方程式・時間の解析・動的 LCA・検証まで。"""
    i = lambda x: f"<i style='font-family:FreeSerif'>{x}</i>"  # noqa: E731
    sub = lambda x: f"<sub>{x}</sub>"  # noqa: E731

    def box(no, t, f, sec, w=330, tone="#fff"):
        return (f"<div style='{BOX};width:{w}px;background:{tone}'><b style='font-size:15px'>{no} {t}</b>"
                f"<div style='font-family:FreeSerif;font-size:15.5px;margin:4px 0'>{f}</div>"
                f"<div style='font-size:12px;color:#444'>{sec}</div></div>")

    def down(label):
        return (f"<div style='display:flex;align-items:center;height:34px;padding-left:150px'>"
                f"<span style='font-size:20px;color:#555'>↓</span><span style='font-size:12.5px;color:#333;margin-left:8px'>{label}</span></div>")
    main = [
        box("①", "量 × 係数", f"{i('C')} = {i('f')}{i('m')}", "P1・2.2 節"),
        down("項目を足す（線形性・分配法則）"),
        box("②", "積和", f"{i('C')} = Σ{sub(i('i'))} {i('f')}{sub(i('i'))}{i('m')}{sub(i('i'))}", "P1・2.3〜2.7 節（行列 S）"),
        down("条件を 0/1 にして掛ける（AND は積、OR は重ならない和）"),
        box("③", "マスク付き積和（第 1 の構造）", f"out[{i('g')}] = Σ{sub(i('x'))} Σ{sub(i('j'))} Π{sub(i('k'))} φ{sub(i('j,k'))}({i('x')})", "P2・3.4 節"),
        down("T への依存を核に分ける（振幅は T によらない）"),
        box("④", "時間関数：核の重ね合わせ", f"Φ({i('T')}) = Σ{sub(i('j'))} {i('a')}{sub(i('j'))} κ({i('T')}; {i('s')}, ℓ, {i('g')})", "P3・4.2〜4.7 節"),
        down("核を節点の一次式に分ける"),
        box("⑤", "節点スペクトル（第 2 の構造）", f"Φ({i('T')}) = Φ{sub('0')} + Σ{sub(i('u') + ' &lt; ' + i('T'))} ({i('c')}{sub('0')} + {i('c')}{sub('1')}{i('T')})", "P3・4.8 節"),
        down("70 単位・14 段階を合わせ、同じ節点を足す"),
        box("⑥", "建物全体の方程式", f"{i('C')}({i('T')}) = {i('A')}{sub('0')} + Σ{sub('Λ')}[{i('t')}&lt;{i('T')}]({i('P')}+{i('Q')}{i('T')}) + Σ{sub(i('E'))} θ({i('p')}+{i('q')}{i('T')})",
            "第 5 章（区分一次の証明 5.5 節）", tone="#f2f2f2"),
        down("節点の表から読む"),
        box("⑦", "跳び・傾き・積分・ラプラス変換", f"{i('J')} = {i('c')}{sub('0')}+{i('c')}{sub('1')}{i('u')}、 ℒ = Σ {i('e')}<sup>−{i('us')}</sup>(…)", "4.9・4.10・8.2 節"),
    ]
    side = [
        box("⑧", "実時間に置く（P5）", f"{i('C')}({i('T')}) = {i('M')}([0,{i('T')}]) + {i('Z')}({i('T')})", "7.3 節：傾き ≠ 排出率", w=300),
        down("工程ごとに分ける"),
        box("⑨", "工程関数と再合成", f"Σ{sub(i('i'))} ∫ {i('e')}{sub(i('i'))} + {i('Z')} = {i('C')}{sub('70')}", "7.4〜7.6 節（時期は一意でない）", w=300),
        down("時刻ごとの重みを掛ける"),
        box("⑩", "動的な特性化（畳み込み）", f"{i('W')} = Σ {i('m')}{sub(i('j'))} {i('R')}({i('t')}{sub('end')}−{i('t')}{sub(i('j'))})/{i('R')}(100)", "7.7 節", w=300),
        "<div style='height:16px'></div>",
        box("⑪", "畳み込み（時不変・線形）", f"{i('y')}{sub(i('t'))} = Σ{sub(i('s'))} {i('x')}{sub(i('s'))}{i('h')}{sub(i('t') + '−' + i('s'))}", "6.3 節", w=300),
        down("時不変でないとき"),
        box("⑫", "状態の漸化式（P4）", f"{i('u')}{sub(i('k'))} = χ{i('m')}{sub('0')} + (1−χ){i('q')}{i('u')}{sub(i('k') + '−1')}", "6.5・6.6 節：二時刻の核", w=300),
        "<div style='height:16px'></div>",
        box("E", "主張の強さ（検証）", f"照合・(1−{i('p')})<sup>{i('N')}</sup> ≥ 0.05 ⇒ {i('p')} ≤ 1−0.05<sup>1/{i('N')}</sup>", "第 9 章", w=300),
    ]
    note = ("<div style='font-size:12.5px;color:#333;margin-top:8px;width:700px'>⑥ から ⑧ へ（実時間に置く）、② から ⑪ へ（比例は畳み込みの特別な場合）、"
            "③ から ⑫ へ（交換の有無 χ は 0/1）がつながる。左の列が教材の主な導出の道筋、右の列が時間の扱いの枝分かれ。</div>")
    return (f"<div style='padding:12px;background:#fff;font-family:IPAGothic;width:720px'><div style='display:flex;gap:40px'>"
            f"<div>{''.join(main)}</div><div style='padding-top:40px'>{''.join(side)}</div></div>{note}</div>")


def fig_research_map():
    """研究全体図：二つの対象（独立概念モデル・J-CAT 原版）を別の帯に分け、章の流れとつながりを示す。"""
    def box(ch, t, s_, w=200, tone="#fff"):
        return (f"<div style='{BOX};width:{w}px;background:{tone};font-size:15px;line-height:1.4'>"
                f"<b style='font-size:15.5px'>{ch}</b> {t}<br><span style='color:#333;font-size:14px'>{s_}</span></div>")
    arr = "<div style='font-size:20px;color:#555;align-self:center;padding:0 3px'>→</div>"

    def lane(title, note, boxes, tone):
        return (f"<div style='border:1px dashed #777;border-radius:8px;padding:8px 10px;margin-bottom:10px;background:{tone}'>"
                f"<div style='font-size:16px;margin-bottom:6px'><b>{title}</b><br><span style='color:#333;font-size:14px'>{note}</span></div>"
                f"<div style='display:flex;align-items:stretch'>{arr.join(boxes[:3])}</div>"
                f"<div style='font-size:18px;color:#555;text-align:right;padding-right:110px'>↓</div>"
                f"<div style='display:flex;align-items:stretch'>{arr.join(boxes[3:])}</div></div>")
    model = [box("01〜08", "研究台帳", "入力 124・算定式 53・出力 32・禁止事項"),
             box("09", "70 評価単位", "凍結した基準計算・生成器。近似 0 採用で停止"),
             box("10・11", "2 つの構造", "マスク付き積和・節点スペクトル。1,293 組で不一致 0"),
             box("17", "全体方程式", "区分一次・C = M + Z・解析手法の比較"),
             box("18", "動的 LCA", "工程関数・再構成・非一意性"),
             box("20・21", "大規模検証と報告", "100,000 ケース・上限 1.7×10⁻⁴・主張の強さ")]
    orig = [box("02・07", "構造の調査", "198 シート・数式セル 3,818,483"),
            box("13", "入力の分類", "構造だけの台帳 14,652 行"),
            box("14", "全数式の開示", "独立方程式 667"),
            box("15", "2 構造への変換", "647 式・全セル・2,000 ケース"),
            box("16", "未解決 8 式", "方式 A（厳密）・表せないことの証明"),
            box("19", "残り 12 式", "方式 A・下流への影響")]
    lane1 = lane("独立概念モデル（架空データ）", "数学的な成果はこの対象について。公開してよい", model, "#fafafa")
    lane2 = lane("J-CAT 原版（利用条件により非公開）", "件数と方法だけを公開。数式の文・値・セル番地は非公開", orig, "#f1f1f1")
    bottom = ("<div style='display:flex;gap:10px;align-items:stretch'>"
              + box("12", "アプリの基礎", "入力変換・表示・SQLite 保存。計算は統一系", w=320)
              + box("22", "教材（本書）", "五つの原理 P1〜P5 ＋ E で全体を学ぶ。問題 47 問", w=320, tone="#eaeaea") + "</div>"
              + "<div style='font-size:14px;color:#333;margin-top:8px;width:700px'>上の帯の 2 つの構造（10・11）を、下の帯の変換（15〜19）で使った。"
                "二つの帯の結果を混同しない（原版の式を表せることは、J-CAT と同じ結果を出すことではない）。</div>")
    return f"<div style='padding:12px;background:#fff;font-family:IPAGothic;width:720px'>{lane1}{lane2}{bottom}</div>"


def build() -> dict[str, Path]:
    figs = {
        "F0-1_principles": ("html", fig_principles()),
        "F1-1_stages": ("html", fig_stages()),
        "F4-1_steps": ("svg", fig_steps()),
        "F4-2_kernels": ("html", fig_kernels()),
        "F5-1_assembly": ("html", fig_assembly()),
        "F6-1_refrigerant": ("svg", fig_refrigerant()),
        "F7-1_MZ": ("svg", fig_mz()),
        "F3-1_derivations": ("html", fig_derivations()),
        "F0-2_research_map": ("html", fig_research_map()),
    }
    return to_png(figs, OUT)


if __name__ == "__main__":
    for k, v in build().items():
        print(k, v)
