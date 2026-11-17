# -*- coding: utf-8 -*-
"""12_原典とコード対応表.md と data/claims_by_source.csv を data/claims.csv から作る。

使い方（研究基盤のフォルダで）：python3 -B tools/build_claims_md.py（先に tools/build_claims.py）。標準ライブラリだけ。
"""
import csv
import os
import re
import sys
from collections import OrderedDict, defaultdict

sys.dont_write_bytecode = True
BASE = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = list(csv.DictReader(open(os.path.join(BASE, "data/claims.csv"), encoding="utf-8")))
TID = {r["orig_id"]: r["id"] for r in rows if r["kind"] == "theorem"}

SRC_ABBR = OrderedDict([
    ("10_TRANSFORM_STUDY/11_UNIFIED_SYSTEM/SPEC_MSP.md", "SMSP"),
    ("10_TRANSFORM_STUDY/11_UNIFIED_SYSTEM/SPEC_KNOTS.md", "SKN"),
    ("10_TRANSFORM_STUDY/11_UNIFIED_SYSTEM/UNITS_70.md", "U70"),
    ("10_TRANSFORM_STUDY/11_UNIFIED_SYSTEM/results/unit_map.json", "UMAP"),
    ("10_TRANSFORM_STUDY/11_UNIFIED_SYSTEM/DERIVATIONS.md", "DER"),
    ("10_TRANSFORM_STUDY/11_UNIFIED_SYSTEM/VERIFICATION.md", "VER"),
    ("10_TRANSFORM_STUDY/11_UNIFIED_SYSTEM/LIMITS.md", "LIM"),
    ("10_TRANSFORM_STUDY/03_ROUTES/experiments/README.md", "EXP"),
    ("10_TRANSFORM_STUDY/03_ROUTES/TC-B-01/IMPLEMENTATION_NOTES.md", "IMPL"),
    ("10_TRANSFORM_STUDY/05_HISTORY/README.md", "HIST"),
    ("10_TRANSFORM_STUDY/07_DECISIONS/README.md", "DEC"),
    ("10_TRANSFORM_STUDY/README.md", "T10"),
    ("14_EQUATION_DISCLOSURE/03_節点スペクトル全方程式.md", "14/03"),
    ("14_EQUATION_DISCLOSURE/04_マスク付き積和全方程式.md", "14/04"),
    ("14_EQUATION_DISCLOSURE/07_建物全体の統一方程式_完全版.md", "14/07"),
    ("14_EQUATION_DISCLOSURE/README.md", "14R"),
    ("17_WHOLE_BUILDING_TIME_THEORY/01_理想方程式.md", "17/01"),
    ("17_WHOLE_BUILDING_TIME_THEORY/02_係数表.md", "17/02"),
    ("17_WHOLE_BUILDING_TIME_THEORY/03_時間特性の定理と証明.md", "17/03"),
    ("17_WHOLE_BUILDING_TIME_THEORY/04_解析手法の比較.md", "17/04"),
    ("17_WHOLE_BUILDING_TIME_THEORY/05_最良表現.md", "17/05"),
    ("17_WHOLE_BUILDING_TIME_THEORY/06_70単位の時間特性.md", "17/06"),
    ("17_WHOLE_BUILDING_TIME_THEORY/07_検証の結果.md", "17/07"),
    ("18_DYNAMIC_LCA_EXTENSION/02_工程と時間変数.md", "18/02"),
    ("18_DYNAMIC_LCA_EXTENSION/03_工程間の関係.md", "18/03"),
    ("18_DYNAMIC_LCA_EXTENSION/04_再構成と整合.md", "18/04"),
    ("18_DYNAMIC_LCA_EXTENSION/05_時間配分の仮定と非一意性.md", "18/05"),
    ("18_DYNAMIC_LCA_EXTENSION/06_動的特性化.md", "18/06"),
    ("18_DYNAMIC_LCA_EXTENSION/07_検証の結果.md", "18/07"),
    ("20_LARGE_RANDOM_VERIFICATION/02_結果.md", "20/02"),
    ("20_LARGE_RANDOM_VERIFICATION/README.md", "20R"),
    ("21_UNIFIED_THEORY_REPORT/README.md", "21"),
    ("15_JCAT_CONVERSION/README.md", "15R"),
    ("15_JCAT_CONVERSION/04_検証の方法と結果.md", "15/04"),
    ("15_JCAT_CONVERSION/05_建物全体への接続.md", "15/05"),
    ("16_UNRESOLVED8_EXACT_APPROX/03_不可能性の証明.md", "16/03"),
    ("16_UNRESOLVED8_EXACT_APPROX/README.md", "16R"),
    ("19_JCAT_REMAINING12/README.md", "19R"),
    ("19_JCAT_REMAINING12/01_依存関係と必要性.md", "19/01"),
    ("19_JCAT_REMAINING12/02_変換方式.md", "19/02"),
    ("09_APPROX_STUDY/README.md", "09R"),
    ("09_APPROX_STUDY/01_LEDGER/README.md", "09L"),
    ("09_APPROX_STUDY/04_VERIFICATION/README.md", "09V"),
    ("22_WLC_COMPLETE_TEXTBOOK/record/research_record.md", "REC"),
    ("research_archive/real_equation_checkpoint/INDEX.md", "ARC"),
    ("01_COMPLIANCE/README.md", "COMPL"),
])
CODE_ABBR = [
    ("10_TRANSFORM_STUDY/research_code/", "10rc/"),
    ("17_WHOLE_BUILDING_TIME_THEORY/code/", "17c/"),
    ("18_DYNAMIC_LCA_EXTENSION/code/", "18c/"),
    ("20_LARGE_RANDOM_VERIFICATION/code/", "20c/"),
    ("09_APPROX_STUDY/research_code/", "09rc/"),
    ("15_JCAT_CONVERSION/tools/", "15t/"),
    ("16_UNRESOLVED8_EXACT_APPROX/tools/", "16t/"),
    ("19_JCAT_REMAINING12/tools/", "19t/"),
    ("WLC_THEORY_RESEARCH_BASE/", "base/"),
]


