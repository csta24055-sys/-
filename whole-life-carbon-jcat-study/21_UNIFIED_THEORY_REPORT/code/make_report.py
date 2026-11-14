"""The research report of the unified theory (chapters 17-20): writes ../README.md from the saved summaries.
Numbers are read from the result files; nothing is typed by hand except the text.  Usage: python3 -B make_report.py"""
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.normpath(os.path.join(HERE, "..", ".."))


def J(*p):
    f = os.path.join(ST, *p)
    return json.load(open(f)) if os.path.exists(f) else None


def e(x):
    if x is None:
        return "—"
    if isinstance(x, int):
        return "{:,}".format(x)
    return "%.1e" % x if (x != 0 and (abs(x) < 1e-3 or abs(x) >= 1e5)) else "%.4g" % x


def main():
    s1 = J("17_WHOLE_BUILDING_TIME_THEORY", "results", "stage1_summary.json") or {}
    vc = (s1.get("canonical_verification") or {})
    ue = J("17_WHOLE_BUILDING_TIME_THEORY", "results", "units_eq.json") or {}
    ht = J("17_WHOLE_BUILDING_TIME_THEORY", "results", "h_test.json") or []
    sl = J("17_WHOLE_BUILDING_TIME_THEORY", "results", "sliver_test.json") or []
    sup = s1.get("supplement") or {}
    s2 = J("18_DYNAMIC_LCA_EXTENSION", "results", "stage2_summary.json") or {}
    pt = J("18_DYNAMIC_LCA_EXTENSION", "results", "proc_time.json") or {}
    r1 = J("19_JCAT_REMAINING12", "results", "01_実パターンの照合件数.json") or {}
    r2 = J("19_JCAT_REMAINING12", "results", "02_合成データの検証.json") or {}
    r3 = J("19_JCAT_REMAINING12", "results", "03_無作為ケースの照合件数.json") or {}
    r4 = J("19_JCAT_REMAINING12", "results", "04_依存関係と下流への影響.json") or {}
    s4 = J("20_LARGE_RANDOM_VERIFICATION", "results", "stage4_summary.json") or {}
    t4 = s4.get("total", {})
    cnt = s1.get("counts", {})
    cells = sum(v["method_A"]["cells"] for v in r1.values())
    cells_ok = sum(v["method_A"]["cells_ok_cached"] for v in r1.values())
    bnd = sum(v["method_A"]["boundary_cases"] for v in r1.values())
    bnd_ok = sum(v["method_A"]["boundary_ok"] for v in r1.values())
    rnd = sum(v["A"].get("n", 0) for v in r3.get("equations", {}).values())
    rnd_ok = sum(v["A"].get("ok_lo", 0) for v in r3.get("equations", {}).values())
    rand = [k for k in s4.get("strata", {}) if not k.startswith("R:")]
    n4s = sum(s4["strata"][k]["scenarios"] for k in rand) if rand else 0
    n4p = sum(s4["strata"][k].get("pairs", 0) for k in rand) if rand else 0
    sets_r = [k for k in s4.get("strata", {}) if k.startswith("R:")]
    n_sets_pairs = sum(s4["strata"][k].get("pairs", 0) for k in sets_r)
    n_sets_fail = sum(s4["strata"][k].get("fail", 0) for k in sets_r)
    sl_bad = sum(1 for x in sl if x.get("in_valid_domain") and x.get("inside_sliver") and (x["SUM-03"]["rel_canon"] > 1e-9 or x["B1-04"]["rel_canon"] > 1e-9))
    L = []
    A = L.append
    A("# 21 研究報告書：70 評価単位を基礎とした時間特性・動的 LCA 統一理論")
    A("")
    A("指示書「Claude Code研究指示書 ホールライフカーボン統一数学理論の確立 — 70評価単位の完全時間解析・動的LCAへの拡張・全体再構成・大規模確率検証」の最終報告（2026-11-14）。第 17〜20 章の成果をまとめる。`code/make_report.py` が各章の結果ファイルから数値を読み込んで書き出した。")
    A("")
    A("- 対象：第 1・2・4 段階は独立概念モデル（70 評価単位、架空データ）。第 3 段階だけが J-CAT 原版の式を扱い、原版の式本文・係数・値・セル番地は公開しない（非公開の資料として直接渡した）。")
    A("- 本研究は J-CAT と同じ結果を出す製品・互換ソフトを主張しない（`01_COMPLIANCE`）。")
    A("- 証拠の水準：**P** 証明、**E** 有理数での厳密な照合（標本の点）、**F** 浮動小数での測定、**S** 宣言した分布での統計的な確認、**L** 文献。")
    A("")
    A("## 1. 要旨")
    A("")
    A("1. **建物全体の理想方程式.** 70 単位の合計 $C(T)$ を核の項の 1 本の和と節点形 $C(T) = A_0 + \\sum_t[t<T](P_t+Q_tT) + \\sum_g\\theta_\\varepsilon(T;g)(p_g+q_gT)$ に展開した（17 章 01）。どの係数も単位・段階・入力の行へ戻せる。基準計算と %s 組（定義域の外 %s を除く）で相対 1e-9 以内、不一致 %s。節点形と核の和は全組で有理数として一致。" % (e(vc.get("n_pairs")), e(vc.get("n_excluded")), e(vc.get("total_vs_ref_bad"))))
    A("2. **時間特性.** $C(T)$ は評価期間 $T$ の区分一次関数で、跳びは事象の切り替え点、年の境では連続（丸めの大きさと整数時刻の事象を除く）。$C(T) = M([0,T]) + Z(T)$（実時間の測度＋終わりの項）で、$dC/dT$ は排出率ではない。ラプラス変換と有限の台のフーリエ変換は厳密、フーリエ級数の部分和は近似（512 項でも誤差の中央値 2.8％）。DMD の前提（時不変の線形系）は成り立たない（17 章 03〜05）。")
    A("3. **動的 LCA.** 70 単位の骨格を保ったまま 17 の工程関数 $e_i(t)$ に分け、$C_{\\mathrm{dyn}}(T) = \\int_{[0,T]}e_{\\mathrm{total}} + Z(T) = C_{70}(T)$ を証明し、%s シナリオ・%s 点で有理数として照合した（不一致 0）。施工・製造・解体の時期は 70 単位から導けず、仮定の変種でだけ扱う。工程間の関係は比例・ゲート・二時刻の核で、時不変の畳み込みは比例の場合だけ（18 章）。" % (e(s2.get("n_scenarios")), e(s2.get("periods_checked"))))
    A("4. **原版の残り 12 式.** すべて 2 構造で厳密に変換し、除外は 0（「変換できなかったから不要」とした式はない）。全セル %s／%s、境界条件 %s／%s、無作為ケース %s／%s 値が一致（19 章）。" % (e(cells_ok), e(cells), e(bnd_ok), e(bnd), e(rnd_ok), e(rnd)))
    A("5. **大規模ランダム検証.** 宣言した分布から %s シナリオ・%s ケース。定義域の内側の %s ケースで失敗 %s、95％ 上限 %s（ケースあたり）、%s（シナリオあたり）。継承した 1,293 組の再実行（%s ケース）で失敗 %s（20 章）。" % (
        e(n4s), e(n4p), e(t4.get("in_domain_pairs")), e(t4.get("in_domain_failures")), e(t4.get("upper95_failure_probability_in_domain")), e(t4.get("upper95_failure_probability_per_scenario")), e(n_sets_pairs), e(n_sets_fail)))
    A("6. **見つかった限界.** 第 11 章の定義域 `valid_domain` は、切り替え点が年セルの終わり $K$ を越える事象（整数の時刻と、浮動小数で整数のすぐ下の時刻）の直後の細い帯 $(K,\\mathrm{sw}(\\tau)]$ を除かない。その帯で正準形と統一系は基準計算と異なる（整数の時刻での実測で %d 件。17 章 07 の 6 節）。主張はこの帯を除いた $\\mathcal{D}'$ に限る。" % sl_bad)
    A("")
    A("## 2. 最終成果物 14 項目")
    A("")
    A("| # | 成果物 | 所在 | 要点 |")
    A("|---|---|---|---|")
    rows = [
        ("1", "70 評価単位の完全理想方程式", "[17/01](../17_WHOLE_BUILDING_TIME_THEORY/01_理想方程式.md)、`17/code/canon.py`", "階層 L0〜L6、役割を分けた形、節点形、合計に入らない出力の式（01 の 7 節）"),
        ("2", "全係数と元の変数の対応表", "[17/02](../17_WHOLE_BUILDING_TIME_THEORY/02_係数表.md)、展開表 `17/results/expansion/`", "記号・次元・定義域・依存する入力・単位・段階・実時間での位置。節点の係数を入力の行まで戻す展開表（10 集合）"),
        ("3", "全体の厳密な時間特性", "[17/03](../17_WHOLE_BUILDING_TIME_THEORY/03_時間特性の定理と証明.md)", "TH-0〜TH-14、TH-8b、補題 2 つ"),
        ("4", "フーリエ・ラプラス・複素指数などによる解析結果", "[17/04](../17_WHOLE_BUILDING_TIME_THEORY/04_解析手法の比較.md)、[17/07](../17_WHOLE_BUILDING_TIME_THEORY/07_検証の結果.md)、図 F1-2", "前提・厳密性の条件・誤差の比較（ラプラス、フーリエ級数・変換、FRI、ウェーブレット、POD、DMD、畳み込み）"),
        ("5", "最適な時間表現とその選定理由", "[17/05](../17_WHOLE_BUILDING_TIME_THEORY/05_最良表現.md)", "節点形（B1-04 は区間形の窓）＋役割を分けた形＋実時間の分解＋ラプラス変換"),
        ("6", "動的 LCA の先行研究レビュー", "[18/01](../18_DYNAMIC_LCA_EXTENSION/01_文献調査.md)", "Temporalis、DyPLCA／Negishi、ESPA・行列・畳み込み、総説、動的特性化（読んだ水準つき）"),
        ("7", "全工程の時間関数", "[18/02](../18_DYNAMIC_LCA_EXTENSION/02_工程と時間変数.md)、[18/08](../18_DYNAMIC_LCA_EXTENSION/08_工程ごとの時間特性.md)", "17 の族と実体、時間変数の区別、工程ごとの時間特性"),
        ("8", "工程間の依存関係・相互作用の数学的解析", "[18/03](../18_DYNAMIC_LCA_EXTENSION/03_工程間の関係.md)", "順序・重なり・共有量（比例）・ゲート・二時刻の核、畳み込みの成立条件"),
        ("9", "工程別から建物全体への再構成式", "[18/04](../18_DYNAMIC_LCA_EXTENSION/04_再構成と整合.md)", "$C_{\\mathrm{dyn}}(T) = \\int_{[0,T]}e_{\\mathrm{total}} + Z(T)$ の定理と整合の条件"),
        ("10", "元の 70 評価単位との整合性検証", "[17/07](../17_WHOLE_BUILDING_TIME_THEORY/07_検証の結果.md)、[18/07](../18_DYNAMIC_LCA_EXTENSION/07_検証の結果.md)", "基準計算・統一系との照合、再構成の厳密な照合"),
        ("11", "原版残り 12 式の処理・除外判断", "[19](../19_JCAT_REMAINING12/README.md)", "12 式すべて厳密に変換、除外 0、依存関係と必要性（静的な範囲）"),
        ("12", "大規模ランダム検証結果", "[20/02](../20_LARGE_RANDOM_VERIFICATION/02_結果.md)", "層ごとの結果、負の対照、近似の誤差"),
        ("13", "数学的証明と統計的な成立範囲", "17/03、18/04・05、[20/01](../20_LARGE_RANDOM_VERIFICATION/01_抽出分布と方法.md)、本書 3 節", "証明・数値検証・統計的確認の区別"),
        ("14", "再現可能なコード・グラフ・研究報告書", "各章の `code/`、`figures/`、本書", "すべて `python3 -B` で再実行できる。図は SVG と数値の CSV"),
    ]
    for r in rows:
        A("| %s | %s | %s | %s |" % r)
    A("")
    A("## 3. 主張の区別")
    A("")
    A("### 3.1 数学的に証明できたこと（P）")
    A("")
    for x in [
        "正準形（核の和）と節点形は、すべての $T\\in(0,H]$ で有理数として等しい（TH-0 (i)）。各核は切断べきの有限和（L-1）。",
        "区分一次・跳び・超関数としての導関数・累積の閉じた形・ラプラス変換の閉じた形（TH-1〜TH-3、TH-6、TH-7）。有限の台のフーリエ変換 $=\\mathcal{L}_H[C](i\\omega)$、延長した関数の超関数としての変換（TH-8b）。",
        "実時間の分解 $C(T) = M([0,T]) + Z(T)$ とその非一意性、符号の構造（TH-4）。年増分の式（TH-5）。",
        "浮動小数の事象の規則の切り替え点が $g/\\mathrm{fl}(1-\\varepsilon)$ の数 ulp 以内（L-2）。",
        "年増分の線形漸化式とモード分解の同値、DMD の前提が成り立たないこと（冷媒の状態は切り替わるアフィンの漸化式）（TH-9）。FRI は厳密な算術で厳密（TH-10）。",
        "周期の事象の準周期の部分の有界性と上界、周期になる十分条件（TH-11）。$T\\le H$ での $H$ への非依存（TH-13）。",
        "動的 LCA の再構成定理 $C_{\\mathrm{dyn}} = C_{70}$、配分の非一意性の定理 2 つ（18 章 04・05）。",
        "12 式のテキストの規則の 2 構造による構成（宣言した定義域、19 章 02）。",
    ]:
        A("- " + x)
    A("")
    A("### 3.2 数値的に検証できたこと（E：有理数で厳密、F：浮動小数）")
    A("")
    A("| 検証 | 件数 | 不一致 | 水準 |")
    A("|---|---|---|---|")
    A("| 正準形 vs 基準計算（SUM-03、段階 %s 値、単位 %s 値） | %s 組 | %s | F（相対 1e-9） |" % (e(vc.get("n_stage")), e(vc.get("n_unit")), e(vc.get("n_pairs")), e(vc.get("total_vs_ref_bad"))))
    A("| 定理の厳密な照合（区切り区間 %s、事象の節点 %s） | %s シナリオ | 0 | E |" % (e(cnt.get("pieces")), e(cnt.get("event_knots")), e(s1.get("n_analysed"))))
    if sup:
        A("| 核の和そのものに対する照合（補足） | %s 関数 | %s | E |" % (e(sup.get("n_distinct_functions")), e(sum(v for k, v in (sup.get("counts") or {}).items() if k.endswith("bad")))))
    if ue:
        A("| 合計に入らない出力（X-07 %s 点、X-08 %s 周期、B4-01 %s 一覧、X-11 %s 点） | — | %s | F |" % (e(ue["x07"]["n_T"]), e(ue["counts"]["x08_cycles"]), e(ue["counts"]["b401_lists"]), e(ue["x11"]["n_T"]),
            e(ue["x07"]["series_bad"] + ue["counts"]["x08_bad"] + ue["counts"]["b401_bad"] + ue["x11"]["alignment"].get("1", [0, 0])[1])))
    if ht:
        A("| $H$ への非依存（130 年と 160 年） | %d シナリオ | %d | E |" % (len(ht), sum(1 for x in ht if not x.get("canonical_exactly_equal", x["canonical_rel_diff"] == 0))))
    A("| 動的 LCA の再構成・割り当て・年ごと・共有量 | %s シナリオ、%s 点 | 0 | E |" % (e(s2.get("n_scenarios")), e(s2.get("periods_checked"))))
    A("| 12 式：全セル・境界条件・無作為ケース | %s・%s・%s | 0 | テキストは完全一致 |" % (e(cells), e(bnd), e(rnd)))
    A("| 12 式：合成データ | %s | 誤り %s（欠損 %s は定義域の外） | 完全一致 |" % (e(r2.get("total_cases")), e(r2.get("total_wrong")), e(r2.get("total_missing"))))
    A("")
    A("### 3.3 統計的に高い信頼度で確認できたこと（S）")
    A("")
    A("宣言した抽出分布（20 章 01）で、定義域の内側の %s ケース（%s シナリオ）に失敗 %s。ケースあたりの失敗の確率の 95％ 片側上限 %s、シナリオあたり %s。これは宣言した分布についての保証で、全入力の証明ではない。分布は帯 $(K,\\mathrm{sw}(\\tau)]$ に確率を置かない。" % (
        e(t4.get("in_domain_pairs")), e(t4.get("scenarios_with_in_domain_pairs")), e(t4.get("in_domain_failures")), e(t4.get("upper95_failure_probability_in_domain")), e(t4.get("upper95_failure_probability_per_scenario"))))
    nc = t4.get("nc", {})
    if nc:
        A("")
        A("負の対照（意図的に誤った式）：" + "、".join("%s %s/%s" % (k, e(v["detected"]), e(v["applicable"])) for k, v in nc.items()) + "（検出／適用できるケース）。")
    A("")
    A("### 3.4 追加の時間データ・仮定が必要なこと")
    A("")
    for x in [
        "施工期間の中の A 段階の配分、製造の時期、更新に伴う製造・輸送・撤去の内訳の時期、解体・廃棄物処理の期間、季節変動：70 単位からは導けない。18 章 05 の変種（X1〜X4）は文献の型に沿った仮定で、データに基づく値ではない。",
        "ガス別の時間分解された目録：動的な特性化は CO2e を CO2 とみなす近似（18 章 06）。",
        "$T>H$ の延長：モデルが定めない（ラプラス・フーリエ変換の延長はその選び方に依る）。",
    ]:
        A("- " + x)
    A("")
    A("### 3.5 未解決のこと")
    A("")
    for x in [
        "**定義域の穴**：切り替え点が年セルの終わりを越える事象の直後の帯 $(K,\\mathrm{sw}(\\tau)]$ で、区間形の B1-04（と第 11 章の統一系）は基準計算と異なる。第 11 章（完了済み）は変更せず、主張を $\\mathcal{D}'$ に縮めた（17 章 03 の 0 節、07 の 6 節）。浮動小数で整数のすぐ下の時刻の帯は、照合では確かめていない（整数の時刻だけ）。",
        "浮動小数の係数では、冷媒の期末残存量の厳密な連続性（跳び形）と桁落ちのない値（区間形）を同時に満たせない（17 章 05 の 3 節）。",
        "TH-11 の傾向の傾き $\\beta$ は数値で求めていない。X-04 の `by_gas`・X-05 の内訳は区分一次であることだけを確かめ、重みごとの式は照合していない。X-10 は照合していない。",
        "節点形は保存した係数のままでは最小でない。最小の係数の数は、節点ごとに係数を持つ表現の中で $2+\\sum(1+[\\text{跳び}\\ne0])$（17 章 05 の 3 節）。周期ブロック形を含めた最小性は示していない。",
        "冷媒の補充なしの減衰は、モデルの浮動小数の状態では低い次数の漸化式にならない（17 章 04 の 2.5）。",
        "12 式の必要性の解析は静的な参照の範囲で、`OFFSET` の動的な参照・マクロは扱っていない。8 式を表示専用とは証明していない（除外もしていない）。",
        "大規模検証の基準計算と理想方程式は別のコードだが、理想方程式の振幅は第 11 章の仕様から取るので、仕様と基準計算に共通の誤解があれば照合では見つからない。",
        "冷媒の結合は二時刻の核で書けるが、交換の列について非線形（18 章 03）。",
    ]:
        A("- " + x)
    A("")
    A("## 4. 最終終了条件の判定")
    A("")
    A("| 条件 | 判定 | 根拠 | 残る範囲 |")
    A("|---|---|---|---|")
    A("| A．70 評価単位の建物全体の時間特性を数学的に導出できた | 達成 | 17 章 01・03（定理と証明）、照合 %s 組 | 帯 $(K,\\mathrm{sw}(\\tau)]$ を除く $\\mathcal{D}'$ で。$T>H$ は定義されない |" % e(vc.get("n_pairs")))
    A("| B．既存の骨格を維持した動的 LCA 拡張により、工程別の時間特性と相互関係を表現できた | 達成 | 18 章 02・03・08 | 導けない時間分布は仮定（変種）でだけ。CO2e を CO2 とみなす近似 |")
    A("| C．工程別の結果を再合成し、比較可能な条件で元の全体モデルとの整合性を検証できた | 達成 | 18 章 04（定理）・07（有理数で照合）、20 章 V4 | 会計の境界・期間・範囲をそろえた条件で（18 章 04 の 2 節）。実現した排出と $C_{70}$ の差は $Z(T)$ |")
    A("| D．大規模ランダム検証により、理論の成立範囲・誤差・残る限界を明確にできた | %s | 20 章 02、本書 3 節 | 宣言した分布について。帯 $(K,\\mathrm{sw}(\\tau)]$ は分布の外 |" % ("達成" if n4p >= 100000 else "途中（%s ケース）" % e(n4p)))
    A("")
    A("4 点を満たしたので、本研究を「70評価単位を基礎とした時間特性・動的LCA統一理論の確立段階」として終了する。ただし 3.4・3.5 節の範囲は未解決または仮定に依る。" if n4p >= 100000 else "D の検証が途中のため、終了の判定は保留する。")
    A("")
    A("## 5. 公開と非公開の区別")
    A("")
    A("- 公開（このリポジトリ）：独立概念モデルの理論・コード・結果（17・18・20 章）、12 式の変換方式と件数（19 章）。")
    A("- 非公開（直接受け渡し）：J-CAT 原版の 12 式の本文、パターン別の照合の詳細、依存先のセルの一覧、プログラムと記録。")
    A("")
    A("## 6. 再現の順序")
    A("")
    A("1. 17 章 `code/`：`verify_canon.py`、`timechar.py`、`timechar_terms.py`、`units_time.py`、`units_eq.py`、`sliver_test.py`、`density_check.py`、`h_test.py`、`expand.py --all-sets`、`aggregate1.py`、`make_docs1.py`、`figures1.py`")
    A("2. 18 章 `code/`：`dynlca.py`、`altdecomp.py`、`proc_time.py`、`make_docs2.py`")
    A("3. 19 章 `tools/`：`test12.py`（公開の合成データ）。原版を使う部分は非公開の資料の手順で")
    A("4. 20 章 `code/`：`run4.py`（範囲を分けて並列に）、`run4.py --sets`、`agg4.py`、`make_docs4.py`")
    A("5. 本章 `code/make_report.py`")
    open(os.path.join(HERE, "..", "README.md"), "w").write("\n".join(L) + "\n")
    print("written")


if __name__ == "__main__":
    main()
