# 再実行手順

## 1. 必要なもの

- Python 3 と NumPy（検証を行った環境：Python 3.13.18、NumPy 2.5.3）。本体と検証はこれだけで動く。
- Git（基準計算が凍結した版であることを、ツリーの識別子で確かめる）。
- 別エンジンの照合だけ：SymPy、SciPy、mpmath、DuckDB（行った環境：Python 3.13.18、SymPy 1.14.0、SciPy 1.18.1、mpmath 1.3.0、DuckDB 2.0.0、NumPy 2.5.4）。
- 入力ファイルは要らない。入力は凍結した生成器（`09_APPROX_STUDY/research_code/synth`）がシードから再生成する架空データである。

## 2. 手順（`whole-life-carbon-jcat-study/10_TRANSFORM_STUDY/research_code` で実行）

`-B` と `PYTHONDONTWRITEBYTECODE=1` は、凍結したフォルダに `__pycache__` を作らないために付ける。

```bash
export PYTHONDONTWRITEBYTECODE=1
python3 -B -m checks.check_baseline                 # 基準計算が凍結した版であること
python3 -B -m checks.check_unified --quick          # 約 5 秒：ベンチマーク S × 3 期間と境界条件 31 件、全 70 単位
python3 -B -m checks.check_unified                  # 約 6 分：全 10 集合（1,293 組）
python3 -B -m checks.check_unified rep_evaluation   # 集合を名前で選ぶこともできる
python3 -B -m checks.check_unified_controls         # 約 3 分：誤り検出 24 件、QA-01 の故障注入 4 件、構造の確認
python3 -B tools_unit_map.py                        # UNIT_MAP.md、results/unit_map.json
python3 -B tools_units_doc.py                       # UNITS_70.md
python3 -B tools_verification_report.py             # VERIFICATION.md
python3 -B tools_example.py                         # results/example_benchmark_S_T62.5.json（70 単位の全出力の実例）
```

別エンジンの照合：

```bash
PY=$HOME/.lca-math/bin/python                        # SymPy・SciPy・mpmath・DuckDB の入った環境
$PY -B -m experiments.expU1_b14_forms                # B1-04 の 3 表現と mpmath 60 桁の真値
git show origin/main:math_tools_v2/lca_ops.py > /tmp/lca_ops.py       # main の 4 演算モジュール（コミット c3b0fb3 で確認）
$PY -B -m experiments.expU2_cross_engines /tmp/lca_ops.py             # SymPy・SciPy・DuckDB・lca_ops
```

SageMath と MATLAB は、main の GitHub Actions（`sagemath-run.yml`、`matlab-run.yml`）を `workflow_dispatch` で起動し、入力 `command` に
`results/external_engines.json` の `command` を渡す。結果はジョブのログの `=== RESULT BEGIN ===` と `=== RESULT END ===` の間に出る。

## 3. 期待される結果

- `check_unified` の各行の末尾が `mismatches 0`、最後が `TOTAL mismatches + failures: 0`。終了コード 0。
- `check_unified_controls` の最後が `SUMMARY {'controls': 24, 'controls_detected': 24, 'qa01_cases': 4, 'qa01_agree_and_fail': 4}`。
- 結果は `11_UNIFIED_SYSTEM/results/` に JSON で書かれる。実行時間（`seconds` で始まるキー）以外は、再実行で同じになる。

1 組だけ計算する例：

```python
from tstudy import baseline, scenarios, unified
baseline.assert_frozen(); baseline.load()
from synth import population
scn = scenarios.benchmark()[0]                               # 架空のベンチマーク S
system = unified.System(scn, baselines=population.BASELINES)  # 共通表 → 積和① → 節点スペクトル
res = system.at(62.5)                                        # 評価期間 62.5 年の 70 単位
print(res["SUM-03"], res["B1-04"], res["QA-02"])
```

## 4. 保存したコードからの再生成の確認

コミットした内容だけを別の場所に取り出して（`git worktree add`）、`check_unified --quick`、`check_unified rep_boundary rep_scale_L new_special`、
`check_unified_controls` を実行し、結果の JSON が作業フォルダのものと（実行時間を除いて）同じであることを確かめた。確認の記録は `results/reproduction_check.json`。
