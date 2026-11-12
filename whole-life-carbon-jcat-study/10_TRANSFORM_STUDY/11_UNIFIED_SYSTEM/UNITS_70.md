# 全 70 評価単位の数学的定義（統合系での式）

`research_code/tools_units_doc.py` が生成した。「基準計算の定義」は凍結した基準計算の定義文の冒頭、「統合系での式」は仕様（`specs/`）から
手で書き起こしたもの、「経路」は `tools_unit_map.py` の追跡結果である。導出は `DERIVATIONS.md` の該当節、入力の全項目は `results/unit_map.json`。

記法：`[..]` は 0/1 の述語、`T' = T(1−1e-9)`、`w_k(T) = clip(T − k, 0, 1)`（年セル k の重み）、`n_i(T)` は行 i の更新回数。
経路の ① は積和①（T によらない）、K は節点スペクトル、②a は TIME（T でのゲート付き和）、②b は AGG（集計）。

| 単位 | 基準計算の定義（冒頭） | 統合系での式 | 導出 | 経路 | 出力キー |
|---|---|---|---|---|---|
| A13-01 | 資材製造排出量。 | Σ_i [解決済][¬EPD][数量 ok]·q_ord·換算·係数 | D-01 | ① | by_item, n_skipped, value |
| A13-02 | 複合材の構成比からの推計。 | 複合係数_i = [不良の構成 0 個][∣Σ_j 比_j − 1∣ ≤ 1e-6]·Σ_j 比_j·換算_j·係数_j | D-02 | ① | by_item, n_invalid |
| A13-03 | EPD／商品固有値。 | Σ_i [EPD][数量 ok]·q_ord·換算·係数 | D-01 | ① | by_item, n_skipped, value |
| A13-04 | 未数量工事項目の推定（本研究が独立に設計した上乗せ式）。 | Σ_i [0 < r < 1]·(a01_i + a03_i)·r/(1−r) | D-01 | ① | by_item, n_skipped, value |
| A13-05 | 数量による端材の扱い。 | ok = [Q ≥ 0][0 ≤ w < 1]；q_ord = [ok]([DESIGN]·Q·1/(1−w) + [¬DESIGN]·Q)；q_inst = [ok]([DESIGN]·Q + [¬DESIGN]·Q·(1−w)) | D-01 | ① | n_skipped, q_inst, q_ord |
| A4-01 | 質量距離ベースの輸送。 | Σ_i [搬入係数なし][係数が使える][質量, 距離 ≥ 0]·質量·距離·換算·係数 | D-01 | ① | by_item, n_skipped, value |
| A4-02 | 製品別輸送負荷。 | Σ_i [搬入係数あり][係数が使える][数量 ok]·q_ord·換算·係数 | D-01 | ① | by_item, n_skipped, value |
| A5-01 | 仮設電気。 | [買電量 ≥ 0][電力係数の単位が読める][kWh から換算可][使用許諾]·kWh·換算·工事期間の電力係数 | D-01 | ① | computed, value |
| A5-02 | 施工燃料。 | Σ_燃料 [数量 ≥ 0][係数が使える]·数量·換算·係数 | D-01 | ① | n_skipped, value |
| A5-03 | 工事廃棄物。 | Σ_廃棄物 [質量 ≥ 0][係数が使える]·質量·換算·係数 | D-01 | ① | n_skipped, value |
| A5-04 | 工事負荷の合計。 | A5-01 + A5-02 + A5-03 | D-01 | ① | other_assessed, parts, value |
| B1-01 | 物質の CO2e 充填量。 | Σ_d [充填量 ≥ 0][GWP ≥ 0]·充填量·GWP | D-08 | ① | n_skipped, value |
| B1-02 | 使用期間の漏洩。 | Σ_{d,k} u_{d,k}·r_d·GWP_d·w_k(T)；u = (I+N)(I+N²)…(I+N¹²⁸) b（年初の残存量） | D-08 | ① K ②a | by_item, by_year, n_skipped, value |
| B1-03 | 更新時の漏洩。 | Σ_交換 [τ < T']·λ·GWP·([その年の最初]·u·(1 − [補充なし]·r·w_k(T)) + [2 回目以降]·m0) | D-08 | ① K ②a | by_year, n_skipped, value |
| B1-04 | 廃棄時未回収量。 | T ∈ (K, K+1]：A_K + B_K·(T − K) + Σ_{セル K の交換, τ < T'} (κ(m0 − u) + κ·u·r·(T − K))（区間形） | D-09 | ① K | n_skipped, value |
| B2-01 | 施設管理に帰属させる運用負荷。 | [0 ≤ ρ ≤ 1]·EL(T)·ρ、EL(T) = Σ_k e_k·w_k(T)（買電排出） | D-07 | ① K ②a | computed, value |
| B3-01 | 年間修繕。 | Σ_i a_i·T − Σ_{事象を含む年セル (i,k)} a_i·[その年の最初の事象 < T']·w_k(T)、a_i = [r ≥ 0]·e0_i·r_i | D-05 | ① K ②a | by_year, n_skipped, value |
| B3-02 | 期間中の反復修繕（推計）。 | Σ_i [r ≥ 0]·e0_i·r_i·T | D-05 | ① ②a | n_skipped, value |
| B4-01 | 更新イベント年の生成。 | 設備 j の事象 = {τ : [使う格子][τ < T']}（一覧があれば一覧、なければ耐用年数の倍数）；件数 = Σ [..] | D-04 | ① ②a | events, n_events |
| B4-02 | 機器・資材更新負荷。 | Σ_{(i,n)} u_i·[τ_{i,n} < T']；n_partial = Σ_i [構成要素が欠けている]·[τ_{i,1} < T'] | D-04 | ① K ②a | by_item_equipment, by_item_material, by_year, n_partial, value |
| B4-03 | 交換回数の概算。 | n_i(T) = Σ_n [n·c_i < T'] | D-04 | ②a | by_item |
| B5-01 | 大型改修・建替イベント。 | Σ_n [n·C < T']·[NONE でない][0 ≤ φ ≤ 1]·φ·(初期の A1-A3＋A4＋A5＋C1〜C4) | D-06 | ① K ②a | by_year, computed, n_events, value |
| B6-01 | 年間買電排出。 | e_k = [使用許諾][換算可][B6-04 算出済]·n_k·換算·γ_k | D-07 | ① ②a | by_year, computed |
| B6-02 | 燃料の年間排出。 | f_k = Σ_燃料 [単位が「単位/year」][係数が使える]·量_k·換算·係数 | D-07 | ① K ②a ②b | by_year, descriptors_match_tables, n_skipped |
| B6-03 | 評価年数の積算。 | Σ_k (e_k + f_k)·w_k(T) | D-07 | ① K | value |
| B6-04 | オンサイト発電の扱い。 | n_k = [単位と換算が有効]·[d_k ≥ 0]·d_k、d_k = c_k − (g_k·cg − x_k·cx) | D-07 | ① K ②a ②b | by_year, computed, descriptors_match_tables |
| B7-01 | 上水利用排出。 | 年 k：[単位が「単位/year」][係数が使える]·上水量_k·換算·係数 | D-07 | ① K ②a ②b | by_year, descriptors_match_tables, n_skipped |
| B7-02 | 下水処理排出。 | 年 k：同じ形（下水） | D-07 | ① K ②a ②b | by_year, descriptors_match_tables, n_skipped |
| B7-03 | 一般廃棄物排出。 | 年 k：同じ形（一般廃棄物） | D-07 | ① K ②a ②b | by_year, descriptors_match_tables, n_skipped |
| B7-04 | 評価期間積算。 | Σ_k (上水 + 下水 + 廃棄物)_k·w_k(T) | D-07 | ① K | value |
| C-05 | 資材の質量収支。 | v1_i = [負の比率 ≥ 1 個] + [0 個][¬(Σ比率 ≤ 1+1e-6)]；未配分_i = [v1 = 0][Σ比率 < 1−1e-6]；v2_i = [点検できる][¬(廃棄質量 ≤ 据付質量·換算·(1+1e-6))]；ok = [Σ(v1 + v2) = 0] | D-12 | ① | n_mass_unchecked, ok, under_allocated, violations |
| C1-01 | 解体作業排出。 | Σ_活動 [数量 ≥ 0][係数が使える]·数量·換算·係数 | D-01 | ① | n_skipped, value |
| C2-01 | 廃棄物搬出。 | Σ_i [係数が使える][質量, 距離 ≥ 0]·質量·0.001·距離·換算·係数 + Σ_搬出 [..]·質量·距離·換算·係数 | D-01 | ① | by_item, n_skipped, value |
| C3-01 | 廃棄物処理。 | Σ_{(i,j): 最終処分以外} [係数が使える][比率 ≥ 0][質量 ≥ 0]·質量_i·比率_ij·換算·係数 | D-01 | ① | by_item, n_routes_skipped, n_skipped, value |
| C4-01 | 最終処分。 | Σ_{(i,j): 最終処分} [係数が使える][比率 ≥ 0][質量 ≥ 0]·質量_i·比率_ij·換算·係数 | D-01 | ① | by_item, n_routes_skipped, n_skipped, value |
| QA-01 | 相互排他の境界。 | (a) [¬(∣full_s − 足し直し_s∣ ≤ 1e-9·max(∣full_s∣, 1))]、(b) [a01 ≠ 0][a03 ≠ 0]、(c) [a41 ≠ 0][a42 ≠ 0]；ok = [件数 = 0] | D-12 | ① K ②a ②b | ok, violations |
| QA-02 | 時間境界検査。 | 行ごと：Σ_t ([¬(t ≥ 0)] + [t ≥ 0][T' ≤ t]) ≥ 1 なら違反、Σ_t [t = 0] ≥ 1 なら警告 | D-12 | ②a ②b | ok, violations, warnings |
| QA-03 | 出典ゲート。 | 使用_f(T) = [存在する行の数 ≥ 1]；違反 = 使用_f·[使用許諾なし または 出典が空]；n_used = Σ_f 使用_f | D-11 | ① ②a | n_used, ok, violations |
| QA-04 | 用途別面積の検算。 | [A > 0]·[r ≤ 1e-6·A][−r ≤ 1e-6·A]、r = A − Σ 用途別面積 | D-12 | ① | ok, status |
| STO-01 | 木材の炭素貯蔵（参考値）。 | [3 量とも ≥ 0]·木材量·絶乾密度·炭素含有率·(44/12) | D-01 | ① | value |
| STO-02 | コンクリート炭酸化等の取り扱い（参考値）。 | [係数が使える（段階 MEMO）][数量 ≥ 0]·コンクリート量·換算·吸収係数 | D-01 | ① | value |
| SUM-01 | アップフロント。 | Σ_s [対象][A1-A3, A4, A5]·by_stage_s | D-10 | ① K ②a ②b | complete, value |
| SUM-02 | エンボディド。 | Σ_s [対象][B6, B7 以外]·by_stage_s | D-10 | ① K ②a ②b | complete, value |
| SUM-03 | ホールライフ。 | Σ_s [対象]·by_stage_s | D-10 | ① K ②a ②b | complete, value |
| SUM-04 | 延べ床面積当たり。 | [A > 0]·SUM-03·(1/A) | D-10 | ① K ②a ②b | value |
| SUM-05 | 年平均・床面積当たり。 | [A > 0]·SUM-03·1/(A·T) | D-10 | ① K ②a ②b | value |
| SUM-06 | t-CO2e 換算。 | SUM-03·0.001 | D-10 | ① K ②a ②b | value |
| SUM-07 | 段階別割合。 | [SUM-03 > 0][負の段階 0 個]·by_stage_s·(1/SUM-03) | D-10 | ① K ②a ②b | by_stage, defined |
| SUM-08 | 改善案との差分。 | 比較可能 = [基準案あり][面積][期間][段階の集合][ガスの範囲][係数の版の集合]；差 = p − b；削減率 = [b > 0]·(b − p)·(1/b) | D-10 | ① K ②a ②b | baseline, delta, reasons, saving, status |
| SYS-01 | 入力数値の状態判定。 | 項目ごとに状態の指示関数（欠損・導出・明示の 0・実測・推定）を作り、26 種類の項目について足す；ok = [欠損 = 0] | D-12 | ① | counts, ok, violations |
| SYS-02 | 単位整合性検証。 | 違反 = [適用][単位なし] + [適用][単位あり][記録あり][換算不可]；段階の不一致は係数ごとに数える；ok = [違反 0][不一致 0] | D-12 | ① | n_checked, ok, stage_mismatches, violations |
| SYS-03 | 係数権限ゲート。 | [適用][ID なし] + [適用][ID あり][記録なし] + Σ_f 参照数_f·[許諾なし または 出典が空] + [電力係数の許諾なし]；ok = [合計 = 0] | D-12 | ① | n_checked, n_references_affected, ok, violations |
| SYS-04 | 延床面積との面積整合。 | r = A − Σ（用途名の昇順）用途別面積；ok = [A > 0][r ≤ 1e-9·A][−r ≤ 1e-9·A] | D-12 | ① | ok, residual, status, sum |
| X-01 | 設備機器の初期製造排出。 | Σ_j [数量 ≥ 0][係数が使える]·数量·換算·係数 | D-01 | ① | by_item, n_skipped, value |
| X-02 | 段階結果ベクトルの合成。 | full_s = Σ_u M_{s,u}·v_u(T)；by_stage_s = [s が対象]·(B2 が対象外なら B6 から B2-01 を引かない)；complete = [Σ [対象][bad_u(T) ≥ 1] = 0] | D-10 | ① K ②a ②b | by_stage, by_stage_all, complete, incomplete_units |
| X-03 | 複合品の構成資材への展開。 | 構成材 f ごと：質量 = Σ_{(i,j): 係数 = f} [複合][数量 ok]·q_ord·換算·比_j、排出 = 質量·換算_j·係数_j | D-13 | ① | emission_by_component, mass_by_component, value |
| X-04 | ガス別内訳と CO2 換算の合算。 | by_gas[g] = Σ_f (Σ_s L_s[f](T))·ガス量[f,g]；値 = Σ_g GWP_g·by_gas[g] + 買電 + 冷媒；足し直し_s = Σ_f L_s[f]·値_f + 擬似の行 | D-11 | ① K ②a ②b | by_gas, by_stage_recomputed, co2e_from_gases, grid_co2e, refrigerant_co2e, value |
| X-05 | GHG 版と CO2 版の並行算定。 | CO2_s = Σ_f L_s[f](T)·CO2_f + 買電の行；値 = Σ_s [対象]·CO2_s（+ B2 の分） | D-11 | ① K ②a ②b | by_stage_co2, value |
| X-06 | 電力排出係数の年次系列の生成。 | γ_k = [一定]·start + [直線低下]·max(floor, start − decline·k) + [段階]·Σ_s [f_s ≤ k < f_{s+1}]·val_s + [整っていない]·table_k | D-07 | ① K ②a ②b | by_year, matches_table, source |
| X-07 | 経年表記（年次・累積の排出系列）。 | series_0 = 初期段階；series_y = 年次の排出·w + 事象の排出（年 y）；最終年に C 段階と B1-04；cum_y = Σ_{y' ≤ y} series_{y'} | D-11 | ① K ②a ②b | by_year, cumulative, value |
| X-08 | 更新周期別の集計。 | 周期の値 c ごと：U_c = Σ_{周期 = c の行} u、E_c = n_c(T)·U_c；明示の一覧の設備は Σ u_j·n_j(T) を別掲 | D-04 | ① ②a | by_cycle, explicit, value |
| X-09 | 廃棄物の発生品目別・処理経路別の集計。 | mass[c, ρ] = Σ_{(i,j)} [質量 ≥ 0][比率 ≥ 0]·質量·比率·[区分_i = c][経路_j = ρ]；emission は C3-01・C4-01 の項を同じキーでまとめる | D-13 | ① | emission, mass, value |
| X-10 | ライフサイクル資源量・廃棄物量の集計（単位 kg）。 | 資源量 = Σ_i [ok]·q_ord·換算·(1 + n_i(T))；廃棄物量 = Σ_i [ok]·((q_ord − q_inst)·換算 + 廃棄質量)·(1 + n_i(T)) + Σ_j [質量 ≥ 0]·質量·(1 + n_j(T)) | D-04 | ① ②a | n_excluded, resource_kg, waste_kg |
| X-11 | 床面積当たり統計値による運用エネルギーの推定。 | [面積 > 0][原単位 ≥ 0][換算可][使用許諾]·面積·原単位·換算·G(T)、G(T) = Σ_k γ_k·w_k(T) | D-07 | ① K ②a | value |
| X-12 | 積載率による輸送排出の補正。 | A4-01 の各項に [積載率 > 0]·(1/積載率) を掛ける | D-01 | ① | by_item, n_skipped, value |
| X-13 | 端材の再使用を考慮した正味の発注量。 | net = [ok][0 ≤ ρ ≤ 1]·(q_inst + (q_ord − q_inst)·(1 − ρ)) | D-01 | ① | by_item, waste_by_item |
| X-14 | 設備機器の廃棄時排出。 | Σ_j [係数が使える][廃棄質量 ≥ 0]·廃棄質量·換算·係数 | D-01 | ① | by_item, n_skipped, value |
| X-15 | 係数の検索結合と適用優先順位の解決。 | 種別 = [EPD が使える] / [¬EPD][複合][複合係数あり][kg へ換算可] / [¬EPD][単体][汎用係数が使える]；係数・換算倍率 = 種別ごとの値の排他的な和 | D-02 | ① | conv, factor, kind, n_epd_declined, n_unresolved |
| X-16 | 物価補正（費用ベース係数の基準年換算）。 | Σ_項目 [費用 ≥ 0][係数が使える][指数 > 0]·費用·(基準年の指数·1/費用年の指数)·換算·係数 | D-13 | ① | by_item, n_skipped, value |
| X-17 | 主要数量による簡易算定。 | 区分 c：fbar_c = [q_c ≠ 0]·(Σ_{i ∈ c}(a01_i + a03_i))·(1/q_c)、e_c = q_c·fbar_c；値 = Σ_c e_c | D-13 | ① | by_class, value |
