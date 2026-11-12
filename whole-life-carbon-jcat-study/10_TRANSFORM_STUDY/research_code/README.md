# research_code：第10章の研究用コード

数学的変換による再構成の研究のためのコード。**製品用のエンジンではない。UI・API・配布の仕組みを持たない。**
入力はすべて、旧研究の生成器（`../../09_APPROX_STUDY/research_code/synth`）が作る架空データである。

| 所在 | 役割 |
|---|---|
| `tstudy/baseline.py` | 基準計算（旧研究の公開中の版の `refcalc`）を、読み取り専用で呼ぶ。呼ぶ前に、コードが記録した版（Git のツリーの識別子）と同じであることを確かめる。同じでなければ測定を止める |
| `tstudy/scenarios.py` | 架空シナリオの集合（変換を作るための集合、評価だけに使う集合、境界条件、標準ベンチマーク）と、基準計算の値を正として使える入力かどうかの判定 |
| `tstudy/metrics.py` | 誤差の統計（符号つき平均、絶対値の平均、95％点、最大、最悪の例、基準が 0 の件数）と、段階の値を置き換えたときの合計への波及 |
| `checks/` | 上の動作の確認 |

実行は `research_code` で行う。基準計算のフォルダに `__pycache__` を作らないよう、`-B` を付ける。

```
python3 -B -m checks.check_baseline
```

基準計算と生成器のコードは書き換えない。このフォルダのコードは、`09_APPROX_STUDY/` に何も書き込まない。

## 候補と実験のコード

| 所在 | 役割 |
|---|---|
| `tstudy/rampstep.py`、`tstudy/knots.py` | 評価期間への依存の共通の形（ゲート付きのクリップ・ランプ）と、その節点スペクトル（累積和と二分探索） |
| `tstudy/tables.py` | シナリオを表（列）に直す前処理。入力の型だけを見る。評価単位の知識を持たない |
| `tstudy/msp.py` | マスク付き積和の演算子（候補 TC-B-01）。評価単位による分岐を持たない |
| `specs/pre_a.py` | 製品段階・輸送・施工の 18 単位の仕様（データだけ） |
| `checks/check_msp_pre_a.py` | 演算子と仕様の検査（基準計算との照合、故障注入、語彙の記録、時間） |
| `experiments/exp01〜exp04` | 実験 EXP-01〜04（`../03_ROUTES/experiments/README.md`） |
| `experiments/expA1_route_a_recount.py` | ルート A（旧研究の統合モデル）の数え直し。旧研究のコードは読み込むだけで、書き換えない |
| `tools_render_ledgers.py` | 調査台帳と分類台帳の文書を、元のデータから作る（計算はしない） |

```
python3 -B -m checks.check_msp_pre_a
python3 -B -m experiments.exp01_rampstep_sweep 60 M
python3 -B -m experiments.exp02_knot_spectrum 30 M L
python3 -B -m experiments.exp03_fourier_counting 40 M
python3 -B -m experiments.exp04_pod_time_curves 100 M
```

## 統合系（2026-11-13）

全 70 単位を、共通表 → 積和① → 節点スペクトル → 積和② で計算する。説明と結果は [../11_UNIFIED_SYSTEM/](../11_UNIFIED_SYSTEM/README.md)。

| 所在 | 役割 |
|---|---|
| `tstudy/index.py` | 共通表：文字列の分割、添字集合、節点の格子（評価単位の知識を持たない一般の操作） |
| `tstudy/interval.py` | 節点スペクトルの区間形（冷媒の期末残存量） |
| `tstudy/unified.py` | 統合系の本体 `System`。基準計算を読まない |
| `specs/lib.py` | 仕様を書くための短縮記法と共通テンプレート |
| `specs/physical.py` | 解体・廃棄、使用段階の振幅、事象の表、運用、冷媒、排出の行（データだけ） |
| `specs/gates.py` | 検査・状態・単位と権限のゲート、集計表（データだけ） |
| `specs/at_t.py` | 時刻 T での 2 つのプログラム（TIME、AGG） |
| `specs/system.py` | 全体の組み立て：共通表の計画、積和①、節点への受け渡し、静的な表 |
| `checks/sets_unified.py`、`checks/check_unified.py` | 検証の集合と、全 70 単位・全出力の比較 |
| `checks/check_unified_controls.py` | 誤り検出の確認、QA-01 の故障注入、構造の確認 |
| `experiments/expU1_b14_forms.py`、`expU2_cross_engines.py` | B1-04 の 3 表現（mpmath）、別エンジンでの照合（SymPy、SciPy、DuckDB、lca_ops） |
| `tools_unit_map.py`、`tools_units_doc.py`、`tools_verification_report.py`、`tools_example.py` | 追跡表・定義表・検証報告・全出力の実例の生成 |
| `recovered_2026-11-12/` | 2026-11-12 の一時スクリプト（記録から復元。実行用ではない） |

```
python3 -B -m checks.check_unified --quick
python3 -B -m checks.check_unified
python3 -B -m checks.check_unified_controls
```
