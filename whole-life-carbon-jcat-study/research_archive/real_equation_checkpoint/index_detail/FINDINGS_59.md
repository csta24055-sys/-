# 第2回の独立検査の指摘 59 件：登録簿と、停止時点の状態

[INDEX.md](../INDEX.md) の 5.2 節の詳細。分類担当（読み取り専用、観点 R6）が、保存した資料を読んで作った。

- 範囲：旧研究（09_APPROX_STUDY、独立概念モデル、架空データ）についての指摘の登録簿。数値はすべて架空データでの測定で、実建物での精度や、ほかの道具との一致を示すものではない。
- 判定の欄：verdict は検証担当（指摘ごとに反証を試みた 2 人目）の判定。REP の 18 件には 2 人目の検証が無いので NOT_SECOND_VERIFIED とした（再現したという記述は BRIEF.md による。保存資料に再実行の出力は無い。）。PARTLY_CONFIRMED の statement は検証担当の訂正後の内容。
- 公開中の版に残るかどうか：09_APPROX_STUDY は、README 冒頭の手書きの追記を除いて 60e720f と同一（git diff --stat 60e720f HEAD）。60e720f と、検査担当が調べた 43ba5d7 との差は 00_POLICY/EVALUATION_PROTOCOL.md だけ（git diff --stat 43ba5d7 60e720f）。したがって 59 件すべてが公開中の版に残る。指摘ごとの committed_check は、該当の行・文言・JSON の値を読み取った結果で、実行はしていない。
- REP の 18 件について：停止前に、主担当（研究の実行担当）が検査担当のスクリプトを再実行して再現した。その出力は保存していないので、保存資料からは確かめられない。
- 指摘の全文と再現の手順は `materials/round2_review/triage/` の 5 ファイルにある。**`materials/round2_review/checker_scripts/` のスクリプトは旧研究のコードを読み込むので、実行しない。**

## 件数

| 分け方 | 件数 |
|---|---|
| 判定 | 反証検査で確認 33、一部確認（訂正つき）8、反証検査なし（REP）18 |
| 検査担当が付けた重さ | 高 3、中 27、低 29 |
| 停止時点の状態 | 中断時の編集で対応（自己申告・未検証） 38、対応しない（文書化のみの予定で未実施） 1、未対応 10、途中で停止 10 |
| 担当する予定だった段階 | C 7、a1 26、a2 9、b2 13、b3 4 |
| 公開中の版（`09_APPROX_STUDY/`） | 59 件とも残っている |

## 状態の決め方

- **中断時の編集で対応（自己申告・未検証）**：段階 a1 または b2 の作業担当が、その指摘のコード・測定の側を FIXED または PARTLY_FIXED と報告し、対応する編集が停止時点の差分（65ff124 の patch）に文字列として見えるもの。試験や測定の結果は報告書の自己申告で、独立の検査は無い。文書・記録・報告書の側（段階 C）の残りは未着手で、remaining_at_stop に書いた。
- **途中で停止**：段階 a2（報告前に停止）に割り当てられていたもの。差分に編集はあるが、完了の報告も受け入れ確認の記録も無い。REP-10 は例外で、手順書の部分だけが 60e720f で先に改訂され、台帳の部分（b3）が未着手のもの。
- **未対応**：段階 b3 または段階 C（どちらも未着手）に割り当てられ、差分に該当の編集が無いもの。
- **対応しない（文書化のみの予定で未実施）**：仕様が、指摘の中心についてコードを変えずに限界として文書に書くだけと決めており、その文書（06_OPEN_ISSUES、段階 C）が書かれていないもの（NUM-10。その一部 (b) だけは a1 がコードを直したと自己申告）。
- **共通**：どの状態でも、公開中の版（09_APPROX_STUDY。60e720f と同じ内容に README 冒頭の手書きの追記を加えたもの）には編集が入っていない。0db5c77 が 65ff124 の編集を作業ツリーから取り除いたためである。

## 指摘のまとまり（8 群）と、新研究で使うときの注意

### 群 1：「どの入力でも基準計算と一致する」は言えない（一致を確かめたのは整った入力の範囲）

