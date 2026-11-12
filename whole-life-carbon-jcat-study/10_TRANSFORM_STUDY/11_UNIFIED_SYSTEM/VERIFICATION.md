# 検証結果（全70評価単位、基準計算との総当たり比較）

`research_code/tools_verification_report.py` が `results/*.json` から生成した。数値はすべて架空データ・独立概念モデルでのもので、
確認者は実装者のみ（証拠水準 N：数値の一致）。証明ではなく、他のツールとの整合を示すものでもない。

比較の規則（`checks/check_msp_pre_a.py` の `compare`。緩めていない）：数値は相対差 1e-9 以内、基準計算が厳密に 0 の値は厳密に 0、
真偽値・整数・文字列・一覧・辞書のキーは型を含めて完全一致。70 単位の公開出力キーをすべて、要素ごとに比べる。

## 1. 集合ごとの結果

| 集合 | 内容 | 組 | 除外 | 失敗 | 単位 | キー | 比較した値 | 不一致 | 最大相対差（単位） | SUM-03 p95 / 最大 | 段階 p95 の最大 / 段階の最大 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `dev_design` | 調整用：設計用集合 40 件 × 4 期間 | 160 | 0 | 0 | 70 | 190 | 3,401,110 | 0 | 2.2e-12（X-13） | 1.7e-14 / 3.3e-14 | 1.0e-13 / 2.4e-13 |
| `dev_edge` | 調整用：名前付き境界条件 32 件 × 2 期間 | 62 | 2 | 0 | 70 | 190 | 80,726 | 0 | 1.8e-13（X-02） | 4.1e-15 / 5.0e-15 | 2.0e-14 / 1.8e-13 |
| `rep_evaluation` | 再現：評価用集合 60 件 × 5 期間 | 300 | 0 | 0 | 70 | 190 | 5,501,050 | 0 | 2.2e-12（X-13） | 2.2e-14 / 8.3e-14 | 1.5e-13 / 4.8e-13 |
| `rep_boundary` | 再現：境界の評価期間（S・評価用 3 件・M） | 46 | 0 | 0 | 70 | 190 | 556,874 | 0 | 1.3e-12（X-13） | 1.1e-14 / 2.4e-14 | 7.9e-14 / 1.2e-13 |
| `rep_constructed` | 再現：特殊条件 115 件 × 3 期間 | 345 | 0 | 0 | 70 | 190 | 6,644,651 | 0 | 1.4e-12（X-13） | 1.5e-14 / 4.3e-14 | 7.1e-14 / 2.0e-13 |
| `rep_scale_L` | 再現：最大規模 L × 2 期間 | 2 | 0 | 0 | 70 | 190 | 864,434 | 0 | 2.2e-12（X-13） | 1.0e-13 / 1.0e-13 | 5.7e-13 / 5.7e-13 |
| `rep_defects` | 再現：欠陥入り 12 件 × 2 期間（有効範囲外） | 24 | 0 | 0 | 70 | 188 | 437,348 | 0 | 5.0e-13（X-13） | 7.4e-15 / 8.5e-15 | 3.2e-14 / 3.5e-14 |
| `new_population` | 新規：別シードの母集団 40 件 × 6 期間 | 240 | 0 | 0 | 70 | 190 | 3,157,069 | 0 | 1.7e-12（X-13） | 1.2e-14 / 3.8e-14 | 7.6e-14 / 2.5e-13 |
| `new_defects` | 新規：欠陥入り 12 件 × 2 期間（有効範囲外） | 24 | 0 | 0 | 70 | 188 | 443,865 | 0 | 1.3e-12（X-13） | 1.1e-14 / 1.3e-14 | 8.7e-14 / 1.1e-13 |
| `new_special` | 新規：追加単位向けの特殊条件 × 3 期間（有効範囲外を含む） | 90 | 0 | 0 | 70 | 188 | 1,611,275 | 0 | 1.2e-12（X-13） | 7.0e-15 / 8.4e-15 | 5.0e-14 / 5.0e-14 |

