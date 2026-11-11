# 材料分類の設計案（分類体系先行型）

- 状態：`DESIGN_DRAFT`（設計草案。実データによる検証は一切行っていない）
- 作成日：2026-11-11
- 位置づけ：指示書第7章「次段階：材料データの分類」に向けた構造調査（第6章の資源配分 10％）のうち、独立に作成した設計案の一つ。本案の観点は「先に分類体系（階層・軸・ID規則）を決め、名称違い・類似・単位違い・重複の整理はその体系に対する対応付けとして行う」こと。
- 対象外：UI、画面、アプリのコード。本書はデータ構造と手順の設計だけを扱う。

## 0. 前提と、分かっていないこと

| 項目 | 状態 |
|---|---|
| 実在の材料データセット（品目一覧・単位・係数） | **未入手**。品目が何件あるか、本設計が実データにどの程度適合するかは何も言えない |
| 実建物の数量内訳書・設備機器表 | 未入手 |
| J-CAT の分類表・コード表・原単位・更新周期・修繕率など | 他の算定ツールへの流用は禁止（第1章）。本書は参照も再現もしていない |
| 分類表・集計表ワークブック | `02_SOURCES/ALL_198_SHEETS.json` でシート名だけが見える。内容は未確認（`NOT_VERIFIED`）。シート名から読み取れるのは「建築と設備職種ごとに表が分かれているらしい」「職種をまたぐ表がありうる」という程度で、本設計はその内容に依拠していない |
| 本書の分類名（グループ名・部位名・材料系統名） | 一般的な建築用語から本案の作成者が選んだ暫定案。いずれの既存分類表の写しでもない |
| 本書の例示レコード | すべて架空のプレースホルダ。係数・密度・耐用年数などの値は含めていない |

既存資料との関係：`03_INPUTS/inputs.json` の `MATERIAL.construction_division`（工種）、`MATERIAL.material_class`（資材の分類）、`EQUIPMENT.equipment_trade`、`EQUIPMENT.equipment_model`、`MATERIAL.material_id`、`EQUIPMENT.equipment_id` は、`06_LINEAGE/links.json` でどの概念式にも未接続（`NOT_YET_LINKED`）である。本設計はこれらに「検索結合のキー」と「集計のキー」という役割を与える（付録A）。

---

## 1. 設計目標と、解決する問題

### 1.1 設計目標

| ID | 目標 | 判定方法（実データ入手後） |
|---|---|---|
| G1 | 1つの階層は1つの分類原理だけを持つ（部位と物質を同じ階層に混ぜない） | 各ノードの定義文が、その階層の原理だけで書けること |
| G2 | 同じ品目は体系の中に1回だけ存在する（どの部位で使っても同じ品目レコード） | 仕様の指紋（`spec_fingerprint`）が重複しないこと |
| G3 | 部位別の集計と品目別の集計が、どちらも全行をちょうど1回ずつ数える | Σ（部位グループ別。未配置の別掲分を含む）＝ Σ（系統別）＝ 合計 |
| G4 | 分類の移動・統合・分割があっても、過去の案件データの参照が壊れない | ID が不変であること、変更履歴から復元できること |
| G5 | 少ない選択回数で品目を一意に指定できる | 選択回数の分布（5.7 の数え方） |
| G6 | 建築材料と設備機器を同じ構造で扱う | 設備専用のテーブルを別に作らずに表現できること |
| G7 | 係数・耐用年数などの値を分類体系に埋め込まない（権利と版の管理を分離する） | 分類テーブルに数値の係数列が無いこと |

### 1.2 解決する問題

| 問題 | 本設計での扱い |
|---|---|
| 分類が「部位」なのか「材料の種類」なのか曖昧になる | 2つの独立した軸（部位軸・品目軸）に分け、対応表（配置）でつなぐ |
| 同じ材料が複数の部位で使われ、部位ごとに重複登録される | 品目は品目軸に1回だけ登録し、部位との関係は配置レコードを増やして表す |
| 名称違い | 別名辞書（`alias`）を品目・仕様・部位ノードに付ける。正規化規則は 5.3 |
| 類似材料 | 「同じ品種の仕様違い」と「別の品種だが類似」を区別する。前者は同じ品種の下の別仕様、後者は類似リンク。自動統合はしない |
| 単位違い | 品種ごとに基準単位を1つ決め、仕様ごとに使える単位と換算規則を持つ。換算できない単位は使用不可とする |
| 重複データ | 取込原票を消さずに残し、仕様への対応付け（`record_mapping`）で重複の種類を記録する |
| 分類の深さが増えて選択が長くなる | 厚さ・強度・容量などは階層にせず仕様のパラメータにする。階層は固定で 3＋3 段 |
| 設備が建築材料と別体系になり、配管や保温材のような共通品目が二重になる | 設備も同じ2軸で表す。職種は部位軸、機器・配管の種類は品目軸に置く |

---

## 2. 分類体系の全体像

### 2.1 2軸・各3階層

1本の木（例：部位 → 工種 → 材料 → 仕様）にすると、複数の部位で使う材料が部位ごとに枝分かれして重複する。本案は次の2軸に分ける。

```
部位軸（どこで・何の役割で使うか）        品目軸（それが何であるか）
 F1 区分     division                    I1 系統  family
  └ F2 グループ group                     └ I2 品種  type
     └ F3 部位要素 element  ──配置──────────  └ I3 仕様  spec
                          placement
```

| 軸 | 階層 | 名称 | 意味（分類原理） | その階層で決まること |
|---|---|---|---|---|
| 部位軸 | F1 | 区分 `DIVISION` | 建物本体か、設備か | 入力グループ（`MATERIAL` か `EQUIPMENT` か） |
| 部位軸 | F2 | グループ `GROUP` | 指示書第7章の分類単位（基礎、躯体、…、搬送設備） | 報告・集計の標準単位 |
| 部位軸 | F3 | 部位要素 `ELEMENT` | 数量を拾い分ける単位（建築は部位、設備は系統） | 配置の受け皿。更新・修繕の前提の参照先 |
| 品目軸 | I1 | 系統 `FAMILY` | 主たる物質、または機器の物理的な種類 | 廃棄時の区分、典型的な数量の次元 |
| 品目軸 | I2 | 品種 `TYPE` | 基準単位と仕様パラメータの定義が共通になる範囲 | 基準単位、パラメータの定義、別名の主な付け先 |
| 品目軸 | I3 | 仕様 `SPEC` | パラメータ値の1組（指定できる最小単位） | 係数との対応、単位換算、重複判定 |

配置（`placement`）は「部位要素 F3 × 品種 I2（必要なら仕様 I3 まで）」の許される組合せを1件ずつ記録する多対多の対応表である。

### 2.2 階層数をこの数にした理由

1. **固定深さ**：すべての末端が同じ深さにある（部位軸は必ず F3、品目軸は必ず I3）。集計・検索・検証の実装が単純になる。細分する意味がない箇所には、通過用の子ノードを1件だけ作る（`is_passthrough = true`）。
2. **階層にしないものを決める**：厚さ、強度区分、口径、容量区分、樹種などは階層にせず、仕様のパラメータ（`parameters`）にする。これらを階層にすると組合せの数だけ枝が増える。
3. **F1 は選択に使わない**：区分は2〜3値しかなく、グループから一意に決まるので、指定操作ではグループから始める。F1 は入力グループと計算経路の切替のために持つ。
4. **この深さが実データに合うかは未検証**：品種の下にさらに細分が必要になる可能性、逆に F3 が不要な可能性がある（7章 Q1）。

### 2.3 指示書の9グループの対応

| 指示書の分類 | F1 `division` | F2 `group` の `code` | 入力グループ | 境界の考え方（暫定） |
|---|---|---|---|---|
| 基礎 | `BUILDING` | `FOUNDATION` | `MATERIAL` | 建物の荷重を地盤へ伝える部分 |
| 躯体 | `BUILDING` | `STRUCTURE` | `MATERIAL` | 基礎より上で荷重を支える部分 |
| 屋根・外壁 | `BUILDING` | `ENVELOPE` | `MATERIAL` | 外気に接する面の非耐力の層（仕上げ・下地・断熱・防水）。屋根と外壁は F3 で分ける |
| 開口部 | `BUILDING` | `OPENINGS` | `MATERIAL` | 窓・扉などの建具 |
| 内装 | `BUILDING` | `INTERIOR` | `MATERIAL` | 室内側の仕上げ・下地・間仕切 |
| 電気設備 | `SERVICES` | `ELECTRICAL` | `EQUIPMENT` | 電力・照明・通信の系統 |
| 空調設備 | `SERVICES` | `HVAC` | `EQUIPMENT` | 熱と空気を扱う系統（換気を含めるかは Q3） |
| 給排水設備 | `SERVICES` | `PLUMBING` | `EQUIPMENT` | 水を扱う系統と衛生器具 |
| 搬送設備 | `SERVICES` | `CONVEYANCE` | `EQUIPMENT` | 人・物を運ぶ設備 |

指示書は「など」としているため、次を**予約枠**として `status = PROPOSED` で用意する。実データで必要性が確認されるまで有効化しない。

| 予約 `code` | 想定 | 備考 |
|---|---|---|
| `EXTERNAL_WORKS` | 外構 | 算定範囲に含めるかは未決定 |
| `TEMPORARY_WORKS` | 仮設（型枠・足場など、建物に残らないもの） | 施工段階の扱いと合わせて決める |
| `OTHER_SERVICES` | 上記4職種に入らない設備 | 防災系などの置き場は Q3 |

「未分類」というグループは作らない。分類できない行は、行の側の状態（`placement_state = UNPLACED`）として明示する（T13）。

### 2.4 F3 部位要素の初期案（暫定・一般用語）

実データと照合していない叩き台である。件数・粒度は変わる前提で、すべて `status = PROPOSED` とする。