def esc(s):
    # 表のセルの | を逃がし、本文の数式 [c<T](p+qT) などが Markdown のリンクにならないよう ]( を ]\( にする
    return (s or "").replace("|", "\\|").replace("\n", " ").replace("](", "]\\(")


def short(s, n):
    s = s or ""
    return s if len(s) <= n else s[: n - 1] + "…"


def src_md(r, with_sec=True):
    ps = r["source_path"].split(" ; ") if r["source_path"] else []
    cs = r["source_commit"].split(" ; ") if r["source_commit"] else []
    ss = r["source_section"].split(" ; ") if r["source_section"] else [""] * len(ps)
    out = []
    for p, c, sec in zip(ps, cs, ss + [""] * (len(ps) - len(ss))):
        if p.startswith("WLC_THEORY_RESEARCH_BASE/"):
            fn = p.split("/", 1)[1]
            out.append(f"本基盤 {fn[:2]}" + (f" {sec}" if sec and with_sec else ""))
            continue
        ab = SRC_ABBR.get(p)
        name = f"[{ab}]" if ab else f"`{p}`"
        out.append(f"{name}@{c}" + (f" {sec}" if sec and with_sec else ""))
    return "；".join(out)


def code_md(r, with_fn=True, with_commit=True):
    ps = r["code_path"].split(" ; ") if r["code_path"] else []
    fs = r["code_function"].split(" ; ") if r["code_function"] else [""] * len(ps)
    cs = r["code_commit"].split(" ; ") if r["code_commit"] else [""] * len(ps)
    out = []
    for p, f, c in zip(ps, fs + [""] * (len(ps) - len(fs)), cs + [""] * (len(ps) - len(cs))):
        q = p
        for a, b in CODE_ABBR:
            if q.startswith(a):
                q = b + q[len(a):]
                break
        cc = "" if (c in ("（本基盤）", "") or not with_commit) else f"@{c}"
        out.append(f"`{q}`{cc}" + (f"（{f}）" if f and with_fn and not f.startswith("（") else (f if f and with_fn else "")))
    return "；".join(out) if out else "—"