合計：1,293 組、比較した値 22,698,402 個、不一致 0、失敗 0、除外 2。
内訳：調整用 222 組、再現 717 組（うち欠陥入り 24 組を除く 693 組が 2026-11-12 の「調整に使っていない 693 組」と同じ条件）、新規 354 組。

除外・注記：
- `dev_edge`：excluded edge life_near_divisor T=60.0: material M000002.material_life: an event time lies on a knife edge of the time rule
- `dev_edge`：excluded edge life_near_divisor T=42.5: material M000002.material_life: an event time lies on a knife edge of the time rule

## 2. 単位ごとの結果（全集合の合計）

「ビット一致」は、0 でない数値のうち基準計算と倍精度で完全に同じ値だった割合。

| 単位 | 出力キー | 比較した値 | 不一致 | 最大相対差 | ビット一致 |
|---|---|---|---|---|---|
| A13-01 | by_item, n_skipped, value | 985,684 | 0 | 4.7e-16 | 83.4% |
| A13-02 | by_item, n_invalid | 984,391 | 0 | 0.0e+00 | 100.0% |
| A13-03 | by_item, n_skipped, value | 985,684 | 0 | 4.0e-16 | 83.4% |
| A13-04 | by_item, n_skipped, value | 985,684 | 0 | 5.5e-16 | 84.8% |
| A13-05 | n_skipped, q_inst, q_ord | 1,967,489 | 0 | 2.2e-16 | 90.3% |
| A4-01 | by_item, n_skipped, value | 985,684 | 0 | 0.0e+00 | 100.0% |
| A4-02 | by_item, n_skipped, value | 985,684 | 0 | 4.2e-16 | 83.4% |
| A5-01 | computed, value | 2,586 | 0 | 0.0e+00 | 100.0% |
| A5-02 | n_skipped, value | 2,586 | 0 | 0.0e+00 | 100.0% |
| A5-03 | n_skipped, value | 2,586 | 0 | 0.0e+00 | 100.0% |
| A5-04 | other_assessed, parts, value | 6,465 | 0 | 0.0e+00 | 100.0% |
| B1-01 | n_skipped, value | 2,586 | 0 | 0.0e+00 | 100.0% |
| B1-02 | by_item, by_year, n_skipped, value | 89,243 | 0 | 3.5e-15 | 71.2% |
| B1-03 | by_year, n_skipped, value | 68,687 | 0 | 2.6e-14 | 42.6% |
| B1-04 | n_skipped, value | 2,586 | 0 | 4.0e-15 | 35.7% |
| B2-01 | computed, value | 2,586 | 0 | 2.9e-15 | 28.8% |
| B3-01 | by_year, n_skipped, value | 68,687 | 0 | 5.7e-13 | 20.0% |
| B3-02 | n_skipped, value | 2,586 | 0 | 4.3e-15 | 21.5% |
| B4-01 | events, n_events | 621,703 | 0 | 0.0e+00 | 100.0% |
| B4-02 | by_item_equipment, by_item_material, by_year, n_partial, value | 1,346,855 | 0 | 8.3e-15 | 88.7% |
| B4-03 | by_item | 983,098 | 0 | - | - |
| B5-01 | by_year, computed, n_events, value | 69,980 | 0 | 2.2e-16 | 89.7% |
| B6-01 | by_year, computed | 67,394 | 0 | 0.0e+00 | 100.0% |
| B6-02 | by_year, descriptors_match_tables, n_skipped | 68,687 | 0 | 0.0e+00 | 100.0% |
| B6-03 | value | 1,293 | 0 | 3.2e-15 | 23.7% |
| B6-04 | by_year, computed, descriptors_match_tables | 68,687 | 0 | 0.0e+00 | 100.0% |
| B7-01 | by_year, descriptors_match_tables, n_skipped | 68,687 | 0 | 0.0e+00 | 100.0% |
| B7-02 | by_year, descriptors_match_tables, n_skipped | 68,687 | 0 | 0.0e+00 | 100.0% |
| B7-03 | by_year, descriptors_match_tables, n_skipped | 68,687 | 0 | 0.0e+00 | 100.0% |
| B7-04 | value | 1,293 | 0 | 2.5e-15 | 19.3% |
| C-05 | n_mass_unchecked, ok, under_allocated, violations | 3,402 | 0 | - | - |
| C1-01 | n_skipped, value | 2,586 | 0 | 0.0e+00 | 100.0% |
| C2-01 | by_item, n_skipped, value | 985,684 | 0 | 5.0e-16 | 89.1% |
| C3-01 | by_item, n_routes_skipped, n_skipped, value | 986,977 | 0 | 0.0e+00 | 100.0% |
| C4-01 | by_item, n_routes_skipped, n_skipped, value | 986,977 | 0 | 0.0e+00 | 100.0% |
| QA-01 | ok, violations | 1,293 | 0 | - | - |
| QA-02 | ok, violations, warnings | 20,479 | 0 | - | - |
| QA-03 | n_used, ok, violations | 2,610 | 0 | - | - |
| QA-04 | ok, status | 2,586 | 0 | - | - |
| STO-01 | value | 1,293 | 0 | 0.0e+00 | 100.0% |
| STO-02 | value | 1,293 | 0 | 0.0e+00 | 100.0% |
| SUM-01 | complete, value | 2,586 | 0 | 2.5e-16 | 84.7% |
| SUM-02 | complete, value | 2,586 | 0 | 1.1e-13 | 4.0% |
| SUM-03 | complete, value | 2,586 | 0 | 1.0e-13 | 4.7% |
| SUM-04 | value | 1,293 | 0 | 1.0e-13 | 4.3% |
| SUM-05 | value | 1,293 | 0 | 1.0e-13 | 3.9% |
| SUM-06 | value | 1,293 | 0 | 1.0e-13 | 4.3% |
| SUM-07 | by_stage, defined | 19,171 | 0 | 4.7e-13 | 3.6% |
| SUM-08 | baseline, delta, reasons, saving, status | 4,309 | 0 | 1.3e-13 | 7.6% |
| SYS-01 | counts, ok, violations | 9,137 | 0 | - | - |
| SYS-02 | n_checked, ok, stage_mismatches, violations | 3,534 | 0 | - | - |
| SYS-03 | n_checked, n_references_affected, ok, violations | 4,321 | 0 | - | - |
| SYS-04 | ok, residual, status, sum | 5,172 | 0 | 0.0e+00 | 100.0% |
| X-01 | by_item, n_skipped, value | 297,656 | 0 | 0.0e+00 | 100.0% |
| X-02 | by_stage, by_stage_all, complete, incomplete_units | 38,037 | 0 | 5.7e-13 | 59.8% |
| X-03 | emission_by_component, mass_by_component, value | 114,465 | 0 | 4.8e-16 | 86.2% |
| X-04 | by_gas, by_stage_recomputed, co2e_from_gases, grid_co2e, refrigerant_co2e, value | 32,325 | 0 | 7.1e-14 | 17.9% |
| X-05 | by_stage_co2, value | 19,395 | 0 | 2.4e-14 | 24.7% |
| X-06 | by_year, matches_table, source | 68,687 | 0 | 0.0e+00 | 100.0% |
| X-07 | by_year, cumulative, value | 133,495 | 0 | 3.0e-15 | 58.6% |
| X-08 | by_cycle, explicit, value | 1,001,487 | 0 | 2.5e-15 | 89.2% |
| X-09 | emission, mass, value | 132,949 | 0 | 0.0e+00 | 100.0% |
| X-10 | n_excluded, resource_kg, waste_kg | 3,879 | 0 | 4.7e-15 | 49.7% |
| X-11 | value | 1,293 | 0 | 4.0e-15 | 24.3% |
| X-12 | by_item, n_skipped, value | 985,684 | 0 | 4.3e-16 | 76.3% |
| X-13 | by_item, waste_by_item | 1,966,196 | 0 | 2.2e-12 | 83.4% |
| X-14 | by_item, n_skipped, value | 297,656 | 0 | 0.0e+00 | 100.0% |
| X-15 | conv, factor, kind, n_epd_declined, n_unresolved | 2,951,880 | 0 | 0.0e+00 | 100.0% |
| X-16 | by_item, n_skipped, value | 9,755 | 0 | 4.1e-16 | 62.2% |
| X-17 | by_class, value | 24,567 | 0 | 5.1e-16 | 81.3% |

