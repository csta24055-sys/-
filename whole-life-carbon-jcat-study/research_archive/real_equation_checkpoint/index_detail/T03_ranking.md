# 索引の詳細 T03：着手順序（評価軸 A・B）

[INDEX.md](../INDEX.md) の項目ごとの詳細。分類担当（読み取り専用）が書いた内容を、欄ごとにそのまま載せる。
旧研究の数値はすべて架空データでの値で、対象は独立概念モデルである。原版の表計算との一致や、実建物での精度を示すものではない。
所在の表記：`09_APPROX_STUDY/…` などは `whole-life-carbon-jcat-study/` からの位置、`materials/…` はこの保存フォルダからの位置。

| 項目 | 区分 | 題 |
|---|---|---|
| [CK-R1-17](#ck-r1-17) | 2 | 評価軸 A：基準計算の単位別の負荷の測定と A スコア |
| [CK-R1-18](#ck-r1-18) | 2 | 評価軸 B：3 つの自動評価による採点（8 観点×0〜3 点） |
| [CK-R1-19](#ck-r1-19) | 3 | 評価軸 B の評価者が書いた理由と置き換え案（70 単位×3 者） |
| [CK-R1-20](#ck-r1-20) | 2 | 着手順序（優先スコア、着手群 3 つ、旧・上位 30％ の参考表示） |
| [CK-R3-22](#ck-r3-22) | 2 | 評価軸 A の単位別の負荷測定（測り方） |

<a id="ck-r1-17"></a>

## CK-R1-17　評価軸 A：基準計算の単位別の負荷の測定と A スコア

- **区分**：2　暫定・未検証成果
- **内容**：独立に実装した基準計算を架空の標準ベンチマーク（規模 S・M・L）で実行し、70 単位ごとに実行時間、実行したバイトコード命令数、ピークメモリを測った値と、それに台帳から数えた 4 指標を加えた 7 指標の百分位の重み付き和（A スコア）による順位。測ったのは 43ba5d7 の基準計算であり、原版ブックではない（原版は実行していない）。
- **所在**：
  - [`09_APPROX_STUDY/02_RANKING/axis_a_measurements.json`](../../../09_APPROX_STUDY/02_RANKING/axis_a_measurements.json)
  - [`09_APPROX_STUDY/02_RANKING/axis_a.json`](../../../09_APPROX_STUDY/02_RANKING/axis_a.json)
  - [`09_APPROX_STUDY/02_RANKING/README.md`](../../../09_APPROX_STUDY/02_RANKING/README.md)
  - [`09_APPROX_STUDY/research_code/bench/measure_axis_a.py`](../../../09_APPROX_STUDY/research_code/bench/measure_axis_a.py)
  - [`09_APPROX_STUDY/research_code/tools/rank_axes.py`](../../../09_APPROX_STUDY/research_code/tools/rank_axes.py)
- **確かめ方**：測定：標準ベンチマーク S（資材 200 行、設備 60 行、冷媒機器 5 台）、M（2,000、600、40）、L（20,000、6,000、300）、評価期間 60 年。Python 3.13.18、7 回反復、時間はごみ集め（GC）を止めた反復の中央値。指標：a1 時間の割合（重み 0.35）、a2 命令数（0.15）、a3 ピークメモリ（0.10）、a4 申告の入力数＋正規形の演算子の数（0.10）、a5 分岐と反復の数（0.10）、a6 depends_on と feeds の数（0.10）、a7 対応するシート族のノード占有率を関連単位の数で等分した値（0.10）。a1〜a3 は規模ごとの百分位の中央値。スコアと順位の計算は第2回の検査が入力から再計算して差 0。測定値そのものは第2回で測り直していない（時間とメモリは機械に依存するため対象外。命令数の数え直しは基準計算全体の規模 S・M だけで、単位別ではない）。第1回の検査が計算時間に GC の影響が混ざると指摘し、43ba5d7 の測定は GC を止めて時間を測っている（axis_a_measurements.json の garbage_collector）。
- **確かめた者**：作成者のみ（測定値）。スコアと順位の計算だけ 独立検査（第2回）で再現
- **言える範囲**：架空データ、独立概念モデル、純粋な Python の基準計算（43ba5d7）、同じ機械での値。資材 20,000 行まで。原版の計算負荷は測っていない。
- **関係する第2回の指摘**：REP-10、REP-11、REP-7、REP-18
- **第2回の指摘の影響**：測定値への指摘はない。a2 の説明（旧：基本演算回数）は v1.4 草稿で「実行したバイトコード命令数」に直した（REP-10）。a4 は申告の入力数を使い、申告は実際に読む入力と食い違う（REP-7）。a7 は名称からの推定の対応を使う（REP-18）。旧・上位 30％ の件数の文面は REP-11 のとおり読み違えやすい。
- **今の時点で言ってよいこと**：43ba5d7 の基準計算を架空の標準ベンチマークで測った値として、70 単位すべての時間・命令数・メモリが保存されている（未測定の単位はない）。規模 L の時間の割合が大きいのは SUM-08 29.79％、X-04 16.82％、B3-01 8.78％（割合の分母は 70 単位の時間の和）。A スコアの上位は B4-02 0.921、B3-01 0.916、X-04 0.873。重みを変えた 3 通り（時間のみ、全指標等重み、代理指標 a7 を除外）の順位も保存されている。順位は着手順序の参考にだけ使われた。
- **使ってはいけない記述**：
  - 軸 A が原版ブックの計算負荷を表す（a7 は数式ノード数による代理指標で、対応は名称からの推定）
  - 時間とメモリの絶対値が、他の機械や他の実装でも同じである
  - 02_RANKING/README.md:11「軸 A 22 件（重みを変えた場合だけ入るもの 6 件）」を、6 件が 22 件の内数であると読むこと（6 件は 22 件の外）
  - a2 を「基本演算回数（内側ループの反復回数）」とする v1.3 以前の説明
  - 保存資料の axis_a_run.log.txt（69 単位を測定、1 単位は未測定）が現在の測定の記録である（初版のときの実行記録）
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：基準計算のどの単位に計算が集まるかの目安として、新研究で計算の重さを比べるときの基準側の参考値にする。
  - 条件・注意：純粋な Python の実装を同じ機械で測った値で、絶対値は環境で変わる。架空ベンチマークの行数の比（資材 : 設備 : 冷媒機器 = 200 : 60 : 5 など）に依存する（06_OPEN_ISSUES E）。43ba5d7 のコードの値で、65ff124 の変更後は測り直していない。SUM-08 の値は、定義どおり基準シナリオの計算をもう一度行う分を含む。新研究で使う数字は測り直す。
- **分類の根拠**：
  - [`09_APPROX_STUDY/02_RANKING/axis_a_measurements.json`](../../../09_APPROX_STUDY/02_RANKING/axis_a_measurements.json): what_is_measured, python 3.13.18, repeats 7, garbage_collector, benchmark_rows, total_time_ns, units[].measured（70 件とも真）
  - [`09_APPROX_STUDY/02_RANKING/axis_a.json`](../../../09_APPROX_STUDY/02_RANKING/axis_a.json): weights, ranking[].time_share / operations / peak_memory_bytes / static / percentile_ranks, rank_by_variant, reference_top30（k 21、main 22 件、sensitivity_only 6 件）
  - [`09_APPROX_STUDY/02_RANKING/README.md`](../../../09_APPROX_STUDY/02_RANKING/README.md):15-16, 20-22, 27（軸 A の説明と表）
  - [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md):100-116（P4）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):71-76（REP-11）、130（Absolute times and peak memory ... not re-measured）
  - [`09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md`](../../../09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md):53（GC の影響の指摘と対応）
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md):83-87（E）
  - [`materials/earlier_session_scratch/wfB/axis_a_run.log.txt`](../materials/earlier_session_scratch/wfB/axis_a_run.log.txt)
- **分類した観点**：R1（統制文書・台帳・順位）

<a id="ck-r1-18"></a>

## CK-R1-18　評価軸 B：3 つの自動評価による採点（8 観点×0〜3 点）

- **区分**：2　暫定・未検証成果
- **内容**：3 つの自動評価（AI エージェント。観点は代数的統合、数値近似、入力・データモデル削減）が、評価単位の事実だけをまとめた資料（axis_b_input_digest.json）を読み、指示書の 8 観点（b1〜b8）を各 0〜3 点で採点したもの。B スコアは観点ごとの 3 者の中央値の合計（0〜24）、統合観点は b2＋b3＋b4＋b8。人による評価ではなく、測定でもない。簡略化・近似・統合の「余地」についての事前の判断であり、実際にできたかどうかの結果ではない。
- **所在**：
  - [`09_APPROX_STUDY/02_RANKING/axis_b.json`](../../../09_APPROX_STUDY/02_RANKING/axis_b.json)
  - [`09_APPROX_STUDY/02_RANKING/axis_b_judges/`](../../../09_APPROX_STUDY/02_RANKING/axis_b_judges)
  - [`09_APPROX_STUDY/02_RANKING/axis_b_input_digest.json`](../../../09_APPROX_STUDY/02_RANKING/axis_b_input_digest.json)
  - [`09_APPROX_STUDY/02_RANKING/README.md`](../../../09_APPROX_STUDY/02_RANKING/README.md)
  - [`materials/earlier_session_scratch/`](../materials/earlier_session_scratch)
- **確かめ方**：点数は評価者（AI）の判断で、内容を点検した検査はない。中央値の合計、統合観点、割れの印の計算は、第2回の検査で再現した（この読み取りでも 3 つの評価者のファイルから数え直して不一致 0）。評価者が互いの採点を見なかったことは、リポジトリの内容からは確かめられない。
- **確かめた者**：作成者のみ（採点）。集計の計算だけ 独立検査（第2回）で再現
- **言える範囲**：独立概念モデルの 70 単位。採点は初版の台帳に対するもの（評価者に渡した資料の最終変更は a4e6427、評価者のファイルと axis_b.json の最終変更は d519433）。その後の基準定義の変更（X-16 を基準計算に加えたことなど）は反映していない。
- **関係する第2回の指摘**：REP-2、REP-11
- **第2回の指摘の影響**：採点そのものへの指摘はない。採点を後の記録と対照した表（03_MODELS/judge_proposal_trace.json）は、観点 b7（入力変数を減らせそう）を「他の式と共通の近似モデルにできる」として M4 に対応させており、手順書 P5 の定義（共通の代理モデルは b8）と合わない（REP-2）。
- **今の時点で言ってよいこと**：70 単位×3 者×8 観点の点数と、各採点の理由・置き換え案の文章が保存されている。B スコアは最高 21（B1-02、B3-01）、最低 4（SYS-01）。3 者の合計の差が 6 点以上の「割れ」は 6 単位（X-17、X-13、X-15、X-10、SUM-08、B2-01）。点数は着手順序の決定にだけ使われた。
- **使ってはいけない記述**：
  - 軸 B の点数が、簡略化・近似・統合が実際にできる度合いを測った値である
  - 評価者が人である、または互いに独立であることが確かめられている
  - 採点が現在の台帳・基準定義に対するものである
  - 03_MODELS/README.md と judge_proposal_trace.json の「2 点以上だった単位×段階は 52 件。このうち測定をせずに理由だけで見送ったものは 20 件」（P5 の定義どおり b8 を使うと 23＋33＝56 件、測定なしは 14 件）
- **新研究での再利用**：候補にしない
  - 理由・注意：AI による事前の判断で、初版の台帳に対するもの。
- **分類の根拠**：
  - [`09_APPROX_STUDY/02_RANKING/axis_b.json`](../../../09_APPROX_STUDY/02_RANKING/axis_b.json): definition, judges, unification_criteria, disputed_units, ranking[].median_by_criterion / judge_totals / judge_spread
  - [`09_APPROX_STUDY/02_RANKING/axis_b_judges/judge_algebraic_unification.json`](../../../09_APPROX_STUDY/02_RANKING/axis_b_judges/judge_algebraic_unification.json), judge_input_data_model.json, judge_numerical_approximation.json: scores（各 70 件）
  - [`09_APPROX_STUDY/02_RANKING/axis_b_input_digest.json`](../../../09_APPROX_STUDY/02_RANKING/axis_b_input_digest.json): note（Opinions about how to simplify are deliberately left out）
  - [`09_APPROX_STUDY/02_RANKING/README.md`](../../../09_APPROX_STUDY/02_RANKING/README.md):95, 170
  - [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md):118-135（P5）
  - [`09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md`](../../../09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md):65（採点は初版の台帳に対するもので、やり直していない）
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md):86
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):8-13（REP-2）、130（COULD NOT CHECK: judges ... without seeing each other's output）
  - [`09_APPROX_STUDY/03_MODELS/judge_proposal_trace.json`](../../../09_APPROX_STUDY/03_MODELS/judge_proposal_trace.json): score_2_or_more（b7→M4 が 29 件、b6→M3 が 23 件。JSON の解析）
- **分類した観点**：R1（統制文書・台帳・順位）

<a id="ck-r1-19"></a>

## CK-R1-19　評価軸 B の評価者が書いた理由と置き換え案（70 単位×3 者）

- **区分**：3　研究途中の数式・仮説
- **内容**：3 つの自動評価が、採点と一緒に各単位について書いた理由（rationale）と置き換え案（replacement_idea）。例：B1-02（使用期間の漏洩）について、年ごとの漸化式を交換区間ごとの等比級数の閉形式にし、B1-03・B1-04 と残存量を共有する 1 つの物質収支にまとめる案。SYS-01〜03 を共通の規則表に載せる案。
- **所在**：
  - [`09_APPROX_STUDY/02_RANKING/axis_b_judges/`](../../../09_APPROX_STUDY/02_RANKING/axis_b_judges)
  - [`09_APPROX_STUDY/02_RANKING/axis_b.json`](../../../09_APPROX_STUDY/02_RANKING/axis_b.json)
  - [`09_APPROX_STUDY/03_MODELS/judge_proposal_trace.json`](../../../09_APPROX_STUDY/03_MODELS/judge_proposal_trace.json)
- **確かめ方**：なし（提案の文章）。一部の案は後に統合モデルの記録や近似候補として取り上げられた。どの案がどう記録されたかの対照表（judge_proposal_trace.json）には、名前の付いた提案 10 件の扱いが書かれているが、観点と段階の対応に誤りがある（REP-2）。
- **確かめた者**：なし
- **言える範囲**：初版の台帳に対する AI の提案。独立概念モデルの単位について。
- **関係する第2回の指摘**：REP-2
- **第2回の指摘の影響**：提案の文章への指摘はない。対照表の「2 点以上 52 件、測定なし 20 件」は別の問いに答えた数である（REP-2）。対照表で「測定あり」とされた項目のうち 10 件は、建物全体の代理モデル AP-15 だけが測定の記録である（REP-2 の EVIDENCE）。
- **今の時点で言ってよいこと**：210 件（70 単位×3 者）の理由と置き換え案が、提案として保存されている。提案が正しいかどうかは、この文章からは分からない。
- **使ってはいけない記述**：
  - 置き換え案を、検証済みの簡略化・統合として読むこと
  - judge_proposal_trace.json の measured が真であることを、その単位の式で近似を測定したという意味に読むこと
- **新研究での再利用**：候補（ルート B・C）
  - 使い道：式どうしの共通の形についての仮説の一覧として、新研究で変換の候補を探すときに読む。
  - 条件・注意：AI の提案で未検証。初版の台帳に対するもの。旧研究で実際に取り上げた案の結果は、03_MODELS を担当する読み取りの分類に従う。
- **分類の根拠**：
  - [`09_APPROX_STUDY/02_RANKING/axis_b.json`](../../../09_APPROX_STUDY/02_RANKING/axis_b.json): ranking[].rationales, ranking[].replacement_ideas
  - [`09_APPROX_STUDY/02_RANKING/axis_b_judges/`](../../../09_APPROX_STUDY/02_RANKING/axis_b_judges)*.json: scores[].rationale, scores[].replacement_idea
  - [`09_APPROX_STUDY/03_MODELS/judge_proposal_trace.json`](../../../09_APPROX_STUDY/03_MODELS/judge_proposal_trace.json): named_proposals（10 件）, not_measured（20 件）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):8-13（REP-2）
