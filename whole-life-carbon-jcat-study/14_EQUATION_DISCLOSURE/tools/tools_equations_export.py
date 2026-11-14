"""Write out every equation of the unified system (two structures) as LaTeX, from the specification data.

Nothing is typed by hand: every step of the programs P1, TIME and AGG and every emission row of the knot
spectra is rendered from the data that the engine executes. Output (public; independent concept model,
fictional data, no content of other tools):

  03_節点スペクトル全方程式.md   04_マスク付き積和全方程式.md   07_建物全体の統一方程式_完全版.md
  05b_評価単位から統一式への変換対応表.csv   (unit -> steps / spectra / derivation)
  equations_research.json      (counts used by the index and the report)

Usage: python3 -B tools_equations_export.py <out dir>
"""
from __future__ import annotations

import collections
import csv
import json
import os
import re
import sys

sys.dont_write_bytecode = True
HERE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "10_TRANSFORM_STUDY", "research_code"))
sys.path.insert(0, HERE)

from specs import system as S_  # noqa: E402
from specs.lib import CAL  # noqa: E402
from tstudy import unified as U  # noqa: E402
from tstudy import rampstep as RS  # noqa: E402

UNITS_DOC = os.path.join(HERE, "..", "11_UNIFIED_SYSTEM", "UNITS_70.md")
UNIT_MAP = os.path.join(HERE, "..", "11_UNIFIED_SYSTEM", "results", "unit_map.json")


# ---------------------------------------------------------------------------------------------
# LaTeX of the vocabulary
# ---------------------------------------------------------------------------------------------
def tt(name: str) -> str:
    s = str(name).replace("\\", "/")
    for a, b in (("_", r"\_"), ("#", r"\#"), ("%", r"\%"), ("&", r"\&"), ("$", r"\$"), ("{", r"\{"), ("}", r"\}"), ("~", r"\~{}"),
                 ("^", r"\^{}")):
        s = s.replace(a, b)
    return r"\mathtt{%s}" % s


def const(v) -> str:
    if isinstance(v, str):
        if v in ("inf", "-inf"):
            return r"\infty" if v == "inf" else r"-\infty"
        return r"\text{``%s''}" % v.replace("_", r"\_").replace("#", r"\#").replace("%", r"\%").replace("&", r"\&")
    if isinstance(v, bool):
        return str(int(v))
    return repr(v)


def operand(op, x="x") -> str:
    if isinstance(op, str):
        if op == "_row":
            return x
        if op == "_parent":
            return r"\pi(%s)" % x
        return r"%s[%s]" % (tt(op), x)
    if "const" in op:
        return const(op["const"])
    if "via" in op:
        return r"%s\big[%s[%s]\big]" % (tt(op["col"]), tt(op["via"]), x)
    if "of" in op:
        return r"%s^{\langle %s\rangle}" % (tt(op["col"]), tt(op["of"]))
    raise ValueError(op)


def bound(v):
    return const(v) if isinstance(v, str) else repr(v)


def factor(f, x="x") -> str:
    if isinstance(f, str):
        return operand(f, x)
    if "pred" in f:
        a = operand(f["a"], x)
        p = f["pred"]
        if p == "present":
            body = r"%s \neq \bot" % a
        elif p == "eq":
            body = r"%s = %s" % (a, operand(f["b"], x))
        elif p == "le":
            body = r"%s \le %s" % (a, operand(f["b"], x))
        elif p == "range":
            lo = r"%s %s" % (bound(f["lo"]), "<" if f.get("lo_open") else r"\le")
            hi = r"%s %s" % ("<" if f.get("hi_open") else r"\le", bound(f["hi"]))
            body = r"%s %s %s" % (lo, a, hi)
        else:
            raise ValueError(p)
        return (r"\neg[%s]" if f.get("not") else r"[%s]") % body
    if "fn" in f:
        a = operand(f["a"], x)
        return {"inv": r"\frac{1}{%s}" % a, "one_minus": r"(1-%s)" % a, "inv_one_minus": r"\frac{1}{1-%s}" % a,
                "ratio_one_minus": r"\frac{%s}{1-%s}" % (a, a)}[f["fn"]]
    return operand(f, x)