def compress(ids):
    out, run = [], []
    def flush():
        if not run:
            return
        out.append(run[0] if len(run) == 1 else f"{run[0]}〜{run[-1]}")
    prev = None
    for i in ids:
        m = re.match(r"^([A-Z]+-)(\d+)$", i)
        if m and prev and prev[0] == m.group(1) and int(m.group(2)) == prev[1] + 1:
            run.append(i)
        else:
            flush()
            run = [i]
        prev = (m.group(1), int(m.group(2))) if m else None
    flush()
    return out



by = defaultdict(list)
for r in rows:
    by[r["kind"]].append(r)

L = []
w = L.append
w("# 12 原典とコード対応表：式・定理・主張から原典とコードへ")
w("")
w("本基盤（`WLC_THEORY_RESEARCH_BASE/`）の重要な式・定理・主張・検証件数・70 単位・仮説・未解決事項に ID を付け、"
  "**本基盤のどの節で扱い、証拠の区分は何で、原典のどのファイル（パス・コミット・節）に基づき、どのコードが計算または照合するか**を対応させた表である。"
  "どの主張からでも、ここを経て原典とコードまで戻れることを目的にする。")
w("")
w(f"- 全件（{len(rows)} 行）は機械可読の [data/claims.csv](data/claims.csv)（UTF-8）にある。この文書は CSV から作った要約で、"
  "式は全文、定理・主張は要約、検証件数・70 単位・仮説・未解決は ID の範囲と主な対応だけを載せる。範囲（`scope`）・照合（`checked_by`）・注記（`note`）の全文は CSV を見ること。")
w("- 対象の区別：系統 **A**＝独立した 70 評価単位の研究（架空データ）、**B**＝J-CAT 原版の変換実験（公開の水準：件数・分類・方法・結果だけ。原版の式本文・係数・値・セル番地は含まない）、"
  "**L**＝文献の標準的な理論、**BASE**＝本基盤で新しく書いたもの（計算・整理・仮説）。A と B はつながっていない（[01_研究の経緯.md](01_研究の経緯.md) §4）。")
w("- **計算結果の一致は、現実の建物の CO2 予測精度ではない**（係数はすべて架空）。")
w("- 作成：2026-11-17。原典は研究ブランチ `claude/jcat-lca-app-foundation-c33936` の `f2ea616`。コードのコミットは `git log -1 --format=%h f2ea616 -- <パス>` で取った（読み取りだけ）。")
w("")
w("## 1. 読み方")
w("")
w("### 1.1 ID と件数")
w("")
w("| 接頭辞 | 種類（CSV の `kind`） | 件数 | 本文の節 |")
w("|---|---|---:|---|")
names = [("F-", "formula", "式（定義・再利用する式。LaTeX つき）", "§2"), ("T-", "theorem", "定理・恒等式・補題（`data/theorems.csv` の 56 行＋本基盤で拾った行）", "§3"),
         ("C-", "claim", "主張（件数・分類・限界・記録）", "§4"), ("V-", "verification", "検証の件数（`data/verification_counts.csv` の 125 行）", "§5"),
         ("U-", "unit", "70 評価単位（`data/units70.json`）", "§6"), ("HYP-", "hypothesis", "仮説 A〜J（`data/hypotheses.csv`）", "§7"), ("OQ-", "open", "未解決事項（09 の OQ-01〜OQ-45）", "§7")]
for pre, k, desc, sec in names:
    w(f"| `{pre}` | {desc}（`{k}`） | {len(by[k])} | {sec} |")
