# 索引の詳細 T04：基準計算と規約

[INDEX.md](../INDEX.md) の項目ごとの詳細。分類担当（読み取り専用）が書いた内容を、欄ごとに載せる。停止後の点検で改めた項目には「停止後の点検による訂正」と記してある。
旧研究の数値はすべて架空データでの値で、対象は独立概念モデルである。原版の表計算との一致や、実建物での精度を示すものではない。
所在の表記：`09_APPROX_STUDY/…` などは `whole-life-carbon-jcat-study/` からの位置、`materials/…` はこの保存フォルダからの位置。

| 項目 | 区分 | 題 |
|---|---|---|
| [CK-R2-01](#ck-r2-01) | 1 | 基準計算の本体（70 評価単位の逐次計算。誤差と負荷を測る基準） |
| [CK-R2-02](#ck-r2-02) | 1 | 時間の規約（事象の数え方、年への割り当て、許容幅 1e-9） |
| [CK-R2-03](#ck-r2-03) | 4 | 時間の規約のナイフエッジ（周期 1.000000001 で年の割り当てが丸めで決まる） |
| [CK-R2-04](#ck-r2-04) | 2 | 完全性の印（X-02 の complete・incomplete_units、SUM-01〜03 の complete） |
| [CK-R2-05](#ck-r2-05) | 4 | 完全性の印の穴（データの流れを追っていない。B3・B5、SUM-08、B2-01） |
| [CK-R2-06](#ck-r2-06) | 2 | 使えない係数と不正な値の扱い（除外して数える規則。実装されている範囲） |
| [CK-R2-07](#ck-r2-07) | 4 | 不正な値の扱いの穴（検査されない値、無効な周期、例外、ゲートとの食い違い） |
| [CK-R2-08](#ck-r2-08) | 2 | 規約の一覧（06_OPEN_ISSUES の B-1〜B-21 と base.py 冒頭の規約文） |
| [CK-R2-09](#ck-r2-09) | 4 | 定義文とコードの食い違い、定義文に無い動作、数値上の限界（基準計算の側） |
| [CK-R2-10](#ck-r2-10) | 4 | 基準計算について検証できていないこと（06_OPEN_ISSUES の D） |
| [CK-R7-17](#ck-r7-17) | 1 | 基準計算（refcalc）のうち、定義文からの独立した書き直しと一致した 53 単位 |
| [CK-R7-18](#ck-r7-18) | 2 | 基準計算のうち、独立した書き直しがない 14 単位と、間接的な確認だけの 3 単位 |
| [CK-R7-19](#ck-r7-19) | 4 | 基準計算の定義の穴（不正な値・部分的な境界・検査との食い違い） |
| [CK-R7-20](#ck-r7-20) | 4 | 時間規則の端（周期 1.000000001）と、修繕の除外年の閉形式の不一致 |
| [CK-R7-28](#ck-r7-28) | 1 | 本研究が決めた規約 B-1〜B-21 のうち、第2回でコードとの符合が確認されたもの |
| [CK-R7-29](#ck-r7-29) | 4 | 規約一覧に無い規約と、定義文に書かれていない挙動 |

<a id="ck-r2-01"></a>

## CK-R2-01　基準計算の本体（70 評価単位の逐次計算。誤差と負荷を測る基準）

- **区分**：1　検証済み成果
- **根拠の強さについての注記（索引の作成者）**：書き直しとの一致は第2回の検査担当 1 者の報告で、反証検査担当はこの一致をやり直していない。
- **内容**：独立概念モデルの評価単位ごとに 1 関数を置き、概念式の定義どおりに行ごと・年ごと・事象ごとに計算する Python コード（標準ライブラリのみ、製品用エンジンではない）。関数の説明文がその単位の定義で、台帳の reference_semantics と同文。registry.run_all が評価期間を検査したうえで依存順に 70 単位を実行する。統合モデルと近似候補の誤差・負荷は、すべてこの結果を基準に測られた。
- **所在**：
  - [`09_APPROX_STUDY/research_code/refcalc/__init__.py`](../../../09_APPROX_STUDY/research_code/refcalc/__init__.py)
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py)
  - [`09_APPROX_STUDY/research_code/refcalc/registry.py`](../../../09_APPROX_STUDY/research_code/refcalc/registry.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py)
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
- **確かめ方**：(1) 作成者の試験 tests/test_refcalc.py 8 件（手計算との照合 1 例、境界条件 32 件での恒等式と検査単位、標準ベンチマーク S、入れた不備の検出など）。(2) 04_VERIFICATION/unified_model_exactness.json：書き方の違う統合モデルと、架空の 681 シナリオ・70 単位で突き合わせ、許容差 相対 1e-9 で不一致 0（最大 4.8e-13）。(3) 第1回の独立検査（初版が対象）：定義からの再導出で定義の穴が見つかり、改めた（INDEPENDENT_REVIEW.md 2.2）。(4) 第2回の独立検査（43ba5d7 のコード。60e720f と同一）：検査担当が台帳の定義文と base.py の規約文だけから 53 単位を書き直し、119 シナリオ（検証用の母集団 24、境界条件 32、不備を入れたもの 14、壊し方 36、小数境界 5、段階の部分集合 8）で全数値・全件数が相対 1e-9 以内で一致。違いは表示と印の 4 点だけ（X-15 の未解決行の表示、B2-01 の computed が壊し方 4 件、SUM-07 の未定義時の形、負の廃棄質量での C-05 の n_mass_unchecked が 4 と 5）。X-04（by_gas）・X-05・SUM-08 は 50 シナリオで間接的に一致。14 段階の全部分集合 16,384 通り（1 シナリオ、T=62.5）で不整合 0。70 単位で台帳の定義文と説明文、depends_on が一致（差 0）。別の検査担当が 681 シナリオを床なしの厳密比較でやり直し、葉 7,962,996 個で不一致 0（最大 4.77e-13）。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：架空データのみ。独立概念モデルのみ。再導出に使われたのは小さいシナリオ（規模 M・L は対象外）、評価期間 99.9 年以下、許容差 相対 1e-9。規約（base.py の説明文）は所与として使われ、規約自体の当否は検査されていない。SYS-01〜04、QA-01、QA-03、QA-04、X-03、X-08、X-09、X-11、X-17、STO-01、STO-02 の 14 単位は独立の書き直しをしておらず、コードと定義文の読み比べと個別の入力での確認だけ。実建物での精度、原版ブックや他のツールとの関係は何も示さない。
- **関係する第2回の指摘**：RED-1、RED-2、RED-3、RED-4、RED-5、RED-6、RED-7、RED-8、RED-9、RED-10、RED-11、RED-12、NUM-1、NUM-2、NUM-3、NUM-4、NUM-5、NUM-8、NUM-10
- **第2回の指摘の影響**：不備のない入力での数値は否定されていない。弱められたのは次の 3 点。(a) 不備のある入力では「除外して数え、合計に不完全の印を付ける」という一般的な記述（RED-1、RED-2、RED-3、RED-5、RED-6、RED-10、NUM-2、NUM-4）。(b) 時間の規約が 2 進の丸めに依存しないという記述（NUM-1 への検証者の追記）。(c) 定義文がコードの動作を言い尽くしているという前提（RED-4、RED-7、RED-8、RED-9、RED-11、RED-12、NUM-3）。
- **今の時点で言ってよいこと**：公開中の版の基準計算（コードは 43ba5d7 と同じ）は、架空の 119 シナリオで、定義文と規約文だけから独立に書き直した 53 単位の実装と、数値と件数が相対 1e-9 以内で一致した（例外は「確かめ方」に記した 4 点：表示 2、印 1、負の廃棄質量を入れた壊し方での C-05 の件数 1）。X-04（ガス別内訳）・X-05・SUM-08（基準案のある 3 シナリオ）は 50 シナリオで間接的に一致した。比べたのは各単位の値・内訳・件数の欄で、X-02 と SUM-01〜03 の完全性の印（complete、incomplete_units）は比べていない。70 単位すべてで台帳の定義文と関数の説明文は同文である。不備のない架空シナリオについて、基準計算は書かれた定義どおりに計算する、と言える範囲はここまで。
- **使ってはいけない記述**：
  - refcalc/base.py 46-47 行「A result that could not be computed completely is flagged」を、すべての入力で成り立つとする読み方（RED-1、RED-2、RED-3、RED-5）
  - 09_APPROX_STUDY/README.md 26 行（60e720f では 18 行）「不備のある入力や、冗長な入力どうしが食い違う場合も、同じ値を返し、同じ不備を報告する」を一般の入力に広げた読み方（NUM-2、検証者の追記）
  - 06_OPEN_ISSUES/README.md D-3 と INDEPENDENT_REVIEW.md 7 行「対応後の版に対する独立した検査は、まだ行っていない」（第2回の検査は行われたが、この 2 文書には反映されていない）
  - 台帳 reference_note の「reference_semantics が定義」を、定義文だけで各単位の結果が決まるという意味に取ること（RED-4、RED-7、RED-9、RED-12）
  - 基準計算の値を、実建物の排出量や、原版ブック・他のツールの結果の代わりに使うこと（06_OPEN_ISSUES D-1、D-2 が対象外と明記）
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：コミット 60e720f の refcalc を変更せずに固定の基準（誤差の分母）として使う。70 単位の定義文（説明文 = reference_semantics）と depends_on は、ルート B で「元の式」と依存関係を読む出発点になる。結果の形式（value、by_item、by_year、by_stage、ok と violations、件数。「_」で始まるキーは作業用で比較対象外）は、新しいモデルとの突き合わせにそのまま使える。
  - 条件・注意：(1) コードを変えない。65ff124 の a1 の版は別物で未検証。(2) 定義どおりの動作が独立に確認されたのは、不備のない入力（make_scenario の dirty=False、境界条件 32 件、検証用の母集団）で、周期が生成器の作る値（整数、小数 2 桁、T/n）のとき。境界は 14 段階すべて、または不備のない入力での段階の部分集合。(3) 避ける入力：周期 1.000000001 のように τ×(1−1e-9) が整数に丸まる周期と極端に短い正の周期（CK-R2-03）、B3・B5 を上流の段階なしで含む境界と不備のある行の組合せ（CK-R2-05）、年次量・電力係数・係数値・換算倍率の負値・NaN・無限大、無効な周期、None を含む表や一覧、評価期間より短い年次表（CK-R2-07）、係数 ID「GRID」「REFRIGERANT」、値 0 でガス別量が 0 でない係数、施設管理の比率 1.0 で燃料がごく小さい入力（CK-R2-09）。(4) 規模 M・L と 99.9 年を超える評価期間は、定義からの再導出の対象外（統合モデルとの突き合わせだけがある）。(5) SUM-08 は synth.population.BASELINES というプロセス内の登録表を読む。基準案はシナリオの外にある入力として管理する。(6) 記録済みの負荷の数値（規模 S で 2,528,394 命令など）は 43ba5d7 のコードに対応する。
- **分類の根拠**：
  - [`09_APPROX_STUDY/research_code/refcalc/__init__.py`](../../../09_APPROX_STUDY/research_code/refcalc/__init__.py):1-7（1 単位 1 関数、簡略化なし、比較の基準）
  - [`09_APPROX_STUDY/research_code/refcalc/registry.py`](../../../09_APPROX_STUDY/research_code/refcalc/registry.py):34-43, 90-104（登録と依存順の実行、check_period）
  - refcalc/units_*.py の @unit の数：units_pre_a 22、units_b 22、units_c_sum 26、計 70（ソースの文字列を数えた）
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)：units 70 件、computable_in_reference が真 70 件、reference_note
  - [`09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json`](../../../09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json)：scenarios 681、tolerance 1e-09、all_exact true、failures 0 件
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):146（CHECKS PERFORMED 1〜7：53 単位、119 シナリオ、16384 部分集合、70 単位の定義文一致）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):148（COULD NOT CHECK：独立に書き直していない 14 単位、規模 M・L と 99.9 年超は未実施）
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):134（CHECKS PERFORMED 9：681 シナリオの床なし再比較、最大 4.77e-13）、numeric.md:118（葉 7,962,996 個、差 0）
  - [`09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md`](../../../09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md):7-8, 28-40（第1回の指摘と対応、対応後は未検査との記述）
- **分類した観点**：R2（基準計算・架空データ・比較・試験）
- **停止後の点検による訂正**：点検の指摘 V1-12 により、上の記述の一部を改めた。分類担当の元の記述は `materials/classification/R2.json`、訂正の内容は `materials/classification/overrides.json` にある。

<a id="ck-r2-02"></a>

## CK-R2-02　時間の規約（事象の数え方、年への割り当て、許容幅 1e-9）

- **区分**：1　検証済み成果
- **根拠の強さについての注記（索引の作成者）**：独立実装との一致は第2回の検査担当 1 者の報告。試験の合否は停止後に確かめていない。
- **内容**：評価期間 T は実数。評価年は y = 1..ceil(T)、年重みは w_y = min(1, T − (y−1))。周期 L の事象は τ = n×L（n = 1, 2, …）を 1 つずつ数え上げ、τ < T×(1 − 1e-9) のものだけを評価期間の内側とする（T ちょうどは数えない）。事象は年 max(1, ceil(τ×(1 − 1e-9))) に属する。明示の一覧は 0 < t で内側のものだけを使い、周期が欠損・非有限・非正なら事象なし。by_year は Y+1 個で添字 0 が τ = 0。
- **所在**：
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py)
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md)
  - [`09_APPROX_STUDY/research_code/tests/test_refcalc.py`](../../../09_APPROX_STUDY/research_code/tests/test_refcalc.py)
  - [`09_APPROX_STUDY/research_code/tests/test_closed_forms.py`](../../../09_APPROX_STUDY/research_code/tests/test_closed_forms.py)
- **確かめ方**：作成者の試験が期待値を持つ：T=99.9・周期 33.3 で更新 2 回・建替 2 回（test_decimal_period_boundary）、T=10.5・周期 3.5 で更新 2 回、更新の年 4 と 7 を修繕から除く（test_hand_calculation）、(99.9, 33.3)→2、(99.9, 11.1)→8、(60.0, 0.1)→599、(12.3, 4.1)→2、(0.3, 0.1)→2、event_year(25×2.2)=55（test_closed_forms.py）。一致確認の「小数の評価期間と周期の端」10 シナリオで統合モデルと不一致 0。第2回：検査担当が同じ規約文から書いた独立実装と、小数境界と非整数の評価期間で一致。B1-02〜04、B3-01、B4-01〜03、B5-01、X-07、X-10、QA-02 の間に不整合なし。試験の合否は今回実行していない。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：架空データ、独立概念モデル。規約は本研究が決めたもので、他のツールの仕様ではない（base.py 3-4 行）。確認された周期は、生成器の作る値と小数境界の組（99.9 と 33.3 など 5 組）。T ちょうどを数えない、切り上げた年に置く、という選択そのものの当否は検査対象外。
- **関係する第2回の指摘**：NUM-1、RED-3、RED-11、RED-12
- **第2回の指摘の影響**：NUM-1 への検証者の追記により、「許容幅によって規約は 2 進の丸めに依存しない」は成り立たない（CK-R2-03）。RED-3：無効な周期が件数なしで「事象なし」になる規約は 06_OPEN_ISSUES の B に載っていない。RED-11(4)：明示の一覧で同じ年が重なると、その回数だけ数える（B に未記載、QA-02 は警告しない）。RED-12(7)：正の周期に下限がない。
- **今の時点で言ってよいこと**：コミット版の基準計算は、内側の判定 τ < T×(1 − 1e-9) と年の割り当て max(1, ceil(τ×(1 − 1e-9))) を、B1・B3・B4・B5・X-07・X-10・QA-02 で同じ関数から使う。小数境界の 5 組と非整数の評価期間では、規約文から書いた独立実装と回数・年が一致した（第2回、架空データ）。
- **使ってはいけない記述**：
  - refcalc/base.py 14-15 行「The tolerance makes the rule independent of binary rounding」
  - 06_OPEN_ISSUES/README.md B-15 の括弧書き（許容幅で、小数の周期が浮動小数点の誤差で端をまたがない）を、すべての周期についての保証と読むこと
  - INDEPENDENT_REVIEW.md 35 行の対応（許容幅を定義した）で、端の問題が解消したという読み方
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：固定の基準の一部。新しいモデルが同じ回数と同じ年の割り当てを再現できるかを見る基準にする。回数は T と L だけで決まる階段状の関数、年の割り当ては切り上げで、少数の変換（母関数、畳み込みなど）で表す対象になる。
  - 条件・注意：周期は丸めの端を避ける。確認済みの反例は倍精度値 1.000000001 の 1 つ（CK-R2-03）。整数 m に対する m×(1±1e-9) 付近と 1/(1−1e-9) 付近は、a1 の仕様書が追加の試験対象に挙げた帯で、コミット版での挙動は未確認（実行が必要）。1 年未満の周期は 1 行当たりの事象が増える（0.1 年・T=60 で 599 回）。同じ年に複数の事象が入る場合の扱い（B1-02 は年末にまとめて反映）は定義文どおり。
- **分類の根拠**：
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py):6-21（規約文）、66（EPS = 1e-9）、91-93（inside）、109-118（periodic_events）、125-126（event_year）
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md):26-28, 43（B-1、B-2、B-3、B-15）
  - [`09_APPROX_STUDY/research_code/tests/test_refcalc.py`](../../../09_APPROX_STUDY/research_code/tests/test_refcalc.py):58-83, 98-105
  - [`09_APPROX_STUDY/research_code/tests/test_closed_forms.py`](../../../09_APPROX_STUDY/research_code/tests/test_closed_forms.py):80-86
  - [`09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json`](../../../09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json)：by_group.decimal（scenarios 10、failed 0）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):146（CHECKS PERFORMED 6：時間の規約は一貫して使われ、不整合なし）
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):138（検証者の追記 1：基準計算のループは NUM-1 の入力で書かれた規約から外れる）
- **分類した観点**：R2（基準計算・架空データ・比較・試験）

<a id="ck-r2-03"></a>

## CK-R2-03　時間の規約のナイフエッジ（周期 1.000000001 で年の割り当てが丸めで決まる）

- **区分**：4　不具合・未解決事項
- **内容**：浮動小数点で 周期×(1 − 1e-9) がちょうど 1.0 に丸まる周期（倍精度値 1.000000001、16 進で 0x1.000000044b830p+0）では、事象の属する年が丸めで決まり、基準計算のループの結果が、書かれた規約を厳密な有理数で計算した結果と食い違う。不備のない有効な入力で起きる。あわせて、正の周期に下限がなく、ごく短い周期は事象を 1 つずつ数えて保持する（RED-12(7)）。
- **所在**：
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py)
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md)
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md)
- **確かめ方**：第2回の検査担当と検証者がそれぞれ自分のスクリプトで再現。T=7：事象 6 回の年が [1, 2, 4, 4, 6, 7]（異なる年 5）。T=30：異なる年 26（事象 29）。T=60：異なる年 48（事象 59）。厳密な有理数で規約を計算すると、T=60 の 59 回は年 2..60 の 59 個の異なる年に入る。全行の周期を 1.000000001 にした架空シナリオ（T=60、資材 12 行）で、B3-01 は基準計算 229291.25152413402、統合モデル 19107.60429367785（相対差 0.9167）、SUM-03 は 114273919.42727956 と 114063735.7800491（相対差 1.84e-3）。走査：検査担当 702,603 組（±4000 ulp）、検証者 1,512,126 組（±6000 ulp）と 1・2・3・5 付近の乱数 300,000 個で、食い違うのはこの倍精度値 1 つだけ。RED-12(7)：周期 1e-4 年・T=60 で 1 行が 599,999 事象。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：架空データ、独立概念モデル。影響する単位は、同じ event_year を使う B3-01（修繕を除く年）、B4-02・B5-01 の by_year、B1-02〜04、X-07。「ほかに食い違う倍精度値がない」ことは証明されていない（走査した範囲で見つからなかっただけ）。内側の判定（回数）について同種の反例は第2回の資料に無い。
- **関係する第2回の指摘**：NUM-1、RED-12
- **第2回の指摘の影響**：この項目自体が第2回の指摘。SPEC_A1 は REC-1 と APP-5 を同じ問題の別の見方として扱っている（両指摘の本文はこの読み取りの範囲外）。検証者の整理：この入力で閉形式（統合モデル）が返すのは厳密計算の値、基準計算のループが返すのは丸めの産物。どちらを正とするかは定義に書かれていない。
- **今の時点で言ってよいこと**：周期が倍精度値 1.000000001 のとき、コミット版の基準計算は、書かれた規約の厳密な値とは違う年に事象を置く。この 1 点以外に食い違う周期は、約 151 万組の走査では見つかっていない。
- **使ってはいけない記述**：
  - refcalc/base.py 14-15 行「independent of binary rounding」
  - fastcalc/closed_forms.py の説明文「All of them are exact」と、03_MODELS/DERIVATIONS.md D3 の「c >= 1 なら事象ごとに年が違い」（NUM-1 が引用。両ファイルの本文はこの読み取りの範囲外）
  - 記録 EX-B3-01-M1 の成功・検証済みの表示を、すべての入力についての一致と読むこと（NUM-1）
- **新研究での再利用**：候補にしない
  - 理由・注意：新研究の入力に、周期 1.000000001（1 + 1e-9 に相当する倍精度値）を入れない。入れる場合は、基準計算の値を「定義の値」とみなせないことを明記する。極端に短い周期も避ける（第2回の例は 1e-4 年で 1 行 599,999 事象。1 行当たり約 1 万事象を超える周期は第2回でも試されていない）。a1 の版（厳密な整数演算）はこの欠陥への修正案だが未検証（CK-R2-19）。
- **分類の根拠**：
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):1-11（NUM-1、判定 CONFIRMED、数値と走査の範囲）
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):138（検証者の追記 1：厳密な有理数での年 2..60、基準計算は 48 個の異なる年）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):136, 142（RED-12(7)：refresh_cycle 1e-4、T=60 で B4-03 が [599999]）
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py):109-118, 125-126（数え上げと event_year。浮動小数点の積 n*period を使う）
  - [`09_APPROX_STUDY/research_code/tests/test_closed_forms.py`](../../../09_APPROX_STUDY/research_code/tests/test_closed_forms.py):26（試験が引く周期のずれは 1e-15、1e-12、1e-10、1e-8、1e-6 で、1e-9 が無い）
