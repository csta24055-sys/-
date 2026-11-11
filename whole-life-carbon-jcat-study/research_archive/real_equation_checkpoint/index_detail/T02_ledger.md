# 索引の詳細 T02：評価単位の台帳・シート族・依存関係

[INDEX.md](../INDEX.md) の項目ごとの詳細。分類担当（読み取り専用）が書いた内容を、欄ごとにそのまま載せる。
旧研究の数値はすべて架空データでの値で、対象は独立概念モデルである。原版の表計算との一致や、実建物での精度を示すものではない。
所在の表記：`09_APPROX_STUDY/…` などは `whole-life-carbon-jcat-study/` からの位置、`materials/…` はこの保存フォルダからの位置。

| 項目 | 区分 | 題 |
|---|---|---|
| [CK-R1-05](#ck-r1-05) | 1 | 台帳・順位表・自動生成の報告の、数と相互参照の整合（数え直しで一致した範囲） |
| [CK-R1-06](#ck-r1-06) | 2 | 評価単位の一覧（70 件＝既存の概念式 53＋追加で特定した計算構造 17） |
| [CK-R1-07](#ck-r1-07) | 2 | 構造分類と形式の記述（structure_class 13 種、正規形、反復、分岐、計算量） |
| [CK-R1-08](#ck-r1-08) | 3 | 台帳の見込み欄・提案欄・曖昧点（統合と近似の見込み、定義の提案） |
| [CK-R1-09](#ck-r1-09) | 1 | 基準定義 reference_semantics：文面と基準計算の説明文の一致、文面からの再導出 |
| [CK-R1-10](#ck-r1-10) | 4 | 基準定義の穴と文面の不足（第2回「定義からの再導出」の指摘 12 件ほか） |
| [CK-R1-12](#ck-r1-12) | 2 | 単位ごとの入力の申告（inputs 欄、全体で 116 種類＝既存 88＋仮置き 28） |
| [CK-R1-13](#ck-r1-13) | 2 | 式に未接続だった入力 53 項目の扱い（記録用 30、追加単位で接続 14、既存式が暗黙に使用 9） |
| [CK-R1-14](#ck-r1-14) | 2 | シート族の集計（198 シートを名称だけで 59 族に整理。数式ノード 3,818,483） |
| [CK-R1-15](#ck-r1-15) | 2 | シート族と評価単位の対応の表示（名称だけからの推定。状態 4 区分） |
| [CK-R1-16](#ck-r1-16) | 4 | 調べていない範囲と、評価単位にしなかった計算構造 |
| [CK-R1-21](#ck-r1-21) | 4 | 誤りまたは古いと指摘された数と記述の一覧（台帳・順位・関連する報告） |
| [CK-R7-01](#ck-r7-01) | 1 | 台帳の束縛欄（70 単位の id・段階・基準定義文・依存） |
| [CK-R7-02](#ck-r7-02) | 1 | 評価単位の依存グラフ（depends_on） |
| [CK-R7-03](#ck-r7-03) | 2 | 台帳の分析欄（構造分類 13 種・標準形・分岐・未定義点） |
| [CK-R7-30](#ck-r7-30) | 4 | 台帳と記録の古い欄・食い違う欄 |

<a id="ck-r1-05"></a>

## CK-R1-05　台帳・順位表・自動生成の報告の、数と相互参照の整合（数え直しで一致した範囲）

- **区分**：1　検証済み成果
- **根拠の強さについての注記（索引の作成者）**：件数と相互参照の数え直しだけである。内容が正しいことの確認ではない。数え直したのは第2回の検査担当 1 者。
- **内容**：台帳（01_LEDGER）と順位表（02_RANKING）の件数・集計・ファイル間の参照が、互いに、また上流の資料（02_SOURCES・03_INPUTS・04_FORMULAS）と合っているという事実。分類・推定・採点の内容が正しいことではなく、数え上げと対応の整合だけを指す。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
  - [`09_APPROX_STUDY/01_LEDGER/sheet_families.json`](../../../09_APPROX_STUDY/01_LEDGER/sheet_families.json)
  - [`09_APPROX_STUDY/01_LEDGER/sheet_family_coverage.json`](../../../09_APPROX_STUDY/01_LEDGER/sheet_family_coverage.json)
  - [`09_APPROX_STUDY/01_LEDGER/unlinked_input_disposition.json`](../../../09_APPROX_STUDY/01_LEDGER/unlinked_input_disposition.json)
  - [`09_APPROX_STUDY/01_LEDGER/README.md`](../../../09_APPROX_STUDY/01_LEDGER/README.md)
  - [`09_APPROX_STUDY/02_RANKING/axis_a.json`](../../../09_APPROX_STUDY/02_RANKING/axis_a.json)
  - [`09_APPROX_STUDY/02_RANKING/axis_b.json`](../../../09_APPROX_STUDY/02_RANKING/axis_b.json)
  - [`09_APPROX_STUDY/02_RANKING/research_priority.json`](../../../09_APPROX_STUDY/02_RANKING/research_priority.json)
  - [`09_APPROX_STUDY/02_RANKING/README.md`](../../../09_APPROX_STUDY/02_RANKING/README.md)
- **確かめ方**：第2回の「報告書の監査」の検査が、(1) 自動生成の README 6 点をメモリ上で再生成し、ディスクの内容とバイト単位で同じことを確認、(2) 台帳の数を JSON から数え直し、(3) 軸 A・軸 B・優先スコア・着手順・着手群を研究の順位付けの関数で入力から再計算して差 0、(4) ファイル間の参照を突き合わせた。数は完全一致で比べている。報告書の監査の指摘 18 件は、全体の調整役が検査のスクリプトを再実行して再現した（検査が「合った」と報告した項目のすべてを再実行したかは、記録からは分からない）。第1回の検査でも報告書の数字 54 個を再計算して合った（初版）。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：コミット 43ba5d7 の版（HEAD の 01_LEDGER・02_RANKING と同一）のファイルどうしの整合。独立概念モデルの 70 評価単位と、シート名・数式ノード数というメタデータについての数である。分類・推定・採点の内容が正しいこと、原版の数式を調べたことは含まない。
- **関係する第2回の指摘**：REP-8、REP-11、REP-18、REP-1、REP-7
- **第2回の指摘の影響**：数え直して合わなかった箇所、数は合うが意味が違う箇所が、この 5 件の指摘に当たる（CK-R1-21 に一覧）。それらを除いた範囲がこの項目である。
- **今の時点で言ってよいこと**：次の数と対応は、第2回の検査の数え直しと合っている。(1) 評価単位 70 件（既存 53、追加 17）。既存 53 件の ID と名称は 04_FORMULAS/formulas.json と同じ。(2) 入力の申告を数えた値は 116 種類（入力仕様の 88、NEW: を付けたもの 28）。(3) 198 シート、59 シート族（数式を持つ族 41）、数式ノード 3,818,483。02_SOURCES の一覧と同じ。状態別の族数 24・9・11・15 とノード数 3,708,176・79,260・31,047・0 は、付いている表示を数えた値。(4) 未接続の入力 53 項目の内訳 30・14・9、評価単位にしなかったもの 7 件。(5) units.json の sheet_family_links と sheet_family_coverage.json の対応の不一致 0（70 単位）。depends_on・feeds は基準計算の登録簿と同じ。(6) 軸 A・軸 B・優先スコア・着手順・着手群は入力から再計算して差 0。README の表（軸 A の 700 個の値、軸 B の 70 行、着手順の 70 行）は JSON と同じ。research_priority.json と progress_ledger.json の順序・群の不一致 0。(7) 自動生成の README 6 点は再生成した内容と同じで、古い生成物ではない。
- **使ってはいけない記述**：
  - 01_LEDGER/README.md の構造別の表のうち「活動量×係数の総和 29」「比・換算 11」（単位から数えると 30 と 10）
  - 02_RANKING/README.md 11 行目の「軸 A 22 件（重みを変えた場合だけ入るもの 6 件）…和集合 42 件」の読み方（CK-R1-20）
  - 数が合っていることを、分類・対応の推定・採点の内容が正しいことの根拠にすること
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：旧研究の台帳・順位表の数を引用するとき、JSON と README のどちらからも同じ数が得られる根拠になる。新研究の分類台帳の出発点として 70 単位の ID・依存関係を取り込むときの、ファイル間の整合の根拠になる。
  - 条件・注意：整合は 43ba5d7 の版についてのもの。65ff124 の台帳（CK-R1-11）は対象外。(7) はこの読み取りでは確かめていない（確かめるには生成器の実行が要る）。この読み取りで JSON の解析だけで数え直して合ったのは (1)〜(5) と、(6) のうち軸 B の中央値の合計・統合観点・割れの印（不一致 0）、軸 A スコア（保存された百分位×重みの和）、優先スコア（小数 4 桁の丸めの範囲、差 4.3e-5 以内）である。
- **分類の根拠**：
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):128（CHECKS PERFORMED 1: 01_LEDGER/README と 02_RANKING/README の数、7: Ledger consistency）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):71-76（REP-11 EVIDENCE: recomputing both axes, the priority score, order and waves from the inputs gives 0 differences）
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json): unit_count 70, existing_unit_count 53, additional_unit_count 17
  - [`09_APPROX_STUDY/01_LEDGER/sheet_families.json`](../../../09_APPROX_STUDY/01_LEDGER/sheet_families.json): total_sheets 198, total_formula_nodes 3818483, family_count 59, families_with_formulas 41
  - [`09_APPROX_STUDY/01_LEDGER/sheet_family_coverage.json`](../../../09_APPROX_STUDY/01_LEDGER/sheet_family_coverage.json): families_by_status
  - [`09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md`](../../../09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md):70（報告書の数字 54 個を再計算して一致。初版）
- **分類した観点**：R1（統制文書・台帳・順位）

<a id="ck-r1-06"></a>

## CK-R1-06　評価単位の一覧（70 件＝既存の概念式 53＋追加で特定した計算構造 17）

- **区分**：2　暫定・未検証成果
- **内容**：独立概念モデルの固有の計算構造を 1 件ずつ登録した台帳。53 件は第4章の概念式で、ID をそのまま使う。17 件（X-01〜X-17）は、シート名と数式ノード数、式に未接続の入力項目、既存資料の記述から旧研究が推定した独立設計の案である。「70 単位」は独立概念モデルの単位の数であり、原版ブックの約 382 万（3,818,483）の数式ノードを調べた数ではない。原版の数式本文は 1 件も確認していない。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
  - [`09_APPROX_STUDY/01_LEDGER/README.md`](../../../09_APPROX_STUDY/01_LEDGER/README.md)
  - [`materials/earlier_session_scratch/wfA/`](../materials/earlier_session_scratch/wfA)
- **確かめ方**：件数と ID の対応は第2回の検査が数え直して合った（CK-R1-05）。どの計算構造を単位にするかの選択と、追加 17 単位の推定は主担当（自動の AI エージェント）が行い、原版と照合していない（原版はリポジトリにも研究環境にもない）。既存 53 単位のうち 29 件の記述は 2 つの自動分析（AI エージェント）が作成した。
- **確かめた者**：作成者のみ（件数・ID・依存関係の整合だけ 独立検査（第2回）で再現）
- **言える範囲**：独立概念モデル。評価単位が原版の計算構造をどこまで覆っているかは未検証（06_OPEN_ISSUES A-6）。
- **関係する第2回の指摘**：なし
- **第2回の指摘の影響**：一覧そのものへの指摘はない。depends_on は基準計算の登録簿と 70 単位とも同じだった（第2回の 2 つの検査）。
- **今の時点で言ってよいこと**：台帳には 70 単位があり、根拠区分は EXISTING_CONCEPT 53、INFERRED_FROM_SHEET_METADATA 9、INFERRED_FROM_UNLINKED_INPUT 6、INFERRED_FROM_EXISTING_DOCS 2。70 単位すべてに基準計算の関数がある（computable_in_reference が 70 件とも真）。作成者の内訳は、自動分析 29 件（すべて既存単位）、主担当 41 件（既存 24、追加 17）。依存関係（depends_on）の辺は 183 本で、基準計算の登録簿の宣言と同じ。入力検査（SYS-01・SYS-02・SYS-03）との関係は gated_by に分けてある。
- **使ってはいけない記述**：
  - 70 単位が原版の計算式の全体を表す、または原版の数式を調べた結果である
  - 追加単位 17 件が原版の式の再現である（台帳の scope_statement は「独立設計の案」と明記）
  - depends_on が実際のデータの流れを漏れなく表す（中断した修正の自己申告は、X-07 が B2-01 を宣言なしに読んでいたと述べる。未検証。RED-1 は完全性の印が上流の除外に追従しないことを示した）
  - 分析担当が互いの出力を見ずに作業した（確かめる手段がない）
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：新研究の「方程式グループと依存関係の分類台帳」の出発点として、単位の ID、段階、依存関係（depends_on・feeds・gated_by）を取り込む。
  - 条件・注意：独立概念モデルの単位であること、追加 17 件は設計案であることを明記して使う。依存関係は 43ba5d7 の登録簿の宣言と同じで、65ff124 では X-02・X-04・X-07 の depends_on が変わっている（未検証）。原版との対応を主張しない。
- **分類の根拠**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json): scope_statement, authorship_note, dependency_note, unit_count, existing_unit_count, additional_unit_count
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json): units[].origin（EXISTING_53 53、ADDITIONAL 17）、units[].evidence_level（53・9・6・2）、units[].author（MAIN_SESSION 41、ANALYST 29）
  - [`09_APPROX_STUDY/01_LEDGER/README.md`](../../../09_APPROX_STUDY/01_LEDGER/README.md):7-8, 16-20
  - [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md):39-54（P2）
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md):14（A-6）、18
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):146（4. Ledger versus code: depends_on equals the registry's depends_on, 0 differences）
  - [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json): decisions[7]
- **分類した観点**：R1（統制文書・台帳・順位）

<a id="ck-r1-07"></a>

## CK-R1-07　構造分類と形式の記述（structure_class 13 種、正規形、反復、分岐、計算量）

- **区分**：2　暫定・未検証成果
- **内容**：各単位に付けた数学的な構造の分類（structure_class）、副分類、正規形の記号式（canonical_form）、反復の次元（loop_dims）、分岐（branches）、計算量（complexity）。分析時の判断として書かれたもので、測定ではない。軸 A の指標 a4（入力数＋正規形の演算子の数）と a5（分岐と反復の数）はこの欄から数えている。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
  - [`09_APPROX_STUDY/01_LEDGER/README.md`](../../../09_APPROX_STUDY/01_LEDGER/README.md)
- **確かめ方**：分類と記号式の内容は、分析担当と主担当（どちらも自動の AI エージェント）が書いたままで、検査で内容を点検した記録はない。第2回の検査は分類の件数を数え直し、見出しの件数と README の表が 2 分類で合わないことを見つけた（REP-8）。
- **確かめた者**：作成者のみ
- **言える範囲**：独立概念モデルの 70 単位に対する分析担当の分類。
- **関係する第2回の指摘**：REP-8、REP-10、RED-6
- **第2回の指摘の影響**：REP-8：units.json 見出しの structure_class_counts と 01_LEDGER/README.md の表は LINEAR_SUM_PRODUCT 29・RATIO 11 だが、70 単位から数えると 30・10（ほかの 11 分類は合う）。REP-10：A13-04 は副分類に UNDEFINED_MODEL が残るが、基準計算に実装済み。RED-6：SYS-01 の branches 欄「値が null・空・NaN → MISSING」は、拘束力のある定義文（None だけが MISSING）と食い違う。
- **今の時点で言ってよいこと**：70 単位から数えた分類の件数は、LINEAR_SUM_PRODUCT（活動量×係数の総和）30、RATIO（比・換算）10、PREDICATE_GATE（判定・検証）8、SUM_OF_STAGES 5、TIME_SERIES_SUM 4、EVENT_SCHEDULE 3、LOOKUP_JOIN 3、MAX_CLAMP 2、WEIGHTED_AVERAGE・RECURRENCE・COUNT_FLOOR・MASS_BALANCE_CONSTRAINT・MATRIX_EXPANSION 各 1。副分類を持つ単位は 21。これらは分析時の分類であり、採用した定義は reference_semantics（CK-R1-09）である。
- **使ってはいけない記述**：
  - 01_LEDGER/README.md の表「活動量×係数の総和 29」「比・換算 11」と、units.json 見出しの structure_class_counts（29・11）
  - A13-04 の structure_subclass「UNDEFINED_MODEL」（基準計算に旧研究の独立設計の式が実装されている）
  - canonical_form と branches が基準計算の定義と同じである（例：SYS-01 のこの 2 欄は計算停止の規則を含むが、reference_semantics には停止の記述がない）
- **新研究での再利用**：候補（ルート B・C）
  - 使い道：新研究で式を少数の変換にまとめるとき、同じ形の式を集める最初の手がかりにする（例：活動量×係数の総和 30 件、年次の積算 4 件、周期イベント 3 件、年ごとの状態更新 1 件）。
  - 条件・注意：分類は分析担当の判断で、独立の点検を受けていない。件数は単位から数え直した値（30・10）を使う。式の内容は reference_semantics と基準計算のコードで確かめてから使う。
- **分類の根拠**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json):11-25（structure_class_counts。LINEAR_SUM_PRODUCT 29、RATIO 11）
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json): units[].structure_class を数えた値（30・10・8・5・4・3・3・2・1・1・1・1・1。JSON の解析）
  - [`09_APPROX_STUDY/01_LEDGER/README.md`](../../../09_APPROX_STUDY/01_LEDGER/README.md):56-70（構造別の件数の表）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):50-55（REP-8）、64-69（REP-10）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):61-71（RED-6）
  - [`09_APPROX_STUDY/research_code/tools/rank_axes.py`](../../../09_APPROX_STUDY/research_code/tools/rank_axes.py):114-115（a4・a5 の数え方。読んだだけで実行していない）
- **分類した観点**：R1（統制文書・台帳・順位）

<a id="ck-r1-08"></a>

## CK-R1-08　台帳の見込み欄・提案欄・曖昧点（統合と近似の見込み、定義の提案）

- **区分**：3　研究途中の数式・仮説
- **内容**：各単位の unification_potential（統合の見込み）、approximation_potential（近似の見込み）、expected_precision_loss（想定される精度低下）、similar_units（同じ構造の単位）、boundary_unit_caveats（同一視してはならない算定境界・単位）、ambiguities（概念式が決めていない点）と、29 単位にある reference_semantics_proposal（分析担当による定義の提案）。分析時の仮説と提案で、この欄自体に測定や導出の裏付けはない。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
- **確かめ方**：なし。一部の案は後に 03_MODELS の記録で測定・導出されたが、この欄は初版の分析時の文面のままで、後の結果と突き合わせて直していない。
- **確かめた者**：なし
- **言える範囲**：独立概念モデルの単位に対する仮説と提案。
- **関係する第2回の指摘**：REP-10
- **第2回の指摘の影響**：REP-10：A13-04 の reference_semantics_proposal に「基準計算には実装しない」、approximation_potential に「モデルが未定義のため…基準計算との誤差比較はできない」が残る。実際は基準計算に実装され、近似候補 AP-19a・AP-19b がそれに対して測定された。
- **今の時点で言ってよいこと**：これらは仮説・提案の記録である。units.json の reference_note のとおり、reference_semantics_proposal と reference_semantics が違うときは reference_semantics が優先する。boundary_unit_caveats は、統合のときに同一視してはならない算定境界と単位の注意書きとして読める。
- **使ってはいけない記述**：
  - A13-04 の「基準計算には実装しない」「モデルが未定義のため、近似の対象となる厳密式がそもそも存在しない」
  - 見込み欄の記述を、測定または導出で確かめた結果として読むこと
  - reference_semantics_proposal を採用された定義として読むこと
- **新研究での再利用**：候補（ルート B・C）
  - 使い道：式どうしの関係についての仮説の一覧として使う（例：A13-04 の欄にある「端材の補正と未数量分の上乗せは、同じ 1 変数関数 g(x) = 1/(1−x) の 2 つの適用」という案）。boundary_unit_caveats は、変換で式をまとめるときに混ぜてはならない境界と単位の確認表として使う。
  - 条件・注意：仮説であり、検証済みとして扱わない。初版の分析時の文面で、その後の定義の変更を反映していない箇所がある。他のツールの値や式を述べるものではない（各欄も独立設計と明記）。
- **分類の根拠**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json): reference_note（reference_semantics が優先）
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json): units[id=A13-04].approximation_potential, reference_semantics_proposal, computable_in_reference（真）
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json): units[].reference_semantics_proposal は 29 単位にだけある（JSON の解析）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):64-69（REP-10）
- **分類した観点**：R1（統制文書・台帳・順位）

<a id="ck-r1-09"></a>

## CK-R1-09　基準定義 reference_semantics：文面と基準計算の説明文の一致、文面からの再導出

- **区分**：1　検証済み成果
- **根拠の強さについての注記（索引の作成者）**：文面の一致は検査担当 2 者。書き直しとの一致は検査担当 1 者の報告で、反証検査担当はこの一致をやり直していない。
- **内容**：台帳の各単位の reference_semantics 欄は、基準計算が実際に採用した定義を日本語の文で書いたもので、基準計算（research_code/refcalc）の関数の説明文と同じ文面である。旧研究はこれを拘束力のある定義とした。HEAD の文面は 43ba5d7 のコードに対応する。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
  - [`09_APPROX_STUDY/research_code/refcalc/`](../../../09_APPROX_STUDY/research_code/refcalc)
- **確かめ方**：(1) 第2回の 2 つの検査（報告書の監査、定義からの再導出）が、台帳の文面と基準計算の関数の説明文を 70 単位で照合し、差 0。depends_on も登録簿と差 0。(2) 定義からの再導出の検査が、53 単位を定義文と base.py の規約の説明文だけから書き直し、119 の架空シナリオ（検証用の母集団から 24、境界条件 32、不備入り 14、入力を壊した変異 36、小数の境界の評価期間 5、段階の部分集合 8）で基準計算と比べ、数値と件数が相対 1e-9 以内で合った。合わなかったのは表示・件数の 4 点（X-15 の未解決行の表示、B2-01 の computed、SUM-07 の空の内訳、C-05 の未検査の件数 4 対 5）。(3) X-05・X-04 のガス別内訳・SUM-08 は 50 シナリオで間接的に再導出し差なし。(4) 14 段階の全部分集合 16,384 通り（不備のない 1 シナリオ）で、段階の値の出入りに不整合 0。第1回の検査でも同じ観点の再導出を行い、見つかった定義の穴には 43ba5d7 までに対応した（対応が及んでいない箇所が第2回で見つかった。CK-R1-10）。
- **確かめた者**：独立検査（第1回）、独立検査（第2回）で再現
- **言える範囲**：架空データだけ。独立概念モデルだけ。43ba5d7 の基準計算と HEAD の台帳の文面について。再導出は 53 単位、規模 S、評価期間 99.9 年まで。残る 14 単位（SYS-01〜04、QA-01、QA-03、QA-04、X-03、X-08、X-09、X-11、X-17、STO-01、STO-02）は独立に書き直しておらず、コードを文面と読み比べただけである。再導出は base.py の規約文（時間の規則、係数を使える条件、記述子と年次表の規則）を与えられたものとして使ったので、規約そのものを別の出所と照合したものではない。定義が現実の排出量を正しく表すかは対象外。(2)〜(4) は検査担当の実施記録で、反証役の検証者が再確認したのは指摘（RED-1〜12）の側である。
- **関係する第2回の指摘**：RED-1、RED-2、RED-3、RED-4、RED-5、RED-6、RED-7、RED-8、RED-9、RED-10、RED-11、RED-12、REC-1、NUM-1
- **第2回の指摘の影響**：文面が基準計算の説明文と同じであること、検査で使った 119 シナリオ（不備入りを含む）で文面から同じ数が得られることは、指摘で否定されていない。指摘が弱めるのは「定義文だけで各単位の結果が完全に定まる」「不備のある入力はすべて除外して数え、合計に不完全の印が付く」という読み方である（穴の一覧は CK-R1-10）。REC-1・NUM-1 の検証者は、周期 1.000000001 年で基準計算の年の判定が浮動小数点の丸めの影響を受けることを示した。
- **今の時点で言ってよいこと**：70 単位すべてで、台帳の reference_semantics は 43ba5d7 の基準計算の関数の説明文と同じ文面である。53 単位は、定義文と規約の説明文だけから独立に書き直した計算が、119 の架空シナリオで基準計算と相対 1e-9 以内で合った。文面とコードの動作が合わない箇所、文面が動作を書いていない箇所は CK-R1-10 のとおりである。
- **使ってはいけない記述**：
  - reference_semantics だけで各単位の結果が完全に定まる（RED-9：B4-02 の式の文に設備の搬入・据付がない、B1-02 の式に ×GWP がない。RED-12：定義文にない出力と分岐が 7 点。RED-7：「行の製造排出」に A13-04 の上乗せを含むかは depends_on で決まる）
  - 「使えない行・経路・項目は合計に入れず、件数を報告し、合計に不完全の印を付ける」（06_OPEN_ISSUES B-17。RED-1 により、B3 または B5 を含み上流の段階を含まない境界では印が付かない）
  - 「負の数量・質量・距離、範囲外の率は、その行を計算から除いて数える」（B-18。RED-2 により、年次量の負・NaN は検査なしで使われる）
  - X-04 の定義文「…一致することを確かめる」（RED-4：コードは比較結果を返さない）
  - SYS-01 の定義文「数値入力を 1 つずつ調べ」（RED-6：調べるのは固定の一覧だけ）
  - base.py の「許容幅により判定は二進の丸めに依存しない」（REC-1・NUM-1：周期 1.000000001 年では成り立たない）
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：新研究が変えてはならない基準計算の、文章による定義として使う。Route B で式を組み直すときの出発点（元の式の記述）、Route A・C で旧研究の結果を読むときの定義の参照にする。
  - 条件・注意：HEAD（43ba5d7 と同じ）の文面を使う。不備のある入力の扱いには RED-1〜RED-12 の穴がある（CK-R1-10）。規約（06_OPEN_ISSUES の B-1〜B-21）と併せて読む。65ff124 の書き換えた文面（CK-R1-11）は未検証で、HEAD の基準計算には対応しない。旧研究の独立設計の定義であり、他のツールの式や値を表すものではない。
- **分類の根拠**：
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):128（3. Hand-written documents vs code and data: reference_semantics equals the reference docstrings for all 70 units; depends_on/feeds equal the registry）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):146（CHECKS PERFORMED 1〜4, 7）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):148（COULD NOT CHECK: 14 単位は独立に書き直していない）
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json): reference_note、units[].reference_semantics（70 単位にある）
  - [`09_APPROX_STUDY/01_LEDGER/README.md`](../../../09_APPROX_STUDY/01_LEDGER/README.md):10
  - [`09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md`](../../../09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md):15（定義からの再導出。第1回）
  - git show 43ba5d7:[`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json) は HEAD の内容と同じ（JSON の比較で確認）
- **分類した観点**：R1（統制文書・台帳・順位）

<a id="ck-r1-10"></a>

## CK-R1-10　基準定義の穴と文面の不足（第2回「定義からの再導出」の指摘 12 件ほか）

- **区分**：4　不具合・未解決事項
- **内容**：基準計算の定義と定義文について、第2回の検査が見つけた穴（不備のある入力の扱いが規約と合わない箇所、定義文がコードの動作を書いていない箇所、規約の一覧にない規約）。HEAD の基準計算と台帳に残っている。
- **所在**：
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md)
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md)
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md)
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md)
- **確かめ方**：検査担当が自分の実装と基準計算を架空シナリオで実行して見つけ、反証役の検証者が別のシナリオで再現した。判定は RED-1・2・4・5・6・7・8・10・12 が CONFIRMED、RED-3・9・11 が PARTLY_CONFIRMED、REC-1・NUM-1 が CONFIRMED。影響の数値は架空データ上の値で、RED-7・8・9 の大きさは標準ベンチマーク S だけの値。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：架空データ、独立概念モデル、43ba5d7 の基準計算。多くは不備のある入力（欠損、負、NaN、不正な周期）か、対象段階を一部だけにした境界で現れる。
- **関係する第2回の指摘**：RED-1、RED-2、RED-3、RED-4、RED-5、RED-6、RED-7、RED-8、RED-9、RED-10、RED-11、RED-12、REC-1、NUM-1
- **第2回の指摘の影響**：RED-1（重大）：対象段階が B3 または B5 を含み上流の段階を含まないとき、上流で除外された行があっても合計の complete が真のまま（例：対象段階 B3 だけで SUM-03 が 98378.05 から 43676.16、complete 真）。14 段階すべてを対象にすると印は付く。RED-2：年次量の負・NaN、電力係数、係数の値、行の換算倍率は検査なしで掛けられ、件数・complete・SYS-01〜03 のどれにも現れない（B-18 と文面で食い違うのは年次量の部分）。RED-3（一部確認）：負・0・NaN・無限大の周期や耐用年数は「事象なし」として扱い、数えない（例：SUM-03 が −16.1％ で complete 真）。規約は B4-01・B4-03 の定義文にあるが、B5-01・B1-02 の定義文と 06_OPEN_ISSUES の B にはない。RED-4：X-04 は「確かめる」と書くが比較結果を返さない。RED-5：SUM-08 は不完全な合計どうしでも比較する。登録のない基準案 ID は「基準案なし」と区別されない。RED-6：SYS-01 が調べる数値入力は固定の一覧だけ。RED-7：「行の製造排出」に A13-04 の上乗せを含むか（B3・B4 は含まず、B5 は含む）が定義文だけでは決まらない。標準ベンチマーク S で B4 に +0.542％、B3 に +3.93％ の差。RED-8：資材の初期の据付を計上しない規約が B-11 にない（標準ベンチマーク S で A5 の 41.1％ に当たる量）。RED-9（一部確認）：B4-02 の式の文に設備の搬入・据付がない。B1-02 の式に ×GWP がない。RED-10：None の経路比率・電力係数・係数の値・要約数量で計算全体が TypeError、年次表が評価期間より短いと IndexError（B-21 は評価期間だけをエラーとする）。RED-11（一部確認）：設備の廃棄係数が None のとき SYS-03 は通るが X-14 は行を除外する。明示の更新年の重複はそれぞれ数える。RED-12：定義文にない出力（X-02 の by_stage_all、X-05 の by_stage_co2）、B2-01 が B6-01 未算出でも computed 真、X-17 で要約数量 0 の区分が消える、ほか計 7 点。REC-1・NUM-1（重大）：周期 1.000000001 年（倍精度の値 1 つ）で、基準計算の年の判定が、正確な算術なら別々の年になる事象を同じ年に置く（T = 60 で 59 事象が 48 の年）。
- **今の時点で言ってよいこと**：上の指摘は記録どおりで、修正は検証されていない（段階 a1 が 65ff124 で修正を申告したが、独立の検査は未実施で、作業ツリーからは取り除かれている）。多くは不備のある入力か、対象段階を一部だけにした境界で現れる（RED-1 の検証者：全 14 段階を対象にすると A13-01・X-01 を通じて印が付く）。REC-1・NUM-1 は整った入力（周期 1.000000001 年）で現れる。RED-7・RED-8・RED-9 は定義文と規約の一覧の記載の不足で、基準計算の数値を変える指摘ではない。
- **使ってはいけない記述**：
  - 06_OPEN_ISSUES B-17「使えない行・経路・項目は合計に入れず、件数を報告し、合計に不完全の印を付ける」を、どの境界でも成り立つと読むこと
  - 06_OPEN_ISSUES B-18 を、年次量・電力係数・係数の値・換算倍率にも当てはまると読むこと
  - 06_OPEN_ISSUES B-21「評価期間が有限の正の数でなければ、計算全体をエラーにする」を、エラーになるのはその場合だけと読むこと
  - INDEPENDENT_REVIEW.md 2.2「負の数量、範囲外の率、欠損…除外して数える規則に統一」
  - 09_APPROX_STUDY/README.md「不備のある入力や、冗長な入力どうしが食い違う場合も、同じ値を返し、同じ不備を報告する」（検証者の追記：検査していない非有限の入力では基準計算と統合モデルの結果が分かれる）
- **新研究での再利用**：候補にしない
  - 理由・注意：新研究は基準計算を変えないので、これらの穴は残る前提で使う。誤差を測る母集団は、穴に当たらない入力（整った入力、または旧研究の検証で使った種類の不備）に限るか、当たる場合を別に記録する。
- **分類の根拠**：
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):1-11（RED-1）、13-23（RED-2）、25-35（RED-3）、37-47（RED-4）、49-59（RED-5）、61-71（RED-6）、73-83（RED-7）、85-95（RED-8）、97-107（RED-9）、109-119（RED-10）、121-131（RED-11）、133-143（RED-12）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):150（ADDITIONAL (verifier) 1〜3）
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):1-11（REC-1）、114（ADDITIONAL (verifier) 1）
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):1-8（NUM-1 の見出しと判定）
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md):38-39（B-11）、45-46（B-17、B-18）、49（B-21）
  - [`STOP_STATUS.md`](../STOP_STATUS.md):54（a1 は完了を報告。独立の検査は未実施）
- **分類した観点**：R1（統制文書・台帳・順位）

<a id="ck-r1-12"></a>

## CK-R1-12　単位ごとの入力の申告（inputs 欄、全体で 116 種類＝既存 88＋仮置き 28）

- **区分**：2　暫定・未検証成果
- **内容**：各単位の inputs 欄（必要な入力変数の申告）と n_inputs。入力仕様（03_INPUTS、124 項目）の ID か、仕様にないものは「NEW:」を付けた名前で書かれている。70 単位を合わせると 116 種類（仕様の 88、NEW: 28）。分析時の申告であって、測定ではない。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
  - [`09_APPROX_STUDY/01_LEDGER/README.md`](../../../09_APPROX_STUDY/01_LEDGER/README.md)
  - [`09_APPROX_STUDY/05_DECISIONS/README.md`](../../../09_APPROX_STUDY/05_DECISIONS/README.md)
  - [`09_APPROX_STUDY/04_VERIFICATION/input_usage.json`](../../../09_APPROX_STUDY/04_VERIFICATION/input_usage.json)
- **確かめ方**：件数 116・88・28 は第2回の検査が数え直して合った。申告の内容は、第2回の検査が基準計算の入力の読み出しの実測（04_VERIFICATION/input_usage.json、架空の 33 シナリオで属性の読み出しを追跡）と突き合わせ、食い違いを確認した（REP-7）。
- **確かめた者**：独立検査（第2回）で再現（件数と、実測との食い違い）
- **言える範囲**：独立概念モデルの単位に対する分析担当の申告。実測は架空シナリオ上で、70 単位をまとめた値。
- **関係する第2回の指摘**：REP-7、REP-1
- **第2回の指摘の影響**：申告は、基準計算が実際に読む入力を表していない。実測で基準計算が読むのは、仕様の 77 項目と、旧研究が加えた項目 56（加えた項目は全部で 73）。申告にある仕様の入力のうち 12 項目は読まれない（TRANSPORT.mode、PROJECT.building_use、FACTOR.factor_boundary、OPERATION.grid_factor_scenario_id を含む）。MATERIAL.construction_division は読まれるが、どの単位の申告にもない。申告の NEW: の名前 28 のうち、加えた項目 73 に同じ名前があるのは 4 つだけ。05_DECISIONS/README.md の表は「単位が参照する入力項目 116（既存 88＋追加 28）｜同じ｜変化なし」と「計算中に読まれた入力項目（実測） 既存 77＋追加 56」を説明なしに並べている。
- **今の時点で言ってよいこと**：116・88・28 は台帳の申告を数えた値である。単位ごとに実測した入力の一覧は存在しない（段階 b3 で作る設計だったが未着手）。軸 A の指標 a4 は、この申告の入力数（n_inputs）を使っている。
- **使ってはいけない記述**：
  - 05_DECISIONS/README.md「単位が参照する入力項目｜116（既存 88＋追加 28）｜同じ｜変化なし」を測定結果として読むこと
  - inputs 欄が基準計算の実際の入力である
  - 手順書 P3 の inputs_read_by_reference・n_inputs_read（台帳に存在しない）
- **新研究での再利用**：候補にしない
  - 理由・注意：実測は 70 単位をまとめた値で、単位ごとの内訳はない。input_usage.json は「読まれた項目は、必要な項目の上限」と注記している。
- **分類の根拠**：
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):43-48（REP-7）
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json): units[].inputs を数えると 116 種類（NEW: 28、仕様 88。JSON の解析）
  - [`09_APPROX_STUDY/04_VERIFICATION/input_usage.json`](../../../09_APPROX_STUDY/04_VERIFICATION/input_usage.json): inputs_in_specification 124, inputs_added_by_this_study 73, summary.reference_all_units（existing_inputs_read 77, added_inputs_read 56）, scenarios 33, what_is_measured
  - [`09_APPROX_STUDY/05_DECISIONS/README.md`](../../../09_APPROX_STUDY/05_DECISIONS/README.md):105-106
  - [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md):65-66
  - [`materials/interrupted_fix/specs/SPEC_B3.md`](../materials/interrupted_fix/specs/SPEC_B3.md):20-30（単位ごとの実測の設計。未着手）
- **分類した観点**：R1（統制文書・台帳・順位）

<a id="ck-r1-13"></a>

## CK-R1-13　式に未接続だった入力 53 項目の扱い（記録用 30、追加単位で接続 14、既存式が暗黙に使用 9）

- **区分**：2　暫定・未検証成果
- **内容**：既存の対応台帳で、どの式にも接続していなかった入力 53 項目を 3 つに分けた表。METADATA_ONLY（記録用、計算に使わない）30、NEEDS_NEW_UNIT（追加単位で接続）14、IMPLICIT_IN_EXISTING（既存式が暗黙に使用）9。追加単位 X-01、X-11〜X-14、X-17 を置く根拠の 1 つになった。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/unlinked_input_disposition.json`](../../../09_APPROX_STUDY/01_LEDGER/unlinked_input_disposition.json)
  - [`09_APPROX_STUDY/01_LEDGER/README.md`](../../../09_APPROX_STUDY/01_LEDGER/README.md)
  - [`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../../09_APPROX_STUDY/04_VERIFICATION/README.md)
- **確かめ方**：件数 53・30・14・9 は第2回の検査が数え直して合った。分類の内容は、基準計算の入力の読み出しの実測と突き合わせて食い違いを確認した（REP-7）。
- **確かめた者**：独立検査（第2回）で再現（件数と、実測との食い違い）
- **言える範囲**：入力仕様 124 項目のうち、既存の対応台帳で未接続だった 53 項目に対する主担当の分類。
- **関係する第2回の指摘**：REP-7、REP-1
- **第2回の指摘の影響**：「追加単位で接続」14 のうち 3（PROJECT.building_use、PROJECT.structure_type、EQUIPMENT.equipment_trade）は基準計算が読んでいない。「既存式が暗黙に使用」9 のうち 6 は読んでいない。04_VERIFICATION/README.md 103 行目の「入力仕様 124 項目のうち 0 項目は記録用で、どの計算にも使われない」は誤りで、実測では 124 項目のうち 47 項目がどの計算にも読まれない（124 − 77）。0 は、どの項目にも付いていない目印を数えた値である（REP-1）。
- **今の時点で言ってよいこと**：53・30・14・9 は、付けた分類を数えた値である。「記録用」とした 30 項目は、実測でも 30 項目とも読まれていない（input_usage.json から、この読み取りで数えた）。「追加単位で接続」「既存式が暗黙に使用」の分類は、基準計算の実測とは合わない項目を含む。
- **使ってはいけない記述**：
  - 「入力仕様 124 項目のうち 0 項目は記録用で、どの計算にも使われない」（04_VERIFICATION/README.md:103）
  - 「追加単位で接続 14」「既存式が暗黙に使用 9」を、基準計算がその 23 項目を使っているという意味に読むこと
  - 記録用の入力は 30 項目だけである（実測で読まれない仕様の入力は 47 項目）
- **新研究での再利用**：候補にしない
  - 理由・注意：実測と合わせた分類のやり直しは段階 b3 の設計にあったが未着手。
- **分類の根拠**：
  - [`09_APPROX_STUDY/01_LEDGER/unlinked_input_disposition.json`](../../../09_APPROX_STUDY/01_LEDGER/unlinked_input_disposition.json): input_count 53, counts（METADATA_ONLY 30, NEEDS_NEW_UNIT 14, IMPLICIT_IN_EXISTING 9）
  - [`09_APPROX_STUDY/01_LEDGER/README.md`](../../../09_APPROX_STUDY/01_LEDGER/README.md):147-155
  - [`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../../09_APPROX_STUDY/04_VERIFICATION/README.md):103
  - [`09_APPROX_STUDY/04_VERIFICATION/input_usage.json`](../../../09_APPROX_STUDY/04_VERIFICATION/input_usage.json): metadata_only_inputs 0, not_read_by_reference（64 件＝仕様 47＋追加 17。JSON の解析）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):1-6（REP-1）、43-48（REP-7）