w("")
w("T-01〜T-56 は `data/theorems.csv` の行の順、T-57 以降は本基盤の文書から拾った書き換え規則・本基盤の主張・文献の定理である。CSV の `orig_id` に原典側の ID（例 `17.TH-4`、`04.R5`、`15.DEG`）を残した。")
w("")
w("### 1.2 CSV の列")
w("")
w("| 列 | 内容 |")
w("|---|---|")
for k, v in [("id", "本表の ID"), ("kind", "種類（上の表）"), ("orig_id", "原典・本基盤の文書での ID"), ("statement", "主張・式の意味（日本語）"),
             ("latex", "式の LaTeX（F 行は `$$` を除いた本体、U 行は台帳 `data/units70.json` の `formula_latex` のまま（`$$…$$` と説明の文を含む））"), ("class", "証拠の区分 P・E・F・S・L・H。式の定義は「定義」、件数・所在の記録は「記録」、未解決事項は「未解決」"),
             ("scope", "成立範囲（定義域）。P・E・F・S の主張では必ず読む"), ("base_ref", "本基盤の文書と節（`05 §4.3` は 05_時間スペクトルの理論.md の 4.3 節。`09 OQ-07`、`10 HYP-I` は項目の見出し）"),
             ("source_path / source_commit / source_section", "原典（`whole-life-carbon-jcat-study/` からの相対パス、そのファイルを最後に変更したコミット、節）。複数は ` ; ` で区切り、順にそろえる。本基盤の文書は `WLC_THEORY_RESEARCH_BASE/…` と `（本基盤）`"),
             ("code_path / code_commit / code_function", "計算または照合するコード（同じく相対パス、コミット、関数・クラス・仕様のキー）"),
             ("checked_by", "照合・検算の記録（区分つき）"), ("lineage", "系統 A・B・L・BASE"), ("note", "注記")]:
    w(f"| `{k}` | {v} |")
w("")
w("### 1.3 この文書の略記")
w("")
w("原典（`パス@コミット`、パスは `whole-life-carbon-jcat-study/` から）：")
w("")
w("| 略記 | パス |")
w("|---|---|")
used = set()
for r in rows:
    for p in (r["source_path"].split(" ; ") if r["source_path"] else []):
        used.add(p)
for p, a in SRC_ABBR.items():
    if p in used:
        w(f"| [{a}] | `{p}` |")
w("")
w("コード：`10rc/`＝`10_TRANSFORM_STUDY/research_code/`、`17c/`＝`17_WHOLE_BUILDING_TIME_THEORY/code/`、`18c/`＝`18_DYNAMIC_LCA_EXTENSION/code/`、"
  "`20c/`＝`20_LARGE_RANDOM_VERIFICATION/code/`、`09rc/`＝`09_APPROX_STUDY/research_code/`、`15t/`・`16t/`・`19t/`＝第 15・16・19 章の `tools/`、`base/`＝本基盤。"
  "「本基盤 05 §x」は本基盤の文書。")
w("")
w("### 1.4 たどり方の例")
w("")
w(f"「$C(T)=M([0,T])+Z(T)$ はどこまで確かか」→ §3 の `17.TH-4` の行（{TID['17.TH-4']}）→ 区分 [P]、範囲「$T\\in(0,H]$、浮動小数の振幅・時刻を有理数とみなしたとき」→ 本基盤 05 §5.1・07 §2.2 → 原典 [17/03]@46781f2 TH-4 → コード `17c/timechar.py`（`realtime`・`RT`・`th45`）と `17c/timechar_terms.py`（S6）→ 照合 [E] 28,530 比較で不一致 0（V-048）。"
  "数値の照合はすべて標本の点での一致で、全入力での一致の証明ではない。")
w("")

# ---- F
w("## 2. 式（F-01〜F-%02d）" % len(by["formula"]))
w("")
w("区分の「定義」は仕様そのもの（主張ではない）。定義が実装どおりに働くことの確認や、定義から従う性質は `checked_by` と §3 の定理に書いた。注記は CSV の `note`。")
w("")
for r in by["formula"]:
    w(f"**{r['id']}**　{esc(r['statement'])}　〔{r['class']}〕")
    w("")
    if r["latex"]:
        w("$$ " + r["latex"] + " $$")
        w("")
    w(f"- 範囲：{esc(r['scope'])}")
    w(f"- 本基盤：{r['base_ref']}　原典：{src_md(r)}　コード：{code_md(r)}")
    if r["checked_by"] and r["checked_by"] != "—":
        w(f"- 確認：{esc(r['checked_by'])}")
    w("")

# ---- T
w("## 3. 定理・恒等式・補題（T-01〜T-%02d）" % len(by["theorem"]))
w("")
w("要約は短くした（全文と範囲は CSV の `statement`・`scope`、式は本基盤の該当節、コードのコミットは §8）。区分の「P＋F」などは、実数の主張が [P] で浮動小数での差が [F] のように、主張の部分ごとに区分が違うもの。"
  "本基盤で新しく書いた証明（系統 BASE の [P]）は独立の確認を受けていない。原典の定理（T-01〜T-56）は 08 §1 にも一覧がある（本基盤の列では 08 を省いた）。")
