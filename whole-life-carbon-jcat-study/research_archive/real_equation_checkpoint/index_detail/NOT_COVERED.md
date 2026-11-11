# 分類担当が読んでいない範囲・分類できなかった範囲

[INDEX.md](../INDEX.md) の 9 節の詳細。観点ごとに、分類担当が申告した内容をそのまま載せる。

## R1（統制文書・台帳・順位）

- units.json の 70 単位の長い文章（purpose、見込み欄、曖昧点）は 8 単位しか通読していない。残りは項目の有無と件数だけを機械的に確かめた。各単位の記述の当否は分類していない。
- 軸 B の評価者の理由と置き換え案（210 件）は、先頭の単位と README の表以外は読んでいない。個々の提案の中身は分類していない（まとめて「研究途中の仮説」とした）。
- 軸 A の測定値が正しいかどうかは確かめていない（確かめるには測定の実行が要る。実行は禁止されている）。measure_axis_a.py は読んでいない。
- 自動生成の README が再生成した内容と同じであること（第2回の検査の報告）は、この読み取りでは確かめていない（確かめるには生成器の実行が要る）。
- numeric.md（NUM-1〜11）と approx.md（APP-1〜9）は見出しと関連箇所だけを読んだ。res.json、検査のスクリプト（checker_scripts）、検証用の指示文（VERIFY_*.md）、SPEC_A1.md・SPEC_A2.md・SPEC_B2.md、B2_REPORT*.json は読んでいない。
- 進捗台帳（05_DECISIONS）、記録（03_MODELS/records）、検証（04_VERIFICATION）の中身はこのレンズの外で、手順書との食い違いを述べるのに必要な範囲だけ第2回の指摘から引用した。
- 01〜08 章（旧研究より前の資料）は、件数と ID の照合に使った 3 つの JSON と 01_COMPLIANCE/README.md 以外は読んでいない。第2章の数（198 シート、3,818,483 ノード）そのものが正しいかは、原版がないので確かめられない。
- INDEX.md と HANDOVER.md は、読んだ時点ではフォルダになかった（STOP_STATUS.md と 09_APPROX_STUDY/README.md が参照している）。
- 分析担当・評価者・検査担当が互いの出力を見ずに作業したかどうかは、リポジトリの内容からは確かめられない（第2回の検査も同じ結論）。

## R2（基準計算・架空データ・比較・試験）

- 試験・測定・生成器は一切実行していない（指示による）。試験 28 件の合否、生成器の再現性、ナイフエッジの周期を生成器が作らないこと、は「未確認（実行が必要）」のまま。
- fastcalc（engine.py、closed_forms.py）と tools/、bench/approx_study.py、measure_axis_a.py、input_usage.py は担当外で読んでいない。統合モデル側の指摘（NUM-6、NUM-9 など）は基準計算に関係する部分だけ記した。
- bench/verify_unified.py は 1-175 行（scenarios、run_both、exactness）だけ読んだ。sweep_check と負荷の測定の部分は読んでいない。
- synth/generate.py のうち、係数カタログ、GWP、出所、プロジェクト、運用の後半、上水・廃棄物、解体、費用の生成部（およそ 500-695 行、1060-1145 行）は関数名の一覧だけで、本文を読んでいない。
- 中断時点のパッチ（working_tree_at_stop_65ff124.patch）は、ファイルの一覧と文字列の出現数だけを見た。a1 のコードの中身は確認しておらず、CK-R2-19〜24 は申告の内容の分類である。
- a1_scratch の出力は exact_60_20.out の先頭だけ見た。ほかの .out と .json は読んでいない。
- 第2回の指摘のうち records.md、approx.md、reports.md は担当外で読んでいない。REC-1、APP-5、REP-16、REP-17 は SPEC_A1.md と A1_REPORT.json での言及だけに基づく。
- 03_MODELS/DERIVATIONS.md、03_MODELS/records/、fastcalc/closed_forms.py の文言は直接読んでおらず、NUM-1 の引用を通してだけ触れた。
- 01_LEDGER/units.json は件数と注記だけを JSON として読んだ。70 単位の定義文と説明文が同文であることは、第2回の検査担当の報告（rederive.md CHECKS PERFORMED 4）に依る。