- **分類した観点**：R1（統制文書・台帳・順位）

<a id="ck-r1-14"></a>

## CK-R1-14　シート族の集計（198 シートを名称だけで 59 族に整理。数式ノード 3,818,483）

- **区分**：2　暫定・未検証成果
- **内容**：第2章が記録した 198 シートの一覧（シート名、表示状態、数式 XML ノード数）を、シート名の正規化（末尾の _GHG・_CO2、空白、(2)・(3) の添字などを除く）だけで 59 のシート族に整理した表。数式を持つ族は 41。数式ノードの合計は 3,818,483。この数は架空データではなく、第2章（旧研究より前の資料）から引き継いだ原版ブックのメタデータ（名称と件数だけ）である。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/sheet_families.json`](../../../09_APPROX_STUDY/01_LEDGER/sheet_families.json)
  - [`09_APPROX_STUDY/01_LEDGER/README.md`](../../../09_APPROX_STUDY/01_LEDGER/README.md)
  - [`02_SOURCES/ALL_198_SHEETS.json`](../../../02_SOURCES/ALL_198_SHEETS.json)
- **確かめ方**：第2回の検査が、族の表が上流の一覧（198 シート、3,818,483 ノード）と合うことを確認した（CK-R1-05）。上流の数そのものは、原版がリポジトリにも研究環境にもないので、ここでは確かめられない。族への整理はシート名だけで行っており、内容による確認はない。
- **確かめた者**：作成者のみ（集計の数だけ 独立検査（第2回）で再現）
- **言える範囲**：原版ブックのメタデータ（シート名、表示状態、数式ノード数）だけ。全 59 族の計算内容は未調査（sheet_families.json の evidence_level）。
- **関係する第2回の指摘**：なし
- **第2回の指摘の影響**：なし（REP-18 は族と単位の対応の表示についての指摘で、CK-R1-15 に記載）。
- **今の時点で言ってよいこと**：198 シート、59 族（数式を持つ族 41）、数式ノード 3,818,483 は、第2章の一覧から数え直せる。最大の族「資材構成」は 3,145,987 ノード（82.39％）。シート名の末尾が _GHG のシートは 1,857,127 ノード、_CO2 は 1,844,617 ノード。数式ノード数は「同じ計算が何回繰り返されているか」の代理指標で、実行時間でも式の種類数でもない（sheet_families.json の warning）。
- **使ってはいけない記述**：
  - シート族の整理が原版の計算構造の調査である
  - 名称やノード数が同じシートの式が同じである（_GHG と _CO2 の 2 系統が同じ式かどうかは未確認）
  - 数式ノード数が計算時間や式の種類数を表す
- **新研究での再利用**：候補（ルート B・C）
  - 使い道：旧研究が何を調べていないかを示す資料として、また原版側で繰り返しが集中する場所の代理指標として、新研究の範囲の記述に使う。
  - 条件・注意：メタデータだけである。シート名を公開資料に含めてよいかは権利者の確認による（06_OPEN_ISSUES F）。原版の内容を推測して書かない。原版と同じ・互換という表現に使わない。
- **分類の根拠**：
  - [`09_APPROX_STUDY/01_LEDGER/sheet_families.json`](../../../09_APPROX_STUDY/01_LEDGER/sheet_families.json): source, method, evidence_level, warning, total_sheets 198, total_formula_nodes 3818483, family_count 59, families_with_formulas 41, nodes_by_scope_suffix（GHG 1857127、CO2 1844617、NONE 116739）
  - [`02_SOURCES/ALL_198_SHEETS.json`](../../../02_SOURCES/ALL_198_SHEETS.json): sheets 198 件、formula_xml_nodes の合計 3818483（JSON の解析）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):128（Sheet families equal the upstream 02_SOURCES list）
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md):93
- **分類した観点**：R1（統制文書・台帳・順位）

<a id="ck-r1-15"></a>

## CK-R1-15　シート族と評価単位の対応の表示（名称だけからの推定。状態 4 区分）

- **区分**：2　暫定・未検証成果
- **内容**：59 のシート族それぞれに、関連すると推定した評価単位（related_units）と状態を付けた表。状態と件数は、COVERED_BY_ADDITIONAL 24 族（3,708,176 ノード、97.11％）、NOT_INSPECTED 9 族（79,260、2.08％）、COVERED_BY_EXISTING 11 族（31,047、0.81％）、NON_CALCULATION 15 族（0）。対応は 59 族ともシート名だけからの推定である。units.json の sheet_family_links はこの表から機械的に作る。軸 A の指標 a7 もこの対応から求める。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/sheet_family_coverage.json`](../../../09_APPROX_STUDY/01_LEDGER/sheet_family_coverage.json)
  - [`09_APPROX_STUDY/01_LEDGER/README.md`](../../../09_APPROX_STUDY/01_LEDGER/README.md)
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
- **確かめ方**：第1回の検査が 2 つのファイルの食い違いを指摘し、出所をこの表 1 つにして機械的に同期するよう直した。第2回の検査で units.json との参照の不一致は 0。状態の表示の付け方は、第2回で不統一と指摘された（REP-18）。対応の内容そのものを確かめる手段はない（原版の式を見ていない）。
- **確かめた者**：作成者のみ（参照の整合だけ 独立検査（第2回）で再現）
- **言える範囲**：シート名からの推定。原版の式の内容は全 59 族について未確認。
- **関係する第2回の指摘**：REP-18
- **第2回の指摘の影響**：COVERED_BY_EXISTING の 3 族（複合原単位、EPD組込、算定結果）は関連単位に追加単位（X-）を含む（合わせて 19,388 ノードで、0.81％ の行の 62％）。NON_CALCULATION の 11 族は関連単位として X-15 または X-16 を持つ。数式 0 件の 3 族（CH4、CO2、N2O）は COVERED_BY_ADDITIONAL になっている。ノード占有率への影響は 0.6 ポイント未満。
- **今の時点で言ってよいこと**：族と単位の対応（related_units）は台帳と合っている。4 区分の件数と占有率は、付いている表示を数えた値としては合っている。「対応あり」は、名称が示す計算構造を独立モデルの単位が表しているという意味で、原版の式を調べた・再現したという意味ではない（表の warning）。
- **使ってはいけない記述**：
  - 「追加単位が対応（推定） 24 族 97.11％」を、原版の数式の 97.11％ を調べた・覆ったと読むこと
  - 状態の 4 区分が、互いに重ならない一貫した規則で付いているという読み方
  - 軸 A の a7（族の占有率を関連単位の数で等分した値）が原版側の計算負荷を表す
