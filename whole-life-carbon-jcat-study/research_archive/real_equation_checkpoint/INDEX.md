# INDEX — 旧研究（実数方程式の簡素化研究）の成果の索引

- 対象：`whole-life-carbon-jcat-study/09_APPROX_STUDY/`（計算式の簡略化・統合・近似の研究）と、その作業資料
- 作成：2026-11-11。研究の停止を実施した作業担当（Claude Code のセッション）が、読み取り専用の分類担当 7 観点の結果をまとめた
- 関連文書：[STOP_STATUS.md](STOP_STATUS.md)（停止の記録）、[HANDOVER.md](HANDOVER.md)（引継ぎ）、[STOP_ORDER.md](STOP_ORDER.md)（受領した停止指示）

旧研究は 2026-11-11 に**未完成のまま終了**した。この索引は、残った成果を「何が、どこにあり、どこまで確かめてあり、新研究で使えるか」で引けるようにしたものである。
旧研究の `09_APPROX_STUDY/` の本文（README、記録、報告書）は、第2回の独立検査の指摘 59 件を**反映していない**。旧研究の数字や文を使う前に、この索引で状態を確かめること。

## 0. この索引の読み方

### 0.1 作り方と限界

1. 停止後、旧研究のコード（基準計算、統合モデル、測定、試験、生成器）は**一度も実行していない**。分類は、コミット済みのファイルと保存した作業資料を読むことだけで行った。
2. 分類担当は 7 観点（統制文書・台帳・順位／基準計算と架空データ／統合モデル／近似検証／記録と報告書／第2回の指摘の登録簿／再利用の下調べ）で、それぞれ別の AI 作業担当である。全員が「旧研究のコードを実行していない、リポジトリを変更していない」と申告し、分類の後に作業ツリーに変更が無いことを確かめた。
3. したがって、この索引は**記録に何が書いてあるか**の整理である。記録された数値が今の環境で再現するかは確かめていない（確かめるには旧研究の実行が必要で、停止指示が禁じている）。
4. 分類担当が読まなかった範囲は 9 節と [index_detail/NOT_COVERED.md](index_detail/NOT_COVERED.md) にある。
5. 項目の表と詳細は、分類担当が書いた JSON（`materials/classification/`）から機械的に生成した。0 節、1 節、6.1〜6.2 節、8 節、9 節は索引の作成者が書いた。

### 0.2 用語

| 用語 | 意味 |
|---|---|
| 独立概念モデル | 旧研究が調べた計算。公開の規格の考え方に沿って独自に組んだ 70 の評価単位から成る。**原版の表計算の数式を調べたものではなく、互換でも等価でもない** |
| 架空データ | 旧研究の生成器が作った架空の建物の入力。実在の建物や原版の係数・耐用年数・率ではない |
| 基準計算 | 評価単位を定義文どおりに 1 つずつ計算するプログラム（`research_code/refcalc`）。誤差と負荷を測る基準 |
| 統合モデル | 同じ結果を、共有の表と共有の関数 K1〜K7 で求めるプログラム（`research_code/fastcalc`） |
| 第1回・第2回の独立検査 | 研究を作った作業担当とは別の AI 作業担当による検査。第2回は 5 観点の検査担当と、指摘ごとに反証を試みる反証検査担当から成る。**人や外部の機関による査読ではない** |
| 中断した修正 | 第2回の指摘を反映する作業。停止の時点で途中だった。編集はコミット `65ff124` と差分ファイルに残してあり、公開中の版には入っていない |
| 公開中の版 | 現在の `09_APPROX_STUDY/`。コミット `60e720f` と同じ内容に、README 冒頭の終了の注記を加えたもの。コードは `43ba5d7`（第2回の検査が調べた版）と同じ |

### 0.3 区分の定義（停止指示 0-2 の 5 区分）

各項目に、状態の区分 1〜4 を 1 つ付けた。区分 5（再利用候補）は 1〜4 に重ねて付ける印である。

| 区分 | 定義 |
|---|---|
| 1 検証済み成果 | 次の 3 つをすべて満たすもの。(a) 公開中の版に測定または導出の記録がある。(b) 作成した作業担当とは別の検査担当が、少なくとも 1 者、独立に再現または照合した。(c) 第2回の指摘と矛盾しない範囲に文面を狭めてある。**範囲は架空データと独立概念モデルに限る。実建物での精度、原版やほかの道具との一致は意味しない** |
| 2 暫定・未検証成果 | 作られてはいるが、独立の検査を受けていないもの、第2回の指摘の影響が残るもの、中断した修正の自己申告だけのもの、文面の一部に誤りがあると分かっているもの |
| 3 研究途中の数式・仮説 | 式、モデル化の案、保留した近似候補、設計はしたが実装（または検証）していない修正、評価者の提案 |
| 4 不具合・未解決事項 | 分かっている不具合、未解決の問い、限界、行っていない確認 |
| 5 新研究への再利用候補 | 新研究のルート A（保存した簡素化成果を使う）、B（元の式から作り直す）、C（混合）のどれかで使えると分類担当が判断したもの。使う条件を併記した |

迷った項目は、区分 1 ではなく区分 2 にした。区分 1 のうち根拠が比較的弱いもの（検査担当が 1 者だけ、件数の数え直しだけ、など）には「根拠の強さ」の注記を付けた。

### 0.4 件数

| 区分 | 項目数 |
|---|---|
| 1 検証済み成果 | 35 |
| 2 暫定・未検証成果 | 79 |
| 3 研究途中の数式・仮説 | 25 |
| 4 不具合・未解決事項 | 32 |
| 5 新研究への再利用候補（1〜4 と重ねて付ける） | 133 |
| 合計（区分 1〜4） | 171 |
| 別に：第2回の指摘の登録簿 | 59 |

1 つの成果を複数の観点が別の面から扱っている場合がある（例：基準計算は 3 観点に項目がある）。そのため項目数は成果の数より多い。主題ごとのまとまりは 7 節の早見表で引ける。

### 0.5 所在の書き方

- `09_APPROX_STUDY/…`、`01_COMPLIANCE/…` など：`whole-life-carbon-jcat-study/` からの位置
- `materials/…`、`index_detail/…`：この保存フォルダ（`whole-life-carbon-jcat-study/research_archive/real_equation_checkpoint/`）からの位置
- 「コミット `65ff124` の版」：公開中の版には無く、`git show 65ff124:<パス>` で読める中断時の編集

## 1. 最初に知っておくこと

### 1.1 言ってよいこと（区分 1 の要点。すべて架空データ・独立概念モデルの範囲）

| 言ってよいこと | 項目 |
|---|---|
| 架空の 681 シナリオ（数値 7,406,182 個）で、統合モデルは基準計算と相対 1e-9 以内で一致した（実測の最大 4.8e-13）。第2回の検査担当と反証検査担当が、より厳しい比較でやり直して再現した | CK-R3-18、CK-R7-22 |
| 基準計算の 70 単位は、台帳の定義文とコードの説明文が同じ文面である。うち 53 単位は、定義文と規約文だけから独立に書き直した計算と、119 の架空シナリオで相対 1e-9 以内で一致した（表示・件数の 4 点を除く） | CK-R2-01、CK-R1-09、CK-R7-17、CK-R7-01 |
| 評価単位の依存関係は 183 辺で、閉路が無い | CK-R7-02 |
| 式の変形として成り立つ構造：行から（表、係数キー）への合算と係数との積和（線形）、回数関数 N(T,c)＝ceil(T/c)−1（端の規約つき）、年重み付き和（等差級数と 2 乗和）、補充なしの冷媒の等比、建替・指標の一次式。第2回の検査担当が、自作の逐次計算との総当たりで確かめた（周期で与える修繕の除外年の閉形式は反例が 1 点あり、区分 2） | CK-R3-01、CK-R3-09、CK-R3-10、CK-R3-12〜16、CK-R7-23 |
| 行の合算を 1 回行えば、別の評価期間の結果を乗数の計算だけで求められる（150 シナリオ×20 期間などで基準計算と一致） | CK-R3-19 |
| 近似候補のうち、更新回数の連続近似（AP-01〜03）、修繕の更新年除外の無視（AP-04）、複合係数の構成材の切り捨て（AP-07a・b）、評価期間についての直線補間（AP-14）、CO2 のみでの代用（AP-22a）は、架空の母集団で目標（段階 2％・合計 1％）を外れた。不採用は成り立つ | CK-R4-04、CK-R4-05、CK-R4-09、CK-R4-19、CK-R4-20、CK-R4-22、CK-R7-26 |
| 架空の標準ベンチマーク S・M で、統合モデルが実行した命令数は基準計算より少なかった（全出力で 54.2％・63.6％、合計のみで 67.6％・72.6％ の減） | CK-R3-20 |
| 旧研究が決めた規約 B-1〜B-21 のうち 15 件は、但し書きなしでコードと合う | CK-R7-28 |
| 台帳・記録・進捗台帳・報告書の件数と相互参照は、同じ版の JSON と合っている（内容が正しいことの確認ではない） | CK-R1-05、CK-R5-01、CK-R5-11 |

### 1.2 使ってはいけない記述（旧研究の文書に残っているもの）

| 旧研究の文書にある記述 | 実際 | 関係する指摘 |
|---|---|---|
| 「統合モデルは、どの入力でも基準計算と同じ結果を返す」「不備のある入力でも同じ値・同じ不備を返す」 | 一致を確かめたのは 681 の架空シナリオの範囲。周期が倍精度の 1.000000001 のとき修繕（B3-01）が最大約 92％ 食い違うほか、検査のない項目の NaN・無限大などで食い違う | NUM-1〜11、REC-1 |
| 「66 単位が 7 つの統合モデルにまとまった」「計算の定義の数 70 → 11」 | 数え方に異論があり、合意した数え直しは無い（記録の検査は約 62〜63 単位、報告書の検査はさらに少ないとする）。**数として引用しない** | REC-2、REP-4 |
| 「不完全な結果には必ず印が付く」 | 一部の段階だけを対象にした境界では、上流の行を除いても `complete` が真のままになる（例で合計が最大 62.8％ 減っても印なし） | RED-1、RED-5 |
| 「負の値や範囲外の値は、その行を除いて数える」 | 年次量、電力係数、係数の値、換算倍率は検査なしで使われる | RED-2、RED-3 |
| 「成功の記録は 3 つの裏付けを持つ。無ければ生成が失敗する」 | 成功 118 件のうち 3 つがそろうのは 96 件。仕組みの確認に使った計数の一部は、失敗し得ない位置に置いた集計である | REC-4、REC-5、REP-3 |
| 「記録用の入力は 0 項目」「入力は 116 種類で同じ」 | 入力仕様 124 項目のうち 47 項目はどの計算にも読まれない。台帳の入力一覧は申告で、実際に読む入力と合わない | REP-1、REP-7 |
| 「全単位を対象に近似を調べた」 | 近似の段階 280（単位×段階）のうち 204 は測定なしの判断。「保留あり」44 単位のうち 21 単位は建物全体の代理モデル 1 件だけによる | REP-5 |
| 近似の誤差表の「B6 段階」「合計への影響」「厳密な式が同じ手間で使えるため不採用」 | 「B6 段階」は B6-03（B6＋B2）に対する値。「合計への影響」は下流への波及を含まない。手間は測っていない | APP-2、APP-3、REP-6 |
| 手順書 v1.4 の改訂履歴の「定めた」規則（厳密な有理数の時間規則、故障注入による所属の確認など） | 本文にも公開中のコードにも入っていない。草稿であることは文書の中に書かれていない（コミットの説明だけ） | — |
| コミット `65ff124`（中断した修正）の数字 | 作業担当の自己申告だけで、独立の検査は無い。作業ツリー全体としての試験結果も無い | — |

### 1.3 基準計算には 2 つの版がある

| 版 | 所在 | 状態 |
|---|---|---|
| 公開中の版 | `09_APPROX_STUDY/research_code/refcalc/`（`43ba5d7` と同じ） | 公開済みの測定・記録・報告書はすべてこの版に対応する。第2回の検査が調べた版。定義の穴（5.2 節の群 1・2）を持つ |
| 中断した修正の版 | コミット `65ff124` | 時間の判定、不正な値の扱い、完全性の印、50 単位の定義文を変える。**未検証**。公開済みの測定・記録・報告書と対応しない |

新研究の基準計算は**公開中の版**とし、変更しない（[HANDOVER.md](HANDOVER.md) の 4 節）。

## 2. 区分 1：検証済み成果

ここでの「検証済み」は、0.3 の定義を満たすものだけである。どの項目も、**架空データ**と**独立概念モデル**の範囲に限り、下の「言ってよいこと」の文面に狭めてある。旧研究の文書にある元の文面のうち使ってはいけないものは、詳細の「使ってはいけない記述」に挙げた。

### 評価単位の台帳・シート族・依存関係（T02）