- 指摘：[NUM-1](#num-1)、[REC-1](#rec-1)、[NUM-2](#num-2)、[NUM-3](#num-3)、[NUM-4](#num-4)、[NUM-5](#num-5)、[NUM-6](#num-6)、[NUM-7](#num-7)、[NUM-8](#num-8)、[NUM-9](#num-9)、[NUM-10](#num-10)
- 内容：統合モデルと基準計算の一致は、研究の 681 の架空シナリオについては第 2 回の検査でも再現した（下限なし・型と無限大を厳密にした比較で差 0 件、最大 4.77e-13）。成り立たないのは「どの入力でも」「不備のある入力でも同じ値・同じ不備」という一般の文で、周期が倍精度の 1.000000001、検査のない項目の NaN・無限大、値 0 でガス別量のある係数、短い年次表と別の不備の組み合わせ、擬似キーと同名の係数 ID、桁落ちやオーバーフローを起こす値で食い違う。
- 新研究で使うときの注意：統合モデル（K1〜K7）を使うときは「架空データ、独立概念モデル、有限で範囲内の整った入力、研究の生成器が作る範囲で、相対 1e-9 の一致を確認」と限定して書く。B3 の除外年の閉形式は周期 1.000000001 で基準計算と食い違うが、正確な有理数演算では閉形式の側が定義どおりで、基準計算のループが丸めの産物を持つ（検証担当）。新研究は基準計算を変えないので、この値を既知の例外として扱うか比較から外すかを先に決める。65ff124 の修正は基準計算の年の判定そのものを変える未検証の編集なので、検証済みの成果として使わない。

### 群 2：基準計算の定義の穴と、一覧にない取り決め（両方の計算が同じ穴を持つ）

- 指摘：[RED-1](#red-1)、[RED-2](#red-2)、[RED-3](#red-3)、[RED-4](#red-4)、[RED-5](#red-5)、[RED-6](#red-6)、[RED-7](#red-7)、[RED-8](#red-8)、[RED-9](#red-9)、[RED-10](#red-10)、[RED-11](#red-11)、[RED-12](#red-12)、[REP-17](#rep-17)
- 内容：基準計算と統合モデルは互いに一致するが、同じ穴を共有している：一部の段階だけを対象にした境界では上流の除外が complete に出ない（RED-1。例で -55.6％ でも complete True）、負や NaN の年次量・電力係数・係数の値・換算係数がそのまま合計に入る（RED-2）、不正な周期が印なしに「事象なし」になる（RED-3）、SUM-08 が不完全な合計どうしを比べる（RED-5）、欠損の一部が計算全体の例外になる（RED-10）。結果を変える取り決めのうち、資材の初期の据付を数えない（ベンチマーク S で A5 の 41.1％ 相当）、未数量分の上乗せを B3・B4 に含めず B5 に含める、重複した事象年をそれぞれ数える、短い電力係数の表でエラーにする、は 06_OPEN_ISSUES の B 節に載っていない。
- 新研究で使うときの注意：基準計算の値を正として使えるのは、14 段階すべてを含む境界で、入力が有限・範囲内の場合に限る。一部の段階だけの境界では complete = True を「除外なし」の根拠にしない。新研究で基準計算を変えないなら、これらは直さずに、既知の制限・取り決めとして新しい文書に書き写す（B 節は不完全なので、この一覧で補う）。ルート B で式を作り直す場合、B3・B4・B5 での上乗せの扱いと初期の据付の扱いは、定義文ではなく depends_on とコードで確かめる。65ff124 は 50 単位の定義文、結果の鍵、incomplete_units の意味を変える未検証の編集で、採用すると 43ba5d7 の測定・記録・報告書と対応しなくなる。

### 群 3：検証が覆っている範囲と、検証の道具の限界

- 指摘：[NUM-11](#num-11)、[REP-16](#rep-16)、[REC-6](#rec-6)、[REP-15](#rep-15)
- 内容：一致の比較には README に書かれていない絶対下限（1e-9×|SUM-03|）があり、無限大と bool の扱いが緩かった（NUM-11。681 シナリオでは隠れていた差は無かった）。評価期間を変えた照合は、70 単位のうち 22 単位、基準案との比較なし、64 の小さなシナリオだけである（REP-16）。年次量の閉形式は、その単位自身の出力ではなく B6-03・B7-04・B2-01・X-11 と合計を通じてだけ検証されている（REC-6）。改訂後の版に対する独立の検査はこの第 2 回が初めてで、その結果は 09_APPROX_STUDY の中に記録されていない（REP-15）。
- 新研究で使うときの注意：「7,406,182 個の値が一致」「172,404 個の値が一致」は、上の範囲の中の事実として引用する。1 回の合算から別の評価期間を計算する仕組みを新研究で使う場合、SUM-06・SUM-07・X-07・B4-01・SUM-08 は旧研究では照合していないので、未検証として扱う。閉形式の正しさの根拠に、B6-02・B7-01〜03・B6-01 の記録が引く値の一致を使わない。04_VERIFICATION/INDEPENDENT_REVIEW.md は第 1 回だけの記録として読み、第 2 回は research_archive の triage を見る。

### 群 4：「66 単位が 7 つの統合モデルに」「70 → 11」の数え方

- 指摘：[REC-2](#rec-2)、[REP-4](#rep-4)、[REC-7](#rec-7)、[REP-9](#rep-9)
- 内容：統合の所属は、研究自身の基準（共有の表から読むか、共有の関数で求める）に照らすと、66 単位のうち少なくとも X-13・B1-01・SYS-03 が満たさず、A13-05 は解釈次第、QA-03 は別のモデル、A5-01・B6-04 は形式的である（REC-2。裏付けられるのは約 62〜63 単位）。K5 の SUM-04〜08 は基準計算と同じ別々の式のままで、66 単位のうち 14 単位は計算が何も変わっていない（REP-4）。記録の題と、「検査の 4 単位」「3 単位だけ」の記述にも食い違いがある（REC-7、REP-9）。
- 新研究で使うときの注意：ルート A・C で統合モデルを出発点にするとき、「66」「7」「70 → 11」を検証済みの数として引用しない。検査担当が所属を確かめた単位（表の読み出し、回数・重み・モーメント・充填サイクルの共有関数、pick、_within から読む 58 単位）と争いのある 8 単位（A13-05、X-13、B1-01、SYS-03、QA-03、B6-04、X-07、A5-01。検証担当は X-07 を行別の出力では擁護できるとした）を分けて扱う。a2 の途中の出力（故障注入で A13-05・SYS-03・X-13 が反応しない）は未検証で、しかも a2 が改造した後のコード（B1 の機器の表、indicator 関数）についての測定なので、公開中のコードの所属の証拠にはならない。

### 群 5：仕組みの確認（演算回数の計数）と SUCCESS 記録の裏付け

- 指摘：[REC-3](#rec-3)、[REC-4](#rec-4)、[REC-5](#rec-5)、[REP-3](#rep-3)、[REC-9](#rec-9)、[REP-12](#rep-12)
- 内容：記録が「仕組みは計数で確認した」と言う計数器は、決まった位置に置いた集計で失敗し得ず（REC-4、REP-12）、「組ごとに 1 回だけ解決」は行ごとの換算を持つ行では成り立たない（REC-3）。SUCCESS 118 件のうち 3 つの裏付けが揃うのは 96 件で、注記の「なければ生成が失敗する」は事実と違う（REC-5、REP-3）。「乗算 3373 回」「520 回」は表の項目数・行数であって、乗算の数ではない（REC-9、REP-12）。
- 新研究で使うときの注意：記録（03_MODELS/records/units.json）の verification = VERIFIED_ANALYTIC_AND_SYNTHETIC を、そのまま「検証済み」と読まない。使ってよい核は、検査担当が外から測って確かめた狭い事実である：合計のみの出力では、資材・設備の行を 1 回だけ読み、行ごとに係数の値を掛けず、周期的な更新年の一覧を作らない（架空の 1 シナリオ、43ba5d7 のコード）。計算量の議論に 520・3373・299・8 を使うときは、何を数えた値かを triage/records.md で確かめる。演算の回数には行数に比例する部分がある（規模 L で解決 5657 回のうち 5183 回が行ごと）。

### 群 6：近似検証の測定の定義（基準量、合計への影響、標本内のパラメータ）

- 指摘：[APP-1](#app-1)、[APP-2](#app-2)、[APP-3](#app-3)、[APP-4](#app-4)、[APP-5](#app-5)、[APP-6](#app-6)、[APP-7](#app-7)、[APP-8](#app-8)、[APP-9](#app-9)
- 内容：近似候補の公表した統計は、検査担当が再実装で再現した（確認できなかった候補は triage/approx.md の COULD NOT CHECK にある）。問題は、何を測った値かの定義にある：「B6 段階」は B6-03（B6＋B2）で、B2 段階では AP-09c が 2％ を超える（APP-2）。「合計への影響」は下流への波及を含まない（APP-3）。AP-18a〜c と AP-19a は評価する建物自身の行から作ったパラメータによる最良の場合で、別の建物のパラメータでは AP-18b が -41％〜+337％ になる（APP-9）。AP-05 は題と違う変種を測っている（APP-6）。不採用・保留の結論そのものは、どの指摘でも変わっていない。
- 新研究で使うときの注意：candidates.json と approximation_study.json の数値を新研究で比較の基準にするときは、(1) 電力の候補は B6-03 に対する誤差であること、(2) total_error は局所の差を建物合計で割った値であること、(3) AP-17・AP-18a〜c・AP-19a は標本内の最良値で入力の削減の証拠ではないこと、を付記する。within_stage_target = true の AP-09c は B2 段階では偽である。APP-1 の安全側の候補も、母集団では 2％ 以内だが寿命の構成次第で +3.3％ になるので、「目標を満たす近似」として扱わない。b2 が作り直した測定（b2_output/approximation_study_UNVERIFIED.json）は自己申告だけで、a1 が変えた基準計算の上で走っているので、検証済みの値として使わない（b2 の報告は、旧来の 3936 個の値が名前を変えて同じ値のまま残ると述べている）。

### 群 7：近似の段階（M3〜M6）の記録の範囲と、進捗の件数

- 指摘：[REP-5](#rep-5)、[REP-6](#rep-6)、[REC-8](#rec-8)、[REP-14](#rep-14)、[REP-2](#rep-2)、[REP-13](#rep-13)
- 内容：近似の段階 280 単位×段階のうち 204 は測定なしの NOT_APPLICABLE で、「保留あり」44 単位のうち 21 単位は建物水準の代理モデル AP-15 だけによる（REP-5）。近似候補について測ったのは誤差だけで、時間・メモリ・命令数・入力数は測っておらず、「厳密な閉形式が同じ手間」は論拠にとどまる（REP-6）。NOT_APPLICABLE の定型の理由文に事実と違うものがあり（REC-8、REP-14）、評価者の提案との対照は手順書と違う基準で集計され（REP-2）、候補と単位の対応が 2 つのファイルで 7 候補食い違う（REP-13）。
- 新研究で使うときの注意：進捗台帳の「検証完了」「保留 44 単位」を、単位ごとに近似を調べた結果として読まない：単位固有の M4 候補があるのは 13 単位である。「旧研究は近似できないと結論した」と引用してよいのは、測定のある不採用 16 候補だけで、NOT_APPLICABLE（226 記録）は論拠であって結果ではない。変換の種類を減らす代わりに式が複雑になってよいという新しい方針の下では、「同じ手間なので近似の利点なし」という不採用の理由は前提が違うので、そのまま引き継がない（b2 の自己申告では、AP-04 は 1 行あたり 14 命令対 112 命令で、この理由を支持しない。未検証）。年次表で与えた年次量の近似は、公開中の版では何も測っていない。

### 群 8：台帳・入力項目・報告書の数値と文言の誤り

- 指摘：[REP-1](#rep-1)、[REP-7](#rep-7)、[REP-8](#rep-8)、[REP-10](#rep-10)、[REP-11](#rep-11)、[REP-18](#rep-18)
- 内容：報告書の「記録用の入力は 0 項目」は誤りで、仕様 124 項目のうち 47 項目はどの計算にも読まれない（REP-1）。台帳の各単位の入力一覧は申告であって、基準計算が実際に読む入力（仕様 77＋追加 56）と合わない（REP-7）。構造別の件数（29・11 は正しくは 30・10）、順位付けの和集合の書き方、シート族の対応状況の名札、A13-04 の「実装しない」という注記が、古いか不整合である（REP-8、REP-11、REP-18、REP-10）。
- 新研究で使うときの注意：方程式のグループや入力の依存関係を新研究で分類するとき、01_LEDGER/units.json の inputs と n_inputs を依存関係の事実として使わない。実測は 04_VERIFICATION/input_usage.json にあるが単位別ではなく、単位別の実測は旧研究に無い（b3 は未着手）。depends_on・feeds と定義文は、基準計算の登録簿・説明文と一致することを第 2 回の検査が確かめている（70 単位で差 0）。ただし a1 の自己申告（未検証）では、公開中の X-07 は depends_on に無い B2-01 を読んでいる。手順書 v1.4 の草稿（60e720f）は、台帳にまだ無い欄（inputs_read_by_reference）と、公開中のコードに入っていない規則（正確な有理数演算、故障注入による所属の確認）を「定めた」と書いているので、現状の説明として読まない。A13-04 は基準計算に実装済みである（本研究の独立の設計）。

## 指摘ごとの記録

<a id="num-1"></a>

### NUM-1

- **重さ／判定**：高／反証検査で確認
- **内容**：更新周期（資材の更新周期、設備の耐用年数）が倍精度の値 1.000000001 のとき、統合モデルの修繕（B3-01）の閉形式は「周期 1 年以上なら事象ごとに年が違う」と仮定するが、基準計算のループは複数の事象を同じ年に置くため、B3-01 が最大約 92％、SUM-03 が約 0.18％ 食い違う（T=60、全行がこの周期の例）。検証担当の補足：正確な有理数演算では閉形式の側が書かれた定義どおりで、基準計算の値が丸めの産物である。約 150 万組の走査で食い違ったのはこの 1 値だけ。
- **影響する成果**：統合モデルの閉形式（research_code/fastcalc/closed_forms.py skip_weight_periodic）、基準計算の年の判定（research_code/refcalc/base.py）、導出 D3（03_MODELS/DERIVATIONS.md）、記録 EX-B3-01-M1、「どの入力でも一致」の記述（README、04_VERIFICATION/README）、期間スイープ（engine.sweep）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/numeric/`](../materials/round2_review/checker_scripts/numeric) の repro_findings.py、cfbrute.py、cfbrute2.py、t9.py、fuzz1.py ／ 検証担当：[`materials/round2_review/checker_scripts/numeric_verify/`](../materials/round2_review/checker_scripts/numeric_verify) の v1.py、v6.py（repro_findings.py は NUM-1 の節）
- **担当する予定だった段階**：a1（ほかに C）
- **予定していた対応**：時間の判定（期間の内側か、どの年か、n 回目の事象 = n×周期）を、与えられた倍精度値に対する正確な整数（有理数）演算に改め、基準計算と閉形式を同じ規則にする（SPEC_A1 項目 1〜3）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[NUM-1] = FIXED（修正後は B3-01 が基準 19107.604293677847／統合 19107.60429367785 と自己申告）。[`materials/interrupted_fix/working_tree_at_stop_65ff124.patch`](../materials/interrupted_fix/working_tree_at_stop_65ff124.patch) に refcalc/base.py と fastcalc/closed_forms.py の as_integer_ratio、tests/test_closed_forms.py と bench/mutations.py の 1.000000001、synth/population.py の life_at_year_tolerance の追加行がある（文字列の有無だけを確認。実行していない）。
- **停止時点で残っていた作業**：導出 D3 と記録 EX-B3-01-* の改訂（段階 C）は未着手。独立の検査（反証検査の反復）は未着手。
- **公開中の版**：残っている。fastcalc/closed_forms.py 62 行に 'every event has its own year'、3 行に 'All of them are exact' が残る。03_MODELS/DERIVATIONS.md 67 行に「事象ごとに年が違い」が残る。

<a id="num-2"></a>

### NUM-2

- **重さ／判定**：中／反証検査で確認
- **内容**：範囲の検査が無い入力（年次量の記述子と表、電力係数の記述子・表・施工時の値、係数の値、換算係数）に NaN・無限大を入れると、基準計算と統合モデルが食い違う（数値の葉を 1 つずつ壊した 3461 件のうち 212 件：片方だけ例外 5 件、値や QA-01 の合否の違い 207 件）。検証担当の補足：36 種類の壊し方についての README の文は偽ではなく、裏付けが無いのは「不備のある入力でも同じ値を返し同じ不備を報告する」という一般の文である。
- **影響する成果**：統合モデル（closed_forms.py grid_segments、engine.py の QA-01 と B5）、基準計算（refcalc/base.py、units_c_sum.py）、壊し方の一覧（bench/mutations.py）、README と 04_VERIFICATION/README の「不備のある入力でも一致」の文
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/numeric/`](../materials/round2_review/checker_scripts/numeric) の repro_findings.py、t7.py、t7.out、t6.py ／ 検証担当：[`materials/round2_review/checker_scripts/numeric_verify/`](../materials/round2_review/checker_scripts/numeric_verify) の v2.py、v3.py、t7_rerun.out
- **担当する予定だった段階**：a1（ほかに C）
- **予定していた対応**：欠損・非有限・範囲外の数値は計算に使わず、それを必要とする最小の対象（行・系列・単位）を除外して数え、依存する合計を不完全とする規則を、両方の計算に同じ述語で入れる（SPEC_A1 一般原則と項目 5〜10）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[NUM-2] = FIXED（総当たり 3461 件：同一 3383、食い違い 0、評価期間の ValueError 12、型の違う入力での同型の例外 66 と自己申告）。patch に refcalc/base.py の factor_values_ok・grid_table_usable、engine.py の _profile_state・_record_ok の追加と、closed_forms.py の旧判定 'd < 0.0 or start < floor' の削除がある。
- **停止時点で残っていた作業**：README の一般の文の訂正と 06_OPEN_ISSUES B-18 の改訂（段階 C）は未着手。型の違う入力（文字列など）は仕様で対象外。
- **公開中の版**：残っている。fastcalc/closed_forms.py 106 行に旧判定 'd < 0.0 or start < floor' が残る。

<a id="num-3"></a>

### NUM-3

- **重さ／判定**：中／反証検査で確認
- **内容**：係数の値が 0 でガス別量が 0 でないレコードを使う行に修繕があると、基準計算は B3 のガス別の行を落とし（e0 == 0.0 の近道）、統合モデルは残すため、X-04 と X-05 が食い違う（設備の例で X-04 +0.51％、X-05 +0.58％。SUM-03 と B3-01 は一致）。
- **影響する成果**：基準計算 B3-01（refcalc/units_b.py 204・225 行）、統合モデル X-04・X-05（engine.py）、壊し方の一覧（bench/mutations.py）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/numeric/`](../materials/round2_review/checker_scripts/numeric) の repro_findings.py、t14.py、fuzz1.py ／ 検証担当：[`materials/round2_review/checker_scripts/numeric_verify/`](../materials/round2_review/checker_scripts/numeric_verify) の v3.py、v4.py
- **担当する予定だった段階**：a1
- **予定していた対応**：基準計算 B3-01 から e0 == 0.0 の近道を除き、製造の結果が求まっていて修繕率が正の行はガス別の行を出す（両方の計算を同じにする。SPEC_A1 項目 14）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[NUM-3] = FIXED（t14.py で食い違う単位なしと自己申告）。patch で refcalc/units_b.py の 'e0 == 0.0' を含む 2 行が削除されている。
- **停止時点で残っていた作業**：独立の検査は未着手。
- **公開中の版**：残っている。refcalc/units_b.py 204 行と 225 行に 'e0 == 0.0' が残る。

<a id="num-4"></a>

### NUM-4

- **重さ／判定**：中／反証検査で確認
- **内容**：評価期間より短い年次表と、その行を使えなくする第 2 の不備（係数なし、単位が /year でない）が重なると、基準計算は IndexError、統合モデルは完全に見える結果を返す。基準案だけにこの不備がある場合も、基準計算は例外、統合モデルは SUM-08 を COMPARED で返す。
- **影響する成果**：基準計算（refcalc/base.py profile_values・check_period、units_b.py）、統合モデル（engine.py _values）、SUM-08、「同じ不備を報告する」の文
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/numeric/`](../materials/round2_review/checker_scripts/numeric) の repro_findings.py、t1.py、t6.py ／ 検証担当：[`materials/round2_review/checker_scripts/numeric_verify/`](../materials/round2_review/checker_scripts/numeric_verify) の v3.py
- **担当する予定だった段階**：a1
- **予定していた対応**：期間より短い、または不正な値を含む年次表の系列は使えないものとして除外して数え、例外にしない。記述子がある場合の短い写しは descriptors_match_tables = False で報告する（SPEC_A1 項目 7。検査担当の案「両方で同じ ValueError」とは違う決定）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[NUM-4] = FIXED（t1.py 46 例で差なしと自己申告）。patch で refcalc/base.py と engine.py の 'shorter than the study period' が削除され、closed_forms.py に table_usable が追加されている。
- **停止時点で残っていた作業**：独立の検査は未着手。
- **公開中の版**：残っている。refcalc/base.py 75 行と fastcalc/engine.py 774 行の check_period は電力係数の表の長さだけを調べる旧コードのまま。

<a id="num-5"></a>

### NUM-5

- **重さ／判定**：中／反証検査で確認
- **内容**：係数 ID が内部の擬似キー 'GRID'・'REFRIGERANT' と同じ文字列のレコードを使うと、統合モデルは擬似行の乗数を上書きし、合計が基準計算と食い違う（例：SUM-03 が -0.79％、A5-01 が基準 5328.16848 に対し統合 12885.209905420988）。基準計算自体も、この入力では X-04 と合計が互いに合わない。
- **影響する成果**：統合モデルの擬似キー（engine.py 35・103・182 行）、基準計算 X-04、入力モデル（係数 ID は自由な文字列）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/numeric/`](../materials/round2_review/checker_scripts/numeric) の repro_findings.py、t12.py ／ 検証担当：[`materials/round2_review/checker_scripts/numeric_verify/`](../materials/round2_review/checker_scripts/numeric_verify) の v3.py
- **担当する予定だった段階**：a1
- **予定していた対応**：買電と冷媒の擬似行を、係数 ID と等しくなり得ないモジュール水準の番兵オブジェクトで識別する（SPEC_A1 項目 14）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[NUM-5] = FIXED。patch に refcalc/base.py の class PseudoLine、engine.py の class PseudoKey の追加と、engine.py の 'GRID = "GRID"' の削除がある。
- **停止時点で残っていた作業**：独立の検査は未着手。
- **公開中の版**：残っている。fastcalc/engine.py 35 行に 'GRID = "GRID"'、103 行に 'fval = {GRID: 1.0, ...' が残る。

<a id="num-6"></a>

### NUM-6

- **重さ／判定**：低／反証検査で確認
- **内容**：複合原単位の行があるとき、ガスの一覧に 'CO2' が 2 回あると統合モデルの X-04 が基準計算より 28％ 大きくなり、'CO2' が無いと統合モデルだけ KeyError になる。複合の行が無ければ差は出ない。
- **影響する成果**：統合モデル X-04・X-05（engine.py 1039〜1051、1073〜1076 行）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/numeric/`](../materials/round2_review/checker_scripts/numeric) の repro_findings.py、t10.py ／ 検証担当：[`materials/round2_review/checker_scripts/numeric_verify/`](../materials/round2_review/checker_scripts/numeric_verify) の v3.py
- **担当する予定だった段階**：a1
- **予定していた対応**：X-04・X-05 はガスの一覧を重複なし（最初の出現、順序は維持）で使い、各レコード自身のガス別量を読む。X-05 は一覧に CO2 を要しない（SPEC_A1 項目 14）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[NUM-6] = FIXED（t10.py 15 例で差なしと自己申告）。patch に refcalc/units_c_sum.py の listed_gases と n_gases_skipped、engine.py の n_gases_skipped の追加がある。
- **停止時点で残っていた作業**：独立の検査は未着手。
- **公開中の版**：残っている。09_APPROX_STUDY は 43ba5d7 のコードと同一（git diff で確認）。該当行の個別の文字列確認はしていない。

<a id="num-7"></a>

### NUM-7

- **重さ／判定**：低／反証検査で確認
- **内容**：電力係数の STEPWISE 記述子で、段の開始位置（from_index）が float 型だと、基準計算は記述子を採用し、統合モデルは TypeError になる。
- **影響する成果**：統合モデル X-06 とその下流（engine.py 933 行、closed_forms.py 119〜131 行）、記述子が整っているかの判定（両方の計算）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/numeric/`](../materials/round2_review/checker_scripts/numeric) の repro_findings.py、t1.py ／ 検証担当：[`materials/round2_review/checker_scripts/numeric_verify/`](../materials/round2_review/checker_scripts/numeric_verify) の v3.py
- **担当する予定だった段階**：a1
- **予定していた対応**：from_index が int 型でない記述子は整っていないものとし、両方の計算で年次表を使う（SPEC_A1 項目 8）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[NUM-7] = FIXED（X-06.source が 3 つの実行とも TABLE と自己申告）。patch の refcalc/base.py と closed_forms.py に from_index と型の判定の追加行がある。
- **停止時点で残っていた作業**：独立の検査は未着手。
- **公開中の版**：残っている。09_APPROX_STUDY は 43ba5d7 のコードと同一（git diff で確認）。該当行の個別の文字列確認はしていない。

<a id="num-8"></a>

### NUM-8

- **重さ／判定**：低／反証検査で確認
- **内容**：単位の名前が文字どおり 'None' のとき、基準計算は目標単位を文字列 'UNIT:None' に整形するため欠損と区別できず、SYS-02 の違反一覧が統合モデルと食い違う（値は一致）。作為的な入力である。
- **影響する成果**：基準計算 SYS-02（refcalc/units_pre_a.py 152 行）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/numeric/`](../materials/round2_review/checker_scripts/numeric) の repro_findings.py ／ 検証担当：[`materials/round2_review/checker_scripts/numeric_verify/`](../materials/round2_review/checker_scripts/numeric_verify) の v3.py
- **担当する予定だった段階**：a1
- **予定していた対応**：基準計算の factor_uses が、目標単位を整形した文字列ではなく値として渡す（SPEC_A1 項目 14）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[NUM-8] = FIXED。patch の refcalc/units_pre_a.py に class UnitOnly の追加と '"None"' を含む行の削除がある。
- **停止時点で残っていた作業**：独立の検査は未着手。
- **公開中の版**：残っている。refcalc/units_pre_a.py 152 行に '"None"' の文字列比較が残る。

<a id="num-9"></a>

### NUM-9

- **重さ／判定**：低／反証検査で確認
- **内容**：呼び出し側が保持する基準案の合計（baseline_totals）を、統合モデルが入力ではない meta.scenario_id で引くため、登録名が違い meta の ID が同じ 2 つの基準案では、2 番目の提案が 1 番目の基準案の合計を使う（削減率が基準 0.302 に対し 0.386）。検証担当の補足：研究自身の生成器が作るデータではこの衝突は起きない。
- **影響する成果**：統合モデル SUM-08 の基準案の再利用（engine.py 1140〜1145 行）、04_VERIFICATION/README の基準案の再利用の記述
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/numeric/`](../materials/round2_review/checker_scripts/numeric) の repro_findings.py、t6.py ／ 検証担当：[`materials/round2_review/checker_scripts/numeric_verify/`](../materials/round2_review/checker_scripts/numeric_verify) の v3.py、v7.py
- **担当する予定だった段階**：a1
- **予定していた対応**：保持する合計は入力の boundary.baseline_scenario で引き、基準案の完全性も一緒に持つ。キーは名前だけで基準案を識別し、基準案・期間・境界を変えると無効になることを説明文に書く（SPEC_A1 項目 13）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[NUM-9] = FIXED。patch で engine.py の 'meta.scenario_id' の行が削除され、baseline_scenario を使う行が追加されている。
- **停止時点で残っていた作業**：独立の検査は未着手。
- **公開中の版**：残っている。fastcalc/engine.py 1140 行に 'meta.scenario_id' が残る。

<a id="num-10"></a>

### NUM-10

- **重さ／判定**：低／反証検査で確認
- **内容**：有限の入力でも、桁落ち・オーバーフロー・極端に小さい値では、研究自身の比較規則の下で 1e-9 を超える差が出る（(a) 施設管理比率 1.0 かつ燃料を 1e-7 倍、(b) T = 1.000000001 で基礎 0 の電力、(c) 基準案が 1 行だけ 1e-8 違う、(d) 数量 1.2e308、(e) 漏洩率 1−1e-8）。通常の大きさの入力（研究の 681 シナリオを下限なしで比べ直したもの）では 1e-9 を超える差は 0 件で、条件数の限界であって通常の入力での誤りではない。
- **影響する成果**：統合モデルの閉形式（closed_forms.py segment_moments）、基準計算の B6 = B6-03 − B2-01 の桁落ち、06_OPEN_ISSUES D-4（一致の限界の記述）、「許容差は相対 1e-09、不一致なし」を全入力の文として読むこと
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/numeric/`](../materials/round2_review/checker_scripts/numeric) の repro_findings.py、t4.py、t9.py、t16.py ／ 検証担当：[`materials/round2_review/checker_scripts/numeric_verify/`](../materials/round2_review/checker_scripts/numeric_verify) の v4.py、v5.py
- **担当する予定だった段階**：a1（ほかに C）
- **予定していた対応**：(b) だけコードを直し（年の和に端数年の分を足す形にする。SPEC_A1 項目 16）、(a)(c)(d)(e) はコードを変えずに一致の限界として 06_OPEN_ISSUES D-3・D-4 に書く（SPEC_A1「What NOT to change」、STAGE_C_NOTES）。
- **停止時点の状態**：対応しない（文書化のみの予定で未実施）
- **作業担当の自己申告**：PARTLY_FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[NUM-10] = PARTLY_FIXED：(b) は修正（patch の closed_forms.py に 'wl * last' の追加と '(1.0 - wl)' の削除、仕様外の変更として refrigerant_fractions の残量を exp と log1p で計算）、(a)(c)(d)(e) は「コード変更なし、まだ食い違う」と自己申告。open_problems に「乱数試験 6000 件中 2 件が (e) の類で食い違い、目標 0 に届かず」とある。06_OPEN_ISSUES/README.md は patch に含まれない。
- **停止時点で残っていた作業**：限界の文書化（06_OPEN_ISSUES D-3・D-4、段階 C）は未着手。(b) の修正は未検証。
- **公開中の版**：残っている。09_APPROX_STUDY は 43ba5d7 のコードと同一。06_OPEN_ISSUES/README.md に第 2 回の指摘の記載は無い。

<a id="num-11"></a>

### NUM-11

- **重さ／判定**：低／反証検査で確認
- **内容**：検証に使った比較は、基準側が ±inf なら候補が何でも一致とし、bool と int を同じとみなし、全ての葉に 1e-9×|SUM-03| の絶対下限（kgCO2e）を無次元の葉にも当て、合計のみの出力では余分な葉を調べない。下限は README に書かれていない。ただし 681 シナリオを下限なし・型と無限大を厳密にして比べ直した結果は差 0 件で、実際に隠れていた差は無かった。
- **影響する成果**：比較関数（research_code/common/compare.py 29〜36、76〜87 行）、検証スクリプト（bench/verify_unified.py 115〜130 行）、04_VERIFICATION/README 1 節の許容差の説明、04_VERIFICATION/unified_model_exactness.json
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/numeric/`](../materials/round2_review/checker_scripts/numeric) の repro_findings.py、t15.py、t8.py、t16.py ／ 検証担当：[`materials/round2_review/checker_scripts/numeric_verify/`](../materials/round2_review/checker_scripts/numeric_verify) の v4.py、v5.py
- **担当する予定だった段階**：a1（ほかに C）
- **予定していた対応**：比較関数で無限大と bool を厳密に扱い、一致の検証は下限 0（純粋に相対）で行い、合計のみの出力の余分な葉を不一致として扱う（SPEC_A1 項目 16）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[NUM-11] = FIXED（下限 0 で 1490 シナリオ all_exact True、最大 4.775e-13 と自己申告）。patch の common/compare.py に isinf と bool の判定、bench/verify_unified.py に EXACT_FLOOR = 0.0 の追加がある。
- **停止時点で残っていた作業**：一致検証の JSON の再生成と README の説明の改訂（段階 C）は未着手。
- **公開中の版**：残っている。bench/verify_unified.py 120〜121 行に下限つきの比較が残り、common/compare.py に isinf は無い。04_VERIFICATION/unified_model_exactness.json に下限を示す鍵は無い。

<a id="red-1"></a>

### RED-1

- **重さ／判定**：高／反証検査で確認
- **内容**：対象段階に B3 または B5 を含み、その上流の段階（A1-A3 など）を含まない境界では、上流で除外された行が B3・B5 を黙って小さくしても complete が True のままになる（例：対象 ['B3'] で 98378.05 → 43676.16（-55.6％）、['B5'] で -62.8％、incomplete_units は空）。基準計算と統合モデルは同じ誤った印を返す。検証担当の補足：X-02 の文面はコードどおりで、偽になるのは B-17、base.py、SUM の説明、INDEPENDENT_REVIEW 2.2 の「不完全と示す」であり、14 段階すべてを含む境界では印が立つ。
- **影響する成果**：基準計算の完全性の印（refcalc/units_c_sum.py 240〜250 行 STAGE_UNITS、X-02、SUM-01〜03）、統合モデルの同じ表、06_OPEN_ISSUES B-17、04_VERIFICATION/INDEPENDENT_REVIEW.md 2.2、検証シナリオ（対象段階を一部にしたシナリオは不備なしのものだけ）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/rederive/`](../materials/round2_review/checker_scripts/rederive) の holes1.py、holes5.py、holes6.py ／ 検証担当：[`materials/round2_review/checker_scripts/rederive_verify/`](../materials/round2_review/checker_scripts/rederive_verify) の v1.py、v1.out（holes1.py は H1 の節）
- **担当する予定だった段階**：a1（ほかに C）
- **予定していた対応**：完全性を手書きの表ではなくデータの流れから決める：段階を構成する単位と、その depends_on の推移閉包のどれかが除外を数えたら不完全とする。統合モデルは同じ表を持ち、試験で登録簿の閉包との一致を確かめる。「一部の段階＋上流の不備」のシナリオを検証に加える（SPEC_A1 項目 11）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[RED-1] = FIXED（['B3']・['B5']・['B3','B5'] で complete False、検証に stage_subset_with_defect の 90 シナリオを追加と自己申告）。patch に refcalc/units_c_sum.py の stage_upstream の追加と STAGE_UNITS の削除、engine.py の STAGE_UPSTREAM・B6_UPSTREAM_WITHOUT_B2、bench/verify_unified.py の 'stage_subset_with_defect' がある。
- **停止時点で残っていた作業**：06_OPEN_ISSUES B-17 と INDEPENDENT_REVIEW の記述の改訂（段階 C）は未着手。a1 自身が「閉包の規則は保守的で、既存の不備つきシナリオの incomplete_units は以前より多くの単位を挙げる」と申告。
- **公開中の版**：残っている。refcalc/units_c_sum.py 240 行と 288 行に STAGE_UNITS が残る（B3 は B3-01、B5 は B5-01 だけを見る旧コード）。

<a id="red-2"></a>

### RED-2

- **重さ／判定**：中／反証検査で確認
- **内容**：年次量（ガス、油、地域熱、水、下水、廃棄物）の負や NaN は検査なしで使われ、除外件数も complete も SYS の検査も反応しない（B-18 と INDEPENDENT_REVIEW 2.2 に反する）。電力係数、施工時の電力係数、係数の値、換算係数も検査されず、負・NaN・無限大が complete = True のまま合計に入るが、B-18 はこれらを挙げていないので「一覧にない穴」である（検証担当の訂正）。B6-04 の max(0, …) は単位の定義で、B-18 の例外として明記が要る。
- **影響する成果**：基準計算（refcalc/base.py profile_values・grid_values・convert・lookup、units_b.py、units_pre_a.py a5_01）、統合モデル（同じ挙動）、06_OPEN_ISSUES B-18、04_VERIFICATION/INDEPENDENT_REVIEW.md 2.2
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/rederive/`](../materials/round2_review/checker_scripts/rederive) の holes1.py、holes5.py ／ 検証担当：[`materials/round2_review/checker_scripts/rederive_verify/`](../materials/round2_review/checker_scripts/rederive_verify) の v2.py、v2b.py、v5.py（holes1.py は H2・H3・H5 の節）
- **担当する予定だった段階**：a1（ほかに C）
- **予定していた対応**：年次量、電力係数（系列と施工時の値）、係数の値、ガス別量、換算係数を有限かつ 0 以上（換算は正）と検査し、外れたものは除外して数え、合計を不完全にする。B6-04 の max(0, …) は買電の定義として残し、文面にそう書く（SPEC_A1 項目 5〜8）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[RED-2] = FIXED（負や NaN のガス基礎値で B6-02 n_skipped 1・complete False などと自己申告）。patch に synth/model.py の usable_multiplier、refcalc/base.py の factor_values_ok・grid_table_usable の追加がある。
- **停止時点で残っていた作業**：06_OPEN_ISSUES B-18 の改訂（段階 C）は未着手。a1 は「基準計算が使用のたびに係数レコードを再検査するため、基準計算の命令数が約 1.24 倍になった」と申告しており、負荷の測定値は取り直しが必要なまま。
- **公開中の版**：残っている。09_APPROX_STUDY は 43ba5d7 のコードと同一。06_OPEN_ISSUES B-18 は旧文面のまま。

<a id="red-3"></a>

### RED-3

- **重さ／判定**：中／一部確認（訂正つき）
- **内容**：不正な（負、0、NaN、無限大の）更新周期・耐用年数・建替周期は「事象なし」として扱われ、件数も印も立たず、合計は complete のままになる（例：SUM-03 が -16.1％ で complete True）。この取り決めは B4-01・B4-03 の文面と base.py にはあるが、06_OPEN_ISSUES の B 節と B5-01・B1-02 の文面には無く、NaN・無限大は文面が扱っていない。B-18 自体には反しない（検証担当の訂正）。
- **影響する成果**：基準計算（refcalc/base.py periodic_events、B4-01・B4-03・B5-01・B1-02）、統合モデル（同じ挙動）、06_OPEN_ISSUES B 節、SYS-01（負・NaN・無限大の周期、建替周期を報告しない）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/rederive/`](../materials/round2_review/checker_scripts/rederive) の holes1.py ／ 検証担当：[`materials/round2_review/checker_scripts/rederive_verify/`](../materials/round2_review/checker_scripts/rederive_verify) の v1.py（holes1.py は H8 の節）
- **担当する予定だった段階**：a1（ほかに C）
- **予定していた対応**：None は「更新しない」で数えない。値があって有限の正でない周期は事象なしとした上で数える（B4-01・B4-03 の n_invalid、冷媒機器は B1 の除外件数）。建替の想定が NONE 以外で周期が欠損・不正なら B5-01 を computed False にする（SPEC_A1 項目 4）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：PARTLY_FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[RED-3] = PARTLY_FIXED（コードと B4-01・B4-03・B5-01・B1-02 の文面は変更、B 節への記載は「自分の担当ファイルではない」として未実施）。patch に refcalc/units_b.py と engine.py の n_invalid、refcalc/base.py の invalid_period の追加がある。
- **停止時点で残っていた作業**：06_OPEN_ISSUES B 節への取り決めの記載（段階 C）は未着手。
- **公開中の版**：残っている。refcalc/units_b.py に n_invalid は無い（旧コード）。

<a id="red-4"></a>

### RED-4

- **重さ／判定**：中／反証検査で確認
- **内容**：X-04 の定義文は「ガス別量×GWP の合計＋買電＋冷媒 が段階合計の総和に一致することを確かめる」と言うが、コードは照合の結果を返さず、QA-01 もガス別量と係数の値の食い違いを検出できない（1 つの係数の CO2 量を 3 倍にすると X-04 が段階合計より +3.46％ になるが、全ての検査が ok のまま）。
- **影響する成果**：基準計算 X-04・QA-01（refcalc/units_c_sum.py 322〜352、523〜540 行）、統合モデル（同じ挙動）、台帳 X-04 の定義文
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/rederive/`](../materials/round2_review/checker_scripts/rederive) の holes1.py ／ 検証担当：[`materials/round2_review/checker_scripts/rederive_verify/`](../materials/round2_review/checker_scripts/rederive_verify) の v3.py（holes1.py は H6 の節）
- **担当する予定だった段階**：a1
- **予定していた対応**：X-04 に実際の照合の結果 matches_stage_total を持たせ、QA-01 に検査 (d) を加える（SPEC_A1 項目 14）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[RED-4] = FIXED（CO2 量 3 倍で QA-01 が violations ['gas breakdown total'] と自己申告）。patch の refcalc/units_c_sum.py と engine.py に matches_stage_total、'gas breakdown total' の追加がある。
- **停止時点で残っていた作業**：独立の検査は未着手。
- **公開中の版**：残っている。refcalc/units_c_sum.py に matches_stage_total は無い（旧コード）。

<a id="red-5"></a>

### RED-5

- **重さ／判定**：中／反証検査で確認
- **内容**：SUM-08（基準案との比較）は 2 つの合計が完全かどうかを条件にせず、印も返さないため、不完全な基準案と比べても COMPARED になる（例：基準案の上位 4 行が計算不能だと削減率が 0.2123 → -0.1732 と符号が変わる）。登録のない基準案 ID は「基準案なし」と区別できない。検証担当の補足：SUM-08 の文面どおりの実装で、定義の穴である。
- **影響する成果**：基準計算 SUM-08（refcalc/units_c_sum.py 495〜518 行）、統合モデル SUM-08、台帳 SUM-08 の定義文、06_OPEN_ISSUES B-17（不完全の印が比較に届かない）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/rederive/`](../materials/round2_review/checker_scripts/rederive) の holes4.py、holes3.py ／ 検証担当：[`materials/round2_review/checker_scripts/rederive_verify/`](../materials/round2_review/checker_scripts/rederive_verify) の v3.py（holes3.py は A9 の節）
- **担当する予定だった段階**：a1
- **予定していた対応**：比較の条件に両方の合計が完全であることを加え、状態 BASELINE_NOT_FOUND と INCOMPLETE（delta と saving は None、proposal_complete と baseline_complete を返す）を加える（SPEC_A1 項目 13）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[RED-5] = FIXED。patch の refcalc/units_c_sum.py と engine.py に BASELINE_NOT_FOUND、proposal_complete の追加がある。
- **停止時点で残っていた作業**：独立の検査は未着手。
- **公開中の版**：残っている。refcalc/units_c_sum.py に BASELINE_NOT_FOUND・INCOMPLETE は無い（旧コード）。

