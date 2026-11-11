# 索引の詳細 T09：記録・進捗台帳・報告書・必須成果物

[INDEX.md](../INDEX.md) の項目ごとの詳細。分類担当（読み取り専用）が書いた内容を、欄ごとにそのまま載せる。
旧研究の数値はすべて架空データでの値で、対象は独立概念モデルである。原版の表計算との一致や、実建物での精度を示すものではない。
所在の表記：`09_APPROX_STUDY/…` などは `whole-life-carbon-jcat-study/` からの位置、`materials/…` はこの保存フォルダからの位置。

| 項目 | 区分 | 題 |
|---|---|---|
| [CK-R5-01](#ck-r5-01) | 1 | 記録・進捗台帳・報告書の件数と相互参照の整合（数え直しで一致した範囲） |
| [CK-R5-02](#ck-r5-02) | 2 | 単位別の検討記録 454 件（記録とは何か、どんな裏付けを名乗っているか） |
| [CK-R5-03](#ck-r5-03) | 2 | 厳密な段階（M1・M2）の成功記録 118 件 |
| [CK-R5-04](#ck-r5-04) | 4 | 成功記録の裏付けの表示の誤り（「3 つの裏付け」と、仕組みの計数） |
| [CK-R5-05](#ck-r5-05) | 2 | 近似の段階の「不採用」記録 39 件（候補 16 種） |
| [CK-R5-06](#ck-r5-06) | 3 | 近似の段階の「保留」記録 71 件（候補 16 種。実データ待ち） |
| [CK-R5-07](#ck-r5-07) | 3 | 「候補なし」記録 226 件（測定をしていない判断） |
| [CK-R5-08](#ck-r5-08) | 2 | 進捗台帳（progress_ledger.json と PROGRESS.md）の構造と判定の規則 |
| [CK-R5-09](#ck-r5-09) | 4 | 状態別の件数 3／66／0／0／0／1 のうち、第2回の指摘と矛盾する数 |
| [CK-R5-10](#ck-r5-10) | 2 | 自動生成の報告書 6 点と PROGRESS.md（文面としての状態） |
| [CK-R5-11](#ck-r5-11) | 1 | README の要点 1「評価単位は 70 件（53＋17）。全件を研究対象にした」 |
| [CK-R5-12](#ck-r5-12) | 4 | README の要点 2「66 単位が 7 つの統合モデルに、結果を変えずにまとまった」 |
| [CK-R5-13](#ck-r5-13) | 2 | README の要点 3「統合モデルは基準計算と一致した」 |
| [CK-R5-14](#ck-r5-14) | 2 | README の要点 4「計算の重さは減った」 |
| [CK-R5-15](#ck-r5-15) | 2 | README の要点 5「近似は 1 つも採用していない」 |
| [CK-R5-16](#ck-r5-16) | 2 | README の要点 6「入力項目は減っていない」 |
| [CK-R5-17](#ck-r5-17) | 2 | README の要点 7「材料・用途・構造の違いは式に現れず、データの違いとして扱う（設計上）」 |
| [CK-R5-18](#ck-r5-18) | 2 | 05_DECISIONS/README.md の採否の理由（採用・不採用・保留・現状維持の文面） |
| [CK-R5-19](#ck-r5-19) | 2 | 05_DECISIONS/README.md「統合前後の変化」の表（行ごとの状態） |
| [CK-R5-20](#ck-r5-20) | 2 | 旧指示書の必須成果物 9 点（有無と状態） |
| [CK-R5-21](#ck-r5-21) | 4 | 評価者の提案との対照（judge_proposal_trace.json）：観点と段階の対応づけの誤り |
| [CK-R5-22](#ck-r5-22) | 4 | 未解決事項の一覧（06_OPEN_ISSUES/README.md の A〜H） |
| [CK-R5-23](#ck-r5-23) | 4 | 未解決事項の一覧に載っていない事項と、古くなった記述（第2回で判明） |
| [CK-R5-24](#ck-r5-24) | 2 | 第1回の独立検査の記録（INDEPENDENT_REVIEW.md：指摘と対応） |
| [CK-R5-25](#ck-r5-25) | 4 | 検査の記録の欠落と、検査されていない範囲 |
| [CK-R5-29](#ck-r5-29) | 2 | 記録・台帳・報告書の生成器（research_code/tools/ の 5 本）：どの生成器がどのファイルを書くか |

<a id="ck-r5-01"></a>

## CK-R5-01　記録・進捗台帳・報告書の件数と相互参照の整合（数え直しで一致した範囲）

- **区分**：1　検証済み成果
- **根拠の強さについての注記（索引の作成者）**：件数と相互参照の数え直しだけである。内容が正しいことの確認ではない。
- **内容**：単位別の記録（454 件）、進捗台帳（70 単位）、統合モデルの目録、自動生成の報告書 6 点と PROGRESS.md の間で、件数・状態・所属が互いに食い違っていないという事実。記録の中身が正しいかどうかとは別の事柄である。
- **所在**：
  - [`09_APPROX_STUDY/03_MODELS/records/units.json`](../../../09_APPROX_STUDY/03_MODELS/records/units.json)
  - [`09_APPROX_STUDY/05_DECISIONS/progress_ledger.json`](../../../09_APPROX_STUDY/05_DECISIONS/progress_ledger.json)
  - [`09_APPROX_STUDY/05_DECISIONS/PROGRESS.md`](../../../09_APPROX_STUDY/05_DECISIONS/PROGRESS.md)
  - [`09_APPROX_STUDY/03_MODELS/models.json`](../../../09_APPROX_STUDY/03_MODELS/models.json)
  - [`09_APPROX_STUDY/README.md`](../../../09_APPROX_STUDY/README.md)
  - [`09_APPROX_STUDY/03_MODELS/README.md`](../../../09_APPROX_STUDY/03_MODELS/README.md)
  - [`09_APPROX_STUDY/05_DECISIONS/README.md`](../../../09_APPROX_STUDY/05_DECISIONS/README.md)
- **確かめ方**：第2回の検査（報告書の観点）が、報告書 6 点をメモリ上で再生成してディスク上のファイルとバイト単位で一致することを確かめ、記録 454 件（成功 118、不採用 39、保留 71、候補なし 226）、状態別の件数 3／66／0／0／0／1、保留のある 44 単位、段階別の単位数、PROGRESS.md の表 910 セルを JSON から数え直した。第2回の検査（記録の観点）が、手順書 P10 の規則を独自に書いて 70 単位の状態と段階の結論を記録から求め、保存値と一致した。この読み取りでも JSON を読み込んで数え直し、454 件、118／39／71／226、66／3／1、44 を確認した（旧研究のコードは実行していない）。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：43ba5d7 の版のファイルどうしの整合に限る。架空データと独立概念モデルについての記録の整合であり、記録の中身（一致の主張、統合の所属、理由文）が正しいことは意味しない。
- **関係する第2回の指摘**：REP-1、REP-8、REP-9、REP-13、REP-2、REP-7、REP-11、REP-14、REP-18
- **第2回の指摘の影響**：件数と相互参照が整合しない箇所として、次の 4 件が指摘された。REP-1：04_VERIFICATION の「0 項目は記録用」は、使われていない番兵から作った数。REP-8：01_LEDGER の構造別の件数の表は、units.json の古い見出しを写しており 2 行が違う。REP-9：03_MODELS の「検査の 4 単位」は生成器の固定文。REP-13：candidates.json と approximation_study.json で、候補が付く単位の一覧が 7 候補で違う（共通する数値とフラグ 1,521 個は一致）。このほか、REP-2（52／20 は別の観点を数えた値）、REP-7（05_DECISIONS の表の隣り合う 2 行 88＋28 と 77＋56 が説明なしに食い違う）、REP-11（和集合 42 件は A と B だけなら 38 件）、REP-14（17 単位の M6 の理由文が、存在しない M1 の記録を参照している）、REP-18（シート族の状態の区分が一貫しない）も、報告書や記録の内部の食い違いを指摘している。
- **今の時点で言ってよいこと**：09_APPROX_STUDY の自動生成の報告書は、43ba5d7 の時点で、同じ版の JSON から再生成したものと一致した（古い報告書が残っているのではない）。公開中の版の README.md には、その後に手書きの終了の注記（冒頭の枠）を加えてある。records/units.json と progress_ledger.json はどちらも 454 件で、候補・結論・理由・段階の結論に不一致 0。models.json・記録・進捗台帳の所属に不一致 0。research_priority.json と進捗台帳の着手順・群に不一致 0。70 単位の状態は、記録から P10 の規則どおりに求めた値（統合成功 66、簡略化成功 3、保留 1）と同じである。
- **使ってはいけない記述**：
  - 数が JSON と一致していることを、内容が検証済みであることの根拠にする読み方
  - build_reports.py の冒頭の説明「reports cannot drift from the data」を、報告書の文面に誤りがないという意味に読むこと（REP-1・REP-8・REP-9 は生成器またはデータの見出しの誤り）
- **新研究での再利用**：候補（ルート A・C）
  - 使い道：旧研究の公表済みの数字を引用するときに、どのファイルのどのキーから来た数かをたどる手掛かりにする。
  - 条件・注意：引用できるのは「旧研究がそう記録した」という事実まで。数字の意味と成り立つ範囲は、各項目（CK-R5-09、CK-R5-11〜17 など）の限定に従う。
- **分類の根拠**：
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):128（CHECKS PERFORMED 1：6 報告書がバイト一致、05_DECISIONS と PROGRESS.md と第9章 README の数字が JSON と一致。7：台帳どうしの不一致 0）
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):110（CHECKS PERFORMED 6：70 単位の状態と段階の結論を独自に再計算して一致、454 件）
  - [`09_APPROX_STUDY/03_MODELS/records/units.json`](../../../09_APPROX_STUDY/03_MODELS/records/units.json): record_count = 454
  - [`09_APPROX_STUDY/05_DECISIONS/progress_ledger.json`](../../../09_APPROX_STUDY/05_DECISIONS/progress_ledger.json): units[].status を数えると DONE_UNIFIED 66、DONE_SIMPLIFIED 3、HOLD_DATA_OR_RIGHTS 1
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）
- **停止後の点検による訂正**：点検の指摘 V2-03、V2-11 により、上の記述の一部を改めた。分類担当の元の記述は `materials/classification/R5.json`、訂正の内容は `materials/classification/overrides.json` にある。

<a id="ck-r5-02"></a>

## CK-R5-02　単位別の検討記録 454 件（記録とは何か、どんな裏付けを名乗っているか）

- **区分**：2　暫定・未検証成果
- **内容**：評価単位×検討段階（M1〜M6）×候補を 1 件とする記録の集まり。項目は unit_id、step、candidate_id、title、outcome（SUCCESS／REJECTED／HOLD／NOT_APPLICABLE）、verification（VERIFIED_ANALYTIC_AND_SYNTHETIC／VERIFIED_SYNTHETIC_ONLY／NOT_VERIFIED）、unified_model、mechanism、derivation、reason、data_needed、evidence。tools/build_records.py が、ファイル内に手書きされた計画表（plan）と測定結果の JSON から生成する。
- **所在**：
  - [`09_APPROX_STUDY/03_MODELS/records/units.json`](../../../09_APPROX_STUDY/03_MODELS/records/units.json)
  - [`09_APPROX_STUDY/research_code/tools/build_records.py`](../../../09_APPROX_STUDY/research_code/tools/build_records.py)
  - [`09_APPROX_STUDY/03_MODELS/README.md`](../../../09_APPROX_STUDY/03_MODELS/README.md)
- **確かめ方**：生成時の機械的な確認は 3 種類。厳密な記録（EX）：unified_model_exactness.json でその単位の不一致が 0 で最大の相対差が許容差以下であること、引用した導出の見出しが DERIVATIONS.md にあること。近似の記録（AP）：宣言した結論が approximation_study.json の統計と矛盾しないこと。候補なしの記録（NA）：確認なし。件数は、成功 118、不採用 39、保留 71、候補なし 226。段階別は M1 70、M2 70、M3 86、M4 84、M5 74、M6 70。verification は「導出と架空データ」137、「架空データのみ」91、「未検証」226（この読み取りで数えた）。
- **確かめた者**：作成者のみ（件数と進捗台帳との整合は独立検査（第2回）で再現。裏付けの表示は第2回で誤りを指摘され、未修正）
- **言える範囲**：架空データ、独立概念モデルの 70 単位。43ba5d7 のコードと測定に対応する記録で、第1回の検査の指摘を受けて作り直した版である。
- **関係する第2回の指摘**：REC-1、REC-2、REC-3、REC-4、REC-5、REC-6、REC-7、REC-8、REC-9、REP-2、REP-3、REP-5、REP-13、REP-14
- **第2回の指摘の影響**：記録が名乗る裏付けの型が実際と違う（REC-5・REP-3：注記は「成功は 3 つの裏付けがあるものだけ。なければ生成が失敗する」と述べるが、機構と導出は任意の引数で、欠けていても生成は失敗しない）。機構の確認は単位ごとではなく、1 つの架空シナリオでの全体の計数である（REC-4・REC-5）。M2 の成功記録のうち少なくとも 3〜4 件は統合の基準を満たさない（REC-2）。候補なしの理由の一部は事実と違う（REC-8・REP-14）。第2回の指摘は記録に反映されていない。
- **今の時点で言ってよいこと**：記録は「旧研究が各単位・各段階で何を試し、どう結論したか」の一覧として読める。成功 118 件のうち、出力の一致・機構の記号・導出の 3 つがそろうのは 96 件。機構の記号がないもの 18 件、導出がないもの 5 件、どちらもないもの 1 件（EX-QA-04-M1）。機構の記号がある記録は全体で 100 件、導出がある記録は 113 件である。
- **使ってはいけない記述**：
  - units.json の注記「SUCCESS は、出力の一致・仕組みの計数・導出の 3 つに裏付けがあるものだけ（裏付けがなければ生成が失敗する）」
  - 03_MODELS/README.md 149 行「SUCCESS は、(1) 出力が基準計算と一致、(2) 述べている仕組みが計数で確かめられる、(3) 導出が DERIVATIONS.md にある、の裏付けを生成時に確かめたもの」
  - research_code/README.md「記録の生成は、出力の一致・仕組みの計数・導出のどれかに裏付けのない『成功』…があると失敗する」
  - 手順書 P8 の「SUCCESS の記録は (1)(2)(3) を記録の生成時に機械的に確かめる」
  - verification = VERIFIED_ANALYTIC_AND_SYNTHETIC を、その単位の式が導出と測定の両方で確かめられたという意味で引用すること（機械的に確かめているのは、導出の見出しが存在することだけ）
- **新研究での再利用**：候補（ルート A・C）
  - 使い道：旧研究が単位ごとに何を試したかの索引として使う。
  - 条件・注意：検証の根拠としては使わない。成功の根拠が要るときは、unified_model_exactness.json の単位別の結果と、REC-1・REC-2・REC-6 の限定を合わせて読む。記録を作り直す作業（Stage C）は未着手のまま終了している。
- **分類の根拠**：
  - [`09_APPROX_STUDY/research_code/tools/build_records.py`](../../../09_APPROX_STUDY/research_code/tools/build_records.py):1-27（記録の種類と出力ファイル）
  - [`09_APPROX_STUDY/research_code/tools/build_records.py`](../../../09_APPROX_STUDY/research_code/tools/build_records.py):137（EX の引数 model・mech・deriv は任意）
  - [`09_APPROX_STUDY/research_code/tools/build_records.py`](../../../09_APPROX_STUDY/research_code/tools/build_records.py):463-480（失敗するのは一致が崩れたときと、導出の見出しがないときだけ）
  - [`09_APPROX_STUDY/research_code/tools/build_records.py`](../../../09_APPROX_STUDY/research_code/tools/build_records.py):500-504（注記の文）
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):49-59（REC-5：96 件が 3 つそろう、18 件は機構なし、5 件は導出なし）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):15-20（REP-3）
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

<a id="ck-r5-03"></a>

## CK-R5-03　厳密な段階（M1・M2）の成功記録 118 件

- **区分**：2　暫定・未検証成果
- **内容**：厳密な簡略化（M1：52 単位）と厳密な統合（M2：66 単位）について「基準計算と同じ結果になる」とした記録。理由文は「出力が基準計算と一致（681 シナリオ、数値 n 個、最大の相対差 …）」と、機構の記号があれば「仕組みの確認：…」からなる。
- **所在**：
  - [`09_APPROX_STUDY/03_MODELS/records/units.json`](../../../09_APPROX_STUDY/03_MODELS/records/units.json)
  - [`09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json`](../../../09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json)
  - [`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md)
- **確かめ方**：単位ごとの出力の一致は unified_model_exactness.json（681 架空シナリオ、許容差 相対 1e-9）による。第2回の検査（記録の観点）は、118 件の題名をすべて engine.py・closed_forms.py と読み合わせ、係数の読み出しや行の読み取りを数える仕掛けを入れて確かめ、記録を「正確」「正確だが留保つき」「言い過ぎ」「誤り・統合の基準を満たさない」に分けた。
- **確かめた者**：独立検査（第2回）で一部を再現、一部に誤りを指摘（REC-1・2・4・5・7 は CONFIRMED、REC-3・6 は PARTLY_CONFIRMED。未修正）
- **言える範囲**：架空データ、独立概念モデル、681 シナリオ、許容差 相対 1e-9。記録が述べる計算の仕組みの多くは「合計のみの出力」の場合に限る。
- **関係する第2回の指摘**：REC-1、REC-2、REC-3、REC-4、REC-5、REC-6、REC-7、NUM-1、REP-3、REP-4
- **第2回の指摘の影響**：誤り・統合の基準を満たさない記録：EX-A13-05-M2、EX-X-13-M2、EX-B1-01-M2、EX-SYS-03-M2（A13-05 は「行の乗数であること」を所属と認めるかどうかで判断が分かれる）、EX-QA-03-M2（K7 ではなく K1 の表から読んでいる）、EX-A5-01-M1・M2（単一の値に電力係数を掛けてから表に入れるだけで、簡略化も実質の統合もない）。言い過ぎの記録：EX-SYS-02-M1・EX-X-15-M1（「組ごとに 1 回」は行ごとの換算を持たない行だけ）、EX-B4-02-M1（明示の更新年一覧を持つ設備は行ごとに足す）、EX-QA-03-M1（使用した係数の集合の出所）、EX-B6-04-M2（所属が弱い）。EX-X-07-M2 は検査担当が弱いとし、検証担当は全出力の場合は擁護できるとした。留保つきの記録：EX-B3-01-M1・M2（周期 1.000000001 年で基準計算と食い違う）、B6-01・B6-02・B6-04・B7-01〜03・X-06 の M1・M2（引用した一致は年ごとの繰り返しで作った年次系列とフラグの一致で、閉形式そのものは B6-03・B7-04・B2-01・X-11 と合計を通してだけ確かめられている）、B4-01・B4-03・B5-01 の M1（周期の行については正しい）、EX-QA-02-M1（引用した機構の計数が、その処理を覆っていない）。
- **今の時点で言ってよいこと**：118 件のそれぞれについて、その単位の出力が 681 架空シナリオで基準計算と相対 1e-9 以内で一致したという測定が記録されている。第2回の検査（記録の観点）が題名とコードを読み合わせて「正確」とした記録は、A13-01、A13-03、A13-04、X-01、A4-01、A4-02、A5-02、A5-03、C1-01、C2-01、C3-01、C4-01、X-14、X-12、X-16 の M1・M2 と、records.md の CHECKS PERFORMED 1 に列挙された記録である（値は表の合計から得ており、合計のみの出力では資材・設備の行ごとに係数を掛けていない）。
- **使ってはいけない記述**：
  - 「成功 ＝ その単位の計算が題名どおりに簡略化・統合された」という一律の読み方
  - EX-B3-01-M1・M2 を「どの入力でも一致する」記録として引用すること
  - 理由文の「数値 n 個」を、閉形式を確かめた量として引用すること（B6-02、B7-01〜03 などでは年次系列の葉の数）
  - 上に挙げた「誤り」「言い過ぎ」の記録の題名
  - D8 の「SYS-03・QA-03 はこの解決の結果から読める」と D6 の最後の行（コードと合わない。REC-2・REC-7）
- **新研究での再利用**：候補（ルート A・C）
  - 使い道：どの単位のどの簡略化が題名どおりだったかの一覧として、Route A で旧成果から使う部分を選ぶ材料にする。
  - 条件・注意：第2回の検査の分類（records.md 110 行）と合わせて読む。「正確」とされた記録も、681 架空シナリオの範囲での一致である。所属を測定で確かめ直す作業（a2）は途中で止まっており、結果はない。
- **分類の根拠**：
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):110（CHECKS PERFORMED 1：118 件の分類、2：66 の所属）
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):1-11（REC-1）
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):13-23（REC-2）
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):61-71（REC-6）
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):73-83（REC-7）
  - [`09_APPROX_STUDY/03_MODELS/records/units.json`](../../../09_APPROX_STUDY/03_MODELS/records/units.json): outcome = SUCCESS の 118 件（M1 52、M2 66）
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

<a id="ck-r5-04"></a>

## CK-R5-04　成功記録の裏付けの表示の誤り（「3 つの裏付け」と、仕組みの計数）

- **区分**：4　不具合・未解決事項
- **内容**：記録・報告書・手順書は「成功の記録は、出力の一致・仕組みの計数・導出の 3 つで機械的に裏付けた」と述べているが、実際にはそうなっていないという不具合。仕組みの計数は、統合モデルが決まった位置で増やす数で、主張に反する動作があっても変わらないものを含む。
- **所在**：
  - [`09_APPROX_STUDY/03_MODELS/records/units.json`](../../../09_APPROX_STUDY/03_MODELS/records/units.json)
  - [`09_APPROX_STUDY/03_MODELS/README.md`](../../../09_APPROX_STUDY/03_MODELS/README.md)
  - [`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../../09_APPROX_STUDY/04_VERIFICATION/README.md)
  - [`09_APPROX_STUDY/03_MODELS/models.json`](../../../09_APPROX_STUDY/03_MODELS/models.json)
  - [`09_APPROX_STUDY/research_code/tools/build_records.py`](../../../09_APPROX_STUDY/research_code/tools/build_records.py)
  - [`09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json`](../../../09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json)
- **確かめ方**：第2回の検査（記録の観点）が、係数の辞書と行に数える仕掛けを入れ、仕組みの確認に使う架空シナリオ（資材 400 行、設備 120 行、冷媒機器 10 件、乱数の種 5）で実際の演算を数えて、計数と比べた。検証担当が別の仕掛けで数え直した。
- **確かめた者**：独立検査（第2回）で再現（REC-4・REC-5・REC-9 は CONFIRMED、REC-3 は PARTLY_CONFIRMED。REP-3・REP-12 は第2検証なし）
- **言える範囲**：43ba5d7 の統合モデルと記録。数は上の 1 つの架空シナリオと、標準ベンチマーク S・M・L でのもの。
- **関係する第2回の指摘**：REC-3、REC-4、REC-5、REC-9、REP-3、REP-12
- **第2回の指摘の影響**：(1) build_records.py は機構と導出を任意の引数にしており、欠けていても生成は失敗しない。(2) 仕組みの確認は 8 個の述語を 1 つの架空シナリオで 1 回評価したもので、単位との結び付きは手書きの計画表だけである。(3) M-SINGLEPASS・M-EVENTS・M-ROWPROD の計数は、繰り返しの先頭などの決まった位置で増やすだけで、反する動作を数えない。公表値のうち「読んだ行 520（全出力）」は、全出力で設備 104 行を読み直すことを数えていない。「合計のみでは更新年の一覧を 1 つも作らない（0）」は、明示の一覧 16 個と冷媒の交換年の一覧 10 個を作ることを数えていない。「行ごとの係数の乗算 520」は行数であり、全出力での係数の乗算は集計の段で約 4,000 回、詳細の段で約 830 回ある。(4) M-RESOLVE の「係数・段階・単位の組ごとに 1 回」は、行ごとの換算を持つ行では成り立たない（数えた 299 回のうち 105 回が行ごとの繰り返し。規模 L では 5,657 回のうち 5,183 回）。(5) M-GROUPS の述語（周期の値 245 ＜ 行 520）は架空データの性質を調べるもので、コードの検査ではない。(6) 「表の読み出しでの乗算 3,373」は表の長さの和で、実際の係数の乗算は 2,847＋522 回と、計数のない X-03 の展開 223 回である。
- **今の時点で言ってよいこと**：第2回の検証担当が外から計測して確かめた範囲：合計のみの出力では、資材・設備の行は 1 回だけ読まれ、資材・設備の行ごとに係数の値を掛けることはなく、周期による資材・設備の更新年の一覧は作られない。M-RECIPE（複合係数の計算 30 回 ＝ 相異なる配合 30）と M-SWEEP は成り立つ。M-YEARLOOP は値の計算について成り立つ。「単位換算の解決 8」は、このシナリオについて正しい。
- **使ってはいけない記述**：
  - 03_MODELS/README.md「仕組みを統合モデル自身が数えた回数で確かめている（成り立たなければ記録の生成が失敗する）」を、単位ごとの裏付けとして引用すること
  - 04_VERIFICATION/README.md の演算の回数の表のうち、「行ごとの係数の乗算 520」「作った更新年の一覧 0（合計のみ）」「読んだ行 520（全出力）」「表の読み出しでの乗算 3,373」
  - M-RESOLVE と K7 の式「係数・対象段階・単位の組ごとに 1 回解決」
  - M-EVENTS「合計のみの出力では更新年の一覧を 1 つも作らない」
  - DERIVATIONS.md D1 の「右辺は係数キーの数だけ乗算する」を、乗算が行数より少ないという意味で引用すること（規模 S・M・L の表の読み出しの乗算は 2,058・10,798・70,273 回で、どの規模でも行数より多い）
  - INDEPENDENT_REVIEW.md 2.3「記録が述べる仕組みを、統合モデル自身が数えた回数で確かめるようにした」を、対応が済んだという意味で引用すること
- **新研究での再利用**：候補にしない
  - 理由・注意：外から計測する設計案（mechanism_probe）は a2 の途中の出力しかなく、未検証である。
- **分類の根拠**：
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):25-35（REC-3 と訂正後の文）
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):37-47（REC-4 と訂正後の文）
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):49-59（REC-5）
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):97-107（REC-9）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):78-83（REP-12：規模別の表の読み出しの乗算）
  - [`09_APPROX_STUDY/research_code/tools/build_records.py`](../../../09_APPROX_STUDY/research_code/tools/build_records.py):86-111（8 個の述語）
  - [`09_APPROX_STUDY/03_MODELS/README.md`](../../../09_APPROX_STUDY/03_MODELS/README.md):70-85（仕組みの確認の表）
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

<a id="ck-r5-05"></a>

## CK-R5-05　近似の段階の「不採用」記録 39 件（候補 16 種）

- **区分**：2　暫定・未検証成果
- **内容**：M3（38 件）と M6（1 件）で、近似候補を測定したうえで不採用とした記録。候補は AP-01、02、03、04、05、06、06b、07a、07b、08、09a、09b、14、19b、20、22a の 16 種で、1 つの候補を複数の単位に付けている。verification は「導出と架空データ」24 件（誤差の符号を不等式で示したとするもの）、「架空データのみ」15 件。
- **所在**：
  - [`09_APPROX_STUDY/03_MODELS/records/units.json`](../../../09_APPROX_STUDY/03_MODELS/records/units.json)
  - [`09_APPROX_STUDY/03_MODELS/candidates.json`](../../../09_APPROX_STUDY/03_MODELS/candidates.json)
  - [`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)
  - [`09_APPROX_STUDY/05_DECISIONS/README.md`](../../../09_APPROX_STUDY/05_DECISIONS/README.md)
- **確かめ方**：bench/approx_study.py による、架空の母集団 400 シナリオ（構造 4 種×用途 6 種、規模 S・M、評価期間 30〜100 年と非整数）での誤差の測定。build_records.py が、宣言した結論と統計が矛盾しないことを生成時に確かめる（例：AP-01 は、最大の過大が 1e-12 以下で、過小の幅が 2％ を超えること）。第2回の検査（報告書の観点）は AP-04 と AP-22a の統計を基準計算だけから計算し直し、保存値と一致した。残りの候補は、ファイル間と報告書の整合だけを確かめた。
- **確かめた者**：作成者のみ（AP-04・AP-22a の統計だけ独立検査（第2回）で再現）
- **言える範囲**：架空の母集団での値。目標は合計 1％、段階 2％。実建物での誤差を示さない。
- **関係する第2回の指摘**：APP-2、APP-3、APP-5、APP-6、APP-7、APP-8、REP-5、REP-6、REP-13
- **第2回の指摘の影響**：「厳密な閉形式が同じ手間で使える」「利点がない」という不採用の理由（AP-04、05、06、07b、08、09a）は、測定の裏付けがない論拠である（REP-6：近似候補の時間・メモリ・命令数・入力数は測っていない）。AP-08・09a・09b の「B6 段階」は、実際には B6-03（段階 B6＋B2）の値（APP-2）。AP-05 の数字は、題名の線形化より粗い変種のもの（APP-6）。AP-01・AP-20 の「基準を上回ることがない」「必ず上下限の間に入る」は、相対 1e-9 の範囲を除いて成り立つ（APP-5）。AP-03 の「B5 で平均 +42.7％」は 89 シナリオだけの値で、基準が 0 の組を数えずに落としている（APP-7）。「合計への影響」は局所の差を合計で割った値で、上流の候補（AP-06、AP-07b）では下流へ伝わった後の影響が 95％ 点で最大約 2.2 倍になる（APP-3。結論は変わらない）。AP-14 の測定には生成の副作用があるが、数字と不採用は変わらない（APP-8）。AP-08 を B2-01・B6-04 に、AP-05 を B1-03・B1-04 に付けた記録は、その単位自身の出力を測っていない（REP-5）。AP-06・AP-22a は、候補が付く単位の一覧が 2 つのファイルで違う（REP-13）。
- **今の時点で言ってよいこと**：16 種の候補が架空の母集団で測定され、どれも採用されなかった。測定値（平均、95％ 点、範囲）は approximation_study.json と candidates.json に記録されている。重大な過小評価が出た候補（AP-01、AP-07a、AP-22a）と、目標を大きく超えた候補（AP-02、AP-03、AP-19b）の不採用は、第2回の指摘で結論が変わっていない。
- **使ってはいけない記述**：
  - 「厳密な閉形式が同じ手間で使えるため不採用」を測定結果として引用すること
  - AP-08・AP-09a・AP-09b の「B6 段階で …」という段階の名前
  - AP-05「線形近似 r·k で B1 段階の平均 +28.0％、最大 +180.7％」を、題名どおりの線形化の誤差として引用すること
  - AP-01・AP-20 の「必ず」を、許容幅 1e-9 の断りなしに引用すること
  - 「合計への影響（95％ 点）」を建物全体の誤差として引用すること（上流の候補）
  - AP-03 の「B5 で平均 +42.7％」を母集団全体の値として引用すること
  - 04_VERIFICATION/README.md の AP-06b の過小評価の列「—」（実際は 175,143 行の 100％ で過小）
- **新研究での再利用**：候補（ルート A・C）
  - 使い道：新研究で誤差を測るときの比較の相手（単純な近似がどの程度外れたか）と、同じ候補を繰り返さないための一覧として使う。
  - 条件・注意：数字は架空の母集団の値。中断した修正 b2 の測り直しと結論の言い換え案（conclusion_proposals.json：41 候補のうち言い換え 16、現状維持 16、新規 9）は自己申告で、未検証である。
- **分類の根拠**：
  - [`09_APPROX_STUDY/03_MODELS/records/units.json`](../../../09_APPROX_STUDY/03_MODELS/records/units.json): outcome = REJECTED の 39 件（M3 38、M6 1）
  - [`09_APPROX_STUDY/research_code/tools/build_records.py`](../../../09_APPROX_STUDY/research_code/tools/build_records.py):305-419（結論の宣言と、統計との照合）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):128（CHECKS PERFORMED 2：AP-04 と AP-22a を再計算して一致）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):36-41（REP-6）
  - [`materials/round2_review/triage/approx.md`](../materials/round2_review/triage/approx.md):13-23、25-35、49-59、61-71、73-83、85-95（APP-2、3、5、6、7、8）
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

<a id="ck-r5-06"></a>

## CK-R5-06　近似の段階の「保留」記録 71 件（候補 16 種。実データ待ち）

- **区分**：3　研究途中の数式・仮説
- **内容**：M3（6 件）、M4（53 件）、M5（8 件）、M6（4 件）で「架空データでは判断できず、実データが要る」とした記録。候補は AP-09c、10、10b、11、12、13、15、16、17、18、18a、18b、18c、19a、21、22b の 16 種。全件に必要なデータ（data_needed）が書かれ、verification はすべて「架空データのみ」。
- **所在**：
  - [`09_APPROX_STUDY/03_MODELS/records/units.json`](../../../09_APPROX_STUDY/03_MODELS/records/units.json)
  - [`09_APPROX_STUDY/03_MODELS/candidates.json`](../../../09_APPROX_STUDY/03_MODELS/candidates.json)
  - [`09_APPROX_STUDY/05_DECISIONS/README.md`](../../../09_APPROX_STUDY/05_DECISIONS/README.md)
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md)
- **確かめ方**：架空の母集団で誤差を測定した。母集団から係数を決める候補（AP-10、10b、11、15、16、21、22b）は、前半で係数を決め、後半で誤差を測った。独立の再計算はない。
- **確かめた者**：作成者のみ
- **言える範囲**：架空の母集団での値。採否の結論は出ていない。実建物での誤差を示さない（記録自身がそう述べている）。
- **関係する第2回の指摘**：APP-1、APP-2、APP-4、APP-9、REP-5、REP-6、REP-13
- **第2回の指摘の影響**：AP-15（延床面積×平均原単位による建物全体の代理。単位の式を使わない）が 33 単位に付いている。M4 が保留の 39 単位のうち 26 単位は AP-15 だけ、保留のある 44 単位のうち 21 単位は AP-15 だけによる保留で、単位ごとの M4 候補があるのは 13 単位（REP-5。この読み取りでも台帳から 26 と 21 を数えた）。AP-18a〜c・AP-19a の数字は、評価する建物自身の行から代表値を作った最良の場合の値で、入力は減っていない。区分の代表値を他の架空の建物から取ると、AP-18b は B3 で −41％〜+337％ になる（APP-9）。AP-09c の「段階 2％ の内側」は B6 では成り立つが、B2 では +2.03％ に達する。AP-18c の「C3＋C4」は資材だけの C3-01＋C4-01 である（APP-2）。AP-17 の結論の最後の文（重い資材ほど遠くから運ぶ傾向で決まる）は不完全で、質量と距離を独立に決めた架空データでも −37％〜+117％ になる（APP-4）。AP-18b の保留の理由「過小になる場合がある」は、過小にならない変種を測っていないことによる（APP-1）。保留の候補が述べる入力の削減は数えていない（REP-6）。
- **今の時点で言ってよいこと**：16 種の候補について、架空の母集団での誤差の統計と、判断に必要な実データの種類が記録されている。どの候補も採用されていない。
- **使ってはいけない記述**：
  - 「M4 の保留 39 単位」「44 単位に実データ待ちの保留」を、単位ごとに近似候補を調べた数として引用すること
  - AP-18b「B3 段階で −1.9％〜+1.1％、段階 2％ の内側」と AP-19a の数字を、入力を減らしたモデルの測定値として引用すること
  - AP-09c「段階 2％ の内側」を B2 を含めて引用すること
  - 「誤差が実建物のばらつきで決まるため保留」を、架空データで測れることをすべて測った結果として引用すること
  - AP-17「重い資材ほど遠くから運ぶ傾向が実際にあるかどうかで結果が決まる」
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：新研究で近似や低次元化の候補を考えるときに、既に出た案と、判断に必要なデータの一覧として使う。
  - 条件・注意：仮説として扱う。数字は架空の母集団の値で、区分パラメータの数字は標本内の値である。候補の題名に、フーリエ変換・ラプラス変換・特異値分解などの変換による案はない（candidates.json の題名を検索した）。
- **分類の根拠**：
  - [`09_APPROX_STUDY/03_MODELS/records/units.json`](../../../09_APPROX_STUDY/03_MODELS/records/units.json): outcome = HOLD の 71 件（M3 6、M4 53、M5 8、M6 4）
  - [`09_APPROX_STUDY/05_DECISIONS/progress_ledger.json`](../../../09_APPROX_STUDY/05_DECISIONS/progress_ledger.json): M4 の結論が HOLD の 39 単位のうち、M4 の候補が AP-15 だけの単位が 26
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):29-34（REP-5）
  - [`materials/round2_review/triage/approx.md`](../materials/round2_review/triage/approx.md):97-107（APP-9）
  - [`materials/round2_review/triage/approx.md`](../materials/round2_review/triage/approx.md):13-23（APP-2）
  - [`materials/round2_review/triage/approx.md`](../materials/round2_review/triage/approx.md):37-47（APP-4）
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

<a id="ck-r5-07"></a>

## CK-R5-07　「候補なし」記録 226 件（測定をしていない判断）

- **区分**：3　研究途中の数式・仮説
- **内容**：測定をせず、理由だけで段階を閉じた記録。M1 18、M2 4、M3 42、M4 31、M5 66、M6 65。verification は全件「未検証」で、根拠のファイルの欄は空。理由は build_records.py に書かれた定型文（判定は近似しない、すでに最小の形、積 1 つでこれより単純な式はない、他の単位の和、厳密式が同じ手間で使える、など）か、単位ごとの文である。
- **所在**：
  - [`09_APPROX_STUDY/03_MODELS/records/units.json`](../../../09_APPROX_STUDY/03_MODELS/records/units.json)
  - [`09_APPROX_STUDY/research_code/tools/build_records.py`](../../../09_APPROX_STUDY/research_code/tools/build_records.py)
  - [`09_APPROX_STUDY/05_DECISIONS/PROGRESS.md`](../../../09_APPROX_STUDY/05_DECISIONS/PROGRESS.md)
- **確かめ方**：確認はない。第2回の検査（記録の観点）が理由を種類ごとにまとめ、台帳の定義と計数に照らして、事実と違う理由を指摘した。それ以外の理由は「反証する実験を見つけられなかった論拠」とされた。
- **確かめた者**：なし（独立検査（第2回）が理由文の一部に誤りを指摘。REC-8 は CONFIRMED）
- **言える範囲**：独立概念モデルの 70 単位についての、測定を伴わない論拠。検証結果ではない（記録の注記と各報告書がそう明記している）。
- **関係する第2回の指摘**：REC-8、REP-5、REP-14
- **第2回の指摘の影響**：近似の段階（M3〜M6）の 280 の単位×段階のうち 204 が候補なしである。M5 の理由 66 件のうち 54 件、M6 の理由 65 件のうち 51 件は同じ定型文（REP-5。この読み取りでも数えた）。17 単位（B1-01、C-05、QA-01〜04、STO-02、SUM-06〜08、SYS-01〜04、X-07、X-15、X-16）は、測定した近似候補が 1 件もない。事実と違う理由：NA-B6-04-M4「他の単位の値の和（または比）で、近似する対象となる独自の式がない」（B6-04 は自分の式を持つ）。定型文「厳密式がすべての入力条件で同じ手間で使え」（年次表の入力では年ごとの繰り返しが 480 回、記述子の入力では 0 回）。B6-02・B7-01〜03 の M3「M1 の閉形式は…」（閉形式があるのは記述子の入力だけ）（REC-8）。M6 の理由「場合分けは厳密な計算どうしで、M1 に記録した」を持つ 17 単位は、M1 が候補なしで、場合分けの記録がない（REP-14）。
- **今の時点で言ってよいこと**：226 件は「その段階では測定をしていない」という事実の記録であり、理由は論拠である。
- **使ってはいけない記述**：
  - 候補なしの理由を検証結果として引用すること
  - 件数を、指示書 第8章「対象を調べずに『近似できない』と判断してはならない」を満たした根拠として引用すること
  - NA-B6-04-M4 の理由、定型文「厳密式がすべての入力条件で同じ手間で使え…（場合分けは…M1 に記録した）」、B6-02・B7-01〜03 の M3 の理由
- **新研究での再利用**：候補（ルート B・C）
  - 使い道：旧研究が測らずに見送った箇所の一覧として、新研究で改めて調べる対象を選ぶときに使う。
  - 条件・注意：理由は未検証の論拠。新研究は旧研究の「候補なし」に縛られない。
- **分類の根拠**：
  - [`09_APPROX_STUDY/03_MODELS/records/units.json`](../../../09_APPROX_STUDY/03_MODELS/records/units.json): outcome = NOT_APPLICABLE の 226 件（verification はすべて NOT_VERIFIED、evidence は空）
  - [`09_APPROX_STUDY/research_code/tools/build_records.py`](../../../09_APPROX_STUDY/research_code/tools/build_records.py):114-124（定型文）、148-152（M5 の文）
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):85-95（REC-8）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):29-34（REP-5）、92-97（REP-14）
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

<a id="ck-r5-08"></a>

## CK-R5-08　進捗台帳（progress_ledger.json と PROGRESS.md）の構造と判定の規則

- **区分**：2　暫定・未検証成果
- **内容**：70 単位のそれぞれについて、M1〜M6 の段階の結論（候補の記録の写しつき）、状態（6 種）、保留中の段階、統合先のモデル、着手順と群を持つ台帳。tools/progress_ledger.py が records/units.json から機械的に作る（init → merge → check → report）。PROGRESS.md はその表示である。
- **所在**：
  - [`09_APPROX_STUDY/05_DECISIONS/progress_ledger.json`](../../../09_APPROX_STUDY/05_DECISIONS/progress_ledger.json)
  - [`09_APPROX_STUDY/05_DECISIONS/PROGRESS.md`](../../../09_APPROX_STUDY/05_DECISIONS/PROGRESS.md)
  - [`09_APPROX_STUDY/research_code/tools/progress_ledger.py`](../../../09_APPROX_STUDY/research_code/tools/progress_ledger.py)
  - [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md)
- **確かめ方**：段階の結論は 成功 ＞ 保留 ＞ 不採用 ＞ 候補なし の順で決め、単位の状態は手順書 P10 の規則で決める。check は、未実施の段階がある単位や、測定・導出の裏付けが 1 件もない単位を完了にしていないこと、不採用・候補なし・保留に理由があること、保留に必要なデータが書かれていることを確かめる。第2回の検査（記録の観点）が規則を独自に書いて 70 単位の状態と段階の結論を求め、保存値と一致した。
- **確かめた者**：独立検査（第2回）で再現（規則どおりに求まることの再現。状態の中身は第2回の指摘で一部が争われている）
- **言える範囲**：独立概念モデルの 70 単位。「検証完了」は、厳密な部分（M1・M2）について、数学的な導出と架空データでの確認が終わったという意味である（台帳自身の定義）。実建物での精度を保証しない。
- **関係する第2回の指摘**：REC-1、REC-2、REP-4、REP-5
- **第2回の指摘の影響**：規則の実装に誤りは指摘されていない。状態は元の記録で決まるので、争われている M2 の記録（REC-2）を除くと 5 単位の状態が変わる。保留中の段階（steps_on_hold）は、単位ごとの候補による保留と、建物全体の代理（AP-15）だけによる保留を区別していない（REP-5）。件数ごとの評価は CK-R5-09。
- **今の時点で言ってよいこと**：台帳は、記録から P10 の規則どおりに求めた状態の一覧である。70 単位すべてに 6 段階の結論があり（420 の単位×段階に空がない）、未実施の段階はない。段階別の単位数は、M1 成功 52・候補なし 18、M2 成功 66・候補なし 4、M3 不採用 22・保留 6・候補なし 42、M4 保留 39・候補なし 31、M5 保留 4・候補なし 66、M6 不採用 1・保留 4・候補なし 65。
- **使ってはいけない記述**：
  - 「検証完了」を、その単位のすべての段階が検証されたという意味で引用すること
  - has_verified_record が 70 単位すべてで真であることを、各単位に独立に確かめられた裏付けがあるという意味で引用すること
  - 保留中の段階の数を、単位ごとに調べた近似候補の保留として数えること
- **新研究での再利用**：候補（ルート A・C）
  - 使い道：単位ごとの到達点の索引として使う。状態を記録から機械的に求める規則は、新研究の進捗の管理の参考になる。
  - 条件・注意：状態の表示を、新研究の「検証済み」の一覧にそのまま写さない。台帳を作り直す作業（証拠の範囲の区別を加える案）は未着手のまま終了している。
- **分類の根拠**：
  - [`09_APPROX_STUDY/research_code/tools/progress_ledger.py`](../../../09_APPROX_STUDY/research_code/tools/progress_ledger.py):67-77（段階の結論の優先順）、80-111（状態の規則）、213-246（check）
  - [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md):222-241（P10）
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):110（CHECKS PERFORMED 6）
  - [`09_APPROX_STUDY/05_DECISIONS/PROGRESS.md`](../../../09_APPROX_STUDY/05_DECISIONS/PROGRESS.md):23-30（段階別の件数）
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

<a id="ck-r5-09"></a>

## CK-R5-09　状態別の件数 3／66／0／0／0／1 のうち、第2回の指摘と矛盾する数

- **区分**：4　不具合・未解決事項
- **内容**：進捗台帳、PROGRESS.md、第9章 README、05_DECISIONS/README.md が掲げる状態別の件数（検証完了・簡略化成功 3、検証完了・統合成功 66、検証完了・近似不採用 0、検証中 0、未検証 0、データ・権利上の制約により保留 1、合計 70）を、第2回の指摘に照らして 1 つずつ見たもの。
- **所在**：
  - [`09_APPROX_STUDY/05_DECISIONS/progress_ledger.json`](../../../09_APPROX_STUDY/05_DECISIONS/progress_ledger.json)
  - [`09_APPROX_STUDY/05_DECISIONS/PROGRESS.md`](../../../09_APPROX_STUDY/05_DECISIONS/PROGRESS.md)
  - [`09_APPROX_STUDY/README.md`](../../../09_APPROX_STUDY/README.md)
  - [`09_APPROX_STUDY/05_DECISIONS/README.md`](../../../09_APPROX_STUDY/05_DECISIONS/README.md)
- **確かめ方**：第2回の検査（記録の観点）の検証担当が、旧研究自身の状態の規則を使い、争われている M2 の記録を除いた場合の状態を求めた（リポジトリは書き換えていない）。第2回の検査（報告書の観点）が、所属と保留の内訳を数えた。
- **確かめた者**：独立検査（第2回）で再現（REC-2 は第2検証で CONFIRMED。REP-4・REP-5 は第2検証がなく、主担当が検査担当のスクリプトを再実行して再現）
- **言える範囲**：独立概念モデルの 70 単位の状態の数。43ba5d7 の記録にもとづく。
- **関係する第2回の指摘**：REC-1、REC-2、REC-4、REP-4、REP-5、NUM-1
- **第2回の指摘の影響**：66（統合成功）：矛盾する。X-13、B1-01、SYS-03 は統合の基準を満たさず、A13-05 は基準の文面どおりには満たさない。裏付けられる数は約 62〜63 単位（REC-2 の訂正後の文）。さらに、K5 の SUM-04〜08 は別々の式のままで、14 単位（A5-04、B1-01、B2-01、B7-04、STO-02、SUM-01〜08、SYS-04）は M1 が候補なしで M2 の裏付けが出力の一致だけである（REP-4。14 単位はこの読み取りでも記録から数えた）。0（近似不採用）：矛盾しうる。争われている M2 の記録を除くと、A13-05 と X-13 がこの状態になる。0（未検証）：矛盾しうる。同じく B1-01 が「未検証」になる（6 段階すべてが理由だけの候補なし）。3（簡略化成功：C-05、QA-02、SYS-01）：この 3 単位の状態を否定する指摘はない。SYS-03 と QA-03 は、M2 の記録を除くとこの状態に移る（QA-03 は K1 の表から読んでいるので、K1 に付け替えれば統合のままになる）。QA-02 の M1 の記録は、引用した機構の計数がその処理を覆っていない（REC-4）。0（検証中）：台帳の規則では正しい（未実施の段階がない）。ただし、近似の段階 280 のうち 204 は測定なしで閉じており、17 単位は測定した近似候補が 1 件もない（REP-5）。旧研究の作業としては、停止時点でタスク「全評価単位の近似・統合研究（M1〜M6）と精度・性能の検証、進捗台帳の更新」が進行中だった。1（保留：STO-01）：否定する指摘はない。この状態は、単位そのものの保留ではなく、「採用した候補がなく、保留中の段階（M3 の AP-21）がある」という規則から来ている。44（検証完了のうち近似の段階に保留がある単位）：数は記録と合うが、21 単位は AP-15 だけによる保留である。B3-01 は「検証完了・統合成功」だが、周期 1.000000001 年で基準計算と食い違う（REC-1・NUM-1）。
- **今の時点で言ってよいこと**：「記録から規則どおりに求めた件数が 3／66／0／0／0／1 である」という事実だけが成り立つ。簡略化成功の 3 単位（C-05、QA-02、SYS-01）と保留の 1 単位（STO-01）の状態を直接否定する指摘はない。
- **使ってはいけない記述**：
  - 「検証完了・統合成功 66」
  - 「検証完了・近似不採用 0」「未検証 0」を、該当する単位がないという意味で引用すること
  - 「検証完了」は合計 69 単位、という数え方
  - 05_DECISIONS/README.md「測定や導出の裏付けが 1 件もない単位は『完了』にしない規則にしている（該当なし）」を、全単位に確かめられた裏付けがあるという意味で引用すること
  - 「このうち 44 単位は、近似の段階に実データ待ちの保留がある」を、44 単位で単位ごとの近似候補を調べたという意味で引用すること
- **新研究での再利用**：候補にしない
  - 理由・注意：所属を測定で確かめ直す作業（a2）は途中で止まっており、確定した数はない。
- **分類の根拠**：
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):13-23（REC-2。検証担当の再計算：B1-01 → 未検証、A13-05・X-13 → 近似不採用、SYS-03・QA-03 → 簡略化成功）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):22-27（REP-4）、29-34（REP-5）
  - [`STOP_STATUS.md`](../STOP_STATUS.md):43-48（停止時に未完了だった旧タスク #4、#5、#8、#9）
  - [`09_APPROX_STUDY/05_DECISIONS/PROGRESS.md`](../../../09_APPROX_STUDY/05_DECISIONS/PROGRESS.md):9-19
  - [`09_APPROX_STUDY/research_code/tools/progress_ledger.py`](../../../09_APPROX_STUDY/research_code/tools/progress_ledger.py):98-100（採用した候補がなく保留の段階があれば「保留」）
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

<a id="ck-r5-10"></a>

## CK-R5-10　自動生成の報告書 6 点と PROGRESS.md（文面としての状態）

- **区分**：2　暫定・未検証成果
- **内容**：tools/build_reports.py が JSON から書く 6 つの README（第9章の README、01_LEDGER、02_RANKING、03_MODELS、04_VERIFICATION、05_DECISIONS）と、tools/progress_ledger.py が書く PROGRESS.md。本文は 43ba5d7 で生成されたままである。第9章の README の冒頭には、停止時に手書きで加えた枠（研究が終了したこと、本文は第2回の指摘 59 件を反映していないこと、使う前に INDEX.md を確認すること）がある。
- **所在**：
  - [`09_APPROX_STUDY/README.md`](../../../09_APPROX_STUDY/README.md)
  - [`09_APPROX_STUDY/01_LEDGER/README.md`](../../../09_APPROX_STUDY/01_LEDGER/README.md)
  - [`09_APPROX_STUDY/02_RANKING/README.md`](../../../09_APPROX_STUDY/02_RANKING/README.md)
  - [`09_APPROX_STUDY/03_MODELS/README.md`](../../../09_APPROX_STUDY/03_MODELS/README.md)
  - [`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../../09_APPROX_STUDY/04_VERIFICATION/README.md)
  - [`09_APPROX_STUDY/05_DECISIONS/README.md`](../../../09_APPROX_STUDY/05_DECISIONS/README.md)
  - [`09_APPROX_STUDY/05_DECISIONS/PROGRESS.md`](../../../09_APPROX_STUDY/05_DECISIONS/PROGRESS.md)
  - [`09_APPROX_STUDY/research_code/tools/build_reports.py`](../../../09_APPROX_STUDY/research_code/tools/build_reports.py)
- **確かめ方**：第2回の検査（報告書の観点）が、各報告書の数字を JSON から数え直し、報告書をメモリ上で再生成してディスク上のファイルとバイト単位で一致することを確かめた。数字は一致し、誤りは生成器の固定文、データの見出し、対応づけにあった。
- **確かめた者**：独立検査（第2回）で数字の一致を再現。文面の誤りは未修正（REP の指摘は第2検証がなく、主担当が検査担当のスクリプトを再実行して再現）
- **言える範囲**：43ba5d7 の JSON に対応する文面。架空データと独立概念モデルについての報告である。
- **関係する第2回の指摘**：REP-1、REP-8、REP-9、REP-11、REP-12、REP-13、REP-15、REP-16、REP-18、REC-9
- **第2回の指摘の影響**：生成されたまま残っている誤り。04_VERIFICATION「入力仕様 124 項目のうち 0 項目は記録用で、どの計算にも使われない」：input_usage.json では、仕様の 124 項目のうち 47 項目がどの計算にも読まれない。台帳は 30 項目を記録用としている（REP-1）。01_LEDGER の構造別の件数「活動量×係数の総和 29、比・換算 11」：単位を数えると 30 と 10（REP-8）。03_MODELS「統合しなかった単位（4）…検査の 4 単位は」：検査は 3 単位（C-05、QA-02、SYS-01）で、STO-01 は検査ではない（REP-9・REC-9）。02_RANKING「軸 A 22 件（重みを変えた場合だけ入るもの 6 件）、軸 B 30 件、和集合 42 件」：6 件は 22 件の外にあり、A と B だけの和集合は 38 件（REP-11）。03・04 の仕組みの表の数（CK-R5-04）。04「評価期間を 9 通り…比較した値は 172,404 個」：比べたのは 70 単位のうち 22 単位の合計だけで、基準案との比較は切ってあり、64 シナリオである（REP-16）。04 の AP-06b の過小評価の列「—」（REP-13）。01_LEDGER のシート族の対応の状態区分が一貫していない（REP-18。ノード占有率への影響は 0.6 ポイント未満）。第9章 README の本文は、掲載の数字が第1回の対応後の版のもので、その版への独立検査が済んでいなかったことを述べていない（REP-15）。この点は、停止時の手書きの枠が補っている。
- **今の時点で言ってよいこと**：報告書の数字は同じ版の JSON と一致する。各報告書の冒頭の注意（検証はすべて架空データ上で行った。一致・誤差・速度は独立に設計した基準計算に対するもので、実建物での精度や他のツールとの一致を示さない）と、第9章 README の「この研究で言えないこと」の 6 項目は、第2回の検査で否定されていない。第2回の検査は、J-CAT との同等、原版ブックの調査、実建物での精度を主張する文が報告書にないことを確かめた。
- **使ってはいけない記述**：
  - 04_VERIFICATION/README.md「入力仕様 124 項目のうち 0 項目は記録用で、どの計算にも使われない」
  - 01_LEDGER/README.md の構造別の件数の表の 2 行（29、11）
  - 03_MODELS/README.md「検査の 4 単位は判定の対象と基準がそれぞれ違い…」
  - 02_RANKING/README.md「軸 A 22 件（重みを変えた場合だけ入るもの 6 件）…和集合 42 件」
  - 04_VERIFICATION/README.md の評価期間の掃引の文を、全単位・全出力の突合せとして引用すること
  - 各報告書の「このファイルは…自動生成したもの。数値を手で書き換えない」を、文面が正しいことの保証として読むこと
- **新研究での再利用**：候補（ルート A・C）
  - 使い道：旧研究の公表文を引用するときの出典として使う。
  - 条件・注意：引用するときは、第2回の指摘の番号を添えて、成り立つ範囲を限定する。報告書を再生成しない（生成器の実行は旧研究の再開に当たる。再生成すると第9章 README の手書きの枠も消える）。
- **分類の根拠**：
  - [`09_APPROX_STUDY/README.md`](../../../09_APPROX_STUDY/README.md):3-9（停止時の手書きの枠）、11（自動生成の注記）
  - [`09_APPROX_STUDY/research_code/tools/build_reports.py`](../../../09_APPROX_STUDY/research_code/tools/build_reports.py):532-539（6 つの報告書を書く）、340（「0 項目」の文）、225（「検査の 4 単位」の固定文）、102（構造別の件数は units.json の見出しから）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):1-6（REP-1）、50-55（REP-8）、57-62（REP-9）、71-76（REP-11）、99-104（REP-15）、106-111（REP-16）、120-125（REP-18）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):128（CHECKS PERFORMED 1・4）
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

<a id="ck-r5-11"></a>

## CK-R5-11　README の要点 1「評価単位は 70 件（53＋17）。全件を研究対象にした」

- **区分**：1　検証済み成果
- **根拠の強さについての注記（索引の作成者）**：件数の数え直しだけである。数え直したのは第2回の検査担当 1 者。
- **内容**：第9章 README「結果の要点」の 1。全文：「評価単位は 70 件（既存の概念式 53＋追加で特定した計算構造 17）。上位 30％ に絞らず、全件を研究対象にした。これは独立概念モデルの単位であり、原版の数式を調べたものではない。」
- **所在**：
  - [`09_APPROX_STUDY/README.md`](../../../09_APPROX_STUDY/README.md)
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
  - [`09_APPROX_STUDY/05_DECISIONS/progress_ledger.json`](../../../09_APPROX_STUDY/05_DECISIONS/progress_ledger.json)
- **確かめ方**：台帳の件数。第2回の検査（報告書の観点）が 70／53／17 を数え直し、既存の 53 単位が 04_FORMULAS の ID と名称に一致すること、研究対象の数（research_target_count）が 70 であること、420 の単位×段階に空がないことを確かめた。この読み取りでも、進捗台帳の origin を数えて 53 と 17 を確認した。
- **確かめた者**：独立検査（第2回）で再現（件数という記録上の事実の数え直し）
- **言える範囲**：独立概念モデルの単位の数に限る。単位の切り方が妥当か、原版の計算構造をどこまで覆うかは含まない（06_OPEN_ISSUES A-6 で未検証としている）。
- **関係する第2回の指摘**：REP-5、REP-10
- **第2回の指摘の影響**：件数は否定されていない。「全件を研究対象にした」は、全単位に 6 段階の結論の記録があるという意味では成り立つが、近似の段階 280 のうち 204 は測定なしで閉じている（REP-5）。台帳の A13-04 の文面に「基準計算には実装しない」という古い記述が残っている（REP-10。実際は計算でき、AP-19a・AP-19b を測定している）。
- **今の時点で言ってよいこと**：台帳には 70 単位が登録されている（既存の概念式 53、追加で特定した計算構造 17）。上位 30％ による絞り込みは行わず、70 単位すべてに M1〜M6 の結論を記録した。これらは独立概念モデルの単位であり、原版の数式を調べたものではない。
- **使ってはいけない記述**：
  - 「全件を研究対象にした」を、全単位について近似候補を測定したという意味で引用すること（17 単位は測定した近似候補が 1 件もない）
  - 70 単位が原版の計算構造を網羅する、という読み方
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：新研究で方程式のグループを数えるときに、旧研究の側の母数として引用する。
  - 条件・注意：単位の一覧と定義文そのものの状態は、台帳の観点の分類に従う（定義の穴は RED-1〜12）。区分 1 としたのは件数の事実だけである。
- **分類の根拠**：
  - [`09_APPROX_STUDY/README.md`](../../../09_APPROX_STUDY/README.md):24
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):128（CHECKS PERFORMED 1：70/53/17 が一致、既存 53 単位は 04_FORMULAS の ID と名称に一致。5：research_target_count 70、420 の単位×段階に空なし）
  - [`09_APPROX_STUDY/05_DECISIONS/progress_ledger.json`](../../../09_APPROX_STUDY/05_DECISIONS/progress_ledger.json): units[].origin を数えると EXISTING_53 が 53、ADDITIONAL が 17
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):29-34（REP-5）、64-69（REP-10）
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

<a id="ck-r5-12"></a>

## CK-R5-12　README の要点 2「66 単位が 7 つの統合モデルに、結果を変えずにまとまった」

- **区分**：4　不具合・未解決事項
- **内容**：第9章 README「結果の要点」の 2。全文：「独立概念モデルでは、66 単位が 7 つの統合モデルに、結果を変えずにまとまった（統合されなかったのは 4 単位）。排出と集計は『表ごとに 活動量×係数 を足す』1 つの形と、評価期間に依存する数個の乗数の関数で書ける。」同じ数が 03_MODELS/README.md と、05_DECISIONS/README.md の「計算の定義の数 70 → 11」にある。
- **所在**：
  - [`09_APPROX_STUDY/README.md`](../../../09_APPROX_STUDY/README.md)
  - [`09_APPROX_STUDY/03_MODELS/README.md`](../../../09_APPROX_STUDY/03_MODELS/README.md)
  - [`09_APPROX_STUDY/03_MODELS/models.json`](../../../09_APPROX_STUDY/03_MODELS/models.json)
  - [`09_APPROX_STUDY/05_DECISIONS/README.md`](../../../09_APPROX_STUDY/05_DECISIONS/README.md)
- **確かめ方**：66 は models.json の単位数の和（26＋9＋10＋4＋8＋3＋6）。第2回の検査（記録の観点）が 66 の所属を 1 つずつコードと照合した：基準を明確に満たさないもの 4（A13-05、X-13、B1-01、SYS-03）、弱いか付け先が違うもの 4（QA-03、B6-04、X-07、A5-01）、残り 58 は記載どおり。検証担当は X-07 を擁護できるとした。第2回の検査（報告書の観点）は、K5 の SUM-04〜08 が別々の式のままであることなどを指摘した。
- **確かめた者**：独立検査（第2回）で否定（REC-2 は CONFIRMED。REP-4 は第2検証がなく、主担当が検査担当のスクリプトを再実行して再現）
- **言える範囲**：独立概念モデル。統合の基準は旧研究自身のもの（値を共有の表から読むか、共有のパラメータ付き関数で求める単位だけを数える。形が似ているだけ、同じ走査の中にあるだけのものは数えない）。
- **関係する第2回の指摘**：REC-1、REC-2、REC-5、REC-7、REP-3、REP-4、REP-9
- **第2回の指摘の影響**：「66 単位」「7 つにまとまった」は、旧研究自身の統合の基準に照らすと成り立たない単位を含む。REC-2 の訂正後の文では、裏付けられるのは約 62〜63 単位。REP-4 は、さらに K5 の 5 単位（SUM-04〜08）と、機構の裏付けのない M2 の成功（A5-04、B7-04、B2-01、B1-01、STO-02、X-17）を「基準計算から計算が変わっていない」とする。2 つの検査で数え方がそろっておらず、確定した数はない。「結果を変えずに」は 681 架空シナリオでの一致を指しており、周期 1.000000001 年の行がある入力では B3-01 が食い違う（REC-1）。
- **今の時点で言ってよいこと**：独立概念モデルについて、7 つの統合モデル（K1〜K7）の定義と、66 単位をそれに割り当てた目録が存在する。681 架空シナリオでは、統合モデルの出力が基準計算と相対 1e-9 以内で一致した。第2回の検査（記録の観点）が「記載どおり共有の表・関数から値を得ている」とした所属は 58 で、そのうち K5 の SUM-04〜08 には報告書の観点から異論がある。第 2 文（1 つの形と数個の乗数の関数で書ける）は独立概念モデルの設計による形で、第2回の検査で否定されていない（買電と冷媒は、活動量の時点で排出量になっている特別なキーとして表に入る）。
- **使ってはいけない記述**：
  - 「66 単位が 7 つの統合モデルにまとまった」という数
  - 「統合されなかったのは 4 単位」
  - 05_DECISIONS/README.md「計算の定義の数 70 → 11」「共通化できた単位 66 単位 → 7 モデル」
  - 「結果を変えずに」を、どの入力でも、という意味で引用すること
  - 統合モデルの数 7 を式の種類の数として引用すること（05_DECISIONS/README.md 自身が「式の種類そのものの数ではない」と断っている）
  - INDEPENDENT_REVIEW.md 2.3「検査は実際に共有の関数にした 3 単位だけを統合に数える」（models.json は検査 9 単位のうち 6 単位を統合に数えている）
- **新研究での再利用**：候補（ルート A・C）
  - 使い道：7 つのモデルの形は、新研究が少数の変換で表し直す対象を整理するときの出発点として使える。
  - 条件・注意：件数を引用しない。所属は REC-2・REP-4 の一覧で単位ごとに確かめる。所属を故障注入で測り直す作業（a2）は途中で止まっており、結果はない。モデルごとの状態は統合モデルの観点の分類に従う。
- **分類の根拠**：
  - [`09_APPROX_STUDY/README.md`](../../../09_APPROX_STUDY/README.md):25
  - [`09_APPROX_STUDY/03_MODELS/models.json`](../../../09_APPROX_STUDY/03_MODELS/models.json): models[].unit_count = 26、9、10、4、8、3、6。not_unified = C-05、QA-02、STO-01、SYS-01
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):13-23（REC-2 と訂正後の文）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):22-27（REP-4）
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):110（CHECKS PERFORMED 2：4 件は明確に不適合、4 件は弱いか付け先違い、58 件は記載どおり）
  - [`09_APPROX_STUDY/05_DECISIONS/README.md`](../../../09_APPROX_STUDY/05_DECISIONS/README.md):103-104、117
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

<a id="ck-r5-13"></a>

## CK-R5-13　README の要点 3「統合モデルは基準計算と一致した」

- **区分**：2　暫定・未検証成果
- **内容**：第9章 README「結果の要点」の 3。全文：「統合モデルは基準計算と一致した。681 の架空シナリオ、数値 7,406,182 個を突き合わせて不一致なし（許容差は相対 1e-09）。不備のある入力や、冗長な入力どうしが食い違う場合も、同じ値を返し、同じ不備を報告する。」
- **所在**：
  - [`09_APPROX_STUDY/README.md`](../../../09_APPROX_STUDY/README.md)
  - [`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../../09_APPROX_STUDY/04_VERIFICATION/README.md)
  - [`09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json`](../../../09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json)
- **確かめ方**：bench/verify_unified.py による 681 シナリオ（標準ベンチマーク 3、境界条件 32、検証用の母集団 400、不備を入れたもの 60、1 か所ずつ壊したもの 144、小数の評価期間と周期の端 10、対象段階を一部にしたもの 32）での全出力の比較。第2回の検査（数値の観点）の検証担当が、同じ 681 シナリオを、床を使わず、無限大と型も厳密に見る独自の比較でやり直し、葉 7,962,996 個で 1e-9 を超える差 0、最大の差 4.77e-13（SUM-08 の差分）だった。第2回は別に、乱数で複数の不備を入れた 20,260 シナリオなどで反例を探した。
- **確かめた者**：独立検査（第2回）で再現（681 シナリオの範囲の一致）。一般の文としては第2回で否定（NUM-1〜11 と REC-1 はすべて CONFIRMED）
- **言える範囲**：架空データ、独立概念モデル、681 シナリオ、許容差 相対 1e-9。旧研究の比較には 1e-9×（ホールライフ合計の絶対値）の床があった。
- **関係する第2回の指摘**：NUM-1、NUM-2、NUM-3、NUM-4、NUM-5、NUM-6、NUM-7、NUM-8、NUM-9、NUM-10、NUM-11、REC-1、REP-16
- **第2回の指摘の影響**：第 1 文と第 3 文は、試したシナリオの外へ広げられない。周期がちょうど 1.000000001 年（倍精度の 1 つの値）の行があると、B3-01 と、B3 を含む合計が食い違う（全行がその周期の例で B3-01 が最大約 92％、1 行だけなら 2e-6〜2e-3）（NUM-1・REC-1）。範囲の検査がない項目に非数や無限大を入れると、例外の出方、QA-01 の合否、値が食い違う（1 項目ずつ変えた 3,461 件のうち 212 件）（NUM-2）。係数の値が 0 のときの修繕のガス別内訳（NUM-3）、年次表が評価期間より短いことと別の不備の組合せでの例外の出方の違い（NUM-4）、係数の ID が内部の擬似 ID と重なる場合（NUM-5）、ほか NUM-6〜9。桁落ちや桁あふれが起きる入力では 1e-9 を超える（NUM-10）。旧研究の比較の関数は、基準側が無限大の葉、真偽値と整数の違いを見逃し、床のために小さい葉の許容差が実質的に緩かった（NUM-11）。ただし 681 シナリオについては、厳密な比較でも差は出なかった。
- **今の時点で言ってよいこと**：681 の架空シナリオ（上の 7 種類）で、統合モデルと基準計算の全出力を突き合わせ、相対 1e-9 を超える差はなかった（数値 7,406,182 個、最大の相対差 4.8e-13）。この範囲の一致は、第2回の検証担当が独自の厳密な比較で再現した。試した 36 種類の壊し方については、両方の計算が同じ値と同じ不備の報告を返した。
- **使ってはいけない記述**：
  - 「統合モデルは基準計算と一致した」を条件なしで引用すること
  - 「不備のある入力や、冗長な入力どうしが食い違う場合も、同じ値を返し、同じ不備を報告する」を一般の文として引用すること
  - 「どの入力でも一致する」（第9章 README の手書きの枠も、言えないと明記している）
  - closed_forms.py の説明文「All of them are exact」
  - 「許容差は相対 1e-09」を、床のない純粋な相対比較として引用すること
  - 05_DECISIONS/README.md「結果の差：相対 1e-09 以内で一致／精度の低下なし」を、入力の限定なしで引用すること
- **新研究での再利用**：候補（ルート A・C）
  - 使い道：Route A で旧成果を使うときに、一致が確かめられている入力の範囲（681 シナリオ）として引用する。
  - 条件・注意：「整った入力と、試した 36 種類の不備」の範囲に限る。中断した修正 a1 が報告した修正後の一致の数字は自己申告で、引用しない。
- **分類の根拠**：
  - [`09_APPROX_STUDY/README.md`](../../../09_APPROX_STUDY/README.md):26
  - [`09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json`](../../../09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json): scenarios = 681、tolerance = 1e-09、all_exact = true、units[].leaves_compared の和 = 7,406,182
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):109-119（NUM-10：検証担当の厳密なやり直し。681 シナリオ、葉 7,962,996 個、差 0）
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):1-11（NUM-1）、13-23（NUM-2）、121-131（NUM-11）
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):1-11（REC-1）
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

<a id="ck-r5-14"></a>

## CK-R5-14　README の要点 4「計算の重さは減った」

- **区分**：2　暫定・未検証成果
- **内容**：第9章 README「結果の要点」の 4。全文：「計算の重さは減った。資材 2 万行の規模で、実行した命令数は、基準計算と同じ出力をすべて出す場合に 66.3％ 減、合計・段階・指標・検査だけを求める場合に 73.6％ 減（時間は 1689 ms → 862 ms、624 ms。同じ言語・同じ機械、ごみ集めを止めて測定）。評価期間だけを変えた再計算は、行の合算をやり直さずに済む。」
- **所在**：
  - [`09_APPROX_STUDY/README.md`](../../../09_APPROX_STUDY/README.md)
  - [`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../../09_APPROX_STUDY/04_VERIFICATION/README.md)
  - [`09_APPROX_STUDY/04_VERIFICATION/unified_model_load.json`](../../../09_APPROX_STUDY/04_VERIFICATION/unified_model_load.json)
  - [`09_APPROX_STUDY/05_DECISIONS/README.md`](../../../09_APPROX_STUDY/05_DECISIONS/README.md)
- **確かめ方**：bench/verify_unified.py による、実行したバイトコード命令の数、時間（ごみ集めを止めた反復の中央値）、ピークメモリの測定。第2回の検査（報告書の観点）は、規模 S・M の命令数（基準計算、全出力、合計のみ）を数え直し、公表値と約 100 命令以内で一致した（削減率は S で 54.2％ と 67.6％、M で 63.6％ と 72.6％）。規模 L（基準計算で 245,195,907 命令）は実行し直していない。時間とメモリは機械に依存し、測り直していない。
- **確かめた者**：作成者のみ（規模 S・M の命令数だけ独立検査（第2回）で再現）
- **言える範囲**：架空のベンチマーク、純粋な Python の実装どうし、同じ機械。独立に実装した基準計算との比較であり、原版ブックの計算時間については何も言えない（README 自身の注意）。
- **関係する第2回の指摘**：REC-3、REC-4、REP-12、REP-16、REP-17、NUM-1
- **第2回の指摘の影響**：見出しの数字（規模 L の 66.3％、73.6％、1689 ms → 862 ms、624 ms）を否定する指摘はないが、独立には確かめられていない（確かめるには実行が要る）。「行の合算をやり直さずに済む」は、資材・設備の行については第2回の検証担当の計測と合う（合計のみの出力で、乗数を掛ける段は資材・設備の行に触れない）。冷媒の行は評価期間ごとに読み直す（REC-4）。評価期間を変えた結果を基準計算と突き合わせたのは、70 単位のうち 22 単位の合計だけである（REP-16）。年次表が評価期間より短いと両方の計算が例外を出すので、変えられる評価期間は年次表の長さ以内に限られる（REP-17）。周期 1.000000001 年では、この結果も食い違う（NUM-1）。係数の解決の回数は、行ごとの換算を持つ行の数に比例して増える（規模 L で 5,657 回のうち 5,183 回が行ごとの繰り返し。REC-3）。
- **今の時点で言ってよいこと**：規模 S（資材 200 行）と M（2,000 行）で、統合モデルが実行した命令数は基準計算より少ない（全出力で 54.2％ 減と 63.6％ 減、合計のみで 67.6％ 減と 72.6％ 減）。この 2 つの規模の命令数は、第2回の検査が数え直して一致した。規模 L（資材 2 万行）の 66.3％ 減・73.6％ 減と、時間・メモリの値は、旧研究が測定して記録した値である（独立の確認なし）。
- **使ってはいけない記述**：
  - 規模 L の削減率・時間・メモリを、独立に確かめられた値として引用すること
  - 「別の評価期間 4 通りの合計 92.1％ 減」を、全単位・全出力についての値として引用すること
  - 削減率を、原版ブックや他の実装の計算時間の見込みとして引用すること
  - 命令数が減った理由を「係数の解決を相異なる組の数だけに減らした」と説明すること（REC-3）
- **新研究での再利用**：候補（ルート A・C）
  - 使い道：新研究で計算量を比べるときの基準線（旧統合モデルの命令数）として引用する。
  - 条件・注意：規模 L の値と時間・メモリは、新研究が自分の測定として測り直すまで未確認として扱う。保存の作業では測り直さない。
- **分類の根拠**：
  - [`09_APPROX_STUDY/README.md`](../../../09_APPROX_STUDY/README.md):27
  - [`09_APPROX_STUDY/04_VERIFICATION/unified_model_load.json`](../../../09_APPROX_STUDY/04_VERIFICATION/unified_model_load.json): sizes.L.reference_without_baseline_comparison.instructions = 245195907、unified_full_outputs.instruction_reduction = 0.6634、unified_totals_only.instruction_reduction = 0.7359
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):128（CHECKS PERFORMED 2：S と M の命令数を数え直して約 100 命令以内で一致）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):130（COULD NOT CHECK：時間とメモリは測り直していない。規模 L は実行し直していない）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):106-118（REP-16、REP-17）
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):25-47（REC-3、REC-4）
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

<a id="ck-r5-15"></a>

## CK-R5-15　README の要点 5「近似は 1 つも採用していない」

- **区分**：2　暫定・未検証成果
- **内容**：第9章 README「結果の要点」の 5。全文：「近似は 1 つも採用していない。近似候補 32 種を測定し、不採用 16、実データ待ちの保留 16。更新回数の連続近似のように重大な過小評価を生むものがあり、それ以外の多くも、厳密な閉形式が同じ手間で使えるため近似の利点がなかった。異なる式を共通の近似モデルへまとめる試み（区分ごとの代表パラメータなど）は、誤差が実建物のばらつきで決まるため、架空データでは結論を出せず保留した。」
- **所在**：
  - [`09_APPROX_STUDY/README.md`](../../../09_APPROX_STUDY/README.md)
  - [`09_APPROX_STUDY/03_MODELS/candidates.json`](../../../09_APPROX_STUDY/03_MODELS/candidates.json)
  - [`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)
  - [`09_APPROX_STUDY/05_DECISIONS/README.md`](../../../09_APPROX_STUDY/05_DECISIONS/README.md)
- **確かめ方**：架空の母集団 400 シナリオでの誤差の測定（approximation_study.json）と、候補ごとの結論（candidates.json）。第2回の検査（近似の観点）が、測定の定義、結論の文、候補の網羅を点検した。第2回の検査（報告書の観点）が、32 候補・不採用 16・保留 16 の件数を確かめ、AP-04 と AP-22a の統計を計算し直して一致した。
- **確かめた者**：作成者のみ（件数と 2 候補の統計は独立検査（第2回）で再現。APP-2・3・5・6・7・9 は CONFIRMED、APP-1・4・8 は PARTLY_CONFIRMED）
- **言える範囲**：架空の母集団での測定。近似候補について測ったのは誤差だけである。
- **関係する第2回の指摘**：APP-1、APP-2、APP-3、APP-4、APP-5、APP-6、APP-7、APP-8、APP-9、REP-5、REP-6、REP-13
- **第2回の指摘の影響**：「近似は 1 つも採用していない」「32 種、不採用 16、保留 16」は記録と合う。「厳密な閉形式が同じ手間で使えるため近似の利点がなかった」は、近似候補の時間・メモリ・命令数・入力数を測っていないので、論拠である（REP-6）。「誤差が実建物のばらつきで決まるため…保留した」について：区分パラメータの数字は、評価する建物自身の行から代表値を作った標本内の値で、入力も減らしていない（APP-9）。AP-17 の誤差は質量と距離の標本共分散で決まり、体系的な傾向がなくても −37％〜+117％ になる（APP-4）。修繕については、過小にならない変種を測っていない（APP-1）。「更新回数の連続近似のように重大な過小評価を生む」：AP-01 の測定値は否定されていない（「基準を上回ることがない」は相対 1e-9 の範囲を除く。APP-5）。
- **今の時点で言ってよいこと**：旧研究は近似を 1 つも採用しなかった。測定した近似候補は 32 種で、不採用 16、保留 16。更新回数の連続近似（AP-01）は、架空の母集団の B4 段階で平均 −18.7％、最大 −58.5％ の過小評価になった。保留の候補は、架空データでは採否を決められないとして実データ待ちにした。
- **使ってはいけない記述**：
  - 「厳密な閉形式が同じ手間で使えるため近似の利点がなかった」を測定結果として引用すること
  - 「誤差が実建物のばらつきで決まるため」を、保留のただ 1 つの理由として引用すること
  - 近似候補を「測定した」を、時間・メモリ・入力数の削減まで測ったという意味で引用すること（指示書 第5章が求めた測定のうち、行ったのは誤差だけ）
  - この要点を「建築 LCA の計算式は近似できない」という一般の結論として引用すること（候補は 32 種の単純な近似と代理モデルに限られる）
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：新研究で、既に試して外れた近似と、結論が出ていない近似を区別するために引用する。
  - 条件・注意：数字は架空の母集団の値。32 種の題名に、フーリエ変換・ラプラス変換・特異値分解・モード分解などによる候補はない。
- **分類の根拠**：
  - [`09_APPROX_STUDY/README.md`](../../../09_APPROX_STUDY/README.md):28
  - [`09_APPROX_STUDY/03_MODELS/candidates.json`](../../../09_APPROX_STUDY/03_MODELS/candidates.json): candidates 32 件（outcome は REJECTED 16、HOLD 16。step は M3 19、M4 8、M5 2、M6 3）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):36-41（REP-6）
  - [`materials/round2_review/triage/approx.md`](../materials/round2_review/triage/approx.md):1-11（APP-1）、37-47（APP-4）、49-59（APP-5）、97-107（APP-9）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):128（CHECKS PERFORMED 1：32 候補、不採用 16、保留 16 が一致）
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

<a id="ck-r5-16"></a>

## CK-R5-16　README の要点 6「入力項目は減っていない」

- **区分**：2　暫定・未検証成果
- **内容**：第9章 README「結果の要点」の 6。全文：「入力項目は減っていない。厳密な統合では、読む入力は基準計算と同じだった（実測）。入力を減らすには少数入力の近似モデルが必要だが、その精度は実建物のデータがなければ検証できない。」
- **所在**：
  - [`09_APPROX_STUDY/README.md`](../../../09_APPROX_STUDY/README.md)
  - [`09_APPROX_STUDY/04_VERIFICATION/input_usage.json`](../../../09_APPROX_STUDY/04_VERIFICATION/input_usage.json)
  - [`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../../09_APPROX_STUDY/04_VERIFICATION/README.md)
  - [`09_APPROX_STUDY/05_DECISIONS/README.md`](../../../09_APPROX_STUDY/05_DECISIONS/README.md)
- **確かめ方**：bench/input_usage.py が、33 の架空シナリオで、計算の途中に読まれたシナリオの属性を記録した（input_usage.json）。基準計算、統合モデルの全出力、統合モデルの合計のみのどれも、入力仕様の項目 77＋旧研究が加えた項目 56。第2回の検査（報告書の観点）は、報告書の表が JSON と一致することを確かめ、「入力は減っていない」を、構成上当然で、そう開示されている結果に分類した。読み取りの記録を独立に取り直したかどうかは、検査の記録の文面からは判別できない。
- **確かめた者**：作成者のみ（報告書と JSON の一致は独立検査（第2回）で再現）
- **言える範囲**：架空データ、33 シナリオ。記録しているのは属性の読み取りで、読まれた項目は、必要な項目の上限である（input_usage.json の説明）。
- **関係する第2回の指摘**：REP-1、REP-6、REP-7、APP-9
- **第2回の指摘の影響**：要点 6 の第 1 文・第 2 文そのものを否定する指摘はない。関連する別の文が誤りである。04_VERIFICATION「入力仕様 124 項目のうち 0 項目は記録用」：実際は 47 項目がどの計算にも読まれない（REP-1）。05_DECISIONS の表「単位が参照する入力項目 116（既存 88＋追加 28）｜同じ｜変化なし」：台帳の申告の数で、測定ではない。隣の行の 77＋56 と説明なしに食い違う。台帳に載っている仕様の項目のうち 12 項目は読まれない（REP-7）。保留の候補が述べる入力の削減は数えていない（REP-6）。AP-18 の系統と AP-19a は入力を減らしていない（APP-9）。
- **今の時点で言ってよいこと**：厳密な統合では、統合モデルが読む入力項目は基準計算と同じだった（33 の架空シナリオでの読み取りの記録で、どちらも 入力仕様の項目 77＋旧研究が加えた項目 56。基準計算は読むが統合モデルは読まない項目は 0）。厳密な統合は結果を変えないので、これは構成上当然の結果である。
- **使ってはいけない記述**：
  - 04_VERIFICATION/README.md「入力仕様 124 項目のうち 0 項目は記録用で、どの計算にも使われない」
  - 05_DECISIONS/README.md の表の行「単位が参照する入力項目 116（既存 88＋追加 28）｜同じ｜変化なし」を測定値として引用すること
  - 「入力を減らすには少数入力の近似モデルが必要」を、確かめられた結論として引用すること（旧研究の文書自身が、厳密なまま入力を減らす案を未実施として挙げている：06_OPEN_ISSUES G-2 の建替なしを範囲比 0 で表す案、G-3 の年次表を入力から外す案、AP-21 の貯蔵量を 1 つの入力にまとめる恒等式）
  - 台帳の単位ごとの入力の一覧を、基準計算が実際に使う入力として引用すること（REP-7）
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：新研究で入力の数を比べるときの基準（基準計算が読む項目の数）として引用する。
  - 条件・注意：77 と 56 は旧研究の記録上の値。台帳の入力の一覧を実測に合わせて作り直す作業（b3）は未着手のまま終了している。
- **分類の根拠**：
  - [`09_APPROX_STUDY/README.md`](../../../09_APPROX_STUDY/README.md):29
  - [`09_APPROX_STUDY/04_VERIFICATION/input_usage.json`](../../../09_APPROX_STUDY/04_VERIFICATION/input_usage.json): scenarios = 33、inputs_in_specification = 124、metadata_only_inputs = 0、summary の 3 つの計算とも existing_inputs_read = 77、added_inputs_read = 56、not_read_by_reference は 64 項目
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):1-6（REP-1）、43-48（REP-7）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):128（CHECKS PERFORMED 4：構成上当然で開示済みの結果として「inputs not reduced」）
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md):100-101（G-2、G-3）
  - [`09_APPROX_STUDY/05_DECISIONS/README.md`](../../../09_APPROX_STUDY/05_DECISIONS/README.md):60（AP-21：入力は 3 つから 2 つになる（恒等））
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

<a id="ck-r5-17"></a>

## CK-R5-17　README の要点 7「材料・用途・構造の違いは式に現れず、データの違いとして扱う（設計上）」

- **区分**：2　暫定・未検証成果
- **内容**：第9章 README「結果の要点」の 7。全文：「独立概念モデルでは（設計上）、材料・用途・構造の違いは式には現れず、行（数量と係数）というデータの違いとして扱っている。評価期間と更新・修繕の条件は、乗数の関数の引数になる。原版に工種別・用途別の式があるかどうかは、調べていない。」
- **所在**：
  - [`09_APPROX_STUDY/README.md`](../../../09_APPROX_STUDY/README.md)
  - [`09_APPROX_STUDY/03_MODELS/README.md`](../../../09_APPROX_STUDY/03_MODELS/README.md)
  - [`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md)
- **確かめ方**：独立概念モデルの設計についての記述。第1回の検査が「結果のように書かれている」と指摘し、設計によるものであることを明記した。第2回の検査（報告書の観点）は、この文を、構成上当然で、そう開示されている結果に分類し、誤りを指摘していない。「乗数の関数の引数になる」は DERIVATIONS.md の D2〜D4 の形で、周期で与えられる更新・修繕・建替について、681 架空シナリオで基準計算と一致している。
- **確かめた者**：独立検査（第1回）の指摘で表現を是正。独立検査（第2回）で否定されず
- **言える範囲**：独立概念モデルの設計の記述であり、発見ではない。架空データ。原版に工種別・用途別の式があるかどうかは調べていない（文自身が述べている）。
- **関係する第2回の指摘**：REC-1、REC-7
- **第2回の指摘の影響**：文そのものを否定する指摘はない。限定が 2 つある。修繕の乗数の閉形式は、周期 1.000000001 年で基準計算の値と食い違う（REC-1。乗数の関数の引数になるという形の記述は変わらない）。もう 1 つ：明示の更新年一覧を持つ設備は、乗数の関数ではなく行ごとの加算で計算している（REC-7。DERIVATIONS.md の D2 には書いてある）。材料区分別の誤差の差は、架空データの生成器の設定を映したもので、実建物の性質ではない（第2回の検査が、開示済みとして確認）。
- **今の時点で言ってよいこと**：独立概念モデルは、材料・用途・構造の違いを式ではなく行（数量と係数）というデータの違いとして表すように設計されている。評価期間と、周期で与えられる更新・修繕・建替の条件は、乗数の関数の引数になる。原版に工種別・用途別の式があるかどうかは、調べていない。ただし、木材だけ・コンクリートだけ・固定の 6 資材区分を対象にする単位（STO-01、STO-02、X-17）がある。70 単位の式に材料別の式が無いことを、独立に点検した記録は無い（第2回の検査は、この文を「構成上当然で、そう開示されている」に分類しただけである）。
- **使ってはいけない記述**：
  - この文を「建築 LCA の計算では材料・用途・構造による式の違いがない」という一般の知見として引用すること
  - 原版ブックの構造についての記述として引用すること
  - 「乗数の関数の引数になる」を、明示の更新年一覧を持つ行にも当てはめること
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：新研究が計算の体系を「行（データ）×少数の乗数の関数」として表し直すときの、整理の出発点にする。
  - 条件・注意：設計上の選択である。規約を変えると形が変わる（例：06_OPEN_ISSUES B-8 の、更新時点の係数を使う場合は、回数×1 回当たりではなく事象の年ごとの係数の和になる。実装も検証もしていない）。
- **分類の根拠**：
  - [`09_APPROX_STUDY/README.md`](../../../09_APPROX_STUDY/README.md):30
  - [`09_APPROX_STUDY/03_MODELS/README.md`](../../../09_APPROX_STUDY/03_MODELS/README.md):28-44（全体の形と、設計の結果であるという断り）
  - [`09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md`](../../../09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md):59（「結果のように書かれていた」→ 設計によるものと明記）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):128（CHECKS PERFORMED 4：構成上当然で開示済みの結果）
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):73-83（REC-7：B4-02 の明示の一覧の行は行ごと）
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md):51（B-8）
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):1-11（REC-1）
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）
- **停止後の点検による訂正**：点検の指摘 V2-01 により、上の記述の一部を改めた。分類担当の元の記述は `materials/classification/R5.json`、訂正の内容は `materials/classification/overrides.json` にある。

<a id="ck-r5-18"></a>

## CK-R5-18　05_DECISIONS/README.md の採否の理由（採用・不採用・保留・現状維持の文面）

- **区分**：2　暫定・未検証成果
- **内容**：旧指示書の成果物 7 に当たる文面。「採用（研究上の推奨）」（K1〜K7 を厳密な統合として推奨し、モデルごとの単位数と、名称から推定したシート族を表にする）、「不採用」16 候補の理由、「検証保留」16 候補の理由と必要なデータ、「現状のまま維持」（統合しなかった 4 単位と、すべての検査は近似しないこと）、進捗の集計からなる。candidates.json、models.json、進捗台帳から自動生成される。
- **所在**：
  - [`09_APPROX_STUDY/05_DECISIONS/README.md`](../../../09_APPROX_STUDY/05_DECISIONS/README.md)
  - [`09_APPROX_STUDY/03_MODELS/candidates.json`](../../../09_APPROX_STUDY/03_MODELS/candidates.json)
  - [`09_APPROX_STUDY/03_MODELS/models.json`](../../../09_APPROX_STUDY/03_MODELS/models.json)
- **確かめ方**：件数と文は JSON と一致する（第2回の検査で確認）。中身は、各候補の測定（作成者）と、第2回の指摘による。
- **確かめた者**：作成者のみ（JSON との一致は独立検査（第2回）で再現。内容には第2回の指摘があり未修正）
- **言える範囲**：架空データ、独立概念モデル。「採用」は将来の実装候補としての推奨で、製品への組み込みを意味しない（文面自身の断り）。
- **関係する第2回の指摘**：REC-2、REC-3、REP-4、REP-5、REP-6、REP-9、APP-2、APP-5、APP-6、APP-9、NUM-1、NUM-2
- **第2回の指摘の影響**：「7 つの統合モデル（K1〜K7）を、厳密な統合として推奨する。681 の架空シナリオ…で、基準計算と全出力が一致し、入力検査の結果も同じだった」：681 シナリオの一致は成り立つ。表の「まとめた単位数」（26、9、10、4、8、3、6）は REC-2・REP-4 で争われている。K7 の「組ごとに 1 回解決」は行ごとの換算を持たない行だけである（REC-3）。「共通する理由は 2 つ…(2) 厳密な閉形式が同じ手間で使えるので、近似に替える利点がない」：(2) は測定のない論拠（REP-6）。「統合しなかった 4 単位…検査は判定の対象と基準がそれぞれ違い」：検査は 3 単位（REP-9）。「測定や導出の裏付けが 1 件もない単位は『完了』にしない規則にしている（該当なし）」：B1-01 は、争われている M2 の記録を除くと該当する（REC-2）。「M4 は…いずれも誤差が実建物のばらつきで決まるため保留」：APP-9 と REP-5 の限定がつく。候補ごとの理由文の限定は CK-R5-05 と CK-R5-06。
- **今の時点で言ってよいこと**：旧研究の最後の判断として、(1) 近似は採用しない、(2) K1〜K7 を将来の実装候補として推奨する、(3) 16 候補を不採用、16 候補を実データ待ちの保留にする、(4) 検査（SYS・QA・C-05）は近似せず、判定の基準を変えない、と記録されている。
- **使ってはいけない記述**：
  - 推奨を「検証済みの統合モデル 7 つ」として引用すること
  - 表の「まとめた単位数」の列
  - 表の「関連すると推定されるシート族（数式ノード占有率）」を、原版の式がそのモデルで置き換えられる割合として引用すること（シート名だけからの推定で、式の本文は全シート族で未確認）
  - 「厳密な閉形式が同じ手間で使える」を測定結果として引用すること
  - 「入力検査の結果も同じだった」を、試した不備の種類の外まで広げること（NUM-2 ほか）
- **新研究での再利用**：候補（ルート A・C）
  - 使い道：旧研究が最後に何を推奨し、何を退け、何を保留にしたかの一覧として引用する。
  - 条件・注意：推奨は旧研究の主担当の判断で、第2回の指摘を反映していない。新研究は、少数の変換の種類を減らすためなら式が複雑になることを許すので、旧研究の「利点がない」という不採用の理由に縛られない。
- **分類の根拠**：
  - [`09_APPROX_STUDY/05_DECISIONS/README.md`](../../../09_APPROX_STUDY/05_DECISIONS/README.md):9-21（採用）、25-42（不採用）、46-61（検証保留）、65-66（現状のまま維持）、80-82、95
  - [`09_APPROX_STUDY/research_code/tools/build_reports.py`](../../../09_APPROX_STUDY/research_code/tools/build_reports.py):378-461（この文面の生成）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):128（CHECKS PERFORMED 1：05_DECISIONS の数字が一致）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):36-41（REP-6）、57-62（REP-9）
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):13-35（REC-2、REC-3）
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

<a id="ck-r5-19"></a>

## CK-R5-19　05_DECISIONS/README.md「統合前後の変化」の表（行ごとの状態）

- **区分**：2　暫定・未検証成果
- **内容**：旧指示書の成果物 8 に当たる表。計算の定義の数、共通化できた単位、単位が参照する入力項目、読まれた入力項目、命令数（規模 L の 4 通り）、計算時間、ピークメモリ、結果の差の 13 行と、5 つの注記からなる。独立概念モデルについての値で、原版ブックの数式の数や計算時間の変化を示さない（表の前の断り）。
- **所在**：
  - [`09_APPROX_STUDY/05_DECISIONS/README.md`](../../../09_APPROX_STUDY/05_DECISIONS/README.md)
  - [`09_APPROX_STUDY/04_VERIFICATION/unified_model_load.json`](../../../09_APPROX_STUDY/04_VERIFICATION/unified_model_load.json)
  - [`09_APPROX_STUDY/04_VERIFICATION/input_usage.json`](../../../09_APPROX_STUDY/04_VERIFICATION/input_usage.json)
  - [`09_APPROX_STUDY/03_MODELS/models.json`](../../../09_APPROX_STUDY/03_MODELS/models.json)
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
- **確かめ方**：表の数字は JSON と一致し、削減率は生の値から計算し直して一致した（第2回の検査、報告書の観点）。命令数は規模 S・M だけ数え直しがあり、この表が使う規模 L は実行し直していない。
- **確かめた者**：作成者のみ（表と JSON の一致、削減率の計算し直しは独立検査（第2回）で再現）
- **言える範囲**：架空のベンチマーク（規模 L は資材 2 万行）、純粋な Python の実装どうし、同じ機械。
- **関係する第2回の指摘**：REP-4、REP-7、REC-2、REC-3、NUM-1、NUM-10
- **第2回の指摘の影響**：行ごとの状態。「計算の定義の数 70 → 11」「共通化できた単位 66 単位 → 7 モデル」：引用しない（REP-4・REC-2。数の一部はラベルの数）。「単位が参照する入力項目 116（既存 88＋追加 28）｜同じ｜変化なし」：台帳の申告の数で、測定ではない。台帳の「NEW:」28 個のうち、旧研究が加えた属性 73 個の中に名前があるのは 4 個だけで、MATERIAL.construction_division は読まれるのにどの単位にも載っていない（REP-7）。「計算中に読まれた入力項目（実測）既存 77＋追加 56」：旧研究の記録上の測定値。命令数（245,195,907 → 82,539,384 で 66.3％ 減、64,746,240 で 73.6％ 減、基準案との比較を含めて 57.1％ 減、別の評価期間 4 通りで 92.1％ 減）：旧研究の記録上の測定値で、規模 L は独立に確かめられていない。時間（1689 ms → 862 ms、624 ms）とメモリ（65 MiB → 25 MiB、15 MiB）：機械に依存し、測り直していない。「結果の差：相対 1e-09 以内で一致／精度の低下なし」：681 架空シナリオの範囲で成り立つ（NUM-1〜10 の限定がつく）。
- **今の時点で言ってよいこと**：表の数字は、旧研究が 43ba5d7 の版で記録した値と一致する。規模 S・M の命令数の削減（04_VERIFICATION の表にある）は第2回で数え直して一致した。注記のうち「『計算の定義の数』は、式の種類そのものの数ではない」「入力項目は減っていない」「(b)〜(d) は合計のみを求める場合に最も効く」は、第2回の指摘と矛盾しない。
- **使ってはいけない記述**：
  - 「計算の定義の数 70 → 11」
  - 「共通化できた単位 66 単位 → 7 モデル」
  - 「単位が参照する入力項目 116（既存 88＋追加 28）｜同じ｜変化なし」
  - 規模 L の命令数・時間・メモリを、独立に確かめられた値として引用すること
  - 「精度の低下なし」を入力の限定なしで引用すること
  - 注記 (b)「係数を行ごとに掛けず、表の中で合算してから掛ける」を、全出力の場合や、係数 1 の特別なキーで表に入る買電・冷媒にも当てはめること
- **新研究での再利用**：候補（ルート A・C）
  - 使い道：新研究が「統合前後」を比べる表を作るときの、項目の立て方と、旧研究の側の値として引用する。
  - 条件・注意：新研究は式の数ではなく変換の種類の数を数えるので、「70 → 11」と同じ数え方をしない。値を引用するときは行ごとの状態を添える。
- **分類の根拠**：
  - [`09_APPROX_STUDY/05_DECISIONS/README.md`](../../../09_APPROX_STUDY/05_DECISIONS/README.md):97-121
  - [`09_APPROX_STUDY/research_code/tools/build_reports.py`](../../../09_APPROX_STUDY/research_code/tools/build_reports.py):437-460（表の生成。入力項目の行は台帳の inputs を数えたもの）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):22-27（REP-4）、43-48（REP-7）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):128（CHECKS PERFORMED 1：統合前後の表の数字が一致。load table は削減率を生の値から計算し直した）
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

<a id="ck-r5-20"></a>

## CK-R5-20　旧指示書の必須成果物 9 点（有無と状態）

- **区分**：2　暫定・未検証成果
- **内容**：旧指示書 第8章が求めた 9 つの記録。第9章 README の成果物の表が置き場所を示す。9 点ともファイルとして存在する。どれも 43ba5d7（第1回の検査の対応後）の版で、第2回の指摘 59 件を反映していない。停止時点で、旧タスク #5「必須成果物 9 点の整備、最終監査」と #9「記録・報告書・手書き文書の改訂と、全体の再生成」は未着手だった。
- **所在**：
  - [`09_APPROX_STUDY/README.md`](../../../09_APPROX_STUDY/README.md)
  - [`09_APPROX_STUDY/00_POLICY/DIRECTIVE.md`](../../../09_APPROX_STUDY/00_POLICY/DIRECTIVE.md)
  - [`09_APPROX_STUDY/01_LEDGER/`](../../../09_APPROX_STUDY/01_LEDGER)
  - [`09_APPROX_STUDY/02_RANKING/`](../../../09_APPROX_STUDY/02_RANKING)
  - [`09_APPROX_STUDY/03_MODELS/`](../../../09_APPROX_STUDY/03_MODELS)
  - [`09_APPROX_STUDY/04_VERIFICATION/`](../../../09_APPROX_STUDY/04_VERIFICATION)
  - [`09_APPROX_STUDY/05_DECISIONS/`](../../../09_APPROX_STUDY/05_DECISIONS)
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md)
- **確かめ方**：第2回の検査（報告書の観点）が、成果物 1〜9 がすべて存在すること、指示書への適合（全単位が研究対象、6 状態の表示、M1〜M6 の記録、アプリ・UI のコードがないこと）と、不足（REP-4〜7）を点検した。
- **確かめた者**：独立検査（第2回）で存在を確認。内容には未反映の指摘がある
- **言える範囲**：独立概念モデルについての研究の記録。原版ブックの数式を調べた記録ではない。
- **関係する第2回の指摘**：REP-1、REP-2、REP-3、REP-4、REP-5、REP-6、REP-7、REP-8、REP-9、REP-10、REP-11、REP-13、REP-15、REP-16、REP-17、REP-18
- **第2回の指摘の影響**：成果物ごとの状態。1 全計算式・式群の分類台帳（01_LEDGER）：存在。単位ごとの入力の一覧が基準計算の読む入力と合わない（REP-7）、構造別の件数の見出しが古い（REP-8）、A13-04 の文面が古い（REP-10）、シート族の状態区分が不統一（REP-18）。原版の式の本文は全シート族で未確認。2 評価軸 A のランキング（02_RANKING の axis_a.json）：存在。順位は入力から計算し直して差 0。時間とメモリの絶対値は測り直していない。上位 30％ の一覧は、追加・変更指示 第1号で参考表示になった。3 評価軸 B のランキング（axis_b.json、axis_b_judges）：存在。採点は初版の台帳に対するもので、やり直していない。4 両者を統合した検証対象一覧（research_priority.json：全 70 単位と着手順・3 群）：存在。和集合の文言に誤り（REP-11）。5 検討した近似式・統合モデル（03_MODELS）：存在。REP-2、REP-3、REP-4、REP-9、REP-13 と REC-1〜9。6 基準計算との誤差と処理時間（04_VERIFICATION）：存在。REP-1、REP-15、REP-16 と NUM-1〜11、APP-1〜9。独立した検査の記録は第1回だけ。7 採用・不採用・検証保留の理由（05_DECISIONS、PROGRESS.md）：存在。REP-5、REP-6。8 統合前後の数式数と計算負荷の変化（05_DECISIONS の表）：存在。「70 → 11」は REP-4、「116…同じ」は REP-7。9 未解決事項と追加検証に必要なデータ（06_OPEN_ISSUES）：存在。第2回で分かった事項が載っていない（REP-17 ほか）。
- **今の時点で言ってよいこと**：旧指示書の必須成果物 9 点は、09_APPROX_STUDY の 01_LEDGER〜06_OPEN_ISSUES にファイルとして存在する。全 70 単位が研究対象として管理され、進捗台帳は追加・変更指示 第1号の 6 状態を使い、全単位に M1〜M6 の結論の記録がある。アプリ・UI・Web のコードと、原版のファイルや実在の係数らしい値は含まれていない（第2回の検査が確認）。
- **使ってはいけない記述**：
  - 「必須成果物 9 点がそろった」を、指示書の要求を満たして完成したという意味で引用すること（整備と最終監査は未着手）
  - 指示書 第5章（近似候補の時間・メモリ・入力数の削減の測定、材料・用途・構造別の誤差）への適合（REP-6：材料区分別があるのは 32 候補のうち 7）
  - 指示書 第8章「対象を調べずに『近似できない』と判断してはならない」への適合（REP-5）
  - 指示書 第6章の資源配分（75％・15％・10％）が守られたこと（どこにも報告がなく、第2回の検査も評価できなかった）
  - 成果物 6 の「独立した検査」を、掲載の数字が独立に検査されたという意味で引用すること（REP-15）
- **新研究での再利用**：候補（ルート A・C）
  - 使い道：旧研究の資料の置き場所の一覧として使う。
  - 条件・注意：どの成果物も第2回の指摘を反映していない。各成果物の中身の状態は、対応する項目の分類に従う。
- **分類の根拠**：
  - [`09_APPROX_STUDY/00_POLICY/DIRECTIVE.md`](../../../09_APPROX_STUDY/00_POLICY/DIRECTIVE.md):244-262（第8章 必須成果物）
  - [`09_APPROX_STUDY/README.md`](../../../09_APPROX_STUDY/README.md):55-69（成果物の表）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):128（CHECKS PERFORMED 5：成果物 1〜9 がすべて存在。不足は REP-4〜7。6：禁止された種類のファイルなし）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):130（COULD NOT CHECK：資源配分）
  - [`STOP_STATUS.md`](../STOP_STATUS.md):43-48（旧タスク #5、#9 は未着手）
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

<a id="ck-r5-21"></a>

## CK-R5-21　評価者の提案との対照（judge_proposal_trace.json）：観点と段階の対応づけの誤り

- **区分**：4　不具合・未解決事項
- **内容**：評価軸 B の採点（3 者の中央値）で 2 点以上だった単位について、対応する段階に何を記録したかの対照表（52 行。うち測定なしが 20 行）と、第1回の検査が「取り上げていない」と指摘した具体的な提案 10 件の扱いの一覧。build_records.py が生成する。対照表は、観点と段階の対応づけが手順書と違う。
- **所在**：
  - [`09_APPROX_STUDY/03_MODELS/judge_proposal_trace.json`](../../../09_APPROX_STUDY/03_MODELS/judge_proposal_trace.json)
  - [`09_APPROX_STUDY/research_code/tools/build_records.py`](../../../09_APPROX_STUDY/research_code/tools/build_records.py)
  - [`09_APPROX_STUDY/03_MODELS/README.md`](../../../09_APPROX_STUDY/03_MODELS/README.md)
  - [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md)
- **確かめ方**：第2回の検査（報告書の観点）が、手順書 P5 の観点の定義と生成器の対応づけを照合し、手順書どおりの観点で数え直した。この読み取りでも、対照表の内訳（b6 → M3 が 23 行で測定なし 9、b7 → M4 が 29 行で測定なし 11、測定の記録が AP-15 だけの行が 10）を数えた。
- **確かめた者**：独立検査（第2回）で再現（REP-2。第2検証がなく、主担当が検査担当のスクリプトを再実行して再現）
- **言える範囲**：独立概念モデルの 70 単位に対する、3 つの自動評価の採点の追跡。採点は初版の台帳に対するもの。
- **関係する第2回の指摘**：REP-2、REP-5、REC-3
- **第2回の指摘の影響**：生成器は、b6 を M3（「単純な近似式で置き換えられる」）、b7 を M4（「他の式と共通の近似モデルにできる」）に対応させている。手順書 P5 と指示書では、b7 は「入力変数を減らせそう」で、共通の代理モデルへの統合は b8 である。b8 で数えると、2 点以上は 33 単位、単位×段階は 23＋33 ＝ 56、そのうち測定なしは 14（M3 が 9、M4 が 5：X-06、X-13、X-12、B3-02、X-07）。公表の「52 件／20 件」は、書かれた問いとは別の問いへの答えになっている。また、「測定あり」とした行のうち 10 行は、建物全体の代理（AP-15）だけが測定の記録である。b5（複雑な条件分岐を近似で置き換える）と b8 は追跡されていない。
- **今の時点で言ってよいこと**：ファイルの数（52、20）は、生成器の対応づけ（b6 → M3、b7 → M4）に従って数えた結果としては記録と合う。具体的な提案 10 件の一覧は、第1回の検査が挙げた提案を、どの記録で扱ったか（または扱っていないか）を主担当が書いたもので、2 件（B5-01 の「建替なしを範囲比 0 として表す」、X-07 の「累積系列を乗数から直接求める閉形式」）は未実装・未検証と明記されている。
- **使ってはいけない記述**：
  - 03_MODELS/README.md「評価軸 B の採点で『近似・共通化できる』が 2 点以上だった単位×段階は 52 件。このうち測定をせずに理由だけで見送ったものは 20 件」
  - 対照表の「測定あり」を、その単位の式について近似を測定したという意味で引用すること
  - INDEPENDENT_REVIEW.md 2.3「評価者が挙げた置き換え案…測定を追加し、対照表を作った」を、評価者の提案がすべて追跡されたという意味で引用すること
  - 提案の一覧の「係数解決は係数・段階・単位の組ごとに 1 回にした（厳密）」（REC-3 の限定がつく）
- **新研究での再利用**：候補にしない
  - 理由・注意：対照表を作り直す案（b1 → M1、b2・b3・b4 → M2、b5・b6 → M3、b8 → M4 と M5、b7 は測定した候補へ）は、未着手のまま終了している。
- **分類の根拠**：
  - [`09_APPROX_STUDY/research_code/tools/build_records.py`](../../../09_APPROX_STUDY/research_code/tools/build_records.py):540-549（b6 → M3、b7 → M4 の対応づけ）
  - [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md):122-131（P5：b7 は入力変数を減らせそう、b8 は異なる式を共通の代理モデルへ統合できそう）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):8-13（REP-2）
  - [`09_APPROX_STUDY/03_MODELS/judge_proposal_trace.json`](../../../09_APPROX_STUDY/03_MODELS/judge_proposal_trace.json): score_2_or_more 52 行（criterion は b6 23、b7 29）、not_measured 20 行、named_proposals 10 件
  - [`09_APPROX_STUDY/03_MODELS/README.md`](../../../09_APPROX_STUDY/03_MODELS/README.md):130-145
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

<a id="ck-r5-22"></a>

## CK-R5-22　未解決事項の一覧（06_OPEN_ISSUES/README.md の A〜H）

- **区分**：4　不具合・未解決事項
- **内容**：旧指示書の成果物 9 に当たる手書きの一覧。A 原資料について調べられていないこと（A-1〜A-6）、B 独立モデルの定義として旧研究が決めた点（B-1〜B-21）、C 実データがないために保留している検証（C-1〜C-9）、D 精度について検証できていないこと（7 項目）、E 測定についての注意、F 権利について残っていること、G 検討したが実装・測定していないもの（G-1〜G-7）、H 次の段階に向けて。
- **所在**：
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md)
- **確かめ方**：手書き。第2回の検査（報告書の観点）が、B-7（更新 31 回 → 19 回、B4 が 40.6％ 減、ホールライフ合計が 1.9％ 減）、B-10（規模 S で SUM-02 の 7.0％）、B-11（A4 の 0.12％、A5 の 5.0％）の影響の数字を再現した。第2回の検査（定義の観点）が、B の一覧をコードと照合した。
- **確かめた者**：作成者のみ（B-7・B-10・B-11 の数字は独立検査（第2回）で再現）
- **言える範囲**：停止の時点で未解決のまま残っている事項。独立概念モデルと架空データについての研究の限界を述べる。
- **関係する第2回の指摘**：REP-17、RED-1、RED-2、RED-3、RED-7、RED-8、RED-10、RED-11、NUM-1、NUM-10
- **第2回の指摘の影響**：B の一覧は規約を網羅しておらず、B-15・B-17・B-18・B-21 の文は第2回の指摘と合わない。D-3 の「改めた後の版に対する独立検査は、まだ行っていない」は古い。内容は CK-R5-23 にまとめた。A、C、E、F、G への指摘はない。
- **今の時点で言ってよいこと**：次の事項は、停止の時点でもそのまま未解決である。A：原版ブックの式の本文は全シート族で未確認で、評価単位が原版の計算構造をどこまで覆うかは検証していない。C：保留している近似候補と、判断に必要な実データ。D-1・D-2：実建物での精度と、他のツールの結果との一致は検証していない。D-5：資材 2 万行までしか測っていない。D-6・D-7：単位ごとの代理モデルは作っておらず、「候補なし」は測定のない判断である。F：権利者への照会の結果は反映されておらず、独立した係数データは未入手。G-1〜G-7：実装・測定していない案（累積系列の閉形式、建替なしを範囲比 0 で表す、年次表を入力から外す、更新時点の係数を使う場合の統合、など）。B-7・B-10・B-11 の影響の数字は、第2回の検査が再現した。
- **使ってはいけない記述**：
  - B-1〜B-21 を、基準計算の規約の完全な一覧として引用すること
  - B-17「使えない行・経路・項目は合計に入れず、件数を報告し、合計に『不完全』の印を付ける」（RED-1：B3 または B5 を含み上流の段階を含まない対象範囲では印が立たない）
  - B-18「負の数量…範囲外の率…は、その行を計算から除いて数える」を全項目について引用すること（RED-2：年次量の負や非数は黙って使われる）
  - B-21 を、計算全体がエラーになるただ 1 つの場合として引用すること（REP-17、RED-10）
  - B-15 の許容幅を「浮動小数点の誤差で端をまたがないようにする」ものとして引用すること（NUM-1・REC-1：周期 1.000000001 年では、許容幅のために年の割り当てが丸めで決まる）
  - D-3「改めた後の版に対する独立検査は、まだ行っていない」
  - B-8 と G-6 の「同じ枠組みに入ると見込まれる」を結果として引用すること（実装も検証もしていない）
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：新研究の未解決事項の最初の一覧と、必要なデータの一覧として使う。G-1、G-2、G-3、G-6 は、新研究で扱える未着手の案である。
  - 条件・注意：第2回で分かった事項（CK-R5-23）を足して読む。実データは、利用条件を確認したうえで、原単位などの流用禁止に触れないものに限る（一覧自身の注記）。
- **分類の根拠**：
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md):5-18（A）、20-51（B）、53-69（C）、71-79（D）、81-87（E）、89-93（F）、95-105（G）、107-110（H）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):128（CHECKS PERFORMED 2：B-7、B-10、B-11 の影響の数字が再現）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):113-118（REP-17）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):1-11（RED-1）、13-23（RED-2）
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

<a id="ck-r5-23"></a>

## CK-R5-23　未解決事項の一覧に載っていない事項と、古くなった記述（第2回で判明）

- **区分**：4　不具合・未解決事項
- **内容**：第2回の検査で確認されたが、06_OPEN_ISSUES/README.md にも、ほかの 09_APPROX_STUDY の文書にも書かれていない規約・穴・限界と、古くなった記述の一覧。
- **所在**：
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md)
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md)
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md)
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md)
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md)
  - [`materials/interrupted_fix/specs/STAGE_C_NOTES.md`](../materials/interrupted_fix/specs/STAGE_C_NOTES.md)
- **確かめ方**：第2回の検査（定義・数値・記録・報告書の観点）が、一覧とコードを照合し、反例を作って確かめた。それぞれ第2の検証担当が判定した（REP は第2検証なし）。
- **確かめた者**：独立検査（第2回）で再現（RED-3・RED-11 は PARTLY_CONFIRMED、ほかは CONFIRMED。REP-17 は第2検証なし）
- **言える範囲**：43ba5d7 の基準計算と統合モデル。架空データ、独立概念モデル。
- **関係する第2回の指摘**：REP-15、REP-17、RED-1、RED-2、RED-3、RED-5、RED-7、RED-8、RED-10、RED-11、NUM-1、NUM-10、REC-1
- **第2回の指摘の影響**：載っていない事項。(1) 年次表が評価期間より短いと、記述子が整っていても両方の計算が例外を出す規約。「別の評価期間の結果を合算のやり直しなしに求める」は、年次表の長さ以内に限られる（REP-17）。(2) 資材の初期の据付を計上しない規約（B-11 は設備だけを挙げる。RED-8）。(3) 未数量分（A13-04）の上乗せを「行の製造排出」に含めるかどうかの規約（RED-7）。(4) 無効な周期・耐用年数（負、0、非数、無限大）を、数えも印も付けずに「事象なし」として扱う規約（RED-3）。(5) 年次量の負や非数は黙って使われ、電力係数、係数の値、換算の乗数は検査されない（RED-2）。(6) 完全性の印が立たない対象範囲があり（RED-1）、基準案との比較（SUM-08）は不完全な合計どうしを比べる（RED-5）。(7) 明示の更新年の重複はそれぞれ数える、など（RED-11）。制御されていない例外がある（RED-10）。(8) 桁落ちや桁あふれが起きる入力での数値の限界。D-4 は許容差だけを述べる（NUM-10）。(9) 周期 1.000000001 年での年の割り当ての丸め（NUM-1・REC-1）。古くなった記述：D-3 と INDEPENDENT_REVIEW.md の「まだ行っていない」（第2回の検査は実施済みで、09_APPROX_STUDY には記録がない）。
- **今の時点で言ってよいこと**：上の事項は、第2回の検査で確認された、文書に載っていない規約・穴・限界である。本文は archive の materials/round2_review/triage/ にある。
- **使ってはいけない記述**：
  - 06_OPEN_ISSUES/README.md を、未解決事項の完全な一覧として引用すること
  - STAGE_C_NOTES.md に書かれた追記予定の試算値（資材の初期据付が規模 S で A5 の 41.1％・ホールライフ合計の 0.096％、A13-04 の上乗せの扱いで規模 S の B4 が +0.54％・B3 が +3.93％）を確定値として引用すること（覚え書き自身が「測り直す」としている）
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：新研究が基準計算を変えずに使うときの、既知の穴と未記載の規約の一覧として使う。
  - 条件・注意：中断した修正 a1 はこの一部を直したと自己申告しているが、未検証で、作業ツリーから取り除かれている。新研究では基準計算を変えないので、これらは「基準計算の既知の性質」として扱う。
- **分類の根拠**：
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):113-118（REP-17）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):25-35（RED-3）、73-83（RED-7）、85-95（RED-8）、109-119（RED-10）、121-131（RED-11）
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):109-119（NUM-10）
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md):75（D-3）、76（D-4）
  - [`materials/interrupted_fix/specs/STAGE_C_NOTES.md`](../materials/interrupted_fix/specs/STAGE_C_NOTES.md):51-55（追記の予定と、測り直すとした試算値）
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

<a id="ck-r5-24"></a>

## CK-R5-24　第1回の独立検査の記録（INDEPENDENT_REVIEW.md：指摘と対応）

- **区分**：2　暫定・未検証成果
- **内容**：初版に対して行った 3 つの自動検査（数値の反例探し、定義からの再導出、記録の監査）の主な指摘と、それへの対応を、主担当がまとめた手書きの記録。2.1 一致が条件付きだった（3 件）、2.2 定義の穴（9 件）、2.3 記録がコードより強いことを言っていた（15 件）、3 対応していないもの（3 件）、4 問題が見つからなかった点（4 件）。検査担当は互いの出力を見ない自動の AI エージェントで、人による検査ではない。
- **所在**：
  - [`09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md`](../../../09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md)
  - [`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../../09_APPROX_STUDY/04_VERIFICATION/README.md)
- **確かめ方**：対応後の一致の確認は、主担当が検証スクリプトを広げて行った（文書自身の記載）。第2回の検査は対応後の版（43ba5d7）を対象にし、対応の一部が不完全であることを示した。
- **確かめた者**：作成者のみ（対応の記述）。対応後の版は独立検査（第2回）の対象になり、一部の対応が否定された
- **言える範囲**：初版に対する検査と、43ba5d7 までの対応の記録。第2回の検査については何も書かれていない。
- **関係する第2回の指摘**：RED-1、RED-2、NUM-1、NUM-2、REC-1、REC-2、REC-4、REC-5、REP-2、REP-5、REP-6、REP-9、REP-15
- **第2回の指摘の影響**：対応の記述のうち、第2回で否定または限定されたもの。2.1「整っていなければどちらも年次表を使う」：低下量などが非数のとき、基準計算は年次表を使い、統合モデルは例外を出す（NUM-2）。2.2「使えない行・経路・項目は合計に入れず…合計に『不完全』の印を付ける」：印が立たない対象範囲がある（RED-1）。2.2「除外して数える規則に統一」：年次量の負や非数は黙って使われる（RED-2）。2.2「判定に許容幅を定義し、両方の計算で同じ判定式を使う」：周期 1.000000001 年で食い違う（NUM-1・REC-1）。2.3「記録が述べる仕組みを、統合モデル自身が数えた回数で確かめるようにした（成り立たなければ記録の生成が失敗する）」：計数の一部は反する動作を数えず、機構のない成功記録も生成される（REC-4・REC-5）。2.3「統合の基準を定義…検査は実際に共有の関数にした 3 単位だけを統合に数える」：基準を満たさない所属が残り（REC-2）、models.json は検査 9 単位のうち 6 単位を統合に数えている（REP-9）。2.3「B5 と X-10 でも測定した」：その単位で測っていない誤差を引用する記録が、AP-08（B2-01、B6-04）と AP-05（B1-03、B1-04）に残る（REP-5）。2.3「材料区分別の誤差…追加」：あるのは 32 候補のうち 7（REP-6）。2.3「対照表を作った」：対応づけが違う（REP-2）。冒頭「対応後の版に対する独立した検査は、まだ行っていない」：古い。
- **今の時点で言ってよいこと**：第1回の検査が何を指摘し、主担当がどう対応したと記録したかの一覧として読める。記録と報告書に関する対応のうち、第2回の記録・報告書の観点で否定する指摘が出ていないもの：M6 の成功 14 件を厳密な計算どうしの場合分けとして M1 に移した、導出のない記録を「架空データでの一致のみ」と表示する（該当 5 件）、主な指標を命令数にして時間はごみ集めを止めて測る、「全体は 1 つの式で書ける」などが設計によるものであることの明記、検査担当や評価者が自動の AI エージェントであることの明記、シート族と評価単位の対応の出所を 1 つにしたこと（対応の不一致は 0）。3 の「対応していないもの」（出所レコードごとの入力状態の前計算、累積系列の閉形式、建替なしを範囲比 0 とする入力の整理は実装していない。評価軸 B の採点はやり直していない）は、そのまま残っている。
- **使ってはいけない記述**：
  - この文書を、対応が済んだことの証明として引用すること
  - 上の「否定または限定された」対応の記述
  - 4「報告書の数字 54 個を JSON から再計算し、すべて一致した」「規模 L の比較でも基準計算と一致した」を、現在の版についての記述として引用すること（どちらも初版についての記述）
  - 「独立した検査」を、人による検査の意味で引用すること
- **新研究での再利用**：候補にしない
  - 理由・注意：2.1・2.2 の、基準計算の定義に関する対応の当否は、基準計算の観点の分類に従う。第1回の指摘の原資料は archive の materials/earlier_session_scratch/verify/ にあるが、この読み取りでは開いていない。
- **分類の根拠**：
  - [`09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md`](../../../09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md):3-8（検査の性格と「まだ行っていない」）、20-26（2.1）、28-40（2.2）、42-60（2.3）、62-66（3）、68-73（4）
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):13-23（NUM-2）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):1-23（RED-1、RED-2）
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):37-59（REC-4、REC-5）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):29-34（REP-5）、57-62（REP-9）
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

