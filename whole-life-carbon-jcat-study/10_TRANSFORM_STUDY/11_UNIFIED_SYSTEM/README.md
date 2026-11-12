# 11_UNIFIED_SYSTEM：全 70 評価単位を 2 つの数学的構造で計算する統合系（2026-11-13）

独立概念モデル（架空データ）の 70 評価単位・公開出力 189 キー（比較の状態によって現れる SUM-08 の `reasons` を含めると 190）を、
**マスク付き積和**と**節点スペクトル**の 2 構造だけで、元の入力から計算する。基準計算の出力は係数に使わない（比較にだけ使う）。

- 状態：全 70 単位の全出力が、1,293 組（シナリオ×評価期間）・約 2,270 万個の値で基準計算と一致（不一致 0、失敗 0）。数値の最大相対差は 2.2e-12（X-13）、
  それを除くと 5.7e-13（B3-01）。ホールライフ合計の相対差の 95 パーセンタイルは 1.0e-13 以下、段階別は 5.7e-13 以下。
- 証拠の水準：**数値の一致（N）、確認者は実装者のみ**。独立の検査は受けていない。証明は `DERIVATIONS.md` に恒等式として書いた部分に限る。
- 対象は独立概念モデルと架空データである。他のツールの式・係数・結果との整合を示すものではなく、実務での精度を保証しない。

## 計算の流れ

```
建物の入力（シナリオ）
  └ 共通表：平坦化、文字列の分割、添字集合、節点の格子           tstudy/tables.py, tstudy/index.py（INDEX_PLAN）
      └ 積和①（P1、1,528 ステップ）：係数・数量・条件・検査の印・振幅      specs/pre_a.py, physical.py, gates.py
          └ 節点スペクトル（跳び形 23 本＋区間形 1 本）：振幅を節点に置き、T で評価          specs/system.py（EMIT）, tstudy/knots.py, interval.py
              └ 積和②（TIME 95 ステップ、AGG 166 ステップ）：T での行・年・係数ごとの値、段階・合計・指標・判定   specs/at_t.py
                  └ 70 単位の結果（読み出し：整形のみ）                tstudy/unified.py
```

`System(scenario)` が建物ごとに 1 回の準備（共通表、積和①、節点スペクトル）を行い、`System.at(T)` が任意の評価期間の結果を返す。

## 保存した内容（指示書 6 節の 10 項目との対応）

| # | 内容 | 所在 |
|---|---|---|
| 1 | 全 70 評価単位の数学的定義 | [UNITS_70.md](UNITS_70.md) |
| 2 | 元の方程式からの変形・導出過程 | [DERIVATIONS.md](DERIVATIONS.md)（D-01〜D-13、各 10 項目） |
| 3 | マスク付き積和の統一計算仕様 | [SPEC_MSP.md](SPEC_MSP.md)、`research_code/specs/` |
| 4 | 節点スペクトルの時間計算仕様 | [SPEC_KNOTS.md](SPEC_KNOTS.md)、`research_code/tstudy/{rampstep,knots,interval}.py` |
| 5 | 2 構造間のデータ受け渡し仕様 | [SPEC_HANDOVER.md](SPEC_HANDOVER.md)、`research_code/specs/system.py` |
| 6 | 実際に動作する統合計算コード | `research_code/tstudy/unified.py` ほか |
| 7 | 検証用の入力条件 | `research_code/checks/sets_unified.py`（シード・期間・特殊条件の作り方。入力は生成器が再生成する） |
| 8 | 実験結果・誤差・失敗条件 | [VERIFICATION.md](VERIFICATION.md)、`results/*.json`（1 シナリオの全出力の実例 `example_benchmark_S_T62.5.json` を含む）、DERIVATIONS 付録 B |
| 9 | 数学的な成立範囲・未解決事項 | [LIMITS.md](LIMITS.md) |
| 10 | 再実行手順 | [REPRODUCE.md](REPRODUCE.md) |

ほかに：単位ごとの追跡表 [UNIT_MAP.md](UNIT_MAP.md)（入力→演算→出力。コードから自動生成）、復元と再実装の区別 [PROVENANCE.md](PROVENANCE.md)。

## 最終確認（指示書 7 節）

| 確認事項 | 結果 | 根拠 |
|---|---|---|
| 全 70 単位の必要な出力を確認したか | 公開出力キーをすべて比較（70 単位、190 キー） | VERIFICATION 2 節 |
| 第 3 の構造を追加していないか | エンジン `msp.py` は無変更。使っている語彙は既存のものだけ。時間は節点スペクトル（跳び形・区間形）と、同じ核のゲート付き和（積和）だけ | VERIFICATION 5 節、SPEC_KNOTS |
| 基準計算の結果から係数を逆算していないか | `tstudy/unified.py` は基準計算を読まない（コード上の確認あり）。係数はすべて入力から | VERIFICATION 5 節 |
| 導出過程を追跡できるか | 式の族ごとに 10 項目で記録。単位→式→導出節→入力の対応表あり | DERIVATIONS、UNITS_70、UNIT_MAP |
| 数式と実装が一致しているか | 仕様はデータで、文書の式は仕様から書き起こした。一致の確認は「基準計算との全出力の一致」と「仕様を壊すと検出される」ことによる。文書と仕様の機械的な照合はしていない | VERIFICATION、LIMITS 4 |
| 元入力から再実行できるか | できる。入力は生成器がシードから作り直す。全 10 集合を 3 回実行して同じ結果（作業フォルダで 2 回、別の場所に取り出して 1 回） | REPRODUCE |
| 独立した評価条件で精度を満たしたか | 調整に使っていない 693 組（再現）と新規 354 組で不一致 0。SUM-03 の p95 は 1e-13 以下（基準 1％）、段階の p95 は 5.7e-13 以下（基準 2％） | VERIFICATION 1・3 節 |
| 使ったエンジンを記録したか | NumPy（本体）、SymPy・SciPy・mpmath・DuckDB（局所）、main の `lca_ops.py`、SageMath・MATLAB（GitHub Actions、実行 ID 付き） | VERIFICATION 6 節 |
| 証明と数値の一致を区別しているか | 区別している。恒等式は DERIVATIONS に根拠つきで、ほかは数値の一致 | DERIVATIONS 冒頭、LIMITS 1 |
| 保存したコードから結果を再生成できるか | コミット `bd45157` を別の場所に取り出して全検証を再実行し、結果の JSON 14 個が保存済みのものと（実行時間を除いて）完全に同じであることを確認 | REPRODUCE 4 節、`results/reproduction_check.json` |