| F2 | F3 の初期案（`code`：表示名） |
|---|---|
| `FOUNDATION` | `PILE_GROUNDWORK`：杭・地業／`FOOTING`：基礎本体／`GRADE_BEAM`：基礎梁 |
| `STRUCTURE` | `COLUMN`：柱／`BEAM`：梁／`FLOOR_SLAB`：床／`STRUCTURAL_WALL`：耐力壁／`STAIR`：階段 |
| `ENVELOPE` | `ROOF_COVERING`：屋根仕上・防水／`ROOF_INSULATION`：屋根断熱／`EXT_WALL_FINISH`：外壁仕上／`EXT_WALL_BACKING`：外壁下地／`EXT_WALL_INSULATION`：外壁断熱 |
| `OPENINGS` | `EXT_WINDOW`：外部窓／`EXT_DOOR`：外部扉／`INT_DOOR`：内部建具 |
| `INTERIOR` | `FLOOR_FINISH`：床仕上／`WALL_FINISH`：壁仕上／`CEILING`：天井／`PARTITION`：間仕切 |
| `ELECTRICAL` | `POWER_RECEIVING`：受変電／`WIRING`：幹線・配線／`LIGHTING`：照明／`COMMUNICATION`：通信・弱電／`GENERATION_STORAGE`：発電・蓄電 |
| `HVAC` | `HEAT_SOURCE`：熱源／`AIR_HANDLING`：空調機／`DUCTWORK`：ダクト／`HVAC_PIPING`：配管／`VENTILATION`：換気／`CONTROLS`：自動制御 |
| `PLUMBING` | `WATER_SUPPLY`：給水／`HOT_WATER`：給湯／`DRAINAGE`：排水／`SANITARY_FIXTURES`：衛生器具 |
| `CONVEYANCE` | `ELEVATOR`：エレベーター／`ESCALATOR`：エスカレーター／`OTHER_CONVEYANCE`：その他搬送 |

### 2.5 I1 系統の初期案（暫定・一般用語）

| `code` | 表示名 | 主に含む `item_kind` |
|---|---|---|
| `CEMENTITIOUS` | コンクリート・セメント系 | `BULK_MATERIAL` |
| `FERROUS_METAL` | 鉄鋼 | `BULK_MATERIAL` |
| `NONFERROUS_METAL` | 非鉄金属 | `BULK_MATERIAL` |
| `TIMBER` | 木材・木質材料 | `BULK_MATERIAL` |
| `MASONRY_CERAMIC` | 組積・窯業系 | `BULK_MATERIAL` |
| `STONE_AGGREGATE` | 石材・骨材・土 | `BULK_MATERIAL` |
| `GLASS` | ガラス | `BULK_MATERIAL` |
| `BOARD_PANEL` | ボード・パネル | `BULK_MATERIAL` |
| `INSULATION` | 断熱・保温材 | `BULK_MATERIAL` |
| `MEMBRANE_SEALANT` | 防水・シーリング | `BULK_MATERIAL` |
| `COATING_FINISH` | 塗料・仕上塗材 | `BULK_MATERIAL` |
| `POLYMER` | 樹脂・プラスチック | `BULK_MATERIAL` |
| `FITTINGS_HARDWARE` | 建具・金物などの成形品 | `FORMED_PRODUCT` |
| `MACHINE_UNIT` | 機器本体（台数で数える機械・装置） | `EQUIPMENT_UNIT` |
| `TERMINAL_FIXTURE` | 器具・端末（照明器具・衛生器具・吹出口など） | `EQUIPMENT_UNIT` |
| `PANEL_CONTROL` | 盤・制御機器 | `EQUIPMENT_UNIT` |
| `DISTRIBUTION_LINE` | 配管・ダクト・配線（長さで数える） | `DISTRIBUTION_LINE` |
| `COMPOSITE_ASSEMBLY` | 複合品（複数の品目を決まった構成で含むもの） | `ASSEMBLY` |

### 2.6 設備職種の位置づけ

- 職種（電気・空調・給排水・搬送）は**部位軸**の F2 グループとして、建築の5グループと同じ階層に並べる。違いは F1 区分が `SERVICES` であることだけで、テーブルは共通である。
- 機器・配管・配線は**品目軸**に置く。品目軸の系統は職種で分けず、物理的な種類（機器本体、器具・端末、盤・制御、配管・ダクト・配線）で分ける。理由：ポンプ、配管、保温材、ケーブルなどは複数の職種で使われうるため、職種で分けると同じ品目が職種の数だけ重複する。
- 職種をまたぐ品目は、建築材料が複数の部位で使われる場合と同じ仕組み（配置を複数持つ）で表す。
- 設備の中で使われる建築材料（例：ダクトの保温材）は、品目軸では建築材料と同じ品種を使い、配置だけを設備側の部位要素に追加する。
- 機器の仕様パラメータは容量区分・口径などとし、品種の `spec_parameters` で定義する。
- 冷媒など他の入力グループと連動する品種は `linked_input_groups`（例：`["REFRIGERANT"]`）で連動先を示す。値は持たない。
- 職種で分けるべきか物理的な種類で分けるべきかは、実データで「同じ機器が職種ごとに別の係数で提供されているか」を見ないと決められない（Q4）。

### 2.7 複数の部位で使う材料の扱い（機能による分類と物質による分類）

結論：**同一性は品目軸で決め、使われ方は部位軸で決める。両方を持ち、どちらか一方に寄せない。**

| 規則 | 内容 |
|---|---|
| D1 | 品目（品種・仕様）は品目軸にちょうど1回だけ登録する。部位が違うことを理由に品種・仕様を複製しない |
| D2 | 部位との関係は配置で表す。1つの品種は0件以上の配置を持てる。有効な配置のうち1件だけを `is_primary = true` とする（名称検索から入ったときの既定の部位） |
| D3 | 数量の1行は、仕様を1つ、配置を高々1つだけ参照する。1行を複数の部位に自動で按分しない。複数の部位にまたがる数量は、数量を分けた複数行にする |
| D4 | 部位によって値が変わる前提（更新・修繕の前提など）は配置の側に参照を持つ。物質で決まる前提（製造段階の係数、質量換算、廃棄時の区分）は品目の側に持つ（2.8） |
| D5 | あるデータ源が「同じ物質を部位別に別レコード・別の値」で提供している場合、勝手に統合しない。差の理由（算定境界・含まれる工程の違いなど）が出典で確認できるときだけ、係数対応に配置の限定（`factor_link.placement_id`）を付けて同一仕様の下に残す。確認できないときは `UNRESOLVED` として人の判断に回す |
| D6 | 複合品は品目軸の `COMPOSITE_ASSEMBLY` に1件として登録し、構成表（`assembly_component`）で単一物質の仕様に展開できるようにする。部位別集計は複合品の配置で、物質別集計は展開後の構成品で行い、展開元の行と構成品の行を二重に数えない。構成量が得られず展開できない複合品は、品目別集計では `COMPOSITE_ASSEMBLY` にそのまま計上する |

### 2.8 属性をどちらの軸に持たせるか

| 属性 | 持たせる場所 | 理由 |
|---|---|---|
| 製造段階の係数との対応 | 仕様（`factor_link`） | 物質と仕様で決まる |
| 基準単位、単位換算、質量への換算 | 品種・仕様 | 物質の性質で決まる。輸送質量の算出にも使う |
| 廃棄時の区分（`eol_stream`） | 品種 | 物質で決まる |
| 生物由来炭素の対象かどうか | 品種 | 物質で決まる |
| 更新・修繕の前提の参照 | 配置（無ければ部位要素） | 同じ物質でも使う部位で変わりうる。値は分類体系に持たず、参照IDだけを持つ |
| その部位でよく使う単位、既定の仕様 | 配置 | 使い方で決まる |
| 報告・集計の区分 | 部位グループ（F2）と系統（I1） | 2通りの集計を両立させる |

「更新・修繕の前提が部位で決まるのか、品目で決まるのか、両方か」は実データを見ないと確定できない（Q5）。上表はそのどれにも対応できるよう、参照の探索順（行の明示値 → 配置 → 部位要素 → 無し）を定めるにとどめる。

---

## 3. データ構造（フィールド表）

共通の約束：
- 型の表記：`string` / `integer` / `number` / `boolean` / `date` / `enum` / `array<T>` / `object` / `T|null`。
- 「必須」欄：○＝必須、△＝条件付き必須（条件を意味欄に記載）、−＝任意。
- すべてのテーブルは T0 の共通列を持つ（表では繰り返さない）。
- 本書で「有効なレコード」とは、`status` が `DEPRECATED` でないもの（`PROPOSED` と `ACTIVE`）を指す。
- 排出係数・耐用年数・修繕率・構成量を置く列は、どのテーブルにも無い（参照IDだけを持つ）。数値を持つのは、仕様を区別するパラメータ（厚さなど）と、単位の定義で決まる換算係数（kg と t など）だけである。密度のような物性値は、出所を示せる場合に限り仕様のパラメータまたは外部台帳に置く。

### T0 共通列

| 名前 | 型 | 必須 | 意味 |
|---|---|---|---|
| `status` | enum | ○ | `PROPOSED` / `ACTIVE` / `DEPRECATED` |
| `valid_from_version` | string | ○ | このレコードが追加された分類体系の版 |
| `valid_to_version` | string\|null | − | 廃止された版。有効な間は null |
| `replaced_by` | `array<string>` | − | 廃止時の後継ID（統合は1件、分割は複数件、単純廃止は空） |
| `evidence_level` | enum | ○ | `OBSERVED` / `SAMPLED` / `INFERRED` / `NOT_VERIFIED` / `RESTRICTED`（第7章 7.5 の語彙）。現時点の全レコードは `INFERRED` |
| `license_status` | enum | ○ | `PERMITTED_PUBLIC` / `PERMISSION_REQUIRED` / `RESTRICTED` / `UNKNOWN`（第1章 1-E の語彙） |
| `note_ja` | string | − | 補足 |

### T1 `taxonomy_release`（分類体系の版）

| 名前 | 型 | 必須 | 意味 |
|---|---|---|---|
| `taxonomy_version` | string | ○ | 版。`MAJOR.MINOR.PATCH` 形式（4.3） |
| `released_at` | date | ○ | 公開日 |
| `release_status` | enum | ○ | `DRAFT` / `ACTIVE` / `SUPERSEDED` |
| `previous_version` | string\|null | ○ | 直前の版 |
| `change_summary_ja` | string | ○ | 変更の要約 |