- **分類した観点**：R2（基準計算・架空データ・比較・試験）

<a id="ck-r2-04"></a>

## CK-R2-04　完全性の印（X-02 の complete・incomplete_units、SUM-01〜03 の complete）

- **区分**：2　暫定・未検証成果
- **内容**：X-02 が、対象段階ごとに手書きの表 STAGE_UNITS に載っている単位を見て、n_skipped・n_routes_skipped・n_partial が 1 以上、または computed が偽の単位を incomplete_units に挙げ、1 つでもあれば complete を偽にする。SUM-01〜03 はその complete を引き継ぐ。第1回の検査への対応として加えられた仕組み。
- **所在**：
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py)
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py)
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md)
  - [`09_APPROX_STUDY/research_code/tests/test_refcalc.py`](../../../09_APPROX_STUDY/research_code/tests/test_refcalc.py)
- **確かめ方**：作成者の試験 1 件（test_wrong_unit_stage_or_range_is_skipped_and_reported：14 段階すべてが対象の小さいシナリオで、係数の単位・対象段階の誤り、負の数量、月単位の年次量を入れ、complete が偽、incomplete_units に C2-01 が入ることを期待）。第2回：再導出した実装と件数（B4-02 の n_partial、C3・C4 の経路の件数を含む）が 119 シナリオで一致。境界 ['A1-A3','B3'] では complete 偽・['A13-01','X-01']、['B4'] では偽・['B4-02'] を確認。境界に上流の段階が無い場合の穴が見つかった（CK-R2-05）。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：架空データ、独立概念モデル。印が働くことが確認されたのは、除外の件数を自分で持つ単位が対象段階に入っている場合だけ。
- **関係する第2回の指摘**：RED-1、RED-2、RED-3、RED-5、RED-12
- **第2回の指摘の影響**：RED-1（CONFIRMED）：B3・B5 は上流の単位の行結果から作るが、表には B3-01・B5-01 しか無く、上流で除外があっても complete は真のまま。RED-2・RED-3：検査されない値（負・NaN の年次量、無効な周期など）は件数に入らないので、14 段階すべてが対象でも complete は真のまま。RED-5：SUM-08 は完全性を見ない。RED-12(2)：B2-01 は B6-01 が算出されなくても computed 真を返す。
- **今の時点で言ってよいこと**：X-02 の定義文（対象段階の単位が除外をしたらその単位を挙げる）どおりにコードは動く。「合計が不完全なら必ず印が付く」とは言えない。印は、対象段階に属する単位が自分で数えた除外だけを反映する。
- **使ってはいけない記述**：
  - 06_OPEN_ISSUES/README.md B-17「使えない行・経路・項目は合計に入れず、件数を報告し、合計に『不完全』の印を付ける」を一般の保証と読むこと
  - refcalc/base.py 46-47 行と、SUM-01・SUM-03 の定義文「除外した行などがあれば complete を偽にする」
  - INDEPENDENT_REVIEW.md 33 行の対応（合計に「不完全」の印を付ける）が、すべての境界で成り立つという読み方