- **新研究での再利用**：候補にしない
  - 理由・注意：使う場合は「名称からの推定」と明記する。規則で付け直す設計（SPEC_B3.md の 4）は未着手。
- **分類の根拠**：
  - [`09_APPROX_STUDY/01_LEDGER/sheet_family_coverage.json`](../../../09_APPROX_STUDY/01_LEDGER/sheet_family_coverage.json): warning, families_by_status, node_share_by_status, correspondence_source_note, families[].correspondence_evidence（59 族とも INFERRED_FROM_NAME_ONLY）
  - [`09_APPROX_STUDY/01_LEDGER/sheet_family_coverage.json`](../../../09_APPROX_STUDY/01_LEDGER/sheet_family_coverage.json): families[family_id=SF-13, SF-20, SF-34]（COVERED_BY_EXISTING で X- を含む。15,942＋3,173＋273 ノード）、SF-42・SF-43・SF-44（数式 0 件で COVERED_BY_ADDITIONAL）
  - [`09_APPROX_STUDY/01_LEDGER/README.md`](../../../09_APPROX_STUDY/01_LEDGER/README.md):16-19, 24-31
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):120-125（REP-18）
  - [`09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md`](../../../09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md):58
  - [`09_APPROX_STUDY/02_RANKING/axis_a.json`](../../../09_APPROX_STUDY/02_RANKING/axis_a.json): ranking[].static.a7（族の占有率÷関連単位の数の和と 70 単位で同じ。JSON の解析）