<a id="red-6"></a>

### RED-6

- **重さ／判定**：中／反証検査で確認
- **内容**：SYS-01（数値入力の状態の検査）は決まった項目しか見ず、施設管理比率、建替範囲比、建替周期、積載率、運搬距離、経路比率、費用額、年次量、電力係数などの欠損を報告しない。NaN は MISSING にならない。検証担当の補足：拘束する定義文は「欠損（None）は MISSING」でコードはそのとおりであり、「NaN → MISSING」と書くのは台帳の branches 欄（分析担当の分類）なので、後半は台帳の内部の不整合である。
- **影響する成果**：基準計算 SYS-01（refcalc/units_pre_a.py 13〜75 行）、台帳 01_LEDGER/units.json の SYS-01（branches 欄と定義文）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/rederive/`](../materials/round2_review/checker_scripts/rederive) の holes1.py ／ 検証担当：[`materials/round2_review/checker_scripts/rederive_verify/`](../materials/round2_review/checker_scripts/rederive_verify) の v3.py（holes1.py は H7 の節）
- **担当する予定だった段階**：a1
- **予定していた対応**：調べる項目の集合は変えずに文面へ列挙し、一覧外の入力はそれを必要とする単位が件数や computed で報告すると書く。調べる項目の NaN・無限大は NOT_FINITE（違反）として報告し、台帳の branches 欄を手で直す（SPEC_A1 項目 15）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[RED-6] = FIXED。patch の refcalc/units_pre_a.py と 01_LEDGER/units.json に NOT_FINITE の追加行がある。
- **停止時点で残っていた作業**：独立の検査は未着手。
- **公開中の版**：残っている。01_LEDGER/units.json の SYS-01 の branches 欄の先頭は「値が null・空・NaN → MISSING」のまま（JSON を読んで確認）。

<a id="red-7"></a>

### RED-7

- **重さ／判定**：中／反証検査で確認
- **内容**：更新（B4-02）と修繕（B3-01・B3-02）の「行の製造排出」は未数量分の上乗せ（A13-04）を含まず、建替（B5-01）の基礎は含む。B4-02 の文面「A1-A3 の行結果」はどちらにも読め、この違いは 06_OPEN_ISSUES の B 節に無い（標準ベンチマーク S で、上乗せを含めると B4 が +0.542％、B3 が +3.93％）。検証担当の補足：depends_on と A13-04 の文面が読みを決めており、重大度は MEDIUM の下端。
- **影響する成果**：台帳の定義文（B4-02、B3-01、B3-02、B5-01）、06_OPEN_ISSUES B 節、基準計算（refcalc/units_b.py。数値は変えない決定）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/rederive/`](../materials/round2_review/checker_scripts/rederive) の holes3.py ／ 検証担当：[`materials/round2_review/checker_scripts/rederive_verify/`](../materials/round2_review/checker_scripts/rederive_verify) の v3.py（holes3.py は A3 の節）
- **担当する予定だった段階**：a1（ほかに C）
- **予定していた対応**：数値は変えず、B4-02・B3-01・B3-02 の文面に「上乗せ A13-04 を含まない」、B5-01 に「含む」と書き、B 節に大きさ（測り直しのうえ）とともに載せる（SPEC_A1 項目 15、STAGE_C_NOTES）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：PARTLY_FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[RED-7] = PARTLY_FIXED（単位の文面は変更、数値は不変、B 節への記載は未実施）。patch の refcalc/units_b.py に 'A13-04' を含む追加行が 4 行ある。
- **停止時点で残っていた作業**：06_OPEN_ISSUES B 節への記載と大きさの測り直し（段階 C）は未着手。
- **公開中の版**：残っている。06_OPEN_ISSUES/README.md の B 節は B-1〜B-21 のままで、この取り決めの項目は無い（B-22 の文字列なし）。

<a id="red-8"></a>

### RED-8

- **重さ／判定**：中／反証検査で確認
- **内容**：資材の据付係数は更新時（B4）だけに使われ、初期の据付は A5 に計上されないが、B-11 は設備だけを挙げている。標準ベンチマーク S で、計上されない資材の初期据付は 31617.67 kgCO2e（A5 の 41.1％、SUM-03 の 0.096％）に当たり、記載済みの設備分の約 8 倍である。
- **影響する成果**：06_OPEN_ISSUES B-11、台帳 A5-04 の定義文、基準計算（units_b.py material_install_line、units_pre_a.py a5_04。数値は変えない決定）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/rederive/`](../materials/round2_review/checker_scripts/rederive) の holes3.py ／ 検証担当：[`materials/round2_review/checker_scripts/rederive_verify/`](../materials/round2_review/checker_scripts/rederive_verify) の v3.py（holes3.py は A2 の節）
- **担当する予定だった段階**：a1（ほかに C）
- **予定していた対応**：計算は変えず、A5-04 の文面に「係数による据付は A5 に含めない（更新時だけ）」と書き、B-11 に資材の行と大きさ（測り直しのうえ）を加える（SPEC_A1 項目 15、STAGE_C_NOTES）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：PARTLY_FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[RED-8] = PARTLY_FIXED（A5-04 の文面だけ変更、B-11 への追記は未実施）。patch の refcalc/units_pre_a.py に「据付」を含む追加行がある。
- **停止時点で残っていた作業**：06_OPEN_ISSUES B-11 への資材の行の追記（段階 C）は未着手。指摘の中心（B 節に載っていないこと）は手当てされていない。
- **公開中の版**：残っている。06_OPEN_ISSUES/README.md の B-11 は「設備機器の初期の搬入・据付は計上しない」だけで、資材の記載は無い。

<a id="red-9"></a>

### RED-9

- **重さ／判定**：低／一部確認（訂正つき）
- **内容**：B4-02 の式の文は設備の更新ごとの搬入・据付を書いておらず、搬入・据付係数に必要な段階（A4・A5）はどの単位の文面にも無い（挙動自体は B-11 に書かれ、B4-02 の最後の文が示唆している）。B1-02 の式は結果が kgCO2e なのに「×GWP」を欠く。文言だけの問題で、研究の数値は変わらない（検証担当の訂正）。
- **影響する成果**：台帳の定義文（B4-02、B1-02）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/rederive/`](../materials/round2_review/checker_scripts/rederive) の holes3.py ／ 検証担当：[`materials/round2_review/checker_scripts/rederive_verify/`](../materials/round2_review/checker_scripts/rederive_verify) の v3.py（holes3.py は A3 の後半と A4 の節）
- **担当する予定だった段階**：a1
- **予定していた対応**：B4-02 の文面に設備の搬入（A4 段階の係数）と据付（A5 段階の係数）、資材の据付係数の段階を、B1-02 に「×GWP」を書き足す。数値は変えない（SPEC_A1 項目 15）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[RED-9] = FIXED（文面だけ、数値は不変と自己申告）。patch の refcalc/units_b.py に GWP を含む追加行があり、01_LEDGER/units.json の定義文も同期されている（74 行追加、55 行削除）。
- **停止時点で残っていた作業**：独立の検査は未着手。
- **公開中の版**：残っている。09_APPROX_STUDY の定義文は 43ba5d7 と同一。

