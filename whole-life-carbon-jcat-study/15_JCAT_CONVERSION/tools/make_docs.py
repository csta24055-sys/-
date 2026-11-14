"""Public documents of chapter 15 (numbers from totals.json and the result files; no J-CAT formula, value
or label). Usage: make_docs.py <chapter_dir>"""
import sys, os, json, pickle, collections, glob, csv, shutil

C = os.path.dirname(os.path.abspath(__file__))
S = os.path.dirname(C)
out = sys.argv[1]
T = json.load(open(os.path.join(C, "totals.json"), encoding="utf-8"))
status = json.load(open(os.path.join(C, "status.json"), encoding="utf-8"))
cls = json.load(open(os.path.join(S, "classify", "final.json"), encoding="utf-8"))
import rc_load
RCS = rc_load.load_all(os.path.join(S, "lo"))
CH = {os.path.basename(p)[6:-4]: pickle.load(open(p, "rb")) for p in glob.glob(os.path.join(C, "chain_*.pkl"))}
VB = {m: pickle.load(open(os.path.join(C, "vb_%s.pkl" % m), "rb")) for m in ("base", "improved") if os.path.exists(os.path.join(C, "vb_%s.pkl" % m))}
approx = json.load(open(os.path.join(C, "approx_check.json")))
lo_base = pickle.load(open(os.path.join(S, "lo", "baseline.pkl"), "rb"))["cmp"]
roots = pickle.load(open(os.path.join(S, "lo", "roots.pkl"), "rb"))


def f(n):
    return "{:,}".format(n)


# ---- random-case totals ------------------------------------------------------------------------------
rc = collections.Counter()
rc_kinds = collections.Counter()
for b, r in RCS.items():
    for pid, d in r["stats"].items():
        for k, v in d["improved"].items():
            rc["improved:" + k] += v
        for k, v in d["base"].items():
            rc["base:" + k] += v
cases_by_book = {b: len(r["cases"]) for b, r in RCS.items()}
inputs_changed = {b: sum(c["inputs_changed"] for c in r["cases"]) for b, r in RCS.items()}
cells_changed = {b: sum(c["cells_changed"] for c in r["cases"]) for b, r in RCS.items()}
vb = {m: collections.Counter() for m in VB}
vb_kind_bad = {m: collections.Counter() for m in VB}
for m, r in VB.items():
    for pid, d in r["results"].items():
        for k in ("n", "ok", "bad", "missing", "variants"):
            vb[m][k] += d[k]
        vb[m]["unsupported"] += d["unsupported"] is not None
        vb_kind_bad[m].update(d["bad_by_kind"])
ch_tot = collections.Counter()
for b, r in CH.items():
    for k, v in r["totals"].items():
        ch_tot[k] += v

n_l1_b, n_l1_i = T["base:l1_n"], T["improved:l1_n"]
n_vb = vb.get("improved", {}).get("n", 0) + vb.get("base", {}).get("n", 0)
n_rc = rc["improved:n"] + rc["base:n"]
n_total = n_l1_b + n_l1_i + n_vb + n_rc + ch_tot["converted:n"]
mismatch_conv_ref = (T["base:l1_n"] - T["base:l1_ok"]) + (T["improved:l1_n"] - T["improved:l1_ok"]) + \
    vb.get("base", {}).get("bad", 0) + vb.get("improved", {}).get("bad", 0) + \
    (rc["improved:n"] - rc["improved:ok_ref"]) + (rc["base:n"] - rc["base:ok_ref"]) + ch_tot["converted:bad"]
mismatch_lo = (rc["improved:n"] - rc["improved:ok_lo"]) + (rc["base:n"] - rc["base:ok_lo"])

# ---- per-category table -----------------------------------------------------------------------------
cat_rows = collections.OrderedDict()
for k, name in (("1", "実際のLCA排出量算定式"), ("2", "数量・係数・時間・条件分岐に関する計算式"), ("3", "集計式"),
                ("4", "単なるセル転記・表示・補助処理"), ("5", "その他")):
    eqs = [e for e in cls if cls[e]["category"] == k]
    cat_rows[k] = dict(name=name, n=len(eqs), essential=sum(cls[e]["essential_rule"] for e in eqs),
                       base_ok=sum(status[e]["base"] == "成功" for e in eqs), imp_ok=sum(status[e]["improved"] == "成功" for e in eqs),
                       imp_approx=sum(status[e]["improved"] == "近似で変換" for e in eqs),
                       imp_dom=sum(status[e]["improved"] == "定義域付きで変換" for e in eqs),
                       base_fail=sum(status[e]["base"] == "失敗" for e in eqs), imp_fail=sum(status[e]["improved"] == "失敗" for e in eqs))
