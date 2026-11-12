# 第3段階：SageMath→MATLABの構造化数学データ受け渡し

研究本体とは分離した実証実験。第1段階の制限付き Math IR 0.1 と厳密有理数の合成データ5件を使用する。

## 入力・出力フロー

1. Pythonが入力 `input.json` と系譜・単位・仮定をハッシュ化した `manifest.json` を生成。
2. GitHub ActionsのArtifactを介してSageMath 10.10へ渡す。
3. SageMathが構造化された厳密有理数 `sage_result.json` を出力。
4. 別のGitHub Actionsジョブが成果物をダウンロード。
5. MATLAB + Symbolic Math Toolboxが **SageMath結果を実際に読み込み**、同じ元式をMATLAB自身でも独立に計算。両者が一致しない場合は失敗。
6. MATLABが `matlab_result.json` を生成。
7. Python/SymPyが各演算結果・厳密な分子分母・符号・単位・元の仮定・入力ハッシュを照合する。
8. 元データや数学結果を故意に変更する8種類の試験が、すべて拒否されることを確認する。

## 合格条件

`Math IR Phase 3 - Structured SageMath MATLAB Transfer` の全4ジョブ（prepare, sage, matlab, verify）が成功し、5件の厳密値一致と8件の改ざん拒否がログ上で確認できること。

計算に使うのは合成データのみ。研究ファイル・既存MATLAB/SageMath診断用ワークフローに触れない。

## 注意と制限

- SageMathとMATLABを1つのプロセスにまとめるわけではない。Artifactでの**実データ受け渡し**を検証する。
- 仮定と単位はJSONで保存・検証するが、一般的な次元解析や全ての定義域の数学的証明はまだ対象外。
- 大規模な数式・時間関数・任意の数式入力・未信頼のコード実行には未対応。
- ハッシュは改変検出に役立つが、第三者の真正性を示す電子署名ではない。
- MATLAB公開リポジトリ向けの利用条件と、GitHub Actionsの計算時間・利用枠には制限がある。
- 第4段階（依存関係・キャッシュ・再計算）は未実装のまま維持する。

## 検証ファイル

- `math_interop_v0/phase3.py`
- `math_interop_v0/phase3_matlab.m`
- `.github/workflows/math-ir-phase3.yml`