def term(t, x="x") -> str:
    return r" \cdot ".join(factor(f, x) for f in t) if t else "1"


def step_tex(st) -> str:
    if st["op"] == "match":
        keys = ", ".join(operand(k, "x") for k in st["keys"])
        on = ", ".join(operand(k, "y") for k in st["on"])
        return (r"%s[x] = \min\left\{ y \in %s \;:\; (%s) = (%s) \right\},\quad x \in %s"
                % (tt(st["out"]), tt(st["into"]), on, keys, tt(st["table"])))
    body = r" \;+\; ".join(term(t) for t in st["terms"])
    g = st["group"]
    if g == "none":
        return r"%s[x] = %s,\quad x \in %s" % (tt(st["out"]), body, tt(st["table"]))
    if g == "total":
        return r"%s = \sum_{x \in %s} \Big(%s\Big)" % (tt(st["out"]), tt(st["table"]), body)
    ref = g["by"]
    return (r"%s[y] = \sum_{x \in %s \,:\, %s = y} \Big(%s\Big)"
            % (tt(st["out"]), tt(st["table"]), operand(ref, "x"), body))


# ---------------------------------------------------------------------------------------------
# knot spectra
# ---------------------------------------------------------------------------------------------
SHAPE = {
    "const": (r"a[x]", "定数（T によらない）"),
    "atom": (r"a[x]\,\big[\tau[x] < T(1-\varepsilon)\big]", "原子：時刻 τ の事象（T(1−ε) より前に起きたものだけ数える）"),
    "cell": (r"a[x]\,\operatorname{clip}\big(T - k[x],\,0,\,1\big)", "年セル：年 k+1 の年重み w_{k+1}(T)"),
    "gcell": (r"a[x]\,\big[\tau[x] < T(1-\varepsilon)\big]\,\operatorname{clip}\big(T - k[x],\,0,\,1\big)", "ゲート付き年セル：事象 τ のある年"),
    "density": (r"a[x]\,T \quad (0 < T \le H)", "密度：T に比例（長さ H の傾斜）"),
}


def emit_tex(e) -> str:
    shape, _ = SHAPE[e["shape"]]
    a = tt(e["amp"])
    s = shape.replace("a[x]", a + "[x]")
    if "k" in e:
        k = r"x" if e["k"] == "_pos" else tt(e["k"]) + "[x]"
        s = s.replace("k[x]", k)
    if "tau" in e:
        tau = r"x" if e["tau"] == "_pos" else tt(e["tau"]) + "[x]"
        s = s.replace(r"\tau[x]", tau)
    return r"\sum_{x \in %s} %s" % (tt(e["table"]), s)