w("")
w("| ID | 元の ID | 主張（要約） | 区分 | 範囲（要約） | 本基盤 | 原典 | コード |")
w("|---|---|---|---|---|---|---|---|")
for r in by["theorem"]:
    w(f"| {r['id']} | `{r['orig_id']}` | {esc(short(r['statement'], 56))} | {r['class']} | {esc(short(r['scope'], 28))} | {re.sub(r'；08 §1\.\d', '', r['base_ref'])} | {esc(src_md(r))} | {esc(code_md(r, with_commit=False))} |")
w("")

# ---- C
w("## 4. 主張（C-01〜C-%02d）" % len(by["claim"]))
w("")
w("| ID | 主張（要約） | 区分 | 範囲（要約） | 本基盤 | 原典 | コード |")
w("|---|---|---|---|---|---|---|")
for r in by["claim"]:
    w(f"| {r['id']} | {esc(short(r['statement'], 84))} | {r['class']} | {esc(short(r['scope'], 40))} | {r['base_ref']} | {esc(src_md(r))} | {esc(code_md(r, with_fn=False, with_commit=False))} |")
w("")

# ---- V
w("## 5. 検証の件数（V-001〜V-%03d）" % len(by["verification"]))
w("")
w("1 行 1 照合（母集団・件数・合格・失敗・許容差・区分・出典）は CSV と [data/verification_counts.csv](data/verification_counts.csv)、本文は [08_証明と検証結果.md](08_証明と検証結果.md)。ここでは範囲ごとの対応だけを示す。")
w("")
groups = OrderedDict()
for r in by["verification"]:
    key = (r["base_ref"], r["code_path"], r["class"])
    groups.setdefault(key, []).append(r)
w("| V の範囲 | 内容（最初の行） | 区分 | 本基盤 | 原典 | コード |")
w("|---|---|---|---|---|---|")
for (bref, cpath, cls), rs in groups.items():
    rng = rs[0]["id"] if len(rs) == 1 else f"{rs[0]['id']}〜{rs[-1]['id']}"
    stmt = rs[0]["statement"].split("（")[0]
    srcs = "；".join(dict.fromkeys(src_md(x) for x in rs))
    w(f"| {rng} | {esc(short(stmt, 50))} | {cls} | {bref} | {esc(short(srcs, 90))} | {esc(code_md(rs[0], with_fn=False, with_commit=False))} |")
w("")
w("系統 B（第 15・16・19 章）の行の多くは原版または非公開資料が無いと再実行できない（[NONPUBLIC_INDEX.md](NONPUBLIC_INDEX.md)）。どのスクリプトがどの件数を出したかの記録が原典に無い行は、主な道具だけを挙げ、CSV の `note` にそう書いた。")
w("")

# ---- U
w("## 6. 70 評価単位（U-…、70 行）")
w("")
w("各単位の行は、名前・役割・段階・$T$ 依存・式（LaTeX、CSV の `latex`）・本基盤の節（[02_70評価単位の完全台帳.md](02_70評価単位の完全台帳.md) §5）・原典（[U70]@ac291dd の行、[UMAP]@ac291dd、直接寄与する単位は [14/07]@4c38df6 §3・§4）・"
  "コード（統一系 `10rc/tstudy/unified.py`（`System.at`）、仕様 `10rc/specs/`、凍結した基準計算の関数 `09rc/refcalc/units_*.py`、本基盤の照合 `base/tools/check_units70.py`）・照合の件数（V11 と台帳の照合 L）を持つ。"
  "70 単位は 70 個の独立した物理法則ではない：役割ごとの数は DIRECT 21・AGGREGATE 9・AUXILIARY 15・REFERENCE 10・DECISION 9・BREAKDOWN 6。")