### T2 `function_node`（部位軸のノード：F1〜F3）

| 名前 | 型 | 必須 | 意味 |
|---|---|---|---|
| `node_id` | string | ○ | 不変ID。`FN` ＋ 6桁以上の数字 |
| `level` | integer | ○ | 1〜3 |
| `level_kind` | enum | ○ | `DIVISION` / `GROUP` / `ELEMENT`（`level` と一致） |
| `parent_id` | string\|null | ○ | 親の `node_id`。F1 は null |
| `code` | string | △ | 英大文字の符号。F1・F2 は必須で、有効化後は変更禁止。F3 は任意 |
| `label_ja` | string | ○ | 表示名 |
| `definition_ja` | string | ○ | このノードに入るものの定義を1〜2文で書く |
| `includes_ja` | `array<string>` | − | 境界上で「含む」と決めたもの |
| `excludes_ja` | `array<string>` | − | 境界上で「含まない」と決めたものと、その行き先 |
| `input_group` | enum\|null | △ | `MATERIAL` / `EQUIPMENT`。F2 で必須。配下は継承 |
| `is_passthrough` | boolean | ○ | 固定深さを保つためだけの通過ノードなら true |
| `lifecycle_profile_ref` | string\|null | − | 更新・修繕の前提を収めた外部台帳のID。F3 のみ。値そのものは持たない |
| `sort_key` | integer | ○ | 兄弟の中の並び順（IDとは独立） |

### T3 `item_node`（品目軸のノード：I1 系統・I2 品種）

| 名前 | 型 | 必須 | 意味 |
|---|---|---|---|
| `node_id` | string | ○ | 不変ID。`IN` ＋ 6桁以上の数字 |
| `level` | integer | ○ | 1（系統）または 2（品種） |
| `level_kind` | enum | ○ | `FAMILY` / `TYPE` |
| `parent_id` | string\|null | ○ | 品種は系統の `node_id`。系統は null |
| `code` | string | △ | 系統は必須。品種は任意 |
| `label_ja` | string | ○ | 正式表示名（別名は T6） |
| `definition_ja` | string | ○ | 定義 |
| `item_kind` | enum | △ | 品種で必須。`BULK_MATERIAL` / `FORMED_PRODUCT` / `EQUIPMENT_UNIT` / `DISTRIBUTION_LINE` / `ASSEMBLY` |
| `canonical_dimension` | enum | △ | 品種で必須。`MASS` / `VOLUME` / `AREA` / `LENGTH` / `COUNT` |
| `canonical_unit` | enum | △ | 品種で必須。`kg` / `t` / `m3` / `m2` / `m` / `unit` |
| `spec_parameters` | `array<object>` | △ | 品種で必須（空配列可）。仕様を区別するパラメータの定義（T3a） |
| `eol_stream` | enum\|null | − | 廃棄時の区分。`MINERAL` / `METAL` / `WOOD` / `PLASTIC` / `GLASS` / `MIXED` / `EQUIPMENT` / `UNKNOWN` |
| `biogenic_flag` | boolean\|null | − | 生物由来炭素の対象かどうか。不明は null |
| `linked_input_groups` | `array<enum>` | − | 連動する入力グループ（例 `REFRIGERANT`） |
| `calc_class` | string\|null | − | 評価プロトコル P8 の M4（材料などをパラメータ化した共通近似モデル）で使う区分キーの置き場。現時点では未定義（null） |
| `sort_key` | integer | ○ | 並び順 |

#### T3a `spec_parameters` の1要素

| 名前 | 型 | 必須 | 意味 |
|---|---|---|---|
| `key` | string | ○ | パラメータ名（英小文字と下線、単位付き。例 `thickness_mm`） |
| `label_ja` | string | ○ | 表示名 |
| `value_type` | enum | ○ | `number` / `enum` / `string` / `boolean` |
| `unit` | string\|null | ○ | 数値の単位。無次元・非数値は null |
| `required` | boolean | ○ | 仕様の登録に必須か |
| `allowed_values` | array\|null | − | `enum` の許容値 |
| `affects_conversion` | boolean | ○ | 単位換算に使うか（厚さ・単位質量など） |
| `affects_factor` | boolean\|null | ○ | 係数が変わると見込むか。実データを見るまで null |

### T4 `item_spec`（I3 仕様：指定できる最小単位）

| 名前 | 型 | 必須 | 意味 |
|---|---|---|---|
| `spec_id` | string | ○ | 不変ID。`SP` ＋ 6桁以上の数字 |
| `type_id` | string | ○ | 品種（T3、`level_kind = TYPE`）の `node_id` |
| `label_ja` | string | ○ | 表示名。品種名とパラメータ値から規則で生成する |
| `parameters` | object | ○ | `key` → 値。品種の `spec_parameters` に従う。パラメータが無ければ空 |
| `is_generic` | boolean | ○ | 一般品（代表仕様）なら true、特定製品なら false |
| `product_key` | string\|null | △ | `is_generic = false` のとき必須。製品を識別する文字列（出典の許す範囲で） |
| `spec_fingerprint` | string | ○ | 重複判定用の指紋（4.4 の規則で機械的に生成） |
| `is_default_for_type` | boolean | ○ | 仕様が分からないときの既定候補。品種ごとに高々1件 |
| `allowed_units` | `array<enum>` | ○ | この仕様の数量に使える単位。`canonical_unit` を必ず含む |
| `factor_link_state` | enum | ○ | `NONE` / `LINKED` / `PENDING_LICENSE` / `RESTRICTED` |
| `provenance_ref` | string\|null | − | 根拠資料の参照（`PROVENANCE` グループの記録） |

### T5 `placement`（配置：部位要素と品種の対応）

| 名前 | 型 | 必須 | 意味 |
|---|---|---|---|
| `placement_id` | string | ○ | 不変ID。`PL` ＋ 6桁以上の数字 |
| `element_id` | string | ○ | F3 部位要素の `node_id` |
| `type_id` | string | ○ | 品種の `node_id` |
| `spec_ids` | `array<string>` | ○ | この配置で使える仕様の限定。空配列は「その品種の全仕様」 |
| `is_primary` | boolean | ○ | その品種の既定の配置。有効な配置のうち品種ごとに1件だけ true |
| `role` | enum | ○ | その部位での役割。`MAIN` / `FINISH` / `BACKING` / `INSULATION` / `ACCESSORY` / `EQUIPMENT` / `DISTRIBUTION` |
| `default_unit` | enum\|null | − | その部位でよく使う単位。対象仕様の `allowed_units` に含まれること |
| `default_spec_id` | string\|null | − | この配置での既定仕様。無ければ品種の既定に従う |
| `lifecycle_profile_ref` | string\|null | − | 更新・修繕の前提の参照ID。部位要素の参照より優先。値は持たない |
| `applicability` | object\|null | − | 案件属性による絞り込み条件（例 `{"structure_type": ["TYPE_A"]}`）。キーは `PROJECT` グループの項目 |
| `rank_hint` | integer\|null | − | 候補の並び順。実際の使用頻度が得られるまで null |

一意制約：`(element_id, type_id, role)` が有効レコードの中で一意。

### T5b `factor_link`（仕様と係数の対応。値は持たない）

| 名前 | 型 | 必須 | 意味 |
|---|---|---|---|
| `link_id` | string | ○ | 不変ID。`FL` ＋ 6桁以上の数字 |
| `spec_id` | string | ○ | 対象の仕様 |
| `placement_id` | string\|null | ○ | 規則 D5 による配置の限定。限定が無ければ null |
| `factor_id` | string | ○ | 係数台帳（`FACTOR.factor_id`）のID。係数の値・版・出典・許諾は係数台帳の側で管理する |
| `stage_set` | `array<string>` | ○ | 対応する段階（例 `["A1-A3"]`）。係数台帳の記載と一致すること |
| `denominator_unit` | enum | ○ | 係数の分母単位。仕様の `allowed_units` に含まれること |
| `link_basis` | enum | ○ | `EXACT`（同一品目）／`GENERIC`（一般値）／`PROXY`（代用） |
| `proxy_reason_ja` | string\|null | △ | `PROXY` のとき必須 |

### T6 `alias`（別名辞書）

| 名前 | 型 | 必須 | 意味 |
|---|---|---|---|
| `alias_id` | string | ○ | 不変ID。`AL` ＋ 6桁以上の数字 |
| `alias_text` | string | ○ | 元の表記のまま |
| `normalized_text` | string | ○ | 5.3 の規則で正規化した文字列 |
| `target_kind` | enum | ○ | `FUNCTION_NODE` / `ITEM_NODE` / `ITEM_SPEC` |
| `target_id` | string | ○ | 対象のID |
| `alias_kind` | enum | ○ | `SYNONYM` / `ABBREVIATION` / `SPELLING_VARIANT` / `LEGACY_NAME` / `TRADE_NAME` / `SOURCE_LABEL` |
| `ambiguity` | enum | ○ | `UNIQUE`（正規化後の文字列が1対象だけを指す）／`AMBIGUOUS`（複数を指す）。機械的に再計算する |
| `source_dataset_id` | string\|null | − | `SOURCE_LABEL` のときの出典データセット |

### T7 `unit_conversion`（単位換算の規則）

