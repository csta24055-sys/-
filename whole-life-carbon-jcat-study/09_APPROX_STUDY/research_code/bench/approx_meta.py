"""Declarations of the approximate candidates: what each one is and what it was measured on.

This table is the single source of the unit attachment of a candidate:

    scope              UNIT      the candidate uses the unit's own formula (with one step replaced)
                                 and is measured on the unit's own output;
                       STAGE     it is measured only on a stage total or on a sum of several units;
                       BUILDING  it does not use the unit's formula at all (floor-area intensity,
                                 regression of the total).
    units              exactly the units on whose OWN output the candidate was measured
                       (``bench.approx_study`` refuses to write a result in which this list and the
                       measured ``by_unit`` keys differ);
    units_stage_level  further units the candidate says something about only through a stage
                       total or a sum of several units.

Evidence of a record (unit, candidate): BUILDING when the candidate's scope is BUILDING, else
UNIT for ``units`` and STAGE for ``units_stage_level``.

``parameters_from`` says where representative parameters come from: the evaluated building
itself (in-sample: best case, no input is saved), other buildings (train/test split), or
None when the candidate only changes a formula.
"""
from __future__ import annotations

import re

IN_SAMPLE = "same building (in-sample)"
SPLIT = "other buildings (train/test split)"

SAME_INPUTS = "入力は厳密な式と同じで、減らない。"
NO_ROWS = "資材の行に作用する候補ではない。"
LOAD_NOT_THE_REASON = "負荷は測っていない。この候補の不採用・保留の理由は誤差または入力の入手であり、計算負荷ではない。"
LEAF = "NONE"                    # the changed quantity is not reused by another stage: the local total is the whole effect
PROPAGATED = "PROPAGATED"        # reused downstream, and the reference was re-run with the approximated input
NOT_PROPAGATED = "NOT_PROPAGATED"  # reused downstream, but the candidate gives nothing that could be handed on


def _d(title, replaces, stage, step, units, **more):
    out = {"title": title, "replaces": replaces, "stage": stage, "step": step, "units": list(units),
           "scope": "UNIT", "units_stage_level": [], "parameters_from": None, "downstream_reuse": LEAF}
    out.update(more)
    return out


COUNT_UNITS = ["B4-01", "B4-03", "B4-02", "X-08", "B5-01", "X-10"]
ELEC_NOTE = ("段階 B6 は X-02 の値（B6-03 − B2-01）、段階 B2 は B2-01。従来「B6 段階」として公表していた値は "
             "B6-03（= B6＋B2）に対するもので、other_targets に「B6-03（= B6＋B2）」として残した。")
AP15_UNITS = ["X-02", "SUM-01", "SUM-02", "SUM-03", "A5-04", "B2-01", "B3-01", "B4-02", "B5-01", "B7-04", "C1-01", "C2-01", "C4-01"]
AP15_STAGE_LEVEL = ["A13-01", "A13-03", "A13-04", "X-01", "A4-01", "A4-02", "A5-01", "A5-02", "A5-03", "B1-02", "B1-03",
                    "B1-04", "B6-01", "B6-02", "B6-03", "B7-01", "B7-02", "B7-03", "C3-01", "X-14"]

