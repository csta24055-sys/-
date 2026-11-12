# 軽量化版 Math IR Efficient — 実装・性能・品質監査

監査日：2026-11-12
対象：`csta24055-sys/-`
PR：[ #12 ](https://github.com/csta24055-sys/-/pull/12)
マージコミット：`cf84ac8d82b9208323a95d2b14ab585de9e62d97`
最終実測：[GitHub Actions 43163250912](https://github.com/csta24055-sys/-/actions/runs/43163250912)

## 結論

**限定的なMath IR 0.1合成数式を対象に、従来の4ジョブを1ジョブへ集約し、可変6式を含む7エンジン計算と独立照合の試験が成功。** 既存の数学基盤フェーズ1〜5と研究コードには変更を加えていない。

## 構造上の改善

| 指標 | 従来の統合テスト | 軽量版 |
|---|---|---|
| GitHub Actionsジョブ | 4 | **1** |
| Python環境の準備 | Python側・最終照合側の2回 | **1回** |
| ジョブ間Artifacts | Python入力・SageMath結果・MATLAB結果 | **不要（同一ランナー）** |
| アップロード成果物 | 中間物を含む複数 | **最終出力のみ、保持1日** |
| サンプル式 | 固定5件 | **1〜20件の公開Math IRファイルに対応（6件実測）** |
| 追加の計算方式 | 毎回7エンジン | **Pythonのみを選択できるモードを追加** |

大容量pipキャッシュは最終構成で無効化しており、ライブラリは1回だけ導入する。

## 実測結果

- 初回の軽量版： [43162446437](https://github.com/csta24055-sys/-/actions/runs/43162446437) — 約161秒、6ケース・7エンジン、成功。
- 最終版： [43163250912](https://github.com/csta24055-sys/-/actions/runs/43163250912) — 約168秒、6ケース・7エンジン、成功。pipキャッシュを無効にした最終構成。
- 従来の4ジョブ統合版： [43158772490](https://github.com/csta24055-sys/-/actions/runs/43158772490) — 約203秒、5ケース・7エンジン、成功。

これらの秒数は、各GitHub Actions実行の`run_started_at`から`updated_at`までの差。**テスト件数が異なり、GitHubのランナー状況の影響もあるため、厳密なベンチマークではない。**

最終版のGitHub Actionsログ：

```text
PORTABLE PREPARE: PASS 6 cases, 32 Python nodes
PORTABLE VERIFY: PASS 6 cases, 5 engines, 32 Python cache hits
PASS tamper rejected: rehashed cached approximation
PORTABLE VERIFY: PASS 6 cases, 7 engines, 32 Python cache hits
PASS tamper rejected: rehashed cached approximation
PASS tamper rejected: sage_value
PASS tamper rejected: matlab_value
PASS tamper rejected: metadata_unit
PORTABLE AUDIT: PASS full source reconstruction
```

最終の成果物`math-ir-efficient-result`は約852バイトのZIPとしてアップロードされた。これは**出力要約だけ**であり、完全なDAGキャッシュを永続保管したものではない。

## モードと検証状況

- `portable-full`：**GitHub Actionsの全ルートで検証済み**。6ケースを全7エンジンで処理し、SageMath・MATLABの実出力を照合。
- `portable-python`：**5エンジン計算・照合・再ハッシュ改ざん拒否を同じワークフロー内で先行実行し検証済み**。ただし`portable-python`だけを指定してGitHub Actionsを独立起動する試験は未実施。
- `baseline-compact`：**選択肢として追加済みだが、当該新モード単独のGitHub Actions試験は未実施**。既存4ジョブの43ノード版は別途合格済みで維持。

## 現時点の制約

1. Python 5エンジンの可変ケースDAGは`5×ケース数+2`ノード。可変ケース版はSageMath・MATLAB結果を照合・要約するが、**旧Phase 5の固定43ノードと同じ統合DAGを汎用生成しているわけではない**。
2. 対応演算はMath IR 0.1の整数・有理数・記号・二項加算/乗算・制限付き整数冪。変数は合理数・非負・代入値必須。一般の微積分AST、時間関数、区分関数、節点スペクトルやマスク付き積和は未対応。
3. 可変ケースでのSciPyは`x^2`の数値積分リファレンスに用いられており、各入力式を自動でSciPy積分するわけではない。
4. 単位は`1`、`kgCO2e`のラベルであり次元解析は未対応。NumPy/mpmathの誤差記録は普遍的な誤差上界ではない。
5. 固定順の計算フロー。7エンジンを任意順で自動選択する動的な分散DAGスケジューラではない。
6. 成果物は1日保持の一時データ。ワークフロー間で継続的に保存される長期共有キャッシュではない。
7. リポジトリは公開。入力は`math_tools_v2/examples/`直下のコミット済みファイルに限定し、任意の研究秘密や個人情報は使用しない。
8. 旧4ジョブ版は依然として別ランナー間のArtifacts受け渡しの検証用に残してある。軽量版は同一ランナーで完結するため、別ランナー間転送の検証とは同一ではない。

## 操作

GitHub Actions [Math IR Efficient](https://github.com/csta24055-sys/-/actions/workflows/math-ir-efficient.yml)を`main`から実行。modeとして`portable-python`、`portable-full`、`baseline-compact`を選択。可変ケース入力は`math_tools_v2/examples/six_cases.json`などの安全な公開ファイルだけを受け付ける。

**建築LCA研究本体を勝手に再開・変更してはいけない。** 実研究に適用する場合は、まずMath IRの演算範囲・公開条件を満たすか別途検証すること。