ess = [e for e in cls if cls[e]["essential_rule"]]
ess_base_ok = sum(status[e]["base"] == "成功" for e in ess)
ess_imp_ok = sum(status[e]["improved"] == "成功" for e in ess)
ess_imp_apx = sum(status[e]["improved"] == "近似で変換" for e in ess)
ess_base_fail = sum(status[e]["base"] == "失敗" for e in ess)
ess_imp_fail = sum(status[e]["improved"] == "失敗" for e in ess)
all_base_ok = sum(s["base"] == "成功" for s in status.values())
all_imp_ok = sum(s["improved"] == "成功" for s in status.values())
all_imp_apx = sum(s["improved"] == "近似で変換" for s in status.values())
all_imp_dom = sum(s["improved"] == "定義域付きで変換" for s in status.values())
all_base_dom = sum(s["base"] == "定義域付きで変換" for s in status.values())
ess_imp_dom = sum(status[e]["improved"] == "定義域付きで変換" for e in ess)
ess_base_dom = sum(status[e]["base"] == "定義域付きで変換" for e in ess)
all_base_fail = sum(s["base"] == "失敗" for s in status.values())
all_imp_fail = sum(s["improved"] == "失敗" for s in status.values())

# failures by cause (counts only, generic wording)
fail_kinds = {"base": collections.Counter(), "improved": collections.Counter()}
for e, s in status.items():
    for m in ("base", "improved"):
        if s[m] == "失敗":
            for c in s["detail"][m]["causes"]:
                fail_kinds[m][c.split("：")[0] if "：" in c else c[:40]] += 1