- **分類した観点**：R1（統制文書・台帳・順位）

<a id="ck-r1-20"></a>

## CK-R1-20　着手順序（優先スコア、着手群 3 つ、旧・上位 30％ の参考表示）

- **区分**：2　暫定・未検証成果
- **内容**：優先スコア ＝ 0.35×軸 B の百分位 ＋ 0.30×統合観点（b2＋b3＋b4＋b8）の百分位 ＋ 0.35×軸 A の百分位 の高い順に 70 単位を並べ、3 つの着手群（24・24・22 件）に分けたもの。研究対象の絞り込みには使わず、着手の順番だけを示す。旧方針の上位 30％（各軸 k ＝ 21）は参考の印として残してある。
- **所在**：
  - [`09_APPROX_STUDY/02_RANKING/research_priority.json`](../../../09_APPROX_STUDY/02_RANKING/research_priority.json)
  - [`09_APPROX_STUDY/02_RANKING/README.md`](../../../09_APPROX_STUDY/02_RANKING/README.md)
  - [`09_APPROX_STUDY/research_code/tools/rank_axes.py`](../../../09_APPROX_STUDY/research_code/tools/rank_axes.py)
- **確かめ方**：順序と群の計算は、第2回の検査が入力から再計算して差 0。research_priority.json と progress_ledger.json の順序・群の不一致 0。入力である軸 A の測定値は測り直されておらず（CK-R1-17）、軸 B は AI の判断である（CK-R1-18）。
- **確かめた者**：作成者のみ（入力）。計算だけ 独立検査（第2回）で再現
- **言える範囲**：独立概念モデルの 70 単位の着手の順番。原資料全体の順位ではない。旧研究の作業の順番を決めるためのもので、研究の終了により役目を終えている。
- **関係する第2回の指摘**：REP-11
- **第2回の指摘の影響**：REP-11：02_RANKING/README.md 11 行目「軸 A 22 件（重みを変えた場合だけ入るもの 6 件）、軸 B 30 件（境界の同点を含む）、和集合 42 件」は読み違えやすい。重みを変えた場合だけ入る 6 件は 22 件の外にある。A（22 件）と B（30 件）の和集合は 38 件（重なり 14 件）で、42 件は感度の 6 件を加えた和集合である。research_priority.json の reference_top30_counts.union の 42 も同じ数え方。ほかの順位の数はすべて再現した。
- **今の時点で言ってよいこと**：1 位 B3-01（優先スコア 0.969）、2 位 B4-02（0.961）、3 位 B1-02（0.909）、70 位 SUM-06（0.048）。旧・上位 30％ の件数は、軸 A 22 件（境界の同点を含むので 21 を超える）、重みを変えた場合だけ入るもの 6 件（22 件とは別）、軸 B 30 件（B スコア 13 の同点 10 件を含む）、A と B の和集合 38 件、感度の 6 件を加えた和集合 42 件。70 単位すべてが研究対象として扱われた（research_target_count 70）。
- **使ってはいけない記述**：
  - 「軸 A 22 件（重みを変えた場合だけ入るもの 6 件）…和集合 42 件」を、6 件が 22 件に含まれ、A と B の和集合が 42 件であると読むこと
  - この順序が原資料全体の順位である
  - この順序が、どの単位で簡略化の効果が大きいかを確かめた結果である