<a id="ck-r5-25"></a>

## CK-R5-25　検査の記録の欠落と、検査されていない範囲

- **区分**：4　不具合・未解決事項
- **内容**：(1) 第2回の独立検査（指摘 59 件：NUM 11、RED 12、REC 9、APP 9、REP 18。判定は CONFIRMED 33、PARTLY_CONFIRMED 8、反証 0。REP の 18 件は第2の検証担当なし）が、09_APPROX_STUDY のどの文書にも記録されていない。(2) 第9章 README の本文は、掲載の数字が第1回の対応後の版のもので、その版への独立検査が済んでいなかったことを述べていない。(3) 第2回でも確かめられなかった範囲がある。(4) 中断した修正（65ff124）に対する反証の検査は始まっていない。
- **所在**：
  - [`09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md`](../../../09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md)
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md)
  - [`09_APPROX_STUDY/README.md`](../../../09_APPROX_STUDY/README.md)
  - [`materials/round2_review/triage/res.json`](../materials/round2_review/triage/res.json)
  - [`STOP_STATUS.md`](../STOP_STATUS.md)
- **確かめ方**：STOP_STATUS.md の記載と、第2回の検査の「確かめられなかったこと」の記載による。判定の件数は、この読み取りで res.json を数えて確認した（数値 11 件すべて CONFIRMED、定義 9＋3、記録 7＋2、近似 6＋3、報告書 18 件は判定なし）。
- **確かめた者**：独立検査（第2回）の記録と、停止を実施した作業担当の記録（第三者の確認ではない）
- **言える範囲**：旧研究の検査の記録の状態。
- **関係する第2回の指摘**：REP-15
- **第2回の指摘の影響**：第2回の結果は archive の materials/round2_review/triage/ にだけある。第2回でも確かめられなかったこと：分類台帳の分析担当・評価者・第1回の検査担当が互いの出力を見ずに作業したかどうか。規模 L の命令数と、時間・メモリの絶対値。近似の測定の全体（報告書の観点が計算し直したのは 32 候補のうち 2 候補）。機構の計数の全箇所。材料分類の設計の中身と、そのレビュー記録の個々の項目。資源配分。シート名を公開資料に含めてよいかどうか。記録の観点は、近似（AP）の記録とその誤差の統計を対象にしていない。
- **今の時点で言ってよいこと**：09_APPROX_STUDY の中で「独立した検査」と書かれているものは、第1回（初版に対する 3 つの自動検査）だけを指す。第2回の検査の指摘 59 件は、記録・進捗台帳・報告書・手書きの文書のどれにも反映されていない。
- **使ってはいけない記述**：
  - 第9章 README の成果物 6 の「独立した検査」を、掲載の数字が独立に検査されたという意味で引用すること
  - INDEPENDENT_REVIEW.md と 06_OPEN_ISSUES D-3 の「まだ行っていない」を、現在の状態として引用すること
  - REP-1〜18 を、第2の検証担当が確かめた指摘として引用すること（主担当が検査担当のスクリプトを再実行して再現したもの）
  - 中断した修正 a1・b2 の報告にある試験や一致の結果を、検査済みとして引用すること（自己申告）