## R3（統合モデルとその根拠）

- 03_MODELS/records/units.json の個々の記録（454 件）の題名と理由文：件数と注記だけを JSON として読んだ。記録ごとの当否は、第2回の指摘（REC、REP）に書かれた範囲でしか述べていない。
- 03_MODELS/candidates.json、judge_proposal_trace.json、04_VERIFICATION/approximation_study.json、bench/approx_study.py、bench/mutations.py：近似候補は担当の範囲外として読んでいない。壊し方 36 種の中身は名前の一覧（unified_model_exactness.json の mutations）だけを見た。
- research_code/refcalc（基準計算）と common/compare.py の本文：読んでいない。基準計算の側の挙動と比較関数の中身は、第2回の指摘の記述に依った。
- rederive.md と approx.md：RED-3、RED-4、RED-12、APP-5 と見出しだけを読んだ。RED-1、RED-2、RED-5、RED-7 は見出しと、a1 の報告・仕様の記述から引いた。
- working_tree_at_stop_65ff124.patch の中身（bench/membership_check.py、bench/mechanism_probe.py、作り直しの途中の engine.py と closed_forms.py）：変更されたファイルの一覧だけを見た。a2 のスクリプトと再構成がどこまで完成していたかは判定していない。
- a2 の報告（A2_REPORT.json）：存在しない（a2 は報告の前に停止した）。
- a1_scratch の出力ファイル、B2 の報告、checker_scripts の各スクリプト（reports/recompute10.py の先頭 40 行を除く）：読んでいない。
- 02_RANKING/axis_a_measurements.json：読んでいない（測定スクリプトだけを読んだ）。
- 公表の数字が今の環境で再現するかどうか：確認していない（実行が必要。旧研究のコードは実行していない）。
- 掃引の 64 シナリオの内訳：JSON に記録がない。スクリプトは「規模 S の母集団 n 件＋名前に period を含まない境界条件」と作るが、実行時の n は確認できない（REP-16 は 32＋32 と書く）。
- 入力項目の使用の追跡を第2回の検査担当がやり直したかどうか：triage の記述と recompute10.py の先頭からは、JSON と報告書の照合しか確認できなかった。

## R4（近似検証）

- 構造別・用途別（by_group）の内訳は項目にしていない。数値は approximation_study.json にあるが、第2回でも独自に再実装されていない。
- 05_DECISIONS/PROGRESS.md、progress_ledger.json、03_MODELS/judge_proposal_trace.json、03_MODELS/DERIVATIONS.md は読んでいない。REP-5・REP-2 の件数は triage の記述からの引用で、このリーダーが数え直したのは records/units.json の段階×結論の件数だけ。
- 第2回の検査担当のスクリプトとログ（checker_scripts/approx、approx_verify）は存在だけ確かめ、中身は読んでいない。数値は triage/approx.md の記述からの引用。
- 65ff124 の b2 のコード本文（approx_measures.py など）と working_tree_at_stop_65ff124.patch は読んでいない（git show --stat で存在だけ確かめた）。b2 の出力 JSON は、スキーマ、新しい候補 8 種の主な項目、候補ごとの 1 行要約、波及後の合計だけを読んだ。
- A1_REPORT.json（b2 が使った基準計算の変更の内容）は読んでいない。
- 数値の再計算はしていない（旧研究のコードを実行していない）。未確認（実行が必要）：b2 のすべての数値、「時間規則の変更で近似の数値は変わらなかった」という b2 の申告、AP-06b・AP-12・AP-13・AP-15・AP-16 の公表値。
- 不採用理由にある「厳密な閉形式 K2・K3・K4・K7 が使える」という統合モデル側の主張の成否は、この担当の範囲外（統合モデルの担当の範囲）。

## R5（記録・進捗台帳・報告書・成果物・材料分類）