<a id="red-10"></a>

### RED-10

- **重さ／判定**：低／反証検査で確認
- **内容**：欠損・NaN の一部が、除外して数えられずに計算全体の例外になるか、検査をすり抜ける：経路比率 None で C-05 が TypeError、経路比率 NaN は C-05 が ok、施工時の電力係数 None・年次表の中の None・係数の値 None で TypeError、期間より短い年次量の表で IndexError。検証担当が同種の 3 か所（概要数量 None、用途別面積の None、明示の事象一覧の中の None）を追加で確認した。基準計算と統合モデルは同じ型の例外を出す。
- **影響する成果**：基準計算（units_c_sum.py c_05、base.py check_period・profile_values・grid_values、units_pre_a.py a5_01・x_17・sys_04）、統合モデル（同じ挙動）、base.py の取り決め（None は MISSING、除外して数える）、06_OPEN_ISSUES B-21（エラーは不正な評価期間だけ）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/rederive/`](../materials/round2_review/checker_scripts/rederive) の holes1.py ／ 検証担当：[`materials/round2_review/checker_scripts/rederive_verify/`](../materials/round2_review/checker_scripts/rederive_verify) の v4.py（holes1.py は H3・H4・H5・H9 の節）
- **担当する予定だった段階**：a1
- **予定していた対応**：これらを例外にせず、一般原則どおり除外して数える（C-05：不正な比率は違反、不正な質量は n_mass_unchecked。SYS-04：不正な面積は INVALID。X-17：n_classes_skipped。X-13：n_skipped）。例外になるのは不正な評価期間だけにする（SPEC_A1 項目 9）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[RED-10] = FIXED。patch の refcalc/units_pre_a.py に n_classes_skipped、units_c_sum.py に n_mass_unchecked の追加がある。a1 は「レコードや一覧を置くべき欄に数値を入れた型違いの入力は今も例外（66 件、対象外）」と申告。
- **停止時点で残っていた作業**：独立の検査は未着手。
- **公開中の版**：残っている。refcalc/units_pre_a.py に n_classes_skipped は無い（旧コード）。

<a id="red-11"></a>

### RED-11

- **重さ／判定**：低／一部確認（訂正つき）
- **内容**：検査と計算が実際に食い違うのは 1 点：設備の廃棄係数が無い行を SYS-03 は任意の欄として通すが、X-14 は行を除外し合計が不完全になる。ほかは文言と一覧にない取り決めである（SYS-02 の「すべての箇所」は EPD 係数を含まないが、これは B-14 の取り決めで X-15 が報告する。明示の事象一覧の重複した年はそれぞれ数え、QA-02 は警告しない。比率 0 で係数なしの経路も合計を不完全にするが、これは B-17 どおり）：検証担当の訂正。
- **影響する成果**：基準計算（units_pre_a.py sys_02・sys_03、synth/model.py factor_references、units_c_sum.py x_14・qa_02）、台帳の定義文（SYS-02、C3-01）、06_OPEN_ISSUES B 節
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/rederive/`](../materials/round2_review/checker_scripts/rederive) の holes3.py ／ 検証担当：[`materials/round2_review/checker_scripts/rederive_verify/`](../materials/round2_review/checker_scripts/rederive_verify) の v4.py（holes3.py は A6・A7・A8 の節）
- **担当する予定だった段階**：a1（ほかに C）
- **予定していた対応**：SYS-03 が、廃棄係数のない設備の行を係数のない経路と同じように報告する。SYS-02 の文面に EPD 係数は調べないと書く。重複はそれぞれ数え QA-02 の warnings に載せる。比率 0 の経路の扱いは変えない（SPEC_A1 項目 2・15、「What NOT to change」）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：PARTLY_FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[RED-11] = PARTLY_FIXED（(2) 修正、(1) 文面、(4) warnings、(3) は決定により維持、B 節への記載は未実施）。patch の synth/model.py に eol_factor_id、units_c_sum.py に warnings の追加行がある。
- **停止時点で残っていた作業**：06_OPEN_ISSUES B 節への取り決め（重複年、比率 0 の経路）の記載（段階 C）は未着手。
- **公開中の版**：残っている。09_APPROX_STUDY は 43ba5d7 のコードと同一。

<a id="red-12"></a>

### RED-12

- **重さ／判定**：低／反証検査で確認
- **内容**：定義文が書いていない出力・分岐と、文面とコードの小さな違いが 7 点ある：(1) X-02 の by_stage_all と X-05 の by_stage_co2 が対象外の段階も返す、(2) B6-01 が計算されないとき B2-01 が computed True・値 0.0 を返す、(3) QA-01 の絶対下限（1e-9×max(|値|, 1)）が文面に無く、検査 (b)(c) は構造上失敗しない、(4) SUM-05 の「評価期間 ≤ 0」の分岐は到達しない、(5) X-17 は概要数量 0 の分類を落とし、文面の恒等式に反する、(6) X-13 は不正な行に None を返し件数が無い、(7) 正の周期に下限が無い（周期 1e-4、T=60 で 1 行が 599999 事象）。
- **影響する成果**：基準計算（units_c_sum.py x_02・x_05・qa_01・sum_05、units_b.py b2_01、units_pre_a.py x_17・x_13）、台帳の定義文（X-02、X-05、QA-01、SUM-05、X-17）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/rederive/`](../materials/round2_review/checker_scripts/rederive) の driver.py、holes2.py、holes3.py、holes5.py ／ 検証担当：[`materials/round2_review/checker_scripts/rederive_verify/`](../materials/round2_review/checker_scripts/rederive_verify) の v4.py
- **担当する予定だった段階**：a1
- **予定していた対応**：(1) 文面に by_stage_all と by_stage_co2 を書く、(2) B2-01 を computed False にする、(3) QA-01 の文面に下限を書く、(4) SUM-05 の分岐と文を除く、(5) X-17 は正の概要数量を持つ分類だけの恒等式とし除外を数える、(6) X-13 に n_skipped を加える（SPEC_A1 項目 9・12・15）。(7) は仕様に入っていない。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：PARTLY_FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[RED-12] = PARTLY_FIXED（(1)〜(6) は変更、(7) と QA-01 (b)(c) は未対応）。patch の refcalc/units_c_sum.py に by_stage_all を含む追加行、units_pre_a.py に n_skipped の追加がある。a1 は open_problems で「周期 1e-9 年・T=60 では 6e10 事象になり、探索の乱数試験がメモリ不足で止まった」と申告。
- **停止時点で残っていた作業**：(7)（極小の周期での事象数の爆発）と、QA-01 の検査 (b)(c) が失敗し得ないことは、どの段階の仕様にも入っていない。
- **公開中の版**：残っている。09_APPROX_STUDY は 43ba5d7 のコードと同一。04_VERIFICATION/unified_model_exactness.json の units_without_output_in_totals_mode は ['B4-03', 'X-13'] のまま。

<a id="rec-1"></a>

### REC-1

- **重さ／判定**：高／反証検査で確認
- **内容**：NUM-1 と同じ問題を記録の側から見た指摘：周期が倍精度の 1.000000001 のとき統合モデルと基準計算が食い違い（全行がこの周期なら B3-01 で最大約 92％、1 行だけなら 2e-6〜2e-3）、「どの入力でも基準計算と同じ結果」、closed_forms.py の「All of them are exact」、導出 D3 の「c ≥ 1 なら事象ごとに年が違う」、B3-01 の SUCCESS 記録は、この入力では成り立たない。検証担当の補足：正確な演算では事象は別々の年に入り、閉形式が数学的に意図どおりの側で、基準計算のループが丸めの産物を持つので、どちらの側を直すかを決める必要がある。
- **影響する成果**：導出 D3（03_MODELS/DERIVATIONS.md）、記録 EX-B3-01-M1・EX-B3-01-M2（03_MODELS/records/units.json）、統合モデルの閉形式（closed_forms.py 58〜71 行）、基準計算の年の判定（refcalc/base.py）、試験（tests/test_closed_forms.py）と小数の端の一覧（bench/mutations.py DECIMAL_BOUNDARIES）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/records/`](../materials/round2_review/checker_scripts/records) の d3_band.py、d3_ulps.py、d3_targets.py、brute_cf.py、d3_band.out、brute_cf.out ／ 検証担当：[`materials/round2_review/checker_scripts/records_verify/`](../materials/round2_review/checker_scripts/records_verify) の v1_d3.py、v1_e2e.py、v1_e2e_b.py、v1_exact.py
- **担当する予定だった段階**：a1（ほかに C）
- **予定していた対応**：基準計算の年の割り当てを丸めに依存しない正確な演算に直し（NUM-1 と同じ修正）、導出 D3 を正確な演算の条件（q = L×c ≥ 1 なら年が別々、という証明つき）で書き直し、記録を再生成する（SPEC_A1 項目 1〜3、STAGE_C_NOTES）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：PARTLY_FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[REC-1] = PARTLY_FIXED（コード側は NUM-1 として修正、DERIVATIONS.md D3 と記録は後段）。patch の該当は NUM-1 と同じ。03_MODELS/DERIVATIONS.md と tools/build_records.py は patch に含まれない。
- **停止時点で残っていた作業**：導出 D3 の書き直しと記録 EX-B3-01-* の再生成（段階 C）は未着手。
- **公開中の版**：残っている。03_MODELS/DERIVATIONS.md 67 行、fastcalc/closed_forms.py 3 行と 62 行に元の記述が残る。tests/test_closed_forms.py に 1.000000001 は無い。

<a id="rec-2"></a>

### REC-2

- **重さ／判定**：中／反証検査で確認
- **内容**：統合に数えた 66 単位のうち、研究自身の基準（値を共有の表から読むか、共有のパラメータ付き関数で求める。同じ走査の中にあるだけでは数えない）を少なくとも X-13、B1-01、SYS-03 の 3 単位が満たさず、A13-05 は「K1 の式の行乗数であること」を所属と認める場合だけ満たす。QA-03 は K7 ではなく K1 に属し、A5-01 と B6-04 は形式的な所属である。裏付けられる見出しは約 62〜63 単位で、M2 の記録を除くと B1-01 は「未検証」、A13-05 と X-13 は「近似不採用」になる。
- **影響する成果**：統合モデルの所属（03_MODELS/models.json の K1・K3・K4・K7）、記録（EX-A13-05-M2、EX-X-13-M2、EX-B1-01-M2、EX-SYS-03-M2、EX-QA-03-M2 など）、進捗台帳の状態（05_DECISIONS）、見出し「66 単位が 7 つの統合モデルに」（README）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/records/`](../materials/round2_review/checker_scripts/records) の instr3.py、instr2.py、ledger_check.py ／ 検証担当：[`materials/round2_review/checker_scripts/records_verify/`](../materials/round2_review/checker_scripts/records_verify) の v2_membership.py、v2_ledger.py、v3_counts.py
- **担当する予定だった段階**：a2（ほかに C）
- **予定していた対応**：安く自然にできる所は共有の構造を実際に作り（K4 の機器ごとの表、K5 の indicator 関数、係数解決のメモ化）、所属の根拠を「共有の表・関数を外から壊すと単位の出力が変わる」という測定（bench/membership_check.py）に置き換える。反応しない単位（A13-05、X-13、SYS-03 を想定）は統合に数えない（SPEC_A2 1・2 節、STAGE_C_NOTES 1）。
- **停止時点の状態**：途中で停止
- **作業担当の自己申告**：報告なし（段階 a2 は報告前に停止）
- **状態の根拠**：[`STOP_STATUS.md`](../STOP_STATUS.md) 1・3 節：a2 は作業の途中で停止、報告なし。patch に新規の bench/membership_check.py（773 行）と tests/test_mechanism_probe.py、engine.py の改造（Aggregate.charges の機器の表、indicator 関数、Resolver）がある。[`materials/interrupted_fix/a2_partial_outputs/membership_check_UNVERIFIED.json`](../materials/interrupted_fix/a2_partial_outputs/membership_check_UNVERIFIED.json) が残っており、claims.not_sensitive_to_any_shared_object_of_their_model は ['A13-05 (K1)', 'SYS-03 (K7)', 'X-13 (K1)']（未検証、a2 が改造した後のコードについての出力）。
- **停止時点で残っていた作業**：a2 の受け入れ確認（試験、縮小した一致検証、命令数の前後比較）の記録が無い。models.json、記録、進捗台帳、見出しの改訂（段階 C）は未着手。
- **公開中の版**：残っている。03_MODELS/models.json は K1〜K7 に 26・9・10・4・8・3・6 = 66 単位を数えたまま（JSON を読んで確認）。README 25 行に「66 単位が 7 つの統合モデルに」が残る。

<a id="rec-3"></a>

### REC-3

- **重さ／判定**：中／一部確認（訂正つき）
- **内容**：「係数・段階・単位の組ごとに 1 回だけ解決する」（EX-SYS-02-M1 と EX-X-15-M1 の題、K7 の形、導出 D8）は、行ごとの換算を持たない行にしか当てはまらない：数えられた解決 299 回のうち 105 回（規模 L では 5657 回のうち 5183 回）は行ごとの繰り返しで、解決の回数は行数に比例する。EPD の適用可否も行ごとに調べる（37 回）。「単位換算の解決 8 回」はこのシナリオでは正しく、M-RESOLVE の条件は破れていない（検査担当の「231 回」は kg→kg の恒等な呼び出し 223 回を含む数え方の産物）：検証担当の訂正。
- **影響する成果**：記録 EX-SYS-02-M1・EX-X-15-M1 と M-RESOLVE の文（9 記録）、導出 D8、記録生成器の仕組みの確認（tools/build_records.py mechanism_checks）、統合モデルの係数解決（engine.py 141・166・172・290・750 行）、04_VERIFICATION/README の演算回数の表
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/records/`](../materials/round2_review/checker_scripts/records) の instr2.py、instr4.py ／ 検証担当：[`materials/round2_review/checker_scripts/records_verify/`](../materials/round2_review/checker_scripts/records_verify) の v3_counts.py、v3_conv.py、v3_scale.py
- **担当する予定だった段階**：a2（ほかに C）
- **予定していた対応**：係数レコードの部分（存在、許諾、段階、値の妥当性）を（係数 ID、段階）ごとに、単位換算を単位の組ごとにメモ化し、行ごとの換算だけを行ごとに残す。回数は統合モデルの外からの計数（bench/mechanism_probe.py の P7）で示す（SPEC_A2 1・3 節）。
- **停止時点の状態**：途中で停止
- **作業担当の自己申告**：報告なし（段階 a2 は報告前に停止）
- **状態の根拠**：a2 は報告前に停止（STOP_STATUS 1・3 節）。patch の engine.py に Resolver（計数は factor_records_resolved と unit_pairs_resolved）の追加と、旧計数器 factor_resolutions・unit_conversions_resolved の削除がある。[`materials/interrupted_fix/a2_partial_outputs/mechanism_probe_UNVERIFIED.json`](../materials/interrupted_fix/a2_partial_outputs/mechanism_probe_UNVERIFIED.json) の statements.P7.holds は true（未検証）。
- **停止時点で残っていた作業**：a2 の受け入れ確認の記録が無い。記録の題、導出 D8、報告書の改訂（段階 C）は未着手。
- **公開中の版**：残っている。09_APPROX_STUDY は 43ba5d7 のコードと同一で、Resolver は無い。

<a id="rec-4"></a>

### REC-4

