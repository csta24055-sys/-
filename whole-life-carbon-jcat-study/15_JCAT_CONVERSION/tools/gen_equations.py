"""PRIVATE deliverable: for each of the 667 independent equations, the six items of the directive
(1 original equation, 2 with mathematical variables, 3 masked sum-product form, 4 knot spectra, 5 final unified
equation, 6 correspondence of variables and conditions), for the representative pattern, converted by the
base method and by the improved method. Output: one Markdown file with copyable LaTeX ($$ ... $$ blocks).

Usage: gen_equations.py <scan> <instances.pkl> <02b.csv> <final_class.json> <status.json> <out.md>"""
import sys, os
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "jcat_tools"))
import collections, csv, json, re
import fx
import excel_ref as X
import compile2 as K
import run_compile as RC
import render_tex as RT
from tstudy import msp

KNOT_DEF = {
    "integer lattice": r"F(x) = \sum_{m \ge 1} [\, m \le x \,] = \lfloor x \rfloor \ (x \ge 0),\quad "
                       r"\text{evaluated as } r_0 = x,\ r_{j+1} = r_j - 2^{51-j}\,[\,2^{51-j} \le r_j\,],\ \lfloor x \rfloor = x - r_{52}",
    "decimal lattice": r"E(y) = \sum_{k=-40}^{40} [\, 10^{k} \le y \,] - 41 = \lfloor \log_{10} y \rfloor,\quad "
                       r"h(y) = \sum_{k} [10^{k} \le y][\,y < 10^{k+1}]\; \tfrac12 10^{k-14}",
    "binary lattice": r"\mathrm{ulp}(q) = \sum_{k=-300}^{300} [\, 2^{k} \le |q| \,][\, |q| < 2^{k+1} \,]\; 2^{k-52}",
    "running count": r"O(p) = \sum_{q \le p} [\, \mathrm{nonblank}(q) \,]",
}


def knot_used(notes):
    out = []
    for k in notes:
        for name in KNOT_DEF:
            if name in k and name not in out:
                out.append(name)
    return out