- **分類した観点**：R1（統制文書・台帳・順位）

<a id="ck-r1-16"></a>

## CK-R1-16　調べていない範囲と、評価単位にしなかった計算構造

- **区分**：4　不具合・未解決事項
- **内容**：旧研究が調べていないものの記録。(1) 原版ブックの数式本文は全シート族について未確認（数式ノード 3,818,483 の 100％）。原版ファイル・マニュアル・VBA はリポジトリにも研究環境にもない。(2) 名称から対応する計算構造を推定できなかったシート族 9 件（79,260 ノード、2.08％）。(3) 検討したが評価単位にしなかった計算構造 7 件：用途別面積による結果の按分、原単位化の他指標への適用、報告書式・グラフ用の整形、標準・簡易・詳細の方式切替、不確実性の伝播、モジュール D（範囲外の便益）、コンクリート炭酸化の時間依存モデル。(4) 詳細算定ブックのマクロと外部の計算ツールとの連携は実行も解析もしていない。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/README.md`](../../../09_APPROX_STUDY/01_LEDGER/README.md)
  - [`09_APPROX_STUDY/01_LEDGER/considered_not_adopted.json`](../../../09_APPROX_STUDY/01_LEDGER/considered_not_adopted.json)
  - [`09_APPROX_STUDY/01_LEDGER/sheet_family_coverage.json`](../../../09_APPROX_STUDY/01_LEDGER/sheet_family_coverage.json)
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md)
  - [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md)
- **確かめ方**：第2回の検査が、未調査の範囲が 01_LEDGER・06_OPEN_ISSUES・冒頭の README に書かれていること、文書のどこにも原版の調査や原版との一致を主張する記述がないことを確認した。
- **確かめた者**：独立検査（第2回）で再現（記載があることの確認）
- **言える範囲**：旧研究の範囲の外にあるものの一覧。
- **関係する第2回の指摘**：なし
- **第2回の指摘の影響**：なし。
- **今の時点で言ってよいこと**：旧研究の「全評価単位に結論を記録した」「全式調査」は独立概念モデルの 70 単位についての記述であり、原版 3,818,483 数式ノードの調査でも検証でもない。評価単位にしなかった 7 件は、既存資料に式や出力の根拠がない、表示だけの処理である、独立した計算構造ではない、という理由で外した（considered_not_adopted.json の reason）。
- **使ってはいけない記述**：
  - 旧研究が原版の全計算式を調査・検証した
  - 未調査は 9 族だけである（式の本文は 59 族すべてで未調査）
- **新研究での再利用**：候補（ルート B・C）
  - 使い道：新研究が建築 LCA の計算体系の全体を扱うとき、旧研究の 70 単位に入っていない計算構造（7 件）と、調べていない範囲を先に確認する一覧として使う。
  - 条件・注意：7 件の根拠は既存資料（01〜08 章）の記述だけである。原版の内容は推測で補わない。
- **分類の根拠**：
  - [`09_APPROX_STUDY/01_LEDGER/README.md`](../../../09_APPROX_STUDY/01_LEDGER/README.md):14-20（調べていないもの）、157-165（評価単位にしなかったもの）
  - [`09_APPROX_STUDY/01_LEDGER/considered_not_adopted.json`](../../../09_APPROX_STUDY/01_LEDGER/considered_not_adopted.json): not_adopted（7 件）
  - [`09_APPROX_STUDY/01_LEDGER/sheet_family_coverage.json`](../../../09_APPROX_STUDY/01_LEDGER/sheet_family_coverage.json): families[status=NOT_INSPECTED]（9 族、79,260 ノード）
  - [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md):26-35（P1）
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md):5-18（A-1〜A-6）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):128（4. Over-claims、5. Directive compliance: Uninspected scope is stated in 01, 06 and the top-level README）
- **分類した観点**：R1（統制文書・台帳・順位）

<a id="ck-r1-21"></a>

## CK-R1-21　誤りまたは古いと指摘された数と記述の一覧（台帳・順位・関連する報告）

- **区分**：4　不具合・未解決事項
- **内容**：台帳と順位、およびそれを引用する報告のうち、第2回の検査が誤りまたは古いと指摘した数と記述を 1 か所にまとめたもの。どれも HEAD に残っている（直す段階 b3 と報告の再生成は未着手）。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
  - [`09_APPROX_STUDY/01_LEDGER/README.md`](../../../09_APPROX_STUDY/01_LEDGER/README.md)
  - [`09_APPROX_STUDY/01_LEDGER/sheet_family_coverage.json`](../../../09_APPROX_STUDY/01_LEDGER/sheet_family_coverage.json)
  - [`09_APPROX_STUDY/01_LEDGER/unlinked_input_disposition.json`](../../../09_APPROX_STUDY/01_LEDGER/unlinked_input_disposition.json)
  - [`09_APPROX_STUDY/02_RANKING/README.md`](../../../09_APPROX_STUDY/02_RANKING/README.md)
  - [`09_APPROX_STUDY/02_RANKING/research_priority.json`](../../../09_APPROX_STUDY/02_RANKING/research_priority.json)
  - [`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../../09_APPROX_STUDY/04_VERIFICATION/README.md)
  - [`09_APPROX_STUDY/05_DECISIONS/README.md`](../../../09_APPROX_STUDY/05_DECISIONS/README.md)
  - [`09_APPROX_STUDY/03_MODELS/judge_proposal_trace.json`](../../../09_APPROX_STUDY/03_MODELS/judge_proposal_trace.json)