- **新研究での再利用**：候補にしない
  - 理由・注意：第2回の結果を INDEPENDENT_REVIEW.md に書き足す作業は予定されていたが、未着手のまま終了している（旧研究の文書は書き換えない）。
- **分類の根拠**：
  - [`STOP_STATUS.md`](../STOP_STATUS.md):50-63（第2回の指摘の反映の内訳。記録・報告書は第2回の指摘を反映していない）
  - [`materials/round2_review/triage/res.json`](../materials/round2_review/triage/res.json): 観点ごとの verdicts を数えると CONFIRMED 33、PARTLY_CONFIRMED 8。reports は verdicts なし
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):99-104（REP-15）、130（COULD NOT CHECK）
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):112（COULD NOT CHECK：近似の記録は対象外）
  - [`09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md`](../../../09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md):7-8
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md):75
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

<a id="ck-r5-29"></a>

## CK-R5-29　記録・台帳・報告書の生成器（research_code/tools/ の 5 本）：どの生成器がどのファイルを書くか

- **区分**：2　暫定・未検証成果
- **内容**：tools/sync_ledger.py：基準計算の関数の説明文と依存関係を 01_LEDGER/units.json（reference_semantics、depends_on、feeds、sheet_family_links）へ写し、01_LEDGER/sheet_family_coverage.json を更新する。refcalc を取り込んで動く。tools/rank_axes.py：台帳、シート族の情報、軸 A の測定、評価者の採点から、02_RANKING の axis_a.json、axis_b.json、research_priority.json を書く。tools/build_records.py：unified_model_exactness.json、approximation_study.json、台帳、axis_b.json、DERIVATIONS.md の見出しから、03_MODELS の models.json、candidates.json、records/units.json、judge_proposal_trace.json を書く。単位×段階の計画表、候補の結論の文、候補なしの定型文、統合モデルの定義文、評価者の提案の扱いは、このファイルの中に手書きされている。tools/progress_ledger.py：記録、台帳、着手順から、05_DECISIONS の progress_ledger.json と PROGRESS.md を書く（check は検査だけ）。tools/build_reports.py：JSON から 6 つの README（第9章、01_LEDGER、02_RANKING、03_MODELS、04_VERIFICATION、05_DECISIONS）を書く。測定の JSON（axis_a_measurements.json、unified_model_exactness.json、unified_model_load.json、input_usage.json、approximation_study.json）は bench/ が書く。tools の 5 本のどれも新しく作らないデータは、01_LEDGER の sheet_families.json、unlinked_input_disposition.json、considered_not_adopted.json、units.json のうち上の 4 つの欄以外、02_RANKING/axis_b_judges/ の採点（読むだけ）。生成器が書かない手書きの文書は、00_POLICY の 3 点、03_MODELS/DERIVATIONS.md、04_VERIFICATION/INDEPENDENT_REVIEW.md、06_OPEN_ISSUES/README.md、07_MATERIAL_TAXONOMY の 5 点、research_code/README.md、第9章 README の冒頭の停止の枠。
- **所在**：
  - [`09_APPROX_STUDY/research_code/tools/sync_ledger.py`](../../../09_APPROX_STUDY/research_code/tools/sync_ledger.py)
  - [`09_APPROX_STUDY/research_code/tools/rank_axes.py`](../../../09_APPROX_STUDY/research_code/tools/rank_axes.py)
  - [`09_APPROX_STUDY/research_code/tools/build_records.py`](../../../09_APPROX_STUDY/research_code/tools/build_records.py)
  - [`09_APPROX_STUDY/research_code/tools/progress_ledger.py`](../../../09_APPROX_STUDY/research_code/tools/progress_ledger.py)
  - [`09_APPROX_STUDY/research_code/tools/build_reports.py`](../../../09_APPROX_STUDY/research_code/tools/build_reports.py)
  - [`09_APPROX_STUDY/research_code/README.md`](../../../09_APPROX_STUDY/research_code/README.md)