- **新研究での再利用**：候補（ルート A・C）
  - 使い道：固定の基準の出力の一部として読む。不備のない入力では常に complete が真になるので、新しいモデルとの比較では真であることの確認にだけ使う。
  - 条件・注意：不備のある入力の検出器としては使わない。complete が真でも、CK-R2-05 と CK-R2-07 の入力では合計が欠けている、または NaN・負になる。
- **分類の根拠**：
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py):240-250（STAGE_UNITS、_incomplete）、253-291（X-02）、438-454（SUM-01〜03）
  - [`09_APPROX_STUDY/research_code/tests/test_refcalc.py`](../../../09_APPROX_STUDY/research_code/tests/test_refcalc.py):107-128
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):1-11（RED-1、検証者の確認値）
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md):45（B-17）
- **分類した観点**：R2（基準計算・架空データ・比較・試験）

<a id="ck-r2-05"></a>

## CK-R2-05　完全性の印の穴（データの流れを追っていない。B3・B5、SUM-08、B2-01）

- **区分**：4　不具合・未解決事項
- **内容**：対象段階に B3 または B5 があり、その上流の段階（A1-A3。B5 では A4・A5・C も）が対象外のとき、上流の行が除外されて B3・B5 の値が下がっても、complete は真、incomplete_units は空のままになる。SUM-08 は基準案と当該案の完全性を条件にも結果にも含めない。B2-01 は B6-01 が算出されないとき computed 真・値 0.0 を返す。
- **所在**：
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py)
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md)
- **確かめ方**：第2回の検査担当と検証者が再現。架空シナリオ（シード 11、RC・office、T=60、資材 12 行、建替周期 25）で、数量の大きい資材 3 行を欠損、設備 1 行の係数を未登録にすると、対象 ['B3']：SUM-03 が 98378.05 → 43676.16（−55.6％）で complete 真。対象 ['B5']：894813.87 → 333032.14（−62.8％）で complete 真。対象 ['B3','B5']：993191.93 → 376708.29 で complete 真。使用許諾 RESTRICTED の係数 1 つだけでも、対象 ['B5'] で 894813.87 → 741862.36（−17.1％）、complete 真。統合モデルも同じ値と同じ印を返す。RED-5：基準案の数量上位 4 行を欠損にすると SUM-08 は COMPARED のまま、削減率が 0.2123 → −0.1732（符号が反転）。当該案の側を欠損にすると 0.5406。登録の無い基準案 ID は NO_BASELINE（指定なしと同じ）。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：架空データ、独立概念モデル。穴が現れるのは、B3 または B5 を上流の段階なしで含む境界と、上流の行の不備の組合せ。14 段階すべてが対象なら、同じ不備は A13-01・X-01 経由で印が付く。不備と部分集合の組合せを調べたのは B1、B2、B3、B4、B5、B3+B5 だけ。
- **関係する第2回の指摘**：RED-1、RED-5、RED-12
- **第2回の指摘の影響**：RED-1 と RED-5 は CONFIRMED。検証に使われた段階の部分集合のシナリオ（verify_unified.py 73 行、population.py 186 行、test_refcalc.py 88・93 行）はすべて不備なしで、この組合せは一度も実行されていなかった。
- **今の時点で言ってよいこと**：コミット版の基準計算と統合モデルは、この組合せで同じ欠けた合計と同じ「完全」の印を返す。2 つが一致していても、印が正しいことにはならない。
- **使ってはいけない記述**：
  - 06_OPEN_ISSUES/README.md B-17 の「合計に『不完全』の印を付ける」
  - SUM-08 の「比較可能な場合だけ比較する」を、合計が完全な場合だけ比較するという意味に取ること
  - 基準計算と統合モデルが印まで一致していることを、印の正しさの根拠にすること
- **新研究での再利用**：候補にしない
  - 理由・注意：新研究で段階の部分集合を使うなら、不備のない入力に限る。SUM-08 を使うなら、基準案と当該案の両方が完全であることを呼び出し側で確かめる。a1 の版はデータの流れに沿った印に作り直したと申告しているが未検証（CK-R2-21）。
- **分類の根拠**：
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):1-11（RED-1）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):49-59（RED-5）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):133-143（RED-12(2)）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):150（検証者の追記 3：部分集合のシナリオはすべて不備なし。RESTRICTED の例）
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py):240-245（STAGE_UNITS の B3、B5）、495-518（SUM-08）
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py):199-206, 380-383（B3-01 は e0 = 0 の行を黙って飛ばす。B5-01 は上流の件数を見ない）
- **分類した観点**：R2（基準計算・架空データ・比較・試験）

<a id="ck-r2-06"></a>

## CK-R2-06　使えない係数と不正な値の扱い（除外して数える規則。実装されている範囲）