def main():
    scan, inst, p02b, fcls, fstat, outp = sys.argv[1:7]
    RC.setup(scan, inst)
    rows = list(csv.DictReader(open(p02b, encoding="utf-8-sig")))
    by_eq = collections.defaultdict(list)
    for r in rows:
        by_eq[r["独立方程式ID"]].append(r)
    cls = json.load(open(fcls, encoding="utf-8"))
    status = json.load(open(fstat, encoding="utf-8"))
    out = open(outp, "w", encoding="utf-8")
    out.write("# 667 独立方程式の変換前後の全方程式（非公開）\n\n")
    out.write("**非公開資料。原版の数式本文を含む。公開リポジトリに載せないこと。**\n\n")
    out.write("各節：1 原版の方程式／2 数学変数に置き換えた式／3 マスク付き積和への変換式（全ステップ、改良方式）／"
              "4 節点スペクトル／5 最終的な統一方程式／6 変換前後の変数・計算条件の対応。\n\n")
    out.write("記法：$\\mathcal{T}_{\\mathrm{G}}$ は式の写し（セル）$i$ の集合。$t,n,s,k,e,p,q,w,o$ は値の成分"
              "（型、数値、文字列の識別符号、照合順位、エラー符号、文字列が読める数値とその有無、ワイルドカードの有無、比較演算子で始まるか）。"
              "$t^{(m)}_i$ はセル配置 $m$（6 の対応表）の成分。$[\\cdot]$ はアイバーソン括弧（マスク）。"
              "$v[\\rho]$ は参照列 $\\rho$ を通した取り出し。$\\min\\{y : \\cdots\\}$ は最初の一致（match）。\n\n")
    out.write("型の符号：0 空欄、1 数値、2 文字列、3 論理値、4 エラー。エラー符号：1 #NULL!、2 #DIV/0!、3 #VALUE!、4 #REF!、5 #NAME?、6 #NUM!、7 #N/A。\n\n")
    for eq in sorted(by_eq):
        pats = sorted(by_eq[eq], key=lambda r: -int(r["セル数"]))
        rep = pats[0]
        pid = rep["パターンID"]
        c = cls[eq]
        st = status[eq]
        out.write("## %s（%s セル、パターン %d）\n\n" % (eq, "{:,}".format(sum(int(r["セル数"]) for r in pats)), len(pats)))
        out.write("- 分類：%s %s（%s）。本質的な算定規則：%s。理由：%s（%s）\n" % (c["category"], c["category_name"], c["subtype"],
                                                                          "はい" if c["essential_rule"] else "いいえ（表示・転記）", c["reason"], c["decided"]))
        out.write("- 変換：基本方式 %s／改良方式 %s\n" % (st["base"], st["improved"]))
        if st.get("cause"):
            out.write("- 変換できない理由：%s\n" % st["cause"])
        out.write("- 検証：%s\n\n" % st["verification"])
        out.write("### 1 原版の方程式\n\n代表 %s：`%s`\n\n" % (rep["代表（ブック:シート!セル）"], rep["A 原版の式（代表）"]))
        if len(pats) > 1:
            out.write("参照先違いの変種（%d）：\n\n" % (len(pats) - 1))
            for r in pats[1:]:
                out.write("- %s（%s セル）`%s`\n" % (r["パターンID"], r["セル数"], r["A 原版の式（代表）"]))
            out.write("\n")
        out.write("### 2 数学変数に置き換えた式\n\n$$ %s $$\n\n" % rep["B LaTeX"])
        p = RC.DATA["patterns"][pid]
        (book, sheet), arr = next(iter(RC.DATA["instances"][pid].items()))
        try:
            ast = fx.Parser(fx.tokenize(p["text"])).parse()
            tree = X.prepare(ast, p["row"], RC.col_num(p["col"]), RC.STORE, book, sheet)
            b = K.Builder(RC.STORE, RC.SD, RC.CACHE, book, sheet, arr[:4, 0], arr[:4, 1])
            b.improve = True
            v = b.finish(b.ev(tree))
            lines, res, nm = RT.program_tex(b.steps, v.c)
            usage = collections.Counter()
            for u in msp.static_usage(b.program()).values():
                usage.update(u)
            out.write("### 3 マスク付き積和への変換式（%d ステップ）\n\n" % len(b.steps))
            if lines:
                out.write("$$\n\\begin{aligned}\n" + " \\\\\n".join(lines) + "\n\\end{aligned}\n$$\n\n")
            else:
                out.write("ステップなし（セルの配置だけで値が決まる：転記）。\n\n")
            ks = knot_used(b.notes)
            out.write("### 4 節点スペクトル\n\n")
            if ks:
                for k in ks:
                    out.write("- %s：$$ %s $$\n" % (k, KNOT_DEF[k]))
                out.write("\n")
            else:
                out.write("使わない（この規則は時間・丸め・位置の格子を必要としない）。\n\n")
            out.write("### 5 最終的な統一方程式\n\n")
            out.write("$$\n\\begin{aligned}\n" + " \\\\\n".join(res) + "\n\\end{aligned}\n$$\n\n")
            out.write("$$ y_i = \\mathcal{D}\\big(t_{\\mathrm{out}}(i),\\, n_{\\mathrm{out}}(i),\\, s_{\\mathrm{out}}(i),\\, e_{\\mathrm{out}}(i)\\big),\\quad "
                      "\\mathcal{D}(0,\\cdot)=0,\\ \\mathcal{D}(1,n)=n,\\ \\mathcal{D}(2,s)=\\mathrm{text}(s),\\ \\mathcal{D}(3,n)=(n=1),\\ \\mathcal{D}(4,e)=\\mathrm{error}(e) $$\n\n")
            out.write("ここで右辺の各成分は 3 のステップの合成（マスク付き積和と match の有限列）である。\n\n")
            out.write("### 6 変換前後の変数・計算条件の対応\n\n| 変換後 | 種類 | 原版のシート | 行 | 列 |\n|---|---|---|---|---|\n")
            for row in RT.legend(b, nm):
                out.write("| %s | %s | %s | %s | %s |\n" % (row["column"], row["kind"], row["sheet"], row["row"], row["col"]))
            out.write("\n計算条件の対応：%s\n\n" % "；".join("%s（%d）" % (k, n) for k, n in sorted(b.notes.items())))
            out.write("語彙の使用回数：%s\n\n" % "、".join("%s %d" % (k, n) for k, n in sorted(usage.items())))
        except K.Unsupported as e:
            out.write("### 3〜6\n\n**変換できない**：%s。マスク付き積和・節点スペクトルの式は作られない（成功とは数えない）。\n\n" % e)
    out.close()


if __name__ == "__main__":
    main()