- **確かめ方**：第2回の検査が、progress_ledger.py の規則を独自に書いて全 70 単位の状態を再現し、rank_axes.py の関数で 2 軸・優先スコア・着手順・群を計算し直して差 0、build_reports.py の出力がディスクとバイト単位で一致することを確かめた。tools に対する単体試験はない（tests/ は synth、refcalc、closed_forms、engine の 4 ファイル）。この読み取りでは、ソースの文面を読んだだけで、実行も取り込みもしていない。
- **確かめた者**：独立検査（第2回）で progress_ledger.py と rank_axes.py の結果を再現。build_records.py と build_reports.py には誤りの指摘があり、未修正
- **言える範囲**：43ba5d7 の版。中断した修正（65ff124）は tools のファイルに触れていない（変更されたのは 01_LEDGER/units.json と、bench、common、fastcalc、refcalc、synth、tests）。
- **関係する第2回の指摘**：REP-1、REP-2、REP-3、REP-8、REP-9、REP-13、REP-14、REC-5、REC-8、REC-9
- **第2回の指摘の影響**：生成器の中の既知の誤り。build_reports.py 340 行：使われていない番兵の数から「0 項目は記録用」の文を作る（REP-1）。102 行：units.json の古い見出しを構造別の件数の表にする。sync_ledger.py はこの見出しを更新しない（REP-8）。225 行：「検査の 4 単位」が固定文（REP-9）。build_records.py 544 行：b7 を M4 に対応させている（REP-2）。137 行と 463〜480 行：機構と導出が任意で、欠けていても生成が通る。502 行：注記の文が実際と違う（REC-5・REP-3）。124 行ほかの定型文：事実と違う理由を複数の単位に付ける（REC-8・REP-14）。候補が付く単位の一覧を、計画表と approximation_study.json の 2 か所で別々に持っている（REP-13）。progress_ledger.py と rank_axes.py には、誤りの指摘がない。
- **今の時点で言ってよいこと**：5 本の生成器の入力と出力は上のとおりで、research_code/README.md の「再現の手順」に実行の順序が書かれている。progress_ledger.py は手順書 P10 を書かれたとおりに実装しており、状態は記録から機械的に求まる。
- **使ってはいけない記述**：
  - build_reports.py の説明「Every number in the generated files is read from a JSON output of the study, so the reports cannot drift from the data」を、文面に誤りが入らないという意味で引用すること
  - build_records.py の冒頭の説明（EX の記録は、出力の一致・機構の計数・導出のすべてを確かめ、なければ失敗する）
  - research_code/README.md「記録の生成は…裏付けのない『成功』や、測定値と矛盾する結論があると失敗する」の前半