| 名前 | 型 | 必須 | 意味 |
|---|---|---|---|
| `conversion_id` | string | ○ | 不変ID。`UC` ＋ 6桁以上の数字 |
| `scope_kind` | enum | ○ | `GLOBAL` / `TYPE` / `SPEC` |
| `scope_id` | string\|null | △ | `TYPE`・`SPEC` のとき必須 |
| `from_unit` | enum | ○ | 換算元 |
| `to_unit` | enum | ○ | 換算先 |
| `method` | enum | ○ | `DEFINITIONAL`（定義で決まる。例 kg→t）／`PHYSICAL_PARAMETER`（厚さ・密度などが必要）／`PER_UNIT_MASS`（1個・1mあたり質量が必要）／`NOT_CONVERTIBLE` |
| `parameter_key` | string\|null | △ | `PHYSICAL_PARAMETER`・`PER_UNIT_MASS` のとき必須 |
| `parameter_source` | enum\|null | △ | `SPEC_PARAMETER`（仕様のパラメータから取る）／`REGISTRY_REF`（外部台帳）／`USER_INPUT` |
| `definitional_factor` | number\|null | △ | `DEFINITIONAL` のときだけ値を持つ（単位の定義値に限る）。それ以外は null |
| `verification_state` | enum | ○ | `VERIFIED` / `NOT_VERIFIED` / `BLOCKED_NO_DATA` |

### T8 `source_record`（取込原票。消さない）

| 名前 | 型 | 必須 | 意味 |
|---|---|---|---|
| `source_record_id` | string | ○ | 不変ID。`SR` ＋ 6桁以上の数字 |
| `source_dataset_id` | string | ○ | 出典データセットのID |
| `source_item_key` | string\|null | − | 出典側の品目キー。**許諾が再掲を認めない場合は公開リポジトリに保存しない**（null または非公開保管） |
| `raw_label` | string | △ | 出典の品目名。許諾が再掲を認めない場合は保存しない |
| `raw_unit` | string | ○ | 出典の単位表記 |
| `raw_grouping` | `array<string>` | − | 出典側の見出し・区分（工種別や部位別の見出しなど）。対応付けの手掛かりとしてだけ使う |
| `raw_attributes` | object | − | 出典にあったその他の属性（係数値は入れない） |
| `imported_at` | date | ○ | 取込日 |

### T9 `record_mapping`（取込原票から仕様への対応付け）

| 名前 | 型 | 必須 | 意味 |
|---|---|---|---|
| `mapping_id` | string | ○ | 不変ID。`MP` ＋ 6桁以上の数字 |
| `source_record_id` | string | ○ | 対象の原票 |
| `spec_id` | string\|null | ○ | 対応する仕様。未解決・対象外は null |
| `match_status` | enum | ○ | `NEW_SPEC` / `EXACT_DUPLICATE` / `SAME_SPEC_OTHER_UNIT` / `SAME_SPEC_OTHER_SOURCE` / `NEW_TYPE_REQUIRED` / `UNRESOLVED` / `OUT_OF_SCOPE` |
| `decided_by` | enum | ○ | `RULE`（規則で自動）／`REVIEWER`（人が判断） |
| `decision_reason_ja` | string | ○ | 判断理由 |
| `decided_at` | date | ○ | 判断日 |

### T10 `similarity_link`（類似関係。統合ではない）

| 名前 | 型 | 必須 | 意味 |
|---|---|---|---|
| `link_id` | string | ○ | 不変ID。`SL` ＋ 6桁以上の数字 |
| `from_spec_id` | string | ○ | 起点の仕様 |
| `to_spec_id` | string | ○ | 相手の仕様 |
| `relation` | enum | ○ | `SAME_TYPE_VARIANT`（同じ品種の仕様違い）／`SUBSTITUTABLE`（用途上置き換えうる別品種）／`GENERIC_OF`（一般品と特定製品）／`PROXY_CANDIDATE`（係数の代用候補） |
| `proxy_allowed` | boolean | ○ | 係数の代用を認めるか。既定は false。true にするには根拠が必要 |
| `basis_ja` | string | ○ | 類似と判断した根拠 |

### T11 `assembly_component`（複合品の構成）

| 名前 | 型 | 必須 | 意味 |
|---|---|---|---|
| `component_id` | string | ○ | 不変ID。`AC` ＋ 6桁以上の数字 |
| `assembly_spec_id` | string | ○ | 複合品の仕様（`item_kind = ASSEMBLY`） |
| `component_spec_id` | string | ○ | 構成品の仕様 |
| `basis_unit` | enum | ○ | 複合品側の単位（例 `m2`） |
| `component_unit` | enum | ○ | 構成品側の単位 |
| `quantity_ref` | string\|null | ○ | 複合品1単位あたりの構成量を収めた外部台帳の参照ID。**値は分類体系に持たない**。未入手なら null（その複合品は展開不可） |

### T12 `change_log`（変更履歴）

| 名前 | 型 | 必須 | 意味 |
|---|---|---|---|
| `change_id` | string | ○ | 不変ID。`CH` ＋ 6桁以上の数字 |
| `taxonomy_version` | string | ○ | この変更を含む版 |
| `change_type` | enum | ○ | `ADD` / `RENAME` / `REDEFINE` / `MOVE` / `MERGE` / `SPLIT` / `DEPRECATE` |
| `target_table` | string | ○ | 対象テーブル名 |
| `target_ids` | `array<string>` | ○ | 対象ID |
| `result_ids` | `array<string>` | ○ | 変更後のID（統合・分割で新設したものなど） |
| `before` / `after` | object\|null | − | 変更前後の値 |
| `reason_ja` | string | ○ | 理由 |

### T13 `line_classification`（案件側：数量1行が持つ分類の参照）

分類体系そのものではないが、参照の形を固定するために定義する。

| 名前 | 型 | 必須 | 意味 |
|---|---|---|---|
| `line_id` | string | ○ | 行ID（`MATERIAL.material_id` / `EQUIPMENT.equipment_id` に相当。分類体系とは別の名前空間） |
| `spec_id` | string | ○ | 仕様 |
| `placement_id` | string\|null | ○ | 配置。null は `placement_state = UNPLACED` のときだけ |
| `placement_state` | enum | ○ | `PLACED` / `UNPLACED` |
| `taxonomy_version` | string | ○ | 選択したときの版 |
| `quantity_unit` | enum | ○ | 仕様の `allowed_units` に含まれること |
| `selection_path` | enum | ○ | `TREE` / `ALIAS_SEARCH` / `IMPORT_MAPPING` |
| `defaulted_fields` | `array<string>` | ○ | 既定値をそのまま採用した項目（例 `["spec_id"]`）。既定の採用を追跡可能にする |
| `expanded_from_line_id` | string\|null | − | 複合品の展開で生成された行なら、元の行ID |

`UNPLACED` の行は、部位別集計では「未配置」として別掲し、配置由来の既定の参照（更新・修繕の前提）を一切適用しない。0 として扱うことも、他の部位に寄せることもしない。

### 3.1 整合性制約（実装時に検査として書く）

| ID | 制約 |
|---|---|
| C1 | `function_node`：`level = n` の親は `level = n − 1`。末端は必ず `level = 3` |
| C2 | `item_node`：品種の親は系統。`item_spec.type_id` は品種を指す |
| C3 | `placement.element_id` は `ELEMENT`、`type_id` は `TYPE` を指す。`spec_ids` の各仕様はその品種に属する |
| C4 | 品種ごとに、有効な配置の `is_primary = true` はちょうど1件（配置が0件の品種は除く） |
| C5 | 有効な `item_spec` の中で `spec_fingerprint` は一意 |
| C6 | 品種ごとに `is_default_for_type = true` は高々1件 |
| C7 | `allowed_units` の各単位は、`canonical_unit` への換算規則が T7 にあり、`NOT_CONVERTIBLE` でなく、`verification_state = VERIFIED` であること |
| C8 | `DEPRECATED` のノードは有効な子・有効な配置を持たない |
| C9 | 一度発行したIDは再利用しない。レコードは物理削除しない |
| C10 | `line_classification`：`placement` の品種と `spec` の品種が一致する |
| C11 | `assembly_component` は循環しない |
| C12 | `factor_link.denominator_unit` と `stage_set` は係数台帳の記載と一致する（不一致は計算停止：SYS-02 と同じ扱い） |
| C13 | 部位グループ別の合計（未配置の別掲分を含む）、系統別の合計、全体合計が一致する（展開行は元の行と二重に数えない） |

---

## 4. ID とコードの規則

### 4.1 ID（不変の識別子）

| 規則 | 内容 |
|---|---|
| R1 | 形式は `^[A-Z]{2}[0-9]{6,}$`。先頭2文字はテーブルの接頭辞（`FN` `IN` `SP` `PL` `FL` `AL` `UC` `SR` `MP` `SL` `AC` `CH`）、続く数字は発行順の連番（ゼロ埋め） |
| R2 | ID に意味を持たせない。親ノード、階層、部位、単位、名称、出典側のコードを ID に埋め込まない |
| R3 | 再利用しない。廃止したIDは `DEPRECATED` として残し、`replaced_by` で後継を示す |
| R4 | 連番はテーブルごとに単調増加。欠番があってよい。振り直しをしない |
| R5 | 並び順は `sort_key` で持つ。ID の大小に意味を持たせない |
| R6 | ID の比較は文字列の完全一致で行う（桁数が増えても動くようにする） |
| R7 | 出典データセット側のコードを ID として使わない。対応は `source_record.source_item_key` に分離し、許諾が認めない場合は公開しない |
| R8 | 検査桁は付けない（ID は選択で入るもので、手入力を想定しない）。手入力が必要になった時点で再検討する（Q9） |

### 4.2 コードとパス（人が読むための符号）

| 規則 | 内容 |
|---|---|
| R9 | `code` は `^[A-Z][A-Z0-9_]{1,31}$`。兄弟の中で一意 |
| R10 | F1・F2 と系統（I1）の `code` は、入力スキーマの enum 値や集計結果の見出しとして使われるため、`ACTIVE` にした後は変更しない。意味を変えたいときは新しいノードを追加する。分類テーブルどうしの参照と案件行からの参照は、この階層でも ID で行う |
| R11 | F3・品種の `code` は任意で、変更してよい。データの参照には必ず ID を使う |
| R12 | 表示用のパス（例 `BUILDING.ENVELOPE.EXT_WALL_INSULATION`）は現在の親子関係から都度生成する。保存してキーに使うことはしない |

### 4.3 版の番号