w("")
w("| 02 の節 | 単位（役割の略記：D＝DIRECT、G＝AGGREGATE、A＝AUXILIARY、R＝REFERENCE、J＝DECISION、K＝BREAKDOWN） |")
w("|---|---|")
rolech = {"DIRECT": "D", "AGGREGATE": "G", "AUXILIARY": "A", "REFERENCE": "R", "DECISION": "J", "BREAKDOWN": "K"}
secs = OrderedDict()
for r in by["unit"]:
    sec = r["base_ref"].split(" ")[1]
    role = re.search(r"役割 (\w+)", r["statement"]).group(1)
    fn = r["code_function"].split(" ; ")[2] if len(r["code_function"].split(" ; ")) > 3 else ""
    fn = fn.replace("（凍結した基準計算）", "")
    secs.setdefault(sec, []).append(f"{r['id']}（{rolech.get(role, role)}{'・' + fn if fn else ''}）")
for sec, items in sorted(secs.items(), key=lambda kv: [int(x) for x in kv[0].lstrip("§").split(".")]):
    w(f"| 02 {sec} | {'、'.join(items)} |")
w("")
w("括弧の中の関数名は凍結した基準計算（`09rc/refcalc/`）の関数。全単位の照合の結果：台帳の式×統一系で不一致 0（C-23）、独立の評価 IND×統一系で不一致 0（C-33）、統一系×基準計算で不一致 0（C-03）。節点とその前後でも帯 $(K,\\mathrm{sw}(K))$ の外では不一致 0（C-34）で、整数の時刻の交換の直後の帯の違いは未解決（C-23）。入力の感度は C-35、構造と整合は C-36。")
w("")

# ---- HYP & OQ
w("## 7. 仮説（HYP-A〜HYP-J）と未解決事項（OQ-01〜OQ-45）")
w("")
w("仮説はすべて [H]（未検証）。本文は [10_新しい研究仮説.md](10_新しい研究仮説.md)、実験計画は [11_研究実験計画.md](11_研究実験計画.md) §3、関係する原典は CSV の `source_*`（[data/hypotheses.csv](data/hypotheses.csv) の `related_sources` から）。")
w("")
w("| ID | 仮説 | 本基盤 | 関係する原典（主なもの） |")
w("|---|---|---|---|")
for r in by["hypothesis"]:
    w(f"| {r['id']} | {esc(short(r['statement'].split('：')[0], 40))} | {r['base_ref']} | {esc(short(src_md(r, with_sec=False), 140))} |")
w("")
w("未解決事項は [09_未解決問題と限界.md](09_未解決問題と限界.md)（§1 の一覧、各項目の節）。CSV の `scope` に種類（自認・反例・欠落・原理的）と閉じ方、`note` に関係する仮説、`source_*` に項目の本文が引く主な原典（略記を 09 §0.4 の表で展開したもの）を入れた。")
w("")
t09 = open(os.path.join(BASE, "09_未解決問題と限界.md"), encoding="utf-8").read()
grp = OrderedDict()
cur = None
for line in t09.splitlines():
    m = re.match(r"^## (\d+)\. (.+)$", line)
    if m:
        cur = (m.group(1), m.group(2))
    m = re.match(r"^### (OQ-\d\d) ", line)
    if m and cur:
        grp.setdefault(cur, []).append(m.group(1))
w("| 09 の節 | 項目 |")
w("|---|---|")
for (num, title), ids in grp.items():
    w(f"| §{num} {esc(title)} | {'、'.join(compress(ids))} |")
w("")

# ---- reverse code index
w("## 8. コードからの逆引き")
w("")
w("コード（パス@コミット）→ それを使う ID。研究コードは**読み取り専用**で使う（変更しない）。出力先が固定でリポジトリを書き換えるものがあるので、実行の方法は [14_研究用データ索引.md](14_研究用データ索引.md) §5.2 と [13_別チャット引継ぎ文.md](13_別チャット引継ぎ文.md) §5。")
w("")
cidx = OrderedDict()
for r in rows:
    ps = r["code_path"].split(" ; ") if r["code_path"] else []
    cs = r["code_commit"].split(" ; ") if r["code_commit"] else [""] * len(ps)
    for p, c in zip(ps, cs):
        cidx.setdefault((p, c), []).append(r["id"])