単位 70、出力キー 190。最大相対差の大きい順：X-13 2.2e-12、X-02 5.7e-13、B3-01 5.7e-13、SUM-07 4.7e-13、SUM-08 1.3e-13、SUM-02 1.1e-13。

## 3. 精度の基準との対比

暫定基準：ホールライフ合計（SUM-03）の相対誤差の 95 パーセンタイルが 1％以内、段階別が 2％以内。比較基準：2026-11-12 の最大相対差 5.7e-13。

| 集合 | SUM-03 の組数 | SUM-03 p95 | SUM-03 最大 | 段階 p95 の最大 | 段階の最大 |
|---|---|---|---|---|---|
| `dev_design` | 160 | 1.7e-14 | 3.3e-14 | 1.0e-13 | 2.4e-13 |
| `dev_edge` | 62 | 4.1e-15 | 5.0e-15 | 2.0e-14 | 1.8e-13 |
| `rep_evaluation` | 300 | 2.2e-14 | 8.3e-14 | 1.5e-13 | 4.8e-13 |
| `rep_boundary` | 46 | 1.1e-14 | 2.4e-14 | 7.9e-14 | 1.2e-13 |
| `rep_constructed` | 339 | 1.5e-14 | 4.3e-14 | 7.1e-14 | 2.0e-13 |
| `rep_scale_L` | 2 | 1.0e-13 | 1.0e-13 | 5.7e-13 | 5.7e-13 |
| `rep_defects` | 24 | 7.4e-15 | 8.5e-15 | 3.2e-14 | 3.5e-14 |
| `new_population` | 240 | 1.2e-14 | 3.8e-14 | 7.6e-14 | 2.5e-13 |
| `new_defects` | 24 | 1.1e-14 | 1.3e-14 | 8.7e-14 | 1.1e-13 |
| `new_special` | 90 | 7.0e-15 | 8.4e-15 | 5.0e-14 | 5.0e-14 |