- **確かめ方**：第2回の「報告書の監査」の検査が JSON から数え直して見つけた（REP）。この検査の指摘には第2の検証者は付かず、全体の調整役が検査のスクリプトを再実行して再現した。RED-6 は反証役の検証者が CONFIRMED とした。この読み取りでも、保存された JSON の解析だけで (1)〜(7) の数、(8) の台帳の文面、(9) の 52 件と 56 件を確かめ、指摘と同じだった。(8) のコードの動作と (9) の「測定なし 14 件」は確かめていない。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：43ba5d7 の版（HEAD と同じ）の台帳・順位・報告の記述。
- **関係する第2回の指摘**：REP-1、REP-2、REP-7、REP-8、REP-10、REP-11、REP-18、RED-6
- **第2回の指摘の影響**：(1) REP-8：units.json 見出しの structure_class_counts と 01_LEDGER/README.md の表は LINEAR_SUM_PRODUCT 29・RATIO 11。70 単位から数えると 30・10。ほかの 11 分類は合う。同じ README の単位の一覧は 30・10 を示している。(2) REP-7：05_DECISIONS/README.md「単位が参照する入力項目 116（既存 88＋追加 28）｜同じ｜変化なし」は台帳の申告の数で、測定ではない。実測は仕様 77＋追加 56。(3) REP-1：04_VERIFICATION/README.md 103 行目「入力仕様 124 項目のうち 0 項目は記録用で、どの計算にも使われない」。実測で読まれない仕様の入力は 47 項目（読まれない項目の一覧は 64 件＝仕様 47＋追加 17）。台帳は 30 項目を記録用としている。(4) REP-7：未接続入力の「追加単位で接続 14」のうち 3、「既存式が暗黙に使用 9」のうち 6 は基準計算が読まない。(5) REP-11：02_RANKING/README.md 11 行目の和集合の文面。A と B の和集合は 38（重なり 14）、42 は感度の 6 件を含む。(6) REP-18：シート族の状態の表示が不統一（COVERED_BY_EXISTING の 3 族が追加単位を含む、NON_CALCULATION の 11 族が関連単位を持つ、数式 0 件の 3 族が COVERED_BY_ADDITIONAL）。(7) REP-10：A13-04 の台帳の文面（副分類 UNDEFINED_MODEL、「基準計算には実装しない」、「モデルが未定義のため…基準計算との誤差比較はできない」）。computable_in_reference は真で、基準計算に実装されている。v1.4 草稿は手順書の側だけを直し、台帳は直していない。(8) RED-6：SYS-01 の branches「値が null・空・NaN → MISSING」。定義文とコードでは None だけが MISSING。(9) REP-2：judge_proposal_trace.json の「2 点以上 52 件、測定なし 20 件」は観点 b7 を使っている。P5 の定義どおり b8 を使うと 56 件、測定なし 14 件。
- **今の時点で言ってよいこと**：読んだ範囲では、台帳・順位について第2回の検査が数や記述の誤り・古さを指摘した箇所は上の 9 点である（REP-1〜18、REC-1〜9、RED-1〜12 は全文を読んだ。NUM と APP は見出しと該当箇所だけを読んだ）。これ以外の台帳・順位の数は、数え直しで合っている（CK-R1-05）。第2回の指摘ではないが、この読み取りで気づいた古い記述が 1 つある：SYS-01 の purpose 欄の「feeds には…42 単位を挙げた」は現在の台帳と合わない（SYS-01 の feeds は空で、検査の関係は gated_by に分けてあり、SYS-01 を gated_by に持つ単位は 17）。
- **使ってはいけない記述**：
  - 「活動量×係数の総和 29」「比・換算 11」（01_LEDGER/README.md、units.json の structure_class_counts）
  - 「単位が参照する入力項目｜116（既存 88＋追加 28）｜同じ｜変化なし」（05_DECISIONS/README.md:105）
  - 「入力仕様 124 項目のうち 0 項目は記録用で、どの計算にも使われない。」（04_VERIFICATION/README.md:103）
  - 「軸 A 22 件（重みを変えた場合だけ入るもの 6 件）、軸 B 30 件（境界の同点を含む）、和集合 42 件」（02_RANKING/README.md:11）の内数・和集合としての読み方
  - 「既存 53 式が対応（推定） 11 族 0.81％」「計算なし（数式 0 件） 15 族」を、重ならない一貫した区分として読むこと
  - A13-04 の「基準計算には実装しない」、SYS-01 の「NaN → MISSING」
  - 「評価軸 B の採点で…2 点以上だった単位×段階は 52 件。このうち…20 件」（03_MODELS）
