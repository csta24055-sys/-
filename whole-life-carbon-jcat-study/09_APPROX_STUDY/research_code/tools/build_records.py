#!/usr/bin/env python3
"""Build the research records: one conclusion for every evaluation unit and every method step.

The plan below says, for each unit and each step M1..M6, what was examined. The outcome
and the verification state are NOT typed in by hand where a measurement exists: they are
read from the verification outputs

    04_VERIFICATION/unified_model_exactness.json   (exact simplification / unification)
    04_VERIFICATION/approximation_study.json       (approximate candidates)

and the declared conclusion of each approximate candidate is asserted against the
measured statistics, so a record cannot contradict the data.

Outputs
    03_MODELS/models.json              catalogue of the unified models K1..K8
    03_MODELS/candidates.json          approximate candidates with measured errors and conclusions
    03_MODELS/records/units.json       one record per (unit, step, candidate)

Run:  cd research_code && python3 -m tools.build_records
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[2]
EXACT = STUDY / "04_VERIFICATION" / "unified_model_exactness.json"
APPROX = STUDY / "04_VERIFICATION" / "approximation_study.json"
UNITS = STUDY / "01_LEDGER" / "units.json"
OUT = STUDY / "03_MODELS"

MODELS = {
    "K1": {"name": "行テーブル核",
           "form": "E[s] = Σ_f A[s,f]·v_f,  A[s,f] = Σ_行 (活動量 × 乗数)",
           "idea": "すべての排出を「段階・係数 ID・活動量」の行として 1 つの表に載せ、係数を掛ける前に段階と係数 ID ごとに活動量を合算する。"
                   "段階合計、ガス別内訳、CO2 のみの結果は、同じ表に別の係数列を掛けるだけで得られる。",
           "kept": "行ごとの段階タグ、係数の単位と対象段階の検査、択一の規則（EPD と汎用、質量距離法と数量法）"},
    "K2": {"name": "回数関数とライフサイクル乗数",
           "form": "N(T,c) = #{n≥1 : n·c < T} = ceil(T/c) − 1;  更新 = N·u,  修繕 = r·(T − 除外年の重み)·e0,  建替 = N(T,C)·φ·(初期段階の和)",
           "idea": "更新年の一覧を作らず、回数を閉形式で求めて行の乗数にする。修繕の年次積算も「評価年数から更新が属する年を引く」閉形式になる。",
           "kept": "評価期間の終わりちょうどの更新を数えない規約、明示の更新年一覧の優先、端数年の重み"},
    "K3": {"name": "年重み付き和の閉形式",
           "form": "Σ_y w_y·(b + s·k) = b·T + s·(等差級数);  G(T) = Σ_y w_y·g_y（一定・直線低下・段階は閉形式、年次表は走査）",
           "idea": "年ごとの積算を、一定値・直線・段階関数の和の公式に置き換える。買電量が一定なら 買電量×G(T) の 1 回の乗算になる。",
           "kept": "端数年の按分、自家消費の打ち切り max(0, ·)、年次表はそのまま走査"},
    "K4": {"name": "充填サイクルの質量収支",
           "form": "補充なし：1 サイクル j 年の漏洩 = m0·(1 − (1−r)^j);  補充あり：m0·r·T;  交換時損失・廃棄時未回収は残存量から",
           "idea": "冷媒の残存量を年ごとに更新する代わりに、交換から交換までを 1 サイクルとして等比の閉形式で求める。",
           "kept": "交換が属する年の年末に反映する規約、端数年の按分、B1 への帰属"},
    "K5": {"name": "指標行列",
           "form": "指標 = M·E（M は 0/1 の行列）÷ 尺度（面積、面積×年数、1000、合計）",
           "idea": "アップフロント・エンボディド・ホールライフ・原単位・割合・施設管理分の切り出しを、段階ベクトルの線形関数として 1 か所で求める。",
           "kept": "対象段階の指定、面積・年数が無効なら算出しない規則、参考値を合計に入れない規則"},
    "K6": {"name": "検査規則表",
           "form": "判定キー（係数 ID、単位の組、出所、行）ごとに 1 回だけ評価する真偽の規則",
           "idea": "入力状態・単位・使用許諾・面積・質量収支・時間境界の検査を 1 つの走査にまとめ、同じキーの判定を繰り返さない。検査そのものは近似しない。",
           "kept": "すべての検査項目と合否の基準（結果は基準計算と一致）"},
    "K7": {"name": "係数解決の一括化",
           "form": "複合係数 (W·f) を配合の内容ごとに 1 回、係数レコードと単位換算を ID・単位の組ごとに 1 回",
           "idea": "行ごとに繰り返していた複合係数の算出と係数の検索を、相異なる配合・係数・単位の組の数だけに減らす。",
           "kept": "EPD の適用条件、質量比の合計の検査、換算の根拠"},
    "K8": {"name": "基準案の結果の再利用",
           "form": "基準案の合計を 1 回だけ計算して保持し、差と削減率だけを求める",
           "idea": "比較のたびに基準案を最初から計算し直さない。",
           "kept": "比較可能性の条件（面積・期間・段階・ガス範囲・係数の版）"},
}

NA_GATE = "検査（合否や状態の判定）であり、近似すると判定の意味が失われるため、近似の対象にしない。"
NA_EXACT = "M1・M2 で厳密な簡略化と統合が得られており、近似に置き換えても計算量も入力項目も減らないため、近似の利点がない。"
NA_MIN = "すでに最小の形（四則演算 1〜2 回）で、これ以上の簡略化はない。"
NA_LINEAR = "関数形は活動量×係数の線形和で、これより単純な式はない。近似の余地は入力行数の削減だけであり、M4 で扱う。"
NA_UNIT_SURROGATE = "単位単独の代理モデルは、厳密式より入力も計算も増えるため利点がない。建物全体の代理モデルは SUM-03 の候補（AP-11・AP-16）で扱う。"
NA_HYBRID = "厳密式が全条件で同じ手間で使えるため、近似との併用は不要。"
NA_MEMO = "参考値（段階合計の外）であり、行テーブルへ統合すると段階合計と混同するおそれがある。関数形は活動量×係数と同じだが、境界を保つために統合しない。"
NA_AGG = "他の単位の結果を集計・再配置するだけで、近似する対象となる独自の関数形がない。"
DATA_REAL = "実建物の数量内訳（資材行・設備行）と、利用許諾のある係数データ。構造・用途ごとに複数棟。"
DATA_ENERGY = "実建物の年間エネルギー使用量と延床面積、利用許諾のある面積当たり統計値。"

# stage of each emission unit (for the stage-intensity surrogate AP-15)
EMISSION = {
    "A13-01": "A1-A3", "A13-03": "A1-A3", "A13-04": "A1-A3", "X-01": "A1-A3", "A4-01": "A4", "A4-02": "A4", "X-12": "A4",
    "A5-01": "A5", "A5-02": "A5", "A5-03": "A5", "A5-04": "A5", "B1-02": "B1", "B1-03": "B1", "B1-04": "B1", "B2-01": "B2",
    "B3-01": "B3", "B3-02": "B3", "B4-02": "B4", "B5-01": "B5", "B6-01": "B6", "B6-02": "B6", "B6-03": "B6", "B7-01": "B7",
    "B7-02": "B7", "B7-03": "B7", "B7-04": "B7", "C1-01": "C1", "C2-01": "C2", "C3-01": "C3", "C4-01": "C4", "X-14": "C3",
}

# ---- plan helpers -------------------------------------------------------------------------------------------------
EX = lambda text, model=None: ("EX", text, model)          # exact: verified by the leaf-by-leaf comparison
NA = lambda reason: ("NA", reason)
AP = lambda cid: ("AP", cid)


def plan() -> dict:
    P: dict[str, dict] = {}

    def put(uid, m1, m2, m3=None, m4=None, m5=None, m6=None):
        P[uid] = {"M1": m1, "M2": m2, "M3": m3, "M4": m4, "M5": m5, "M6": m6}

    # gates
    gate_m1 = {
        "SYS-01": "状態の判定を、計算と同じ行の単一走査に組み込む（入力を 2 度たどらない）",
        "SYS-02": "単位の組ごとに換算を 1 回だけ引き、計算で使う換算結果をそのまま検査に使う",
        "SYS-03": "参照箇所ごとではなく係数 ID ごとに 1 回だけ判定し、参照数は数えるだけにする",
        "QA-01": "段階合計を同じ行テーブルから読むので突合は 2 系統の集計の比較 1 回になり、択一は分岐の構造で保証される",
        "QA-03": "使用した係数の集合を行テーブルのキーから得て、行をたどり直さない",
        "QA-04": "SYS-04 の残差を再利用する",
        "C-05": "経路比率の和を、廃棄段階の計算と同じ走査の中で求める",
    }
    for uid in ("SYS-01", "SYS-02", "SYS-03", "SYS-04", "QA-01", "QA-02", "QA-03", "QA-04", "C-05"):
        m1 = [EX(gate_m1[uid])] if uid in gate_m1 else [NA(NA_MIN if uid == "SYS-04" else "一覧を 1 回走査するだけで、これ以上の簡略化はない。")]
        put(uid, m1, [EX("検査規則表の 1 行として統合", "K6")], [NA(NA_GATE)], [NA(NA_GATE)], [NA(NA_GATE)], [NA(NA_GATE)])

    # quantities and factor resolution
    put("A13-05", [NA(NA_MIN)], [EX("発注量への倍率を行の活動量に含める（行テーブル核の活動量）", "K1")], [AP("AP-06")],
        [NA("行ごとの倍率であり、共通の近似モデルにまとめる対象がない。")], [NA(NA_UNIT_SURROGATE)], [NA(NA_HYBRID)])
    put("X-13", [NA(NA_MIN)], [EX("発注量と同じく、行の数量に掛ける倍率として同じ走査で求める", "K1")], [AP("AP-06")],
        [NA("行ごとの倍率であり、共通の近似モデルにまとめる対象がない。")], [NA(NA_UNIT_SURROGATE)], [NA(NA_HYBRID)])
    put("A13-02", [EX("複合係数を配合の内容ごとに 1 回だけ計算する")], [EX("係数解決の一括化に統合", "K7")],
        [NA("構成比による加重和で、これより単純な式はない。寄与の小さい構成材の切り捨ては必ず過小評価になる。")],
        [NA("配合ごとの前計算で十分に軽く、近似モデルにまとめる利点がない。")], [NA(NA_UNIT_SURROGATE)], [NA(NA_HYBRID)])
    put("X-15", [EX("係数レコードと単位換算を ID・単位の組ごとに 1 回だけ解決する")], [EX("係数解決の一括化に統合", "K7")],
        [NA("検索と優先順位の解決であり、近似の対象ではない。")], [NA("同上。")], [NA("同上。")], [NA(NA_HYBRID)])
    put("X-03", [EX("配合ごとに行の質量を合算してから構成比で展開する（展開は配合の数だけ）")], [EX("配合キーの行として行テーブル核に載せ、最後に 1 回だけ展開", "K7")],
        [NA("寄与の小さい構成材の切り捨ては必ず過小評価になり、比率の補正なしには使えない。厳密な前計算で十分に軽い。")],
        [NA(NA_EXACT)], [NA(NA_UNIT_SURROGATE)], [NA(NA_HYBRID)])

    # activity x factor sums
    kernel_text = "段階と係数 ID ごとに活動量を合算してから係数を掛ける（係数の乗算は行数ではなく係数の種類数）"
    for uid in ("A13-01", "A13-03", "A13-04", "X-01", "A4-01", "A4-02", "X-12", "A5-01", "A5-02", "A5-03", "C1-01", "C2-01",
                "C3-01", "C4-01", "X-14"):
        m4 = [AP("AP-15")]
        m5 = [NA(NA_UNIT_SURROGATE)]
        m6 = [NA(NA_HYBRID)]
        if uid in ("A13-01", "A13-03"):
            m4 = [AP("AP-10"), AP("AP-15")]
            m6 = [AP("AP-12")]
        put(uid, [EX(kernel_text)], [EX("行テーブル核の行として統合", "K1")], [NA(NA_LINEAR)], m4, m5, m6)
    put("A5-04", [NA("3 項の和で、これ以上の簡略化はない。")], [EX("行テーブル核の A5 段階の合計として読む", "K1")], [NA(NA_AGG)],
        [AP("AP-15")], [NA(NA_UNIT_SURROGATE)], [NA(NA_HYBRID)])
    put("X-17", [EX("製造排出を、同じ走査の中で 6 区分に足し込む")], [EX("行テーブル核の集約キーを 6 区分にしたもの", "K1")], [NA(NA_LINEAR)],
        [AP("AP-10")], [AP("AP-11")], [AP("AP-12")])

    # renewals, repairs, rebuild
    cnt = "更新年の一覧を作らず、回数を閉形式 N = ceil(T/c) − 1 で求める（同じ判定式で端を補正）"
    put("B4-01", [EX(cnt)], [EX("回数関数に統合", "K2")], [AP("AP-01"), AP("AP-02"), AP("AP-03")], [NA("回数関数 1 つに厳密に統合済みで、近似モデルにまとめる利点がない。")],
        [NA(NA_UNIT_SURROGATE)], [EX("周期更新は閉形式、明示の更新年一覧は一覧を走査（どちらも厳密）")])
    put("B4-03", [EX(cnt)], [EX("回数関数に統合", "K2")], [AP("AP-01"), AP("AP-02"), AP("AP-03")], [NA("回数関数 1 つに厳密に統合済みで、近似モデルにまとめる利点がない。")],
        [NA(NA_UNIT_SURROGATE)], [NA(NA_HYBRID)])
    put("B4-02", [EX("事象ごとの加算を 回数×1 回当たりの排出 に置き換える")], [EX("行の乗数（更新回数）として行テーブル核に統合", "K2")],
        [AP("AP-01"), AP("AP-02"), AP("AP-03")], [AP("AP-15")], [NA(NA_UNIT_SURROGATE)], [EX("周期更新は閉形式、明示の更新年一覧は一覧を走査（どちらも厳密）")])
    put("X-08", [EX("1 回当たりの排出を、同じ走査の中で周期ごとに合算する")], [EX("回数関数×周期別の合算として統合", "K2")],
        [AP("AP-01"), AP("AP-02"), AP("AP-03")], [NA(NA_AGG)], [NA(NA_UNIT_SURROGATE)], [EX("周期更新は周期別に合算、明示の一覧は別枠（どちらも厳密）")])
    put("B3-01", [EX("年ごとの加算を r·e0·(T − 更新が属する年の重み) の閉形式に置き換える")], [EX("行の乗数（修繕）として行テーブル核に統合", "K2")],
        [AP("AP-04")], [AP("AP-15")], [NA(NA_UNIT_SURROGATE)], [EX("周期更新は閉形式、明示の更新年一覧は一覧から除外年を求める（どちらも厳密）")])
    put("B3-02", [NA("すでに閉形式（e0·r·T）で、これ以上の簡略化はない。")], [EX("行の乗数 r·T として同じ走査で求める", "K2")],
        [NA("本式自体が B3-01 の概算であり、その誤差は AP-04 として B3-01 側に記録した。")], [AP("AP-15")], [NA(NA_UNIT_SURROGATE)], [NA(NA_HYBRID)])
    put("B5-01", [EX("事象ごとの加算を 回数×範囲比×初期段階の和 に置き換える")], [EX("回数関数と、初期段階の行への共通乗数として統合", "K2")],
        [AP("AP-01"), AP("AP-02"), AP("AP-03")], [AP("AP-15")], [NA(NA_UNIT_SURROGATE)], [NA(NA_HYBRID)])
    put("X-10", [EX("更新回数を閉形式で求め、同じ走査の中で質量を合算する")], [EX("係数を質量に置き換えた行として、回数の乗数とともに統合", "K2")],
        [AP("AP-01"), AP("AP-02"), AP("AP-03")], [NA(NA_AGG)], [NA(NA_UNIT_SURROGATE)], [NA(NA_HYBRID)])

    # refrigerants
    put("B1-01", [NA(NA_MIN)], [NA(NA_MEMO)], [NA(NA_MIN)], [NA(NA_MEMO)], [NA(NA_UNIT_SURROGATE)], [NA(NA_HYBRID)])
    cyc = "年ごとの残存量の更新を、充填サイクルごとの等比の閉形式に置き換える"
    for uid in ("B1-02", "B1-03", "B1-04"):
        put(uid, [EX(cyc)], [EX("充填サイクルの質量収支 1 式に統合", "K4")], [AP("AP-05")], [AP("AP-15")], [NA(NA_UNIT_SURROGATE)],
            [NA("交換年の一覧があってもなくても同じ閉形式が使えるため、併用は不要。")])

    # operation
    put("X-06", [EX("係数の累積 G(T) を閉形式で求め、合計の計算には年次系列を使わない")], [EX("年重み付き和の閉形式に統合", "K3")],
        [AP("AP-09a"), AP("AP-09b")], [NA("累積係数 1 つに厳密に統合済みで、近似モデルにまとめる利点がない。")], [NA(NA_UNIT_SURROGATE)],
        [EX("一定・直線低下・段階は閉形式、年次表は表を走査（どちらも厳密）")])
    put("B6-04", [EX("消費・発電・売電が一定なら max を 1 回だけ評価する")], [EX("年重み付き和の閉形式に統合", "K3")], [AP("AP-08")],
        [NA(NA_AGG)], [NA(NA_UNIT_SURROGATE)], [EX("一定なら 1 回の評価、そうでなければ年ごとに評価（どちらも厳密）")])
    put("B6-01", [EX("買電量が一定なら 買電量×累積係数 の 1 回の乗算にする")], [EX("年重み付き和の閉形式として行テーブル核に統合", "K3")], [AP("AP-08")],
        [AP("AP-13"), AP("AP-15")], [NA(NA_UNIT_SURROGATE)], [EX("一定なら閉形式、そうでなければ年次計算（どちらも厳密）")])
    for uid in ("B6-02", "B7-01", "B7-02", "B7-03"):
        put(uid, [EX("年ごとの加算を等差級数の和（一定なら 値×T）に置き換え、係数は最後に 1 回掛ける")], [EX("年重み付き和の閉形式として行テーブル核に統合", "K3")],
            [NA(NA_EXACT)], [AP("AP-15")], [NA(NA_UNIT_SURROGATE)], [EX("一定・直線は閉形式、年次表は表を走査（どちらも厳密）")])
    put("B6-03", [EX("年ごとの加算を 買電分（累積係数）＋燃料分（等差級数）の和に置き換える")], [EX("年重み付き和の閉形式に統合", "K3")], [AP("AP-08")],
        [AP("AP-15")], [NA(NA_UNIT_SURROGATE)], [EX("一定なら閉形式、そうでなければ年次計算（どちらも厳密）")])
    put("B7-04", [EX("年ごとの加算を等差級数の和に置き換える")], [EX("年重み付き和の閉形式に統合", "K3")], [NA(NA_EXACT)], [AP("AP-15")],
        [NA(NA_UNIT_SURROGATE)], [EX("一定・直線は閉形式、年次表は表を走査（どちらも厳密）")])
    put("B2-01", [NA(NA_MIN)], [EX("B6 の買電分に対する定数倍として指標の段で求める", "K5")], [AP("AP-08")], [AP("AP-15")], [NA(NA_UNIT_SURROGATE)],
        [EX("買電分が閉形式でも年次計算でも同じ 1 回の乗算（厳密）")])
    put("X-11", [EX("累積係数 G(T) を再利用し、面積×原単位×G(T) の 1 式にする")], [EX("年重み付き和の閉形式に統合", "K3")],
        [NA("すでに面積×原単位×累積係数の 1 式で、これより単純な式はない。")], [AP("AP-13")], [NA(NA_UNIT_SURROGATE)], [NA(NA_HYBRID)])

    # end-of-life tables and totals
    put("X-09", [EX("C3・C4 と同じ積を 1 回だけ計算し、資材区分×経路の表にも足し込む")], [EX("行テーブル核の集約キーを 資材区分×経路 にしたもの", "K1")],
        [NA(NA_AGG)], [NA(NA_AGG)], [NA(NA_UNIT_SURROGATE)], [NA(NA_HYBRID)])
    put("STO-01", [NA(NA_MIN)], [NA(NA_MEMO)], [NA(NA_MIN)], [NA(NA_MEMO)], [NA(NA_UNIT_SURROGATE)], [NA(NA_HYBRID)])
    put("STO-02", [NA(NA_MIN)], [NA(NA_MEMO)], [NA(NA_MIN)], [NA(NA_MEMO)], [NA(NA_UNIT_SURROGATE)], [NA(NA_HYBRID)])

    # stage vector, gases, series
    put("X-02", [EX("段階の値を行テーブルの段階別合計として読む")], [EX("行テーブル核の段階別合計", "K1")], [NA(NA_AGG)], [AP("AP-15")],
        [AP("AP-11"), AP("AP-16")], [NA(NA_HYBRID)])
    put("X-04", [EX("行を 1 本ずつたどらず、段階と係数 ID ごとに合算した活動量にガス別の量を掛ける")], [EX("行テーブル核に係数列（ガス別）を足すだけ", "K1")],
        [NA("CO2 以外のガスを省くと必ず過小評価になる。厳密な集約で十分に軽い。")], [NA(NA_EXACT)], [NA(NA_UNIT_SURROGATE)], [NA(NA_HYBRID)])
    put("X-05", [EX("全ガス版の計算を繰り返さず、同じ集約表に CO2 の係数列を掛ける")], [EX("行テーブル核に係数列（CO2）を足すだけ", "K1")],
        [NA("CO2 版を全ガス版の定数倍で近似すると、行ごとに CO2 の割合が違うため誤差が出る。厳密な集約で十分に軽い。")], [NA(NA_EXACT)],
        [NA(NA_UNIT_SURROGATE)], [NA(NA_HYBRID)])
    put("X-07", [EX("更新と修繕の年次配置を、行ごとではなく周期の種類ごとに行う")], [EX("回数関数と年重みで系列を組み立てる", "K2")],
        [NA("系列そのものが出力であり、刻みを粗くすると出力が変わる。")], [NA(NA_AGG)], [NA(NA_UNIT_SURROGATE)], [NA(NA_HYBRID)])

    # indicators
    for uid in ("SUM-01", "SUM-02"):
        put(uid, [NA("段階の値の和で、これ以上の簡略化はない。")], [EX("指標行列の 1 行として統合", "K5")], [NA(NA_AGG)], [AP("AP-15")],
            [NA("合計の代理モデルは SUM-03 で扱う。")], [NA(NA_HYBRID)])
    put("SUM-03", [NA("段階の値の和で、これ以上の簡略化はない。")], [EX("指標行列の 1 行として統合", "K5")], [AP("AP-14")], [AP("AP-11"), AP("AP-15")],
        [AP("AP-16")], [NA("厳密な統合モデルが十分に軽いため、近似との併用は不要。")])
    for uid in ("SUM-04", "SUM-05"):
        put(uid, [NA(NA_MIN)], [EX("指標行列の 1 行（合計÷尺度）として統合", "K5")], [NA(NA_MIN)], [AP("AP-11")], [AP("AP-16")], [NA(NA_HYBRID)])
    put("SUM-06", [NA(NA_MIN)], [EX("指標行列の 1 行（合計÷1000）として統合", "K5")], [NA(NA_MIN)], [NA(NA_AGG)], [NA(NA_UNIT_SURROGATE)], [NA(NA_HYBRID)])
    put("SUM-07", [NA(NA_MIN)], [EX("指標行列の 1 行（段階÷合計）として統合", "K5")], [NA(NA_MIN)], [NA(NA_AGG)], [NA(NA_UNIT_SURROGATE)], [NA(NA_HYBRID)])
    put("SUM-08", [EX("基準案の合計を 1 回だけ計算して保持し、比較のたびに計算し直さない")], [EX("基準案の結果の再利用に統合（差と比は指標の段で求める）", "K8")],
        [NA("差と比だけの式で、これより単純な式はない。なお差は合計の誤差を増幅するので、合計を近似した場合は差の誤差を別に確認する必要がある。")],
        [NA(NA_AGG)], [NA(NA_UNIT_SURROGATE)], [NA(NA_HYBRID)])
    return P


# declared conclusion of each approximate candidate: (outcome, verification, check(stats) -> bool, reason, data needed)
def conclusions(ap: dict) -> dict:
    pct = lambda x: f"{x * 100:+.1f}％"      # signed error
    upct = lambda x: f"{x * 100:.1f}％"      # magnitude (percentiles of |error|)
    s = {cid: c["stage_error"] for cid, c in ap.items()}
    t = {cid: c["total_error"] for cid, c in ap.items()}
    kinds8 = ap["AP-08"]["by_profile_kind"]
    g9 = ap["AP-09a"]["by_grid_kind"]
    out = {
        "AP-01": ("REJECTED", "VERIFIED_ANALYTIC_AND_SYNTHETIC", s["AP-01"]["max_over"] <= 1e-12 and s["AP-01"]["max_under"] < -0.02,
                  f"T/c − 1 ≤ ceil(T/c) − 1 なので必ず過小評価になる。B4 段階で平均 {pct(s['AP-01']['mean_signed'])}、最大 {pct(s['AP-01']['max_under'])}。重大な過小評価を生むため不採用。", None),
        "AP-02": ("REJECTED", "VERIFIED_SYNTHETIC_ONLY", s["AP-02"]["max_under"] < -0.02 and s["AP-02"]["max_over"] > 0.02,
                  f"誤差の符号が定まらず、B4 段階で {pct(s['AP-02']['max_under'])}〜{pct(s['AP-02']['max_over'])}。段階 2％ の目標を大きく超え、過小評価もあるため不採用。", None),
        "AP-03": ("REJECTED", "VERIFIED_ANALYTIC_AND_SYNTHETIC", s["AP-03"]["max_under"] > 0.02,
                  f"T/c > ceil(T/c) − 1 なので必ず過大。B4 段階で平均 {pct(s['AP-03']['mean_signed'])}。目標を大きく超えるため不採用。", None),
        "AP-04": ("REJECTED", "VERIFIED_ANALYTIC_AND_SYNTHETIC", s["AP-04"]["max_under"] >= 0.0 and s["AP-04"]["p95_abs"] > 0.02,
                  f"更新年の除外を無視するので必ず過大（安全側）。B3 段階で平均 {pct(s['AP-04']['mean_signed'])}、95 パーセンタイル {upct(s['AP-04']['p95_abs'])}、最大 {pct(s['AP-04']['max_over'])} で段階 2％ の目標を超える。"
                  "厳密な閉形式（K2）が同じ手間で使えるため不採用。", None),
        "AP-05": ("REJECTED", "VERIFIED_ANALYTIC_AND_SYNTHETIC", s["AP-05"]["max_under"] >= -1e-9 and s["AP-05"]["p95_abs"] > 0.02,
                  f"1−(1−r)^k ≤ r·k なので必ず過大（安全側）だが、B1 段階で平均 {pct(s['AP-05']['mean_signed'])}、最大 {pct(s['AP-05']['max_over'])} と大きい。"
                  "厳密な閉形式（K4）が同じ手間で使えるため不採用。", None),
        "AP-06": ("REJECTED", "VERIFIED_ANALYTIC_AND_SYNTHETIC", s["AP-06"]["max_over"] <= 0.0 and s["AP-06"]["max_under"] < 0.0,
                  f"1+w < 1/(1−w) なので必ず過小評価（A1-A3 段階で平均 {pct(s['AP-06']['mean_signed'])}、最大 {pct(s['AP-06']['max_under'])}）。"
                  "誤差は目標内だが、除算 1 回を乗算 1 回に替えるだけで得るものがなく、常に過小側に偏るため不採用。", None),
        "AP-08": ("REJECTED", "VERIFIED_SYNTHETIC_ONLY", kinds8["CONSTANT"]["max_abs"] < 1e-9 and s["AP-08"]["max_abs"] > 0.02,
                  f"買電量が一定なら誤差 0（このとき K3 の閉形式と同じ式）。一定でない場合は買電量と係数の相関の分だけずれ、B6 段階で {pct(s['AP-08']['max_under'])}〜{pct(s['AP-08']['max_over'])}。"
                  "一定の場合は厳密な閉形式として採用済み（M1・M6）で、それ以外に広げる近似としては不採用。", None),
        "AP-09a": ("REJECTED", "VERIFIED_SYNTHETIC_ONLY", g9["CONSTANT"]["max_abs"] < 1e-9 and g9["STEPWISE"]["max_abs"] > 0.02,
                   f"一定の系列では誤差 0、直線低下では最大 {pct(g9['LINEAR_DECLINE_TO_FLOOR']['max_over'])}（過小なし）だが、段階的な系列では {pct(g9['STEPWISE']['max_under'])}〜{pct(g9['STEPWISE']['max_over'])}。"
                   "パラメータ型の系列は厳密な閉形式（K3）があり、補間に置き換える利点がないため不採用。", None),
        "AP-09b": ("REJECTED", "VERIFIED_SYNTHETIC_ONLY", ap["AP-09b"]["stage_error"]["max_abs"] > 0.02,
                   f"10 年刻みでは B6 段階で {pct(s['AP-09b']['max_under'])}〜{pct(s['AP-09b']['max_over'])}。5 年刻み（AP-09a）より悪く、同じ理由で不採用。", None),
        "AP-10": ("HOLD", "VERIFIED_SYNTHETIC_ONLY", s["AP-10"]["n"] > 0,
                  f"架空の母集団では資材製造の誤差が 95 パーセンタイルで {upct(s['AP-10']['p95_abs'])}。ただし架空データの係数と数量のばらつきは実建物を表していないので、この値から採否を判断できない。", DATA_REAL),
        "AP-11": ("HOLD", "VERIFIED_SYNTHETIC_ONLY", s["AP-11"]["n"] > 0,
                  f"架空の母集団では合計の誤差が 95 パーセンタイルで {upct(s['AP-11']['p95_abs'])}。架空データでは実用精度を評価できない。", DATA_REAL),
        "AP-12": ("HOLD", "VERIFIED_SYNTHETIC_ONLY", s["AP-12"]["n"] > 0,
                  f"架空の母集団では平均 {pct(s['AP-12']['mean_signed'])}、最大 {pct(s['AP-12']['max_under'])} の過小評価。質量の大きい行ほど係数が小さい傾向があると過小になる。実建物での傾向は未確認。", DATA_REAL),
        "AP-13": ("HOLD", "VERIFIED_SYNTHETIC_ONLY", s["AP-13"]["n"] > 0,
                  f"架空の母集団では B6 段階で {pct(s['AP-13']['max_under'])}〜{pct(s['AP-13']['max_over'])}。面積当たり使用量と実績の関係は架空データでは意味を持たない。", DATA_ENERGY),
        "AP-14": ("REJECTED", "VERIFIED_SYNTHETIC_ONLY", s["AP-14"]["max_abs"] > 0.01,
                  f"更新が評価期間の途中で段差を作るため、直線補間では合計が {pct(s['AP-14']['max_under'])}〜{pct(s['AP-14']['max_over'])} ずれる。"
                  "統合モデルは評価期間を引数として厳密に計算でき十分に軽いので不採用。", None),
        "AP-15": ("HOLD", "VERIFIED_SYNTHETIC_ONLY", s["AP-15"]["n"] > 0,
                  f"架空の母集団では合計の誤差が 95 パーセンタイルで {upct(s['AP-15']['p95_abs'])}。段階別にはさらに大きい。架空データでは実用精度を評価できない。", DATA_REAL),
        "AP-16": ("HOLD", "VERIFIED_SYNTHETIC_ONLY", s["AP-16"]["n"] > 0,
                  f"架空の母集団では合計の誤差が 95 パーセンタイルで {upct(s['AP-16']['p95_abs'])}。架空データでは実用精度を評価できない。", DATA_REAL),
    }
    for cid, (_, _, ok, _, _) in out.items():
        if not ok:
            raise SystemExit(f"declared conclusion of {cid} contradicts the measured statistics")
    return out


def main() -> int:
    exact = json.loads(EXACT.read_text(encoding="utf-8"))
    approx = json.loads(APPROX.read_text(encoding="utf-8"))["candidates"]
    units = json.loads(UNITS.read_text(encoding="utf-8"))["units"]
    concl = conclusions(approx)
    P = plan()
    records = []
    for u in units:
        uid = u["id"]
        if uid not in P:
            if u["computable_in_reference"]:
                raise SystemExit(f"no research plan for computable unit {uid}")
            continue
        ex = exact["units"].get(uid)
        for step in ("M1", "M2", "M3", "M4", "M5", "M6"):
            for k, item in enumerate(P[uid][step], 1):
                kind = item[0]
                if kind == "EX":
                    ok = ex is not None and ex["failures"] == 0 and ex["max_abs_rel_error"] <= exact["tolerance"]
                    if not ok:
                        raise SystemExit(f"{uid} {step}: exactness is claimed but not supported by the verification output")
                    records.append({
                        "unit_id": uid, "step": step, "candidate_id": f"EX-{uid}-{step}", "title": item[1],
                        "outcome": "SUCCESS", "verification": "VERIFIED_ANALYTIC_AND_SYNTHETIC", "unified_model": item[2],
                        "reason": f"基準計算と全出力が一致（{exact['scenarios']} シナリオ、数値 {ex['leaves_compared']} 個、最大の相対差 {ex['max_abs_rel_error']:.1e}）。",
                        "data_needed": None,
                        "evidence": ["04_VERIFICATION/unified_model_exactness.json", "research_code/fastcalc/engine.py"]})
                elif kind == "NA":
                    records.append({
                        "unit_id": uid, "step": step, "candidate_id": f"NA-{uid}-{step}", "title": "検討の結果、対象外",
                        "outcome": "NOT_APPLICABLE", "verification": "NOT_VERIFIED", "unified_model": None, "reason": item[1],
                        "data_needed": None, "evidence": []})
                else:
                    cid = item[1]
                    outcome, verification, _, reason, data = concl[cid]
                    if cid == "AP-15" and uid in EMISSION:
                        st = approx["AP-15"]["by_stage"].get(EMISSION[uid])
                        if st and st.get("n"):
                            reason += f"（この単位の段階 {EMISSION[uid]} では 95 パーセンタイル {st['p95_abs'] * 100:.0f}％）"
                    records.append({
                        "unit_id": uid, "step": step, "candidate_id": cid, "title": approx[cid]["title"], "outcome": outcome,
                        "verification": verification, "unified_model": None, "reason": reason, "data_needed": data,
                        "evidence": ["04_VERIFICATION/approximation_study.json", "research_code/bench/approx_study.py"]})
    (OUT / "records").mkdir(parents=True, exist_ok=True)
    (OUT / "records" / "units.json").write_text(json.dumps({
        "schema_version": "1.0",
        "note": "1 件 = 評価単位×検討段階×候補。SUCCESS は検証出力に裏付けがあるものだけ。架空データでの検証であり、実建物での精度を保証しない。",
        "record_count": len(records), "records": records}, ensure_ascii=False, indent=1), encoding="utf-8")

    covered: dict[str, list] = {k: [] for k in MODELS}
    for r in records:
        if r["outcome"] == "SUCCESS" and r["unified_model"] and r["unit_id"] not in covered[r["unified_model"]]:
            covered[r["unified_model"]].append(r["unit_id"])
    (OUT / "models.json").write_text(json.dumps({
        "schema_version": "1.0",
        "note": "統合モデルの目録。いずれも基準計算と結果が一致することを架空データで確認した厳密な統合（近似ではない）。",
        "models": [{"id": k, **v, "units": covered[k], "unit_count": len(covered[k])} for k, v in MODELS.items()]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    cands = []
    for cid, c in approx.items():
        outcome, verification, _, reason, data = concl[cid]
        used_by = sorted({r["unit_id"] for r in records if r["candidate_id"] == cid})
        cands.append({"candidate_id": cid, "title": c["title"], "replaces": c["replaces"], "outcome": outcome,
                      "verification": verification, "reason": reason, "data_needed": data, "units": used_by,
                      "stage_error": c["stage_error"], "total_error": c["total_error"],
                      "under_estimates": c["under_estimates"], "within_stage_target": c["within_stage_target"],
                      "within_total_target": c["within_total_target"]})
    (OUT / "candidates.json").write_text(json.dumps({
        "schema_version": "1.0", "targets": {"total": 0.01, "stage": 0.02},
        "note": "近似候補と測定した誤差（架空データ）。誤差 = (候補 − 基準)/基準。負は過小評価。",
        "candidates": cands}, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print(f"records: {len(records)}  outcomes: {dict(Counter(r['outcome'] for r in records))}")
    print("models:", {k: len(v) for k, v in covered.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