## 4. 検査が実際に働いた回数（基準計算側の値の内訳）

真偽値が常に真、一覧が常に空のままでは一致に意味がないので、基準計算の値の内訳を数えた。

| 出力 | 内訳 |
|---|---|
| A13-01/by_item | empty 2、non-empty 1291 |
| A13-02/by_item | empty 2、non-empty 1291 |
| A13-03/by_item | empty 2、non-empty 1291 |
| A13-04/by_item | empty 2、non-empty 1291 |
| A13-05/q_inst | empty 2、non-empty 1291 |
| A13-05/q_ord | empty 2、non-empty 1291 |
| A4-01/by_item | empty 2、non-empty 1291 |
| A4-02/by_item | empty 2、non-empty 1291 |
| A5-01/computed | = False 27、= True 1266 |
| A5-04/other_assessed | = False 1293 |
| A5-04/parts | non-empty 1293 |
| B1-02/by_item | empty 2、non-empty 1291 |
| B1-02/by_year | non-empty 1293 |
| B1-03/by_year | non-empty 1293 |
| B2-01/computed | = False 12、= True 1281 |
| B3-01/by_year | non-empty 1293 |
| B4-01/events | empty 2、non-empty 1291 |
| B4-02/by_item_equipment | empty 2、non-empty 1291 |
| B4-02/by_item_material | empty 2、non-empty 1291 |
| B4-02/by_year | non-empty 1293 |
| B4-02/n_partial | = 0 1221、> 0 72 |
| B4-03/by_item | empty 2、non-empty 1291 |
| B5-01/by_year | non-empty 1293 |
| B5-01/computed | = False 6、= True 1287 |
| B6-01/by_year | non-empty 1293 |
| B6-01/computed | = False 54、= True 1239 |
| B6-02/by_year | non-empty 1293 |
| B6-02/descriptors_match_tables | = False 2、= True 1291 |
| B6-04/by_year | non-empty 1293 |
| B6-04/computed | = False 27、= True 1266 |
| B6-04/descriptors_match_tables | = False 6、= True 1287 |
| B7-01/by_year | non-empty 1293 |
| B7-01/descriptors_match_tables | = False 3、= True 1290 |
| B7-02/by_year | non-empty 1293 |
| B7-02/descriptors_match_tables | = True 1293 |
| B7-03/by_year | non-empty 1293 |
| B7-03/descriptors_match_tables | = True 1293 |
| C-05/ok | = False 69、= True 1224 |
| C-05/under_allocated | empty 1253、non-empty 40 |
| C-05/violations | empty 1224、non-empty 69 |
| C2-01/by_item | empty 2、non-empty 1291 |
| C3-01/by_item | empty 2、non-empty 1291 |
| C4-01/by_item | empty 2、non-empty 1291 |
| QA-01/ok | = True 1293 |
| QA-02/ok | = False 628、= True 665 |
| QA-02/violations | empty 665、non-empty 628 |
| QA-02/warnings | empty 1275、non-empty 18 |
| QA-03/n_used | > 0 1293 |
| QA-03/ok | = False 9、= True 1284 |
| QA-03/violations | empty 1284、non-empty 9 |
| QA-04/ok | = False 66、= True 1227 |
| SUM-01/complete | = False 183、= True 1110 |
| SUM-02/complete | = False 183、= True 1110 |
| SUM-03/complete | = False 183、= True 1110 |
| SUM-04/value | is None 16 |
| SUM-05/value | is None 16 |
| SUM-07/by_stage | empty 6、non-empty 1287 |
| SUM-07/defined | = False 6、= True 1287 |
| SUM-08/delta | is None 1210 |
| SUM-08/reasons | non-empty 291 |
| SUM-08/saving | is None 1210 |
| SYS-01/counts | non-empty 1293 |
| SYS-01/ok | = False 102、= True 1191 |
| SYS-01/violations | empty 1191、non-empty 102 |
| SYS-02/ok | = False 102、= True 1191 |
| SYS-02/stage_mismatches | empty 1275、non-empty 18 |
| SYS-02/violations | empty 1200、non-empty 93 |
| SYS-03/ok | = False 84、= True 1209 |
| SYS-03/violations | empty 1209、non-empty 84 |
| SYS-04/ok | = False 66、= True 1227 |
| SYS-04/residual | is None 16 |
| X-01/by_item | empty 2、non-empty 1291 |
| X-02/by_stage | non-empty 1293 |
| X-02/by_stage_all | non-empty 1293 |
| X-02/complete | = False 183、= True 1110 |
| X-02/incomplete_units | empty 1110、non-empty 183 |
| X-03/emission_by_component | empty 8、non-empty 1285 |
| X-03/mass_by_component | empty 8、non-empty 1285 |
| X-04/by_gas | non-empty 1293 |
| X-04/by_stage_recomputed | non-empty 1293 |
| X-05/by_stage_co2 | non-empty 1293 |
| X-06/by_year | non-empty 1293 |
| X-06/matches_table | = False 10、= True 1283 |
| X-07/by_year | non-empty 1293 |
| X-07/cumulative | non-empty 1293 |
| X-08/by_cycle | empty 18、non-empty 1275 |
| X-09/emission | empty 2、non-empty 1291 |
| X-09/mass | empty 2、non-empty 1291 |
| X-11/value | is None 49 |
| X-12/by_item | empty 2、non-empty 1291 |
| X-13/by_item | empty 2、non-empty 1291 |
| X-13/waste_by_item | empty 2、non-empty 1291 |
| X-14/by_item | empty 2、non-empty 1291 |
| X-15/conv | empty 2、non-empty 1291 |
| X-15/factor | empty 2、non-empty 1291 |
| X-15/kind | empty 2、non-empty 1291 |
| X-16/by_item | non-empty 1293 |
| X-17/by_class | non-empty 1293 |

