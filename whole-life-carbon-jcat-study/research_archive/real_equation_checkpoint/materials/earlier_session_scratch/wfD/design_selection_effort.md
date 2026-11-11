# 材料指定データ構造の設計案 ― 選択手数を最小にする観点から（独立提案）

> **状態**：`DESIGN_DRAFT`（次段階に向けた構造調査の草案。検証していない）
> **根拠**：`09_APPROX_STUDY/00_POLICY/DIRECTIVE.md` 第7章「次段階：材料データの分類」、第6章（資源配分10％）。同フォルダの `EVALUATION_PROTOCOL.md` の P0・P1・P9。
> **範囲**：データ構造と手順の設計案だけを扱う。画面・UI・アプリのコードは含まない。
> **例示**：本書の例示レコードはすべて架空（ID に `FICT` を含む）。係数・耐用年数・修繕率・構成比などの値は一切含まない。
> **独立性**：他の担当の提案（分類体系の案、名寄せの案）は読まずに書いた。統合時に項目名をそろえる必要がある（5.6）。

---

## 0. 位置づけと前提

### 0.1 本書の観点

指示書第7章は、材料を部位別のグループに分け、名称違い・類似材料・単位違い・重複を整理したうえで「将来的に少ない操作で材料を指定できるデータ構造」を設計することを次段階の課題としている。
本書はこのうち **「少ない操作で指定できる」** を出発点に置き、そこから逆算して必要な表と規則を決める。分類体系そのものや名寄せの方法は主題にしない。

### 0.2 分かっていること・分かっていないこと

| 事項 | 現在の状態 | 本書での扱い |
|---|---|---|
| 実在の材料データセット | **未入手** | 件数、部位別の偏り、名称の揺れ方、単位の種類について何も主張しない |
| 分類表ブック（13シート）・集計表ブック（11シート） | シート**名**だけが `02_SOURCES/ALL_198_SHEETS.json` にある。内容は利用できない | シート名からは、建築・電気・空調・衛生・昇降の区分ごとの表、コード表、複合的な原単位の表、電気の主要機器の表、配管・ケーブルの表があると読めるだけで、粒度・件数・項目は不明。本設計はそれらを写していない |
| `03_INPUTS/inputs.json` | MATERIAL 20、EQUIPMENT 9、FACTOR 11、TRANSPORT 5、END_OF_LIFE 9、PROVENANCE 8 項目の草案がある | 本設計の接続先として使う（付録A） |
| 統一計算行 | 計算研究の側で検討中 | 「活動量・単位・係数参照・耐用年数・修繕率・廃棄経路」を持つ1行と仮定する。項目名は仮で、確定後に合わせる |
| 係数・耐用年数・修繕率・構成比などの値 | J-CAT の値は流用禁止。独立して使える値は未入手 | 表には**参照だけ**を置き、値は置かない |

### 0.3 用語

| 用語 | 本書での意味 |
|---|---|
| 部位グループ | 基礎、躯体、屋根・外壁、開口部、内装、電気設備、空調設備、給排水設備、搬送設備などの大区分 |
| 材料族 | 同じ数量単位で数えられ、同じ絞り込み軸を持つ材料レコードのまとまり（部位に依存しない） |
| 材料レコード | 計算行の元になる最小単位の正規レコード |
| 代表レコード | 材料族を細かく指定しなかったときに使う材料レコード |
| 選択ノード | 部位グループから材料族・束へ辿る経路上の1点 |
| 絞り込み軸 | 材料族の中で材料レコードを区別する属性（例：強度区分）。計算行のどれかの項目を変えるものに限る |
| 文脈 | 案件ごとに一度決まる条件（主要構造、主用途など） |
| 文脈既定 | 文脈に応じて候補の先頭に置く・あらかじめ選んでおく・候補から外す、という規則 |
| 束 | 1回の選択で複数の材料レコードをまとめて指定する定義 |
| 検索キー | 名称の揺れ・略称・読み・現場用語を、選択対象に結び付ける語 |
| 単位プロファイル | 数量を入れる単位と、係数の分母単位への換算方法の定義 |
| 計算行 | 計算研究に渡す1行 |
| 操作 | 1.2 で定義する、画面に依存しない数え方の単位 |

---

## 1. 設計目標と、解決する課題

### 1.1 目標

| ID | 目標 | 内容 |
|---|---|---|
| G1 | 粗い選択で計算行が成立する | 材料族を選んで数量を入れるだけで、代表レコードによる計算行ができる |
| G2 | 細かい指定は任意で、後からできる | 絞り込むと同じ行の材料レコードが置き換わる。行は増えない |
| G3 | 文脈で候補を減らす | 部位グループと主要構造などから、候補の順序・既定・除外を決める |
| G4 | 単位は選択で決まる | 材料族を選んだ時点で数量の単位が一意に決まり、単位を選ぶ操作をなくす |
| G5 | 複数の材料を一度に指定できる | 束を1回選び、基準数量を1つ入れると複数の計算行ができる |
| G6 | 名称の揺れを吸収する | 検索キーで、略称・読み・現場用語から同じ選択対象に到達する |
| G7 | 選択から計算行までが決定的で追跡できる | 同じ選択記録と同じカタログ版から、必ず同じ計算行が得られる |
| G8 | 既定・代表の使用が結果に残る | どの行が代表レコードか、どの値が既定かを計算行に記録する。黙って補わない |
| G9 | 値を持たない | 係数などの値は外部のパラメータ台帳に置き、本構造は参照と権限状態だけを持つ |

### 1.2 「操作」の数え方（画面に依存しない定義）

手数を減らす設計を比べるには、数え方が必要になる。画面の作りに左右されないよう、次の5種類を数える。

| 操作 | 定義 | 数え方 |
|---|---|---|
| `PICK` | 有限の候補から1つ選ぶ | 1回。あわせて候補数 n を記録する |
| `ENTER` | 数値を1つ入れる（数量、厚さなど） | 1回 |
| `SEARCH` | 検索語を1回与える | 1回。結果が1件に定まらなければ続けて `PICK` が要る |
| `ACCEPT` | あらかじめ選ばれた既定を承認する | 1回。自動適用（`auto_apply = true`）の既定は0回だが、記録は残す |
| `OVERRIDE` | 既定や代表から得た値を別の値に置き換える | 1回。理由を記録する |

- 1つの選択の手数 = `PICK + ENTER + SEARCH + ACCEPT + OVERRIDE` の回数の合計。
- 補助指標として **選択情報量** = Σ log2(候補数) を使う。9個から1つ選ぶのと、数百個から1つ選ぶのとでは負担が違うため。
- 案件ごとに一度だけ決める文脈（主要構造など）は、材料1件あたりの手数には数えない。

設計上の目標値（**仮説であり、実データでは確かめていない**）：

| ID | 仮の目標 |
|---|---|
| T1 | 部位グループが決まっている状態で、材料1行の粗い指定は `PICK` 2回以内 + `ENTER` 1回 |
| T2 | 束は `PICK`（または `ACCEPT`）1回 + `ENTER` 1回（換算に寸法が要る場合はその分を加える）で複数行 |
| T3 | 1回の `PICK` の候補数は上限 `max_fanout` 以下。値は仮に 12 と置く（根拠なし。実データで決める） |
| T4 | 検索は `SEARCH` 1回 + `PICK` 1回以内で選択対象に届く。届く割合の目標は名称データがないため未設定 |

注意：手数の大半は数量の拾い出しであり、選択の手数を減らしても数量を調べる手間は減らない。束の構成比で数量を導けば `ENTER` は減るが、推定誤差が入る（6章）。

### 1.3 課題と対応

| 課題 | 何が起きるか | 本設計での対応 | 該当する表 |
|---|---|---|---|
| 行ごとに部位・分類・仕様・単位を個別に指定する | 行数に比例して手数が増える | 材料族の選択で単位・計算行の雛形・既定パラメータの参照が決まる | `material_family`、`calc_row_template`、`param_binding` |
| 仕様が分からない段階では選べない | 基本計画段階で計算できない | 代表レコードを必ず定義し、粗い選択で成立させる | `material_family.representative_item_id` |
| 候補が多すぎる | 1回の選択が重い | 部位ごとの選択木、候補数の上限、文脈による順序付けと除外 | `selection_node`、`context_default` |
| 同じ材料が複数の部位で使われる | 部位ごとに重複レコードを作ってしまう | 部位を材料の属性にせず、選択の属性にする | `selection_record.part_id` |
| 名称の揺れ | 探しても見つからず、類似レコードを誤って選ぶ | 検索キーと正規化手順。曖昧な語は粗い側へ落とす | `search_key` |
| 単位の不一致 | 計算停止、または誤った換算 | 単位は材料族で固定。許した入力単位と換算方法だけを使う | `unit_profile`、`unit_conversion` |
| 関連する材料の指定漏れ | 過小評価 | 束と、部位ごとの出発点セット | `bundle`、`context_default` |
| 既定・代表の多用で結果の質が見えなくなる | 粗い結果を精密な結果と誤認する | 行ごとに代表性と値の状態を記録し、集計できるようにする | `calc_row.representativeness` ほか |
| 束と個別指定の重複 | 二重計上 | 範囲キーによる検査 | `scope_key` |

### 1.4 設計の骨子（6つの決定）

1. **三層に分ける。** (a) 正規カタログ層＝「何であるか」（材料族、材料レコード、絞り込み軸、単位）。(b) 選択層＝「どう辿り着くか」（選択ノード、文脈既定、束、検索キー）。(c) 記録・接続層＝「何を選び、どの計算行になったか」（選択記録、計算行、パラメータ束縛）。選択層は何度作り直しても、正規カタログ層と過去の選択記録を壊さない。
2. **部位は選択の属性にする。** 材料レコードは部位を持たない。同じ材料族を複数の部位の選択ノードから指す。
3. **代表レコード＝すべての絞り込み軸が既定値の材料レコード。** 粗い選択と細かい選択を同じ仕組みで扱い、絞り込みは「既定値を1つずつ置き換えること」として表す。
4. **単位は材料族で固定する。** 材料族の中の材料レコードは同じ正規単位を持つ。単位が違うものは別の材料族にする。
5. **束は構成行へ展開する。** 束を1つの合成係数にまとめず、構成要素ごとの計算行にする。耐用年数や廃棄経路が構成要素ごとに違い得るため。
6. **値は継承で決め、参照だけを持つ。** 係数・耐用年数・修繕率・廃棄経路は「製品 → 材料レコード → 材料族 → 部位グループ」の順に最も具体的な束縛を使う。利用者が指定する必要があるのは置き換えたいときだけ。

### 1.5 検討して採らなかった構成

| 構成 | 採らなかった理由 |
|---|---|
| 一覧＋検索だけ（木を持たない） | 名称を知らないと選べない。粗い選択（代表レコード）の置き場がない |
| 深い木だけ（仕様の末端まで木で辿る） | 仕様の軸が複数あると組合せで枝が増え、`PICK` の回数も候補数も増える |
| 属性の絞り込みだけ（木を持たない） | 最初の候補が全件になり、部位と構造による既定を置きにくい |
| 束を合成係数1つで持つ | 構成要素ごとの耐用年数・修繕率・廃棄経路を失う。算定境界の混在を検査できない |

採用したのは「浅い木（部位グループ → 材料族）＋ 任意の軸 ＋ 検索キー ＋ 束」の組合せである。これが実データに合うかどうかは確かめていない（5章）。

---

## 2. データ構造（項目表）

### 2.0 全体像

```
[正規カタログ層]
  material_family ─< material_item
        │  └─ axis_ids ──> refinement_axis ─< refinement_option
        ├──> unit_profile ─< unit_conversion
        └──> calc_row_template

[選択層]
  building_part ─< selection_node ──> material_family / material_item / bundle
  context_default ──> selection_node / bundle / refinement_option
  bundle ─< bundle_component ──> material_family / material_item
  search_key ──> material_family / material_item / bundle / selection_node / refinement_option

[記録・接続層]
  project_context ─< selection_record ─< calc_row ──> 計算研究の統一計算行
  param_binding（部位グループ／材料族／材料レコード／製品 × パラメータ種別）──> 外部のパラメータ台帳（値は別管理）
```

