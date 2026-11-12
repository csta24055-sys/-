"""Writes ``11_UNIFIED_SYSTEM/UNITS_70.md``: the mathematical definition of each of the 70 units in the unified
system, next to the definition text of the reference calculation and the trace of ``tools_unit_map.py``.

Run from ``research_code`` after ``tools_unit_map.py``:  PYTHONDONTWRITEBYTECODE=1 python3 -B tools_units_doc.py
The expressions below are written by hand from the specification (``specs/``); the derivations are in DERIVATIONS.md.
"""
import json
import os
import sys

sys.dont_write_bytecode = True

from tstudy import baseline

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "11_UNIFIED_SYSTEM", "UNITS_70.md"))
MAP = os.path.normpath(os.path.join(HERE, "..", "11_UNIFIED_SYSTEM", "results", "unit_map.json"))

# unit -> (derivation section, expression in the unified system). [..] is a 0/1 predicate, T' = T(1-1e-9),
# w_k(T) = clip(T - k, 0, 1) the weight of the year cell k, n_i(T) = number of renewals of row i before T'.
F = {
    "A13-05": ("D-01", "ok = [Q ≥ 0][0 ≤ w < 1]；q_ord = [ok]([DESIGN]·Q·1/(1−w) + [¬DESIGN]·Q)；q_inst = [ok]([DESIGN]·Q + [¬DESIGN]·Q·(1−w))"),
    "X-13": ("D-01", "net = [ok][0 ≤ ρ ≤ 1]·(q_inst + (q_ord − q_inst)·(1 − ρ))"),
    "A13-02": ("D-02", "複合係数_i = [不良の構成 0 個][|Σ_j 比_j − 1| ≤ 1e-6]·Σ_j 比_j·換算_j·係数_j"),
    "X-15": ("D-02", "種別 = [EPD が使える] / [¬EPD][複合][複合係数あり][kg へ換算可] / [¬EPD][単体][汎用係数が使える]；係数・換算倍率 = 種別ごとの値の排他的な和"),
    "A13-01": ("D-01", "Σ_i [解決済][¬EPD][数量 ok]·q_ord·換算·係数"),
    "A13-03": ("D-01", "Σ_i [EPD][数量 ok]·q_ord·換算·係数"),
    "A13-04": ("D-01", "Σ_i [0 < r < 1]·(a01_i + a03_i)·r/(1−r)"),
    "X-01": ("D-01", "Σ_j [数量 ≥ 0][係数が使える]·数量·換算·係数"),
    "X-03": ("D-13", "構成材 f ごと：質量 = Σ_{(i,j): 係数 = f} [複合][数量 ok]·q_ord·換算·比_j、排出 = 質量·換算_j·係数_j"),
    "A4-01": ("D-01", "Σ_i [搬入係数なし][係数が使える][質量, 距離 ≥ 0]·質量·距離·換算·係数"),
    "X-12": ("D-01", "A4-01 の各項に [積載率 > 0]·(1/積載率) を掛ける"),
    "A4-02": ("D-01", "Σ_i [搬入係数あり][係数が使える][数量 ok]·q_ord·換算·係数"),
    "A5-01": ("D-01", "[買電量 ≥ 0][電力係数の単位が読める][kWh から換算可][使用許諾]·kWh·換算·工事期間の電力係数"),
    "A5-02": ("D-01", "Σ_燃料 [数量 ≥ 0][係数が使える]·数量·換算·係数"),
    "A5-03": ("D-01", "Σ_廃棄物 [質量 ≥ 0][係数が使える]·質量·換算·係数"),
    "A5-04": ("D-01", "A5-01 + A5-02 + A5-03"),
    "X-17": ("D-13", "区分 c：fbar_c = [q_c ≠ 0]·(Σ_{i ∈ c}(a01_i + a03_i))·(1/q_c)、e_c = q_c·fbar_c；値 = Σ_c e_c"),
    "X-16": ("D-13", "Σ_項目 [費用 ≥ 0][係数が使える][指数 > 0]·費用·(基準年の指数·1/費用年の指数)·換算·係数"),
    "C1-01": ("D-01", "Σ_活動 [数量 ≥ 0][係数が使える]·数量·換算·係数"),
    "C2-01": ("D-01", "Σ_i [係数が使える][質量, 距離 ≥ 0]·質量·0.001·距離·換算·係数 + Σ_搬出 [..]·質量·距離·換算·係数"),
    "C3-01": ("D-01", "Σ_{(i,j): 最終処分以外} [係数が使える][比率 ≥ 0][質量 ≥ 0]·質量_i·比率_ij·換算·係数"),
    "C4-01": ("D-01", "Σ_{(i,j): 最終処分} [係数が使える][比率 ≥ 0][質量 ≥ 0]·質量_i·比率_ij·換算·係数"),
    "X-14": ("D-01", "Σ_j [係数が使える][廃棄質量 ≥ 0]·廃棄質量·換算·係数"),
    "C-05": ("D-12", "v1_i = [負の比率 ≥ 1 個] + [0 個][¬(Σ比率 ≤ 1+1e-6)]；未配分_i = [v1 = 0][Σ比率 < 1−1e-6]；v2_i = [点検できる][¬(廃棄質量 ≤ 据付質量·換算·(1+1e-6))]；ok = [Σ(v1 + v2) = 0]"),
    "X-09": ("D-13", "mass[c, ρ] = Σ_{(i,j)} [質量 ≥ 0][比率 ≥ 0]·質量·比率·[区分_i = c][経路_j = ρ]；emission は C3-01・C4-01 の項を同じキーでまとめる"),
    "X-10": ("D-04", "資源量 = Σ_i [ok]·q_ord·換算·(1 + n_i(T))；廃棄物量 = Σ_i [ok]·((q_ord − q_inst)·換算 + 廃棄質量)·(1 + n_i(T)) + Σ_j [質量 ≥ 0]·質量·(1 + n_j(T))"),
    "STO-01": ("D-01", "[3 量とも ≥ 0]·木材量·絶乾密度·炭素含有率·(44/12)"),
    "STO-02": ("D-01", "[係数が使える（段階 MEMO）][数量 ≥ 0]·コンクリート量·換算·吸収係数"),
    "B1-01": ("D-08", "Σ_d [充填量 ≥ 0][GWP ≥ 0]·充填量·GWP"),
    "B1-02": ("D-08", "Σ_{d,k} u_{d,k}·r_d·GWP_d·w_k(T)；u = (I+N)(I+N²)…(I+N¹²⁸) b（年初の残存量）"),
    "B1-03": ("D-08", "Σ_交換 [τ < T']·λ·GWP·([その年の最初]·u·(1 − [補充なし]·r·w_k(T)) + [2 回目以降]·m0)"),
    "B1-04": ("D-09", "T ∈ (K, K+1]：A_K + B_K·(T − K) + Σ_{セル K の交換, τ < T'} (κ(m0 − u) + κ·u·r·(T − K))（区間形）"),
    "B2-01": ("D-07", "[0 ≤ ρ ≤ 1]·EL(T)·ρ、EL(T) = Σ_k e_k·w_k(T)（買電排出）"),
    "B3-01": ("D-05", "Σ_i a_i·T − Σ_{事象を含む年セル (i,k)} a_i·[その年の最初の事象 < T']·w_k(T)、a_i = [r ≥ 0]·e0_i·r_i"),
    "B3-02": ("D-05", "Σ_i [r ≥ 0]·e0_i·r_i·T"),
    "B4-01": ("D-04", "設備 j の事象 = {τ : [使う格子][τ < T']}（一覧があれば一覧、なければ耐用年数の倍数）；件数 = Σ [..]"),
    "B4-02": ("D-04", "Σ_{(i,n)} u_i·[τ_{i,n} < T']；n_partial = Σ_i [構成要素が欠けている]·[τ_{i,1} < T']"),
    "B4-03": ("D-04", "n_i(T) = Σ_n [n·c_i < T']"),
    "B5-01": ("D-06", "Σ_n [n·C < T']·[NONE でない][0 ≤ φ ≤ 1]·φ·(初期の A1-A3＋A4＋A5＋C1〜C4)"),
    "X-06": ("D-07", "γ_k = [一定]·start + [直線低下]·max(floor, start − decline·k) + [段階]·Σ_s [f_s ≤ k < f_{s+1}]·val_s + [整っていない]·table_k"),
    "B6-04": ("D-07", "n_k = [単位と換算が有効]·[d_k ≥ 0]·d_k、d_k = c_k − (g_k·cg − x_k·cx)"),
    "B6-01": ("D-07", "e_k = [使用許諾][換算可][B6-04 算出済]·n_k·換算·γ_k"),
    "B6-02": ("D-07", "f_k = Σ_燃料 [単位が「単位/year」][係数が使える]·量_k·換算·係数"),
    "B6-03": ("D-07", "Σ_k (e_k + f_k)·w_k(T)"),
    "B7-01": ("D-07", "年 k：[単位が「単位/year」][係数が使える]·上水量_k·換算·係数"),
    "B7-02": ("D-07", "年 k：同じ形（下水）"),
    "B7-03": ("D-07", "年 k：同じ形（一般廃棄物）"),
    "B7-04": ("D-07", "Σ_k (上水 + 下水 + 廃棄物)_k·w_k(T)"),
    "X-11": ("D-07", "[面積 > 0][原単位 ≥ 0][換算可][使用許諾]·面積·原単位·換算·G(T)、G(T) = Σ_k γ_k·w_k(T)"),
    "X-08": ("D-04", "周期の値 c ごと：U_c = Σ_{周期 = c の行} u、E_c = n_c(T)·U_c；明示の一覧の設備は Σ u_j·n_j(T) を別掲"),
    "X-02": ("D-10", "full_s = Σ_u M_{s,u}·v_u(T)；by_stage_s = [s が対象]·(B2 が対象外なら B6 から B2-01 を引かない)；complete = [Σ [対象][bad_u(T) ≥ 1] = 0]"),
    "SUM-01": ("D-10", "Σ_s [対象][A1-A3, A4, A5]·by_stage_s"),
    "SUM-02": ("D-10", "Σ_s [対象][B6, B7 以外]·by_stage_s"),
    "SUM-03": ("D-10", "Σ_s [対象]·by_stage_s"),
    "SUM-04": ("D-10", "[A > 0]·SUM-03·(1/A)"),
    "SUM-05": ("D-10", "[A > 0]·SUM-03·1/(A·T)"),
    "SUM-06": ("D-10", "SUM-03·0.001"),
    "SUM-07": ("D-10", "[SUM-03 > 0][負の段階 0 個]·by_stage_s·(1/SUM-03)"),
    "SUM-08": ("D-10", "比較可能 = [基準案あり][面積][期間][段階の集合][ガスの範囲][係数の版の集合]；差 = p − b；削減率 = [b > 0]·(b − p)·(1/b)"),
    "X-04": ("D-11", "by_gas[g] = Σ_f (Σ_s L_s[f](T))·ガス量[f,g]；値 = Σ_g GWP_g·by_gas[g] + 買電 + 冷媒；足し直し_s = Σ_f L_s[f]·値_f + 擬似の行"),
    "X-05": ("D-11", "CO2_s = Σ_f L_s[f](T)·CO2_f + 買電の行；値 = Σ_s [対象]·CO2_s（+ B2 の分）"),
    "X-07": ("D-11", "series_0 = 初期段階；series_y = 年次の排出·w + 事象の排出（年 y）；最終年に C 段階と B1-04；cum_y = Σ_{y' ≤ y} series_{y'}"),
    "QA-01": ("D-12", "(a) [¬(|full_s − 足し直し_s| ≤ 1e-9·max(|full_s|, 1))]、(b) [a01 ≠ 0][a03 ≠ 0]、(c) [a41 ≠ 0][a42 ≠ 0]；ok = [件数 = 0]"),
    "QA-02": ("D-12", "行ごと：Σ_t ([¬(t ≥ 0)] + [t ≥ 0][T' ≤ t]) ≥ 1 なら違反、Σ_t [t = 0] ≥ 1 なら警告"),
    "QA-03": ("D-11", "使用_f(T) = [存在する行の数 ≥ 1]；違反 = 使用_f·[使用許諾なし または 出典が空]；n_used = Σ_f 使用_f"),
    "QA-04": ("D-12", "[A > 0]·[r ≤ 1e-6·A][−r ≤ 1e-6·A]、r = A − Σ 用途別面積"),
    "SYS-01": ("D-12", "項目ごとに状態の指示関数（欠損・導出・明示の 0・実測・推定）を作り、26 種類の項目について足す；ok = [欠損 = 0]"),
    "SYS-02": ("D-12", "違反 = [適用][単位なし] + [適用][単位あり][記録あり][換算不可]；段階の不一致は係数ごとに数える；ok = [違反 0][不一致 0]"),
    "SYS-03": ("D-12", "[適用][ID なし] + [適用][ID あり][記録なし] + Σ_f 参照数_f·[許諾なし または 出典が空] + [電力係数の許諾なし]；ok = [合計 = 0]"),
    "SYS-04": ("D-12", "r = A − Σ（用途名の昇順）用途別面積；ok = [A > 0][r ≤ 1e-9·A][−r ≤ 1e-9·A]"),
}


