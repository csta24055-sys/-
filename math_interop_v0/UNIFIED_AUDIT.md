# 7エンジン統合システム・最終監査

監査日：2026-11-12
対象：`csta24055-sys/-` / PR [#11](https://github.com/csta24055-sys/-/pull/11)
統合コード：`math_interop_v0/phase5.py`
CI：`.github/workflows/math-ir-unified.yml`
マージコミット：`89d89fd3fa99486ebad82d376775312812524f46`

## 結論

**限定的な合成データに対する、7種類の実計算エンジンを使った単一ワークフロー・43ノードの統合実証は合格。** 建築LCA研究の本体は編集・再開していない。

これは、任意の複雑な数学問題に対応する完成版の汎用分散計算システムではない。

## 実証した計算の連鎖

`Python 5エンジン(27ノード)` → `SageMath 10.10(5ノード)` → `MATLAB + Symbolic Math Toolbox(5ノード)` → `照合(5ノード)` → `統合集約(1ノード)` ＝ **43ノード**。

- Python側は既存のPhase 4による27ノードのキャッシュ付きDAGとPhase 2の数値・誤差記録を再利用。
- SageMathは入力JSONを独立に厳密評価。
- MATLABはSageMathが実際に出力したJSONを取り込み、元の式から独立に記号計算して照合。
- それぞれの結果はGitHub Actionsの小容量Artifactsで受け渡し。
- 最終ジョブは27件のPythonキャッシュを別ランナーで読み込み、27件が再利用されること、数式・仮定・単位・有理数・数値近似・計算履歴・各ノードの依存関係を整合させることを検証。
- 生成した統合JSONを独立したプロセスで再構築し、9種類の改ざんを検出して拒否。

## 実測したGitHub Actions（すべて成功）

| 対象 | 実行ID | 結果 |
|---|---:|---|
| **7エンジン統合** | [43158772490](https://github.com/csta24055-sys/-/actions/runs/43158772490) | python-five / sage / matlab / unified-verify の4ジョブ合格 |
| Phase 1回帰 | [43158772397](https://github.com/csta24055-sys/-/actions/runs/43158772397) | 合格 |
| Phase 2回帰 | [43158772498](https://github.com/csta24055-sys/-/actions/runs/43158772498) | 合格 |
| Phase 3回帰 | [43158772550](https://github.com/csta24055-sys/-/actions/runs/43158772550) | 4ジョブ合格 |
| Phase 4回帰 | [43158772423](https://github.com/csta24055-sys/-/actions/runs/43158772423) | 合格 |

統合の `unified-verify` ジョブログには、以下のメッセージを確認済み：

```text
UNIFIED FINALIZE: PASS 43 nodes; 7 engines; full lineage in JSON
PASS independently reopened 43-node seven-engine DAG
PASS unified tamper rejected: exact_result
PASS unified tamper rejected: matlab_result
PASS unified tamper rejected: metadata_unit
PASS unified tamper rejected: engine
PASS unified tamper rejected: engine_version
PASS unified tamper rejected: dependency_edge
PASS unified tamper rejected: missing_node
PASS unified tamper rejected: source_lineage
PASS unified tamper rejected: graph_digest
UNIFIED SEVEN ENGINES: PASS 43 nodes, 7 engines, 9 tamper checks
```

## 統合の過程で解消した問題

初回の統合実行（[43158204285](https://github.com/csta24055-sys/-/actions/runs/43158204285)）では、Python5・SageMath・MATLABの実計算は成功した一方、統合時に`scipy_reference`への参照エラーが発生した。

原因：正規化JSONの保存時に辞書のキー順がアルファベット順になり、計算ノードの実際の依存順とは異なっていた。

対策：キャッシュのノードをJSONのキー順ではなく、**依存関係に基づいたトポロジカル順**で再構成するよう修正した。修正版の5ワークフローが全件成功済み。

## 明確な未実装範囲

1. 遠隔SageMathとMATLABの起動順はGitHub Actionsの固定`needs`。**任意の7エンジンDAGを実行時に自動分配する汎用スケジューラは未実装**。
2. Python27ノードのキャッシュを**同一ワークフロー内の別ランナー**で再利用した。別ワークフロー実行・別日の継続利用を保証する**永続共有キャッシュは未実装**。
3. 計算対象は5種類の限定的な合成有理数式。一般の記号関数・時間関数・節点スペクトル・建築LCA70評価単位は対象外。
4. 単位は文字列ラベルの保持・比較のみ。単位次元の代数的整合性検証は未実装。
5. 近似誤差は既知の厳密値との測定であり、普遍的な保証区間ではない。
6. MATLABの実ランタイムの正確なバージョンをJSONに記録していない。SageMath Dockerもタグ指定であり、イメージダイジェスト固定ではない。
7. GitHub Actions成果物は**1日保持の一時転送**で、永続アーカイブではない。
8. 同時書込・分散ロック・暗号署名・改ざん者の認証は未実装。SHA-256だけで真正性の証明はできない。
9. 公開リポジトリ上のため、非公開研究データ・機密情報を本ワークフローに入力してはならない。
10. 実際の建築LCAに対する大規模性能・計算費用・精度保証は未検証。

## 運用方針

- 既存の第1〜4段階および`matlab-run.yml`、`sagemath-run.yml`は変更せずに保持。
- この統合は本業研究と独立した数学計算基盤の実証成果。Claude Codeが研究作業を進める際、勝手に研究ファイルへ混入させない。
- 将来の改良は、7エンジンの動的DAG実行、遠隔ジョブの内容ベースキャッシュ、永続ストレージ、幅広い数学IRと単位次元の検証を優先する。
- 現時点で「限定的な7エンジン統合試験に合格した」と判断できる。**すべての数学式を損失なしに移動できることまでは確認していない。**