| 変更 | 版の上げ方 | ID の扱い |
|---|---|---|
| 別名の追加、表示名の誤記修正、並び順の変更、配置の `rank_hint` 変更 | PATCH | 変わらない |
| ノード・仕様・配置の追加、定義文の明確化（所属が変わらない範囲） | MINOR | 既存は変わらない |
| 移動（親の変更） | MINOR | **変わらない**（ID に親を埋め込まないのはこのため） |
| 統合・分割・所属が変わる再定義・廃止 | MAJOR | 対象を `DEPRECATED` にし、新しい ID を発行する |

### 4.4 仕様の指紋 `spec_fingerprint`

次の3部を `|` でつないだ文字列とする。

1. `type_id`
2. パラメータを `key` の昇順に並べ、`key=value` を `;` でつないだもの。数値は品種で定義した単位に直し、末尾の0と不要な小数点を除いた10進表記。enum は大文字。未指定の任意パラメータは書かない
3. `GENERIC` または `PRODUCT:` ＋ `product_key`

例：`IN000021|thickness_mm=50|GENERIC`（パラメータが2つ以上あれば `key1=value1;key2=value2` のように並ぶ）

指紋が同じなら同じ仕様であり、2件目を作らない（C5）。指紋が違うが数値パラメータの差がわずかな組は、自動では統合せず確認対象に挙げる。

---

## 5. 規則と手順

### 5.1 品目軸の判定規則（「それは何か」）

上から順に適用し、最初に当てはまったもので決める。

| 順 | 条件 | 判定 |
|---|---|---|
| I-1 | 複数の品目を決まった構成で含み、1つの単位で数量を拾う | `item_kind = ASSEMBLY`、系統 `COMPOSITE_ASSEMBLY` |
| I-2 | 単体で機能する機械・装置・器具で、台数・個数で数える | `EQUIPMENT_UNIT`。系統は機器本体／器具・端末／盤・制御のいずれか |
| I-3 | 流体・空気・電気・信号を通す線状のもので、長さで数える | `DISTRIBUTION_LINE` |
| I-4 | 工場で形が決まった製品で、個数または面積で数える（建具・金物など） | `FORMED_PRODUCT` |
| I-5 | 上記以外で、質量・体積・面積で数える素材 | `BULK_MATERIAL`。系統は主たる物質で決める |
| I-6 | 主たる物質が出典から判断できない | 推測で決めない。`UNRESOLVED` として確認に回す |

品種の切り方：基準単位が同じで、仕様を区別するパラメータの定義が同じになる範囲を1品種とする。基準の次元が違うもの（例：面積で数える板状品と、体積で数える充填材）は別品種にする。

### 5.2 部位軸の判定規則（「どこで・何の役割で使うか」）

| 順 | 規則 |
|---|---|
| F-1 | 物質や施工する業者ではなく、建物の中で果たす機能で決める |
| F-2 | 区分：建物そのものを構成するなら `BUILDING`、エネルギー・流体・人や物・情報を運ぶ系統の一部なら `SERVICES` |
| F-3 | 多層の構成は層ごとに分け、層それぞれの機能で配置する（例：耐力壁の本体は躯体、その外側の仕上げ層は屋根・外壁） |
| F-4 | 荷重を支える役割と仕上げの役割を兼ねるものは、荷重を支える側に置く |
| F-5 | 設備を支えるための建築工事（機器の基礎など）は、物としての性質に従い `BUILDING` 側に置く（暫定。Q2） |
| F-6 | 上の規則で決まらない境界は、定義文の `includes_ja` / `excludes_ja` に個別の決定を追記して解消する。行ごとの場当たりの判断で済ませない |
| F-7 | 部位が分からない行は `UNPLACED` とし、推測で配置しない |

### 5.3 名称の正規化規則

`normalized_text` は次の順で機械的に作る。元の表記（`alias_text`）は必ず残す。

| 順 | 処理 |
|---|---|
| N-1 | Unicode 互換正規化（全角英数・半角カナ・合成文字の統一） |
| N-2 | 英字を大文字に統一 |
| N-3 | 空白・改行・中点・各種ハイフンの除去 |
| N-4 | 括弧の種類の統一（括弧の中身は残す） |
| N-5 | 長音・促音などの表記ゆれの統一（対象表を別に定める。意味が変わる置換はしない） |
| N-6 | 名称に埋まった寸法・区分の表記（例 `t50`、`厚50`、`50mm`）を切り出し、名称本体から除いてパラメータ候補として別に保持する |
| N-7 | 単位記号の表記ゆれの統一（例 `㎡`・`m^2` → `m2`） |

N-6 の切り出しパターン、N-5 の対象表は、実データの表記を見てから決める。現時点では未定義である。

### 5.4 取込の手順（実データを入手した後）

| 手順 | 作業 | 出力 |
|---|---|---|
| S1 | 許諾の確認。データセットごとに、再掲・改変・公開・比較の可否を記録する。不明なら取り込まない | データセット台帳（`license_status`） |
| S2 | 原票をそのまま `source_record` に入れる（係数値は入れない。許諾が認めない項目は公開側に置かない） | T8 |
| S3 | 5.3 で名称を正規化し、寸法・区分の表記を切り出す | 正規化文字列、パラメータ候補 |
| S4 | **品目軸を先に決める**（5.1）：`item_kind` → 系統 → 品種。既存の品種に当たらなければ `NEW_TYPE_REQUIRED` | 品種の候補 |
| S5 | パラメータ値を確定し、指紋を作る（4.4）。必須パラメータが出典から決まらないときは推測で埋めず、`UNRESOLVED` にする | `spec_fingerprint` |
| S6 | 重複判定（5.5）。既存の仕様があれば対応付け、無ければ仕様を新設 | T4、T9 |
| S7 | 単位の確認（5.5 の U 規則）。換算できない単位は `allowed_units` に入れない | T7 |
| S8 | **部位軸への配置**（5.2）。出典の見出し（`raw_grouping`）は手掛かりにするが、そのまま採用しない。複数の部位で使うものは配置を複数作り、`is_primary` を1件決める | T5 |
| S9 | 別名の登録。出典の表記を `SOURCE_LABEL` として登録し、`ambiguity` を再計算する | T6 |
| S10 | 未解決（`UNRESOLVED`、`NEW_TYPE_REQUIRED`、`AMBIGUOUS`）を確認の一覧に出し、人が判断して理由を記録する | T9 の `decision_reason_ja` |
| S11 | 3.1 の制約をすべて検査し、5.8 の指標を計算する | 検査結果、指標 |
| S12 | 変更履歴を書き、版を上げて公開する | T12、T1 |

品目軸を先に決める理由：同一性（重複かどうか）は品目軸だけで判定でき、部位の情報が欠けた出典（工種別にまとめた内訳など）でも S4〜S7 まで進められるため。

### 5.5 重複・類似・単位違いの判定手順

| 順 | 条件 | `match_status` | 処理 |
|---|---|---|---|
| M-1 | 指紋が一致し、単位も出典も同じ | `EXACT_DUPLICATE` | 既存の仕様に対応付ける。原票は残す |
| M-2 | 指紋が一致し、単位だけが違う | `SAME_SPEC_OTHER_UNIT` | 同じ仕様に対応付け、換算規則が検証済みなら `allowed_units` に追加。未検証なら追加しない |
| M-3 | 指紋が一致し、出典が違う | `SAME_SPEC_OTHER_SOURCE` | 同じ仕様に対応付ける。係数の対応は出典ごとに `factor_link` を分け、どれを使うかは係数台帳の側で決める |
| M-4 | 品種はあるが、指紋が一致する仕様が無い（パラメータ値が違う、またはその品種で最初の仕様） | `NEW_SPEC` | 仕様を新設する。同じ品種に他の仕様があれば `SAME_TYPE_VARIANT` の類似リンクを張る |
| M-5 | 名称は似ているが、品種が同じと確認できない | `UNRESOLVED` | 統合しない。確認に回す |
| M-6 | 品種が存在しない | `NEW_TYPE_REQUIRED` | 品種の追加を提案する（5.6） |
| M-7 | 算定の対象外 | `OUT_OF_SCOPE` | 理由を記録して残す |

単位の規則：

| ID | 規則 |
|---|---|
| U-1 | 品種ごとに基準単位は1つ。次元の違う単位を同じ品種の基準にしない |
| U-2 | 定義で決まる換算（kg と t など）だけを `GLOBAL` に置く |
| U-3 | 厚さ・密度・単位質量が必要な換算は、その値の出所（仕様のパラメータ／外部台帳／利用者の入力）を必ず示す。出所の無い値で換算しない |
| U-4 | 換算規則が無い、または未検証の単位で入力された数量は計算しない（既存方針「資材単位の不一致は計算を停止」に従う） |
| U-5 | 単位が違うだけのレコードを別品目として数えない。逆に、単位が同じでも算定境界が違うものを同一視しない |

### 5.6 分類体系を変更する手順

| 変更 | 手順 |
|---|---|
| 追加 | 定義文と境界（含む・含まない）を書く → 兄弟ノードの定義と重ならないことを確認 → `PROPOSED` で追加 → 実データで使われたら `ACTIVE` |
| 改名 | `label_ja` を変え、旧名を `LEGACY_NAME` の別名として残す。ID は変えない |
| 移動 | `parent_id` を変える。ID は変えない。`change_log` に移動前後の親を記録 |
| 統合 | 残す側を決める（または新設）→ 消える側を `DEPRECATED`、`replaced_by` に後継1件 → 配置・別名・対応付けを後継に付け替える |
| 分割 | 新しいノードを複数作る → 元を `DEPRECATED`、`replaced_by` に全後継 → 既存の案件行は**自動では振り分けない**（どの後継かは行ごとの判断が要る）。未移行の行は旧 ID のまま有効な版に固定して残す |
| 廃止 | `DEPRECATED` にする。物理削除しない |

### 5.7 少ない操作で指定する経路と、操作数の数え方

「1操作」＝候補一覧から1つ選ぶこと、または文字列を1回入力すること。数量の入力は数えない。画面の設計は本書の対象外であり、ここではデータ構造が許す最短の経路だけを定める。