- **重さ／判定**：中／反証検査で確認
- **内容**：仕組みの確認 M-SINGLEPASS・M-EVENTS・M-ROWPROD の裏にある計数器（rows_scanned、event_lists_built、row_factor_products）は決まった位置に置いた集計で、失敗し得ない。測って正しかったのは「合計のみの出力では、資材・設備の行を 1 回だけ読み、行ごとに係数の値を掛けず、周期的な更新年の一覧を作らない」という狭い核だけで、公表した「行の読み取り 520（行別の出力でも）」「更新年の一覧を 1 つも作らない」「行ごとの係数の乗算 520 回」は事実と違う（行別の出力では設備 104 行を読み直し、合計のみでも明示の一覧 16 と冷媒の交換年の一覧 10 を作り、乗算は合算で約 4,000 回、詳細でさらに約 830 回）。
- **影響する成果**：統合モデルの計数器（engine.py 242・469・503・574・1305 行）、記録の仕組みの文（M-SINGLEPASS・M-EVENTS・M-ROWPROD を引く記録）、03_MODELS/README と 04_VERIFICATION/README の仕組み・演算回数の表、手順書 P8（仕組みは計数で確認する、という条件）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/records/`](../materials/round2_review/checker_scripts/records) の instr1.py、instr2.py、instr5.py、instr1.out、instr2.out ／ 検証担当：[`materials/round2_review/checker_scripts/records_verify/`](../materials/round2_review/checker_scripts/records_verify) の v3_counts.py、v4_products.py
- **担当する予定だった段階**：a2（ほかに C）
- **予定していた対応**：失敗し得ない手置きの計数器を除き、実際の演算を統合モデルの外から数える測定（bench/mechanism_probe.py。数値から計算した真偽 P1〜P7）に置き換える（SPEC_A2 1・3 節）。
- **停止時点の状態**：途中で停止
- **作業担当の自己申告**：報告なし（段階 a2 は報告前に停止）
- **状態の根拠**：a2 は報告前に停止。patch の engine.py から rows_scanned・row_factor_products・event_lists_built の行が削除され（追加行には無い）、新規の bench/mechanism_probe.py（789 行）があり、bench/verify_unified.py の mechanisms() はその結果を返す形に変わっている。[`materials/interrupted_fix/a2_partial_outputs/mechanism_probe_UNVERIFIED.json`](../materials/interrupted_fix/a2_partial_outputs/mechanism_probe_UNVERIFIED.json) の statements は P1〜P7 すべて holds = true（未検証、a2 が改造した後のコードについての出力）。
- **停止時点で残っていた作業**：a2 の受け入れ確認の記録が無い。記録、報告書、手順書 P8 の本文の改訂（段階 C）は未着手。
- **公開中の版**：残っている。fastcalc/engine.py 106〜107 行ほかに rows_scanned・row_factor_products・event_lists_built が残る。04_VERIFICATION/README 43・50 行に 520 の記述が残る。

<a id="rec-5"></a>

### REC-5

- **重さ／判定**：中／反証検査で確認
- **内容**：記録の注記「SUCCESS は、出力の一致・仕組みの計数・導出の 3 つに裏付けがあるものだけ（裏付けがなければ生成が失敗する）」は事実と違う：SUCCESS 118 件のうち 3 つとも揃うのは 96 件で、18 件は仕組みの確認が無く、5 件は導出が無く、EX-QA-04-M1 はどちらも無い。生成器はこれらで失敗しない。仕組みが引かれている場合も、1 つの架空シナリオについての全体の述語 8 個を、手書きの plan() で単位に結び付けたものである。
- **影響する成果**：記録 03_MODELS/records/units.json の注記と SUCCESS 118 件、記録生成器（tools/build_records.py 463〜480 行）、03_MODELS/README 149 行、手順書 P8
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/records/`](../materials/round2_review/checker_scripts/records) の ledger_check.py、instr3.py ／ 検証担当：[`materials/round2_review/checker_scripts/records_verify/`](../materials/round2_review/checker_scripts/records_verify) の v3_scale.py
- **担当する予定だった段階**：a2（ほかに C）
- **予定していた対応**：記録の裏付けを、(1) 出力の一致、(2) M2 は故障注入による所属の測定、M1 は外からの計数 P1〜P7（全体の測定と明記する）、(3) 導出、に改め、M2 の SUCCESS に裏付けが無ければ生成を失敗させ、注記には計算した実数を書く（SPEC_A2、STAGE_C_NOTES 1）。
- **停止時点の状態**：途中で停止
- **作業担当の自己申告**：報告なし（段階 a2 は報告前に停止）
- **状態の根拠**：測定の側（bench/membership_check.py、bench/mechanism_probe.py）は a2 の途中の編集として patch にあるが、報告なし。記録生成器 tools/build_records.py と記録の注記は patch に含まれない（段階 C は未着手）。
- **停止時点で残っていた作業**：a2 の受け入れ確認の記録が無い。記録生成器と注記、README、手順書 P8 の改訂（段階 C）は未着手。
- **公開中の版**：残っている。03_MODELS/records/units.json の注記に「裏付けがなければ生成が失敗する」が残り、SUCCESS 118 件のうち mechanism が null のものが 18 件、derivation が null のものが 5 件（JSON を読んで数えた）。

<a id="rec-6"></a>

### REC-6

- **重さ／判定**：中／一部確認（訂正つき）
- **内容**：B6-02、B7-01〜03、B6-01（M1 と M2）と、B6-04・X-06 の M2 の記録が根拠に引く一致（約 41,000 個の値）は、ループで作った年次の系列とフラグの一致で、閉形式を通っていない。閉形式は B6-03、B7-04、B2-01、X-11 と合計を通じてだけ検証されている。「合計のみの出力で出力を持たないのは B4-03・X-13 だけ」という README の文は文字どおり正しいが、B6-01・B6-04・X-06 はフラグだけ、B6-02・B7-01〜03 は除外件数とフラグだけを返すことを書き足す必要がある（検証担当の訂正）。
- **影響する成果**：記録 EX-B6-02-M1、EX-B7-01〜03-M1、EX-B6-01-M1、EX-B6-04-M1、EX-X-06-M1 とその M2、04_VERIFICATION/unified_model_exactness.json（units_without_output_in_totals_mode）、04_VERIFICATION/README 26 行
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/records/`](../materials/round2_review/checker_scripts/records) の instr3.py、instr3.out ／ 検証担当：[`materials/round2_review/checker_scripts/records_verify/`](../materials/round2_review/checker_scripts/records_verify) の v2_membership.py
- **担当する予定だった段階**：a2（ほかに C）
- **予定していた対応**：閉形式を壊したときにどの単位が検出するか（detected_by）を故障注入で測り、閉形式の M1 記録はその単位名を根拠に書く。合計のみの出力でフラグだけを返す単位を別に示す（SPEC_A2 2 節、STAGE_C_NOTES 1 の (2')）。
- **停止時点の状態**：途中で停止
- **作業担当の自己申告**：報告なし（段階 a2 は報告前に停止）
- **状態の根拠**：a2 は報告前に停止。[`materials/interrupted_fix/a2_partial_outputs/membership_check_UNVERIFIED.json`](../materials/interrupted_fix/a2_partial_outputs/membership_check_UNVERIFIED.json) に closed_forms.*.detected_by_full／detected_by_totals と units[].flag_only_in_totals の鍵がある（例：linear_weighted_sum を 1.5 倍にすると B6-03・B7-04 と合計が検出。未検証）。記録生成器は patch に含まれない。
- **停止時点で残っていた作業**：a2 の受け入れ確認の記録が無い。記録の根拠の書き換えと README の追記（段階 C）は未着手。
- **公開中の版**：残っている。04_VERIFICATION/README 26 行の「B4-03・X-13 は出力を持たない」は追記なしのまま。

<a id="rec-7"></a>

### REC-7

- **重さ／判定**：低／反証検査で確認
- **内容**：個別の SUCCESS 記録の題がコードを表していない：A5-01-M1（1 つのスカラーに電力係数を掛けてから表に入れるので、係数キーごとの合算も後掛けも無い）、QA-03-M1（使用済みの集合は係数解決ではなく段階の表のキーから得る）、B4-02-M1（明示の事象一覧を持つ設備は行ごとに足す）、B1-01-M2 と導出 D6 の最終行（充填量×GWP を合算と仕上げで 2 回計算しており、コード上の共通項は無い）。
- **影響する成果**：記録 EX-A5-01-M1・EX-A5-01-M2、EX-QA-03-M1、EX-B4-02-M1、EX-B1-01-M2、導出 D6 の最終行（03_MODELS/DERIVATIONS.md）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/records/`](../materials/round2_review/checker_scripts/records) の instr3.py、instr5.py、instr2.py ／ 検証担当：[`materials/round2_review/checker_scripts/records_verify/`](../materials/round2_review/checker_scripts/records_verify) の v2_membership.py、v3_counts.py
- **担当する予定だった段階**：a2（ほかに C）
- **予定していた対応**：コード側は a2 で直せる所を直し（B1 を機器ごとの 1 つの表にする）、題は記録生成器で直す：A5-01 の M1 は NOT_APPLICABLE、QA-03-M1 は「排出の表に現れる係数キーから得る」、B4-02-M1 に「明示の更新年一覧を持つ行は行ごと」を加える（SPEC_A2 1 節、STAGE_C_NOTES 2）。
- **停止時点の状態**：途中で停止
- **作業担当の自己申告**：報告なし（段階 a2 は報告前に停止）
- **状態の根拠**：a2 は報告前に停止。patch の engine.py に「B1-01: the sum of the device table」という追加行と Aggregate.charges があり、旧の 'b1_01 += dev.charge_mass_kg * dev.gwp' は削除されている。記録生成器と DERIVATIONS.md は patch に含まれない。
- **停止時点で残っていた作業**：a2 の受け入れ確認の記録が無い。記録の題と導出 D6 の改訂（段階 C）は未着手。
- **公開中の版**：残っている。09_APPROX_STUDY の記録と導出は 43ba5d7 と同一。

<a id="rec-8"></a>

### REC-8

- **重さ／判定**：低／反証検査で確認
- **内容**：NOT_APPLICABLE の理由文に事実と違うものがある：B6-04 の M4「他の単位の値の和（または比）で、独自の式がない」（B6-04 は 3 つの入力系列からの年ごとの max(0, …) という独自の式）、M6 の定型文「厳密式がすべての入力条件で同じ手間で使え」（合計のみの出力の年ループは、記述子の入力で 0 回、年次表の入力で 480 回）、B6-02・B7-0x の M3「M1 の閉形式は…」（閉形式は記述子の入力にしか無く、年次表については何も測っていない）。
- **影響する成果**：記録 NA-B6-04-M4、NA-*-M6（B6-02、B6-03、B6-04、B7-01〜03、B2-01、X-11）、NA-B6-02-M3、NA-B7-01〜03-M3、記録生成器の定型文（tools/build_records.py NA_SUM・NA_HYBRID・NA_EXACT）、近似検証（年次表の入力に対する候補の測定が無い）
- **再現の手順の所在**：専用のスクリプトなし（[`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md) REC-8 の REPRO は、04_VERIFICATION/unified_model_exactness.json の mechanism_counts を読む 1 行と、台帳の定義文の読み取り）
- **担当する予定だった段階**：b2（ほかに C）
- **予定していた対応**：欠けていた測定として、年次表で与えた年次量を 5 年おきに間引いて直線補間する候補を追加し（段階 b2）、理由文は記録生成器で直す：B6-04 の M4 に独自の理由、NA_HYBRID は該当する単位だけ、運用の単位は「記述子なら閉形式、年次表なら走査（どちらも厳密）」（SPEC_B2 項目 10、STAGE_C_NOTES 3）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：PARTLY_FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/B2_REPORT.json`](../materials/interrupted_fix/agent_reports/B2_REPORT.json) findings[REC-8] = PARTLY_FIXED（新候補 AP-24a：燃料・水・下水・廃棄物の年次表、AP-24b：電力の年次表。AP-24a は 173 シナリオで B7 -4.07〜+2.14％、B6 -1.77〜+1.37％ と自己申告）。patch の bench/approx_meta.py に AP-24a、approx_measures.py に AP-24b がある。NOT_APPLICABLE の文は「後段」として未実施。
- **停止時点で残っていた作業**：記録生成器の理由文の改訂（段階 C）は未着手。b2 の測定は未検証。
- **公開中の版**：残っている。03_MODELS/candidates.json に AP-24 は無い。記録の理由文は元のまま。

<a id="rec-9"></a>

### REC-9