型の表記：`string`、`integer`、`number`、`boolean`、`enum`、`ref`（他の表のID）、`array<…>`、`object`。
必須欄：`必須`／`任意`／`条件付き`（条件を意味欄に書く）。
すべての表は `status`（`DRAFT`／`ACTIVE`／`DEPRECATED`／`MERGED`）と `introduced_in_version`・`deprecated_in_version` を持つ（各表では省略）。

### 2.1 `building_part`（部位グループ）

| 項目 | 型 | 必須 | 意味 |
|---|---|---|---|
| `part_id` | enum | 必須 | `FOUNDATION`、`STRUCTURE`、`ROOF_EXTERIOR_WALL`、`OPENING`、`INTERIOR`、`ELECTRICAL`、`HVAC`、`PLUMBING`、`CONVEYANCE`。追加候補として `EXTERIOR_WORKS`、`TEMPORARY_WORKS`、`OTHER_UNCLASSIFIED`（要否は未決） |
| `label_ja` | string | 必須 | 表示名（基礎、躯体 など） |
| `domain` | enum | 必須 | `ARCHITECTURE`／`EQUIPMENT` |
| `input_group` | enum | 必須 | 生成する計算行が対応する inputs.json の群。`MATERIAL`／`EQUIPMENT` |
| `sort_order` | integer | 必須 | 既定の並び順 |
| `root_node_id` | ref | 必須 | この部位の選択木の根（`selection_node`） |

### 2.2 `material_family`（材料族）

| 項目 | 型 | 必須 | 意味 |
|---|---|---|---|
| `family_id` | string | 必須 | 意味を持たない安定ID。階層や名称をIDに埋め込まない |
| `label_ja` | string | 必須 | 正規名称 |
| `item_kind` | enum | 必須 | `MATERIAL`／`PRODUCT`／`EQUIPMENT_UNIT`／`PROCESS` |
| `canonical_unit` | enum | 必須 | 正規単位（係数の分母単位）。族内の全材料レコードで共通 |
| `unit_profile_id` | ref | 必須 | 入力単位と換算の定義 |
| `axis_ids` | array<ref> | 必須（空可） | 絞り込み軸。並び順は問う順序（結果への影響が大きい順。実データがないため順序の根拠は未定） |
| `calc_row_template_id` | ref | 必須 | 計算行の雛形 |
| `representative_item_id` | ref | 必須 | 代表レコード。全軸が既定値の材料レコードと一致しなければならない（3.8 の I-03） |
| `representative_rule` | enum | 必須 | 代表の決め方。`MOST_COMMON`／`MEDIAN_OF_MEMBERS`／`CONSERVATIVE_UPPER`／`EXPERT_PICK`／`NOT_DECIDED` |
| `representative_basis_note` | string | 任意 | 決め方の根拠（資料名、判断者、日付） |
| `spread_class` | enum | 必須 | 族内の係数のばらつきの区分。`UNKNOWN`／`NARROW`／`MODERATE`／`WIDE`。使える係数データが得られるまで `UNKNOWN`。区分の閾値は未定 |
| `refinement_recommended` | boolean | 必須 | ばらつきが大きく、粗い選択のままにすべきでない族に `true`。`spread_class` から導く |
| `scope_key` | string | 必須 | 二重計上の検査に使う範囲キー（例：`CONCRETE_STRUCTURAL`） |

### 2.3 `material_item`（材料レコード）

| 項目 | 型 | 必須 | 意味 |
|---|---|---|---|
| `item_id` | string | 必須 | 意味を持たない安定ID |
| `family_id` | ref | 必須 | 属する材料族（1つだけ） |
| `canonical_name_ja` | string | 必須 | 正規名称 |
| `record_kind` | enum | 必須 | `SPECIFIC`（個別仕様）／`GENERIC_REPRESENTATIVE`（族を代表する一般レコード。係数は族内の値から規則で導く）／`PRODUCT_SPECIFIC`（製品固有。EPD 等） |
| `axis_values` | array<object> | 必須（空可） | この材料レコードの各軸上の位置。要素は `{axis_id, option_id}` |
| `derivation_rule` | string | 条件付き | `GENERIC_REPRESENTATIVE` のとき必須。係数の導き方（例：構成比による加重。重みは実データが必要） |
| `license_status` | enum | 必須 | `PERMITTED_PUBLIC`／`PERMISSION_REQUIRED`／`RESTRICTED`／`UNKNOWN`（第1章 1-E の語彙） |
| `source_record_refs` | array<string> | 任意 | 名寄せ前の原レコードへの参照（名寄せの台帳側のID） |
| `merged_into_item_id` | ref | 条件付き | `status = MERGED` のとき必須。統合先 |

材料レコードは**係数の値も、耐用年数の値も持たない**。それらは `param_binding` を通じて参照する。

### 2.4 `refinement_axis` と `refinement_option`（絞り込み軸）

`refinement_axis`

| 項目 | 型 | 必須 | 意味 |
|---|---|---|---|
| `axis_id` | string | 必須 | 安定ID |
| `label_ja` | string | 必須 | 軸の名称（例：強度区分） |
| `value_type` | enum | 必須 | `ENUM`／`NUMERIC_BAND`（数値の区間）／`PRODUCT_REF`（製品固有レコードの指定） |
| `unit` | enum | 条件付き | `NUMERIC_BAND` のとき必須 |
| `affects` | array<enum> | 必須（1つ以上） | この軸で変わる計算行の項目。`FACTOR`／`MASS_PER_UNIT`／`SERVICE_LIFE`／`REPAIR_RATE`／`EOL_ROUTE`。**何も変えない属性（色など）は軸にしない**（検索キーで吸収する） |
| `default_option_id` | ref | 必須 | 既定値。代表レコードはこの既定値に対応する |
| `default_rule` | enum | 必須 | 既定値の決め方。`representative_rule` と同じ語彙 |

`refinement_option`

| 項目 | 型 | 必須 | 意味 |
|---|---|---|---|
| `option_id` | string | 必須 | 安定ID |
| `axis_id` | ref | 必須 | 属する軸 |
| `label_ja` | string | 必須 | 選択肢の名称 |
| `band_min`／`band_max` | number | 条件付き | `NUMERIC_BAND` のとき必須。下限を含み上限を含まない |
| `sort_order` | integer | 必須 | 並び順 |

寸法（厚さなど）のうち、材料レコードを変えずに数量だけを変えるものは軸ではなく**換算パラメータ**として扱う（2.9）。

### 2.5 `selection_node`（選択ノード）

| 項目 | 型 | 必須 | 意味 |
|---|---|---|---|
| `node_id` | string | 必須 | 意味を持たない安定ID |
| `parent_node_id` | ref | 条件付き | 根以外は必須 |
| `part_id` | ref | 必須 | 属する部位グループ（検索と検査のために冗長に持つ） |
| `level` | enum | 必須 | `PART`／`GROUP`／`FAMILY`／`VARIANT` |
| `node_kind` | enum | 必須 | `NAVIGATION_ONLY`（辿るだけ）／`SELECTABLE`（ここで止めて計算行にできる） |
| `target_kind` | enum | 必須 | `NONE`／`FAMILY`／`ITEM`／`BUNDLE` |
| `target_id` | ref | 条件付き | `target_kind ≠ NONE` のとき必須 |
| `label_ja` | string | 必須 | この部位の中での呼び名（材料族の正規名称と違ってよい） |
| `axis_default_overrides` | array<object> | 任意 | この部位で使うときの軸の既定値の差し替え。要素は `{axis_id, option_id}`。部位によって代表レコードを変えたいときに使う |
| `entry_unit_override` | enum | 任意 | この部位で数量を入れる単位。単位プロファイルが許す単位に限る |
| `sort_key` | integer | 必須 | 既定の並び順（使用頻度の順位を想定。実データがないため根拠は未定） |

制約：
- 部位の根から最初の `SELECTABLE` ノードまでの深さは2以内（T1 に対応）。
- `GROUP` は候補数が `max_fanout` を超えるときだけ挟む。
- `VARIANT` で `target_kind = ITEM` のノードは、よく使う個別仕様への近道として置く（軸を辿らずに1回の `PICK` で届く）。

### 2.6 `context_default`（文脈既定）

`project_context`（案件ごとに1件。値は inputs.json の PROJECT 群から取る）

| 項目 | 型 | 必須 | 意味 |
|---|---|---|---|
| `project_id` | string | 必須 | 案件ID |
| `structure_type` | enum | 必須 | `RC`／`S`／`SRC`／`W`／`MIXED`／`UNKNOWN`（`PROJECT.structure_type`） |
| `building_use` | enum | 必須 | 主用途（`PROJECT.building_use`）。語彙は未定 |
| `design_stage` | enum | 任意 | 設計段階（`PROJECT.design_stage`） |
| `default_quantity_basis` | enum | 必須 | 数量の根拠の案件既定。`DESIGN`／`ORDERED`／`AS_BUILT`（`MATERIAL.quantity_basis`） |
| `catalog_version` | string | 必須 | 使用するカタログ版 |

`context_default`

| 項目 | 型 | 必須 | 意味 |
|---|---|---|---|
| `default_id` | string | 必須 | 安定ID |
| `part_id` | ref | 必須 | 対象の部位グループ |
| `scope_node_id` | ref | 任意 | この規則が効く選択ノード。省略時は部位の根 |
| `structure_type` | enum | 必須 | 条件。`ANY` を許す |
| `building_use` | enum | 必須 | 条件。`ANY` を許す |
| `other_conditions` | object | 任意 | 追加条件（規模区分など）。使う場合は語彙を別に定義する |
| `default_kind` | enum | 必須 | `PRESELECT_NODE`（子ノードを1つ選んでおく）／`PRESELECT_BUNDLE`／`PRESELECT_AXIS_OPTION`／`ORDER_BOOST`（候補の先頭へ）／`EXCLUDE`（既定の候補から外す。検索では到達できる）／`STARTER_SET`（部位の出発点として提示する束・ノードの一覧） |
| `target_kind`／`target_id` | enum／ref | 必須 | 対象（ノード、束、軸の選択肢） |
| `specificity` | integer | 必須（導出） | `ANY` でない条件の数 |
| `priority` | integer | 必須 | 同じ `specificity` のときの優先（小さいほど先） |
| `auto_apply` | boolean | 必須 | `true` は承認なしで適用。計算結果を変える既定は原則 `false` |
| `basis` | enum | 必須 | `EXPERT_JUDGEMENT`／`FREQUENCY_FROM_DATA`／`REGULATORY`／`PLACEHOLDER` |
| `evidence_ref` | string | 条件付き | `basis ≠ PLACEHOLDER` のとき必須。根拠資料 |

### 2.7 `bundle` と `bundle_component`（束）

`bundle`

| 項目 | 型 | 必須 | 意味 |
|---|---|---|---|
| `bundle_id` | string | 必須 | 安定ID |
| `label_ja` | string | 必須 | 名称 |
| `part_id` | ref | 必須 | 使う部位グループ |
| `bundle_kind` | enum | 必須 | `ASSEMBLY`（層構成・納まりの一式）／`SYSTEM_KIT`（機器と付属の配管・配線などの一式）／`STARTER_SET`（部位と構造から決まる出発点の一式） |
| `driver_quantity_kind` | enum | 必須 | 基準数量の種類。`AREA`／`VOLUME`／`LENGTH`／`MASS`／`COUNT`／`CAPACITY`／`GROSS_FLOOR_AREA` |
| `driver_unit` | enum | 必須 | 基準数量の単位。束を選ぶとこの単位に決まる |
| `expansion_mode` | enum | 必須 | `EXPAND_TO_ROWS`（構成要素ごとに計算行。既定）／`PRECOMPOSED`（合成済み。構成行へ展開できる定義が別にある場合の計算上の短絡に限る） |
| `covers_scope_keys` | array<string> | 必須 | この束が覆う範囲キー（構成要素の `scope_key` の和集合） |
| `factor_stage_note` | string | 任意 | 構成要素の係数が含む段階についての注意（段階の混在を避けるため） |

`bundle_component`