| 経路 | 手順 | 操作数 |
|---|---|---|
| P1 階層から | グループ（F2）→ 部位要素（F3）→ その部位要素の配置に載っている品種 →（既定の仕様で良ければ終わり／違えばパラメータを選ぶ） | 3〜4 |
| P2 名称から | 名称を入力 → 別名辞書で候補を選ぶ →（既定の配置で良ければ終わり／違えば部位要素を選ぶ） | 2〜3 |
| P3 取込から | 取り込んだ行の名称が別名辞書で `UNIQUE` に当たれば自動で対応付け。`AMBIGUOUS` と未登録だけ人が選ぶ | 0〜2 |

既定値を採用した項目は必ず `defaulted_fields` に残す。既定の仕様が排出量を小さく見せる側に偏らないかは、係数データが得られてから確認する（8章）。

設計上の目安として、1回の選択で示す候補数を少数（暫定で12件以下）に抑えたい。この数は一覧性についての経験的な目安であり、実データで確かめた値ではない。

### 5.8 設計の妥当性を測る指標（実データ入手後に計算する）

| ID | 指標 | 何が分かるか |
|---|---|---|
| V1 | 人の確認なしで仕様に対応付いた原票の割合 | 判定規則と別名辞書の網羅性 |
| V2 | 階層ごとの子の数（最大・95パーセンタイル） | 階層数と粒度が適切か |
| V3 | 配置を2件以上持つ品種の割合 | 2軸に分ける必要があったか（0に近ければ1本の木で足りる） |
| V4 | 正規化後の別名が複数の対象を指す割合 | 名称検索の曖昧さ |
| V5 | `EXACT_DUPLICATE`・`SAME_SPEC_*` の割合 | 重複の規模 |
| V6 | 出現した（仕様、単位）の組のうち、検証済みの換算がある割合 | 単位整理の達成度 |
| V7 | 実際の数量内訳の各行を指定するのに要した操作数（中央値・95パーセンタイル・最大） | G5 の達成度 |
| V8 | 2人が独立に同じ原票を分類したときの一致率 | 定義文の明確さ |
| V9 | 新しいデータセットを1つ足したときに必要になった移動・統合・分割の件数 | 体系の安定性 |
| V10 | 部位別合計＝品目別合計＝全体合計（C13） | 二重計上・計上漏れが無いこと（架空データでも試験できる） |

現時点で計算できる指標は無い。V10 だけは架空データで構造の試験ができるが、それは実用上の適合を示すものではない。

---

## 6. 具体例（すべて架空のプレースホルダ）

「架空断熱材Q」「架空ポンプP」「架空断熱材R」と、データセット `DS_FICTIONAL_A`・`DS_FICTIONAL_B` は実在しない。厚さ50・100 と容量区分は説明用に置いた架空のパラメータで、係数・密度・耐用年数・構成量の値は含めていない。数量そのものは既存の入力項目（`MATERIAL.quantity` など）が持つため、例には載せていない。

### 6.1 状況

- 架空断熱材Q は、屋根の断熱、外壁の断熱、ダクトの保温の3か所で使われる。
- 架空ポンプP は、空調の配管系統と給水系統の両方で使われる。
- 2つの架空データセットから、表記と単位が違う原票が5件届いた。
- 品種「架空断熱材Q」「架空ポンプP」は登録済みで、仕様はまだ1件も無い状態から始める。

### 6.2 レコード

