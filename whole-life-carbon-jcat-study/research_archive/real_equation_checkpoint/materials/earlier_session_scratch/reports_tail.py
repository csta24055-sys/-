def _err(c):
    return c.get("stage_error") or c.get("row_error") or {}


def models_report():
    mj = load("03_MODELS/models.json")
    models = mj["models"]
    cands = load("03_MODELS/candidates.json")["candidates"]
    recs = load("03_MODELS/records/units.json")
    trace = load("03_MODELS/judge_proposal_trace.json")
    oc = Counter(r["outcome"] for r in recs["records"])
    by_step = {m: Counter(r["outcome"] for r in recs["records"] if r["step"] == m) for m in ("M1", "M2", "M3", "M4", "M5", "M6")}
    n_units = len(load("01_LEDGER/units.json")["units"])
    unified = sum(m["unit_count"] for m in models)
    cc = Counter(c["outcome"] for c in cands)
    t = ["# 03 検討した近似式・統合モデル（成果物 5）", "", NOTICE, CAVEAT,
         "## 結論の要約", "",
         f"- 評価単位 {n_units} 件のそれぞれについて 6 段階（M1 厳密な簡略化、M2 厳密な統合、M3 単純な近似、M4 共通の近似モデル、M5 代理モデル、M6 厳密と近似の併用）を検討し、"
         f"**{recs['record_count']} 件**の記録を残した（成功 {oc['SUCCESS']}、不採用 {oc['REJECTED']}、保留 {oc['HOLD']}、候補なし {oc['NOT_APPLICABLE']}）。記録は [records/units.json](records/units.json)。",
         f"- **独立概念モデルでは、{unified} 単位が {len(models)} つの統合モデルに、結果を変えずにまとまった。** 統合されなかったのは {len(mj['not_unified'])} 単位（{'、'.join(mj['not_unified'])}）。",
         f"- **近似の段階（M3〜M6）で採用した候補はない。** 測定した近似候補 {len(cands)} 種は、不採用 {cc['REJECTED']}、実データ待ちの保留 {cc['HOLD']}。"
         "重視した M4（異なる式を共通の近似モデルへまとめる）も、結論が出たものはなく、すべて保留である。", "",
         table(["段階", "成功", "不採用", "保留", "候補なし（測定なし）"],
               [[m, by_step[m]["SUCCESS"], by_step[m]["REJECTED"], by_step[m]["HOLD"], by_step[m]["NOT_APPLICABLE"]] for m in by_step],
               ["---", "---:", "---:", "---:", "---:"]), "",
         "表は記録の件数（単位×段階×候補）。「候補なし」は、測定をせずに理由だけで見送ったもので、検証結果ではない。", "",
         "## 統合の基準", "",
         f"{mj['membership_rule']} 関数の形が似ているだけのもの、同じ走査の中で別々に計算しているだけのものは、統合に数えない。", "",
         "## 全体の形（独立概念モデルでは）", "",
         "```",
         "値[表] = Σ_係数キー  A[表, 係数キー] × 係数         A = Σ_行 活動量 × 行の乗数",
         "",
         "評価期間 T に依存する乗数   1 回限り      1                              A1-A3・A4・A5・C1〜C4",
         "                           更新          N(T, 周期)                     B4",
         "                           修繕          T − 除外年の重み(T, 周期)      B3",
         "                           建替          N(T, 建替周期) × 範囲比        B5",
         "                           年次          年重み付きの和（G・H）         B6・B7・B2",
         "                           充填サイクル  1 − (1−漏洩率)^年数 など       B1",
         "```",
         "",
         "- これは**独立概念モデルを設計した結果**であり、原版の式がこの形であることを確かめたものではない。独立概念モデルでは、材料・用途・構造の違いを行（数量と係数）というデータの違いとして表すように設計したので、"
         "式には現れない。原版に工種別・用途別の式があるかどうかは調べていない。",
         "- 上の形に入るのは排出と集計の単位である。検査、係数解決、指標は別のモデル（K6・K7・K5）で、買電と冷媒は活動量の時点で排出量になっている（係数 1 の特別なキー）。",
         "- 行の合算（A と、周期ごとの合算）は評価期間 T に依存しない。そのため、T を変えた結果は合算をやり直さずに乗数だけ計算し直して得られる（実装して基準計算と突き合わせた。[04_VERIFICATION](../04_VERIFICATION/README.md)）。",
         "- 式の導出は [DERIVATIONS.md](DERIVATIONS.md)。", "",
         "## 統合モデルの目録", "",
         table(["ID", "名称", "式", "考え方", "統合しても保つもの", "導出", "単位数"],
               [[m["id"], m["name"], f"`{m['form']}`", m["idea"], m["kept"], m["derivation"], m["unit_count"]] for m in models],
               ["---", "---", "---", "---", "---", "---", "---:"]), "",
         "統合した単位：", "",
         "\n".join(f"- **{m['id']} {m['name']}**（{m['unit_count']}）：{'、'.join(m['units'])}" for m in models), "",
         f"統合しなかった単位（{len(mj['not_unified'])}）：{'、'.join(mj['not_unified'])}。検査の 4 単位は判定の対象と基準がそれぞれ違い、同じ走査に組み込むこと（M1）にとどめた。"
         "STO-01 は入力が係数ではなく物性値で与えられるため、表に載せても式も入力も減らない。", "",
         "## 仕組みの確認", "",
         "記録が「係数を行ごとに掛けない」「年ごとの繰り返しをしない」などと述べる場合、その仕組みを統合モデル自身が数えた回数で確かめている"
         "（[unified_model_exactness.json](../04_VERIFICATION/unified_model_exactness.json) の `mechanism_counts`。成り立たなければ記録の生成が失敗する）。", "",
         table(["記号", "確かめた内容"], [[k, v["statement"]] for k, v in mj["mechanisms"].items()]), "",
         "多くの仕組みは**合計のみを求める場合**に成り立つ。行別の一覧や年次の系列まで出力する場合は、値は同じだが、行ごと・年ごとの計算が残る。", "",
         "## 近似候補と測定結果", "",
         "誤差 = (候補 − 基準) ÷ 基準。負は過小評価。「対象」は誤差を測った量、「合計」はホールライフ合計に対する影響。", "",
         table(["ID", "段階", "候補", "対象", "判定", "平均", "95％点", "最大の過大", "最大の過小", "合計：95％点", "理由"],
               [[c["candidate_id"], c["step"], c["title"], c["measured_on"], OUTCOME_JA[c["outcome"]], pct(_err(c).get("mean_signed"), 1, True), pct(_err(c).get("p95_abs")),
                 pct(_err(c).get("max_over"), 1, True), pct(_err(c).get("max_under"), 1, True), pct((c.get("total_error") or {}).get("p95_abs")), c["reason"]]
                for c in cands], ["---", "---", "---", "---", "---", "---:", "---:", "---:", "---:", "---:", "---"]), "",
         "- 保留の候補は、誤差が建物ごとの資材構成や条件のばらつきで決まる。架空データは実建物を表していないので、ここでの値からは採否を判断できない。必要なデータは [06_OPEN_ISSUES](../06_OPEN_ISSUES/README.md) に記載した。",
         "- AP-20 は推定値ではなく上下限なので、誤差の列は空欄。内容は [04_VERIFICATION](../04_VERIFICATION/README.md)。",
         "- 条件別・構造別・用途別・材料区分別の内訳は [approximation_study.json](../04_VERIFICATION/approximation_study.json) にある。", "",
         "## 評価者の提案との対照", "",
         f"評価軸 B の採点で「近似・共通化できる」が 2 点以上だった単位×段階は {len(trace['score_2_or_more'])} 件。このうち測定をせずに理由だけで見送ったものは {len(trace['not_measured'])} 件"
         f"（{'、'.join(trace['not_measured']) or 'なし'}）。初版で取り上げていなかった具体的な提案の扱い：", "",
         table(["対象", "提案", "記録", "扱い"], [[n["units"], n["proposal"], "、".join(n["records"]) or "—", n["disposition"]] for n in trace["named_proposals"]]), "",
         "## 単位別の記録の見方", "",
         "`records/units.json` の 1 件は「評価単位×段階×候補」。SUCCESS は、(1) 出力が基準計算と一致、(2) 述べている仕組みが計数で確かめられる、(3) 導出が DERIVATIONS.md にある、の裏付けを生成時に確かめたもの。"
         "導出のないものは `VERIFIED_SYNTHETIC_ONLY`（架空データでの一致のみ）と表示する。NOT_APPLICABLE は測定をしていない判断で、`verification` は `NOT_VERIFIED`。"]
    write("03_MODELS/README.md", "\n".join(t))