def main():
    registry = baseline.load()
    trace = json.load(open(MAP))
    ids = sorted(registry.UNITS)
    missing = [u for u in ids if u not in F]
    assert not missing, missing
    L = ["# 全 70 評価単位の数学的定義（統合系での式）", "",
         "`research_code/tools_units_doc.py` が生成した。「基準計算の定義」は凍結した基準計算の定義文の冒頭、「統合系での式」は仕様（`specs/`）から",
         "手で書き起こしたもの、「経路」は `tools_unit_map.py` の追跡結果である。導出は `DERIVATIONS.md` の該当節、入力の全項目は `results/unit_map.json`。", "",
         "記法：`[..]` は 0/1 の述語、`T' = T(1−1e-9)`、`w_k(T) = clip(T − k, 0, 1)`（年セル k の重み）、`n_i(T)` は行 i の更新回数。",
         "経路の ① は積和①（T によらない）、K は節点スペクトル、②a は TIME（T でのゲート付き和）、②b は AGG（集計）。", "",
         "| 単位 | 基準計算の定義（冒頭） | 統合系での式 | 導出 | 経路 | 出力キー |", "|---|---|---|---|---|---|"]
    for uid in ids:
        doc = " ".join((registry.UNITS[uid].fn.__doc__ or "").split())
        head = doc.split("。")[0] + "。"
        t = trace[uid]
        s = t["steps"]
        path = "①" if any(k.startswith("P1") for k in s) else ""
        if t["spectra"]:
            path += " K"
        if any(k.startswith("TIME") for k in s):
            path += " ②a"
        if any(k.startswith("AGG") for k in s):
            path += " ②b"
        L.append("| %s | %s | %s | %s | %s | %s |" % (uid, head.replace("|", "／"), F[uid][1].replace("|", "∣"), F[uid][0], path.strip(), "{keys:%s}" % uid))
    text = "\n".join(L) + "\n"
    ver = os.path.join(os.path.dirname(MAP), "verification_rep_evaluation.json")
    if os.path.exists(ver):
        units = json.load(open(ver))["units"]
        for uid in ids:
            text = text.replace("{keys:%s}" % uid, ", ".join(sorted(units.get(uid, {}).get("keys", {}))))
    with open(OUT, "w") as f:
        f.write(text)
    print("written", OUT, len(ids), "units")


if __name__ == "__main__":
    main()
