# 索引の詳細 T07：厳密一致・負荷・入力の測定と反例

[INDEX.md](../INDEX.md) の項目ごとの詳細。分類担当（読み取り専用）が書いた内容を、欄ごとに載せる。停止後の点検で改めた項目には「停止後の点検による訂正」と記してある。
旧研究の数値はすべて架空データでの値で、対象は独立概念モデルである。原版の表計算との一致や、実建物での精度を示すものではない。
所在の表記：`09_APPROX_STUDY/…` などは `whole-life-carbon-jcat-study/` からの位置、`materials/…` はこの保存フォルダからの位置。

| 項目 | 区分 | 題 |
|---|---|---|
| [CK-R3-18](#ck-r3-18) | 1 | 厳密一致の測定（681 シナリオ、数値 7,406,182 個、許容差 相対 1e-9） |
| [CK-R3-19](#ck-r3-19) | 1 | 評価期間の掃引（1 回の合算から別の評価期間の結果を求める） |
| [CK-R3-20](#ck-r3-20) | 1 | 負荷の測定：実行した命令数（規模 S・M、基準計算・全出力・合計のみ） |
| [CK-R3-21](#ck-r3-21) | 2 | 負荷の測定：規模 L、計算時間、ピークメモリ、基準案込み、評価期間 4 通り |
| [CK-R3-23](#ck-r3-23) | 2 | 入力項目の使用の測定（基準計算と統合モデルが読む入力は同じ） |
| [CK-R3-27](#ck-r3-27) | 4 | 反例：周期 1.000000001 で修繕（B3-01）が基準計算と食い違う |
| [CK-R3-28](#ck-r3-28) | 4 | 不備のある入力・特殊な入力での食い違い（NUM-2〜NUM-9） |
| [CK-R3-29](#ck-r3-29) | 4 | 条件の悪い入力での限界（NUM-10：桁落ち・桁あふれ） |
| [CK-R3-30](#ck-r3-30) | 4 | 一致の確認に使った比較の弱点（NUM-11：床、無限大、真偽値、余分な葉） |
| [CK-R7-22](#ck-r7-22) | 1 | 681 架空シナリオでの基準計算と統合モデルの一致（記録された測定） |

<a id="ck-r3-18"></a>

## CK-R3-18　厳密一致の測定（681 シナリオ、数値 7,406,182 個、許容差 相対 1e-9）

- **区分**：1　検証済み成果
- **内容**：統合モデルの 2 つの出力（全出力、合計のみ）と基準計算の全出力を、架空の 681 シナリオ・70 単位で 1 つずつ突き合わせた結果。内訳は標準ベンチマーク 3、境界条件 32、検証用の母集団 400、不備を入れたシナリオ 60、入力を 1 か所ずつ壊したシナリオ 144（36 種類×4）、小数の評価期間と周期の端 10、対象段階を一部にしたシナリオ 32。数値 7,406,182 個と数値以外 586,280 個を比べ、不一致 0、最大の相対差 4.8e-13（SUM-08）。無効な評価期間 5 種はどちらもエラーにする。
- **所在**：
  - [`09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json`](../../../09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json)
  - [`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../../09_APPROX_STUDY/04_VERIFICATION/README.md)
  - [`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../../09_APPROX_STUDY/research_code/bench/verify_unified.py)
- **確かめ方**：bench/verify_unified.py の exactness()。比較は common.compare.compare、許容差 1e-9、床 1e-9×|SUM-03|（報告書に記載がない）。第2回：数値の検査担当が同じシナリオ一覧を、床なし・無限大と型を区別する自作の比較でやり直し、1e-9 を超える葉 0、最大 4.77e-13（SUM-08 の delta）で、記録の 4.8e-13 を再現した。検証担当も独自にやり直し、葉 7,962,996 個で不一致 0、例外の食い違い 0、余分な葉 0。記録の検査担当は別の種の 60 シナリオ（367,518 個、最大 1.3e-13、失敗 0）、報告書の検査担当は境界条件 32・ベンチマーク S と M・母集団の先頭 60 で失敗 0（境界条件の最大差は保存値と全桁一致）。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：この 681 シナリオについての事実。架空データのみ、独立概念モデルのみ、基準計算に対する一致、許容差 相対 1e-9。
- **関係する第2回の指摘**：NUM-1、NUM-2、NUM-3、NUM-4、NUM-5、NUM-6、NUM-7、NUM-8、NUM-9、NUM-10、NUM-11、REC-1、REC-6、REP-15
- **第2回の指摘の影響**：「681 シナリオで不一致なし」の表はそのまま成り立つ。成り立たないのは一般化した言い方である。(1) どの入力でも一致する（周期 1.000000001 で B3-01 が最大 92％ ずれる。NUM-1）。(2) 不備のある入力でも同じ値と同じ不備の報告になる（壊し方 36 種の外で、値の食い違いと例外の非対称がある。NUM-2〜NUM-8）。(3) 許容差は純粋に相対 1e-9（床があり、無限大と真偽値を見逃す比較だった。NUM-11）。(4) 条件の悪い入力（NUM-10）。また、B6-01・B6-02・B6-04・B7-01〜03・X-06 の一致は年次の系列と印の一致で、閉形式を通っていない（REC-6）。60e720f の文書は「対応後の版に対する独立した検査は、まだ行っていない」のままで、第2回の結果は INDEPENDENT_REVIEW.md に記録されていない（REP-15）。
- **今の時点で言ってよいこと**：架空の 681 シナリオ（生成器が作る整った入力、生成器の不備 60 件、壊し方 36 種、小数の端 5 組、段階の部分集合 8 通り）では、統合モデルの全出力と合計のみの出力が、基準計算と相対 1e-9 以内（実測の最大 4.8e-13）で一致する。第2回の検査担当 1 者と反証検査担当 1 者が、床なしの比較で再現した。
- **使ってはいけない記述**：
  - 統合モデルはどの入力でも基準計算と同じ結果を返す
  - どちらの計算も、使えない行・経路・項目を除いたうえで同じ値を返し、同じ不備を報告する（壊し方 36 種の外への一般化として）
  - 許容差は相対 1e-09（床なしの純粋な相対比較という読み方）
  - この一致を、実建物での精度、原版や他のツールとの一致、基準計算の定義の正しさの根拠として使うこと
  - 記録の「解析的に検証」表示（導出と一致の両方があることを示すだけで、第2回の指摘は反映されていない）
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：新研究での厳密一致・誤差測定の型として使える。シナリオの種類（ベンチマーク、境界条件、母集団、不備、壊し方、小数の端、段階の部分集合）と、葉ごとの比較という方法である。第2回の検査担当の厳密な比較（床なし、無限大・型・余分な葉を検出）は materials/round2_review/checker_scripts/numeric/h.py に保存されている。
  - 条件・注意：比較は床なしにする。周期 1.000000001 と NUM-2〜NUM-8 の入力をシナリオに加える（中断した修正 a1 が壊し方を 214 種に増やしたと申告しているが未検証）。この測定が示さないもの：実建物での精度、原版や他のツールとの関係、基準計算の定義の当否（基準計算と統合モデルは同じ作成者が書いており、同じ読み違いが両方に入り得る）、681 件の外の入力での一致。数字が今の環境で再現するかは、実行していないので確認していない。
- **分類の根拠**：
  - [`09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json`](../../../09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json): scenarios, tolerance, by_group, units, all_exact, mutations, invalid_periods_refused_by_both
  - [`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../../09_APPROX_STUDY/04_VERIFICATION/README.md):9-27
  - [`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../../09_APPROX_STUDY/research_code/bench/verify_unified.py):41, 47-75, 93-171 (床は 115-121 行)
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):9, 118, 134 (CHECKS PERFORMED 9)
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):110 (7)
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):99-104, 128
  - [`09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md`](../../../09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md):7-8
- **分類した観点**：R3（統合モデルとその根拠）
- **停止後の点検による訂正**：点検の指摘 V1-14 により、上の記述の一部を改めた。分類担当の元の記述は `materials/classification/R3.json`、訂正の内容は `materials/classification/overrides.json` にある。

<a id="ck-r3-19"></a>

## CK-R3-19　評価期間の掃引（1 回の合算から別の評価期間の結果を求める）

- **区分**：1　検証済み成果
- **内容**：engine.sweep と、同じ Aggregate に対する finish の繰り返し。行の合算を 1 回だけ行い、評価期間ごとに乗数だけ計算し直して結果を得る。公表の確認は、64 シナリオについて評価期間 9 通り（10、30、42.5、50、60、75、99.9、100、120 年）の結果を、期間ごとに最初から計算した基準計算と突き合わせたもの。比較した値は 172,404 個、最大の相対差 1.1e-13、不一致 0。
- **所在**：
  - [`09_APPROX_STUDY/research_code/fastcalc/engine.py`](../../../09_APPROX_STUDY/research_code/fastcalc/engine.py)
  - [`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../../09_APPROX_STUDY/research_code/bench/verify_unified.py)
  - [`09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json`](../../../09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json)
- **確かめ方**：bench/verify_unified.py の sweep_check()。作成者の試験 test_sweep_from_one_aggregation。第2回：数値の検査担当が、150 の乱数シナリオで 20 通りの評価期間（0.3〜130 年、非整数を含む）を全出力と合計のみで 2 回ずつ、期間ごとの基準計算と比べ（3,000 組）、|SUM-03|×1e-12 を超える食い違いなし。同じ Aggregate を 2 回 finish した結果はビット単位で同一、掃引はシナリオを書き換えない。記録の検査担当は全単位について 8 シナリオ×9 期間（46,827 個）で失敗 0。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：架空データ、独立概念モデル、許容差 相対 1e-9（第2回の数値の検査担当の比較は |SUM-03|×1e-12 の絶対差）。公表の 172,404 個は、70 単位のうち 22 単位、合計のみの形、基準案との比較を切った状態、規模の小さい 64 シナリオについての数字である。
- **関係する第2回の指摘**：REP-16、REP-17、NUM-1、REC-4
- **第2回の指摘の影響**：公表の文は範囲を書いていない。比べたのは 22 単位（X-02、SUM-01〜05、B4-02、B3-01、B3-02、B1-02〜04、B5-01、B6-03、B7-04、B2-01、X-04、X-05、X-08、X-10、X-11、QA-02）で、SUM-06、SUM-07、X-07、B4-01、SUM-08 は入っていない（REP-16）。T は電力係数の年次表の長さ以内に限る（REP-17）。周期 1.000000001 では掃引の結果も食い違う（NUM-1）。別の評価期間の finish のたびに冷媒の行を読み直す（REC-4）。
- **今の時点で言ってよいこと**：統合モデルは、行の合算（aggregate）をやり直さずに、別の評価期間の結果を求められる。ただし評価期間ごとに、冷媒機器の行の読み直しと、明示の更新年一覧・冷媒の交換年一覧の作成は行う（REC-4）。周期が倍精度の 1.000000001 のときは、この求め方の結果も基準計算と食い違う（NUM-1）。評価期間は電力係数の年次表の長さ以内に限る（REP-17）。第2回の検査で、150 シナリオ×20 期間（判定は |SUM-03|×1e-12 の絶対差）と、全単位での 8 シナリオ×9 期間について、期間ごとに最初から計算した基準計算と一致した。
- **使ってはいけない記述**：
  - 172,404 個の比較が全出力・全単位を覆っているという読み方
  - どの評価期間でも求められる（年次表の長さを超える T はエラーになる）
- **新研究での再利用**：候補（ルート A・C）
  - 使い道：T に依存しない部分（A、U_c、R_c、機器の一覧）と T に依存する乗数の分離が、実装と測定の両方で確かめられた例として使う。新研究で T を変数とする変換（T についての関数として結果を表す）を試すとき、厳密な対照を安く作る手段になる。
  - 条件・注意：冷媒と明示の更新年一覧は T ごとに機器・行の単位で計算し直す。基準案との比較（SUM-08）は基準案の期間が同じでなければ比較不可になる。公表の 64 シナリオの内訳は JSON に記録がない（REP-16 は規模 S の母集団 32＋境界条件 32 と書く）。
- **分類の根拠**：
  - [`09_APPROX_STUDY/research_code/fastcalc/engine.py`](../../../09_APPROX_STUDY/research_code/fastcalc/engine.py):794-812, 1409-1418
  - [`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../../09_APPROX_STUDY/research_code/bench/verify_unified.py):42-44, 174-197
  - [`09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json`](../../../09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json): period_sweep
  - [`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../../09_APPROX_STUDY/04_VERIFICATION/README.md):29-31
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):134 (CHECKS PERFORMED 5)
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):106-118
- **分類した観点**：R3（統合モデルとその根拠）
- **停止後の点検による訂正**：点検の指摘 V1-03 により、上の記述の一部を改めた。分類担当の元の記述は `materials/classification/R3.json`、訂正の内容は `materials/classification/overrides.json` にある。

<a id="ck-r3-20"></a>

## CK-R3-20　負荷の測定：実行した命令数（規模 S・M、基準計算・全出力・合計のみ）

- **区分**：1　検証済み成果
- **根拠の強さについての注記（索引の作成者）**：数え直したのは報告書の検査担当 1 者。反証検査担当は付いていない。
- **内容**：同じ言語（純粋な Python 3.13.18）、同じ機械、同じ入力で、基準計算（SUM-08 を除く全単位）と統合モデルが実行したバイトコード命令の数を sys.monitoring で数えた値。規模 S（資材 200 行）は基準計算 2,528,394、統合モデルの全出力 1,158,253（54.2％ 減）、合計のみ 819,555（67.6％ 減）。規模 M（資材 2,000 行）は 24,869,192、9,064,197（63.6％ 減）、6,811,966（72.6％ 減）。
- **所在**：
  - [`09_APPROX_STUDY/04_VERIFICATION/unified_model_load.json`](../../../09_APPROX_STUDY/04_VERIFICATION/unified_model_load.json)
  - [`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../../09_APPROX_STUDY/04_VERIFICATION/README.md)
  - [`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../../09_APPROX_STUDY/research_code/bench/verify_unified.py)
- **確かめ方**：bench/verify_unified.py の load()。命令数は 1 回の実行で数える。第2回：報告書の検査担当が規模 S と M の命令数（基準計算、全出力、合計のみ）を数え直し、公表値と約 100 命令以内で一致した（54.2％・67.6％、63.6％・72.6％）。生成器の耐用年数の設定を変えても、合計のみの削減率は S で 66.9〜68.7％、M で 70.9〜72.6％ の範囲だった。REP の指摘と確認には反証担当が付いていない。
- **確かめた者**：独立検査（第2回）で再現（反証担当なし）
- **言える範囲**：この 2 つの実装（評価単位ごとに 1 関数で行を走査し直す基準計算と、1 回の走査の統合モデル）の間の、架空の標準ベンチマーク S・M での命令数。独立概念モデルのみ。Python の版と実装の書き方に依存する。第2回の数え直しとの差は約 100 命令以内。
- **関係する第2回の指摘**：REP-4、REP-6、REP-12
- **第2回の指摘の影響**：数字への反証はない。削減は 2 つの実装の差であり、式の種類の数の差ではない（「70 → 11」は名札の数。REP-4）。近似候補については負荷も入力数も測っていない（REP-6）。中断した修正 a1 は、基準計算の変更後は基準計算の命令数が 1.24 倍になり、削減率の上昇のうち約 3〜5 ポイントは統合モデルの改善ではなく基準計算が重くなったことによる、と申告している（未検証）。
- **今の時点で言ってよいこと**：架空の標準ベンチマーク S・M で、基準案との比較（SUM-08）を除いた計算どうしを比べると、統合モデルが実行した命令数は基準計算より全出力で 54.2％・63.6％、合計のみで 67.6％・72.6％ 少なかった。第2回の検査担当 1 者がこの命令数を数え直し、約 100 命令以内の差で合った。基準案との比較を含めた場合の全出力の減り方 44.9％・54.3％ は作成者の測定だけで、第2回は数え直していない（CK-R3-21）。
- **使ってはいけない記述**：
  - この削減率を、式を簡略化した効果の大きさ、または別の言語・別の実装での速度の見込みとして使うこと
  - 原版の表計算の計算時間がどれだけ変わるかの根拠として使うこと（原版は実行していない）
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：使えるのは測り方である：機械の混み具合に左右されない指標として実行命令数を数え、同じ仕事をする組だけを比べ、出力の範囲（全出力、合計のみ）を分けて示す。数字そのものは新研究のモデルとの比較の基準線にはなるが、同じ Python の版と同じベンチマークで測り直す必要がある。
  - 条件・注意：基準計算は読みやすさを優先して単位ごとに行を走査し直す実装であり、これを負荷の基準にすると削減が大きく出る。削減の理由 (a) 行を 1 回だけ走査する、は式の効果ではなく実装の効果である（05_DECISIONS/README.md が 4 つの理由を挙げている）。
- **分類の根拠**：
  - [`09_APPROX_STUDY/04_VERIFICATION/unified_model_load.json`](../../../09_APPROX_STUDY/04_VERIFICATION/unified_model_load.json): sizes.S, sizes.M, python, repeats
  - [`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../../09_APPROX_STUDY/research_code/bench/verify_unified.py):230-276, 279-334
  - [`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../../09_APPROX_STUDY/04_VERIFICATION/README.md):53-89
  - [`09_APPROX_STUDY/05_DECISIONS/README.md`](../../../09_APPROX_STUDY/05_DECISIONS/README.md):103-119
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):128 (CHECKS PERFORMED 2), 130
  - [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json): open_problems
- **分類した観点**：R3（統合モデルとその根拠）
- **停止後の点検による訂正**：点検の指摘 V1-11、再点検 FV1-N01 により、上の記述の一部を改めた。分類担当の元の記述は `materials/classification/R3.json`、訂正の内容は `materials/classification/overrides.json` にある。

<a id="ck-r3-21"></a>

## CK-R3-21　負荷の測定：規模 L、計算時間、ピークメモリ、基準案込み、評価期間 4 通り

- **区分**：2　暫定・未検証成果
- **内容**：CK-R3-20 と同じ測定のうち、第2回で測り直されていない部分。規模 L（資材 20,000 行）の命令数は基準計算 245,195,907、全出力 82,539,384（66.3％ 減）、合計のみ 64,746,240（73.6％ 減）。時間（GC 停止、反復 7 回の中央値）は L で 1688.6 ms → 862.3 ms（48.9％ 減）・624.3 ms（63.0％ 減）。ピークメモリは L で 66,505 KiB → 25,480 KiB・15,077 KiB。基準案との比較を含む場合は L で 57.1％ 減。別の評価期間 4 通り（30・50・75・100 年）の合計は L で 405,484,294 → 32,008,336（92.1％ 減）。
- **所在**：
  - [`09_APPROX_STUDY/04_VERIFICATION/unified_model_load.json`](../../../09_APPROX_STUDY/04_VERIFICATION/unified_model_load.json)
  - [`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../../09_APPROX_STUDY/04_VERIFICATION/README.md)
  - [`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../../09_APPROX_STUDY/research_code/bench/verify_unified.py)
- **確かめ方**：bench/verify_unified.py の load()。時間は time.perf_counter_ns、メモリは tracemalloc、命令数は sys.monitoring。第2回：報告書の検査担当は表の 216 個の値が JSON と一致することと、削減率の再計算が合うことを確かめたが、規模 L の命令数、絶対時間、ピークメモリは測り直していない（「機械に依存し、再測定していない」と明記）。
- **確かめた者**：作成者のみ（第2回は報告書と JSON の照合だけ）
- **言える範囲**：作成者の 1 台の機械、1 回の測定。架空の標準ベンチマーク。時間とメモリは実行環境で変わる。
- **関係する第2回の指摘**：REP-4、REP-6
- **第2回の指摘の影響**：数字への反証はないが、独立の再測定もない。第1回の検査で、初版の時間の削減率にごみ集めの影響が混ざっていた（基準計算の時間の約 37％）ことが指摘され、命令数を主な指標に変えた経緯がある。
- **今の時点で言ってよいこと**：作成者の測定では、規模 L で命令数が全出力 66.3％、合計のみ 73.6％ 減った。独立の再測定はない。
- **使ってはいけない記述**：
  - 別の評価期間 4 通りで 92.1％ 減、を「4 通りの計算の全体」の比較として読むこと（統合モデルの側は、合算を済ませた後の finish 4 回だけを測っている。verify_unified.py 288 行と 309-310 行）
  - 基準案の合計を呼び出し側が保持する行の削減率（式の効果ではないと報告書自身が述べている）
  - GC を動かしたときの時間の差（実行環境の効果）
  - 時間とメモリの絶対値
- **新研究での再利用**：候補にしない
  - 理由・注意：新研究で比較に使うなら測り直す。旧研究の測定は「静かな機械で」と指定されているが、測定時の機械の状態の記録はない。
- **分類の根拠**：
  - [`09_APPROX_STUDY/04_VERIFICATION/unified_model_load.json`](../../../09_APPROX_STUDY/04_VERIFICATION/unified_model_load.json): sizes.L, sizes.*.reference_four_more_periods, sizes.*.unified_four_more_periods_from_one_aggregation
  - [`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../../09_APPROX_STUDY/research_code/bench/verify_unified.py):253-276, 284-311
  - [`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../../09_APPROX_STUDY/04_VERIFICATION/README.md):55-89
  - [`09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md`](../../../09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md):53
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):130
- **分類した観点**：R3（統合モデルとその根拠）

<a id="ck-r3-23"></a>

## CK-R3-23　入力項目の使用の測定（基準計算と統合モデルが読む入力は同じ）

- **区分**：2　暫定・未検証成果
- **内容**：33 シナリオ（ベンチマーク S と境界条件）で、計算の途中でシナリオのオブジェクトから読まれた属性を記録した結果。基準計算、統合モデルの全出力、統合モデルの合計のみのいずれも、既存の入力仕様の項目 77 と本研究で加えた項目 56 を読む。基準計算は読むが統合モデルは読まない項目は 0 件。読まれた項目は、必要な項目の上限である。
- **所在**：
  - [`09_APPROX_STUDY/04_VERIFICATION/input_usage.json`](../../../09_APPROX_STUDY/04_VERIFICATION/input_usage.json)
  - [`09_APPROX_STUDY/research_code/bench/input_usage.py`](../../../09_APPROX_STUDY/research_code/bench/input_usage.py)
  - [`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../../09_APPROX_STUDY/04_VERIFICATION/README.md)
- **確かめ方**：bench/input_usage.py（モデルのクラスの属性の読み取りを追跡）。第2回：報告書の検査担当は JSON と報告書の表（77・56 が 3 つの計算で同じ）の一致を確かめた。追跡そのものをやり直した記録は読んだ範囲にない。
- **確かめた者**：作成者のみ（第2回は報告書と JSON の照合だけ）
- **言える範囲**：架空の 33 シナリオで読まれた属性。読むことと結果に効くことは別（スクリプトの説明文が上限と明記）。
- **関係する第2回の指摘**：REP-1、REP-7
- **第2回の指摘の影響**：報告書の文「入力仕様 124 項目のうち 0 項目は記録用で、どの計算にも使われない」は誤りで、JSON 自身は 124 項目のうち 47 項目がどの計算にも読まれないことを示す（0 は使われていない目印を数えた値。REP-1）。台帳の単位別の入力の一覧（既存 88＋追加 28）は実測（77＋56）と合わず、05_DECISIONS の表の隣り合う 2 行が説明なしに食い違う（REP-7）。入力項目の実測のやり直し（段階 b3）は未着手のまま停止した。
- **今の時点で言ってよいこと**：作成者の測定では、架空の 33 シナリオで統合モデルが読む入力項目の集合は基準計算と同じだった（既存 77、追加 56）。厳密な統合は結果を変えないので、入力は減らない。
- **使ってはいけない記述**：
  - 入力仕様 124 項目のうち 0 項目は記録用で、どの計算にも使われない（04_VERIFICATION/README.md 103 行）
  - 単位が参照する入力項目 116（既存 88＋追加 28）を実測値として読むこと（台帳の申告値である）
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：入力数を数える方法（属性の読み取りの追跡）は、新研究で「入力変数の数」を比べるときの型として使える。結果のうち使えるのは「厳密な書き換えでは入力は減らない」という点だけ。
  - 条件・注意：読まれた項目は上限であり、結果に効く項目の数ではない。記述子で与えられる年次量の年次表は、合計の計算には使わないが、食い違いの報告のために読まれる。単位別の実測はない（b3 の仕様にあるだけ）。
- **分類の根拠**：
  - [`09_APPROX_STUDY/04_VERIFICATION/input_usage.json`](../../../09_APPROX_STUDY/04_VERIFICATION/input_usage.json): scenarios, summary, not_read_by_reference, metadata_only_inputs
  - [`09_APPROX_STUDY/research_code/bench/input_usage.py`](../../../09_APPROX_STUDY/research_code/bench/input_usage.py):1-12
  - [`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../../09_APPROX_STUDY/04_VERIFICATION/README.md):91-103
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):1-6, 43-48
  - [`STOP_STATUS.md`](../STOP_STATUS.md):57
- **分類した観点**：R3（統合モデルとその根拠）

<a id="ck-r3-27"></a>

## CK-R3-27　反例：周期 1.000000001 で修繕（B3-01）が基準計算と食い違う

- **区分**：4　不具合・未解決事項
- **内容**：不備のない有効な入力で、更新周期（資材の更新周期または設備の耐用年数）が倍精度値 1.000000001 のとき、統合モデルの B3-01 と、B3 を含むすべての合計が基準計算と食い違う。この値は 周期×(1−1e-9) が浮動小数点でちょうど 1.0 に丸まり、基準計算のループでは事象 n が年 n か n+1 に入って複数の事象が同じ年に重なる。閉形式 skip_weight_periodic は「周期 1 以上なら事象ごとに年が違う」と仮定している。
- **所在**：
  - [`09_APPROX_STUDY/research_code/fastcalc/closed_forms.py`](../../../09_APPROX_STUDY/research_code/fastcalc/closed_forms.py)
  - [`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md)
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md)
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md)
- **確かめ方**：第2回：数値の検査担当が乱数の反例探し（種 365）で見つけ、記録の検査担当が別に見つけた。それぞれの検証担当が自分のスクリプトで再現した。T＝7 で 6 事象が 5 年（ループ 5.0、閉形式 6.0）、T＝30 で 26.0 と 29.0、T＝60 で 48.0 と 59.0。全行がこの周期のシナリオで B3-01 は基準計算 229291.25152413402、統合モデル 19107.60429367785（相対 −91.7％）、SUM-03 は相対 −1.8e-3。1 行だけ変えた場合は B3-01 で 2e-6〜8e-2。近傍の走査（±4,000〜6,000 ulp、1,512,126 組、乱数 300,000〜400,000 件）で、食い違うのはこの 1 つの倍精度値だけ。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：60e720f のコード（43ba5d7 と同一）についての事実。ほかに孤立した値がないことは証明されておらず、見つかっていないだけである（検査担当が明記）。
- **関係する第2回の指摘**：NUM-1、REC-1
- **第2回の指摘の影響**：研究自身の比較規則（床あり、許容差 1e-9）でも B3-01、X-02、X-04、X-05、X-07（合計のみ）、SUM-02〜07 が不一致になる。掃引も食い違う。統合モデルの全出力は自己矛盾する（B3-01 の年次の系列の和と X-07 は基準計算に一致し、B3-01 の値と SUM-03 は一致しないのに、QA-01 は合格）。厳密な有理数の演算では事象は別々の年に入り、閉形式が書かれた定義の値を返す。基準計算のループの値（B3-01、および B4-02・B5-01・B1・X-07 の年次の系列の年の割り当て）が丸めの産物である。したがって「閉形式をループに合わせる」修正は一致を戻すが、定義からのずれを両方に残す。作成者の試験は 1e-9 の摂動を引かない。
- **今の時点で言ってよいこと**：倍精度値 1.000000001 を更新周期に持つ入力では、統合モデルと基準計算は B3-01 で最大約 92％、B3 を含む合計で 1e-9 を超えて食い違う。原因は、年の判定の許容幅 1e-9 が、τ×(1−1e-9) が整数に近いところで浮動小数点の丸めに依存することにある。
- **使ってはいけない記述**：
  - 統合モデルはどの入力でも基準計算と相対 1e-9 以内で一致する
  - 事象の時刻と年の判定は、許容幅により 2 進の丸めに依存しない（06_OPEN_ISSUES B-15、refcalc/base.py の規約文）
  - この問題は修正済みである（修正は中断した a1 の自己申告だけで、作業ツリーから取り除かれている）
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：新研究は基準計算を変えないので、この入力では基準計算が「書かれた定義」と違う値を返すことを前提にする。新しいモデルの検証シナリオにこの周期とその近傍を入れ、不一致が出たときに「モデルの誤り」と「基準計算の丸め」を区別する。
  - 条件・注意：どちらの値を正とするかは決まっていない。決める案は中断した修正の仕様（すべての時間の判定を、与えられた 2 進の値に対する厳密な有理数の演算で行う）にあり、実装は未検証（CK-R3-31）。
- **分類の根拠**：
  - [`09_APPROX_STUDY/research_code/fastcalc/closed_forms.py`](../../../09_APPROX_STUDY/research_code/fastcalc/closed_forms.py):3-5, 58-71
  - [`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md):67
  - [`09_APPROX_STUDY/research_code/tests/test_closed_forms.py`](../../../09_APPROX_STUDY/research_code/tests/test_closed_forms.py):26
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md):43
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):1-11, 137-138
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):1-11, 113-114
- **分類した観点**：R3（統合モデルとその根拠）

<a id="ck-r3-28"></a>

## CK-R3-28　不備のある入力・特殊な入力での食い違い（NUM-2〜NUM-9）

- **区分**：4　不具合・未解決事項
- **内容**：統合モデルと基準計算が、値・合否・例外の出方で食い違う入力の群。(NUM-2) 範囲の検査がない項目の NaN・無限大：1 項目ずつ変える 3,461 件のうち 212 件が食い違い（電力係数の記述子の NaN で統合モデルだけ例外、QA-01 の合否、B5-01 が 0.0 と nan）。(NUM-3) 値 0 でガス内訳が 0 でない係数：X-04・X-05 が＋0.5％ 程度ずれる。(NUM-4) 評価期間より短い年次表と 2 つ目の不備の組：基準計算は IndexError、統合モデルは完了したように見える結果を返す。(NUM-5) 係数 ID が GRID／REFRIGERANT：SUM-03 が −0.79％。(NUM-6) ガス一覧の重複・CO2 の欠落と複合品：X-04 が＋28％、または統合モデルだけ KeyError。(NUM-7) 段の添字が float：統合モデルだけ TypeError。(NUM-8) 単位が文字列 None：SYS-02 の違反一覧が違う。(NUM-9) 呼び出し側が保持する基準案の合計のキーが scenario_id：別の基準案の合計を黙って使う。
- **所在**：
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md)
  - [`09_APPROX_STUDY/research_code/fastcalc/engine.py`](../../../09_APPROX_STUDY/research_code/fastcalc/engine.py)
  - [`09_APPROX_STUDY/research_code/fastcalc/closed_forms.py`](../../../09_APPROX_STUDY/research_code/fastcalc/closed_forms.py)
- **確かめ方**：第2回：数値の検査担当が、乱数で 0〜10 個の不備を入れた 20,260 シナリオの突き合わせ（床なし）、全数値項目を 1 つずつ nan・±inf・None に変える 3,461 件、基準案まわりの個別の場合で見つけ、検証担当が 8 件すべてを自分のスクリプトで再現した（反証なし）。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：60e720f のコードについての事実。架空データ。NUM-9 の衝突は研究の生成器が作るデータでは起きない（手で作った登録が要る）。2 つ以上の NaN・無限大の組、型の違う入力（文字列など）は調べられていない。
- **関係する第2回の指摘**：NUM-2、NUM-3、NUM-4、NUM-5、NUM-6、NUM-7、NUM-8、NUM-9
- **第2回の指摘の影響**：報告書の文「どちらの計算も…同じ値を返し、同じ不備を報告する」は、試した壊し方 36 種については正しいが、不備のある入力一般には成り立たない。検証担当の追加の指摘：年次量・係数の値・電力係数には、どちらの計算にも範囲の検査がなく、負の年次量を入れても合計が負のまま「完全」と報告される（基準計算の定義の穴）。研究自身の NaN の壊し方は、範囲の検査で弾かれる項目にしか触れないので、これらを見つけられない。
- **今の時点で言ってよいこと**：上の 8 種類の入力では、統合モデルと基準計算の結果が食い違う。乱数の反例探し 20,260 シナリオでは、これらと周期 1.000000001、冷媒の丸めの雑音のほかに食い違いは見つからなかった（2 つ以上の通常の不備の組合せ、明示の一覧、複合品・EPD の行、段階の部分集合、基準案の自己参照や循環では食い違いなし）。
- **使ってはいけない記述**：
  - どちらの計算も、使えない行・経路・項目を合計から除いたうえで同じ値を返し、同じ不備を報告する（一般の主張として）
  - 基準案の合計を呼び出し側が保持する使い方でも基準計算と一致する（キーの衝突と、基準案・期間の変更後の古い値の場合を除く、という限定なしで）
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：新研究のモデルを基準計算と比べるときの検査シナリオの材料と、定義を決めるべき点の一覧として使う。どの項目の NaN・無限大・負を無効とするか、係数の値とガス内訳が矛盾する場合、擬似キーの扱い、年次表の長さ、を先に決めておかないと、新しいモデルでも同じ食い違いが出る。
  - 条件・注意：基準計算（60e720f）自身がこれらの入力で疑わしい値を返す場合がある（係数 ID が GRID のとき基準計算の内部でも矛盾、負の年次量を黙って使う）。どちらが正しいかは検査担当も判定していない。修正は中断した a1 の自己申告だけ。
- **分類の根拠**：
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):13-107, 134, 136, 138
  - [`09_APPROX_STUDY/research_code/fastcalc/closed_forms.py`](../../../09_APPROX_STUDY/research_code/fastcalc/closed_forms.py):106
  - [`09_APPROX_STUDY/research_code/fastcalc/engine.py`](../../../09_APPROX_STUDY/research_code/fastcalc/engine.py):64-66, 103, 182, 450-451, 787-791, 933, 1039-1051, 1100, 1140-1145
  - [`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../../09_APPROX_STUDY/04_VERIFICATION/README.md):23, 35
- **分類した観点**：R3（統合モデルとその根拠）

<a id="ck-r3-29"></a>

## CK-R3-29　条件の悪い入力での限界（NUM-10：桁落ち・桁あふれ）

- **区分**：4　不具合・未解決事項
- **内容**：有限の入力でも、研究自身の比較規則（床あり、許容差 1e-9）で差が 1e-9 を超える場合。(a) 施設管理比 1.0 で燃料の使用をごく小さくした場合：1e-7 倍で X-02 の B6 が 5.0e-8 ずれ、QA-01 の合否も違う（1e-6 倍から現れる。基準計算のほうが B6-03−B2-01 で桁を失う）。(b) T が整数をわずかに超え、電力の基礎が 0：B6-03 が T＝1.000000001 で 5.2e-8、T＝1＋1e-12 で 6.4e-5（統合モデルの segment_moments が引き算で桁を失う）。(c) 提案と 1 行が 1e-8 だけ違う基準案：SUM-08 の差が 4.2e-5。(d) 1.2e308 級の数量 2 行：A13-01 が 2.4e+305 と inf、B5-01 が 0.0 と nan。(e) 漏洩率 1−1e-8 で補充なし：B1-02 の年次の値が 5.8e-9。
- **所在**：
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md)
  - [`09_APPROX_STUDY/research_code/fastcalc/closed_forms.py`](../../../09_APPROX_STUDY/research_code/fastcalc/closed_forms.py)
- **確かめ方**：第2回：数値の検査担当が個別の入力で示し、検証担当が 5 つの場合すべてを再現した。(b) は厳密な有理数の計算と比べ、基準計算が 1.8e-16 まで正しく、統合モデルが 5.25e-8 ずれることを確かめた。(a) は逆に統合モデルが燃料だけの和と一致し、基準計算が桁を失う。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：通常の大きさの値では現れない。研究の 681 シナリオでは、床なしの比較でも 1e-9 を超える葉は 0 だった。
- **関係する第2回の指摘**：NUM-10
- **第2回の指摘の影響**：「許容差は相対 1e-9、不一致なし」は、どの入力についても成り立つ主張としては使えない。06_OPEN_ISSUES の D-4 は許容差だけを述べ、この限界を書いていない。中断した修正の仕様は、(b) だけコードを直し（全年の和に重み付きの最後の年を足す形にする）、(a)(c)(d)(e) は文書に限界として書く、としていた。文書化は行われていない。
- **今の時点で言ってよいこと**：差を取る量（B6＝B6-03−B2-01、基準案との差、端数年の補正）、桁あふれ、漏洩率が 1 付近の等比では、2 つの計算の差が 1e-9 を超える入力がある。どちらの計算が正確かは場合による。
- **使ってはいけない記述**：
  - 一致は丸め誤差の範囲であり、どの入力でも相対 1e-9 以内に収まる
  - 差が出た場合は統合モデルの側の誤りである（(a) では基準計算の側が桁を失う）
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：新研究の誤差の目標を決めるときの下限の目安として使う。基準計算そのものが桁を失う量があるので、基準計算との差だけでモデルの誤りを判定できない場合がある。変換を使うモデル（級数の打ち切り、行列の分解）では、この種の桁落ちが増える可能性があるので、同じ入力を検査に入れる。
  - 条件・注意：誤差の測り方（相対か絶対か、どの量を分母にするか）を先に決める。旧研究の比較は合計を基準にした床を持っていた（CK-R3-30）。
- **分類の根拠**：
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):109-119
  - [`09_APPROX_STUDY/research_code/fastcalc/closed_forms.py`](../../../09_APPROX_STUDY/research_code/fastcalc/closed_forms.py):140-158
  - [`materials/interrupted_fix/specs/SPEC_A1.md`](../materials/interrupted_fix/specs/SPEC_A1.md):195-203, 215-220
- **分類した観点**：R3（統合モデルとその根拠）

<a id="ck-r3-30"></a>

## CK-R3-30　一致の確認に使った比較の弱点（NUM-11：床、無限大、真偽値、余分な葉）

- **区分**：4　不具合・未解決事項
- **内容**：common/compare.py の比較と、bench/verify_unified.py での使い方の弱点。(1) 基準側が ±inf のとき、相手が何であっても合格になる（誤差が NaN になり、比較が偽になる）。(2) 真偽値 True と整数 1 を等しいとみなす。(3) 床 1e-9×|SUM-03|（kgCO2e）を、無次元の葉を含むすべての葉に当てる。ベンチマーク S では 0 でない葉 4,346 個のうち 19 個、M では 33,208 個のうち 1,226 個（3.7％）が床より小さく、実質の許容差が相対 1e-9 より緩い。報告書は床に触れていない。(4) 合計のみの出力の比較は、余分な葉を調べない。
- **所在**：
  - [`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../../09_APPROX_STUDY/research_code/bench/verify_unified.py)
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md)
- **確かめ方**：第2回：数値の検査担当が compare() を直接呼んで示し、検証担当が 4 点すべてを再現した。そのうえで両者が、床なし・無限大と型に厳密・余分な葉を数える比較で 681 シナリオをやり直し、不一致 0、余分な葉 0 を確かめた。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：比較の方法の弱点。681 シナリオについては、この弱点が隠していた不一致はなかった（第2回で確認）。
- **関係する第2回の指摘**：NUM-11
- **第2回の指摘の影響**：「許容差は相対 1e-09」という報告書の記述は、床があるので正確でない。ただし 681 シナリオの結論は変わらない。中断した修正 a1 は、比較を床 0 にし、無限大と真偽値を厳密にし、合計のみの余分な葉を失敗にしたと申告している（未検証）。
- **今の時点で言ってよいこと**：60e720f の比較は、床と、無限大・真偽値の扱いのために、一部の不一致を見逃し得る。681 シナリオでは実際には何も見逃していなかった。
- **使ってはいけない記述**：
  - 比較は純粋に相対 1e-9 で、すべての違いを捕まえる
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：新研究の誤差測定では、比較の規則（相対と絶対の床、無限大と NaN、型、欠けた葉と余分な葉）を最初に定義し、報告書に書く。第2回の検査担当の厳密な比較の実装が保存されている（checker_scripts/numeric/h.py）。
  - 条件・注意：近似を扱う新研究では、床なしの相対誤差は 0 に近い量で意味を持たないので、量ごとに尺度を決める必要がある。その尺度は明示する。
- **分類の根拠**：
  - [`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../../09_APPROX_STUDY/research_code/bench/verify_unified.py):115-130
  - [`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../../09_APPROX_STUDY/04_VERIFICATION/README.md):21
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):121-131
  - [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json): findings (NUM-11)
- **分類した観点**：R3（統合モデルとその根拠）

<a id="ck-r7-22"></a>

## CK-R7-22　681 架空シナリオでの基準計算と統合モデルの一致（記録された測定）

- **区分**：1　検証済み成果
- **内容**：統合モデル（fastcalc）の全出力と合計のみの 2 形式を、基準計算と leaf ごとに比べた記録。681 シナリオ（ベンチマーク 3、境界条件 32、母集団 400、欠陥入り 60、入力を壊す操作 144、小数の境界 10、段階の部分集合 32）で失敗 0、相対誤差の最大は 4.8e-13。
- **所在**：
  - [`09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json`](../../../09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json)
  - [`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../../09_APPROX_STUDY/04_VERIFICATION/README.md)
  - [`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../../09_APPROX_STUDY/research_code/bench/verify_unified.py)
- **確かめ方**：旧研究の bench/verify_unified.py による測定（コミット済みの JSON）。第2回の数値の反例探しが、同じ 681 シナリオを下限なし・型に厳密な独自の比較でやり直し、相対 1e-9 を超える leaf 0（最大 4.77e-13、SUM-08.delta）。検証者も独自にやり直して 7,962,996 個の leaf で差 0、例外の非対称 0、余分な leaf 0。報告書検査は 94 シナリオを再実行して失敗 0、境界条件の群の最大誤差が保存値と全桁一致。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：架空データだけ。この 681 シナリオについての事実で、43ba5d7 の版のコードどうしの一致。実建物での精度でも、原版ブックとの一致でもない。基準計算と統合モデルは同じ主担当が書いた。
- **関係する第2回の指摘**：NUM-1、NUM-2、NUM-3、NUM-4、NUM-5、NUM-6、NUM-7、NUM-10、NUM-11、REP-16
- **第2回の指摘の影響**：「すべての入力で一致する」という一般化は成り立たない：欠陥のない入力で 1 件（周期 1.000000001。NUM-1）、非有限値（NUM-2）、係数値 0 でガス別量が 0 でない係数（NUM-3）、短い年次表と別の欠陥の組合せ（NUM-4）、擬似 ID と同じ係数 ID（NUM-5）、ガスの一覧の欠陥（NUM-6）、float の段の添字（NUM-7）、桁落ち・桁あふれ（NUM-10）で食い違う。
- **今の時点で言ってよいこと**：この 681 シナリオでは、統合モデルの 2 形式は基準計算と相対 1e-9 以内で一致し（記録の最大 4.77e-13）、第2回の床なしの再比較でも、相対 1e-9 を超える差は 0 件だった（最大 4.77e-13）。
- **使ってはいけない記述**：
  - 「統合モデルは、すべての入力で基準計算と同じ結果になる」
  - 「不備のある入力でも同じ値を返し、同じ不備を報告する」（検証した 36 種の操作の外では成り立たない例がある）
- **新研究での再利用**：候補（ルート A・C）
  - 使い道：ルート A で保存済みの簡素化成果（統合モデル）を出発点にするとき、その成果がこの母集団で基準計算を再現していたという根拠と、回帰確認の合格線（681 シナリオ、相対 1e-9）として使う。
  - 条件・注意：一致の範囲はこの母集団に限る。母集団に無い種類の入力（CK-R7-16 の一覧）では食い違いが確認されている。統合モデルの実装 engine.py は R7 は読んでいない。
- **分類の根拠**：
  - [`09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json`](../../../09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json): scenarios=681、tolerance=1e-09、by_group（benchmark 3 件・最大 1.4e-13、edge 32 件・最大 2.1e-14、population 400 件・最大 4.8e-13、defective 60 件・最大 4.9e-14、mutated 144 件・最大 4.2e-14、decimal 10 件・最大 1.5e-14、stage_subset 32 件・最大 2.1e-14）、failures=[]、all_exact=true
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):112,118（NUM-10 の本文と検証：681 シナリオを下限なしで再比較、差 0、最大 4.77e-13、7,962,996 leaf）
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):134（CHECKS 9）；[`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):128（CHECKS 2：94 シナリオの再実行）
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））
- **停止後の点検による訂正**：点検の指摘 V1-10 により、上の記述の一部を改めた。分類担当の元の記述は `materials/classification/R7.json`、訂正の内容は `materials/classification/overrides.json` にある。

