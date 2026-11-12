# 建築LCA向け4演算の実行モジュール（実験仕様 v0.2）

## 何を追加したか

既存の7エンジン基盤は保持し、従来の軽量版では直接扱えなかった次の計算を独立した安全なJSON入口から実行可能にする。

1. **定積分・不定積分**：制限付きASTでSymPyによる厳密積分を試み、定積分はSciPyとmpmathで数値照合。不定積分は結果を微分して元の式に戻るか検証。
2. **区分的な時間関数**：時間区間ごとの積分・境界点での値を評価。区間の重複や欠落は拒否。
3. **マスク付き積和**：元入力の数量・排出係数・マスクから厳密な有理数係数を生成。基準計算から係数を逆算しない。
4. **節点スペクトル候補**：生成した係数をIDで参照し、初期事象・周期的交換・連続排出を時間軸で計算。評価終了時点を含むか明示。

### 実行ファイル

- math_tools_v2/lca_ops.py — 本体。run INPUT OUTPUT / verify INPUT OUTPUT
- math_tools_v2/examples/lca_ops_demo.json — 合成8タスク。研究秘密は含まない
- math_tools_v2/test_lca_ops.py — 正常・異常系テスト
- .github/workflows/math-ir-lca-operators.yml — GitHub Actionsで実行可能

### CLIの例

```bash
python -m pip install -r math_tools_v2/requirements.txt
python math_tools_v2/lca_ops.py run math_tools_v2/examples/lca_ops_demo.json /tmp/lca_ops_result.json
python math_tools_v2/lca_ops.py verify math_tools_v2/examples/lca_ops_demo.json /tmp/lca_ops_result.json
python -m unittest discover -s math_tools_v2 -p 'test_lca_ops.py' -v
```

## 数学的な接続

元数量・排出係数・条件 → masked_sum_product（係数ID）→ node_spectrum（時間イベントと連続時間積分）→ 時間累積排出量。

候補式は E(T,x) = Σ_j c_j(x) K_j(T,x)。係数 c_j は必ず元入力由来。K_j に離散イベントと連続積分を含める考え方だが、本研究の正式な節点スペクトルとの一般的同値性は未証明。

### 合成例の期待値

- 数量12kg × 排出係数1/3 kgCO2e/kg = 初期係数4kgCO2e
- 交換一回4kgCO2e、周期10年、運用2kgCO2e/年、評価期間20年
- 初期時点を含み20年末の交換を除く：48kgCO2e
- 20年末の交換を含む：52kgCO2e
- 区分的時間関数2（0〜10年）・3（10〜20年）の積分：50kgCO2e

## 入力仕様

最上位：schema=lca-math-operators/0.2 と tasks（最大40件）。入力は64KiB以下。
式は許可されたASTのみ：integer/rational/symbol(t)/pi, add/sub/mul/div/pow, sin/cos/exp/log/sqrt/abs/neg。任意コードevalは禁止。
integral：expression, bounds（nullなら不定積分）, integrand_unit, variable_unit, result_unit。
time_function：segments（start/end/expression）, interval, samples, rate_unit, time_unit, result_unit。
masked_sum_product：groups（id/output_unit/terms）、terms（id/mask/factors）、各factorはvalueとunit。
node_spectrum：interval, include_start, include_end, events, periodic, rates, result_unit。係数は先に計算したmasked_sum_productのtask/group IDで参照する。

## 範囲と制約（重要）

- 7エンジン統合基盤とは独立したPython側の4演算入口。新しい積分ASTや時間モデルをSageMath/MATLABに一般転送するアダプターではない。既存7エンジン統合基盤は従来どおり存続。
- 一般積分といっても数学上あらゆる関数・特異積分の計算を保証する意味ではない。非初等関数を含め有限区間で評価できる範囲の実装。特異性が検出されれば原則拒否。
- 単位は限定された単位文字列の次元計算。全面的な単位変換・単位系統合は未実装。
- 不定積分は微分による一致を検証。時間端点の包含は事象の計上に影響するが、連続積分の値には通常影響しない。
- 現行 node_spectrum は数学的に明示した候補モデル。現在の建築LCA研究におけるすべての節点スペクトルと厳密に等価だと決めつけない。
- 大規模演算・任意モデル・70評価単位への一般適用、誤差保証の普遍性は未検証。
- GitHubリポジトリは公開。非公開研究データを投入しない。

これら4演算以外の研究本体・旧数学エンジンコードに触れない。