| 項目 | 型 | 必須 | 意味 |
|---|---|---|---|
| `bundle_id`／`line_no` | ref／integer | 必須 | 束と行番号 |
| `target_kind`／`target_id` | enum／ref | 必須 | `FAMILY`（代表レコードで展開し、後から絞り込める）／`ITEM` |
| `ratio_per_driver` | number | 任意 | 基準数量1単位あたりの構成要素の数量。**値は権利の確認できたデータからのみ入れる。未入手なら null** |
| `ratio_unit` | string | 必須 | 「構成要素の正規単位／基準数量の単位」（例：`kg/m3`） |
| `ratio_basis` | enum | 必須 | `DRIVER_IDENTITY`（基準数量そのもの。比は定義上 1）／`GEOMETRIC_DEFINITION`（寸法から定義で決まる）／`USER_PARAMETER`（利用者が与える）／`STATISTICAL`（統計値。出典と権利の確認が必要）／`PLACEHOLDER` |
| `ratio_value_state` | enum | 必須 | `MISSING`／`OBSERVED`／`USER_ESTIMATE`／`LICENSED_DEFAULT`／`DERIVED` |
| `ratio_param_name` | string | 条件付き | `USER_PARAMETER`・`GEOMETRIC_DEFINITION` のとき必須（例：`thickness_m`） |
| `default_included` | boolean | 必須 | 既定で含めるか |
| `optional` | boolean | 必須 | 利用者が外してよいか |
| `substitutable` | boolean | 必須 | 同じ材料族の別レコードへ差し替えてよいか |
| `scope_key` | string | 必須 | 構成要素の範囲キー（材料族の `scope_key` と同じ値） |

### 2.8 `search_key`（検索キー）

| 項目 | 型 | 必須 | 意味 |
|---|---|---|---|
| `key_id` | string | 必須 | 安定ID |
| `display_form` | string | 必須 | 元の表記 |
| `normalized_key` | string | 必須 | 3.4 の手順で正規化した文字列 |
| `key_type` | enum | 必須 | `CANONICAL_NAME`／`SYNONYM`／`ABBREVIATION`／`READING_KANA`／`ROMAJI`／`TRADE_TERM`（現場用語）／`FOREIGN`／`MISSPELLING`／`OWN_LEGACY_ID`（自前の旧ID） |
| `target_kind`／`target_id` | enum／ref | 必須 | `FAMILY`／`ITEM`／`BUNDLE`／`NODE`／`AXIS_OPTION` |
| `ambiguity` | enum | 必須 | `UNIQUE`／`AMBIGUOUS`（同じ `normalized_key` が複数の対象を指す） |
| `context_part_id` | ref | 任意 | この部位の中でだけ有効な語の場合に指定 |
| `weight` | integer | 必須 | 同順位の並びを決める重み |
| `source` | enum | 必須 | `CURATED`／`FROM_INPUT_LOG`／`FROM_RAW_DATA` |
| `rights_note` | string | 条件付き | 第三者のコード・商標・製品名に由来する語の場合は必須。権利未確認の語は登録しない |

検索語に含まれる寸法・等級の表記（例：厚さを表す `t50`）は名称としては照合せず、**仕様トークン**として切り出して軸の選択肢または換算パラメータに変える。これにより、検索1回で絞り込みまで済むことがある。切り出しの型は別表 `spec_token_pattern`（`pattern_id`、`pattern`、`maps_to_kind`（`AXIS_OPTION`／`CONVERSION_PARAM`）、`maps_to_name`、`unit`）で管理する。

### 2.9 `unit_profile` と `unit_conversion`（単位）

`unit_profile`

| 項目 | 型 | 必須 | 意味 |
|---|---|---|---|
| `unit_profile_id` | string | 必須 | 安定ID |
| `canonical_unit` | enum | 必須 | 正規単位。`kg`／`t`／`m`／`m2`／`m3`／`unit`／`set`／`kW`／`L` など |
| `default_entry_unit` | enum | 必須 | 数量を入れる既定の単位 |
| `allowed_entries` | array<object> | 必須（1件以上） | 許す入力単位と換算。要素は `{entry_unit, conversion_id}` |

`unit_conversion`

| 項目 | 型 | 必須 | 意味 |
|---|---|---|---|
| `conversion_id` | string | 必須 | 安定ID |
| `from_unit`／`to_unit` | enum | 必須 | 入力単位／正規単位 |
| `conversion_kind` | enum | 必須 | `IDENTITY`／`SI_DEFINITION`（1 t = 1000 kg などの定義）／`GEOMETRIC`（寸法を掛ける）／`DENSITY`（密度が要る）／`PIECE_MASS`（1個・1本あたりの量が要る）／`CAPACITY`（定格能力が要る） |
| `required_params` | array<string> | 必須（空可） | 必要なパラメータ名（例：`thickness_m`） |
| `param_source_order` | array<enum> | 必須（空可） | パラメータの取得元の優先順。`SPEC_TOKEN`／`AXIS_OPTION`／`ITEM_ATTRIBUTE`／`USER_INPUT`／`LICENSED_REQUIRED` |
| `formula_note` | string | 必須 | 換算の式（例：`q_canonical = q_entry × thickness_m`） |
| `exactness` | enum | 必須 | `EXACT_DEFINITION`／`PARAMETER_DEPENDENT` |

### 2.10 `calc_row_template` と `param_binding`（計算行への接続）

`calc_row_template`

| 項目 | 型 | 必須 | 意味 |
|---|---|---|---|
| `template_id` | string | 必須 | 安定ID |
| `activity_kind` | enum | 必須 | `MATERIAL_QUANTITY`／`EQUIPMENT_COUNT`／`EQUIPMENT_CAPACITY`／`PROCESS_ACTIVITY` |
| `required_param_kinds` | array<enum> | 必須 | 計算に欠かせないパラメータ種別（最低限 `FACTOR`） |
| `optional_param_kinds` | array<enum> | 必須（空可） | 段階によって使うパラメータ種別 |
| `dependent_requirements` | array<enum> | 必須（空可） | この行に伴って別の入力が必要になる事項（例：`REFRIGERANT_CHARGE`）。**値は自動で補わず、未入力の要求として残す** |

`param_binding`（値ではなく参照を持つ）

| 項目 | 型 | 必須 | 意味 |
|---|---|---|---|
| `binding_id` | string | 必須 | 安定ID |
| `scope_kind` | enum | 必須 | `PART`／`FAMILY`／`ITEM`／`PRODUCT` |
| `scope_id` | ref | 必須 | 対象のID |
| `param_kind` | enum | 必須 | `FACTOR`／`MASS_PER_UNIT`／`SERVICE_LIFE`／`REPAIR_RATE`／`EOL_ROUTE`／`WASTE_RATE`／`TRANSPORT_PROFILE` |
| `param_ref` | string | 任意 | 外部のパラメータ台帳のID（`FACTOR.factor_id` など）。未束縛なら null |
| `context_condition` | object | 任意 | この束縛が効く文脈（例：主用途）。省略時は常に有効 |
| `value_state` | enum | 必須 | `MISSING`／`LICENSED_DEFAULT`／`USER_ESTIMATE`／`OBSERVED`／`DERIVED` |
| `license_status` | enum | 必須 | 第1章 1-E の語彙 |

束縛の解決順（具体的なものが優先）：利用者の置き換え → `PRODUCT` → `ITEM` → `FAMILY` → `PART`。どこにも束縛がなければ `MISSING` のままにし、既定値を作り出さない。

### 2.11 `selection_record`（選択記録）

| 項目 | 型 | 必須 | 意味 |
|---|---|---|---|
| `selection_id` | string | 必須 | 安定ID |
| `project_id`／`catalog_version` | ref／string | 必須 | 案件と、解決に使ったカタログ版 |
| `part_id` | ref | 必須 | 使用箇所の部位グループ |
| `zone_id` | string | 任意 | 同じ材料を棟・階などで分けて持つときの区分 |
| `chosen_target_kind`／`chosen_target_id` | enum／ref | 必須 | 選んだ対象（`FAMILY`／`ITEM`／`BUNDLE`） |
| `via_node_id` | ref | 任意 | 辿った選択ノード（検索で直接届いた場合は null） |
| `search_key_id` | ref | 任意 | 使った検索キー |
| `resolution_mode` | enum | 必須 | `REPRESENTATIVE`／`REFINED`／`EXACT_ITEM`／`PRODUCT_SPECIFIC`／`BUNDLE_EXPANDED` |
| `axis_choices` | array<object> | 必須（空可） | 要素は `{axis_id, option_id, state}`。`state` は `USER_CHOSEN`／`DEFAULTED`／`FROM_SPEC_TOKEN` |
| `component_refinements` | array<object> | 必須（空可） | 束の構成要素ごとの指定。要素は `{line_no, axis_choices, included, direct_quantity}` |
| `entry_quantity`／`entry_unit` | number／enum | 条件付き | 数量と入力単位。未入力のときは null とし `quantity_state = MISSING` |
| `quantity_state` | enum | 必須 | `MISSING`／`EXPLICIT_ZERO`／`OBSERVED`／`USER_ESTIMATE`／`LICENSED_DEFAULT`／`DERIVED`（第3章の語彙） |
| `quantity_basis` | enum | 必須 | `DESIGN`／`ORDERED`／`AS_BUILT`。省略時は案件既定を写して記録 |
| `conversion_id`／`conversion_params` | ref／object | 必須 | 使った換算と、そのパラメータの値・取得元 |
| `defaults_applied` | array<ref> | 必須（空可） | 適用した `context_default` のID |
| `overrides` | array<object> | 必須（空可） | 要素は `{param_kind, new_param_ref, reason}`（`PROVENANCE.user_override_reason` に対応） |
| `operation_count` | object | 必須 | `{pick, enter, search, accept, override}` の回数 |
| `candidate_counts` | array<integer> | 必須（空可） | 各 `PICK` の候補数（選択情報量の計算用） |
| `resolved_row_ids` | array<ref> | 必須 | 生成した計算行 |

### 2.12 `calc_row`（計算行。計算研究の統一計算行への受け渡し）

| 項目 | 型 | 必須 | 意味 | 統一計算行での役割（仮） |
|---|---|---|---|---|
| `row_id` | string | 必須 | 安定ID。絞り込みで材料レコードが替わっても変えない | 行の識別 |
| `selection_id` | ref | 必須 | 元の選択記録 | 追跡 |
| `bundle_id`／`bundle_line_no` | ref／integer | 任意 | 束から展開した行の場合 | 追跡 |
| `part_id` | ref | 必須 | 部位グループ | 部位別集計の鍵 |
| `item_id` | ref | 必須 | 解決した材料レコード | 材料別集計の鍵 |
| `activity` | number | 条件付き | 正規単位での活動量。欠けるときは null | 活動量 |
| `activity_unit` | enum | 必須 | 材料族の正規単位 | 単位 |
| `activity_state` | enum | 必須 | 活動量の状態（`quantity_state` と同じ語彙。束の比から導いたものは `DERIVED`） | 入力状態 |
| `factor_ref` | string | 任意 | 係数の参照。未束縛は null | 係数参照 |
| `mass_per_unit_ref` | string | 任意 | 質量換算の参照（輸送・廃棄の質量基準に必要） | 輸送・廃棄の活動量の導出 |
| `service_life_ref` | string | 任意 | 耐用年数の参照 | 耐用年数 |
| `repair_rate_ref` | string | 任意 | 修繕率の参照 | 修繕率 |
| `eol_route_ref` | string | 任意 | 廃棄経路（経路と配分）の参照 | 廃棄経路 |
| `waste_rate_ref` | string | 任意 | 施工端材率の参照 | 発注量と設置量の換算 |
| `param_states` | object | 必須 | 各参照の `value_state` と `license_status` と束縛元（`PRODUCT`／`ITEM`／`FAMILY`／`PART`／`USER`） | 権限の検査、出典の表示 |
| `representativeness` | enum | 必須 | `EXACT`／`REFINED`／`REPRESENTATIVE`／`REPRESENTATIVE_WIDE`（代表で、族のばらつきが `WIDE` または `UNKNOWN`） | 結果の質の集計 |
| `scope_key` | string | 必須 | 範囲キー | 二重計上の検査 |
| `computable` | boolean | 必須 | 必要な参照と活動量がそろい、権限が許すか | 計算の可否 |
| `blocking_reasons` | array<enum> | 必須（空可） | `FACTOR_MISSING`／`LICENSE_NOT_PERMITTED`／`QUANTITY_MISSING`／`UNIT_CONVERSION_PARAM_MISSING`／`BUNDLE_RATIO_MISSING`／`UNIT_MISMATCH` | 停止理由 |
| `dependent_requirements` | array<object> | 必須（空可） | 要素は `{kind, state}`。未入力の付随要求 | 入力漏れの検出 |

