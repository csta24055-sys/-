# 共通数学データ形式・第1段階（Math IR 0.1）

このフォルダは**建築LCA研究本体とは完全に分離**した数学計算基盤の実証実験です。研究再開・実データ処理は行いません。既存の `matlab-run.yml` と `sagemath-run.yml` は変更しません。

## 今回の目的

**SymPy → 共通JSON → SageMath → 共通JSON → SymPy** の順に、厳密な数学データを引き継ぎ、結果とメタデータの損失を検証します。Claude Codeが数式や係数を文章として転記する作業は不要にします。

## v0.1仕様

- 許可する数式ノード：`integer`, `rational`, `symbol`, `add`, `mul`, `pow`。
- 整数は整数文字列として保存。有理数は既約な分子と正の分母を整数文字列として保存。
- **浮動小数点への暗黙の変換は禁止**。結果は厳密な有理数。
- 変数情報：`domain: rational`、`constraints: [nonnegative]`。ただしSageMath内部へ同じ仮定が自動適用されることは仮定せず、入力・結果に必ずメタデータとして保持する。
- 単位情報：当初は `1`（無次元）と `kgCO2e` のラベルを保持する。**次元解析は未実装**。
- 元の式・代入値・仮定・単位を含むJSON全体を失わず引き継ぎ、SHA-256で入力との一致を検証。
- 不明な演算、誤った分母、非正規な整数表記、仮定違反などは安全側に拒否。文字列の `eval` / `exec` による数式実行を行わない。

## 確認する5ケース

1. 厳密な 1/3 と単位情報の保持。
2. 負の有理数の加算。
3. `(x+1/3)^2` を境界 `x=0` で評価。
4. `(x+1/3)^2` を有理数 `x=1/7` で評価。
5. 45桁超の整数を含む式を有理数で評価。

SageMathが独立に再計算した厳密値を、SymPyが再計算した厳密値と比較する。計算結果が一致しても、数学全般について証明が成立したとは主張しません。

## 実行方法

GitHub Actions：`.github/workflows/math-ir-phase1.yml`

- 専用PRの変更に対して起動。
- Python側にSymPy 1.14.0を導入し、合成データを生成。
- SageMath 10.10の公式Dockerイメージを起動して厳密計算。
- 入力式・仮定・単位・SHA-256・厳密有理数の一致を検証。
- テスト用JSONだけを7日間の成果物として保存。

Pythonのみの事前テスト：

```bash
python -m pip install sympy==1.14.0
python math_interop_v0/phase1.py self-test
python math_interop_v0/phase1.py produce /tmp/math-ir-input.json
```

GitHub ActionsのSageMath計算が完了したら、`verify`が次のように検証します。

```bash
python math_interop_v0/phase1.py verify /tmp/math-ir-input.json /tmp/math-ir-output.json
```

## 第1段階の合格条件

**GitHub Actionsの`test-exact-transfer`が成功し、5ケースすべての厳密有理数が一致し、元の式・単位・仮定・ハッシュが維持され、破損データを拒否できること。**

**範囲外：** 一般の超越関数・区分関数・記号上の完全な等価変換・単位次元解析・MATLAB連携・大規模データ・キャッシュ・建築LCA70評価単位。

この第1段階が合格するまでは、第2～4段階へ進まない。

## 後続計画（実装しない）

1. 共通IR＋SymPy/SageMath厳密受け渡し（今回）。
2. Python内の数式・数値データ連携と型・精度の維持。
3. SageMathとMATLABの構造化入力・出力、成果物の継承。
4. 計算依存関係・キャッシュ・独立検証・再計算管理。

公開リポジトリなので非公開の研究データを試験に含めないこと。