GROUP_JA = {"benchmark": "標準ベンチマーク（規模 S・M・L）", "edge": "境界条件", "population": "検証用の母集団", "defective": "不備を入れたシナリオ",
            "mutated": "入力を 1 か所ずつ壊したシナリオ", "decimal": "小数の評価期間と周期の端", "stage_subset": "対象段階を一部にしたシナリオ"}
LOAD_ROWS = [
    ("reference_without_baseline_comparison", "基準計算（基準案との比較を除く）"),
    ("unified_full_outputs", "統合モデル：全出力（行別の一覧と年次の系列を含む）"),
    ("unified_totals_only", "統合モデル：合計・段階・指標・検査のみ"),
    ("reference_with_baseline_comparison", "基準計算（基準案との比較を含む）"),
    ("unified_full_outputs_with_baseline_comparison", "統合モデル：全出力、基準案も計算"),
    ("unified_full_outputs_baseline_total_held_by_caller", "統合モデル：全出力、基準案の合計は呼び出し側が保持"),
    ("reference_four_more_periods", "基準計算：別の評価期間 4 通りの合計"),
    ("unified_four_more_periods_from_one_aggregation", "統合モデル：同じ 4 通りを 1 回の合算から"),
]


def verification_report():
    ex = load("04_VERIFICATION/unified_model_exactness.json")
    ld = load("04_VERIFICATION/unified_model_load.json")
    ap = load("04_VERIFICATION/approximation_study.json")
    iu = load("04_VERIFICATION/input_usage.json")
    leaves = sum(u["leaves_compared"] for u in ex["units"].values())
    other = sum(u["non_numeric_compared"] for u in ex["units"].values())
    worst = max(ex["units"].items(), key=lambda kv: kv[1]["max_abs_rel_error"])
    sw = ex["period_sweep"]
    mc = ex["mechanism_counts"]
    rows = []
    for size, r in ld["sizes"].items():
        for key, label in LOAD_ROWS:
            v = r[key]
            red = "compared_with" in v
            rows.append([size, f"{r['rows']['materials']:,}", label, f"{v['instructions']:,}", pct(v["instruction_reduction"]) if red else "—",
                         f"{v['time_ms']:.1f}", pct(v["time_reduction_gc_off"]) if red else "—", f"{v['time_ms_gc_on']:.1f}",
                         f"{v['peak_memory_kib']:,.0f}", pct(v["memory_reduction"]) if red else "—"])
    c = ap["candidates"]
    st = lambda s: (f"{s['n']} 件、平均 {pct(s['mean_signed'], 2, True)}、95％点 {pct(s['p95_abs'], 2)}、範囲 {pct(s['max_under'], 1, True)}〜{pct(s['max_over'], 1, True)}"
                    if s and s.get("n") else "該当なし")
    cls_rows = []
    for cid in ("AP-01", "AP-06", "AP-07a", "AP-18a"):
        for k, v in (c[cid].get("by_material_class") or {}).items():
            cls_rows.append([cid, k, v["n"], pct(v["mean_signed"], 1, True), pct(v["p95_abs"], 1), pct(v["max_over"], 1, True), pct(v["max_under"], 1, True)])
    stat_keys = [("row_factor_products", "行ごとの係数の乗算"), ("table_factor_products", "表の読み出しでの乗算"), ("year_loop_iterations", "年ごとの繰り返し"),
                 ("event_lists_built", "作った更新年の一覧"), ("recipes_computed", "複合係数の計算"), ("factor_resolutions", "係数の解決"),
                 ("unit_conversions_resolved", "単位換算の解決"), ("rows_scanned", "読んだ行"), ("consistency_scan_values", "記述子と年次表の読み比べ（値の数）")]
    par, tab = mc["parametric_inputs"], mc["year_table_inputs"]
    L = ld["sizes"]["L"]
    b20 = c["AP-20"]
    t = ["# 04 基準計算との誤差と処理時間（成果物 6）", "", NOTICE, CAVEAT,
         "## 1. 統合モデルは基準計算と一致するか", "",
         f"統合モデル（`research_code/fastcalc/engine.py`）と基準計算（`research_code/refcalc/`）の全出力を、**{ex['scenarios']} シナリオ**で 1 つずつ突き合わせた。", "",
         table(["シナリオの種類", "件数", "最大の相対差", "不一致のシナリオ"],
               [[GROUP_JA.get(k, k), v["scenarios"], f"{v['max_abs_rel_error']:.1e}", v["failed"]] for k, v in ex["by_group"].items()], ["---", "---:", "---:", "---:"]), "",
         f"- 比較した数値は **{leaves:,} 個**、数値以外（合否・状態・件数の一覧など）は {other:,} 個。許容差は相対 {ex['tolerance']:.0e}。",
         f"- 結果：**不一致なし**（`all_exact = {str(ex['all_exact']).lower()}`）。最大の相対差は {worst[1]['max_abs_rel_error']:.1e}（{worst[0]}）で、加算の順序が違うことによる丸めの差。",
         f"- 「入力を 1 か所ずつ壊したシナリオ」は {len(ex['mutations'])} 種類の壊し方（記述子と年次表の食い違い、係数の単位・対象段階の誤り、負や範囲外の値、欠損、期間外の事象、"
         "小数の周期、自分自身を基準案にする指定など）を使う。どちらの計算も、使えない行・経路・項目を合計から除いたうえで同じ値を返し、同じ不備を報告する。",
         "- **一致の意味の限定**：一致するのは、両方の計算が同じ定義（年次量は整った記述子を正とする、など）に従うからである。記述子と年次表が食い違う入力では、"
         "どちらを正とするかという定義の選択が結果を左右する。両者はその食い違いを報告するが、正しい値がどちらかは入力からは決められない。",
         f"- 無効な評価期間（0、負、非数、無限大）は、どちらの計算も {ex['invalid_periods_refused_by_both']} でエラーにする。",
         f"- 「合計・段階・指標・検査のみ」の出力でも同じ値になることを確認した。ただしこの出力では、{'・'.join(ex['units_without_output_in_totals_mode'])} は出力を持たない（行別の値だけを出す単位のため）。",
         "- 個々の閉形式（更新回数、修繕の除外年、年次の和、電力係数のモーメント、冷媒の充填サイクル）は、ループ版との一致を別途、乱数と境界値で検査している（`tests/test_closed_forms.py`）。", "",
         "### 評価期間を変えたとき", "",
         f"{sw['scenarios']} シナリオについて、評価期間を {len(sw['periods'])} 通り（{'、'.join(f'{p:g}' for p in sw['periods'])} 年）に変えた結果を、行の合算 1 回から乗数だけ計算し直して求め、"
         f"期間ごとに最初から計算した基準計算と突き合わせた。比較した値は {sw['values_compared']:,} 個、最大の相対差 {sw['max_abs_rel_error']:.1e}、不一致 {len(sw['failures'])} 件。", "",
         "### 基準案との比較", "",
         "統合モデルは基準案の結果を内部に保持しない（保持すると、基準案を書き換えたときに古い値を返す）。基準案の合計を呼び出し側が持っていて渡した場合に限り、"
         f"基準案の計算を省く。この使い方でも基準計算と一致すること、基準案を書き換えたら渡した値を捨てる必要があることを確認した（`baseline_reuse_checked = {str(ex['baseline_reuse_checked']).lower()}`）。"
         "これは式の簡略化ではなく作業の進め方であり、下の表では別の行に分けている。", "",
         "### 統合モデルが実際に行った演算の回数", "",
         f"資材 {par['rows']['materials']} 行・設備 {par['rows']['equipment']} 行の架空シナリオで数えた（相異なる係数 {par['distinct']['factors_used']}、周期の値 {par['distinct']['renewal_periods']}、配合 {par['distinct']['compositions']}）。", "",
         table(["数えたもの", "記述子の入力：合計のみ", "記述子の入力：全出力", "年次表の入力：合計のみ", "年次表の入力：全出力"],
               [[label, f"{par['totals_only'][k]:,}", f"{par['full_outputs'][k]:,}", f"{tab['totals_only'][k]:,}", f"{tab['full_outputs'][k]:,}"] for k, label in stat_keys],
               ["---", "---:", "---:", "---:", "---:"]), "",
         "## 2. 計算の重さはどれだけ減るか", "",
         "同じ言語（純粋な Python）、同じ機械、同じ入力で測った。**主な指標は実行したバイトコード命令数**（機械の混み具合やごみ集めに左右されない）。"
         "時間は、ごみ集め（GC）を止めた反復の中央値で、GC を動かしたときの値を並べて示す。ベクトル化などの実装技法は使っていない。", "",
         table(["規模", "資材行", "計算", "命令数", "命令数の削減", "時間 ms（GC 停止）", "時間の削減", "時間 ms（GC あり）", "ピークメモリ KiB", "メモリの削減"],
               rows, ["---", "---:", "---", "---:", "---:", "---:", "---:", "---:", "---:", "---:"]), "",
         "- 削減率は、同じ仕事をする基準計算の行に対する値（統合モデルの 1・2 行目は 1 行目の基準計算、3・4 行目は 4 行目の基準計算、最後の行はその上の基準計算）。",
         "- 「全出力」は、基準計算が出す行別の一覧と年次の系列をすべて出す場合。「合計・段階・指標・検査のみ」はそれらを省いた場合。",
         "- 基準案の合計を呼び出し側が保持する行は、基準案の計算を省いた分だけ軽い。式の効果ではないので、成果の数字としては使わない。",
         f"- 別の評価期間の合計は、合算をやり直さないので、規模 L で命令数が {pct(L['unified_four_more_periods_from_one_aggregation']['instruction_reduction'])} 減る（4 通り分）。",
         "- GC を動かしたときの時間は、基準計算のほうが多くの一時オブジェクトを作るぶん不利に出る。この差は式の効果ではなく実行環境の効果なので、時間の比較は GC を止めた値で行う。",
         "- 測定値は実行環境で変わる。再測定は `python3 -m bench.verify_unified`。", "",
         "## 3. 入力項目は減るか", "",
         f"計算の途中で読まれた入力の項目を、基準計算と統合モデルで記録した（{iu['scenarios']} シナリオ。[input_usage.json](input_usage.json)）。", "",
         table(["計算", "既存の入力仕様の項目", "本研究で加えた項目"],
               [[{"reference_all_units": "基準計算", "unified_full_outputs": "統合モデル：全出力", "unified_totals_only": "統合モデル：合計のみ"}[k],
                 v["existing_inputs_read"], v["added_inputs_read"]] for k, v in iu["summary"].items()], ["---", "---:", "---:"]), "",
         f"- **統合モデルが読む入力は、基準計算と同じである。** 基準計算は読むが統合モデル（合計のみ）は読まない項目は {len(iu['read_by_reference_but_not_by_unified_totals_only'])} 件。厳密な統合では入力は減らない。",
         "- 記述子で与えられる年次量の年次表は、合計の計算には使わないが、記述子との食い違いを報告するために読む。食い違いの報告をやめれば読まずに済むが、その場合は一致の確認ができなくなる。",
         f"- 入力仕様 {iu['inputs_in_specification']} 項目のうち {iu['metadata_only_inputs']} 項目は記録用で、どの計算にも使われない。", "",
         "## 4. 近似候補の誤差", "",
         f"検証用の母集団 {ap['population']} シナリオ（構造 4 種×用途 6 種、規模 S・M、評価期間 30〜100 年と非整数）で測定した。目標は 合計 {pct(ap['targets']['total'], 0)}、段階 {pct(ap['targets']['stage'], 0)}。"
         "母集団から学習する候補（AP-10・10b・11・15・16・21・22b）は、前半で係数を決め、後半で誤差を測った。", "",
         table(["ID", "候補", "誤差を測った量", "誤差", "合計への影響（95％点）", "過小評価"],
               [[cid, v["title"], v["stage"], st(_err(v)), pct((v.get("total_error") or {}).get("p95_abs"), 2), {True: "あり", False: "なし", None: "—"}[v.get("under_estimates")]]
                for cid, v in c.items() if cid != "AP-20"]), "",
         f"**AP-20（上下限）**：{b20['n']} シナリオのすべてで基準値が上下限の間に入った。上下限の幅は B4 の値に対して平均 {pct(b20['bracket_width_relative_to_reference']['mean_abs'])}。", "",
         "条件別に見ると：", "",
         f"- **AP-01〜03（更新回数）を B5 と X-10 に適用した場合**：AP-01 は B5 で {st(c['AP-01']['other_targets']['B5（建替・大型改修の回数に適用）']['stage_error'])}、X-10 の資源量で {st(c['AP-01']['other_targets']['X-10 資源量[kg]'])}。",
         f"- **AP-08（平均×平均）**：買電量が一定なら {st(c['AP-08']['by_profile_kind']['CONSTANT'])}。直線的に変化する場合は {st(c['AP-08']['by_profile_kind']['LINEAR_TREND'])}。",
         f"- **AP-09a（5 年ごとの補間）**：直線低下の係数では {st(c['AP-09a']['by_grid_kind']['LINEAR_DECLINE_TO_FLOOR'])}、段階的な係数では {st(c['AP-09a']['by_grid_kind']['STEPWISE'])}、"
         f"年次表の係数では {st(c['AP-09a']['by_grid_kind']['TABLE'])}。",
         f"- **AP-05（冷媒の線形近似）**：補充しない機器で 漏洩率×サイクル年数 が 0.05〜0.2 の場合 {st(c['AP-05']['by_rate_times_cycle_years_no_top_up_devices']['0.05<rk<=0.2'])}。",
         f"- **AP-17（平均距離）**：{'；'.join(f'{k} {st(v)}' for k, v in c['AP-17']['other_targets'].items())}。", "",
         "構造別・用途別（AP-04 の例。どの区分でも過大側で、区分による差は小さい）：", "",
         table(["区分", "件数", "平均", "95％点", "最大"],
               [[k, v["n"], pct(v["mean_signed"], 2, True), pct(v["p95_abs"], 2), pct(v["max_over"], 2, True)] for k, v in c["AP-04"]["by_group"].items()],
               ["---", "---:", "---:", "---:", "---:"]), "",
         "材料区分別（資材の行に作用する候補。1 シナリオ内の区分ごとの合計の誤差。設備は EQUIPMENT）：", "",
         table(["候補", "材料区分", "件数", "平均", "95％点", "最大の過大", "最大の過小"], cls_rows, ["---", "---", "---:", "---:", "---:", "---:", "---:"]), "",
         "材料区分の名前と区分ごとの条件は架空データの生成器が決めたもので、区分による違いは生成器の設定を映しているだけである。実際の材料区分での誤差は実データで測る必要がある。", "",
         "段階ごとの原単位による代理モデル（AP-15）の段階別の誤差（架空の母集団）：", "",
         table(["段階", "件数", "平均", "95％点", "最大の過大", "最大の過小"],
               [[k, v["n"], pct(v["mean_signed"], 0, True), pct(v["p95_abs"], 0), pct(v["max_over"], 0, True), pct(v["max_under"], 0, True)]
                for k, v in c["AP-15"]["by_stage"].items() if v.get("n")], ["---", "---:", "---:", "---:", "---:", "---:"]), "",
         "これらの大きな誤差は、架空データの数量と係数を広い範囲の乱数で作っているためで、実建物での誤差を表していない。代理モデルの採否は実データなしには判断できない。", "",
         "## 5. 独立した検査", "",
         "初版の結果に対して、3 つの自動検査（数値の反例探し、定義からの再導出、記録の監査）を行い、指摘を反映した。指摘と対応は [INDEPENDENT_REVIEW.md](INDEPENDENT_REVIEW.md)。", "",
         "## ファイル", "",
         "- [unified_model_exactness.json](unified_model_exactness.json)：単位ごとの比較結果、評価期間を変えた比較、演算の回数",
         "- [unified_model_load.json](unified_model_load.json)：命令数・時間・メモリ",
         "- [input_usage.json](input_usage.json)：読まれた入力項目",
         "- [approximation_study.json](approximation_study.json)：近似候補の誤差（全体・構造別・用途別・材料区分別・条件別）",
         "- [INDEPENDENT_REVIEW.md](INDEPENDENT_REVIEW.md)：独立した検査の指摘と対応"]
    write("04_VERIFICATION/README.md", "\n".join(t))