概念式との対応（04_FORMULAS の式ID）：

| 計算行の項目 | 使う式（独立概念モデル） |
|---|---|
| `activity` × `factor_ref` | A13-01（数量×係数）、製品固有の参照に替えると A13-03 |
| 束の展開 | A13-02 に相当する構成の考え方を、合成係数ではなく行の展開として表す |
| `waste_rate_ref` | A13-05 |
| `activity` × `mass_per_unit_ref` | A4-01、C2-01 の質量 |
| `repair_rate_ref` | B3-01、B3-02 |
| `service_life_ref` | B4-01、B4-02、B4-03 |
| `eol_route_ref` | C3-01、C4-01、C-05（質量収支） |
| `activity_unit` と係数の分母単位の一致 | SYS-02 |
| `param_states` の権限 | SYS-03、QA-03 |

### 2.13 主キーと一意制約

| 表 | 主キー | 一意制約・外部参照 |
|---|---|---|
| `building_part` | `part_id` | `root_node_id` → `selection_node` |
| `material_family` | `family_id` | `representative_item_id` → 同じ族の `material_item` |
| `material_item` | `item_id` | （`family_id`、`axis_values` の組合せ）が一意 |
| `refinement_axis`／`refinement_option` | `axis_id`／`option_id` | `default_option_id` → 同じ軸の選択肢 |
| `selection_node` | `node_id` | （`parent_node_id`、`label_ja`）が一意。`target_id` → `target_kind` が示す表 |
| `context_default` | `default_id` | （`part_id`、`scope_node_id`、条件、`default_kind`、`priority`）が一意 |
| `bundle`／`bundle_component` | `bundle_id`／（`bundle_id`、`line_no`） | 束の中で `scope_key` が一意 |
| `search_key` | `key_id` | （`normalized_key`、`target_kind`、`target_id`、`context_part_id`）が一意 |
| `unit_profile`／`unit_conversion` | `unit_profile_id`／`conversion_id` | プロファイルの中で `entry_unit` が一意 |
| `calc_row_template` | `template_id` | ― |
| `param_binding` | `binding_id` | （`scope_kind`、`scope_id`、`param_kind`、`context_condition`）が一意 |
| `selection_record` | `selection_id` | `project_id` → `project_context` |
| `calc_row` | `row_id` | （`selection_id`、`bundle_line_no`）が一意 |

---

## 3. 規則と手順

### 3.1 規則

| ID | 規則 |
|---|---|
| R-01 停止可能 | `SELECTABLE` のノードで止めれば、必ず1つの材料レコード（代表）に解決できる |
| R-02 置換であって追加でない | 絞り込みは同じ `row_id` の `item_id` と参照を置き換える。行を増やさない |
| R-03 代表は既定値の組合せ | 代表レコードは、全軸に既定値を与えたときに解決される材料レコードと同じでなければならない |
| R-04 代表は過小評価に寄せない | 代表の決め方は記録する。係数データが得られた段階で、族の中央より低い側に偏る代表を採らない方針とする（方針であり、未検証） |
| R-05 ばらつきの大きい族は粗いまま使わせない | `spread_class = WIDE` の族は `refinement_recommended = true` とし、粗い選択の行を `REPRESENTATIVE_WIDE` と記録する。`UNKNOWN` も同じ扱い |
| R-06 既定の優先 | 条件が具体的なものが優先。同順位は `priority`。それでも決まらなければカタログの欠陥として既定を適用しない |
| R-07 既定は必ず記録 | 適用した既定は `defaults_applied` に残す。自動適用でも同じ |
| R-08 数量は既定で作らない | 数量を既定値で埋めない。束の比から導いた数量は `DERIVED` とし、比の状態と出典を引き継ぐ |
| R-09 単位は材料族で固定 | 入力単位は単位プロファイルが許すものに限る。許されない単位は換算せず停止する |
| R-10 換算パラメータは推測しない | 密度などが必要で、権利の確認できた値も利用者の入力もなければ停止する |
| R-11 曖昧な語は粗い側へ | 検索キーが複数の対象を指すときは、共通の上位ノードが `SELECTABLE` ならそこへ、なければ候補を返す。勝手に1つに決めない |
| R-12 束は行へ展開 | 構成要素ごとに計算行を作り、束のIDと行番号を残す |
| R-13 範囲キーの衝突を検査 | 同じ案件・部位・区分で、束から来た行と個別に選んだ行が同じ `scope_key` を持つときは、どちらかを明示させる（`REPLACES_BUNDLE_LINE`／`ADDITIONAL_QUANTITY`） |
| R-14 部位は選択の属性 | 同じ材料レコードを複数の部位で使ってよい。部位は選択記録と計算行に持つ |
| R-15 参照が欠けたら計算しない | `FACTOR` が未束縛、または権限が許さない行は `computable = false`。別の材料レコードへ黙って差し替えない |
| R-16 製品固有値は最も具体的な束縛 | 製品固有の参照は係数の参照だけを置き換える。単位の一致と対象段階の確認は同じように行う |
| R-17 候補数の上限 | 1回の `PICK` の候補は `max_fanout` 以下。超えるときは `GROUP` を挟むか、区別を軸へ移す |
| R-18 付随要求は残す | 雛形の `dependent_requirements` は未入力の要求として計算行に付け、値を補わない |
| R-19 版の固定 | 選択記録は解決に使った `catalog_version` を持つ。版が変わっても過去の記録は同じ結果に解決できる |
| R-20 IDは意味を持たず、消さない | 統合・廃止されたレコードは残し、`merged_into` で辿れるようにする |

### 3.2 手順A：選択から計算行への解決

1. **文脈を読む。** `project_context` から主要構造・主用途・カタログ版・数量の根拠の既定を得る。
2. **部位を決める。** `part_id` を1つ決める（同じ部位の指定を続けて行う場合は一度だけ）。
3. **候補を作る。** 部位の根の子ノードを集め、手順Bで除外・順序付け・事前選択を行う。
4. **対象を決める。** 候補から選ぶ、既定を承認する、または手順Cの検索で対象を得る。対象は材料族・材料レコード・束のいずれか。
5. **材料レコードへ解決する。**
   - 材料族の場合：各軸について、利用者の指定 → 仕様トークン → ノードの差し替え既定 → 文脈既定 → 軸の既定値、の順に値を決め、その組合せを持つ材料レコードを選ぶ。該当する材料レコードがない組合せは解決失敗とし、近いものへ寄せない。
   - 材料レコードの場合：そのまま使う。
   - 束の場合：手順Eへ。
6. **単位を確定する。** 手順Dで入力単位を決め、数量を受け取り、正規単位へ換算する。
7. **計算行を作る。** 雛形に従い、`param_binding` を解決順（2.10）で引いて各参照を埋める。束縛元と状態を `param_states` に記録する。
8. **代表性を付ける。** すべての軸が利用者指定なら `REFINED`、材料レコードを直接選んだなら `EXACT`、1つでも既定なら `REPRESENTATIVE`（族のばらつきが `WIDE`／`UNKNOWN` なら `REPRESENTATIVE_WIDE`）。
9. **検査する。** 単位の一致、権限、活動量の有無、範囲キーの衝突、付随要求。問題は `blocking_reasons` に列挙し、行は残す。
10. **記録する。** 選択記録に、対象・軸の指定・適用した既定・換算・操作回数・候補数・生成した行を書く。

### 3.3 手順B：文脈既定の適用

1. `part_id` が一致し、`scope_node_id` が現在のノード（省略時は部位の根）である規則を集める。
2. 各条件が文脈の値と等しいか `ANY` である規則だけを残す。文脈の値が `UNKNOWN` のときは `ANY` の条件にだけ一致する。
3. `EXCLUDE` に当たる候補を既定の候補から外す（検索での到達は妨げない）。
4. `ORDER_BOOST` に当たる候補を先頭へ移し、残りは `sort_key` 順に並べる。
5. `PRESELECT_*` は `specificity` が最大のものを1つ選ぶ。同点は `priority`、さらに同点は適用しない（R-06）。事前選択の対象が `EXCLUDE` されていたらカタログの欠陥として記録する。
6. 事前選択が `auto_apply = false` なら承認を待つ（`ACCEPT` 1回）。`true` なら適用し、どちらの場合も `defaults_applied` に残す。

### 3.4 手順C：検索キーの正規化と照合

正規化（登録時と照合時に同じ手順を使う）：

| 段 | 処理 |
|---|---|
| N1 | Unicode の互換正規化（全角・半角の統一） |
| N2 | 英字を小文字にする |
| N3 | ひらがなとカタカナを一方に統一する |
| N4 | 空白、中点、括弧、ハイフン類を取り除く |
| N5 | 長音記号・小書き文字の揺れは、元の語を壊さず**派生キー**を追加して吸収する |
| N6 | 異体字・新旧字体は自前の対応表で統一する |
| N7 | 寸法・等級の表記を仕様トークンとして切り出す（名称の照合から外す） |

照合の順序：
1. `normalized_key` の完全一致で `key_type = CANONICAL_NAME`。
2. 完全一致でその他の `key_type`。
3. 前方一致。
4. 語を分けたうえでの全語一致。
5. 同順位の中では、現在の部位に一致する `context_part_id` を持つキー、次に `weight` の大きいキーを先にする。

結果の扱い：
- 対象が1つなら、そのまま手順Aの5へ進む（`SEARCH` 1回のみ）。
- 対象が材料族で、部位が未定なら、その族を指すノードを持つ部位を候補として返す（`PICK` 1回）。
- 対象が複数なら R-11 に従う。
- 一致がなければ「未登録の語」として記録し、検索キーの追加候補にする（自動登録はしない）。

### 3.5 手順D：単位の確定と換算

1. 正規単位は材料族の `canonical_unit`。
2. 入力単位は、ノードの `entry_unit_override`、なければ単位プロファイルの `default_entry_unit`。
3. 利用者が別の単位の数量を持っている場合は、`allowed_entries` にある単位に限って受け付ける。
4. 換算に必要なパラメータを `param_source_order` の順に探す。`LICENSED_REQUIRED` しか残らず、権利の確認できた値がなければ停止する（`UNIT_CONVERSION_PARAM_MISSING`）。
5. 入力値、入力単位、換算ID、パラメータの値と取得元、正規単位での活動量を記録する。

### 3.6 手順E：束の展開と二重計上の防止

1. 束の `driver_unit` で基準数量を受け取る。
2. `default_included = true` の構成要素ごとに、対象を材料レコードへ解決する（材料族なら代表）。
3. 構成要素の数量 = 基準数量 × `ratio_per_driver`。比が null なら数量は null、状態は `MISSING`、理由は `BUNDLE_RATIO_MISSING`。
4. 利用者が構成要素の数量を直接与えた場合は、比を使わずその値を採り、状態を利用者の申告どおりにする。
5. 構成要素ごとに計算行を作り、`bundle_id`・`bundle_line_no`・`scope_key` を付ける。
6. 同じ案件・部位・区分の既存行と `scope_key` を突き合わせ、束由来の行と個別選択の行が衝突したら R-13 の判断を求める。
7. 構成要素の絞り込みは、その行の材料レコードの置換として扱う（R-02）。外した構成要素は行を消さず、除外の記録を残す。

### 3.7 手順F：カタログの構築（次段階。実データの入手後）

1. 使うデータセットの権利を確認し、レコードごとに `license_status` を付ける。確認できないものは取り込まない。
2. 名寄せを行い、材料レコードを確定する（名寄せの方法は別の提案の範囲）。
3. 正規単位と絞り込み軸が同じ材料レコードを材料族にまとめる。単位が違えば族を分ける。
4. 軸を定義する。計算行の項目を変えない属性は軸にしない。
5. 各軸の既定値と、族の代表レコードを決め、決め方と根拠を記録する。
6. 単位プロファイルと換算を定義する。換算に必要な値の出典と権利を確認する。
7. 部位ごとに選択木を作る。候補数の上限を超えたら `GROUP` を挟む。
8. 束を定義する。構成比は権利の確認できたデータか、利用者・自組織のデータに限る。
9. 文脈既定を定義する。根拠のないものは `PLACEHOLDER` と明示する。
10. 検索キーを登録する。第三者のコード・商標に由来する語は権利を確認する。
11. 3.8 の整合性検査を通す。
12. 3.9 の手順で手数を測り、目標（T1〜T4）と比べる。