- **区分**：2　暫定・未検証成果
- **内容**：係数は、レコードがあり、使用許諾が PERMITTED_PUBLIC で、対象段階が使う段階と完全に同じで、単位が一致するか直接の換算が登録されているときだけ使う（base.lookup）。数量・質量・距離・率は、欠損（None）・NaN・無限大・負・範囲外なら、その行（または経路）を計算から除いて件数に数える（nonneg、ratio、positive）。0 や上限に丸めない。年次量の単位は「単位/year」だけ。評価期間が有限の正の数でなければ計算全体を ValueError にする。
- **所在**：
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py)
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md)
- **確かめ方**：作成者の試験（test_defects_are_detected：生成器が入れた不備の場所と SYS-01・SYS-02・SYS-03・C-05・QA-02・A13-02 の報告が一致することを期待。test_wrong_unit_stage_or_range_is_skipped_and_reported。test_invalid_study_period_is_refused：0、−5、NaN、無限大で ValueError）。一致確認：不備を入れたシナリオ 60 件と、36 種類の壊し方×4 の 144 件で統合モデルと不一致 0。無効な評価期間は 5/5 で両方がエラー。第2回：不備を入れた 14 件と壊し方 36 件で、定義文から書いた独立実装と数値・件数が一致。係数レコードとの乗算はすべて base.lookup を通ることを読み取りで確認。同じ第2回で、規則の届かない入力が見つかった（CK-R2-07）。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：架空データ、独立概念モデル。確認されたのは、生成器の 8 種類の不備と mutations.py の 36 種類の壊し方が触る項目だけ。INVALID_PERIODS の 5 つ目は 500.0 で、これは評価期間が無効だからではなく、年次表（130 個）が評価期間より短いために check_period が ValueError を出す（コードの読み取りによる。実行はしていない）。
- **関係する第2回の指摘**：RED-2、RED-3、RED-6、RED-10、RED-11、NUM-2、NUM-4
- **第2回の指摘の影響**：RED-2（CONFIRMED）：年次量（ガス、石油、地域熱、上水、下水、廃棄物）の負値・NaN は黙って使われ、B-18 と INDEPENDENT_REVIEW 2.2 の記述に反する。電力係数の値、工事期間の電力係数、係数値、換算倍率も検査されない（B-18 が名指ししていない穴）。RED-3（PARTLY_CONFIRMED）：無効な周期は件数なしで「事象なし」。RED-10（CONFIRMED）：評価期間以外の入力でも TypeError・IndexError が出る。RED-6（CONFIRMED）：SYS-01 が見るのは数値入力の一部。RED-11（PARTLY_CONFIRMED）：設備の廃棄係数が None のとき、SYS-03 は通り X-14 は除外する。
- **今の時点で言ってよいこと**：nonneg・ratio・positive・lookup で守られている項目（資材・設備・冷媒の数量、質量、距離、率、係数の使用条件）については、生成器の 8 種類の不備と 36 種類の壊し方で、基準計算は定義文どおりに除外して数えた（第2回の独立実装と数値・件数が一致）。
- **使ってはいけない記述**：
  - 06_OPEN_ISSUES/README.md B-18「負の数量・質量・距離、範囲外の率は、その行を計算から除いて数える」を、年次量を含むすべての数値入力に及ぶと読むこと
  - refcalc/base.py 41-45 行「None means MISSING ... skipped and counted」を、すべての None で例外が出ないと読むこと
  - INDEPENDENT_REVIEW.md 36 行「除外して数える規則に統一」
  - 04_VERIFICATION/README.md 25 行「無効な評価期間（0、負、非数、無限大）は 5/5 でエラー」の 5 件目が 500.0（年次表より長い期間）である点を、無効な評価期間の例として扱うこと
- **新研究での再利用**：候補（ルート A・C）
  - 使い道：固定の基準の動作の一部。新しいモデルが、不備のある行を同じ条件で除外するかを見るときの参照になる。
  - 条件・注意：不備のある入力を新研究で使うなら、生成器の 8 種類と 36 種類の壊し方の範囲に限る。CK-R2-07 の入力は使わない。
- **分類の根拠**：
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py):32-47（係数の使用条件、欠損と不正な値）、96-106（positive、nonneg、ratio）、133-143（lookup）、69-76（check_period）
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md):45-49（B-17〜B-21）
  - [`09_APPROX_STUDY/research_code/tests/test_refcalc.py`](../../../09_APPROX_STUDY/research_code/tests/test_refcalc.py):107-146
  - [`09_APPROX_STUDY/research_code/bench/mutations.py`](../../../09_APPROX_STUDY/research_code/bench/mutations.py):336（INVALID_PERIODS = (0.0, -5.0, nan, inf, 500.0)）
  - [`09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json`](../../../09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json)：by_group.defective（60、failed 0）、by_group.mutated（144、failed 0）、invalid_periods_refused_by_both「5/5」
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):146（CHECKS PERFORMED 1、5）
- **分類した観点**：R2（基準計算・架空データ・比較・試験）

<a id="ck-r2-07"></a>

## CK-R2-07　不正な値の扱いの穴（検査されない値、無効な周期、例外、ゲートとの食い違い）

- **区分**：4　不具合・未解決事項
- **内容**：コミット版の基準計算には、検査なしで演算に使われる数値入力と、例外で止まる入力がある。(a) 年次量、電力係数（系列と工事期間の値）、係数値、ガス別量、換算倍率は、負・NaN・無限大でもそのまま掛けられ、件数も印も SYS-01〜03 も反応しない。(b) 負・0・NaN・無限大の更新周期・耐用年数・建替周期は、件数なしで「事象なし」になる。(c) None の経路比率・電力係数・係数値・要約数量・用途別面積・事象一覧の要素は TypeError、評価期間より短い TABLE 型の年次表は IndexError になる。(d) SYS-01 は数値入力の一部しか見ず、NaN を MISSING にしない。設備の廃棄係数が None でも SYS-03 は通るが X-14 は除外する。
- **所在**：
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py)
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md)
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md)
- **確かめ方**：第2回の検査担当と検証者が再現（架空シナリオ、シード 11 ほか）。RED-2：ガスと上水の基準値を負にすると B6-03 が 1910920.70 → 1106878.12、B7-04 が 99907.16 → 70795.70、n_skipped 0、complete 真。ガスの基準値 NaN で SUM-03 が NaN、complete 真。電力係数の初期値 −0.4 で B6-03 が −2036536.49。工事期間の係数 −1 で A5-01 が −30324.2。係数値 NaN で SUM-03 が NaN、全ゲート合格。行の換算倍率を負にすると A13-01 の行結果が 30326.53 → −30326.53。検証者：ガスの基準値 −5e9 で SUM-03 が −630713478768.06、complete 真、全検査合格。RED-3：周期をすべて無効にすると B4 333158.14 → 0.0、B5 894813.87 → 0.0、SUM-03 7893398.71 → 6619741.07（−16.1％）、complete 真。RED-10：上の (c) の例外をそれぞれ再現。NUM-2：1 項目ずつ NaN・±無限大・None にした 3461 例のうち 212 例で基準計算と統合モデルが食い違う。NUM-4：短い年次表と、係数なしや単位違いが重なると、基準計算だけが IndexError。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：架空データ、独立概念モデル。型の違う入力（文字列など）と、NaN・無限大が 2 か所以上ある組合せは調べられていない。負の電力需要を max(0, …) で 0 にするのは B6-04 の定義文に書かれた式で、欠陥ではなく B-18 の文言との不整合（検証者の整理）。
- **関係する第2回の指摘**：RED-2、RED-3、RED-6、RED-10、RED-11、NUM-2、NUM-4、NUM-7
- **第2回の指摘の影響**：RED-2・RED-6・RED-10・NUM-2・NUM-4・NUM-7 は CONFIRMED、RED-3・RED-11 は PARTLY_CONFIRMED。RED-3 の訂正：無効な周期を事象なしとする規約は B4-01・B4-03 の定義文と base.py にはあり、無いのは B5-01・B1-02 の定義文、NaN・無限大への言及、06_OPEN_ISSUES の B。RED-11 の訂正：実際の食い違いは設備の廃棄係数（SYS-03 と X-14）だけで、EPD が使えないときの扱いは B-14 どおり。NUM-7：STEPWISE の段の添字が float でも基準計算は受け入れる（型注釈は int）。
- **今の時点で言ってよいこと**：年次量・電力係数・係数値・換算倍率・周期・None を含む表という入力の種類では、コミット版の基準計算の合計は、負・NaN になったり例外で止まったりし、そのとき complete は真のままである。この種類の入力に対する基準計算の値は、定義の値として使えない。
- **使ってはいけない記述**：
  - 06_OPEN_ISSUES/README.md B-18 と B-21（評価期間だけがエラーになる、という読み方）
  - 09_APPROX_STUDY/README.md 26 行と 04_VERIFICATION/README.md 23 行の「同じ値を返し、同じ不備を報告する」（NaN・無限大では基準計算は不備を何も報告せず、統合モデルと QA-01 の合否が食い違う）
  - SYS-01 の定義文「数値入力を 1 つずつ調べ」を、計算が読む数値入力すべてと読むこと。台帳の SYS-01 の branches 欄「NaN → MISSING」
- **新研究での再利用**：候補にしない
  - 理由・注意：新研究の入力は、数値がすべて有限で 0 以上（換算倍率は正）、周期は有限の正の数または None、年次表は ceil(T) 個以上、表や一覧に None を含まないものに限る。生成器の不備なしシナリオはこの条件を満たす設計と読める（実行による確認はしていない）。