json.dump(dict(totals=T, random=dict(rc), random_cases=cases_by_book, inputs_changed=inputs_changed, cells_changed=cells_changed,
               boundary={m: dict(v) for m, v in vb.items()}, boundary_bad_by_kind={m: dict(v) for m, v in vb_kind_bad.items()},
               chain=dict(ch_tot), chain_books={b: dict(r["totals"], components=r["components"], largest=r["largest"], iters_max=r["iters_max"],
                                                         evaluations=r["evaluations"], nonconv=r["nonconv"]) for b, r in CH.items()},
               conditions_total=n_total, mismatch_conv_vs_ref=mismatch_conv_ref, mismatch_vs_libreoffice=mismatch_lo,
               approximation=approx, libreoffice_baseline={b: v[0] for b, v in lo_base.items()},
               libreoffice_roots=dict(cells=sum(roots["roots"].values()), patterns=len(roots["roots"])),
               failure_causes={m: dict(v) for m, v in fail_kinds.items()}),
          open(os.path.join(out, "04b_検証件数.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
shutil.copy(os.path.join(C, "public_table.csv"), os.path.join(out, "01_分類と変換状態_667件.csv"))

catmd = "\n".join("| %s %s | %d | %d | %d | %d | %d | %d | %d | %d |" % (k, v["name"], v["n"], v["essential"], v["base_ok"], v["base_fail"],
                                                                          v["imp_ok"], v["imp_dom"], v["imp_approx"], v["imp_fail"]) for k, v in cat_rows.items())
rc_books = "、".join("%s %d 件" % (b, n) for b, n in sorted(cases_by_book.items()))
README = f"""# 15 J-CAT 原版 667 数式パターンの 2 構造への変換と検証（2026-11-14）

2026-11-14 の指示書「J-CAT原版667数式パターンの2構造への完全変換・検証」の成果物（公開分）。

## 0. 前提

- 対象は J-CAT 原版 5 ブックの全数式セル 3,818,483 個、正規化パターン 4,241 個、独立方程式（骨格）667 個（14 章で抽出済み、非公開台帳）。今回、全セルの再走査・再抽出はしていない。
- 変換先は既存の研究エンジン（`10_TRANSFORM_STUDY/research_code/tstudy/msp.py`、**変更なし**）の 2 つのステップ（マスク付き積和 `sp`、最初の一致 `match`）と、その上で評価する節点スペクトル（整数格子・10 進格子・2 進格子・走行カウント）。方式は [02_変換方式.md](02_変換方式.md)。
- 原版の式本文・係数・値・セル番地・見出しは**公開しない**。それらを含む成果物（全方程式の LaTeX、理由つきの分類、パターン別の検証の詳細、無作為ケースの入力）は非公開ファイルとして直接渡した。
- この研究は原版の計算規則の表現可能性を調べたもので、J-CAT と同じ結果を出す製品・互換ソフトを主張するものではない（`01_COMPLIANCE`）。

## 1. 結論（指示書 7 の 8 項目）

| 項目 | 結果 |
|---|---|
| 原版 667 パターンの分類完了数 | **667 / 667**（未確認 0）。2 組の読み手が独立に分類し、一致 629 件、食い違い 38 件は判定者が決定 |
| 実質的に独立した LCA 算定規則の数 | **{len(ess)}**（本質的な算定規則。表示・転記・補助だけの {667 - len(ess)} 件は理由つきで算定規則から除外。ただし変換と照合は 667 件すべてで実施） |
| 2 構造への変換成功数 | 基本方式 **{all_base_ok} / 667**（算定規則 {ess_base_ok} / {len(ess)}）＋定義域付き {all_base_dom}。改良方式 **{all_imp_ok} / 667**（算定規則 {ess_imp_ok} / {len(ess)}）＋定義域付き {all_imp_dom}（算定規則 {ess_imp_dom}）＋近似で変換 {all_imp_apx}（算定規則 {ess_imp_apx}） |
| 変換失敗数 | 基本方式 **{all_base_fail}**（算定規則 {ess_base_fail}）。改良方式 **{all_imp_fail}**（算定規則 {ess_imp_fail}）。近似で変換した {all_imp_apx} 件と定義域付きの {all_imp_dom} 件は成功に数えない |
| 検証した入力条件の総数 | **{f(n_total)}**（全セル照合 基本 {f(n_l1_b)}・改良 {f(n_l1_i)}、境界条件 {f(n_vb)}、無作為ケース {f(n_rc)}（{sum(cases_by_book.values())} ケース：{rc_books}）、建物全体の連鎖 {f(ch_tot['converted:n'])}） |
| 数値照合の不一致数 | 変換後の式と元の規則（Excel 保存値・参照評価器）：**{f(mismatch_conv_ref)}**。内訳：値の食い違い {f(mismatch_conv_ref - vb.get('improved', {}).get('missing', 0) - vb.get('base', {}).get('missing', 0))}（基本方式の境界条件 {f(vb.get('base', {}).get('bad', 0) - vb.get('base', {}).get('missing', 0))}：割り算の最下位桁が床・比較で増幅した反例。無作為ケース {f(rc['improved:n'] - rc['improved:ok_ref'] + rc['base:n'] - rc['base:ok_ref'])}：同じ 1 セルを両方式で数えたもので、ROUND の半分の境目で参照評価器のモデルと食い違い、変換後の式は LibreOffice と一致）、範囲外の欠損 {f(vb.get('improved', {}).get('missing', 0) + vb.get('base', {}).get('missing', 0))}（定義域付きの改良 1 件が値を返さなかった入力）。改良方式の値の食い違いは {f(rc['improved:n'] - rc['improved:ok_ref'] + vb.get('improved', {}).get('bad', 0) - vb.get('improved', {}).get('missing', 0))} 件。無作為ケースで LibreOffice と：{f(mismatch_lo)}（すべて同じ入力の参照評価器とは一致。LibreOffice 側の意味論の違い。03 の 4 節） |
| 発見された反例とその原因 | [03_反例と成立条件.md](03_反例と成立条件.md)。テキストを作る演算（連結・置換）、割り算の最下位桁、超越関数、照合規則の文字分解 |
| 主張できる成立範囲 | 3 節と 03 の 5 節 |

### 分類ごとの内訳

| 分類 | 件数 | 算定規則 | 基本方式 成功 | 基本方式 失敗 | 改良方式 成功 | 定義域付き | 近似 | 改良方式 失敗 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
{catmd}

## 2. 検証

[04_検証の方法と結果.md](04_検証の方法と結果.md)。要点：

- **代表条件（全セル）**：原版のモデル建物の値（Excel の保存値）を入力に、変換後の式を全数式セルで実行。変換できたパターンの全セル（基本 {f(n_l1_b)}、改良 {f(n_l1_i)}）で不一致 0。
- **境界条件**：全パターンについて、参照するセルに空欄・0・±1・式中のしきい値とその前後・丸めの半分点・文字列・エラー・論理値・検索表の値などを入れた 40 通りを、Excel 意味論の参照評価器と同じ入力で照合。
- **無作為の現実的な建物**：{sum(cases_by_book.values())} ケース（{rc_books}）。LibreOffice で原版ブックの複製を丸ごと再計算し、変換後の式・参照評価器・LibreOffice の 3 者を同じ値で照合。乱数シード {RCS[next(iter(RCS))]['seed'] if RCS else ''}、抽出方法は 04。
- **建物全体**：全数式セルを空にした状態から、変換した規則だけを依存関係の順に合成して計算（[05_建物全体への接続.md](05_建物全体への接続.md)）。

## 3. 成立範囲（主張できること）

- 改良方式で変換に成功した {all_imp_ok} 件の規則（算定規則 {ess_imp_ok} 件）は、上の全条件で元の規則と一致した。数値は相対差 1e-9 以下（多くは完全一致）、文字列・エラー・型は完全一致。
- 基本方式は、割り算を逆数の積で表すため、商が整数やしきい値のすぐ近くにある入力で結果が変わる反例がある（03）。現実的な値の範囲での照合（代表・無作為）では差は出ていない。
- テキストを作る規則（連結・置換）は変換できていない。検索キーや表示文字列を作るものが大半だが、算定規則として残るものもある（03 の 2 節）。
- 実数べき・常用対数は厳密には表せない。近似の相対誤差は {approx['domain 3e4..5e6 pow 0.05416']['max_rel']:.1e}（原版の式が使う範囲）。
- LibreOffice は Excel と一部の意味論が違う（未整列の表の近似一致検索、空文字列セルの検索結果、#REF! の符号、SINGLE）。これらのセルの基準には参照評価器を使った。

## 4. ファイル

| ファイル | 内容 |
|---|---|
| [01_分類と変換状態_667件.csv](01_分類と変換状態_667件.csv) | 667 件の分類・算定規則か・変換状態（基本・改良）・失敗の種類・照合件数（式本文と理由は非公開版） |
| [02_変換方式.md](02_変換方式.md) | 値の表し方、構文ごとの変換規則、節点スペクトル、改良方式 |
| [03_反例と成立条件.md](03_反例と成立条件.md) | 反例、原因（本質的か方法の不足か）、成立条件 |
| [04_検証の方法と結果.md](04_検証の方法と結果.md)、[04b_検証件数.json](04b_検証件数.json) | 照合の方法・抽出・乱数シード・件数 |
| [05_建物全体への接続.md](05_建物全体への接続.md) | 建物全体の統一方程式への接続（規則の合成による全セルの再計算） |
| `tools/` | 変換器・参照評価器・照合のプログラム（原版のデータは含まない） |

非公開（直接受け渡し）：667 式の分類と理由・原版の式つき対応表、変換前後の全方程式（各式の 1〜6、LaTeX）、パターン別の検証結果と不一致の例、無作為ケースの入力とシード、LibreOffice と Excel の違いの一覧、入力欄の一覧、分類の判断資料。
"""
open(os.path.join(out, "README.md"), "w", encoding="utf-8").write(README)
print("README written; totals:", n_total, mismatch_conv_ref, mismatch_lo)

# ---- 03 counterexamples ---------------------------------------------------------------------------------
def eqs_with(m, word):
    return sorted(e for e, s in status.items() if s[m] != "成功" and any(word in c for c in s["detail"][m]["causes"]))


def cnt_cells(eqs):
    return sum(json.load(open(os.path.join(C, "dossier.json"), encoding="utf-8"))[e]["cells"] for e in eqs)


DOS = json.load(open(os.path.join(C, "dossier.json"), encoding="utf-8"))
groups = [
    ("テキストの連結", "本質的ではない（方法の不足）", "改良方式でも未変換"),
    ("テキストの置換", "本質的ではない（方法の不足）", "改良方式でも未変換"),
    ("テキストの部分取り出し", "本質的ではない（方法の不足）", "改良方式で変換（定義域：整数、数字で始まる文字列）"),
    ("ワイルドカード", "本質的ではない（方法の不足）", "改良方式で変換（「?」のみ。「*」は範囲外として欠損）"),
    ("整数でない指数", "本質的（2 構造では厳密に表せない）", "改良方式は近似（成功に数えない）"),
    ("常用対数", "本質的（2 構造では厳密に表せない）", "改良方式は近似（成功に数えない）"),
]
lines = []
for word, kind, imp in groups:
    eqs = eqs_with("base", word)
    ess_n = sum(cls[e]["essential_rule"] for e in eqs)
    cats = collections.Counter(cls[e]["category"] for e in eqs)
    lines.append("| %s | %d（算定規則 %d） | %s | %s | %s | %s |" % (word, len(eqs), ess_n, f(sum(DOS[e]["cells"] for e in eqs)),
                                                                   "、".join("%s:%d" % kv for kv in sorted(cats.items())), kind, imp))
vb_fail_base = sorted(e for e, s in status.items() if any("境界条件で不一致" in c for c in s["detail"]["base"]["causes"]))
vb_fail_imp = sorted(e for e, s in status.items() if any("境界条件で不一致" in c for c in s["detail"]["improved"]["causes"]))
rc_fail_imp = sorted(e for e, s in status.items() if any("無作為ケースで" in c for c in s["detail"]["improved"]["causes"]))
ess_fail_imp = sorted(e for e in ess if status[e]["improved"] == "失敗")
bk = VB.get("base", {}).get("results", {})
base_bad_kinds = collections.Counter()
for pid, d in bk.items():
    base_bad_kinds.update(d["bad_by_kind"])
imp_bad_kinds = collections.Counter()
for pid, d in VB.get("improved", {}).get("results", {}).items():
    imp_bad_kinds.update(d["bad_by_kind"])
R03 = f"""# 03 反例と成立条件

指示書 5 に従い、変換できない・一致しない例を「2 構造では本質的に表現できない」か「現在の変換方法の不足」かに分けて記録する。
原版の式本文は書かない（独立方程式 ID と仕組みだけ。式本文は非公開の対応表）。

## 1. 変換できない構文（全セル照合の前に変換器が「範囲外」と判断したもの）

| 構文 | 独立方程式（基本方式で失敗） | セル数 | 分類の内訳 | 原因の種類 | 改良方式 |
|---|---|---:|---|---|---|
{chr(10).join(lines)}

- **テキストを作る演算**：今の値の表し方では、テキストは識別符号と照合順位の 2 つの数で表される。2 構造（数の積和と最初の一致）は既存のテキストを写す・比べることはできるが、新しいテキストを作れない。テキストを「長さと各位置の文字符号」の並び（文字の索引集合）として持たせれば、連結は位置をずらした写し、置換は走行カウントによる位置の付け替えとして積和で書ける見込みがある。ただし今回は実装・検証していないので、**変換失敗**として数える。
- **超越関数**：$x^{{m}}$（$m$ が整数でない）と $\\log_{{10}} x$ は、有理関数と格子の和（階段関数）の有限の合成ではどの区間でも厳密に一致しない。区間ごとの多項式で近似はできる（5 節）。

## 2. 算定規則として残る失敗（改良方式でも変換できない本質的な算定規則）

{len(ess_fail_imp)} 件：{"、".join(ess_fail_imp) if ess_fail_imp else "なし"}。

- テキストの連結（{"、".join(e for e in ess_fail_imp if any("テキスト" in c for c in status[e]["detail"]["improved"]["causes"]))}）：検索キーや集計の条件のテキストを組み立てる式。下流の検索・集計は変換できているが、キーを作る段だけが 2 構造の外にある。建物全体の連鎖計算（05）では、これらのセルに Excel の保存値を外部データとして与え、その数を記録した。
- 丸めの境目（{"、".join(e for e in ess_fail_imp if any("無作為" in c for c in status[e]["detail"]["improved"]["causes"]))}）：無作為ケースの 1 セルで、参照評価器のモデルと食い違った（4c）。変換後の式は独立した LibreOffice と一致しており、どちらが Excel と同じかは確かめられないため、反例として失敗に数えた。

## 3. 数値の反例（変換はできたが、ある入力で元の規則と一致しない）

境界条件の照合で見つかったもの：

| 方式 | 不一致のある独立方程式 | 不一致の入力の種類（件数） |
|---|---|---|
| 基本方式 | {len(vb_fail_base)} 件 {"、".join(vb_fail_base[:30])}{" ほか" if len(vb_fail_base) > 30 else ""} | {json.dumps(dict(base_bad_kinds), ensure_ascii=False)} |
| 改良方式 | 値の不一致 {len(vb_fail_imp)} 件 {"、".join(vb_fail_imp[:30])} | なし（このほか、定義域付きの {"、".join(e for e, st_ in status.items() if st_["improved"] == "定義域付きで変換")} が定義域外の入力 {f(vb.get('improved', {}).get('missing', 0))} 件で値を返さず欠損：{json.dumps(dict(imp_bad_kinds), ensure_ascii=False)}） |

原因（基本方式）：**割り算を逆数の積で表している**ため。2 構造の語彙に割り算はなく、$a/b$ を $a\\cdot(1/b)$ で表すと最下位桁が 1 つずれることがある（無作為な 20 万組の 26%）。ずれ自体は相対 $10^{{-16}}$ だが、直後に床（INT・MOD・丸め）、等号・大小の比較、検索のキーが来ると、結果が大きく変わる。例：剰余 MOD$(3, 10^{{-9}})$ は、IEEE の割り算では商が $3\\times10^{{9}}$ ちょうどになり 0 になるが、逆数の積では商が $2999999999.9999995$ になり、剰余が約 $10^{{-9}}$ になる。その結果、MOD$=0$ の条件分岐が逆の枝を選んだ。**これは方法の不足である**：Dekker の誤差なし積と 2 進格子の ulp を使えば、正しく丸めた商を 2 構造の中で作れる（改良方式。02 の 5 節）。

無作為ケース（現実的な値）では、どちらの方式でも参照評価器との不一致は{"なかった" if not rc_fail_imp else "次の件にあった：" + "、".join(rc_fail_imp)}。

## 4. 検証の道具の側で見つかった違い（変換の反例ではない）

- **LibreOffice と Excel の意味論の違い**：原版の入力で再計算すると、SIM で {lo_base.get('SIM', [{}])[0].get('bad', 0)} セル、STD で {lo_base.get('STD', [{}])[0].get('bad', 0)} セル、DET で {lo_base.get('DET', [{}])[0].get('bad', 0)} セル、SUM で {lo_base.get('SUM', [{}])[0].get('bad', 0)} セルが Excel の保存値と違った。根（LibreOffice 自身が、同じ入力に対して規則と違う値を出したセル）は {roots['roots'] and sum(roots['roots'].values())} セル・{len(roots['roots'])} パターンで、次の 5 種類だった：空欄と空文字列の扱い、検索結果が空文字列のセル、#REF! の符号、SINGLE（暗黙の共通部分）が使えない、未整列の見出しに対する近似一致検索の探索手順。STD の差のほとんどは SINGLE の連鎖で、LibreOffice 用の複製だけで同値な式（1 セルの名前の SINGLE を外す）に置き換えた。
- 無作為ケースで変換後の式が LibreOffice と違った {f(mismatch_lo)} 件は、すべて同じ入力の参照評価器とは一致しており、上の根に由来する。
- 参照評価器の不具合 1 件：OFFSET の位置がシートの右端（16,384 列）を越えたとき、セルの番地の整数が次の行に桁あふれして別のセルを読んでいた（Excel は #REF!）。境界条件の照合で見つけて直した。

## 4b. 検証の途中で見つけて直した変換器の不具合（両方式に適用。数えているのは直したあとの結果）

| 不具合 | 見つけた照合 | 内容 | 種類 |
|---|---|---|---|
| 範囲表のキャッシュのキー | 全セル照合（4 セル） | 解放済みのオブジェクトの id が再利用され、同じ式の別の範囲の表を取り違えた | 実装の誤り |
| INDEX のエラー判定の順序 | 全セル照合（75 セル） | MATCH のエラーより先に「0 番目の行」を判定していた | 実装の誤り |
| 範囲外の目印の伝わり方 | 境界条件 | 範囲外の値を欠損にしていたが、後段の述語は欠損を「偽」と読むため、空欄として黙って計算が進んだ。目印を式全体で集め、最終結果を欠損にするよう改めた（選ばれない枝でも欠損にする安全側） | 方法の不足 |
| OFFSET のシート範囲外 | 境界条件 | 計算した位置がシートの外のとき #REF! にせず空欄として扱っていた | 方法の不足 |
| 大きな値の 15 桁丸め | 境界条件 | $\lvert x\rvert 10^{d} \ge 10^{14}$ では 15 桁の格子が 1 より粗いのに、半単位を足して床を取っていた（例：$3.5\times10^{15}$ で 5 ずれ）。15 桁の単位の最も近い倍数にするよう改めた（ちょうど半分は切り上げ。Excel は偶数への丸めの可能性があり未確認） | 方法の不足 |

## 4c. 元の規則のモデルが決まらない例（変換後の式と LibreOffice は一致、参照評価器と不一致）

無作為ケース（SIM、ケース 178）で 1 件。ROUND の中の値が実数では $-0.0005$ ちょうど、浮動小数点では $-0.0004999999999999995$ になる式で、小数 3 桁への丸めのちょうど半分の境目にある。参照評価器（「15 桁に丸めてから四捨五入」のモデル）は $-0.0$、変換後の式は境目の判定の最下位桁の丸めで上に振れて $-0.001$、独立した LibreOffice も $-0.001$。本物の Excel の値はこの環境では確かめられない。**丸めの半分の境目から約 2 ulp 以内では、変換後の式と参照評価器のモデルが食い違いうる**（成立条件 4）。

## 5. 成立条件（変換後の式が元の規則と一致すると主張できる範囲）

1. **値**：IEEE 倍精度の数・文字列・論理値・エラー・空欄。テキストの照合順位は Shift_JIS 順（Excel の日本語環境の順序を、検索セル 514,007 個で確かめたもの）。
2. **数値の一致の基準**：相対差 $10^{{-9}}$ 以下または絶対差 $10^{{-12}}$ 以下。多くは完全一致。
3. **基本方式**：割り算の直後に床・比較・検索が来る規則では、商が整数・しきい値のすぐ近くにある入力（相対 $10^{{-16}}$ 程度）で結果が変わることがある。それ以外は全条件で一致。
4. **改良方式**：割り算は IEEE と同じ（商の大きさ $2^{{-300}}$〜$2^{{301}}$ の範囲）。ROUND 系は「15 桁に丸めてから丸める」Excel の挙動を 10 進格子で写したもので、16 桁目がちょうど 5 になる 16 桁の 2 進数（$10^{{15}}$ 以上の整数など）の同点の扱いは確かめていない。
5. **近似**：実数べき・常用対数の相対誤差は、原版の式が使う範囲で {approx['domain 3e4..5e6 pow 0.05416']['max_rel']:.1e}（べき）、{approx['domain 5e3..3e6 log None']['max_rel']:.1e}（対数）以下。広い範囲 $10^{{-6}}$〜$10^{{12}}$ ではべき {approx['wide 1e-6..1e12 pow 0.05416']['max_rel']:.1e}、対数 {approx['wide 1e-6..1e12 log None']['max_rel']:.1e}（値が 0 に近い $x\\approx1$ 付近の相対誤差）。
6. **範囲外**（値を出さず欠損にする）：データの集計条件に比較演算子やワイルドカードが付く場合、ワイルドカード「*」、INDEX の 0 番目、数字以外で始まる文字列の LEFT。
7. **確かめていないこと**：Excel そのものでの無作為ケースの再計算（LibreOffice と、Excel の保存値で検証した参照評価器で代えた）。原版の入力欄以外（係数表など）を変えた場合。マクロ（DET の .xlsm の VBA）は対象外。
"""
open(os.path.join(out, "03_反例と成立条件.md"), "w", encoding="utf-8").write(R03)

# ---- 04 verification ----------------------------------------------------------------------------------
fr = {b: r["fractions"] for b, r in RCS.items()}
R04 = f"""# 04 検証の方法と結果

## 1. 照合の基準

- **元の規則**：Excel の保存値（原版の入力のとき）と、Excel の意味論を書いた参照評価器（`tools/excel_ref.py`）。参照評価器は、原版の全数式セル 3,818,483 個の保存値をすべて再現することを先に確かめた（不一致 0）。変換器とは別のコード（同じ構文解析だけを共有）。
- **独立した再計算器**：LibreOffice 24.2（無作為ケースの正解。原版ブックの作業用複製を丸ごと再計算。保存はしない）。
- 一致：数値は相対差 1e-9 以下または絶対差 1e-12 以下、文字列・エラー符号・型は完全一致。変換後の式が欠損（範囲外）を返したら不一致と数える。

## 2. 代表条件（全セル）

原版のモデル建物（保存されている入力）で、全 4,241 パターンの全インスタンスを実行。

| 方式 | 実行したセル | 一致 | 不一致 | 変換できなかったパターン（セル） |
|---|---:|---:|---:|---|
| 基本 | {f(T['base:l1_n'])} | {f(T['base:l1_ok'])} | {f(T['base:l1_n'] - T['base:l1_ok'])} | 56（21,790） |
| 改良 | {f(T['improved:l1_n'])} | {f(T['improved:l1_ok'])} | {f(T['improved:l1_n'] - T['improved:l1_ok'])} | 29（21,609） |

## 3. 境界条件

- 抽出：パターンとシートの組ごとに最大 8 インスタンス（シード SHA-256(20261114, パターン, ブック, シート, "sample")）。
- 入力：変換後の式が位置で読むセル（単一セルと 64 セル以下の範囲）を、40 通りの生成規則で置き換える（各通りのシード SHA-256(20261114, パターン, ブック, シート, 番号)）。規則：空欄、0、1、−1、現実的な大きさ（$10^{{-3}}$〜$10^{{6}}$、小数 0〜4 桁）×6、整数 0〜120 ×4、式中のしきい値 $c$ と $c\\pm1, c\\pm0.5, c(1\\pm10^{{-9}})$ ×6、丸めの半分点（$k+0.5$、$\\pm10^{{-13}}$、$\\pm10^{{-10}}$、小数 3 桁）×3、文字列 ×2、エラー、論理値、検索表にある値 ×6、混合 ×7。
- 期待値：同じ入力での参照評価器。

| 方式 | 照合件数 | 一致 | 不一致 | 欠損 |
|---|---:|---:|---:|---:|
| 基本（手順が改良と同じパターンは改良の結果を流用） | {f(vb.get('base', {}).get('n', 0))}（実行分） | {f(vb.get('base', {}).get('ok', 0))} | {f(vb.get('base', {}).get('bad', 0))} | {f(vb.get('base', {}).get('missing', 0))} |
| 改良 | {f(vb.get('improved', {}).get('n', 0))} | {f(vb.get('improved', {}).get('ok', 0))} | {f(vb.get('improved', {}).get('bad', 0))} | {f(vb.get('improved', {}).get('missing', 0))} |

不一致・欠損の入力の種類：基本 {json.dumps(dict(vb_kind_bad.get('base', {})), ensure_ascii=False)}、改良 {json.dumps(dict(vb_kind_bad.get('improved', {})), ensure_ascii=False)}。欠損は 02 の 6 節の範囲外の入力（データの条件に演算子が付いた文字列など）。

## 4. 無作為の現実的な建物

- ケース数：{sum(cases_by_book.values())}（{rc_books}）。各ケースのシード SHA-256(20261114, ブック, ケース番号)。
- 入力の作り方（原版のモデル建物の入力を基準に）：選択式は入力規則の選択肢から（確率 0.85）、数値は元の値の 0.25〜4 倍（対数一様。整数は整数）、竣工年 1995〜2035、評価期間 30〜100 年の典型値、率 0〜1、数量欄の空欄は同じ列の値の大きさから確率 0.15 で記入、テキストは元のまま。SUM は入力欄がすべて空欄なので確率 0.3 で 0.1〜1000。SIM と STD は LibreOffice への書き込みが遅い（1 セル約 0.17 秒）ため、各入力欄を確率 0.05 で変える（ほかは元の値）。
- 配分の変更：当初 SIM・STD 各 500 件を予定したが、書き込みの遅さのため SIM・STD 各 200 件とし、DET・SUM を増やして計 2,000 件にした。
- 照合する規則：各ケースで、変わったセルを読む（または自身が変わった）パターン単位のうち、シード付きの割合 {json.dumps(fr, ensure_ascii=False)}（(最初のケース, 最後のケース, 割合)）を照合。各単位は固定の 8 インスタンス。
- 期待値：LibreOffice の値。参照評価器（同じケースの値で）も計算し、3 者を比べる。

| | 照合件数 | 参照評価器と一致 | LibreOffice と一致 | 参照評価器と LibreOffice が一致 |
|---|---:|---:|---:|---:|
| 改良方式 | {f(rc['improved:n'])} | {f(rc['improved:ok_ref'])} | {f(rc['improved:ok_lo'])} | {f(rc['improved:ref_eq_lo'])} |
| 基本方式（手順が違う単位のみ） | {f(rc['base:n'])} | {f(rc['base:ok_ref'])} | {f(rc['base:ok_lo'])} | {f(rc['base:ref_eq_lo'])} |

変わった入力の延べ数：{json.dumps(inputs_changed, ensure_ascii=False)}。値が変わった数式セルの延べ数：{json.dumps(cells_changed, ensure_ascii=False)}。

LibreOffice と合わない件は、すべて参照評価器とは一致した（03 の 4 節の LibreOffice 側の違い）。

## 5. 再現

`tools/` のプログラムと非公開の台帳（原版の走査結果）で再現できる。乱数はすべて上のシードから決まる。
"""
open(os.path.join(out, "04_検証の方法と結果.md"), "w", encoding="utf-8").write(R04)

# ---- 05 building-level connection -----------------------------------------------------------------------
chain_rows = "\n".join("| %s | %s | %s | %s | %s | %d | %d | %d |" % (
    b, f(r["totals"].get("converted:n", 0)), f(r["totals"].get("converted:ok", 0)), f(r["totals"].get("converted:bad", 0)),
    f(r["totals"].get("external:n", 0)), r["components"], r["largest"], r["iters_max"]) for b, r in sorted(CH.items()))
R05 = f"""# 05 建物全体の統一方程式への接続

## 1. 方法

1. ブックの全数式セルを空欄にする（Excel の保存値は使わない）。入力と定数はブックのもの。
2. 単位 = （パターン, シート）のすべてのインスタンス。単位 U が単位 V の計算したセルを読むとき U は V に依存する。
3. 依存の強連結成分を、依存される側から順に評価する。成分の中は、値が変わらなくなるまで繰り返す（不動点）。
4. 変換できない単位（テキストの連結・置換）のセルだけは Excel の保存値を外部データとして与え、件数を記録する。
5. 最後に、全数式セルを Excel の保存値と比べる。

各単位は改良方式の変換後の式（マスク付き積和と節点スペクトル）だけで計算する。これは、建物全体の計算 $\\mathbf{{y}} = \\Phi(\\mathbf{{x}})$ を、変換した規則 $\\phi_u$ の合成 $\\Phi = \\phi_{{u_K}} \\circ \\cdots \\circ \\phi_{{u_1}}$（成分の中は不動点 $\\mathbf{{y}}_C = \\phi_C(\\mathbf{{y}}_C, \\mathbf{{y}}_{{<C}}, \\mathbf{{x}})$）として書いたものの数値的な確認である。

## 2. 結果

| ブック | 変換した規則で計算したセル | Excel と一致 | 不一致 | 外部データ（未変換の規則） | 強連結成分 | 最大の成分（単位） | 最大の反復回数 |
|---|---:|---:|---:|---:|---:|---:|---:|
{chain_rows}

- 詳細算定（DET）と集計表（SUM）では、入力と定数だけから、変換した規則の合成で全数式セルを再現した。
- 簡易算定（SIM）と標準算定（STD）は、単位数（4,366 と約 6,800）と反復の量が大きく、今回のセッションでは連鎖計算を行っていない。これらのブックの規則は、全セル照合（代表条件）・境界条件・無作為ケースで 1 つずつ確かめた。全体の合成を数値で確かめたのは DET と SUM だけである。
"""
open(os.path.join(out, "05_建物全体への接続.md"), "w", encoding="utf-8").write(R05)
print("03 04 05 written")