### 3.8 整合性検査（機械的に検査できる不変条件）

| ID | 条件 |
|---|---|
| I-01 | すべての材料族に代表レコードが1つあり、その材料レコードは同じ族に属する |
| I-02 | 族内のすべての材料レコードの正規単位が、族と単位プロファイルの `canonical_unit` に一致する |
| I-03 | 全軸に既定値を与えて解決した材料レコードが `representative_item_id` と一致する（ノードの差し替え既定がある場合は、その組合せの材料レコードが存在する） |
| I-04 | 同じ族の中で、軸の値の組合せが同じ材料レコードは1つだけ |
| I-05 | 軸の値の組合せのうち材料レコードがないものを一覧にできる（欠けた組合せは解決失敗になるため） |
| I-06 | どのノードも子の数が `max_fanout` 以下 |
| I-07 | 部位の根から最初の `SELECTABLE` ノードまでの深さが2以下 |
| I-08 | 選択木に循環がない。`merged_into` の連鎖が有限で、廃止されていないレコードに到達する |
| I-09 | `ambiguity = UNIQUE` の検索キーは、同じ `context_part_id` の範囲で対象が1つ |
| I-10 | 束の構成要素の `ratio_unit` が「構成要素の正規単位／束の `driver_unit`」に一致する |
| I-11 | 束の `covers_scope_keys` が構成要素の `scope_key` の和集合に一致する |
| I-12 | 同じ条件・同じ `specificity`・同じ `priority` で対象が異なる `PRESELECT_*` がない |
| I-13 | 文脈既定・検索キー・束の対象が存在し、廃止されていない |
| I-14 | すべての軸の `affects` が空でない |
| I-15 | カタログの各表に、係数・年数・率の**値**を入れる項目が存在しない（項目名の検査。`ratio_per_driver` は例外で、状態と根拠の記録を必須とする） |
| I-16 | `license_status` が `PERMITTED_PUBLIC` でない束縛を持つ行は `computable = false` になる |

### 3.9 手順G：手数の測定と、絞り込みの優先順位付け

**手数の測定**（実データの入手後）
1. 試験用の数量内訳（材料名・単位・数量の行の集まり）を用意する。権利と守秘の確認が前提。
2. 各行について、検索で届く場合と選択木で届く場合の最小の操作回数と選択情報量を、手順A〜Eを機械的に適用して数える。
3. 行あたりの回数の分布（平均、95パーセンタイル、最大）、検索で届かなかった語の割合、曖昧と判定された語の割合、既定がそのまま使えた割合を出す。
4. 比較対象は「inputs.json の MATERIAL 群の必須項目を行ごとに1つずつ指定する場合」とする。

**絞り込みの優先順位付け**（計算研究の結果を使う）
1. 粗い選択のまま一度計算する。
2. 行ごとに「全体に占める排出量の割合 × 族のばらつきの区分」を求め、大きい順に並べる。
3. 上位の行から絞り込む。あわせて「代表レコード由来の行が全体の排出量に占める割合」を結果とともに示す。

この手順は、絞り込みの操作を結果への影響が大きい行に集めるためのものである。ばらつきの区分は係数データがなければ決められない。

---

## 4. 小さな実例（すべて架空）

**断り書き**：以下は構造の動きを示すための架空の例である。名称は一般的な建築用語に「（架空）」を付けたもの、ID は `FICT` を含むもの、数量は説明用に置いた入力値であり、実在のデータベース・分類表・係数とは関係がない。係数・耐用年数・修繕率・構成比の値は含まない。したがって**どの計算行も計算可能にはならない**。これは意図どおりの動作である（R-15）。

### 4.1 カタログの抜粋

