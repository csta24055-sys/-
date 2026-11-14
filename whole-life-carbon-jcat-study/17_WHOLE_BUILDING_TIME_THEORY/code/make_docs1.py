"""Stage 1: write 07_検証の結果.md from results/stage1_summary.json and 06_70単位の時間特性.md from
results/units_time.json (both generated; numbers are never typed by hand).

Usage (from this folder): python3 -B make_docs1.py
"""
import collections
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
CH = os.path.normpath(os.path.join(HERE, ".."))
RES = os.path.join(CH, "results")


def e(x, f="%.1e"):
    return "—" if x is None else (f % x)


def doc07(s):
    cv = s.get("canonical_verification", {})
    L = []
    L.append("# 07 検証の結果（第 1 段階）\n")
    L.append("`code/aggregate1.py` が `results/` の JSON から作った `results/stage1_summary.json` を、`code/make_docs1.py` がこの文書に書き出した。"
             "表と本文の数値は JSON から読んでいる。対象は独立概念モデルと架空データ。独立レビュー（5 つの観点）の指摘を受けて、検査の分類（実装の確認か、"
             "核の和そのものの照合か）と件数（実行した比較の数）を書き直し、補足の検査（`code/timechar_terms.py`）を加えた。\n")
    L.append("## 1. 理想方程式と 70 単位モデル（基準計算）との一致\n")
    L.append("比較の規則は第 11 章と同じ：数値は相対 1e-9、基準計算が厳密に 0 なら 0 であること（浮動小数どうしの一致であり、厳密な等号ではない）。`code/verify_canon.py`。\n")
    L.append("| 項目 | 件数 | 不一致 | 最大相対差 |")
    L.append("|---|---|---|---|")
    L.append("| 組（シナリオ×評価期間） | %s（定義域の外で除外 %s、基準計算の例外 %s、失敗 %s） | — | — |"
             % (cv.get("n_pairs"), cv.get("n_excluded"), cv.get("n_ref_raised", 0), cv.get("n_failed")))
    L.append("| ホールライフ合計 SUM-03（正準形 vs 基準計算） | %s | %s | %s |" % (cv.get("n_pairs"), cv.get("total_vs_ref_bad"), e(cv.get("max_rel_total_vs_ref"))))
    L.append("| 同（正準形 vs 統一系、相対 1e-12） | %s | %s | — |" % (cv.get("n_pairs"), cv.get("total_vs_sys_bad")))
    L.append("| 節点形 ＝ 核の和（照合の評価期間で、有理数として） | %s | %s | — |" % (cv.get("knot_vs_terms_exact_checked"), cv.get("knot_vs_terms_exact_bad")))
    L.append("| 評価範囲に入る段階の値（基準計算の by_stage に出る段階） | %s | %s | %s |" % (cv.get("n_stage"), cv.get("stage_vs_ref_bad"), e(cv.get("max_rel_stage_vs_ref"))))
    L.append("| 合計に入る 21 単位の値（構成表は 22 行。B2-01 は B2 と B6 に現れる） | %s | %s | %s |" % (cv.get("n_unit"), cv.get("unit_vs_ref_bad"), e(cv.get("max_rel_unit_vs_ref"))))
    L.append("| 参考：B1-04 の跳び形（正準形には使わない） | %s | %s | — |" % (cv.get("n_jumpform"), cv.get("jumpform_vs_ref_bad")))
    L.append("")
    L.append("集合ごと：\n")
    L.append("| 集合 | 組 | 除外 | SUM-03 不一致 | 段階 | 段階 不一致 | 単位 | 単位 不一致 | 跳び形の不一致 |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for k, v in cv.get("by_set", {}).items():
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (k, v["n_pairs"], v["n_excluded"], v["total_vs_ref_bad"], v["n_stage"], v["stage_vs_ref_bad"],
                                                               v["n_unit"], v["unit_vs_ref_bad"], v.get("jumpform_vs_ref_bad")))
    L.append("")
    dc = s.get("density_check", {})
    ex = (dc.get("examples") or [{}])[0]
    L.append("**1.2 密度の振幅を率で持つ理由**（`code/density_check.py`、`results/density_check.json`）。dev_edge の %s 組のうち、基準計算の B3 の値が厳密に 0 の組は %s。"
             "第 11 章と同じく密度の振幅を浮動小数の積 $\\mathrm{fl}(aH)$ で持って厳密に評価すると、そのうち %s 組で 0 にならない（例：`%s`、T = %s で %s）。率 $a$ で持つと %s 組。\n"
             % (dc.get("n"), dc.get("n_reference_zero"), dc.get("product_form_nonzero_where_reference_zero"), ex.get("label"), ex.get("T"),
                e(ex.get("product_form")), dc.get("rate_form_nonzero_where_reference_zero")))
    jf = []
    for k, v in cv.get("by_set", {}).items():
        jf += [x for x in s.get("jumpform_examples", {}).get(k, [])]
    L.append("**1.3 B1-04 の跳び形。** 跳び形を厳密に評価すると、強く減衰する冷媒で基準計算と %s 件の不一致（`results/verify_canon_all.json` の examples）。"
             "係数そのものが浮動小数で丸められているので、厳密な評価でも桁落ちは消えない（第 11 章 D-09 の現象を再現）。区間形では 0 件。\n" % cv.get("jumpform_vs_ref_bad"))
    L.append("## 2. 時間特性の定理の厳密な照合（有理数）\n")
    c = s["counts"]
    sup = s.get("supplement", {})
    sc = sup.get("counts", {})
    L.append("### 2.1 核の和そのものに対する照合（補足、`code/timechar_terms.py`）\n")
    L.append("同じ正準形を持つシナリオは 1 回だけ調べた：%s 項目のうち相異なる関数 %s、重複 %s。件数はすべて**実行した比較の数**。\n"
             % (sup.get("n_entries"), sup.get("n_distinct_functions"), sup.get("n_duplicates")))
    L.append("| 照合 | 比較の数 | 不一致 |")
    L.append("|---|---|---|")
    for lab, k1, k2 in (("S1 TH-1/TH-3：核の和が区間で一次式（3 点）で、係数が節点の累積和に等しい（各関数で無作為の最大 100 区間）", "s1_checked", "s1_bad"),
                        ("S2 TH-2：核の和の跳びと傾きの変化 ＝ $p+q\\,\\mathrm{sw}$、$q$（無作為の隣り合う区間、最大 40 組）", "s2_checked", "s2_bad"),
                        ("S3 区切り点そのものとその隣の浮動小数で、核の和 ＝ 節点形（最大 60 点×3）", "s3_checked", "s3_bad"),
                        ("S4 整数時刻の事象：B1-04 以外の項の跳びが格子の節点で 0", "s4_checked", "s4_other_jump_bad"),
                        ("S4 整数時刻の事象：区間形の跳び（$K$）＝ 跳び形の跳び（$\\mathrm{sw}(K)$）（残存量の相対 1e-12）", "s4_b14_compared", "s4_b14_bad"),
                        ("S5 段階ごとの節点形 ＝ 段階の核の和（10 期間）", "s5_stage_checked", "s5_stage_bad"),
                        ("S5 単位ごとの節点形 ＝ 単位の核の和（10 期間）", "s5_unit_checked", "s5_unit_bad"),
                        ("S6 TH-4：$M([0,T]) + Z(T)$ ＝ 核の和（S1 の中点）", "s6_checked", "s6_bad")):
        L.append("| %s | %s | %s |" % (lab, sc.get(k1, 0), sc.get(k2, 0)))
    L.append("")
    L.append("- S4 で比べた整数時刻の事象のうち、冷媒の初期化があったもの %s。区間形と跳び形の跳びの差の最大は残存量の相対 %s。" % (sc.get("s4_b14_resets", 0), e(sup.get("s4_max_rel"))))
    L.append("- 区間の内側に浮動小数がない（幅が数 ulp の）区間は S1・S2 から外した（S1 で %s、S2 で %s 件）。" % (sc.get("s1_skipped_no_interior_floats", 0), sc.get("s2_skipped_no_interior_floats", 0)))
    L.append("")
    L.append("### 2.2 節点形の上での検査（timechar.py）\n")
    L.append("シナリオ %s 件（全 10 集合。同じ関数の重複を含む）。TH-1〜TH-3 の「節点形の区間・係数・跳び」は、節点形が作り方から区分一次なので**実装の確認**であり、"
             "核の和の性質の照合ではない（それは 2.1）。TH-0 の中点の照合、TH-2 の事象の前後の照合、TH-4〜TH-6 は、節点形とは別に作った量（核の和、実時間の測度、積分）と比べている。\n"
             % s["n_analysed"])
    L.append("| 照合 | 標本 | 不一致 | 種類 |")
    L.append("|---|---|---|---|")
    exf = s["exact_failures"]
    rows = [("TH-0 核の和 ＝ 節点形（各シナリオ最大 60 区間の中点）", c["th0_points"], exf.get("th0_bad"), "独立な照合"),
            ("TH-2 事象の前後の跳び（核の和で。各シナリオ最大 12 事象）", c["th2_events_with_terms"], exf.get("th2_terms_bad"), "独立な照合"),
            ("TH-2 切り替えの直前の値が左の区間に乗る（核の和）", c["th2_events_with_terms"], exf.get("th2_left_continuity_bad"), "独立な照合"),
            ("TH-4 $C = M([0,T]) + Z(T)$（節点形と、項から作った測度）", "全区間（内側に浮動小数がある区間）", exf.get("th4_decomp_bad"), "独立な照合"),
            ("TH-4 $C' = \\rho + Z'$", "同上", exf.get("th4_rate_bad"), "独立な照合"),
            ("TH-4 測度の累積和 ＝ 項ごとの和", "各シナリオ 40 区間", exf.get("th4_direct_sum_bad"), "独立な照合"),
            ("TH-5 年増分の分解", "全年", exf.get("th5_increment_bad"), "独立な照合"),
            ("TH-6 積分の閉じた形 ＝ 区間ごとの積分", c["th6_points"], exf.get("th6_integral_bad"), "代数の確認"),
            ("TH-1 節点形の区間が一次式、係数が累積和", "全区間", exf.get("th1_affine_bad"), "実装の確認"),
            ("TH-2・TH-3 節点形の跳び・傾きの変化", "全隣接区間", exf.get("th2_jump_bad"), "実装の確認"),
            ("TH-2 格子の丸めの跳びが係数の相対 1e-12 以下", c["lattice_rounding_jumps"], exf.get("lattice_jumps_above_1em12"), "測定")]
    for a, b, d_, kd in rows:
        L.append("| %s | %s | %s | %s |" % (a, b, d_, kd))
    L.append("")
    sz = s.get("size", {})
    L.append("- 大きさ：核の項はシナリオの中央値 %s（最大 %s）、節点（格子＋事象）は中央値 %s（最大 %s）、項／節点の比の中央値 %.1f。年次表の長さ $H$：%s。"
             % (sz.get("terms_median"), sz.get("terms_max"), sz.get("knots_median"), sz.get("knots_max"), sz.get("ratio_terms_per_knot_median") or 0, sz.get("H_values")))
    L.append("- 節点の数：区間 %s、事象の節点 %s、格子の節点 %s、跳び %s（うち整数時刻の事象による区間形の初期化 %s、格子の丸めの跳び %s、その最大は係数の大きさの相対 %s）。"
             % (c["pieces"], c["event_knots"], c["lattice_knots"], c["jumps"], c["integer_event_reset_jumps"], c["lattice_rounding_jumps"], e(s["max_rel_lattice_rounding_jump"])))
    L.append("- 補題 L-2：浮動小数の切り替え点 $\\mathrm{sw}(g)$ と $g/\\mathrm{fl}(1-\\varepsilon)$ の差は最大 %.2f ulp。" % s["switch_offset_ulp_max"])
    ts = s["terminal_slope"]
    L.append("- TH-4(a)：終わりの項の傾き $Z'\\ne0$ を持つシナリオ %s / %s。区間のうち $Z'\\ne0$ の割合の中央値 %.2f。$|Z'|/|C'|$ の最大 %s、95 パーセンタイル %s。"
             % (ts["scenarios_with_any"], s["n_analysed"], ts["median_fraction_of_pieces"] or 0, e(ts["max_rel_to_total_slope"]), e(ts["p95_rel_to_total_slope"])))
    L.append("- TH-4(b)：$C(0^+)$ が節点形の $A_0$ と異なる関数 %s / %s（区間形の窓が格子の節点 0 に置かれるため）。" % (sup.get("C0plus_differs_from_A0"), sup.get("n_distinct_functions")))
    neg = s["negative_parts"]
    L.append("- TH-4(d) 符号：負の原子を持つ単位 %s、負の密度を持つ単位 %s（項の数、カッコ内はシナリオ数）。段階でまとめた負の密度の区間 %s、段階でまとめた負の原子 %s。"
             % (fmt_counts(neg, "neg_mass_units"), fmt_counts(neg, "neg_density_units"), fmt_counts(neg, "neg_stage_density_intervals"), fmt_counts(neg, "neg_stage_masses")))
    L.append("")
    L.append("役割ごとの値の割合（中央値、$C(T)$ に対する比）：\n")
    roles = ["A_init", "B", "Gamma", "Delta", "R", "A_term"]
    L.append("| T | " + " | ".join(roles) + " |")
    L.append("|---|" + "---|" * len(roles))
    for T in sorted(s["role_share_median"], key=float):
        d = s["role_share_median"][T]
        L.append("| %s | " % T + " | ".join("%.3f" % d.get(r, 0.0) for r in roles) + " |")
    L.append("")
    L.append("## 3. ラプラス変換・フーリエ級数（浮動小数）\n")
    L.append("- ラプラス変換：閉じた形と区分ごとのガウス・ルジャンドル積分の相対差の最大 %s（$s$ = 0.01、0.1、1、0.05+0.3i）。" % e(s["laplace_max_rel"]))
    L.append("- フーリエ係数：閉じた形と数値積分の相対差の最大 %s（$n$ = 0、1、5、37）、%s（$n$ = −1、−5、−37。補足）。共役対称は実数の係数から浮動小数で計算すれば自動的に成り立つので、証拠に数えない。"
             "係数の減衰の傾き（両対数）中央値 %.3f（範囲 %.3f〜%.3f。傾き 0 は $C$ が $T$ によらず $c_n=0$（$n\\ne0$）のシナリオ）。"
             % (e(s["fourier_closed_vs_pieces_max_rel"]), e(sup.get("fourier_negative_n_max_rel")), s["fourier_decay_slope"]["median"],
                s["fourier_decay_slope"]["min"], s["fourier_decay_slope"]["max"]))
    L.append("- 周期の境界：部分和（512 項）の $T=0$ の値と $(C(0^+)+C(H))/2$ の差は、$C(H)$ に対する相対で中央値 %s、最大 %s（補足：$C(0^+)$ を節点形の $0$ の直後の値で計算）。"
             % (e(sup.get("boundary_rel_to_midpoint_median")), e(sup.get("boundary_rel_to_midpoint_max"))))
    L.append("")
    L.append("部分和の誤差（$\\max|C|$ に対する相対。全シナリオの中央値と最大）：\n")
    L.append("| 項数 $N$（$|n|\\le N$） | 最大誤差 中央値 | 最大誤差 最大 | 区切りから 0.05 年以上離れた点の最大誤差 中央値 | 誤差の中央値（中央値） |")
    L.append("|---|---|---|---|---|")
    for M, d in s["fourier_partial_sums"].items():
        L.append("| %s | %s | %s | %s | %s |" % (M, e(d["max_rel_all_median"], "%.3g"), e(d["max_rel_all_max"], "%.3g"), e(d["max_rel_far_median"], "%.3g"), e(d["median_rel_median"], "%.2e")))
    L.append("")
    L.append("## 4. 線形漸化式（厳密な次数）と特性根\n")
    L.append("年増分 $d_y$（$y=2..H$）の最小の線形漸化式の次数（バーレカンプ・マッシー法、有理数）。固有値は特性多項式の根。ハンケル行列の DMD は、合計の次数が 40 以下で一意に決まるシナリオが無かったので実行していない。\n")
    L.append("- 合計：%s" % ", ".join("%s：%s 件" % (k, v) for k, v in s["recurrence_total"].items()))
    for role, d in sorted(s["recurrence_by_role_maximality"].items()):
        L.append("- 役割 %s：%s" % (role, ", ".join("%s：%s 件" % (k, v) for k, v in sorted(d.items()))))
    L.append("")
    L.append("役割ごとの次数の分布（次数：シナリオ数）：\n")
    for role, d in sorted(s["recurrence_by_role"].items()):
        L.append("- %s：%s" % (role, ", ".join("%s：%s" % (k, v) for k, v in d.items())))
    L.append("")
    L.append("次数の低い例（固有値＝特性根）：\n")
    import cmath
    from fractions import Fraction as _F
    for role, exs in sorted(s["recurrence_low_order_examples"].items()):
        for x in exs[:3]:
            ev = [complex(a, b) for a, b in (x.get("eigenvalues") or [])]
            mods = sorted({round(abs(z), 6) for z in ev})
            fr = sorted({_F(cmath.phase(z) / (2 * cmath.pi)).limit_denominator(64) % 1 for z in ev if abs(abs(z) - 1) < 1e-6})
            dens = sorted({f.denominator for f in fr})
            L.append("- %s：%s、次数 %s、固有値の絶対値 %s、単位円上の根の偏角／2π の分母（＝周期）%s%s"
                     % (role, x["label"], x["order"], mods[:6], dens, "（1 を含む）" if any(f == 0 for f in fr) else ""))
    L.append("- 合計で次数 0 のシナリオは、年増分がすべて 0（評価範囲に $T$ によって変わる段階がない）もの。")
    L.append("")
    L.append("## 5. FRI（フーリエ係数からの切り替え点）\n")
    L.append("跳びだけの段階（B4・B5）で、事象の数 $K\\le 30$ のもの。回収するのは切り替え点 $\\mathrm{sw}(\\tau)$（$\\tau$ との差は $\\tau\\cdot10^{-9}$ 程度）。$K$ が大きいとトエプリッツ系の条件数が急に悪くなり、回収は失敗する（表の最後の行）。\n")
    fri = s["fri"]["by_K"]
    byK = collections.defaultdict(list)
    for x in fri:
        byK[x["K"]].append(x)
    L.append("| 事象の数 K | 件数 | 切り替え点の誤差の最大（年） | 条件数の最大 |")
    L.append("|---|---|---|---|")
    for K in sorted(byK):
        xs = byK[K]
        L.append("| %d | %d | %s | %s |" % (K, len(xs), e(max(x["err"] for x in xs)), e(max(x["cond"] for x in xs))))
    L.append("")
    sl = s.get("sliver_test", [])
    if sl:
        L.append("## 6. 整数時刻の交換の直後の帯 $(K, \\mathrm{sw}(K))$（独立レビューの指摘、`code/sliver_test.py`）\n")
        L.append("一覧の交換年（整数）を持つ冷媒のあるシナリオで、$T$ を $K$ の直後の浮動小数、$K(1+5\\times10^{-11})$、$K(1+3\\times10^{-10})$、$K(1+3\\times10^{-8})$ に置き、"
                 "基準計算・統一系（第 11 章）・正準形を比べた。\n")
        L.append("| 位置 | `valid_domain` の内側 | 帯の中 | 組 | B1-04 または SUM-03 が相対 1e-9 を超えて基準計算と異なる組（正準形／統一系） | B1-04 の最大相対差 | SUM-03 の最大相対差 |")
        L.append("|---|---|---|---|---|---|---|")
        grp = collections.defaultdict(list)
        for x in sl:
            grp[(str(x["rel_offset"]), x["in_valid_domain"], x["inside_sliver"])].append(x)
        for (off, dom, ins), xs in sorted(grp.items()):
            badc = sum(1 for x in xs if x["SUM-03"]["rel_canon"] > 1e-9 or x["B1-04"]["rel_canon"] > 1e-9)
            bads = sum(1 for x in xs if x["SUM-03"]["rel_system"] > 1e-9 or x["B1-04"]["rel_system"] > 1e-9)
            L.append("| %s | %s | %s | %d | %d／%d | %s | %s |" % (off, "はい" if dom else "いいえ", "はい" if ins else "いいえ", len(xs), badc, bads,
                                                          e(max(x["B1-04"]["rel_canon"] for x in xs)), e(max(x["SUM-03"]["rel_canon"] for x in xs))))
        L.append("")
        L.append("帯の中では、正準形と統一系はどちらも基準計算と異なりうる（交換の初期化を $T>K$ で効かせるため）。`valid_domain` は一覧の事象を調べないので、"
                 "帯のうち $K$ に相対 1e-10 より近い部分が定義域 $\\mathcal{D}$ に残る。第 1 段階の主張は、この帯を除いた $\\mathcal{D}'$ に限る（03 の 0 節）。"
                 "第 11 章（完成済み）は変更していない。\n")
    ue = s.get("units_eq")
    if ue:
        x11, x7, cn = ue["x11"], ue["x07"], ue["counts"]
        L.append("## 7. 合計に入らない $T$ 依存の出力の式（01 の 7 節、`code/units_eq.py`）\n")
        L.append("| 出力 | 照合の内容 | 件数 | 不一致 |")
        L.append("|---|---|---|---|")
        al = x11["alignment"].get("1", [0, 0])
        L.append("| X-11 | $\\mathrm{X11}(T)/G(T)$ が各シナリオで一定（相対 1e-12）、$\\gamma_k$ = X-06 の `by_year[k+1]` | %d シナリオ、%d 点 | %d（`by_year[k]` と読むと %d シナリオすべてで一定にならない） |"
                 % (x11["n_scn"], x11["n_T"], al[1], x11["alignment"].get("0", [0, 0])[1]))
        L.append("| X-07 `by_year` | 核の項を年セルで分けた式（相対 1e-9、$C$ に対して） | %d 点 | %d（最大 %s） |" % (x7["n_T"], x7["series_bad"], e(x7["max_rel"])))
        L.append("| X-07 `cumulative`・`value` | 累積が列の和、値が $C(T)$ | %d 点 | %d、%d |" % (x7["n_T"], x7["cum_bad"], x7["value_vs_C_bad"]))
        L.append("| X-07 と TH-4 の年ごとの分解 | 実時間の測度を $(y-1,y]$ で区切ったものと異なる点 | %d 点 | 異なる %d（すべて整数時刻の事象が数えられている点：%d、整数時刻の事象なしで異なる点：%d） |"
                 % (x7["n_T"], x7["th4_binning_differs"], x7["th4_differs_with_integer_events"], x7["th4_differs_without_integer_events"]))
        L.append("| X-08 `count` | $\\#\\{n:\\mathrm{fl}(nc)<\\mathrm{fl}(T\\,\\mathrm{fl}(1-\\varepsilon))\\}$ | %d（周期×点） | %d |" % (cn["x08_cycles"], cn["x08_bad"]))
        L.append("| B4-01 `events`・`n_events` | $T$ での一覧が $T=H$ の一覧の $\\tau<\\mathrm{fl}(T\\,\\mathrm{fl}(1-\\varepsilon))$ の部分、件数がその和 | %d 一覧 | %d、%d |" % (cn["b401_lists"], cn["b401_bad"], cn["b401_n_bad"]))
        L.append("")
        L.append("B4-01 の一覧（$T=H$）のうち、等差（$\\tau_n = \\mathrm{fl}(n\\tau_1)$）は %d、等差でない（明示の一覧）は %d。B4 の一覧の時刻のうち $C$ の節点にならない（振幅 0 の品目だけの）時刻は %d 個（B4 の節点の時刻は %d 個）。"
                 "回数はこれらも数える（03 の TH-14）。標本：%s の各集合の先頭 25 シナリオまで、各シナリオで保存した評価期間と無作為の 3 点（定義域の内側）。\n"
                 % (cn["arithmetic"], cn["non_arithmetic"], cn["zero_amplitude_event_times"], cn["b4_knot_times"], "dev_design, dev_edge, rep_boundary, rep_evaluation, rep_constructed"))
    ht = s.get("h_test")
    if ht:
        L.append("## 8. 年次表の長さ $H$ への非依存（03 の TH-13、`code/h_test.py`）\n")
        L.append("生成器で $H=160$ の入力を作り、すべての年次表を最初の 130 年で切った入力（$H=130$）と比べた。%d シナリオ×7 点（$T\\le130$）で、正準形の相対差の最大 %s、基準計算の相対差の最大 %s。"
                 "生成器は年ごとに乱数を引くので、同じ種で長さだけを変えると入力そのものが変わる（最初の試行では 8 シナリオ中 6 で年次表が異なった）。そのため切り詰めで同じ入力を作った。\n"
                 % (len(ht), e(max(x["canonical_rel_diff"] for x in ht)), e(max(x["reference_rel_diff"] for x in ht))))
    ex = s.get("expansion")
    if ex:
        L.append("## 9. 節点の係数から単位・入力の行への展開表（`code/expand.py --all-sets`）\n")
        L.append("各集合の先頭のシナリオについて、すべての節点の係数を、寄与した項（単位・段階・核の形）と積和①の出所の行（項ごとの $(p,q)$）に分けて保存した（`results/expansion/<集合>.json.gz`）。"
                 "節点ごとの寄与の和と、まとめた係数の一致は作り方からの帳簿の確認であり、独立の検証ではない。\n")
        L.append("| 集合 | シナリオ | 項 | 節点 | 出所の行の数 | 寄与の和とまとめた係数の不一致 | 保存した評価期間での $C$ と基準計算の最大相対差 |")
        L.append("|---|---|---|---|---|---|---|")
        for k, v in ex.items():
            L.append("| %s | %s | %d | %d | %d | %d | %s |" % (k, v["label"], v["n_terms"], v["n_knots"], v["n_provenance_entries"], v["contributions_vs_merged_bad"], e(v["values_vs_reference_max_rel"])))
        L.append("")
    return "\n".join(L)