- **分類の根拠**：
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):13-23（RED-2）、25-35（RED-3）、61-71（RED-6）、109-119（RED-10）、121-131（RED-11）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):150（検証者の追記 1、2：非有限の入力での食い違い、追加の例外 3 か所）
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):13-23（NUM-2）、37-47（NUM-4）、73-83（NUM-7）、138（検証者の追記 2）
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py):69-76（check_period は電力係数の表の長さしか見ない）、152-164（profile_values は検査なし）、184-203（grid_values）
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py):450-467（_annual は年次量を検査なしで掛ける）
  - [`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py):29-75（SYS-01 が見る項目の固定の一覧）、526-533（A5-01 は construction_value を検査しない）
- **分類した観点**：R2（基準計算・架空データ・比較・試験）

<a id="ck-r2-08"></a>

## CK-R2-08　規約の一覧（06_OPEN_ISSUES の B-1〜B-21 と base.py 冒頭の規約文）

- **区分**：2　暫定・未検証成果
- **内容**：基準計算が、概念式の決めていない点をどう定めたかの一覧。06_OPEN_ISSUES/README.md の B に 21 項目（端数年の按分、T ちょうどを数えない、更新の年は修繕を除く、冷媒の交換は年末、B1-04 は B1 段階、建替で更新周期を初期化しない、係数は時点によらず固定、未数量分は r/(1−r)、B2 と B6 の振り分け、設備の初期の搬入・据付は不計上、記述子を正とする、など）と、一部に影響の大きさの試算。同じ規約の英文が refcalc/base.py の冒頭にある。
- **所在**：
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md)
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py)
- **確かめ方**：手書きの文書。第2回：B-1〜B-21 をコードと照合し、B-17（RED-1）、B-18（RED-2・RED-3）、B-11（RED-8）を除いて一致。付記の数値は再現：B-7（更新 31 → 19 回、B4 −40.6％、ホールライフ −1.90％）、B-10（11.52％、標準ベンチマーク S で SUM-02 の 7.00％）、B-11（A4 の 0.118％、A5 の 5.014％）、B-12（ガスの範囲で合計は変わらない）。一覧に無い規約がコードにあることも見つかった。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：架空データ、独立概念モデル。影響の大きさは標準ベンチマーク S や境界条件の 1 例についての値で、一般の大きさではない。
- **関係する第2回の指摘**：RED-1、RED-2、RED-3、RED-7、RED-8、RED-10、RED-11、NUM-1、NUM-10
- **第2回の指摘の影響**：第2回の指摘は一覧に反映されていない。成り立たない項目：B-17（印が付かない境界がある）、B-18（年次量などに届かない）、B-15 の括弧書き（ナイフエッジ）。不足している項目：B-11 に資材の初期の据付が無い。一覧に無い規約：無効な周期は事象なし（RED-3）、未数量分 A13-04 を B3・B4 には入れず B5 には入れる（RED-7）、資材の据付係数は更新時だけ使う（RED-8）、明示の一覧の重複した年はその回数だけ数える・比率 0 で係数なしの経路も不完全にする（RED-11）。D-4 は許容差だけを述べ、桁落ちの限界を述べていない（NUM-10）。
- **今の時点で言ってよいこと**：21 項目のうち B-11、B-17、B-18 を除く 18 項目は、コードの動作の記述として一致する（第2回の照合）。うち B-15 は判定式としては一致するが、括弧書きの目的（丸めで端をまたがない）は NUM-1 で成り立たない。B-21 は書かれたとおりだが、評価期間以外の入力でも例外が出る（RED-10）。B-7、B-10、B-11、B-12 に付いた影響の数値は再現された。一覧は、基準計算の規約のすべてではない。
- **使ってはいけない記述**：
  - B-17 の「合計に『不完全』の印を付ける」
  - B-18 が「該当する全単位」に及ぶという記述
  - B-15 の括弧書き（浮動小数点の誤差で端をまたがないようにする許容幅）
  - B-11 が初期に計上しない据付のすべてだという読み方（資材の分 31617.67 kgCO2e、標準ベンチマーク S で報告値の A5 の 41.1％ に当たる分が載っていない）
  - B-21 を「評価期間以外の入力では例外は出ない」と読むこと（RED-10、NUM-4）
  - B の 21 項目が、結果を変える選択のすべてだという読み方
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：新研究で「元の式」を読むときの前提の一覧として使う。規約を変えれば基準の値が変わる点（特に B-2、B-3、B-4、B-7、B-8、B-10、B-11、B-16）を、変換で表す対象の式の一部として扱う。
  - 条件・注意：第2回で見つかった一覧に無い規約（RED-3、RED-7、RED-8、RED-11）を補って読む。B-17・B-18・B-15 は書かれたとおりには成り立たない。規約は本研究の設計であり、他のツールの仕様ではない。
- **分類の根拠**：
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md):20-51
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py):1-54
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):146（CHECKS PERFORMED 7：B-1〜B-21 の照合、再現した数値、一覧に無い規約）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):73-95（RED-7、RED-8 と数値）
- **分類した観点**：R2（基準計算・架空データ・比較・試験）

<a id="ck-r2-09"></a>

## CK-R2-09　定義文とコードの食い違い、定義文に無い動作、数値上の限界（基準計算の側）

- **区分**：4　不具合・未解決事項
- **内容**：基準計算の定義文（説明文）とコードの間、または定義の内部に残っている食い違いの一覧。X-04 は定義文で「一致することを確かめる」と言うが検査結果を返さない。B4-02・B3 の「製造排出」に未数量分 A13-04 が入るかが文から決まらない。X-02 の by_stage_all、X-05 の by_stage_co2 は定義文に無い。X-17 は要約数量 0 の区分を落とす。B3-01 は e0 = 0 の行の排出の行を捨てる。係数 ID が擬似 ID「GRID」「REFRIGERANT」と衝突すると基準計算の内部で矛盾する。施設管理の比率 1.0 で燃料がごく小さいと B6-03 − B2-01 で桁が落ちる。
- **所在**：
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py)
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md)
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md)
- **確かめ方**：第2回の検査担当と検証者が再現（架空データ）。RED-4：係数 1 つの CO2 量を 3 倍にすると X-04 は 7240695.00、14 段階の和は 6998584.83（+3.46％）で、QA-01・QA-03 は合格のまま。RED-7：標準ベンチマーク S で A13-04 は 167094.80（A1-A3 の 3.95％）。B4 はコード 6490922.78、上乗せ込みの読み方で 6526129.00（+0.542％）。B3 は 3766020.36 と 3913846.95（+3.93％）。RED-8：同 S で、据付係数を持つ資材 92 行の初期の据付 31617.67 kgCO2e（報告値の A5 76918 の 41.1％、SUM-03 の 0.096％）は計上されない。RED-12(5)：同 S で concrete_m3 を 0 にすると X-17 が 2895945.56 → 1194519.62。NUM-3：値 0 でガス別量が 0 でない係数で、X-04 が基準計算 8893233.37821491、統合モデル 8938913.46839103（+5.136e-03）。NUM-5：資材の係数を ID「GRID」にすると SUM-03 が基準計算 8965567.801008811、統合モデル 8895116.777675131。基準計算は X-04 でその行を擬似行として扱い、QA-01 が不合格になる。NUM-10(a)：比率 1.0、燃料を 1e-7 倍で、X-02 の B6 が基準計算 0.14876614138484、燃料だけの和 0.14876614887071526。基準計算の QA-01 が有効な入力で不合格。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：架空データ、独立概念モデル。RED-7・RED-8・RED-9 の大きさは標準ベンチマーク S だけの値。RED-9 は文言だけの問題で、研究の数値は変わらない（判定 PARTLY_CONFIRMED）。NUM-3 と NUM-5 は、どちらの計算が正しいかを検査担当は判断していない。
- **関係する第2回の指摘**：RED-4、RED-7、RED-8、RED-9、RED-11、RED-12、NUM-3、NUM-5、NUM-8、NUM-10
- **第2回の指摘の影響**：RED-4、RED-7、RED-8、RED-12、NUM-3、NUM-5、NUM-8、NUM-10 は CONFIRMED、RED-9 と RED-11 は PARTLY_CONFIRMED。その他の細目：QA-01 (a) は相対 1e-9 に絶対値の下限 1.0 を併用し、(b)(c) は作りの上で不合格になり得ない。SUM-05 の「評価年数 0 以下」の枝は到達しない。X-13 は無効な行を件数なしで None にする。SYS-02 は EPD の係数を見ない。SYS-02 は単位名が文字列「None」のとき欠損として報告する（NUM-8）。B4-02 の文は設備の搬入・据付と係数の段階（A4・A5）を、B1-02 の文は ×GWP を書いていない。
- **今の時点で言ってよいこと**：コードの値は一意に決まる。食い違いは 2 種類ある。(1) 定義文の読み方で値が変わるもの（RED-7、RED-8、RED-9）。コードの読みは depends_on で確定し、どの架空シナリオにも同じ読みが当てはまる。(2) 特定の入力でだけ現れるもの（RED-4、RED-12(5)、NUM-3、NUM-5、NUM-10(a)）。係数のガス別量と値が食い違う入力、要約数量 0、擬似 ID と同じ係数 ID、桁落ちする大きさの組合せのとき。不備のない架空シナリオでは、X-04 の値と 14 段階の和は相対 3e-16 で一致する（RED-4 の検証者の確認、シード 11 の 1 例）。
- **使ってはいけない記述**：
  - X-04 の定義文「ガス別量×GWP の合計＋買電＋冷媒 が段階合計の総和に一致することを確かめる」
  - X-17 の定義文「定義上、6 区分の製造排出を区分別に集計し直したものに等しい」（要約数量 0 の区分では成り立たない）
  - QA-01 の定義文「相対 1e-9 以内」（実際は 1e-9×max(|値|, 1.0)）
  - B4-02 の「製造（A1-A3 の行結果）」を、未数量分 A13-04 を含むと読むこと（コードは含めない。B5-01 は含める）
  - X-02 の定義文「対象外の段階は結果に含めない」（by_stage_all と X-05 の by_stage_co2 は 14 段階すべてを返す）
- **新研究での再利用**：候補にしない
  - 理由・注意：ルート B で定義文から式を組み直すときは、depends_on とコードで読みを確定する（B3・B4 の製造排出は A13-01 + A13-03、B5 の基準は A13-04 を含む）。by_stage と by_stage_all の B6 は B2 が対象外のとき B2-01 の分だけ違う。係数 ID に「GRID」「REFRIGERANT」を使わない。
- **分類の根拠**：
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):37-47（RED-4）、73-83（RED-7）、85-95（RED-8）、97-107（RED-9）、121-131（RED-11）、133-143（RED-12）
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):25-35（NUM-3）、49-59（NUM-5）、85-95（NUM-8）、109-119（NUM-10）
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py):322-352（X-04 は検査結果を返さない）、523-540（QA-01 の 531 行）、253-291（by_stage_all）
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py):204, 225（r == 0.0 or e0 == 0.0 で行を捨てる）、70（B4_DEPS に A13-04 が無い）、367-368（B5-01 の depends_on に A13-04 がある）
  - [`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py):603-623（X-17 の 619 行）、152（target == "None"）
