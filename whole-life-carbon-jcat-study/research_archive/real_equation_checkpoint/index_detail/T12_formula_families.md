# 索引の詳細 T12：式の族と未実装の案（構造の棚卸し）

[INDEX.md](../INDEX.md) の項目ごとの詳細。分類担当（読み取り専用）が書いた内容を、欄ごとにそのまま載せる。
旧研究の数値はすべて架空データでの値で、対象は独立概念モデルである。原版の表計算との一致や、実建物での精度を示すものではない。
所在の表記：`09_APPROX_STUDY/…` などは `whole-life-carbon-jcat-study/` からの位置、`materials/…` はこの保存フォルダからの位置。

| 項目 | 区分 | 題 |
|---|---|---|
| [CK-R7-04](#ck-r7-04) | 2 | 式の族 F01：行の和（活動量×換算倍率×係数） |
| [CK-R7-05](#ck-r7-05) | 2 | 式の族 F02：行ごとの数量の比・換算（端材率・再使用率） |
| [CK-R7-06](#ck-r7-06) | 2 | 式の族 F03：加重和・行列の展開・区分別の再集計 |
| [CK-R7-07](#ck-r7-07) | 2 | 式の族 F04：事象の数え上げ（評価期間 T と周期） |
| [CK-R7-08](#ck-r7-08) | 2 | 式の族 F05：年重み付き和（年次量×年ごとの係数） |
| [CK-R7-09](#ck-r7-09) | 2 | 式の族 F06：区分的に直線・段階的な電力係数の年次系列（X-06） |
| [CK-R7-10](#ck-r7-10) | 2 | 式の族 F07：冷媒の充填・漏洩・補充・交換（年ごとの漸化式） |
| [CK-R7-11](#ck-r7-11) | 2 | 式の族 F08：比・指標（原単位、単位換算、段階別割合） |
| [CK-R7-12](#ck-r7-12) | 2 | 式の族 F09：集約の木（段階ベクトルと部分和） |
| [CK-R7-13](#ck-r7-13) | 2 | 式の族 F10：基準案との比較（SUM-08） |
| [CK-R7-14](#ck-r7-14) | 2 | 式の族 F11：条件分岐・述語（入力検査、整合の検査、係数の解決） |
| [CK-R7-31](#ck-r7-31) | 3 | 検討したが実装・検証していない式の案（06_OPEN_ISSUES の G-1〜G-7、B-8 の別の選択肢） |

<a id="ck-r7-04"></a>

## CK-R7-04　式の族 F01：行の和（活動量×換算倍率×係数）

- **区分**：2　暫定・未検証成果
- **内容**：行（資材・設備・燃料・廃棄物・解体活動・費用項目・機器）ごとに 活動量×換算倍率×係数値 を作って足す形の 19 単位。活動量は数量そのもの、質量×距離、質量×経路の比率、費用のいずれかで、行の乗数（未数量分 r/(1−r)、積載率 1/lf、物価の比）が付く単位がある。区分は R7 が台帳の structure_class と基準定義文・コードを読んで付けた整理用のもので、旧研究の成果物ではない（独立の検査なし）。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py)
  - [`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md)
- **確かめ方**：値は第2回の再導出検査が定義文から書き直して比べた（下の evidence）。族としての形の読み取りは R7 だけ。
- **確かめた者**：独立検査（第2回）で再現（値の一致。族の区分は検査なし）
- **言える範囲**：架空データだけ。独立概念モデル（70 評価単位）の定義についての記述で、原版ブックの式との対応は未確認。有限で範囲内の入力について。
- **関係する第2回の指摘**：RED-2、RED-7、RED-8、RED-10、RED-11、NUM-5、REP-10
- **第2回の指摘の影響**：係数値・換算倍率・建設時の電力係数は検査されずに掛けられる（負・NaN がそのまま合計に入る。RED-2）。係数値が None だと全体がエラーになる（RED-10）。係数 ID が「GRID」「REFRIGERANT」だと擬似行と衝突する（NUM-5）。資材の初期の据付は計上されない（RED-8）。
- **今の時点で言ってよいこと**：有限で範囲内の入力では、この族の値は「行ごとの 活動量×換算倍率×係数値 の和」で、数量と係数値のそれぞれに 1 次、評価期間 T と年の添字に依存しない。
- **使ってはいけない記述**：
  - 「使えない係数・範囲外の値は必ず除外して数えられる」（係数値・換算倍率・建設時係数は対象外。RED-2）
  - 「製造の行結果」に未数量分 A13-04 が含まれるという読み（B3・B4 では含まれず、B5 では含まれる。RED-7）
- **新研究での再利用**：候補（ルート B・C）
  - 使い道：行×係数の双一次の部分（段階 A1-A3・A4・A5・C1〜C4 の本体）を、行列・テンソルの形で書き直すときの対象範囲と、行結果が下流（B3・B4・B5・X-04・X-05・X-17）へ渡る点の確認に使う。ルート A では統合モデル K1（行テーブル）に対応する。
  - 条件・注意：形の記述は 43ba5d7 の版の定義文とコードの読み取り。新しい定式化を作る作業は含まない。係数の使用条件（レコードあり、PERMITTED_PUBLIC、対象段階がその段階だけ、単位が換算可能。行固有の換算を先に見る、連鎖なし）と、択一（A13-01／A13-03、A4-01／A4-02）は、和の外にある離散の分岐である。STO-01・STO-02 は独立の書き直しがない。
- **分類の根拠**：
  - 件数（units.json から python で集計）：19 単位＝A13-01、A13-03、A13-04、A4-01、A4-02、A5-01、A5-02、A5-03、C1-01、C2-01、C3-01、C4-01、X-01、X-12、X-14、X-16、STO-01、STO-02、B1-01。台帳の structure_class：LINEAR_SUM_PRODUCT 17、RATIO 2。段階：A1-A3 5、A4 3、A5 3、C1 1、C2 1、C3 2、C4 1、MEMO 2、B1 1。出所：既存 15・追加 4。統合モデル（models.json）：K1 17、統合なし 1、K4 1
  - 形：E=Σ_i a_i·c_i·f_k(i)。A4-01・C2-01 は a=質量×距離、C3-01・C4-01 は a=廃棄質量×経路の比率（行×経路の二重和）、A13-04 は 行の製造排出×r/(1−r)、X-12 は ÷積載率、X-16 は ×(基準年の物価指数÷費用の年の物価指数)、A5-01 は 買電量×換算×建設時の電力係数（係数レコードなし）、B1-01 は 充填質量×GWP（在庫量）、STO-01 は 数量×密度×炭素含有率×44/12
  - 依存する変数：行 i、係数キー k(i)、段階（係数の対象段階との完全一致）、単位（換算倍率）。T・年添字・周期には依存しない。資材区分は式に現れない
  - 線形性：数量と係数値に双一次。行パラメータの有理関数（r/(1−r)、1/lf、指数の比）が乗数に入る単位が 3（A13-04、X-12、X-16）
  - 分岐：係数の使用条件（base.py:133-143 lookup）、択一（units_pre_a.py:331-362、452-519）、欠損・範囲外の行は足さずに n_skipped に数える
  - 段階合計に入る：A13-01・A13-03・A13-04・X-01（A1-A3）、A4-01・A4-02（A4）、A5-01〜03（A5-04 経由で A5）、C1-01、C2-01、C3-01・X-14（C3）、C4-01。入らない：X-12、X-16、STO-01、STO-02、B1-01
  - 第2回の再導出検査（[`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):145-148）での扱い：定義文から独立に書き直して値が一致 17 単位（A13-01、A13-03、A13-04、A4-01、A4-02、A5-01、A5-02、A5-03、B1-01、C1-01、C2-01、C3-01、C4-01、X-01、X-12、X-14、X-16）。独立の書き直しなし 2 単位（STO-01、STO-02）。
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):13-23（RED-2）、73-95（RED-7・RED-8）；[`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):49-59（NUM-5）
  - [`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md):13-37（D1）
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））

<a id="ck-r7-05"></a>

## CK-R7-05　式の族 F02：行ごとの数量の比・換算（端材率・再使用率）

- **区分**：2　暫定・未検証成果
- **内容**：資材の行ごとに、数量の基準と端材率から発注量と据付量を作る A13-05 と、端材の再使用を引いた正味の発注量 X-13 の 2 単位。結果は行ごとの一覧で、スカラーの合計を持たない。区分は R7 が台帳の structure_class と基準定義文・コードを読んで付けた整理用のもので、旧研究の成果物ではない（独立の検査なし）。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py)
- **確かめ方**：2 単位とも第2回の再導出検査が定義文から書き直して値が一致。族の区分は R7 だけ。
- **確かめた者**：独立検査（第2回）で再現（値の一致。族の区分は検査なし）
- **言える範囲**：架空データだけ。独立概念モデル（70 評価単位）の定義についての記述で、原版ブックの式との対応は未確認。0≦w<1、Q≧0、0≦ρ≦1 の行について。
- **関係する第2回の指摘**：REC-2、RED-12、APP-3
- **第2回の指摘の影響**：A13-05 と X-13 を統合モデル K1 の構成員に数えた記録は、統合の基準を満たさない（REC-2）。X-13 は無効な行の件数を返さない（RED-12）。端材倍率を変える近似の影響は下流の B3・B4・B5 に伝わる（APP-3）。
- **今の時点で言ってよいこと**：A13-05：数量の基準が DESIGN なら 据付量=Q、発注量=Q/(1−w)。ORDERED・AS_BUILT なら 発注量=Q、据付量=Q(1−w)。X-13：処分される端材=(発注量−据付量)(1−ρ)、正味の発注量=据付量＋処分される端材。
- **使ってはいけない記述**：
  - 「A13-05・X-13 は行テーブル（K1）に統合された」（REC-2）
- **新研究での再利用**：候補（ルート B・C）
  - 使い道：行和の族 F01 に掛かる行の乗数（w の有理関数 1/(1−w)）の定義として使う。A13-05 の発注量は 9 単位（A13-01、A13-03、A4-02、B4-02、C-05、X-03、X-08、X-10、X-13）に渡る。
  - 条件・注意：形の記述は 43ba5d7 の版の定義文とコードの読み取り。新しい定式化を作る作業は含まない。数量の基準による場合分け（DESIGN とそれ以外）がある。Q または w が欠損・範囲外の行は None になり、下流で除外される。
- **分類の根拠**：
  - 件数（units.json から python で集計）：2 単位＝A13-05、X-13。台帳の structure_class：RATIO 2。段階：A1-A3 2。出所：既存 1・追加 1。統合モデル（models.json）：K1 2
  - 依存する変数：行 i、端材率 w、再使用率 ρ、数量の基準（3 値）。Q に 1 次、w に非線形（1/(1−w)）。T に依存しない
  - [`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py):209-246
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json): A13-05.feeds
  - 第2回の再導出検査（[`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):145-148）での扱い：定義文から独立に書き直して値が一致 2 単位（A13-05、X-13）。
  - [`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):13-23（REC-2）；[`materials/round2_review/triage/approx.md`](../materials/round2_review/triage/approx.md):25-35（APP-3：AP-06 の合計への影響は、伝播させると最大 −0.655％、記録は最大 −0.384％）
  - [`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json): candidates.AP-06.stage_error（AP-06（端材倍率の線形化 1/(1−w) ≈ 1+w。記録の stage 欄：A1-A3）n=400、平均 -0.26％、範囲 -1.06％〜-0.05％、95％点（絶対値）0.48％）
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））

<a id="ck-r7-06"></a>

## CK-R7-06　式の族 F03：加重和・行列の展開・区分別の再集計

- **区分**：2　暫定・未検証成果
- **内容**：複合係数（質量比で加重した係数の和）A13-02、その構成材への展開 X-03、ガス別の内訳 X-04、CO2 だけの並行算定 X-05、資材区分×処理経路の表 X-09、6 区分の再集計 X-17 の 6 単位。同じ行の活動量に、別の列（質量比、ガス別量、区分、経路）を掛けて足し直す形である。区分は R7 が台帳の structure_class と基準定義文・コードを読んで付けた整理用のもので、旧研究の成果物ではない（独立の検査なし）。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py)
  - [`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md)
- **確かめ方**：A13-02 は第2回が直接書き直して一致。X-04・X-05 は係数値をガス別量に置き換える間接的な方法で 50 シナリオ差なし。X-03・X-09・X-17 は独立の書き直しがない。
- **確かめた者**：独立検査（第2回）で再現（A13-02 と、間接的に X-04・X-05。残り 3 単位は作成者のみ）
- **言える範囲**：架空データだけ。独立概念モデル（70 評価単位）の定義についての記述で、原版ブックの式との対応は未確認。有限で範囲内の入力について。
- **関係する第2回の指摘**：RED-4、NUM-3、NUM-6、RED-10、RED-12
- **第2回の指摘の影響**：X-04 は定義文が「一致することを確かめる」と言うが、照合の結果を返さず、係数のガス別量が係数値と合わなくてもどの検査にも掛からない（RED-4）。係数値が 0 でガス別量が 0 でない係数では、基準計算は B3 のガス別の行を落とす（NUM-3）。ガスの一覧に重複があると複合品の扱いが分かれる（NUM-6。統合モデル側）。X-17 は要約数量が 0 の区分を落とし、None では全体がエラーになる（RED-12・RED-10）。
- **今の時点で言ってよいこと**：A13-02：複合係数＝Σ_j(質量比_j×換算_j×係数_j)、質量比の合計が 1 から 1e-6 を超えてずれる行は係数を作らず、正規化しない。X-04：全 14 段階の行（係数 ID と活動量）にガス別量を掛けて足し、GWP で合算、買電と冷媒は別掲。X-05：同じ行に CO2 の量だけを掛ける。
- **使ってはいけない記述**：
  - 「X-04 はガス別量×GWP の合計が段階合計の総和に一致することを確かめる」（RED-4）
  - 「X-17 は定義上、6 区分の製造排出の再集計に等しい」（要約数量が 0 の区分では成り立たない。RED-12）
- **新研究での再利用**：候補（ルート B・C）
  - 使い道：行×構成材、行×ガス（7 種）、区分（13）×経路（4）という添字の組を持つ線形の展開の一覧として使う。ルート A では K7（複合係数）と K1（同じ表の別の読み方）に対応する。
  - 条件・注意：形の記述は 43ba5d7 の版の定義文とコードの読み取り。新しい定式化を作る作業は含まない。X-04・X-05 は B 段階の行も通るので、T への依存を上流（B3・B4・B5・B6・B7）から引き継ぐ。資材区分が式に現れるのは X-09 と X-17 だけ。
- **分類の根拠**：
  - 件数（units.json から python で集計）：6 単位＝A13-02、X-03、X-04、X-05、X-09、X-17。台帳の structure_class：WEIGHTED_AVERAGE 1、MATRIX_EXPANSION 1、LINEAR_SUM_PRODUCT 3、LOOKUP_JOIN 1。段階：A1-A3 3、SUM 2、C1-C4 1。出所：既存 1・追加 5。統合モデル（models.json）：K7 2、K1 4
  - 依存する変数：行 i、構成材 j、ガス g、資材区分 c、経路 r、段階 s。いずれも線形（数量×比率×係数の多重線形）。分岐：係数の使用条件、質量比の合計の検査、区分の割当て（units_pre_a.py:585-594 simple_class）
  - [`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py):249-280（A13-02）、429-449（X-03）、603-623（X-17）
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py):298-376（stage_lines、X-04、X-05）、163-187（X-09）
  - 第2回の再導出検査（[`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):145-148）での扱い：定義文から独立に書き直して値が一致 1 単位（A13-02）。間接的な確認だけ 2 単位（X-04、X-05）。独立の書き直しなし 3 単位（X-03、X-09、X-17）。
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):37-47（RED-4）；[`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):25-35（NUM-3）、61-71（NUM-6）
  - [`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md):21-37、136-137（D1・D8）
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））

<a id="ck-r7-07"></a>

## CK-R7-07　式の族 F04：事象の数え上げ（評価期間 T と周期）

- **区分**：2　暫定・未検証成果
- **内容**：周期 c の倍数 n·c が評価期間の内側にある個数 N(T,c) と、それを 1 回分の排出に掛ける形の 6 単位（更新年の一覧 B4-01、交換回数 B4-03、更新負荷 B4-02、建替 B5-01、周期別の集計 X-08、資源量・廃棄物量 X-10）。N は T と c の階段関数で、規約の許容幅を除けば ceil(T/c)−1 に等しい。区分は R7 が台帳の structure_class と基準定義文・コードを読んで付けた整理用のもので、旧研究の成果物ではない（独立の検査なし）。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py)
  - [`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md)
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md)
- **確かめ方**：B4-01・B4-02・B4-03・B5-01・X-10 は第2回が定義文から書き直して一致。回数の閉形式は第2回の 2 つの検査が数え上げと総当たりで比べ、不一致 0（CK-R7-23）。X-08 は独立の書き直しがない。
- **確かめた者**：独立検査（第2回）で再現（値の一致。X-08 は作成者のみ。族の区分は検査なし）
- **言える範囲**：架空データだけ。独立概念モデル（70 評価単位）の定義についての記述で、原版ブックの式との対応は未確認。周期が有限の正の数である行について。
- **関係する第2回の指摘**：RED-1、RED-3、RED-7、RED-8、RED-9、RED-11、RED-12、APP-5、NUM-1
- **第2回の指摘の影響**：負・0・NaN・無限大の周期は「事象なし」になり、件数にも不完全の印にも出ない（RED-3、一部確認）。B5 の不完全の印は上流の除外を拾わない（RED-1）。明示の一覧に同じ年が重複していれば、その回数だけ数える（RED-11）。正の周期に下限がなく、周期 1e-4・T=60 では 1 行で 599999 回になる（RED-12）。事象の属する年の判定は周期 1.000000001 で丸めに依存する（NUM-1 の検証者の追加指摘。B4-02・B5-01 の年次の置き場所にも同じ判定が使われる）。
- **今の時点で言ってよいこと**：N(T,c)=#{n≧1：n·c<T·(1−1e-9)}。明示の更新年一覧があれば 0<t かつ内側のものを使う。B4-02=Σ_i N_i·u_i（u_i は 製造＋搬入＋据付＋旧品の廃棄 の 1 回分）、B5-01=N(T,C)·範囲比·(初期の A1-A3＋A4＋A5＋C1〜C4)、X-10 は質量×(1＋N)。
- **使ってはいけない記述**：
  - 「T/c−1≦N が必ず成り立つ」（許容幅 1e-9 の範囲で破れる。APP-5）
  - 「不正な周期は除外して数えられ、合計に不完全の印が付く」（RED-3）
  - 「B4-02 の製造は A1-A3 の行結果」を未数量分込みと読むこと（A13-01＋A13-03 だけ。B5 は A13-04 込み。RED-7）
- **新研究での再利用**：候補（ルート B・C）
  - 使い道：床・天井関数で表される不連続な T 依存（T=n·c で 1 段上がる）と、「回数×1 回分」という積の形の所在を示す。ルート A では K2（回数関数と周期ごとの合算 Σ_c N(T,c)·U_c）に対応する。
  - 条件・注意：形の記述は 43ba5d7 の版の定義文とコードの読み取り。新しい定式化を作る作業は含まない。規約：T ちょうどの事象は数えない（B-2）、許容幅 1e-9（B-15）、事象は属する年（切り上げ）に置く（B-3）、建替があっても周期を初期化しない（B-7）、更新時も初期と同じ係数（B-8）。連続な近似は架空の母集団で大きく外れた（下の evidence）。
- **分類の根拠**：
  - 件数（units.json から python で集計）：6 単位＝B4-01、B4-03、B4-02、B5-01、X-08、X-10。台帳の structure_class：EVENT_SCHEDULE 2、COUNT_FLOOR 1、LINEAR_SUM_PRODUCT 2、LOOKUP_JOIN 1。段階：B4 4、B5 1、SUM 1。出所：既存 4・追加 2。統合モデル（models.json）：K2 6
  - 依存する変数：T、周期（資材の refresh_cycle、設備の service_life、建物の replacement_cycle）、行 i、事象の番号 n、事象の属する年。T と c に非線形（階段）、1 回分の排出 u_i に 1 次。T を動かすと c ごとに周期的に段が現れる
  - 分岐：明示の一覧か周期か、建替シナリオが NONE か、範囲比が 0〜1 か、周期が欠損・非正なら 0 回
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py):91-93（inside）、109-126（periodic_events、explicit_events、event_year）
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py):18-41、73-177、367-391
  - 第2回の再導出検査（[`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):145-148）での扱い：定義文から独立に書き直して値が一致 5 単位（B4-01、B4-02、B4-03、B5-01、X-10）。独立の書き直しなし 1 単位（X-08）。
  - 反例（[`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)、架空の母集団 400、B4 の段階誤差）：AP-01（更新回数の連続近似 N ≈ max(0, T/c − 1)。記録の stage 欄：B4）n=400、平均 -18.68％、範囲 -58.47％〜0.00％、95％点（絶対値）41.73％；AP-02（更新回数の中点補正 N ≈ max(0, T/c − 1/2)。記録の stage 欄：B4）n=400、平均 +22.52％、範囲 -15.11％〜+983.53％、95％点（絶対値）66.82％；AP-03（更新回数の切り捨てなし N ≈ T/c。記録の stage 欄：B4）n=400、平均 +95.56％、範囲 +16.20％〜+2158.07％、95％点（絶対値）251.09％
  - AP-20 の上下限の幅（基準値に対する比、同ファイル candidates.AP-20.bracket_width_relative_to_reference）：平均 114.24％、最大 2172.52％
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):25-35（RED-3）、121-143（RED-11・RED-12）；[`materials/round2_review/triage/approx.md`](../materials/round2_review/triage/approx.md):49-59（APP-5）
  - [`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md):39-59、75-78（D2・D4）；[`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md):27-34,43,51
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））
- **停止後の点検による訂正**：点検の指摘 C1-06 により、上の記述の一部を改めた。分類担当の元の記述は `materials/classification/R7.json`、訂正の内容は `materials/classification/overrides.json` にある。

<a id="ck-r7-08"></a>

## CK-R7-08　式の族 F05：年重み付き和（年次量×年ごとの係数）

- **区分**：2　暫定・未検証成果
- **内容**：評価年 y=1..Y（Y=ceil(T)）について、年次量と係数の積に年重み w_y=min(1, T−(y−1)) を掛けて足す形の 13 単位（買電と燃料の B6、施設管理分 B2、上水・下水・一般廃棄物の B7、修繕 B3、面積当たりの推定 X-11、年次・累積の系列 X-07）。区分は R7 が台帳の structure_class と基準定義文・コードを読んで付けた整理用のもので、旧研究の成果物ではない（独立の検査なし）。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py)
  - [`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md)
- **確かめ方**：X-11 以外の 12 単位は第2回が定義文から書き直して一致。年和の閉形式は総当たりで不一致 0（CK-R7-23）だが、修繕の除外年の重みだけは周期 1.000000001 で基準計算と食い違う（CK-R7-20）。
- **確かめた者**：独立検査（第2回）で再現（値の一致。X-11 は作成者のみ。族の区分は検査なし）
- **言える範囲**：架空データだけ。独立概念モデル（70 評価単位）の定義についての記述で、原版ブックの式との対応は未確認。年次量・係数が有限で 0 以上、年次表が ceil(T) 以上の長さを持つ入力について。
- **関係する第2回の指摘**：RED-2、RED-10、RED-12、NUM-1、REC-1、NUM-3、NUM-4、NUM-10、REC-6、REP-17、APP-2
- **第2回の指摘の影響**：年次量（ガス・石油・地域熱・上水・下水・廃棄物）は負や NaN でもそのまま使われ、規約 B-18 と食い違う（RED-2）。評価期間より短い年次表は IndexError になる（NUM-4、RED-10）。B6=B6-03−B2-01 は施設管理の比率が 1 に近く燃料が小さいと桁落ちする（NUM-10）。B2-01 は B6-01 が算出されていなくても computed=True、値 0 を返す（RED-12）。基準計算の B3-01 は 修繕率が 0 または初期排出が 0 の行のガス別の行を落とす（NUM-3）。
- **今の時点で言ってよいこと**：年重みは Σ_y w_y=T。B6-04：買電量_y=max(0, 消費_y−(発電_y−売電_y))。B6-01：買電量_y×換算×電力係数_y。B6-03=Σ_y w_y(買電排出_y＋燃料排出_y)。B2-01=比率×Σ_y w_y·買電排出_y。B7-04 も同じ形。B3-01=Σ_i e0_i·r_i·Σ_{y∉S_i} w_y（S_i はその行の更新が属する年）。B3-02=T·Σ_i e0_i·r_i。X-07 は年次の値と事象の値を年に置いて累積する。
- **使ってはいけない記述**：
  - 「負の年次量は除外して数えられる」（B-18 の文言。RED-2）
  - 「B6 段階」と書かれた近似誤差の表を段階 B6 の誤差として読むこと（測った量は B6-03＝段階 B6＋B2。APP-2）
  - 「更新の周期が 1 年以上なら事象ごとに年が違う」（基準計算の浮動小数点の年の割当てでは周期 1.000000001 で成り立たない。REC-1・NUM-1）
- **新研究での再利用**：候補（ルート B・C）
  - 使い道：年の添字を持つ 2 つの系列の積の和（買電量×電力係数）、端数年の重み、打ち切り max(0,·)、事象の年を除く和（修繕）の所在を示す。ルート A では K3（区分的に直線な系列のモーメント）と K2（修繕の除外年の重み）に対応する。
  - 条件・注意：形の記述は 43ba5d7 の版の定義文とコードの読み取り。新しい定式化を作る作業は含まない。年次量は 一定・直線（base＋slope·k）・年次表 の 3 種で、一定と直線は記述子が正、年次表は写し（食い違いは報告だけ。B-16）。単位は「単位/year」に限る（B-20）。X-07 の関数は依存に宣言していない B2-01 を読む（CK-R7-02）。修繕は事象の数え上げ（F04）と結び付いている。
- **分類の根拠**：
  - 件数（units.json から python で集計）：13 単位＝B6-01、B6-02、B6-03、B6-04、B7-01、B7-02、B7-03、B7-04、B2-01、X-11、B3-01、B3-02、X-07。台帳の structure_class：LINEAR_SUM_PRODUCT 7、TIME_SERIES_SUM 4、MAX_CLAMP 1、RATIO 1。段階：B6 5、B7 4、B2 1、B3 2、SUM 1。出所：既存 11・追加 2。統合モデル（models.json）：K3 9、K1 1、K2 3
  - 依存する変数：年の添字 k=y−1、T（Y と最終年の重み）、燃料の種類、行 i（B3）、事象の年（B3-01、X-07）。年次量と係数に 1 次、買電量と電力係数については双一次（2 つの年系列の積）。打ち切り max(0,·) は区分的に 1 次。T への依存は、端数年の重みにより連続で区分的に 1 次（B3-01 と X-07 は事象の年を通じて不連続）。周期性は事象を通じてだけ現れる
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py):83-88（year_weights）、152-164（profile_values）
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py):186-260（B3）、413-572（B6・B2・X-11・B7）；[`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py):379-425（X-07）
  - 第2回の再導出検査（[`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):145-148）での扱い：定義文から独立に書き直して値が一致 12 単位（B2-01、B3-01、B3-02、B6-01、B6-02、B6-03、B6-04、B7-01、B7-02、B7-03、B7-04、X-07）。独立の書き直しなし 1 単位（X-11）。
  - 反例（[`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)、架空の母集団。AP-08 の stage 欄は B6 だが、基準にとった量は B6-03＝段階 B6＋B2。APP-2）：AP-08（買電排出を 平均買電量×平均係数×T で近似。記録の stage 欄：B6）n=400、平均 +0.22％、範囲 -8.13％〜+11.81％、95％点（絶対値）3.24％；AP-04（修繕の更新年除外を無視（B3-02 で B3-01 を代用）。記録の stage 欄：B3）n=400、平均 +2.05％、範囲 +0.06％〜+5.42％、95％点（絶対値）3.97％；AP-14（評価期間 T=60 の合計を、同じ建物の T=50 と T=75 の結果からの直線補間で求める。記録の stage 欄：WLC）n=80、平均 +2.30％、範囲 -11.93％〜+22.77％、95％点（絶対値）11.80％
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):13-23（RED-2）；[`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):37-47（NUM-4）、109-119（NUM-10）；[`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):61-71（REC-6）；[`materials/round2_review/triage/approx.md`](../materials/round2_review/triage/approx.md):13-23（APP-2）
  - [`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md):61-108（D3・D5）
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））
- **停止後の点検による訂正**：点検の指摘 C1-06 により、上の記述の一部を改めた。分類担当の元の記述は `materials/classification/R7.json`、訂正の内容は `materials/classification/overrides.json` にある。

<a id="ck-r7-09"></a>

## CK-R7-09　式の族 F06：区分的に直線・段階的な電力係数の年次系列（X-06）

- **区分**：2　暫定・未検証成果
- **内容**：電力排出係数の年次系列を、記述子から作る 1 単位。一定、直線低下（下限つき：max(下限, 初期値−年低下量×k)）、段階（添字 0 から厳密に増える段）の 3 種は記述子が整っていれば記述子から、それ以外は年次表から取る。年次量の 一定・直線・年次表 の扱い（base.py の profile_values）も同じ考え方である。区分は R7 が台帳の structure_class と基準定義文・コードを読んで付けた整理用のもので、旧研究の成果物ではない（独立の検査なし）。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py)
  - [`09_APPROX_STUDY/research_code/synth/model.py`](../../../09_APPROX_STUDY/research_code/synth/model.py)
  - [`09_APPROX_STUDY/research_code/fastcalc/closed_forms.py`](../../../09_APPROX_STUDY/research_code/fastcalc/closed_forms.py)
- **確かめ方**：第2回の再導出検査が定義文から書き直して一致。区分への分解（grid_segments）は、第2回の 2 つの検査がループと比べて同一と報告（不正な記述子を含む 120,000 件ほか）。
- **確かめた者**：独立検査（第2回）で再現（値の一致。族の区分は検査なし）
- **言える範囲**：架空データだけ。独立概念モデル（70 評価単位）の定義についての記述で、原版ブックの式との対応は未確認。記述子と年次表の値が有限である入力について。
- **関係する第2回の指摘**：NUM-2、NUM-7、RED-2、REP-17
- **第2回の指摘の影響**：記述子に NaN・無限大があると、基準計算は年次表を使うか記述子を使い、統合モデルは例外になる（NUM-2）。段の添字が float だと統合モデルだけ例外になる（NUM-7）。係数の値は負でも NaN でも検査されない（RED-2）。記述子が整っていても、年次表が ceil(T) より短いと全体がエラーになる規則がどの規約一覧にも無い（REP-17）。
- **今の時点で言ってよいこと**：添字 k=y−1 の系列は、整った記述子では区間ごとに g_k=α＋β·k（直線低下は下限に達する添字で 2 区間、段階は段ごとに定数）で、整っていなければ年次表の値。建設時の係数は添字 0 より前の別の 1 値。どちらを使ったか（source）と年次表との一致（matches_table）を報告する。
- **使ってはいけない記述**：
  - 「年次表は、整った記述子があれば写しにすぎない」（長さの検査は常に年次表に掛かる。REP-17）
- **新研究での再利用**：候補（ルート B・C）
  - 使い道：年の添字に対する係数系列の種類（定数、折れ線 1 か所、階段、任意の表）の一覧として使う。ルート A では K3 の G=Σ w·g、H=Σ w·k·g を求める区分の分解に対応する。
  - 条件・注意：形の記述は 43ba5d7 の版の定義文とコードの読み取り。新しい定式化を作る作業は含まない。「整っている」条件（低下量≧0、初期値≧下限、段が添字 0 から厳密に増加）は離散の分岐で、満たさなければ表に落ちる。年次表は 130 個以上かつ ceil(T) 個以上（synth/model.py）。
- **分類の根拠**：
  - 件数（units.json から python で集計）：1 単位＝X-06。台帳の structure_class：MAX_CLAMP 1。段階：B6 1。出所：既存 0・追加 1。統合モデル（models.json）：K3 1
  - 依存する変数：年の添字 k、系列の種類（4 値）、パラメータ（初期値、年低下量、下限、段）。k について区分的に 1 次または区分的に定数。max による折れ点が最大 1 つ
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py):171-203（grid_well_formed、grid_values）
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py):396-406（X-06）
  - [`09_APPROX_STUDY/research_code/synth/model.py`](../../../09_APPROX_STUDY/research_code/synth/model.py):513-569（AnnualProfile、GridFactorScenario）
  - 第2回の再導出検査（[`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):145-148）での扱い：定義文から独立に書き直して値が一致 1 単位（X-06）。
  - 反例（[`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)。stage 欄は B6 だが、基準にとった量は B6-03＝段階 B6＋B2。APP-2）：AP-09a（電力係数を 5 年ごとの点の直線補間で持つ（全種類の系列に適用）。記録の stage 欄：B6）n=400、平均 +0.01％、範囲 -3.95％〜+3.82％、95％点（絶対値）1.56％；AP-09b（電力係数を 10 年ごとの点の直線補間で持つ（全種類の系列に適用）。記録の stage 欄：B6）n=400、平均 +0.06％、範囲 -5.37％〜+7.49％、95％点（絶対値）2.76％；AP-09c（併用：パラメータ型の系列は厳密な閉形式、年次表の系列だけ 5 年ごとの点の直線補間。記録の stage 欄：B6）n=98、平均 +0.14％、範囲 -1.35％〜+1.73％、95％点（絶対値）1.27％
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):13-23（NUM-2）、73-83（NUM-7）；[`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):113-118（REP-17）；[`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):110（CHECKS 4：区分の分解は基準計算と同一）
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））

<a id="ck-r7-10"></a>

## CK-R7-10　式の族 F07：冷媒の充填・漏洩・補充・交換（年ごとの漸化式）

- **区分**：2　暫定・未検証成果
- **内容**：機器ごとに残存量を 1 年ずつ進める 3 単位（使用期間の漏洩 B1-02、交換時の損失 B1-03、廃棄時の未回収 B1-04）。その年の漏洩＝年初の残存量×年間漏洩率×年重み。補充しない機器は年末に漏洩分を引き、交換は属する年の年末に残存量を初期充填量へ戻す。毎年補充する機器は残存量が常に初期充填量。区分は R7 が台帳の structure_class と基準定義文・コードを読んで付けた整理用のもので、旧研究の成果物ではない（独立の検査なし）。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py)
  - [`09_APPROX_STUDY/research_code/fastcalc/closed_forms.py`](../../../09_APPROX_STUDY/research_code/fastcalc/closed_forms.py)
  - [`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md)
- **確かめ方**：3 単位とも第2回の再導出検査が定義文から書き直して一致。閉形式（refrigerant_fractions）は第2回の 2 つの検査が年ごとのループと 40,000 件・150,000 件で比べ、不一致 0。
- **確かめた者**：独立検査（第2回）で再現（値の一致。族の区分は検査なし）
- **言える範囲**：架空データだけ。独立概念モデル（70 評価単位）の定義についての記述で、原版ブックの式との対応は未確認。充填量・GWP が 0 以上、漏洩率・損失率・回収率が 0〜1 の機器について。
- **関係する第2回の指摘**：RED-3、RED-9、NUM-10、APP-6
- **第2回の指摘の影響**：機器の耐用年数が負・NaN などでも「交換なし」として計算され、印が付かない（RED-3）。B1-02 の定義文の式には ×GWP が書かれていない（RED-9、文言）。漏洩率が 1 に極めて近く補充なしのとき、年次の小さな値で 1e-9 を超える差が出る（NUM-10）。近似候補 AP-05 が測ったのは題名の線形化ではなく「すべての機器を常に満充填とみなす」形である（APP-6）。
- **今の時点で言ってよいこと**：補充なし：m_{y+1}=m_y·(1−r·w_y)、交換のない j 年のあとは m0·(1−r)^j。補充あり：m≡m0、漏洩は m0·r·T。B1-03=Σ_機器 損失率×GWP×Σ_交換 (交換直前の残存量)。B1-04=Σ_機器 (期末の残存量)×(1−回収率)×GWP。交換は交換年一覧（0<t かつ内側）、なければ耐用年数の倍数。B1-04 は B1 段階に入れる（B-6）。
- **使ってはいけない記述**：
  - AP-05 の数値を「1−(1−r)^k≈r·k の線形化の誤差」として引用すること（APP-6）
- **新研究での再利用**：候補（ルート B・C）
  - 使い道：状態（残存量）を持つ唯一の族として、漸化式・等比の和・事象による初期化の所在を示す。ルート A では K4（充填サイクルの質量収支）に対応する。
  - 条件・注意：形の記述は 43ba5d7 の版の定義文とコードの読み取り。新しい定式化を作る作業は含まない。漏洩率 r に非線形（べき）、初期充填量と GWP に 1 次。交換の年は事象の数え上げ（F04）と同じ判定を使う。同じ年に複数の交換があれば、その回数だけ交換直前の残存量を記録する。
- **分類の根拠**：
  - 件数（units.json から python で集計）：3 単位＝B1-02、B1-03、B1-04。台帳の structure_class：RECURRENCE 1、EVENT_SCHEDULE 1、LINEAR_SUM_PRODUCT 1。段階：B1 2、B1/C 1。出所：既存 3・追加 0。統合モデル（models.json）：K4 3
  - 依存する変数：機器 d、評価年 y、T（Y と最終年の重み）、交換の年（周期または一覧）、漏洩率 r、補充の有無（2 値の分岐）、GWP、損失率、回収率。補充なしで交換が周期のとき、残存量は交換のたびに初期充填量へ戻る
  - [`09_APPROX_STUDY/research_code/refcalc/units_b.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_b.py):265-362
  - [`09_APPROX_STUDY/research_code/fastcalc/closed_forms.py`](../../../09_APPROX_STUDY/research_code/fastcalc/closed_forms.py):175-219；[`09_APPROX_STUDY/03_MODELS/DERIVATIONS.md`](../../../09_APPROX_STUDY/03_MODELS/DERIVATIONS.md):110-119（D6）
  - 第2回の再導出検査（[`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):145-148）での扱い：定義文から独立に書き直して値が一致 3 単位（B1-02、B1-03、B1-04）。
  - 反例（[`09_APPROX_STUDY/04_VERIFICATION/approximation_study.json`](../../../09_APPROX_STUDY/04_VERIFICATION/approximation_study.json)、B1 の段階誤差。APP-6 の但し書きつき）：AP-05（冷媒漏洩の線形近似 1−(1−r)^k ≈ r·k。記録の stage 欄：B1）n=400、平均 +28.02％、範囲 0.00％〜+180.71％、95％点（絶対値）109.77％
  - [`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):134（CHECKS 3：refrigerant_fractions 40,000 件、絶対 1e-12 を超える差なし）；[`materials/round2_review/triage/records.md`](../materials/round2_review/triage/records.md):110（CHECKS 4：150,000 件、不一致 0、最大 3.5e-15）
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):97-107（RED-9）；[`materials/round2_review/triage/approx.md`](../materials/round2_review/triage/approx.md):61-71（APP-6）
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））

<a id="ck-r7-11"></a>

## CK-R7-11　式の族 F08：比・指標（原単位、単位換算、段階別割合）

- **区分**：2　暫定・未検証成果
- **内容**：ホールライフの合計を延床面積、面積×評価年数、1000 で割る SUM-04・SUM-05・SUM-06 と、段階の値を合計で割る SUM-07 の 4 単位。区分は R7 が台帳の structure_class と基準定義文・コードを読んで付けた整理用のもので、旧研究の成果物ではない（独立の検査なし）。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py)
- **確かめ方**：4 単位とも第2回の再導出検査が定義文から書き直して一致。
- **確かめた者**：独立検査（第2回）で再現（値の一致。族の区分は検査なし）
- **言える範囲**：架空データだけ。独立概念モデル（70 評価単位）の定義についての記述で、原版ブックの式との対応は未確認。
- **関係する第2回の指摘**：RED-12、REP-4、NUM-11
- **第2回の指摘の影響**：SUM-05 の「評価年数が 0 以下」の分岐は、期間の検査が先にエラーにするので到達しない（RED-12）。SUM-04〜08 を統合モデル K5 に数えたのは名札によるもので、計算は基準計算と同じ式のまま（REP-4）。旧研究の比較関数は合計に比例する下限を全 leaf に掛けており、SUM-07 のような無次元の小さな値では相対 1e-9 より緩かった（NUM-11）。
- **今の時点で言ってよいこと**：SUM-04=合計÷延床面積（面積が欠損または 0 以下なら算出しない）、SUM-05=合計÷(面積×T)、SUM-06=合計÷1000、SUM-07=対象段階ごとに 段階の値÷合計（合計が 0 以下、または負の段階があれば定義しない）。
- **使ってはいけない記述**：
  - 「SUM-04〜08 は共有のパラメータ付き関数に統合された」（REP-4）
- **新研究での再利用**：候補（ルート B・C）
  - 使い道：段階ベクトルの線形関数を尺度で割る形（尺度に対しては非線形）の一覧として使う。
  - 条件・注意：形の記述は 43ba5d7 の版の定義文とコードの読み取り。新しい定式化を作る作業は含まない。合計が不完全（complete が偽）でも指標は数値を返す。指標そのものは不完全の印を持たない。
- **分類の根拠**：
  - 件数（units.json から python で集計）：4 単位＝SUM-04、SUM-05、SUM-06、SUM-07。台帳の structure_class：RATIO 4。段階：SUM 4。出所：既存 4・追加 0。統合モデル（models.json）：K5 4
  - 依存する変数：段階 s、延床面積 A、T。段階の値に 1 次、A と T に対しては逆数。分岐：面積が無効なら None、割合は条件つきで未定義
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py):457-492
  - 第2回の再導出検査（[`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):145-148）での扱い：定義文から独立に書き直して値が一致 4 単位（SUM-04、SUM-05、SUM-06、SUM-07）。
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):133-143（RED-12）；[`materials/round2_review/triage/reports.md`](../materials/round2_review/triage/reports.md):22-27（REP-4。第2検証者なし）；[`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):121-131（NUM-11）
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））

<a id="ck-r7-12"></a>

## CK-R7-12　式の族 F09：集約の木（段階ベクトルと部分和）

- **区分**：2　暫定・未検証成果
- **内容**：工事負荷の合計 A5-04、14 段階のベクトルを作る X-02、その部分和であるアップフロント SUM-01・エンボディド SUM-02・ホールライフ SUM-03 の 5 単位。対象段階の指定（included_lifecycle_stages）が 0／1 の重みとして掛かる。区分は R7 が台帳の structure_class と基準定義文・コードを読んで付けた整理用のもので、旧研究の成果物ではない（独立の検査なし）。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py)
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md)
- **確かめ方**：5 単位とも第2回が定義文から書き直して一致。さらに第2回は、欠陥のない 1 シナリオ（T=62.5、改修周期 25）で 14 段階の選び方 16384 通りすべてを調べ、不一致 0（二重計上・消失なし。記載済みの規約と RED-8 を除く）と報告。
- **確かめた者**：独立検査（第2回）で再現（値の一致。族の区分は検査なし）
- **言える範囲**：架空データだけ。独立概念モデル（70 評価単位）の定義についての記述で、原版ブックの式との対応は未確認。部分集合の確認は欠陥のない 1 シナリオだけ。
- **関係する第2回の指摘**：RED-1、RED-5、RED-12、RED-8
- **第2回の指摘の影響**：不完全の印（complete、incomplete_units）は、段階を直接構成する単位の件数しか見ない。境界に B3 または B5 だけを含め、上流の A1-A3 などを外すと、上流で除外された行があっても complete が真のままになる（例：対象段階が B3 だけのとき SUM-03 が 98378.05 から 43676.16 へ下がって complete は真。RED-1、重大度 HIGH）。X-02 は定義文に無い by_stage_all（14 段階、B6 は常に B2 を引いた値）も返す（RED-12）。
- **今の時点で言ってよいこと**：X-02 の規則：A1-A3=A13-01＋A13-03＋A13-04＋X-01、A4=A4-01＋A4-02、A5=A5-04、B1=B1-02＋B1-03＋B1-04、B2=B2-01、B3=B3-01、B4=B4-02、B5=B5-01、B6=B6-03−B2-01（B2 が対象外なら B6-03）、B7=B7-04、C1=C1-01、C2=C2-01、C3=C3-01＋X-14、C4=C4-01。対象外の段階は結果に入れない。SUM-01=A1-A3＋A4＋A5、SUM-02=A1-A3〜A5＋B1〜B5＋C1〜C4、SUM-03=14 段階。
- **使ってはいけない記述**：
  - 「合計から何かを除いたら、その合計には不完全の印が付く」（B-17 と base.py の文言。RED-1）
  - 「X-02 は対象外の段階を結果に含めない」を全出力について読むこと（by_stage_all と X-05 の by_stage_co2 は 14 段階を返す。RED-12）
- **新研究での再利用**：候補（ルート B・C）
  - 使い道：最終の合計がどの単位の和でできているか（29 単位→14 段階→3 つの部分和）と、B2／B6 の条件つきの引き算、参考値・代替値を合計に入れない規則の確認に使う。
  - 条件・注意：形の記述は 43ba5d7 の版の定義文とコードの読み取り。新しい定式化を作る作業は含まない。規約：B1-04 は B1 に入れる（B-6）、B2 は買電排出の定率で B2 が対象のときだけ B6 から引く（B-10）、エンボディド SUM-02 は B2 を含む、ガスの範囲はラベルで合計は常に全ガス（B-12）、設備の初期の搬入・据付と資材の初期の据付は計上しない（B-11、RED-8）。
- **分類の根拠**：
  - 件数（units.json から python で集計）：5 単位＝A5-04、X-02、SUM-01、SUM-02、SUM-03。台帳の structure_class：SUM_OF_STAGES 5。段階：A5 1、SUM 4。出所：既存 4・追加 1。統合モデル（models.json）：K1 2、K5 3
  - 依存する変数：段階 s（14）、対象段階の集合。段階の値に 1 次（0／1 の重みつき和）。条件つきの項が 1 つ（B2 が対象かどうかで B6 の式が変わる）
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py):240-291（STAGE_UNITS、X-02）、430-454（SUM-01〜03）；[`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py):571-579（A5-04）
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json): X-02.depends_on（29 単位）
  - 第2回の再導出検査（[`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):145-148）での扱い：定義文から独立に書き直して値が一致 5 単位（A5-04、SUM-01、SUM-02、SUM-03、X-02）。
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):146（CHECKS 3：16384 通り、不一致 0）、1-11（RED-1）、85-95（RED-8）、133-143（RED-12）
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md):31,36-40（B-6、B-10、B-11、B-12）
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））

<a id="ck-r7-13"></a>

## CK-R7-13　式の族 F10：基準案との比較（SUM-08）

- **区分**：2　暫定・未検証成果
- **内容**：基準シナリオが指定されていれば、基準シナリオを同じ基準計算で最初から計算し、差＝当該案−基準案、削減率＝(基準案−当該案)÷基準案 を出す 1 単位。延床面積・評価期間・対象段階・ガスの範囲・係数の公開年の集合がすべて一致するときだけ比べる。区分は R7 が台帳の structure_class と基準定義文・コードを読んで付けた整理用のもので、旧研究の成果物ではない（独立の検査なし）。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py)
  - [`09_APPROX_STUDY/research_code/synth/population.py`](../../../09_APPROX_STUDY/research_code/synth/population.py)
- **確かめ方**：第2回の再導出検査は、基準案を計算し直す間接的な方法で 3 シナリオを確認（差なし）。数値の反例探しは、基準案に欠陥・別の期間・別の面積・循環・自己参照などを与えた場合に基準計算と統合モデルが一致することを確認（NUM-2・NUM-4 に由来する例外の非対称 2 件を除く）。
- **確かめた者**：独立検査（第2回）で再現（間接的な確認。族の区分は検査なし）
- **言える範囲**：架空データだけ。独立概念モデル（70 評価単位）の定義についての記述で、原版ブックの式との対応は未確認。
- **関係する第2回の指摘**：RED-5、NUM-9、NUM-10
- **第2回の指摘の影響**：完全性は比較の条件に入っておらず、基準案の合計が不完全でも status は COMPARED になり、基準案の不完全は結果のどこにも出ない（例：削減率 0.2123 が −0.1732 に変わる。RED-5）。登録されていない基準案の id は「基準案なし」と区別できない（RED-5）。1e-8 だけ違う基準案との差は桁落ちで相対 4.2e-5 ずれる（NUM-10）。
- **今の時点で言ってよいこと**：status は NO_BASELINE／NOT_COMPARABLE／COMPARED の 3 値。COMPARED のとき delta=P−B、saving=(B−P)/B（B>0 のときだけ）。
- **使ってはいけない記述**：
  - 「比較可能な場合だけ比べる」を、両方の合計が完全であることまで含めて読むこと（RED-5）
- **新研究での再利用**：候補（ルート B・C）
  - 使い道：2 つのシナリオの合計の差と比という形、および「基準案の計算は全体の再実行」という計算上の位置づけの確認に使う。
  - 条件・注意：形の記述は 43ba5d7 の版の定義文とコードの読み取り。新しい定式化を作る作業は含まない。基準案はシナリオの入力に入っておらず、プロセス内の登録表 synth.population.BASELINES から id で引く。依存の宣言は SUM-03 だけで、再実行は依存グラフに現れない（CK-R7-02）。
- **分類の根拠**：
  - 件数（units.json から python で集計）：1 単位＝SUM-08。台帳の structure_class：RATIO 1。段階：SUM 1。出所：既存 1・追加 0。統合モデル（models.json）：K5 1
  - 依存する変数：当該案と基準案の 2 つの合計、比較条件 5 つ。差は 1 次、削減率は比。分岐：3 つの status
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py):495-518；[`09_APPROX_STUDY/research_code/synth/population.py`](../../../09_APPROX_STUDY/research_code/synth/population.py):26-29（BASELINES、attach_baseline）
  - 第2回の再導出検査（[`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):145-148）での扱い：定義文から独立に書き直して値が一致 0 単位。間接的な確認だけ 1 単位（SUM-08）。
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):49-59（RED-5）；[`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):97-119（NUM-9・NUM-10）、134（CHECKS 6）
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））

<a id="ck-r7-14"></a>

## CK-R7-14　式の族 F11：条件分岐・述語（入力検査、整合の検査、係数の解決）

- **区分**：2　暫定・未検証成果
- **内容**：入力値の状態 SYS-01、単位と段階の整合 SYS-02、係数の使用許諾 SYS-03、面積の整合 SYS-04・QA-04、段階合計の突合と択一 QA-01、時間境界 QA-02、出典 QA-03、質量収支 C-05、係数の検索と優先順位 X-15 の 10 単位。出力は真偽・列挙値・違反箇所の一覧・件数で、連続量ではない。区分は R7 が台帳の structure_class と基準定義文・コードを読んで付けた整理用のもので、旧研究の成果物ではない（独立の検査なし）。
- **所在**：
  - [`09_APPROX_STUDY/01_LEDGER/units.json`](../../../09_APPROX_STUDY/01_LEDGER/units.json)
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py)
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py)
- **確かめ方**：C-05・QA-02・X-15 は第2回が定義文から書き直して一致（C-05 の n_mass_unchecked に 1 件の差：負の廃棄質量）。残り 7 単位は独立の書き直しがなく、コードを読んだうえでの狙い撃ちの入力による確認だけ。
- **確かめた者**：独立検査（第2回）で再現（3 単位）。残り 7 単位は作成者のみ
- **言える範囲**：架空データだけ。独立概念モデル（70 評価単位）の定義についての記述で、原版ブックの式との対応は未確認。
- **関係する第2回の指摘**：RED-4、RED-6、RED-10、RED-11、RED-12、NUM-2、NUM-8
- **第2回の指摘の影響**：SYS-01 が調べるのは数値入力の一部で、施設管理の比率、範囲比、建替周期、年次量、電力係数、経路の比率、質量比、要約数量などは対象外。NaN は MISSING にならない（RED-6）。C-05 は比率が None だと全体がエラー、NaN だと違反にも未配分にもならない（RED-10）。設備の廃棄係数が None でも SYS-03 は通るが、X-14 は行を除外し合計は不完全になる（RED-11）。QA-01 の (b)(c) は作り方から失敗し得ず、(a) は相対 1e-9 に絶対の下限 max(|値|,1) が付く（RED-12）。NaN の段階値に対する QA-01 の判定が基準計算と統合モデルで逆になる（NUM-2）。
- **今の時点で言ってよいこと**：係数の使用条件は 1 つの規則（レコードあり、使用許諾 PERMITTED_PUBLIC、対象段階がその段階だけ、単位が換算可能）で、X-15 は 製品固有値（EPD）→複合係数→汎用係数 の順に決める。EPD は行の申告（対象段階・単位・有効期限）がレコードと一致し、算定日に有効なときだけ使う。許容差：SYS-04 は |r|≦1e-9×面積、QA-04 は 1e-6×面積、C-05 は 1e-6、QA-01 は相対 1e-9。
- **使ってはいけない記述**：
  - 「SYS-01 は数値入力を 1 つずつ調べ、MISSING の場所を列挙する」（RED-6）
  - 「SYS-02 は活動量と係数が出会うすべての箇所を調べる」（EPD の係数は対象外。RED-11、一部確認）
  - 「検査に通れば合計は完全」「検査が通らなければ計算されない」のどちらも成り立たない（計算は検査の結果を読まない。CK-R7-02）
- **新研究での再利用**：候補（ルート B・C）
  - 使い道：連続な式の外側にある離散の分岐（使える係数の選択、択一、妥当性、許容差つきの判定）の一覧として使う。ルート A では K7（係数解決）と K6（許容差つきの残差判定）に対応する。
  - 条件・注意：形の記述は 43ba5d7 の版の定義文とコードの読み取り。新しい定式化を作る作業は含まない。検査の単位は計算を止めず、報告するだけである。計算の側は単位ごとに「除外して数える」を行い、その範囲は検査の範囲と一致しない。新しい定式化で分岐を扱うときは、検査ではなく各単位の関数の条件を見る必要がある。
- **分類の根拠**：
  - 件数（units.json から python で集計）：10 単位＝SYS-01、SYS-02、SYS-03、SYS-04、QA-01、QA-02、QA-03、QA-04、C-05、X-15。台帳の structure_class：PREDICATE_GATE 8、MASS_BALANCE_CONSTRAINT 1、LOOKUP_JOIN 1。段階：PRE 5、QA 4、C1-C4 1。出所：既存 9・追加 1。統合モデル（models.json）：統合なし 3、K7 4、K6 3
  - 依存する変数：行・項目・係数・段階・単位の組、許容差。出力は不連続（真偽・列挙・一覧）
  - [`09_APPROX_STUDY/research_code/refcalc/base.py`](../../../09_APPROX_STUDY/research_code/refcalc/base.py):133-143（lookup）
  - [`09_APPROX_STUDY/research_code/refcalc/units_pre_a.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_pre_a.py):29-206（SYS-01〜04、factor_uses）、283-328（EPD の条件、X-15）
  - [`09_APPROX_STUDY/research_code/refcalc/units_c_sum.py`](../../../09_APPROX_STUDY/research_code/refcalc/units_c_sum.py):135-160（C-05）、523-577（QA-01〜04）
  - 第2回の再導出検査（[`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):145-148）での扱い：定義文から独立に書き直して値が一致 3 単位（C-05、QA-02、X-15）。独立の書き直しなし 7 単位（QA-01、QA-03、QA-04、SYS-01、SYS-02、SYS-03、SYS-04）。
  - [`materials/round2_review/triage/rederive.md`](../materials/round2_review/triage/rederive.md):61-71（RED-6）、109-143（RED-10・RED-11・RED-12）；[`materials/round2_review/triage/numeric.md`](../materials/round2_review/triage/numeric.md):13-23（NUM-2）、85-95（NUM-8）
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））

<a id="ck-r7-31"></a>

## CK-R7-31　検討したが実装・検証していない式の案（06_OPEN_ISSUES の G-1〜G-7、B-8 の別の選択肢）

- **区分**：3　研究途中の数式・仮説
- **内容**：旧研究が検討だけして実装も測定もしなかった 7 件：累積の年次系列の閉形式（G-1）、建替なしを範囲比 0 で表す（G-2）、記述子で与えられる年次量の年次表を入力から外す（G-3）、出所レコードごとの入力状態の前計算（G-4）、木材の炭素貯蔵を導出係数として行テーブルに載せる（G-5）、更新時点の係数を使う場合の統合（G-6）、評価単位ごとの代理モデル（G-7）。
- **所在**：
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md)
  - [`09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md`](../../../09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md)
- **確かめ方**：実装も検証も無い（文書に「実装も検証もしていない」と明記）。G-1 は「年末ちょうどの事象の扱いが 1 点で違うことを確認した段階」とある。
- **確かめた者**：なし
- **言える範囲**：案の記述だけ。
- **関係する第2回の指摘**：なし
- **第2回の指摘の影響**：なし
- **今の時点で言ってよいこと**：これらは案であって成果ではない。G-6 について文書が述べているのは「更新時点の係数を使うと、更新の排出は『回数×1 回当たり』ではなく『事象の年ごとの係数の和』になる。回数の代わりに事象年の係数の和を乗数にすれば同じ枠組みに入ると見込まれるが、実装も検証もしていない」まで。
- **使ってはいけない記述**：
  - G-6 の「同じ枠組みに入ると見込まれる」を確認済みの性質として使うこと
  - G-2 の「式の上では同じ結果になる」を検証済みとして使うこと
- **新研究での再利用**：候補（ルート B・C）
  - 使い道：旧研究が式の形について気づいていて手を付けなかった点の一覧として参照する（特に、規約 B-8 を変えると F04 の「回数×1 回分」という形が崩れる、という記述）。
  - 条件・注意：いずれも未検証。G-3 は入力仕様の変更（冗長な入力を持つ目的との兼ね合い）、G-2 も入力仕様の変更になる、と文書にある。
- **分類の根拠**：
  - [`09_APPROX_STUDY/06_OPEN_ISSUES/README.md`](../../../09_APPROX_STUDY/06_OPEN_ISSUES/README.md):51（B-8 の別の選択肢について）、95-105（G-1〜G-7）
  - [`09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md`](../../../09_APPROX_STUDY/04_VERIFICATION/INDEPENDENT_REVIEW.md):62-64（第1回の指摘のうち対応していないもの）
- **分類した観点**：R7（新研究のための再利用の下調べ（構造の棚卸し））