```json
{
  "_notice": "FICTIONAL_PLACEHOLDER_ONLY: 架空の例示。実在のデータベース・分類表・コード表とは無関係。係数・比率・年数・率の値は含まない。",
  "catalog_version": "FICT-0.0",
  "max_fanout": 12,
  "building_part": [
    {"part_id": "STRUCTURE", "label_ja": "躯体", "domain": "ARCHITECTURE", "input_group": "MATERIAL", "sort_order": 20, "root_node_id": "N-FICT-0001"},
    {"part_id": "ROOF_EXTERIOR_WALL", "label_ja": "屋根・外壁", "domain": "ARCHITECTURE", "input_group": "MATERIAL", "sort_order": 30, "root_node_id": "N-FICT-0002"},
    {"part_id": "HVAC", "label_ja": "空調設備", "domain": "EQUIPMENT", "input_group": "EQUIPMENT", "sort_order": 70, "root_node_id": "N-FICT-0003"}
  ],
  "material_family": [
    {"family_id": "FAM-FICT-CONC", "label_ja": "（架空）構造用コンクリート", "item_kind": "MATERIAL", "canonical_unit": "m3", "unit_profile_id": "UP-FICT-VOLUME", "axis_ids": ["AX-FICT-STRENGTH"], "calc_row_template_id": "TPL-FICT-MATERIAL", "representative_item_id": "M-FICT-0102", "representative_rule": "NOT_DECIDED", "spread_class": "UNKNOWN", "refinement_recommended": true, "scope_key": "CONCRETE_STRUCTURAL"},
    {"family_id": "FAM-FICT-REBAR", "label_ja": "（架空）鉄筋", "item_kind": "MATERIAL", "canonical_unit": "kg", "unit_profile_id": "UP-FICT-MASS", "axis_ids": [], "calc_row_template_id": "TPL-FICT-MATERIAL", "representative_item_id": "M-FICT-0201", "representative_rule": "NOT_DECIDED", "spread_class": "UNKNOWN", "refinement_recommended": true, "scope_key": "REBAR"},
    {"family_id": "FAM-FICT-FORM", "label_ja": "（架空）型枠", "item_kind": "MATERIAL", "canonical_unit": "m2", "unit_profile_id": "UP-FICT-AREA", "axis_ids": [], "calc_row_template_id": "TPL-FICT-MATERIAL", "representative_item_id": "M-FICT-0301", "representative_rule": "NOT_DECIDED", "spread_class": "UNKNOWN", "refinement_recommended": true, "scope_key": "FORMWORK"},
    {"family_id": "FAM-FICT-INSUL", "label_ja": "（架空）繊維系断熱材", "item_kind": "MATERIAL", "canonical_unit": "m3", "unit_profile_id": "UP-FICT-VOLUME-BY-AREA", "axis_ids": [], "calc_row_template_id": "TPL-FICT-MATERIAL", "representative_item_id": "M-FICT-0401", "representative_rule": "NOT_DECIDED", "spread_class": "UNKNOWN", "refinement_recommended": true, "scope_key": "INSULATION_FIBROUS"},
    {"family_id": "FAM-FICT-HEATSRC", "label_ja": "（架空）熱源機器", "item_kind": "EQUIPMENT_UNIT", "canonical_unit": "unit", "unit_profile_id": "UP-FICT-COUNT", "axis_ids": [], "calc_row_template_id": "TPL-FICT-EQUIPMENT", "representative_item_id": "M-FICT-0501", "representative_rule": "NOT_DECIDED", "spread_class": "UNKNOWN", "refinement_recommended": true, "scope_key": "HEAT_SOURCE_UNIT"}
  ],
  "material_item": [
    {"item_id": "M-FICT-0101", "family_id": "FAM-FICT-CONC", "canonical_name_ja": "（架空）構造用コンクリート 強度区分L", "record_kind": "SPECIFIC", "axis_values": [{"axis_id": "AX-FICT-STRENGTH", "option_id": "OPT-FICT-STR-L"}], "license_status": "UNKNOWN"},
    {"item_id": "M-FICT-0102", "family_id": "FAM-FICT-CONC", "canonical_name_ja": "（架空）構造用コンクリート 強度区分M", "record_kind": "SPECIFIC", "axis_values": [{"axis_id": "AX-FICT-STRENGTH", "option_id": "OPT-FICT-STR-M"}], "license_status": "UNKNOWN"},
    {"item_id": "M-FICT-0103", "family_id": "FAM-FICT-CONC", "canonical_name_ja": "（架空）構造用コンクリート 強度区分H", "record_kind": "SPECIFIC", "axis_values": [{"axis_id": "AX-FICT-STRENGTH", "option_id": "OPT-FICT-STR-H"}], "license_status": "UNKNOWN"},
    {"item_id": "M-FICT-0201", "family_id": "FAM-FICT-REBAR", "canonical_name_ja": "（架空）鉄筋 代表", "record_kind": "GENERIC_REPRESENTATIVE", "axis_values": [], "derivation_rule": "未定（族内の係数データが必要）", "license_status": "UNKNOWN"},
    {"item_id": "M-FICT-0301", "family_id": "FAM-FICT-FORM", "canonical_name_ja": "（架空）型枠 代表", "record_kind": "GENERIC_REPRESENTATIVE", "axis_values": [], "derivation_rule": "未定（族内の係数データが必要）", "license_status": "UNKNOWN"},
    {"item_id": "M-FICT-0401", "family_id": "FAM-FICT-INSUL", "canonical_name_ja": "（架空）繊維系断熱材 代表", "record_kind": "GENERIC_REPRESENTATIVE", "axis_values": [], "derivation_rule": "未定（族内の係数データが必要）", "license_status": "UNKNOWN"},
    {"item_id": "M-FICT-0501", "family_id": "FAM-FICT-HEATSRC", "canonical_name_ja": "（架空）熱源機器 代表", "record_kind": "GENERIC_REPRESENTATIVE", "axis_values": [], "derivation_rule": "未定（族内の係数データが必要）", "license_status": "UNKNOWN"}
  ],
  "refinement_axis": [
    {"axis_id": "AX-FICT-STRENGTH", "label_ja": "（架空）強度区分", "value_type": "ENUM", "affects": ["FACTOR"], "default_option_id": "OPT-FICT-STR-M", "default_rule": "NOT_DECIDED"}
  ],
  "refinement_option": [
    {"option_id": "OPT-FICT-STR-L", "axis_id": "AX-FICT-STRENGTH", "label_ja": "区分L", "sort_order": 1},
    {"option_id": "OPT-FICT-STR-M", "axis_id": "AX-FICT-STRENGTH", "label_ja": "区分M", "sort_order": 2},
    {"option_id": "OPT-FICT-STR-H", "axis_id": "AX-FICT-STRENGTH", "label_ja": "区分H", "sort_order": 3}
  ],
  "selection_node": [
    {"node_id": "N-FICT-0001", "parent_node_id": null, "part_id": "STRUCTURE", "level": "PART", "node_kind": "NAVIGATION_ONLY", "target_kind": "NONE", "target_id": null, "label_ja": "躯体", "sort_key": 0},
    {"node_id": "N-FICT-0011", "parent_node_id": "N-FICT-0001", "part_id": "STRUCTURE", "level": "FAMILY", "node_kind": "SELECTABLE", "target_kind": "FAMILY", "target_id": "FAM-FICT-CONC", "label_ja": "（架空）コンクリート", "sort_key": 10},
    {"node_id": "N-FICT-0012", "parent_node_id": "N-FICT-0001", "part_id": "STRUCTURE", "level": "FAMILY", "node_kind": "SELECTABLE", "target_kind": "FAMILY", "target_id": "FAM-FICT-REBAR", "label_ja": "（架空）鉄筋", "sort_key": 20},
    {"node_id": "N-FICT-0013", "parent_node_id": "N-FICT-0001", "part_id": "STRUCTURE", "level": "FAMILY", "node_kind": "SELECTABLE", "target_kind": "FAMILY", "target_id": "FAM-FICT-FORM", "label_ja": "（架空）型枠", "sort_key": 30},
    {"node_id": "N-FICT-0014", "parent_node_id": "N-FICT-0001", "part_id": "STRUCTURE", "level": "FAMILY", "node_kind": "SELECTABLE", "target_kind": "BUNDLE", "target_id": "B-FICT-RCFRAME", "label_ja": "（架空）RC躯体一式", "sort_key": 5},
    {"node_id": "N-FICT-0002", "parent_node_id": null, "part_id": "ROOF_EXTERIOR_WALL", "level": "PART", "node_kind": "NAVIGATION_ONLY", "target_kind": "NONE", "target_id": null, "label_ja": "屋根・外壁", "sort_key": 0},
    {"node_id": "N-FICT-0021", "parent_node_id": "N-FICT-0002", "part_id": "ROOF_EXTERIOR_WALL", "level": "FAMILY", "node_kind": "SELECTABLE", "target_kind": "FAMILY", "target_id": "FAM-FICT-INSUL", "label_ja": "（架空）断熱材（繊維系）", "entry_unit_override": "m2", "sort_key": 10},
    {"node_id": "N-FICT-0003", "parent_node_id": null, "part_id": "HVAC", "level": "PART", "node_kind": "NAVIGATION_ONLY", "target_kind": "NONE", "target_id": null, "label_ja": "空調設備", "sort_key": 0},
    {"node_id": "N-FICT-0031", "parent_node_id": "N-FICT-0003", "part_id": "HVAC", "level": "FAMILY", "node_kind": "SELECTABLE", "target_kind": "FAMILY", "target_id": "FAM-FICT-HEATSRC", "label_ja": "（架空）熱源機器", "sort_key": 10}
  ],
  "bundle": [
    {"bundle_id": "B-FICT-RCFRAME", "label_ja": "（架空）RC躯体一式", "part_id": "STRUCTURE", "bundle_kind": "ASSEMBLY", "driver_quantity_kind": "VOLUME", "driver_unit": "m3", "expansion_mode": "EXPAND_TO_ROWS", "covers_scope_keys": ["CONCRETE_STRUCTURAL", "REBAR", "FORMWORK"]}
  ],
  "bundle_component": [
    {"bundle_id": "B-FICT-RCFRAME", "line_no": 1, "target_kind": "FAMILY", "target_id": "FAM-FICT-CONC", "ratio_per_driver": 1, "ratio_unit": "m3/m3", "ratio_basis": "DRIVER_IDENTITY", "ratio_value_state": "DERIVED", "default_included": true, "optional": false, "substitutable": true, "scope_key": "CONCRETE_STRUCTURAL"},
    {"bundle_id": "B-FICT-RCFRAME", "line_no": 2, "target_kind": "FAMILY", "target_id": "FAM-FICT-REBAR", "ratio_per_driver": null, "ratio_unit": "kg/m3", "ratio_basis": "PLACEHOLDER", "ratio_value_state": "MISSING", "default_included": true, "optional": false, "substitutable": true, "scope_key": "REBAR"},
    {"bundle_id": "B-FICT-RCFRAME", "line_no": 3, "target_kind": "FAMILY", "target_id": "FAM-FICT-FORM", "ratio_per_driver": null, "ratio_unit": "m2/m3", "ratio_basis": "PLACEHOLDER", "ratio_value_state": "MISSING", "default_included": true, "optional": true, "substitutable": true, "scope_key": "FORMWORK"}
  ],
  "context_default": [
    {"default_id": "D-FICT-01", "part_id": "STRUCTURE", "scope_node_id": "N-FICT-0001", "structure_type": "RC", "building_use": "ANY", "default_kind": "PRESELECT_BUNDLE", "target_kind": "BUNDLE", "target_id": "B-FICT-RCFRAME", "specificity": 1, "priority": 10, "auto_apply": false, "basis": "PLACEHOLDER", "evidence_ref": null},
    {"default_id": "D-FICT-02", "part_id": "STRUCTURE", "scope_node_id": "N-FICT-0001", "structure_type": "RC", "building_use": "ANY", "default_kind": "ORDER_BOOST", "target_kind": "NODE", "target_id": "N-FICT-0011", "specificity": 1, "priority": 20, "auto_apply": true, "basis": "PLACEHOLDER", "evidence_ref": null}
  ],
  "search_key": [
    {"key_id": "K-FICT-01", "display_form": "生コン", "normalized_key": "生コン", "key_type": "TRADE_TERM", "target_kind": "FAMILY", "target_id": "FAM-FICT-CONC", "ambiguity": "UNIQUE", "weight": 10, "source": "CURATED"},
    {"key_id": "K-FICT-02", "display_form": "なまこん", "normalized_key": "ナマコン", "key_type": "READING_KANA", "target_kind": "FAMILY", "target_id": "FAM-FICT-CONC", "ambiguity": "UNIQUE", "weight": 5, "source": "CURATED"},
    {"key_id": "K-FICT-03", "display_form": "断熱マット", "normalized_key": "断熱マット", "key_type": "SYNONYM", "target_kind": "FAMILY", "target_id": "FAM-FICT-INSUL", "ambiguity": "UNIQUE", "context_part_id": "ROOF_EXTERIOR_WALL", "weight": 10, "source": "CURATED"}
  ],
  "spec_token_pattern": [
    {"pattern_id": "ST-FICT-01", "pattern": "t<数値>（単位 mm）", "maps_to_kind": "CONVERSION_PARAM", "maps_to_name": "thickness_m", "unit": "mm"}
  ],
  "unit_profile": [
    {"unit_profile_id": "UP-FICT-VOLUME", "canonical_unit": "m3", "default_entry_unit": "m3", "allowed_entries": [{"entry_unit": "m3", "conversion_id": "UC-FICT-IDENTITY-M3"}]},
    {"unit_profile_id": "UP-FICT-MASS", "canonical_unit": "kg", "default_entry_unit": "kg", "allowed_entries": [{"entry_unit": "kg", "conversion_id": "UC-FICT-IDENTITY-KG"}, {"entry_unit": "t", "conversion_id": "UC-FICT-T-TO-KG"}]},
    {"unit_profile_id": "UP-FICT-AREA", "canonical_unit": "m2", "default_entry_unit": "m2", "allowed_entries": [{"entry_unit": "m2", "conversion_id": "UC-FICT-IDENTITY-M2"}]},
    {"unit_profile_id": "UP-FICT-VOLUME-BY-AREA", "canonical_unit": "m3", "default_entry_unit": "m3", "allowed_entries": [{"entry_unit": "m3", "conversion_id": "UC-FICT-IDENTITY-M3"}, {"entry_unit": "m2", "conversion_id": "UC-FICT-M2-TO-M3"}]},
    {"unit_profile_id": "UP-FICT-COUNT", "canonical_unit": "unit", "default_entry_unit": "unit", "allowed_entries": [{"entry_unit": "unit", "conversion_id": "UC-FICT-IDENTITY-UNIT"}]}
  ],
  "unit_conversion": [
    {"conversion_id": "UC-FICT-IDENTITY-M3", "from_unit": "m3", "to_unit": "m3", "conversion_kind": "IDENTITY", "required_params": [], "param_source_order": [], "formula_note": "q_canonical = q_entry", "exactness": "EXACT_DEFINITION"},
    {"conversion_id": "UC-FICT-IDENTITY-KG", "from_unit": "kg", "to_unit": "kg", "conversion_kind": "IDENTITY", "required_params": [], "param_source_order": [], "formula_note": "q_canonical = q_entry", "exactness": "EXACT_DEFINITION"},
    {"conversion_id": "UC-FICT-IDENTITY-M2", "from_unit": "m2", "to_unit": "m2", "conversion_kind": "IDENTITY", "required_params": [], "param_source_order": [], "formula_note": "q_canonical = q_entry", "exactness": "EXACT_DEFINITION"},
    {"conversion_id": "UC-FICT-IDENTITY-UNIT", "from_unit": "unit", "to_unit": "unit", "conversion_kind": "IDENTITY", "required_params": [], "param_source_order": [], "formula_note": "q_canonical = q_entry", "exactness": "EXACT_DEFINITION"},
    {"conversion_id": "UC-FICT-T-TO-KG", "from_unit": "t", "to_unit": "kg", "conversion_kind": "SI_DEFINITION", "required_params": [], "param_source_order": [], "formula_note": "q_canonical = q_entry × 1000", "exactness": "EXACT_DEFINITION"},
    {"conversion_id": "UC-FICT-M2-TO-M3", "from_unit": "m2", "to_unit": "m3", "conversion_kind": "GEOMETRIC", "required_params": ["thickness_m"], "param_source_order": ["SPEC_TOKEN", "USER_INPUT"], "formula_note": "q_canonical = q_entry × thickness_m", "exactness": "PARAMETER_DEPENDENT"}
  ],
  "calc_row_template": [
    {"template_id": "TPL-FICT-MATERIAL", "activity_kind": "MATERIAL_QUANTITY", "required_param_kinds": ["FACTOR"], "optional_param_kinds": ["MASS_PER_UNIT", "SERVICE_LIFE", "REPAIR_RATE", "EOL_ROUTE", "WASTE_RATE"], "dependent_requirements": []},
    {"template_id": "TPL-FICT-EQUIPMENT", "activity_kind": "EQUIPMENT_COUNT", "required_param_kinds": ["FACTOR"], "optional_param_kinds": ["MASS_PER_UNIT", "SERVICE_LIFE", "REPAIR_RATE", "EOL_ROUTE"], "dependent_requirements": ["REFRIGERANT_CHARGE"]}
  ],
  "param_binding": [
    {"binding_id": "PB-FICT-01", "scope_kind": "ITEM", "scope_id": "M-FICT-0103", "param_kind": "FACTOR", "param_ref": null, "value_state": "MISSING", "license_status": "UNKNOWN"},
    {"binding_id": "PB-FICT-02", "scope_kind": "FAMILY", "scope_id": "FAM-FICT-CONC", "param_kind": "EOL_ROUTE", "param_ref": null, "value_state": "MISSING", "license_status": "UNKNOWN"},
    {"binding_id": "PB-FICT-03", "scope_kind": "PART", "scope_id": "STRUCTURE", "param_kind": "SERVICE_LIFE", "param_ref": null, "value_state": "MISSING", "license_status": "UNKNOWN"}
  ]
}
```

### 4.2 場面ごとの解決

文脈：架空の案件 `PRJ-FICT-01`、`structure_type = RC`、主用途は任意（この例の文脈既定は、どれも主用途の条件が `ANY`）、数量の根拠の案件既定は `DESIGN`。文脈の設定は材料ごとの手数に数えない。

**場面1：粗い指定（束）**

| 手順 | 内容 | 操作 |
|---|---|---|
| 部位を決める | 躯体（指示書が挙げる9グループから1つ） | `PICK` 1（候補9） |
| 候補を作る | D-FICT-02 によりコンクリートが先頭へ。D-FICT-01 により束 `B-FICT-RCFRAME` が事前選択される | ― |
| 既定を承認する | `auto_apply = false` なので承認が要る | `ACCEPT` 1 |
| 基準数量を入れる | 束の `driver_unit` により単位は m3 に決まっている。コンクリート体積 120 を入れる（説明用の入力値） | `ENTER` 1 |
| 展開する | 行1：コンクリート 120 m3（比は基準数量そのもの）。行2：鉄筋、数量は「120 × 比」だが比が未入手なので null。行3：型枠も同じ | ― |

結果：3回の操作で3行。ただし行2・行3は数量が欠けている（`BUNDLE_RATIO_MISSING`）。完成させる道は2つある。
- (a) 権利の確認できた構成比、または利用者自身の構成比を束に与える。数量は `DERIVED` になり、推定である旨が行に残る。操作は増えない。
- (b) 鉄筋と型枠の数量を直接入れる。`ENTER` が2回増え、合計5回で3行。数量は利用者の申告どおりの状態になる。

**場面2：後からの絞り込み**

行1の強度区分を「区分H」に指定する（`PICK` 1、候補3）。
- 行1の `item_id` が `M-FICT-0102`（代表＝区分M）から `M-FICT-0103` に替わる。`row_id` は変わらず、行は増えない（R-02）。
- 行1の代表性は `REPRESENTATIVE_WIDE` から `REFINED` に替わる。
- 係数の参照は `M-FICT-0103` の束縛（PB-FICT-01）を引くが、未束縛なので `FACTOR_MISSING` のまま。

**場面3：検索と、選択で決まる単位**