- **分類した観点**：R2（基準計算・架空データ・比較・試験）

<a id="ck-r2-10"></a>

## CK-R2-10　基準計算について検証できていないこと（06_OPEN_ISSUES の D）

- **区分**：4　不具合・未解決事項
- **内容**：基準計算の精度と正しさについて、研究が自分で未検証と書いた 7 点。実建物での実用精度は対象外。他のツールの結果とは比較していない。基準計算と統合モデルはどちらも主担当（自動の AI エージェント）が書き、人による確認と手計算との全面的な照合はしていない。許容差は相対 1e-9 で、表示上の丸めは扱っていない。測定は資材 2 万行まで。評価単位ごとの代理モデルは作っていない。「候補なし」は測定をしていない判断。
- **所在**：
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md)
- **確かめ方**：文書の記述。第2回の検査で内容が否定された項目は無いが、D-3 の後半（改めた後の版に対する独立検査は行っていない）は、第2回の検査が行われた時点で古くなった。
- **確かめた者**：なし
- **言える範囲**：独立概念モデルと架空データについての限界の記述。
- **関係する第2回の指摘**：NUM-10
- **第2回の指摘の影響**：NUM-10（CONFIRMED）：D-4 は許容差だけを述べ、桁落ち・桁あふれする入力では 1e-9 を超えるという限界を述べていない。第2回の検査の結果は、この文書にも INDEPENDENT_REVIEW.md にも記録されていない（STOP_STATUS.md 3 節）。
- **今の時点で言ってよいこと**：基準計算は、現実の排出量、原版ブック、他のツールのいずれとも照合されていない。照合の相手は、同じ主担当が書いた統合モデルと、2 回の独立検査（自動の AI エージェント）による定義文からの書き直しだけである。人による確認は無い。
- **使ってはいけない記述**：
  - D-3 の「改めた後の版に対する独立検査は、まだ行っていない」（第2回は行われた。ただしその指摘への対応は未完了で未検証）
  - D-4 を、すべての入力で相対 1e-9 の一致が成り立つという意味に取ること
- **新研究での再利用**：候補にしない
  - 理由・注意：新研究の誤差は「この基準計算に対する誤差」であり、実建物の精度ではないと書く。資材 2 万行を超える規模は未測定。
- **分類の根拠**：
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md):71-79（D の 1〜7）
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):109-119（NUM-10：D-4 は限界を述べていない）
  - [`STOP_STATUS.md`](../STOP_STATUS.md):50-62（第2回の指摘は記録・報告書に未反映）
- **分類した観点**：R2（基準計算・架空データ・比較・試験）

<a id="ck-r7-17"></a>

## CK-R7-17　基準計算（refcalc）のうち、定義文からの独立した書き直しと一致した 53 単位

- **区分**：1　検証済み成果
- **根拠の強さについての注記（索引の作成者）**：書き直しとの一致は第2回の検査担当 1 者の報告で、反証検査担当はこの一致をやり直していない。
- **内容**：評価単位ごとに 1 関数で、定義文どおりに行ごと・年ごと・事象ごとに計算する逐次の実装（規約と補助関数 base.py、登録と依存順の実行 registry.py、単位の 3 モジュール）。新研究の指示で「変更しない」とされている基準値の出どころで、このうち 53 単位は第2回の検査が定義文だけから書き直して比べた。
- **所在**：
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py)
  - [`09_APPROX_STUDY/research_code/refcalc/registry.py`](../../../09_APPROX_STUDY/research_code/refcalc/registry.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py)
  - [`09_APPROX_STUDY/research_code/tests/test_refcalc.py`](../../../09_APPROX_STUDY/research_code/tests/test_refcalc.py)
- **確かめ方**：コミット済みの確認：tests/test_refcalc.py 8 件（手計算との照合 test_hand_calculation、B2 と B6 の間に漏れがないこと、小数の評価期間の端、欠陥の検出など。第2回の報告書検査が旧研究のテスト 28 件の合格を報告）と、681 シナリオでの統合モデルとの突き合わせ。第2回の再導出：定義文と base.py の規約の説明だけから 53 単位を書き直し、119 シナリオ（母集団 24、境界条件 32、dirty 14、入力を壊す操作 36、小数の境界 5、段階の部分集合 8）で、すべての数値と件数が相対 1e-9 以内で一致。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：架空データだけ。独立概念モデル（70 評価単位）の定義についての記述で、原版ブックの式との対応は未確認。確認の範囲は第2回の 119 シナリオ（小さい規模）。43ba5d7 の版。規模 M・L と 99.9 年を超える期間は第2回の再導出では実行していない。再導出は base.py の規約の説明を与件として使っており、規約そのものを別の出典と照合したものではない。
- **関係する第2回の指摘**：RED-1、RED-2、RED-3、RED-7、RED-9、RED-10、RED-12、NUM-1、NUM-3
- **第2回の指摘の影響**：不正な入力、境界の部分集合、検査の網羅についての一般的な記述は成り立たない（CK-R7-19）。周期 1.000000001 では基準計算の年の割当てが、書かれた規則を厳密な算術で評価した結果と食い違う（CK-R7-20）。規約一覧に無い規約がある（CK-R7-29）。
- **今の時点で言ってよいこと**：第2回の検査担当が定義文と規約の説明だけから書き直した実装と、基準計算の 53 単位（A13-01、A13-02、A13-03、A13-04、A13-05、A4-01、A4-02、A5-01、A5-02、A5-03、A5-04、B1-01、B1-02、B1-03、B1-04、B2-01、B3-01、B3-02、B4-01、B4-02、B4-03、B5-01、B6-01、B6-02、B6-03、B6-04、B7-01、B7-02、B7-03、B7-04、C-05、C1-01、C2-01、C3-01、C4-01、QA-02、SUM-01、SUM-02、SUM-03、SUM-04、SUM-05、SUM-06、SUM-07、X-01、X-02、X-06、X-07、X-10、X-12、X-13、X-14、X-15、X-16）の数値・件数は、119 架空シナリオ（境界条件、欠陥入り、入力を壊す操作 36 種、小数の境界、段階の部分集合を含む）で相対 1e-9 以内で一致した。差は 4 点だけ：X-15 が未解決の行に付ける印、B2-01 の computed（入力を壊した 4 件）、SUM-07 が未定義のときの出力、C-05 の n_mass_unchecked（負の廃棄質量）。これは「コードが定義文どおりに計算している」ことの確認で、定義そのものの穴（CK-R7-19）や、この 119 件に無い入力での挙動を覆うものではない。比べたのは各単位の値・内訳・件数の欄で、X-02 と SUM-01〜03 の完全性の印（complete、incomplete_units）は比べていない。
- **使ってはいけない記述**：
  - 「欠損・範囲外の入力は必ず除外して数えられ、合計に不完全の印が付く」（RED-1・RED-2・RED-3）
  - 「時間の判定は許容幅により 2 進の丸めに依存しない」（base.py の説明。NUM-1・REC-1 の検証者の追加指摘）
  - 「評価期間が有限の正の数でないときだけ、計算全体がエラーになる」（B-21。RED-10・REP-17）
  - 「基準計算の正しさ」を、現実の排出量や他のツールの結果との一致として読むこと（06_OPEN_ISSUES D-1・D-2：対象外）
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：新しい定式化の誤差を測るときの基準値を出す計算として使う。ルート B では、この関数群の定義文とコードが「元の式」に当たる。
  - 条件・注意：基準計算は公開中の版（43ba5d7 と同じ）に固定する。中断した修正の版は使わない（HANDOVER.md 4.2）。版は 2 つある：コミット済みの版（43ba5d7 と同じ）と、中断した修正の版（65ff124。定義が変わる、未検証）がある。指示は基準計算の変更を禁じているので、穴のある入力範囲（CK-R7-19、CK-R7-20）は、基準計算を直すのではなく測定の母集団から外すか別扱いにする必要がある。結果の形（value／by_item／by_year／by_stage／ok と violations、「_」で始まるキーは下流用で比較の対象外）は registry.py と base.py の冒頭にある。
