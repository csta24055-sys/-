# 建築LCA向け4数学演算の追加・最終監査（2026-11-12）

対象：csta24055-sys/- / PR #13
マージコミット：791a006794cdc145d431e4c834fd5c9f92a0792d

## 結論

既存の7エンジン統合基盤とMath IR 0.1は残したまま、軽量版に**4つの直接実行可能な数学演算**を追加した。研究本体の数式・データは変更していない。

| 追加演算 | 実装済みの範囲 |
| --- | --- |
| 積分 | 制限付きASTでの定積分（SymPy＋SciPy/mpmath照合）・不定積分（微分確認） |
| 時間関数 | 区分的な連続時間関数の積分・時点別評価・区間欠落拒否 |
| マスク付き積和 | 元入力の数量・係数・二値マスクから厳密有理数を計算、単位次元確認 |
| 節点スペクトル候補 | 初期イベント・周期イベント・連続時間レートの集計、端点包含指定 |

## CI実測結果

- [4演算専用CI 43167850625](https://github.com/csta24055-sys/-/actions/runs/43167850625)：8件のPythonテスト合格、JSONファイルrun/verify成功。
- [既存軽量7エンジン回帰CI 43167850680](https://github.com/csta24055-sys/-/actions/runs/43167850680)：Python→SageMath→MATLABの既存計算経路成功。
- 数値例：係数 initial=4 kgCO2e、replacement=4 kgCO2e、operation_rate=2 kgCO2e/year。
- 時間事象：20年目の交換を除外→48 kgCO2e、含める→52 kgCO2e。
- 区分時間積分：0〜10年は2、10〜20年は3で50 kgCO2e。
- 定積分：∫(0..3)t²dt=9、∫(0..1)sin(t)dt=1−cos(1)、指数関数型積分を計算。
- 不定積分：∫sin(t)dt=−cos(t)+C、結果を微分して検証。
- 拒否試験：不正演算、零除算、単位不一致、時間区間の欠落、非二値マスク、参照先なし、周期0、評価区間不正、特異点、結果改ざんなど。

## 操作

GitHub Actions：
https://github.com/csta24055-sys/-/actions/workflows/math-ir-efficient.yml
modeとして lca-operators を選択。case_fileは既定のsix_cases.jsonであれば自動的に lca_ops_demo.json に置換される。

または次のコマンド：

```bash
python math_tools_v2/lca_ops.py run math_tools_v2/examples/lca_ops_demo.json /tmp/lca_ops_result.json
python math_tools_v2/lca_ops.py verify math_tools_v2/examples/lca_ops_demo.json /tmp/lca_ops_result.json
```

## 厳密な達成範囲

- 研究上の『節点スペクトル』の定義が全評価単位について正しいと証明したわけではない。あくまで離散イベント＋連続排出の候補計算モデル。
- 『一般積分』はすべての積分が必ず解けることを意味しない。安全な有限区間・許可済み関数の範囲で解析計算し、必要なら数値計算へ移行。
- 4演算の**直接実行はPython系**。SageMathとMATLABを含む旧7エンジン連携は回帰成功したが、新しい演算ASTを7エンジンすべてに個別実装したわけではない。
- 基準計算結果から係数を逆算せず、元入力の値から係数を作る。
- 公開リポジトリに機密データを置かない。実建築LCA70評価単位の一般同値性・誤差保証・長期共有キャッシュは未検証。

この範囲の計算基盤実装・試験として完了。以後の建築LCA本業研究は別作業として扱う。
