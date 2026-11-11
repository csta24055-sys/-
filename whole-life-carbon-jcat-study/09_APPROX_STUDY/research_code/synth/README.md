# synth：架空データの建物シナリオ（検算用）

基準計算（`refcalc`）と候補モデル（`fastcalc`）が共通で読む**入力側だけ**のデータ。計算結果は一切持たない。

## データについての宣言
- すべての数値は、固定シードの乱数で作った**架空値**（`SYNTHETIC_FICTIONAL`）。J-CAT その他の実在の原単位・耐用年数・修繕率・漏洩率・倍率の表は使っていない。
- 乱数でない数値は単位の定義（1 t = 1000 kg など）だけ。
- 構造種別・用途・規模の違いは、モジュール内の架空の倍率表で表している。**このデータ上の結果は、実建物での精度について何も示さない。**

## 構成
| ファイル | 内容 |
|---|---|
| `model.py` | シナリオのデータ構造。入力 124 項目すべてを `INPUT_FIELD_MAP` で属性に対応付け（`check_input_coverage()` で検査） |
| `generate.py` | `make_scenario(seed, structure, use, size_class, study_period=60.0, dirty=False, **options)` |
| `population.py` | `standard_benchmark()`、`verification_population(n, seed)`、`edge_cases()` |
| `io.py` | JSON への保存と復元 |

## 規模区分
| 区分 | 資材行 | 設備行 | 冷媒機器 |
|---|---:|---:|---:|
| S | 200 | 60 | 5 |
| M | 2,000 | 600 | 40 |
| L | 20,000 | 6,000 | 300 |

構造は S / RC / SRC / W、用途は office / residential / school / hospital / retail / warehouse。資材行の約 30％ は 3〜12 成分の複合品。

## 主なオプション
`generate.OPTION_HELP` に全項目の説明がある。よく使うもの：`profile_kind`、`grid_kind`、`service_life_mode`（`EXACT_DIVISOR` は耐用年数が評価期間をちょうど割り切る）、`service_life_choices`、`top_up`、`epd_share`、`composite_share`、`replacement_cycle`、`reconstruction_scenario`、`results_gas_scope`、`included_stages`。
`dirty=True` は欠損・権利不明・単位不整合・比率の不整合などの欠陥をわざと入れ、入れた欠陥の一覧を `meta.injected_defects` に返す（検証式の試験用）。

## 境界条件
`edge_cases()` は、耐用年数が評価期間と等しい／割り切る／わずかにずれる／より長い、数量ゼロ、1 行だけ、行なし、全量リサイクル、漏洩率 0 と 1、回収率 0 と 1、発電量が消費量を上回る、排出係数が期間の途中で下限に達する、1 年未満・非整数の評価期間、期間内の建替・大規模改修など 31 ケースを返す。

## 再現
```
cd research_code
python3 -m unittest tests.test_synth -v
```
同じ引数からは常に同じシナリオが得られる。