**[CK-R1-05](index_detail/T02_ledger.md#ck-r1-05)　台帳・順位表・自動生成の報告の、数と相互参照の整合（数え直しで一致した範囲）**

- 言ってよいこと：次の数と対応は、第2回の検査の数え直しと合っている。(1) 評価単位 70 件（既存 53、追加 17）。既存 53 件の ID と名称は 04_FORMULAS/formulas.json と同じ。(2) 入力の申告を数えた値は 116 種類（入力仕様の 88、NEW: を付けたもの 28）。(3) 198 シート、59 シート族（数式を持つ族 41）、数式ノード 3,818,483。02_SOURCES の一覧と同じ。状態別の族数 24・9・11・15 とノード数 3,708,176・79,260・31,047・0 は、付いている表示を数えた値。(4) 未接続の入力 53 項目の内訳 30・14・9、評価単位にしなかったもの 7 件。(5) units.json の sheet_family_links と sheet_family_coverage.json の対応の不一致 0（70 単位）。depends_on・feeds は基準計算の登録簿と同じ。(6) 軸 A・軸 B・優先スコア・着手順・着手群は入力から再計算して差 0。README の表（軸 A の 700 個の値、軸 B の 70 行、着手順の 70 行）は JSON と同じ。research_priority.json と progress_ledger.json の順序・群の不一致 0。(7) 自動生成の README 6 点は再生成した内容と同じで、古い生成物ではない。
- 確かめた者：独立検査（第2回）で再現
- 根拠の強さ：件数と相互参照の数え直しだけである。内容が正しいことの確認ではない。数え直したのは第2回の検査担当 1 者。
- 所在：[`09_APPROX_STUDY/01_LEDGER/units.json`](../../09_APPROX_STUDY/01_LEDGER/units.json)、[`09_APPROX_STUDY/01_LEDGER/sheet_families.json`](../../09_APPROX_STUDY/01_LEDGER/sheet_families.json)、[`09_APPROX_STUDY/01_LEDGER/sheet_family_coverage.json`](../../09_APPROX_STUDY/01_LEDGER/sheet_family_coverage.json)　ほか 6
- 使ってはいけない記述：3 件（詳細を参照）　／　再利用：A・B・C

**[CK-R1-09](index_detail/T02_ledger.md#ck-r1-09)　基準定義 reference_semantics：文面と基準計算の説明文の一致、文面からの再導出**

- 言ってよいこと：70 単位すべてで、台帳の reference_semantics は 43ba5d7 の基準計算の関数の説明文と同じ文面である。53 単位は、定義文と規約の説明文だけから独立に書き直した計算が、119 の架空シナリオで基準計算と相対 1e-9 以内で合った。文面とコードの動作が合わない箇所、文面が動作を書いていない箇所は CK-R1-10 のとおりである。
- 確かめた者：独立検査（第1回）、独立検査（第2回）で再現
- 根拠の強さ：文面の一致は検査担当 2 者。書き直しとの一致は検査担当 1 者の報告で、反証検査担当はこの一致をやり直していない。
- 所在：[`09_APPROX_STUDY/01_LEDGER/units.json`](../../09_APPROX_STUDY/01_LEDGER/units.json)、[`09_APPROX_STUDY/research_code/refcalc/`](../../09_APPROX_STUDY/research_code/refcalc)
- 使ってはいけない記述：6 件（詳細を参照）　／　再利用：A・B・C

**[CK-R7-01](index_detail/T02_ledger.md#ck-r7-01)　台帳の束縛欄（70 単位の id・段階・基準定義文・依存）**

- 言ってよいこと：70 単位すべてで、台帳の reference_semantics は基準計算（43ba5d7 の版）の関数の説明文と同じ文字列、depends_on は登録の宣言と同じ、feeds は depends_on の逆引きである。
- 確かめた者：独立検査（第2回）で再現
- 所在：[`09_APPROX_STUDY/01_LEDGER/units.json`](../../09_APPROX_STUDY/01_LEDGER/units.json)、[`09_APPROX_STUDY/research_code/tools/sync_ledger.py`](../../09_APPROX_STUDY/research_code/tools/sync_ledger.py)、[`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py)　ほか 2
- 使ってはいけない記述：3 件（詳細を参照）　／　再利用：A・B・C

**[CK-R7-02](index_detail/T02_ledger.md#ck-r7-02)　評価単位の依存グラフ（depends_on）**

- 言ってよいこと：台帳の depends_on（183 辺）は基準計算の宣言と同じで、閉路が無い。主な流れ：A13-02→X-15、A13-05・X-15→A13-01／A13-03→A13-04；A1-A3・A4・C の行結果→B3-01・B4-02・B5-01；B6-04・X-06→B6-01→B6-03・B2-01；B7-01〜03→B7-04；B1-02→B1-03・B1-04；29 単位→X-02→SUM-01・SUM-02・SUM-03、SUM-03→SUM-04〜08；X-04→QA-01・QA-03；SYS-04→QA-04。
- 確かめた者：独立検査（第2回）で再現
- 所在：[`09_APPROX_STUDY/01_LEDGER/units.json`](../../09_APPROX_STUDY/01_LEDGER/units.json)、[`09_APPROX_STUDY/research_code/refcalc/registry.py`](../../09_APPROX_STUDY/research_code/refcalc/registry.py)、[`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py)　ほか 2
- 使ってはいけない記述：3 件（詳細を参照）　／　再利用：A・B・C

### 基準計算と規約（T04）

**[CK-R2-01](index_detail/T04_reference_calculation.md#ck-r2-01)　基準計算の本体（70 評価単位の逐次計算。誤差と負荷を測る基準）**

- 言ってよいこと：コミット 60e720f の基準計算は、架空の 119 シナリオで、定義文と規約文だけから独立に書き直した 53 単位の実装と、数値と件数が相対 1e-9 以内で一致した（例外は checked_how に記した 4 点：表示 2、印 1、負の廃棄質量を入れた壊し方での C-05 の件数 1）。X-04・X-05・SUM-08 は 50 シナリオで間接的に一致した。70 単位すべてで台帳の定義文と関数の説明文は同文である。不備のない架空シナリオについて、基準計算は書かれた定義どおりに計算する、と言える範囲はここまで。
- 確かめた者：独立検査（第2回）で再現
- 根拠の強さ：書き直しとの一致は第2回の検査担当 1 者の報告で、反証検査担当はこの一致をやり直していない。
- 所在：[`09_APPROX_STUDY/research_code/refcalc/__init__.py`](../../09_APPROX_STUDY/research_code/refcalc/__init__.py)、[`09_APPROX_STUDY/research_code/refcalc/base.py`](../../09_APPROX_STUDY/research_code/refcalc/base.py)、[`09_APPROX_STUDY/research_code/refcalc/registry.py`](../../09_APPROX_STUDY/research_code/refcalc/registry.py)　ほか 4
- 使ってはいけない記述：5 件（詳細を参照）　／　再利用：A・B・C

**[CK-R2-02](index_detail/T04_reference_calculation.md#ck-r2-02)　時間の規約（事象の数え方、年への割り当て、許容幅 1e-9）**

- 言ってよいこと：コミット版の基準計算は、内側の判定 τ < T×(1 − 1e-9) と年の割り当て max(1, ceil(τ×(1 − 1e-9))) を、B1・B3・B4・B5・X-07・X-10・QA-02 で同じ関数から使う。小数境界の 5 組と非整数の評価期間では、規約文から書いた独立実装と回数・年が一致した（第2回、架空データ）。
- 確かめた者：独立検査（第2回）で再現
- 根拠の強さ：独立実装との一致は第2回の検査担当 1 者の報告。試験の合否は停止後に確かめていない。
- 所在：[`09_APPROX_STUDY/research_code/refcalc/base.py`](../../09_APPROX_STUDY/research_code/refcalc/base.py)、[`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../09_APPROX_STUDY/research_code/refcalc/units_b.py)、[`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py)　ほか 3
- 使ってはいけない記述：3 件（詳細を参照）　／　再利用：A・B・C

**[CK-R7-17](index_detail/T04_reference_calculation.md#ck-r7-17)　基準計算（refcalc）のうち、定義文からの独立した書き直しと一致した 53 単位**

- 言ってよいこと：第2回の検査担当が定義文と規約の説明だけから書き直した実装と、基準計算の 53 単位（A13-01、A13-02、A13-03、A13-04、A13-05、A4-01、A4-02、A5-01、A5-02、A5-03、A5-04、B1-01、B1-02、B1-03、B1-04、B2-01、B3-01、B3-02、B4-01、B4-02、B4-03、B5-01、B6-01、B6-02、B6-03、B6-04、B7-01、B7-02、B7-03、B7-04、C-05、C1-01、C2-01、C3-01、C4-01、QA-02、SUM-01、SUM-02、SUM-03、SUM-04、SUM-05、SUM-06、SUM-07、X-01、X-02、X-06、X-07、X-10、X-12、X-13、X-14、X-15、X-16）の数値・件数は、119 架空シナリオ（境界条件、欠陥入り、入力を壊す操作 36 種、小数の境界、段階の部分集合を含む）で相対 1e-9 以内で一致した。差は 4 点だけ：X-15 が未解決の行に付ける印、B2-01 の computed（入力を壊した 4 件）、SUM-07 が未定義のときの出力、C-05 の n_mass_unchecked（負の廃棄質量）。これは「コードが定義文どおりに計算している」ことの確認で、定義そのものの穴（CK-R7-19）や、この 119 件に無い入力での挙動を覆うものではない。
- 確かめた者：独立検査（第2回）で再現
- 根拠の強さ：書き直しとの一致は第2回の検査担当 1 者の報告で、反証検査担当はこの一致をやり直していない。
- 所在：[`09_APPROX_STUDY/research_code/refcalc/base.py`](../../09_APPROX_STUDY/research_code/refcalc/base.py)、[`09_APPROX_STUDY/research_code/refcalc/registry.py`](../../09_APPROX_STUDY/research_code/refcalc/registry.py)、[`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py)　ほか 3
- 使ってはいけない記述：4 件（詳細を参照）　／　再利用：A・B・C

**[CK-R7-28](index_detail/T04_reference_calculation.md#ck-r7-28)　本研究が決めた規約 B-1〜B-21 のうち、第2回でコードとの符合が確認されたもの**

- 言ってよいこと：但し書きなしでコードと合うと報告されたのは 15 件：B-1（T は実数、最終年を按分）、B-2（n×周期<T だけ数える）、B-3（事象は属する年に置く）、B-4（更新が属する年は修繕なし）、B-5（冷媒の交換は年末に反映）、B-6（B1-04 は B1 段階）、B-7（建替で更新周期を初期化しない）、B-8（更新・建替も初期と同じ係数）、B-9（未数量分は r/(1−r) の上乗せ）、B-10（B2 は買電排出の定率、B2 が対象のときだけ B6 から引く）、B-12（ガスの範囲はラベル、合計は全ガス）、B-13（経路比率の合計が 1 未満は未配分）、B-14（EPD の適用条件）、B-19（質量収支は据付量と比べる）、B-20（年次量の単位は「単位/year」だけ）。影響の数字：B-7 は境界条件の例（T=60、建替周期 25、範囲比 1.0）で更新 31 回→19 回、B4 −40.6％、合計 −1.9％。B-10 は B2 が標準ベンチマーク S の SUM-02 の 7.0％。B-11 は A4 の 0.12％、A5 の 5.0％。
- 確かめた者：独立検査（第2回）で再現
- 根拠の強さ：コードとの照合は第2回の検査担当 1 者。
- 所在：[`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md)、[`09_APPROX_STUDY/research_code/refcalc/base.py`](../../09_APPROX_STUDY/research_code/refcalc/base.py)
- 使ってはいけない記述：3 件（詳細を参照）　／　再利用：A・B・C

### 統合モデル K1〜K7 と導出（T06）

**[CK-R3-01](index_detail/T06_unified_models.md#ck-r3-01)　全体の形：排出＝Σ（活動量×係数）、評価期間への依存は乗数だけ**

- 言ってよいこと：独立概念モデルの排出と集計の単位は、(a) 行から（表、係数キー）への活動量の合算、(b) 係数との積和、(c) T と周期・事象年・漏洩率などで決まる乗数、に分けて書ける。行の合算は T に依存しない。この形で書いた統合モデルは、架空の 681 シナリオで基準計算と相対 1e-9 以内で一致した（第2回の検査で再現）。
- 確かめた者：独立検査（第2回）で再現
- 所在：[`09_APPROX_STUDY/03_MODELS/README.md`](../../09_APPROX_STUDY/03_MODELS/README.md)、[`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md)、[`09_APPROX_STUDY/research_code/fastcalc/engine.py`](../../09_APPROX_STUDY/research_code/fastcalc/engine.py)
- 使ってはいけない記述：4 件（詳細を参照）　／　再利用：A・C

**[CK-R3-02](index_detail/T06_unified_models.md#ck-r3-02)　統合モデル K1 行テーブル**

- 言ってよいこと：A13-01、A13-03、A13-04、X-01、A4-01、A4-02、A5-02、A5-03、C1-01、C2-01、C3-01、C4-01、X-14、X-12、X-16、STO-02、A5-04、B7-04、X-17、X-09、X-02、X-04、X-05 の 23 単位は、値が共有の表の読み出し（またはその和）から得られ、架空の 681 シナリオで基準計算と相対 1e-9 以内で一致する。ただし A5-04・B7-04・STO-02・X-17 は基準計算と計算の中身が変わっていない。
- 確かめた者：独立検査（第2回）で再現
- 所在：[`09_APPROX_STUDY/03_MODELS/models.json`](../../09_APPROX_STUDY/03_MODELS/models.json)、[`09_APPROX_STUDY/03_MODELS/README.md`](../../09_APPROX_STUDY/03_MODELS/README.md)、[`09_APPROX_STUDY/research_code/fastcalc/engine.py`](../../09_APPROX_STUDY/research_code/fastcalc/engine.py)
- 使ってはいけない記述：4 件（詳細を参照）　／　再利用：A・C

**[CK-R3-03](index_detail/T06_unified_models.md#ck-r3-03)　統合モデル K2 回数関数とライフサイクル乗数**

- 言ってよいこと：B4-02、B5-01、X-08、X-10、B3-02、B4-01（事象の件数）は、回数関数と周期別の合算から得られ、架空の 681 シナリオで基準計算と一致する。B3-01 も 681 シナリオでは一致する。B4-03 は全出力のときだけ行別の回数を出す。
- 確かめた者：独立検査（第2回）で再現
- 所在：[`09_APPROX_STUDY/03_MODELS/models.json`](../../09_APPROX_STUDY/03_MODELS/models.json)、[`09_APPROX_STUDY/research_code/fastcalc/engine.py`](../../09_APPROX_STUDY/research_code/fastcalc/engine.py)、[`09_APPROX_STUDY/research_code/fastcalc/closed_forms.py`](../../09_APPROX_STUDY/research_code/fastcalc/closed_forms.py)
- 使ってはいけない記述：5 件（詳細を参照）　／　再利用：A・C

**[CK-R3-05](index_detail/T06_unified_models.md#ck-r3-05)　統合モデル K4 充填サイクルの質量収支**

- 言ってよいこと：B1-02、B1-03、B1-04 の合計は充填サイクルの閉形式から得られ、架空の 681 シナリオで基準計算と一致する。
- 確かめた者：独立検査（第2回）で再現
- 所在：[`09_APPROX_STUDY/03_MODELS/models.json`](../../09_APPROX_STUDY/03_MODELS/models.json)、[`09_APPROX_STUDY/research_code/fastcalc/engine.py`](../../09_APPROX_STUDY/research_code/fastcalc/engine.py)、[`09_APPROX_STUDY/research_code/fastcalc/closed_forms.py`](../../09_APPROX_STUDY/research_code/fastcalc/closed_forms.py)
- 使ってはいけない記述：3 件（詳細を参照）　／　再利用：A・C

**[CK-R3-07](index_detail/T06_unified_models.md#ck-r3-07)　統合モデル K6 許容差つきの残差判定**

- 言ってよいこと：SYS-04、QA-04、QA-01 は 1 つの判定関数を共有し、架空の 681 シナリオで基準計算と同じ合否を返す。
- 確かめた者：独立検査（第2回）で再現
- 所在：[`09_APPROX_STUDY/03_MODELS/models.json`](../../09_APPROX_STUDY/03_MODELS/models.json)、[`09_APPROX_STUDY/research_code/fastcalc/engine.py`](../../09_APPROX_STUDY/research_code/fastcalc/engine.py)
- 使ってはいけない記述：2 件（詳細を参照）　／　再利用：—

**[CK-R3-09](index_detail/T06_unified_models.md#ck-r3-09)　導出 D1 行テーブル（和の順序の入れ替え）**

- 言ってよいこと：Σ_i a_i·v_{k(i)}＝Σ_k A_k·v_k は実数の演算での恒等式である。同じ A に係数の別の列を掛けると、ガス別内訳と CO2 のみの結果が得られる。
- 確かめた者：独立検査（第2回）で再現
- 所在：[`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md)、[`09_APPROX_STUDY/research_code/fastcalc/engine.py`](../../09_APPROX_STUDY/research_code/fastcalc/engine.py)
- 使ってはいけない記述：2 件（詳細を参照）　／　再利用：A・C

**[CK-R3-10](index_detail/T06_unified_models.md#ck-r3-10)　導出 D2 回数関数 N(T,c) と周期ごとの合算**

- 言ってよいこと：N(T,c) は T と c だけの関数で、端の規約（評価期間の終わりちょうどの事象を数えない、許容幅 1e-9）を除けば ceil(T/c)−1 である。更新の排出は周期ごとの合算 U_c に N を掛けた和に等しく、U_c は T に依存しない。統合モデルの回数は、第2回の総当たりの範囲で基準計算の数え上げと 1 件も違わなかった。
- 確かめた者：独立検査（第2回）で再現
- 所在：[`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md)、[`09_APPROX_STUDY/research_code/fastcalc/closed_forms.py`](../../09_APPROX_STUDY/research_code/fastcalc/closed_forms.py)、[`09_APPROX_STUDY/research_code/tests/test_closed_forms.py`](../../09_APPROX_STUDY/research_code/tests/test_closed_forms.py)
- 使ってはいけない記述：2 件（詳細を参照）　／　再利用：A・B・C

**[CK-R3-12](index_detail/T06_unified_models.md#ck-r3-12)　導出 D4 建替・大型改修**

- 言ってよいこと：B5＝N(T,C)·φ·（初期段階の和）。回数関数は更新と同じ N。架空の 681 シナリオで基準計算と一致する。
- 確かめた者：独立検査（第2回）で再現（読み比べと全体の一致による。専用の総当たりなし）
- 根拠の強さ：コードとの読み比べと全体の一致による。専用の総当たりはしていない。
- 所在：[`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md)、[`09_APPROX_STUDY/research_code/fastcalc/engine.py`](../../09_APPROX_STUDY/research_code/fastcalc/engine.py)
- 使ってはいけない記述：1 件（詳細を参照）　／　再利用：A・C

**[CK-R3-13](index_detail/T06_unified_models.md#ck-r3-13)　導出 D5 年次量の年重み付き和（一定・直線）**

- 言ってよいこと：一定・直線の年次量の年重み付き和は b·T＋s·((Y−2)(Y−1)/2＋w_Y·(Y−1)) に等しい。第2回の総当たり 120,000 件で、年ごとのループとの差は最大 1.9e-13 だった。
- 確かめた者：独立検査（第2回）で再現
- 所在：[`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md)、[`09_APPROX_STUDY/research_code/fastcalc/closed_forms.py`](../../09_APPROX_STUDY/research_code/fastcalc/closed_forms.py)
- 使ってはいけない記述：1 件（詳細を参照）　／　再利用：A・C

**[CK-R3-14](index_detail/T06_unified_models.md#ck-r3-14)　導出 D5 電力係数の区間とモーメント G・H、買電排出 B·G＋S·H**

- 言ってよいこと：整った記述子の電力係数は年の添字について区分的に直線で、G と H は区間ごとの等差級数と 2 乗和の公式で求まる。買電量が直線で両端が 0 以上なら、買電排出＝B·G＋S·H。有限で整った記述子と通常の大きさの値では、基準計算の年ごとの計算と一致した（681 シナリオと第2回の総当たり）。
- 確かめた者：独立検査（第2回）で再現
- 所在：[`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md)、[`09_APPROX_STUDY/research_code/fastcalc/closed_forms.py`](../../09_APPROX_STUDY/research_code/fastcalc/closed_forms.py)、[`09_APPROX_STUDY/research_code/fastcalc/engine.py`](../../09_APPROX_STUDY/research_code/fastcalc/engine.py)
- 使ってはいけない記述：3 件（詳細を参照）　／　再利用：A・C

**[CK-R3-15](index_detail/T06_unified_models.md#ck-r3-15)　導出 D6 冷媒の充填サイクル（等比の閉形式）**

- 言ってよいこと：補充しない機器の j 年の漏洩は m·(1−(1−r)^j)、毎年補充する機器は m0·r·T。第2回の総当たり 190,000 件で、年ごとのループとの不一致は見つからなかった。
- 確かめた者：独立検査（第2回）で再現
- 所在：[`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md)、[`09_APPROX_STUDY/research_code/fastcalc/closed_forms.py`](../../09_APPROX_STUDY/research_code/fastcalc/closed_forms.py)
- 使ってはいけない記述：2 件（詳細を参照）　／　再利用：A・C

**[CK-R3-16](index_detail/T06_unified_models.md#ck-r3-16)　導出 D7 指標と残差判定**

- 言ってよいこと：指標は段階ベクトルの一次式か比であり、段階の値が一致すれば指標も一致する。
- 確かめた者：独立検査（第2回）で再現（読み比べと全体の一致による）
- 根拠の強さ：コードとの読み比べと全体の一致による。専用の総当たりはしていない。
- 所在：[`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md)、[`09_APPROX_STUDY/research_code/fastcalc/engine.py`](../../09_APPROX_STUDY/research_code/fastcalc/engine.py)
- 使ってはいけない記述：1 件（詳細を参照）　／　再利用：A・B・C

**[CK-R7-23](index_detail/T06_unified_models.md#ck-r7-23)　厳密な閉形式のうち、第2回の総当たりで基準のループと食い違わなかったもの**

- 言ってよいこと：renewal_count は、基準計算と同じ判定式で前後を確かめるので、数え上げと同じ回数を返す（数学的には ceil(T/c)−1、許容幅 1e-9 を除く）。linear_weighted_sum は Σ_k w_{k+1}(b＋s·k)=b·T＋s·((Y−2)(Y−1)/2＋w_Y·(Y−1))。segment_moments は G=Σ w·g と H=Σ w·k·g を区間ごとの等差・平方和で求める。refrigerant_fractions は交換から交換までを m·(1−(1−r)^j) で求める。これらは上の件数の総当たりで、逐次ループと丸めの範囲で一致した（モーメントだけは T が整数の直上で桁落ちし、1.08e-9〜5.2e-8 の差が出る）。
- 確かめた者：独立検査（第2回）で再現
- 所在：[`09_APPROX_STUDY/research_code/fastcalc/closed_forms.py`](../../09_APPROX_STUDY/research_code/fastcalc/closed_forms.py)、[`09_APPROX_STUDY/research_code/tests/test_closed_forms.py`](../../09_APPROX_STUDY/research_code/tests/test_closed_forms.py)、[`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md)
- 使ってはいけない記述：3 件（詳細を参照）　／　再利用：A・C

### 厳密一致・負荷・入力の測定と反例（T07）

**[CK-R3-18](index_detail/T07_exactness_load.md#ck-r3-18)　厳密一致の測定（681 シナリオ、数値 7,406,182 個、許容差 相対 1e-9）**

- 言ってよいこと：架空の 681 シナリオ（生成器が作る整った入力、生成器の不備 60 件、壊し方 36 種、小数の端 5 組、段階の部分集合 8 通り）では、統合モデルの全出力と合計のみの出力が、基準計算と相対 1e-9 以内（実測の最大 4.8e-13）で一致する。第2回の検査担当 2 者が床なしの比較で再現した。
- 確かめた者：独立検査（第2回）で再現
- 所在：[`09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json`](../../09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json)、[`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../09_APPROX_STUDY/04_VERIFICATION/README.md)、[`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../09_APPROX_STUDY/research_code/bench/verify_unified.py)
- 使ってはいけない記述：5 件（詳細を参照）　／　再利用：A・B・C

**[CK-R3-19](index_detail/T07_exactness_load.md#ck-r3-19)　評価期間の掃引（1 回の合算から別の評価期間の結果を求める）**

- 言ってよいこと：統合モデルは、行の合算を 1 回行えば、別の評価期間の結果を乗数の計算だけで求められる。第2回の検査で、150 シナリオ×20 期間と、全単位での 8 シナリオ×9 期間について、期間ごとに最初から計算した基準計算と一致した。
- 確かめた者：独立検査（第2回）で再現
- 所在：[`09_APPROX_STUDY/research_code/fastcalc/engine.py`](../../09_APPROX_STUDY/research_code/fastcalc/engine.py)、[`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../09_APPROX_STUDY/research_code/bench/verify_unified.py)、[`09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json`](../../09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json)
- 使ってはいけない記述：2 件（詳細を参照）　／　再利用：A・C

**[CK-R3-20](index_detail/T07_exactness_load.md#ck-r3-20)　負荷の測定：実行した命令数（規模 S・M、基準計算・全出力・合計のみ）**

- 言ってよいこと：架空の標準ベンチマーク S・M で、統合モデルが実行した命令数は基準計算より全出力で 54.2％・63.6％、合計のみで 67.6％・72.6％ 少なかった。第2回の検査担当が命令数を数え直して一致した。
- 確かめた者：独立検査（第2回）で再現（反証担当なし）
- 根拠の強さ：数え直したのは報告書の検査担当 1 者。反証検査担当は付いていない。
- 所在：[`09_APPROX_STUDY/04_VERIFICATION/unified_model_load.json`](../../09_APPROX_STUDY/04_VERIFICATION/unified_model_load.json)、[`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../09_APPROX_STUDY/04_VERIFICATION/README.md)、[`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../09_APPROX_STUDY/research_code/bench/verify_unified.py)
- 使ってはいけない記述：2 件（詳細を参照）　／　再利用：A・B・C

**[CK-R7-22](index_detail/T07_exactness_load.md#ck-r7-22)　681 架空シナリオでの基準計算と統合モデルの一致（記録された測定）**

- 言ってよいこと：この 681 シナリオでは、統合モデルの 2 形式は基準計算と相対 1e-9 以内で一致し（記録の最大 4.77e-13）、第2回の厳密な再比較でも差は 0 だった。
- 確かめた者：独立検査（第2回）で再現
- 所在：[`09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json`](../../09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json)、[`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../09_APPROX_STUDY/04_VERIFICATION/README.md)、[`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../09_APPROX_STUDY/research_code/bench/verify_unified.py)
- 使ってはいけない記述：2 件（詳細を参照）　／　再利用：A・C

### 近似検証（M3〜M6）（T08）

**[CK-R4-04](index_detail/T08_approximation.md#ck-r4-04)　更新回数の連続近似（AP-01・AP-02・AP-03）と上下限（AP-20）**

- 言ってよいこと：架空の母集団では、3 つの連続近似はどれも段階 2％・合計 1％ の目標を大きく外れる（AP-01 は 77.5％ のシナリオで過小で最大 -58.5％、AP-03 は常に過大で平均 +95.6％、AP-02 は符号が定まらない）。上下限 AP-20 は母集団の 400 件すべてを含むが、幅が B4 の平均 114.2％ あり推定値の代わりにならない。不採用の結論は第2回でも支持された。
- 確かめた者：独立検査（第2回）で再現（B4、B5、X-10 の資源量、AP-20 の幅と上下限を 1e-15 以下の差で再現）
- 所在：[`09_APPROX_STUDY/03_MODELS/candidates.json`](../../09_APPROX_STUDY/03_MODELS/candidates.json)、[`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)、[`09_APPROX_STUDY/research_code/bench/approx_study.py`](../../09_APPROX_STUDY/research_code/bench/approx_study.py)　ほか 1
- 使ってはいけない記述：3 件（詳細を参照）　／　再利用：A・B・C

**[CK-R4-05](index_detail/T08_approximation.md#ck-r4-05)　修繕の更新年除外を無視する形（AP-04）**

- 言ってよいこと：架空の母集団で AP-04 は常に過大（安全側）で、B3 段階の最大 +5.4％ は段階 2％ の目標を超える。この理由による不採用は成り立つ。
- 確かめた者：独立検査（第2回）で再現（近似の検査担当、反証検査担当、報告書の検査担当がそれぞれ再計算し、件数・平均・95％点・最大・最小・合計の 95％点・構造別の平均が一致）
- 所在：[`09_APPROX_STUDY/03_MODELS/candidates.json`](../../09_APPROX_STUDY/03_MODELS/candidates.json)、[`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)、[`09_APPROX_STUDY/research_code/bench/approx_study.py`](../../09_APPROX_STUDY/research_code/bench/approx_study.py)　ほか 1
- 使ってはいけない記述：1 件（詳細を参照）　／　再利用：A・B・C

**[CK-R4-09](index_detail/T08_approximation.md#ck-r4-09)　複合係数の構成材の切り捨て（AP-07a・AP-07b）**

- 言ってよいこと：架空の母集団では、質量比 5％ 未満の構成材を落とすと複合品の製造排出が最大 -20.2％（補正なし）、-14.7％〜+7.5％（補正あり）ずれ、段階 2％ の目標を超える。補正なしは常に過小。不採用は成り立つ。
- 確かめた者：独立検査（第2回）で再現
- 所在：[`09_APPROX_STUDY/03_MODELS/candidates.json`](../../09_APPROX_STUDY/03_MODELS/candidates.json)、[`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)、[`09_APPROX_STUDY/research_code/bench/approx_study.py`](../../09_APPROX_STUDY/research_code/bench/approx_study.py)　ほか 1
- 使ってはいけない記述：1 件（詳細を参照）　／　再利用：A・B・C

**[CK-R4-19](index_detail/T08_approximation.md#ck-r4-19)　評価期間についての直線補間（AP-14）**

- 言ってよいこと：架空の 80 シナリオで、評価期間についての直線補間は合計を -11.9％〜+22.8％ ずらす（研究の記録では、更新が評価期間の途中で段差を作るため）。合計 1％ の目標を大きく超え、不採用は成り立つ。
- 確かめた者：独立検査（第2回）で再現（検査担当と反証検査担当がそれぞれ同じ値を得た）
- 所在：[`09_APPROX_STUDY/03_MODELS/candidates.json`](../../09_APPROX_STUDY/03_MODELS/candidates.json)、[`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)、[`09_APPROX_STUDY/research_code/bench/approx_study.py`](../../09_APPROX_STUDY/research_code/bench/approx_study.py)
- 使ってはいけない記述：2 件（詳細を参照）　／　再利用：A・B・C

**[CK-R4-20](index_detail/T08_approximation.md#ck-r4-20)　全ガスの合計を CO2 のみの合計で代用する（AP-22a）**

- 言ってよいこと：架空の母集団で、CO2 のみの合計は全ガスの合計を常に下回り、平均 -12.2％、最大 -32.4％。不採用は成り立つ。
- 確かめた者：独立検査（第2回）で再現（近似の検査担当と報告書の検査担当がそれぞれ基準計算から再計算）
- 所在：[`09_APPROX_STUDY/03_MODELS/candidates.json`](../../09_APPROX_STUDY/03_MODELS/candidates.json)、[`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)、[`09_APPROX_STUDY/research_code/bench/approx_study.py`](../../09_APPROX_STUDY/research_code/bench/approx_study.py)
- 使ってはいけない記述：1 件（詳細を参照）　／　再利用：A・B・C

**[CK-R4-22](index_detail/T08_approximation.md#ck-r4-22)　誤差の符号が式から決まる候補（片側にしか外れない近似）の一覧**

- 言ってよいこと：上の一覧の符号は、係数が非負で、端材率が 0 より大きく 1 未満で、周期が相対 1e-9 の境界の外にある入力について成り立ち、架空の母集団の測定でも例外は無かった。AP-01 と AP-20 の下限は相対 1e-9 の許容差つきで成り立つ。
- 確かめた者：独立検査（第2回）で再現
- 所在：[`09_APPROX_STUDY/03_MODELS/candidates.json`](../../09_APPROX_STUDY/03_MODELS/candidates.json)、[`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)、[`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md)　ほか 1
- 使ってはいけない記述：2 件（詳細を参照）　／　再利用：A・B・C

**[CK-R7-26](index_detail/T08_approximation.md#ck-r7-26)　近似候補の誤差測定のうち、第2回の独立した再実装で統計値が再現した 27 件（反例として）**

- 言ってよいこと：母集団 400 件（シード 20261111、規模 M まで）の架空シナリオで、27 候補（AP-01、AP-02、AP-03、AP-04、AP-05、AP-06、AP-07a、AP-07b、AP-08、AP-09a、AP-09b、AP-09c、AP-17、AP-18a、AP-18b、AP-18c、AP-18、AP-19a、AP-19b、AP-20、AP-22a、AP-10、AP-10b、AP-11、AP-21、AP-22b、AP-14）の誤差の統計値は、第2回の独立した再実装で再現した。符号についての解析的な主張のうち、AP-03・AP-04・AP-05・AP-19b が常に過大、AP-06・AP-07a・AP-22a が常に過小であることは、第2回が解析と数値の両方で確認した。
- 確かめた者：独立検査（第2回）で再現
- 所在：[`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)、[`09_APPROX_STUDY/03_MODELS/candidates.json`](../../09_APPROX_STUDY/03_MODELS/candidates.json)、[`09_APPROX_STUDY/research_code/bench/approx_study.py`](../../09_APPROX_STUDY/research_code/bench/approx_study.py)
- 使ってはいけない記述：5 件（詳細を参照）　／　再利用：A・B・C

### 記録・進捗台帳・報告書・必須成果物（T09）

**[CK-R5-01](index_detail/T09_records_reports.md#ck-r5-01)　記録・進捗台帳・報告書の件数と相互参照の整合（数え直しで一致した範囲）**

- 言ってよいこと：09_APPROX_STUDY の自動生成の報告書は、同じ版（43ba5d7）の JSON から再生成したものと一致する（古い報告書が残っているのではない）。records/units.json と progress_ledger.json はどちらも 454 件で、候補・結論・理由・段階の結論に不一致 0。models.json・記録・進捗台帳の所属に不一致 0。research_priority.json と進捗台帳の着手順・群に不一致 0。70 単位の状態は、記録から P10 の規則どおりに求めた値（統合成功 66、簡略化成功 3、保留 1）と同じである。
- 確かめた者：独立検査（第2回）で再現
- 根拠の強さ：件数と相互参照の数え直しだけである。内容が正しいことの確認ではない。
- 所在：[`09_APPROX_STUDY/03_MODELS/records/units.json`](../../09_APPROX_STUDY/03_MODELS/records/units.json)、[`09_APPROX_STUDY/05_DECISIONS/progress_ledger.json`](../../09_APPROX_STUDY/05_DECISIONS/progress_ledger.json)、[`09_APPROX_STUDY/05_DECISIONS/PROGRESS.md`](../../09_APPROX_STUDY/05_DECISIONS/PROGRESS.md)　ほか 4
- 使ってはいけない記述：2 件（詳細を参照）　／　再利用：A・C

**[CK-R5-11](index_detail/T09_records_reports.md#ck-r5-11)　README の要点 1「評価単位は 70 件（53＋17）。全件を研究対象にした」**

- 言ってよいこと：台帳には 70 単位が登録されている（既存の概念式 53、追加で特定した計算構造 17）。上位 30％ による絞り込みは行わず、70 単位すべてに M1〜M6 の結論を記録した。これらは独立概念モデルの単位であり、原版の数式を調べたものではない。
- 確かめた者：独立検査（第2回）で再現（件数という記録上の事実の数え直し）
- 根拠の強さ：件数の数え直しだけである。数え直したのは第2回の検査担当 1 者。
- 所在：[`09_APPROX_STUDY/README.md`](../../09_APPROX_STUDY/README.md)、[`09_APPROX_STUDY/01_LEDGER/units.json`](../../09_APPROX_STUDY/01_LEDGER/units.json)、[`09_APPROX_STUDY/05_DECISIONS/progress_ledger.json`](../../09_APPROX_STUDY/05_DECISIONS/progress_ledger.json)
- 使ってはいけない記述：2 件（詳細を参照）　／　再利用：A・B・C

**[CK-R5-17](index_detail/T09_records_reports.md#ck-r5-17)　README の要点 7「材料・用途・構造の違いは式に現れず、データの違いとして扱う（設計上）」**

- 言ってよいこと：独立概念モデルは、材料・用途・構造の違いを式ではなく行（数量と係数）というデータの違いとして表すように設計されている。評価期間と、周期で与えられる更新・修繕・建替の条件は、乗数の関数の引数になる。原版に工種別・用途別の式があるかどうかは、調べていない。
- 確かめた者：独立検査（第1回）の指摘で表現を是正。独立検査（第2回）で否定されず
- 根拠の強さ：設計についての記述であり、測定の結果ではない。
- 所在：[`09_APPROX_STUDY/README.md`](../../09_APPROX_STUDY/README.md)、[`09_APPROX_STUDY/03_MODELS/README.md`](../../09_APPROX_STUDY/03_MODELS/README.md)、[`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md)
- 使ってはいけない記述：3 件（詳細を参照）　／　再利用：A・B・C

## 3. 区分 2：暫定・未検証成果

作られてはいるが、独立の検査を受けていないもの、第2回の指摘の影響が残るもの、中断した修正の自己申告だけのもの、文面の一部に誤りがあると分かっているもの。**検証済みとして扱わない。**

### 統制文書と手順書（T01）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R1-01](index_detail/T01_policy_protocol.md#ck-r1-01) | **指示書の写し 2 点（開発方針指示書、追加・変更指示 第1号）**<br>2026-11-11 に受領した指示書 2 点を、第9章の統制文書として保存した写し。研究の成果ではなく、旧研究が従った指示の記録である。追加・変更指示 第1号は「2 軸それぞれの上位 30％ だけを研究対象にする」制限を撤廃し、2 軸の評価を着手順序の決定だけに使うと定めた。 | [`09_APPROX_STUDY/00_POLICY/DIRECTIVE.md`](../../09_APPROX_STUDY/00_POLICY/DIRECTIVE.md)<br>[`09_APPROX_STUDY/00_POLICY/DIRECTIVE_AMENDMENT_01.md`](../../09_APPROX_STUDY/00_POLICY/DIRECTIVE_AMENDMENT_01.md) | 作成者のみ | — |
| [CK-R1-02](index_detail/T01_policy_protocol.md#ck-r1-02) | **研究プロトコル EVALUATION_PROTOCOL.md（v1.4 草稿。使われた規則と草稿の部分）**<br>指示書 2 点を、評価単位の定義（P2）、台帳の様式（P3）、軸 A（P4）、軸 B（P5）、着手順序（P6）、検証手順（P7）、6 段階の検討（P8）、進捗台帳の 6 状態（P10）に落とした手書きの手順書。 | [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md) | 独立検査（第2回）で再現（P4〜P6 と P10 の計算規則だけ）。v1.4 の差分は作成者のみ | A・B・C |

### 評価単位の台帳・シート族・依存関係（T02）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R1-06](index_detail/T02_ledger.md#ck-r1-06) | **評価単位の一覧（70 件＝既存の概念式 53＋追加で特定した計算構造 17）**<br>独立概念モデルの固有の計算構造を 1 件ずつ登録した台帳。53 件は第4章の概念式で、ID をそのまま使う。17 件（X-01〜X-17）は、シート名と数式ノード数、式に未接続の入力項目、既存資料の記述から旧研究が推定した独立設計の案である。 | [`09_APPROX_STUDY/01_LEDGER/units.json`](../../09_APPROX_STUDY/01_LEDGER/units.json)<br>[`09_APPROX_STUDY/01_LEDGER/README.md`](../../09_APPROX_STUDY/01_LEDGER/README.md)<br>ほか 1 | 作成者のみ（件数・ID・依存関係の整合だけ 独立検査（第2回）で再現） | A・B・C |
| [CK-R1-07](index_detail/T02_ledger.md#ck-r1-07) | **構造分類と形式の記述（structure_class 13 種、正規形、反復、分岐、計算量）**<br>各単位に付けた数学的な構造の分類（structure_class）、副分類、正規形の記号式（canonical_form）、反復の次元（loop_dims）、分岐（branches）、計算量（complexity）。分析時の判断として書かれたもので、測定ではない。 | [`09_APPROX_STUDY/01_LEDGER/units.json`](../../09_APPROX_STUDY/01_LEDGER/units.json)<br>[`09_APPROX_STUDY/01_LEDGER/README.md`](../../09_APPROX_STUDY/01_LEDGER/README.md) | 作成者のみ | B・C |
| [CK-R1-12](index_detail/T02_ledger.md#ck-r1-12) | **単位ごとの入力の申告（inputs 欄、全体で 116 種類＝既存 88＋仮置き 28）**<br>各単位の inputs 欄（必要な入力変数の申告）と n_inputs。入力仕様（03_INPUTS、124 項目）の ID か、仕様にないものは「NEW:」を付けた名前で書かれている。70 単位を合わせると 116 種類（仕様の 88、NEW: 28）。分析時の申告であって、測定ではない。 | [`09_APPROX_STUDY/01_LEDGER/units.json`](../../09_APPROX_STUDY/01_LEDGER/units.json)<br>[`09_APPROX_STUDY/01_LEDGER/README.md`](../../09_APPROX_STUDY/01_LEDGER/README.md)<br>ほか 2 | 独立検査（第2回）で再現（件数と、実測との食い違い） | — |
| [CK-R1-13](index_detail/T02_ledger.md#ck-r1-13) | **式に未接続だった入力 53 項目の扱い（記録用 30、追加単位で接続 14、既存式が暗黙に使用 9）**<br>既存の対応台帳で、どの式にも接続していなかった入力 53 項目を 3 つに分けた表。METADATA_ONLY（記録用、計算に使わない）30、NEEDS_NEW_UNIT（追加単位で接続）14、IMPLICIT_IN_EXISTING（既存式が暗黙に使用）9。 | [`09_APPROX_STUDY/01_LEDGER/unlinked_input_disposition.json`](../../09_APPROX_STUDY/01_LEDGER/unlinked_input_disposition.json)<br>[`09_APPROX_STUDY/01_LEDGER/README.md`](../../09_APPROX_STUDY/01_LEDGER/README.md)<br>ほか 1 | 独立検査（第2回）で再現（件数と、実測との食い違い） | — |
| [CK-R1-14](index_detail/T02_ledger.md#ck-r1-14) | **シート族の集計（198 シートを名称だけで 59 族に整理。数式ノード 3,818,483）**<br>第2章が記録した 198 シートの一覧（シート名、表示状態、数式 XML ノード数）を、シート名の正規化（末尾の _GHG・_CO2、空白、(2)・(3) の添字などを除く）だけで 59 のシート族に整理した表。数式を持つ族は 41。数式ノードの合計は 3,818,483。 | [`09_APPROX_STUDY/01_LEDGER/sheet_families.json`](../../09_APPROX_STUDY/01_LEDGER/sheet_families.json)<br>[`09_APPROX_STUDY/01_LEDGER/README.md`](../../09_APPROX_STUDY/01_LEDGER/README.md)<br>ほか 1 | 作成者のみ（集計の数だけ 独立検査（第2回）で再現） | B・C |
| [CK-R1-15](index_detail/T02_ledger.md#ck-r1-15) | **シート族と評価単位の対応の表示（名称だけからの推定。状態 4 区分）**<br>59 のシート族それぞれに、関連すると推定した評価単位（related_units）と状態を付けた表。 | [`09_APPROX_STUDY/01_LEDGER/sheet_family_coverage.json`](../../09_APPROX_STUDY/01_LEDGER/sheet_family_coverage.json)<br>[`09_APPROX_STUDY/01_LEDGER/README.md`](../../09_APPROX_STUDY/01_LEDGER/README.md)<br>ほか 1 | 作成者のみ（参照の整合だけ 独立検査（第2回）で再現） | — |
| [CK-R7-03](index_detail/T02_ledger.md#ck-r7-03) | **台帳の分析欄（構造分類 13 種・標準形・分岐・未定義点）**<br>各単位に付けた structure_class（13 種）、structure_subclass、canonical_form、loop_dims、branches、complexity、similar_units、unification_potential、approximation_potential、ambiguities と、分析担当の定義案 reference_semantics_proposal（29 件… | [`09_APPROX_STUDY/01_LEDGER/units.json`](../../09_APPROX_STUDY/01_LEDGER/units.json)<br>[`09_APPROX_STUDY/01_LEDGER/README.md`](../../09_APPROX_STUDY/01_LEDGER/README.md) | 作成者のみ | B・C |

### 着手順序（評価軸 A・B）（T03）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R1-17](index_detail/T03_ranking.md#ck-r1-17) | **評価軸 A：基準計算の単位別の負荷の測定と A スコア**<br>独立に実装した基準計算を架空の標準ベンチマーク（規模 S・M・L）で実行し、70 単位ごとに実行時間、実行したバイトコード命令数、ピークメモリを測った値と、それに台帳から数えた 4 指標を加えた 7 指標の百分位の重み付き和（A スコア）による順位。 | [`09_APPROX_STUDY/02_RANKING/axis_a_measurements.json`](../../09_APPROX_STUDY/02_RANKING/axis_a_measurements.json)<br>[`09_APPROX_STUDY/02_RANKING/axis_a.json`](../../09_APPROX_STUDY/02_RANKING/axis_a.json)<br>ほか 3 | 作成者のみ（測定値）。スコアと順位の計算だけ 独立検査（第2回）で再現 | A・B・C |
| [CK-R1-18](index_detail/T03_ranking.md#ck-r1-18) | **評価軸 B：3 つの自動評価による採点（8 観点×0〜3 点）**<br>3 つの自動評価（AI エージェント。観点は代数的統合、数値近似、入力・データモデル削減）が、評価単位の事実だけをまとめた資料（axis_b_input_digest.json）を読み、指示書の 8 観点（b1〜b8）を各 0〜3 点で採点したもの。 | [`09_APPROX_STUDY/02_RANKING/axis_b.json`](../../09_APPROX_STUDY/02_RANKING/axis_b.json)<br>[`09_APPROX_STUDY/02_RANKING/axis_b_judges/`](../../09_APPROX_STUDY/02_RANKING/axis_b_judges)<br>ほか 3 | 作成者のみ（採点）。集計の計算だけ 独立検査（第2回）で再現 | — |
| [CK-R1-20](index_detail/T03_ranking.md#ck-r1-20) | **着手順序（優先スコア、着手群 3 つ、旧・上位 30％ の参考表示）**<br>優先スコア ＝ 0.35×軸 B の百分位 ＋ 0.30×統合観点（b2＋b3＋b4＋b8）の百分位 ＋ 0.35×軸 A の百分位 の高い順に 70 単位を並べ、3 つの着手群（24・24・22 件）に分けたもの。研究対象の絞り込みには使わず、着手の順番だけを示す。 | [`09_APPROX_STUDY/02_RANKING/research_priority.json`](../../09_APPROX_STUDY/02_RANKING/research_priority.json)<br>[`09_APPROX_STUDY/02_RANKING/README.md`](../../09_APPROX_STUDY/02_RANKING/README.md)<br>ほか 1 | 作成者のみ（入力）。計算だけ 独立検査（第2回）で再現 | — |
| [CK-R3-22](index_detail/T03_ranking.md#ck-r3-22) | **評価軸 A の単位別の負荷測定（測り方）**<br>bench/measure_axis_a.py。 | [`09_APPROX_STUDY/research_code/bench/measure_axis_a.py`](../../09_APPROX_STUDY/research_code/bench/measure_axis_a.py) | 作成者のみ（第2回は順位の計算の照合だけ） | — |

### 基準計算と規約（T04）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R2-04](index_detail/T04_reference_calculation.md#ck-r2-04) | **完全性の印（X-02 の complete・incomplete_units、SUM-01〜03 の complete）**<br>X-02 が、対象段階ごとに手書きの表 STAGE_UNITS に載っている単位を見て、n_skipped・n_routes_skipped・n_partial が 1 以上、または computed が偽の単位を incomplete_units に挙げ、1 つでもあれば complete を偽にする。 | [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py)<br>[`09_APPROX_STUDY/research_code/refcalc/base.py`](../../09_APPROX_STUDY/research_code/refcalc/base.py)<br>ほか 2 | 独立検査（第2回）で再現 | A・C |
| [CK-R2-06](index_detail/T04_reference_calculation.md#ck-r2-06) | **使えない係数と不正な値の扱い（除外して数える規則。実装されている範囲）**<br>係数は、レコードがあり、使用許諾が PERMITTED_PUBLIC で、対象段階が使う段階と完全に同じで、単位が一致するか直接の換算が登録されているときだけ使う（base.lookup）。 | [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../09_APPROX_STUDY/research_code/refcalc/base.py)<br>[`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py)<br>ほか 3 | 独立検査（第2回）で再現 | A・C |
| [CK-R2-08](index_detail/T04_reference_calculation.md#ck-r2-08) | **規約の一覧（06_OPEN_ISSUES の B-1〜B-21 と base.py 冒頭の規約文）**<br>基準計算が、概念式の決めていない点をどう定めたかの一覧。 | [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md)<br>[`09_APPROX_STUDY/research_code/refcalc/base.py`](../../09_APPROX_STUDY/research_code/refcalc/base.py) | 独立検査（第2回）で再現 | A・B・C |
| [CK-R7-18](index_detail/T04_reference_calculation.md#ck-r7-18) | **基準計算のうち、独立した書き直しがない 14 単位と、間接的な確認だけの 3 単位**<br>第2回の再導出検査が定義文から書き直さなかった 14 単位（QA-01、QA-03、QA-04、STO-01、STO-02、SYS-01、SYS-02、SYS-03、SYS-04、X-03、X-08、X-09、X-11、X-17）と、間接的な方法でだけ確かめた 3 単位（X-04、X-05、SUM-08）。 | [`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py)<br>[`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../09_APPROX_STUDY/research_code/refcalc/units_b.py)<br>ほか 2 | 作成者のみ（第2回は読み比べと間接的な確認） | A・B・C |

### 架空データ・比較の仕組み・試験（T05）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R2-11](index_detail/T05_synthetic_data_harness.md#ck-r2-11) | **架空シナリオのデータ構造（synth/model.py と JSON の入出力）**<br>架空の建物シナリオの入力側だけを持つデータ構造（dataclass 29 個。 | [`09_APPROX_STUDY/research_code/synth/model.py`](../../09_APPROX_STUDY/research_code/synth/model.py)<br>[`09_APPROX_STUDY/research_code/synth/io.py`](../../09_APPROX_STUDY/research_code/synth/io.py)<br>ほか 2 | 作成者のみ | A・B・C |
| [CK-R2-12](index_detail/T05_synthetic_data_harness.md#ck-r2-12) | **架空シナリオの生成器（synth/generate.py の make_scenario）**<br>make_scenario(seed, structure, use, size_class, study_period=60.0, dirty=False, **options)。固定シードの乱数（節ごとに独立した部分列）で架空シナリオを 1 つ作る。 | [`09_APPROX_STUDY/research_code/synth/generate.py`](../../09_APPROX_STUDY/research_code/synth/generate.py)<br>[`09_APPROX_STUDY/research_code/synth/README.md`](../../09_APPROX_STUDY/research_code/synth/README.md)<br>ほか 1 | 作成者のみ | A・B・C |
| [CK-R2-13](index_detail/T05_synthetic_data_harness.md#ck-r2-13) | **架空シナリオの集合（標準ベンチマーク S・M・L、検証用の母集団、境界条件 32 件、基準案の登録）**<br>standard_benchmark()：RC・office・T=60 の規模 S・M・L（シード 101・102・103）の 3 件で、それぞれに基準案の写し（電力・ガス 15％ 増、発電なし、資材 10 行に 1 行の数量 20％ 増）を付ける。 | [`09_APPROX_STUDY/research_code/synth/population.py`](../../09_APPROX_STUDY/research_code/synth/population.py)<br>[`09_APPROX_STUDY/research_code/synth/README.md`](../../09_APPROX_STUDY/research_code/synth/README.md)<br>ほか 1 | 作成者のみ | A・B・C |
| [CK-R2-14](index_detail/T05_synthetic_data_harness.md#ck-r2-14) | **入力を壊す操作（bench/mutations.py：36 種類の壊し方、小数境界、段階の部分集合、無効な評価期間）**<br>不備のない架空シナリオを書き換えて、生成器の 8 種類の不備が覆わない欠陥や極端な値を作る 36 個の操作（記述子と年次表の食い違い、係数レコードの欠落、段階・単位の誤り、負の値、範囲外の率、一部の項目の NaN と無限大、変則的な事象一覧、段の並びの乱れ、自分自身や互いを基準案にする指定、EPD の申告の食い違いなど）。 | [`09_APPROX_STUDY/research_code/bench/mutations.py`](../../09_APPROX_STUDY/research_code/bench/mutations.py)<br>[`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../09_APPROX_STUDY/research_code/bench/verify_unified.py) | 独立検査（第2回）で再現 | A・C |
| [CK-R2-15](index_detail/T05_synthetic_data_harness.md#ck-r2-15) | **結果の比較の仕組み（common/compare.py）**<br>基準の結果と候補の結果を葉ごとに機械的に比べる関数群。flatten が入れ子の辞書とリストを「経路: 値」に開き、「_」で始まるキーを除く。signed_rel_error は (候補 − 基準) / max(\|基準\|, floor) で、負が過小評価。 | [`09_APPROX_STUDY/research_code/common/compare.py`](../../09_APPROX_STUDY/research_code/common/compare.py)<br>[`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../09_APPROX_STUDY/research_code/bench/verify_unified.py)<br>ほか 1 | 独立検査（第2回）で再現 | A・B・C |
| [CK-R2-17](index_detail/T05_synthetic_data_harness.md#ck-r2-17) | **単体試験 28 件（tests/。コミット版）**<br>標準ライブラリ unittest の試験 4 ファイル・28 件（件数はソースの def test_ を数えた値）。test_synth.py 7 件：入力 124 項目の対応、同じ引数で同じシナリオ、JSON の往復、不備なしシナリオの整合、記述子と年次表の一致、不備入りの一覧、集合の規模。 | [`09_APPROX_STUDY/research_code/tests/test_synth.py`](../../09_APPROX_STUDY/research_code/tests/test_synth.py)<br>[`09_APPROX_STUDY/research_code/tests/test_refcalc.py`](../../09_APPROX_STUDY/research_code/tests/test_refcalc.py)<br>ほか 2 | 作成者のみ | A・B・C |
| [CK-R7-15](index_detail/T05_synthetic_data_harness.md#ck-r7-15) | **入力データモデル（Scenario：スカラー欄と表）**<br>基準計算と統合モデルが共通に読む入力だけのデータ構造（dataclass 29 個）。入力仕様 124 項目（12 群）を属性に対応付け、仕様に無い 73 項目を「NEW:」として加えている。 | [`09_APPROX_STUDY/research_code/synth/model.py`](../../09_APPROX_STUDY/research_code/synth/model.py)<br>[`09_APPROX_STUDY/research_code/synth/io.py`](../../09_APPROX_STUDY/research_code/synth/io.py)<br>ほか 1 | 作成者のみ | A・B・C |
| [CK-R7-16](index_detail/T05_synthetic_data_harness.md#ck-r7-16) | **架空シナリオの生成器と母集団**<br>固定シードの乱数で建物の入力一式を作る make_scenario(seed, structure, use, size_class, study_period=60.0, dirty=False, **options) と、標準ベンチマーク（S・M・L）、検証用の母集団、境界条件 32 件、入力を壊す操作 36 種。 | [`09_APPROX_STUDY/research_code/synth/generate.py`](../../09_APPROX_STUDY/research_code/synth/generate.py)<br>[`09_APPROX_STUDY/research_code/synth/population.py`](../../09_APPROX_STUDY/research_code/synth/population.py)<br>ほか 2 | 作成者のみ（第2回は説明文との整合と値の性質だけを確認） | A・B・C |
| [CK-R7-21](index_detail/T05_synthetic_data_harness.md#ck-r7-21) | **比較の仕組み（結果の leaf ごとの比較、検証の実行、入力を壊す操作）**<br>基準計算の結果と候補の結果を、入れ子の辞書・リストを平らにして leaf ごとに比べる compare()（符号つき相対誤差、過小側を区別）、681 シナリオと評価期間の振り直しを実行する bench/verify_unified.py、入力を壊す 36 種の操作 bench/mutations.py。 | [`09_APPROX_STUDY/research_code/common/compare.py`](../../09_APPROX_STUDY/research_code/common/compare.py)<br>[`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../09_APPROX_STUDY/research_code/bench/verify_unified.py)<br>ほか 2 | 独立検査（第2回）で再現（欠点の確認と、実際には差を隠していなかったことの確認） | A・C |

### 統合モデル K1〜K7 と導出（T06）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R3-04](index_detail/T06_unified_models.md#ck-r3-04) | **統合モデル K3 年重み付き和（区分的に直線な系列のモーメント）**<br>年ごとの積算を、一定・直線の年次量の和の公式と、区分的に直線な電力係数のモーメント G＝Σ w_y·g_y、H＝Σ w_y·k·g_y に置き換える形。買電排出は打ち切りが働かないとき B·G＋S·H。 | [`09_APPROX_STUDY/03_MODELS/models.json`](../../09_APPROX_STUDY/03_MODELS/models.json)<br>[`09_APPROX_STUDY/research_code/fastcalc/engine.py`](../../09_APPROX_STUDY/research_code/fastcalc/engine.py)<br>ほか 1 | 独立検査（第2回）で再現（所属の主張は弱められた） | A・C |
| [CK-R3-06](index_detail/T06_unified_models.md#ck-r3-06) | **統合モデル K5 指標（段階ベクトルの線形関数）**<br>アップフロント・エンボディド・ホールライフ・原単位・割合・基準案との差を、段階ベクトルの部分和と尺度（1、面積、面積×年数、1000、合計）による除算で求める形。公表の所属は 8 単位（SUM-01〜SUM-08）。 | [`09_APPROX_STUDY/03_MODELS/models.json`](../../09_APPROX_STUDY/03_MODELS/models.json)<br>[`09_APPROX_STUDY/research_code/fastcalc/engine.py`](../../09_APPROX_STUDY/research_code/fastcalc/engine.py) | 独立検査（第2回）で再現（統合としての主張は弱められた） | A・B・C |
| [CK-R3-08](index_detail/T06_unified_models.md#ck-r3-08) | **統合モデル K7 係数解決の表**<br>行ごとに繰り返していた係数の検索、適用可否の判定、単位換算、複合係数の算出を相異なる組の数だけに減らし、検査（単位・段階・参照・使用係数）も同じ表から読む、という形。式は「係数・対象段階・単位の組ごとに 1 回解決。複合係数 Σ(質量比×換算×係数) は配合の内容ごとに 1 回」。 | [`09_APPROX_STUDY/03_MODELS/models.json`](../../09_APPROX_STUDY/03_MODELS/models.json)<br>[`09_APPROX_STUDY/research_code/fastcalc/engine.py`](../../09_APPROX_STUDY/research_code/fastcalc/engine.py) | 独立検査（第2回）で再現（記述の一部は否定された） | A・C |
| [CK-R3-11](index_detail/T06_unified_models.md#ck-r3-11) | **導出 D3 修繕の除外年の重み**<br>修繕は、更新が属する年を除いた年について e0·r·w_y を足す。除外する年の集合を S とすると Σ_{y∉S} w_y＝T−Σ_{y∈S} w_y。周期 c の更新では、c≥1 なら事象ごとに年が違い（S の年の数＝事象の数）、c＜1 なら年 1 から最後の事象の年までがすべて入る、とする。 | [`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md)<br>[`09_APPROX_STUDY/research_code/fastcalc/closed_forms.py`](../../09_APPROX_STUDY/research_code/fastcalc/closed_forms.py)<br>ほか 1 | 独立検査（第2回）で再現（反例 1 点が確認された） | A・C |
| [CK-R3-17](index_detail/T06_unified_models.md#ck-r3-17) | **導出 D8 係数解決と複合係数**<br>ある係数を、ある段階の、ある単位の活動量に使えるかどうかと換算倍率は（係数、段階、単位）の組だけで決まるので、1 回だけ解決して覚えておけばよい、という記述。単位と段階の検査（SYS-02）、参照の検査（SYS-03）、使用した係数の検査（QA-03）はこの解決の結果から読める、とする。 | [`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md)<br>[`09_APPROX_STUDY/research_code/fastcalc/engine.py`](../../09_APPROX_STUDY/research_code/fastcalc/engine.py) | 独立検査（第2回）で再現（記述の一部が否定された） | A・C |
| [CK-R3-26](index_detail/T06_unified_models.md#ck-r3-26) | **厳密な簡略化・統合の「成功」記録 118 件の裏付けの表示**<br>03_MODELS/records/units.json の、M1（厳密な簡略化）52 件と M2（厳密な統合）66 件の成功の記録。注記は「成功は、出力の一致・仕組みの計数・導出の 3 つに裏付けがあるものだけ（裏付けがなければ生成が失敗する）」と書く。 | [`09_APPROX_STUDY/03_MODELS/records/units.json`](../../09_APPROX_STUDY/03_MODELS/records/units.json)<br>[`09_APPROX_STUDY/03_MODELS/README.md`](../../09_APPROX_STUDY/03_MODELS/README.md) | 独立検査（第2回）で再現（表示の誤りが確認された） | — |
| [CK-R7-24](index_detail/T06_unified_models.md#ck-r7-24) | **導出の文書 DERIVATIONS.md（D1〜D8）**<br>統合モデルが基準計算と同じ結果になる理由を式で示した文書。D1 行テーブル（和の順序の入れ替え）、D2 回数関数と周期ごとの合算、D3 修繕（除外年の重み）、D4 建替、D5 年重み付き和、D6 冷媒の充填サイクル、D7 指標と残差判定、D8 係数解決、と当てはまらない範囲。 | [`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md) | 独立検査（第2回）で再現（D1・D2・D4・D5・D6・D7。D3 の 1 文、D8、D6 の最後の行は反証） | A・C |
| [CK-R7-25](index_detail/T06_unified_models.md#ck-r7-25) | **統合モデル K1〜K7 の目録（保存済みの簡素化成果の構成）**<br>評価単位を、基準計算と同じ結果になる形で 7 つにまとめた目録：K1（行テーブル）26、K2（回数関数とライフサイクル乗数）9、K3（年重み付き和（区分的に直線な系列のモーメント））10、K4（充填サイクルの質量収支）4、K5（指標（段階ベクトルの線形関数））8、K6（許容差つきの残差判定）3、K7（係数解決の表）6。 | [`09_APPROX_STUDY/03_MODELS/models.json`](../../09_APPROX_STUDY/03_MODELS/models.json)<br>[`09_APPROX_STUDY/03_MODELS/README.md`](../../09_APPROX_STUDY/03_MODELS/README.md)<br>ほか 2 | 独立検査（第2回）で再現（値の一致だけ。構成員の数え方と仕組みの計数は反証） | A・C |

### 厳密一致・負荷・入力の測定と反例（T07）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R3-21](index_detail/T07_exactness_load.md#ck-r3-21) | **負荷の測定：規模 L、計算時間、ピークメモリ、基準案込み、評価期間 4 通り**<br>CK-R3-20 と同じ測定のうち、第2回で測り直されていない部分。規模 L（資材 20,000 行）の命令数は基準計算 245,195,907、全出力 82,539,384（66.3％ 減）、合計のみ 64,746,240（73.6％ 減）。 | [`09_APPROX_STUDY/04_VERIFICATION/unified_model_load.json`](../../09_APPROX_STUDY/04_VERIFICATION/unified_model_load.json)<br>[`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../09_APPROX_STUDY/04_VERIFICATION/README.md)<br>ほか 1 | 作成者のみ（第2回は報告書と JSON の照合だけ） | — |
| [CK-R3-23](index_detail/T07_exactness_load.md#ck-r3-23) | **入力項目の使用の測定（基準計算と統合モデルが読む入力は同じ）**<br>33 シナリオ（ベンチマーク S と境界条件）で、計算の途中でシナリオのオブジェクトから読まれた属性を記録した結果。基準計算、統合モデルの全出力、統合モデルの合計のみのいずれも、既存の入力仕様の項目 77 と本研究で加えた項目 56 を読む。基準計算は読むが統合モデルは読まない項目は 0 件。 | [`09_APPROX_STUDY/04_VERIFICATION/input_usage.json`](../../09_APPROX_STUDY/04_VERIFICATION/input_usage.json)<br>[`09_APPROX_STUDY/research_code/bench/input_usage.py`](../../09_APPROX_STUDY/research_code/bench/input_usage.py)<br>ほか 1 | 作成者のみ（第2回は報告書と JSON の照合だけ） | A・B・C |

### 近似検証（M3〜M6）（T08）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R4-01](index_detail/T08_approximation.md#ck-r4-01) | **「近似は 1 つも採用していない」という全体の結論**<br>近似の段階（M3〜M6）で測定した候補 32 種のうち、採用（SUCCESS）は 0、不採用（REJECTED）16、実データ待ちの保留（HOLD）16 という結論。 | [`09_APPROX_STUDY/03_MODELS/candidates.json`](../../09_APPROX_STUDY/03_MODELS/candidates.json)<br>[`09_APPROX_STUDY/03_MODELS/README.md`](../../09_APPROX_STUDY/03_MODELS/README.md)<br>ほか 3 | 独立検査（第2回）で一部再現（測定値の再現と、不採用理由の点検）。件数の意味と網羅性には第2回の指摘が残る | A・B・C |
| [CK-R4-02](index_detail/T08_approximation.md#ck-r4-02) | **近似候補の誤差測定の枠組み（測定プログラムと出力の形式）**<br>基準計算の結果に対して候補の値を計算し、符号付きの相対誤差 (候補 − 基準) ÷ 基準 を集める測定プログラム bench/approx_study.py と、その出力 approximation_study.json（schema 2.0、候補 32 種）。 | [`09_APPROX_STUDY/research_code/bench/approx_study.py`](../../09_APPROX_STUDY/research_code/bench/approx_study.py)<br>[`09_APPROX_STUDY/research_code/synth/population.py`](../../09_APPROX_STUDY/research_code/synth/population.py)<br>ほか 4 | 独立検査（第2回）で再現（公表した統計の再現）。測定の定義には確認済みの欠陥がある（CK-R4-03） | A・B・C |
| [CK-R4-07](index_detail/T08_approximation.md#ck-r4-07) | **冷媒漏洩の線形近似（AP-05）**<br>充填サイクルの閉形式 1−(1−r)^k を r·k で置き換える M3 の候補。不採用。測定プログラムが実際に測っているのは題名の式より粗い変種で、漏洩を m0·r·T とし、更新時の漏洩と廃棄時の残存にも満充填量 m0 を使う（すべての機器を毎年補充する機器として扱うのと同じ）。 | [`09_APPROX_STUDY/03_MODELS/candidates.json`](../../09_APPROX_STUDY/03_MODELS/candidates.json)<br>[`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)<br>ほか 2 | 独立検査（第2回）で再現（公表値は「満充填量をどこでも使う」変種の値として再現された） | A・B・C |
| [CK-R4-08](index_detail/T08_approximation.md#ck-r4-08) | **端材倍率の線形化（AP-06・AP-06b）**<br>発注量の倍率 1/(1−w) を 1+w で置き換える候補（AP-06。A1-A3 段階で測定）と、端材の再使用を考慮した正味発注量 1 + w(1−ρ)/(1−w) を 1 + w(1−ρ) で置き換える候補（AP-06b。X-13 の行ごとに測定）。どちらも M3、不採用。 | [`09_APPROX_STUDY/03_MODELS/candidates.json`](../../09_APPROX_STUDY/03_MODELS/candidates.json)<br>[`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)<br>ほか 1 | AP-06 は独立検査（第2回）で再現。AP-06b は作成者のみ（第2回は独自に再実装せず、不等式の向きだけ確かめた） | A・B・C |
| [CK-R4-10](index_detail/T08_approximation.md#ck-r4-10) | **買電排出の平均×平均（AP-08）と電力係数の補間（AP-09a・AP-09b）**<br>年次の積算 Σ(買電量×係数) を 平均買電量×平均係数×T で置き換える候補（AP-08）と、年次の電力係数系列を 5 年ごと（AP-09a）・10 年ごと（AP-09b）の点の直線補間で持つ候補。3 つとも M3、不採用。 | [`09_APPROX_STUDY/03_MODELS/candidates.json`](../../09_APPROX_STUDY/03_MODELS/candidates.json)<br>[`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)<br>ほか 2 | 独立検査（第2回）で再現（B6-03 に対する値として） | A・B・C |
| [CK-R7-27](index_detail/T08_approximation.md#ck-r7-27) | **近似候補の誤差測定のうち、第2回が再実装しなかった 5 件と内訳表**<br>第2回の近似の検査が独立に実装し直さず、数字を公表値のまま受け取った候補 5 件（AP-06b、AP-12、AP-13、AP-15、AP-16）と、AP-17 の副次の対象（X-12、C2）、X-10 の廃棄物量、構造・用途別の内訳（by_group）。 | [`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)<br>[`09_APPROX_STUDY/03_MODELS/candidates.json`](../../09_APPROX_STUDY/03_MODELS/candidates.json) | 作成者のみ | A・B・C |

### 記録・進捗台帳・報告書・必須成果物（T09）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R5-02](index_detail/T09_records_reports.md#ck-r5-02) | **単位別の検討記録 454 件（記録とは何か、どんな裏付けを名乗っているか）**<br>評価単位×検討段階（M1〜M6）×候補を 1 件とする記録の集まり。 | [`09_APPROX_STUDY/03_MODELS/records/units.json`](../../09_APPROX_STUDY/03_MODELS/records/units.json)<br>[`09_APPROX_STUDY/research_code/tools/build_records.py`](../../09_APPROX_STUDY/research_code/tools/build_records.py)<br>ほか 1 | 作成者のみ（件数と進捗台帳との整合は独立検査（第2回）で再現。裏付けの表示は第2回で誤りを指摘され、未修正） | A・C |
| [CK-R5-03](index_detail/T09_records_reports.md#ck-r5-03) | **厳密な段階（M1・M2）の成功記録 118 件**<br>厳密な簡略化（M1：52 単位）と厳密な統合（M2：66 単位）について「基準計算と同じ結果になる」とした記録。理由文は「出力が基準計算と一致（681 シナリオ、数値 n 個、最大の相対差 …）」と、機構の記号があれば「仕組みの確認：…」からなる。 | [`09_APPROX_STUDY/03_MODELS/records/units.json`](../../09_APPROX_STUDY/03_MODELS/records/units.json)<br>[`09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json`](../../09_APPROX_STUDY/04_VERIFICATION/unified_model_exactness.json)<br>ほか 1 | 独立検査（第2回）で一部を再現、一部に誤りを指摘（REC-1・2・4・5・7 は CONFIRMED、REC-3・6 は PARTLY_CONFIRMED。 | A・C |
| [CK-R5-05](index_detail/T09_records_reports.md#ck-r5-05) | **近似の段階の「不採用」記録 39 件（候補 16 種）**<br>M3（38 件）と M6（1 件）で、近似候補を測定したうえで不採用とした記録。候補は AP-01、02、03、04、05、06、06b、07a、07b、08、09a、09b、14、19b、20、22a の 16 種で、1 つの候補を複数の単位に付けている。 | [`09_APPROX_STUDY/03_MODELS/records/units.json`](../../09_APPROX_STUDY/03_MODELS/records/units.json)<br>[`09_APPROX_STUDY/03_MODELS/candidates.json`](../../09_APPROX_STUDY/03_MODELS/candidates.json)<br>ほか 2 | 作成者のみ（AP-04・AP-22a の統計だけ独立検査（第2回）で再現） | A・C |
| [CK-R5-08](index_detail/T09_records_reports.md#ck-r5-08) | **進捗台帳（progress_ledger.json と PROGRESS.md）の構造と判定の規則**<br>70 単位のそれぞれについて、M1〜M6 の段階の結論（候補の記録の写しつき）、状態（6 種）、保留中の段階、統合先のモデル、着手順と群を持つ台帳。 | [`09_APPROX_STUDY/05_DECISIONS/progress_ledger.json`](../../09_APPROX_STUDY/05_DECISIONS/progress_ledger.json)<br>[`09_APPROX_STUDY/05_DECISIONS/PROGRESS.md`](../../09_APPROX_STUDY/05_DECISIONS/PROGRESS.md)<br>ほか 2 | 独立検査（第2回）で再現（規則どおりに求まることの再現。状態の中身は第2回の指摘で一部が争われている） | A・C |
| [CK-R5-10](index_detail/T09_records_reports.md#ck-r5-10) | **自動生成の報告書 6 点と PROGRESS.md（文面としての状態）**<br>tools/build_reports.py が JSON から書く 6 つの README（第9章の README、01_LEDGER、02_RANKING、03_MODELS、04_VERIFICATION、05_DECISIONS）と、tools/progress_ledger.py が書く PROGRESS.md。 | [`09_APPROX_STUDY/README.md`](../../09_APPROX_STUDY/README.md)<br>[`09_APPROX_STUDY/01_LEDGER/README.md`](../../09_APPROX_STUDY/01_LEDGER/README.md)<br>ほか 6 | 独立検査（第2回）で数字の一致を再現。 | A・C |
| [CK-R5-13](index_detail/T09_records_reports.md#ck-r5-13) | **README の要点 3「統合モデルは基準計算と一致した」**<br>第9章 README「結果の要点」の 3。全文：「統合モデルは基準計算と一致した。681 の架空シナリオ、数値 7,406,182 個を突き合わせて不一致なし（許容差は相対 1e-09）。不備のある入力や、冗長な入力どうしが食い違う場合も、同じ値を返し、同じ不備を報告する。」 | [`09_APPROX_STUDY/README.md`](../../09_APPROX_STUDY/README.md)<br>[`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../09_APPROX_STUDY/04_VERIFICATION/README.md)<br>ほか 1 | 独立検査（第2回）で再現（681 シナリオの範囲の一致）。 | A・C |
| [CK-R5-14](index_detail/T09_records_reports.md#ck-r5-14) | **README の要点 4「計算の重さは減った」**<br>第9章 README「結果の要点」の 4。全文：「計算の重さは減った。資材 2 万行の規模で、実行した命令数は、基準計算と同じ出力をすべて出す場合に 66.3％ 減、合計・段階・指標・検査だけを求める場合に 73.6％ 減（時間は 1689 ms → 862 ms、624 ms。 | [`09_APPROX_STUDY/README.md`](../../09_APPROX_STUDY/README.md)<br>[`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../09_APPROX_STUDY/04_VERIFICATION/README.md)<br>ほか 2 | 作成者のみ（規模 S・M の命令数だけ独立検査（第2回）で再現） | A・C |
| [CK-R5-15](index_detail/T09_records_reports.md#ck-r5-15) | **README の要点 5「近似は 1 つも採用していない」**<br>第9章 README「結果の要点」の 5。全文：「近似は 1 つも採用していない。近似候補 32 種を測定し、不採用 16、実データ待ちの保留 16。更新回数の連続近似のように重大な過小評価を生むものがあり、それ以外の多くも、厳密な閉形式が同じ手間で使えるため近似の利点がなかった。 | [`09_APPROX_STUDY/README.md`](../../09_APPROX_STUDY/README.md)<br>[`09_APPROX_STUDY/03_MODELS/candidates.json`](../../09_APPROX_STUDY/03_MODELS/candidates.json)<br>ほか 2 | 作成者のみ（件数と 2 候補の統計は独立検査（第2回）で再現。 | A・B・C |
| [CK-R5-16](index_detail/T09_records_reports.md#ck-r5-16) | **README の要点 6「入力項目は減っていない」**<br>第9章 README「結果の要点」の 6。全文：「入力項目は減っていない。厳密な統合では、読む入力は基準計算と同じだった（実測）。入力を減らすには少数入力の近似モデルが必要だが、その精度は実建物のデータがなければ検証できない。」 | [`09_APPROX_STUDY/README.md`](../../09_APPROX_STUDY/README.md)<br>[`09_APPROX_STUDY/04_VERIFICATION/input_usage.json`](../../09_APPROX_STUDY/04_VERIFICATION/input_usage.json)<br>ほか 2 | 作成者のみ（報告書と JSON の一致は独立検査（第2回）で再現） | A・B・C |
| [CK-R5-18](index_detail/T09_records_reports.md#ck-r5-18) | **05_DECISIONS/README.md の採否の理由（採用・不採用・保留・現状維持の文面）**<br>旧指示書の成果物 7 に当たる文面。 | [`09_APPROX_STUDY/05_DECISIONS/README.md`](../../09_APPROX_STUDY/05_DECISIONS/README.md)<br>[`09_APPROX_STUDY/03_MODELS/candidates.json`](../../09_APPROX_STUDY/03_MODELS/candidates.json)<br>ほか 1 | 作成者のみ（JSON との一致は独立検査（第2回）で再現。内容には第2回の指摘があり未修正） | A・C |
| [CK-R5-19](index_detail/T09_records_reports.md#ck-r5-19) | **05_DECISIONS/README.md「統合前後の変化」の表（行ごとの状態）**<br>旧指示書の成果物 8 に当たる表。計算の定義の数、共通化できた単位、単位が参照する入力項目、読まれた入力項目、命令数（規模 L の 4 通り）、計算時間、ピークメモリ、結果の差の 13 行と、5 つの注記からなる。 | [`09_APPROX_STUDY/05_DECISIONS/README.md`](../../09_APPROX_STUDY/05_DECISIONS/README.md)<br>[`09_APPROX_STUDY/04_VERIFICATION/unified_model_load.json`](../../09_APPROX_STUDY/04_VERIFICATION/unified_model_load.json)<br>ほか 3 | 作成者のみ（表と JSON の一致、削減率の計算し直しは独立検査（第2回）で再現） | A・C |
| [CK-R5-20](index_detail/T09_records_reports.md#ck-r5-20) | **旧指示書の必須成果物 9 点（有無と状態）**<br>旧指示書 第8章が求めた 9 つの記録。第9章 README の成果物の表が置き場所を示す。9 点ともファイルとして存在する。どれも 43ba5d7（第1回の検査の対応後）の版で、第2回の指摘 59 件を反映していない。 | [`09_APPROX_STUDY/README.md`](../../09_APPROX_STUDY/README.md)<br>[`09_APPROX_STUDY/00_POLICY/DIRECTIVE.md`](../../09_APPROX_STUDY/00_POLICY/DIRECTIVE.md)<br>ほか 6 | 独立検査（第2回）で存在を確認。内容には未反映の指摘がある | A・C |
| [CK-R5-24](index_detail/T09_records_reports.md#ck-r5-24) | **第1回の独立検査の記録（INDEPENDENT_REVIEW.md：指摘と対応）**<br>初版に対して行った 3 つの自動検査（数値の反例探し、定義からの再導出、記録の監査）の主な指摘と、それへの対応を、主担当がまとめた手書きの記録。 | [`09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md`](../../09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md)<br>[`09_APPROX_STUDY/04_VERIFICATION/README.md`](../../09_APPROX_STUDY/04_VERIFICATION/README.md) | 作成者のみ（対応の記述）。対応後の版は独立検査（第2回）の対象になり、一部の対応が否定された | — |
| [CK-R5-29](index_detail/T09_records_reports.md#ck-r5-29) | **記録・台帳・報告書の生成器（research_code/tools/ の 5 本）：どの生成器がどのファイルを書くか**<br>tools/sync_ledger.py：基準計算の関数の説明文と依存関係を 01_LEDGER/units.json（reference_semantics、depends_on、feeds、sheet_family_links）へ写し、01_LEDGER/sheet_family_coverage.json を更新する。 | [`09_APPROX_STUDY/research_code/tools/sync_ledger.py`](../../09_APPROX_STUDY/research_code/tools/sync_ledger.py)<br>[`09_APPROX_STUDY/research_code/tools/rank_axes.py`](../../09_APPROX_STUDY/research_code/tools/rank_axes.py)<br>ほか 4 | 独立検査（第2回）で progress_ledger.py と rank_axes.py の結果を再現。 | A・C |

### 材料分類の設計草案（T10）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R5-27](index_detail/T10_material_taxonomy.md#ck-r5-27) | **材料分類の設計草案のレビュー記録（REVIEW_LOG.md）**<br>独立したレビュー担当（自動）が、草案の 4 ファイルの内部整合について挙げた指摘 25 件（HIGH 2、MEDIUM 18、LOW 5）と、その採否（反映 24、却下 0、先送り 1）、修正後に行った検査の一覧。 | [`09_APPROX_STUDY/07_MATERIAL_TAXONOMY/REVIEW_LOG.md`](../../09_APPROX_STUDY/07_MATERIAL_TAXONOMY/REVIEW_LOG.md) | 作成者の記録（指摘は独立の自動レビュー。対応と修正後の検査は作成者。再現できない） | — |

### 中断した修正（65ff124）と未実施の改訂（T11）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R1-11](index_detail/T11_interrupted_fix.md#ck-r1-11) | **中断した修正（65ff124）での台帳の書き換え（reference_semantics 50 単位ほか）**<br>停止時点の作業ツリー（65ff124）では、段階 a1 の作業担当が台帳 units.json を書き換えていた。 | git show 65ff124:`09_APPROX_STUDY/01_LEDGER/units.json`（コミット `65ff124` の版）<br>[`materials/interrupted_fix/working_tree_at_stop_65ff124.patch`](materials/interrupted_fix/working_tree_at_stop_65ff124.patch)<br>ほか 1 | 中断した修正の自己申告 | — |
| [CK-R2-19](index_detail/T11_interrupted_fix.md#ck-r2-19) | **中断した修正 a1：時間の判定の厳密化（整数演算。事象の「年」を受け渡す）**<br>a1 の自己申告によると、65ff124 の refcalc/base.py と fastcalc/closed_forms.py で、内側の判定、事象の年、n 回目の事象 n×L を、as_integer_ratio() による整数演算で厳密に計算するようにした。 | [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](materials/interrupted_fix/agent_reports/A1_REPORT.json)<br>[`materials/interrupted_fix/working_tree_at_stop_65ff124.patch`](materials/interrupted_fix/working_tree_at_stop_65ff124.patch)<br>ほか 2 | 中断した修正の自己申告 | — |
| [CK-R2-20](index_detail/T11_interrupted_fix.md#ck-r2-20) | **中断した修正 a1：値の妥当性の規則（検査なしの値を除外して数える。評価期間以外で例外を出さない）**<br>a1 の自己申告によると、65ff124 で、年次量、電力係数（記述子・年次表・工事期間の値）、係数値、ガス別量、換算倍率、GWP を「有限で 0 以上（換算倍率は正）」と検査し、満たさない系列・行・単位を除外して数えるようにした。 | [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](materials/interrupted_fix/agent_reports/A1_REPORT.json)<br>[`materials/interrupted_fix/working_tree_at_stop_65ff124.patch`](materials/interrupted_fix/working_tree_at_stop_65ff124.patch)<br>ほか 2 | 中断した修正の自己申告 | — |
| [CK-R2-21](index_detail/T11_interrupted_fix.md#ck-r2-21) | **中断した修正 a1：データの流れに沿った完全性の印、B2-01 の computed、SUM-08 の状態の追加**<br>a1 の自己申告によると、65ff124 で、完全性を「X-02 が段階を作るのに使う単位と、その depends_on の推移閉包」から求めるようにした（手書きの表 STAGE_UNITS を廃止）。 | [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](materials/interrupted_fix/agent_reports/A1_REPORT.json)<br>[`materials/interrupted_fix/working_tree_at_stop_65ff124.patch`](materials/interrupted_fix/working_tree_at_stop_65ff124.patch)<br>ほか 2 | 中断した修正の自己申告 | — |
| [CK-R2-22](index_detail/T11_interrupted_fix.md#ck-r2-22) | **中断した修正 a1：ガス別内訳の検査、擬似行の番兵、ゲートと定義文の改訂**<br>a1 の自己申告によると、65ff124 で次を変えた。X-04 が matches_stage_total を返し、QA-01 に検査 (d)（違反名「gas breakdown total」）を加えた。B3-01 の「e0 = 0 なら行を捨てる」近道を外した。 | [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](materials/interrupted_fix/agent_reports/A1_REPORT.json)<br>[`materials/interrupted_fix/working_tree_at_stop_65ff124.patch`](materials/interrupted_fix/working_tree_at_stop_65ff124.patch)<br>ほか 1 | 中断した修正の自己申告 | — |
| [CK-R2-23](index_detail/T11_interrupted_fix.md#ck-r2-23) | **中断した修正 a1：試験 68 件、壊し方 214 種類、比較の厳格化、一致確認の自己申告**<br>a1 の自己申告によると、65ff124 で、試験を 28 件から 68 件に増やした（test_closed_forms.py を fractions.Fraction のループとの比較に書き直して 14 件、test_refcalc.py に DefinitionTests 23 件、test_engine.py に 9 件追加）。 | [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](materials/interrupted_fix/agent_reports/A1_REPORT.json)<br>[`materials/interrupted_fix/working_tree_at_stop_65ff124.patch`](materials/interrupted_fix/working_tree_at_stop_65ff124.patch)<br>ほか 3 | 中断した修正の自己申告 | — |
| [CK-R3-31](index_detail/T11_interrupted_fix.md#ck-r3-31) | **中断した修正 a1：時間の判定を厳密な有理数の演算にし、閉形式を作り直す**<br>第2回の指摘 NUM-1・REC-1・APP-5 への対応として決めた設計と、その実装の自己申告。 | [`materials/interrupted_fix/specs/SPEC_A1.md`](materials/interrupted_fix/specs/SPEC_A1.md)<br>[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](materials/interrupted_fix/agent_reports/A1_REPORT.json)<br>ほか 1 | 中断した修正の自己申告 | A・B・C |
| [CK-R3-32](index_detail/T11_interrupted_fix.md#ck-r3-32) | **中断した修正 a1：修正後の一致確認と負荷の変化（自己申告の数字）**<br>a1 が、基準計算と統合モデルの両方を直した後のコードについて報告した数字。厳密一致は 1,490 シナリオ（壊し方を 36 種から 214 種に増やし、段階の部分集合と上流の不備の組 90 件を加えた）で、床 0 の比較で不一致 0、最大 4.775e-13（SUM-08 の delta）。 | [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](materials/interrupted_fix/agent_reports/A1_REPORT.json)<br>[`materials/interrupted_fix/a1_scratch`](materials/interrupted_fix/a1_scratch) | 中断した修正の自己申告 | — |
| [CK-R3-36](index_detail/T11_interrupted_fix.md#ck-r3-36) | **中断した段階 a2 の途中の出力 2 ファイル（未検証）**<br>a2 が停止前に書き出した JSON。(1) membership_check_UNVERIFIED.json：5 つの架空シナリオ（各 資材 60・設備 24・冷媒 8）で 35 種の故障を入れ、変わった単位を記録したもの。 | [`materials/interrupted_fix/a2_partial_outputs/membership_check_UNVERIFIED.json`](materials/interrupted_fix/a2_partial_outputs/membership_check_UNVERIFIED.json)<br>[`materials/interrupted_fix/a2_partial_outputs/mechanism_probe_UNVERIFIED.json`](materials/interrupted_fix/a2_partial_outputs/mechanism_probe_UNVERIFIED.json) | なし（中断した修正の出力。自己申告の報告もない） | — |
| [CK-R4-23](index_detail/T11_interrupted_fix.md#ck-r4-23) | **b2 の再測定と新しい候補（中断した修正。自己申告のみ）**<br>第2回の指摘（APP-1〜9、REP-5・6・13、REC-8）を測定プログラムに反映した版と、その出力。approx_study.py を 4 つのモジュールに分け、schema 3.0 の出力（候補 40 種）を作った。 | [`materials/interrupted_fix/b2_output/approximation_study_UNVERIFIED.json`](materials/interrupted_fix/b2_output/approximation_study_UNVERIFIED.json)<br>[`materials/interrupted_fix/agent_reports/B2_REPORT.json`](materials/interrupted_fix/agent_reports/B2_REPORT.json)<br>ほか 5 | 中断した修正の自己申告（独立の検査は未実施。このリーダーも実行していない） | B・C |
| [CK-R7-32](index_detail/T11_interrupted_fix.md#ck-r7-32) | **中断した修正（65ff124）の基準計算・閉形式：定義が変わった未検証の版**<br>第2回の指摘を反映する作業の途中で止まった作業ツリーの記録。a1 段階（基準計算の定義、時間の厳密な判定、不正値の扱い、完全性の印）は作業担当が完了を報告したが、独立の検査を受けていない。 | [`materials/interrupted_fix/working_tree_at_stop_65ff124.patch`](materials/interrupted_fix/working_tree_at_stop_65ff124.patch)<br>[`materials/interrupted_fix/agent_reports/A1_REPORT.json`](materials/interrupted_fix/agent_reports/A1_REPORT.json)<br>ほか 2 | 中断した修正の自己申告 | B・C |

### 式の族と未実装の案（構造の棚卸し）（T12）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R7-04](index_detail/T12_formula_families.md#ck-r7-04) | **式の族 F01：行の和（活動量×換算倍率×係数）**<br>行（資材・設備・燃料・廃棄物・解体活動・費用項目・機器）ごとに 活動量×換算倍率×係数値 を作って足す形の 19 単位。活動量は数量そのもの、質量×距離、質量×経路の比率、費用のいずれかで、行の乗数（未数量分 r/(1−r)、積載率 1/lf、物価の比）が付く単位がある。 | [`09_APPROX_STUDY/01_LEDGER/units.json`](../../09_APPROX_STUDY/01_LEDGER/units.json)<br>[`09_APPROX_STUDY/research_code/refcalc/base.py`](../../09_APPROX_STUDY/research_code/refcalc/base.py)<br>ほか 4 | 独立検査（第2回）で再現（値の一致。族の区分は検査なし） | B・C |
| [CK-R7-05](index_detail/T12_formula_families.md#ck-r7-05) | **式の族 F02：行ごとの数量の比・換算（端材率・再使用率）**<br>資材の行ごとに、数量の基準と端材率から発注量と据付量を作る A13-05 と、端材の再使用を引いた正味の発注量 X-13 の 2 単位。結果は行ごとの一覧で、スカラーの合計を持たない。 | [`09_APPROX_STUDY/01_LEDGER/units.json`](../../09_APPROX_STUDY/01_LEDGER/units.json)<br>[`09_APPROX_STUDY/research_code/refcalc/base.py`](../../09_APPROX_STUDY/research_code/refcalc/base.py)<br>ほか 1 | 独立検査（第2回）で再現（値の一致。族の区分は検査なし） | B・C |
| [CK-R7-06](index_detail/T12_formula_families.md#ck-r7-06) | **式の族 F03：加重和・行列の展開・区分別の再集計**<br>複合係数（質量比で加重した係数の和）A13-02、その構成材への展開 X-03、ガス別の内訳 X-04、CO2 だけの並行算定 X-05、資材区分×処理経路の表 X-09、6 区分の再集計 X-17 の 6 単位。同じ行の活動量に、別の列（質量比、ガス別量、区分、経路）を掛けて足し直す形である。 | [`09_APPROX_STUDY/01_LEDGER/units.json`](../../09_APPROX_STUDY/01_LEDGER/units.json)<br>[`09_APPROX_STUDY/research_code/refcalc/base.py`](../../09_APPROX_STUDY/research_code/refcalc/base.py)<br>ほか 3 | 独立検査（第2回）で再現（A13-02 と、間接的に X-04・X-05。残り 3 単位は作成者のみ） | B・C |
| [CK-R7-07](index_detail/T12_formula_families.md#ck-r7-07) | **式の族 F04：事象の数え上げ（評価期間 T と周期）**<br>周期 c の倍数 n·c が評価期間の内側にある個数 N(T,c) と、それを 1 回分の排出に掛ける形の 6 単位（更新年の一覧 B4-01、交換回数 B4-03、更新負荷 B4-02、建替 B5-01、周期別の集計 X-08、資源量・廃棄物量 X-10）。 | [`09_APPROX_STUDY/01_LEDGER/units.json`](../../09_APPROX_STUDY/01_LEDGER/units.json)<br>[`09_APPROX_STUDY/research_code/refcalc/base.py`](../../09_APPROX_STUDY/research_code/refcalc/base.py)<br>ほか 4 | 独立検査（第2回）で再現（値の一致。族の区分は検査なし） | B・C |
| [CK-R7-08](index_detail/T12_formula_families.md#ck-r7-08) | **式の族 F05：年重み付き和（年次量×年ごとの係数）**<br>評価年 y=1..Y（Y=ceil(T)）について、年次量と係数の積に年重み w_y=min(1, T−(y−1)) を掛けて足す形の 13 単位（買電と燃料の B6、施設管理分 B2、上水・下水・一般廃棄物の B7、修繕 B3、面積当たりの推定 X-11、年次・累積の系列 X-07）。 | [`09_APPROX_STUDY/01_LEDGER/units.json`](../../09_APPROX_STUDY/01_LEDGER/units.json)<br>[`09_APPROX_STUDY/research_code/refcalc/base.py`](../../09_APPROX_STUDY/research_code/refcalc/base.py)<br>ほか 3 | 独立検査（第2回）で再現（値の一致。族の区分は検査なし） | B・C |
| [CK-R7-09](index_detail/T12_formula_families.md#ck-r7-09) | **式の族 F06：区分的に直線・段階的な電力係数の年次系列（X-06）**<br>電力排出係数の年次系列を、記述子から作る 1 単位。一定、直線低下（下限つき：max(下限, 初期値−年低下量×k)）、段階（添字 0 から厳密に増える段）の 3 種は記述子が整っていれば記述子から、それ以外は年次表から取る。 | [`09_APPROX_STUDY/01_LEDGER/units.json`](../../09_APPROX_STUDY/01_LEDGER/units.json)<br>[`09_APPROX_STUDY/research_code/refcalc/base.py`](../../09_APPROX_STUDY/research_code/refcalc/base.py)<br>ほか 3 | 独立検査（第2回）で再現（値の一致。族の区分は検査なし） | B・C |
| [CK-R7-10](index_detail/T12_formula_families.md#ck-r7-10) | **式の族 F07：冷媒の充填・漏洩・補充・交換（年ごとの漸化式）**<br>機器ごとに残存量を 1 年ずつ進める 3 単位（使用期間の漏洩 B1-02、交換時の損失 B1-03、廃棄時の未回収 B1-04）。その年の漏洩＝年初の残存量×年間漏洩率×年重み。補充しない機器は年末に漏洩分を引き、交換は属する年の年末に残存量を初期充填量へ戻す。 | [`09_APPROX_STUDY/01_LEDGER/units.json`](../../09_APPROX_STUDY/01_LEDGER/units.json)<br>[`09_APPROX_STUDY/research_code/refcalc/base.py`](../../09_APPROX_STUDY/research_code/refcalc/base.py)<br>ほか 3 | 独立検査（第2回）で再現（値の一致。族の区分は検査なし） | B・C |
| [CK-R7-11](index_detail/T12_formula_families.md#ck-r7-11) | **式の族 F08：比・指標（原単位、単位換算、段階別割合）**<br>ホールライフの合計を延床面積、面積×評価年数、1000 で割る SUM-04・SUM-05・SUM-06 と、段階の値を合計で割る SUM-07 の 4 単位。 | [`09_APPROX_STUDY/01_LEDGER/units.json`](../../09_APPROX_STUDY/01_LEDGER/units.json)<br>[`09_APPROX_STUDY/research_code/refcalc/base.py`](../../09_APPROX_STUDY/research_code/refcalc/base.py)<br>ほか 1 | 独立検査（第2回）で再現（値の一致。族の区分は検査なし） | B・C |
| [CK-R7-12](index_detail/T12_formula_families.md#ck-r7-12) | **式の族 F09：集約の木（段階ベクトルと部分和）**<br>工事負荷の合計 A5-04、14 段階のベクトルを作る X-02、その部分和であるアップフロント SUM-01・エンボディド SUM-02・ホールライフ SUM-03 の 5 単位。対象段階の指定（included_lifecycle_stages）が 0／1 の重みとして掛かる。 | [`09_APPROX_STUDY/01_LEDGER/units.json`](../../09_APPROX_STUDY/01_LEDGER/units.json)<br>[`09_APPROX_STUDY/research_code/refcalc/base.py`](../../09_APPROX_STUDY/research_code/refcalc/base.py)<br>ほか 3 | 独立検査（第2回）で再現（値の一致。族の区分は検査なし） | B・C |
| [CK-R7-13](index_detail/T12_formula_families.md#ck-r7-13) | **式の族 F10：基準案との比較（SUM-08）**<br>基準シナリオが指定されていれば、基準シナリオを同じ基準計算で最初から計算し、差＝当該案−基準案、削減率＝(基準案−当該案)÷基準案 を出す 1 単位。延床面積・評価期間・対象段階・ガスの範囲・係数の公開年の集合がすべて一致するときだけ比べる。 | [`09_APPROX_STUDY/01_LEDGER/units.json`](../../09_APPROX_STUDY/01_LEDGER/units.json)<br>[`09_APPROX_STUDY/research_code/refcalc/base.py`](../../09_APPROX_STUDY/research_code/refcalc/base.py)<br>ほか 2 | 独立検査（第2回）で再現（間接的な確認。族の区分は検査なし） | B・C |
| [CK-R7-14](index_detail/T12_formula_families.md#ck-r7-14) | **式の族 F11：条件分岐・述語（入力検査、整合の検査、係数の解決）**<br>入力値の状態 SYS-01、単位と段階の整合 SYS-02、係数の使用許諾 SYS-03、面積の整合 SYS-04・QA-04、段階合計の突合と択一 QA-01、時間境界 QA-02、出典 QA-03、質量収支 C-05、係数の検索と優先順位 X-15 の 10 単位。 | [`09_APPROX_STUDY/01_LEDGER/units.json`](../../09_APPROX_STUDY/01_LEDGER/units.json)<br>[`09_APPROX_STUDY/research_code/refcalc/base.py`](../../09_APPROX_STUDY/research_code/refcalc/base.py)<br>ほか 2 | 独立検査（第2回）で再現（3 単位）。残り 7 単位は作成者のみ | B・C |

## 4. 区分 3：研究途中の数式・仮説

式、モデル化の案、保留した近似候補、設計はしたが実装（または検証）していない修正、評価者の提案。**成果ではなく材料である。**

### 統制文書と手順書（T01）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R1-03](index_detail/T01_policy_protocol.md#ck-r1-03) | **手順書 v1.4 で定めるとした規則と、台帳・順位・報告の未実施の修正設計**<br>第2回の指摘を受けて決めた修正の設計のうち、手順書・台帳・順位・報告に関するもの。手順書の改訂履歴 1.4 の行と、保存された作業指示（SPEC_B3.md、STAGE_C_NOTES.md）に書かれている。段階 b3（台帳の入力項目の実測）と、記録・報告の再生成は着手されていない。 | [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md)<br>[`materials/interrupted_fix/specs/SPEC_B3.md`](materials/interrupted_fix/specs/SPEC_B3.md)<br>ほか 1 | なし | A・B・C |

### 評価単位の台帳・シート族・依存関係（T02）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R1-08](index_detail/T02_ledger.md#ck-r1-08) | **台帳の見込み欄・提案欄・曖昧点（統合と近似の見込み、定義の提案）**<br>各単位の unification_potential（統合の見込み）、approximation_potential（近似の見込み）、expected_precision_loss（想定される精度低下）、similar_units（同じ構造の単位）、boundary_unit_caveats（同一視してはならない算定境界・単位）、ambiguities（概念式が決めていない点）と、29 単位にある reference… | [`09_APPROX_STUDY/01_LEDGER/units.json`](../../09_APPROX_STUDY/01_LEDGER/units.json) | なし | B・C |

### 着手順序（評価軸 A・B）（T03）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R1-19](index_detail/T03_ranking.md#ck-r1-19) | **評価軸 B の評価者が書いた理由と置き換え案（70 単位×3 者）**<br>3 つの自動評価が、採点と一緒に各単位について書いた理由（rationale）と置き換え案（replacement_idea）。例：B1-02（使用期間の漏洩）について、年ごとの漸化式を交換区間ごとの等比級数の閉形式にし、B1-03・B1-04 と残存量を共有する 1 つの物質収支にまとめる案。 | [`09_APPROX_STUDY/02_RANKING/axis_b_judges/`](../../09_APPROX_STUDY/02_RANKING/axis_b_judges)<br>[`09_APPROX_STUDY/02_RANKING/axis_b.json`](../../09_APPROX_STUDY/02_RANKING/axis_b.json)<br>ほか 1 | なし | B・C |

### 統合モデル K1〜K7 と導出（T06）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R3-33](index_detail/T06_unified_models.md#ck-r3-33) | **設計案：統合の所属を故障注入で確かめる（membership_check）**<br>統合モデルの共有物（表の読み出し、回数と除外年の重みの関数、年重み付き和とモーメントの関数、冷媒の機器の表と充填サイクルの関数、指標の関数、残差判定、係数の解決）を外から故意に壊し（結果を 1.5 倍にする、真偽を反転するなど）、小さい架空シナリオの組で統合モデルを全出力と合計のみで実行して、どの単位の公開の結果が変わるかを記録する。 | [`materials/interrupted_fix/specs/SPEC_A2.md`](materials/interrupted_fix/specs/SPEC_A2.md)<br>[`materials/interrupted_fix/specs/STAGE_C_NOTES.md`](materials/interrupted_fix/specs/STAGE_C_NOTES.md) | なし | A・B・C |
| [CK-R3-34](index_detail/T06_unified_models.md#ck-r3-34) | **設計案：仕組みを外から計測する（mechanism_probe）**<br>統合モデルの中に手で置いた計数をやめ、外からの計測に置き換える設計。係数の値を数える float の派生型、行の代理オブジェクト、係数の辞書と換算関数の呼び出しの計数、事象年の一覧を作る補助関数の計数、年ごとの繰り返しの目的別の計数で、aggregate と finish を分けて数える。 | [`materials/interrupted_fix/specs/SPEC_A2.md`](materials/interrupted_fix/specs/SPEC_A2.md)<br>[`materials/interrupted_fix/specs/STAGE_C_NOTES.md`](materials/interrupted_fix/specs/STAGE_C_NOTES.md) | なし | A・B・C |
| [CK-R3-35](index_detail/T06_unified_models.md#ck-r3-35) | **設計案：共有の構造をコード上で実体にする統合モデルの再構成**<br>結果を変えずに、所属の主張に合うようコードを直す設計。(1) 指標 K5：1 つの共有関数 indicator(段階ベクトル, 部分集合, 除数) を SUM-01〜06 と SUM-07 の割合に使い、SUM-08 はその SUM-03 の値を使う。 | [`materials/interrupted_fix/specs/SPEC_A2.md`](materials/interrupted_fix/specs/SPEC_A2.md)<br>[`materials/interrupted_fix/working_tree_at_stop_65ff124.patch`](materials/interrupted_fix/working_tree_at_stop_65ff124.patch) | なし | — |
| [CK-R3-37](index_detail/T06_unified_models.md#ck-r3-37) | **統合モデルの拡張案のうち実装・検証していないもの**<br>検討したが実装も測定もしていない案。(1) 累積の年次系列（X-07）を乗数から直接求める閉形式：年末ちょうどの事象の扱いが「評価期間 t の合計」と 1 点で違うことを確かめた段階。(2) 建替なしを範囲比 0 として表し、建替シナリオの入力を 1 つ減らす：式の上では同じ結果。 | [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md)<br>[`09_APPROX_STUDY/03_MODELS/README.md`](../../09_APPROX_STUDY/03_MODELS/README.md)<br>ほか 1 | なし | A・C |

### 近似検証（M3〜M6）（T08）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R4-06](index_detail/T08_approximation.md#ck-r4-06) | **修繕の安全側の候補（除外年数の連続近似。第2回で提案、b2 で AP-23a・b・c）**<br>修繕年数 = T − min(T, max(0, T/c − 1)) とする候補。行ごとの形と、資材区分ごとに Σe0·r と「e0·r で重み付けした調和平均の周期」の 2 つだけを持つ区分パラメータの形がある。60e720f の研究には無い。 | [`materials/round2_review/triage/approx.md`](materials/round2_review/triage/approx.md)<br>[`materials/round2_review/checker_scripts/approx/recheck3.py`](materials/round2_review/checker_scripts/approx/recheck3.py)<br>ほか 4 | 独立検査（第2回）の検査担当と反証検査担当が測定（研究本体の記録には無い）。b2 の実装は中断した修正の自己申告 | B・C |
| [CK-R4-11](index_detail/T08_approximation.md#ck-r4-11) | **年次表の電力係数だけを 5 年刻みにする併用（AP-09c）**<br>記述子（一定・直線低下・段階）で与えられる系列は厳密な閉形式のまま、年次表で与えられる系列だけを 5 年ごとの点の直線補間で持つ M6 の候補。保留（必要なデータ：利用許諾のある電力排出係数の将来見通しの刻みと形）。 | [`09_APPROX_STUDY/03_MODELS/candidates.json`](../../09_APPROX_STUDY/03_MODELS/candidates.json)<br>[`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)<br>ほか 2 | 独立検査（第2回）で再現（B6-03 に対する値として） | B・C |
| [CK-R4-12](index_detail/T08_approximation.md#ck-r4-12) | **区分パラメータによる共通近似モデル（AP-18a・AP-18b・AP-18）**<br>資材区分ごとに代表値を持ち、行ごとの条件を使わない M4 の候補。AP-18a：代表更新周期（更新 1 回の排出で重み付けした調和平均）で B4 を計算。AP-18b：代表修繕率（初期排出で重み付けした平均）と代表周期で B3 を計算。AP-18：AP-18a〜c を同時に適用。すべて保留。 | [`09_APPROX_STUDY/03_MODELS/candidates.json`](../../09_APPROX_STUDY/03_MODELS/candidates.json)<br>[`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)<br>ほか 3 | 独立検査（第2回）で再現（公表した統計）。測定の意味には指摘がある | B・C |
| [CK-R4-13](index_detail/T08_approximation.md#ck-r4-13) | **廃棄段階の区分集約（AP-18c）**<br>資材区分ごとに処理経路の比率（単純平均）と経路係数（単純平均）を持ち、行は質量だけにする M4 の候補。保留。 | [`09_APPROX_STUDY/03_MODELS/candidates.json`](../../09_APPROX_STUDY/03_MODELS/candidates.json)<br>[`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)<br>ほか 1 | 独立検査（第2回）で再現 | B・C |
| [CK-R4-14](index_detail/T08_approximation.md#ck-r4-14) | **要約数量×代表係数による資材製造の概算（AP-10・AP-10b）**<br>6 区分の要約数量（X-17）に（構造×用途）ごとの代表係数を掛けて資材製造（A13-01＋A13-03）を概算する M4 の候補（AP-10）と、6 区分に入らない資材の分の割増（構造×用途ごとの平均比）を掛ける変種（AP-10b）。どちらも保留。 | [`09_APPROX_STUDY/03_MODELS/candidates.json`](../../09_APPROX_STUDY/03_MODELS/candidates.json)<br>[`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)<br>ほか 2 | 独立検査（第2回）で再現（学習と試験の間に漏れが無いことも確認） | B・C |
| [CK-R4-15](index_detail/T08_approximation.md#ck-r4-15) | **延床面積の原単位・回帰による代理モデル（AP-11・AP-15・AP-16・AP-13）**<br>単位の式を使わず、延床面積・評価年数・構造・用途だけから求める候補。AP-11（M5）：合計 = 面積×年数×（構造×用途）の平均原単位。AP-15（M4）：14 段階のそれぞれを 面積（使用段階は×年数）×平均原単位 で求める「共通近似モデル」。 | [`09_APPROX_STUDY/03_MODELS/candidates.json`](../../09_APPROX_STUDY/03_MODELS/candidates.json)<br>[`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)<br>ほか 3 | AP-11 は独立検査（第2回）で再現。 | B・C |
| [CK-R4-16](index_detail/T08_approximation.md#ck-r4-16) | **質量上位の行だけを詳細計算する併用（AP-12）**<br>質量上位 20％ の資材行だけを詳細に計算し、残りを質量比で補う M6 の候補。保留。 | [`09_APPROX_STUDY/03_MODELS/candidates.json`](../../09_APPROX_STUDY/03_MODELS/candidates.json)<br>[`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)<br>ほか 1 | 作成者のみ（第2回は独自に再実装していない） | B・C |
| [CK-R4-17](index_detail/T08_approximation.md#ck-r4-17) | **輸送の単純平均距離（AP-17）**<br>輸送手段ごとに 合計質量×単純平均距離 で輸送排出を求める M3 の候補。同じ置き換えを X-12（積載率補正後の輸送、参考値）と C2（廃棄物の搬出）にも当てて測っている。保留。 | [`09_APPROX_STUDY/03_MODELS/candidates.json`](../../09_APPROX_STUDY/03_MODELS/candidates.json)<br>[`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)<br>ほか 1 | 独立検査（第2回）で再現（A4 段階の値）。X-12 と C2 の値は再測定されていない | A・B・C |
| [CK-R4-18](index_detail/T08_approximation.md#ck-r4-18) | **未数量分の比率を 1 つにまとめる（AP-19a・AP-19b）**<br>未数量分（A13-04）の上乗せ倍率 r/(1−r) で、行ごとの比率の代わりに単純平均の比率 1 つ（AP-19a、保留）または最大の比率 1 つ（AP-19b、不採用）を使う M3 の候補。 | [`09_APPROX_STUDY/03_MODELS/candidates.json`](../../09_APPROX_STUDY/03_MODELS/candidates.json)<br>[`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)<br>ほか 1 | 独立検査（第2回）で再現 | B・C |
| [CK-R4-21](index_detail/T08_approximation.md#ck-r4-21) | **母集団の平均比で置き換える候補（AP-21・AP-22b）**<br>AP-21：木材の炭素貯蔵（STO-01、参考値）を 数量×（構造×用途）ごとの平均の m3 当たり貯蔵量 で求める。AP-22b：CO2 のみの合計を 全ガスの合計×（構造×用途）ごとの平均の CO2 比 で求める。どちらも M3、保留。 | [`09_APPROX_STUDY/03_MODELS/candidates.json`](../../09_APPROX_STUDY/03_MODELS/candidates.json)<br>[`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)<br>ほか 2 | 独立検査（第2回）で再現 | — |

### 記録・進捗台帳・報告書・必須成果物（T09）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R5-06](index_detail/T09_records_reports.md#ck-r5-06) | **近似の段階の「保留」記録 71 件（候補 16 種。実データ待ち）**<br>M3（6 件）、M4（53 件）、M5（8 件）、M6（4 件）で「架空データでは判断できず、実データが要る」とした記録。候補は AP-09c、10、10b、11、12、13、15、16、17、18、18a、18b、18c、19a、21、22b の 16 種。 | [`09_APPROX_STUDY/03_MODELS/records/units.json`](../../09_APPROX_STUDY/03_MODELS/records/units.json)<br>[`09_APPROX_STUDY/03_MODELS/candidates.json`](../../09_APPROX_STUDY/03_MODELS/candidates.json)<br>ほか 2 | 作成者のみ | A・B・C |
| [CK-R5-07](index_detail/T09_records_reports.md#ck-r5-07) | **「候補なし」記録 226 件（測定をしていない判断）**<br>測定をせず、理由だけで段階を閉じた記録。M1 18、M2 4、M3 42、M4 31、M5 66、M6 65。verification は全件「未検証」で、根拠のファイルの欄は空。 | [`09_APPROX_STUDY/03_MODELS/records/units.json`](../../09_APPROX_STUDY/03_MODELS/records/units.json)<br>[`09_APPROX_STUDY/research_code/tools/build_records.py`](../../09_APPROX_STUDY/research_code/tools/build_records.py)<br>ほか 1 | なし（独立検査（第2回）が理由文の一部に誤りを指摘。REC-8 は CONFIRMED） | B・C |

### 材料分類の設計草案（T10）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R5-26](index_detail/T10_material_taxonomy.md#ck-r5-26) | **材料分類の設計草案（07_MATERIAL_TAXONOMY：データ構造と手順の形だけ。データセットではない）**<br>旧指示書 第7章「次段階：材料データの分類」に向けて、データ構造と手順の形だけを先に調べた設計草案。README.md（本文）、taxonomy_schema.json（レコード定義 20 種。うち最初の作業に要る最小の組が 12 種。 | [`09_APPROX_STUDY/07_MATERIAL_TAXONOMY/README.md`](../../09_APPROX_STUDY/07_MATERIAL_TAXONOMY/README.md)<br>[`09_APPROX_STUDY/07_MATERIAL_TAXONOMY/taxonomy_schema.json`](../../09_APPROX_STUDY/07_MATERIAL_TAXONOMY/taxonomy_schema.json)<br>ほか 2 | 作成者と、内部整合だけの独立レビュー 1 回（実データでの検証なし）。独立検査（第2回）は件数の一致だけ | B・C |

### 中断した修正（65ff124）と未実施の改訂（T11）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R2-18](index_detail/T11_interrupted_fix.md#ck-r2-18) | **第2回の指摘に対する基準計算の定義の修正方針（SPEC_A1.md の設計決定）**<br>中断した修正の段階 a1 に渡された指示書。一般原則は「欠損・非有限・範囲外の数値入力は演算に使わない。それを必要とする最小の単位（行、経路、年次系列、区分、単位）を除いて数え、依存する合計をすべて不完全にする。無効な評価期間以外の入力では例外を出さない」。 | [`materials/interrupted_fix/specs/SPEC_A1.md`](materials/interrupted_fix/specs/SPEC_A1.md)<br>[`materials/interrupted_fix/specs/VERIFY_DEF.md`](materials/interrupted_fix/specs/VERIFY_DEF.md) | なし | B・C |
| [CK-R4-24](index_detail/T11_interrupted_fix.md#ck-r4-24) | **b2 の設計（SPEC_B2）と結論文の書き換え案**<br>測定の修正の仕様（SPEC_B2.md、変更 13 項目と受入条件 3 項目）と、b2 の作業担当が出した候補ごとの結論文の案（conclusion_proposals.json、41 件：書き換え 16、そのまま 16、新規 9）。 | [`materials/interrupted_fix/specs/SPEC_B2.md`](materials/interrupted_fix/specs/SPEC_B2.md)<br>[`materials/interrupted_fix/agent_reports/conclusion_proposals.json`](materials/interrupted_fix/agent_reports/conclusion_proposals.json)<br>ほか 1 | 中断した修正の自己申告 | A・C |
| [CK-R5-30](index_detail/T11_interrupted_fix.md#ck-r5-30) | **予定だったが行われなかった改訂（Stage C）：記録・進捗台帳・報告書の生成器**<br>第2回の指摘を記録・進捗台帳・報告書に反映するための改訂の覚え書き。ワークフローの各段階（a1、a2、b3、b2、反証の検査と修正）の報告を入力にして、主担当が行う予定だった。どれも着手されていない。内容：build_records.py について 7 点。(1) 厳密な記録の裏付けを作り直す。 | [`materials/interrupted_fix/specs/STAGE_C_NOTES.md`](materials/interrupted_fix/specs/STAGE_C_NOTES.md)<br>[`materials/interrupted_fix/agent_reports/conclusion_proposals.json`](materials/interrupted_fix/agent_reports/conclusion_proposals.json)<br>ほか 2 | なし | A・C |
| [CK-R5-31](index_detail/T11_interrupted_fix.md#ck-r5-31) | **予定だったが行われなかった改訂（Stage C）：手書きの文書と、全体の再生成**<br>第2回の指摘を手書きの文書に反映し、全体を測り直して再生成する予定の覚え書き。内容：DERIVATIONS.md（D2・D3 を厳密な演算で書き直し、事象が相異なる年に入る条件の証明を付ける。D6 の最後の行、D8 の「何を記憶するか」、「導出が当てはまらない範囲」）。 | [`materials/interrupted_fix/specs/STAGE_C_NOTES.md`](materials/interrupted_fix/specs/STAGE_C_NOTES.md)<br>[`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md)<br>ほか 3 | なし | A・C |

### 式の族と未実装の案（構造の棚卸し）（T12）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R7-31](index_detail/T12_formula_families.md#ck-r7-31) | **検討したが実装・検証していない式の案（06_OPEN_ISSUES の G-1〜G-7、B-8 の別の選択肢）**<br>旧研究が検討だけして実装も測定もしなかった 7 件：累積の年次系列の閉形式（G-1）、建替なしを範囲比 0 で表す（G-2）、記述子で与えられる年次量の年次表を入力から外す（G-3）、出所レコードごとの入力状態の前計算（G-4）、木材の炭素貯蔵を導出係数として行テーブルに載せる（G-5）、更新時点の係数を使う場合の統合（G-6）、評価単位ごとの代理モデル（G-7）。 | [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md)<br>[`09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md`](../../09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md) | なし | B・C |

## 5. 区分 4：不具合・未解決事項

分かっている不具合、未解決の問い、限界、行っていない確認。5.1 は成果の側から見た項目、5.2 は第2回の指摘 59 件の登録簿である。

### 5.1 成果の側から見た不具合・未解決事項

#### 統制文書と手順書（T01）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R1-04](index_detail/T01_policy_protocol.md#ck-r1-04) | **手順書・指示書に対する未達と、書かれた規則と実際の食い違い**<br>手順書と指示書が求める内容のうち、第2回の検査で実際とずれていると分かった点、および確かめる手段がない点の一覧。どれも HEAD に残っている（修正は中断、記録と報告の再生成は未着手）。 | [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md)<br>[`09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md`](../../09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md)<br>ほか 3 | 独立検査（第2回）で再現 | — |

#### 評価単位の台帳・シート族・依存関係（T02）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R1-10](index_detail/T02_ledger.md#ck-r1-10) | **基準定義の穴と文面の不足（第2回「定義からの再導出」の指摘 12 件ほか）**<br>基準計算の定義と定義文について、第2回の検査が見つけた穴（不備のある入力の扱いが規約と合わない箇所、定義文がコードの動作を書いていない箇所、規約の一覧にない規約）。HEAD の基準計算と台帳に残っている。 | [`materials/round2_review/triage/rederive.md`](materials/round2_review/triage/rederive.md)<br>[`materials/round2_review/triage/records.md`](materials/round2_review/triage/records.md)<br>ほか 3 | 独立検査（第2回）で再現 | — |
| [CK-R1-16](index_detail/T02_ledger.md#ck-r1-16) | **調べていない範囲と、評価単位にしなかった計算構造**<br>旧研究が調べていないものの記録。(1) 原版ブックの数式本文は全シート族について未確認（数式ノード 3,818,483 の 100％）。原版ファイル・マニュアル・VBA はリポジトリにも研究環境にもない。 | [`09_APPROX_STUDY/01_LEDGER/README.md`](../../09_APPROX_STUDY/01_LEDGER/README.md)<br>[`09_APPROX_STUDY/01_LEDGER/considered_not_adopted.json`](../../09_APPROX_STUDY/01_LEDGER/considered_not_adopted.json)<br>ほか 3 | 独立検査（第2回）で再現（記載があることの確認） | B・C |
| [CK-R1-21](index_detail/T02_ledger.md#ck-r1-21) | **誤りまたは古いと指摘された数と記述の一覧（台帳・順位・関連する報告）**<br>台帳と順位、およびそれを引用する報告のうち、第2回の検査が誤りまたは古いと指摘した数と記述を 1 か所にまとめたもの。どれも HEAD に残っている（直す段階 b3 と報告の再生成は未着手）。 | [`09_APPROX_STUDY/01_LEDGER/units.json`](../../09_APPROX_STUDY/01_LEDGER/units.json)<br>[`09_APPROX_STUDY/01_LEDGER/README.md`](../../09_APPROX_STUDY/01_LEDGER/README.md)<br>ほか 7 | 独立検査（第2回）で再現 | — |
| [CK-R7-30](index_detail/T02_ledger.md#ck-r7-30) | **台帳と記録の古い欄・食い違う欄**<br>台帳（units.json）と、それを写した報告書に残っている、現在のコードや測定と合わない記述。 | [`09_APPROX_STUDY/01_LEDGER/units.json`](../../09_APPROX_STUDY/01_LEDGER/units.json)<br>[`09_APPROX_STUDY/01_LEDGER/README.md`](../../09_APPROX_STUDY/01_LEDGER/README.md)<br>ほか 2 | 独立検査（第2回）で再現（第2検証者なし） | B・C |

#### 基準計算と規約（T04）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R2-03](index_detail/T04_reference_calculation.md#ck-r2-03) | **時間の規約のナイフエッジ（周期 1.000000001 で年の割り当てが丸めで決まる）**<br>浮動小数点で 周期×(1 − 1e-9) がちょうど 1.0 に丸まる周期（倍精度値 1.000000001、16 進で 0x1.000000044b830p+0）では、事象の属する年が丸めで決まり、基準計算のループの結果が、書かれた規約を厳密な有理数で計算した結果と食い違う。 | [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../09_APPROX_STUDY/research_code/refcalc/base.py)<br>[`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../09_APPROX_STUDY/research_code/refcalc/units_b.py)<br>ほか 2 | 独立検査（第2回）で再現 | — |
| [CK-R2-05](index_detail/T04_reference_calculation.md#ck-r2-05) | **完全性の印の穴（データの流れを追っていない。B3・B5、SUM-08、B2-01）**<br>対象段階に B3 または B5 があり、その上流の段階（A1-A3。B5 では A4・A5・C も）が対象外のとき、上流の行が除外されて B3・B5 の値が下がっても、complete は真、incomplete_units は空のままになる。 | [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py)<br>[`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../09_APPROX_STUDY/research_code/refcalc/units_b.py)<br>ほか 1 | 独立検査（第2回）で再現 | — |
| [CK-R2-07](index_detail/T04_reference_calculation.md#ck-r2-07) | **不正な値の扱いの穴（検査されない値、無効な周期、例外、ゲートとの食い違い）**<br>コミット版の基準計算には、検査なしで演算に使われる数値入力と、例外で止まる入力がある。(a) 年次量、電力係数（系列と工事期間の値）、係数値、ガス別量、換算倍率は、負・NaN・無限大でもそのまま掛けられ、件数も印も SYS-01〜03 も反応しない。 | [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../09_APPROX_STUDY/research_code/refcalc/base.py)<br>[`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py)<br>ほか 4 | 独立検査（第2回）で再現 | — |
| [CK-R2-09](index_detail/T04_reference_calculation.md#ck-r2-09) | **定義文とコードの食い違い、定義文に無い動作、数値上の限界（基準計算の側）**<br>基準計算の定義文（説明文）とコードの間、または定義の内部に残っている食い違いの一覧。X-04 は定義文で「一致することを確かめる」と言うが検査結果を返さない。B4-02・B3 の「製造排出」に未数量分 A13-04 が入るかが文から決まらない。 | [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py)<br>[`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../09_APPROX_STUDY/research_code/refcalc/units_b.py)<br>ほか 3 | 独立検査（第2回）で再現 | — |
| [CK-R2-10](index_detail/T04_reference_calculation.md#ck-r2-10) | **基準計算について検証できていないこと（06_OPEN_ISSUES の D）**<br>基準計算の精度と正しさについて、研究が自分で未検証と書いた 7 点。実建物での実用精度は対象外。他のツールの結果とは比較していない。基準計算と統合モデルはどちらも主担当（自動の AI エージェント）が書き、人による確認と手計算との全面的な照合はしていない。 | [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md) | なし | — |
| [CK-R7-19](index_detail/T04_reference_calculation.md#ck-r7-19) | **基準計算の定義の穴（不正な値・部分的な境界・検査との食い違い）**<br>第2回の検査で確認された、基準計算の定義とコードの欠陥。入力が有限で範囲内、かつ 14 段階すべてを対象にする場合には現れないが、それ以外では、合計が黙って変わる・不完全の印が付かない・全体が例外で止まる、のいずれかが起きる。 | [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../09_APPROX_STUDY/research_code/refcalc/base.py)<br>[`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py)<br>ほか 4 | 独立検査（第2回）で再現 | A・B・C |
| [CK-R7-20](index_detail/T04_reference_calculation.md#ck-r7-20) | **時間規則の端（周期 1.000000001）と、修繕の除外年の閉形式の不一致**<br>事象の属する年を ceil(τ·(1−1e-9)) で決める規約は、周期が倍精度の 1.000000001（1 値）のとき丸めに依存する。 | [`09_APPROX_STUDY/research_code/fastcalc/closed_forms.py`](../../09_APPROX_STUDY/research_code/fastcalc/closed_forms.py)<br>[`09_APPROX_STUDY/research_code/refcalc/base.py`](../../09_APPROX_STUDY/research_code/refcalc/base.py)<br>ほか 3 | 独立検査（第2回）で再現 | A・B・C |
| [CK-R7-29](index_detail/T04_reference_calculation.md#ck-r7-29) | **規約一覧に無い規約と、定義文に書かれていない挙動**<br>コードには在るが、06_OPEN_ISSUES の規約一覧（B-1〜B-21）や単位の定義文に書かれていない取り決め。値を変えるものと、出力の形だけのものがある。 | [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md)<br>[`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../09_APPROX_STUDY/research_code/refcalc/units_b.py)<br>ほか 3 | 独立検査（第2回）で再現 | B・C |

#### 架空データ・比較の仕組み・試験（T05）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R2-16](index_detail/T05_synthetic_data_harness.md#ck-r2-16) | **比較の仕組みの既知の弱点（無限大、bool、床、余分な葉）**<br>compare.py と、それを使う一致確認の 4 つの弱点。(1) 基準の葉が ±無限大で候補が NaN 以外なら合格になる（符号付き誤差が NaN になり、abs(err) > max が偽）。(2) True と 1 を等しいとみなす。 | [`09_APPROX_STUDY/research_code/common/compare.py`](../../09_APPROX_STUDY/research_code/common/compare.py)<br>[`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../09_APPROX_STUDY/research_code/bench/verify_unified.py)<br>ほか 1 | 独立検査（第2回）で再現 | — |

#### 統合モデル K1〜K7 と導出（T06）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R3-24](index_detail/T06_unified_models.md#ck-r3-24) | **「仕組みの確認」の根拠が手で置いた計数である問題**<br>記録が述べる仕組み（係数を行ごとに掛けない、年ごとの繰り返しをしない、など）を「統合モデル自身が数えた回数」で確かめる、とする仕掛け。 | [`09_APPROX_STUDY/research_code/fastcalc/engine.py`](../../09_APPROX_STUDY/research_code/fastcalc/engine.py)<br>[`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../09_APPROX_STUDY/research_code/bench/verify_unified.py)<br>ほか 3 | 独立検査（第2回）で再現 | — |
| [CK-R3-25](index_detail/T06_unified_models.md#ck-r3-25) | **統合の件数「66 単位が 7 つの統合モデルに」「計算の定義の数 70 → 11」**<br>報告書の見出しの数字。70 評価単位のうち 66 単位が K1〜K7（26・9・10・4・8・3・6）に統合され、統合しなかったのは C-05、QA-02、STO-01、SYS-01 の 4 単位、とする。 | [`09_APPROX_STUDY/03_MODELS/README.md`](../../09_APPROX_STUDY/03_MODELS/README.md)<br>[`09_APPROX_STUDY/03_MODELS/models.json`](../../09_APPROX_STUDY/03_MODELS/models.json)<br>ほか 1 | 独立検査（第2回）で再現 | — |

#### 厳密一致・負荷・入力の測定と反例（T07）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R3-27](index_detail/T07_exactness_load.md#ck-r3-27) | **反例：周期 1.000000001 で修繕（B3-01）が基準計算と食い違う**<br>不備のない有効な入力で、更新周期（資材の更新周期または設備の耐用年数）が倍精度値 1.000000001 のとき、統合モデルの B3-01 と、B3 を含むすべての合計が基準計算と食い違う。 | [`09_APPROX_STUDY/research_code/fastcalc/closed_forms.py`](../../09_APPROX_STUDY/research_code/fastcalc/closed_forms.py)<br>[`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md)<br>ほか 2 | 独立検査（第2回）で再現 | A・B・C |
| [CK-R3-28](index_detail/T07_exactness_load.md#ck-r3-28) | **不備のある入力・特殊な入力での食い違い（NUM-2〜NUM-9）**<br>統合モデルと基準計算が、値・合否・例外の出方で食い違う入力の群。(NUM-2) 範囲の検査がない項目の NaN・無限大：1 項目ずつ変える 3,461 件のうち 212 件が食い違い（電力係数の記述子の NaN で統合モデルだけ例外、QA-01 の合否、B5-01 が 0.0 と nan）。 | [`materials/round2_review/triage/numeric.md`](materials/round2_review/triage/numeric.md)<br>[`09_APPROX_STUDY/research_code/fastcalc/engine.py`](../../09_APPROX_STUDY/research_code/fastcalc/engine.py)<br>ほか 1 | 独立検査（第2回）で再現 | A・B・C |
| [CK-R3-29](index_detail/T07_exactness_load.md#ck-r3-29) | **条件の悪い入力での限界（NUM-10：桁落ち・桁あふれ）**<br>有限の入力でも、研究自身の比較規則（床あり、許容差 1e-9）で差が 1e-9 を超える場合。(a) 施設管理比 1.0 で燃料の使用をごく小さくした場合：1e-7 倍で X-02 の B6 が 5.0e-8 ずれ、QA-01 の合否も違う（1e-6 倍から現れる。 | [`materials/round2_review/triage/numeric.md`](materials/round2_review/triage/numeric.md)<br>[`09_APPROX_STUDY/research_code/fastcalc/closed_forms.py`](../../09_APPROX_STUDY/research_code/fastcalc/closed_forms.py) | 独立検査（第2回）で再現 | A・B・C |
| [CK-R3-30](index_detail/T07_exactness_load.md#ck-r3-30) | **一致の確認に使った比較の弱点（NUM-11：床、無限大、真偽値、余分な葉）**<br>common/compare.py の比較と、bench/verify_unified.py での使い方の弱点。(1) 基準側が ±inf のとき、相手が何であっても合格になる（誤差が NaN になり、比較が偽になる）。(2) 真偽値 True と整数 1 を等しいとみなす。 | [`09_APPROX_STUDY/research_code/bench/verify_unified.py`](../../09_APPROX_STUDY/research_code/bench/verify_unified.py)<br>[`materials/round2_review/triage/numeric.md`](materials/round2_review/triage/numeric.md) | 独立検査（第2回）で再現 | A・B・C |

#### 近似検証（M3〜M6）（T08）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R4-03](index_detail/T08_approximation.md#ck-r4-03) | **誤差測定方法の確認済みの欠陥（第2回の指摘）**<br>近似検証の測定の定義と表示にある欠陥の一覧。数値の再現性の問題ではなく、「何を測ったか」と「何と書いたか」の食い違いである。(1) 電力の候補（AP-08・09a・09b・09c・13）の基準量は B6-03（= 段階 B6 ＋ 段階 B2）なのに「B6 段階」と表示。 | [`materials/round2_review/triage/approx.md`](materials/round2_review/triage/approx.md)<br>[`materials/round2_review/triage/reports.md`](materials/round2_review/triage/reports.md)<br>ほか 3 | 独立検査（第2回）で再現 | A・B・C |
| [CK-R4-25](index_detail/T08_approximation.md#ck-r4-25) | **架空データでは近似の実用精度を確立できない、という限界**<br>近似候補の誤差はすべて架空の母集団上の値で、実建物での精度を示さない。保留の 16 候補はこの理由で結論を出していない。架空データの測定は候補を否定できるが、精度を確立することはできない。 | [`09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md`](../../09_APPROX_STUDY/00_POLICY/EVALUATION_PROTOCOL.md)<br>[`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)<br>ほか 3 | 独立検査（第2回）で確認（否定されていない） | A・B・C |
| [CK-R4-26](index_detail/T08_approximation.md#ck-r4-26) | **近似の段階の網羅性の不足（測定なしの見送り、建物水準の候補の付け替え）**<br>M3〜M6 の単位×段階 280 のうち 204 は、測定をせずに理由だけで見送った「候補なし」（NOT_APPLICABLE）である。M5 の理由 66 件中 54 件、M6 の理由 65 件中 51 件は同じ定型文。17 単位は測定した近似候補が 1 つも無いまま「検証完了」になっている。 | [`09_APPROX_STUDY/03_MODELS/records/units.json`](../../09_APPROX_STUDY/03_MODELS/records/units.json)<br>[`09_APPROX_STUDY/03_MODELS/README.md`](../../09_APPROX_STUDY/03_MODELS/README.md)<br>ほか 4 | 独立検査（第2回）で再現 | B・C |

#### 記録・進捗台帳・報告書・必須成果物（T09）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R5-04](index_detail/T09_records_reports.md#ck-r5-04) | **成功記録の裏付けの表示の誤り（「3 つの裏付け」と、仕組みの計数）**<br>記録・報告書・手順書は「成功の記録は、出力の一致・仕組みの計数・導出の 3 つで機械的に裏付けた」と述べているが、実際にはそうなっていないという不具合。仕組みの計数は、統合モデルが決まった位置で増やす数で、主張に反する動作があっても変わらないものを含む。 | [`09_APPROX_STUDY/03_MODELS/records/units.json`](../../09_APPROX_STUDY/03_MODELS/records/units.json)<br>[`09_APPROX_STUDY/03_MODELS/README.md`](../../09_APPROX_STUDY/03_MODELS/README.md)<br>ほか 4 | 独立検査（第2回）で再現（REC-4・REC-5・REC-9 は CONFIRMED、REC-3 は PARTLY_CONFIRMED。 | — |
| [CK-R5-09](index_detail/T09_records_reports.md#ck-r5-09) | **状態別の件数 3／66／0／0／0／1 のうち、第2回の指摘と矛盾する数**<br>進捗台帳、PROGRESS.md、第9章 README、05_DECISIONS/README.md が掲げる状態別の件数（検証完了・簡略化成功 3、検証完了・統合成功 66、検証完了・近似不採用 0、検証中 0、未検証 0、データ・権利上の制約により保留 1、合計 70）を、第2回の指摘に照らして 1 つずつ見たもの。 | [`09_APPROX_STUDY/05_DECISIONS/progress_ledger.json`](../../09_APPROX_STUDY/05_DECISIONS/progress_ledger.json)<br>[`09_APPROX_STUDY/05_DECISIONS/PROGRESS.md`](../../09_APPROX_STUDY/05_DECISIONS/PROGRESS.md)<br>ほか 2 | 独立検査（第2回）で再現（REC-2 は第2検証で CONFIRMED。 | — |
| [CK-R5-12](index_detail/T09_records_reports.md#ck-r5-12) | **README の要点 2「66 単位が 7 つの統合モデルに、結果を変えずにまとまった」**<br>第9章 README「結果の要点」の 2。全文：「独立概念モデルでは、66 単位が 7 つの統合モデルに、結果を変えずにまとまった（統合されなかったのは 4 単位）。排出と集計は『表ごとに 活動量×係数 を足す』1 つの形と、評価期間に依存する数個の乗数の関数で書ける。 | [`09_APPROX_STUDY/README.md`](../../09_APPROX_STUDY/README.md)<br>[`09_APPROX_STUDY/03_MODELS/README.md`](../../09_APPROX_STUDY/03_MODELS/README.md)<br>ほか 2 | 独立検査（第2回）で否定（REC-2 は CONFIRMED。 | A・C |
| [CK-R5-21](index_detail/T09_records_reports.md#ck-r5-21) | **評価者の提案との対照（judge_proposal_trace.json）：観点と段階の対応づけの誤り**<br>評価軸 B の採点（3 者の中央値）で 2 点以上だった単位について、対応する段階に何を記録したかの対照表（52 行。うち測定なしが 20 行）と、第1回の検査が「取り上げていない」と指摘した具体的な提案 10 件の扱いの一覧。build_records.py が生成する。 | [`09_APPROX_STUDY/03_MODELS/judge_proposal_trace.json`](../../09_APPROX_STUDY/03_MODELS/judge_proposal_trace.json)<br>[`09_APPROX_STUDY/research_code/tools/build_records.py`](../../09_APPROX_STUDY/research_code/tools/build_records.py)<br>ほか 2 | 独立検査（第2回）で再現（REP-2。第2検証がなく、主担当が検査担当のスクリプトを再実行して再現） | — |
| [CK-R5-22](index_detail/T09_records_reports.md#ck-r5-22) | **未解決事項の一覧（06_OPEN_ISSUES/README.md の A〜H）**<br>旧指示書の成果物 9 に当たる手書きの一覧。 | [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md) | 作成者のみ（B-7・B-10・B-11 の数字は独立検査（第2回）で再現） | A・B・C |
| [CK-R5-23](index_detail/T09_records_reports.md#ck-r5-23) | **未解決事項の一覧に載っていない事項と、古くなった記述（第2回で判明）**<br>第2回の検査で確認されたが、06_OPEN_ISSUES/README.md にも、ほかの 09_APPROX_STUDY の文書にも書かれていない規約・穴・限界と、古くなった記述の一覧。 | [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md)<br>[`materials/round2_review/triage/reports.md`](materials/round2_review/triage/reports.md)<br>ほか 4 | 独立検査（第2回）で再現（RED-3・RED-11 は PARTLY_CONFIRMED、ほかは CONFIRMED。 | A・B・C |
| [CK-R5-25](index_detail/T09_records_reports.md#ck-r5-25) | **検査の記録の欠落と、検査されていない範囲**<br>(1) 第2回の独立検査（指摘 59 件：NUM 11、RED 12、REC 9、APP 9、REP 18。判定は CONFIRMED 33、PARTLY_CONFIRMED 8、反証 0。REP の 18 件は第2の検証担当なし）が、09_APPROX_STUDY のどの文書にも記録されていない。 | [`09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md`](../../09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md)<br>[`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md)<br>ほか 3 | 独立検査（第2回）の記録と、停止を実施した作業担当の記録（第三者の確認ではない） | — |

#### 材料分類の設計草案（T10）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R5-28](index_detail/T10_material_taxonomy.md#ck-r5-28) | **材料分類の設計草案の未解決事項と、行っていない確認**<br>草案自身が挙げる未解決事項 26 件（U-01〜U-26）、必要なデータ 8 件（D-1〜D-8）、実データが届いたら測るとした指標（どれも未測定）と、行っていない確認の一覧。 | [`09_APPROX_STUDY/07_MATERIAL_TAXONOMY/README.md`](../../09_APPROX_STUDY/07_MATERIAL_TAXONOMY/README.md)<br>[`09_APPROX_STUDY/07_MATERIAL_TAXONOMY/REVIEW_LOG.md`](../../09_APPROX_STUDY/07_MATERIAL_TAXONOMY/REVIEW_LOG.md)<br>ほか 1 | 作成者のみ | B・C |

#### 中断した修正（65ff124）と未実施の改訂（T11）

| 項目 | 成果と内容 | 所在（主なもの） | 確かめた者 | 再利用 |
|---|---|---|---|---|
| [CK-R2-24](index_detail/T11_interrupted_fix.md#ck-r2-24) | **中断した修正 a1 に残る未解決事項と副作用（自己申告の open_problems）**<br>a1 が自分の報告に残した未解決の点。(1) NUM-10 の限界は指示どおり変えていない：施設管理の比率 1.0 で燃料が 1e-6 倍以下、1e-8 だけ違う基準案、1e308 付近の桁あふれ、漏洩率が 1 から 1e-8 以内で補充なし。 | [`materials/interrupted_fix/agent_reports/A1_REPORT.json`](materials/interrupted_fix/agent_reports/A1_REPORT.json)<br>[`STOP_STATUS.md`](STOP_STATUS.md)<br>ほか 1 | 中断した修正の自己申告 | — |

### 5.2 第2回の独立検査の指摘 59 件（登録簿）

第2回の独立検査は、`43ba5d7` のコードと文書に対して 5 つの観点で行った。指摘は 59 件で、反証検査担当が退けたものは無い。公開中の `09_APPROX_STUDY/` には **59 件とも残っている**（修正は反映されていない）。指摘ごとの内容・再現の手順の所在・停止時点の状態は [index_detail/FINDINGS_59.md](index_detail/FINDINGS_59.md) にある。

| 分け方 | 件数 |
|---|---|
| 判定 | 反証検査で確認 33、一部確認（訂正つき）8、反証検査なし（REP の 18 件。主担当が検査のスクリプトを再実行して再現、出力は未保存）18 |
| 検査担当が付けた重さ | 高 3（NUM-1、RED-1、REC-1）、中 27、低 29 |
| 停止時点の状態 | 中断時の編集で対応（自己申告・未検証） 38、対応しない（文書化のみの予定で未実施） 1、未対応 10、途中で停止 10 |

| 群 | まとまり | 指摘 |
|---|---|---|
| 1 | 「どの入力でも基準計算と一致する」は言えない（一致を確かめたのは整った入力の範囲） | [NUM-1](index_detail/FINDINGS_59.md#num-1)、[REC-1](index_detail/FINDINGS_59.md#rec-1)、[NUM-2](index_detail/FINDINGS_59.md#num-2)、[NUM-3](index_detail/FINDINGS_59.md#num-3)、[NUM-4](index_detail/FINDINGS_59.md#num-4)、[NUM-5](index_detail/FINDINGS_59.md#num-5)、[NUM-6](index_detail/FINDINGS_59.md#num-6)、[NUM-7](index_detail/FINDINGS_59.md#num-7)、[NUM-8](index_detail/FINDINGS_59.md#num-8)、[NUM-9](index_detail/FINDINGS_59.md#num-9)、[NUM-10](index_detail/FINDINGS_59.md#num-10) |
| 2 | 基準計算の定義の穴と、一覧にない取り決め（両方の計算が同じ穴を持つ） | [RED-1](index_detail/FINDINGS_59.md#red-1)、[RED-2](index_detail/FINDINGS_59.md#red-2)、[RED-3](index_detail/FINDINGS_59.md#red-3)、[RED-4](index_detail/FINDINGS_59.md#red-4)、[RED-5](index_detail/FINDINGS_59.md#red-5)、[RED-6](index_detail/FINDINGS_59.md#red-6)、[RED-7](index_detail/FINDINGS_59.md#red-7)、[RED-8](index_detail/FINDINGS_59.md#red-8)、[RED-9](index_detail/FINDINGS_59.md#red-9)、[RED-10](index_detail/FINDINGS_59.md#red-10)、[RED-11](index_detail/FINDINGS_59.md#red-11)、[RED-12](index_detail/FINDINGS_59.md#red-12)、[REP-17](index_detail/FINDINGS_59.md#rep-17) |
| 3 | 検証が覆っている範囲と、検証の道具の限界 | [NUM-11](index_detail/FINDINGS_59.md#num-11)、[REP-16](index_detail/FINDINGS_59.md#rep-16)、[REC-6](index_detail/FINDINGS_59.md#rec-6)、[REP-15](index_detail/FINDINGS_59.md#rep-15) |
| 4 | 「66 単位が 7 つの統合モデルに」「70 → 11」の数え方 | [REC-2](index_detail/FINDINGS_59.md#rec-2)、[REP-4](index_detail/FINDINGS_59.md#rep-4)、[REC-7](index_detail/FINDINGS_59.md#rec-7)、[REP-9](index_detail/FINDINGS_59.md#rep-9) |
| 5 | 仕組みの確認（演算回数の計数）と SUCCESS 記録の裏付け | [REC-3](index_detail/FINDINGS_59.md#rec-3)、[REC-4](index_detail/FINDINGS_59.md#rec-4)、[REC-5](index_detail/FINDINGS_59.md#rec-5)、[REP-3](index_detail/FINDINGS_59.md#rep-3)、[REC-9](index_detail/FINDINGS_59.md#rec-9)、[REP-12](index_detail/FINDINGS_59.md#rep-12) |
| 6 | 近似検証の測定の定義（基準量、合計への影響、標本内のパラメータ） | [APP-1](index_detail/FINDINGS_59.md#app-1)、[APP-2](index_detail/FINDINGS_59.md#app-2)、[APP-3](index_detail/FINDINGS_59.md#app-3)、[APP-4](index_detail/FINDINGS_59.md#app-4)、[APP-5](index_detail/FINDINGS_59.md#app-5)、[APP-6](index_detail/FINDINGS_59.md#app-6)、[APP-7](index_detail/FINDINGS_59.md#app-7)、[APP-8](index_detail/FINDINGS_59.md#app-8)、[APP-9](index_detail/FINDINGS_59.md#app-9) |
| 7 | 近似の段階（M3〜M6）の記録の範囲と、進捗の件数 | [REP-5](index_detail/FINDINGS_59.md#rep-5)、[REP-6](index_detail/FINDINGS_59.md#rep-6)、[REC-8](index_detail/FINDINGS_59.md#rec-8)、[REP-14](index_detail/FINDINGS_59.md#rep-14)、[REP-2](index_detail/FINDINGS_59.md#rep-2)、[REP-13](index_detail/FINDINGS_59.md#rep-13) |
| 8 | 台帳・入力項目・報告書の数値と文言の誤り | [REP-1](index_detail/FINDINGS_59.md#rep-1)、[REP-7](index_detail/FINDINGS_59.md#rep-7)、[REP-8](index_detail/FINDINGS_59.md#rep-8)、[REP-10](index_detail/FINDINGS_59.md#rep-10)、[REP-11](index_detail/FINDINGS_59.md#rep-11)、[REP-18](index_detail/FINDINGS_59.md#rep-18) |

| 指摘 | 重さ | 判定 | 予定の段階 | 停止時点の状態 |
|---|---|---|---|---|
| [NUM-1](index_detail/FINDINGS_59.md#num-1) | 高 | 反証検査で確認 | a1 | 中断時の編集で対応（自己申告・未検証） |
| [NUM-2](index_detail/FINDINGS_59.md#num-2) | 中 | 反証検査で確認 | a1 | 中断時の編集で対応（自己申告・未検証） |
| [NUM-3](index_detail/FINDINGS_59.md#num-3) | 中 | 反証検査で確認 | a1 | 中断時の編集で対応（自己申告・未検証） |
| [NUM-4](index_detail/FINDINGS_59.md#num-4) | 中 | 反証検査で確認 | a1 | 中断時の編集で対応（自己申告・未検証） |
| [NUM-5](index_detail/FINDINGS_59.md#num-5) | 中 | 反証検査で確認 | a1 | 中断時の編集で対応（自己申告・未検証） |
| [NUM-6](index_detail/FINDINGS_59.md#num-6) | 低 | 反証検査で確認 | a1 | 中断時の編集で対応（自己申告・未検証） |
| [NUM-7](index_detail/FINDINGS_59.md#num-7) | 低 | 反証検査で確認 | a1 | 中断時の編集で対応（自己申告・未検証） |
| [NUM-8](index_detail/FINDINGS_59.md#num-8) | 低 | 反証検査で確認 | a1 | 中断時の編集で対応（自己申告・未検証） |
| [NUM-9](index_detail/FINDINGS_59.md#num-9) | 低 | 反証検査で確認 | a1 | 中断時の編集で対応（自己申告・未検証） |
| [NUM-10](index_detail/FINDINGS_59.md#num-10) | 低 | 反証検査で確認 | a1 | 対応しない（文書化のみの予定で未実施） |
| [NUM-11](index_detail/FINDINGS_59.md#num-11) | 低 | 反証検査で確認 | a1 | 中断時の編集で対応（自己申告・未検証） |
| [RED-1](index_detail/FINDINGS_59.md#red-1) | 高 | 反証検査で確認 | a1 | 中断時の編集で対応（自己申告・未検証） |
| [RED-2](index_detail/FINDINGS_59.md#red-2) | 中 | 反証検査で確認 | a1 | 中断時の編集で対応（自己申告・未検証） |
| [RED-3](index_detail/FINDINGS_59.md#red-3) | 中 | 一部確認（訂正つき） | a1 | 中断時の編集で対応（自己申告・未検証） |
| [RED-4](index_detail/FINDINGS_59.md#red-4) | 中 | 反証検査で確認 | a1 | 中断時の編集で対応（自己申告・未検証） |
| [RED-5](index_detail/FINDINGS_59.md#red-5) | 中 | 反証検査で確認 | a1 | 中断時の編集で対応（自己申告・未検証） |
| [RED-6](index_detail/FINDINGS_59.md#red-6) | 中 | 反証検査で確認 | a1 | 中断時の編集で対応（自己申告・未検証） |
| [RED-7](index_detail/FINDINGS_59.md#red-7) | 中 | 反証検査で確認 | a1 | 中断時の編集で対応（自己申告・未検証） |
| [RED-8](index_detail/FINDINGS_59.md#red-8) | 中 | 反証検査で確認 | a1 | 中断時の編集で対応（自己申告・未検証） |
| [RED-9](index_detail/FINDINGS_59.md#red-9) | 低 | 一部確認（訂正つき） | a1 | 中断時の編集で対応（自己申告・未検証） |
| [RED-10](index_detail/FINDINGS_59.md#red-10) | 低 | 反証検査で確認 | a1 | 中断時の編集で対応（自己申告・未検証） |
| [RED-11](index_detail/FINDINGS_59.md#red-11) | 低 | 一部確認（訂正つき） | a1 | 中断時の編集で対応（自己申告・未検証） |
| [RED-12](index_detail/FINDINGS_59.md#red-12) | 低 | 反証検査で確認 | a1 | 中断時の編集で対応（自己申告・未検証） |
| [REC-1](index_detail/FINDINGS_59.md#rec-1) | 高 | 反証検査で確認 | a1 | 中断時の編集で対応（自己申告・未検証） |
| [REC-2](index_detail/FINDINGS_59.md#rec-2) | 中 | 反証検査で確認 | a2 | 途中で停止 |
| [REC-3](index_detail/FINDINGS_59.md#rec-3) | 中 | 一部確認（訂正つき） | a2 | 途中で停止 |
| [REC-4](index_detail/FINDINGS_59.md#rec-4) | 中 | 反証検査で確認 | a2 | 途中で停止 |
| [REC-5](index_detail/FINDINGS_59.md#rec-5) | 中 | 反証検査で確認 | a2 | 途中で停止 |
| [REC-6](index_detail/FINDINGS_59.md#rec-6) | 中 | 一部確認（訂正つき） | a2 | 途中で停止 |
| [REC-7](index_detail/FINDINGS_59.md#rec-7) | 低 | 反証検査で確認 | a2 | 途中で停止 |
| [REC-8](index_detail/FINDINGS_59.md#rec-8) | 低 | 反証検査で確認 | b2 | 中断時の編集で対応（自己申告・未検証） |
| [REC-9](index_detail/FINDINGS_59.md#rec-9) | 低 | 反証検査で確認 | a2 | 途中で停止 |
| [APP-1](index_detail/FINDINGS_59.md#app-1) | 中 | 一部確認（訂正つき） | b2 | 中断時の編集で対応（自己申告・未検証） |
| [APP-2](index_detail/FINDINGS_59.md#app-2) | 中 | 反証検査で確認 | b2 | 中断時の編集で対応（自己申告・未検証） |
| [APP-3](index_detail/FINDINGS_59.md#app-3) | 中 | 反証検査で確認 | b2 | 中断時の編集で対応（自己申告・未検証） |
| [APP-4](index_detail/FINDINGS_59.md#app-4) | 中 | 一部確認（訂正つき） | b2 | 中断時の編集で対応（自己申告・未検証） |
| [APP-5](index_detail/FINDINGS_59.md#app-5) | 低 | 反証検査で確認 | b2 | 中断時の編集で対応（自己申告・未検証） |
| [APP-6](index_detail/FINDINGS_59.md#app-6) | 低 | 反証検査で確認 | b2 | 中断時の編集で対応（自己申告・未検証） |
| [APP-7](index_detail/FINDINGS_59.md#app-7) | 低 | 反証検査で確認 | b2 | 中断時の編集で対応（自己申告・未検証） |
| [APP-8](index_detail/FINDINGS_59.md#app-8) | 低 | 一部確認（訂正つき） | b2 | 中断時の編集で対応（自己申告・未検証） |
| [APP-9](index_detail/FINDINGS_59.md#app-9) | 低 | 反証検査で確認 | b2 | 中断時の編集で対応（自己申告・未検証） |
| [REP-1](index_detail/FINDINGS_59.md#rep-1) | 中 | 反証検査なし | b3 | 未対応 |
| [REP-2](index_detail/FINDINGS_59.md#rep-2) | 中 | 反証検査なし | C | 未対応 |
| [REP-3](index_detail/FINDINGS_59.md#rep-3) | 中 | 反証検査なし | C | 未対応 |
| [REP-4](index_detail/FINDINGS_59.md#rep-4) | 中 | 反証検査なし | a2 | 途中で停止 |
| [REP-5](index_detail/FINDINGS_59.md#rep-5) | 中 | 反証検査なし | b2 | 中断時の編集で対応（自己申告・未検証） |
| [REP-6](index_detail/FINDINGS_59.md#rep-6) | 中 | 反証検査なし | b2 | 中断時の編集で対応（自己申告・未検証） |
| [REP-7](index_detail/FINDINGS_59.md#rep-7) | 中 | 反証検査なし | b3 | 未対応 |
| [REP-8](index_detail/FINDINGS_59.md#rep-8) | 低 | 反証検査なし | b3 | 未対応 |
| [REP-9](index_detail/FINDINGS_59.md#rep-9) | 低 | 反証検査なし | C | 未対応 |
| [REP-10](index_detail/FINDINGS_59.md#rep-10) | 低 | 反証検査なし | C | 途中で停止 |
| [REP-11](index_detail/FINDINGS_59.md#rep-11) | 低 | 反証検査なし | C | 未対応 |
| [REP-12](index_detail/FINDINGS_59.md#rep-12) | 低 | 反証検査なし | a2 | 途中で停止 |
| [REP-13](index_detail/FINDINGS_59.md#rep-13) | 低 | 反証検査なし | b2 | 中断時の編集で対応（自己申告・未検証） |
| [REP-14](index_detail/FINDINGS_59.md#rep-14) | 低 | 反証検査なし | C | 未対応 |
| [REP-15](index_detail/FINDINGS_59.md#rep-15) | 低 | 反証検査なし | C | 未対応 |
| [REP-16](index_detail/FINDINGS_59.md#rep-16) | 低 | 反証検査なし | a1 | 中断時の編集で対応（自己申告・未検証） |
| [REP-17](index_detail/FINDINGS_59.md#rep-17) | 低 | 反証検査なし | a1 | 中断時の編集で対応（自己申告・未検証） |
| [REP-18](index_detail/FINDINGS_59.md#rep-18) | 低 | 反証検査なし | b3 | 未対応 |

## 6. 区分 5：新研究への再利用候補

再利用の印は、区分 1〜4 に重ねて付けた。**区分 2〜4 の項目を再利用しても、その項目が検証済みになるわけではない。** 新研究で使う場合は、新研究の側で改めて確かめ、未検証のものを検証済みとして扱わない。

### 6.1 研究ルートと、使ってよい基準

| ルート | 旧研究の成果の使い方 |
|---|---|
| A 既存の簡素化モデルを使う | 統合モデル K1〜K7 と導出 D1〜D8 を出発点にする。使えるのは、所属が確かめられた単位と、総当たりで確かめられた閉形式に限る。「66 単位」「70 → 11」は使わない |
| B 元の式から作り直す | 台帳の定義文（`reference_semantics`）、依存関係（`depends_on`）、基準計算を出発点にする。統合モデルには拘束されない。旧研究の式の族（6.2）は整理用の区分として参考にする |
| C 混合 | A と B を単位や式の族ごとに使い分ける |

どのルートでも、誤差を測る基準は**公開中の版の基準計算**（`09_APPROX_STUDY/research_code/refcalc/`）である。これを変更しない。基準計算の値を正として使えるのは、次の範囲である。

- 入力が有限で範囲内であること（負・NaN・無限大の年次量、電力係数、係数の値、換算倍率を含まない）
- 14 段階すべてを含む境界、または不備のない入力での段階の部分集合
- 周期と評価期間が、時間の判定の端（倍精度の 1.000000001 のような値）に当たらないこと
- 生成器が作る範囲の値であること（極端な桁の値では桁落ち・桁あふれがある）

この範囲の外では、基準計算の値そのものが定義文と食い違うか、印なしに一部を除いた値になる（5.2 節の群 1・2）。新研究では、範囲の外の入力を比較から外すか、既知の例外として扱うかを、測定の前に決めて記録する。

### 6.2 構造の棚卸しの要点（観点 R7。新研究の方程式の分類の材料）

- 評価単位 70 件の依存関係は 183 辺、閉路なし、深さ 0〜7。29 単位が段階の集計（X-02）に入り、合計（SUM-03）の上流は 37 単位である（CK-R7-02、区分 1）。
- 分類担当は、定義文とコードの読み取りから、70 単位を 11 の「式の族」に整理した：行の和 19、行ごとの数量の比 2、加重和・行列の展開 6、事象の数え上げ 6、年重み付き和 13、係数の年次系列 1、冷媒の漸化式 3、比・指標 4、集約の木 5、基準案との比較 1、条件分岐・述語 10。**この族は分類担当が付けた整理用の区分で、旧研究の成果物には無く、独立の検査も受けていない**（CK-R7-04〜14、区分 2）。
- 台帳の構造分類（`structure_class`）は、単位から数えると「活動量×係数の総和」30、「比・換算」10 である。台帳の見出しの 29・11 は古い。
- 式の変形として確立しているもの（区分 1）と、架空データで観測しただけのもの（係数キーや周期の種類が行数より少ないこと、負荷の削減率、入力が減らないこと）を区別する。後者は構造の性質としては使えない。
- 旧研究の近似候補 32 件に、変換（フーリエ、ラプラス、特異値分解、母関数など）に基づくものは無い（候補の題名の検索による。分類担当の読み取り）。
- 近似候補の測定は、新研究にとっては**反例の資料**である。回数関数の滑らかな置き換え（AP-01〜03）、評価期間についての補間（AP-14）、積の和を平均の積で置き換える形（AP-17、AP-08、AP-18c。誤差は標本の共分散に等しい）、ほかの建物の代表値を使う区分パラメータ（AP-18b で −41％〜+337％）は、架空の母集団で大きく外れた。
- 「厳密な式が同じ手間で使えるので近似の利点なし」という旧研究の不採用の理由は、変換の種類を減らすことを優先する新研究では前提が違う。そのまま引き継がない。

### 6.3 再利用候補の一覧（主題別）

「使い道」は冒頭だけを載せた。全文と、使う条件・注意は、各項目の詳細（項目の番号から開く）にある。**条件・注意を読まずに使わないこと。**

#### 統制文書と手順書（T01）

| 項目 | 区分 | ルート | 成果 | 使い道（冒頭） |
|---|---|---|---|---|
| [CK-R1-02](index_detail/T01_policy_protocol.md#ck-r1-02) | 2 | A・B・C | 研究プロトコル EVALUATION_PROTOCOL.md（v1.4 草稿。使われた規則と草稿の部分） | 新研究の評価手順を書くときのひな形にする。 |
| [CK-R1-03](index_detail/T01_policy_protocol.md#ck-r1-03) | 3 | A・B・C | 手順書 v1.4 で定めるとした規則と、台帳・順位・報告の未実施の修正設計 | 新研究で検証の裏付けを設計するときの案として使う：共有部品を壊して出力の変化を見る所属の確認、外側からの演算の計数、測定の範囲の 3 区分（単位・段階・建物全体）、単位ごとの入力の追跡。 |

#### 評価単位の台帳・シート族・依存関係（T02）

| 項目 | 区分 | ルート | 成果 | 使い道（冒頭） |
|---|---|---|---|---|
| [CK-R1-05](index_detail/T02_ledger.md#ck-r1-05) | 1 | A・B・C | 台帳・順位表・自動生成の報告の、数と相互参照の整合（数え直しで一致した範囲） | 旧研究の台帳・順位表の数を引用するとき、JSON と README のどちらからも同じ数が得られる根拠になる。 |
| [CK-R1-06](index_detail/T02_ledger.md#ck-r1-06) | 2 | A・B・C | 評価単位の一覧（70 件＝既存の概念式 53＋追加で特定した計算構造 17） | 新研究の「方程式グループと依存関係の分類台帳」の出発点として、単位の ID、段階、依存関係（depends_on・feeds・gated_by）を取り込む。 |
| [CK-R1-07](index_detail/T02_ledger.md#ck-r1-07) | 2 | B・C | 構造分類と形式の記述（structure_class 13 種、正規形、反復、分岐、計算量） | 新研究で式を少数の変換にまとめるとき、同じ形の式を集める最初の手がかりにする（例：活動量×係数の総和 30 件、年次の積算 4 件、周期イベント 3 件、年ごとの状態更新 1 件）。 |
| [CK-R1-08](index_detail/T02_ledger.md#ck-r1-08) | 3 | B・C | 台帳の見込み欄・提案欄・曖昧点（統合と近似の見込み、定義の提案） | 式どうしの関係についての仮説の一覧として使う（例：A13-04 の欄にある「端材の補正と未数量分の上乗せは、同じ 1 変数関数 g(x) = 1/(1−x) の 2 つの適用」という案）。 |
| [CK-R1-09](index_detail/T02_ledger.md#ck-r1-09) | 1 | A・B・C | 基準定義 reference_semantics：文面と基準計算の説明文の一致、文面からの再導出 | 新研究が変えてはならない基準計算の、文章による定義として使う。 |
| [CK-R1-14](index_detail/T02_ledger.md#ck-r1-14) | 2 | B・C | シート族の集計（198 シートを名称だけで 59 族に整理。数式ノード 3,818,483） | 旧研究が何を調べていないかを示す資料として、また原版側で繰り返しが集中する場所の代理指標として、新研究の範囲の記述に使う。 |
| [CK-R1-16](index_detail/T02_ledger.md#ck-r1-16) | 4 | B・C | 調べていない範囲と、評価単位にしなかった計算構造 | 新研究が建築 LCA の計算体系の全体を扱うとき、旧研究の 70 単位に入っていない計算構造（7 件）と、調べていない範囲を先に確認する一覧として使う。 |
| [CK-R7-01](index_detail/T02_ledger.md#ck-r7-01) | 1 | A・B・C | 台帳の束縛欄（70 単位の id・段階・基準定義文・依存） | 方程式グループの分類台帳を作るときの、単位 id・段階・定義文・依存の対応表として使う。 |
| [CK-R7-02](index_detail/T02_ledger.md#ck-r7-02) | 1 | A・B・C | 評価単位の依存グラフ（depends_on） | 方程式グループ間の依存関係の台帳、計算順序、どの単位の誤差がどこへ伝わるか（上流の行結果→B3・B4・B5→合計）を調べるときの出発点。 |
| [CK-R7-03](index_detail/T02_ledger.md#ck-r7-03) | 2 | B・C | 台帳の分析欄（構造分類 13 種・標準形・分岐・未定義点） | 式の形の一次分類（13 種）、単位ごとの繰り返しの次元（loop_dims）、未定義点の一覧（ambiguities）を、新しい分類台帳の材料にする。 |
| [CK-R7-30](index_detail/T02_ledger.md#ck-r7-30) | 4 | B・C | 台帳と記録の古い欄・食い違う欄 | 台帳を新しい分類台帳の材料にするとき、使ってはいけない欄の一覧として使う。 |

#### 着手順序（評価軸 A・B）（T03）

| 項目 | 区分 | ルート | 成果 | 使い道（冒頭） |
|---|---|---|---|---|
| [CK-R1-17](index_detail/T03_ranking.md#ck-r1-17) | 2 | A・B・C | 評価軸 A：基準計算の単位別の負荷の測定と A スコア | 基準計算のどの単位に計算が集まるかの目安として、新研究で計算の重さを比べるときの基準側の参考値にする。 |
| [CK-R1-19](index_detail/T03_ranking.md#ck-r1-19) | 3 | B・C | 評価軸 B の評価者が書いた理由と置き換え案（70 単位×3 者） | 式どうしの共通の形についての仮説の一覧として、新研究で変換の候補を探すときに読む。 |

#### 基準計算と規約（T04）

| 項目 | 区分 | ルート | 成果 | 使い道（冒頭） |
|---|---|---|---|---|
| [CK-R2-01](index_detail/T04_reference_calculation.md#ck-r2-01) | 1 | A・B・C | 基準計算の本体（70 評価単位の逐次計算。誤差と負荷を測る基準） | コミット 60e720f の refcalc を変更せずに固定の基準（誤差の分母）として使う。 |
| [CK-R2-02](index_detail/T04_reference_calculation.md#ck-r2-02) | 1 | A・B・C | 時間の規約（事象の数え方、年への割り当て、許容幅 1e-9） | 固定の基準の一部。新しいモデルが同じ回数と同じ年の割り当てを再現できるかを見る基準にする。 |
| [CK-R2-04](index_detail/T04_reference_calculation.md#ck-r2-04) | 2 | A・C | 完全性の印（X-02 の complete・incomplete_units、SUM-01〜03 の complete） | 固定の基準の出力の一部として読む。不備のない入力では常に complete が真になるので、新しいモデルとの比較では真であることの確認にだけ使う。 |
| [CK-R2-06](index_detail/T04_reference_calculation.md#ck-r2-06) | 2 | A・C | 使えない係数と不正な値の扱い（除外して数える規則。実装されている範囲） | 固定の基準の動作の一部。新しいモデルが、不備のある行を同じ条件で除外するかを見るときの参照になる。 |
| [CK-R2-08](index_detail/T04_reference_calculation.md#ck-r2-08) | 2 | A・B・C | 規約の一覧（06_OPEN_ISSUES の B-1〜B-21 と base.py 冒頭の規約文） | 新研究で「元の式」を読むときの前提の一覧として使う。 |
| [CK-R7-17](index_detail/T04_reference_calculation.md#ck-r7-17) | 1 | A・B・C | 基準計算（refcalc）のうち、定義文からの独立した書き直しと一致した 53 単位 | 新しい定式化の誤差を測るときの基準値を出す計算として使う。ルート B では、この関数群の定義文とコードが「元の式」に当たる。 |
| [CK-R7-18](index_detail/T04_reference_calculation.md#ck-r7-18) | 2 | A・B・C | 基準計算のうち、独立した書き直しがない 14 単位と、間接的な確認だけの 3 単位 | 基準値として使う場合は、この 17 単位が独立の書き直しを経ていないことを前提にする。 |
| [CK-R7-19](index_detail/T04_reference_calculation.md#ck-r7-19) | 4 | A・B・C | 基準計算の定義の穴（不正な値・部分的な境界・検査との食い違い） | 新しい定式化の定義域を決めるときの「避ける入力範囲」の一覧として使う。誤差測定の母集団からこれらの入力を外す、または「基準値なし」として扱う根拠になる。 |
| [CK-R7-20](index_detail/T04_reference_calculation.md#ck-r7-20) | 4 | A・B・C | 時間規則の端（周期 1.000000001）と、修繕の除外年の閉形式の不一致 | 時間を離散化する規約（許容幅つきの切り上げ）が、厳密な算術と浮動小数点で食い違う点の実例として使う。 |
| [CK-R7-28](index_detail/T04_reference_calculation.md#ck-r7-28) | 1 | A・B・C | 本研究が決めた規約 B-1〜B-21 のうち、第2回でコードとの符合が確認されたもの | 新しい定式化が基準計算と同じ値を出すために守る必要のある規約の一覧。特に、時間の離散化（B-1〜B-5、B-15）と段階への帰属（B-6、B-10、B-12）は式の形を直接決める。 |
| [CK-R7-29](index_detail/T04_reference_calculation.md#ck-r7-29) | 4 | B・C | 規約一覧に無い規約と、定義文に書かれていない挙動 | 元の式から組み直すとき（ルート B）、定義文と規約一覧だけでは基準計算と合わなくなる箇所の一覧として使う。 |

#### 架空データ・比較の仕組み・試験（T05）

| 項目 | 区分 | ルート | 成果 | 使い道（冒頭） |
|---|---|---|---|---|
| [CK-R2-11](index_detail/T05_synthetic_data_harness.md#ck-r2-11) | 2 | A・B・C | 架空シナリオのデータ構造（synth/model.py と JSON の入出力） | 固定の入力スキーマとして使う。新しいモデルが同じ Scenario を読めば、基準計算と同じ入力で比較できる。JSON の保存・復元でシナリオを固定できる。 |
| [CK-R2-12](index_detail/T05_synthetic_data_harness.md#ck-r2-12) | 2 | A・B・C | 架空シナリオの生成器（synth/generate.py の make_scenario） | 固定の入力生成器として使う。新しいモデルと固定の基準に同じシナリオを与える。規模 S・M・L と構造×用途 24 組で、行数や構成を変えた比較ができる。 |
| [CK-R2-13](index_detail/T05_synthetic_data_harness.md#ck-r2-13) | 2 | A・B・C | 架空シナリオの集合（標準ベンチマーク S・M・L、検証用の母集団、境界条件 32 件、基準案の登録） | 固定の評価用の集合として使う。標準ベンチマーク S・M・L は行数だけが違う 3 件で、規模への依存を見る。 |
| [CK-R2-14](index_detail/T05_synthetic_data_harness.md#ck-r2-14) | 2 | A・C | 入力を壊す操作（bench/mutations.py：36 種類の壊し方、小数境界、段階の部分集合、無効な評価期間） | 新しいモデルが、不備のある行の除外と件数を固定の基準と同じに返すかを見る入力として使える。小数境界の 5 組は、回数の端の確認に使える。 |
| [CK-R2-15](index_detail/T05_synthetic_data_harness.md#ck-r2-15) | 2 | A・B・C | 結果の比較の仕組み（common/compare.py） | 新しいモデルの出力と固定の基準の出力を葉ごとに比べる道具として使える。符号付きの誤差で過小評価を分けて集計できる。 |
| [CK-R2-17](index_detail/T05_synthetic_data_harness.md#ck-r2-17) | 2 | A・B・C | 単体試験 28 件（tests/。コミット版） | 試験が持つ期待値（手計算の例：T=10.5、周期 3.5、冷媒 1 台。小数境界の回数の表）は、固定の基準の受け入れ例として読める。 |
| [CK-R7-15](index_detail/T05_synthetic_data_harness.md#ck-r7-15) | 2 | A・B・C | 入力データモデル（Scenario：スカラー欄と表） | 新研究で基準計算に与える入力の受け口。どの入力が式に効くか（行の表、年の表、スカラー）の一覧として使う。 |
| [CK-R7-16](index_detail/T05_synthetic_data_harness.md#ck-r7-16) | 2 | A・B・C | 架空シナリオの生成器と母集団 | 新しい定式化の誤差測定と反例探索の入力に使う候補。 |
| [CK-R7-21](index_detail/T05_synthetic_data_harness.md#ck-r7-21) | 2 | A・C | 比較の仕組み（結果の leaf ごとの比較、検証の実行、入力を壊す操作） | 新しい定式化と基準計算の結果を比べる道具の候補。過小評価を符号で区別する誤差の定義（負＝過小）と、leaf ごとの比較という方式は、そのまま参照できる。 |

#### 統合モデル K1〜K7 と導出（T06）

| 項目 | 区分 | ルート | 成果 | 使い道（冒頭） |
|---|---|---|---|---|
| [CK-R3-01](index_detail/T06_unified_models.md#ck-r3-01) | 1 | A・C | 全体の形：排出＝Σ（活動量×係数）、評価期間への依存は乗数だけ | 新研究が少数の変換で書き直す対象の出発点になる。導出（式の変形）で確立している構造は 4 つ。(1) 排出は、行×係数キーの活動量の合算と係数ベクトルの積和で、線形である（D1）。 |
| [CK-R3-02](index_detail/T06_unified_models.md#ck-r3-02) | 1 | A・C | 統合モデル K1 行テーブル | E＝A·v（A は 表×係数キーの活動量、v は係数の値）という行列の形として使う。 |
| [CK-R3-03](index_detail/T06_unified_models.md#ck-r3-03) | 1 | A・C | 統合モデル K2 回数関数とライフサイクル乗数 | 周期ごとの合算 U_c が T に依存しないので、T を変える再計算は乗数の計算だけで済む（D2 の導出による）。回数は T と周期の天井関数（段差関数）。 |
| [CK-R3-04](index_detail/T06_unified_models.md#ck-r3-04) | 2 | A・C | 統合モデル K3 年重み付き和（区分的に直線な系列のモーメント） | 使うのは所属の一覧ではなく閉形式（CK-R3-13、CK-R3-14）。年次の排出は、年の重みを掛けた系列どうしの内積として書ける。 |
| [CK-R3-05](index_detail/T06_unified_models.md#ck-r3-05) | 1 | A・C | 統合モデル K4 充填サイクルの質量収支 | 機器ごとに（漏洩率、補充の有無、交換の年の並び）で決まる T の非線形関数として使う。補充なしの残存量は公比 1−r の等比で、交換の年に初期値へ戻る。 |
| [CK-R3-06](index_detail/T06_unified_models.md#ck-r3-06) | 2 | A・B・C | 統合モデル K5 指標（段階ベクトルの線形関数） | 指標＝段階ベクトルへの選択（部分和）と除算、という定義上の事実として使う。新研究の出力側の写像に当たる。簡略化の成果ではない。 |
| [CK-R3-08](index_detail/T06_unified_models.md#ck-r3-08) | 2 | A・C | 統合モデル K7 係数解決の表 | 使えるのは定義上の構造 2 点。(1) 係数が使えるかどうかと換算倍率は（係数、段階、単位）の組だけで決まる（行ごとの換算がない場合）。 |
| [CK-R3-09](index_detail/T06_unified_models.md#ck-r3-09) | 1 | A・C | 導出 D1 行テーブル（和の順序の入れ替え） | 行列の形 E＝A·v、ガス別は A·Γ（Γ は 係数キー×ガスの量）。集約キーを増やせばテンソルになる。導出で確立しているのは線形性と集約キーの自由だけ。 |
| [CK-R3-10](index_detail/T06_unified_models.md#ck-r3-10) | 1 | A・B・C | 導出 D2 回数関数 N(T,c) と周期ごとの合算 | 回数関数と端の規約は基準計算の定義の一部なので、どのルートでも再現の対象になる。更新は時刻 n·c の周期的な事象列で、合計は事象の数×1 回分。 |
| [CK-R3-11](index_detail/T06_unified_models.md#ck-r3-11) | 2 | A・C | 導出 D3 修繕の除外年の重み | 修繕＝年率×（T−除外年の重み）で、除外年は更新の事象年の集合である。事象列を年の格子に落とす操作として扱う対象になる。 |
| [CK-R3-12](index_detail/T06_unified_models.md#ck-r3-12) | 1 | A・C | 導出 D4 建替・大型改修 | 建替は初期段階のベクトルへのスカラー倍 N·φ として書ける。D1 の表にそのまま乗数を掛ける形。 |
| [CK-R3-13](index_detail/T06_unified_models.md#ck-r3-13) | 1 | A・C | 導出 D5 年次量の年重み付き和（一定・直線） | 年重み付き和は年の格子の上の重み付きの和 Σ w_y·x_y。系列が 0 次・1 次なら 2 つの数（b と s）と T だけで決まる。 |
| [CK-R3-14](index_detail/T06_unified_models.md#ck-r3-14) | 1 | A・C | 導出 D5 電力係数の区間とモーメント G・H、買電排出 B·G＋S·H | 買電排出は、買電量の系列と電力係数の系列の年重み付きの内積 Σ w_y·n_y·g_y である。 |
| [CK-R3-15](index_detail/T06_unified_models.md#ck-r3-15) | 1 | A・C | 導出 D6 冷媒の充填サイクル（等比の閉形式） | 機器ごとの残存量は公比 1−r の離散の指数減衰で、交換の年に初期値へ戻る。 |
| [CK-R3-16](index_detail/T06_unified_models.md#ck-r3-16) | 1 | A・B・C | 導出 D7 指標と残差判定 | 新研究の出力側の定義として使う（段階ベクトルから指標への写像）。変換を当てる対象ではない。 |
| [CK-R3-17](index_detail/T06_unified_models.md#ck-r3-17) | 2 | A・C | 導出 D8 係数解決と複合係数 | 複合係数＝配合の行列×係数ベクトル、という一次結合の形だけを使う（CK-R3-08 と同じ）。 |
| [CK-R3-33](index_detail/T06_unified_models.md#ck-r3-33) | 3 | A・B・C | 設計案：統合の所属を故障注入で確かめる（membership_check） | 新研究で「この式群は共通の変換で表されている」と数えるときの確かめ方の型として使える：共通の変換を外から壊し、どの出力が変わるかを見て、変わらない出力はその変換に含めない。 |
| [CK-R3-34](index_detail/T06_unified_models.md#ck-r3-34) | 3 | A・B・C | 設計案：仕組みを外から計測する（mechanism_probe） | 新研究で演算回数・入力の読み取り回数を示すときの測り方の型として使える。評価の対象のコードに計数を埋め込まず、入力と共有関数を包んで外から数える。 |
| [CK-R3-37](index_detail/T06_unified_models.md#ck-r3-37) | 3 | A・C | 統合モデルの拡張案のうち実装・検証していないもの | 新研究の仮説の候補として読む。 |
| [CK-R7-23](index_detail/T06_unified_models.md#ck-r7-23) | 1 | A・C | 厳密な閉形式のうち、第2回の総当たりで基準のループと食い違わなかったもの | ルート A の材料。年の和・事象の数え上げ・冷媒の漸化式を、和の公式・階段関数・等比の式で置き換えた実例と、その一致の確認範囲として使う。 |
| [CK-R7-24](index_detail/T06_unified_models.md#ck-r7-24) | 2 | A・C | 導出の文書 DERIVATIONS.md（D1〜D8） | ルート A の材料。保存済みの簡素化が使っている変形の種類（和の順序の入れ替え、周期ごとの合算、等差・平方和、等比、残差判定）の一覧として読む。 |
| [CK-R7-25](index_detail/T06_unified_models.md#ck-r7-25) | 2 | A・C | 統合モデル K1〜K7 の目録（保存済みの簡素化成果の構成） | ルート A の出発点。保存済みの簡素化が計算体系をどういう 7 つの形に分けたかを示す。少数の変換にまとめ直すときの比較対象（変換の種類の数、どの単位がどの形に入るか）になる。 |

#### 厳密一致・負荷・入力の測定と反例（T07）

| 項目 | 区分 | ルート | 成果 | 使い道（冒頭） |
|---|---|---|---|---|
| [CK-R3-18](index_detail/T07_exactness_load.md#ck-r3-18) | 1 | A・B・C | 厳密一致の測定（681 シナリオ、数値 7,406,182 個、許容差 相対 1e-9） | 新研究での厳密一致・誤差測定の型として使える。シナリオの種類（ベンチマーク、境界条件、母集団、不備、壊し方、小数の端、段階の部分集合）と、葉ごとの比較という方法である。 |
| [CK-R3-19](index_detail/T07_exactness_load.md#ck-r3-19) | 1 | A・C | 評価期間の掃引（1 回の合算から別の評価期間の結果を求める） | T に依存しない部分（A、U_c、R_c、機器の一覧）と T に依存する乗数の分離が、実装と測定の両方で確かめられた例として使う。 |
| [CK-R3-20](index_detail/T07_exactness_load.md#ck-r3-20) | 1 | A・B・C | 負荷の測定：実行した命令数（規模 S・M、基準計算・全出力・合計のみ） | 使えるのは測り方である：機械の混み具合に左右されない指標として実行命令数を数え、同じ仕事をする組だけを比べ、出力の範囲（全出力、合計のみ）を分けて示す。 |
| [CK-R3-23](index_detail/T07_exactness_load.md#ck-r3-23) | 2 | A・B・C | 入力項目の使用の測定（基準計算と統合モデルが読む入力は同じ） | 入力数を数える方法（属性の読み取りの追跡）は、新研究で「入力変数の数」を比べるときの型として使える。結果のうち使えるのは「厳密な書き換えでは入力は減らない」という点だけ。 |
| [CK-R3-27](index_detail/T07_exactness_load.md#ck-r3-27) | 4 | A・B・C | 反例：周期 1.000000001 で修繕（B3-01）が基準計算と食い違う | 新研究は基準計算を変えないので、この入力では基準計算が「書かれた定義」と違う値を返すことを前提にする。 |
| [CK-R3-28](index_detail/T07_exactness_load.md#ck-r3-28) | 4 | A・B・C | 不備のある入力・特殊な入力での食い違い（NUM-2〜NUM-9） | 新研究のモデルを基準計算と比べるときの検査シナリオの材料と、定義を決めるべき点の一覧として使う。 |
| [CK-R3-29](index_detail/T07_exactness_load.md#ck-r3-29) | 4 | A・B・C | 条件の悪い入力での限界（NUM-10：桁落ち・桁あふれ） | 新研究の誤差の目標を決めるときの下限の目安として使う。基準計算そのものが桁を失う量があるので、基準計算との差だけでモデルの誤りを判定できない場合がある。 |
| [CK-R3-30](index_detail/T07_exactness_load.md#ck-r3-30) | 4 | A・B・C | 一致の確認に使った比較の弱点（NUM-11：床、無限大、真偽値、余分な葉） | 新研究の誤差測定では、比較の規則（相対と絶対の床、無限大と NaN、型、欠けた葉と余分な葉）を最初に定義し、報告書に書く。 |
| [CK-R7-22](index_detail/T07_exactness_load.md#ck-r7-22) | 1 | A・C | 681 架空シナリオでの基準計算と統合モデルの一致（記録された測定） | ルート A で保存済みの簡素化成果（統合モデル）を出発点にするとき、その成果がこの母集団で基準計算を再現していたという根拠と、回帰確認の合格線（681 シナリオ、相対 1e-9）として使う。 |

#### 近似検証（M3〜M6）（T08）

| 項目 | 区分 | ルート | 成果 | 使い道（冒頭） |
|---|---|---|---|---|
| [CK-R4-01](index_detail/T08_approximation.md#ck-r4-01) | 2 | A・B・C | 「近似は 1 つも採用していない」という全体の結論 | 新研究で旧研究の近似の結果に触れるときの、言える範囲を定める。採用済みの近似モデルは無いので、ルート A でそのまま引き継げる近似の成果は無い。 |
| [CK-R4-02](index_detail/T08_approximation.md#ck-r4-02) | 2 | A・B・C | 近似候補の誤差測定の枠組み（測定プログラムと出力の形式） | 新研究で変換後のモデルの誤差を測るときの集計様式（符号付き誤差、過小の割合、基準が 0 の件数、構造別・用途別・材料区分別、学習と試験の分割）のひな形になる。 |
| [CK-R4-03](index_detail/T08_approximation.md#ck-r4-03) | 4 | A・B・C | 誤差測定方法の確認済みの欠陥（第2回の指摘） | 新研究の誤差測定を設計するときに避ける点の一覧として使う：基準量は段階の値で取り、合算した量で測らない。上流の量を変える候補は下流まで計算し直して建物合計を測る。 |
| [CK-R4-04](index_detail/T08_approximation.md#ck-r4-04) | 1 | A・B・C | 更新回数の連続近似（AP-01・AP-02・AP-03）と上下限（AP-20） | 反例として使う。段差のある回数関数を滑らかな式で置き換えると、周期が評価期間を割り切らない場合に大きくずれる。 |
| [CK-R4-05](index_detail/T08_approximation.md#ck-r4-05) | 1 | A・B・C | 修繕の更新年除外を無視する形（AP-04） | 過大側にしか外れない近似の例。除外項を落とした値は、安全側の変種（CK-R4-06）の過大の上限になる。 |
| [CK-R4-06](index_detail/T08_approximation.md#ck-r4-06) | 3 | B・C | 修繕の安全側の候補（除外年数の連続近似。第2回で提案、b2 で AP-23a・b・c） | 行ごとの条件を区分の少数の値にまとめても誤差の符号が保たれる例（max(0, x − 1) の凸性と調和平均による片側の保証）。 |
| [CK-R4-07](index_detail/T08_approximation.md#ck-r4-07) | 2 | A・B・C | 冷媒漏洩の線形近似（AP-05） | 等比の形（1−(1−r)^k）を 1 次で打ち切ると、使える範囲（r·k が小さい場合）が狭いことを示す反例。 |
| [CK-R4-08](index_detail/T08_approximation.md#ck-r4-08) | 2 | A・B・C | 端材倍率の線形化（AP-06・AP-06b） | 誤差が目標内でも符号が過小側に固定される近似の例。 |
| [CK-R4-09](index_detail/T08_approximation.md#ck-r4-09) | 1 | A・B・C | 複合係数の構成材の切り捨て（AP-07a・AP-07b） | 加重和の小さい項を落とすと、落とした項の係数が残りの平均と違う分だけずれる例。 |
| [CK-R4-10](index_detail/T08_approximation.md#ck-r4-10) | 2 | A・B・C | 買電排出の平均×平均（AP-08）と電力係数の補間（AP-09a・AP-09b） | 時系列の積の和 Σ x_t·g_t を平均の積で置き換えると、買電量と係数の時間方向の共分散が落ちる例（AP-08）。 |
| [CK-R4-11](index_detail/T08_approximation.md#ck-r4-11) | 3 | B・C | 年次表の電力係数だけを 5 年刻みにする併用（AP-09c） | 入力の形（記述子か年次表か）で厳密と近似を切り替える併用の測定例。年次系列を少数の節点で持つ表現の誤差の目安と、適用範囲の判定の例になる。 |
| [CK-R4-12](index_detail/T08_approximation.md#ck-r4-12) | 3 | B・C | 区分パラメータによる共通近似モデル（AP-18a・AP-18b・AP-18） | 構造の違う式（段差のある回数関数をもつ更新、年の重みと除外をもつ修繕、経路の加重和をもつ廃棄）を、区分ごとの少数のパラメータで 1 つの近似モデルにまとめる試みの主な例。 |
| [CK-R4-13](index_detail/T08_approximation.md#ck-r4-13) | 3 | B・C | 廃棄段階の区分集約（AP-18c） | 行を区分に集約するとき、比率の平均×係数の平均（積の平均ではない）を使うと、区分内の比率と係数の共分散が落ちる例。 |
| [CK-R4-14](index_detail/T08_approximation.md#ck-r4-14) | 3 | B・C | 要約数量×代表係数による資材製造の概算（AP-10・AP-10b） | 多数の行を少数の区分の数量にまとめ、区分ごとの係数で排出を復元するモデルを、作る建物と測る建物を分けて測った例。 |
| [CK-R4-15](index_detail/T08_approximation.md#ck-r4-15) | 3 | B・C | 延床面積の原単位・回帰による代理モデル（AP-11・AP-15・AP-16・AP-13） | 構造の違う 14 段階の式を、同じ形（面積×（年数）×原単位）の 1 つのモデルで置き換える、最も粗い例。 |
| [CK-R4-16](index_detail/T08_approximation.md#ck-r4-16) | 3 | B・C | 質量上位の行だけを詳細計算する併用（AP-12） | 寄与の大きい項だけを残す打ち切りで、順位付けを質量で行うと、質量の大きい行ほど係数が小さい場合に過小へ偏る例。 |
| [CK-R4-17](index_detail/T08_approximation.md#ck-r4-17) | 3 | A・B・C | 輸送の単純平均距離（AP-17） | 行ごとの積の和 Σ m_i·d_i を (Σm)×(d の平均) で置き換えたときの誤差が共分散に等しい、という恒等式がそのまま使える。 |
| [CK-R4-18](index_detail/T08_approximation.md#ck-r4-18) | 3 | B・C | 未数量分の比率を 1 つにまとめる（AP-19a・AP-19b） | 非線形の倍率 h(r) = r/(1−r) を平均の比率で評価するときの誤差の例。 |
| [CK-R4-19](index_detail/T08_approximation.md#ck-r4-19) | 1 | A・B・C | 評価期間についての直線補間（AP-14） | 合計を評価期間 T の関数として見ると、更新の段差のために T について滑らかでない（2 点からの直線補間で ±10〜20％ 外れる）ことを示す反例。 |
| [CK-R4-20](index_detail/T08_approximation.md#ck-r4-20) | 1 | A・B・C | 全ガスの合計を CO2 のみの合計で代用する（AP-22a） | ガス別の成分を 1 つだけ残すと常に過小になる例。 |
| [CK-R4-22](index_detail/T08_approximation.md#ck-r4-22) | 1 | A・B・C | 誤差の符号が式から決まる候補（片側にしか外れない近似）の一覧 | 新研究で「重大な過小評価なし」の条件を確かめるとき、片側にしか外れないことが式から分かる近似の例と、その示し方（凸性、単調性、ベルヌーイの不等式、項を落とす）として使える。 |
| [CK-R4-25](index_detail/T08_approximation.md#ck-r4-25) | 4 | A・B・C | 架空データでは近似の実用精度を確立できない、という限界 | 新研究の誤差評価にも同じ限界がかかる。架空データで書けるのは「この入力の分布ではこうなる」「この候補はこの入力で外れる」までである、という書き方の基準として使う。 |
| [CK-R4-26](index_detail/T08_approximation.md#ck-r4-26) | 4 | B・C | 近似の段階の網羅性の不足（測定なしの見送り、建物水準の候補の付け替え） | 新研究で「旧研究が測っていない範囲」を特定する一覧として使う：年次表の入力をもつ運用段階の単位（B6-02、B6-04、B7-01〜03）、単位ごとの代理モデル、手順書どおりに数えたとき M4 が未測定の 5 単位（X-06、X-13、X-12、B3… |
| [CK-R7-26](index_detail/T08_approximation.md#ck-r7-26) | 1 | A・B・C | 近似候補の誤差測定のうち、第2回の独立した再実装で統計値が再現した 27 件（反例として） | 新しい定式化の候補を絞るときの反例として使う：階段関数の連続化、年系列の積の平均化、行ごとの値の区分平均化などが、この架空の母集団でどれだけ外れたかが分かっている。 |
| [CK-R7-27](index_detail/T08_approximation.md#ck-r7-27) | 2 | A・B・C | 近似候補の誤差測定のうち、第2回が再実装しなかった 5 件と内訳表 | 建物水準の代理モデル（面積・評価年数・構造・用途からの概算、対数線形回帰）と、上位の行だけ詳細計算する併用が、架空の母集団で大きく外れたという記録として参照する。 |

#### 記録・進捗台帳・報告書・必須成果物（T09）

| 項目 | 区分 | ルート | 成果 | 使い道（冒頭） |
|---|---|---|---|---|
| [CK-R5-01](index_detail/T09_records_reports.md#ck-r5-01) | 1 | A・C | 記録・進捗台帳・報告書の件数と相互参照の整合（数え直しで一致した範囲） | 旧研究の公表済みの数字を引用するときに、どのファイルのどのキーから来た数かをたどる手掛かりにする。 |
| [CK-R5-02](index_detail/T09_records_reports.md#ck-r5-02) | 2 | A・C | 単位別の検討記録 454 件（記録とは何か、どんな裏付けを名乗っているか） | 旧研究が単位ごとに何を試したかの索引として使う。 |
| [CK-R5-03](index_detail/T09_records_reports.md#ck-r5-03) | 2 | A・C | 厳密な段階（M1・M2）の成功記録 118 件 | どの単位のどの簡略化が題名どおりだったかの一覧として、Route A で旧成果から使う部分を選ぶ材料にする。 |
| [CK-R5-05](index_detail/T09_records_reports.md#ck-r5-05) | 2 | A・C | 近似の段階の「不採用」記録 39 件（候補 16 種） | 新研究で誤差を測るときの比較の相手（単純な近似がどの程度外れたか）と、同じ候補を繰り返さないための一覧として使う。 |
| [CK-R5-06](index_detail/T09_records_reports.md#ck-r5-06) | 3 | A・B・C | 近似の段階の「保留」記録 71 件（候補 16 種。実データ待ち） | 新研究で近似や低次元化の候補を考えるときに、既に出た案と、判断に必要なデータの一覧として使う。 |
| [CK-R5-07](index_detail/T09_records_reports.md#ck-r5-07) | 3 | B・C | 「候補なし」記録 226 件（測定をしていない判断） | 旧研究が測らずに見送った箇所の一覧として、新研究で改めて調べる対象を選ぶときに使う。 |
| [CK-R5-08](index_detail/T09_records_reports.md#ck-r5-08) | 2 | A・C | 進捗台帳（progress_ledger.json と PROGRESS.md）の構造と判定の規則 | 単位ごとの到達点の索引として使う。状態を記録から機械的に求める規則は、新研究の進捗の管理の参考になる。 |
| [CK-R5-10](index_detail/T09_records_reports.md#ck-r5-10) | 2 | A・C | 自動生成の報告書 6 点と PROGRESS.md（文面としての状態） | 旧研究の公表文を引用するときの出典として使う。 |
| [CK-R5-11](index_detail/T09_records_reports.md#ck-r5-11) | 1 | A・B・C | README の要点 1「評価単位は 70 件（53＋17）。全件を研究対象にした」 | 新研究で方程式のグループを数えるときに、旧研究の側の母数として引用する。 |
| [CK-R5-12](index_detail/T09_records_reports.md#ck-r5-12) | 4 | A・C | README の要点 2「66 単位が 7 つの統合モデルに、結果を変えずにまとまった」 | 7 つのモデルの形は、新研究が少数の変換で表し直す対象を整理するときの出発点として使える。 |
| [CK-R5-13](index_detail/T09_records_reports.md#ck-r5-13) | 2 | A・C | README の要点 3「統合モデルは基準計算と一致した」 | Route A で旧成果を使うときに、一致が確かめられている入力の範囲（681 シナリオ）として引用する。 |
| [CK-R5-14](index_detail/T09_records_reports.md#ck-r5-14) | 2 | A・C | README の要点 4「計算の重さは減った」 | 新研究で計算量を比べるときの基準線（旧統合モデルの命令数）として引用する。 |
| [CK-R5-15](index_detail/T09_records_reports.md#ck-r5-15) | 2 | A・B・C | README の要点 5「近似は 1 つも採用していない」 | 新研究で、既に試して外れた近似と、結論が出ていない近似を区別するために引用する。 |
| [CK-R5-16](index_detail/T09_records_reports.md#ck-r5-16) | 2 | A・B・C | README の要点 6「入力項目は減っていない」 | 新研究で入力の数を比べるときの基準（基準計算が読む項目の数）として引用する。 |
| [CK-R5-17](index_detail/T09_records_reports.md#ck-r5-17) | 1 | A・B・C | README の要点 7「材料・用途・構造の違いは式に現れず、データの違いとして扱う（設計上）」 | 新研究が計算の体系を「行（データ）×少数の乗数の関数」として表し直すときの、整理の出発点にする。 |
| [CK-R5-18](index_detail/T09_records_reports.md#ck-r5-18) | 2 | A・C | 05_DECISIONS/README.md の採否の理由（採用・不採用・保留・現状維持の文面） | 旧研究が最後に何を推奨し、何を退け、何を保留にしたかの一覧として引用する。 |
| [CK-R5-19](index_detail/T09_records_reports.md#ck-r5-19) | 2 | A・C | 05_DECISIONS/README.md「統合前後の変化」の表（行ごとの状態） | 新研究が「統合前後」を比べる表を作るときの、項目の立て方と、旧研究の側の値として引用する。 |
| [CK-R5-20](index_detail/T09_records_reports.md#ck-r5-20) | 2 | A・C | 旧指示書の必須成果物 9 点（有無と状態） | 旧研究の資料の置き場所の一覧として使う。 |
| [CK-R5-22](index_detail/T09_records_reports.md#ck-r5-22) | 4 | A・B・C | 未解決事項の一覧（06_OPEN_ISSUES/README.md の A〜H） | 新研究の未解決事項の最初の一覧と、必要なデータの一覧として使う。G-1、G-2、G-3、G-6 は、新研究で扱える未着手の案である。 |
| [CK-R5-23](index_detail/T09_records_reports.md#ck-r5-23) | 4 | A・B・C | 未解決事項の一覧に載っていない事項と、古くなった記述（第2回で判明） | 新研究が基準計算を変えずに使うときの、既知の穴と未記載の規約の一覧として使う。 |
| [CK-R5-29](index_detail/T09_records_reports.md#ck-r5-29) | 2 | A・C | 記録・台帳・報告書の生成器（research_code/tools/ の 5 本）：どの生成器がどのファイルを書くか | 記録の様式（項目の定義）と、状態を記録から機械的に求める規則の実装は、新研究の記録と進捗の管理の参考になる。 |

#### 材料分類の設計草案（T10）

| 項目 | 区分 | ルート | 成果 | 使い道（冒頭） |
|---|---|---|---|---|
| [CK-R5-26](index_detail/T10_material_taxonomy.md#ck-r5-26) | 3 | B・C | 材料分類の設計草案（07_MATERIAL_TAXONOMY：データ構造と手順の形だけ。データセットではない） | 新研究で計算の入力（行）の形を決めるときの参考にする。 |
| [CK-R5-28](index_detail/T10_material_taxonomy.md#ck-r5-28) | 4 | B・C | 材料分類の設計草案の未解決事項と、行っていない確認 | 新研究が材料データを扱う段階に進む場合の、先に決める必要がある事項と、必要なデータの一覧として使う。 |

#### 中断した修正（65ff124）と未実施の改訂（T11）

| 項目 | 区分 | ルート | 成果 | 使い道（冒頭） |
|---|---|---|---|---|
| [CK-R2-18](index_detail/T11_interrupted_fix.md#ck-r2-18) | 3 | B・C | 第2回の指摘に対する基準計算の定義の修正方針（SPEC_A1.md の設計決定） | ルート B・C で時間の規約を式にするときの仮説として読める：回数 N = ceil(T×c / L) − 1、年 = max(1, ceil(n×L×c))、q = L×c ≥ 1 なら事象の年はすべて異なり、q < 1 なら年 1 から最後の事象… |
| [CK-R3-31](index_detail/T11_interrupted_fix.md#ck-r3-31) | 2 | A・B・C | 中断した修正 a1：時間の判定を厳密な有理数の演算にし、閉形式を作り直す | 時間の規則を丸めに依存しない形で定義する案として読む。新研究が回数関数や年の割り当てを変換で表すとき、対照にする定義の候補になる。 |
| [CK-R4-23](index_detail/T11_interrupted_fix.md#ck-r4-23) | 2 | B・C | b2 の再測定と新しい候補（中断した修正。自己申告のみ） | 欠陥を直した測定の設計（基準量を段階の値で取る、下流まで計算し直した合計、パラメータの出所の表示、基準 0 の件数、入力数と命令数、候補が単位・段階・建物のどの水準で測られたかの表示）を、新研究の誤差測定の設計の参考にする。 |
| [CK-R4-24](index_detail/T11_interrupted_fix.md#ck-r4-24) | 3 | A・C | b2 の設計（SPEC_B2）と結論文の書き換え案 | 旧研究の候補の理由文を引用するときに、どの文を使ってはいけないか（16 候補）を確かめる対照表として使える。 |
| [CK-R5-30](index_detail/T11_interrupted_fix.md#ck-r5-30) | 3 | A・C | 予定だったが行われなかった改訂（Stage C）：記録・進捗台帳・報告書の生成器 | 新研究が旧成果を引用したり、自分の記録を作ったりするときの、裏付けの様式の案として使える（統合の所属は故障注入で確かめる、仕組みは外からの計測で確かめる、近似の証拠の範囲を単位・段階・建物全体で区別する）。 |
| [CK-R5-31](index_detail/T11_interrupted_fix.md#ck-r5-31) | 3 | A・C | 予定だったが行われなかった改訂（Stage C）：手書きの文書と、全体の再生成 | 旧研究の手書きの文書を読むときに、どの記述が改訂の予定だったかを知る対照として使う。 |
| [CK-R7-32](index_detail/T11_interrupted_fix.md#ck-r7-32) | 2 | B・C | 中断した修正（65ff124）の基準計算・閉形式：定義が変わった未検証の版 | 基準計算の穴（CK-R7-19、CK-R7-20）をどう埋めようとしたかの設計の記録として読む。新研究が穴のある入力範囲を扱う場合の参考になる。 |

#### 式の族と未実装の案（構造の棚卸し）（T12）

| 項目 | 区分 | ルート | 成果 | 使い道（冒頭） |
|---|---|---|---|---|
| [CK-R7-04](index_detail/T12_formula_families.md#ck-r7-04) | 2 | B・C | 式の族 F01：行の和（活動量×換算倍率×係数） | 行×係数の双一次の部分（段階 A1-A3・A4・A5・C1〜C4 の本体）を、行列・テンソルの形で書き直すときの対象範囲と、行結果が下流（B3・B4・B5・X-04・X-05・X-17）へ渡る点の確認に使う。 |
| [CK-R7-05](index_detail/T12_formula_families.md#ck-r7-05) | 2 | B・C | 式の族 F02：行ごとの数量の比・換算（端材率・再使用率） | 行和の族 F01 に掛かる行の乗数（w の有理関数 1/(1−w)）の定義として使う。 |
| [CK-R7-06](index_detail/T12_formula_families.md#ck-r7-06) | 2 | B・C | 式の族 F03：加重和・行列の展開・区分別の再集計 | 行×構成材、行×ガス（7 種）、区分（13）×経路（4）という添字の組を持つ線形の展開の一覧として使う。ルート A では K7（複合係数）と K1（同じ表の別の読み方）に対応する。 |
| [CK-R7-07](index_detail/T12_formula_families.md#ck-r7-07) | 2 | B・C | 式の族 F04：事象の数え上げ（評価期間 T と周期） | 床・天井関数で表される不連続な T 依存（T=n·c で 1 段上がる）と、「回数×1 回分」という積の形の所在を示す。 |
| [CK-R7-08](index_detail/T12_formula_families.md#ck-r7-08) | 2 | B・C | 式の族 F05：年重み付き和（年次量×年ごとの係数） | 年の添字を持つ 2 つの系列の積の和（買電量×電力係数）、端数年の重み、打ち切り max(0,·)、事象の年を除く和（修繕）の所在を示す。 |
| [CK-R7-09](index_detail/T12_formula_families.md#ck-r7-09) | 2 | B・C | 式の族 F06：区分的に直線・段階的な電力係数の年次系列（X-06） | 年の添字に対する係数系列の種類（定数、折れ線 1 か所、階段、任意の表）の一覧として使う。 |
| [CK-R7-10](index_detail/T12_formula_families.md#ck-r7-10) | 2 | B・C | 式の族 F07：冷媒の充填・漏洩・補充・交換（年ごとの漸化式） | 状態（残存量）を持つ唯一の族として、漸化式・等比の和・事象による初期化の所在を示す。ルート A では K4（充填サイクルの質量収支）に対応する。 |
| [CK-R7-11](index_detail/T12_formula_families.md#ck-r7-11) | 2 | B・C | 式の族 F08：比・指標（原単位、単位換算、段階別割合） | 段階ベクトルの線形関数を尺度で割る形（尺度に対しては非線形）の一覧として使う。 |
| [CK-R7-12](index_detail/T12_formula_families.md#ck-r7-12) | 2 | B・C | 式の族 F09：集約の木（段階ベクトルと部分和） | 最終の合計がどの単位の和でできているか（29 単位→14 段階→3 つの部分和）と、B2／B6 の条件つきの引き算、参考値・代替値を合計に入れない規則の確認に使う。 |
| [CK-R7-13](index_detail/T12_formula_families.md#ck-r7-13) | 2 | B・C | 式の族 F10：基準案との比較（SUM-08） | 2 つのシナリオの合計の差と比という形、および「基準案の計算は全体の再実行」という計算上の位置づけの確認に使う。 |
| [CK-R7-14](index_detail/T12_formula_families.md#ck-r7-14) | 2 | B・C | 式の族 F11：条件分岐・述語（入力検査、整合の検査、係数の解決） | 連続な式の外側にある離散の分岐（使える係数の選択、択一、妥当性、許容差つきの判定）の一覧として使う。ルート A では K7（係数解決）と K6（許容差つきの残差判定）に対応する。 |
| [CK-R7-31](index_detail/T12_formula_families.md#ck-r7-31) | 3 | B・C | 検討したが実装・検証していない式の案（06_OPEN_ISSUES の G-1〜G-7、B-8 の別の選択肢） | 旧研究が式の形について気づいていて手を付けなかった点の一覧として参照する（特に、規約 B-8 を変えると F04 の「回数×1 回分」という形が崩れる、という記述）。 |

### 6.4 再利用の候補にしなかった項目（38 件）

分類担当が候補にしなかった項目。理由は各項目の詳細にある。

| 区分 | 項目 |
|---|---|
| 1 | [CK-R3-07](index_detail/T06_unified_models.md#ck-r3-07) |
| 2 | [CK-R1-01](index_detail/T01_policy_protocol.md#ck-r1-01)、[CK-R1-11](index_detail/T11_interrupted_fix.md#ck-r1-11)、[CK-R1-12](index_detail/T02_ledger.md#ck-r1-12)、[CK-R1-13](index_detail/T02_ledger.md#ck-r1-13)、[CK-R1-15](index_detail/T02_ledger.md#ck-r1-15)、[CK-R1-18](index_detail/T03_ranking.md#ck-r1-18)、[CK-R1-20](index_detail/T03_ranking.md#ck-r1-20)、[CK-R2-19](index_detail/T11_interrupted_fix.md#ck-r2-19)、[CK-R2-20](index_detail/T11_interrupted_fix.md#ck-r2-20)、[CK-R2-21](index_detail/T11_interrupted_fix.md#ck-r2-21)、[CK-R2-22](index_detail/T11_interrupted_fix.md#ck-r2-22)、[CK-R2-23](index_detail/T11_interrupted_fix.md#ck-r2-23)、[CK-R3-21](index_detail/T07_exactness_load.md#ck-r3-21)、[CK-R3-22](index_detail/T03_ranking.md#ck-r3-22)、[CK-R3-26](index_detail/T06_unified_models.md#ck-r3-26)、[CK-R3-32](index_detail/T11_interrupted_fix.md#ck-r3-32)、[CK-R3-36](index_detail/T11_interrupted_fix.md#ck-r3-36)、[CK-R5-24](index_detail/T09_records_reports.md#ck-r5-24)、[CK-R5-27](index_detail/T10_material_taxonomy.md#ck-r5-27) |
| 3 | [CK-R3-35](index_detail/T06_unified_models.md#ck-r3-35)、[CK-R4-21](index_detail/T08_approximation.md#ck-r4-21) |
| 4 | [CK-R1-04](index_detail/T01_policy_protocol.md#ck-r1-04)、[CK-R1-10](index_detail/T02_ledger.md#ck-r1-10)、[CK-R1-21](index_detail/T02_ledger.md#ck-r1-21)、[CK-R2-03](index_detail/T04_reference_calculation.md#ck-r2-03)、[CK-R2-05](index_detail/T04_reference_calculation.md#ck-r2-05)、[CK-R2-07](index_detail/T04_reference_calculation.md#ck-r2-07)、[CK-R2-09](index_detail/T04_reference_calculation.md#ck-r2-09)、[CK-R2-10](index_detail/T04_reference_calculation.md#ck-r2-10)、[CK-R2-16](index_detail/T05_synthetic_data_harness.md#ck-r2-16)、[CK-R2-24](index_detail/T11_interrupted_fix.md#ck-r2-24)、[CK-R3-24](index_detail/T06_unified_models.md#ck-r3-24)、[CK-R3-25](index_detail/T06_unified_models.md#ck-r3-25)、[CK-R5-04](index_detail/T09_records_reports.md#ck-r5-04)、[CK-R5-09](index_detail/T09_records_reports.md#ck-r5-09)、[CK-R5-21](index_detail/T09_records_reports.md#ck-r5-21)、[CK-R5-25](index_detail/T09_records_reports.md#ck-r5-25) |

## 7. 主題別の早見表

同じ対象を複数の観点が扱っている場合、項目は主題ごとにまとめてある。区分が違うのは、対象が違うためである（例：測定の結果そのものは区分 1、それを一般化した README の文は区分 2、その穴は区分 4）。

| 主題 | 区分 1 | 区分 2 | 区分 3 | 区分 4 | 詳細 |
|---|---|---|---|---|---|
| T01 統制文書と手順書 | — | [CK-R1-01](index_detail/T01_policy_protocol.md#ck-r1-01)<br>[CK-R1-02](index_detail/T01_policy_protocol.md#ck-r1-02) | [CK-R1-03](index_detail/T01_policy_protocol.md#ck-r1-03) | [CK-R1-04](index_detail/T01_policy_protocol.md#ck-r1-04) | [T01_policy_protocol.md](index_detail/T01_policy_protocol.md) |
| T02 評価単位の台帳・シート族・依存関係 | [CK-R1-05](index_detail/T02_ledger.md#ck-r1-05)<br>[CK-R1-09](index_detail/T02_ledger.md#ck-r1-09)<br>[CK-R7-01](index_detail/T02_ledger.md#ck-r7-01)<br>[CK-R7-02](index_detail/T02_ledger.md#ck-r7-02) | [CK-R1-06](index_detail/T02_ledger.md#ck-r1-06)<br>[CK-R1-07](index_detail/T02_ledger.md#ck-r1-07)<br>[CK-R1-12](index_detail/T02_ledger.md#ck-r1-12)<br>[CK-R1-13](index_detail/T02_ledger.md#ck-r1-13)<br>[CK-R1-14](index_detail/T02_ledger.md#ck-r1-14)<br>[CK-R1-15](index_detail/T02_ledger.md#ck-r1-15)<br>[CK-R7-03](index_detail/T02_ledger.md#ck-r7-03) | [CK-R1-08](index_detail/T02_ledger.md#ck-r1-08) | [CK-R1-10](index_detail/T02_ledger.md#ck-r1-10)<br>[CK-R1-16](index_detail/T02_ledger.md#ck-r1-16)<br>[CK-R1-21](index_detail/T02_ledger.md#ck-r1-21)<br>[CK-R7-30](index_detail/T02_ledger.md#ck-r7-30) | [T02_ledger.md](index_detail/T02_ledger.md) |
| T03 着手順序（評価軸 A・B） | — | [CK-R1-17](index_detail/T03_ranking.md#ck-r1-17)<br>[CK-R1-18](index_detail/T03_ranking.md#ck-r1-18)<br>[CK-R1-20](index_detail/T03_ranking.md#ck-r1-20)<br>[CK-R3-22](index_detail/T03_ranking.md#ck-r3-22) | [CK-R1-19](index_detail/T03_ranking.md#ck-r1-19) | — | [T03_ranking.md](index_detail/T03_ranking.md) |
| T04 基準計算と規約 | [CK-R2-01](index_detail/T04_reference_calculation.md#ck-r2-01)<br>[CK-R2-02](index_detail/T04_reference_calculation.md#ck-r2-02)<br>[CK-R7-17](index_detail/T04_reference_calculation.md#ck-r7-17)<br>[CK-R7-28](index_detail/T04_reference_calculation.md#ck-r7-28) | [CK-R2-04](index_detail/T04_reference_calculation.md#ck-r2-04)<br>[CK-R2-06](index_detail/T04_reference_calculation.md#ck-r2-06)<br>[CK-R2-08](index_detail/T04_reference_calculation.md#ck-r2-08)<br>[CK-R7-18](index_detail/T04_reference_calculation.md#ck-r7-18) | — | [CK-R2-03](index_detail/T04_reference_calculation.md#ck-r2-03)<br>[CK-R2-05](index_detail/T04_reference_calculation.md#ck-r2-05)<br>[CK-R2-07](index_detail/T04_reference_calculation.md#ck-r2-07)<br>[CK-R2-09](index_detail/T04_reference_calculation.md#ck-r2-09)<br>[CK-R2-10](index_detail/T04_reference_calculation.md#ck-r2-10)<br>[CK-R7-19](index_detail/T04_reference_calculation.md#ck-r7-19)<br>[CK-R7-20](index_detail/T04_reference_calculation.md#ck-r7-20)<br>[CK-R7-29](index_detail/T04_reference_calculation.md#ck-r7-29) | [T04_reference_calculation.md](index_detail/T04_reference_calculation.md) |
| T05 架空データ・比較の仕組み・試験 | — | [CK-R2-11](index_detail/T05_synthetic_data_harness.md#ck-r2-11)<br>[CK-R2-12](index_detail/T05_synthetic_data_harness.md#ck-r2-12)<br>[CK-R2-13](index_detail/T05_synthetic_data_harness.md#ck-r2-13)<br>[CK-R2-14](index_detail/T05_synthetic_data_harness.md#ck-r2-14)<br>[CK-R2-15](index_detail/T05_synthetic_data_harness.md#ck-r2-15)<br>[CK-R2-17](index_detail/T05_synthetic_data_harness.md#ck-r2-17)<br>[CK-R7-15](index_detail/T05_synthetic_data_harness.md#ck-r7-15)<br>[CK-R7-16](index_detail/T05_synthetic_data_harness.md#ck-r7-16)<br>[CK-R7-21](index_detail/T05_synthetic_data_harness.md#ck-r7-21) | — | [CK-R2-16](index_detail/T05_synthetic_data_harness.md#ck-r2-16) | [T05_synthetic_data_harness.md](index_detail/T05_synthetic_data_harness.md) |
| T06 統合モデル K1〜K7 と導出 | [CK-R3-01](index_detail/T06_unified_models.md#ck-r3-01)<br>[CK-R3-02](index_detail/T06_unified_models.md#ck-r3-02)<br>[CK-R3-03](index_detail/T06_unified_models.md#ck-r3-03)<br>[CK-R3-05](index_detail/T06_unified_models.md#ck-r3-05)<br>[CK-R3-07](index_detail/T06_unified_models.md#ck-r3-07)<br>[CK-R3-09](index_detail/T06_unified_models.md#ck-r3-09)<br>[CK-R3-10](index_detail/T06_unified_models.md#ck-r3-10)<br>[CK-R3-12](index_detail/T06_unified_models.md#ck-r3-12)<br>[CK-R3-13](index_detail/T06_unified_models.md#ck-r3-13)<br>[CK-R3-14](index_detail/T06_unified_models.md#ck-r3-14)<br>[CK-R3-15](index_detail/T06_unified_models.md#ck-r3-15)<br>[CK-R3-16](index_detail/T06_unified_models.md#ck-r3-16)<br>[CK-R7-23](index_detail/T06_unified_models.md#ck-r7-23) | [CK-R3-04](index_detail/T06_unified_models.md#ck-r3-04)<br>[CK-R3-06](index_detail/T06_unified_models.md#ck-r3-06)<br>[CK-R3-08](index_detail/T06_unified_models.md#ck-r3-08)<br>[CK-R3-11](index_detail/T06_unified_models.md#ck-r3-11)<br>[CK-R3-17](index_detail/T06_unified_models.md#ck-r3-17)<br>[CK-R3-26](index_detail/T06_unified_models.md#ck-r3-26)<br>[CK-R7-24](index_detail/T06_unified_models.md#ck-r7-24)<br>[CK-R7-25](index_detail/T06_unified_models.md#ck-r7-25) | [CK-R3-33](index_detail/T06_unified_models.md#ck-r3-33)<br>[CK-R3-34](index_detail/T06_unified_models.md#ck-r3-34)<br>[CK-R3-35](index_detail/T06_unified_models.md#ck-r3-35)<br>[CK-R3-37](index_detail/T06_unified_models.md#ck-r3-37) | [CK-R3-24](index_detail/T06_unified_models.md#ck-r3-24)<br>[CK-R3-25](index_detail/T06_unified_models.md#ck-r3-25) | [T06_unified_models.md](index_detail/T06_unified_models.md) |
| T07 厳密一致・負荷・入力の測定と反例 | [CK-R3-18](index_detail/T07_exactness_load.md#ck-r3-18)<br>[CK-R3-19](index_detail/T07_exactness_load.md#ck-r3-19)<br>[CK-R3-20](index_detail/T07_exactness_load.md#ck-r3-20)<br>[CK-R7-22](index_detail/T07_exactness_load.md#ck-r7-22) | [CK-R3-21](index_detail/T07_exactness_load.md#ck-r3-21)<br>[CK-R3-23](index_detail/T07_exactness_load.md#ck-r3-23) | — | [CK-R3-27](index_detail/T07_exactness_load.md#ck-r3-27)<br>[CK-R3-28](index_detail/T07_exactness_load.md#ck-r3-28)<br>[CK-R3-29](index_detail/T07_exactness_load.md#ck-r3-29)<br>[CK-R3-30](index_detail/T07_exactness_load.md#ck-r3-30) | [T07_exactness_load.md](index_detail/T07_exactness_load.md) |
| T08 近似検証（M3〜M6） | [CK-R4-04](index_detail/T08_approximation.md#ck-r4-04)<br>[CK-R4-05](index_detail/T08_approximation.md#ck-r4-05)<br>[CK-R4-09](index_detail/T08_approximation.md#ck-r4-09)<br>[CK-R4-19](index_detail/T08_approximation.md#ck-r4-19)<br>[CK-R4-20](index_detail/T08_approximation.md#ck-r4-20)<br>[CK-R4-22](index_detail/T08_approximation.md#ck-r4-22)<br>[CK-R7-26](index_detail/T08_approximation.md#ck-r7-26) | [CK-R4-01](index_detail/T08_approximation.md#ck-r4-01)<br>[CK-R4-02](index_detail/T08_approximation.md#ck-r4-02)<br>[CK-R4-07](index_detail/T08_approximation.md#ck-r4-07)<br>[CK-R4-08](index_detail/T08_approximation.md#ck-r4-08)<br>[CK-R4-10](index_detail/T08_approximation.md#ck-r4-10)<br>[CK-R7-27](index_detail/T08_approximation.md#ck-r7-27) | [CK-R4-06](index_detail/T08_approximation.md#ck-r4-06)<br>[CK-R4-11](index_detail/T08_approximation.md#ck-r4-11)<br>[CK-R4-12](index_detail/T08_approximation.md#ck-r4-12)<br>[CK-R4-13](index_detail/T08_approximation.md#ck-r4-13)<br>[CK-R4-14](index_detail/T08_approximation.md#ck-r4-14)<br>[CK-R4-15](index_detail/T08_approximation.md#ck-r4-15)<br>[CK-R4-16](index_detail/T08_approximation.md#ck-r4-16)<br>[CK-R4-17](index_detail/T08_approximation.md#ck-r4-17)<br>[CK-R4-18](index_detail/T08_approximation.md#ck-r4-18)<br>[CK-R4-21](index_detail/T08_approximation.md#ck-r4-21) | [CK-R4-03](index_detail/T08_approximation.md#ck-r4-03)<br>[CK-R4-25](index_detail/T08_approximation.md#ck-r4-25)<br>[CK-R4-26](index_detail/T08_approximation.md#ck-r4-26) | [T08_approximation.md](index_detail/T08_approximation.md) |
| T09 記録・進捗台帳・報告書・必須成果物 | [CK-R5-01](index_detail/T09_records_reports.md#ck-r5-01)<br>[CK-R5-11](index_detail/T09_records_reports.md#ck-r5-11)<br>[CK-R5-17](index_detail/T09_records_reports.md#ck-r5-17) | [CK-R5-02](index_detail/T09_records_reports.md#ck-r5-02)<br>[CK-R5-03](index_detail/T09_records_reports.md#ck-r5-03)<br>[CK-R5-05](index_detail/T09_records_reports.md#ck-r5-05)<br>[CK-R5-08](index_detail/T09_records_reports.md#ck-r5-08)<br>[CK-R5-10](index_detail/T09_records_reports.md#ck-r5-10)<br>[CK-R5-13](index_detail/T09_records_reports.md#ck-r5-13)<br>[CK-R5-14](index_detail/T09_records_reports.md#ck-r5-14)<br>[CK-R5-15](index_detail/T09_records_reports.md#ck-r5-15)<br>[CK-R5-16](index_detail/T09_records_reports.md#ck-r5-16)<br>[CK-R5-18](index_detail/T09_records_reports.md#ck-r5-18)<br>[CK-R5-19](index_detail/T09_records_reports.md#ck-r5-19)<br>[CK-R5-20](index_detail/T09_records_reports.md#ck-r5-20)<br>[CK-R5-24](index_detail/T09_records_reports.md#ck-r5-24)<br>[CK-R5-29](index_detail/T09_records_reports.md#ck-r5-29) | [CK-R5-06](index_detail/T09_records_reports.md#ck-r5-06)<br>[CK-R5-07](index_detail/T09_records_reports.md#ck-r5-07) | [CK-R5-04](index_detail/T09_records_reports.md#ck-r5-04)<br>[CK-R5-09](index_detail/T09_records_reports.md#ck-r5-09)<br>[CK-R5-12](index_detail/T09_records_reports.md#ck-r5-12)<br>[CK-R5-21](index_detail/T09_records_reports.md#ck-r5-21)<br>[CK-R5-22](index_detail/T09_records_reports.md#ck-r5-22)<br>[CK-R5-23](index_detail/T09_records_reports.md#ck-r5-23)<br>[CK-R5-25](index_detail/T09_records_reports.md#ck-r5-25) | [T09_records_reports.md](index_detail/T09_records_reports.md) |
| T10 材料分類の設計草案 | — | [CK-R5-27](index_detail/T10_material_taxonomy.md#ck-r5-27) | [CK-R5-26](index_detail/T10_material_taxonomy.md#ck-r5-26) | [CK-R5-28](index_detail/T10_material_taxonomy.md#ck-r5-28) | [T10_material_taxonomy.md](index_detail/T10_material_taxonomy.md) |
| T11 中断した修正（65ff124）と未実施の改訂 | — | [CK-R1-11](index_detail/T11_interrupted_fix.md#ck-r1-11)<br>[CK-R2-19](index_detail/T11_interrupted_fix.md#ck-r2-19)<br>[CK-R2-20](index_detail/T11_interrupted_fix.md#ck-r2-20)<br>[CK-R2-21](index_detail/T11_interrupted_fix.md#ck-r2-21)<br>[CK-R2-22](index_detail/T11_interrupted_fix.md#ck-r2-22)<br>[CK-R2-23](index_detail/T11_interrupted_fix.md#ck-r2-23)<br>[CK-R3-31](index_detail/T11_interrupted_fix.md#ck-r3-31)<br>[CK-R3-32](index_detail/T11_interrupted_fix.md#ck-r3-32)<br>[CK-R3-36](index_detail/T11_interrupted_fix.md#ck-r3-36)<br>[CK-R4-23](index_detail/T11_interrupted_fix.md#ck-r4-23)<br>[CK-R7-32](index_detail/T11_interrupted_fix.md#ck-r7-32) | [CK-R2-18](index_detail/T11_interrupted_fix.md#ck-r2-18)<br>[CK-R4-24](index_detail/T11_interrupted_fix.md#ck-r4-24)<br>[CK-R5-30](index_detail/T11_interrupted_fix.md#ck-r5-30)<br>[CK-R5-31](index_detail/T11_interrupted_fix.md#ck-r5-31) | [CK-R2-24](index_detail/T11_interrupted_fix.md#ck-r2-24) | [T11_interrupted_fix.md](index_detail/T11_interrupted_fix.md) |
| T12 式の族と未実装の案（構造の棚卸し） | — | [CK-R7-04](index_detail/T12_formula_families.md#ck-r7-04)<br>[CK-R7-05](index_detail/T12_formula_families.md#ck-r7-05)<br>[CK-R7-06](index_detail/T12_formula_families.md#ck-r7-06)<br>[CK-R7-07](index_detail/T12_formula_families.md#ck-r7-07)<br>[CK-R7-08](index_detail/T12_formula_families.md#ck-r7-08)<br>[CK-R7-09](index_detail/T12_formula_families.md#ck-r7-09)<br>[CK-R7-10](index_detail/T12_formula_families.md#ck-r7-10)<br>[CK-R7-11](index_detail/T12_formula_families.md#ck-r7-11)<br>[CK-R7-12](index_detail/T12_formula_families.md#ck-r7-12)<br>[CK-R7-13](index_detail/T12_formula_families.md#ck-r7-13)<br>[CK-R7-14](index_detail/T12_formula_families.md#ck-r7-14) | [CK-R7-31](index_detail/T12_formula_families.md#ck-r7-31) | — | [T12_formula_families.md](index_detail/T12_formula_families.md) |

## 8. 保存資料の所在

### 8.1 Git の記録（作業ブランチ `claude/jcat-formula-approximation-study-c33936`）

| コミット | 内容 |
|---|---|
| `43ba5d7` | 第1回の検査の指摘を反映し、測定・順位・記録・報告書を再生成した版。コード・測定・記録・報告書が互いに対応している最後の版。第2回の検査はこの版を調べた |
| `60e720f` | 手順書 v1.4 の草稿を加えた版（`00_POLICY/EVALUATION_PROTOCOL.md` だけが `43ba5d7` と違う） |
| `65ff124` | 停止の時点の作業ツリーをそのまま記録した版（中断した修正。未検証・未完成） |
| `0db5c77` | 上の編集を作業ツリーから取り除き、`09_APPROX_STUDY/` を `60e720f` と同じ内容に戻した版 |
| それ以降 | この保存フォルダの資料と文書 |

### 8.2 旧研究の本体（削除していない）

| 所在 | 内容 |
|---|---|
| `09_APPROX_STUDY/00_POLICY/` | 旧指示書の写し、追加・変更指示、手順書（v1.4 草稿） |
| `09_APPROX_STUDY/01_LEDGER/` | 評価単位 70 件の台帳、シート族の集計、式に未接続だった入力 |
| `09_APPROX_STUDY/02_RANKING/` | 評価軸 A（測定した負荷）、評価軸 B（採点）、着手順序 |
| `09_APPROX_STUDY/03_MODELS/` | 統合モデル K1〜K7、導出 `DERIVATIONS.md`、近似候補、単位別の記録 454 件 |
| `09_APPROX_STUDY/04_VERIFICATION/` | 厳密一致、負荷、入力の使用、近似検証の測定結果、第1回の独立検査の記録 |
| `09_APPROX_STUDY/05_DECISIONS/` | 進捗台帳、採否の理由、旧指示書の必須成果物 |
| `09_APPROX_STUDY/06_OPEN_ISSUES/` | 未解決事項と規約 B-1〜B-21（第2回の指摘は未反映） |
| `09_APPROX_STUDY/07_MATERIAL_TAXONOMY/` | 材料分類の設計草案（データ構造と手順の形だけ。データセットではない） |
| `09_APPROX_STUDY/research_code/` | 基準計算 `refcalc`、統合モデル `fastcalc`、架空データの生成器 `synth`、測定 `bench`、記録と報告書の生成器 `tools`、試験 `tests`、比較 `common` |

### 8.3 この保存フォルダ

| 所在 | 内容 | 注意 |
|---|---|---|
| `STOP_ORDER.md` | 受領した停止・保存の指示（第0章） | |
| `STOP_STATUS.md` | 停止した対象、確認の結果、残っていたタスク、再開を防ぐ措置 | |
| `HANDOVER.md` | 実施内容、到達点、未完成部分、引継ぎ事項、移行条件の最終確認 | |
| `INDEX.md`、`index_detail/` | この索引と、項目ごとの詳細、指摘 59 件の登録簿 | |
| `materials/round2_review/triage/` | 第2回の独立検査の指摘 59 件の全文（5 観点）と、反証検査担当の判定。`res.json` は構造化した元データ | 指摘の一次資料 |
| `materials/round2_review/checker_scripts/` | 検査担当と反証検査担当が使った再現用のスクリプトとログ | **実行しない。** 旧研究のコードを読み込むので、実行は旧研究の計算の再開になる |
| `materials/interrupted_fix/specs/` | 中断した修正の仕様（a1、a2、b2、b3、反証検査の手順、記録と報告書の改訂の予定） | 設計の資料。実装の完了や検証を意味しない |
| `materials/interrupted_fix/agent_reports/` | 段階 a1・b2 の作業担当の報告 | 自己申告。独立の検査なし |
| `materials/interrupted_fix/a1_scratch/`、`a2_partial_outputs/`、`b2_output/` | 中断した修正の出力 | 未検証。a2 の分は途中の出力 |
| `materials/interrupted_fix/working_tree_at_stop_65ff124.patch` | 中断時の編集の差分（`65ff124` と同じ内容） | 適用しない |
| `materials/interrupted_fix/workflow_script_DO_NOT_RUN.js` | 中断した修正のワークフローの定義 | **実行しない** |
| `materials/earlier_session_scratch/` | それ以前の段階の作業用ファイル（第1回の検査、評価者の入力など） | 古い版の出力を含む。たとえば `wfB/axis_a_run.log.txt` は初版の測定（69 単位）で、公開中の版の測定（70 単位）ではない |
| `materials/classification/` | この索引のもとになった分類の JSON（7 観点）、分類担当への指示、索引の生成スクリプト | 生成スクリプトは JSON と文書を読むだけで、旧研究のコードを読み込まない |

## 9. この索引が扱っていない範囲

- 分類担当が読まなかったファイルと、読み取りだけでは確かめられなかった点は [index_detail/NOT_COVERED.md](index_detail/NOT_COVERED.md) に観点ごとに載せた。主なもの：中断時の差分（723 KB）の全文、検査担当のスクリプトの中身、単位別の記録 454 件の個々の文面、評価者の理由文の大半。
- 公開中の版の試験 28 件が今の環境で通るかどうかは確かめていない（第2回の報告書の検査担当は合格を報告している）。
- `65ff124` のコードが試験に通るか、指摘の再現が消えるかは確かめていない。
- 分類担当の読み取りで見つかり、第2回の指摘には無い点が 3 つある。いずれも実行による確認はしていない：(1) X-07 の関数は B2-01 の結果を読むが、依存の一覧に B2-01 が無い。(2) X-08 は B4-02 を依存に挙げるが、関数の中で読まない。(3) SYS-01 の目的の欄は「42 単位に渡す」と書くが、該当の欄は空で、実際の関係は別の欄（17 単位）にある。
- 第1章から第8章（`01_COMPLIANCE/` 〜 `08_BUILD_PLAN/`）は、旧研究より前の資料であり、この索引の対象ではない。変更していない。
- 旧研究のフォルダのファイルと、項目の「所在」との対応は、索引の生成時に機械的に照合した。結果は [HANDOVER.md](HANDOVER.md) の 5 節に記した。