状態の内訳：QA-04/status = EVALUATED 1277、QA-04/status = NOT_EVALUATED 16、SUM-08/status = COMPARED 83、SUM-08/status = NOT_COMPARABLE 291、SUM-08/status = NO_BASELINE 919、SYS-04/status = EVALUATED 1277、SYS-04/status = INVALID 16、X-06/source = DESCRIPTOR 988、X-06/source = TABLE 305

## 5. 誤り検出の確認

仕様を 1 か所ずつわざと壊し、比較がその単位の不一致を報告するかを確かめた（24 件中 24 件で検出）。

| 壊した内容 | 検出を期待した単位 | 結果 | 不一致が出た単位 |
|---|---|---|---|
| SYS-01: a derived value counted only when it is zero | SYS-01 | 検出 | SYS-01 |
| SYS-02: a wrong stage of a factor does not fail the check | SYS-02 | 検出 | SYS-02 |
| SYS-02: stage mismatches of the generic material factors not listed | SYS-02 | 検出 | SYS-02 |
| SYS-03 / QA-03: an empty source accepted | SYS-03, QA-03 | 検出 | QA-03, SYS-03 |
| QA-03: lines of a renewal counted before any renewal | QA-03 | 検出 | QA-03 |
| X-04 / X-05: rebuild lines of the end-of-life stages dropped | X-04, X-05 | 検出 | QA-01, X-04, X-05 |
| X-05: CO2e value instead of the CO2 amount in stage B4 | X-05 | 検出 | X-05 |
| X-07: end-of-life stages and end residual not placed in the last year | X-07 | 検出 | X-07 |
| X-08: cycle values without a contributing row listed | X-08 | 検出 | X-08 |
| X-09: negative route fractions summed | X-09 | 検出 | X-09 |
| B4-03: a renewal exactly at the end of the period counted | B4-03 | 検出 | B3-01, B4-02, B4-03, QA-01, X-04, X-05, X-07, X-10 |
| B3-01 per year: repairs not skipped in a renewal year | B3-01 | 検出 | B3-01, X-07 |
| X-04: gas amounts replaced by 1 | X-04 | 検出 | X-04 |
| SUM-05: not divided by the study period | SUM-05 | 検出 | SUM-05 |
| B1-04 in the jump form under 35 % leak without replacement (known limit, EXP-U1) | B1-04 | 検出 | B1-04 |
| refrigerant: resolvent truncated to 3 factors | B1-02 | 検出 | B1-02, B1-03, B1-04, SUM-02, SUM-03, SUM-04, SUM-05, SUM-06 … |
| refrigerant: resets ignored | B1-02, B1-04 | 検出 | B1-02, B1-03, B1-04, SUM-02, SUM-03, SUM-04, SUM-05, SUM-06 … |
| refrigerant: every event treated as the first of its year | B1-03 | 検出 | B1-03, SUM-02, SUM-03, SUM-04, SUM-05, SUM-06, SUM-07, X-02 … |
| grid factor: floor of the linear decline dropped | X-06 | 検出 | B2-01, B6-01, B6-03, SUM-02, SUM-03, SUM-04, SUM-05, SUM-06 … |
| grid factor: stepwise without the upper bound of a step | X-06 | 検出 | B2-01, B6-01, B6-03, SUM-02, SUM-03, SUM-04, SUM-05, SUM-06 … |
| purchased electricity without max(0, .) | B6-04 | 検出 | B2-01, B6-01, B6-03, B6-04, SUM-02, SUM-03, SUM-04, SUM-05 … |
| annual profiles: linear trend dropped | B6-04 | 検出 | B2-01, B6-01, B6-02, B6-03, B6-04, B7-01, B7-02, B7-03 … |
| incomplete-renewal flag without three of its conditions | B4-02 | 検出 | B4-02 |
| C-05 without the sum-of-fractions test | C-05 | 検出 | C-05 |