部位は屋根・外壁に決まっているとする。検索語「断熱ﾏｯﾄ t50」を与える（`SEARCH` 1）。
1. 正規化：半角カナを統一し、空白を除く。「t50」は仕様トークンとして切り出され、ST-FICT-01 により厚さ 50 mm、すなわち `thickness_m = 0.05`（単位の定義による換算）になる。
2. 照合：「断熱マット」は K-FICT-03 に完全一致し、対象は `FAM-FICT-INSUL` の1つだけ。部位の中でこの族を指すノードは `N-FICT-0021`。`PICK` は不要。
3. 単位：族の正規単位は m3。ノードの `entry_unit_override` により入力単位は m2。換算は `UC-FICT-M2-TO-M3` で、必要な厚さは仕様トークンから得られている。
4. 数量：面積 200 を入れる（`ENTER` 1。説明用の入力値）。活動量 = 200 m2 × 0.05 m = 10 m3。

結果：2回の操作で1行。単位を選ぶ操作も、厚さを別に入れる操作も発生していない。厚さが検索語になければ `ENTER` が1回増える。

**場面4：設備と付随要求**

空調設備で「（架空）熱源機器」を選び（`PICK` 1）、台数 2 を入れる（`ENTER` 1）。
- 雛形 `TPL-FICT-EQUIPMENT` により `activity_kind = EQUIPMENT_COUNT`、単位は `unit`。
- `dependent_requirements` により、冷媒の充填量が未入力の要求として行に付く。値は補わない（R-18）。

**場面5：曖昧な語（抜粋外の例）**

内装で「ボード」と検索したとき、同じ正規化キーが2つの材料族を指していれば `ambiguity = AMBIGUOUS` であり、共通の `SELECTABLE` な上位ノードがなければ2件の候補を返す（`PICK` 1）。どちらかへ自動で寄せることはしない（R-11）。

### 4.3 生成される選択記録と計算行（場面1(a)未実施＋場面2、場面3、場面4の後）

```json
{
  "_notice": "FICTIONAL_PLACEHOLDER_ONLY: 架空の例示。数量は説明用の入力値。係数・年数・率・構成比の値は含まない。",
  "selection_record": [
    {
      "selection_id": "SEL-FICT-001", "project_id": "PRJ-FICT-01", "catalog_version": "FICT-0.0",
      "part_id": "STRUCTURE", "zone_id": null,
      "chosen_target_kind": "BUNDLE", "chosen_target_id": "B-FICT-RCFRAME", "via_node_id": "N-FICT-0014", "search_key_id": null,
      "resolution_mode": "BUNDLE_EXPANDED", "axis_choices": [],
      "component_refinements": [
        {"line_no": 1, "axis_choices": [{"axis_id": "AX-FICT-STRENGTH", "option_id": "OPT-FICT-STR-H", "state": "USER_CHOSEN"}], "included": true, "direct_quantity": null}
      ],
      "entry_quantity": 120, "entry_unit": "m3", "quantity_state": "USER_ESTIMATE", "quantity_basis": "DESIGN",
      "conversion_id": "UC-FICT-IDENTITY-M3", "conversion_params": {},
      "defaults_applied": ["D-FICT-01", "D-FICT-02"], "overrides": [],
      "operation_count": {"pick": 2, "enter": 1, "search": 0, "accept": 1, "override": 0},
      "candidate_counts": [9, 3],
      "resolved_row_ids": ["ROW-FICT-001", "ROW-FICT-002", "ROW-FICT-003"]
    },
    {
      "selection_id": "SEL-FICT-002", "project_id": "PRJ-FICT-01", "catalog_version": "FICT-0.0",
      "part_id": "ROOF_EXTERIOR_WALL", "zone_id": null,
      "chosen_target_kind": "FAMILY", "chosen_target_id": "FAM-FICT-INSUL", "via_node_id": "N-FICT-0021", "search_key_id": "K-FICT-03",
      "resolution_mode": "REPRESENTATIVE", "axis_choices": [], "component_refinements": [],
      "entry_quantity": 200, "entry_unit": "m2", "quantity_state": "USER_ESTIMATE", "quantity_basis": "DESIGN",
      "conversion_id": "UC-FICT-M2-TO-M3", "conversion_params": {"thickness_m": {"value": 0.05, "source": "SPEC_TOKEN", "pattern_id": "ST-FICT-01"}},
      "defaults_applied": [], "overrides": [],
      "operation_count": {"pick": 0, "enter": 1, "search": 1, "accept": 0, "override": 0},
      "candidate_counts": [],
      "resolved_row_ids": ["ROW-FICT-004"]
    },
    {
      "selection_id": "SEL-FICT-003", "project_id": "PRJ-FICT-01", "catalog_version": "FICT-0.0",
      "part_id": "HVAC", "zone_id": null,
      "chosen_target_kind": "FAMILY", "chosen_target_id": "FAM-FICT-HEATSRC", "via_node_id": "N-FICT-0031", "search_key_id": null,
      "resolution_mode": "REPRESENTATIVE", "axis_choices": [], "component_refinements": [],
      "entry_quantity": 2, "entry_unit": "unit", "quantity_state": "USER_ESTIMATE", "quantity_basis": "DESIGN",
      "conversion_id": "UC-FICT-IDENTITY-UNIT", "conversion_params": {},
      "defaults_applied": [], "overrides": [],
      "operation_count": {"pick": 1, "enter": 1, "search": 0, "accept": 0, "override": 0},
      "candidate_counts": [1],
      "resolved_row_ids": ["ROW-FICT-005"]
    }
  ],
  "calc_row": [
    {
      "row_id": "ROW-FICT-001", "selection_id": "SEL-FICT-001", "bundle_id": "B-FICT-RCFRAME", "bundle_line_no": 1,
      "part_id": "STRUCTURE", "item_id": "M-FICT-0103",
      "activity": 120, "activity_unit": "m3", "activity_state": "USER_ESTIMATE",
      "factor_ref": null, "mass_per_unit_ref": null, "service_life_ref": null, "repair_rate_ref": null, "eol_route_ref": null, "waste_rate_ref": null,
      "param_states": {"FACTOR": {"value_state": "MISSING", "license_status": "UNKNOWN", "bound_from": "ITEM"}, "SERVICE_LIFE": {"value_state": "MISSING", "license_status": "UNKNOWN", "bound_from": "PART"}, "EOL_ROUTE": {"value_state": "MISSING", "license_status": "UNKNOWN", "bound_from": "FAMILY"}},
      "representativeness": "REFINED", "scope_key": "CONCRETE_STRUCTURAL",
      "computable": false, "blocking_reasons": ["FACTOR_MISSING"], "dependent_requirements": []
    },
    {
      "row_id": "ROW-FICT-002", "selection_id": "SEL-FICT-001", "bundle_id": "B-FICT-RCFRAME", "bundle_line_no": 2,
      "part_id": "STRUCTURE", "item_id": "M-FICT-0201",
      "activity": null, "activity_unit": "kg", "activity_state": "MISSING",
      "factor_ref": null, "mass_per_unit_ref": null, "service_life_ref": null, "repair_rate_ref": null, "eol_route_ref": null, "waste_rate_ref": null,
      "param_states": {"FACTOR": {"value_state": "MISSING", "license_status": "UNKNOWN", "bound_from": null}},
      "representativeness": "REPRESENTATIVE_WIDE", "scope_key": "REBAR",
      "computable": false, "blocking_reasons": ["BUNDLE_RATIO_MISSING", "QUANTITY_MISSING", "FACTOR_MISSING"], "dependent_requirements": []
    },
    {
      "row_id": "ROW-FICT-003", "selection_id": "SEL-FICT-001", "bundle_id": "B-FICT-RCFRAME", "bundle_line_no": 3,
      "part_id": "STRUCTURE", "item_id": "M-FICT-0301",
      "activity": null, "activity_unit": "m2", "activity_state": "MISSING",
      "factor_ref": null, "mass_per_unit_ref": null, "service_life_ref": null, "repair_rate_ref": null, "eol_route_ref": null, "waste_rate_ref": null,
      "param_states": {"FACTOR": {"value_state": "MISSING", "license_status": "UNKNOWN", "bound_from": null}},
      "representativeness": "REPRESENTATIVE_WIDE", "scope_key": "FORMWORK",
      "computable": false, "blocking_reasons": ["BUNDLE_RATIO_MISSING", "QUANTITY_MISSING", "FACTOR_MISSING"], "dependent_requirements": []
    },
    {
      "row_id": "ROW-FICT-004", "selection_id": "SEL-FICT-002", "bundle_id": null, "bundle_line_no": null,
      "part_id": "ROOF_EXTERIOR_WALL", "item_id": "M-FICT-0401",
      "activity": 10, "activity_unit": "m3", "activity_state": "DERIVED",
      "factor_ref": null, "mass_per_unit_ref": null, "service_life_ref": null, "repair_rate_ref": null, "eol_route_ref": null, "waste_rate_ref": null,
      "param_states": {"FACTOR": {"value_state": "MISSING", "license_status": "UNKNOWN", "bound_from": null}},
      "representativeness": "REPRESENTATIVE_WIDE", "scope_key": "INSULATION_FIBROUS",
      "computable": false, "blocking_reasons": ["FACTOR_MISSING"], "dependent_requirements": []
    },
    {
      "row_id": "ROW-FICT-005", "selection_id": "SEL-FICT-003", "bundle_id": null, "bundle_line_no": null,
      "part_id": "HVAC", "item_id": "M-FICT-0501",
      "activity": 2, "activity_unit": "unit", "activity_state": "USER_ESTIMATE",
      "factor_ref": null, "mass_per_unit_ref": null, "service_life_ref": null, "repair_rate_ref": null, "eol_route_ref": null, "waste_rate_ref": null,
      "param_states": {"FACTOR": {"value_state": "MISSING", "license_status": "UNKNOWN", "bound_from": null}},
      "representativeness": "REPRESENTATIVE_WIDE", "scope_key": "HEAT_SOURCE_UNIT",
      "computable": false, "blocking_reasons": ["FACTOR_MISSING"], "dependent_requirements": [{"kind": "REFRIGERANT_CHARGE", "state": "MISSING"}]
    }
  ]
}
```

補足：
- `ROW-FICT-004` の活動量は入力値（面積）と厚さから換算で得たため `DERIVED`。元の入力値と換算は選択記録に残る。
- `SEL-FICT-003` の `candidate_counts` が 1 なのは、抜粋のカタログで空調設備の下にノードが1つしかないためで、実際の候補数を示すものではない。

### 4.4 この例での操作回数の数え方

比較対象は「inputs.json の MATERIAL 群の必須項目（工種、資材の分類、数量の単位、数量の根拠、数量）を行ごとに1つずつ指定する」場合とし、1行あたり `PICK` 4 + `ENTER` 1 = 5回と数える（設備の行も同じ数え方を仮に当てはめる）。

| 場面 | 生成行 | 本設計での回数 | 行ごとに指定する場合 | 備考 |
|---|---:|---:|---:|---|
| 1(b)＋2 | 3 | 6（`PICK` 2、`ACCEPT` 1、`ENTER` 3） | 15 | 絞り込み1回を含む。構成比を使わず数量を直接入れた場合 |
| 1(a)＋2 | 3 | 4（`PICK` 2、`ACCEPT` 1、`ENTER` 1） | 15 | 構成比が与えられた場合。2行の数量は推定になる |
| 3 | 1 | 2（`SEARCH` 1、`ENTER` 1） | 5 | 厚さが検索語にあった場合 |
| 4 | 1 | 2（`PICK` 1、`ENTER` 1） | 5 | 冷媒の入力要求は別に残る |

**この表は数え方の例示であり、手数が減ることの証拠ではない。** カタログが架空で極端に小さく、比較対象の数え方も仮定である。実際の効果は 3.9 の手順で、実在の数量内訳を使って測る必要がある。

---

## 5. 未解決事項と、検証に必要な実データ

### 5.1 実データがなければ答えられない問い