def decisions_report():
    mj = load("03_MODELS/models.json")
    models = mj["models"]
    cands = load("03_MODELS/candidates.json")["candidates"]
    led = load("05_DECISIONS/progress_ledger.json")
    ld = load("04_VERIFICATION/unified_model_load.json")["sizes"]
    ex = load("04_VERIFICATION/unified_model_exactness.json")
    iu = load("04_VERIFICATION/input_usage.json")
    units = load("01_LEDGER/units.json")["units"]
    cov = load("01_LEDGER/sheet_family_coverage.json")["families"]
    status = Counter(u["status"] for u in led["units"])
    n_units = len(units)
    unified = sum(m["unit_count"] for m in models)
    partial = [u for u in led["units"] if u["steps_on_hold"] and u["status"].startswith("DONE")]
    inputs_all = {i for u in units for i in u["inputs"]}
    inputs_new = {i for i in inputs_all if i.startswith("NEW:")}
    fam_by_unit = {}
    for f in cov:
        for uid in f["related_units"]:
            fam_by_unit.setdefault(uid, []).append(f)
    rows_models = []
    for m in models:
        fams = {f["family"]: f for uid in m["units"] for f in fam_by_unit.get(uid, []) if f["formula_xml_nodes"]}
        top = sorted(fams.values(), key=lambda f: -f["formula_xml_nodes"])[:3]
        rows_models.append([m["id"], m["name"], m["unit_count"], "、".join(f"{f['family']}（{pct(f['share_of_all_nodes'], 1)}）" for f in top) or "—"])
    L = ld["L"]
    ref, full, tot = L["reference_without_baseline_comparison"], L["unified_full_outputs"], L["unified_totals_only"]
    refb, fullb = L["reference_with_baseline_comparison"], L["unified_full_outputs_with_baseline_comparison"]
    swp, swr = L["unified_four_more_periods_from_one_aggregation"], L["reference_four_more_periods"]
    iur, iut = iu["summary"]["reference_all_units"], iu["summary"]["unified_totals_only"]
    steps = ("M1", "M2", "M3", "M4", "M5", "M6")
    step_rows = []
    for m in steps:
        cnt = Counter(u["steps"][m]["conclusion"] for u in led["units"])
        step_rows.append([f"{m} {led['steps'][m]}", cnt.get("SUCCESS", 0), cnt.get("REJECTED", 0), cnt.get("HOLD", 0), cnt.get("NOT_APPLICABLE", 0), cnt.get("NOT_DONE", 0)])
    hold_units = [u["id"] for u in led["units"] if u["status"] == "HOLD_DATA_OR_RIGHTS"]
    t = ["# 05 採否の理由と、統合前後の変化（成果物 7・8）", "", NOTICE, CAVEAT,
         "## 採用（研究上の推奨）", "",
         f"**{len(models)} つの統合モデル（K1〜K{len(models)}）を、厳密な統合として推奨する。** {ex['scenarios']} の架空シナリオ（不備のある入力、記述子と年次表が食い違う入力を含む）で、"
         "基準計算と全出力が一致し、入力検査の結果も同じだった。ここでの「採用」は将来の実装候補としての推奨で、製品への組み込みを意味しない。", "",
         table(["モデル", "名称", "まとめた単位数", "関連すると推定されるシート族（数式ノード占有率）"], rows_models, ["---", "---", "---:", "---"]), "",
         "右端の列は、シート名だけからの推定による対応で、原版の式がこのモデルで置き換えられることを確認したものではない。名称から対応を推定できない族は載せていない。", "",
         "## 不採用", "",
         "\n".join(f"- **{c['candidate_id']} {c['title']}**：{c['reason']}" for c in cands if c["outcome"] == "REJECTED"), "",
         "共通する理由は 2 つ。(1) 重大な過小評価が出る、または誤差が段階 2％・合計 1％ の目標を超える。(2) 厳密な閉形式が同じ手間で使えるので、近似に替える利点がない。", "",
         "## 検証保留（実データが必要）", "",
         "\n".join(f"- **{c['candidate_id']} {c['title']}**：{c['reason']} 必要なデータ：{c['data_needed']}" for c in cands if c["outcome"] == "HOLD"), "",
         "## 現状のまま維持", "",
         f"- 統合しなかった {len(mj['not_unified'])} 単位（{'、'.join(mj['not_unified'])}）：検査は判定の対象と基準がそれぞれ違い、同じ走査に組み込むことにとどめた。STO-01 は物性値からの積で、表に載せても式も入力も減らない。",
         "- すべての検査（SYS・QA・C-05）：近似しない。判定の基準は変えていない。", "",
         "## 進捗の集計", "",
         table(["状態", "件数"], [[led["status_labels"][k], status.get(k, 0)] for k in led["status_labels"]] + [["**合計**", f"**{n_units}**"]], ["---", "---:"]), "",
         f"- 「検証完了・統合成功」「検証完了・簡略化成功」は、厳密な部分（M1・M2）についての状態である。このうち {len(partial)} 単位は、近似の段階（M3〜M6）に実データ待ちの保留がある。",
         f"- 「データ・権利上の制約により保留」は {'、'.join(hold_units) or 'なし'}。",
         "- 測定や導出の裏付けが 1 件もない単位は「完了」にしない規則にしている（該当なし）。", "",
         "段階別の結論（単位の数）：", "",
         table(["段階", "成功", "不採用", "保留", "候補なし（測定なし）", "未実施"], step_rows, ["---", "---:", "---:", "---:", "---:", "---:"]), "",
         "**近似の段階（M3〜M6）で採用に至った候補はない。** M4（異なる式を共通の近似モデルへまとめる）は、区分ごとの代表パラメータ（AP-18）、区分ごとの代表係数（AP-10）、"
         "面積当たりの原単位（AP-13・AP-15）を測定したが、いずれも誤差が実建物のばらつきで決まるため保留である。単位ごとの状態は [PROGRESS.md](PROGRESS.md)。", "",
         "## 統合前後の変化（成果物 8）", "",
         "独立概念モデルについての値である。原版ブックの数式の数や計算時間がどれだけ変わるかを示すものではない。", "",
         table(["項目", "統合前（基準計算）", "統合後（統合モデル）", "変化"], [
             ["計算の定義の数", f"{n_units}（評価単位ごとに 1 つの関数）", f"統合モデル {len(models)}＋統合されない単位 {len(mj['not_unified'])}", f"{n_units} → {len(models) + len(mj['not_unified'])}"],
             ["共通化できた単位", "—", f"{unified} 単位 → {len(models)} モデル", "—"],
             ["単位が参照する入力項目", f"{len(inputs_all)}（既存 {len(inputs_all) - len(inputs_new)}＋追加 {len(inputs_new)}）", "同じ", "変化なし"],
             ["計算中に読まれた入力項目（実測）", f"既存 {iur['existing_inputs_read']}＋追加 {iur['added_inputs_read']}", f"既存 {iut['existing_inputs_read']}＋追加 {iut['added_inputs_read']}", "変化なし"],
             ["実行した命令数（規模 L、全出力）", f"{ref['instructions']:,}", f"{full['instructions']:,}", pct(full["instruction_reduction"]) + " 減"],
             ["同（合計・段階・指標・検査のみ）", f"{ref['instructions']:,}", f"{tot['instructions']:,}", pct(tot["instruction_reduction"]) + " 減"],
             ["同（基準案との比較を含む、全出力）", f"{refb['instructions']:,}", f"{fullb['instructions']:,}", pct(fullb["instruction_reduction"]) + " 減"],
             ["別の評価期間 4 通りの合計（規模 L）", f"{swr['instructions']:,}", f"{swp['instructions']:,}", pct(swp["instruction_reduction"]) + " 減"],
             ["計算時間（規模 L、全出力、GC 停止）", f"{ref['time_ms']:.0f} ms", f"{full['time_ms']:.0f} ms", pct(full["time_reduction_gc_off"]) + " 減"],
             ["同（合計・段階・指標・検査のみ）", f"{ref['time_ms']:.0f} ms", f"{tot['time_ms']:.0f} ms", pct(tot["time_reduction_gc_off"]) + " 減"],
             ["ピークメモリ（規模 L、全出力）", f"{ref['peak_memory_kib'] / 1024:.0f} MiB", f"{full['peak_memory_kib'] / 1024:.0f} MiB", pct(full["memory_reduction"]) + " 減"],
             ["同（合計・段階・指標・検査のみ）", f"{ref['peak_memory_kib'] / 1024:.0f} MiB", f"{tot['peak_memory_kib'] / 1024:.0f} MiB", pct(tot["memory_reduction"]) + " 減"],
             ["結果の差", "—", f"相対 {ex['tolerance']:.0e} 以内で一致", "精度の低下なし"],
         ], ["---", "---:", "---:", "---:"]), "",
         "- **「計算の定義の数」は、式の種類そのものの数ではない。** 統合モデルの中には、更新・修繕・建替・年次・充填サイクルという乗数の関数と、9 つの検査の規則が、それぞれ別のものとして残っている。"
         "数えているのは、評価単位ごとに別々にあった計算の定義が、いくつの共通の形にまとまったかである。",
         "- **入力項目は減っていない。** 厳密な統合は結果を変えないので、必要な入力も変わらない（実測でも同じ）。入力を減らすには少数の入力で済む近似モデルが必要で、それは実データ待ちで保留している。",
         "- 命令数が減った主な理由は、(a) 行を 1 回だけ走査する、(b) 係数を行ごとに掛けず、表の中で合算してから掛ける、(c) 更新・修繕の乗数を、行ごとではなく周期の値ごとの合算に掛ける、"
         "(d) 年ごと・事象ごとの繰り返しを閉形式にする、の 4 つ。(b)〜(d) は合計のみを求める場合に最も効き、行別の一覧や年次の系列まで出力する場合は効果が小さくなる。",
         "- 基準案の合計を呼び出し側が保持して使い回す場合の数字は、式の効果ではないので、この表には入れていない（[04_VERIFICATION](../04_VERIFICATION/README.md) にはある）。",
         "- 規模 S・M の値、GC を動かしたときの時間は [04_VERIFICATION](../04_VERIFICATION/README.md) にある。"]
    write("05_DECISIONS/README.md", "\n".join(t))


