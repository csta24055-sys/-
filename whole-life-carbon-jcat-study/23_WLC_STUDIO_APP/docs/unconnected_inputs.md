# 計算に反映されない入力の一覧（未接続台帳）

生成：`python3 -B -m wlcstudio ledger --md docs/unconnected_inputs.md`。プロジェクトごとの反映の有無は、結果の画面と `GET /api/projects/{id}/ledger` に出る（未取得・適用外・記録のみの理由つき）。

## 1. 入力分類（13_INPUT_CLASSIFICATION の結び付け 241 項目）のうち、4 画面から届くもの

4 画面の全項目に値があるときに作られる文書に現れる ID：**153 / 241**。

| 大分類 | 届く | 全体 |
|---|---:|---:|
| building | 16 | 31 |
| assessment | 56 | 84 |
| construction | 21 | 38 |
| operation | 48 | 76 |
| equipment | 12 | 12 |

届かない ID（画面に欄が無い、またはアプリが既定で書かないもの）：

`project.building_name`, `project.location`, `project.climate_zone`, `project.typical_floor_area`, `project.maximum_span`, `project.building_shape`, `project.roof_system`, `project.facade_system`, `project.assessor`, `project.design_stage`, `boundary.study_period`, `boundary.replacement_cycle`, `boundary.reconstruction_scope_fraction`, `boundary.functional_unit`, `boundary.baseline_scenario`, `boundary.excluded_scope_notes`, `boundary.results_gas_scope`, `summary_quantities.reinforcement_kg`, `summary_quantities.steel_kg`, `summary_quantities.concrete_m3`, `summary_quantities.timber_m3`, `summary_quantities.envelope_m2`, `summary_quantities.interior_m2`, `summary_quantities.timber_dry_density_kg_per_m3`, `summary_quantities.timber_carbon_fraction`, `summary_quantities.concrete_uptake_factor_id`, `material_life`, `epd.factor_id`, `epd.declared_stages`, `epd.declared_unit`, `epd.valid_until`, `mass_fraction`, `from_unit`, `to_unit`, `factor`, `basis`, `from_unit`, `to_unit`, `factor`, `basis`, `mass_kg`, `construction.duration_months`, `construction.temporary_works`, `operation.new_or_existing`, `operation.electricity.slope`, `operation.electricity.table`, `operation.electricity_per_m2_per_year`, `operation.gas.slope`, `operation.gas.table`, `operation.oil.slope`, `operation.oil.table`, `operation.district_heat.slope`, `operation.district_heat.table`, `operation.onsite_generation.slope`, `operation.onsite_generation.table`, `operation.onsite_export.slope`, `operation.onsite_export.table`, `operation.grid.scenario_id`, `operation.grid.annual_decline`, `operation.grid.floor`, `from_index`, `value`, `operation.grid.table`, `operation.grid.region`, `water_waste.water.slope`, `water_waste.water.table`, `water_waste.sewage.slope`, `water_waste.sewage.table`, `water_waste.municipal_waste.slope`, `water_waste.municipal_waste.table`, `activity_id`, `description`, `haul_id`, `description`, `mass_t`, `distance_km`, `item_id`, `description`, `amount`, `currency`, `price_year`, `factor_base_year`, `composition`, `construction.waste_streams`, `operation.grid.steps`, `end_of_life.demolition_activities`, `end_of_life.waste_hauls`, `cost_items`

（この 241 項目は、詳細分類 175 のうち 77 に結び付いている。残りの 98 の詳細分類はエンジンの入力が無い：12_APP_BASE の README と 13 の README を参照）

## 2. 入力画面に欄が無いエンジンの入力（理由つき）

| エンジンの入力 | 理由 |
|---|---|
| `materials[].epd.*` | EPD（製品の環境宣言）の入力欄は未実装。メーカーの EPD があっても今は反映しない。 |
| `materials[].composition` | 複合材の構成比は未実装。 |
| `materials[].unquantified_cost_ratio` | 金額だけの項目の比率は未実装。 |
| `cost_items` | 金額からの推計（X-16）は未実装。 |
| `equipment[].replacement_event_list` | 交換年の個別指定は未実装（耐用年数で周期交換とみなす）。 |
| `refrigerants[].change_years` | 冷媒の交換年の個別指定は未実装（交換周期を使う）。 |
| `construction.waste_streams` | 現場の廃棄物の内訳は未実装。 |
| `end_of_life.demolition_activities` | 解体工事（C1）の作業量は未実装。 |
| `end_of_life.waste_hauls` | 材料の行に含まれない解体材の運搬は未実装。 |
| `operation.*.LINEAR_TREND` | 年ごとに変わる運用量は未実装（一定とみなす）。 |
| `operation.grid.LINEAR_DECLINE_TO_FLOOR/STEPWISE` | 将来の排出係数の低下は未実装（一定）。 |
| `summary_quantities.timber_*` | 木材の炭素貯蔵（STO-01）の密度・炭素率は未実装。 |

## 3. 画面にあるが計算には使わない項目（記録のみ）

| 項目 | 理由 |
|---|---|
| 建物名称（`b_name`） | 記録のみ。計算には使わず、エンジンの保存にも渡さない。 |
| 所在地（`b_address`） | 住所は自動調査に使うだけで、計算と書き出しには使わない。 |
| 近くのボーリング調査（国土地盤情報）（`g_borehole`） | KuniJiban の検索サイトで調べた地点・距離・調査年を書き留める。敷地そのものの地盤ではない。 |
| 基礎の形式（`g_foundation`） | エンジンは `project.foundation_system` を読まない（記録のみ）。統計の概算の場合分けの説明に使う |
| 主な用途・構造（`b_use`・`b_structure`） | エンジンの単位は用途・構造を直接は読まない（用途別面積と、材料の行の分類を通じて効く） |

## 4. 値によっては計算に入らない場合

- 未取得・計算不能の項目：渡さない（欠損のまま。0 にしない）。材料・設備が未取得なら、その行が無いので合計に入らない（結果に「少なめ（下限）」と出る）。
- 数量の単位が参照セットの原単位と合わない材料（例：m3 の原単位しか無いのに m2）：行を作らない。
- 数量が m3・m2 の材料：質量が分からないので（密度を仮定しない）、解体時の運搬・処理（C2〜C4）のその行は不完全。
- 統計の全体量（基礎を含む）のコンクリートと、基礎のコンクリートが両方あるとき：基礎の行は作らない（二重計上の防止）。
