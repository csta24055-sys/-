# 索引の詳細 T05：架空データ・比較の仕組み・試験

[INDEX.md](../INDEX.md) の項目ごとの詳細。分類担当（読み取り専用）が書いた内容を、欄ごとにそのまま載せる。
旧研究の数値はすべて架空データでの値で、対象は独立概念モデルである。原版の表計算との一致や、実建物での精度を示すものではない。
所在の表記：`09_APPROX_STUDY/…` などは `whole-life-carbon-jcat-study/` からの位置、`materials/…` はこの保存フォルダからの位置。

| 項目 | 区分 | 題 |
|---|---|---|
| [CK-R2-11](#ck-r2-11) | 2 | 架空シナリオのデータ構造（synth/model.py と JSON の入出力） |
| [CK-R2-12](#ck-r2-12) | 2 | 架空シナリオの生成器（synth/generate.py の make_scenario） |
| [CK-R2-13](#ck-r2-13) | 2 | 架空シナリオの集合（標準ベンチマーク S・M・L、検証用の母集団、境界条件 32 件、基準案の登録） |
| [CK-R2-14](#ck-r2-14) | 2 | 入力を壊す操作（bench/mutations.py：36 種類の壊し方、小数境界、段階の部分集合、無効な評価期間） |
| [CK-R2-15](#ck-r2-15) | 2 | 結果の比較の仕組み（common/compare.py） |
| [CK-R2-16](#ck-r2-16) | 4 | 比較の仕組みの既知の弱点（無限大、bool、床、余分な葉） |
| [CK-R2-17](#ck-r2-17) | 2 | 単体試験 28 件（tests/。コミット版） |
| [CK-R7-15](#ck-r7-15) | 2 | 入力データモデル（Scenario：スカラー欄と表） |
| [CK-R7-16](#ck-r7-16) | 2 | 架空シナリオの生成器と母集団 |
| [CK-R7-21](#ck-r7-21) | 2 | 比較の仕組み（結果の leaf ごとの比較、検証の実行、入力を壊す操作） |

<a id="ck-r2-11"></a>

## CK-R2-11　架空シナリオのデータ構造（synth/model.py と JSON の入出力）

- **区分**：2　暫定・未検証成果
- **内容**：架空の建物シナリオの入力側だけを持つデータ構造（dataclass 29 個。Scenario、Project、Boundary、MaterialRow、EquipmentRow、RefrigerantDevice、FactorRecord、AnnualProfile、GridFactorScenario など）。03_INPUTS/inputs.json の入力 124 項目を INPUT_FIELD_MAP で属性に対応付け、inputs.json に無い属性 73 個は「NEW:」付きで EXTRA_FIELD_MAP に載せる。計算結果は持たず、基準計算と統合モデルが同じ Scenario を読む。io.py が JSON への保存と復元をする。
- **所在**：
  - [`09_APPROX_STUDY/research_code/synth/model.py`](../../../09_APPROX_STUDY/research_code/synth/model.py)
  - [`09_APPROX_STUDY/research_code/synth/io.py`](../../../09_APPROX_STUDY/research_code/synth/io.py)
  - [`09_APPROX_STUDY/research_code/synth/__init__.py`](../../../09_APPROX_STUDY/research_code/synth/__init__.py)
  - [`09_APPROX_STUDY/research_code/synth/README.md`](../../../09_APPROX_STUDY/research_code/synth/README.md)
- **確かめ方**：作成者の試験（test_input_coverage：total が 124、test_json_round_trip、test_clean_scenario_is_consistent）。合否は今回実行していない。第2回の検査担当はこの構造を入力に使ったが、対応表そのものを検査した記録は、読んだ資料（numeric.md、rederive.md）には無い。件数 124・73・29 はソースの文字列を数えた値。
- **確かめた者**：作成者のみ
- **言える範囲**：架空データ用の入力スキーマ。独立概念モデルの入力仕様（03_INPUTS）に対応するもので、原版ブックの入力欄との対応は示さない。
- **関係する第2回の指摘**：NUM-5、NUM-7、NUM-9、RED-5
- **第2回の指摘の影響**：構造そのものを否定する指摘は無い。構造が検査しない点が指摘の前提になっている：係数 ID は自由な文字列で擬似 ID を予約していない（NUM-5）、GridStep.from_index は int と注釈されているが検査されない（NUM-7）、ScenarioMeta は「計算で読まない」と書かれているが統合モデルが読んでいた（NUM-9）、基準案は Scenario の外の登録表 BASELINES から読む（RED-5）。
- **今の時点で言ってよいこと**：データ構造と 2 つの対応表はコミットされており、基準計算、統合モデル、第2回の検査のすべてがこの構造を入力に使った。124 項目の対応は作成者の試験が検査する設計（合否は未確認、実行が必要）。
- **使ってはいけない記述**：
  - 「入力 124 項目すべてを属性に対応付け」（research_code/README.md 12 行、synth/README.md 13 行）を、独立に検査済みと読むこと
  - 型注釈や「clean scenarios では…」という説明文を、入力時に検査される条件と読むこと
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：固定の入力スキーマとして使う。新しいモデルが同じ Scenario を読めば、基準計算と同じ入力で比較できる。JSON の保存・復元でシナリオを固定できる。
  - 条件・注意：構造は型も範囲も検査しない。meta は計算で読まない。基準案は synth.population.BASELINES（プロセス内の辞書）にあり、シナリオの JSON には含まれない。年次量と電力係数は記述子と年次表の両方を持つ（冗長な入力。整った記述子が正）。年次表は最低 130 個。CostItem と price_index は inputs.json に無い本研究の追加入力。数値はすべて架空。
- **分類の根拠**：
  - [`09_APPROX_STUDY/research_code/synth/model.py`](../../../09_APPROX_STUDY/research_code/synth/model.py):1-35（データの規約）、671-692（Scenario）、787-924（INPUT_FIELD_MAP）、947-1021（EXTRA_FIELD_MAP）、1102-1137（check_input_coverage）
  - [`09_APPROX_STUDY/research_code/synth/io.py`](../../../09_APPROX_STUDY/research_code/synth/io.py):15-55
  - [`09_APPROX_STUDY/research_code/tests/test_synth.py`](../../../09_APPROX_STUDY/research_code/tests/test_synth.py):18-32
  - [`03_INPUTS/inputs.json`](../../../03_INPUTS/inputs.json)：total_fields 124
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):49-59, 73-83, 97-107（NUM-5、NUM-7、NUM-9）
- **分類した観点**：R2（基準計算・架空データ・比較・試験）

<a id="ck-r2-12"></a>

## CK-R2-12　架空シナリオの生成器（synth/generate.py の make_scenario）

- **区分**：2　暫定・未検証成果
- **内容**：make_scenario(seed, structure, use, size_class, study_period=60.0, dirty=False, **options)。固定シードの乱数（節ごとに独立した部分列）で架空シナリオを 1 つ作る。構造 4 種（S・RC・SRC・W）×用途 6 種。規模区分 S・M・L は、資材 200・2,000・20,000 行、設備 60・600・6,000 行、冷媒機器 5・40・300 台。評価期間は 0 < T ≤ 300。オプション 29 個。資材行の約 30％ は 3〜12 成分の複合品。dirty=True は 8 種類の不備をわざと入れ、入れた場所を meta.injected_defects に返す。倍率や範囲の表はすべて架空の例示。
- **所在**：
  - [`09_APPROX_STUDY/research_code/synth/generate.py`](../../../09_APPROX_STUDY/research_code/synth/generate.py)
  - [`09_APPROX_STUDY/research_code/synth/README.md`](../../../09_APPROX_STUDY/research_code/synth/README.md)
  - [`09_APPROX_STUDY/research_code/tests/test_synth.py`](../../../09_APPROX_STUDY/research_code/tests/test_synth.py)
- **確かめ方**：作成者の試験（test_deterministic：同じ引数で同じ JSON、test_clean_scenario_is_consistent：係数値 = Σ GWP×ガス別量、経路比率と質量比の和が 1、年次表の長さ、test_descriptors_match_tables、test_dirty_scenario_lists_defects）。合否は今回実行していない。第1回の検査への対応で、廃棄質量を据付量に合わせるよう生成器を直した（INDEPENDENT_REVIEW.md 38 行）。第2回：検査担当が 119 件、681 件、乱数の 20,260 件のシナリオ作りに使用。681 件の一覧を作り直した再比較で、記録の最大差 4.8e-13 が再現した（再現性の間接的な裏付け）。生成器を対象にした指摘は、読んだ資料には無い。
- **確かめた者**：作成者のみ
- **言える範囲**：架空データ。値の分布は本研究が作った例示で、実建物のばらつきを表さない（generate.py 1-16 行、synth/README.md 8 行）。
- **関係する第2回の指摘**：NUM-1、NUM-2、RED-11
- **第2回の指摘の影響**：生成器の欠陥の指摘は無い。生成器が作らない入力が指摘の対象になった：周期 1.000000001（NUM-1）、NaN・無限大（NUM-2）。RED-11：不備なしの標準ベンチマークの設備 6,660 行に、廃棄係数が None の行は 0。
- **今の時点で言ってよいこと**：生成器はコミットされており、同じ引数から同じシナリオを作る設計である（部分列のシードは「wlc-synth/1.0/<seed>/<節名>」）。第2回の検査担当が同じ一覧を作り直して記録値を再現しており、再現性に反する報告は無い。
- **使ってはいけない記述**：
  - 生成したシナリオ上の結果を、実建物での精度や規模の傾向として読むこと
  - dirty=False を「どんな検査でも不備が出ない」と読むこと（保証されるのは生成器の 8 種類の不備が無いこと）
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：固定の入力生成器として使う。新しいモデルと固定の基準に同じシナリオを与える。規模 S・M・L と構造×用途 24 組で、行数や構成を変えた比較ができる。
  - 条件・注意：GENERATOR_VERSION 1.0 と乱数の消費順を変えない（変えると既存のシナリオが変わる）。README は Python 3.13 を前提と書く（他の版での同一性は未確認）。周期は _draw_life により、EXACT_DIVISOR 以外では T の約数から相対 1e-6 以内に入らない。整数、小数 2 桁、T/n のいずれかなので、ナイフエッジの周期は作らないと読めるが、実行による確認はしていない。service_life_choices で周期を直接指定するときは CK-R2-03 の値を避ける。不備入りは 8 種類だけ。
- **分類の根拠**：
  - [`09_APPROX_STUDY/research_code/synth/generate.py`](../../../09_APPROX_STUDY/research_code/synth/generate.py):1-16（宣言）、42-49（規模区分、MAX_STUDY_PERIOD 300）、180-210（DEFAULT_OPTIONS 29 個）、246-255（不備 8 種類と反応する検査）、382-384（部分列）、447-476（_draw_life）、1177-1286（_inject_defects）、1335-1421（make_scenario）
  - [`09_APPROX_STUDY/research_code/synth/README.md`](../../../09_APPROX_STUDY/research_code/synth/README.md):18-25（規模区分の表）
  - [`09_APPROX_STUDY/research_code/tests/test_synth.py`](../../../09_APPROX_STUDY/research_code/tests/test_synth.py):23-80
  - [`09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md`](../../../09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md):38
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):134（CHECKS PERFORMED 2、9）、rederive.md:130（clean の設備 6660 行）
- **分類した観点**：R2（基準計算・架空データ・比較・試験）

<a id="ck-r2-13"></a>

## CK-R2-13　架空シナリオの集合（標準ベンチマーク S・M・L、検証用の母集団、境界条件 32 件、基準案の登録）

- **区分**：2　暫定・未検証成果
- **内容**：standard_benchmark()：RC・office・T=60 の規模 S・M・L（シード 101・102・103）の 3 件で、それぞれに基準案の写し（電力・ガス 15％ 増、発電なし、資材 10 行に 1 行の数量 20％ 増）を付ける。verification_population(n, seed, max_size)：構造×用途 24 組を順に回し、規模（重み S 0.65、M 0.33、L 0.02）、評価期間（30・50・60・75・100、15％ の確率で 42.5・62.5・99.9）、周期の作り方 5 種、年次量と電力係数の種類などを乱数で変える。edge_cases()：資材 12 行・設備 6 行・冷媒 4 台の小さいシナリオ 32 件（耐用年数が評価期間と等しい・割り切る・わずかにずれる・より長い・1 年未満、数量ゼロ、1 行だけ、行なし、漏洩率と回収率の 0 と 1、1 年未満と非整数の評価期間、期間内の建替など）。BASELINES は基準案を ID で引く登録表。
- **所在**：
  - [`09_APPROX_STUDY/research_code/synth/population.py`](../../../09_APPROX_STUDY/research_code/synth/population.py)
  - [`09_APPROX_STUDY/research_code/synth/README.md`](../../../09_APPROX_STUDY/research_code/synth/README.md)
  - [`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../../09_APPROX_STUDY/research_code/bench/verify_unified.py)
- **確かめ方**：作成者の試験（test_populations：規模と行数、24 組の網羅、境界条件の名前が重複なしで 30 件以上。test_edge_cases：32 件で恒等式と全ゲートの合格、complete 真を期待）。合否は今回実行していない。一致確認 681 件の内訳：標準ベンチマーク 3、境界条件 32、検証用の母集団 400（シード 20261111、max_size M）、不備入り 60、壊し方 144、小数境界 10、段階の部分集合 32。第2回：検査担当が母集団 24 件と境界条件 32 件を再導出に使い、681 件の一覧を作り直して再比較した。
- **確かめた者**：作成者のみ
- **言える範囲**：架空データ。検証用の母集団は一致確認では規模 M まで（規模 L は標準ベンチマークの 1 件だけ）。境界条件は規模 S 相当の小さいシナリオ。
- **関係する第2回の指摘**：NUM-1、RED-1、RED-5
- **第2回の指摘の影響**：集合そのものの欠陥の指摘は無い。網羅の不足が指摘された：境界条件にナイフエッジの周期が無い（life_near_divisor の値は 19.999999、20.000001、29.9999999、30.0000001）。段階の部分集合のシナリオ（stage_subset）は不備なしだけ（RED-1 への検証者の追記）。基準案を Scenario の入力ではなくプロセス内の登録表から読む点は設計どおりで、登録の無い ID が「指定なし」と区別されない（RED-5）。
- **今の時点で言ってよいこと**：3 つの関数と登録表はコミットされており、一致確認 681 件のうち 435 件（3 + 32 + 400）がここから作られた。第2回の検査担当も同じ関数でシナリオを作り、記録された最大差を再現した。
- **使ってはいけない記述**：
  - 境界条件 32 件が、基準計算の端の条件を網羅しているという読み方
  - 検証用の母集団が規模 L を含むという読み方（一致確認は max_size M。重み 0.02 の L は使われていない）
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：固定の評価用の集合として使う。標準ベンチマーク S・M・L は行数だけが違う 3 件で、規模への依存を見る。検証用の母集団は構造・用途・評価期間・入力の種類を振った分布、境界条件は少数行での端の動作の確認に使う。
  - 条件・注意：同じ引数（n、seed、max_size）で呼べば同じ列が得られる設計。attach_baseline は当該案の boundary.baseline_scenario を書き換え、BASELINES に登録する（プロセス内の状態）。SUM-08 を使う比較では登録表の中身を固定する。測定に使われた呼び出しは verification_population(400, seed=20261111, max_size="M")。
- **分類の根拠**：
  - [`09_APPROX_STUDY/research_code/synth/population.py`](../../../09_APPROX_STUDY/research_code/synth/population.py):17-22（シード、評価期間、規模の重み）、29-51（attach_baseline）、54-59（standard_benchmark）、62-85（verification_population）、157-196（edge_cases 32 件）
  - [`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../../09_APPROX_STUDY/research_code/bench/verify_unified.py):47-75（681 件の作り方）
  - [`09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json`](../../../09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json)：by_group（benchmark 3、edge 32、population 400、defective 60、mutated 144、decimal 10、stage_subset 32）
  - [`09_APPROX_STUDY/research_code/tests/test_synth.py`](../../../09_APPROX_STUDY/research_code/tests/test_synth.py):82-90、tests/test_refcalc.py:41-49
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):150（検証者の追記 3）、numeric.md:134（CHECKS PERFORMED 9）
- **分類した観点**：R2（基準計算・架空データ・比較・試験）

<a id="ck-r2-14"></a>

## CK-R2-14　入力を壊す操作（bench/mutations.py：36 種類の壊し方、小数境界、段階の部分集合、無効な評価期間）

- **区分**：2　暫定・未検証成果
- **内容**：不備のない架空シナリオを書き換えて、生成器の 8 種類の不備が覆わない欠陥や極端な値を作る 36 個の操作（記述子と年次表の食い違い、係数レコードの欠落、段階・単位の誤り、負の値、範囲外の率、一部の項目の NaN と無限大、変則的な事象一覧、段の並びの乱れ、自分自身や互いを基準案にする指定、EPD の申告の食い違いなど）。DECIMAL_BOUNDARIES（評価期間 5 つと周期 14 個：99.9 と 33.3 など）、STAGE_SUBSETS（8 通り。空を含む）、INVALID_PERIODS（0.0、−5.0、NaN、無限大、500.0）も持つ。第1回の検査を受けて作られた。
- **所在**：
  - [`09_APPROX_STUDY/research_code/bench/mutations.py`](../../../09_APPROX_STUDY/research_code/bench/mutations.py)
  - [`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../../09_APPROX_STUDY/research_code/bench/verify_unified.py)
- **確かめ方**：一致確認で、36 種類×4（シード 11・12・13・14、評価期間 60・60・42.5・59.999999）= 144 件、小数境界 5×2 = 10 件、部分集合 8×4 = 32 件に使われ、基準計算と統合モデルの不一致 0。第2回：36 種類すべてで、定義文から書いた独立実装と基準計算の数値・件数が一致（壊し方に関わる違いは、B2-01 の computed が 4 件と、negative_values での C-05 の n_mass_unchecked が 4 と 5）。同じ第2回で、この一覧が覆わない入力の種類が見つかった。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：架空データ。壊し方は規模 S 相当の小さいシナリオ（資材 12 行）に適用された。
- **関係する第2回の指摘**：NUM-1、NUM-2、NUM-3、NUM-4、RED-1
- **第2回の指摘の影響**：一覧が覆わない種類：nan_and_infinite_values は検査で守られた項目（周期、数量 1 つ、漏洩率 1 つ）しか触らない（NUM-2）。年次量・電力係数・係数値・換算倍率の NaN・無限大・負、値 0 でガス別量のある係数（NUM-3）、短い年次表（NUM-4）、周期 1.000000001（NUM-1）、部分集合と不備の組合せ（RED-1）が無い。
- **今の時点で言ってよいこと**：36 種類の壊し方については、基準計算は定義文から書いた独立実装と数値・件数が一致し、統合モデルとも一致した（架空データ、相対 1e-9）。この 36 種類が、起こり得る不備を代表するとは言えない。
- **使ってはいけない記述**：
  - 04_VERIFICATION/README.md 23 行の「36 種類の壊し方」での一致を、不備のある入力一般での一致と読むこと
  - nan_and_infinite_values の合格を、NaN・無限大の入力一般で 2 つの計算が一致する根拠にすること
- **新研究での再利用**：候補（ルート A・C）
  - 使い道：新しいモデルが、不備のある行の除外と件数を固定の基準と同じに返すかを見る入力として使える。小数境界の 5 組は、回数の端の確認に使える。
  - 条件・注意：主な比較は不備のない入力で行い、これは補助にとどめる。壊した入力での基準計算の値は「定義に穴のある動作」を含む（CK-R2-05、CK-R2-07）。65ff124 の 214 種類の版は未検証で、コミット版の基準計算に与えると CK-R2-07 の例外や NaN が出る入力を含む。
- **分類の根拠**：
  - [`09_APPROX_STUDY/research_code/bench/mutations.py`](../../../09_APPROX_STUDY/research_code/bench/mutations.py):293-330（MUTATIONS 36 個）、333-336（DECIMAL_BOUNDARIES、STAGE_SUBSETS、INVALID_PERIODS）、151-163（_nan_inf が触る項目）
  - [`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../../09_APPROX_STUDY/research_code/bench/verify_unified.py):58-75
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):146（CHECKS PERFORMED 1：36 個すべてで一致、違いの一覧）
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):16, 21（NUM-2：研究の NaN の壊し方は守られた項目だけ）
- **分類した観点**：R2（基準計算・架空データ・比較・試験）

<a id="ck-r2-15"></a>

## CK-R2-15　結果の比較の仕組み（common/compare.py）

- **区分**：2　暫定・未検証成果
- **内容**：基準の結果と候補の結果を葉ごとに機械的に比べる関数群。flatten が入れ子の辞書とリストを「経路: 値」に開き、「_」で始まるキーを除く。signed_rel_error は (候補 − 基準) / max(|基準|, floor) で、負が過小評価。compare は数値の葉の最大の相対誤差、符号付きの最小・最大、数値以外の不一致、欠けた葉、余分な葉を返す。within(rel_tol) が合否。percentile は線形補間の百分位。
- **所在**：
  - [`09_APPROX_STUDY/research_code/common/compare.py`](../../../09_APPROX_STUDY/research_code/common/compare.py)
  - [`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../../09_APPROX_STUDY/research_code/bench/verify_unified.py)
  - [`09_APPROX_STUDY/research_code/tests/test_engine.py`](../../../09_APPROX_STUDY/research_code/tests/test_engine.py)
- **確かめ方**：専用の試験は無い（tests に compare.py を対象にした試験は見当たらない）。verify_unified.exactness と tests/test_engine.py の agree が、floor = 1e-9×|SUM-03| を渡して使う。第2回：検査担当が自分の厳密な比較（床なし、無限大・型・余分な葉を検出）で 681 件をやり直し、不一致 0、余分な葉 0。compare の 4 つの弱点を直接の呼び出しで確認（CK-R2-16）。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：比較の道具。架空データ上の基準計算と統合モデルの突き合わせに使われた。
- **関係する第2回の指摘**：NUM-11
- **第2回の指摘の影響**：NUM-11（CONFIRMED、LOW）：無限大と bool の扱い、全葉に掛かる床、合計のみの出力での余分な葉の未検査が指摘された。研究の 681 件では、これらの弱点が隠した差は無かった（床なしの再比較で差 0）。
- **今の時点で言ってよいこと**：研究の 681 シナリオについては、この比較が出した「不一致なし」は、床なし・型に厳密な別の比較でも再現された。比較関数が、あらゆる差を検出するとは言えない。
- **使ってはいけない記述**：
  - 04_VERIFICATION/README.md 21 行「許容差は相対 1e-09」を、床の無い純粋な相対比較と読むこと（実際は全葉に 1e-9×|SUM-03| kgCO2e の床が掛かる。README は床に触れていない）
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：新しいモデルの出力と固定の基準の出力を葉ごとに比べる道具として使える。符号付きの誤差で過小評価を分けて集計できる。
  - 条件・注意：純粋な相対誤差を見るなら floor を 0 にする（既定値は 0。研究の測定は床あり）。基準側が無限大の葉、bool と整数の混同、合計のみの出力での余分な葉は別に検査する（CK-R2-16）。無次元の葉（割合など）に kgCO2e の床を掛けない。
- **分類の根拠**：
  - [`09_APPROX_STUDY/research_code/common/compare.py`](../../../09_APPROX_STUDY/research_code/common/compare.py):13-26（flatten）、29-36（signed_rel_error）、39-52（Comparison、within）、55-94（compare）、97-104（percentile）
  - [`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../../09_APPROX_STUDY/research_code/bench/verify_unified.py):115-130（床の渡し方、合否の条件）
  - [`09_APPROX_STUDY/research_code/tests/test_engine.py`](../../../09_APPROX_STUDY/research_code/tests/test_engine.py):18-25
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):121-131（NUM-11）、134（CHECKS PERFORMED 9、10）
- **分類した観点**：R2（基準計算・架空データ・比較・試験）

<a id="ck-r2-16"></a>

## CK-R2-16　比較の仕組みの既知の弱点（無限大、bool、床、余分な葉）

- **区分**：4　不具合・未解決事項
- **内容**：compare.py と、それを使う一致確認の 4 つの弱点。(1) 基準の葉が ±無限大で候補が NaN 以外なら合格になる（符号付き誤差が NaN になり、abs(err) > max が偽）。(2) True と 1 を等しいとみなす。(3) 一致確認は床 1e-9×|SUM-03| を無次元の葉を含む全葉に掛けるので、床より小さい葉の実効の許容差は相対 1e-9 より緩い。(4) 合計のみの出力の比較は欠けた葉を無視し、余分な葉を調べない。
- **所在**：
  - [`09_APPROX_STUDY/research_code/common/compare.py`](../../../09_APPROX_STUDY/research_code/common/compare.py)
  - [`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../../09_APPROX_STUDY/research_code/bench/verify_unified.py)
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md)
- **確かめ方**：第2回の検査担当と検証者が compare を直接呼んで確認：compare(基準 inf, 候補 1.0)、(inf, −inf)、(−inf, 5.0) は within が真、(1.0, inf) は偽。True と 1 は両方向で真。標準ベンチマーク S（SUM-03 3.295e7、床 0.033）で、0 でない数値の葉 4346 個のうち 19 個が床より小さい。M（床 0.105）で 33208 個のうち 1226 個（3.7％）。値 3.629e-04 の葉を相対 1e-7 変えても合格（報告される誤差 3.45e-10）。
- **確かめた者**：独立検査（第2回）で再現
- **言える範囲**：比較の道具の弱点。研究の 681 件では、床なしの再比較で差 0、余分な葉 0 だったので、記録された一致の結果は変わらない。
- **関係する第2回の指摘**：NUM-11
- **第2回の指摘の影響**：この項目自体が第2回の指摘（CONFIRMED）。
- **今の時点で言ってよいこと**：上の 4 点はコミット版の compare.py と verify_unified.py に残っている。
- **使ってはいけない記述**：
  - compare(...).within(1e-9) が真であることを、無限大や型の違いが無いことの根拠にすること
  - 「許容差は相対 1e-09」を、床より小さい葉にも当てはまると読むこと
- **新研究での再利用**：候補にしない
  - 理由・注意：新研究で compare.py を使うなら、基準側の無限大・NaN、bool の葉、余分な葉を別に検査する。a1 の版は compare を厳しくしたと申告しているが未検証（CK-R2-23）。
- **分類の根拠**：
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):121-131（NUM-11、検証者の確認値）
  - [`09_APPROX_STUDY/research_code/common/compare.py`](../../../09_APPROX_STUDY/research_code/common/compare.py):29-36, 75-91
  - [`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../../09_APPROX_STUDY/research_code/bench/verify_unified.py):120-121, 130
- **分類した観点**：R2（基準計算・架空データ・比較・試験）

<a id="ck-r2-17"></a>

## CK-R2-17　単体試験 28 件（tests/。コミット版）

- **区分**：2　暫定・未検証成果
- **内容**：標準ライブラリ unittest の試験 4 ファイル・28 件（件数はソースの def test_ を数えた値）。test_synth.py 7 件：入力 124 項目の対応、同じ引数で同じシナリオ、JSON の往復、不備なしシナリオの整合、記述子と年次表の一致、不備入りの一覧、集合の規模。test_refcalc.py 8 件：台帳の単位がすべて登録済み、境界条件 32 件の恒等式と検査、標準ベンチマーク S と SUM-08、手計算との照合 1 例、B2 と B6 の振り分け、小数境界、使えない入力の除外と報告、入れた不備の検出。test_closed_forms.py 6 件：閉形式（更新回数、修繕を除く年、直線の和、電力係数のモーメント、冷媒）と基準計算のループの一致を乱数と境界値で。test_engine.py 7 件：統合モデルと基準計算の一致、演算の回数、評価期間の掃引、基準案、無効な評価期間の拒否。
- **所在**：
  - [`09_APPROX_STUDY/research_code/tests/test_synth.py`](../../../09_APPROX_STUDY/research_code/tests/test_synth.py)
  - [`09_APPROX_STUDY/research_code/tests/test_refcalc.py`](../../../09_APPROX_STUDY/research_code/tests/test_refcalc.py)
  - [`09_APPROX_STUDY/research_code/tests/test_closed_forms.py`](../../../09_APPROX_STUDY/research_code/tests/test_closed_forms.py)
  - [`09_APPROX_STUDY/research_code/tests/test_engine.py`](../../../09_APPROX_STUDY/research_code/tests/test_engine.py)
- **確かめ方**：ソースを読んだだけで、今回は実行していない。第2回の報告書の検査担当は、試験 28 件の合格を報告している（反証検査担当の確認は無い。今の環境での合否は確かめていない）。第2回で、試験が拾えなかった欠陥が見つかった。
- **確かめた者**：作成者。合格は、独立検査（第2回）の検査担当 1 者が報告
- **言える範囲**：架空データ。試験は研究の主担当が書いたもので、独立検査の一部ではない。
- **関係する第2回の指摘**：NUM-1、RED-1
- **第2回の指摘の影響**：NUM-1：test_closed_forms.py 26 行が引く周期のずれは 1e-15、1e-12、1e-10、1e-8、1e-6 で、1e-9 が無く、ナイフエッジを拾えなかった。RED-1：段階の部分集合を使う試験（test_refcalc.py 88・93 行）は不備なしだけ。
- **今の時点で言ってよいこと**：28 件の試験がコミットされており、上の内容を検査する。合否は未確認（確認には実行が必要）。試験の合格は、第2回で見つかった欠陥が無いことを意味しない。
- **使ってはいけない記述**：
  - research_code/README.md 18 行の試験の説明（手計算との照合、欠陥の検出、境界条件）を、基準計算の定義どおりの動作が試験で保証されていると読むこと（手計算は 1 例）
  - fastcalc/closed_forms.py の閉形式が「ループと同じ数を返す」ことを、この試験だけを根拠に言うこと（NUM-1）
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：試験が持つ期待値（手計算の例：T=10.5、周期 3.5、冷媒 1 台。小数境界の回数の表）は、固定の基準の受け入れ例として読める。基準計算の恒等式（X-07 の最終値 = SUM-03、X-04 = 14 段階の和、X-08 = B4-02、X-09 = C3-01 + C4-01、B3-01 ≤ B3-02、X-05 ≤ 合計）は、新しいモデルの検査項目になる。
  - 条件・注意：実行するかどうかは新研究の側で決める（この読み取りでは実行していない）。test_closed_forms.py と test_engine.py は旧研究の統合モデル（fastcalc）を対象にする。
- **分類の根拠**：
  - tests/*.py の def test_ の数：test_synth 7、test_refcalc 8、test_closed_forms 6、test_engine 7、計 28（ソースの文字列を数えた）
  - [`09_APPROX_STUDY/research_code/tests/test_refcalc.py`](../../../09_APPROX_STUDY/research_code/tests/test_refcalc.py):29-39（恒等式）、58-83（手計算の例）
  - [`09_APPROX_STUDY/research_code/tests/test_closed_forms.py`](../../../09_APPROX_STUDY/research_code/tests/test_closed_forms.py):18-33（周期の作り方）、80-86
  - [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](../materials/interrupted_fix/agent_reports/A1_REPORT.json)：tests（'Ran 68 tests ... OK' (was 28 tests)）
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):10（検証者：test_closed_forms.py 26 行は 1e-9 を引かない）、rederive.md:150（追記 3）
- **分類した観点**：R2（基準計算・架空データ・比較・試験）
- **停止後の点検による訂正**：点検の指摘 C1-12 により、上の記述の一部を改めた。分類担当の元の記述は `materials/classification/R2.json`、訂正の内容は `materials/classification/overrides.json` にある。

<a id="ck-r7-15"></a>

## CK-R7-15　入力データモデル（Scenario：スカラー欄と表）

- **区分**：2　暫定・未検証成果
- **内容**：基準計算と統合モデルが共通に読む入力だけのデータ構造（dataclass 29 個）。入力仕様 124 項目（12 群）を属性に対応付け、仕様に無い 73 項目を「NEW:」として加えている。表は 資材行・設備行・冷媒機器・係数レコード・燃料・廃棄物・解体活動・搬出・費用項目、スカラーは 建物・境界・運用の比率など。年次量と電力係数は 記述子＋年次表 の両方を持つ。
- **所在**：
  - [`09_APPROX_STUDY/research_code/synth/model.py`](../../../09_APPROX_STUDY/research_code/synth/model.py)
  - [`09_APPROX_STUDY/research_code/synth/io.py`](../../../09_APPROX_STUDY/research_code/synth/io.py)
  - [`09_APPROX_STUDY/04_VERIFICATION/input_usage.json`](../../../09_APPROX_STUDY/04_VERIFICATION/input_usage.json)
- **確かめ方**：124 項目の対応付けは tests/test_synth.py の test_input_coverage が調べる（コミット済み。R7 は実行していない）。読まれた入力項目の実測（33 シナリオ）が input_usage.json にあり、第2回の報告書検査が表の数字（77／56）と JSON の一致を確認。データモデルそのものの独立検査は無い。
- **確かめた者**：作成者のみ
- **言える範囲**：架空データだけ。入力仕様 124 項目は上位の章（03_INPUTS）の独立概念モデルのもの。原版の入力シートとの対応は未確認。
- **関係する第2回の指摘**：REP-1、REP-7、NUM-5、NUM-6、NUM-7、NUM-9、RED-5、RED-10
- **第2回の指摘の影響**：基準計算が実際に読むのは仕様 124 項目のうち 77 と追加項目 73 のうち 56 で、仕様の 47 項目はどの計算にも読まれない。報告書の「0 項目は記録用」は生成器の誤り（REP-1）。台帳の入力一覧（88＋28）は実測と合わない（REP-7）。係数 ID は自由な文字列で、擬似 ID「GRID」「REFRIGERANT」と衝突し得る（NUM-5）。ガスの一覧の重複や CO2 の欠落（NUM-6）、段の添字の型（NUM-7）を検査する仕組みは無い。
- **今の時点で言ってよいこと**：Scenario は meta、project、boundary、gases（7 種）、gwp、unit_conversions（単位の定義 20 行）、provenance、factors、summary_quantities、materials、equipment、refrigerants、construction、operation、water_waste、end_of_life、cost_items、price_index から成り、計算結果を持たない。None は欠損（0 ではない）。年次表は 130 個以上かつ ceil(T) 個以上。
- **使ってはいけない記述**：
  - 04_VERIFICATION/README の「入力仕様 124 項目のうち 0 項目は記録用で、どの計算にも使われない」（REP-1）
  - 台帳・05_DECISIONS の「単位が参照する入力項目 116（既存 88＋追加 28）」を実測として読むこと（REP-7）
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：新研究で基準計算に与える入力の受け口。どの入力が式に効くか（行の表、年の表、スカラー）の一覧として使う。
  - 条件・注意：値はすべて架空。値の範囲や型の検査はモデルに無く、計算側の規則も一部の欄しか見ない（CK-R7-19）。meta は計算が読んではならない欄だが、統合モデルは 1 か所で読む（NUM-9）。65ff124 では model.py が 24 行変わっている（未検証）。
- **分類の根拠**：
  - [`09_APPROX_STUDY/research_code/synth/model.py`](../../../09_APPROX_STUDY/research_code/synth/model.py):672-692（Scenario）、372-401（MaterialRow）、429-473（EquipmentRow、RefrigerantDevice）、513-569（AnnualProfile、GridFactorScenario）、205-226（FactorRecord）
  - [`09_APPROX_STUDY/research_code/synth/model.py`](../../../09_APPROX_STUDY/research_code/synth/model.py):787-924（INPUT_FIELD_MAP：R7 のテキスト集計で 124 項目）、947-1021（EXTRA_FIELD_MAP：73 項目）
  - [`09_APPROX_STUDY/04_VERIFICATION/input_usage.json`](../../../09_APPROX_STUDY/04_VERIFICATION/input_usage.json): inputs_in_specification=124、inputs_added_by_this_study=73、summary.reference_all_units={existing_inputs_read: 77, added_inputs_read: 56}、not_read_by_reference 64 件、what_is_measured（読まれた欄は必要な欄の上限）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):1-6（REP-1）、43-48（REP-7）。REP の指摘には第2検証者が付いていない（主担当が検査のスクリプトを再実行して再現）
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):49-83（NUM-5・NUM-6・NUM-7）
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））

<a id="ck-r7-16"></a>

## CK-R7-16　架空シナリオの生成器と母集団

- **区分**：2　暫定・未検証成果
- **内容**：固定シードの乱数で建物の入力一式を作る make_scenario(seed, structure, use, size_class, study_period=60.0, dirty=False, **options) と、標準ベンチマーク（S・M・L）、検証用の母集団、境界条件 32 件、入力を壊す操作 36 種。構造 4 種×用途 6 種×規模 3 区分（資材行 200／2,000／20,000、設備行 60／600／6,000、冷媒機器 5／40／300）。
- **所在**：
  - [`09_APPROX_STUDY/research_code/synth/generate.py`](../../../09_APPROX_STUDY/research_code/synth/generate.py)
  - [`09_APPROX_STUDY/research_code/synth/population.py`](../../../09_APPROX_STUDY/research_code/synth/population.py)
  - [`09_APPROX_STUDY/research_code/synth/README.md`](../../../09_APPROX_STUDY/research_code/synth/README.md)
  - [`09_APPROX_STUDY/research_code/bench/mutations.py`](../../../09_APPROX_STUDY/research_code/bench/mutations.py)
- **確かめ方**：tests/test_synth.py（7 件：決定性、JSON の往復、記述子と年次表の一致など）がコミット済み。第2回の報告書検査が synth/README の記述（規模、境界条件 32、関数の引数、オプション）とコードの整合、実在の係数表らしい値が無いことを確認。第2回の各検査はこの生成器で作ったシナリオを使った。R7 は README と関数名・定数名だけを読み、本体は読んでいない。
- **確かめた者**：作成者のみ（第2回は説明文との整合と値の性質だけを確認）
- **言える範囲**：すべて架空値（SYNTHETIC_FICTIONAL）。構造・用途・規模の違いはモジュール内の架空の倍率表による。実建物の分布を表さない。
- **関係する第2回の指摘**：NUM-1、NUM-2、RED-1、APP-4、APP-5、APP-8、APP-9、NUM-9
- **第2回の指摘の影響**：生成器が作らない入力があり、そこでの挙動は旧研究の測定に入っていない：周期が評価期間の約数から相対 1e-6 以内（EXACT_DIVISOR 以外。APP-5）、周期 1+1e-9（NUM-1）、負の係数、非有限の年次量・係数（NUM-2）、欠陥のある段階の部分集合（RED-1）。輸送距離は質量と独立に引く（APP-4）。明示の更新年一覧は自分の評価期間の内側だけ（APP-8）。シナリオごとに係数表が別の乱数で作られる。
- **今の時点で言ってよいこと**：同じ引数からは同じシナリオが得られる、という宣言とその試験がコミットされている。規模・構造・用途・オプションの一覧は synth/README と OPTION_HELP にある。
- **使ってはいけない記述**：
  - この母集団での誤差の大きさを実建物の精度として読むこと
  - 「検証した 681 シナリオに無い種類の入力でも同じ結果になる」という推定
- **新研究での再利用**：候補（ルート A・B・C）
  - 使い道：新しい定式化の誤差測定と反例探索の入力に使う候補。母集団のシード（近似の検証は 400 件・シード 20261111・規模 M まで、と第2回の検査記録にある）を固定すれば旧研究の数字と同じ土俵で比べられる。
  - 条件・注意：誤差の分布は生成器の分布で決まる。区分ごとの代表値を使う候補の評価では、標本内（その建物自身の行から作る）か標本外かを区別する（APP-9）。生成器を動かすことは旧研究のコードの実行に当たるので、この確認作業では実行していない。65ff124 では population.py が 5 行、mutations.py が 461 行変わっている（未検証）。
- **分類の根拠**：
  - [`09_APPROX_STUDY/research_code/synth/README.md`](../../../09_APPROX_STUDY/research_code/synth/README.md):6-8,18-32
  - [`09_APPROX_STUDY/research_code/synth/generate.py`](../../../09_APPROX_STUDY/research_code/synth/generate.py):42-53（行数、複合品の割合 0.30、評価期間の上限 300、耐用年数の 5 つのモード）、1335（make_scenario）
  - [`09_APPROX_STUDY/research_code/synth/population.py`](../../../09_APPROX_STUDY/research_code/synth/population.py):17-26,29,54,62,157（ベンチマークのシード、評価期間の候補、BASELINES、attach_baseline、standard_benchmark、verification_population、edge_cases）
  - [`09_APPROX_STUDY/research_code/bench/mutations.py`](../../../09_APPROX_STUDY/research_code/bench/mutations.py):293,333-336（MUTATIONS、DECIMAL_BOUNDARIES、STAGE_SUBSETS、INVALID_PERIODS）
  - [`09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json`](../../../09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json): by_group（benchmark 3、edge 32、population 400、defective 60、mutated 144、decimal 10、stage_subset 32）
  - [`materials/round2_review/triage/approx.md`](../materials/round2_review/triage/approx.md):4,40,57,93,110（母集団のシード、距離と質量の独立、約数の近傍を避ける、明示の一覧の範囲、係数表のばらつき）
  - [`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):128（CHECKS 3・6：README との整合、実在の係数らしい値なし）
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））

<a id="ck-r7-21"></a>

## CK-R7-21　比較の仕組み（結果の leaf ごとの比較、検証の実行、入力を壊す操作）

- **区分**：2　暫定・未検証成果
- **内容**：基準計算の結果と候補の結果を、入れ子の辞書・リストを平らにして leaf ごとに比べる compare()（符号つき相対誤差、過小側を区別）、681 シナリオと評価期間の振り直しを実行する bench/verify_unified.py、入力を壊す 36 種の操作 bench/mutations.py。
- **所在**：
  - [`09_APPROX_STUDY/research_code/common/compare.py`](../../../09_APPROX_STUDY/research_code/common/compare.py)
  - [`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../../09_APPROX_STUDY/research_code/bench/verify_unified.py)
  - [`09_APPROX_STUDY/research_code/bench/mutations.py`](../../../09_APPROX_STUDY/research_code/bench/mutations.py)
  - [`09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json`](../../../09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json)
- **確かめ方**：第2回の数値の反例探しが compare() を直接呼んで性質を調べ、検証者が再現（NUM-11、CONFIRMED）。同じ検査は、下限なし・型に厳密な独自の比較で 681 シナリオをやり直し、隠れた差が無いこと（0 件）も確認した。
- **確かめた者**：独立検査（第2回）で再現（欠点の確認と、実際には差を隠していなかったことの確認）
- **言える範囲**：架空データだけ。43ba5d7 の版のコード。
- **関係する第2回の指摘**：NUM-11、REP-16、NUM-2、RED-1
- **第2回の指摘の影響**：比較関数に欠点がある：基準側が ±無限大だと候補が何でも合格になる、真偽値と整数 1 を等しいとみなす、下限 1e-9×|SUM-03|（kgCO2e）を無次元の leaf を含む全 leaf に掛ける（報告書に記載なし）、合計のみの形式では余分なキーを調べない（NUM-11）。評価期間の振り直しの比較は 70 単位のうち 22 単位の合計だけ、基準案の比較は切って、小さい 64 シナリオで行った（REP-16）。入力を壊す操作は、検査のある欄にしか NaN を入れない（NUM-2）。段階の部分集合のシナリオは欠陥なしだけ（RED-1）。
- **今の時点で言ってよいこと**：compare() は「_」で始まるキーを比較から外し、数値は (候補−基準)/max(|基準|, 下限)、数値でない leaf は等値で比べる。681 シナリオについては、この比較の欠点が差を隠していなかったことが第2回の厳密な再比較で確かめられている。
- **使ってはいけない記述**：
  - 「許容差は相対 1e-9」を、下限なしの純粋な相対誤差として読むこと（NUM-11）
  - 「評価期間を 9 通りに変えた結果を基準計算と突き合わせた（172,404 個）」を全出力についての確認として読むこと（REP-16）
- **新研究での再利用**：候補（ルート A・C）
  - 使い道：新しい定式化と基準計算の結果を比べる道具の候補。過小評価を符号で区別する誤差の定義（負＝過小）と、leaf ごとの比較という方式は、そのまま参照できる。
  - 条件・注意：使うなら、無限大・真偽値・下限・余分なキーの 4 点の扱いを先に決める（第2回の検査担当は、下限なし・型に厳密な比較を別に書いて使った）。65ff124 では compare.py が 13 行、verify_unified.py が 182 行変わっている（自己申告では下限 0 に変更。未検証）。verify_unified.py と mutations.py の本体は R7 は読んでいない（関数名と定数だけ）。
- **分類の根拠**：
  - [`09_APPROX_STUDY/research_code/common/compare.py`](../../../09_APPROX_STUDY/research_code/common/compare.py):13-36,55-94
  - [`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../../09_APPROX_STUDY/research_code/bench/verify_unified.py):41-43（EXACT_TOL=1e-9、SWEEP_PERIODS 9 通り、SWEEP_UNITS）
  - [`09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json`](../../../09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json): tolerance、period_sweep（scenarios 64、units 22 件、values_compared 172404）、mutations
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):121-131（NUM-11）、134（CHECKS 9・10）；[`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):106-111（REP-16。第2検証者なし）
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））

