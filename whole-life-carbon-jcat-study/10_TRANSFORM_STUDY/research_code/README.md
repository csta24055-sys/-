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