- **新研究での再利用**：候補（ルート A・C）
  - 使い道：記録の様式（項目の定義）と、状態を記録から機械的に求める規則の実装は、新研究の記録と進捗の管理の参考になる。
  - 条件・注意：保存の作業では実行しない（実行は旧研究の再開に当たる）。sync_ledger.py は基準計算を取り込む。build_reports.py を実行すると、第9章 README の停止の枠が消える。生成器の改訂の案（CK-R5-30）は未着手のまま終了している。
- **分類の根拠**：
  - [`09_APPROX_STUDY/research_code/tools/sync_ledger.py`](../../../09_APPROX_STUDY/research_code/tools/sync_ledger.py):1-11、20、52、84
  - [`09_APPROX_STUDY/research_code/tools/rank_axes.py`](../../../09_APPROX_STUDY/research_code/tools/rank_axes.py):9-16、332
  - [`09_APPROX_STUDY/research_code/tools/build_records.py`](../../../09_APPROX_STUDY/research_code/tools/build_records.py):20-24（出力）、36-42（入力）、145-302（計画表）、305-419（結論の文）、499-561（4 つの出力の書き込み）
  - [`09_APPROX_STUDY/research_code/tools/progress_ledger.py`](../../../09_APPROX_STUDY/research_code/tools/progress_ledger.py):8-13、24-29
  - [`09_APPROX_STUDY/research_code/tools/build_reports.py`](../../../09_APPROX_STUDY/research_code/tools/build_reports.py):17、39-40、532-539
  - [`09_APPROX_STUDY/research_code/README.md`](../../../09_APPROX_STUDY/research_code/README.md):8-38（構成と再現の手順）
  - [`materials/interrupted_fix/working_tree_at_stop_65ff124.patch`](../materials/interrupted_fix/working_tree_at_stop_65ff124.patch)（変更されたファイルの一覧に tools/ はない）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):128（CHECKS PERFORMED 1：ranking を計算し直して差 0、報告書がバイト一致）
  - [`09_APPROX_STUDY/research_code/bench/measure_axis_a.py`](../../../09_APPROX_STUDY/research_code/bench/measure_axis_a.py):31、verify_unified.py:39-40、input_usage.py:27、approx_study.py:35（測定の JSON の出力先）
- **分類した観点**：R5（記録・進捗台帳・報告書・成果物・材料分類）

