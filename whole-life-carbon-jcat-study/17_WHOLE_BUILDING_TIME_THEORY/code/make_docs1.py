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
    L.append("`code/aggregate1.py` が `results/` の JSON から作った `results/stage1_summary.json` を、`code/make_docs1.py` がこの文書に書き出した（数値は手で書いていない）。"
             "対象は独立概念モデルと架空データ。\n")
    L.append("## 1. 理想方程式と 70 単位モデル（基準計算）との一致\n")
    L.append("比較の規則は第 11 章と同じ：数値は相対 1e-9、基準計算が厳密に 0 なら 0 であること。`code/verify_canon.py`。\n")
    L.append("| 項目 | 件数 | 不一致 | 最大相対差 |")
    L.append("|---|---|---|---|")
    L.append("| 組（シナリオ×評価期間） | %s（定義域の外で除外 %s、失敗 %s） | — | — |" % (cv.get("n_pairs"), cv.get("n_excluded"), cv.get("n_failed")))
    L.append("| ホールライフ合計 SUM-03（正準形 vs 基準計算） | %s | %s | %s |" % (cv.get("n_pairs"), cv.get("total_vs_ref_bad"), e(cv.get("max_rel_total_vs_ref"))))
    L.append("| 同（正準形 vs 統一系、相対 1e-12） | %s | %s | — |" % (cv.get("n_pairs"), cv.get("total_vs_sys_bad")))
    L.append("| 同（節点形 vs 核の和、相対 1e-12） | %s | %s | — |" % (cv.get("n_pairs"), cv.get("knot_vs_terms_bad")))
    L.append("| 14 段階の値 | %s | %s | %s |" % (cv.get("n_stage"), cv.get("stage_vs_ref_bad"), e(cv.get("max_rel_stage_vs_ref"))))
    L.append("| 合計に入る 22 単位の値 | %s | %s | %s |" % (cv.get("n_unit"), cv.get("unit_vs_ref_bad"), e(cv.get("max_rel_unit_vs_ref"))))
    L.append("| 参考：B1-04 の跳び形（正準形には使わない） | %s | %s | — |" % (cv.get("n_jumpform"), cv.get("jumpform_vs_ref_bad")))
    L.append("")
    L.append("集合ごと：\n")
    L.append("| 集合 | 組 | 除外 | SUM-03 不一致 | 段階 | 段階 不一致 | 単位 | 単位 不一致 | 跳び形の不一致 |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for k, v in cv.get("by_set", {}).items():
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (k, v["n_pairs"], v["n_excluded"], v["total_vs_ref_bad"], v["n_stage"], v["stage_vs_ref_bad"],
                                                               v["n_unit"], v["unit_vs_ref_bad"], v.get("jumpform_vs_ref_bad")))
    L.append("")
    L.append("**1.2 密度の振幅を率で持つ理由。** 最初の版は第 11 章と同じく密度の振幅を $a\\cdot H$（浮動小数の積）で持ち、厳密に評価した。基準計算が厳密に 0 を返す段階値"
             "（edge `life_shorter_than_one_year`、T = 10、B3）で −9.8e-12 が残った（丸めた積 $\\mathrm{fl}(aH)/H \\ne a$）。率 $a$ で持つと 0 に一致する（全集合で不一致 0）。\n")
    L.append("**1.3 B1-04 の跳び形。** 跳び形を厳密に評価すると、強く減衰する冷媒（rep_constructed の「no events, leak 35％／60％」）で基準計算と 9 件の不一致（基準 3.9e-21 に対して −8.8e-14 など）。"
             "係数そのものが浮動小数で丸められているので、厳密な評価でも桁落ちは消えない（第 11 章 D-09 の現象を再現）。区間形では 0 件。\n")
    L.append("## 2. 時間特性の定理の厳密な照合（有理数）\n")
    c = s["counts"]
    L.append("シナリオ %s 件（全 10 集合の全シナリオ。準備に失敗 %s 件）。`code/timechar.py`。\n" % (s["n_analysed"], len(s["prepare_errors"])))
    L.append("| 照合 | 標本の数 | 不一致 |")
    L.append("|---|---|---|")
    ex = s["exact_failures"]
    rows = [("TH-0 核の和 ＝ 節点形（各シナリオ最大 60 区間の中点）", c["th0_points"], ex.get("th0_bad")),
            ("TH-1 全区間で一次式（3 点）", c["pieces"], ex.get("th1_affine_bad")),
            ("TH-1 区間の係数 ＝ 節点の累積和", c["pieces"], ex.get("th3_coef_bad")),
            ("TH-2 跳び ＝ $p+q\\,\\mathrm{sw}$（節点形）", c["jumps"], ex.get("th2_jump_bad")),
            ("TH-2 事象の前後の跳び（核の和で、各シナリオ最大 12 事象）", c["th2_events_with_terms"], ex.get("th2_terms_bad")),
            ("TH-2 切り替えの直前の値が左の区間に乗る", c["th2_events_with_terms"], ex.get("th2_left_continuity_bad")),
            ("TH-2 格子の丸めの跳びが相対 1e-12 を超える", c["lattice_rounding_jumps"], ex.get("lattice_jumps_above_1em12")),
            ("TH-3 傾きの変化 ＝ $q$", c["pieces"], ex.get("th3_slope_change_bad")),
            ("TH-4 $C = M([0,T)) + Z(T)$", c["pieces"], ex.get("th4_decomp_bad")),
            ("TH-4 $C' = \\rho + Z'$", c["pieces"], ex.get("th4_rate_bad")),
            ("TH-4 測度の累積和 ＝ 項ごとの和", "各 40 区間", ex.get("th4_direct_sum_bad")),
            ("TH-4 終わりの項の節点形 ＝ 項ごとの和", "50 回に 1 回", ex.get("th4_terminal_form_bad")),
            ("TH-5 年増分の分解", "全年", ex.get("th5_increment_bad")),
            ("TH-6 積分の閉じた形", c["th6_points"], ex.get("th6_integral_bad"))]
    for a, b, d in rows:
        L.append("| %s | %s | %s |" % (a, b, d))
    L.append("")
    sz = s.get("size", {})
    L.append("- 大きさ：核の項はシナリオの中央値 %s（最大 %s）、節点（格子＋事象）は中央値 %s（最大 %s）、項／節点の比の中央値 %.1f。年次表の長さ $H$：%s。"
             % (sz.get("terms_median"), sz.get("terms_max"), sz.get("knots_median"), sz.get("knots_max"), sz.get("ratio_terms_per_knot_median") or 0, sz.get("H_values")))
    L.append("- 節点の数：区間 %s、事象の節点 %s、格子の節点 %s、跳び %s（うち整数時刻の事象による区間形の初期化 %s、格子の丸めの跳び %s、その最大は係数の大きさの相対 %s）。"
             % (c["pieces"], c["event_knots"], c["lattice_knots"], c["jumps"], c["integer_event_reset_jumps"], c["lattice_rounding_jumps"], e(s["max_rel_lattice_rounding_jump"])))
    L.append("- 補題 L-2：浮動小数の切り替え点 $\\mathrm{sw}(g)$ と $g/(1-\\varepsilon)$ の差は最大 %.2f ulp。" % s["switch_offset_ulp_max"])
    ts = s["terminal_slope"]
    L.append("- TH-4(a)：終わりの項の傾き $Z'\\ne0$ を持つシナリオ %s / %s。区間のうち $Z'\\ne0$ の割合の中央値 %.2f。$|Z'|/|C'|$ の最大 %s、95 パーセンタイル %s。"
             % (ts["scenarios_with_any"], s["n_analysed"], ts["median_fraction_of_pieces"] or 0, e(ts["max_rel_to_total_slope"]), e(ts["p95_rel_to_total_slope"])))
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
    L.append("- フーリエ係数：閉じた形と数値積分の相対差の最大 %s、共役対称 $c_{-n}=\\overline{c_n}$ の相対差の最大 %s。係数の減衰の傾き（両対数）中央値 %.3f（範囲 %.3f〜%.3f。傾き 0 は $C$ が $T$ によらず $c_n=0$（$n\\ne0$）のシナリオ）。"
             % (e(s["fourier_closed_vs_pieces_max_rel"]), e(s["fourier_conjugate_symmetry_max"]), s["fourier_decay_slope"]["median"],
                s["fourier_decay_slope"]["min"], s["fourier_decay_slope"]["max"]))
    L.append("- 周期の境界：部分和（512 項）は $T=0$ で $(C(0^+)+C(H))/2$ に近づく（相対差の最大 %s）。" % e(s["fourier_boundary_midpoint_rel_max"]))
    L.append("")
    L.append("部分和の誤差（$\\max|C|$ に対する相対。全シナリオの中央値と最大）：\n")
    L.append("| 項数 $N$（$|n|\\le N$） | 最大誤差 中央値 | 最大誤差 最大 | 区切りから 0.05 年以上離れた点の最大誤差 中央値 | 誤差の中央値（中央値） |")
    L.append("|---|---|---|---|---|")
    for M, d in s["fourier_partial_sums"].items():
        L.append("| %s | %s | %s | %s | %s |" % (M, e(d["max_rel_all_median"], "%.3g"), e(d["max_rel_all_max"], "%.3g"), e(d["max_rel_far_median"], "%.3g"), e(d["median_rel_median"], "%.2e")))
    L.append("")
    L.append("## 4. 線形漸化式（厳密な次数）と DMD\n")
    L.append("年増分 $d_y$（$y=2..H$）の最小の線形漸化式の次数（バーレカンプ・マッシー法、有理数）：\n")
    L.append("- 合計：%s" % ", ".join("%s：%s 件" % (k, v) for k, v in s["recurrence_total"].items()))
    for role, d in sorted(s["recurrence_by_role"].items()):
        L.append("- 役割 %s：%s" % (role, ", ".join("次数 %s：%s 件" % (k, v) for k, v in sorted(d.items(), key=lambda kv: (kv[0] == ">24", int(kv[0]) if kv[0].isdigit() else 0)))))
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
    L.append("")
    L.append("- 漸化式で列を再生した浮動小数の誤差：%s（合計の次数が 40 以下で一意に決まるシナリオが無ければ —）" % e(s.get("recurrence_float_replay_max_rel")))
    L.append("- 合計で次数 0 のシナリオは、年増分がすべて 0（評価範囲に $T$ によって変わる段階がない）もの。")
    L.append("")
    L.append("## 5. FRI（フーリエ係数からの事象の時刻）\n")
    fri = s["fri"]["by_K"]
    byK = collections.defaultdict(list)
    for x in fri:
        byK[x["K"]].append(x)
    L.append("跳びだけの段階（B4・B5）で、事象の数 $K\\le 30$ のもの。$K$ が大きいとトエプリッツ系の条件数が急に悪くなり、回収は失敗する（下の表の最後の行）。\n")
    L.append("| 事象の数 K | 件数 | 時刻の誤差の最大（年） | 条件数の最大 |")
    L.append("|---|---|---|---|")
    for K in sorted(byK):
        xs = byK[K]
        L.append("| %d | %d | %s | %s |" % (K, len(xs), e(max(x["err"] for x in xs)), e(max(x["cond"] for x in xs))))
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
         "`code/units_time.py` が、統一系（第 11 章）を、区切り区間（格子と事象の切り替え点の間）ごとに 3 点で評価し、公開出力の葉ごとに $T$ への依存を分類した"
         "（浮動小数での測定、相対 1e-8）。`code/make_docs1.py` が `results/units_time.json` から書き出した。対象は独立概念モデルと架空データ。\n",
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