- **新研究での再利用**：候補にしない
  - 理由・注意：新研究で優先順位を付けるなら、新研究の目的（変換の種類の数、誤差）に合わせて作り直す。
- **分類の根拠**：
  - [`09_APPROX_STUDY/02_RANKING/research_priority.json`](../../../09_APPROX_STUDY/02_RANKING/research_priority.json): scope_statement, priority_formula, waves（24・24・22 件）, reference_top30_counts（k_per_axis 21, A 22, A_sensitivity_only 6, B 30, union 42）, research_target_count 70
  - [`09_APPROX_STUDY/02_RANKING/axis_a.json`](../../../09_APPROX_STUDY/02_RANKING/axis_a.json): reference_top30.main（22 件）, reference_top30.sensitivity_only（6 件）
  - [`09_APPROX_STUDY/02_RANKING/axis_b.json`](../../../09_APPROX_STUDY/02_RANKING/axis_b.json): reference_top30.members（30 件）, cutoff_score 13
  - A と B の和集合 38、重なり 14、3 つの和集合 42（上の 3 つの一覧から JSON の解析で数えた）
  - [`09_APPROX_STUDY/02_RANKING/README.md`](../../../09_APPROX_STUDY/02_RANKING/README.md):9-11, 174-180, 247
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):71-76（REP-11）、128（research_priority.json vs progress_ledger.json order and wave: 0 mismatches）
  - [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md):137-148（P6）