- **分類の根拠**：
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):146（CHECKS PERFORMED 1：53 単位、119 シナリオ、数値と件数が相対 1e-9 以内。差は 4 点）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):148（COULD NOT CHECK：再導出していない単位、規模、期間、規約の出典）
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py):1-54（規約）、69-76（check_period）；[`09_APPROX_STUDY/research_code/refcalc/registry.py`](../../../09_APPROX_STUDY/research_code/refcalc/registry.py):1-14,90-104
  - [`09_APPROX_STUDY/research_code/tests/test_refcalc.py`](../../../09_APPROX_STUDY/research_code/tests/test_refcalc.py)（test_hand_calculation ほか 8 件。R7 は名前だけ確認）；[`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):128（「The study's 28 unit tests pass」）
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md):73-75（D-1〜D-3）
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））
- **停止後の点検による訂正**：点検の指摘 V1-12、再点検 C1-02 により、上の記述の一部を改めた。分類担当の元の記述は `materials/classification/R7.json`、訂正の内容は `materials/classification/overrides.json` にある。

<a id="ck-r7-18"></a>

## CK-R7-18　基準計算のうち、独立した書き直しがない 14 単位と、間接的な確認だけの 3 単位

- **区分**：2　暫定・未検証成果
- **内容**：第2回の再導出検査が定義文から書き直さなかった 14 単位（QA-01、QA-03、QA-04、STO-01、STO-02、SYS-01、SYS-02、SYS-03、SYS-04、X-03、X-08、X-09、X-11、X-17）と、間接的な方法でだけ確かめた 3 単位（X-04、X-05、SUM-08）。
- **所在**：
  - [`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py)
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
- **確かめ方**：14 単位は、第2回の検査担当がコードを読んだあとで定義文と読み比べ、狙い撃ちの入力で確かめただけ（本人が「独立の導出ではない」と記している）。X-05・X-04（ガス別）・SUM-08 は、書き直した実装の係数値をガス別量に置き換える、基準案を計算し直す、という間接的な方法で 50 シナリオ（うち基準案つき 3）差なし。統合モデルとの 681 シナリオの一致はこれらの単位にも及ぶが、基準計算と統合モデルは同じ主担当が書いた。
- **確かめた者**：作成者のみ（第2回は読み比べと間接的な確認）
- **言える範囲**：架空データだけ。独立概念モデル（70 評価単位）の定義についての記述で、原版ブックの式との対応は未確認。
- **関係する第2回の指摘**：RED-4、RED-5、RED-6、RED-11、RED-12、NUM-8
- **第2回の指摘の影響**：この 17 単位には検査・ゲートが多く、定義文とコードの食い違いの指摘が集まっている：X-04 は照合しない（RED-4）、SUM-08 は完全性を見ない（RED-5）、SYS-01 は一部の入力しか見ない（RED-6）、SYS-02・SYS-03 と計算の食い違い（RED-11）、QA-01 の下限と失敗し得ない検査、X-17 の要約数量 0（RED-12）。
- **今の時点で言ってよいこと**：これらの単位も、台帳の定義文はコードの説明文と同じ文字列で、681 シナリオで統合モデルと相対 1e-9 以内で一致している。定義文からの独立した書き直しによる値の確認は無い。
- **使ってはいけない記述**：
  - これら 17 単位の値を「独立に再導出して確認済み」として扱うこと
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：基準値として使う場合は、この 17 単位が独立の書き直しを経ていないことを前提にする。17 単位はどれも段階合計の外にある（X-11・X-17・STO-01・STO-02 は推定・参考値、X-03・X-08・X-09 は集計表、X-04・X-05 はガス別の内訳、SUM-08 は比較、SYS・QA は検査）。
  - 条件・注意：段階合計（SUM-03 の上流 37 単位）に入る単位は、この 17 単位に 1 つも含まれない（R7 の集計）。したがって合計の基準値への影響は無いが、ガス別内訳、CO2 のみの合計、基準案との差、検査の結果を新研究で使うなら別途の確認が要る。
- **分類の根拠**：
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):146（CHECKS PERFORMED 2：X-05・X-04・SUM-08 の間接的な再導出、50 シナリオ）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):148（COULD NOT CHECK：14 単位は独立に再実装していない）
  - R7 の集計（units.json）：この 17 単位と SUM-03 の上流 37 単位の共通部分は 0 単位
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md):75（D-3：基準計算と統合モデルはどちらも主担当が書いた）
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））

<a id="ck-r7-19"></a>

## CK-R7-19　基準計算の定義の穴（不正な値・部分的な境界・検査との食い違い）

- **区分**：4　不具合・未解決事項
- **内容**：第2回の検査で確認された、基準計算の定義とコードの欠陥。INDEX.md の 6.1 の条件を満たす入力（有限で範囲内、周期が有限の正の数、14 段階すべてを対象、など）にする場合には現れないが、それ以外では、合計が黙って変わる・不完全の印が付かない・全体が例外で止まる、のいずれかが起きる。
- **所在**：
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py)
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md)
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md)
- **確かめ方**：第2回の再導出検査と数値の反例探しが、架空シナリオに欠陥を入れて基準計算を実行し、反証担当の検証者が自分のスクリプトで再現（RED-1・2・4・5・6・10、NUM-2〜7 は CONFIRMED、RED-3・RED-11 は PARTLY_CONFIRMED）。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：架空データだけ。独立概念モデル（70 評価単位）の定義についての記述で、原版ブックの式との対応は未確認。例の数値は小さい架空シナリオ（資材 12 行など）でのもの。
- **関係する第2回の指摘**：RED-1、RED-2、RED-3、RED-4、RED-5、RED-6、RED-10、RED-11、NUM-2、NUM-3、NUM-4、NUM-5、NUM-6、NUM-7
- **第2回の指摘の影響**：これらは未修正のままコミット済みの版に残っている。中断した修正（65ff124）は「修正した」と自己申告しているが、独立の検査を受けていない。
- **今の時点で言ってよいこと**：次の入力範囲では、コミット済みの基準計算の結果を基準値として使えない：(1) B3 または B5 を含み上流の段階を外した境界で、上流に除外された行がある（complete が真のまま合計が下がる。例 −55.6％）。(2) 年次量、電力係数、建設時係数、係数値、換算倍率が負・NaN・無限大（そのまま合計に入り、complete は真、検査もすべて通る）。(3) 周期・耐用年数・建替周期が負・0・NaN・無限大（事象なし、印なし。例 −16.1％）。(4) 経路の比率・係数値・要約数量・用途別面積・更新年一覧の要素が None、年次表が評価期間より短い（TypeError・IndexError で全体が止まる）。(5) 係数 ID が「GRID」「REFRIGERANT」。(6) 係数のガス別量が係数値と合わない（どの検査にも掛からない）。
- **使ってはいけない記述**：
  - 06_OPEN_ISSUES B-17「使えない行・経路・項目は合計に入れず、件数を報告し、合計に『不完全』の印を付ける」を全ての境界について（RED-1）
  - 06_OPEN_ISSUES B-18「負の数量・質量・距離、範囲外の率は、その行を計算から除いて数える」を年次量について（RED-2）
  - README・04_VERIFICATION の「不備のある入力でも、どちらの計算も同じ値を返し、同じ不備を報告する」という一般的な文（NUM-2。検証した 36 種の操作については成り立つ）
  - INDEPENDENT_REVIEW.md 2.2 の「除外して数える規則に統一」
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：新しい定式化の定義域を決めるときの「避ける入力範囲」の一覧として使う。誤差測定の母集団からこれらの入力を外す、または「基準値なし」として扱う根拠になる。
  - 条件・注意：指示は基準計算の変更を禁じているので、穴を埋めた版を基準にしたい場合は、新研究の側でその扱いを明示して決める必要がある（この確認作業は修正を行わない）。基準計算と統合モデルは、有限の欠陥入力では互いに一致する（同じ穴を共有する）ので、両者の一致は穴が無いことの証拠にならない。（再点検による補足：穴を埋めた版（65ff124）は基準にしない。穴のある入力は、比較から外すか、既知の例外として扱う。INDEX.md 6.1、HANDOVER.md 4.2。）
- **分類の根拠**：
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):1-11（RED-1：対象段階 B3 だけで SUM-03 98378.05→43676.16、complete 真）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):13-23（RED-2）、25-35（RED-3：SUM-03 7893398.71→6619741.07、complete 真）、37-71（RED-4・RED-5・RED-6）、109-131（RED-10・RED-11）
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):13-83（NUM-2〜NUM-7）、138（検証者の追加 2：年次量・係数値・電力係数に範囲の検査が無い）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):150（検証者の追加 1〜3）
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py):240-250（STAGE_UNITS、_incomplete）；[`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py):152-164（profile_values：検査なし）
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））
- **停止後の点検による訂正**：点検の指摘 再点検 C1-01、C1-02 により、上の記述の一部を改めた。分類担当の元の記述は `materials/classification/R7.json`、訂正の内容は `materials/classification/overrides.json` にある。

<a id="ck-r7-20"></a>

## CK-R7-20　時間規則の端（周期 1.000000001）と、修繕の除外年の閉形式の不一致

- **区分**：4　不具合・未解決事項
- **内容**：事象の属する年を ceil(τ·(1−1e-9)) で決める規約は、周期が倍精度の 1.000000001（1 値）のとき丸めに依存する。基準計算のループは複数の事象を同じ年に置き、修繕の除外年の重みの閉形式 skip_weight_periodic は「周期が 1 以上なら事象ごとに年が違う」と仮定するので、B3-01 と、B3 を含む合計が食い違う。
- **所在**：
  - [`09_APPROX_STUDY/research_code/fastcalc/closed_forms.py`](../../../09_APPROX_STUDY/research_code/fastcalc/closed_forms.py)
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py)
  - [`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md)
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md)
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md)
- **確かめ方**：第2回の 2 つの検査（数値の反例探し、記録の監査）が別々に見つけ、それぞれの検証者が自分のスクリプトで再現（どちらも CONFIRMED、重大度 HIGH）。周辺の倍精度値（±4000〜6000 ulp）、70 万〜150 万組の (T, 周期)、40 万個の乱数の周期を走査して、失敗するのはこの 1 値だけと報告（ほかに無いことの証明ではない）。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：架空データだけ。独立概念モデル（70 評価単位）の定義についての記述で、原版ブックの式との対応は未確認。欠陥のない入力で起きる。
- **関係する第2回の指摘**：NUM-1、REC-1
- **第2回の指摘の影響**：「統合モデルはすべての入力で基準計算と同じ結果（相対 1e-9）」と、closed_forms.py の「All of them are exact」は、この入力で成り立たない。検証者の追加指摘：書かれた規則を有理数で厳密に評価すると 59 事象は 59 の異なる年に入り、閉形式の値のほうがそれに合う。基準計算のループの値（48 の異なる年）が丸めの産物である。
- **今の時点で言ってよいこと**：周期 1.000000001 を資材の更新周期または設備の耐用年数に持つ行があると、基準計算と統合モデルは B3-01 で食い違う（全行がその周期の例：229291.25 対 19107.60、相対 −0.917。1 行だけなら 2e-6〜2e-3）。T=60 では事象 59 個に対し、基準計算の年の集合は 48 個。同じ年の判定は B4-02・B5-01・B1・X-07 の年次の置き場所にも使われ、そこでは両者が同じ産物を共有する。
- **使ってはいけない記述**：
  - closed_forms.py 冒頭の「All of them are exact: they return the same number as the loop」
  - DERIVATIONS.md D3 の「c≧1 なら事象ごとに年が違い」を、基準計算の浮動小数点の年の割当てについて
  - base.py の「The tolerance makes the rule independent of binary rounding」
  - 記録 EX-B3-01-M1 の「VERIFIED_ANALYTIC_AND_SYNTHETIC」と 04_VERIFICATION/README の「不一致なし」を、すべての入力についての主張として
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：時間を離散化する規約（許容幅つきの切り上げ）が、厳密な算術と浮動小数点で食い違う点の実例として使う。新しい定式化の誤差を測るとき、基準値そのものが丸めに依存する入力として別扱いにする。
  - 条件・注意：どちらを正とするかは決まっていない（基準計算を閉形式に合わせるか、閉形式を基準計算に合わせるか）。中断した修正（65ff124）は「時間の判定を整数の厳密な算術に変えた」と自己申告しているが、未検証で、基準計算の定義を変える。旧研究の試験（tests/test_closed_forms.py）は周期を約数から相対 1e-15、1e-12、1e-10、1e-8、1e-6 だけずらし、1e-9 を引かない。
