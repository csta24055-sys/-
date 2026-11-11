#!/usr/bin/env python3
"""Build the research records: one conclusion for every evaluation unit and every method step.

The plan below says, for each unit and each step M1..M6, what was examined. Where a
measurement exists the record is checked against it, and the build fails otherwise:

  exact records (EX)   the unit's outputs equal the reference in
                       04_VERIFICATION/unified_model_exactness.json, AND the mechanism the
                       title states is asserted on the counters the unified model reports
                       ("mechanism_counts" in the same file), AND the cited derivation exists
                       in 03_MODELS/DERIVATIONS.md
  approximate (AP)     the declared conclusion is asserted against the measured statistics
                       in 04_VERIFICATION/approximation_study.json
  reasoned out (NA)    no measurement: the reason is an argument, and the record says so
                       (verification NOT_VERIFIED)

A unit counts as unified (M2) only when its value is read from a shared table or is
produced by a shared parameterised function of the unified model.

Outputs
    03_MODELS/models.json                 the unified models
    03_MODELS/candidates.json             approximate candidates with measured errors and conclusions
    03_MODELS/records/units.json          one record per (unit, step, candidate)
    03_MODELS/judge_proposal_trace.json   what became of the proposals of the axis-B judges

Run:  cd research_code && python3 -m tools.build_records
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

STUDY = Path(__file__).resolve().parents[2]
EXACT = STUDY / "04_VERIFICATION" / "unified_model_exactness.json"
APPROX = STUDY / "04_VERIFICATION" / "approximation_study.json"
UNITS = STUDY / "01_LEDGER" / "units.json"
AXIS_B = STUDY / "02_RANKING" / "axis_b.json"
OUT = STUDY / "03_MODELS"
DERIVATIONS = OUT / "DERIVATIONS.md"

MODELS = {
    "K1": {"name": "行テーブル",
           "form": "値 = Σ_k A[表,k]·v_k,  A[表,k] = Σ_行 (活動量 × 行の乗数)   （k は係数キー）",
           "idea": "排出を「表・係数キー・活動量」の行として 1 回の走査で表に足し込み、値は表ごとに 活動量×係数 の和として読む。"
                   "段階合計・ガス別内訳・CO2 のみの結果・区分別や経路別の集計は、同じ表の読み方（集約キーと係数の列）を変えるだけで得られる。"
                   "参考値（段階合計に入れない量）も、参考値のタグを付けた表として同じ形に載る。",
           "kept": "係数の対象段階と単位の検査、択一の規則（EPD と汎用、質量距離法と数量法）、参考値を合計に入れない規則",
           "derivation": "D1"},
    "K2": {"name": "回数関数とライフサイクル乗数",
           "form": "N(T,c) = #{n≥1 : n·c が評価期間の内側};  更新 = Σ_c N(T,c)·U_c,  修繕 = Σ_c (T − 除外年の重み)·R_c,  建替 = N(T,C)·φ·(初期段階の和)",
           "idea": "更新年の一覧を作らず回数を求め、行ごとではなく周期の値ごとに合算した活動量（U_c、R_c、質量）に掛ける。この合算は評価期間 T に依存しないので、"
                   "T を変えても乗数を計算し直すだけでよい。",
           "kept": "評価期間の終わりちょうどの更新を数えない規約（判定の許容幅を含む）、明示の更新年一覧の優先、端数年の重み",
           "derivation": "D2・D3・D4"},
    "K3": {"name": "年重み付き和（区分的に直線な系列のモーメント）",
           "form": "Σ_y w_y·(b + s·k) = b·T + s·(等差級数);  G = Σ_y w_y·g_y,  H = Σ_y w_y·k·g_y;  買電排出 = B·G + S·H（打ち切りが働かないとき）",
           "idea": "年ごとの積算を、一定・直線の年次量と、区分的に直線な電力係数（一定・直線低下・段階を 1 つの形で表す）の和の公式に置き換える。",
           "kept": "端数年の按分、自家消費の打ち切り max(0,·)（働く場合は年ごとに計算）、年次表は走査、記述子と年次表が食い違う入力の報告",
           "derivation": "D5"},
    "K4": {"name": "充填サイクルの質量収支",
           "form": "補充なし：サイクル j 年の漏洩 = m·(1 − (1−r)^j);  補充あり：m0·r·T;  交換時損失・廃棄時未回収は残存量から",
           "idea": "冷媒の残存量を年ごとに更新する代わりに、交換から交換までを 1 サイクルとして等比の閉形式で求める。",
           "kept": "交換が属する年の年末に反映する規約、端数年の按分、B1 への帰属",
           "derivation": "D6"},
    "K5": {"name": "指標（段階ベクトルの線形関数）",
           "form": "指標 = (段階ベクトルの一部の和) ÷ 尺度（1、面積、面積×年数、1000、合計）;  比較 = 差と比",
           "idea": "アップフロント・エンボディド・ホールライフ・原単位・割合・基準案との差を、段階ベクトルから 1 か所で求める。",
           "kept": "対象段階の指定、面積・年数が無効なら算出しない規則、B2 が対象外のとき B6 に戻す規則",
           "derivation": "D7"},
    "K6": {"name": "許容差つきの残差判定",
           "form": "合格 ⇔ |残差| ≤ 許容差 × 尺度",
           "idea": "面積の整合（SYS-04・QA-04）と段階合計の突合（QA-01）は、残差と許容差が違うだけの同じ判定関数。残差は 1 回だけ求める。",
           "kept": "それぞれの許容差（1e-9、1e-6）と尺度",
           "derivation": "D7"},
    "K7": {"name": "係数解決の表",
           "form": "係数・対象段階・単位の組ごとに 1 回解決;  複合係数 Σ(質量比×換算×係数) は配合の内容ごとに 1 回",
           "idea": "行ごとに繰り返していた係数の検索、適用可否の判定、単位換算、複合係数の算出を、相異なる組の数だけに減らし、検査（単位・段階・参照・使用係数）も同じ表から読む。",
           "kept": "使用許諾・対象段階・単位・EPD の適用条件、質量比の合計の検査、換算の根拠",
           "derivation": "D8"},
}

# ---- mechanisms: what a record may claim about HOW the unified model computes, and the counter that proves it -------
def mechanism_checks(exact: dict) -> dict:
    mc = exact["mechanism_counts"]
    par, tab = mc["parametric_inputs"], mc["year_table_inputs"]
    rows = par["rows"]["materials"] + par["rows"]["equipment"]
    t, f, d = par["totals_only"], par["full_outputs"], par["distinct"]
    return {
        "M-ROWPROD": (t["row_factor_products"] == 0 and tab["totals_only"]["row_factor_products"] == 0 and f["row_factor_products"] == rows,
                      f"合計のみの出力では行ごとの係数の乗算が 0 回（行別の出力を求めると {f['row_factor_products']} 回＝行数）。"
                      f"表の値の読み出しで行う乗算は {t['table_factor_products']} 回で、行数ではなく表の項目数で決まる"),
        "M-EVENTS": (t["event_lists_built"] == 0 and f["event_lists_built"] > 0,
                     f"合計のみの出力では更新年の一覧を 1 つも作らない（一覧の出力を求めると {f['event_lists_built']} 個）"),
        "M-YEARLOOP": (t["year_loop_iterations"] == 0 and tab["totals_only"]["year_loop_iterations"] > 0,
                       f"年次量と電力係数が記述子で与えられる入力では、合計のみの出力で年ごとの繰り返しが 0 回"
                       f"（年次表で与えられる入力では {tab['totals_only']['year_loop_iterations']} 回、年次の出力を求めると {f['year_loop_iterations']} 回）。"
                       f"ただし、記述子と年次表が食い違っていないかを報告するために年次表の値 {t['consistency_scan_values']} 個を読み比べる走査は、どの場合にも残る"),
        "M-RECIPE": (t["recipes_computed"] == d["compositions"],
                     f"複合係数の計算は相異なる配合の数（{d['compositions']}）と同じ {t['recipes_computed']} 回"),
        "M-RESOLVE": (t["factor_resolutions"] < d["factor_uses_checked_by_reference"] / 5 and t["unit_conversions_resolved"] < 50,
                      f"係数の解決は {t['factor_resolutions']} 回、単位換算の解決は {t['unit_conversions_resolved']} 回"
                      f"（基準計算が検査する係数の使用箇所は {d['factor_uses_checked_by_reference']}）"),
        "M-SINGLEPASS": (t["rows_scanned"] == rows, f"資材・設備の行を読む回数は行数と同じ {t['rows_scanned']} 回（1 回の走査）"),
        "M-GROUPS": (d["renewal_periods"] < rows, f"更新・修繕の乗数を掛ける相手は、行（{rows}）ではなく周期の値ごとの合算（{d['renewal_periods']} 個）"),
        "M-SWEEP": (exact["period_sweep"]["all_exact"],
                    f"評価期間を {len(exact['period_sweep']['periods'])} 通りに変えた結果を 1 回の合算から求め、期間ごとの基準計算と一致"
                    f"（{exact['period_sweep']['values_compared']} 個の値）"),
    }


NA_GATE = ("合否・状態の判定であり、判定を近似すると誤判定（特に不備の見逃し）が生じる。許容できる誤判定の割合を定める根拠がなく、"
           "判定の計算は走査 1 回の中の比較だけなので、近似の対象にしなかった（測定はしていない）。")
NA_CHECK_M2 = ("検査規則を 1 つの規則表にまとめることを検討したが、判定の対象と合否の基準が規則ごとに違い、表にしても規則の数は減らず、"
               "共通の関数にはならない。走査の共通化（M1）にとどめた（実装して比較はしていない）。")
NA_MIN = "すでに最小の形（四則演算 1〜2 回）で、これ以上の簡略化はない。"
NA_LINEAR = ("行の式は 活動量×換算×係数 の積 1 つで、これより単純な近似式はない。計算量や入力を減らす近似は行数や行ごとの条件を減らすものだけで、"
             "M4・M6 の候補として記録した。")
NA_SUM = "他の単位の値の和（または比）で、近似する対象となる独自の式がない。"
NA_EXACT = "M1 の閉形式は加算と乗算が数回で、近似にしても演算も入力も減らない（傾きなどを捨てる近似は、捨てた分がそのまま誤差になる）。測定はしていない。"
NA_MEMO_M4 = "参考値（段階合計の外）であり、段階の値を対象にする共通近似モデル（AP-15）の対象に入らない。"
NA_HYBRID = "厳密式がすべての入力条件で同じ手間で使え、近似へ切り替える条件を設ける利点がない（場合分けは厳密な計算どうしで、M1 に記録した）。"
DATA_REAL = "実建物の数量内訳（資材行・設備行）と、利用許諾のある係数データ。構造・用途ごとに複数棟。"
DATA_ENERGY = "実建物の年間エネルギー使用量と延床面積、利用許諾のある面積当たり統計値。"
DATA_CLASS = "実建物の資材区分ごとの更新周期・修繕率・処理経路の分布（区分内のばらつきが分かるもの）。"

EMISSION = {
    "A13-01": "A1-A3", "A13-03": "A1-A3", "A13-04": "A1-A3", "X-01": "A1-A3", "A4-01": "A4", "A4-02": "A4",
    "A5-01": "A5", "A5-02": "A5", "A5-03": "A5", "A5-04": "A5", "B1-02": "B1", "B1-03": "B1", "B1-04": "B1", "B2-01": "B2",
    "B3-01": "B3", "B4-02": "B4", "B5-01": "B5", "B6-01": "B6", "B6-02": "B6", "B6-03": "B6", "B7-01": "B7",
    "B7-02": "B7", "B7-03": "B7", "B7-04": "B7", "C1-01": "C1", "C2-01": "C2", "C3-01": "C3", "C4-01": "C4", "X-14": "C3",
}


def EX(text, model=None, mech=None, deriv=None):
    return ("EX", text, model, mech, deriv)


NA = lambda reason: ("NA", reason)
AP = lambda cid: ("AP", cid)


def plan(units: dict) -> dict:
    P: dict[str, dict] = {}

    def m5(uid):
        n = units[uid]["n_inputs"]
        return [NA(f"この単位だけを代理モデルに置き換えるには、説明変数としてこの単位の入力（{n} 項目）を同じように読む必要があり、"
                   "統合後の厳密な計算より計算も入力も減らない。入力を減らす代理モデルは建物全体の水準でしか成り立たず、"
                   "段階別（AP-15）と合計（AP-11・AP-16）で測定した。単位単独の代理モデルは作っていない。")]

    def put(uid, m1, m2, m3, m4, m5_=None, m6=None):
        P[uid] = {"M1": m1, "M2": m2, "M3": m3, "M4": m4, "M5": m5_ or m5(uid), "M6": m6 or [NA(NA_HYBRID)]}

    gate = lambda: ([NA(NA_GATE)], [NA(NA_GATE)], [NA(NA_GATE)], [NA(NA_GATE)])

    def put_gate(uid, m1, m2):
        P[uid] = dict(zip(("M1", "M2", "M3", "M4", "M5", "M6"), (m1, m2) + gate()))

    # ---- checks ----
    put_gate("SYS-01", [EX("入力状態の判定を、計算と同じ 1 回の走査の中で行う（入力を別にたどり直さない）", None, "M-SINGLEPASS")], [NA(NA_CHECK_M2)])
    put_gate("SYS-02", [EX("単位と対象段階の検査結果を、計算のための係数解決（係数・段階・単位の組ごとに 1 回）から読む", None, "M-RESOLVE", "D8")],
             [EX("係数解決の表に統合（検査と計算が同じ解決結果を使う）", "K7", "M-RESOLVE", "D8")])
    put_gate("SYS-03", [EX("係数の参照を走査の中で係数 ID ごとに数え、判定は係数 ID ごとに 1 回だけ行う", None, "M-SINGLEPASS")],
             [EX("係数 ID ごとの表から判定を読む（係数解決の表に統合）", "K7", "M-RESOLVE", "D8")])
    put_gate("SYS-04", [NA("用途別面積の和と差 1 回で、これ以上の簡略化はない。")],
             [EX("QA-04・QA-01 と同じ残差判定関数（許容差と尺度だけが違う）で判定する", "K6", None, "D7")])
    put_gate("QA-04", [EX("SYS-04 で求めた残差を再利用し、面積を合計し直さない")], [EX("SYS-04 と同じ残差判定関数（許容差 1e-6）", "K6", None, "D7")])
    put_gate("QA-01", [EX("段階合計を、単位別の表の和と段階別の表の和の 2 系統から求めて比べる（行をたどり直さない）", None, "M-ROWPROD", "D1")],
             [EX("SYS-04・QA-04 と同じ残差判定関数で段階ごとに判定する", "K6", None, "D7")])
    put_gate("QA-02", [EX("時間境界の検査を、更新と冷媒の計算と同じ走査の中で行う", None, "M-SINGLEPASS")], [NA(NA_CHECK_M2)])
    put_gate("QA-03", [EX("使用した係数の集合を、係数解決で使われたキーから得る（行をたどり直さない）", None, "M-RESOLVE", "D8")],
             [EX("係数解決の表から読む", "K7", "M-RESOLVE", "D8")])
    put_gate("C-05", [EX("経路比率の和と質量の比較を、廃棄段階の計算と同じ走査の中で行う", None, "M-SINGLEPASS")],
             [NA(NA_CHECK_M2 + " 上限・下限の片側判定で、K6 の両側の残差判定とも形が違う。")])

    # ---- quantities and factor resolution ----
    na_qty_m4 = "数量を出力する単位で、排出を出力しない。共通近似モデル（AP-10・AP-15）は行の数量そのものを使わないので、この単位は置き換えられる側ではなく、不要になる側である。"
    put("A13-05", [NA(NA_MIN)], [EX("発注量への倍率を、行テーブルに載せる活動量に含める（同じ走査で求める）", "K1", "M-SINGLEPASS", "D1")],
        [AP("AP-06")], [NA(na_qty_m4)])
    put("X-13", [NA(NA_MIN)], [EX("A13-05 と同じ走査で、行ごとの倍率として求める（行別の値だけを出力する単位で、合計のみの出力では出力を持たない）", "K1", "M-SINGLEPASS", "D1")],
        [AP("AP-06b")], [NA(na_qty_m4)])
    put("A13-02", [EX("複合係数を配合の内容ごとに 1 回だけ計算する", None, "M-RECIPE", "D8")], [EX("係数解決の表に統合（複合係数は導出した係数キーとして表に入る）", "K7", "M-RECIPE", "D8")],
        [AP("AP-07a"), AP("AP-07b")], [NA("配合ごとの前計算で済み、他の式と共通の近似モデルにまとめる対象がない。")])
    na_resolve = "係数の検索と適用可否（使用許諾・対象段階・単位・EPD の有効期限）の判定で、数値の式ではない。近似すると適用できない係数を使うおそれがあるため、近似の対象にしなかった（測定はしていない）。"
    put("X-15", [EX("係数レコードと単位換算を、係数・段階・単位の組ごとに 1 回だけ解決する", None, "M-RESOLVE", "D8")], [EX("係数解決の表に統合", "K7", "M-RESOLVE", "D8")],
        [NA(na_resolve)], [NA(na_resolve)], [NA(na_resolve)])
    put("X-03", [EX("配合ごとに行の質量を合算してから構成材へ展開する（展開の回数は配合の種類数）", None, "M-RECIPE", "D8")],
        [EX("配合キーの行として合算し、最後に 1 回だけ展開（係数解決の表に統合）", "K7", "M-RECIPE", "D8")],
        [AP("AP-07a"), AP("AP-07b")], [NA("配合ごとの前計算で済み、他の式と共通の近似モデルにまとめる対象がない。")])

    # ---- activity x factor sums ----
    kernel = "合計のみの出力では、係数を行ごとに掛けず、表の中で係数キーごとに活動量を合算してから 1 回ずつ掛ける（行別の出力を求めるときは行ごとの積も作る）"
    for uid in ("A13-01", "A13-03", "A13-04", "X-01", "A4-01", "A4-02", "A5-01", "A5-02", "A5-03", "C1-01", "C2-01", "C3-01", "C4-01", "X-14"):
        m3 = [NA(NA_LINEAR)]
        m4 = [AP("AP-15")]
        m6 = None
        if uid in ("A13-01", "A13-03"):
            m4 = [AP("AP-10"), AP("AP-10b"), AP("AP-15")]
            m6 = [AP("AP-12")]
        if uid == "A13-04":
            m3 = [AP("AP-19a"), AP("AP-19b")]
        if uid in ("A4-01", "C2-01"):
            m3 = [AP("AP-17")]
        if uid in ("C3-01", "C4-01"):
            m4 = [AP("AP-18c"), AP("AP-18"), AP("AP-15")]
        put(uid, [EX(kernel, None, "M-ROWPROD", "D1")], [EX("行テーブルの 1 つの表として統合（値は 表の活動量×係数 の和として読む）", "K1", "M-ROWPROD", "D1")], m3, m4, None, m6)
    memo_m2 = "参考値のタグを付けた表として行テーブルに載せる（値は同じ読み方で求め、段階合計には入れない）"
    put("X-12", [EX(kernel, None, "M-ROWPROD", "D1")], [EX(memo_m2, "K1", "M-ROWPROD", "D1")], [AP("AP-17")], [NA(NA_MEMO_M4)])
    put("STO-02", [NA(NA_MIN)], [EX(memo_m2, "K1", None, "D1")], [NA(NA_MIN)], [NA(NA_MEMO_M4)])
    put("X-16", [EX("物価の比 P_base/P_cost を行の乗数として活動量に含め、係数は表で 1 回掛ける", None, "M-ROWPROD", "D1")], [EX(memo_m2, "K1", "M-ROWPROD", "D1")],
        [NA("費用×物価の比×係数 の積で、これより単純な式はない。費用ベースの推定そのものが数量ベースの代替であり、その精度は実データなしには評価できない（06_OPEN_ISSUES）。")],
        [NA(NA_MEMO_M4)])
    put("A5-04", [NA("3 つの表の値の和で、これ以上の簡略化はない。")], [EX("A5 の 3 つの表の値の和として読む", "K1", None, "D1")], [NA(NA_SUM)], [AP("AP-15")])
    put("B7-04", [NA("3 つの表の値の和で、これ以上の簡略化はない。")], [EX("B7 の 3 つの表の値の和として読む", "K1", None, "D1")], [NA(NA_SUM)], [AP("AP-15")])
    put("X-17", [EX("製造排出の活動量を、同じ走査の中で 6 区分の表にも足し込む（行をたどり直さない）", None, "M-SINGLEPASS", "D1")],
        [EX("行テーブルの集約キーを 6 区分にした表から読む。なお本単位は定義上の恒等式（要約数量×(区分の排出÷要約数量)）で、区分別に並べ替えただけである", "K1", None, "D1")],
        [NA("代表係数をその建物自身から作る定義なので恒等式であり、単純化の余地がない。代表係数を外から与える近似は AP-10・AP-10b（M4）。")],
        [AP("AP-10"), AP("AP-10b")])
    put("X-09", [EX("C3・C4 と同じ走査で、資材区分×経路の表にも足し込む（行をたどり直さない）", None, "M-SINGLEPASS", "D1")],
        [EX("行テーブルの集約キーを 資材区分×経路 にした表から読む", "K1", "M-ROWPROD", "D1")], [NA(NA_SUM)], [AP("AP-18c")])

    # ---- renewals, repairs, rebuild ----
    cnt = "合計のみの出力では更新年の一覧を作らず、回数を閉形式で求める（端は一覧と同じ判定式で確かめる。一覧の出力を求めるときは一覧を作る）"
    count_ap = [AP("AP-01"), AP("AP-02"), AP("AP-03")]
    na_list = "明示の更新年一覧と周期更新の使い分けは、厳密な計算どうしの場合分け（M1）であり、近似との併用ではない。"
    put("B4-01", [EX(cnt, None, "M-EVENTS", "D2")], [EX("回数関数 N(T,c) に統合", "K2", "M-EVENTS", "D2")], count_ap, [AP("AP-18a")], None, [NA(na_list)])
    put("B4-03", [EX(cnt + "。本単位は行別の回数だけを出力し、合計のみの出力では出力を持たない", None, "M-EVENTS", "D2")],
        [EX("回数関数 N(T,c) に統合", "K2", "M-EVENTS", "D2")], count_ap, [AP("AP-18a")], None, [NA(na_list)])
    put("B4-02", [EX("更新の排出を、周期の値ごとに合算した 1 回分の活動量×回数 で求める（事象ごと・行ごとに足さない）", None, "M-GROUPS", "D2")],
        [EX("周期ごとの合算に回数の乗数を掛けて行テーブルに載せる", "K2", "M-GROUPS", "D2")], count_ap, [AP("AP-18a"), AP("AP-18"), AP("AP-15")], None, [AP("AP-20")])
    put("X-08", [EX("周期ごとの合算は B4-02 の計算の途中結果そのもので、追加の走査をしない", None, "M-GROUPS", "D2")],
        [EX("回数関数×周期ごとの合算として統合", "K2", "M-GROUPS", "D2")], count_ap, [AP("AP-18a")])
    put("B3-01", [EX("年ごとの加算を (T − 更新が属する年の重み) の閉形式に置き換え、周期の値ごとに合算した 活動量×修繕率 に掛ける", None, "M-GROUPS", "D3")],
        [EX("周期ごとの合算に修繕年数の乗数を掛けて行テーブルに載せる", "K2", "M-GROUPS", "D3")], [AP("AP-04")], [AP("AP-18b"), AP("AP-18"), AP("AP-15")])
    put("B3-02", [NA("すでに e0·r·T の閉形式で、これ以上の簡略化はない。")], [EX("B3-01 と同じ合算に、乗数 T を掛けて求める", "K2", "M-GROUPS", "D3")],
        [AP("AP-04")], [NA(NA_MEMO_M4)])
    put("B5-01", [EX("事象ごとの加算を 回数×範囲比×初期段階の和 に置き換える", None, "M-EVENTS", "D4")],
        [EX("回数関数と、初期段階の表への共通の乗数として統合", "K2", "M-EVENTS", "D4")], count_ap, [AP("AP-15")])
    put("X-10", [EX("更新回数を閉形式で求め、周期の値ごとに合算した質量に (1＋回数) を掛ける", None, "M-GROUPS", "D2")],
        [EX("係数の代わりに質量を持つ合算として、回数の乗数とともに統合", "K2", "M-GROUPS", "D2")], count_ap,
        [NA("質量の集計で、排出の段階に属さない。段階の値を対象にする共通近似モデル（AP-15）の対象に入らない。区分ごとの代表周期（AP-18a）の誤差は B4 と同じ仕組みで生じる。")])
    put("X-07", [EX("合計のみの出力では年次系列を作らず合計だけを返す。系列を求めるときは、周期の値ごとに合算した値を更新年に置く（行ごとに置かない）", None, "M-GROUPS", "D2")],
        [EX("回数関数と年重みから系列を組み立てる", "K2", "M-GROUPS", "D2")],
        [NA("系列そのものが出力で、刻みを粗くすると出力が変わる。累積を乗数から直接求める閉形式は、年末ちょうどの事象の扱いが「評価期間 t の合計」と 1 点で違うことを確認した段階で、"
            "実装・検証していない（06_OPEN_ISSUES に記載）。")],
        [NA(NA_SUM)])

    # ---- refrigerants ----
    put("B1-01", [NA(NA_MIN)], [EX("冷媒の走査の中で 充填量×GWP を求める（B1-02〜04 に共通の活動量の項）", "K4", None, "D6")], [NA(NA_MIN)], [NA(NA_MEMO_M4)])
    cyc = "合計のみの出力では、年ごとの残存量の更新を、充填サイクルごとの等比の閉形式に置き換える（年次の出力を求めるときは年ごとに計算する）"
    for uid in ("B1-02", "B1-03", "B1-04"):
        put(uid, [EX(cyc, None, "M-YEARLOOP", "D6")], [EX("充填サイクルの質量収支 1 式に統合（漏洩・交換前の残存・最終残存を同時に得る）", "K4", "M-YEARLOOP", "D6")],
            [AP("AP-05")], [AP("AP-15")], None, [NA("交換年の一覧があってもなくても同じ閉形式が使えるため、併用の必要がない。")])

    # ---- operation ----
    put("X-06", [EX("一定・直線低下・段階の 3 種類を区分的に直線な 1 つの形で表し、合計に使う累積 G(T)・H(T) を閉形式で求める"
                    "（年次表で与えられる系列は走査する。X-06 自身の年次の出力は、合計のみの出力では系列の出所と整合の報告だけになる）", None, "M-YEARLOOP", "D5")],
        [EX("区分的に直線な系列のモーメント G・H として統合", "K3", "M-YEARLOOP", "D5")], [AP("AP-09a"), AP("AP-09b")],
        [NA("累積係数は買電排出の式の一部で、他の式と共通の近似モデルにまとめる対象がない。")], None, [AP("AP-09c")])
    put("B6-04", [EX("消費・発電・売電が一定または直線で、打ち切り max(0,·) が働かないことを両端の 2 点で確かめられるとき、年ごとの評価をしない"
                     "（それ以外は年ごとに評価。本単位の年次の出力は合計のみの出力では作らない）", None, "M-YEARLOOP", "D5")],
        [EX("年重み付き和の閉形式に統合", "K3", "M-YEARLOOP", "D5")], [AP("AP-08")], [NA(NA_SUM)])
    put("B6-01", [EX("買電量が一定または直線のとき、買電排出を B·G(T) + S·H(T) で求める（打ち切りが働く場合と年次表は年ごと）", None, "M-YEARLOOP", "D5")],
        [EX("年重み付き和の閉形式として統合", "K3", "M-YEARLOOP", "D5")], [AP("AP-08")], [AP("AP-13"), AP("AP-15")], None, [AP("AP-09c")])
    for uid in ("B6-02", "B7-01", "B7-02", "B7-03"):
        put(uid, [EX("年ごとの加算を等差級数の和（一定なら 値×T）に置き換え、係数は表で 1 回掛ける（年次表は走査）", None, "M-YEARLOOP", "D5")],
            [EX("年重み付き和の閉形式として行テーブルに載せる", "K3", "M-YEARLOOP", "D5")], [NA(NA_EXACT)], [AP("AP-15")])
    put("B6-03", [EX("買電分（B·G + S·H）と燃料分（等差級数）の和として求める", None, "M-YEARLOOP", "D5")],
        [EX("年重み付き和の閉形式に統合", "K3", "M-YEARLOOP", "D5")], [AP("AP-08")], [AP("AP-15")])
    put("B2-01", [NA(NA_MIN)], [EX("買電分（K3 で求めた値）×施設管理の割合 として求める", "K3", None, "D5")], [AP("AP-08")], [AP("AP-15")])
    put("X-11", [EX("累積係数 G(T) を再利用し、面積×原単位×換算×G(T) の 1 式にする", None, "M-YEARLOOP", "D5")],
        [EX("年重み付き和の閉形式に統合", "K3", "M-YEARLOOP", "D5")], [NA("すでに 1 式で、これより単純な式はない。")], [AP("AP-13")])

    # ---- memo, stage vector, gases ----
    put("STO-01", [NA(NA_MIN)],
        [NA("入力が係数レコードではなく物性値（密度・炭素含有率）で与えられるため、行テーブルに載せるには導出係数 s = 密度×炭素含有率×44/12 を別に作る必要があり、"
            "式の数も入力も減らない。実装していない。")],
        [AP("AP-21")], [NA(NA_MEMO_M4)])
    put("X-02", [EX("段階の値を、単位別の表の値の和として読む（行をたどらない）", None, "M-ROWPROD", "D1")], [EX("行テーブルの段階別の合計", "K1", "M-ROWPROD", "D1")],
        [NA(NA_SUM)], [AP("AP-15")], [AP("AP-11"), AP("AP-16")])
    put("X-04", [EX("行を 1 本ずつたどらず、表の中で係数キーごとに合算した活動量にガス別の量を掛ける", None, "M-ROWPROD", "D1")],
        [EX("行テーブルに係数の列（ガス別）を足して読む", "K1", "M-ROWPROD", "D1")], [AP("AP-22a")], [NA("厳密な読み方が表の項目数だけの乗算で済み、共通の近似モデルにまとめる対象がない。")])
    put("X-05", [EX("全ガス版と同じ表に CO2 の係数列を掛ける（行をたどり直さない）", None, "M-ROWPROD", "D1")],
        [EX("行テーブルに係数の列（CO2）を足して読む", "K1", "M-ROWPROD", "D1")], [AP("AP-22b")], [NA("厳密な読み方が表の項目数だけの乗算で済み、共通の近似モデルにまとめる対象がない。")])

    # ---- indicators ----
    na_ind = "段階の値の和で、これ以上の簡略化はない。"
    na_up = "この指標単独の代理モデルは作っていない。段階別の代理（AP-15）の該当段階の誤差が目安になり、合計の代理は SUM-03 で測定した（AP-11・AP-16）。"
    for uid in ("SUM-01", "SUM-02"):
        put(uid, [NA(na_ind)], [EX("段階ベクトルの一部の和として指標の段で求める", "K5", None, "D7")], [NA(NA_SUM)], [AP("AP-15")], [NA(na_up)])
    put("SUM-03", [NA(na_ind)], [EX("段階ベクトルの和として指標の段で求める", "K5", None, "D7")], [AP("AP-14")], [AP("AP-15")], [AP("AP-11"), AP("AP-16")])
    for uid in ("SUM-04", "SUM-05"):
        put(uid, [NA(NA_MIN)], [EX("合計÷尺度（面積、面積×年数）として指標の段で求める", "K5", None, "D7")], [NA(NA_MIN)], [NA(NA_SUM)], [AP("AP-11"), AP("AP-16")])
    put("SUM-06", [NA(NA_MIN)], [EX("合計÷1000 として指標の段で求める", "K5", None, "D7")], [NA(NA_MIN)], [NA(NA_SUM)])
    put("SUM-07", [NA(NA_MIN)], [EX("段階÷合計 として指標の段で求める", "K5", None, "D7")], [NA(NA_MIN)], [NA(NA_SUM)])
    put("SUM-08", [NA("差と比だけの式で、これ以上の簡略化はない。基準案の合計を呼び出し側が持っていれば基準案を計算し直さずに済むが、これは式の簡略化ではなく作業の進め方（再利用）なので、成果には数えない。")],
        [EX("差と削減率を指標の段で求める（基準案の合計は同じ統合モデルで求める）", "K5", None, "D7")],
        [NA("差と比だけの式で、これより単純な式はない。なお差は合計の誤差を増幅するので、合計を近似した場合は差の誤差を別に確かめる必要がある。")], [NA(NA_SUM)])
    return P


def conclusions(ap: dict) -> dict:
    """Declared conclusion of each approximate candidate, asserted against the measured statistics."""
    pct = lambda x: f"{x * 100:+.1f}％"
    upct = lambda x: f"{x * 100:.1f}％"
    s = {cid: c.get("stage_error") for cid, c in ap.items()}
    rng = lambda cid: f"{pct(s[cid]['max_under'])}〜{pct(s[cid]['max_over'])}"
    synth = "架空の母集団での値であり、実建物での精度を示さない。"
    o1, o2, o3 = (ap[c]["other_targets"] for c in ("AP-01", "AP-02", "AP-03"))
    b5 = "B5（建替・大型改修の回数に適用）"
    kinds8, g9 = ap["AP-08"]["by_profile_kind"], ap["AP-09a"]["by_grid_kind"]
    x13 = ap["AP-06b"]["row_error"]
    br = ap["AP-20"]
    o17 = ap["AP-17"]["other_targets"]
    x12k, c2k = sorted(o17)[1], sorted(o17)[0]
    out = {
        "AP-01": ("REJECTED", "A", s["AP-01"]["max_over"] <= 1e-12 and s["AP-01"]["max_under"] < -0.02 and o1[b5]["stage_error"]["max_over"] <= 1e-12,
                  f"T/c − 1 ≤ ceil(T/c) − 1 なので基準を上回ることがなく、周期が評価期間を割り切る場合のほかは過小評価になる。B4 段階で平均 {pct(s['AP-01']['mean_signed'])}、最大 {pct(s['AP-01']['max_under'])}。"
                  f"B5（建替の回数）では最大 {pct(o1[b5]['stage_error']['max_under'])}、X-10 の資源量では最大 {pct(o1['X-10 資源量[kg]']['max_under'])}。重大な過小評価を生むため不採用。", None),
        "AP-02": ("REJECTED", "S", s["AP-02"]["max_under"] < -0.02 and s["AP-02"]["max_over"] > 0.02,
                  f"誤差の符号が定まらず、B4 段階で {rng('AP-02')}。B5 では {pct(o2[b5]['stage_error']['max_under'])}〜{pct(o2[b5]['stage_error']['max_over'])} で、"
                  f"基準が 0 回なのに排出を計上する場合が {o2[b5]['n_reference_zero_candidate_nonzero']} 件ある。X-10 の資源量は {pct(o2['X-10 資源量[kg]']['max_under'])}〜{pct(o2['X-10 資源量[kg]']['max_over'])}。"
                  "段階 2％ の目標を大きく超え、過小評価もあるため不採用。", None),
        "AP-03": ("REJECTED", "A", s["AP-03"]["max_under"] > 0.02,
                  f"T/c > ceil(T/c) − 1 なので必ず過大。B4 段階で平均 {pct(s['AP-03']['mean_signed'])}、B5 で平均 {pct(o3[b5]['stage_error']['mean_signed'])}、"
                  f"X-10 の資源量で平均 {pct(o3['X-10 資源量[kg]']['mean_signed'])}。目標を大きく超えるため不採用。", None),
        "AP-04": ("REJECTED", "A", s["AP-04"]["max_under"] >= 0.0 and s["AP-04"]["p95_abs"] > 0.02,
                  f"更新年の除外を無視するので必ず過大（安全側）。B3 段階で平均 {pct(s['AP-04']['mean_signed'])}、95 パーセンタイル {upct(s['AP-04']['p95_abs'])}、最大 {pct(s['AP-04']['max_over'])} で段階 2％ の目標を超える。"
                  "厳密な閉形式（K2）が同じ手間で使えるため不採用。", None),
        "AP-05": ("REJECTED", "A", s["AP-05"]["max_under"] >= -1e-9 and s["AP-05"]["p95_abs"] > 0.02,
                  f"1−(1−r)^k ≤ r·k なので必ず過大（安全側）だが、B1 段階で平均 {pct(s['AP-05']['mean_signed'])}、最大 {pct(s['AP-05']['max_over'])} と大きい。"
                  "厳密な閉形式（K4）が同じ手間で使えるため不採用。", None),
        "AP-06": ("REJECTED", "A", s["AP-06"]["max_over"] <= 0.0 and s["AP-06"]["max_under"] < 0.0,
                  f"1+w < 1/(1−w) なので必ず過小評価（A1-A3 段階で平均 {pct(s['AP-06']['mean_signed'])}、最大 {pct(s['AP-06']['max_under'])}）。"
                  "誤差は目標内だが、除算 1 回を乗算 1 回に替えるだけで得るものがなく、常に過小側に偏るため不採用。", None),
        "AP-06b": ("REJECTED", "A", x13["max_over"] <= 1e-12 and x13["max_under"] < 0.0,
                   f"1/(1−w) を 1 に置き換えるので必ず過小（行ごとの正味発注量で平均 {pct(x13['mean_signed'])}、最大 {pct(x13['max_under'])}、{x13['n']} 行）。AP-06 と同じ理由で不採用。", None),
        "AP-07a": ("REJECTED", "A", s["AP-07a"]["max_over"] <= 0.0 and s["AP-07a"]["p95_abs"] > 0.02,
                   f"構成材を落とすだけなので必ず過小評価（複合品の製造排出で平均 {pct(s['AP-07a']['mean_signed'])}、最大 {pct(s['AP-07a']['max_under'])}）。不採用。", None),
        "AP-07b": ("REJECTED", "S", s["AP-07b"]["max_under"] < -0.02 and s["AP-07b"]["max_over"] > 0.02,
                   f"比率を補正しても、落とした構成材の係数が残りの平均と違う分だけずれ、符号が定まらない（{rng('AP-07b')}）。"
                   "複合係数は配合ごとに 1 回の計算で済む（K7）ので、切り捨てる利点がなく不採用。", None),
        "AP-08": ("REJECTED", "S", kinds8["CONSTANT"]["max_abs"] < 1e-9 and s["AP-08"]["max_abs"] > 0.02,
                  f"買電量が一定なら誤差 0。一定でない場合は買電量と係数の相関の分だけずれ、B6 段階で {rng('AP-08')}（直線の買電量では "
                  f"{pct(kinds8['LINEAR_TREND']['max_under'])}〜{pct(kinds8['LINEAR_TREND']['max_over'])}）。直線の場合も厳密な閉形式 B·G+S·H（K3）が使えるので不採用。", None),
        "AP-09a": ("REJECTED", "S", g9["CONSTANT"]["max_abs"] < 1e-9 and g9["STEPWISE"]["max_abs"] > 0.02,
                   f"一定の系列では誤差 0、直線低下では最大 {pct(g9['LINEAR_DECLINE_TO_FLOOR']['max_over'])}（過小なし）だが、段階的な系列では "
                   f"{pct(g9['STEPWISE']['max_under'])}〜{pct(g9['STEPWISE']['max_over'])}。記述子で与えられる系列には厳密な閉形式（K3）があり、補間に置き換える利点がないため、"
                   "全種類への一律の適用は不採用。年次表の系列だけに適用する併用は AP-09c。", None),
        "AP-09b": ("REJECTED", "S", s["AP-09b"]["max_abs"] > 0.02,
                   f"10 年刻みでは B6 段階で {rng('AP-09b')}。5 年刻み（AP-09a）より悪く、同じ理由で不採用。", None),
        "AP-09c": ("HOLD", "S", s["AP-09c"]["n"] > 0 and s["AP-09c"]["max_under"] < 0.0,
                   f"年次表で与えられる系列（{s['AP-09c']['n']} シナリオ）だけに 5 年刻みの補間を使うと、B6 段階で平均 {pct(s['AP-09c']['mean_signed'])}、95 パーセンタイル {upct(s['AP-09c']['p95_abs'])}、"
                   f"{rng('AP-09c')}。架空の系列では段階 2％ の{'内側' if s['AP-09c']['max_abs'] <= 0.02 else '外側'}だが、{upct(s['AP-09c']['share_under_estimated'])} のシナリオで過小になる。"
                   f"入力は年数分の値から 5 年ごとの値に減る。実際の将来係数の見通しがもともと数年刻みで与えられるのか、その形はどうかが分からないと判断できない。{synth}",
                   "利用許諾のある電力排出係数の将来見通し（年次か数年刻みか、その形）。"),
        "AP-10": ("HOLD", "S", s["AP-10"]["n"] > 0,
                  f"架空の母集団では資材製造の誤差が 95 パーセンタイルで {upct(s['AP-10']['p95_abs'])}（{rng('AP-10')}）。架空データの係数と数量のばらつきは実建物を表していないので、この値から採否を判断できない。", DATA_REAL),
        "AP-10b": ("HOLD", "S", s["AP-10b"]["n"] > 0,
                   f"6 区分に入らない資材の割増を掛けても、架空の母集団では 95 パーセンタイル {upct(s['AP-10b']['p95_abs'])}（{rng('AP-10b')}）で、割増なし（AP-10）と同程度。{synth}", DATA_REAL),
        "AP-11": ("HOLD", "S", s["AP-11"]["n"] > 0,
                  f"架空の母集団では合計の誤差が 95 パーセンタイルで {upct(s['AP-11']['p95_abs'])}。架空データでは実用精度を評価できない。", DATA_REAL),
        "AP-12": ("HOLD", "S", s["AP-12"]["n"] > 0,
                  f"架空の母集団では平均 {pct(s['AP-12']['mean_signed'])}、{rng('AP-12')}。質量の大きい行ほど係数が小さい傾向があると過小になる。実建物での傾向は未確認。", DATA_REAL),
        "AP-13": ("HOLD", "S", s["AP-13"]["n"] > 0,
                  f"架空の母集団では B6 段階で {rng('AP-13')}。面積当たり使用量と実績の関係は架空データでは意味を持たない。", DATA_ENERGY),
        "AP-14": ("REJECTED", "S", s["AP-14"]["max_abs"] > 0.01,
                  f"更新が評価期間の途中で段差を作るため、直線補間では合計が {rng('AP-14')} ずれる。"
                  "統合モデルは 1 回の合算から別の評価期間の結果を厳密に求められる（K2）ので不採用。", None),
        "AP-15": ("HOLD", "S", s["AP-15"]["n"] > 0,
                  f"架空の母集団では合計の誤差が 95 パーセンタイルで {upct(s['AP-15']['p95_abs'])}。段階別にはさらに大きい。架空データでは実用精度を評価できない。", DATA_REAL),
        "AP-16": ("HOLD", "S", s["AP-16"]["n"] > 0,
                  f"架空の母集団では合計の誤差が 95 パーセンタイルで {upct(s['AP-16']['p95_abs'])}。架空データでは実用精度を評価できない。", DATA_REAL),
        "AP-17": ("HOLD", "S", s["AP-17"]["n"] > 0 and s["AP-17"]["max_under"] < 0.0 < s["AP-17"]["max_over"],
                  f"質量と距離に相関があると単純平均ではずれ、符号が定まらない。架空の母集団では A4 段階で {rng('AP-17')}、"
                  f"X-12 で {pct(o17[x12k]['max_under'])}〜{pct(o17[x12k]['max_over'])}、C2（搬出距離）で {pct(o17[c2k]['max_under'])}〜{pct(o17[c2k]['max_over'])}。"
                  f"質量で重み付けした平均距離なら厳密（恒等）だが、それには行ごとの質量と距離が要り、入力は減らない。重い資材ほど遠くから運ぶ傾向が実際にあるかどうかで結果が決まる。{synth}",
                  "実建物の資材ごとの輸送質量・距離・手段の記録。"),
        "AP-18a": ("HOLD", "S", s["AP-18a"]["n"] > 0 and s["AP-18a"]["max_under"] < 0.0 < s["AP-18a"]["max_over"],
                   f"区分内の行の周期がそろっていれば厳密だが、ばらつくと回数関数の段差のために大きくずれる。架空の母集団では B4 段階で {rng('AP-18a')}（95 パーセンタイル {upct(s['AP-18a']['p95_abs'])}）。"
                   f"実建物で区分内の周期がどれだけそろっているかで結果が決まる。{synth}", DATA_CLASS),
        "AP-18b": ("HOLD", "S", s["AP-18b"]["n"] > 0 and s["AP-18b"]["max_under"] < 0.0,
                   f"修繕は修繕率について線形なので、初期排出で重み付けした代表修繕率は除外年を除いて厳密。残る誤差は代表周期による除外年の違いだけで、架空の母集団では B3 段階で "
                   f"{rng('AP-18b')}（95 パーセンタイル {upct(s['AP-18b']['p95_abs'])}、段階 2％ の{'内側' if s['AP-18b']['max_abs'] <= 0.02 else '外側'}）。"
                   f"ただし過小になる場合があり（{upct(s['AP-18b']['share_under_estimated'])} のシナリオ）、区分内の周期のばらつきに依存する。{synth}", DATA_CLASS),
        "AP-18c": ("HOLD", "S", s["AP-18c"]["n"] > 0 and s["AP-18c"]["max_under"] < 0.0 < s["AP-18c"]["max_over"],
                   f"区分内で経路の比率と係数が共通なら厳密だが、行ごとに違うとずれる。架空の母集団では C3＋C4 で {rng('AP-18c')}（95 パーセンタイル {upct(s['AP-18c']['p95_abs'])}）。{synth}", DATA_CLASS),
        "AP-18": ("HOLD", "S", s["AP-18"]["n"] > 0,
                  f"AP-18a〜c を同時に適用すると、B3＋B4＋C3＋C4 の合計で {rng('AP-18')}（95 パーセンタイル {upct(s['AP-18']['p95_abs'])}）、ホールライフ合計に対して 95 パーセンタイル "
                  f"{upct(ap['AP-18']['total_error']['p95_abs'])}。誤差のほとんどは代表周期（AP-18a）から来る。{synth}", DATA_CLASS),
        "AP-19a": ("HOLD", "S", s["AP-19a"]["n"] > 0 and s["AP-19a"]["max_under"] < 0.0 < s["AP-19a"]["max_over"],
                   f"比率が行によらず一定なら厳密だが、ばらつくと符号の定まらない誤差になる。架空の母集団では未数量分で {rng('AP-19a')}（ホールライフ合計に対しては 95 パーセンタイル "
                   f"{upct(ap['AP-19a']['total_error']['p95_abs'])}）。実際の比率のばらつきが分からないと判断できない。{synth}",
                   "実建物の未数量工事項目の割合（行ごと、または工種ごと）。"),
        "AP-19b": ("REJECTED", "A", s["AP-19b"]["max_under"] >= 0.0 and s["AP-19b"]["p95_abs"] > 0.02,
                   f"r/(1−r) は r について増加するので、最大の比率を使えば必ず過大（安全側）だが、未数量分が平均 {pct(s['AP-19b']['mean_signed'])} になり推定値として粗すぎる。不採用。", None),
        "AP-20": ("REJECTED", "A", br["share_reference_inside_bracket"] == 1.0 and br["bracket_width_relative_to_reference"]["mean_abs"] > 0.02,
                  f"T/c − 1 ≤ N ≤ T/c から、基準値は必ずこの上下限の間に入る（{br['n']} シナリオすべてで確認）。ただし幅が B4 の平均 {upct(br['bracket_width_relative_to_reference']['mean_abs'])} あり、"
                  "推定値の代わりにはならない。結果の検算用の範囲としては使えるが、計算の置き換えとしては不採用。", None),
        "AP-21": ("HOLD", "S", s["AP-21"]["n"] > 0,
                  f"m3 当たりの貯蔵量 s = 密度×炭素含有率×44/12 を 1 つの入力にすれば厳密で、入力は 3 つから 2 つになる（恒等）。s を構造×用途の平均値で置き換える近似は、"
                  f"架空の母集団で {rng('AP-21')}。樹種ごとの物性の分布で決まる。{synth}", "利用許諾のある樹種別の密度・炭素含有率と、建物ごとの樹種構成。"),
        "AP-22a": ("REJECTED", "A", s["AP-22a"]["max_over"] <= 0.0 and s["AP-22a"]["max_under"] < -0.02,
                   f"CO2 以外のガスと冷媒を落とすので必ず過小評価（対象段階の合計で平均 {pct(s['AP-22a']['mean_signed'])}、最大 {pct(s['AP-22a']['max_under'])}）。不採用。", None),
        "AP-22b": ("HOLD", "S", s["AP-22b"]["n"] > 0 and s["AP-22b"]["max_under"] < 0.0 < s["AP-22b"]["max_over"],
                   f"CO2 の割合は係数ごとに違うので、建物の構成によってずれる。架空の母集団では CO2 のみの合計で {rng('AP-22b')}。厳密な読み方（同じ表に CO2 の列を掛ける）が"
                   f"表の項目数だけの乗算で済むので、近似にする利点は小さい。係数のガス別内訳の実際の分布が分からないと誤差を評価できない。{synth}",
                   "利用許諾のある係数データのガス別内訳。"),
    }
    for cid, (_, _, ok, _, _) in out.items():
        if not ok:
            raise SystemExit(f"declared conclusion of {cid} contradicts the measured statistics")
    missing = set(ap) - set(out)
    if missing:
        raise SystemExit(f"measured candidates without a conclusion: {sorted(missing)}")
    return out


# what became of the concrete proposals of the axis-B judges that the first round had not examined
JUDGE_PROPOSALS = [
    ("X-06", "4 種類の電力係数系列を 1 つの節点表＋補間方式にまとめ、G(T) を区間ごとの等差級数で求める", ["EX-X-06-M1", "EX-X-06-M2", "AP-09c"],
     "一定・直線低下・段階を区分的に直線な 1 つの形にまとめた（厳密）。年次表の系列は走査のままで、節点への間引きは AP-09c として保留。"),
    ("A4-01, X-12, C2-01", "質量×距離×係数の共通核と、質量加重平均距離による近似", ["EX-A4-01-M2", "EX-X-12-M2", "EX-C2-01-M2", "AP-17"],
     "3 単位とも行テーブルの表として統合（厳密）。単純平均距離は AP-17 として測定し保留。質量加重平均は恒等で入力が減らない。"),
    ("C3-01, C4-01", "資材区分ごとの経路係数 φ = Σ 比率×係数 にまとめ、行は質量だけにする", ["EX-X-09-M2", "AP-18c"],
     "区分×経路への並べ替えは X-09 として厳密に統合。区分ごとの代表値に置き換える近似は AP-18c として測定し保留。"),
    ("A13-04", "平均の比率による上乗せ h(r̄)·E と、最大の比率による安全側の近似", ["AP-19a", "AP-19b"], "どちらも測定した。平均は保留、最大は不採用。"),
    ("B3-01", "区分ごとの修繕率", ["AP-18b"], "測定した。架空データでは段階 2％ の内側だが過小があり、保留。"),
    ("B4-02", "点推定の代わりに Σu·(T/c−1) と Σu·T/c の上下限を使う", ["AP-20"], "上下限は必ず成り立つが幅が広く、計算の置き換えとしては不採用。"),
    ("B5-01", "建替なしを 範囲比 0 として表し、場合分けの入力を減らす", [],
     "範囲比 0 と建替なしは同じ結果になる（式の上で明らか）。入力仕様の変更になるため実装しておらず、入力の厳密な削減の候補として 06_OPEN_ISSUES に記載した。"),
    ("X-07", "累積系列を乗数から直接求める閉形式", [], "未実装・未検証。年末ちょうどの事象の扱いが違うことだけ確認した。06_OPEN_ISSUES に記載した。"),
    ("X-17, AP-10", "6 区分に入らない資材の割増を加える", ["AP-10b"], "測定した。架空データでは AP-10 と同程度で、保留。"),
    ("SYS-01, X-15", "出所レコードごとの状態の前計算と、係数解決の記憶", ["EX-X-15-M1", "EX-SYS-02-M2"],
     "係数解決は係数・段階・単位の組ごとに 1 回にした（厳密）。出所レコードごとの状態の前計算は実装していない（状態の判定は行ごとに項目別の指定が優先するため）。"),
]


def main() -> int:
    exact = json.loads(EXACT.read_text(encoding="utf-8"))
    approx = json.loads(APPROX.read_text(encoding="utf-8"))["candidates"]
    units = {u["id"]: u for u in json.loads(UNITS.read_text(encoding="utf-8"))["units"]}
    mech = mechanism_checks(exact)
    for key, (ok, text) in mech.items():
        if not ok:
            raise SystemExit(f"mechanism {key} is not supported by the counters: {text}")
    derived = set(re.findall(r"^## (D\d+)", DERIVATIONS.read_text(encoding="utf-8"), flags=re.M))
    concl = conclusions(approx)
    VER = {"A": "VERIFIED_ANALYTIC_AND_SYNTHETIC", "S": "VERIFIED_SYNTHETIC_ONLY"}
    no_totals = set(exact["units_without_output_in_totals_mode"])
    P = plan(units)
    if set(P) != set(units):
        raise SystemExit(f"plan and ledger differ: {sorted(set(P) ^ set(units))}")
    records = []
    for uid in units:
        ex = exact["units"].get(uid)
        for step in ("M1", "M2", "M3", "M4", "M5", "M6"):
            for item in P[uid][step]:
                kind = item[0]
                if kind == "EX":
                    _, title, model, mkey, deriv = item
                    ok = ex is not None and ex["failures"] == 0 and ex["max_abs_rel_error"] <= exact["tolerance"]
                    if not ok:
                        raise SystemExit(f"{uid} {step}: exactness is claimed but not supported by the verification output")
                    if deriv and not set(deriv.split("・")) <= derived:
                        raise SystemExit(f"{uid} {step}: derivation {deriv} is not in DERIVATIONS.md")
                    reason = (f"出力が基準計算と一致（{exact['scenarios']} シナリオ、数値 {ex['leaves_compared']} 個、最大の相対差 {ex['max_abs_rel_error']:.1e}）。")
                    if mkey:
                        reason += f" 仕組みの確認：{mech[mkey][1]}。"
                    if uid in no_totals:
                        reason += " この単位は合計のみの出力では出力を持たない。"
                    records.append({
                        "unit_id": uid, "step": step, "candidate_id": f"EX-{uid}-{step}", "title": title, "outcome": "SUCCESS",
                        "verification": VER["A"] if deriv else VER["S"], "unified_model": model, "mechanism": mkey, "derivation": deriv,
                        "reason": reason, "data_needed": None,
                        "evidence": ["04_VERIFICATION/unified_model_exactness.json", "research_code/fastcalc/engine.py"]
                                    + ([f"03_MODELS/DERIVATIONS.md#{deriv}"] if deriv else [])})
                elif kind == "NA":
                    records.append({
                        "unit_id": uid, "step": step, "candidate_id": f"NA-{uid}-{step}", "title": "検討の結果、候補なし（測定なし）",
                        "outcome": "NOT_APPLICABLE", "verification": "NOT_VERIFIED", "unified_model": None, "mechanism": None, "derivation": None,
                        "reason": item[1], "data_needed": None, "evidence": []})
                else:
                    cid = item[1]
                    outcome, ver, _, reason, data = concl[cid]
                    if cid == "AP-15" and uid in EMISSION:
                        st = approx["AP-15"]["by_stage"].get(EMISSION[uid])
                        if st and st.get("n"):
                            reason += f"（この単位の段階 {EMISSION[uid]} では 95 パーセンタイル {st['p95_abs'] * 100:.0f}％）"
                    if approx[cid].get("step") != step:
                        raise SystemExit(f"{cid} is a {approx[cid].get('step')} candidate but is planned as {step} for {uid}")
                    records.append({
                        "unit_id": uid, "step": step, "candidate_id": cid, "title": approx[cid]["title"], "outcome": outcome,
                        "verification": VER[ver], "unified_model": None, "mechanism": None, "derivation": None, "reason": reason, "data_needed": data,
                        "evidence": ["04_VERIFICATION/approximation_study.json", "research_code/bench/approx_study.py"]})
    (OUT / "records").mkdir(parents=True, exist_ok=True)
    (OUT / "records" / "units.json").write_text(json.dumps({
        "schema_version": "2.0",
        "note": "1 件 = 評価単位×検討段階×候補。SUCCESS は、出力の一致・仕組みの計数・導出の 3 つに裏付けがあるものだけ（裏付けがなければ生成が失敗する）。"
                "NOT_APPLICABLE は測定をしていない判断で、理由は論拠であって検証結果ではない。架空データでの検証であり、実建物での精度を保証しない。",
        "record_count": len(records), "records": records}, ensure_ascii=False, indent=1), encoding="utf-8")

    ids = {r["candidate_id"] for r in records}
    covered: dict[str, list] = {k: [] for k in MODELS}
    for r in records:
        if r["outcome"] == "SUCCESS" and r["unified_model"] and r["unit_id"] not in covered[r["unified_model"]]:
            covered[r["unified_model"]].append(r["unit_id"])
    unified = {u for v in covered.values() for u in v}
    (OUT / "models.json").write_text(json.dumps({
        "schema_version": "2.0",
        "note": "統合モデルの目録。独立概念モデルの評価単位を、基準計算と同じ結果になる形でまとめたもの（近似ではない）。"
                "一致は、冗長な入力（記述子と年次表）が食い違う場合や不備のある入力を含む架空データで確認した。",
        "membership_rule": "値を共有の表から読むか、共有のパラメータ付き関数で求める単位だけを、そのモデルに統合されたものとして数える。",
        "not_unified": sorted(set(units) - unified),
        "models": [{"id": k, **v, "units": covered[k], "unit_count": len(covered[k])} for k, v in MODELS.items()],
        "mechanisms": {k: {"holds": ok, "statement": text} for k, (ok, text) in mech.items()}},
        ensure_ascii=False, indent=1), encoding="utf-8")

    cands = []
    for cid, c in approx.items():
        outcome, ver, _, reason, data = concl[cid]
        cands.append({"candidate_id": cid, "step": c.get("step"), "title": c["title"], "replaces": c["replaces"], "measured_on": c["stage"],
                      "outcome": outcome, "verification": VER[ver], "reason": reason, "data_needed": data,
                      "units": sorted({r["unit_id"] for r in records if r["candidate_id"] == cid}),
                      "stage_error": c.get("stage_error") or c.get("row_error"), "total_error": c.get("total_error"),
                      "by_material_class": c.get("by_material_class"), "other_targets": c.get("other_targets"),
                      "under_estimates": c.get("under_estimates"), "within_stage_target": c.get("within_stage_target"),
                      "within_total_target": c.get("within_total_target")})
        if not cands[-1]["units"]:
            raise SystemExit(f"candidate {cid} is not attached to any unit")
    (OUT / "candidates.json").write_text(json.dumps({
        "schema_version": "2.0", "targets": {"total": 0.01, "stage": 0.02},
        "note": "近似候補と測定した誤差（架空データ）。誤差 = (候補 − 基準)/基準。負は過小評価。measured_on は誤差を測った量。",
        "candidates": cands}, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- judge proposals: scores of 2 or more against what was recorded ----
    rank = {r["id"]: r for r in json.loads(AXIS_B.read_text(encoding="utf-8"))["ranking"]}
    trace = []
    for uid in units:
        med = rank[uid]["median_by_criterion"] if uid in rank else {}
        for crit, step, label in (("b6", "M3", "単純な近似式で置き換えられる"), ("b7", "M4", "他の式と共通の近似モデルにできる")):
            if med.get(crit, 0) >= 2:
                recs = [r for r in records if r["unit_id"] == uid and r["step"] == step]
                trace.append({"unit_id": uid, "criterion": crit, "meaning": label, "median_score": med[crit], "step": step,
                              "records": [{"candidate_id": r["candidate_id"], "outcome": r["outcome"]} for r in recs],
                              "measured": any(r["verification"] != "NOT_VERIFIED" for r in recs)})
    named = []
    for target, proposal, rec_ids, disposition in JUDGE_PROPOSALS:
        lost = [i for i in rec_ids if i not in ids]
        if lost:
            raise SystemExit(f"judge proposal for {target} points to missing records {lost}")
        named.append({"units": target, "proposal": proposal, "records": rec_ids, "disposition": disposition})
    (OUT / "judge_proposal_trace.json").write_text(json.dumps({
        "schema_version": "1.0",
        "note": "評価軸 B の採点（3 者の中央値）で「近似・共通化できる」が 2 点以上だった単位について、対応する段階に何を記録したかの対照表。"
                "measured が偽の行は、測定せずに理由だけで候補なしとしたもの。",
        "score_2_or_more": trace, "not_measured": [f"{t['unit_id']} {t['step']}" for t in trace if not t["measured"]],
        "named_proposals": named}, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"records: {len(records)}  outcomes: {dict(Counter(r['outcome'] for r in records))}")
    print("by step:", {m: dict(Counter(r["outcome"] for r in records if r["step"] == m)) for m in ("M1", "M2", "M3", "M4", "M5", "M6")})
    print("models:", {k: len(v) for k, v in covered.items()}, "not unified:", sorted(set(units) - unified))
    print("score>=2 without a measurement:", [f"{t['unit_id']} {t['step']}" for t in trace if not t["measured"]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
