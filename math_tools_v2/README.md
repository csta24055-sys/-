# Math IR Efficient v1 — 軽量化・可変入力

**目的：既存の7エンジン検証コードを壊さず、準備と出力を減らし、固定5件以外の安全な数学問題でも利用できるようにする。** 建築LCA本業の解析コードには一切手を加えない。

## 追加：建築LCA向け4演算モード（2026-11-12）

従来のMath IR 0.1は保ったまま、**積分、区分的な時間関数、マスク付き積和、節点スペクトル候補**を実行できる専用モジュールを追加した。

- GitHub Actions：Math IR Efficient - One Job and Variable Cases の mode で **lca-operators** を選択する。case_file が既定のsix_cases.jsonなら、自動的に lca_ops_demo.jsonへ切り替える。
- 独立テスト：Math IR LCA Operators - Integral Time Mask Spectrum。
- 数式処理本体：math_tools_v2/lca_ops.py。
- 入力例：math_tools_v2/examples/lca_ops_demo.json。
- 操作方法と数学的限界：[README-operators.md](README-operators.md)。

**注意：** 新しい4演算はPython側で直接実行する機能である。旧7エンジン統合基盤は維持されているが、新しい時間・マスクASTをMATLAB/SageMathへ自動受け渡しする汎用アダプターまでは未実装。節点スペクトルの研究上の一般的同値性も未証明。

## 大幅な効率化が期待できる3点

| 変更 | 以前 | 新方式 |
|---|---|---|
| 実行ジョブ | 4ジョブ（Python→SageMath→MATLAB→照合） | **1ジョブ**。同じランナーで引き継ぐ |
| Pythonインストール | 別ジョブにて複数回 | **1回**。依存ファイルを一元化し、容量の大きいpipキャッシュを保存しない |
| 中間データ | 複数のGitHub Artifactsをアップロード・ダウンロード | **中間Artifactsなし**。最後の小さなJSONのみ1日保存 |

これらは**構造的な削減**であり、所要時間・料金の改善率は実測して判断する。SageMathのDocker取得とMATLABのセットアップは従来どおり必要で、それらの時間が必ず大幅に短縮するとは限らない。

## 選択できる3モード

GitHub Actions：`.github/workflows/math-ir-efficient.yml`

ワークフロー名：**Math IR Efficient - One Job and Variable Cases**

- **portable-python**：SymPy / NumPy / SciPy / mpmath / DuckDBだけを実行。SageMath・MATLABを起動せず、短時間の試験を優先
- **portable-full**：入力JSONの1〜20件について、Python 5種類 → SageMath → MATLABを実行し、独立の厳密値とメタデータを照合。既定の入力は`math_tools_v2/examples/six_cases.json`
- **baseline-compact**：元の第1〜5段階で確認した**合成5件・43ノード**を1ジョブで再実行。旧4ジョブ統合版と結果を比較する検証用

重要：Pythonのみのモードでも、SciPyは汎用的な入力式の積分をするのではなく、既存の`x^2`の独立数値積分試験を担当する。DuckDBは入力結果を単位ラベルごとに集計する。全7エンジンがすべての入力式を個別に処理するという意味ではない。

## 可変入力の安全な仕様

入力JSONは、`math_tools_v2/examples/`直下の既にコミットされた公開ファイルから選ぶ。

- Math IR 0.1（`phase1.check_envelope`で厳密検証）
- 1〜20ケース、入力最大64 KiB、case_id重複禁止
- 整数・有理数・記号・二項加算/乗算/整数べき乗（指数0〜8）
- 変数は有理数かつ非負の仮定、具体的な代入値が必要
- 単位ラベルは`1`または`kgCO2e`のみ
- 浮動小数への暗黙の変換なし（変換時は厳密値と誤差情報を別保存）
- **未対応の式は拒否**。ユーザー任意コード・任意数式文字列の`eval`はしない
- 入力ファイルの指定は正規表現で限定し、ディレクトリ移動を拒否

この仕様に収まる式は増やせるが、**一般の時間関数・節点スペクトル・マスク付き積和・積分演算ASTなどは未対応**。

## 実装コードと再利用関係

- `math_tools_v2/portable.py`：可変ケース数の共通入力検証、DAG生成、厳密計算・近似値の整合確認、SageMath/MATLAB照合、改ざん検出
- `math_tools_v2/requirements.txt`：5ライブラリのバージョンを一元管理（大容量キャッシュは作成しない）
- `math_tools_v2/examples/six_cases.json`：既存5式とは異なる6件のテスト
- `.github/workflows/math-ir-efficient.yml`：選択モード付き・1ジョブの実行

計算本体は従来の`math_interop_v0/phase1.py`、`phase2.py`、`phase4.CalcDAG`、MATLABの`phase3_matlab.m`を再利用する。従来の`math-ir-unified.yml`は**独立ランナー間の受け渡しを含む回帰検証として維持**する。

## CLI相当

```bash
python math_tools_v2/portable.py prepare math_tools_v2/examples/six_cases.json math_ir_io
# Pythonのみで完了するなら：
python math_tools_v2/portable.py verify-python math_ir_io
python math_tools_v2/portable.py audit-python math_ir_io
```

全7エンジンの場合、上記prepareの後に`phase1.py sage`と`phase3_matlab`が実際に`sage_result.json`/`matlab_result.json`を作成する。続いて：

```bash
python math_tools_v2/portable.py verify-full math_ir_io
python math_tools_v2/portable.py audit-full math_ir_io
```

計算結果は`math_ir_io/result.json`に集約。エンジン数・ケース数・厳密値・単位・元入力のハッシュ・Pythonキャッシュ再利用数を含む。あくまでテストの要約であり、完全な数値近似履歴はDAGキャッシュを参照する。

## 合格条件と安全上の制約

- `portable-full`で新しい6件の式をSymPy/SageMath/MATLABが厳密照合し、Python 5エンジンのDAGが動くこと
- Pythonキャッシュが同じワークフロー内の別プロセスで全件再利用されること
- SageMath計算値・MATLAB計算値・単位の3つの改ざんを実際に拒否すること
- `portable-python`がSageMath/MATLABなしで合格すること
- `baseline-compact`が既存5件・43ノードの監査に合格すること
- 元の`math_ir_unified`の検証結果を破棄しない

公開GitHubリポジトリ上のため非公開研究データを投入してはいけない。GitHub Actions成果物は1日保存であり永続キャッシュではない。単位の次元解析や、任意数式に対する数学的証明・誤差上界も未実装。