- **分類の根拠**：
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):1-11（NUM-1：T=7 で 6 事象・5 年、T=30 で 29・26、T=60 で 59・48。B3-01 229291.25152413402 対 19107.60429367785）
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):1-11（REC-1）、114（検証者の追加 1：厳密な有理数の算術では 59 の異なる年）
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):138（検証者の追加 1：B-15 の許容幅そのものの端）
  - [`09_APPROX_STUDY/research_code/fastcalc/closed_forms.py`](../../../09_APPROX_STUDY/research_code/fastcalc/closed_forms.py):1-11,58-71；[`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py):12-17,125-126；[`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md):67
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））

<a id="ck-r7-28"></a>

## CK-R7-28　本研究が決めた規約 B-1〜B-21 のうち、第2回でコードとの符合が確認されたもの

- **区分**：1　検証済み成果
- **根拠の強さについての注記（索引の作成者）**：コードとの照合は第2回の検査担当 1 者。
- **内容**：概念式が決めていない点を旧研究が定めた 21 件の規約（評価期間は実数で最終年を按分、T ちょうどの事象は数えない、事象は属する年に置く、更新年は修繕を計上しない、冷媒の交換は年末に反映、など）。基準計算と統合モデルの両方がこの規約を前提にしている。
- **所在**：
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md)
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py)
- **確かめ方**：規約の一覧と影響の試算は 06_OPEN_ISSUES の B にコミット済み（影響の大きさは第1回の独立検査による試算と明記）。第2回の再導出の検査担当が、B-1〜B-21 は B-11・B-17・B-18 を除きコードと合うと 1 文で報告した（1 件ごとの照合の記録は無い）。影響の数字（B-7、B-10、B-11、B-12）は第2回の 2 つの検査が再計算して一致。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：架空データだけ。独立概念モデル（70 評価単位）の定義についての記述で、原版ブックの式との対応は未確認。「符合」は規約の文とコードの挙動が合うという意味で、規約の選び方の妥当性ではない。影響の数字は架空の境界条件の例と標準ベンチマーク S でのもの。
- **関係する第2回の指摘**：RED-1、RED-2、RED-3、RED-8、REP-17、NUM-1
- **第2回の指摘の影響**：B-11（設備の初期の搬入・据付を計上しない）は設備については合うが、資材の行の据付係数にも同じ扱いがあり、一覧に無い（RED-8）。B-17（除外して数え、不完全の印）は部分的な境界で破れる（RED-1）。B-18（負の値・範囲外は除外して数える）は年次量で破れる（RED-2）。B-15（許容幅 1e-9）は実装どおりだが、周期 1.000000001 で丸めに依存する（NUM-1 の検証者の追加指摘）。B-16・B-21 は、年次表が ceil(T) より短いと全体がエラーになる規則を書いていない（REP-17）。
- **今の時点で言ってよいこと**：第2回の検査担当 1 者は、B-11・B-17・B-18 の 3 件を除く 18 件がコードと合うと報告した（1 文の報告で、1 件ごとの照合の記録は無い）。分類担当は、ほかの指摘との関係から、さらに B-15・B-16・B-21 に限定を付けた。残る 15 件：B-1（T は実数、最終年を按分）、B-2（n×周期<T だけ数える）、B-3（事象は属する年に置く）、B-4（更新が属する年は修繕なし）、B-5（冷媒の交換は年末に反映）、B-6（B1-04 は B1 段階）、B-7（建替で更新周期を初期化しない）、B-8（更新・建替も初期と同じ係数）、B-9（未数量分は r/(1−r) の上乗せ）、B-10（B2 は買電排出の定率、B2 が対象のときだけ B6 から引く）、B-12（ガスの範囲はラベル、合計は全ガス）、B-13（経路比率の合計が 1 未満は未配分）、B-14（EPD の適用条件）、B-19（質量収支は据付量と比べる）、B-20（年次量の単位は「単位/year」だけ）。影響の数字：B-7 は境界条件の例（T=60、建替周期 25、範囲比 1.0）で更新 31 回→19 回、B4 −40.6％、合計 −1.9％。B-10 は B2 が標準ベンチマーク S の SUM-02 の 7.0％。B-11 は A4 の 0.12％、A5 の 5.0％。このうち B-2 と B-3 は、B-15 の許容幅（1e-9）つきで実装されており、時間の判定の端では B-15 と同じ限定が付く。
- **使ってはいけない記述**：
  - B-17 を全ての境界について、B-18 を年次量・電力係数・係数値・換算倍率・周期について（CK-R7-19）
  - B-11 を「計上しない初期分は設備だけ」として（資材の初期の据付は標準ベンチマーク S で 31617.67 kgCO2e、A5 の 41.1％ に当たる。RED-8）
  - B-21 を「全体がエラーになるのは評価期間が不正なときだけ」として（RED-10、REP-17）
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：新しい定式化が基準計算と同じ値を出すために守る必要のある規約の一覧。特に、時間の離散化（B-1〜B-5、B-15）と段階への帰属（B-6、B-10、B-12）は式の形を直接決める。
  - 条件・注意：規約を変えれば結果も変わる（06_OPEN_ISSUES の B の冒頭）。B-8（係数は時点によらず固定）は「回数×1 回分」という形の前提で、更新時点の係数を使う場合の扱いは実装も検証もされていない（CK-R7-31）。一覧に無い規約がある（CK-R7-29）。
- **分類の根拠**：
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md):20-51（B-1〜B-21 と影響の大きさ）
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py):1-54（規約の説明）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):146（CHECKS PERFORMED 6・7：時間の規約は一貫して使われている。B-1〜B-21 は RED-1・RED-2／3・RED-8 の例外を除きコードと合う。B-7、B-10、B-11、B-12 の数字を再現）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):128（CHECKS 2：B-7、B-10、B-11 の数字を再現）、113-118（REP-17。第2検証者なし）
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):138（検証者の追加 1：B-15 の端）
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））
- **停止後の点検による訂正**：点検の指摘 V1-07、再点検 V1-07 により、上の記述の一部を改めた。分類担当の元の記述は `materials/classification/R7.json`、訂正の内容は `materials/classification/overrides.json` にある。

<a id="ck-r7-29"></a>

## CK-R7-29　規約一覧に無い規約と、定義文に書かれていない挙動

- **区分**：4　不具合・未解決事項
- **内容**：コードには在るが、06_OPEN_ISSUES の規約一覧（B-1〜B-21）や単位の定義文に書かれていない取り決め。値を変えるものと、出力の形だけのものがある。
- **所在**：
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md)
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py)
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md)
- **確かめ方**：第2回の再導出検査がコードと定義文・規約一覧を読み比べ、標準ベンチマーク S などで大きさを測り、検証者が再現（RED-7・RED-8・RED-12 は CONFIRMED、RED-3・RED-9・RED-11 は PARTLY_CONFIRMED）。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：架空データだけ。独立概念モデル（70 評価単位）の定義についての記述で、原版ブックの式との対応は未確認。大きさの数字は標準ベンチマーク S（架空）だけ。
- **関係する第2回の指摘**：RED-3、RED-7、RED-8、RED-9、RED-11、RED-12、REP-17、NUM-3
- **第2回の指摘の影響**：未記載のまま残っている。中断した修正（65ff124）は定義文を書き足したと自己申告しているが、規約一覧（06_OPEN_ISSUES）への追記はしていない、と同じ報告にある。
- **今の時点で言ってよいこと**：(1) 更新（B4-02）と修繕（B3-01・B3-02）の「製造」は A13-01＋A13-03（設備は X-01）で、未数量分 A13-04 を含まない。建替（B5-01）の基礎は A13-04 を含む（S で、含めると B4 が +0.542％、B3 が +3.93％）。(2) 資材の行の据付係数は更新のときだけ使い、初期には計上しない（S で 31617.67 kgCO2e＝A5 の 41.1％、合計の 0.096％）。(3) 設備の更新 1 回には、数量×搬入係数（対象段階 A4）と数量×据付係数（A5）が加わる（S で B4 の 0.105％）。(4) 無効な周期は事象なしで、印が付かない。(5) 明示の一覧に重複した年は、その回数だけ数える。(6) 比率 0 で係数の無い経路でも、合計は不完全になる。(7) 記述子が整っていても、電力係数の年次表が ceil(T) より短ければ全体がエラー。(8) X-02 は by_stage_all、X-05 は by_stage_co2 として 14 段階すべてを返す。(9) 基準計算の B3-01 は 修繕率 0 または初期排出 0 の行の行データを落とす。
- **使ってはいけない記述**：
  - 06_OPEN_ISSUES の B を「結果を変える規約の全部」として読むこと
  - B4-02 の定義文の式の部分だけから設備の更新 1 回の内容を読むこと（RED-9）
- **新研究での再利用**：候補（ルート B・C）
  - 使い道：元の式から組み直すとき（ルート B）、定義文と規約一覧だけでは基準計算と合わなくなる箇所の一覧として使う。
  - 条件・注意：定義文と規約一覧に加えて、depends_on とコードの条件を読む必要がある。(1) は依存の宣言だけが決めている（B4-02・B3-01 の依存に A13-04 が無く、B5-01 には在る）。
- **分類の根拠**：
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):73-107（RED-7：A13-04 は S で A1-A3 の 3.95％。RED-8：92 行／200 行が据付係数を持つ。RED-9：設備の搬入・据付は B4 の 0.1049％）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):25-35（RED-3）、121-143（RED-11・RED-12）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):113-118（REP-17）；[`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):25-35（NUM-3）
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py):44-67,70,186,204,225,367-368；[`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py):74-75
  - [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json): findings の RED-3／RED-7／RED-8（status PARTLY_FIXED。自己申告）
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））