- 04_VERIFICATION/README.md の 113〜239 行（近似候補の誤差の表、条件別・材料区分別・段階別の表）は読んでいない。近似候補の個々の数字の分類は、近似の観点の読み取りに委ねる。
- numeric.md・approx.md・rederive.md は、見出しと CLAIM REFUTED・CORRECTED の行だけを読んだ（NUM-2、NUM-10、NUM-11 は全文）。証拠の細部（EVIDENCE、V-EVIDENCE）は、この 3 つの指摘を除いて読んでいない。
- build_reports.py の 58〜375 行（台帳・順位・モデル・検証の報告の生成部分）は、入力・出力先・固定文の行を検索しただけで、通読していない。rank_axes.py は 61 行以降を通読していない。bench/ の各スクリプトは、出力先を定義する行だけを見た（中身は読んでいない）。
- progress_ledger.json と records/units.json は、全体を読み込んで件数を数えたが、理由文を 1 件ずつ読んだのは一部（記録 14 件、単位 2 件）だけである。個々の記録の題名や理由がコードと合うかは、第2回の検査の記載によった（自分では確かめていない。確かめるには旧研究のコードの実行が要る）。
- 規模 L の命令数、時間、メモリ、681 シナリオの一致、近似の統計は、どれも記録された値を引用した。旧研究のコードを実行していないので、値そのものは確認していない。
- INDEX.md と HANDOVER.md は、読み取りの時点で research_archive/real_equation_checkpoint/ に存在しなかった（第9章 README の手書きの枠はこの 2 つを参照先に挙げている）。
- 第1回の検査の原資料（archive の materials/earlier_session_scratch/verify/）、中断した修正の報告（A1_REPORT.json、B2_REPORT.json、B2_REPORT_long.json）と仕様（SPEC_A1.md、SPEC_A2.md、SPEC_B2.md、SPEC_B3.md）は、この観点の対象外として開いていない。
- 07_MATERIAL_TAXONOMY の 3 つの JSON は、構造と件数を数えただけで、レコード定義の項目や不変条件の本文を 1 つずつ読んではいない。
- 01_LEDGER、02_RANKING の README と JSON（成果物 1〜4 の中身）は、この観点では読んでいない。成果物 1〜4 の状態は、第2回の検査（報告書の観点）の記載によった。

## R7（新研究のための再利用の下調べ（構造の棚卸し））

- research_code/fastcalc/engine.py（統合モデルの実装）は読んでいない。K1〜K7 の項目は models.json、DERIVATIONS.md、第2回の記録の監査の報告に基づく。
- research_code/synth/generate.py と population.py の本体、bench/approx_study.py、bench/verify_unified.py、bench/mutations.py の本体は読んでいない（README と関数名・定数名だけ）。生成器の分布の細部は第2回の報告からの引用。
- 03_MODELS/candidates.json の結論文、03_MODELS/records/units.json、03_MODELS/README.md、01_LEDGER/README.md、sheet_families.json、sheet_family_coverage.json、02_RANKING、05_DECISIONS、07_MATERIAL_TAXONOMY は読んでいない（R7 の観点の外、または他の読み手の担当）。
- materials/round2_review/triage/res.json（生の構造化結果）は読んでいない。同じ内容の triage/*.md を全文読んだ。
- 中断した修正：パッチの本文、SPEC_A1〜B3、B2_REPORT、a2_partial_outputs、b2_output は読んでいない。A1_REPORT.json は冒頭から RED-10 の項までを読んだ。65ff124 の版で依存グラフや定義文がどう変わるかは確認していない。
- 式の族 F01〜F11 は R7 が付けた整理用の区分で、旧研究の成果物には無い。各族の「依存する変数・線形性・分岐」は定義文とコードの読み取りで、実行による確認はしていない（実行は禁止）。
- 依存の宣言と関数本体の読み取りの食い違い（X-07 の B2-01、X-08 の B4-02）は R7 のテキスト照合によるもので、補助関数を経由する読み取りまでは追っていない。ほかに無いことは確認していない。
- 第2回の REP-1〜REP-18 には第2検証者が付いていない（主担当が検査のスクリプトを再実行して再現）。REP に基づく記述はその前提。
- 検査担当のスクリプト（materials/round2_review/checker_scripts/）は読んでいない。第2回の件数・数値は triage/*.md の記載のまま引用した（R7 は再計算していない。再計算には旧研究のコードの実行が必要）。

## R6（第2回の指摘 59 件の登録簿）

[FINDINGS_59.md](FINDINGS_59.md) の末尾を参照。