- **分類した観点**：R1（統制文書・台帳・順位）

<a id="ck-r3-22"></a>

## CK-R3-22　評価軸 A の単位別の負荷測定（測り方）

- **区分**：2　暫定・未検証成果
- **内容**：bench/measure_axis_a.py。基準計算の評価単位ごとに、標準ベンチマーク S・M・L で、単位の関数の時間（GC 停止、反復の中央値）、全単位の時間に占める割合、実行したバイトコード命令数、メモリの増分のピークを測り、02_RANKING/axis_a_measurements.json に書く。測るのは架空データ上の基準計算だけで、原版の計算時間ではない。
- **所在**：
  - [`09_APPROX_STUDY/research_code/bench/measure_axis_a.py`](../../../09_APPROX_STUDY/research_code/bench/measure_axis_a.py)
- **確かめ方**：スクリプトの本文を読んだ。第2回：報告書の検査担当は、測定値のファイルを入力として軸 A・軸 B・優先度・着手順を計算し直し差 0 としたが、時間とメモリは測り直していない。
- **確かめた者**：作成者のみ（第2回は順位の計算の照合だけ）
- **言える範囲**：架空の標準ベンチマーク、基準計算の実装、作成者の機械。
- **関係する第2回の指摘**：REP-10
- **第2回の指摘の影響**：手順書 P4 は a2 を「基本演算回数（内側ループの反復回数）」と書くが、実際に測っているのは実行したバイトコード命令数である（REP-10）。
- **今の時点で言ってよいこと**：単位別の負荷は、基準計算の実装を架空のベンチマークで測った値で、着手順を決めるためだけに使われた。
- **使ってはいけない記述**：
  - 軸 A の値を、原版や実務の計算でどの式が重いかの根拠として使うこと
  - 手順書 P4 の a2 の説明（基本演算回数）
- **新研究での再利用**：候補にしない
  - 理由・注意：順位は架空ベンチマークの行数の比率（資材：設備：冷媒機器＝200：60：5 など）に依存する（06_OPEN_ISSUES の E）。測定値のファイル本体はこの読み手は読んでいない。
- **分類の根拠**：
  - [`09_APPROX_STUDY/research_code/bench/measure_axis_a.py`](../../../09_APPROX_STUDY/research_code/bench/measure_axis_a.py):1-15, 88-126
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):64-69, 128
- **分類した観点**：R3（統合モデルとその根拠）