QA-01 は入力では違反を起こせない（導出文書 D-12）。上流の結果を両側で同じように偽って、基準計算の関数と同じ違反一覧になるかを確かめた（4 件中 4 件で一致し、どれも不合格）。

| 偽った内容 | 一致 | 基準計算の違反一覧 |
|---|---|---|
| (b) A13-01 and A13-03 both counted on three rows | 一致 | materials[0] A13-01/A13-03; materials[1] A13-01/A13-03; materials[2] A13-01/A13-03 |
| (c) A4-01 and A4-02 both counted on two rows | 一致 | materials[2] A4-01/A4-02; materials[3] A4-01/A4-02 |
| (a) stage values of B4 and C2 falsified | 一致 | stage B4; stage C2 |
| (a), (b) and (c) together | 一致 | stage B4; stage C2; materials[0] A13-01/A13-03; materials[1] A13-01/A13-03; materials[2] A13-01/A13-03 |

構造の確認：仕様 3 本はデータのみ（JSON にできる）＝True、エンジン・平坦化・節点スペクトル・核・18 単位の仕様はコミット済みのまま＝True、統合モジュールは基準計算を読まない＝True。
ステップ数：P1 {'sp': 1358, 'match': 170}、TIME {'sp': 95}、AGG {'match': 10, 'sp': 156}。使っている関数：fn:inv, fn:inv_one_minus, fn:one_minus, fn:ratio_one_minus。エンジンの語彙の外の要素：なし。

