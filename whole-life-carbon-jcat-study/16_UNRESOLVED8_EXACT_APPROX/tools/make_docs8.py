"""Writes 04_検証の方法と結果.md and 05_採用方式と適用範囲.md of chapter 16 from the result files
(public counts only: no formula, coefficient or cell value of the original workbooks).
Usage: make_docs8.py <chapter dir> <counts.json> <synthetic.json> <bounds.json> <round_probe_lo.json>"""
import os, sys, json

ch, cj, sj, bj, rj = sys.argv[1:6]
C = json.load(open(cj, encoding="utf-8"))
SY = json.load(open(sj, encoding="utf-8"))
BO = json.load(open(bj, encoding="utf-8"))
RP = json.load(open(rj, encoding="utf-8"))["summary"]
ORDER = ["EQ-0023", "EQ-0144", "EQ-0469", "EQ-0298", "EQ-0450", "EQ-0451", "EQ-0452", "EQ-0229"]


def frac(a, b):
    return "%s / %s" % (format(a or 0, ","), format(b or 0, ","))


def l1s(r):
    l = r["L1"]
    return frac(l.get("ok_cached"), l.get("n"))


def vbs(r):
    v = r["boundary"]
    s = frac(v.get("ok"), v.get("n"))
    extra = []
    if v.get("missing"):
        extra.append("欠損 %s" % format(v["missing"], ","))
    if v.get("wrong"):
        extra.append("**誤り %s**" % format(v["wrong"], ","))
    return s + ("（%s）" % "、".join(extra) if extra else "")


def rcs(r):
    c = r["random_cases"]
    if not c.get("n"):
        return "対象ケースなし（%s ケース中、入力が届くケース 0）" % format(c.get("cases", 0), ",")
    s = "LibreOffice %s、参照評価器 %s" % (frac(c.get("ok_lo"), c.get("n")), frac(c.get("ok_ref"), c.get("n")))
    if c.get("missing"):
        s += "、欠損 %s" % format(c["missing"], ",")
    return s


def perf(r):
    p = r["performance"]
    return "%s ステップ、最大 %s 行、表 %.1f MB・計算列 %.1f MB、全セル 1 回 %.0f ms" % (
        format(int(p.get("steps_max", 0)), ","), format(int(p.get("rows_max", 0)), ","), p.get("table_bytes_max", 0) / 1e6,
        p.get("engine_bytes_max", 0) / 1e6, p.get("run_ms_L1", 0))


def down(eq):
    d = C[eq]
    cl = d["consumers"].get("closure")
    dv = d.get("downstream_variants")
    if dv:
        parts = []
        for m, lab in (("A", "方式 A"), ("B", "方式 B"), ("ulp+", "+1 ulp"), ("ulp-", "−1 ulp")):
            c = dv["counts"].get(m, {})
            extra = ""
            if "targets_differing_from_correctly_rounded_ref" in c:
                extra = "（正しく丸めた参照とは %s）" % format(c["targets_differing_from_correctly_rounded_ref"], ",")
            parts.append("%s：式の値が参照と異なる %s%s、消費セルの変化 比例的 %s・不連続 %s" % (
                lab, format(c.get("targets_differing", 0), ","), extra, format(c.get("proportional", 0), ","), format(c.get("discontinuous", 0), ",")))
        return "消費セル（推移閉包）%s；入力の変種 %d で評価 %s 回：%s" % (
            format(cl, ",") if cl is not None else "—", dv["variants"], format(dv["counts"].get("A", {}).get("consumer_evals", 0), ","), "；".join(parts))
    sens = d.get("sensitivity_ulp") or {}
    s = "消費セル（推移閉包）%s" % (format(cl, ",") if cl is not None else "未計算")
    ch = []
    for m in ("A", "B"):
        dd = d[m]["downstream"]
        if dd.get("substituted") is not None:
            ch.append("方式%s：差し替え %s セル → 変化 %s" % (m, format(dd["substituted"], ","), (dd.get("changed") or {}).get("changed", 0)))
    for m in ("ulp+", "ulp-"):
        v = sens.get(m)
        if v is not None:
            ch.append("±1ulp（%s）：比例的でない変化 %s" % (m[-1], v.get("changed", 0)))
    return s + ("；" + "；".join(ch) if ch else "")