def fmt_counts(neg, key):
    d = neg.get(key, {})
    sc = neg.get(key + "__scenarios", {})
    if not d:
        return "なし"
    return "、".join("%s %s（%s）" % (u, n, sc.get(u)) for u, n in sorted(d.items()))


CLASS_JA = {"const": "一定", "step": "階段", "affine": "区分一次", "hyperbolic": "双曲（1/T）", "ratio": "比（一次分数）",
            "other": "その他", "shape": "長さが変わる"}


def unit_structures():
    """Unit -> structures used (column 5 of chapter 11 UNITS_70.md: (1) P1 only, K knot spectrum, (2)a/(2)b TIME/AGG)."""
    p = os.path.join(CH, "..", "10_TRANSFORM_STUDY", "11_UNIFIED_SYSTEM", "UNITS_70.md")
    out = {}
    for line in open(p, encoding="utf-8"):
        if line.startswith("| ") and not line.startswith("| 単位") and not line.startswith("|---"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 6:
                out[cells[0]] = cells[4]
    return out


def doc06(u):
    st = unit_structures()
    L = ["# 06 全 70 評価単位の時間特性（全出力の分類）\n",
         "`code/units_time.py` が、統一系（第 11 章）を、各シナリオで**幅 1e-6 年を超える区切り区間**（格子と事象の切り替え点の間）から**無作為に 30 区間**を選び、"
         "各区間の 3 点で評価して、公開出力の葉ごとに $T$ への依存を分類した（浮動小数での測定、相対 1e-8）。幅 1e-6 年以下の区間（$\\varepsilon$ の帯など）は標本にない。`code/make_docs1.py` が `results/units_time.json` から書き出した。対象は独立概念モデルと架空データ。\n",
         "分類：**一定**（すべての $T$ で同じ）、**階段**（区間ごとに一定。回数・判定・欠損の数・事象の一覧の要素）、**区分一次**（区間ごとに一次式、跳びを含む）、"
         "**双曲**（$T\\cdot$値が区間ごとに一次：年平均）、**比**（$C(T)\\cdot$値が区間ごとに一次：段階の割合）、**その他**、"
         "**期間で現れる**（出力のキーが一部の $T$ にだけある：年次の列の要素など）。列の長さが $T$ で変わる出力は別に数えた。\n",
         "各欄はその分類になった（シナリオ×出力の葉）の数。理論の欄は第 11 章 UNITS_70 の「使う構造」（① 積和①だけ＝$T$ によらない、K 節点スペクトル、②a・②b 評価期間の積和）。\n",
         "標本：%d シナリオ（%s）。\n" % (len([x for x in u["scenarios"] if "error" not in x]), ", ".join(sorted({x["set"] for x in u["scenarios"]}))),
         "| 単位 | 理論（使う構造） | 一定 | 階段 | 区分一次 | 双曲 | 比 | その他 | 期間で現れる | 長さが変わる列 | 理論との関係 |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    keys = ["const", "step", "affine", "hyperbolic", "ratio", "other", "shape"]
    n_bad = 0
    others = []
    for uid in sorted(u["units"]):
        paths = u["units"][uid]
        tot = collections.Counter()
        for p, cnt in paths.items():
            if p == "__list_length_varies__":
                continue
            for k, v in cnt.items():
                tot[k] += v
                if k == "other":
                    others.append((uid, p, v))
        nlist = len(paths.get("__list_length_varies__", {}))
        s = st.get(uid, "?")
        t_indep = ("K" not in s) and ("②" not in s)
        varying = sum(v for k, v in tot.items() if k != "const")
        if t_indep:
            rel = "一致（T によらない）" if varying == 0 and nlist == 0 else "要確認：T によらないはずの単位に変化"
        else:
            rel = "T 依存（構造と整合）" if varying or nlist else "T 依存の構造だが標本では変化なし"
        n_bad += rel.startswith("要確認")
        L.append("| %s | %s | %s | %s |" % (uid, s, " | ".join(str(tot.get(k, 0)) for k in keys), "%d | %s" % (nlist, rel)))
    L.append("")
    L.append("- 「T によらない」構造の単位で変化を示したもの：%d 件。" % n_bad)
    L.append("- 「その他」に分類された葉：%s。" % ("なし" if not others else "、".join("%s `%s`（%d）" % o for o in others)))
    if others:
        L.append("  いずれも edge `zero_quantities`（数量 0 の品目）で、排出の振幅が 0 の事象は $C(T)$ の節点にならない（正準形から除かれる）が、"
                 "回数には数えられるので、正準形の区間の内側で回数が変わる。回数の出力は事象の規則の階段関数であり、$C$ の区切りとは一致しない場合がある。")
    L.append("- 出力の葉ごとの分類（全キー）は `results/units_time.json` の `units`。")
    L.append("")
    L.append("## 理論との対応（03 の TH-14）")
    L.append("")
    L.append("- 合計・段階の値（SUM-01〜03、X-02 の by_stage、X-04・X-05 の内訳、X-07 の累積、SUM-06）：区分一次（TH-1）。A 段階だけの SUM-01 は一定。")
    L.append("- SUM-05（年平均・床面積当たり）：双曲。SUM-07 の割合：比（一次分数）。")
    L.append("- 回数・事象の一覧・判定（B4-01、B4-03、B5-01 の n_events、QA-02、QA-03、X-08、X-10）：階段。")
    L.append("- 年次の列（by_year）：長さが $\\lceil T\\rceil$ で変わり、要素は期間で現れる。")
    return "\n".join(L) + "\n"


def main():
    s = json.load(open(os.path.join(RES, "stage1_summary.json")))
    open(os.path.join(CH, "07_検証の結果.md"), "w").write(doc07(s))
    up = os.path.join(RES, "units_time.json")
    if os.path.exists(up):
        open(os.path.join(CH, "06_70単位の時間特性.md"), "w").write(doc06(json.load(open(up))))
    print("written")


if __name__ == "__main__":
    main()