## 6. 別エンジンによる照合

EXP-U1（mpmath 60 桁を真値とする B1-04 の 3 表現、45 条件）：最大相対誤差は 基準計算 4.6e-16、跳び形 6.1e+21、区間形 6.6e-15、局所形（積和）6.7e-15。

EXP-U2：
- SymPy（厳密）：n=8, 3 factors, symbolic weights → True；n=16, 4 factors, symbolic weights → True；exact rationals: 40 random devices (40, 130, 200 years), entries that differ → 0
- SciPy（疎な三角解、ベンチマーク M、未知数 5200）：積和 8 段との最大相対差 1.9e-15
- DuckDB（SQL での再集計、ベンチマーク M）：X-09 mass by class and route → {"cells": 52, "max_rel_difference": 0.0}；B4-03 renewals per row at T=62.5 → {"rows": 2000, "rows_that_differ": 0}；year-weighted purchased-electricity emission at T=62.5 → {"sql": 33896824.93951324, "knot_spectrum": 33896824.93951324, "rel_difference": 0.0}
- main の `math_tools_v2/lca_ops.py`（厳密な有理数）：T=4 厳密値 608/15、相対差 1.8e-16；T=15/4 厳密値 4819/120、相対差 1.8e-16；T=5/2 厳密値 97/20、相対差 0.0e+00；T=1/2 厳密値 21/20、相対差 0.0e+00
- 版：{"numpy": "2.5.4", "sympy": "1.14.0", "scipy": "1.18.1", "mpmath": "1.3.0", "duckdb": "2.0.0", "python": "3.13.18"}

- sagemath（GitHub Actions、実行 ID 43199948838、success）：{"resets": 6, "product_times_I_minus_N_is_identity": true, "N_nilpotent": true, "inverse_equals_product": true, "recurrence_equals_product": true}
- matlab（GitHub Actions、実行 ID 43199960240、success）：{"resets": 10, "max_rel_solve_vs_product": 2.285e-16, "max_rel_recurrence_vs_product": 2.285e-16, "norm_N_pow_256": 0.0, "year_weight_sum": 31.7421417979727, "closed_form_of_the_same_sum": 31.7421417979727}

