# 索引の詳細 T11：中断した修正（65ff124）と未実施の改訂

[INDEX.md](../INDEX.md) の項目ごとの詳細。分類担当（読み取り専用）が書いた内容を、欄ごとに載せる。停止後の点検で改めた項目には「停止後の点検による訂正」と記してある。
旧研究の数値はすべて架空データでの値で、対象は独立概念モデルである。原版の表計算との一致や、実建物での精度を示すものではない。
所在の表記：`09_APPROX_STUDY/…` などは `whole-life-carbon-jcat-study/` からの位置、`materials/…` はこの保存フォルダからの位置。

| 項目 | 区分 | 題 |
|---|---|---|
| [CK-R1-11](#ck-r1-11) | 2 | 中断した修正（65ff124）での台帳の書き換え（reference_semantics 50 単位ほか） |
| [CK-R2-18](#ck-r2-18) | 3 | 第2回の指摘に対する基準計算の定義の修正方針（SPEC_A1.md の設計決定） |
| [CK-R2-19](#ck-r2-19) | 2 | 中断した修正 a1：時間の判定の厳密化（整数演算。事象の「年」を受け渡す） |
| [CK-R2-20](#ck-r2-20) | 2 | 中断した修正 a1：値の妥当性の規則（検査なしの値を除外して数える。評価期間以外で例外を出さない） |
| [CK-R2-21](#ck-r2-21) | 2 | 中断した修正 a1：データの流れに沿った完全性の印、B2-01 の computed、SUM-08 の状態の追加 |
| [CK-R2-22](#ck-r2-22) | 2 | 中断した修正 a1：ガス別内訳の検査、擬似行の番兵、ゲートと定義文の改訂 |
| [CK-R2-23](#ck-r2-23) | 2 | 中断した修正 a1：試験 68 件、壊し方 214 種類、比較の厳格化、一致確認の自己申告 |
| [CK-R2-24](#ck-r2-24) | 4 | 中断した修正 a1 に残る未解決事項と副作用（自己申告の open_problems） |
| [CK-R3-31](#ck-r3-31) | 2 | 中断した修正 a1：時間の判定を厳密な有理数の演算にし、閉形式を作り直す |
| [CK-R3-32](#ck-r3-32) | 2 | 中断した修正 a1：修正後の一致確認と負荷の変化（自己申告の数字） |
| [CK-R3-36](#ck-r3-36) | 2 | 中断した段階 a2 の途中の出力 2 ファイル（未検証） |
| [CK-R4-23](#ck-r4-23) | 2 | b2 の再測定と新しい候補（中断した修正。自己申告のみ） |
| [CK-R4-24](#ck-r4-24) | 3 | b2 の設計（SPEC_B2）と結論文の書き換え案 |
| [CK-R5-30](#ck-r5-30) | 3 | 予定だったが行われなかった改訂（Stage C）：記録・進捗台帳・報告書の生成器 |
| [CK-R5-31](#ck-r5-31) | 3 | 予定だったが行われなかった改訂（Stage C）：手書きの文書と、全体の再生成 |
| [CK-R7-32](#ck-r7-32) | 2 | 中断した修正（65ff124）の基準計算・閉形式：定義が変わった未検証の版 |

<a id="ck-r1-11"></a>

## CK-R1-11　中断した修正（65ff124）での台帳の書き換え（reference_semantics 50 単位ほか）

- **区分**：2　暫定・未検証成果
- **内容**：停止時点の作業ツリー（65ff124）では、段階 a1 の作業担当が台帳 units.json を書き換えていた。変わったのは reference_semantics 50 単位、depends_on 3 単位（X-02、X-04、X-07）、feeds 9 単位、SYS-01 の branches である。0db5c77 で作業ツリーから取り除かれ、HEAD の台帳は 43ba5d7 と同じ内容に戻っている。
- **所在**：
  - git show 65ff124:`09_APPROX_STUDY/01_LEDGER/units.json`（コミット `65ff124` の版）
  - [`materials/interrupted_fix/working_tree_at_stop_65ff124.patch`](../materials/interrupted_fix/working_tree_at_stop_65ff124.patch)
  - [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json)
- **確かめ方**：段階 a1 の作業担当の自己申告だけ（A1_REPORT.json：台帳の文面は基準計算の説明文と同じ、同期の道具の最後の実行は「70 単位、変更 0」、修正の前後で 299 シナリオを比べ、整ったシナリオの基準計算の値は変わらなかった）。独立の検査は未実施。この読み取りでは、HEAD と 65ff124 の 2 つの JSON を比べて、変わった項目の数だけを数えた（コードは実行していない）。
- **確かめた者**：中断した修正の自己申告
- **言える範囲**：65ff124 の作業ツリーだけ。この版のコードに対応する測定・記録・報告は作られていない（公開済みのものは 43ba5d7 のコードに対応）。
- **関係する第2回の指摘**：RED-1、RED-4、RED-6、NUM-1、REC-1
- **第2回の指摘の影響**：基準定義への指摘（RED・NUM）に対応しようとした修正である。自己申告によると、完全性の印を上流の単位まで追うようにし（RED-1）、X-04 に X-02 との比較を加え（RED-4）、SYS-01 で NaN・無限大を NOT_FINITE として報告するようにし（RED-6）、時間の判定の規則を変えた（NUM-1・REC-1 への対応）。どれも検証されていない。
- **今の時点で言ってよいこと**：65ff124 には、a1 が直した基準計算に合わせて書き換えた定義文を持つ台帳がある。変更の数は上のとおり（JSON の比較で数えた）。内容が正しいかどうかは確かめられていない。
- **使ってはいけない記述**：
  - 65ff124 の reference_semantics が検証済みの定義である
  - HEAD の台帳に a1 の修正が入っている（入っていない。HEAD は 43ba5d7 と同じ）
  - A1_REPORT.json の「試験に通った」という記載（自己申告で、停止後に実行して確かめていない）
- **新研究での再利用**：候補にしない
  - 理由・注意：65ff124 の定義を使う場合は基準計算を変えることになり、独立の検査が先に要る。未検証のまま検証済みとして扱わない。
- **分類の根拠**：
  - git show --stat 65ff124（01_LEDGER/units.json 129 行の変更）
  - HEAD と 65ff124 の units.json の比較：reference_semantics 50 単位、depends_on 3、feeds 9、branches 1（JSON の解析）
  - [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json): interface_changes[11], decisions[7], acceptance[5], findings[11], findings[16], findings[17]
  - [`STOP_STATUS.md`](../STOP_STATUS.md):54, 86-92, 97-99
- **分類した観点**：R1（統制文書・台帳・順位）

<a id="ck-r2-18"></a>

## CK-R2-18　第2回の指摘に対する基準計算の定義の修正方針（SPEC_A1.md の設計決定）

- **区分**：3　研究途中の数式・仮説
- **内容**：中断した修正の段階 a1 に渡された指示書。一般原則は「欠損・非有限・範囲外の数値入力は演算に使わない。それを必要とする最小の単位（行、経路、年次系列、区分、単位）を除いて数え、依存する合計をすべて不完全にする。無効な評価期間以外の入力では例外を出さない」。時間の判定は、与えられた倍精度値の上の厳密な有理数演算にする：c = 1 − 1e-9 に最も近い倍精度値、内側 ⇔ τ < T×c、年 = max(1, ceil(τ×c))、n 回目の事象は n×L ちょうど。閉形式は 更新回数 = ceil(T×c / L) − 1。完全性は depends_on の推移閉包から求める。SUM-08 に BASELINE_NOT_FOUND と INCOMPLETE を加える。X-04 は実際の検査を返す。擬似行は番兵オブジェクトで区別する。
- **所在**：
  - [`materials/interrupted_fix/specs/SPEC_A1.md`](../materials/interrupted_fix/specs/SPEC_A1.md)
  - [`materials/interrupted_fix/specs/VERIFY_DEF.md`](../materials/interrupted_fix/specs/VERIFY_DEF.md)
  - [`materials/interrupted_fix/specs/COMMON.md`](../materials/interrupted_fix/specs/COMMON.md)（各段階に共通の指示）
  - [`materials/interrupted_fix/specs/VERIFY_NUM.md`](../materials/interrupted_fix/specs/VERIFY_NUM.md)（修正後の反証検査の手順。未実施）
- **確かめ方**：指示書であり、検査の対象ではない。実装は a1 が申告したが（CK-R2-19〜23）、指示書が予定した独立の検査（VERIFY_DEF.md）は開始されなかった。
- **確かめた者**：なし
- **言える範囲**：独立概念モデルの定義をどう閉じるかの設計。架空データでの検証を前提にした方針で、どれも確定した定義ではない。
- **関係する第2回の指摘**：NUM-1、NUM-2、NUM-3、NUM-4、NUM-5、NUM-6、NUM-7、NUM-8、NUM-9、NUM-10、NUM-11、RED-1、RED-2、RED-3、RED-4、RED-5、RED-6、RED-7、RED-8、RED-9、RED-10、RED-11、RED-12、REC-1、APP-5、REP-16、REP-17
- **第2回の指摘の影響**：指摘 NUM-1〜11、RED-1〜12 と、同じ問題を別の見方から述べた REC-1、APP-5、REP-17 への対応方針（REP-16 は掃引の比較範囲）。方針として「変えない」と決めたもの：NUM-10 の (a)(c)(d)(e)（桁落ち・桁あふれの入力）、RED-11(3)、型の違う入力。
- **今の時点で言ってよいこと**：第2回の指摘に対して、基準計算の定義をこう閉じるという方針が書かれている。採用も検証もされていない。
- **使ってはいけない記述**：
  - 指示書の規則（厳密な時間判定、妥当性の規則、データの流れに沿った完全性）を、コミット版の基準計算の動作と読むこと
  - 指示書の「now provably exact」（閉形式が証明可能に厳密になる）を、証明済み・検証済みと読むこと
- **新研究での再利用**：候補（ルート B・C）
  - 使い道：ルート B・C で時間の規約を式にするときの仮説として読める：回数 N = ceil(T×c / L) − 1、年 = max(1, ceil(n×L×c))、q = L×c ≥ 1 なら事象の年はすべて異なり、q < 1 なら年 1 から最後の事象の年までを埋める。また、固定の基準に与えてはいけない入力の種類を知る一覧として使える。
  - 条件・注意：仮説として扱う。新研究では基準計算を変えないので、この方針を基準計算に適用しない。式は、ナイフエッジの周期ではコミット版の基準計算と違う値を与える（その入力では基準計算のほうが丸めの産物）。それ以外の周期で同じ値になることは未検証。
- **分類の根拠**：
  - [`materials/interrupted_fix/specs/SPEC_A1.md`](../materials/interrupted_fix/specs/SPEC_A1.md):28-37（一般原則）、39-78（時間の規約）、80-127（検査なしで使われていた値）、129-151（完全性、SUM-08）、153-169（ガス別内訳、擬似行）、171-193（ゲートと文言）、195-213（数値と比較）、215-220（変えないもの）、222-235（受け入れ条件）
  - [`materials/interrupted_fix/specs/VERIFY_DEF.md`](../materials/interrupted_fix/specs/VERIFY_DEF.md):1-44（予定されていた独立検査の内容）
  - [`STOP_STATUS.md`](../STOP_STATUS.md):52-60（a1 は完了を報告、独立の検査は未実施。反証検査は未着手）
- **分類した観点**：R2（基準計算・架空データ・比較・試験）
- **停止後の点検による訂正**：点検の指摘 C1-14 により、上の記述の一部を改めた。分類担当の元の記述は `materials/classification/R2.json`、訂正の内容は `materials/classification/overrides.json` にある。

<a id="ck-r2-19"></a>

## CK-R2-19　中断した修正 a1：時間の判定の厳密化（整数演算。事象の「年」を受け渡す）

- **区分**：2　暫定・未検証成果
- **内容**：a1 の自己申告によると、65ff124 の refcalc/base.py と fastcalc/closed_forms.py で、内側の判定、事象の年、n 回目の事象 n×L を、as_integer_ratio() による整数演算で厳密に計算するようにした。periodic_events と explicit_events、B4-01 の events は、事象の時刻ではなく事象の年（整数）を返す。周期 1.000000001・T=60 では基準計算も統合モデルも 59 回を年 2..60 に置く、と申告。境界条件に life_at_year_tolerance を 1 件追加（33 件）。
- **所在**：
  - [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json)
  - [`materials/interrupted_fix/working_tree_at_stop_65ff124.patch`](../materials/interrupted_fix/working_tree_at_stop_65ff124.patch)
  - [`materials/interrupted_fix/a1_scratch/`](../materials/interrupted_fix/a1_scratch)
  - git コミット 65ff124（`09_APPROX_STUDY/research_code/refcalc/base.py`（コミット `65ff124` の版）、fastcalc/closed_forms.py、synth/population.py）
- **確かめ方**：a1 の自己申告だけ。申告の内容：NUM-1 の再現スクリプトで B3-01 が基準計算 19107.604293677847、統合モデル 19107.60429367785。tests/test_closed_forms.py が fractions.Fraction で書いたループと、回数・年・除外の重みを 3,000 以上の端の組と 12,000 の乱数の組で比べて不一致 0。不備なしの 299 シナリオで、修正前後の基準計算の値がビット単位で同じ。独立の検査（VERIFY_DEF の 3）は開始されなかった。今回は実行していない。
- **確かめた者**：中断した修正の自己申告
- **言える範囲**：65ff124 のスナップショットにだけある。作業ツリー（HEAD）の 09_APPROX_STUDY には無い（0db5c77 で取り除いた）。架空データ、独立概念モデル。
- **関係する第2回の指摘**：NUM-1、REC-1、APP-5
- **第2回の指摘の影響**：NUM-1 は FIXED、REC-1 は PARTLY_FIXED（DERIVATIONS.md D3 と記録は未改訂）、APP-5 は DOCUMENTED_ONLY と申告。この版の基準計算は、ナイフエッジの入力でコミット版と違う値を返す（B3-01 が 229291.25 → 19107.60）。
- **今の時点で言ってよいこと**：65ff124 に、時間の判定を整数演算に置き換えたコードがある（パッチに as_integer_ratio の出現 16 か所）。正しく動くかは確認されていない。
- **使ってはいけない記述**：
  - A1_REPORT.json の NUM-1「FIXED」と、試験の不一致 0 の申告を、検証済みと読むこと
  - 「不備なしのシナリオでは修正前後で値が同じ」（299 シナリオ）を、確認済みの事実として使うこと
- **新研究での再利用**：候補にしない
  - 理由・注意：参照するなら「未検証の修正案」と明記する。事象の受け渡しが時刻から年に変わっており、コミット版と結果のキーの意味が違う（B4-01 の events）。
- **分類の根拠**：
  - [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json)：findings[0]（NUM-1）、findings[23]（REC-1）、findings[24]（APP-5）、decisions[0]（events は年）、interface_changes
  - git show --stat 65ff124：refcalc/base.py 332 行、fastcalc/closed_forms.py 211 行、synth/population.py 5 行の変更
  - [`materials/interrupted_fix/working_tree_at_stop_65ff124.patch`](../materials/interrupted_fix/working_tree_at_stop_65ff124.patch)（as_integer_ratio の出現 16 か所。本文は読んでいない）
  - [`STOP_STATUS.md`](../STOP_STATUS.md):54, 97-99（a1 は独立の検査が未実施。中断時点のコードは構文だけ確認し、実行していない）
- **分類した観点**：R2（基準計算・架空データ・比較・試験）

<a id="ck-r2-20"></a>

## CK-R2-20　中断した修正 a1：値の妥当性の規則（検査なしの値を除外して数える。評価期間以外で例外を出さない）

- **区分**：2　暫定・未検証成果
- **内容**：a1 の自己申告によると、65ff124 で、年次量、電力係数（記述子・年次表・工事期間の値）、係数値、ガス別量、換算倍率、GWP を「有限で 0 以上（換算倍率は正）」と検査し、満たさない系列・行・単位を除外して数えるようにした。無効な周期は事象なしにしたうえで n_invalid に数え、建替周期が無効なら B5-01 を computed 偽にする。None を含む表や一覧、短い年次表でも例外を出さず、check_period は評価期間だけを拒否する。conversion_factor は有限の正でない倍率に None を返す。
- **所在**：
  - [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json)
  - [`materials/interrupted_fix/working_tree_at_stop_65ff124.patch`](../materials/interrupted_fix/working_tree_at_stop_65ff124.patch)
  - [`materials/interrupted_fix/a1_scratch/`](../materials/interrupted_fix/a1_scratch)
  - git コミット 65ff124（`09_APPROX_STUDY/research_code/refcalc/`（コミット `65ff124` の版）、synth/model.py）
- **確かめ方**：a1 の自己申告だけ。申告の内容：1 項目ずつ NaN・±無限大・None にした 3461 例で、基準計算・統合モデル（全出力・合計のみ）が同じ結果 3383 例、食い違い 0、評価期間による ValueError 12 例、型の違う値を入れたことによる同じ型の例外 66 例。RED-2・RED-3・RED-10 の再現スクリプトで、件数と complete 偽が出る。今回は実行していない。
- **確かめた者**：中断した修正の自己申告
- **言える範囲**：65ff124 のスナップショットにだけある。架空データ、独立概念モデル。型の違う入力（数値の代わりに文字列など、レコードや一覧の場所に数値）は対象外と申告。
- **関係する第2回の指摘**：RED-2、RED-3、RED-10、NUM-2、NUM-4、NUM-7、REP-17
- **第2回の指摘の影響**：RED-2、RED-10、NUM-2、NUM-4、NUM-7 は FIXED、RED-3 と REP-17 は PARTLY_FIXED と申告（06_OPEN_ISSUES の B など、a1 の担当外の文書は未改訂）。副作用の申告：係数レコードを使うたびに検査するため、基準計算の実行命令数が 1.24 倍（規模 S で 2,528,394 → 3,135,214、M で 24,869,192 → 30,840,145）。
- **今の時点で言ってよいこと**：65ff124 に、妥当性の検査を加えた基準計算のコードがある。規則が漏れなく実装されているか、コミット版と不備なしの入力で同じ値を返すかは確認されていない。
- **使ってはいけない記述**：
  - A1_REPORT.json の「0 disagreements」「no exception except the study period」を検証済みと読むこと
  - この版の実行命令数（1.24 倍）を、43ba5d7 の負荷の測定値と並べて使うこと（負荷の測定はやり直されていない）
- **新研究での再利用**：候補にしない
  - 理由・注意：参照するなら「未検証の修正案」と明記する。結果のキーが増え、意味が変わったものがある（n_invalid、X-06 の computed と source NONE、B6-04 の computed など）。
- **分類の根拠**：
  - [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json)：findings[1]（NUM-2）、[3]（NUM-4）、[6]（NUM-7）、[12]（RED-2）、[13]（RED-3）、[20]（RED-10）、[25]（REP-17）、acceptance[1]（3461 例）、open_problems（命令数 1.24 倍）
  - git show --stat 65ff124：refcalc/units_b.py 175 行、units_c_sum.py 248 行、units_pre_a.py 142 行、synth/model.py 24 行の変更
  - [`materials/interrupted_fix/specs/SPEC_A1.md`](../materials/interrupted_fix/specs/SPEC_A1.md):80-127
- **分類した観点**：R2（基準計算・架空データ・比較・試験）

<a id="ck-r2-21"></a>

## CK-R2-21　中断した修正 a1：データの流れに沿った完全性の印、B2-01 の computed、SUM-08 の状態の追加

- **区分**：2　暫定・未検証成果
- **内容**：a1 の自己申告によると、65ff124 で、完全性を「X-02 が段階を作るのに使う単位と、その depends_on の推移閉包」から求めるようにした（手書きの表 STAGE_UNITS を廃止）。除外の件数は n_skipped、n_routes_skipped、n_partial、n_invalid、n_unresolved と computed 偽。B2-01 は B6-01 が算出されないとき computed 偽。SUM-08 の状態は NO_BASELINE、BASELINE_NOT_FOUND、NOT_COMPARABLE、INCOMPLETE（差と削減率は None）、COMPARED の 5 つで、proposal_complete と baseline_complete を返す。
- **所在**：
  - [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json)
  - [`materials/interrupted_fix/working_tree_at_stop_65ff124.patch`](../materials/interrupted_fix/working_tree_at_stop_65ff124.patch)
  - [`materials/interrupted_fix/a1_scratch/`](../materials/interrupted_fix/a1_scratch)
  - git コミット 65ff124（`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`（コミット `65ff124` の版）、units_b.py）
- **確かめ方**：a1 の自己申告だけ。申告の内容：RED-1 の再現で、対象 ['B3']、['B5']、['B3','B5'] が complete 偽・['A13-01','A13-05','X-01']。「段階の部分集合＋上流の不備」のシナリオ 90 件を一致確認に追加。RED-5 の再現で、基準案の 4 行が算出不能なら状態 INCOMPLETE。今回は実行していない。独立の検査（VERIFY_DEF の 2）は開始されなかった。
- **確かめた者**：中断した修正の自己申告
- **言える範囲**：65ff124 のスナップショットにだけある。架空データ、独立概念モデル。
- **関係する第2回の指摘**：RED-1、RED-5、RED-12、NUM-9
- **第2回の指摘の影響**：RED-1、RED-5、NUM-9 は FIXED、RED-12 は PARTLY_FIXED と申告。a1 自身の注記：閉包の規則は保守的で、たとえば数量の使えない行は、その行が質量と距離で搬入されていても A13-05 経由で A4 を不完全にする。既存の不備入りシナリオの incomplete_units は、以前より多くの単位を挙げる。
- **今の時点で言ってよいこと**：65ff124 に、完全性の印を依存関係の閉包から求めるコードと、SUM-08 の 5 つの状態がある。印が過不足なく付くかは確認されていない。
- **使ってはいけない記述**：
  - A1_REPORT.json の RED-1・RED-5「FIXED」を検証済みと読むこと
  - コミット版の SUM-08 に BASELINE_NOT_FOUND・INCOMPLETE の状態があると読むこと（コミット版は NO_BASELINE、NOT_COMPARABLE、COMPARED の 3 つ）
- **新研究での再利用**：候補にしない
  - 理由・注意：参照するなら「未検証の修正案」と明記する。X-02、X-04、X-07 の depends_on がコミット版と違う（台帳 units.json も 65ff124 では書き換わっている）。
- **分類の根拠**：
  - [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json)：findings[11]（RED-1）、[15]（RED-5）、[22]（RED-12）、[8]（NUM-9）、decisions（閉包は保守的、B6 と B2、SUM-08 の NO_BASELINE の条件）、interface_changes
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py):500-518（コミット版の SUM-08 の状態は 3 つ）
  - [`materials/interrupted_fix/specs/SPEC_A1.md`](../materials/interrupted_fix/specs/SPEC_A1.md):129-151
  - [`materials/interrupted_fix/specs/VERIFY_DEF.md`](../materials/interrupted_fix/specs/VERIFY_DEF.md):20-27（予定されていた検査）
- **分類した観点**：R2（基準計算・架空データ・比較・試験）

<a id="ck-r2-22"></a>

## CK-R2-22　中断した修正 a1：ガス別内訳の検査、擬似行の番兵、ゲートと定義文の改訂

- **区分**：2　暫定・未検証成果
- **内容**：a1 の自己申告によると、65ff124 で次を変えた。X-04 が matches_stage_total を返し、QA-01 に検査 (d)（違反名「gas breakdown total」）を加えた。B3-01 の「e0 = 0 なら行を捨てる」近道を外した。買電と冷媒の行を、文字列「GRID」「REFRIGERANT」ではなく番兵オブジェクトで区別する。ガスの一覧は重複を除いて使い、X-05 は CO2 が一覧に無くても動く。SYS-01 は NaN・無限大を NOT_FINITE として報告する。SYS-03 は廃棄係数の無い設備行を報告する。X-17 は要約数量が正でない区分を除いて数える。X-13 に n_skipped。台帳の定義文 50 単位分を書き換えた。
- **所在**：
  - [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json)
  - [`materials/interrupted_fix/working_tree_at_stop_65ff124.patch`](../materials/interrupted_fix/working_tree_at_stop_65ff124.patch)
  - git コミット 65ff124（`09_APPROX_STUDY/research_code/refcalc/`（コミット `65ff124` の版）、`09_APPROX_STUDY/01_LEDGER/units.json`（コミット `65ff124` の版））
- **確かめ方**：a1 の自己申告だけ。申告の内容：RED-4 の再現で QA-01 が不合格・['gas breakdown total']。NUM-3 の再現で X-04 が基準計算 8938913.468391037、統合モデル 8938913.46839103。NUM-5 の再現で係数 ID「GRID」「REFRIGERANT」でも一致。sync_ledger の最終実行で「synced 70 units (0 changed)」。今回は実行していない。
- **確かめた者**：中断した修正の自己申告
- **言える範囲**：65ff124 のスナップショットにだけある。架空データ、独立概念モデル。文言の改訂は a1 の担当ファイルだけで、06_OPEN_ISSUES の B、DERIVATIONS.md、記録、04_VERIFICATION/README は未改訂。
- **関係する第2回の指摘**：RED-4、RED-6、RED-7、RED-8、RED-9、RED-11、RED-12、NUM-3、NUM-5、NUM-6、NUM-8
- **第2回の指摘の影響**：RED-4、RED-6、RED-9、NUM-3、NUM-5、NUM-6、NUM-8 は FIXED、RED-7、RED-8、RED-11、RED-12 は PARTLY_FIXED と申告。未対応と申告：RED-12(7)（正の周期に下限なし）、QA-01 の (b)(c) が不合格になり得ない点。NUM-3 の対応で、値 0・ガス別量ありの係数での X-04 の基準計算の値がコミット版と変わる（8893233.37821491 → 8938913.468391037）。
- **今の時点で言ってよいこと**：65ff124 に、これらの変更を加えた基準計算と台帳がある。定義文とコードが一致しているかは確認されていない（VERIFY_DEF の 5 は開始されなかった）。
- **使ってはいけない記述**：
  - 65ff124 の台帳 units.json の reference_semantics を、コミット版（60e720f）の基準計算の定義として読むこと
  - A1_REPORT.json の「No number changed」（文言の改訂で数値は変わらない）を検証済みと読むこと
- **新研究での再利用**：候補にしない
  - 理由・注意：参照するなら「未検証の修正案」と明記する。定義文はコミット版の units.json（HEAD）から読む。
- **分類の根拠**：
  - [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json)：findings[2]（NUM-3）、[4]（NUM-5）、[5]（NUM-6）、[7]（NUM-8）、[14]（RED-4）、[16]（RED-6）、[17]〜[19]（RED-7〜9）、[21]（RED-11）、[22]（RED-12）、acceptance[5]、interface_changes（units.json は 50 単位の定義文）
  - git show --stat 65ff124：01_LEDGER/units.json 129 行の変更
  - [`materials/interrupted_fix/specs/SPEC_A1.md`](../materials/interrupted_fix/specs/SPEC_A1.md):153-193
- **分類した観点**：R2（基準計算・架空データ・比較・試験）

<a id="ck-r2-23"></a>

## CK-R2-23　中断した修正 a1：試験 68 件、壊し方 214 種類、比較の厳格化、一致確認の自己申告

- **区分**：2　暫定・未検証成果
- **内容**：a1 の自己申告によると、65ff124 で、試験を 28 件から 68 件に増やした（test_closed_forms.py を fractions.Fraction のループとの比較に書き直して 14 件、test_refcalc.py に DefinitionTests 23 件、test_engine.py に 9 件追加）。bench/mutations.py は 36 種類から 214 種類。compare.py は、無限大は同じ無限大とだけ、bool は bool とだけ等しいとする。verify_unified.exactness は床 0 で比べ、合計のみの出力の余分な葉と、有効な評価期間での例外を不合格にする。sweep_check は 70 単位すべてを比べる。
- **所在**：
  - [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json)
  - [`materials/interrupted_fix/working_tree_at_stop_65ff124.patch`](../materials/interrupted_fix/working_tree_at_stop_65ff124.patch)
  - [`materials/interrupted_fix/a1_scratch/exact_60_20.out`](../materials/interrupted_fix/a1_scratch/exact_60_20.out)
  - [`materials/interrupted_fix/a1_scratch/exact_400_60_40.out`](../materials/interrupted_fix/a1_scratch/exact_400_60_40.out)
  - git コミット 65ff124（`09_APPROX_STUDY/research_code/tests/`（コミット `65ff124` の版）、bench/mutations.py、bench/verify_unified.py、common/compare.py）
- **確かめ方**：a1 の自己申告だけ。申告の内容：68 件が合格（'Ran 68 tests in 32.585s' / 'OK'）。exactness(60, 20) は 1110 シナリオで all_exact 真、床 0、最大 1.408e-13（B3-01.value）。exactness(400, 60) と sweep_check(40) は 1490 シナリオで all_exact 真、最大 4.775e-13（SUM-08.delta）、掃引 65 シナリオで最大 1.093e-13。検査担当の乱数ファズ 6000 件は例外 0、食い違い 2 件（目標 0 に届かず、受け入れ条件 e は不合格）。STOP_STATUS は、65ff124 のコードが試験に通るかを確認していないと書く。今回も実行していない。
- **確かめた者**：中断した修正の自己申告
- **言える範囲**：65ff124 のスナップショットにだけある。数値は a1 の版の基準計算と統合モデルどうしの比較で、コミット版の測定値（681 シナリオ）とは対象が違う。研究の JSON（04_VERIFICATION）は書き換えられていない。
- **関係する第2回の指摘**：NUM-10、NUM-11、REP-16
- **第2回の指摘の影響**：NUM-11 と REP-16 は FIXED、NUM-10 は PARTLY_FIXED と申告。a2（統合モデルの再構成）が同じファイルを途中まで書き換えた状態で停止しているので、65ff124 の tests/test_engine.py と bench/verify_unified.py は a1 の申告時点の内容と同じではない可能性がある（git show --stat で test_engine.py は 388 行、verify_unified.py は 182 行の変更。a1 の申告は 205 行と 135 行）。
- **今の時点で言ってよいこと**：65ff124 に、増やした試験と壊し方、厳しくした比較のコードがある。a1 の申告した合格と一致の数値は、誰も再現していない。
- **使ってはいけない記述**：
  - 「Ran 68 tests ... OK」「1490 scenarios all_exact True」を、65ff124 の状態についての確認済みの結果と読むこと
  - a1 の一致確認の数値を、04_VERIFICATION の記録（681 シナリオ）の更新版として使うこと
- **新研究での再利用**：候補にしない
  - 理由・注意：参照するなら「未検証」と明記する。214 種類の壊し方はコミット版の基準計算を前提にしていない（コミット版では例外や NaN になる入力を含む）。
- **分類の根拠**：
  - [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json)：tests、acceptance[0]〜[5]（a〜f。e は passed false）、findings[9]（NUM-10）、[10]（NUM-11）、[26]（REP-16）、decisions（mutations 36 → 214）
  - [`materials/interrupted_fix/a1_scratch/exact_60_20.out`](../materials/interrupted_fix/a1_scratch/exact_60_20.out)（exactness(60, 20)：scenarios 1110、all_exact True、floor 0.0）
  - git show --stat 65ff124：tests/test_refcalc.py 452 行、test_closed_forms.py 286 行、test_engine.py 388 行、bench/mutations.py 461 行、bench/verify_unified.py 182 行、common/compare.py 13 行
  - [`STOP_STATUS.md`](../STOP_STATUS.md):97-99
- **分類した観点**：R2（基準計算・架空データ・比較・試験）

<a id="ck-r2-24"></a>

## CK-R2-24　中断した修正 a1 に残る未解決事項と副作用（自己申告の open_problems）

- **区分**：4　不具合・未解決事項
- **内容**：a1 が自分の報告に残した未解決の点。(1) NUM-10 の限界は指示どおり変えていない：施設管理の比率 1.0 で燃料が 1e-6 倍以下、1e-8 だけ違う基準案、1e308 付近の桁あふれ、漏洩率が 1 から 1e-8 以内で補充なし。(2) 乱数ファズの目標 0 に届かず、6000 件中 2 件が食い違う。(3) 冷媒量 5e-324 kg の桁落ち。(4) 型の違う入力は例外のまま。(5) RED-12(7) は未対応：周期 1e-9 年・T=60 で 6e10 事象になり、試しのファズがメモリ不足で止まった。(6) 基準計算が重くなった（命令数 1.24 倍）。(7) 担当外の文書（06_OPEN_ISSUES の B、DERIVATIONS.md D3、記録、04_VERIFICATION/README）は古い規則のまま。(8) 結果のキーと意味が変わり、保存済みの JSON と tools/build_reports.py が合わなくなる。
- **所在**：
  - [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json)
  - [`STOP_STATUS.md`](../STOP_STATUS.md)
  - [`materials/interrupted_fix/specs/VERIFY_DEF.md`](../materials/interrupted_fix/specs/VERIFY_DEF.md)
- **確かめ方**：a1 の自己申告。独立の検査（V-DEF、V-NUM）と、その後の反証検査・修正の反復、記録と報告書の再生成は開始されなかった（STOP_STATUS.md 3 節）。
- **確かめた者**：中断した修正の自己申告
- **言える範囲**：65ff124 の a1 の版についての記述。コミット版（60e720f）の基準計算には当てはまらない点（1.24 倍、キーの変更）と、コミット版にも当てはまる点（NUM-10 の限界、RED-12(7)、型の違う入力）が混ざっている。
- **関係する第2回の指摘**：NUM-10、RED-12、RED-3、RED-7、RED-8、RED-11、REP-17
- **第2回の指摘の影響**：第2回の指摘 59 件のうち、a1 の範囲の 27 件について、申告は FIXED 18、PARTLY_FIXED 8、DOCUMENTED_ONLY 1。PARTLY_FIXED の残りは主に担当外の文書の改訂。どの申告も独立に確認されていない。
- **今の時点で言ってよいこと**：a1 の版は、(a) 独立の検査を受けていない、(b) a1 自身が食い違いの残り（2/6000）と未対応の点を申告している、(c) 43ba5d7 の測定・記録・報告書と対応しない、の 3 点から、基準としても成果としても確定していない。
- **使ってはいけない記述**：
  - 「a1 は完了」を、基準計算の定義の修正が済んだという意味に取ること（完了は作業担当の報告で、検査は未実施）
  - a1 の版の命令数の削減率の試算（規模 S の合計のみ 0.676 → 0.701 など）を測定結果として使うこと
- **新研究での再利用**：候補にしない
  - 理由・注意：新研究は基準計算を変えないので、a1 の版を基準にしない。コミット版にも当てはまる限界（NUM-10、RED-12(7)、型の違う入力）は、入力の条件として CK-R2-03、CK-R2-07、CK-R2-09 と合わせて守る。
- **分類の根拠**：
  - [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json)：open_problems（10 項目）、acceptance[4]（e. passed false：6000 件中 2 件）、findings の status（FIXED 18、PARTLY_FIXED 8、DOCUMENTED_ONLY 1。JSON を数えた）
  - git show --stat 65ff124：refcalc の 4 ファイルの変更行数（base.py 332、units_b.py 175、units_c_sum.py 248、units_pre_a.py 142）は a1 の申告と同じ。fastcalc/engine.py（申告 455、スナップショット 1051）、closed_forms.py（193 と 211）、tests/test_engine.py（205 と 388）、bench/verify_unified.py（135 と 182）は申告より多く、後の段階の編集が重なっている
  - [`STOP_STATUS.md`](../STOP_STATUS.md):50-62（段階ごとの状態）、90-92（65ff124 を取り除いた理由）
  - [`materials/interrupted_fix/specs/VERIFY_DEF.md`](../materials/interrupted_fix/specs/VERIFY_DEF.md):1-44
- **分類した観点**：R2（基準計算・架空データ・比較・試験）

<a id="ck-r3-31"></a>

## CK-R3-31　中断した修正 a1：時間の判定を厳密な有理数の演算にし、閉形式を作り直す

- **区分**：2　暫定・未検証成果
- **内容**：第2回の指摘 NUM-1・REC-1・APP-5 への対応として決めた設計と、その実装の自己申告。すべての時間の判定を、与えられた 2 進の浮動小数点の値に対する厳密な演算で行う：c＝1−1e-9 に最も近い倍精度値、内側 ⇔ τ＜T·c、年＝max(1, ceil(τ·c))、周期 L の n 番目の事象は厳密に n·L。閉形式は renewal_count＝ceil(T·c/L)−1、除外年の重みは q＝L·c が 1 以上なら事象の年は互いに異なり、1 未満なら年 1 から最後の事象の年まで、を整数の演算で判定する。a1 は基準計算と統合モデルの両方に実装したと報告した。
- **所在**：
  - [`materials/interrupted_fix/specs/SPEC_A1.md`](../materials/interrupted_fix/specs/SPEC_A1.md)
  - [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json)
  - [`materials/interrupted_fix/working_tree_at_stop_65ff124.patch`](../materials/interrupted_fix/working_tree_at_stop_65ff124.patch)
- **確かめ方**：a1 の報告：周期 1.000000001 で両方が書かれた定義の値を返す（T＝60 で 59 事象が年 2〜60。B3-01 は基準計算 19107.604293677847、統合モデル 19107.60429367785）。試験は fractions.Fraction で書いた逐語のループと、境界を狙った 3,000 組以上と乱数 12,000 組で不一致 0。独立の検査は行われていない。停止の作業では、中断時点の Python ファイルが構文として読めることだけを確かめ、実行していない。
- **確かめた者**：中断した修正の自己申告
- **言える範囲**：65ff124 に記録された未検証の編集。作業ツリーからは取り除かれており（0db5c77）、60e720f のコードには入っていない。
- **関係する第2回の指摘**：NUM-1、REC-1、APP-5、RED-3、RED-12
- **第2回の指摘の影響**：第2回の指摘への対応案であり、指摘の対象ではない。この変更は基準計算の出力の形も変える（B4-01 の events が時刻ではなく年の整数になる、無効な周期を数える n_invalid が加わる、など）。回数の式は T·c/L−1 ≤ N＜T·c/L になる（APP-5 の文書化）。正の周期に下限がない点（RED-12 の 7）は対応していない。DERIVATIONS.md の D2・D3 の書き直しは行われていない。
- **今の時点で言ってよいこと**：「時間の判定を厳密な有理数の演算で定義すれば、閉形式は整数の演算で証明でき、丸めに依存しない」という設計がある。実装は 65ff124 と保存したパッチにあり、動作は作成した作業担当の申告だけである。
- **使ってはいけない記述**：
  - NUM-1 は修正済み（FIXED）である、を検証済みの事実として扱うこと
  - 閉形式は「いまや証明できる形で厳密」（仕様の表現。実装の検査はない）
- **新研究での再利用**：候補（ルート B・C）
  - 使い道：時間の規則を丸めに依存しない形で定義する案として読む。基準や対照には使わない。
  - 条件・注意：設計の記録として読むだけにする。65ff124 のコード・閉形式・数値は、基準にも出発点にも使わない（HANDOVER.md 4.1・4.2）。新研究の基準計算は公開中の版で、周期 1.000000001 では丸めに依存したままである。
- **分類の根拠**：
  - [`materials/interrupted_fix/specs/SPEC_A1.md`](../materials/interrupted_fix/specs/SPEC_A1.md):39-78
  - [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json): findings (NUM-1, REC-1, APP-5), decisions, interface_changes
  - [`STOP_STATUS.md`](../STOP_STATUS.md):54, 86-87, 97-99
- **分類した観点**：R3（統合モデルとその根拠）
- **停止後の点検による訂正**：点検の指摘 C1-02、再点検 C1-02 により、上の記述の一部を改めた。分類担当の元の記述は `materials/classification/R3.json`、訂正の内容は `materials/classification/overrides.json` にある。

<a id="ck-r3-32"></a>

## CK-R3-32　中断した修正 a1：修正後の一致確認と負荷の変化（自己申告の数字）

- **区分**：2　暫定・未検証成果
- **内容**：a1 が、基準計算と統合モデルの両方を直した後のコードについて報告した数字。厳密一致は 1,490 シナリオ（壊し方を 36 種から 214 種に増やし、段階の部分集合と上流の不備の組 90 件を加えた）で、床 0 の比較で不一致 0、最大 4.775e-13（SUM-08 の delta）。掃引は 65 シナリオ・70 単位・309,705 個で最大 1.093e-13。全数値項目を 1 つずつ変える 3,461 件は食い違い 0（型の違う入力での同種の例外 66 件）。検査担当の乱数の反例探し 6,000 シナリオは食い違い 2 件（漏洩率 0.999999999 の冷媒）で、目標の 0 に届いていない。試験 68 件は合格。命令数は基準計算が 1.24 倍（S で 2,528,394 → 3,135,214）になり、削減率は S の合計のみで 0.676 → 0.701 と読める、と報告している。
- **所在**：
  - [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json)
  - [`materials/interrupted_fix/a1_scratch`](../materials/interrupted_fix/a1_scratch)
- **確かめ方**：a1 の作業担当が自分で実行した結果の報告。仕様が予定していた反証検査（最大 2 巡）は未着手。停止の作業では実行していない。
- **確かめた者**：中断した修正の自己申告
- **言える範囲**：65ff124 のコード（a2 の途中の編集が重なる前の a1 の時点）についての申告。60e720f の公表値とは別のコード・別のシナリオ集合の数字である。
- **関係する第2回の指摘**：NUM-1、NUM-2、NUM-3、NUM-4、NUM-5、NUM-6、NUM-7、NUM-8、NUM-9、NUM-10、NUM-11、REP-16、REP-17
- **第2回の指摘の影響**：第2回の指摘への対応の結果の申告。a1 自身が残る問題を挙げている：NUM-10 の (a)(c)(d)(e) は残る、反例探しの目標 0 は未達、型の違う入力は例外のまま、ごく小さい正の周期で基準計算が事象を 1 つずつ数える、削減率の上昇のうち約 3〜5 ポイントは基準計算が重くなったことによる。
- **今の時点で言ってよいこと**：a1 の作業担当は上の数字を報告した。独立の検査はなく、公表の測定・記録・報告書（60e720f）とは対応しない。
- **使ってはいけない記述**：
  - 1,490 シナリオで一致、を検証済みの成果として扱うこと
  - 修正後の削減率（0.701 など）を公表値の更新として使うこと
- **新研究での再利用**：候補にしない
  - 理由・注意：使う場合は 65ff124 のコードを独立に検査してからにする。a1_scratch の出力ファイルは、この読み手は名前を見ただけで中身を読んでいない。
- **分類の根拠**：
  - [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json): acceptance, open_problems, decisions, tests
  - [`STOP_STATUS.md`](../STOP_STATUS.md):54, 58, 97-99
- **分類した観点**：R3（統合モデルとその根拠）

<a id="ck-r3-36"></a>

## CK-R3-36　中断した段階 a2 の途中の出力 2 ファイル（未検証）

- **区分**：2　暫定・未検証成果
- **内容**：a2 が停止前に書き出した JSON。(1) membership_check_UNVERIFIED.json：5 つの架空シナリオ（各 資材 60・設備 24・冷媒 8）で 35 種の故障を入れ、変わった単位を記録したもの。公表の 66 件のうち「自分のモデルのどの共有物を壊しても反応しない」のは A13-05（K1）、SYS-03（K7）、X-13（K1）の 3 件、K3 の B6-02・B6-04・B7-01〜03・X-06 は合計のみの出力では件数か印を通じてしか反応しない、B6-01 は全出力でしか反応しない、とする。(2) mechanism_probe_UNVERIFIED.json：仕組みのシナリオ 2 つとベンチマーク S・M・L で数えた演算の回数と、P1〜P7 がすべて真という判定。
- **所在**：
  - [`materials/interrupted_fix/a2_partial_outputs/membership_check_UNVERIFIED.json`](../materials/interrupted_fix/a2_partial_outputs/membership_check_UNVERIFIED.json)
  - [`materials/interrupted_fix/a2_partial_outputs/mechanism_probe_UNVERIFIED.json`](../materials/interrupted_fix/a2_partial_outputs/mechanism_probe_UNVERIFIED.json)
- **確かめ方**：a2 の作業担当が自分のスクリプトで出したもの。a2 は報告を出す前に停止しており、スクリプトが完成していたか、試験に通っていたかの記録はない。独立の検査はない。
- **確かめた者**：なし（中断した修正の出力。自己申告の報告もない）
- **言える範囲**：65ff124 の、作り直しの途中の統合モデルについての数字（故障を入れた場所が Aggregate.charges、indicator、Resolver など、60e720f にはない名前である）。60e720f のコードについての結果ではない。架空データ。
- **関係する第2回の指摘**：REC-2、REC-3、REC-4、REC-6、REP-4
- **第2回の指摘の影響**：第2回の指摘と向きは合う（A13-05・X-13・SYS-03 が外れる、K3 の 7 単位は閉形式の値を自分の出力に持たない、行ごとの換算を持つ行の解決は行ごと：規模 L で 5,183 回・相異なる組 80）。B1-01 は、機器の表を作る再構成の後のコードでは反応する側に入っている。ただし検査を受けていないので、指摘の裏付けとしても、指摘が解消した証拠としても使えない。
- **今の時点で言ってよいこと**：この 2 ファイルは存在し、上の内容を記録している。内容が正しいかどうかは確かめられていない。
- **使ってはいけない記述**：
  - 所属は 63 単位で確定した、という扱い
  - P1〜P7 は成立が確認された、という扱い
  - これらの数字を 60e720f の公表値（mechanism_counts）の訂正として使うこと
- **新研究での再利用**：候補にしない
  - 理由・注意：ファイル名のとおり未検証。パッチの中のスクリプト本体は、この読み手は読んでいない。
- **分類の根拠**：
  - [`materials/interrupted_fix/a2_partial_outputs/membership_check_UNVERIFIED.json`](../materials/interrupted_fix/a2_partial_outputs/membership_check_UNVERIFIED.json): claims, by_model, closed_forms, scenarios, notes, shared_objects
  - [`materials/interrupted_fix/a2_partial_outputs/mechanism_probe_UNVERIFIED.json`](../materials/interrupted_fix/a2_partial_outputs/mechanism_probe_UNVERIFIED.json): statements.P1..P7, engine_counters, notes
  - [`STOP_STATUS.md`](../STOP_STATUS.md):18, 22, 56, 90-92
- **分類した観点**：R3（統合モデルとその根拠）

<a id="ck-r4-23"></a>

## CK-R4-23　b2 の再測定と新しい候補（中断した修正。自己申告のみ）

- **区分**：2　暫定・未検証成果
- **内容**：第2回の指摘（APP-1〜9、REP-5・6・13、REC-8）を測定プログラムに反映した版と、その出力。approx_study.py を 4 つのモジュールに分け、schema 3.0 の出力（候補 40 種）を作った。既存 32 候補の再測定（電力の候補を段階 B6・B2 と単位の出力で測る、下流へ波及させた合計、パラメータの出所、基準 0 の件数、入力数、命令数、材料区分別の追加）と、新しい候補 AP-05a・AP-05b（AP-05 の 2 変種）、AP-18d（AP-18b を他の建物の値で）、AP-19c（全行に 1 つの比率）、AP-23a・b・c（修繕の安全側）、AP-24a・b（年次表の年次量を 5 年刻みに）を含む。基準計算は a1 が変更した 65ff124 の版で、これも未検証。
- **所在**：
  - [`materials/interrupted_fix/b2_output/approximation_study_UNVERIFIED.json`](../materials/interrupted_fix/b2_output/approximation_study_UNVERIFIED.json)
  - [`materials/interrupted_fix/agent_reports/B2_REPORT.json`](../materials/interrupted_fix/agent_reports/B2_REPORT.json)
  - [`materials/interrupted_fix/agent_reports/B2_REPORT_long.json`](../materials/interrupted_fix/agent_reports/B2_REPORT_long.json)
  - [`materials/interrupted_fix/agent_reports/candidate_lines.json`](../materials/interrupted_fix/agent_reports/candidate_lines.json)
  - [`materials/interrupted_fix/agent_reports/cmp_committed_vs_new.log.txt`](../materials/interrupted_fix/agent_reports/cmp_committed_vs_new.log.txt)
  - [`materials/interrupted_fix/working_tree_at_stop_65ff124.patch`](../materials/interrupted_fix/working_tree_at_stop_65ff124.patch)
  - コミット 65ff124 の `09_APPROX_STUDY/research_code/bench/`（コミット `65ff124` の版）（approx_study.py、approx_measures.py、approx_meta.py、approx_support.py）と tests/test_approx_study.py
- **確かめ方**：作業担当の自己申告：母集団 400 の全体の実行を 4 回、単体試験 106 件（うち 16 件が新しい試験）が合格。公表済みの数値 3936 個は名前を変えた場所に同じ値で残り、違いは 29 個（表示、対象単位、材料区分別の追加、AP-09c の印など）。旧コードを新しい基準計算で動かすと公表ファイルと 4410 個すべて一致した（時間規則の変更では数値が変わらなかった）とも申告。第2回の検査担当・反証検査担当の値と一致すると申告されているもの：AP-23a・b、AP-18d、AP-19c、AP-05a、段階 B2 の値、波及後の合計、AP-14 の内訳、AP-17 の恒等式。b2 だけが出した値：AP-24a（173 件）段階 B7 -4.07％〜+2.14％、段階 B6 -1.77％〜+1.37％、入力 304.4 個 → 65.6 個、命令数 3.03 倍。AP-24b（153 件）段階 B6 -2.51％〜+3.04％、段階 B2 -5.93％〜+4.56％。AP-23c -39.4％〜+329.1％。行ごとの命令数（候補／厳密）：AP-01 47.0／63.0、AP-04 14.0／112.4、AP-06 16.1／16.1、AP-07b 134.4／86.9。
- **確かめた者**：中断した修正の自己申告（独立の検査は未実施。このリーダーも実行していない）
- **言える範囲**：架空データ、独立概念モデル、65ff124 の未検証の基準計算。記録と報告書を作る道具（tools/build_records.py、build_reports.py）は新しい JSON に対応しておらず、記録・報告書は再生成されていない。0db5c77 で作業ツリーからは取り除かれている。
- **関係する第2回の指摘**：APP-1、APP-2、APP-3、APP-4、APP-5、APP-6、APP-7、APP-8、APP-9、REP-5、REP-6、REP-13、REC-8
- **第2回の指摘の影響**：b2 は指摘 13 件のうち APP-8 を FIXED、残り 12 件を PARTLY_FIXED と申告した（測定の側だけ対応し、理由文・記録・報告書は後の段階に残した）。その後の段階（b3、反証検査と修正の反復、記録と報告書の再生成）は始まっていない。
- **今の時点で言ってよいこと**：b2 の出力は保存されており、作業担当は第2回の検査担当の値と一致すると申告している。独立に確かめられたものではない。AP-24a・AP-24b・AP-23c・命令数・入力数は b2 だけが出した値で、ほかの誰も測っていない。
- **使ってはいけない記述**：
  - b2 の数値を検証済みとして引用すること
  - AP-23a・AP-23b を「目標を満たす」と書くこと（b2 自身が、周期が評価期間に近い架空シナリオでは +3.5％ になるので書いてはならないと注記している）
  - AP-05a を単位ごとに「安全側」と書くこと（段階 B1 は過小にならないが、単位 B1-03・B1-04 は過小になると申告）
  - 「時間規則の変更で近似の数値は変わらなかった」を確認済みとして扱うこと（未確認。確認には実行が要る）
- **新研究での再利用**：候補（ルート B・C）
  - 使い道：欠陥を直した測定の設計（基準量を段階の値で取る、下流まで計算し直した合計、パラメータの出所の表示、基準 0 の件数、入力数と命令数、候補が単位・段階・建物のどの水準で測られたかの表示）を、新研究の誤差測定の設計の参考にする。新しい候補の一覧は、旧研究が測っていなかった形の一覧として使える。数値を使う場合は新研究で測り直す。
  - 条件・注意：未検証。基準計算が 65ff124 の変更版であること。命令数は 20 シナリオの小さな計算の核の値で、時間とメモリは測っておらず、a2 が編集中だった fastcalc/closed_forms.py に依存する。他の建物から作るパラメータの結果は、作り方（構造×用途ごとの合計の比）で変わる。
- **分類の根拠**：
  - agent_reports/B2_REPORT.json：findings（status）、acceptance、open_problems、interface_changes
  - agent_reports/cmp_committed_vs_new.log.txt 1 行目（same 3936、diff 29、missing 0）
  - b2_output/approximation_study_UNVERIFIED.json：schema_version 3.0、candidates 40 件、error_definition、target_definition
  - STOP_STATUS.md 1 節・3 節（b2：完了を報告、独立の検査は未実施）
  - git show --stat 65ff124（bench の 4 ファイルと tests/test_approx_study.py）
- **分類した観点**：R4（近似検証）

<a id="ck-r4-24"></a>

## CK-R4-24　b2 の設計（SPEC_B2）と結論文の書き換え案

- **区分**：3　研究途中の数式・仮説
- **内容**：測定の修正の仕様（SPEC_B2.md、変更 13 項目と受入条件 3 項目）と、b2 の作業担当が出した候補ごとの結論文の案（conclusion_proposals.json、41 件：書き換え 16、そのまま 16、新規 9）。新規の結論の案は AP-05a・AP-05b・AP-23a が不採用、AP-18d・AP-19c・AP-23b・AP-23c・AP-24a・AP-24b が保留。
- **所在**：
  - [`materials/interrupted_fix/specs/SPEC_B2.md`](../materials/interrupted_fix/specs/SPEC_B2.md)
  - [`materials/interrupted_fix/agent_reports/conclusion_proposals.json`](../materials/interrupted_fix/agent_reports/conclusion_proposals.json)
  - [`materials/interrupted_fix/agent_reports/B2_REPORT.json`](../materials/interrupted_fix/agent_reports/B2_REPORT.json)
- **確かめ方**：なし。案の段階で、記録（candidates.json、records/units.json）にも報告書にも反映されていない。
- **確かめた者**：中断した修正の自己申告
- **言える範囲**：旧研究の記録の文面についての案。架空データ、独立概念モデル。
- **関係する第2回の指摘**：APP-1、APP-2、APP-3、APP-4、APP-5、APP-6、APP-7、APP-9、REP-5、REP-6、REC-8
- **第2回の指摘の影響**：案は第2回の指摘を理由文に反映するためのもの（例：AP-17 は「誤差は標本共分散に等しい」、AP-18b は「同じ建物の値を使った最良の場合」、AP-09c は「B2 段階では 2％ をわずかに超える」、AP-04 は「同じ手間」を外す）。採用も検査もされていない。
- **今の時点で言ってよいこと**：書き換え案と新規候補の結論の案が保存されている、という事実だけ。
- **使ってはいけない記述**：
  - 案の文を旧研究の結論として引用すること
- **新研究での再利用**：候補（ルート A・C）
  - 使い道：旧研究の候補の理由文を引用するときに、どの文を使ってはいけないか（16 候補）を確かめる対照表として使える。
  - 条件・注意：案であり、確定した記録ではない。案の中の数値は b2 の未検証の測定による。
- **分類の根拠**：
  - agent_reports/conclusion_proposals.json：verdict の集計 REWORD 16 / SUPPORTED 16 / NEW 9、suggested_outcome（このリーダーが集計）
  - specs/SPEC_B2.md 変更 1〜13、受入条件 a〜c
  - agent_reports/B2_REPORT.json acceptance c
- **分類した観点**：R4（近似検証）

<a id="ck-r5-30"></a>

## CK-R5-30　予定だったが行われなかった改訂（Stage C）：記録・進捗台帳・報告書の生成器

- **区分**：3　研究途中の数式・仮説
- **内容**：第2回の指摘を記録・進捗台帳・報告書に反映するための改訂の覚え書き。ワークフローの各段階（a1、a2、b3、b2、反証の検査と修正）の報告を入力にして、主担当が行う予定だった。どれも着手されていない。内容：build_records.py について 7 点。(1) 厳密な記録の裏付けを作り直す。M2 は「共有の対象を壊すとその単位の出力が変わる」ことの測定を所属の証拠にし、証拠のない M2 の成功があれば生成を失敗させ、感度のない単位は統合に数えない（対象外になる見込み：A13-05、X-13、SYS-03 と、a2 の報告しだいのもの。B1-01 は機器の表が実体である場合だけ統合に残す）。M1 の機構は、外から計測した全体の測定（P1〜P7）として表示し、閉形式の M1 の記録には「その閉形式を壊すと不合格になる単位」を付ける。「導出と架空データ」の表示は 3 つがそろう場合だけにし、注記は実際の件数を計算して書く。(2) 題名の訂正（A5-01 の M1 を候補なしに、QA-03 の M1、B4-02 の M1、B1-01 と D6 の文言）。(3) 候補なしの理由の訂正（B6-04 の M4、「同じ手間」の定型文の限定、運用の単位は「記述子なら閉形式、年次表なら走査」、M1 の記録のない単位の理由）。(4) 近似候補が付く単位の出所を approximation_study.json の 1 か所にし、記録に証拠の範囲（単位／段階／建物全体）を持たせる。(5) 候補の結論の文の言い換え。(6) 評価者の提案の対照を手順書どおりにする（b1 → M1、b2・b3・b4 → M2、b5・b6 → M3、b8 → M4 と M5、b7 は測定した候補へ）。(7) 「検査の 3 単位」を計算で出し、表の読み出しの数を実際の内容の名前で呼ぶ。progress_ledger.py：段階ごとに証拠の範囲を持たせ、建物全体の代理だけによる保留をそう表示し、単位ごとの保留と数え分ける。build_reports.py：REP-1、7、8、9、11、12、13、15、16、18 の訂正、見出しの統合の数を所属の証拠から出す、近似の単位ごと・建物全体の区別、候補の負荷と入力、所属と機構の測定の節。
- **所在**：
  - [`materials/interrupted_fix/specs/STAGE_C_NOTES.md`](../materials/interrupted_fix/specs/STAGE_C_NOTES.md)
  - [`materials/interrupted_fix/agent_reports/conclusion_proposals.json`](../materials/interrupted_fix/agent_reports/conclusion_proposals.json)
  - [`materials/interrupted_fix/agent_reports/candidate_lines.json`](../materials/interrupted_fix/agent_reports/candidate_lines.json)
  - [`materials/interrupted_fix/a2_partial_outputs/`](../materials/interrupted_fix/a2_partial_outputs)
- **確かめ方**：確認はない（計画の覚え書き）。前提になる a2 の出力（所属の測定、機構の計測）は途中で止まっており未検証。b2 の結論の言い換え案（41 候補：言い換え 16、現状維持 16、新規 9）は自己申告である。
- **確かめた者**：なし
- **言える範囲**：旧研究の記録・台帳・報告書をどう直すつもりだったかの設計。実施されていない。
- **関係する第2回の指摘**：REC-2、REC-5、REC-6、REC-7、REC-8、REC-9、REP-1、REP-2、REP-3、REP-4、REP-5、REP-6、REP-7、REP-8、REP-9、REP-11、REP-12、REP-13、REP-14、REP-15、REP-16、REP-18
- **第2回の指摘の影響**：この覚え書きは、上の指摘への対応の案である。対応は 1 つも実施されていないので、指摘はすべて未反映のまま残っている。
- **今の時点で言ってよいこと**：これは「第2回の指摘をどう反映するつもりだったか」の設計の記録である。記録・進捗台帳・報告書と、その生成器は改訂されていない（65ff124 の差分は、tools、03_MODELS、05_DECISIONS、06_OPEN_ISSUES のファイルに触れていない）。
- **使ってはいけない記述**：
  - 覚え書きの見込み（「対象外になる見込み：A13-05、X-13、SYS-03」など）を結果として引用すること
  - 覚え書きの文を、実施済みの改訂として読むこと
  - b2 の結論の言い換え案と新しい候補（AP-05a、AP-05b、AP-18d、AP-19c、AP-23a〜c、AP-24a・b）を、検証済みの結論として引用すること
- **新研究での再利用**：候補（ルート A・C）
  - 使い道：新研究が旧成果を引用したり、自分の記録を作ったりするときの、裏付けの様式の案として使える（統合の所属は故障注入で確かめる、仕組みは外からの計測で確かめる、近似の証拠の範囲を単位・段階・建物全体で区別する）。
  - 条件・注意：設計案であり、未検証。旧研究の記録をこの案で作り直す作業は行わない（未完成の部分を完成させる作業に当たる）。
- **分類の根拠**：
  - [`materials/interrupted_fix/specs/STAGE_C_NOTES.md`](../materials/interrupted_fix/specs/STAGE_C_NOTES.md):1-5（主担当がワークフローの後に行う予定）、7-33（build_records.py）、35-37（progress_ledger.py）、39-44（build_reports.py）
  - [`STOP_STATUS.md`](../STOP_STATUS.md):19-20、59（記録・進捗台帳・報告書の改訂は未着手）
  - [`materials/interrupted_fix/agent_reports/conclusion_proposals.json`](../materials/interrupted_fix/agent_reports/conclusion_proposals.json): 41 候補（verdict は REWORD 16、SUPPORTED 16、NEW 9）
  - [`materials/interrupted_fix/working_tree_at_stop_65ff124.patch`](../materials/interrupted_fix/working_tree_at_stop_65ff124.patch)（変更されたファイルの一覧）
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

<a id="ck-r5-31"></a>

## CK-R5-31　予定だったが行われなかった改訂（Stage C）：手書きの文書と、全体の再生成

- **区分**：3　研究途中の数式・仮説
- **内容**：第2回の指摘を手書きの文書に反映し、全体を測り直して再生成する予定の覚え書き。内容：DERIVATIONS.md（D2・D3 を厳密な演算で書き直し、事象が相異なる年に入る条件の証明を付ける。D6 の最後の行、D8 の「何を記憶するか」、「導出が当てはまらない範囲」）。EVALUATION_PROTOCOL.md を v1.4 に（P3・P4、P7 の語彙、P8 の裏付けの規則、故障注入による所属）。06_OPEN_ISSUES/README.md（B-11 に資材の初期据付を追加、B-15、B-17、B-18 の書き直し、新しい規約の追加、D-3・D-4、G、第2回の検査の状態）。INDEPENDENT_REVIEW.md（第2回の節：59 件の番号と対応の表、修正後のコードへの反証の検査の節、「まだ行っていない」の削除）。research_code/README.md と synth/README.md（コマンド、新しい測定のファイル）。再生成の順序：試験 → 台帳の同期 → 軸 A の測定 → 順位 → 一致と負荷の測定 → 所属の測定 → 機構の計測 → 入力の使用 → 近似の測定 → 記録 → 進捗台帳 → 報告書 → 登録の検査 → 禁止ファイルの走査。
- **所在**：
  - [`materials/interrupted_fix/specs/STAGE_C_NOTES.md`](../materials/interrupted_fix/specs/STAGE_C_NOTES.md)
  - [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md)
  - [`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md)
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md)
  - [`09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md`](../../../09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md)
- **確かめ方**：確認はない（計画の覚え書き）。
- **確かめた者**：なし
- **言える範囲**：旧研究の手書きの文書をどう直すつもりだったかの設計。実施されたのは、手順書 v1.4 の草稿のうち、修正の結果に依存しない部分のコミット（60e720f）だけである。
- **関係する第2回の指摘**：REC-1、REC-3、REC-7、REP-10、REP-15、REP-17、RED-1、RED-2、RED-3、RED-7、RED-8、RED-11、NUM-1、NUM-10
- **第2回の指摘の影響**：この覚え書きは、上の指摘への対応の案である。手順書 v1.4 の草稿を除き、手書きの文書は 43ba5d7 のままで、指摘は未反映のまま残っている。全体の再生成は行われていない。
- **今の時点で言ってよいこと**：予定の一覧として読める。DERIVATIONS.md、06_OPEN_ISSUES/README.md、INDEPENDENT_REVIEW.md、research_code/README.md は改訂されていない。手順書は v1.4 の草稿の一部だけがコミットされている（改訂履歴に 1.4 の行があり、P7 の語彙の節は書き換え済み。P8 の裏付けの規則の本文は v1.3 のまま）。
- **使ってはいけない記述**：
  - 覚え書きの試算値（資材の初期据付が規模 S で A5 の 41.1％・ホールライフ合計の 0.096％、A13-04 の上乗せの扱いで B4 が +0.54％・B3 が +3.93％）を確定値として引用すること（「測り直す」と注記されている）
  - 手順書の改訂履歴 1.4 の行の「…を定めた」を、コードと記録がそうなっているという意味で引用すること（対応する実装は、作業ツリーから取り除かれたか、未着手）
  - 再生成の順序を、実行してよい手順として読むこと（実行は旧研究の再開に当たる）
- **新研究での再利用**：候補（ルート A・C）
  - 使い道：旧研究の手書きの文書を読むときに、どの記述が改訂の予定だったかを知る対照として使う。
  - 条件・注意：実行しない。旧研究の文書は書き換えない。
- **分類の根拠**：
  - [`materials/interrupted_fix/specs/STAGE_C_NOTES.md`](../materials/interrupted_fix/specs/STAGE_C_NOTES.md):46-58（手書きの文書）、60-63（再生成の順序）
  - [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md):12（改訂履歴 1.4 の行）、183-194（P7 の語彙は書き換え済み）、211（P8 の裏付けの規則は「統合モデル自身の数えた演算回数」のまま）
  - [`STOP_STATUS.md`](../STOP_STATUS.md):52-62（段階ごとの状態）、82-87（60e720f は手順書 v1.4 の草稿。作業途中と明記）
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

<a id="ck-r7-32"></a>

## CK-R7-32　中断した修正（65ff124）の基準計算・閉形式：定義が変わった未検証の版

- **区分**：2　暫定・未検証成果
- **内容**：第2回の指摘を反映する作業の途中で止まった作業ツリーの記録。a1 段階（基準計算の定義、時間の厳密な判定、不正値の扱い、完全性の印）は作業担当が完了を報告したが、独立の検査を受けていない。この版では基準計算そのもの（base.py、単位の 3 モジュール）、閉形式、台帳の定義文と依存が書き換わっている。
- **所在**：
  - [`materials/interrupted_fix/working_tree_at_stop_65ff124.patch`](../materials/interrupted_fix/working_tree_at_stop_65ff124.patch)
  - [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json)
  - [`materials/interrupted_fix/specs/SPEC_A1.md`](../materials/interrupted_fix/specs/SPEC_A1.md)
  - [`STOP_STATUS.md`](../STOP_STATUS.md)
- **確かめ方**：作業担当の自己申告だけ（A1_REPORT.json の how_checked に、反証スクリプトの再実行結果や追加したテスト名が書かれている）。停止の記録は、中断時点の Python ファイルが構文として読めることだけを確認し、試験は実行していないと述べている。
- **確かめた者**：中断した修正の自己申告
- **言える範囲**：コミット 65ff124 と保存したパッチにだけ在り、作業ツリーからは取り除かれている（0db5c77）。a2 段階（統合モデルの再構成）の編集は途中のものが同じコミットに混ざっている。
- **関係する第2回の指摘**：NUM-1、NUM-2、NUM-3、NUM-4、NUM-5、NUM-6、NUM-7、NUM-8、NUM-9、NUM-10、NUM-11、RED-1、RED-2、RED-3、RED-4、RED-5、RED-6、RED-7、RED-8、RED-9、RED-10
- **第2回の指摘の影響**：この版は第2回の指摘への対応として書かれたもので、自己申告では NUM-1〜NUM-9、NUM-11、RED-1、RED-2、RED-4〜RED-6、RED-9、RED-10 を FIXED、NUM-10、RED-3、RED-7、RED-8 を PARTLY_FIXED としている（R7 が読んだのは報告の RED-10 まで）。検証されていない。
- **今の時点で言ってよいこと**：在ること、変更の規模（23 ファイル、7,811 行の追加と 1,364 行の削除。基準計算 base.py 332 行、units_b.py 175 行、units_c_sum.py 248 行、units_pre_a.py 142 行、closed_forms.py 211 行、units.json 129 行）、自己申告の内容。それ以上は言えない。
- **使ってはいけない記述**：
  - A1_REPORT の「FIXED」を修正済みの事実として使うこと
  - この版の基準計算を「基準計算」として、コミット済みの版の測定値（681 シナリオ、近似の誤差）と組み合わせること（定義が違う：自己申告では、時間の判定が整数の厳密な算術になり、不正値は除外して数えられ、完全性の印が依存の閉包に従う）
- **新研究での再利用**：候補（ルート B・C）
  - 使い道：基準計算の穴（CK-R7-19、CK-R7-20）をどう埋めようとしたかの設計の記録として読む。新研究が穴のある入力範囲を扱う場合の参考になる。
  - 条件・注意：設計の記録として読むだけにする。この版を使うことは基準計算の差し替えに当たるので、使わない（HANDOVER.md 4.1・4.2）。a2 の途中の編集（engine.py など）が同じコミットに含まれる。
- **分類の根拠**：
  - [`STOP_STATUS.md`](../STOP_STATUS.md):50-62（段階ごとの状態）、84-92（コミットの説明と、取り除いた理由）、96-99（実行していないこと）
  - git show --stat 65ff124（R7 が読み取り専用で確認：23 files changed, 7811 insertions(+), 1364 deletions(-)）
  - [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json): files_changed（15 件）、findings[].status／what／how_checked
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））
- **停止後の点検による訂正**：点検の指摘 C1-02 により、上の記述の一部を改めた。分類担当の元の記述は `materials/classification/R7.json`、訂正の内容は `materials/classification/overrides.json` にある。