| ID | 問い | 必要なデータ | 権利・守秘の前提 |
|---|---|---|---|
| Q-01 | 材料レコードは何件あり、部位グループごとにどう分布するか。候補数の上限と深さ2以内の制約は両立するか | 権利の確認できた材料・設備のレコード一覧 | データセットの利用許諾 |
| Q-02 | 粗い選択（代表レコード）は、建物全体1％・主要段階2％という暫定目標と両立するか | 同じ族の中の係数のばらつき、および実建物の数量内訳 | 係数の利用許諾。J-CAT の値は使えない |
| Q-03 | 代表レコードの決め方は何がよいか（最頻、中央、高め） | 族内の係数の分布と使用頻度 | 同上 |
| Q-04 | 絞り込み軸はどれが必要で、どの順に問うべきか | 仕様の違いによる係数・耐用年数・廃棄経路の差 | 同上 |
| Q-05 | 部位×主要構造の既定は実際に当たるか（既定がそのまま使える割合） | 複数の実建物の数量内訳（構造・用途の別が分かるもの） | 案件の守秘 |
| Q-06 | 束の構成比は使える精度か。構造・用途・規模でどれだけ変わるか | 同上。および構成比の出典 | 第三者の統計値は利用許諾の確認が必要 |
| Q-07 | 検索キーでどれだけの名称に届くか。曖昧な語はどれくらいあるか | 実務の数量内訳に現れる材料名の一覧、入力記録 | 案件の守秘、個人情報 |
| Q-08 | 係数の分母単位は族の中でそろうか。そろわない族はどれだけあるか | 使うデータセットの単位の一覧 | データセットの利用許諾 |
| Q-09 | 単位換算に必要な値（密度、単位質量など）はどこから得るか | 権利の確認できた物性値、または製品資料 | 出典ごとの確認 |
| Q-10 | 耐用年数・修繕率・廃棄経路を、部位・族・材料レコードのどの水準に束縛するのが妥当か | 独立して使える維持更新・廃棄のデータ | J-CAT の値は使えない |

### 5.2 設計上の未決事項（データがなくても議論できるもの）

| ID | 未決事項 | 現時点の案 |
|---|---|---|
| D-01 | 追加の部位グループ（外構、仮設、その他）の要否 | 候補として置くだけにし、決めない |
| D-02 | 屋根と外壁を1グループのままにするか | 指示書の区分に従い1グループ。下の階層で分ける |
| D-03 | 設備の活動量を台数・能力・床面積のどれで持つか | 雛形の `activity_kind` で族ごとに決める。どれが多いかは不明 |
| D-04 | 数量を把握していない工事項目（概念式 A13-04。モデル未定義）を選択の仕組みに含めるか | 含めない。計算研究の結論を待つ |
| D-05 | 自動適用の既定をどこまで認めるか | 計算結果を変えるものは認めない案。並び順だけは自動適用 |
| D-06 | 束を合成済みとして扱うこと（`PRECOMPOSED`）を認めるか | 構成行へ展開できる定義がある場合の計算上の短絡に限る |
| D-07 | 族の代表を個別仕様から選ぶか、一般レコード（`GENERIC_REPRESENTATIVE`）を別に作るか | 両方を許し、族ごとに記録する。軸を持つ族は個別仕様から選ぶ |
| D-08 | 組織ごとの使用頻度を並び順に反映するか | 構造上は `context_default` の `basis = FREQUENCY_FROM_DATA` で表せる。記録の取り方は未設計 |
| D-09 | 区分（`zone_id`）の語彙 | 未定義。自由記述から始める |
| D-10 | `max_fanout` の値、`spread_class` の閾値 | 仮置き。実データで決める |

### 5.3 分類表・集計表のシート名から言えること・言えないこと

言えること：区分ごとの表、コード表、複合的な原単位の表、電気の主要機器の表、配管・ケーブルの表が、それぞれ別シートとして存在する。数式ノードは分類表ブックに 0 件、集計表ブックに 8,293 件ある。
言えないこと：各表の行数、階層の深さ、コードの体系、単位の持ち方、区分間の重複。したがって、本設計がそれらと整合するかどうかは判断できないし、整合させることを目標にもしていない。

### 5.4 検証計画（実データの入手後に行う。現時点では未実施）

| 指標 | 定義 | 判定に使う場面 |
|---|---|---|
| 到達率 | 数量内訳の行のうち、検索1回＋選択1回以内で選択対象に届いた割合 | Q-07 |
| 行あたり操作回数 | 平均、95パーセンタイル、最大 | T1・T2 |
| 選択情報量 | 行あたりの Σ log2(候補数) | T3 |
| 既定適中率 | 事前選択がそのまま承認された割合 | Q-05 |
| 曖昧率 | 検索結果が複数の対象に分かれた割合 | Q-07 |
| 代表使用時の誤差 | 代表レコードで計算した結果と、個別仕様で計算した結果の相対誤差（符号付き。過小評価を別に集計） | Q-02・Q-03 |
| 束の推定誤差 | 構成比から導いた数量と、実際の数量の相対誤差 | Q-06 |
| 代表由来の割合 | 代表レコードの行が全体の排出量に占める割合 | 結果の質の表示 |

架空データでこれらを測っても、実用上の妥当性は示せない。架空データでできるのは、3.8 の整合性検査と、解決手順が決定的であることの確認までである。

### 5.5 計算研究との間で確認が必要な点

1. 統一計算行の項目名と、本書の `calc_row` の対応（特に廃棄経路の表し方、質量換算の持ち方）。
2. 修繕率と耐用年数を行ごとに持つのか、族・部位の水準でまとめて持つのか。まとめて持てるなら `param_binding` の `PART`・`FAMILY` 水準が主になる。
3. 活動量が欠けている行、参照が欠けている行を計算側がどう扱うか（停止か、除外して明示か）。
4. 束から展開した行をグループとして集計する必要があるか。

### 5.6 他の提案との統合で確認が必要な点

- 材料族・材料レコードの定義と ID 体系（本書は選択に必要な最小の項目だけを定義した）。
- 名寄せの台帳と `source_record_refs`・`merged_into_item_id` の対応。
- 同義語を名寄せ側で持つか、本書の `search_key` で持つか（二重管理を避ける）。
- 部位グループの語彙と、部位を材料の属性にしないという決定（1.4 の2）への賛否。

---

## 6. リスクと、してはならないこと

### 6.1 リスク

| ID | リスク | 影響 | 軽減策（本設計の中で） |
|---|---|---|---|
| K-01 | 代表レコードが族の実態より低い係数に偏る | 系統的な過小評価 | R-04、R-05。代表性を行に記録し、代表由来の割合を結果に示す。ばらつきが不明な族は `REPRESENTATIVE_WIDE` |
| K-02 | 既定が「普通の建物」へ結果を寄せ、案件ごとの違いを消す | 比較（改善案との差分）の意味が薄れる | 既定の適用を記録。計算結果を変える既定は承認を要する。既定のままの行を集計できる |
| K-03 | 束と個別指定の二重計上、または束から外した構成要素の計上漏れ | 過大または過小 | 範囲キーの検査（R-13）。除外の記録を残す |
| K-04 | 束の構成比が実建物と合わない | 数量の推定誤差。構造・規模による偏り | 導いた数量を `DERIVED` とし、比の根拠を引き継ぐ。直接入力を常に許す |
| K-05 | 束の構成要素の係数が含む段階がそろっていない | 算定境界の混在 | 構成行への展開（合成係数にしない）。`factor_stage_note` と係数側の対象段階の検査 |
| K-06 | 単位換算に、出典の確認できない密度などが紛れ込む | 誤差、権利上の問題 | 換算パラメータの取得元を記録。推測しない（R-10） |
| K-07 | 同義語の誤った対応（似た語が別の材料を指す） | 誤った材料レコードの選択 | 曖昧な語は粗い側へ（R-11）。部位による限定。未登録の語は自動登録しない |
| K-08 | 浅い木と候補数の上限が、実データの件数では成り立たない | 設計の作り直し | 選択層を正規カタログ層から分けてあるので、木だけを作り直せる。5.1 の Q-01 で早期に確認 |
| K-09 | 手数の少なさを優先して、精度の検証が後回しになる | 使いやすいが信頼できない結果 | 手数の指標と精度の指標を必ず対で報告する（5.4） |
| K-10 | 選択木の作り直しで ID が変わり、過去の選択記録が解決できなくなる | 再計算の不能 | 意味を持たない安定ID、版の固定、`merged_into`（R-19、R-20） |
| K-11 | 検索キーに第三者のコード・商標・製品名が入る | 権利上の問題 | `rights_note` を必須にし、権利未確認の語は登録しない |
| K-12 | 絞り込みの優先順位付けが、ばらつきの区分が `UNKNOWN` のままでは機能しない | どの行も「要絞り込み」になる | 係数データを得るまでは、排出量の割合だけで並べる。その旨を明示する |

### 6.2 してはならないこと

1. J-CAT の分類表・コード表・原単位・更新周期・修繕率・漏洩率・工事分倍率などを、記憶からも含めて再現しない。選択木・材料族・束・検索キー・ID のいずれにも使わない。
2. 分類表・集計表のシート構成を、そのまま分類体系として写さない。
3. 規格・基準の本文を写さない。
4. カタログの表に、係数・年数・率の値を入れない。参照と状態だけを持つ。
5. 欠けた数量・係数・換算パラメータを 0 や推測値で埋めない。欠けたものは欠けたまま記録し、計算を止める。
6. 既定・代表を黙って適用しない。必ず記録し、結果から辿れるようにする。
7. 代表レコードによる結果を、個別仕様による結果と同じ確からしさで示さない。
8. 権限の確認できない材料レコードを、別の材料レコードへ黙って差し替えない。
9. 架空データでの動作確認を、実データへの適合や実用精度の確認と言い換えない。材料の件数や、手数がどれだけ減るかについて、実データなしに数値を述べない。
10. 画面・UI・アプリのコードを作らない。本書の「候補」「事前選択」「並び順」は、解決手順が返すデータの性質を指し、画面の設計ではない。
11. 「J-CAT と同じ分類」「互換」「検証済み」と受け取られる表現を使わない。

---

## 付録A　inputs.json の項目との対応

| inputs.json の項目 | 本設計での供給元 |
|---|---|
| `MATERIAL.material_id`／`EQUIPMENT.equipment_id` | `calc_row.row_id` |
| `MATERIAL.construction_division`／`EQUIPMENT.equipment_trade` | `calc_row.part_id` |
| `MATERIAL.material_class` | `material_item.family_id` |
| `MATERIAL.material_specification`／`EQUIPMENT.equipment_model` | `selection_record.axis_choices`、`calc_row.item_id` |
| `MATERIAL.quantity`／`EQUIPMENT.equipment_quantity` | `calc_row.activity` |
| `MATERIAL.quantity_unit` | `calc_row.activity_unit`（材料族の正規単位） |
| `MATERIAL.quantity_basis` | `selection_record.quantity_basis` |
| `MATERIAL.waste_rate` | `calc_row.waste_rate_ref` |
| `MATERIAL.material_life`／`MATERIAL.refresh_cycles`／`EQUIPMENT.equipment_service_life` | `calc_row.service_life_ref` |
| `MATERIAL.repair_rate`／`EQUIPMENT.equipment_repair_rate` | `calc_row.repair_rate_ref` |
| `MATERIAL.additional_epd_reference` | `param_binding`（`scope_kind = PRODUCT`） |
| `FACTOR.factor_id`／`EQUIPMENT.equipment_factor_id` | `calc_row.factor_ref` |
| `FACTOR.factor_unit` | `material_family.canonical_unit` と一致することを検査 |
| `FACTOR.factor_stages`／`FACTOR.factor_boundary` | パラメータ台帳側。束の段階の混在の検査に使う |
| `FACTOR.factor_license` | `param_binding.license_status`、`calc_row.param_states` |
| `TRANSPORT.transported_mass` | `calc_row.activity` × `mass_per_unit_ref` |
| `END_OF_LIFE.waste_treatment_route`・`waste_recycle_fraction`・`waste_reuse_fraction`・`eol_factor_ids` | `calc_row.eol_route_ref` |
| `PROVENANCE.source_type`・`license_status`・`data_quality` | `calc_row.activity_state`、`param_states`、`representativeness` |
| `PROVENANCE.user_override_reason` | `selection_record.overrides[].reason` |
| `PROJECT.structure_type`・`building_use`・`design_stage` | `project_context` |
| `MATERIAL.reinforcement_quantity`・`steel_quantity`・`concrete_volume`・`timber_quantity`・`envelope_area`・`interior_area` | 束・出発点セットの基準数量として使える候補（対応は未検討） |

## 付録B　本書で確認していないこと

- 実在の材料データへの適合（データ未入手）。
- 手数が実際に減るかどうか（測定未実施）。
- 代表レコード・既定・束の構成比を使ったときの精度（係数データ・実建物データとも未入手）。
- 統一計算行との項目の一致（計算研究の確定待ち）。
- 他の提案との整合（独立に作成）。