w("| コード | コミット | ID |")
w("|---|---|---|")
for (p, c), ids in sorted(cidx.items()):
    q = p
    for a, b in CODE_ABBR:
        if q.startswith(a):
            q = b + q[len(a):]
            break
    uids = [i for i in ids if i.startswith("U-")]
    other = [i for i in ids if not i.startswith("U-")]
    lst = compress(other)
    if uids:
        lst.append(f"U- の {len(uids)} 単位")
    w(f"| `{q}` | {c} | {esc(short('、'.join(lst), 260))} |")
w("")

# ---- reverse source index
w("## 9. 原典からの逆引き")
w("")
w("原典のファイル（パス@コミット）→ それに基づく ID。章ごとの最終コミットは [00_README.md](00_README.md) §6。")
w("")
sidx = OrderedDict()
for r in rows:
    ps = r["source_path"].split(" ; ") if r["source_path"] else []
    cs = r["source_commit"].split(" ; ") if r["source_commit"] else [""] * len(ps)
    for p, c in zip(ps, cs):
        if p.startswith("WLC_THEORY_RESEARCH_BASE/"):
            continue
        sidx.setdefault((p, c), []).append(r["id"])
with open(os.path.join(BASE, "data/claims_by_source.csv"), "w", encoding="utf-8", newline="") as f:
    cw = csv.writer(f)
    cw.writerow(["source_path", "source_commit", "abbr", "ids"])
    for (p, c), ids in sorted(sidx.items()):
        cw.writerow([p, c, SRC_ABBR.get(p, ""), " ".join(ids)])
chap = OrderedDict()
for (p, c), ids in sorted(sidx.items()):
    k = p.split("/")[0]
    d = chap.setdefault(k, {"files": set(), "commits": set(), "ids": []})
    d["files"].add(p); d["commits"].add(c); d["ids"].extend(ids)
w("1 ファイル 1 行の逆引き（原典のパス・コミット・略記・ID の一覧）は [data/claims_by_source.csv](data/claims_by_source.csv)（この文書と同じスクリプトで作る）。章ごとの要約：")
w("")
w("| 章 | 引いたファイル数 | コミット | ID の数（うち F・T・C） |")
w("|---|---:|---|---|")
for k, d in chap.items():
    ftc = sum(1 for i in dict.fromkeys(d["ids"]) if i[:2] in ("F-", "T-", "C-"))
    w(f"| `{k}` | {len(d['files'])} | {'、'.join(sorted(d['commits']))} | {len(set(d['ids']))}（{ftc}） |")
w("")
w("## 10. 作り方と限界")
w("")
w("- この表は、本基盤の各文書（01〜11、14、15）と機械可読の表（`data/theorems.csv`、`verification_counts.csv`、`units70.json`、`hypotheses.csv`）、09 の一覧から作った。作り直しは `python3 -B tools/build_claims.py` の後に `python3 -B tools/build_claims_md.py`（手で選んだ行は `tools/claims_curated.py`）。"
  "F 行・C 行と T-57 以降の行は手で選び、ほかは表から機械的に写した。コードのコミットは git の記録から機械的に取った。")
w("- 区分は本基盤の文書と原典の区分を写したもので、ここで強めたものは無い。原典が曖昧なものは弱い区分にした（例：方式 A の判定できない割合の見積もり、指紋の衝突の上限を [H]）。")
w("- 第 15・16・19 章の件数とコードは公開章の水準で、どの非公開の入力から作られたかは書かない。原版の式本文・係数・値・セル番地はこの表にも CSV にも無い。")
w("- 検証件数の行（V-）のコードは、原典が「このコードで出した」と書くもの、または `data/data_index.csv` の `produced_by` によるものを挙げた。記録が無いものは主な道具を挙げ、`note` にそう書いた。")
w("- 関数名は、コードの中に `def`・`class`・仕様のキーとして実在することを確かめた（`S1〜S7` は `timechar_terms.py` の中の照合の節の名前）。")
w("- この表そのものは独立の検査を受けていない。")
w("")
text = "\n".join(L) + "\n"
open(os.path.join(BASE, "12_原典とコード対応表.md"), "w", encoding="utf-8").write(text)
print("bytes", len(text.encode("utf-8")))