- **新研究での再利用**：候補にしない
  - 理由・注意：直した版は存在しない。引用するときは、この一覧の正しい側の数（30・10、77＋56、47、38 と 42、56 と 14）を使う。
- **分類の根拠**：
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):1-6（REP-1）、8-13（REP-2）、43-48（REP-7）、50-55（REP-8）、64-69（REP-10）、71-76（REP-11）、120-125（REP-18）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):61-71（RED-6）
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json):11-25、units[id=A13-04].structure_subclass / reference_semantics_proposal / approximation_potential、units[id=SYS-01].branches / purpose / feeds
  - [`09_APPROX_STUDY/01_LEDGER/README.md`](../../../09_APPROX_STUDY/01_LEDGER/README.md):58-59
  - [`09_APPROX_STUDY/02_RANKING/README.md`](../../../09_APPROX_STUDY/02_RANKING/README.md):11
  - [`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../../09_APPROX_STUDY/04_VERIFICATION/README.md):103
  - [`09_APPROX_STUDY/05_DECISIONS/README.md`](../../../09_APPROX_STUDY/05_DECISIONS/README.md):105-106
  - [`materials/interrupted_fix/specs/SPEC_B3.md`](../materials/interrupted_fix/specs/SPEC_B3.md):20-57、[`materials/interrupted_fix/specs/STAGE_C_NOTES.md`](../materials/interrupted_fix/specs/STAGE_C_NOTES.md):31-32, 40-41（直す設計。未着手）
  - [`STOP_STATUS.md`](../STOP_STATUS.md):57-62
- **分類した観点**：R1（統制文書・台帳・順位）

<a id="ck-r7-01"></a>

## CK-R7-01　台帳の束縛欄（70 単位の id・段階・基準定義文・依存）

- **区分**：1　検証済み成果
- **内容**：評価単位 70 件（既存 53、追加 17）の台帳のうち、基準計算のコードから機械的に写している欄（reference_semantics＝基準計算の各関数の説明文、depends_on、feeds）。段階別の件数は PRE 5、A1-A3 10、A4 3、A5 4、B1 3、B1/C 1、B2 1、B3 2、B4 4、B5 1、B6 6、B7 4、C1 1、C2 1、C3 2、C4 1、C1-C4 2、MEMO 2、SUM 13、QA 4（計 70）。段階は A1-A3〜C4 の 14 と PRE・MEMO・SUM・QA で、D 段階の単位は無い。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
  - [`09_APPROX_STUDY/research_code/tools/sync_ledger.py`](../../../09_APPROX_STUDY/research_code/tools/sync_ledger.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py)
- **確かめ方**：tools/sync_ledger.py が説明文と依存をコードから台帳へ写す。第2回の検査 2 件が、70 単位すべてで reference_semantics＝説明文、depends_on・feeds＝登録の宣言（差 0）と報告。R7 も実行せずにテキスト照合（@unit の宣言と説明文を正規表現で読み、units.json と比較）し、差は依存 0 件・定義文 0 件。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：架空データだけ。独立概念モデル（70 評価単位）の定義についての記述で、原版ブックの式との対応は未確認。対象はコミット済みの版（43ba5d7 と同じコード）。追加単位（X-）は、シート名・未接続の入力項目・既存資料から推定した独立設計の案。
- **関係する第2回の指摘**：RED-4、RED-7、RED-9、RED-12、REP-7、REP-8、REP-10
- **第2回の指摘の影響**：文字列の一致そのものには影響しない。定義文がコードの挙動を言い尽くしていない箇所（RED-4・RED-7・RED-9・RED-12）と、束縛欄以外の欄の古さ（REP-7・REP-8・REP-10）は別項目（CK-R7-03、CK-R7-30、CK-R7-29）。
- **今の時点で言ってよいこと**：70 単位すべてで、台帳の reference_semantics は基準計算（43ba5d7 の版）の関数の説明文と同じ文字列、depends_on は登録の宣言と同じ、feeds は depends_on の逆引きである。
- **使ってはいけない記述**：
  - 「基準定義文だけで単位の結果が一意に決まる」（RED-7・RED-9・RED-12）
  - 台帳の見出し structure_class_counts の「LINEAR_SUM_PRODUCT 29、RATIO 11」（単位から数えると 30 と 10。REP-8）
  - 台帳の inputs 欄を、基準計算が読む入力項目の一覧として使うこと（REP-7）
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：方程式グループの分類台帳を作るときの、単位 id・段階・定義文・依存の対応表として使う。
  - 条件・注意：定義文は 43ba5d7 の版のもの。中断した修正（65ff124）は units.json を 129 行、基準計算の 4 ファイルを書き換えており、定義文も依存も変わる（未検証。CK-R7-32）。追加単位 17 件は推定による設計案で、原版にその計算があることは確認していない。
- **分類の根拠**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json): unit_count=70、existing_unit_count=53、additional_unit_count=17、reference_note、dependency_note、scope_statement
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):146（CHECKS PERFORMED 4：70 単位で定義文＝説明文、depends_on＝登録、差 0）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):128（CHECKS PERFORMED 3 と 7：同じ結果。REP の指摘には第2検証者が付いていない）
  - [`09_APPROX_STUDY/research_code/tools/sync_ledger.py`](../../../09_APPROX_STUDY/research_code/tools/sync_ledger.py):5-7,64-83
  - R7 の集計（python、JSON とテキストの解析だけ）：段階別 PRE 5、A1-A3 10、A4 3、A5 4、B1 3、B1/C 1、B2 1、B3 2、B4 4、B5 1、B6 6、B7 4、C1 1、C2 1、C3 2、C4 1、C1-C4 2、MEMO 2、SUM 13、QA 4
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））

<a id="ck-r7-02"></a>

## CK-R7-02　評価単位の依存グラフ（depends_on）

- **区分**：1　検証済み成果
- **内容**：どの単位の結果をどの単位が使うかを表す有向グラフ。頂点 70、辺 183、閉路なし、深さ 0〜7。依存を持たない単位 32、どこにも渡さない単位 30、その両方 10。段階ベクトル X-02 が 29 単位を直接受け、ホールライフ SUM-03 の上流は 37 単位。入力検査の関係 gated_by（38 辺）は別の欄で、台帳だけにある。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
  - [`09_APPROX_STUDY/research_code/refcalc/registry.py`](../../../09_APPROX_STUDY/research_code/refcalc/registry.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py)
- **確かめ方**：registry.order() が依存順に並べ、閉路があればエラーにする（コミット済みの全測定はこの順で実行された）。第2回の検査 2 件が台帳の依存＝登録の宣言（差 0）と報告。R7 は units.json から辺・深さ・上流を数え、@unit の宣言とテキスト照合した（差 0）。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：架空データだけ。独立概念モデル（70 評価単位）の定義についての記述で、原版ブックの式との対応は未確認。グラフは「宣言された依存」で、43ba5d7 の版のもの。
- **関係する第2回の指摘**：RED-1、RED-7、RED-5、RED-11
- **第2回の指摘の影響**：依存の宣言と台帳の一致には影響しない。ただし、不完全の印がこのグラフに沿って伝わらないこと（RED-1）、B3・B4 は A13-04 を使わず B5 は使うという違いが定義文ではなく依存だけで決まっていること（RED-7）、SUM-08 が基準案を入力の外の登録表から取ること（RED-5）は、グラフを使う前に知っておく必要がある。
- **今の時点で言ってよいこと**：台帳の depends_on（183 辺）は基準計算の宣言と同じで、閉路が無い。主な流れ：A13-02→X-15、A13-05・X-15→A13-01／A13-03→A13-04；A1-A3・A4・C の行結果→B3-01・B4-02・B5-01；B6-04・X-06→B6-01→B6-03・B2-01；B7-01〜03→B7-04；B1-02→B1-03・B1-04；29 単位→X-02→SUM-01・SUM-02・SUM-03、SUM-03→SUM-04〜08；X-04→QA-01・QA-03；SYS-04→QA-04。
- **使ってはいけない記述**：
  - 「depends_on は、関数が読む他単位の結果をすべて挙げている」：X-07 の関数は res["B2-01"] を読むが、依存に B2-01 が無い（X-02 経由で先に計算される。R7 のテキスト照合で見つけた点で、第2回の指摘には無い）
  - 「gated_by の検査に通らない行は計算されない」：コード上、SYS の結果を読む単位は QA-04（SYS-04 の残差）だけで、計算は検査の結果を見ずに、単位ごとに除外して数える
  - 「SUM-08 の依存は SUM-03 だけ」：実際には基準案のシナリオを synth.population.BASELINES（シナリオの外の登録表）から取り、基準計算全体をもう一度実行する
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：方程式グループ間の依存関係の台帳、計算順序、どの単位の誤差がどこへ伝わるか（上流の行結果→B3・B4・B5→合計）を調べるときの出発点。
  - 条件・注意：X-08 は B4-02 を依存に挙げるが関数の中では読まない（R7 のテキスト照合）。段階合計に入らない単位（SUM-03 の上流でない 32 単位：代替値、参考値、集計表、検査、指標）を合計の経路と混同しない。65ff124 では依存が変わる（自己申告では X-04 が X-02 に依存するようになる。未検証）。
- **分類の根拠**：
  - R7 の集計（python、units.json）：辺 183、feeds は depends_on の逆引きと一致、gated_by 38 辺（SYS-01 17、SYS-02 10、SYS-03 11）
  - 層の構成：深さ 0＝32 単位（SYS-01、SYS-02、SYS-03、SYS-04、A13-02、A13-05、A4-01、A5-01、A5-02、A5-03、B1-01、B1-02、B4-01、B4-03、B6-02、B6-04、B7-01、B7-02、B7-03、C1-01、C2-01、C3-01、C4-01、STO-01、STO-02、QA-02、X-01、X-06、X-09、X-12、X-14、X-16）；深さ 1＝12 単位（A4-02、A5-04、B1-03、B1-04、B6-01、B7-04、C-05、QA-04、X-10、X-11、X-13、X-15）；深さ 2＝5 単位（A13-01、A13-03、B2-01、B6-03、X-03）；深さ 3＝5 単位（A13-04、B3-01、B3-02、B4-02、X-17）；深さ 4＝2 単位（B5-01、X-08）；深さ 5＝3 単位（X-02、X-04、X-05）；深さ 6＝6 単位（SUM-01、SUM-02、SUM-03、QA-01、QA-03、X-07）；深さ 7＝5 単位（SUM-04、SUM-05、SUM-06、SUM-07、SUM-08）
  - 入る辺の多い単位：X-02 29、X-04 23、X-05 23、X-08 13、B4-02 12、B5-01 12。出る辺の多い単位：A13-01 11、A13-03 11、A13-05 9、X-01 8、A4-01 7、A4-02 7
  - SUM-03 の上流でない単位（自身を除く 32）：B1-01、B3-02、C-05、QA-01、QA-02、QA-03、QA-04、STO-01、STO-02、SUM-01、SUM-02、SUM-04、SUM-05、SUM-06、SUM-07、SUM-08、SYS-01、SYS-02、SYS-03、SYS-04、X-03、X-04、X-05、X-07、X-08、X-09、X-10、X-11、X-12、X-13、X-16、X-17
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py):379-380,395（X-07 の依存の宣言と res["B2-01"] の読み取り）
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py):500,516（SUM-08：population.BASELINES と run_all(base)）
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py):571-577（QA-04 だけが SYS の結果を読む。R7 の検索で res["SYS-…"] は SYS-04 だけ）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):1-11（RED-1）、73-83（RED-7）、49-59（RED-5）
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））

<a id="ck-r7-03"></a>

## CK-R7-03　台帳の分析欄（構造分類 13 種・標準形・分岐・未定義点）

- **区分**：2　暫定・未検証成果
- **内容**：各単位に付けた structure_class（13 種）、structure_subclass、canonical_form、loop_dims、branches、complexity、similar_units、unification_potential、approximation_potential、ambiguities と、分析担当の定義案 reference_semantics_proposal（29 件）。自動分析（AI エージェント）と主担当が書いた分類と案で、基準計算が採用した定義ではない。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
  - [`09_APPROX_STUDY/01_LEDGER/README.md`](../../../09_APPROX_STUDY/01_LEDGER/README.md)
- **確かめ方**：構造分類の件数は第2回の報告書検査が単位から数え直した（見出しと 2 行が食い違う）。標準形や分岐の記述を、基準定義やコードと 1 件ずつ突き合わせた検査の記録は無い。
- **確かめた者**：作成者のみ
- **言える範囲**：架空データだけ。独立概念モデル（70 評価単位）の定義についての記述で、原版ブックの式との対応は未確認。評価軸 B（3 つの自動評価）の採点は初版の台帳に対するもの。
- **関係する第2回の指摘**：REP-8、REP-10、RED-6、REP-7
- **第2回の指摘の影響**：見出しの件数が古い（REP-8）。A13-04 の「基準計算には実装しない」と UNDEFINED_MODEL は現状と合わない（REP-10）。SYS-01 の branches の「NaN→MISSING」は基準定義と食い違う（RED-6）。inputs 欄は基準計算が読む入力と合わない（REP-7）。
- **今の時点で言ってよいこと**：単位から数えた構造分類は LINEAR_SUM_PRODUCT 30、RATIO 10、PREDICATE_GATE 8、SUM_OF_STAGES 5、TIME_SERIES_SUM 4、EVENT_SCHEDULE 3、LOOKUP_JOIN 3、MAX_CLAMP 2、WEIGHTED_AVERAGE 1、RECURRENCE 1、COUNT_FLOOR 1、MASS_BALANCE_CONSTRAINT 1、MATRIX_EXPANSION 1（計 70）。この分類と標準形は「どういう形の式か」の一次的な整理として読める。
- **使ってはいけない記述**：
  - canonical_form を基準定義として使うこと（例：B4-03 は「ceil(T/c)−1」と書くが、基準定義は許容幅つきの数え上げ。SYS-04 は「r==0」と書くが、基準定義は |r|≦1e-9×A。SYS-03 は許諾の用途表を書くが、基準定義は PERMITTED_PUBLIC だけ。R7 の読み比べ）
  - 見出しの structure_class_counts（29／11）
  - A13-04 の structure_subclass=UNDEFINED_MODEL と「基準計算との誤差比較はできない」
  - SYS-01 の branches「値が null・空・NaN → MISSING」
- **新研究での再利用**：候補（ルート B・C）
  - 使い道：式の形の一次分類（13 種）、単位ごとの繰り返しの次元（loop_dims）、未定義点の一覧（ambiguities）を、新しい分類台帳の材料にする。
  - 条件・注意：束縛するのは reference_semantics だけ（units.json の reference_note）。分析欄は初版のままの箇所があり、後から変わった定義（B2 と B6 の規則、係数の使用条件など）を反映していない可能性がある。1 件ずつ基準定義と読み比べてから使う。
- **分類の根拠**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json): structure_class_counts（見出し）と units[].structure_class（R7 の集計：LINEAR_SUM_PRODUCT 30、RATIO 10、PREDICATE_GATE 8、SUM_OF_STAGES 5、TIME_SERIES_SUM 4、EVENT_SCHEDULE 3、LOOKUP_JOIN 3、MAX_CLAMP 2、WEIGHTED_AVERAGE 1、RECURRENCE 1、COUNT_FLOOR 1、MASS_BALANCE_CONSTRAINT 1、MATRIX_EXPANSION 1）
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json): authorship_note（ANALYST 29 件、MAIN_SESSION 41 件）、reference_note
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):50-55（REP-8）、64-69（REP-10）、43-48（REP-7）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):61-71（RED-6）
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md):86（軸 B の採点は初版の台帳に対するもの）
  - R7 の整理用の族（CK-R7-04〜CK-R7-14）と件数（計 70）：F01 行の和（活動量×換算倍率×係数） 19、F02 行ごとの数量の比・換算 2、F03 加重和・行列の展開・区分別の再集計 6、F04 事象の数え上げ（T と周期） 6、F05 年重み付き和 13、F06 区分的に直線・段階的な係数系列 1、F07 冷媒の充填・漏洩・補充・交換 3、F08 比・指標 4、F09 集約の木 5、F10 基準案との比較 1、F11 条件分岐・述語 10
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））

<a id="ck-r7-30"></a>

## CK-R7-30　台帳と記録の古い欄・食い違う欄

- **区分**：4　不具合・未解決事項
- **内容**：台帳（units.json）と、それを写した報告書に残っている、現在のコードや測定と合わない記述。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
  - [`09_APPROX_STUDY/01_LEDGER/README.md`](../../../09_APPROX_STUDY/01_LEDGER/README.md)
  - [`09_APPROX_STUDY/01_LEDGER/unlinked_input_disposition.json`](../../../09_APPROX_STUDY/01_LEDGER/unlinked_input_disposition.json)
  - [`09_APPROX_STUDY/05_DECISIONS/README.md`](../../../09_APPROX_STUDY/05_DECISIONS/README.md)
- **確かめ方**：第2回の報告書検査が JSON から数え直して確認（REP の指摘には第2検証者が付いておらず、主担当が検査のスクリプトを再実行して再現）。構造分類の件数は R7 も units.json から数え直した。
- **確かめた者**：独立検査（第2回）で再現（第2検証者なし）
- **言える範囲**：台帳の記述についての事実。
- **関係する第2回の指摘**：REP-7、REP-8、REP-10、REP-18、RED-6
- **第2回の指摘の影響**：未修正。台帳の見出しの件数は同期の道具（tools/sync_ledger.py）が更新しない。
- **今の時点で言ってよいこと**：(1) 見出し structure_class_counts は LINEAR_SUM_PRODUCT 29・RATIO 11 だが、単位から数えると 30・10（ほかの 11 種は一致）。(2) 単位の inputs 欄は基準計算が読む入力と合わない：台帳は仕様の 88 項目と「NEW:」28 項目を挙げるが、実測は仕様 77 と追加 56。台帳に挙がる仕様 12 項目は読まれず、台帳の「NEW:」名 28 のうち実在の追加欄と合うのは 4。(3) A13-04 は「基準計算には実装しない」、UNDEFINED_MODEL と書かれているが、基準計算の関数があり近似候補も測られている。(4) SYS-01 の branches は NaN を MISSING とするが、基準定義は None だけ。(5) シート族の対応状況のラベルが一貫していない（影響は数式ノードの割合で 0.6 ポイント未満）。
- **使ってはいけない記述**：
  - 見出しの structure_class_counts、単位の inputs 欄、A13-04 の未実装の記述、SYS-01 の branches
  - 05_DECISIONS の「単位が参照する入力項目 116（既存 88＋追加 28）｜同じ｜変化なし」
- **新研究での再利用**：候補（ルート B・C）
  - 使い道：台帳を新しい分類台帳の材料にするとき、使ってはいけない欄の一覧として使う。
  - 条件・注意：入力項目は input_usage.json の実測（読まれた欄＝必要な欄の上限）か、基準計算の関数から取り直す。件数は単位から数える。
- **分類の根拠**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json): structure_class_counts と units[].structure_class（R7 の集計）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):43-55（REP-7・REP-8）、64-69（REP-10）、120-125（REP-18）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):61-71（RED-6：branches の NaN の記述は台帳の内部の食い違い）
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json): units[id=A13-04].structure_subclass="UNDEFINED_MODEL"、computable_in_reference=true
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））