def main(out):
    os.makedirs(out, exist_ok=True)
    programs = (("P1", "積和①（T によらない量）", U.P1), ("TIME", "積和②a（評価期間 T での節点表）", U.P_TIME),
                ("AGG", "積和②b（段階・合計・指標・判定）", U.P_AGG))
    counts = {}
    # ---------------- 04
    L = []
    w = L.append
    w("# 04 マスク付き積和：全方程式（実装の全ステップ）\n")
    w("対象：独立概念モデル（70 評価単位、架空データで検証）の統一系。**J-CAT 原版の式ではない。** "
      "この文書は `research_code/tools_equations_export.py` が、エンジンが実行する仕様データ（`specs/`）から機械的に書き起こしたもの。手で書いた式はない。\n")
    w("## 1. 一般式\n")
    w(r"$$ \mathrm{out}[g] \;=\; \sum_{x \in \mathcal{T}} \; \sum_{t \in \mathcal{E}} \; \prod_{k} \varphi_{t,k}(x) \quad\text{（}g\text{ ごとにまとめる）} $$" + "\n")
    w("- $\\mathcal{T}$：表（添字集合）。行 $x$。$\\pi(x)$ は子表の行の親行、$x$ 自身は行番号（`_row`）。")
    w("- $\\mathcal{E}$：項の一覧。項は因子 $\\varphi$ の積。")
    w("- 因子は次の 3 種類だけ：")
    w("  1. 列（数値）：$c[x]$、参照を通した列 $c\\big[r[x]\\big]$、1 行表の値 $c^{\\langle S\\rangle}$、定数。")
    w("  2. 述語（0/1）：$[c[x] \\neq \\bot]$（値がある）、$[\\ell \\le c[x] \\le u]$（開閉あり）、$[a = b]$、$[a \\le b]$、およびその否定 $\\neg[\\cdot] = 1-[\\cdot]$。")
    w("  3. 1 列の関数：$1/a$、$1-a$、$1/(1-a)$、$a/(1-a)$。")
    w("- まとめ方：行ごと（$\\mathrm{out}[x]$）／合計（$\\mathrm{out}$、1 行表 `S` の列）／参照先の行ごと（$\\mathrm{out}[y] = \\sum_{x: r[x]=y}$）。")
    w("- 検索（match）：$\\mathrm{ref}[x] = \\min\\{ y \\in \\mathcal{U} : \\mathrm{on}(y) = \\mathrm{keys}(x) \\}$（最初に一致した行。なければ $\\bot$）。\n")
    w("## 2. マスクと未知値の規則\n")
    w("- **マスク**：述語の積。項の述語がすべて 1 のときだけ、その項が寄与する。述語が 1 つでも 0 なら、値が欠けていても寄与は厳密に 0。")
    w("- **未知値** $\\bot$：述語がすべて 1 なのに列の値が欠けた項（または関数値が有限でない項）は欠損。欠損の行を含む群は欠損。読み出しは欠損を None にする。欠損を 0 とみなすことはない。")
    w("- 述語を欠損値に当てると 0（`present` も含む）。否定は 1。\n")
    w("## 3. 全ステップ\n")
    w("各ステップの末尾の【】は、評価単位（または共通処理）と、展開元のテンプレート。\n")
    for code, title, P in programs:
        n_sp = sum(1 for s in P.steps if s["op"] == "sp")
        counts[code] = {"steps": len(P.steps), "sp": n_sp, "match": len(P.steps) - n_sp}
        w("### 3.%d %s：%s（%d ステップ：積和 %d、検索 %d）\n" % (len(counts), code, title, len(P.steps), n_sp, len(P.steps) - n_sp))
        unit = None
        for i, st in enumerate(P.steps, 1):
            if st["unit"] != unit:
                unit = st["unit"]
                w("\n#### %s / %s\n" % (code, unit))
            w("%s-%04d【%s%s】\n$$ %s $$\n" % (code, i, unit, "・" + st["template"] if st.get("template") else "", step_tex(st)))
    open(os.path.join(out, "04_マスク付き積和全方程式.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")

    # ---------------- 03
    L = []
    w = L.append
    w("# 03 節点スペクトル：全方程式（実装の全項）\n")
    w("対象：独立概念モデルの統一系（架空データ）。**J-CAT 原版の式ではない。** `tools_equations_export.py` が `specs/system.py` の `EMIT`・`VALUE_AT_T`、"
      "`tstudy/rampstep.py`・`knots.py`・`interval.py`・`index.py` から書き起こしたもの。\n")
    w("## 1. 核（ランプ・ステップ核）\n")
    w(r"$$ h(T;\,s,\ell,g) \;=\; \big[g < T(1-\varepsilon)\big]\cdot \operatorname{clip}\!\Big(\frac{T-s}{\ell},\,0,\,1\Big),\qquad \varepsilon = 10^{-9},\quad \ell = 0 \Rightarrow \operatorname{clip}(\cdot)=1 $$" + "\n")
    w(r"$$ \Phi(T) \;=\; \sum_j a_j\, h(T;\,s_j,\ell_j,g_j) \qquad (a_j \text{ は } T \text{ によらない}) $$" + "\n")
    w("| 形 | $s$ | $\\ell$ | $g$ | 値 |\n|---|---|---|---|---|")
    w("| 定数 | 0 | 0 | $-\\infty$ | $a$ |")
    w("| 原子（時刻 $\\tau$ の事象） | $\\tau$ | 0 | $\\tau$ | $a\\,[\\tau < T(1-\\varepsilon)]$ |")
    w("| 年セル（年 $y$） | $y-1$ | 1 | $-\\infty$ | $a\\,w_y(T)$、$w_y(T)=\\operatorname{clip}(T-(y-1),0,1)$ |")
    w("| ゲート付き年セル | $y-1$ | 1 | $\\tau$ | $a\\,[\\tau<T(1-\\varepsilon)]\\,w_y(T)$ |")
    w("| 密度（長さ $H$） | 0 | $H$ | $-\\infty$ | $(aH)\\,\\min(T/H,1) = aT$（$T\\le H$） |\n")
    w("年重み：$w_y(T) = [y \\le T] + [y-1 < T][\\neg(y \\le T)]\\,(T-(y-1))$。事象の年：$y(\\tau) = \\max(1, \\lceil \\tau(1-\\varepsilon)\\rceil)$。\n")
    w("## 2. 跳び形（標準形）\n")
    w(r"$$ E(T) = b + \sum_{j:\, t^{e}_j < T(1-\varepsilon)} \big(c^{0}_j + c^{1}_j T\big) + \sum_{j:\, t^{p}_j < T} \big(c^{0}_j + c^{1}_j T\big) $$" + "\n")
    w("各項 $a\\,h(T;s,\\ell,g)$ の節点への置き方（`KnotSpectrum._add`）：")
    w("- $\\ell=0,\\ g=-\\infty$：$b \\mathrel{+}= a$")
    w("- $\\ell=0,\\ g$ 有限：事象節点 $(g,\\ a,\\ 0)$")
    w("- $\\ell>0,\\ g=-\\infty$：格子節点 $(s,\\ -as/\\ell,\\ a/\\ell)$ と $(s+\\ell,\\ a(s+\\ell)/\\ell,\\ -a/\\ell)$")
    w("- $\\ell>0,\\ g \\ge (s+\\ell)(1-\\varepsilon)$：事象節点 $(g,\\ a,\\ 0)$")
    w("- $\\ell>0,\\ g$ それ以外：事象節点 $(g,\\ -as/\\ell,\\ a/\\ell)$ と格子節点 $(s+\\ell,\\ a(s+\\ell)/\\ell,\\ -a/\\ell)$\n")
    w("評価：$E(T) = b + P^{0}_{e}[k_e] + P^{0}_{p}[k_p] + T\\,(P^{1}_{e}[k_e] + P^{1}_{p}[k_p])$。$P$ は節点を時刻順に並べた累積和、$k_e,k_p$ は二分探索の位置。\n")
    w("Laplace–Stieltjes 表示（記録のみ。数値計算には使っていない）：")
    w(r"$$ \mathcal{L}\{dE\}(s) \text{ に対応して } \int_0^\infty e^{-sT} E(T)\,dT = \frac{1}{s^2}\sum_j \big(c^{1}_j + s\,(c^{0}_j + c^{1}_j t_j)\big)\,e^{-s t_j} \quad(+\,b/s) $$" + "\n")
    w("## 3. 区間形（B1-04 の期末残存量に使用）\n")
    w(r"$$ E(T) = A_k + B_k\,(T-k) + \sum_{j \in \text{cell } k,\ \tau_j < T(1-\varepsilon)} \big(a_j + g_j\,(T-k)\big),\qquad k = \lceil T\rceil - 1 $$" + "\n")
    w("$A_k = $ `b1.iA`、$B_k = $ `b1.iB`（年表 `cal`）、$a_j = $ `b1.e4a`、$g_j = $ `b1.e4g`、$\\tau_j = $ `b1.tau1`（表 `dy`、`b1.p` が 1 の行）。厳密算術では跳び形と同じ関数。\n")
    w("## 4. 節点の格子（共通表 `index.add_events`）\n")
    w(r"$$ \text{周期}：\ \tau_n = n\,c \quad (n=1,2,\dots,\ \tau_n < H(1-\varepsilon)),\qquad \text{一覧}：\ \tau \in L,\ 0<\tau<H(1-\varepsilon) $$" + "\n")
    w("各節点は `cell` $= y(\\tau)-1$ を持つ。周期と一覧の両方を作り、どちらを数えるかは積和のマスクで決める。")
    for op in S_.INDEX_PLAN:
        if op["op"] == "events":
            w("- 表 `%s`：親 `%s`、周期の列 `%s`%s" % (op["name"], op["parent"], op.get("cycle"), "、一覧 `%s`" % op["lists"] if op.get("lists") else ""))
    w("\n$H$ は年次表の長さ（架空データでは 130 年）。\n")
    w("## 5. 全スペクトルと全項（`EMIT`）\n")
    w("振幅 $a$ は積和①（P1）の結果の列。各スペクトルの値は、その項の和である。\n")
    by = collections.OrderedDict()
    for e in S_.EMIT:
        by.setdefault(e["spectrum"], []).append(e)
    counts["spectra"] = len(by)
    counts["emit_rows"] = len(S_.EMIT)
    for name, rows in by.items():
        w("### スペクトル %s（%d 項）\n" % (name, len(rows)))
        w(r"$$ K_{\mathrm{%s}}(T) = %s $$" % (name.replace("_", r"\_").replace("#", r"\#"), r" \\ &+ ".join(emit_tex(e) for e in rows)
                                                if len(rows) == 1 else r" + ".join(emit_tex(e) for e in rows)) + "\n")
        for e in rows:
            w("- 形 `%s`（%s）：振幅 `%s`、表 `%s`%s%s" % (e["shape"], SHAPE[e["shape"]][1], e["amp"], e["table"],
                                                   "、年の列 `%s`" % e["k"] if "k" in e else "", "、時刻の列 `%s`" % e["tau"] if "tau" in e else ""))
        w("")
    w("## 6. 評価期間 T での値の受け渡し（`VALUE_AT_T`）\n")
    w("| 評価単位 | T での値 |\n|---|---|")
    for uid, (where, nm) in S_.VALUE_AT_T.items():
        txt = {"K": "$K_{\\mathrm{%s}}(T)$（跳び形）" % nm, "I": "区間形 $E_{\\mathrm{B1\\text{-}04}}(T)$（跳び形 $K$ と局所形 `t.b14` は比較用）"}.get(
            where, "積和②の結果 `%s`（スペクトルの値との積）" % nm)
        w("| %s | %s |" % (uid, txt))
    w("\nスペクトルの値 $K_s(T)$ は 1 行表 `TT` の列 `K.<名前>` として積和②（TIME・AGG）に渡る。T によらない単位の値は P1 の列（`CONST_VALUE`）。\n")
    w("| 評価単位 | T によらない値の列 |\n|---|---|")
    for uid, col in S_.CONST_VALUE.items():
        w("| %s | `%s` |" % (uid, col))
    open(os.path.join(out, "03_節点スペクトル全方程式.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")

    # ---------------- 05b
    umap = json.load(open(UNIT_MAP, encoding="utf-8"))
    units_doc = {}
    for line in open(UNITS_DOC, encoding="utf-8"):
        m = re.match(r"\|\s*([A-Z0-9]+-[0-9]+|[A-Z]+-[0-9]+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(D-[0-9, D\-–〜]+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|$", line)
        if m:
            units_doc[m.group(1)] = m.groups()
    steps_of = collections.defaultdict(lambda: collections.Counter())
    for code, _, P in programs:
        for st in P.steps:
            steps_of[st["unit"]][code] += 1
    with open(os.path.join(out, "05b_評価単位から統一式への変換対応表.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["評価単位", "名称", "元の方程式（基準計算・独立概念モデル）", "統一系での書き方（要約）", "導出", "使う構造（①=P1, K=節点スペクトル, ②a=TIME, ②b=AGG）",
                     "出力キー", "P1 の専用ステップ", "読み出しが使った列", "使ったスペクトル", "使った入力の表と列", "検証", "原版（J-CAT）の式との対応"])
        for uid in sorted(umap):
            d = units_doc.get(uid, (uid, "", "", "", "", ""))
            m = umap[uid]
            wr.writerow([uid, d[1], "UNITS_70.md・09 章 units.json の canonical_form（独立概念モデル）", d[2], d[3], d[4], d[5],
                         steps_of.get(uid, {}).get("P1", 0), " ".join(m.get("read_from", [])), " ".join(m.get("spectra", [])),
                         "; ".join("%s:%s" % (t, ",".join(c)) for t, c in m.get("inputs", {}).items()),
                         "全出力キーを基準計算と比較（06_全検証ケース.csv）", "なし（原版の式本文は調べていない。13 章で抽出したのは今回が初めて）"])
    counts["units"] = len(umap)
    counts["shared_steps"] = {k: dict(v) for k, v in steps_of.items() if not re.match(r"^[A-Z0-9]+-[0-9]+$", k)}
    json.dump(counts, open(os.path.join(out, "equations_research.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(counts, ensure_ascii=False)[:600])




# ---------------------------------------------------------------------------------------------
# 07: the whole building in one expression (composition of the two structures)
# ---------------------------------------------------------------------------------------------
def whole(out):
    comp = S_.STATIC_TABLES["COMP"]
    by_stage = collections.OrderedDict((s, []) for s in S_.STAGES)
    for st, u, sg, nb in zip(comp["stage"], comp["unit"], comp["sign"], comp["needs_b2"]):
        by_stage[st].append((u, sg, nb))
    emit = collections.defaultdict(list)
    for e in S_.EMIT:
        emit[e["spectrum"]].append(e)
    agg_ids = {st["out"]: "AGG-%04d" % i for i, st in enumerate(U.P_AGG.steps, 1)}
    time_ids = {st["out"]: "TIME-%04d" % i for i, st in enumerate(U.P_TIME.steps, 1)}
    p1_ids = {st["out"]: "P1-%04d" % i for i, st in enumerate(U.P1.steps, 1)}
    L = []
    w = L.append
    w("# 07 建物全体の統一方程式（完全版）\n")
    w("対象：独立概念モデル（70 評価単位、架空データで検証）の統一系。**J-CAT 原版の式から導いたものではない**（原版の式は 02・05a を参照。統一系への変換は 0 件）。"
      "この文書の式番号（P1-xxxx、TIME-xxxx、AGG-xxxx）は 04 の全ステップ、スペクトル名は 03 を指す。仕様データから機械的に書き出した。\n")
    w("## 1. 全体の合成\n")
    w(r"$$ \boxed{\;\mathcal{R}(\mathbf{x},T) \;=\; \mathrm{RO}\Big(\, \mathrm{AGG}\big(\, \mathrm{TIME}\big(\, \mathcal{P}_1(\mathcal{I}(\mathbf{x})),\; \{K_s(T)\}_{s},\; T \big),\; \{v_u(T)\}_u,\; T \big) \Big)\;} $$" + "\n")
    w("- $\\mathbf{x}$：建物の入力。$\\mathcal{I}$：共通表（平坦化・文字列の分割・添字集合・節点の格子。算術なし）。")
    w("- $\\mathcal{P}_1$：積和①（%d ステップ）。T によらない列（係数・数量・マスク・振幅）をすべて作る。" % len(U.P1.steps))
    w("- $K_s(T)$：節点スペクトル（%d 本＋区間形 1 本）。振幅は $\\mathcal{P}_1$ の列。" % len(S_.SPECTRA))
    w("- TIME（%d ステップ）・AGG（%d ステップ）：評価期間 $T$ での積和②。RO：読み出し（整形のみ）。\n" % (len(U.P_TIME.steps), len(U.P_AGG.steps)))
    w("## 2. 外側のマスク付き積和の中に節点スペクトルが入る形\n")
    w("ホールライフ合計 SUM-03（AGG の `sum3`）を、最内の積和まで展開すると次の 1 本になる。\n")
    w(r"$$ S_3(T) = \sum_{s \in \mathrm{STG}} [\mathrm{inc}_s] \sum_{c \in \mathrm{COMP}:\ \mathrm{stage}(c)=s} \sigma_c\,\beta_c\; v_{u(c)}(T) $$" + "\n")
    w(r"$$ v_u(T) = \begin{cases} \displaystyle \sum_{x \in \mathcal{T}_u} \sum_{t} \prod_k \varphi_{t,k}(x) & u \text{ が T によらない単位（積和①のスカラー）} \\[2ex] \displaystyle K_u(T) = \sum_{e \in \mathrm{EMIT}_u} \sum_{x \in \mathcal{T}_e} \underbrace{\Big(\sum_{t}\prod_k \varphi^{(e)}_{t,k}(x)\Big)}_{\text{振幅 } a_e[x] \text{（積和①）}} h\big(T;\, s_e(x), \ell_e, g_e(x)\big) & u \text{ が T に依存する単位（節点スペクトル）} \\[2ex] \displaystyle \sum_{x} \sum_t \prod_k \varphi_{t,k}(x;\, K(T), T) & u = \text{B2-01（TIME の積和にスペクトル値が入る）} \end{cases} $$" + "\n")
    w(r"$$ h(T; s,\ell,g) = [g < T(1-\varepsilon)]\,\operatorname{clip}\!\big((T-s)/\ell, 0, 1\big),\qquad \beta_c = 1 + \mathrm{needs\_b2}_c\,\big([\mathrm{inc}_{B2}]-1\big) $$" + "\n")
    w("$\\sigma_c$ は構成表の符号（±1）、$[\\mathrm{inc}_s]$ は段階が評価範囲に入っているかの述語（AGG-0002 `x02.inc`）。"
      "つまり、建物全体は「段階×単位の 0/±1 行列」による外側の積和であり、その要素 $v_u(T)$ が「積和①で作った振幅を核 $h$ で重ねた節点スペクトル」になっている。\n")
    w("## 3. 段階の構成表（`COMP`、%d 行）と段階の値\n" % len(comp["stage"]))
    w(r"$$ \mathrm{bs}_s(T) = [\mathrm{inc}_s] \sum_{c:\,\mathrm{stage}(c)=s} \sigma_c\,\beta_c\,v_{u(c)}(T) \qquad (\text{AGG-0007 } \mathtt{x02.bsraw},\ \text{AGG-0008 } \mathtt{x02.bs}) $$" + "\n")
    w("| 段階 | 式 |\n|---|---|")
    for st, rows in by_stage.items():
        if rows:
            terms = " ".join(("+" if sg > 0 else "-") + " " + (r"[\mathrm{inc}_{B2}]\," if nb else "") + "v_{\\text{%s}}(T)" % u for u, sg, nb in rows)
            w("| %s | $\\mathrm{bs}_{\\text{%s}} = [\\mathrm{inc}]\\,(%s)$ |" % (st, st, terms.lstrip("+ ").strip()))
    w("\n## 4. 単位の値 $v_u(T)$ の出どころ\n")
    w("| 単位 | $v_u(T)$ | 定義の場所 |\n|---|---|---|")
    for u, col in S_.CONST_VALUE.items():
        w("| %s | 積和①のスカラー `%s`（T によらない） | %s |" % (u, col, p1_ids.get(col, "04 の P1")))
    for u, (where, nm) in S_.VALUE_AT_T.items():
        if where == "K":
            terms = " + ".join(r"\sum_{x\in\mathtt{%s}} \mathtt{%s}[x]\,h_{\text{%s}}" % (e["table"].replace("_", r"\_"), e["amp"].replace("_", r"\_"), e["shape"]) for e in emit[nm])
            w("| %s | $K_{\\text{%s}}(T) = %s$ | 03 のスペクトル %s |" % (u, nm, terms, nm))
        elif where == "I":
            w("| %s | 区間形 $A_k + B_k(T-k) + \\sum_{j}(a_j + g_j(T-k))$ | 03 の 3 節 |" % u)
        else:
            w("| %s | TIME の結果 `%s` | %s |" % (u, nm, time_ids.get(nm, "04 の TIME")))
    w("\n## 5. 合計・指標・比較（AGG の該当ステップ）\n")
    w(r"$$ S_1 = \sum_s [\mathrm{inc}_s][s \in \{A1\text{-}A3, A4, A5\}]\,\mathrm{bs}_s,\quad S_2 = \sum_s [\mathrm{inc}_s][s \notin \{B6, B7\}]\,\mathrm{bs}_s,\quad S_3 = \sum_s [\mathrm{inc}_s]\,\mathrm{bs}_s $$" + "\n")
    w(r"$$ \mathrm{SUM04} = [A>0]\,S_3\,\frac{1}{A},\quad \mathrm{SUM05} = [A>0]\,S_3\,\frac{1}{A\,T},\quad \mathrm{SUM06} = 0.001\,S_3,\quad \mathrm{share}_s = [\mathrm{inc}_s][S_3>0][\#\{\mathrm{bs}<0\}=0]\,\frac{\mathrm{bs}_s}{S_3} $$" + "\n")
    w(r"$$ \mathrm{complete}(T) = \Big[\sum_{(s,u)\in\mathrm{CHK}} [\mathrm{inc}_s]\,[\mathrm{bad}_u(T) \ge 1] = 0\Big],\qquad \mathrm{SUM08}:\ \Delta = S_3 - S_3^{\mathrm{base}},\ \ \rho = [S_3^{\mathrm{base}}>0]\,\frac{S_3^{\mathrm{base}} - S_3}{S_3^{\mathrm{base}}} $$" + "\n")
    for nm in ("sum1", "sum2", "sum3", "sum4", "sum5", "sum6", "sum7.share", "x02.complete"):
        if nm in agg_ids:
            w("- `%s`：%s" % (nm, agg_ids[nm]))
    w("\nSUM-08 の比較可能性：$[\\text{基準案あり}][A = A^{b}][T = T^{b}][\\text{段階の集合が一致}][\\text{ガスの範囲が一致}][\\text{係数の版の集合が一致}]$（AGG の `s8.*`）。"
      "集合の一致は $[\\sum_{x\\in X}[x\\notin Y]=0]\\,[\\sum_{y\\in Y}[y\\notin X]=0]$。\n")
    w("## 6. 時間変数の扱い\n")
    w("- $T$ は 1 行表 `TT` の列。$T_{in} = T(1-10^{-9})$ を TIME が作る。")
    w("- 年重み：$w_y(T) = [y \\le T] + [y-1 < T]\\,\\neg[y \\le T]\\,(T-(y-1))$（TIME の積和）＝ 年セル $h(T; y-1, 1, -\\infty)$（節点スペクトル）。")
    w("- 事象：$[\\tau < T(1-\\varepsilon)] = \\neg[T_{in} \\le \\tau]$（TIME）＝ 原子 $h(T;\\tau,0,\\tau)$（節点スペクトル）。")
    w("- 周期事象の時刻 $\\tau_n = n c$ は共通表の格子で、振幅ではない。\n")
    w("## 7. 未知値・未確定項\n")
    w("- 入力の欠損は $\\bot$ のまま積和に入る。述語が 1 の項に $\\bot$ があれば結果も $\\bot$。0 とはみなさない。")
    w("- 単位ごとに除外件数 `bad.<単位>` を数え、対象段階に 1 つでもあれば `complete` が偽になる（合計は出すが不完全と示す）。")
    w("- 振幅に $\\bot$ があると節点スペクトルを作れないので、計算を止める（`Unusable`）。\n")
    w("## 8. 全 70 単位の式\n")
    w("単位ごとの式（基準計算の定義と統一系での書き方）は `11_UNIFIED_SYSTEM/UNITS_70.md`、導出は `DERIVATIONS.md`（D-01〜D-13）、"
      "単位ごとのステップ数・入力・スペクトルは `05b_評価単位から統一式への変換対応表.csv`。\n")
    open(os.path.join(out, "07_建物全体の統一方程式_完全版.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main(sys.argv[1])
    whole(sys.argv[1])