```json
{
  "fictional": true,
  "taxonomy_version": "0.1.0",
  "function_node": [
    {"node_id": "FN000001", "level": 1, "level_kind": "DIVISION", "parent_id": null, "code": "BUILDING", "label_ja": "建築", "is_passthrough": false, "status": "PROPOSED"},
    {"node_id": "FN000002", "level": 1, "level_kind": "DIVISION", "parent_id": null, "code": "SERVICES", "label_ja": "設備", "is_passthrough": false, "status": "PROPOSED"},
    {"node_id": "FN000013", "level": 2, "level_kind": "GROUP", "parent_id": "FN000001", "code": "ENVELOPE", "label_ja": "屋根・外壁", "input_group": "MATERIAL", "is_passthrough": false, "status": "PROPOSED"},
    {"node_id": "FN000017", "level": 2, "level_kind": "GROUP", "parent_id": "FN000002", "code": "HVAC", "label_ja": "空調設備", "input_group": "EQUIPMENT", "is_passthrough": false, "status": "PROPOSED"},
    {"node_id": "FN000018", "level": 2, "level_kind": "GROUP", "parent_id": "FN000002", "code": "PLUMBING", "label_ja": "給排水設備", "input_group": "EQUIPMENT", "is_passthrough": false, "status": "PROPOSED"},
    {"node_id": "FN000131", "level": 3, "level_kind": "ELEMENT", "parent_id": "FN000013", "code": "ROOF_INSULATION", "label_ja": "屋根断熱", "is_passthrough": false, "lifecycle_profile_ref": null, "status": "PROPOSED"},
    {"node_id": "FN000132", "level": 3, "level_kind": "ELEMENT", "parent_id": "FN000013", "code": "EXT_WALL_INSULATION", "label_ja": "外壁断熱", "is_passthrough": false, "lifecycle_profile_ref": null, "status": "PROPOSED"},
    {"node_id": "FN000171", "level": 3, "level_kind": "ELEMENT", "parent_id": "FN000017", "code": "DUCTWORK", "label_ja": "ダクト", "is_passthrough": false, "lifecycle_profile_ref": null, "status": "PROPOSED"},
    {"node_id": "FN000172", "level": 3, "level_kind": "ELEMENT", "parent_id": "FN000017", "code": "HVAC_PIPING", "label_ja": "配管", "is_passthrough": false, "lifecycle_profile_ref": null, "status": "PROPOSED"},
    {"node_id": "FN000181", "level": 3, "level_kind": "ELEMENT", "parent_id": "FN000018", "code": "WATER_SUPPLY", "label_ja": "給水", "is_passthrough": false, "lifecycle_profile_ref": null, "status": "PROPOSED"}
  ],
  "item_node": [
    {"node_id": "IN000009", "level": 1, "level_kind": "FAMILY", "parent_id": null, "code": "INSULATION", "label_ja": "断熱・保温材", "status": "PROPOSED"},
    {"node_id": "IN000014", "level": 1, "level_kind": "FAMILY", "parent_id": null, "code": "MACHINE_UNIT", "label_ja": "機器本体", "status": "PROPOSED"},
    {
      "node_id": "IN000021", "level": 2, "level_kind": "TYPE", "parent_id": "IN000009",
      "label_ja": "架空断熱材Q", "item_kind": "BULK_MATERIAL",
      "canonical_dimension": "VOLUME", "canonical_unit": "m3",
      "spec_parameters": [
        {"key": "thickness_mm", "label_ja": "厚さ", "value_type": "number", "unit": "mm", "required": true, "allowed_values": null, "affects_conversion": true, "affects_factor": null}
      ],
      "eol_stream": "UNKNOWN", "biogenic_flag": null, "linked_input_groups": [], "calc_class": null, "status": "PROPOSED"
    },
    {
      "node_id": "IN000031", "level": 2, "level_kind": "TYPE", "parent_id": "IN000014",
      "label_ja": "架空ポンプP", "item_kind": "EQUIPMENT_UNIT",
      "canonical_dimension": "COUNT", "canonical_unit": "unit",
      "spec_parameters": [
        {"key": "capacity_class", "label_ja": "容量区分", "value_type": "enum", "unit": null, "required": true, "allowed_values": ["S", "M", "L"], "affects_conversion": false, "affects_factor": null}
      ],
      "eol_stream": "EQUIPMENT", "biogenic_flag": false, "linked_input_groups": [], "calc_class": null, "status": "PROPOSED"
    }
  ],
  "item_spec": [
    {"spec_id": "SP000001", "type_id": "IN000021", "label_ja": "架空断熱材Q 厚50", "parameters": {"thickness_mm": 50}, "is_generic": true, "product_key": null, "spec_fingerprint": "IN000021|thickness_mm=50|GENERIC", "is_default_for_type": true, "allowed_units": ["m3", "m2"], "factor_link_state": "NONE", "status": "PROPOSED"},
    {"spec_id": "SP000002", "type_id": "IN000021", "label_ja": "架空断熱材Q 厚100", "parameters": {"thickness_mm": 100}, "is_generic": true, "product_key": null, "spec_fingerprint": "IN000021|thickness_mm=100|GENERIC", "is_default_for_type": false, "allowed_units": ["m3", "m2"], "factor_link_state": "NONE", "status": "PROPOSED"},
    {"spec_id": "SP000003", "type_id": "IN000031", "label_ja": "架空ポンプP 容量区分M", "parameters": {"capacity_class": "M"}, "is_generic": true, "product_key": null, "spec_fingerprint": "IN000031|capacity_class=M|GENERIC", "is_default_for_type": true, "allowed_units": ["unit"], "factor_link_state": "NONE", "status": "PROPOSED"}
  ],
  "placement": [
    {"placement_id": "PL000001", "element_id": "FN000131", "type_id": "IN000021", "spec_ids": [], "is_primary": true, "role": "INSULATION", "default_unit": "m2", "default_spec_id": "SP000001", "lifecycle_profile_ref": null, "applicability": null, "rank_hint": null, "status": "PROPOSED"},
    {"placement_id": "PL000002", "element_id": "FN000132", "type_id": "IN000021", "spec_ids": [], "is_primary": false, "role": "INSULATION", "default_unit": "m2", "default_spec_id": "SP000001", "lifecycle_profile_ref": null, "applicability": null, "rank_hint": null, "status": "PROPOSED"},
    {"placement_id": "PL000003", "element_id": "FN000171", "type_id": "IN000021", "spec_ids": ["SP000001"], "is_primary": false, "role": "INSULATION", "default_unit": "m2", "default_spec_id": "SP000001", "lifecycle_profile_ref": null, "applicability": null, "rank_hint": null, "status": "PROPOSED"},
    {"placement_id": "PL000004", "element_id": "FN000172", "type_id": "IN000031", "spec_ids": [], "is_primary": true, "role": "EQUIPMENT", "default_unit": "unit", "default_spec_id": null, "lifecycle_profile_ref": null, "applicability": null, "rank_hint": null, "status": "PROPOSED"},
    {"placement_id": "PL000005", "element_id": "FN000181", "type_id": "IN000031", "spec_ids": [], "is_primary": false, "role": "EQUIPMENT", "default_unit": "unit", "default_spec_id": null, "lifecycle_profile_ref": null, "applicability": null, "rank_hint": null, "status": "PROPOSED"}
  ],
  "alias": [
    {"alias_id": "AL000001", "alias_text": "架空断熱材 Ｑ", "normalized_text": "架空断熱材Q", "target_kind": "ITEM_NODE", "target_id": "IN000021", "alias_kind": "SPELLING_VARIANT", "ambiguity": "UNIQUE"},
    {"alias_id": "AL000002", "alias_text": "ｶｸｳ断熱材Q", "normalized_text": "カクウ断熱材Q", "target_kind": "ITEM_NODE", "target_id": "IN000021", "alias_kind": "SPELLING_VARIANT", "ambiguity": "UNIQUE"},
    {"alias_id": "AL000003", "alias_text": "Q断熱", "normalized_text": "Q断熱", "target_kind": "ITEM_NODE", "target_id": "IN000021", "alias_kind": "ABBREVIATION", "ambiguity": "UNIQUE"},
    {"alias_id": "AL000004", "alias_text": "架空保温材Q", "normalized_text": "架空保温材Q", "target_kind": "ITEM_NODE", "target_id": "IN000021", "alias_kind": "LEGACY_NAME", "ambiguity": "UNIQUE"}
  ],
  "unit_conversion": [
    {"conversion_id": "UC000001", "scope_kind": "GLOBAL", "scope_id": null, "from_unit": "kg", "to_unit": "t", "method": "DEFINITIONAL", "parameter_key": null, "parameter_source": null, "definitional_factor": 0.001, "verification_state": "VERIFIED"},
    {"conversion_id": "UC000002", "scope_kind": "TYPE", "scope_id": "IN000021", "from_unit": "m2", "to_unit": "m3", "method": "PHYSICAL_PARAMETER", "parameter_key": "thickness_mm", "parameter_source": "SPEC_PARAMETER", "definitional_factor": null, "verification_state": "VERIFIED"},
    {"conversion_id": "UC000003", "scope_kind": "TYPE", "scope_id": "IN000021", "from_unit": "m3", "to_unit": "kg", "method": "PHYSICAL_PARAMETER", "parameter_key": "density_kg_per_m3", "parameter_source": "REGISTRY_REF", "definitional_factor": null, "verification_state": "BLOCKED_NO_DATA"}
  ],
  "source_record": [
    {"source_record_id": "SR000001", "source_dataset_id": "DS_FICTIONAL_A", "source_item_key": null, "raw_label": "架空断熱材Q t50", "raw_unit": "㎡", "raw_grouping": ["屋根"], "imported_at": "2026-11-11"},
    {"source_record_id": "SR000002", "source_dataset_id": "DS_FICTIONAL_A", "source_item_key": null, "raw_label": "架空断熱材 Ｑ　50mm", "raw_unit": "m3", "raw_grouping": [], "imported_at": "2026-11-11"},
    {"source_record_id": "SR000003", "source_dataset_id": "DS_FICTIONAL_B", "source_item_key": null, "raw_label": "ｶｸｳ断熱材Q 厚50", "raw_unit": "m2", "raw_grouping": ["外壁"], "imported_at": "2026-11-11"},
    {"source_record_id": "SR000004", "source_dataset_id": "DS_FICTIONAL_B", "source_item_key": null, "raw_label": "架空断熱材Q t100", "raw_unit": "m2", "raw_grouping": ["外壁"], "imported_at": "2026-11-11"},
    {"source_record_id": "SR000005", "source_dataset_id": "DS_FICTIONAL_B", "source_item_key": null, "raw_label": "架空断熱材R t50", "raw_unit": "m2", "raw_grouping": ["外壁"], "imported_at": "2026-11-11"}
  ],
  "record_mapping": [
    {"mapping_id": "MP000001", "source_record_id": "SR000001", "spec_id": "SP000001", "match_status": "NEW_SPEC", "decided_by": "RULE", "decision_reason_ja": "該当する指紋が無いため仕様を新設", "decided_at": "2026-11-11"},
    {"mapping_id": "MP000002", "source_record_id": "SR000002", "spec_id": "SP000001", "match_status": "SAME_SPEC_OTHER_UNIT", "decided_by": "RULE", "decision_reason_ja": "正規化後の名称と厚さが一致し、単位だけが違う", "decided_at": "2026-11-11"},
    {"mapping_id": "MP000003", "source_record_id": "SR000003", "spec_id": "SP000001", "match_status": "SAME_SPEC_OTHER_SOURCE", "decided_by": "REVIEWER", "decision_reason_ja": "半角カナ表記は正規化では一致しないため、人が確認して別名に登録したうえで同一と判断", "decided_at": "2026-11-11"},
    {"mapping_id": "MP000004", "source_record_id": "SR000004", "spec_id": "SP000002", "match_status": "NEW_SPEC", "decided_by": "RULE", "decision_reason_ja": "同じ品種で厚さが違うため別仕様", "decided_at": "2026-11-11"},
    {"mapping_id": "MP000005", "source_record_id": "SR000005", "spec_id": null, "match_status": "UNRESOLVED", "decided_by": "RULE", "decision_reason_ja": "名称は似ているが同じ品種と確認できない。統合しない", "decided_at": "2026-11-11"}
  ],
  "similarity_link": [
    {"link_id": "SL000001", "from_spec_id": "SP000001", "to_spec_id": "SP000002", "relation": "SAME_TYPE_VARIANT", "proxy_allowed": false, "basis_ja": "同じ品種で厚さだけが違う"}
  ],
  "line_classification": [
    {"line_id": "LN-EXAMPLE-001", "spec_id": "SP000001", "placement_id": "PL000002", "placement_state": "PLACED", "taxonomy_version": "0.1.0", "quantity_unit": "m2", "selection_path": "TREE", "defaulted_fields": ["spec_id"], "expanded_from_line_id": null},
    {"line_id": "LN-EXAMPLE-002", "spec_id": "SP000001", "placement_id": "PL000003", "placement_state": "PLACED", "taxonomy_version": "0.1.0", "quantity_unit": "m2", "selection_path": "ALIAS_SEARCH", "defaulted_fields": [], "expanded_from_line_id": null},
    {"line_id": "LN-EXAMPLE-003", "spec_id": "SP000003", "placement_id": "PL000005", "placement_state": "PLACED", "taxonomy_version": "0.1.0", "quantity_unit": "unit", "selection_path": "TREE", "defaulted_fields": ["spec_id"], "expanded_from_line_id": null}
  ]
}
```

（共通列のうち `valid_from_version`、`evidence_level`、`license_status` などは紙面の都合で省略した。実装では全レコードに付ける。）

### 6.3 この例で確かめられること

| 論点 | 例での現れ方 |
|---|---|
| 複数の部位で使う材料 | 架空断熱材Q の品種は `IN000021` の1件だけ。配置が3件（屋根断熱・外壁断熱・ダクト）あり、屋根断熱が `is_primary` |
| 建築材料が設備側でも使われる | `PL000003` は設備（`HVAC` の `DUCTWORK`）への配置だが、品目は建築側と同じレコード |
| 職種をまたぐ機器 | 架空ポンプP は `HVAC_PIPING` と `WATER_SUPPLY` に配置を持つ |
| 名称違い | 原票5件のうち3件が同じ仕様 `SP000001` に集まる。全角・空白・寸法表記の違いは正規化だけで一致し、半角カナ表記は正規化では一致しないので、人が確認して別名に登録している |
| 単位違い | `SR000002` は m3、他は m2。厚さが仕様のパラメータにあるので m2→m3 は換算できる（`UC000002`） |
| 換算できない単位 | m3→kg は密度の値が未入手なので `BLOCKED_NO_DATA`。そのため `allowed_units` に kg は入れていない |
| 類似材料 | 厚100 は同じ品種の別仕様（`SP000002`）。「架空断熱材R」は確認できないので統合せず `UNRESOLVED` |
| 重複 | 原票は5件すべて残り、仕様は2件。重複の種類は `match_status` で追える |
| 操作数 | 行001：屋根・外壁 → 外壁断熱 → 架空断熱材Q →（既定仕様を採用）＝3操作。行002：「Q断熱」と入力 → 候補1件を選ぶ → 部位要素でダクトを選ぶ＝3操作 |
| 集計の整合 | 行001 は部位別では `ENVELOPE`、品目別では `INSULATION` に1回ずつ現れる。行002 は部位別では `HVAC`、品目別では同じ `INSULATION`。行003 は `PLUMBING` と `MACHINE_UNIT`。どちらの集計も3行をちょうど1回ずつ数える |

### 6.4 分割が起きた場合の例

将来「外壁断熱」（`FN000132`）を2つの部位要素に分ける場合：新しい部位要素を2件追加し、`FN000132` を `DEPRECATED`、`replaced_by` に2件を入れ、`change_log` に `SPLIT` を1件書く。行001 は版 `0.1.0` と `PL000002` を参照したまま残り、どちらの後継に移すかを人が決めるまで自動では書き換えない。品目側（`IN000021`、`SP000001`）は何も変わらない。

---

## 7. 未解決事項と、検証に必要な実データ

### 7.1 未解決事項