- **重さ／判定**：低／反証検査で確認
- **内容**：「統合しなかった単位（4）…検査の 4 単位は」は誤りで、検査は 3 単位（C-05、QA-02、SYS-01。STO-01 は検査ではない）。「表の値の読み出しで行う乗算は 3373 回」は表の長さの合計で、実際に行う係数の値との乗算は仕上げで 2847＋522 回、計数器のない X-03 の展開でさらに 223 回である。
- **影響する成果**：03_MODELS/README 68 行（報告書生成器 tools/build_reports.py 225 行の固定の文字）、記録生成器の M-ROWPROD の文、04_VERIFICATION/README の演算回数の表、統合モデルの計数器 table_factor_products
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/records/`](../materials/round2_review/checker_scripts/records) の instr2.py、instr3.py ／ 検証担当：[`materials/round2_review/checker_scripts/records_verify/`](../materials/round2_review/checker_scripts/records_verify) の v3_counts.py、v4_products.py、v3_scale.py
- **担当する予定だった段階**：a2（ほかに C）
- **予定していた対応**：計数器は a2 で外からの測定に置き換え、報告書は「検査の 3 単位」をデータから計算し、3373 は「読んだ表の項目数」として名付け直す（SPEC_A2、STAGE_C_NOTES 7）。
- **停止時点の状態**：途中で停止
- **作業担当の自己申告**：報告なし（段階 a2 は報告前に停止）
- **状態の根拠**：a2 は報告前に停止。patch の engine.py から table_factor_products の行が削除されている。報告書生成器 tools/build_reports.py は patch に含まれない（段階 C は未着手）。
- **停止時点で残っていた作業**：a2 の受け入れ確認の記録が無い。報告書の文の改訂（段階 C）は未着手。
- **公開中の版**：残っている。03_MODELS/README 68 行に「検査の 4 単位」、76 行に 3373 が残る。

<a id="app-1"></a>

### APP-1

- **重さ／判定**：中／一部確認（訂正つき）
- **内容**：測定の漏れ（検証担当は MEDIUM ではなく LOW と評価）：安全側の修繕の近似「修繕年数 = T − min(T, max(0, T/c − 1))」を研究は測っていない。研究の母集団では B3 が平均 +0.30％、最大 +1.44％（分類別の形は +1.46％）で、周期 1 年以上なら過小にならないので、AP-18b の保留理由「過小があり得る」は避けられる。ただし「目標を満たす近似がある」とは言えない：過大の大きさは寿命の構成に依存し（T=30 で期間に近い架空の寿命だと +3.3％）、分類別の形は同じ建物の行から作った値で入力は減らず、行別の形は厳密な閉形式に対する利点が無い。
- **影響する成果**：近似候補の一覧（03_MODELS/candidates.json の AP-04・AP-18b）、近似検証（bench/approx_study.py、04_VERIFICATION/approximation_study.json）、05_DECISIONS/README の近似の要約（42・95 行）、03_MODELS/README 140 行（B3-01 の保留理由）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/approx/`](../materials/round2_review/checker_scripts/approx) の recheck3.py、recheck3.log.txt、recheck2.py、recheck2_400.log.txt ／ 検証担当：[`materials/round2_review/checker_scripts/approx_verify/`](../materials/round2_review/checker_scripts/approx_verify) の v1.py、v1_400.log.txt、v2.py、v2.log.txt
- **担当する予定だった段階**：b2（ほかに C）
- **予定していた対応**：この候補を行別の形と分類別の形で追加し、母集団と、評価期間に近い架空の寿命のストレスシナリオの両方で測って両方を記録する。符号の保証は周期 1 年以上に限ると書き、「目標を満たす」とは書かない（SPEC_B2 項目 3）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：PARTLY_FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/B2_REPORT.json`](../materials/interrupted_fix/agent_reports/B2_REPORT.json) findings[APP-1] = PARTLY_FIXED（AP-23a 行別・AP-23b 同じ建物の分類・AP-23c 別の建物の分類を追加。AP-23a は B3 平均 +0.297％、最大 +1.438％、ストレス T=30 寿命 [29] で +3.33％、AP-23c は -39.4％〜+329.1％ と自己申告）。patch の bench/approx_meta.py と approx_measures.py に AP-23 がある。結論文と candidates.json は「後段」として未実施。
- **停止時点で残っていた作業**：candidates.json、結論文、05・03 の README の改訂（段階 C）は未着手。b2 の測定は未検証で、a1 が変えた基準計算の上で行われている。
- **公開中の版**：残っている。03_MODELS/candidates.json に AP-23 は無い。

<a id="app-2"></a>

### APP-2

- **重さ／判定**：中／反証検査で確認
- **内容**：電力の近似候補（AP-08、AP-09a、AP-09b、AP-09c、AP-13）で「B6 段階」と呼んだ基準量は B6-03（B6 段階＋B2 段階）である。B6 段階そのものでは公表した範囲が表示の精度で成り立つが、B2 段階（と単位 B6-01）では誤差が約 1.3〜1.8 倍で、AP-09c は +2.03％ に達し、「段階 2％ の内側」は B2 では偽になる。AP-18c・AP-18 の「C3＋C4」は C3-01＋C4-01（資材だけ、設備の廃棄 X-14 を含まない）で、段階別では C3 が -34.9％〜+42.8％、C4 が -38.6％〜+118.2％。どの候補の結論も変わらない。
- **影響する成果**：近似検証（bench/approx_study.py 252、269〜271、406〜435 行。approximation_study.json）、近似候補の一覧（candidates.json の AP-08、AP-09a/b/c、AP-13、AP-18c、AP-18 の within_stage_target と理由文）、記録 B2-01 の M3（AP-08 の数値の引用）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/approx/`](../materials/round2_review/checker_scripts/approx) の recheck.py、recheck_400.log.txt、recheck3.py、recheck2.py ／ 検証担当：[`materials/round2_review/checker_scripts/approx_verify/`](../materials/round2_review/checker_scripts/approx_verify) の v1.py、v1_400.log.txt
- **担当する予定だった段階**：b2（ほかに C）
- **予定していた対応**：電力の候補を X-02 の実際の段階値（B6 と B2 を別々）と、候補を付けた単位自身の出力で測り、B6-03 の数値は「B6-03 = B6 + B2」の名札で残す。within_stage_target は最悪の段階で決める。AP-18c・AP-18 は C3 と C4 を別々に報告する（SPEC_B2 項目 1）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：PARTLY_FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/B2_REPORT.json`](../materials/interrupted_fix/agent_reports/B2_REPORT.json) findings[APP-2] = PARTLY_FIXED（AP-09c は B6 で -1.313〜+1.719％、B2 で -1.855〜+2.027％ となり within_stage_target は false、と自己申告）。patch で bench/approx_study.py の 'b6_ref = res["B6-03"]["value"]' が削除されている。[`materials/interrupted_fix/agent_reports/cmp_committed_vs_new.log.txt`](../materials/interrupted_fix/agent_reports/cmp_committed_vs_new.log.txt) に AP-09c within_stage_target の差が記録されている。「B6 段階」と書く文の改訂は「後段」。
- **停止時点で残っていた作業**：candidates.json と記録の文の改訂（段階 C）は未着手。b2 の測定は未検証。
- **公開中の版**：残っている。bench/approx_study.py 409 行に 'b6_ref = res["B6-03"]["value"]' が残り、03_MODELS/candidates.json の AP-09c は within_stage_target = true のまま（JSON を読んで確認）。

<a id="app-3"></a>

### APP-3

- **重さ／判定**：中／反証検査で確認
- **内容**：「合計への影響」（total_error）は、測った段階の局所的な差を建物合計で割った値で、下流で再利用される量を変える候補（AP-06、AP-07b、AP-17）では、近似した入力で基準計算をやり直したときの建物合計の変化のほうが 95％ 点で最大約 2.2 倍大きい（AP-06 が 0.28％ 対 0.13％、AP-07b が 1.20％ 対 0.63％、AP-17 が 0.57％ 対 0.46％）。AP-06 は 1％・2％ の内側のままで、結論は変わらない。
- **影響する成果**：近似検証（bench/approx_study.py Collector.add 58〜60 行、approximation_study.json の total_error と within_total_target）、04_VERIFICATION/README の表の列「合計への影響（95％点）」、近似候補の一覧（AP-06、AP-07b、AP-17）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/approx/`](../materials/round2_review/checker_scripts/approx) の recheck.py、recheck2.py、recheck_400.log.txt、recheck2_400.log.txt ／ 検証担当：[`materials/round2_review/checker_scripts/approx_verify/`](../materials/round2_review/checker_scripts/approx_verify) の v1.py、v1_400.log.txt
- **担当する予定だった段階**：b2（ほかに C）
- **予定していた対応**：total_error を local_total_error と名付け直し、下流で再利用される量を変える候補には、近似した入力で基準計算自体をやり直した propagated_total_error と段階ごとの波及の誤差も測り、within_total_target はそれがある場合そちらを使う（SPEC_B2 項目 2）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：PARTLY_FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/B2_REPORT.json`](../materials/interrupted_fix/agent_reports/B2_REPORT.json) findings[APP-3] = PARTLY_FIXED（AP-06 の波及後は平均 -0.149％、95％ 点 0.284％、最大 -0.655％ と自己申告。別名なしで total_error を local_total_error に改名）。patch の bench/approx_study.py に local_total_error と propagated_total_error の追加行がある。README の列の文は「後段」。
- **停止時点で残っていた作業**：README の列名と説明の改訂、記録・報告書の生成器の新しい JSON への対応（段階 C）は未着手。b2 は「tools/build_records.py と tools/build_reports.py は、対応させるまで新しい JSON では動かない」と申告。
- **公開中の版**：残っている。04_VERIFICATION/approximation_study.json は 32 候補のままで、うち 30 候補が total_error の鍵を持ち、propagated_total_error は無い（JSON を読んで確認）。

<a id="app-4"></a>

### APP-4

- **重さ／判定**：中／一部確認（訂正つき）
- **内容**：AP-17（輸送距離を手段ごとの単純平均にする）の誤差は、手段ごとの質量と距離の標本共分散に恒等的に等しいので、保留理由の第 1 文（相関があるとずれる）は正しい。最後の文（重い資材ほど遠くから運ぶ傾向が実際にあるかどうかで結果が決まる）は不完全で、系統的な傾向が無くても、質量と距離を独立に引いた架空データで A4 が -37％〜+117％ になる（少数の重い行が支配するため）。検証担当は検査担当の主な論拠を誤りとし、文言の問題（LOW）と評価した。
- **影響する成果**：近似候補の一覧（candidates.json の AP-17 の理由文）、記録生成器の結論文（tools/build_records.py 377〜381 行）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/approx/`](../materials/round2_review/checker_scripts/approx) の recheck2.py、recheck.py ／ 検証担当：[`materials/round2_review/checker_scripts/approx_verify/`](../materials/round2_review/checker_scripts/approx_verify) の v1.py、v1_400.log.txt
- **担当する予定だった段階**：b2（ほかに C）
- **予定していた対応**：「単純平均距離の誤差 = 手段ごとの質量と距離の標本共分散」という恒等式（残差の最大値）と、実現した相関の統計を測って保存し、理由文はその恒等式に基づいて書き直す（SPEC_B2 項目 9、STAGE_C_NOTES 5）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：PARTLY_FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/B2_REPORT.json`](../materials/interrupted_fix/agent_reports/B2_REPORT.json) findings[APP-4] = PARTLY_FIXED（恒等式の残差は 400 シナリオで 3.3e-15 以下、実現した相関は平均 +0.0247、と自己申告）。patch の bench/approx_study.py に covariance_identity の追加行がある。理由文は「後段」。
- **停止時点で残っていた作業**：理由文の書き直し（段階 C）は未着手。b2 の測定は未検証。
- **公開中の版**：残っている。03_MODELS/candidates.json 1540 行に「重い資材ほど遠く…」の文が残る。

<a id="app-5"></a>

### APP-5

- **重さ／判定**：低／反証検査で確認
- **内容**：AP-01 の「T/c − 1 ≤ ceil(T/c) − 1 なので基準を上回ることがなく」と AP-20 の「必ず成り立つ上下限」は、研究自身の境界の規則（T の相対 1e-9 以内の事象は数えない）の下では文字どおりには成り立たない：下限は N ≥ T(1−1e-9)/c − 1 としてだけ成り立つ（例：T=60、c=19.99999999 で基準の回数は 2、T/c−1 は 2.0000000015、B4 で +7.5e-10）。上限と AP-03 の「常に過大」は成り立つ。大きさは相対 1e-9 程度で、実用上の影響は無い。
- **影響する成果**：近似候補の一覧（candidates.json の AP-01・AP-20 の題と理由文）、近似検証の上下限の試験（bench/approx_study.py）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/approx/`](../materials/round2_review/checker_scripts/approx) の recheck3.py、recheck3.log.txt ／ 検証担当：[`materials/round2_review/checker_scripts/approx_verify/`](../materials/round2_review/checker_scripts/approx_verify) の v2.py、v2.log.txt
- **担当する予定だった段階**：b2（ほかに a1、C）
- **予定していた対応**：AP-01・AP-20 に、正確な規則の下で成り立つ形の境界（N ≥ T×c/L − 1、c = 1 − 1e-9）を記録し、T の約数のすぐ下の寿命（T=60 で 19.99999999）のシナリオを上下限の試験に加える。理由文の「必ず」は直す（SPEC_B2 項目 8、STAGE_C_NOTES 5）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：PARTLY_FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/B2_REPORT.json`](../materials/interrupted_fix/agent_reports/B2_REPORT.json) findings[APP-5] = PARTLY_FIXED（AP-01・AP-20 に bound を持たせ、AP-20 の題から「必ず成り立つ」を除いた、と自己申告）。[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[APP-5] = DOCUMENTED_ONLY（closed_forms.renewal_count の説明文に「T/period − 1 ≤ count は一般には成り立たない」と記載）。patch の bench/approx_measures.py に 19.99999999、closed_forms.py に該当の説明文がある。理由文は「後段」。
- **停止時点で残っていた作業**：candidates.json の題と理由文の改訂（段階 C）は未着手。
- **公開中の版**：残っている。03_MODELS/candidates.json 2049 行（AP-20 の題）に「必ず成り立つ」が残る。

<a id="app-6"></a>

### APP-6

- **重さ／判定**：低／反証検査で確認
- **内容**：AP-05 は題が「線形近似 1−(1−r)^k ≈ r·k」だが、コードは漏洩の線形化に加えて、交換時の損失と廃棄時の残量にも満充填量を使っており（全機器を補充ありとして扱う粗い変種）、公表値（B1 平均 +28.0％、最大 +180.7％）はその変種のものである。題どおりの一貫した線形化では平均 +23.89％、最大 +164.3％。どちらも過小にならず、不採用は変わらない。一貫した形で 2％ 以内に入る機器は 2434 台のうち 42 台（検査担当は 3 台としたが検証担当が訂正）。
- **影響する成果**：近似検証（bench/approx_study.py 273〜293 行）、近似候補の一覧（candidates.json の AP-05）、04_VERIFICATION/README 150 行（適用範囲の数値）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/approx/`](../materials/round2_review/checker_scripts/approx) の recheck.py、recheck3.py ／ 検証担当：[`materials/round2_review/checker_scripts/approx_verify/`](../materials/round2_review/checker_scripts/approx_verify) の v1.py、v1_400.log.txt
- **担当する予定だった段階**：b2（ほかに C）
- **予定していた対応**：2 つの変種（A：一貫した線形化、B：全機器を補充ありとして扱う＝これまでの測定）を両方測って名前を付け、機器ごとの適用範囲の区分を両方について報告する（SPEC_B2 項目 5）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：PARTLY_FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/B2_REPORT.json`](../materials/interrupted_fix/agent_reports/B2_REPORT.json) findings[APP-6] = PARTLY_FIXED（AP-05 を AP-05a と AP-05b に分割。AP-05b は公開中の AP-05 とビット単位で同じ、AP-05a は平均 +23.894％。新たに「AP-05a は段階 B1 では過小にならないが、単位 B1-03 を最大 -98.6％、B1-04 を最大 -90.5％ 過小に見積もる」と自己申告）。patch の bench/approx_meta.py に AP-05a がある。文は「後段」。
- **停止時点で残っていた作業**：candidates.json と README の文の改訂（段階 C）は未着手。b2 の測定は未検証。
- **公開中の版**：残っている。03_MODELS/candidates.json の AP-05 は 1 候補のまま（AP-05a の文字列なし）。

<a id="app-7"></a>

### APP-7

- **重さ／判定**：低／反証検査で確認
- **内容**：資材分類別の内訳（by_material_class）は、基準が 0 の（シナリオ、分類）の組を、候補が 0 でない場合も数えずに落としている（落ちた 850 組のうち候補が 0 でないのは AP-03 で 850、AP-02 で 694、AP-01 で 0）。AP-03 の理由文は「B5 で平均 +42.7％」が 89 シナリオだけの値で、基準が 0 回なのに計上する場合が 133 件あることを書いていない。
- **影響する成果**：近似検証（bench/approx_study.py Collector.add_classes 70〜74 行、approximation_study.json の by_material_class）、近似候補の一覧（candidates.json の AP-03 の理由文）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/approx/`](../materials/round2_review/checker_scripts/approx) の recheck2.py、recheck.py ／ 検証担当：[`materials/round2_review/checker_scripts/approx_verify/`](../materials/round2_review/checker_scripts/approx_verify) の v1.py、v1_400.log.txt
- **担当する予定だった段階**：b2（ほかに C）
- **予定していた対応**：分類別の集計で、基準が 0 で落とした組の数と、そのうち候補が 0 でない組の数を数えて結果に持たせ、シナリオ単位の集計にも同じ 2 つの数を持たせる（SPEC_B2 項目 6）。AP-03 の理由文は後段で直す。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：PARTLY_FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/B2_REPORT.json`](../materials/interrupted_fix/agent_reports/B2_REPORT.json) findings[APP-7] = PARTLY_FIXED（全ての誤差の系列に n_reference_zero と n_reference_zero_candidate_nonzero を持たせた、と自己申告）。patch の bench/approx_support.py に n_reference_zero_candidate_nonzero の追加行がある。AP-03 の理由文は「後段」。
- **停止時点で残っていた作業**：AP-03 の理由文の改訂（段階 C）は未着手。
- **公開中の版**：残っている。09_APPROX_STUDY の bench/approx_study.py と candidates.json は 43ba5d7 と同一。

<a id="app-8"></a>

### APP-8

- **重さ／判定**：低／一部確認（訂正つき）
- **内容**：AP-14（評価期間を変えた補間）で、明示の更新年の一覧は評価期間を延ばしても延長されないため、80 シナリオのうち 46 では厳密には「同じ建物の長い期間」の比較になっていない。ただし一覧を 75 年まで延長しても結果はほとんど変わらず（95％ 点が 11.80％ → 11.93％、範囲が -11.9％〜+22.8％ → -11.9％〜+23.0％）、公表値と不採用の判断には影響しない（検証担当の訂正）。
- **影響する成果**：近似検証（bench/approx_study.py 550〜560 行）、近似候補の一覧（candidates.json の AP-14 の「同じ建物の T=50 と T=75」）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/approx/`](../materials/round2_review/checker_scripts/approx) の recheck2.py ／ 検証担当：[`materials/round2_review/checker_scripts/approx_verify/`](../materials/round2_review/checker_scripts/approx_verify) の v1.py、v1_400.log.txt
- **担当する予定だった段階**：b2
- **予定していた対応**：自身の評価期間が 75 年以上のシナリオと 75 年未満のシナリオに分けて報告し、明示の一覧をシナリオ自身の期間の先まで延長した測定を 1 回行って、打ち切りの影響を測定値として残す（SPEC_B2 項目 7）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/B2_REPORT.json`](../materials/interrupted_fix/agent_reports/B2_REPORT.json) findings[APP-8] = FIXED（75 年以上 n=34 で -2.68〜+11.80％、75 年未満 n=46 で -11.93〜+22.77％、一覧を延長すると 95％ 点 11.93％、と自己申告）。patch の bench/approx_study.py に by_own_study_period と explicit_lists_continued の追加行がある。
- **停止時点で残っていた作業**：独立の検査は未着手。公開中の JSON は再生成されていない。
- **公開中の版**：残っている。09_APPROX_STUDY の approximation_study.json は 43ba5d7 と同一。

<a id="app-9"></a>

### APP-9

- **重さ／判定**：低／反証検査で確認
- **内容**：AP-18a〜c と AP-19a の数値は、評価する建物自身の行から代表パラメータを作った最良の場合（標本内）の値で、入力は減っていない（AP-19a は、比率を持つ行がどれかという情報も残している）。別の架空の建物から作った分類パラメータを使うと、AP-18b は B3 で -41％〜+337％ になる（標本内では -1.9％〜+1.1％）。保留の判断自体は変わらない。
- **影響する成果**：近似候補の一覧（candidates.json の AP-18a〜c、AP-19a の理由文）、近似検証（bench/approx_study.py 223〜269、320〜327 行）、03_MODELS/README 140 行（B3-01 の要約）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/approx/`](../materials/round2_review/checker_scripts/approx) の recheck4.py、recheck4.log.txt、recheck.py ／ 検証担当：[`materials/round2_review/checker_scripts/approx_verify/`](../materials/round2_review/checker_scripts/approx_verify) の v3.py、v3.log.txt
- **担当する予定だった段階**：b2（ほかに C）
- **予定していた対応**：各候補に parameters_from（同じ建物＝標本内、または別の建物＝学習と評価の分割）を付け、AP-19a には keeps_row_membership を付け、AP-18b などには AP-10 と同じ分割による標本外の変種を追加して測る（SPEC_B2 項目 4）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：PARTLY_FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/B2_REPORT.json`](../materials/interrupted_fix/agent_reports/B2_REPORT.json) findings[APP-9] = PARTLY_FIXED（全候補に parameters_from、標本外の AP-18d・AP-23c と AP-19c を追加。AP-18d は -40.76〜+327.64％ と自己申告）。patch の bench/approx_meta.py に parameters_from（22 行）と AP-18d がある。理由文は「後段」。
- **停止時点で残っていた作業**：理由文と README の要約の改訂（段階 C）は未着手。b2 の測定は未検証。
- **公開中の版**：残っている。09_APPROX_STUDY の bench/approx_study.py に parameters_from は無い。

<a id="rep-1"></a>

### REP-1

- **重さ／判定**：中／反証検査なし
- **内容**：04_VERIFICATION/README の「入力仕様 124 項目のうち 0 項目は記録用で、どの計算にも使われない」は誤り。input_usage.json 自身が、仕様の 124 項目のうち 47 項目はどの計算にも読まれないことを示し（読まれるのは 77）、台帳は 30 項目を記録用（METADATA_ONLY）に分類している。0 は、synth/model.py のどの項目も使っていない番兵を数えた値で、古いファイルではなく生成器の不具合である。
- **影響する成果**：04_VERIFICATION/README 103 行、報告書生成器（tools/build_reports.py 340 行）、04_VERIFICATION/input_usage.json（metadata_only_inputs）、01_LEDGER/unlinked_input_disposition.json と 01_LEDGER/README
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/reports/`](../materials/round2_review/checker_scripts/reports) の findings_repro.py、recompute10.py（findings_repro.py は REP-1 の行）
- **担当する予定だった段階**：b3（ほかに C）
- **予定していた対応**：input_usage.json の値を測定した一覧（どの計算にも読まれない仕様の入力とその ID、読まれない追加項目）に置き換え、台帳の unlinked_input_disposition.json の 3 分類を測定に合わせて直し、報告書の文は測定値から書く（SPEC_B3 項目 2、STAGE_C_NOTES）。
- **停止時点の状態**：未対応
- **作業担当の自己申告**：なし（段階は未着手）
- **状態の根拠**：[`STOP_STATUS.md`](../STOP_STATUS.md) 1・3 節：b3 は未着手。patch に bench/input_usage.py、tools/*、04_VERIFICATION/* は含まれない。
- **停止時点で残っていた作業**：すべて未着手。
- **公開中の版**：残っている。04_VERIFICATION/README 103 行に「0 項目は記録用」が残り、input_usage.json の metadata_only_inputs は 0 のまま（JSON を読んで確認）。HEAD の README 冒頭の手書きの追記が、この文は誤りと注意している（本文は未修正）。

<a id="rep-2"></a>

### REP-2

- **重さ／判定**：中／反証検査なし
- **内容**：「評価軸 B の採点で『近似・共通化できる』が 2 点以上だった単位×段階は 52 件、このうち測定をせずに理由だけで見送ったものは 20 件」は、基準 b7 を M4（共通の近似モデル）に対応させた集計だが、手順書 P5 では b7 は「入力変数を減らせそう」で、共通の代理モデルの基準は b8 である。手順書どおり b8 を使うと 56 件、未測定 14 件になる。「測定済み」に数えたうち 10 件は、AP-15（延床面積当たりの段階別原単位）だけが測定の記録である。
- **影響する成果**：03_MODELS/judge_proposal_trace.json、記録生成器（tools/build_records.py 544 行）、03_MODELS/README「評価者の提案との対照」の節（132 行）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/reports/`](../materials/round2_review/checker_scripts/reports) の findings_repro.py、recompute12.py（findings_repro.py は REP-2 の行）
- **担当する予定だった段階**：C
- **予定していた対応**：評価者の提案との対照を手順書 P5 の基準どおり（b1→M1、b2・b3・b4→M2、b5・b6→M3、b8→M4（M5 も）、b7（入力）→M3〜M6 の測定済みの候補）に組み直し、基準ごとに報告する（STAGE_C_NOTES 6）。
- **停止時点の状態**：未対応
- **作業担当の自己申告**：なし（段階は未着手）
- **状態の根拠**：STOP_STATUS 3 節：記録・進捗台帳・報告書の改訂は未着手。patch に tools/build_records.py と 03_MODELS/* は含まれない。
- **停止時点で残っていた作業**：すべて未着手。
- **公開中の版**：残っている。03_MODELS/README 132 行に 52 件・20 件が残り、judge_proposal_trace.json に「他の式と共通の近似モデルにできる」の名札が 29 か所ある（文字列で確認）。

<a id="rep-3"></a>

### REP-3

- **重さ／判定**：中／反証検査なし
- **内容**：REC-5 と同じ問題を報告書の側から見た指摘：記録の注記、03_MODELS/README 149 行、手順書 P8 は「SUCCESS は出力の一致・仕組みの計数・導出の 3 つに裏付けがある」と言うが、SUCCESS 118 件のうち 18 件は仕組みが null、5 件は導出が null で、EX-QA-04-M1 は両方とも無く出力の一致だけに依っている。仕組みの確認は 400＋120 行の 1 シナリオから計算した 8 個の真偽を鍵で記録に付けたもので、単位ごとの確認ではない。
- **影響する成果**：記録 03_MODELS/records/units.json の注記、03_MODELS/README 149 行、手順書 P8（00_POLICY/EVALUATION_PROTOCOL.md）、記録生成器（tools/build_records.py 137、446〜477 行）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/reports/`](../materials/round2_review/checker_scripts/reports) の findings_repro.py、recompute5.py（findings_repro.py は REP-3 の行）
- **担当する予定だった段階**：C（ほかに a2）
- **予定していた対応**：REC-5 と同じ：記録の裏付けの規則を作り直し（M2 は故障注入、M1 は外からの計数、導出）、裏付けのない M2 の SUCCESS で生成を失敗させ、注記・README・手順書 P8 には実際の件数を書く（STAGE_C_NOTES 1、手順書 v1.4）。
- **停止時点の状態**：未対応
- **作業担当の自己申告**：なし（段階は未着手）
- **状態の根拠**：段階 C は未着手で、tools/build_records.py は patch に含まれない。入力になる測定（a2）は途中で停止。手順書 v1.4 の草稿（60e720f）は改訂履歴の行に P8 を挙げるが、43ba5d7 との差分は改訂履歴・P3・P4・P7 の語彙の表だけで、P8 の本文は変わっていない（git diff 43ba5d7 60e720f で確認）。
- **停止時点で残っていた作業**：すべて未着手。
- **公開中の版**：残っている。03_MODELS/records/units.json の注記に「裏付けがなければ生成が失敗する」が残る（mechanism が null の SUCCESS 18 件、derivation が null 5 件を JSON で確認）。

<a id="rep-4"></a>

### REP-4

- **重さ／判定**：中／反証検査なし
- **内容**：見出しの「66 単位が 7 つの統合モデルに、結果を変えずにまとまった」「計算の定義の数 70 → 11」は、一部が計算の変更ではなく名札の数である：K5（SUM-01〜08）のうち SUM-04・05・06 は 3 つの別々の式、SUM-07・08 もその場の式で、共有の補助関数を使うのは SUM-01〜03 だけ（基準計算も同じ式）。66 単位のうち 14 単位は M1 が NOT_APPLICABLE で、M2 の記録は出力の一致だけに支えられている。
- **影響する成果**：README 要点 2、05_DECISIONS/README「統合前後の変化」の表（70 → 11）、03_MODELS/models.json の K5、統合モデル（engine.py 1104〜1118、1246〜1248 行）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/reports/`](../materials/round2_review/checker_scripts/reports) の findings_repro.py（findings_repro.py は REP-4 の行。ほかは engine.py と units_c_sum.py の該当行の読み取り）
- **担当する予定だった段階**：a2（ほかに C）
- **予定していた対応**：K5 の指標を 1 つの共有の関数 indicator(by_stage, subset, divisor) にし（段階 a2）、統合の数は所属の測定から出して、基準計算が元から同じ形だった単位の数を別に報告する（SPEC_A2 1 節、STAGE_C_NOTES の報告書の項）。
- **停止時点の状態**：途中で停止
- **作業担当の自己申告**：報告なし（段階 a2 は報告前に停止）
- **状態の根拠**：a2 は報告前に停止。patch の engine.py に 'def indicator(by_stage, subset, divisor=1.0)' と、SUM-01〜07 がそれを呼ぶ追加行があり、'wlc / 1000.0' の行は削除されている。報告書生成器と models.json は patch に含まれない。
- **停止時点で残っていた作業**：a2 の受け入れ確認の記録が無い。見出しと表の数え直し（段階 C）は未着手。
- **公開中の版**：残っている。fastcalc/engine.py 1248 行に 'wlc / 1000.0' が残り、README 25 行に見出しが残る。HEAD の README 冒頭の手書きの追記が「66 単位の一部は基準を満たさない」と注意している（本文は未修正）。

<a id="rep-5"></a>

### REP-5

- **重さ／判定**：中／反証検査なし
- **内容**：近似の段階（M3〜M6）の 280 単位×段階のうち 204 は測定なしの NOT_APPLICABLE（論拠だけ）で、M5 の理由 66 件のうち 54 件、M6 の 65 件のうち 51 件は同じ定型文である。M4 が保留の 39 単位のうち 26 単位は、単位の式を使わない建物水準の代理モデル AP-15 だけが M4 の記録で、「保留あり」44 単位のうち 21 単位は AP-15 だけによる。単位固有の M4 候補があるのは 13 単位。報告書は「候補なし（測定なし）」と D-6・D-7 を開示しているので、隠したのではなく、要件の弱めと件数の水増しである。
- **影響する成果**：進捗台帳（05_DECISIONS/progress_ledger.json、PROGRESS.md）、近似候補の一覧（candidates.json の AP-15、AP-11、AP-16）、README の進捗の注記、近似検証（候補を付けた単位の範囲）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/reports/`](../materials/round2_review/checker_scripts/reports) の findings_repro.py、recompute5.py、recompute12.py（findings_repro.py は REP-5 の行）
- **担当する予定だった段階**：b2（ほかに C）
- **予定していた対応**：各候補に測定の範囲（UNIT、STAGE、BUILDING）と、自身の出力で測った単位（units）、段階の合計を通じてだけ言える単位（units_stage_level）を宣言させ（段階 b2）、進捗台帳と報告書では「単位固有の候補を測定」と「段階・建物水準の代理だけ」を分けて件数を出す（SPEC_B2 項目 11、STAGE_C_NOTES）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：PARTLY_FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/B2_REPORT.json`](../materials/interrupted_fix/agent_reports/B2_REPORT.json) findings[REP-5] = PARTLY_FIXED（測定の側だけ。124 の対応のうち UNIT 77、STAGE 6、BUILDING 41、24 単位に自身の出力の測定を追加、と自己申告）。patch の新規 bench/approx_meta.py に units_stage_level と BUILDING がある。PROGRESS と README の件数は「後段」。
- **停止時点で残っていた作業**：進捗台帳（evidence_scope の追加）と報告書の件数の出し直し（段階 C）は未着手。
- **公開中の版**：残っている。05_DECISIONS の進捗台帳と PROGRESS.md は 43ba5d7 と同一。

<a id="rep-6"></a>

### REP-6

- **重さ／判定**：中／反証検査なし
- **内容**：近似候補 32 種について記録されているのは誤差だけで、時間・メモリ・命令数・入力数の削減は測られていない（n_parameters があるのは AP-16 だけ）。不採用の理由「厳密な閉形式が同じ手間で使える」（AP-04、AP-05 など）と、保留の候補の入力の削減は、測定の裏付けが無い。構造・用途別の内訳は 32 候補のうち 30 にあるが、資材分類別は 7 候補だけである。
- **影響する成果**：04_VERIFICATION/approximation_study.json、近似候補の一覧（candidates.json の不採用・保留の理由）、近似検証（bench/approx_study.py）、04_VERIFICATION/README 4 節、指示書 5 章の要件（負荷と入力数の測定）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/reports/`](../materials/round2_review/checker_scripts/reports) の findings_repro.py、recompute8.py（findings_repro.py は REP-6 の行）
- **担当する予定だった段階**：b2（ほかに C）
- **予定していた対応**：各候補に、必要な入力を厳密な形と比べた数（数えられるものは件数、ほかは短文。inputs_measured で区別）を記録し、「同じ手間」を理由にした候補は、候補の核と厳密な閉形式の実行命令数を同じ行で測って保存する。行別の候補に資材分類別の内訳を足す（SPEC_B2 項目 12）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：PARTLY_FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/B2_REPORT.json`](../materials/interrupted_fix/agent_reports/B2_REPORT.json) findings[REP-6] = PARTLY_FIXED（40 候補に inputs、18 候補に命令数、7 候補に資材分類別の内訳を追加。実時間とメモリは未測定。open_problems に「『厳密な閉形式が同じ手間』は AP-04（1 行あたり 14 命令対 112 命令）と AP-05 では支持されず、AP-06・AP-07b・AP-08・AP-09a/b では支持される」と自己申告）。patch の bench/approx_study.py に inputs_measured、approx_support.py に sys.monitoring を使う行がある。
- **停止時点で残っていた作業**：候補の実時間・メモリは測っていない。22 候補は負荷の数値なし。不採用理由の文の見直し（段階 C）は未着手。b2 の測定は未検証。
- **公開中の版**：残っている。04_VERIFICATION/approximation_study.json に負荷・入力数の鍵は無い（32 候補、旧の構造のまま）。

<a id="rep-7"></a>

### REP-7

- **重さ／判定**：中／反証検査なし
- **内容**：台帳の入力一覧は、拘束する基準計算が実際に使う入力を表していない：実測では基準計算は仕様の 77 項目と研究が加えた 56 項目を読むが、台帳は仕様 88 項目と 'NEW:' 28 項目を挙げる（台帳にあって読まれない仕様の入力が 12、読まれるのにどの単位も挙げない入力が 1、'NEW:' 28 のうち追加項目 73 に実在するのは 4）。「未接続だった 53 項目の扱い」の「追加単位で接続 14」のうち 3、「既存式が暗黙に使用 9」のうち 6 は読まれていない。05 の表の隣り合う 2 行（88＋28 と 77＋56）は説明なしに食い違う。
- **影響する成果**：01_LEDGER/units.json（各単位の inputs）、01_LEDGER/unlinked_input_disposition.json、01_LEDGER/README、05_DECISIONS/README の表（単位が参照する入力項目、計算中に読まれた入力項目）、04_VERIFICATION/input_usage.json
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/reports/`](../materials/round2_review/checker_scripts/reports) の findings_repro.py、recompute10.py（findings_repro.py は REP-7 の行）
- **担当する予定だった段階**：b3（ほかに C）
- **予定していた対応**：基準計算の属性の読み出しを単位ごとに追跡し、台帳の各単位に inputs_read_by_reference を書き込み、手書きの inputs は残したまま申告との差（inputs_declared_not_read、inputs_read_not_declared）を見えるようにする。05 の表は、どの行が申告でどの行が測定かを書く（SPEC_B3 項目 1、STAGE_C_NOTES）。
- **停止時点の状態**：未対応
- **作業担当の自己申告**：なし（段階は未着手）
- **状態の根拠**：b3 は未着手（STOP_STATUS 1・3 節）。patch の 01_LEDGER/units.json の変更は a1 の定義文の同期だけで、inputs_read_by_reference の追加行は 0。一方、手順書 v1.4 の草稿（60e720f、公開中）の P3 は、この欄を既にあるものとして説明している。
- **停止時点で残っていた作業**：すべて未着手。手順書の草稿が、台帳にまだ無い欄を説明している状態が残る。
- **公開中の版**：残っている。01_LEDGER/units.json のどの単位にも inputs_read_by_reference は無い（JSON を読んで確認）。05_DECISIONS/README 105 行に「116（既存 88＋追加 28）」が残る。

<a id="rep-8"></a>

### REP-8

- **重さ／判定**：低／反証検査なし
- **内容**：01_LEDGER/README の構造別の件数の表は「活動量×係数の総和 29、比・換算 11」と書くが、70 単位の structure_class を数えると 30 と 10 で、同じ README の単位の一覧も 30 と 10 を示す。units.json のヘッダの欄 structure_class_counts が古く、tools/sync_ledger.py が更新しない。ほかの 11 分類は一致する。
- **影響する成果**：01_LEDGER/README の表「数学的な構造別の件数」、01_LEDGER/units.json のヘッダ（structure_class_counts）、報告書生成器（tools/build_reports.py 102 行）、tools/sync_ledger.py
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/reports/`](../materials/round2_review/checker_scripts/reports) の findings_repro.py、recompute2.py（findings_repro.py は REP-8 の行）
- **担当する予定だった段階**：b3
- **予定していた対応**：units.json のヘッダの structure_class_counts を、tools.sync_ledger が毎回、単位から計算する（SPEC_B3 項目 3）。
- **停止時点の状態**：未対応
- **作業担当の自己申告**：なし（段階は未着手）
- **状態の根拠**：b3 は未着手。patch の 01_LEDGER/units.json に structure_class_counts の変更行は無い。tools/sync_ledger.py は patch に含まれない。
- **停止時点で残っていた作業**：すべて未着手。
- **公開中の版**：残っている。01_LEDGER/units.json のヘッダは LINEAR_SUM_PRODUCT 29・RATIO 11、単位を数えると 30・10（JSON を読んで数えた）。

<a id="rep-9"></a>

### REP-9

- **重さ／判定**：低／反証検査なし
- **内容**：文書どうしの食い違い：03_MODELS/README 68 行の「統合しなかった単位（4）…検査の 4 単位は」は、検査が 3 単位（C-05、QA-02、SYS-01）なので誤り（4 は生成器の固定の文字）。INDEPENDENT_REVIEW.md 2.3 の「検査は実際に共有の関数にした 3 単位だけを統合に数える」も、models.json が検査 9 単位のうち 6 単位（K6 の SYS-04・QA-01・QA-04 と K7 の SYS-02・SYS-03・QA-03）を統合に数えているのと合わない。
- **影響する成果**：03_MODELS/README 68 行（tools/build_reports.py 225 行）、04_VERIFICATION/INDEPENDENT_REVIEW.md 2.3（48 行）、03_MODELS/models.json
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/reports/`](../materials/round2_review/checker_scripts/reports) の findings_repro.py（findings_repro.py は REP-9 の行）
- **担当する予定だった段階**：C
- **予定していた対応**：報告書は「検査の 3 単位」をデータから計算して書き、INDEPENDENT_REVIEW.md の文は K6（3 単位）と K7（検査の 3 単位）を名指しする形に直す（STAGE_C_NOTES 7 と報告書の項）。
- **停止時点の状態**：未対応
- **作業担当の自己申告**：なし（段階は未着手）
- **状態の根拠**：段階 C は未着手。patch に tools/build_reports.py、03_MODELS/README.md、04_VERIFICATION/INDEPENDENT_REVIEW.md は含まれない。
- **停止時点で残っていた作業**：すべて未着手。
- **公開中の版**：残っている。03_MODELS/README 68 行に「検査の 4 単位」、04_VERIFICATION/INDEPENDENT_REVIEW.md 48 行に「3 単位だけ」が残る。

<a id="rep-10"></a>

### REP-10

- **重さ／判定**：低／反証検査なし
- **内容**：手書きの手順書と台帳の注記が古い：P7 の採否の語彙（ADOPT_EXACT など 5 語）はどの JSON・コード・報告書にも使われておらず、P4 の a2 は「基本演算回数」と書くが実際は実行したバイトコード命令数で、未測定の単位の規則と分類 UNDEFINED_MODEL は該当例が無い。台帳の A13-04 は、基準計算に関数があり computable_in_reference が true なのに、structure_subclass が UNDEFINED_MODEL のままで「基準計算には実装しない」と書いている。
- **影響する成果**：手順書（00_POLICY/EVALUATION_PROTOCOL.md の P3・P4・P7）、01_LEDGER/units.json の A13-04（手書きの欄）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/reports/`](../materials/round2_review/checker_scripts/reports) の check_sem.py（ほかは 09_APPROX_STUDY 内の語の検索）
- **担当する予定だった段階**：C（ほかに b3）
- **予定していた対応**：手順書は v1.4 で、使っていない語彙を現在の語彙に対応付け、a2 を実行バイトコード命令数に直し、使っていない規則に注記する（段階 C の手書き文書）。台帳の A13-04 の手書きの欄は「本研究が独立に設計した式を基準計算に実装済みで、精度を比べる相手は無い」という現状に直す（SPEC_B3 項目 5）。
- **停止時点の状態**：途中で停止
- **作業担当の自己申告**：なし（手順書の部分は主担当が 60e720f で先に改訂。台帳の部分は段階 b3 が未着手）
- **状態の根拠**：手順書の部分：git diff 43ba5d7 60e720f に、P3（UNDEFINED_MODEL と computable_in_reference の注記）、P4（a2 を「実行したバイトコード命令数」に変更、未測定の規則に注記）、採否の語彙の対応表がある（主担当の手書き、独立の検査なし、コミット文は work in progress）。台帳の部分：patch に A13-04 の「基準計算には実装しない」を消す行は無い。
- **停止時点で残っていた作業**：台帳 A13-04 の手書きの欄の訂正（段階 b3）は未着手。
- **公開中の版**：残っている。01_LEDGER/units.json 692 行に「基準計算には実装しない」、633 行に UNDEFINED_MODEL が残る（A13-04 の computable_in_reference は true）。手順書の P3・P4・P7 の部分は 60e720f の草稿で手当て済み（未検査）。

<a id="rep-11"></a>

### REP-11

- **重さ／判定**：低／反証検査なし
- **内容**：02_RANKING/README 11 行の「軸 A 22 件（重みを変えた場合だけ入るもの 6 件）、軸 B 30 件（境界の同点を含む）、和集合 42 件」は書き方が誤解を招く：6 件は 22 件に含まれず追加で、A（22）と B（30）の和集合は 38（重なり 14）、42 は感度分析だけで入る 6 件を含めた和集合である。順位付けのほかの数値は、入力からの再計算で差が 0 だった。
- **影響する成果**：02_RANKING/README 11 行、02_RANKING/research_priority.json（reference_top30_counts）、報告書生成器（tools/build_reports.py）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/reports/`](../materials/round2_review/checker_scripts/reports) の recompute3.py
- **担当する予定だった段階**：C
- **予定していた対応**：「軸 A 22 件、ほかに重みを変えた場合だけ入るもの 6 件、軸 B 30 件、これらの和集合 42 件（A と B だけなら 38 件）」と書き直す（STAGE_C_NOTES の報告書の項）。
- **停止時点の状態**：未対応
- **作業担当の自己申告**：なし（段階は未着手）
- **状態の根拠**：段階 C は未着手。patch に tools/build_reports.py と 02_RANKING/* は含まれない。
- **停止時点で残っていた作業**：すべて未着手。
- **公開中の版**：残っている。02_RANKING/README 11 行に「和集合 42 件」の元の文が残る。

<a id="rep-12"></a>

### REP-12

- **重さ／判定**：低／反証検査なし
- **内容**：「行ごとの係数の乗算…行別の出力を求めると 520 回＝行数」の計数器 row_factor_products は、詳細の分岐の中で行ごとに 1 回増えるだけで、その分岐は行ごとに複数回（製造、搬入、運搬、C3・C4 の各経路など）係数を掛ける。520 は分岐に入った行の数で、乗算の数ではない。表の読み出しの乗算は規模 S・M・L（260・2,600・26,000 行）で 2,058・10,798・70,273 回と行数より多いので、導出 D1 の「右辺は係数キーの数だけ乗算する」を「行数より少ない」と読んではならない。
- **影響する成果**：統合モデルの計数器（engine.py 469・574 行）、04_VERIFICATION/README の表「統合モデルが実際に行った演算の回数」、03_MODELS/README の M-ROWPROD、導出 D1 の読み方
- **再現の手順の所在**：専用のスクリプトなし（[`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md) REP-12 の REPRO は engine.py の該当行の読み取りと、04_VERIFICATION/unified_model_load.json の規模別の回数の読み取り）
- **担当する予定だった段階**：a2（ほかに C）
- **予定していた対応**：手置きの計数器をやめ、行ごとの係数の乗算を外から数える測定（bench/mechanism_probe.py）に置き換え、表の読み出しの回数を規模別に行数と並べて示す（SPEC_A2 1・3 節、STAGE_C_NOTES の報告書の項）。
- **停止時点の状態**：途中で停止
- **作業担当の自己申告**：報告なし（段階 a2 は報告前に停止）
- **状態の根拠**：a2 は報告前に停止。patch の engine.py から row_factor_products の行が削除され、新規の bench/mechanism_probe.py がある。[`materials/interrupted_fix/a2_partial_outputs/mechanism_probe_UNVERIFIED.json`](../materials/interrupted_fix/a2_partial_outputs/mechanism_probe_UNVERIFIED.json) の P1 の evidence に規模別の乗算の回数の鍵がある（未検証）。報告書生成器は patch に含まれない。
- **停止時点で残っていた作業**：a2 の受け入れ確認の記録が無い。報告書の表と文の改訂（段階 C）は未着手。
- **公開中の版**：残っている。fastcalc/engine.py 469 行と 574 行に row_factor_products が残り、04_VERIFICATION/README に 520 の記述が残る。

<a id="rep-13"></a>

### REP-13

- **重さ／判定**：低／反証検査なし
- **内容**：candidates.json と approximation_study.json は、共有する 1,521 個の数値・フラグが同一だが、候補を付けた単位の一覧（units）が 7 候補で食い違う（AP-06、AP-17、AP-18a、AP-22a、AP-11、AP-16、AP-15）。別に、04_VERIFICATION/README は AP-06b の「過小評価」の欄を「—」としているが、その行の誤差は 175,143 行の 100％ で負（最大 -1.4％）である。
- **影響する成果**：03_MODELS/candidates.json、04_VERIFICATION/approximation_study.json、04_VERIFICATION/README の AP-06b の行
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/reports/`](../materials/round2_review/checker_scripts/reports) の recompute6.py、recompute7.py
- **担当する予定だった段階**：b2（ほかに C）
- **予定していた対応**：approximation_study.json を候補と単位の対応の唯一の出所にし（段階 b2）、記録生成器の計画がそれと一致することを検査する。AP-06b には過小評価「あり」を出す（SPEC_B2 項目 11、STAGE_C_NOTES 4）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：PARTLY_FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/B2_REPORT.json`](../materials/interrupted_fix/agent_reports/B2_REPORT.json) findings[REP-13] = PARTLY_FIXED（対応の差を解消：AP-06 から X-13 を除く、AP-17 に C2-01、AP-18a に B4-01、AP-22a から X-05 を除く、AP-11・AP-16 に X-02（段階水準）、AP-15 は 33 単位を明示。AP-06b は under_estimates = true、と自己申告）。patch の bench/approx_meta.py に AP-06b がある。candidates.json の生成と README の欄は「後段」。
- **停止時点で残っていた作業**：candidates.json の生成と README の欄の改訂（段階 C）は未着手。
- **公開中の版**：残っている。単位の一覧の食い違いが残る（例：AP-06 は candidates.json で ['A13-05']、approximation_study.json で ['A13-05', 'X-13']。JSON を読んで確認）。

<a id="rep-14"></a>

### REP-14

- **重さ／判定**：低／反証検査なし
- **内容**：M6 の NOT_APPLICABLE の定型の理由「…（場合分けは厳密な計算どうしで、M1 に記録した）」を持つ 17 単位（A13-05、A5-04、B1-01、B2-01、B3-02、B7-04、STO-01、STO-02、SUM-01〜08、X-13）は、M1 が NOT_APPLICABLE で、場合分けの記録が無い。
- **影響する成果**：記録 03_MODELS/records/units.json の NA-*-M6、記録生成器（tools/build_records.py NA_HYBRID）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/reports/`](../materials/round2_review/checker_scripts/reports) の findings_repro.py、recompute5.py（findings_repro.py は REP-14 の行）
- **担当する予定だった段階**：C
- **予定していた対応**：M1 の記録が無い単位には、「M1 に記録した」を含まない理由文を使う（STAGE_C_NOTES 3）。
- **停止時点の状態**：未対応
- **作業担当の自己申告**：なし（段階は未着手）
- **状態の根拠**：段階 C は未着手。tools/build_records.py は patch に含まれない。
- **停止時点で残っていた作業**：すべて未着手。
- **公開中の版**：残っている。03_MODELS/records/units.json に「M1 に記録した」を含む行が 51 行ある（文字列で確認。17 単位の内訳は数えていない）。

<a id="rep-15"></a>

### REP-15

- **重さ／判定**：低／反証検査なし
- **内容**：最上位の README は成果物 6 の一部として「独立した検査」を限定なしに挙げているが、INDEPENDENT_REVIEW.md と 06_OPEN_ISSUES D-3 は、独立の検査は初版だけに行い「対応後の版に対する独立した検査は、まだ行っていない」と書いている。README の数値（681 シナリオ、66.3％、7 モデル、454 記録）はすべて改訂後の版のもので、README の「この研究で言えないこと」にその旨が無い。
- **影響する成果**：README（成果物の表の 6 行目、「この研究で言えないこと」）、04_VERIFICATION/README 5 節、04_VERIFICATION/INDEPENDENT_REVIEW.md、06_OPEN_ISSUES D-3
- **再現の手順の所在**：専用のスクリプトなし（[`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md) REP-15 の REPRO は README、INDEPENDENT_REVIEW.md、06_OPEN_ISSUES の語の検索）
- **担当する予定だった段階**：C
- **予定していた対応**：INDEPENDENT_REVIEW.md に第 2 回の節（59 件の指摘と対応の表、修正後のコードへの反証検査の結果）を加えて「まだ行っていない」を除き、最上位の README の限定を書き直す（STAGE_C_NOTES の手書き文書の項）。
- **停止時点の状態**：未対応
- **作業担当の自己申告**：なし（段階は未着手）
- **状態の根拠**：STOP_STATUS 3 節：「第2回の検査結果を 04_VERIFICATION/INDEPENDENT_REVIEW.md に記録」は未着手。INDEPENDENT_REVIEW.md は patch に含まれない。
- **停止時点で残っていた作業**：すべて未着手。改訂後の版（43ba5d7）に対する独立の検査は、この第 2 回が行ったが、その結果は 09_APPROX_STUDY の中のどの文書にも記録されていない（保存先は research_archive の triage）。
- **公開中の版**：残っている。04_VERIFICATION/INDEPENDENT_REVIEW.md 7 行と 06_OPEN_ISSUES/README.md 75 行に「まだ行っていない」が残り、どちらにも第 2 回の記載は無い。HEAD の README 冒頭の手書きの追記が、本文は第 2 回の指摘を反映していないと注意している（本文は未修正）。

<a id="rep-16"></a>

### REP-16

- **重さ／判定**：低／反証検査なし
- **内容**：評価期間を変えたときの照合（64 シナリオ、9 期間、172,404 個の値、最大 1.1e-13）は、70 単位のうち 22 単位の合計のみの出力を、基準案との比較を切って、小さな 64 シナリオで比べたもので、README はこの範囲を書いていない。SUM-06、SUM-07、X-07、B4-01、SUM-08 など評価期間に依存する出力は対象に入っていない。数値自体は JSON と一致する。
- **影響する成果**：04_VERIFICATION/README「評価期間を変えたとき」の節、04_VERIFICATION/unified_model_exactness.json（period_sweep）、検証スクリプト（bench/verify_unified.py sweep_check、172〜197 行）
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/reports/`](../materials/round2_review/checker_scripts/reports) の findings_repro.py（findings_repro.py は REP-16 の行）
- **担当する予定だった段階**：a1（ほかに C）
- **予定していた対応**：sweep_check が、スイープの返す全単位を（手書きの 22 単位の一覧ではなく）基準案との比較を付けたまま比べ、比べた単位とシナリオ数を結果に記録する（SPEC_A1 項目 17）。README の文は段階 C で直す。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[REP-16] = FIXED（sweep_check(40)：65 シナリオ、70 単位、309705 個の値、最大 1.093e-13 と自己申告）。patch の bench/verify_unified.py から SWEEP_UNITS が削除され、engine.sweep(..., compare=True) の呼び出しが追加されている。
- **停止時点で残っていた作業**：一致検証の JSON の再生成と README の文の改訂（段階 C）は未着手。
- **公開中の版**：残っている。bench/verify_unified.py 43 行に SWEEP_UNITS が残り、unified_model_exactness.json の period_sweep.units は 22 単位（JSON を読んで確認）。

<a id="rep-17"></a>

### REP-17

- **重さ／判定**：低／反証検査なし
- **内容**：取り決めの一覧が不完全：どちらの計算も、電力係数の年次表の長さが ceil(T) より短いと、記述子で定義された電力係数（表は冗長な写し）でも ValueError を出すが、この規則は B-1〜B-21 にも導出の「当てはまらない範囲」にも無い（B-21 は不正な評価期間だけをエラーとし、B-16 は表を写しとする）。「行の合算をやり直さずに別の評価期間を計算できる」という主張も、表の長さ（生成器の既定は max(130, ceil(T)+1)）までの T に限られる。
- **影響する成果**：06_OPEN_ISSUES B 節（B-16、B-21）、導出「導出が当てはまらない範囲」（03_MODELS/DERIVATIONS.md）、基準計算（refcalc/base.py 74〜75 行）と統合モデル（engine.py 774 行）の check_period
- **再現の手順の所在**：専用のスクリプトなし（[`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md) REP-17 の REPRO は refcalc/base.py と fastcalc/engine.py の 'shorter' の検索）
- **担当する予定だった段階**：a1（ほかに C）
- **予定していた対応**：check_period から、短い電力係数の表による ValueError を両方の計算で除き、エラーは不正な評価期間だけにする（B-21 を真にする）。短い表は、整った記述子が無いときにだけ電力係数を使えなくする（SPEC_A1 項目 8。検査担当の案「B-22 として取り決めに加える」とは違う決定）。
- **停止時点の状態**：中断時の編集で対応（自己申告・未検証）
- **作業担当の自己申告**：PARTLY_FIXED
- **状態の根拠**：[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json) findings[REP-17] = PARTLY_FIXED（コードと base.py の取り決めの文は変更、06_OPEN_ISSUES B-16・B-21 と DERIVATIONS は未実施）。patch で refcalc/base.py と engine.py の 'shorter than the study period' の行が削除されている。
- **停止時点で残っていた作業**：06_OPEN_ISSUES と導出の改訂（段階 C）は未着手。
- **公開中の版**：残っている。refcalc/base.py 75 行と fastcalc/engine.py 774 行に 'shorter than the study period' の ValueError が残る。06_OPEN_ISSUES に B-22 は無い。

<a id="rep-18"></a>

### REP-18

- **重さ／判定**：低／反証検査なし
- **内容**：シート族の対応状況の名札が一貫して付けられていない：COVERED_BY_EXISTING の 3 族が追加単位（X-02、X-03、X-05、X-15）を関連単位に挙げ（19,388 ノード＝「0.81％」の行の 62％）、NON_CALCULATION の 11 族が関連単位 X-15・X-16 を持ち、数式 0 件の別の 3 族は COVERED_BY_ADDITIONAL になっている。ノード比率への影響は 0.6 ポイント未満で、units.json との結び付き自体は不整合 0 件である。
- **影響する成果**：01_LEDGER/sheet_family_coverage.json、01_LEDGER/README の表「シート名からの対応状況」
- **再現の手順の所在**：[`materials/round2_review/checker_scripts/reports/`](../materials/round2_review/checker_scripts/reports) の findings_repro.py、recompute1.py（findings_repro.py は REP-18 の行）
- **担当する予定だった段階**：b3
- **予定していた対応**：状態を規則で決めて tools.sync_ledger が付ける：数式ノード 0 の族は常に NON_CALCULATION、ほかは関連単位の種類で COVERED_BY_ADDITIONAL・COVERED_BY_EXISTING・COVERED_BY_BOTH、関連単位なしは NOT_INSPECTED とする（SPEC_B3 項目 4）。
- **停止時点の状態**：未対応
- **作業担当の自己申告**：なし（段階は未着手）
- **状態の根拠**：b3 は未着手。patch に 01_LEDGER/sheet_family_coverage.json と tools/sync_ledger.py は含まれない。
- **停止時点で残っていた作業**：すべて未着手。
- **公開中の版**：残っている。09_APPROX_STUDY の 01_LEDGER/sheet_family_coverage.json は 43ba5d7 と同一（個別の名札は読み直していない）。

## この登録簿が扱っていないこと

- REP の 18 件を「検査担当のスクリプトの再実行で再現した」という事実は BRIEF.md の記述による。res.json の reports の部分に判定は無く、保存した checker_scripts/reports/ に再実行の出力ファイルは無いので、この読み取りでは再現を確認していない。
- 状態の判断は文字列と JSON の読み取りだけによる。65ff124 のコードが試験に通るか、指摘の再現が消えるかは確認していない（確認には旧研究の実行が必要で、禁じられている）。「中断時の編集で対応」は、段階の作業担当の報告と、patch に対応する編集があることを意味するだけである。
- 65ff124 の作業ツリー全体としての試験結果は無い。a1 の「68 件の試験 OK」は a2 が fastcalc を編集する前の時点、b2 の「106 件の試験 OK」は a2 の編集の途中の時点の自己申告で、b2 は a2 の試験（tests/test_mechanism_probe.py）が 1 回だけ失敗したことも申告している。STOP_STATUS 6 節によれば、停止後は Python の 22 ファイルが構文として読めることだけを確かめている。
- a2 の途中の編集（engine.py の改造、membership_check.py、mechanism_probe.py）が仕様をどこまで満たすかは判定していない。a2 の報告も受け入れ確認の記録も無い。a2_partial_outputs の 2 つの JSON は、構造と一部の鍵だけを読んだ。
- patch（723 KB）は全文を読んでいない。指摘ごとに選んだ目印の文字列の有無を数えただけなので、編集が指摘を正しく直しているかどうかは分からない。
- 公開中の版に問題が残るかどうかは、(a) 09_APPROX_STUDY が README 冒頭の手書きの追記を除いて 60e720f と同一、(b) 60e720f と 43ba5d7（検査担当が調べた版）の差が手順書 1 ファイルだけ、という git diff の結果と、該当の行・文言・JSON の値の読み取りによる。挙動の再現はしていない。committed_check に「個別の文字列確認はしていない」と書いた指摘（NUM-6、NUM-7 など）は (a)(b) だけが根拠である。
- 各 triage の末尾にある検証担当の追加所見（ADDITIONAL）と、検査担当が確認できなかった範囲（COULD NOT CHECK）は、59 件の番号を持たないので独立の項目にしていない。既存の指摘の補足になるものは statement に取り込んだ（NUM-1・REC-1 の「基準計算の側が丸めの産物」、RED-10 の追加の 3 か所、APP-1 の「目標を満たすとは言えない」、APP-2 の B2-01 の記録、APP-4 の恒等式）。rederive の追加所見 1（検査のない非有限の入力で基準計算と統合モデルが食い違う）は NUM-2・RED-2 と同じ原因である。
- 保存した checker_scripts のスクリプトは旧研究のコード（refcalc、fastcalc、synth、bench）を読み込むので、実行すると旧研究の計算を再開することになる。43ba5d7 のコードに対して書かれており、スクリプト内の出力先は停止前の作業用フォルダ（/tmp 配下）を指している。repro_files は存在だけを確認した。
- B2_REPORT_long.json、conclusion_proposals.json、candidate_lines.json（b2 の長い報告と結論文の案）は中身を読んでいない。候補ごとの結論文の案はこの登録簿に入っていない。
- 反証検査の反復（VERIFY_NUM、VERIFY_DEF、修正の反復）は未着手なので、修正後のコードに対する新しい指摘の一覧は存在しない。
- severity は検査担当が付けた値である。検証担当が違う重大度を述べた指摘（APP-1 と APP-4 は LOW 相当、RED-7 は MEDIUM の下端、APP-3 は LOW〜MEDIUM）は statement に書いたが、severity の欄は変えていない。