with open(os.path.join(ch, "04_検証の方法と結果.md"), "w", encoding="utf-8") as fh:
    fh.write("# 検証の方法と結果\n\n")
    fh.write("すべての比較は**倍精度数としての完全一致**で数える（+0 と −0 は等しいとする。テキスト・論理値・エラーは完全一致）。"
             "15 章の照合で使った相対 10^{−9} の許容は、方式 A の厳密性の判定には使っていない。\n\n")
    fh.write("## 1. 合成データ（原版に依存しない）\n\n")
    fh.write("原版の係数・文字列を使わず、一般の定数で作った敵対的な入力（境界、同点、桁の繰り上がり、非正規化数、最大値、"
             "Unicode の特殊な文字、ワイルドカードと退避、演算子の接頭辞など）で、参照評価器と比べた。詳細は 07_合成データの検証.json。\n\n")
    fh.write("| 対象 | 方式 | 件数 | 一致 | 誤り | 欠損（宣言した範囲外） | ステップ数 |\n|---|---|---:|---:|---:|---:|---:|\n")
    agg = {}
    for k, v in SY.items():
        parts = k.split("|")
        fam, mode = parts[0], parts[-1]
        if fam == "powlog":
            continue
        if fam == "sumif":
            fam = "sumif:" + parts[2]
        key = (fam, mode)
        a = agg.setdefault(key, dict(n=0, ok=0, wrong=0, missing=0, missing_outside=0, steps=0))
        for kk in ("n", "ok", "wrong", "missing", "missing_outside"):
            a[kk] += v.get(kk, 0)
        a["steps"] = max(a["steps"], v.get("steps", 0))
    names = {"concat": "文字列連結", "round": "ROUND・ROUNDDOWN・ROUNDUP", "value": "VALUE(LEFT())",
             "sumif:no_order_bad": "条件が連結の SUMIF・COUNTIF", "sumif:with_order_bad": "同上（Σ・İ・U+F8F3 を多く含む入力）"}
    for (fam, mode), a in sorted(agg.items()):
        fh.write("| %s | %s | %s | %s | %s | %s | %s |\n" % (names.get(fam, fam), mode, format(a["n"], ","), format(a["ok"], ","),
                                                         format(a["wrong"], ","), format(a["missing"] + a["missing_outside"], ","), format(a["steps"], ",")))
    fh.write("\n非整数乗・常用対数（真値は 60 桁の 10 進演算。結果が正規化数の入力で比べ、溢れと非正規化数の結果は別に数えた）：\n\n| 関数 | 方式 | 件数（正規化数の結果） | 真値の正しい丸めと一致 | 誤り | 最大相対誤差 | 判定不能（欠損） | C ライブラリと一致 | C ライブラリ自身が正しい丸め | 溢れ → #NUM! | 非正規化数の結果（欠損と宣言） |\n|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
    for k, v in SY.items():
        parts = k.split("|")
        if parts[0] != "powlog":
            continue
        name = "x^%s" % parts[2] if parts[1] == "pow" else "log10 x"
        fh.write("| %s | %s | %s | %s | %s | %.2e | %s | %s | %s | %s / %s | %s |\n" % (
            name, parts[-1], format(v["n_pos"], ","), format(v["eq_truth"], ","), format(v.get("wrong", 0), ","), v["max_rel"],
            format(v["flagged"], ","), format(v["eq_libm"], ","), format(v["libm_correct"], ","),
            format(v.get("overflow_num", 0), ","), format(v.get("overflow", 0), ","), format(v.get("subnormal", 0), ",")))
    fh.write("\n区分多項式の近似誤差（48 区間、60 桁で区間あたり 97 点を評価、べきは補間剰余の解析的上限も）：\n\n| 関数 | 方式 A（次数 13）| 方式 B（次数 10、倍精度の係数）|\n|---|---|---|\n")
    for k, v in BO.items():
        a, b = v["A"], v["B"]
        fh.write("| %s | 2^%.1f（解析的上限 %s） | 2^%.1f |\n" % (k, a["log2"], ("2^%.1f" % a["analytic_log2"]) if "analytic_log2" in a else "—", b["log2"]))
    fh.write("\n## 2. ROUND の挙動の判別（一般の入力）\n\n")
    fh.write("参照モデル（15 桁の 10 進表記を四捨五入。方式 A が厳密に再現）、2 進値そのものの四捨五入、方式 B（15 桁目の半単位を足す）"
             "の 3 つが**互いに異なる入力**を作り、LibreOffice で計算した（`tools/round_probe.py`、`tools/round_probe_lo.py`）。"
             "LibreOffice が入力の 17 桁の数字を別の倍精度数として読んだ %d 行を除く %d 行で、LibreOffice の結果は参照モデルと %d 行、"
             "2 進値の丸めと %d 行、方式 B と %d 行で一致した。方式 A と B が異なる %d 行では、LibreOffice は A と %d 行、B と %d 行で一致した。"
             "すなわち、丸めの境界付近の結果は表計算ソフトの実装ごとに異なり、どのモデルも LibreOffice と一致しない。"
             "原版ソフトについては、同じ入力表（`round_probe.xlsx`。非公開資料に同梱）を原版ソフトで開いて D 列を読めば判別できる。\n\n" % (
                 RP["read_differently"], RP["n"], RP["LO_eq_M15"], RP["LO_eq_BIN"], RP["LO_eq_HU"], RP["A_ne_B"], RP["A_ne_B__LO_eq_A"], RP["A_ne_B__LO_eq_B"]))
    fh.write("## 3. 実パターン（原版のセル。件数のみ）\n\n")
    fh.write("- **全セル**：各式のすべての実例セルで、変換した値と原版のキャッシュ値（完全一致）。\n"
             "- **境界条件**：15 章と同じ生成器（空白・0・±1・実在の大きさ・整数・式の閾値 ± 微小量・丸めの中点・テキスト・エラー・論理値・"
             "検索表の値・混合の 40 変種）で、実例（各シート最大 8）の参照セルを置き換え、同じ入力の参照評価器と比べた。手順は 1 回だけ変換し、値の列だけを入れ替えた。\n"
             "- **無作為ケース**：15 章と同じ種で再生成した現実的な建物条件のケース（LibreOffice で全再計算）で、LibreOffice の値と参照評価器の値の両方と比べた。\n\n")
    fh.write("| 式 | 種類 | 方式 | 全セル | 境界条件 | 無作為ケース | 計算量・メモリ |\n|---|---|---|---|---|---|---|\n")
    for eq in ORDER:
        for m in ("A", "B"):
            r = C[eq][m]
            fh.write("| %s | %s | %s | %s | %s | %s | %s |\n" % (eq, C[eq]["kind"], m, l1s(r), vbs(r), rcs(r), perf(r)))
    fh.write("\n## 4. 下流の計算への影響\n\n")
    fh.write("式のセルを読むすべての式セル（静的な参照の範囲に含まれるもの）を段ごとにたどった（推移閉包）。原版の雛形では建物の量の入力が空で、"
             "数値の式の値はほとんど 0 なので、境界条件と同じ生成器で参照セルを 40 通りに変え、式のセルに (i) 参照評価器の値、(ii) 方式 A、"
             "(iii) 方式 B、(iv) 参照の値 ±1 ulp を入れて、消費セルを参照評価器で再計算し、(i) との差を数えた。"
             "差は、8 ulp 以内の比例的な変化と、それを超える不連続な変化（丸め・閾値・検索・エラーの発生が変わる）に分けた。"
             "テキストの式（EQ-0023・EQ-0144）は数値の摂動がなく、方式 A は全セルで値が同じなので下流は変わらない（方式 B の欠損は消費セルにそのまま伝わる）。\n\n")
    for eq in ORDER:
        fh.write("- %s（%s）：%s\n" % (eq, C[eq]["kind"], down(eq)))
print("written")