def overview_report():
    led = load("01_LEDGER/units.json")
    cov = load("01_LEDGER/sheet_family_coverage.json")
    mj = load("03_MODELS/models.json")
    models = mj["models"]
    cands = load("03_MODELS/candidates.json")["candidates"]
    recs = load("03_MODELS/records/units.json")
    ex = load("04_VERIFICATION/unified_model_exactness.json")
    ld = load("04_VERIFICATION/unified_model_load.json")["sizes"]["L"]
    prog = load("05_DECISIONS/progress_ledger.json")
    status = Counter(u["status"] for u in prog["units"])
    partial = sum(1 for u in prog["units"] if u["steps_on_hold"] and u["status"].startswith("DONE"))
    leaves = sum(u["leaves_compared"] for u in ex["units"].values())
    not_inspected = [f for f in cov["families"] if f["status"] == "NOT_INSPECTED"]
    oc = Counter(c["outcome"] for c in cands)
    ref, full, tot = ld["reference_without_baseline_comparison"], ld["unified_full_outputs"], ld["unified_totals_only"]
    t = ["# 第9章：計算式の近似化・統合研究", "", NOTICE,
         "独立計算モデルの式群を、必要な精度を保ったまま、できるだけ少数の簡単な計算式へ置き換えられるかを調べた研究の記録。",
         "**アプリ・UI・製品用エンジンは作っていない。** J-CAT の原版ファイル・式本文・原単位などは含まない（[第1章](../01_COMPLIANCE/README.md)）。", "",
         "## 統制文書", "",
         "- [00_POLICY/DIRECTIVE.md](00_POLICY/DIRECTIVE.md)：開発方針指示書（受領した全文）",
         "- [00_POLICY/DIRECTIVE_AMENDMENT_01.md](00_POLICY/DIRECTIVE_AMENDMENT_01.md)：追加・変更指示 第1号（上位 30％ 制限の撤廃。受領した全文）",
         "- [00_POLICY/EVALUATION_PROTOCOL.md](00_POLICY/EVALUATION_PROTOCOL.md)：評価単位、2 軸評価、着手順序、検討手順、検証手順、進捗台帳の定義", "",
         "## 結果の要点", "",
         f"1. **評価単位は {led['unit_count']} 件**（既存の概念式 {led['existing_unit_count']}＋追加で特定した計算構造 {led['additional_unit_count']}）。上位 30％ に絞らず、全件を研究対象にした。"
         "これは独立概念モデルの単位であり、原版の数式を調べたものではない。",
         f"2. **独立概念モデルでは、{sum(m['unit_count'] for m in models)} 単位が {len(models)} つの統合モデルに、結果を変えずにまとまった**（統合されなかったのは {len(mj['not_unified'])} 単位）。"
         "排出と集計は「表ごとに 活動量×係数 を足す」1 つの形と、評価期間に依存する数個の乗数の関数で書ける（[03_MODELS](03_MODELS/README.md)、導出は [DERIVATIONS.md](03_MODELS/DERIVATIONS.md)）。",
         f"3. **統合モデルは基準計算と一致した。** {ex['scenarios']} の架空シナリオ、数値 {leaves:,} 個を突き合わせて不一致なし（許容差は相対 {ex['tolerance']:.0e}）。"
         "不備のある入力や、冗長な入力どうしが食い違う場合も、同じ値を返し、同じ不備を報告する。",
         f"4. **計算の重さは減った。** 資材 2 万行の規模で、実行した命令数は、基準計算と同じ出力をすべて出す場合に {pct(full['instruction_reduction'])} 減、合計・段階・指標・検査だけを求める場合に {pct(tot['instruction_reduction'])} 減"
         f"（時間は {ref['time_ms']:.0f} ms → {full['time_ms']:.0f} ms、{tot['time_ms']:.0f} ms。同じ言語・同じ機械、ごみ集めを止めて測定）。"
         f"評価期間だけを変えた再計算は、行の合算をやり直さずに済む（[04_VERIFICATION](04_VERIFICATION/README.md)）。",
         f"5. **近似は 1 つも採用していない。** 近似候補 {len(cands)} 種を測定し、不採用 {oc['REJECTED']}、実データ待ちの保留 {oc['HOLD']}。更新回数の連続近似のように重大な過小評価を生むものがあり、"
         "それ以外の多くも、厳密な閉形式が同じ手間で使えるため近似の利点がなかった。異なる式を共通の近似モデルへまとめる試み（区分ごとの代表パラメータなど）は、"
         "誤差が実建物のばらつきで決まるため、架空データでは結論を出せず保留した。",
         "6. **入力項目は減っていない。** 厳密な統合では、読む入力は基準計算と同じだった（実測）。入力を減らすには少数入力の近似モデルが必要だが、その精度は実建物のデータがなければ検証できない。",
         "7. 独立概念モデルでは（設計上）、材料・用途・構造の違いは式には現れず、行（数量と係数）というデータの違いとして扱っている。評価期間と更新・修繕の条件は、乗数の関数の引数になる。"
         "原版に工種別・用途別の式があるかどうかは、調べていない。", "",
         "## 進捗（全評価単位）", "",
         table(["状態", "件数"], [[prog["status_labels"][k], status.get(k, 0)] for k in prog["status_labels"]] + [["**合計**", f"**{len(prog['units'])}**"]], ["---", "---:"]), "",
         f"「検証完了」は厳密な部分（簡略化と統合）についての状態で、数学的な導出と架空データでの確認が終わったことを指す。このうち {partial} 単位は、近似の段階に実データ待ちの保留がある。"
         f"記録は {recs['record_count']} 件（[05_DECISIONS/PROGRESS.md](05_DECISIONS/PROGRESS.md)）。", "",
         "## この研究で言えないこと", "",
         "- **原版ブックの数式は調べていない。** 原版ファイルは本リポジトリにも研究環境にも存在しない。評価単位は独立概念モデルのもので、原版の約 382 万の数式ノードを調査・検証したものではない。",
         f"- シート名と評価単位の対応は名称からの推定で、式の内容は全シート族について未確認。名称からは対応を推定できなかったシート族が {len(not_inspected)} 件ある（{'、'.join(f['family'] for f in not_inspected)}）。",
         "- 検証はすべて架空データ。**実建物での精度、他のツールとの一致は検証していない。**",
         "- 計算の重さは独立に実装した基準計算との比較で、原版ブックの計算時間がどれだけ変わるかは分からない。",
         "- 基準計算の定義には、本研究が決めた規約（端数年の按分、事象の年への帰属、更新年の修繕の除外、記述子と年次表のどちらを正とするか、使えない係数の行の扱いなど）が含まれる。"
         "規約を変えると結果が変わるものは [06_OPEN_ISSUES](06_OPEN_ISSUES/README.md) に、影響の大きさとともに挙げた。",
         f"- {AGENTS}", "",
         "## 成果物", "",
         table(["成果物", "場所"], [
             ["1 全計算式・式群の分類台帳", "[01_LEDGER/](01_LEDGER/README.md)"],
             ["2 評価軸 A のランキング", "[02_RANKING/](02_RANKING/README.md)"],
             ["3 評価軸 B のランキング", "[02_RANKING/](02_RANKING/README.md)"],
             ["4 研究対象と着手順序", "[02_RANKING/](02_RANKING/README.md)"],
             ["5 検討した近似式・統合モデル", "[03_MODELS/](03_MODELS/README.md)、[導出](03_MODELS/DERIVATIONS.md)"],
             ["6 基準計算との誤差と処理時間", "[04_VERIFICATION/](04_VERIFICATION/README.md)、[独立した検査](04_VERIFICATION/INDEPENDENT_REVIEW.md)"],
             ["7 採用・不採用・検証保留の理由、進捗台帳", "[05_DECISIONS/](05_DECISIONS/README.md)、[PROGRESS.md](05_DECISIONS/PROGRESS.md)"],
             ["8 統合前後の数式数と計算負荷", "[05_DECISIONS/](05_DECISIONS/README.md)"],
             ["9 未解決事項と必要なデータ", "[06_OPEN_ISSUES/](06_OPEN_ISSUES/README.md)"],
             ["次段階の材料分類の構造調査", "[07_MATERIAL_TAXONOMY/](07_MATERIAL_TAXONOMY/README.md)"],
             ["検算用コード（製品コードではない）", "[research_code/](research_code/README.md)"],
         ])]
    write("README.md", "\n".join(t))


def main() -> int:
    overview_report()
    ledger_report()
    ranking_report()
    models_report()
    verification_report()
    decisions_report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