| ID | 論点 | 現時点の暫定 | 決めるのに必要なもの |
|---|---|---|---|
| Q1 | 階層数（3＋3）は適切か。品種の下にもう1段要るか、F3 は要るか | 3＋3 の固定深さ | V2・V7 を実データで計算 |
| Q2 | グループ境界：基礎と躯体（基礎梁・地下部分・土間）、躯体と屋根・外壁（耐力のある外壁）、開口部と内装（内部建具）、内装と設備（天井に組み込む器具）、設備を支える建築工事 | 5.2 の F-3〜F-5 と 2.3 の境界の考え方 | 実際の数量内訳での境界事例、V8（独立分類の一致率） |
| Q3 | 9グループに入らないもの（外構、仮設、防災系の設備、換気の所属、発電設備の所属） | 予約枠を `PROPOSED` で用意 | 算定範囲の決定、実データでの出現状況 |
| Q4 | 設備の品目軸を物理的な種類で分けるか、職種で分けるか | 物理的な種類 | 設備の品目データが職種別に別の値で提供されているかの確認 |
| Q5 | 更新・修繕の前提は部位で決まるのか、品目で決まるのか、両方か | 参照の探索順だけを定義 | 適法に使える更新・修繕の前提データ |
| Q6 | 複合品の構成量を適法に入手できるか。入手できない複合品をどう扱うか | 展開不可として明示 | 構成情報の出典と許諾 |
| Q7 | 同じ物質が部位別に別の値で提供されるデータ源への対応（規則 D5）で足りるか | `factor_link.placement_id` | そのようなデータ源の実例 |
| Q8 | 既定の仕様をどう選ぶか（頻度が高いもの／保守的なもの） | 未決定 | 仕様ごとの係数の分布と使用頻度 |
| Q9 | ID の桁数・検査桁、公開リポジトリに置ける範囲 | 6桁以上・検査桁なし | 品目の規模、データセットの許諾条件 |
| Q10 | 数量内訳の様式（工種別にまとめたものと部位別にまとめたもの）のどちらが入力として多いか。工種別の見出しから部位を推定してよいか | 見出しは手掛かりにとどめ、決まらなければ `UNPLACED` | 実際の内訳書の様式の調査 |
| Q11 | 共通近似モデル（評価プロトコル P8 の M4）が必要とする材料区分（`calc_class`）は、系統・品種のどちらに対応するか。分類体系の区分と別に持つ必要があるか | 未定義 | 近似・統合研究の結果 |
| Q12 | 既存の入力項目（`MATERIAL.construction_division` など）を、入力ではなく分類からの導出値に変えるか | 付録Aの対応案 | 第8章 G1（スキーマ確定）での判断 |
| Q13 | 分類体系の変更を誰が承認するか | 未決定 | 運用体制 |

### 7.2 必要な実データ

| データ | 用途 | 権利上の条件 |
|---|---|---|
| 再利用・改変・公開の条件が確認できる材料・製品の品目一覧（名称、単位、算定境界の記載があるもの） | V1〜V6、Q1、Q4、Q7 | データセットごとに許諾を確認。J-CAT の分類表・コード表・原単位は使わない |
| 実建物の数量内訳書（建築・設備。様式の違うものを複数） | V7、V8、Q2、Q3、Q10 | 案件の守秘と個人情報の確認。公開リポジトリには置かない |
| 設備の機器表・配管や配線の数量表 | Q4、設備側の F3 の粒度 | 同上 |
| 更新・修繕の前提として適法に使える資料 | Q5 | 出典と許諾の確認 |
| 複合品の構成が分かる資料 | Q6 | 同上 |
| 名称表記の実例（略称・旧称・商品名） | 5.3 の N-5・N-6 の具体化、V4 | 商品名の扱いに注意 |

これらが得られるまで、本設計は「構造として矛盾なく組める」ことしか言えない。

---

## 8. リスクと、してはならないこと

### 8.1 リスク

| リスク | 内容 | 抑え方 |
|---|---|---|
| 実データに合わない | 階層の深さ・粒度・軸の分け方が、実際の品目に合わない可能性がある | すべて `PROPOSED` のまま置き、実データで V1〜V9 を測ってから有効化する。早い段階で固定しない |
| 2軸が過剰設計になる | 複数の部位で使う品種が少なければ、配置テーブルは手間だけ増える | V3 で判定し、少なければ品種に部位を直接持たせる形へ簡略化する |
| 境界の判断がぶれる | 定義文が曖昧だと分類者ごとに結果が変わる | 定義に「含む・含まない」を書き、V8 を測る |
| 二重計上・計上漏れ | 複合品の展開行と元の行、配置の重複、未配置の行の扱い | C13 の検査、`expanded_from_line_id`、未配置の別掲 |
| 既定値による偏り | 既定の仕様や既定の配置が、排出量を小さく見せる側に偏る | `defaulted_fields` で追跡し、係数が得られてから偏りを確認する（指示書第5章「重大な過小評価を生む条件がないこと」） |
| 類似品の誤統合 | 名称が似ているだけで同じ品目として扱ってしまう | 自動統合しない。`UNRESOLVED` に回す。代用は `proxy_allowed` を明示的に true にした場合だけ |
| 単位換算の誤り | 出所の無い密度・厚さで換算してしまう | U-3・U-4。未検証の換算は使えない状態にする |
| 版の違いで過去の結果と比べられなくなる | 統合・分割の後に集計の区分が変わる | 行に版を保存し、変更履歴から旧区分で再集計できるようにする |
| 権利のあるデータの混入 | 取込原票や別名に、再掲できない名称・コードが入る | S1 の許諾確認、`source_item_key`・`raw_label` の非公開保管、`license_status` の必須化 |
| 分類体系に値が入り込む | 便利さのために係数・耐用年数を分類テーブルに書いてしまう | 値の列を作らない（G7）。参照IDだけを持つ |

### 8.2 してはならないこと

1. J-CAT の分類表、コード表、原単位、更新周期、修繕率、その他の値を、記憶からも含めて再現・転記しない。分類表ワークブックのシート名から分類の中身を推測して埋めない。
2. 規格・標準書式の本文を写さない。分類名は一般用語から自分で定める。
3. 出典側のコードを本体系の ID にしない。出典のコード体系をそのまま階層として取り込まない。
4. ID に意味（親、部位、単位、名称）を埋め込まない。ID を再利用・振り直ししない。レコードを物理削除しない。
5. 部位が違うことを理由に、同じ品目を複製しない。
6. 名称が似ているだけの品目を自動で統合しない。類似品の係数を黙って代用しない。
7. 出所の無い値で単位を換算しない。単位が合わない数量を計算に通さない。
8. 分類できない行を、0 として扱ったり、近い部位に寄せたり、黙って除外したりしない。
9. 1行の数量を複数の部位に自動で按分しない。
10. 分割された分類へ、既存の案件行を自動で振り分けない。
11. 架空の例で構造が組めたことを、実データに適合したことの根拠にしない。品目の件数や適合率について、根拠の無い数字を書かない。
12. この段階で UI・画面・アプリのコードを作らない。

---

## 付録A 既存の入力項目との対応案

| 既存の入力項目（inputs.json） | 本設計での対応 | 備考 |
|---|---|---|
| `MATERIAL.material_id` / `EQUIPMENT.equipment_id` | `line_classification.line_id` | 分類体系の ID とは別の名前空間 |
| `MATERIAL.construction_division` | 配置 → 部位要素 → グループの `code` から導出 | 現在は式に未接続。集計キーとしての役割を与える |
| `MATERIAL.material_class` | 仕様 → 品種 → 系統の `code` から導出 | 同上 |
| `MATERIAL.material_specification` | `item_spec.parameters`（構造化）と `label_ja` | 自由記述を、品種ごとに定義したパラメータへ置き換える |
| `MATERIAL.quantity_unit` | `line_classification.quantity_unit`（`allowed_units` で検査） | 概念式 SYS-02（単位整合性検証）の入力 |
| `MATERIAL.concrete_volume` / `reinforcement_quantity` / `steel_quantity` / `timber_quantity` | 品目軸の系統または品種の水準での粗い指定に当たる | 既存の集約入力は、物質で括ったもの（この行）と部位で括ったもの（次の行）が混在している。2軸に分けると、それぞれがどちらの軸のどの水準かを明示できる |
| `MATERIAL.envelope_area` / `interior_area` | 部位軸のグループの水準での粗い指定に当たる | 粗い指定を代表仕様への参照として表すかどうか、代表仕様をどう定めるかは未決定（Q8） |
| `EQUIPMENT.equipment_trade` | 配置 → 部位要素 → グループ（`SERVICES` 配下） | 既存の表記は4職種。搬送設備は `CONVEYANCE` として受ける |
| `EQUIPMENT.equipment_model` | `item_spec`（`is_generic = false` なら `product_key`） | |
| `FACTOR.factor_id` | `factor_link.factor_id` | 値・版・出典・許諾は係数台帳の側 |
| `MATERIAL.material_life` / `repair_rate` / `refresh_cycles`、`EQUIPMENT.equipment_service_life` / `equipment_repair_rate` | 行の明示値が最優先。既定は `lifecycle_profile_ref` の参照先（外部台帳） | 分類体系に値を持たない。J-CAT の値は使わない |
| `END_OF_LIFE.waste_treatment_route` | 品種の `eol_stream` を候補の絞り込みに使う | 経路そのものは行ごとの入力 |
| `TRANSPORT.transported_mass` | 仕様の質量換算（T7）で数量から導出できる場合がある | 換算が未検証なら導出しない |
| `PROVENANCE.*` | 全テーブルの `evidence_level`・`license_status`・`provenance_ref` | |

計算構造との対応：分類テーブルへの結合は評価プロトコル P3 の構造分類でいう `LOOKUP_JOIN`、複合品の展開は `MATRIX_EXPANSION` に当たると考えられる（概念式 A13-02 が関係するが、分類台帳での区分は本書の時点で確認していない）。分類体系の設計は、これらの計算構造の入力の形を決めるものであり、計算式そのものは変えない。

## 付録B 将来の保存場所の案

実データを入手してテーブルを作る段階では、`09_APPROX_STUDY/07_MATERIAL_TAXONOMY/` の下に、テーブルごとに1ファイル（例 `function_node.json`、`item_node.json`、`item_spec.json`、`placement.json`、`alias.json`、`unit_conversion.json`、`change_log.json`）とし、許諾上公開できない `source_record` と出典側キーは公開リポジトリの外に置く。本書の時点ではこれらのファイルは作成していない。