DECL = {
    "AP-01": _d("更新回数の連続近似 N ≈ max(0, T/c − 1)", "回数関数 N(T,c)", "B4", "M3", COUNT_UNITS, inputs_text=SAME_INPUTS),
    "AP-02": _d("更新回数の中点補正 N ≈ max(0, T/c − 1/2)", "回数関数 N(T,c)", "B4", "M3", COUNT_UNITS, inputs_text=SAME_INPUTS),
    "AP-03": _d("更新回数の切り捨てなし N ≈ T/c", "回数関数 N(T,c)", "B4", "M3", COUNT_UNITS, inputs_text=SAME_INPUTS),
    "AP-04": _d("修繕の更新年除外を無視（B3-02 で B3-01 を代用）", "修繕の年次積算", "B3", "M3", ["B3-01", "B3-02"],
                units_note="B3-02 は候補そのもので、B3-02 の出力を B3-01 の値と比べた（B3-02 の出力を近似したのではない）。",
                inputs_unit="修繕の計算に使う行ごとの更新周期・更新年一覧の数（1 シナリオ当たりの平均）",
                inputs_text="修繕の計算に行ごとの更新周期（または更新年一覧）が要らなくなる。初期排出と修繕率は同じ。"),
    "AP-05a": _d("冷媒の線形近似 1−(1−r)^k ≈ r·k（整合的な形：充填サイクル k 年の漏洩 m0·r·k、交換前・廃棄時の残存量 m0·max(0, 1−r·k)）",
                 "充填サイクルの閉形式", "B1", "M3", ["B1-02", "B1-03", "B1-04"], inputs_text=SAME_INPUTS,
                 no_class_reason="冷媒機器に作用し、資材の行に作用しない。"),
    "AP-05b": _d("冷媒：すべての機器を毎年補充する機器として扱う（漏洩 m0·r·T、交換前・廃棄時の残存量は初期充填量 m0）",
                 "充填サイクルの閉形式", "B1", "M3", ["B1-02", "B1-03", "B1-04"], inputs_text=SAME_INPUTS,
                 renamed_from="AP-05", no_class_reason="冷媒機器に作用し、資材の行に作用しない。",
                 note="これまで AP-05「冷媒漏洩の線形近似」として公表していた値は、この変種のものである。"),
    "AP-06": _d("端材倍率の線形化 1/(1−w) ≈ 1+w", "発注量の算出", "A1-A3", "M3", ["A13-05"], inputs_text=SAME_INPUTS,
                downstream_reuse=PROPAGATED,
                propagation_how="端材率を w' = w/(1+w) に書き換えて基準計算をやり直す（発注量が Q(1+w) になり、据付量は変わらない）。"),
    "AP-06b": _d("端材の再使用を考慮した正味発注量の線形化 1 + w(1−ρ)/(1−w) ≈ 1 + w(1−ρ)", "正味発注量の算出",
                 "X-13 の行ごとの正味発注量", "M3", ["X-13"], inputs_text=SAME_INPUTS,
                 no_class_reason="行ごとの数量（単位が行によって違う）の誤差を集めたもので、区分ごとの合計を作れない。"),
    "AP-07a": _d("複合係数：質量比 5％ 未満の構成材を切り捨てる（補正なし）", "複合係数の加重和", "複合品の製造排出（X-03）", "M3",
                 ["A13-02", "X-03"], downstream_reuse=PROPAGATED,
                 inputs_unit="複合品 1 行当たりの構成材の数（平均）",
                 inputs_text="質量比 5％ 未満の構成材の係数が要らなくなる。",
                 propagation_how="質量比 5％ 未満の構成材の係数を、値 0 の架空の係数に差し替えて基準計算をやり直す（質量比は変えない）。"),
    "AP-07b": _d("複合係数：質量比 5％ 未満の構成材を切り捨て、残りの比率を合計 1 に補正", "複合係数の加重和", "複合品の製造排出（X-03）", "M3",
                 ["A13-02", "X-03"], downstream_reuse=PROPAGATED,
                 inputs_unit="複合品 1 行当たりの構成材の数（平均）",
                 inputs_text="質量比 5％ 未満の構成材の係数が要らなくなる。",
                 propagation_how="質量比 5％ 未満の構成材を除き、残りの質量比を合計 1 に直して基準計算をやり直す。"),
    "AP-08": _d("買電排出を 平均買電量×平均係数×T で近似", "買電量×係数の年次積算", "B6", "M3", ["B6-01", "B6-03", "B2-01"],
                units_stage_level=["B6-04"], parameters_from=IN_SAMPLE, stage_note=ELEC_NOTE,
                units_note="B6-04（買電量）の式は変えず、その出力の平均を使うだけなので、B6-04 自身の出力では測っていない。",
                inputs_unit="買電排出の計算に要る数値の数（消費・発電・売電・電力係数。記述子なら記述子の項目数、年次表なら年数分。1 シナリオ当たりの平均）",
                inputs_text="平均買電量と平均係数の 2 つで済むが、ここではその平均を同じ建物の年次の値から作っている（入力は減っていない）。",
                no_class_reason="買電に作用し、資材の行に作用しない。"),
    "AP-09a": _d("電力係数を 5 年ごとの点の直線補間で持つ（全種類の系列に適用）", "年次の電力係数系列", "B6", "M3", ["X-06"],
                 stage_note=ELEC_NOTE, inputs_unit="電力係数の入力の数（記述子なら記述子の項目数、年次表なら年数分。1 シナリオ当たりの平均）",
                 inputs_text="記述子で与えられる系列では、補間の点のほうが記述子より多い。", no_class_reason="電力係数に作用し、資材の行に作用しない。"),
    "AP-09b": _d("電力係数を 10 年ごとの点の直線補間で持つ（全種類の系列に適用）", "年次の電力係数系列", "B6", "M3", ["X-06"],
                 stage_note=ELEC_NOTE, inputs_unit="電力係数の入力の数（記述子なら記述子の項目数、年次表なら年数分。1 シナリオ当たりの平均）",
                 inputs_text="記述子で与えられる系列では、補間の点のほうが記述子より多い場合がある。", no_class_reason="電力係数に作用し、資材の行に作用しない。"),
    "AP-09c": _d("併用：パラメータ型の系列は厳密な閉形式、年次表の系列だけ 5 年ごとの点の直線補間", "年次の電力係数系列", "B6", "M6",
                 ["X-06", "B6-01"], stage_note=ELEC_NOTE, inputs_unit="年次表で与えられる電力係数の値の数（1 シナリオ当たりの平均）",
                 inputs_text="年数分の値が、5 年ごとの値と最終年の値に減る。", no_class_reason="電力係数に作用し、資材の行に作用しない。"),
    "AP-10": _d("6 区分の要約数量×（構造×用途ごとの代表係数）で資材製造を概算", "資材製造の全行計算", "A1-A3（資材分：A13-01＋A13-03）", "M4",
                ["X-17"], units_stage_level=["A13-01", "A13-03"], parameters_from=SPLIT, downstream_reuse=NOT_PROPAGATED,
                units_note="A13-01 と A13-03 は、2 つの合計（資材製造）でしか測れない（候補は行を持たず、EPD の行と汎用係数の行を分けられない）。",
                inputs_unit="資材製造に要る数量の入力の数（厳密：資材の行数。候補：要約数量 6 個。1 シナリオ当たりの平均）",
                inputs_text="行ごとの数量と係数の代わりに、要約数量 6 個と、外から与える代表係数 6 個を使う。",
                no_class_reason="要約数量の 6 区分で計算する候補で、資材区分（13 区分）には分けられない。6 区分ごとの誤差は by_summary_class にある。"),
    "AP-10b": _d("AP-10 に、6 区分に入らない資材の分の割増（構造×用途ごとの平均比）を掛ける", "資材製造の全行計算", "A1-A3（資材分：A13-01＋A13-03）", "M4",
                 [], scope="STAGE", units_stage_level=["X-17", "A13-01", "A13-03"], parameters_from=SPLIT, downstream_reuse=NOT_PROPAGATED,
                 variant_of="AP-10",
                 units_note="A13-01 と A13-03 の合計（資材製造の全体）でしか測っていない。割増は 6 区分の外の資材の分なので、X-17 の出力（6 区分の合計）とは比べていない"
                            "（X-17 自身の出力に対する誤差は AP-10 に記載）。",
                 inputs_unit="資材製造に要る数量の入力の数（厳密：資材の行数。候補：要約数量 6 個。1 シナリオ当たりの平均）",
                 inputs_text="行ごとの数量と係数の代わりに、要約数量 6 個と、外から与える代表係数 6 個・割増 1 個を使う。",
                 no_class_reason="要約数量の 6 区分で計算する候補で、資材区分（13 区分）には分けられない。"),
    "AP-11": _d("延床面積×評価年数×（構造×用途ごとの平均原単位）でホールライフ合計を概算", "全段階の計算", "WLC", "M5",
                ["SUM-03", "SUM-04", "SUM-05"], scope="BUILDING", units_stage_level=["X-02"], parameters_from=SPLIT, downstream_reuse=None,
                units_note="X-02（段階ベクトル）は、合計を通じてしか測っていない（候補は段階別の値を出さない）。",
                inputs_unit="建物ごとの入力の件数（厳密：資材・設備・冷媒の行数。ほかに運用の年次量などがある。候補：面積・年数・構造・用途の 4 個。1 シナリオ当たりの平均）",
                inputs_text="面積・評価年数・構造・用途の 4 つと、外から与える原単位 1 個。", no_class_reason="建物全体の代理モデルで、資材の行を使わない。"),
    "AP-12": _d("併用：質量上位 20％ の資材行だけ詳細計算し、残りを質量比で補う", "資材製造の全行計算", "A1-A3（資材分：A13-01＋A13-03）", "M6",
                ["A13-01", "A13-03"], parameters_from=IN_SAMPLE, downstream_reuse=NOT_PROPAGATED,
                inputs_unit="数量と係数を詳細に入力する資材の行数（1 シナリオ当たりの平均。候補でも全行の質量は要る）",
                inputs_text="数量と係数が要るのは質量上位 20％ の行だけになるが、全行の質量が要る。"),
    "AP-13": _d("面積当たり電力使用量による買電排出の推定（X-11）で実績計算を代用", "買電排出の年次積算", "B6", "M4", ["B6-01", "X-11"],
                stage_note=ELEC_NOTE,
                units_note="X-11 は候補そのもので、X-11 の出力を B6-01 の年重み付き合計と比べた（X-11 の出力を近似したのではない）。",
                parameters_note="面積当たり使用量は、その建物の入力値（宣言値）で、母集団から推定した値ではない。",
                inputs_unit="買電量の計算に要る数値の数（厳密：消費・発電・売電の記述子の項目数または年数分。候補：延床面積と面積当たり使用量の 2 個。1 シナリオ当たりの平均）",
                inputs_text="消費量・発電量・売電量の系列の代わりに、延床面積と面積当たり使用量の 2 つを使う（電力係数はどちらも要る）。",
                no_class_reason="買電に作用し、資材の行に作用しない。"),
    "AP-14": _d("評価期間 T=60 の合計を、同じ建物の T=50 と T=75 の結果からの直線補間で求める", "評価期間ごとの再計算", "WLC", "M3", ["SUM-03"],
                downstream_reuse=None, inputs_text="入力は同じ。別の評価期間 2 つの計算結果が要る。", no_class_reason="合計に作用し、資材の行に作用しない。",
                load_reason="命令数は測っていない。候補は別の評価期間 2 つ（T=50・75）の計算を使うので、求める評価期間の計算 1 回より計算は多い（回数の比較であり、測定ではない）。"),
    "AP-15": _d("段階ごとに 延床面積（使用段階は×評価年数）×（構造×用途ごとの平均原単位）で概算する共通近似モデル", "各段階の詳細計算",
                "WLC（段階別は by_stage）", "M4", AP15_UNITS, scope="BUILDING", units_stage_level=AP15_STAGE_LEVEL, parameters_from=SPLIT,
                downstream_reuse=None,
                units_note="units は、出力が段階の値そのもの（または段階の値の和）である単位。units_stage_level は、2 つ以上の単位からなる段階の値を通じてしか測っていない単位。"
                           "どの単位についても、候補はその単位の式を使わない。",
                inputs_unit="建物ごとの入力の件数（厳密：資材・設備・冷媒の行数。ほかに運用の年次量などがある。候補：面積・年数・構造・用途の 4 個。1 シナリオ当たりの平均）",
                inputs_text="面積・評価年数・構造・用途の 4 つと、外から与える段階別の原単位 14 個。", no_class_reason="建物全体の代理モデルで、資材の行を使わない。"),
    "AP-16": _d("ホールライフ合計の対数線形回帰（延床面積・評価年数・構造・用途）", "全段階の計算", "WLC", "M5", ["SUM-03", "SUM-04", "SUM-05"],
                scope="BUILDING", units_stage_level=["X-02"], parameters_from=SPLIT, downstream_reuse=None,
                units_note="X-02（段階ベクトル）は、合計を通じてしか測っていない（候補は段階別の値を出さない）。",
                inputs_unit="建物ごとの入力の件数（厳密：資材・設備・冷媒の行数。ほかに運用の年次量などがある。候補：面積・年数・構造・用途の 4 個。1 シナリオ当たりの平均）",
                inputs_text="面積・評価年数・構造・用途の 4 つと、外から与える回帰係数。", no_class_reason="建物全体の代理モデルで、資材の行を使わない。"),
    "AP-17": _d("輸送：輸送手段ごとに 合計質量×単純平均距離 で求める", "行ごとの質量×距離", "A4", "M3", ["A4-01", "X-12", "C2-01"],
                parameters_from=IN_SAMPLE, downstream_reuse=PROPAGATED,
                inputs_unit="輸送距離の入力の数（厳密：質量距離で運ぶ行ごとに 1 個。候補：輸送手段ごとに 1 個。1 シナリオ当たりの平均）",
                inputs_text="行ごとの距離の代わりに輸送手段ごとの平均距離 1 個を使うが、ここではその平均を同じ建物の行から作っている（行ごとの質量は要る）。",
                propagation_how="質量距離で運ぶ行（A4-01）の距離を、その輸送手段の単純平均距離に書き換えて基準計算をやり直す（搬出 C2 の距離は変えない）。"),
    "AP-18a": _d("区分パラメータ：資材区分ごとに代表更新周期（更新 1 回の排出で重み付けした調和平均）を 1 つ持つ", "行ごとの更新周期", "B4", "M4",
                 ["B4-01", "B4-02", "B4-03", "X-08"], parameters_from=IN_SAMPLE,
                 inputs_unit="更新周期の入力の数（厳密：周期で更新する行ごとに 1 個。候補：区分ごとに 1 個。1 シナリオ当たりの平均）",
                 inputs_text="行ごとの周期の代わりに区分ごとの代表周期を使うが、ここではその代表値を同じ建物の行から作っている（入力は減っていない）。"),
    "AP-18b": _d("区分パラメータ：資材区分ごとに代表修繕率（初期排出で重み付けした平均）と代表更新周期を持つ", "行ごとの修繕率と更新周期", "B3", "M4",
                 ["B3-01"], parameters_from=IN_SAMPLE,
                 inputs_unit="修繕率と更新周期の入力の数（厳密：行ごとに 2 個。候補：区分ごとに 2 個。1 シナリオ当たりの平均）",
                 inputs_text="行ごとの修繕率と周期の代わりに区分ごとの代表値を使うが、ここではその代表値を同じ建物の行から作っている（入力は減っていない）。"),
    "AP-18c": _d("区分パラメータ：資材区分ごとに処理経路の比率（単純平均）と経路係数（単純平均）を持ち、行は質量だけにする", "行ごとの経路比率と係数",
                 "C3-01＋C4-01（資材のみ。段階 C3 に入る設備の廃棄 X-14 を含まない）", "M4", ["C3-01", "C4-01", "X-09"], parameters_from=IN_SAMPLE,
                 downstream_reuse=PROPAGATED,
                 stage_note="従来「C3＋C4」と表示していた量。段階 C3（C3-01＋X-14）と段階 C4（C4-01）に対する誤差は by_stage にある。",
                 inputs_unit="経路の比率と経路の係数の入力の数（厳密：行ごと・経路ごとに 2 個。候補：区分ごと・経路ごとに 2 個。1 シナリオ当たりの平均）",
                 inputs_text="行ごとの経路比率と係数の代わりに区分ごとの代表値を使うが、ここではその代表値を同じ建物の行から作っている（入力は減っていない）。",
                 propagation_how="各行の経路の比率を区分の単純平均に、経路の係数を区分の単純平均の値を持つ架空の係数に書き換えて基準計算をやり直す。"),
    "AP-18d": _d("AP-18b の区分パラメータ（代表修繕率・代表更新周期）を、他の建物（構造×用途ごと）から与える", "行ごとの修繕率と更新周期", "B3", "M4",
                 ["B3-01"], parameters_from=SPLIT, variant_of="AP-18b",
                 inputs_unit="修繕率と更新周期の入力の数（厳密：行ごとに 2 個。候補：0 個（外から与える）。区分ごとの初期排出は要る。1 シナリオ当たりの平均）",
                 inputs_text="建物ごとに要るのは区分ごとの初期排出の合計だけで、修繕率と周期は外から与える。"),
    "AP-18": _d("区分パラメータによる共通近似モデル（AP-18a〜c を同時に適用）", "行ごとのライフサイクル条件",
                "B3＋B4＋C3-01＋C4-01（設備の廃棄 X-14 を含まない）", "M4", ["B3-01", "B4-02", "C3-01", "C4-01"], parameters_from=IN_SAMPLE,
                downstream_reuse=NOT_PROPAGATED,
                stage_note="従来「B3＋B4＋C3＋C4」と表示していた量。段階ごとの誤差は by_stage にある。",
                propagation_reason="AP-18a・b・c を、それぞれの量に局所に当てはめて足した値である。AP-18c の経路パラメータを更新 1 回の排出（B4）と建替（B5）にも使う形では測っていない"
                                   "（AP-18c 単独の波及は AP-18c に記載）。",
                inputs_unit="更新周期・修繕率・経路の比率と係数の入力の数（AP-18a〜c の合計。1 シナリオ当たりの平均）",
                inputs_text="AP-18a〜c と同じ。代表値は同じ建物の行から作っている（入力は減っていない）。",
                no_class_reason="AP-18a・AP-18b・AP-18c の区分別の誤差を、それぞれの候補に記載した。"),
    "AP-19a": _d("未数量分：行ごとの比率の代わりに単純平均の比率 1 つを使う", "行ごとの上乗せ倍率", "未数量分（A13-04）", "M3", ["A13-04"],
                 parameters_from=IN_SAMPLE, keeps_row_membership=True, downstream_reuse=PROPAGATED,
                 inputs_unit="未数量費用比率の入力の数（厳密：比率を持つ行ごとに 1 個。候補：1 個。1 シナリオ当たりの平均）",
                 inputs_text="比率は 1 個になるが、どの行が比率を持つかは行ごとの情報をそのまま使い、平均も同じ建物の行から作っている。",
                 propagation_how="比率を持つ行の比率を、その単純平均に書き換えて基準計算をやり直す。"),
    "AP-19b": _d("未数量分：行ごとの比率の代わりに最大の比率 1 つを使う（安全側）", "行ごとの上乗せ倍率", "未数量分（A13-04）", "M3", ["A13-04"],
                 parameters_from=IN_SAMPLE, keeps_row_membership=True, downstream_reuse=PROPAGATED,
                 inputs_unit="未数量費用比率の入力の数（厳密：比率を持つ行ごとに 1 個。候補：1 個。1 シナリオ当たりの平均）",
                 inputs_text="比率は 1 個になるが、どの行が比率を持つかは行ごとの情報をそのまま使い、最大値も同じ建物の行から取っている。",
                 propagation_how="比率を持つ行の比率を、その最大値に書き換えて基準計算をやり直す。"),
    "AP-19c": _d("未数量分：資材の全行に、全行の単純平均の比率 1 つを使う（どの行が比率を持つかを使わない）", "行ごとの上乗せ倍率", "未数量分（A13-04）", "M3",
                 ["A13-04"], parameters_from=IN_SAMPLE, keeps_row_membership=False, downstream_reuse=PROPAGATED, variant_of="AP-19a",
                 inputs_unit="未数量費用比率の入力の数（厳密：比率を持つ行ごとに 1 個。候補：1 個。1 シナリオ当たりの平均）",
                 inputs_text="比率は 1 個で、どの行が比率を持つかも要らない。平均は同じ建物の行から作っている。",
                 propagation_how="資材の全行の比率を、全行の単純平均（比率を持たない行は 0 として平均）に書き換えて基準計算をやり直す。"),
    "AP-20": _d("併用：点推定の代わりに上下限 Σu·max(0,T/c−1) ≤ B4 ≤ Σu·T/c を使う（下限は時間境界の許容差（相対 1e-9）の範囲で成り立つ。明示の更新年一覧は厳密）",
                "回数関数 N(T,c)", "B4", "M6", ["B4-02"], inputs_text=SAME_INPUTS,
                no_class_reason="上下限を段階 B4 の合計で測った。区分ごとには測っていない。"),
    "AP-21": _d("木材の炭素貯蔵：数量×（構造×用途ごとの平均の m3 当たり貯蔵量）", "密度×炭素含有率の入力", "STO-01（参考値）", "M3", ["STO-01"],
                parameters_from=SPLIT, downstream_reuse=None,
                inputs_text="木材の数量だけで済み、密度と炭素含有率の 2 つが要らなくなる（m3 当たり貯蔵量は外から与える）。入力の数は式から決まり、シナリオから数えたものではない。",
                no_class_reason="参考値（木材の要約数量）に作用し、資材の行に作用しない。"),
    "AP-22a": _d("全ガスの合計を CO2 のみの合計で代用する", "ガス別の合算", "対象段階の合計", "M3", ["X-04"], downstream_reuse=None,
                 inputs_unit="使った係数のガス別の量の数（厳密：係数ごとにガスの数だけ。候補：係数ごとに CO2 の 1 個。1 シナリオ当たりの平均）",
                 inputs_text="係数ごとに CO2 の量だけで済む。", no_class_reason="係数のガス別の量に作用し、資材の行だけに作用する候補ではない。"),
    "AP-22b": _d("CO2 のみの合計 = 全ガスの合計 ×（構造×用途ごとの平均の CO2 比）", "CO2 版の並行算定", "CO2 のみの合計（X-05）", "M3", ["X-05"],
                 parameters_from=SPLIT, downstream_reuse=None,
                 inputs_unit="使った係数の CO2 の量の数（厳密：係数ごとに 1 個。候補：外から与える比 1 個。1 シナリオ当たりの平均）",
                 inputs_text="係数ごとの CO2 の量が要らなくなり、外から与える CO2 比 1 個で済む。", no_class_reason="係数のガス別の量に作用し、資材の行だけに作用する候補ではない。"),
    "AP-23a": _d("修繕：更新年の除外を連続近似で置き換える。修繕年数 = T − min(T, max(0, T/c − 1))（行ごと。明示の更新年一覧は厳密）", "修繕の年次積算", "B3", "M3",
                 ["B3-01"], inputs_text=SAME_INPUTS),
    "AP-23b": _d("区分パラメータ：資材区分ごとに Σe0·r と、e0·r で重み付けした調和平均の周期 c̃ を持ち、修繕年数 = T − min(T, max(0, T/c̃ − 1)) とする"
                 "（明示の更新年一覧は厳密）", "行ごとの修繕率と更新周期", "B3", "M4", ["B3-01"], parameters_from=IN_SAMPLE, variant_of="AP-23a",
                 inputs_unit="修繕率と更新周期の入力の数（厳密：行ごとに 2 個。候補：区分ごとに 2 個。1 シナリオ当たりの平均）",
                 inputs_text="行ごとの修繕率と周期の代わりに区分ごとの 2 つの値を使うが、ここではその値を同じ建物の行から作っている（入力は減っていない）。"
                             "評価期間より長い周期の行が区分にないとき、行ごとの形（AP-23a）と同じ値になる。"),
    "AP-23c": _d("AP-23b の区分パラメータ（代表修繕率と調和平均の周期）を、他の建物（構造×用途ごと）から与える", "行ごとの修繕率と更新周期", "B3", "M4",
                 ["B3-01"], parameters_from=SPLIT, variant_of="AP-23b",
                 inputs_unit="修繕率と更新周期の入力の数（厳密：行ごとに 2 個。候補：0 個（外から与える）。区分ごとの初期排出は要る。1 シナリオ当たりの平均）",
                 inputs_text="建物ごとに要るのは区分ごとの初期排出の合計だけで、修繕率と周期は外から与える（明示の更新年一覧を持つ設備は行ごとに厳密）。"),
    "AP-24a": _d("併用：年次表で与えられる燃料・水・廃棄物の年次量を、5 年ごとの値の直線補間で持つ（記述子で与えられる量は厳密な閉形式）", "年次表の年ごとの値",
                 "B6-02＋B7-04（燃料・水・廃棄物の年次量による排出の合計）", "M6", ["B6-02", "B7-01", "B7-02", "B7-03"],
                 stage_note="段階 B7（上水・下水・一般廃棄物）と段階 B6（燃料。買電は変えない）に対する誤差を by_stage に、単位ごとの年重み付き合計に対する誤差を by_unit に記載した。"
                            "年次表で与えられる量が 1 つもないシナリオは厳密なので、誤差の集計に入れていない（n_scenarios_computed_exactly）。",
                 inputs_unit="年次表で与えられる年次量の値の数（1 シナリオ当たりの平均。年次表の量を持つシナリオだけ）",
                 inputs_text="年数分の値が、5 年ごとの値と最終年の値に減る。", no_class_reason="運用の年次量に作用し、資材の行に作用しない。"),
    "AP-24b": _d("併用：年次表で与えられる電力の消費量・発電量・売電量を、5 年ごとの値の直線補間で持つ（記述子で与えられる量は厳密）", "年次表の年ごとの値",
                 "B6", "M6", ["B6-04", "B6-01"], stage_note="段階 B6 は X-02 の値（B6-03 − B2-01）、段階 B2 は B2-01。",
                 inputs_unit="年次表で与えられる電力の年次量の値の数（1 シナリオ当たりの平均。年次表の量を持つシナリオだけ）",
                 inputs_text="年数分の値が、5 年ごとの値と最終年の値に減る。", no_class_reason="運用の年次量に作用し、資材の行に作用しない。",
                 load_reason="命令数は測っていない。粗い表から年ごとの値を作り直して走査する点は AP-24a と同じで、買電量の打ち切り max(0, …) があるため年ごとの評価は残る。"),
}


def order_key(cid: str):
    """Natural order of candidate ids: AP-05a < AP-05b < AP-06 < AP-06b < AP-10."""
    m = re.fullmatch(r"AP-(\d+)([a-z]?)", cid)
    return (int(m.group(1)), m.group(2))


def evidence_scope(decl: dict) -> dict:
    """Evidence level of each (unit, candidate) record implied by the declaration."""
    if decl["scope"] == "BUILDING":
        return {u: "BUILDING" for u in decl["units"] + decl["units_stage_level"]}
    out = {u: "UNIT" for u in decl["units"]}
    out.update({u: "STAGE" for u in decl["units_stage_level"]})
    return out
