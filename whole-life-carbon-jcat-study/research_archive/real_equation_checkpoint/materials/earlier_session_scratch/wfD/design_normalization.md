# 材料データ整理の設計案（正規化優先） — 乱れたレコードをきれいなレコードにする仕組み

- 位置づけ：指示書 第7章「次段階：材料データの分類」に向けた **構造調査（資源配分 約10％）** の設計草案。次段階の作業そのものではない。
- 観点：**正規化優先（NORMALIZATION-FIRST）**。分類体系や選択操作の設計より先に、「名称違い・類似材料・単位違い・重複データ」を機械的かつ追跡可能に整理する層を定める。
- 状態：`DESIGN_DRAFT` / `NOT_VERIFIED`。UI・画面・アプリのコードは含まない。データ構造と手順の設計だけである。
- 言語規約：説明文は日本語、JSON のキーと列挙値は英語。

## 0. 前提 — 分かっていること・分かっていないこと

| 区分 | 内容 |
|---|---|
| 分かっていること | 既存の入力仕様草案（`03_INPUTS/inputs.json` の MATERIAL / EQUIPMENT / FACTOR / TRANSPORT / END_OF_LIFE / PROVENANCE）、権限判断の4状態（`01_COMPLIANCE/README.md` 1-E）、概念式 SYS-02（単位整合）・SYS-03（係数権限ゲート）・QA-03（出典ゲート）、分類表・集計表ブックの **シート名だけ**（`02_SOURCES/ALL_198_SHEETS.json`）。 |
| 分かっていないこと | **実在の材料データセットは1件も入手していない。** したがって、材料が何件あるか、名称違いがどの類型でどれだけ起きるか、単位違いがどの程度あるか、本設計が実データにどれだけ合うかは、いずれも不明であり、本書は何も主張しない。 |
| 使っていないもの | J-CAT の分類表・コード表・原単位・耐用年数・修繕率などの中身。記憶からの再現もしていない。本書の区分名は当方が選んだ一般的な建築語彙であり、例のレコードはすべて架空である。 |

シート名のメタデータから読み取れる構造上の示唆（根拠区分 `INFERRED_FROM_SHEET_METADATA`、中身は `NOT_INSPECTED`）は次の5点にとどまる。いずれも推定であり、設計の入力として「可能性を残す」ためだけに使う。

1. 建築と設備（電気・空調・衛生・昇降機に相当する区分）が別々の表になっているらしい → 材料と機器を同じ枠に押し込まず、`record_kind` で分ける。
2. 設備区分ごとにコード表があるらしい → 第三者ツールのコードを当方の識別子に使わない（意味を持たない独自IDにする）。
3. 複合品の表があるらしい → 単一材料と複合品を区別する（`COMPOSITE`）。
4. 配管・配線類の表が独立しているらしい → 長さで数える品目の形態（`LINEAR`）が要る可能性。
5. 価格・価格補正に関する表があるらしい → 金額を活動量とする行があり得る（`CURRENCY` 次元を予約）。

---

## 1. 設計目標と、解決する問題

### 1.1 目標

| ID | 目標 | 判定方法（実データ入手後に測る。現時点では未測定） |
|---|---|---|
| G1 | 同じ材料を指す表記ゆれ（漢字・かな・全角半角・略称）が、1つの正規レコードに決定的に解決される | 同じ入力と同じ版から常に同じ結果が出る（再現性）。自動解決率・曖昧率 |
| G2 | 似ているが同一ではない材料を、**統合せずに**近縁としてまとめられる | 誤統合が0件であること（正解付きペアで確認） |
| G3 | 単位違いは、根拠（密度・厚さなど）と出典が登録されているときだけ換算され、それ以外は計算が止まる | 停止コード別の件数。黙って換算した件数が0 |
| G4 | 重複レコードは、検出根拠・統合判断・統合前の姿が残る形で統合され、取り消せる | 統合イベントから元レコードを復元できる |
| G5 | すべてのレコードが出典とライセンス状態を持ち、**制限付きデータが混入できない** | リリース時の不変条件検査（2.19）が全件合格 |
| G6 | どの版のデータで計算したかを後から特定でき、破壊的変更が区別される | `release_id` と `normalizer_version` で再計算結果が一致 |
| G7 | 将来「少ない操作で材料を指定する」ための土台になる（名称1回の入力、または系列＋仕様値の2段で特定） | 1行の特定に要した操作数の分布 |

### 1.2 問題と対応する仕組み

| 指示書 第7章の問題 | 具体的な症状 | 本設計の仕組み |
|---|---|---|
| 名称違い | 全角／半角、漢字／ひらがな／カタカナ、長音の有無、略称、名称の中に仕様や単位が埋まっている | 文字列正規化 N1〜N9（3.2）、仕様トークンの分離（3.3）、別名表 `alias`（2.8） |
| 類似材料 | 厚さ・径・強度区分だけが違う品目、出典が違うだけの同等品 | 系列 `material_family` と仕様軸（2.5・2.7）、類似グループ `similarity_group`（2.11） |
| 単位違い | 同じ材料が m2 と 枚、m3 と t で現れる。台と基。一式 | 単位辞書（2.9）、換算表 `unit_conversion`（2.10）、停止コード（3.10） |
| 重複データ | 同じ行の二重登録、表記違いの同一品、出典違いの同一品 | 重複水準 D0〜D4 と統合イベント `merge_event`（2.12、3.7） |
| 少ない操作での指定 | 候補が多すぎて選べない | 名称→系列→仕様値の決定的な解決手順 `resolve`（3.10） |
| 権利 | 制限付きの名称一覧・換算値が混ざる | 出典台帳とライセンス関門（2.3、3.1）、隔離ログ（2.16） |

### 1.3 設計原則

1. **受領した姿は書き換えない。** 受領レコードは追記専用で保存し、正規化結果は必ず再生成できる派生物とする。
2. **誤統合は取りこぼしより悪い。** 統合漏れは操作が1回増えるだけだが、誤統合は計算結果を黙って変える。迷ったら統合しない。自動統合は「正規化後に同一性キーが完全一致する場合」だけに限る。
3. **数値は統合しない。** 係数・換算根拠などの数値は、平均・代表値の選択・上書きによって1つにまとめない。出典ごとに別の行として残す。
4. **不明は不明のまま止める。** 換算根拠の欠損を 0 や 1 で補わない（`RULES.json` R08「unknown is not zero」）。
5. **ライセンスは最も厳しいものが伝わる。** 派生レコードのライセンス状態は、寄与したすべての出典のうち最も制限の強い状態とする。
6. **識別子に意味を持たせない。** 分類・名称・出典を識別子に埋め込まず、一度発行した識別子は再利用しない。
7. **この表群には係数値を置かない。** 排出係数・耐用年数・修繕率・漏洩率・倍率の列は存在させない。係数は別管理の登録簿を `factor_id` で参照するだけである。
8. **部位区分は材料の属性ではなく使われ方の属性とする（提案）。** 同じ材料が基礎にも躯体にも使われるため、部位を同一性に含めると重複が増える。妥当性は実データで要確認（5章 Q4）。

### 1.4 既存資料との接続

| 既存項目（inputs.json 等） | 本設計での対応 | 備考 |
|---|---|---|
| `MATERIAL.material_id`（材料行ID） | 案件内の行ID。本設計の `canonical_id`（カタログ側の識別子）とは別物 | 名前が紛らわしい。行が `canonical_id` を参照する形を提案（5章 Q9） |
| `MATERIAL.construction_division` / `EQUIPMENT.equipment_trade` | `usage_link.element_group`（2.17） | 同一性キーには含めない |
| `MATERIAL.material_class` | `material_family.substance_class` | 語彙は当方の暫定案 |
| `MATERIAL.material_specification` / `EQUIPMENT.equipment_model` | `material_attribute_value`（構造化した仕様） | 自由記述を仕様トークンに分解 |
| `MATERIAL.quantity_unit` | `unit_def.unit_code`（`unit_alias` 経由） | |
| `FACTOR.factor_id` / `factor_unit` / `factor_stages` / `factor_license` | `factor_binding`（参照のみ、値なし） | SYS-02・SYS-03・QA-03 の検査対象 |
| `TRANSPORT.transported_mass`、`END_OF_LIFE.*` の質量 | `canonical_material.mass_path_status` | 宣言単位が質量でない材料は質量への換算経路が要る |
| `PROVENANCE.license_status` / `source_type` / `source_reference` / `last_verified_at` | `source`、`provenance_link` | 4状態の語彙をそのまま使う |
| `MATERIAL.material_life` / `repair_rate` / `refresh_cycles` | **持たない** | R03 の対象になり得る値。本表群の対象外 |

---

## 2. データ構造

### 2.1 全体像

```
[出典台帳 source] --関門--> [受領レコード raw_record] --正規化--> [正規化結果 normalized_record]
        |                                                               |
        | (不許可は中身を保存せず quarantine_log のみ)                   v
        |                                         [別名 alias] --> [系列 material_family]
        |                                                               |  仕様軸の値
        v                                                               v
[来歴 provenance_link] <------------------------------------- [正規材料 canonical_material]
                                                                |        |         |
                                             [単位換算 unit_conversion]  |   [係数参照 factor_binding]
                                             [単位辞書 unit_def/alias]   |   [使われ方 usage_link]
                                                                        v
                              [重複候補 duplicate_candidate] -> [統合イベント merge_event]
                              [類似グループ similarity_group / similarity_member / distinct_pair]
                              [版 release / 変更記録 change_log / 課題 normalization_issue]
```

階層は3段である。

- **系列（`material_family`）**：仕様を除いた材料概念。名称の別名は原則ここに付く。
- **正規材料（`canonical_material`）**：系列＋同一性に効く仕様値。計算で参照する単位。
- **類似グループ（`similarity_group`）**：系列や正規材料をまたぐ近縁関係。統合ではない。

### 2.2 列挙値の語彙

次の JSON が本設計の列挙値の一覧である（構文は python3 で読み込んで確認済み）。`substance_class` と `element_group` は当方が選んだ一般語彙の暫定案で、実データを見てから見直す。

```json
{
  "license_status": ["PERMITTED_PUBLIC", "PERMISSION_REQUIRED", "UNKNOWN", "RESTRICTED"],
  "origin_kind": ["SELF_AUTHORED", "USER_SUPPLIED", "THIRD_PARTY_DATASET", "SYNTHETIC_FICTIONAL"],
  "permitted_use": ["INTERNAL_RESEARCH", "PUBLIC_REDISTRIBUTION", "DERIVATIVE_WORK", "COMMERCIAL_USE", "SAAS_PROVISION"],
  "storage_policy": ["MAY_STORE_IN_PUBLIC_REPO", "PRIVATE_STORE_ONLY", "DO_NOT_INGEST"],
  "content_kind": ["NAMES", "CLASSIFICATION_LABELS", "UNITS", "SPEC_ATTRIBUTES", "CONVERSION_BASIS"],
  "compartment": ["PUBLIC_RELEASE", "PRIVATE_LICENSED"],
  "intake_status": ["ACCEPTED", "DUPLICATE_RAW", "REJECTED_FORMAT"],
  "record_kind": ["MATERIAL", "COMPOSITE", "EQUIPMENT"],
  "form_factor": ["BULK", "SHEET", "LINEAR", "DISCRETE"],
  "substance_class": ["CEMENTITIOUS", "METAL_FERROUS", "METAL_NON_FERROUS", "TIMBER_BASED", "GLASS", "MINERAL_BOARD", "INSULATION", "POLYMER", "CERAMIC_MASONRY", "BITUMINOUS", "COATING", "EARTH_AGGREGATE", "MIXED_ASSEMBLY", "EQUIPMENT_UNIT", "UNSPECIFIED"],
  "record_status": ["DRAFT", "ACTIVE", "DEPRECATED", "MERGED", "QUARANTINED"],
  "declared_unit_basis": ["FACTOR_DENOMINATOR", "SOURCE_DECLARATION", "PROVISIONAL"],
  "mass_path_status": ["DIRECT", "CONVERTIBLE", "BLOCKED_BASIS_MISSING", "NOT_REGISTERED"],
  "attribute_value_type": ["DECIMAL", "ENUM", "TEXT"],
  "attribute_role": ["IDENTITY", "VARIANT_AXIS", "DESCRIPTIVE"],
  "axis_mode": ["ENUMERATED", "CONTINUOUS"],
  "alias_target_level": ["FAMILY", "MATERIAL"],
  "alias_resolution": ["UNIQUE", "AMBIGUOUS"],
  "alias_type": ["CANONICAL_NAME", "SCRIPT_VARIANT", "LONG_VOWEL_VARIANT", "CHARACTER_VARIANT", "ABBREVIATION", "SYNONYM", "GENERIC_TERM", "FOREIGN_NAME", "MISSPELLING", "LEGACY_NAME"],
  "match_strength": ["CANONICAL", "CURATED"],
  "evidence_kind": ["SELF_AUTHORED_GENERIC", "OBSERVED_IN_PERMITTED_SOURCE", "USER_CONFIRMED"],
  "dimension": ["MASS", "VOLUME", "AREA", "LENGTH", "COUNT", "ENERGY", "CURRENCY", "LUMP_SUM"],
  "conversion_kind": ["DENSITY", "THICKNESS", "MASS_PER_AREA", "MASS_PER_LENGTH", "MASS_PER_PIECE", "AREA_PER_PIECE", "LENGTH_PER_PIECE", "COUNT_NOUN_EQUIVALENCE"],
  "basis_origin": ["IDENTITY_ATTRIBUTE", "CURATED_EQUIVALENCE", "EXTERNAL_VALUE"],
  "value_state": ["MISSING", "EXPLICIT_ZERO", "OBSERVED", "USER_ESTIMATE", "LICENSED_DEFAULT", "DERIVED", "SYNTHETIC_FICTIONAL"],
  "conversion_status": ["USABLE", "BLOCKED_BASIS_MISSING", "BLOCKED_LICENSE", "RETIRED"],
  "substitution_policy": ["NONE", "REPRESENTATIVE_ALLOWED_WITH_FLAG"],
  "verification_status": ["NOT_VERIFIED", "VERIFIED_SYNTHETIC_ONLY", "VERIFIED_ANALYTIC_AND_SYNTHETIC"],
  "member_decision": ["SUGGESTED", "CONFIRMED"],
  "distinct_reason": ["DIFFERENT_SUBSTANCE", "DIFFERENT_SPEC", "DIFFERENT_BOUNDARY", "DIFFERENT_UNIT_NO_BASIS", "OTHER"],
  "duplicate_level": ["D0_RAW_EXACT", "D1_IDENTITY", "D2_UNIT_VARIANT", "D3_NEAR", "D4_CROSS_SOURCE"],
  "candidate_state": ["OPEN", "MERGED", "KEPT_DISTINCT", "GROUPED", "BLOCKED"],
  "merge_blocker": ["LICENSE_WOULD_DEGRADE", "COMPARTMENT_MISMATCH", "IDENTITY_ATTRIBUTE_CONFLICT", "CONVERSION_CONFLICT", "KIND_OR_FORM_MISMATCH", "REVIEW_REQUIRED"],
  "merge_event_kind": ["MERGE", "SPLIT"],
  "survivor_rule": ["ACTIVE_OVER_DRAFT", "MORE_COMPLETE_IDENTITY", "OLDER_ID"],
  "field_resolution_rule": ["KEEP_SURVIVOR", "FILL_FROM_MERGED_IF_NULL", "MOVE_TO_ALIAS", "UNION", "MOST_RESTRICTIVE"],
  "derivation": ["COPIED", "NORMALIZED", "PARSED_FROM_TEXT", "CURATED", "MERGED", "COMPUTED"],
  "release_status": ["DRAFT", "PUBLISHED", "WITHDRAWN"],
  "change_kind": ["CREATE", "UPDATE", "MERGE", "SPLIT", "DEPRECATE", "QUARANTINE", "LICENSE_CHANGE"],
  "quarantine_reason": ["LICENSE_RESTRICTED", "LICENSE_UNKNOWN", "PERMISSION_PENDING", "LICENSE_DOWNGRADED", "EVIDENCE_MISSING"],
  "element_group": ["FOUNDATION", "STRUCTURE", "ROOF_AND_EXTERIOR_WALL", "OPENING", "INTERIOR", "ELECTRICAL", "HVAC", "PLUMBING", "CONVEYANCE", "OTHER"],
  "typicality": ["TYPICAL", "POSSIBLE"],
  "issue_code": ["PARSE_INCOMPLETE", "SPEC_UNIT_ASSUMED", "SPEC_ATTRIBUTE_AMBIGUOUS", "UNIT_TEXT_MISSING", "UNIT_UNKNOWN", "ALIAS_UNRESOLVED", "ALIAS_AMBIGUOUS", "IDENTITY_INCOMPLETE", "VARIANT_NOT_REGISTERED"],
  "issue_state": ["OPEN", "RESOLVED", "WONT_FIX"],
  "resolution_status": ["RESOLVED", "STOPPED"],
  "stop_code": ["QUANTITY_MISSING", "UNIT_TEXT_MISSING", "UNIT_UNKNOWN", "LUMP_SUM_UNIT", "ALIAS_UNRESOLVED", "ALIAS_AMBIGUOUS", "VARIANT_UNSPECIFIED", "VARIANT_NOT_REGISTERED", "RECORD_NOT_ACTIVE", "LICENSE_NOT_PERMITTED", "MERGE_REDIRECT_NEEDS_CONFIRMATION", "UNIT_DIMENSION_MISMATCH_NO_PATH", "COUNT_UNIT_NOT_COMPARABLE", "CONVERSION_BASIS_MISSING", "CONVERSION_BASIS_NOT_PERMITTED", "CONVERSION_OUT_OF_APPLICABILITY", "CONVERSION_PATH_CONFLICT", "FACTOR_UNIT_MISMATCH"],
  "warning_code": ["CONVERSION_APPLIED", "COUNT_EQUIVALENCE_APPLIED", "SPEC_UNIT_ASSUMED", "REDIRECTED_BY_MERGE", "REPRESENTATIVE_SUBSTITUTION_APPLIED", "MASS_PATH_UNAVAILABLE"]
}
```

以下の表で「必須」は ○＝必須、△＝条件付き必須、−＝任意。型の `id` は意味を持たない文字列、`enum` は 2.2 の語彙、`decimal` は10進文字列（浮動小数点で持たない）。

### 2.3 `source` — 出典台帳（ライセンス関門の根拠）

| フィールド | 型 | 必須 | 意味 |
|---|---|---|---|
| `source_id` | id（主キー、例 `SRC-0001`） | ○ | 出典の識別子 |
| `title` | string | ○ | 出典の名称 |
| `publisher` | string | △ | 発行者。`origin_kind = THIRD_PARTY_DATASET` のとき必須 |
| `origin_kind` | enum | ○ | 自作／利用者提供／第三者データ／架空 |
| `source_version` | string | ○ | 版・年度 |
| `retrieved_at` | date | ○ | 取得日 |
| `content_kinds` | enum[] | ○ | この出典から取り込む内容の種類（名称、分類ラベル、単位、仕様、換算根拠） |
| `license_status` | enum | ○ | 権限判断の4状態（`01_COMPLIANCE` 1-E と同じ語彙） |
| `license_evidence_ref` | string | △ | 許諾の証拠（規約の所在、書面の管理番号）。`PERMITTED_PUBLIC` のとき必須 |
| `permitted_uses` | enum[] | ○ | 許されている利用形態。空配列は「何も許されていない」 |
| `storage_policy` | enum | ○ | 公開リポジトリに置けるか／非公開保管のみか／取り込み禁止か |
| `license_reviewed_by` / `license_reviewed_at` | string / date | ○ | ライセンスを判断した人と日付 |
| `license_valid_until` | date | − | 再確認期限。過ぎたら `UNKNOWN` として扱う |
| `notes` | string | − | 補足 |

当方自身の命名・整理判断（系列の表示名、人が登録した等価関係など）も、`origin_kind = SELF_AUTHORED` の出典として1件登録する。これにより「来歴の無いレコードは無い」（2.19 I1）を例外なしで検査できる。

### 2.4 `raw_record` と `normalized_record` — 受領した姿と、その正規化結果

`raw_record`（追記専用。更新・削除しない。**係数値の列は持たない**）

| フィールド | 型 | 必須 | 意味 |
|---|---|---|---|
| `raw_id` | id（主キー） | ○ | 受領レコードの識別子 |
| `source_id` | id（→ `source`） | ○ | 出典。`storage_policy` が取り込みを許す出典だけが参照できる |
| `source_locator` | string | ○ | 出典内の位置（ファイル・表・行）。中身ではなく所在 |
| `name_text` | string | ○ | 名称。受領したままの文字列 |
| `spec_text` | string | − | 仕様欄。受領したまま |
| `unit_text` | string | − | 単位欄。受領したまま。無ければ `UNIT_TEXT_MISSING` の課題になる |
| `class_text` | string | − | 出典側の分類ラベル。出典の `content_kinds` に `CLASSIFICATION_LABELS` があるときだけ保存 |
| `content_hash` | string | ○ | `source_id`・名称・仕様・単位・分類ラベルから計算したハッシュ（D0 判定用） |
| `duplicate_of_raw` | id | △ | 同一ハッシュの先行レコード。`intake_status = DUPLICATE_RAW` のとき必須 |
| `occurrence_count` | integer | ○ | 同一内容が出典内に現れた回数 |
| `intake_status` | enum | ○ | 受理／同一行の重複／形式不備 |
| `ingested_in_release` | id（→ `release`） | ○ | 取り込んだ版 |

`normalized_record`（派生物。`raw_record` と `normalizer_version` から再生成できる）

| フィールド | 型 | 必須 | 意味 |
|---|---|---|---|
| `raw_id` | id | ○ | 元の受領レコード（`normalizer_version` と合わせて主キー） |
| `normalizer_version` | string | ○ | 正規化規則の版 |
| `name_key` | string | ○ | 正規化した名称キー（仕様と装飾を除いたもの） |
| `spec_tokens` | object[] | ○ | 取り出した仕様。各要素は `attribute_code`（未確定なら null）、`value`、`unit_code`、`unit_assumed`（真偽）、`matched_text` |
| `decorations` | string[] | ○ | 名称から外した装飾語（注記など） |
| `unit_code` | string | − | 単位欄を解決した結果。解決できなければ null |
| `residual_text` | string | ○ | どの規則でも解釈できずに残った文字列。空でなければ `PARSE_INCOMPLETE` |
| `flags` | enum[] | ○ | `issue_code` のうち該当するもの |
| `resolved_level` / `resolved_id` | enum / id | − | 解決先（系列または正規材料） |

### 2.5 `material_family` — 系列（仕様を除いた材料概念）

| フィールド | 型 | 必須 | 意味 |
|---|---|---|---|
| `family_id` | id（主キー、例 `FAM-0001`） | ○ | 系列の識別子。再利用しない |
| `display_name_ja` | string | ○ | 表示名（当方が付ける一般語彙の名称） |
| `family_name_key` | string | ○ | 表示名の正規化キー |
| `record_kind` | enum | ○ | 材料／複合品／機器 |
| `substance_class` | enum | ○ | 素材の大区分（暫定語彙） |
| `form_factor` | enum | ○ | 形態：かさ物／面材／線材／個物 |
| `default_declared_unit` | string（→ `unit_def`） | ○ | 系列の既定の宣言単位 |
| `status` | enum（`record_status`） | ○ | 状態 |
| `merged_into` | id | △ | 統合先。`status = MERGED` のとき必須 |
| `license_status` | enum | ○ | 来歴から計算した実効ライセンス状態（手入力しない） |
| `compartment` | enum | ○ | 置き場所の区画 |
| `created_in_release` / `retired_in_release` | id / id | ○ / − | 追加した版／退役した版 |
| `record_version` | integer | ○ | 変更のたびに1増える |
| `notes` | string | − | 補足 |

### 2.6 `canonical_material` — 正規材料（計算で参照する単位）

| フィールド | 型 | 必須 | 意味 |
|---|---|---|---|
| `canonical_id` | id（主キー、例 `CM-0001`） | ○ | 正規材料の識別子。意味を持たせず、再利用しない |
| `family_id` | id（→ `material_family`） | ○ | 属する系列 |
| `identity_key` | string | ○ | 同一性キー（3.5）。`ACTIVE` の中で一意 |
| `display_name_ja` | string | ○ | 系列名＋同一性に効く仕様値を固定順で並べて生成した表示名 |
| `declared_unit` | string（→ `unit_def`） | ○ | 宣言単位。この材料の数量を表す基準の単位 |
| `declared_unit_basis` | enum | ○ | 宣言単位の決め方：係数の分母に合わせた／出典の宣言／暫定 |
| `mass_path_status` | enum | ○ | 質量への換算経路の有無（輸送・廃棄段階で必要）。計算で求める。`DIRECT`＝宣言単位が質量、`CONVERTIBLE`＝使える経路がある、`BLOCKED_BASIS_MISSING`＝経路は登録されているが根拠が欠損、`NOT_REGISTERED`＝経路の登録が無い |
| `similarity_group_id` | id | − | 属する類似グループ |
| `status` | enum（`record_status`） | ○ | `ACTIVE` だけが計算で使える |
| `merged_into` | id | △ | 統合先。`status = MERGED` のとき必須 |
| `license_status` | enum | ○ | 実効ライセンス状態（計算で求める） |
| `compartment` | enum | ○ | 区画 |
| `reviewed_by` / `reviewed_at` | string / date | △ | `ACTIVE` にするとき必須 |
| `created_in_release` / `retired_in_release` | id / id | ○ / − | 追加した版／退役した版 |
| `record_version` / `content_hash` | integer / string | ○ | 版番号と内容ハッシュ |

**置いてはいけない列**：排出係数、耐用年数、修繕率、更新周期、漏洩率、倍率、価格。スキーマ検査で列名を禁止する（2.19 I7）。

### 2.7 仕様属性 — `attribute_def` / `family_attribute` / `material_attribute_value`

`attribute_def`（仕様属性の辞書）

| フィールド | 型 | 必須 | 意味 |
|---|---|---|---|
| `attribute_code` | string（主キー、例 `thickness_mm`） | ○ | 属性の識別子 |
| `label_ja` | string | ○ | 表示名 |
| `value_type` | enum | ○ | 10進数／列挙／文字列 |
| `unit_code` | string | △ | 数値属性の単位。`DECIMAL` のとき必須 |
| `canonical_format` | string | ○ | 値の正規表現形式（例：指数表記なし・末尾の0なしの10進文字列） |
| `parse_patterns` | object[] | − | 名称・仕様欄から読み取るための表記規則。各要素は `prefix_tokens`、`suffix_tokens`、`assumed_unit_code` |
| `allowed_values` | string[] | △ | `ENUM` のとき必須 |
| `license_status` | enum | ○ | 語彙の出所のライセンス状態 |

`family_attribute`（系列ごとの属性の役割）

| フィールド | 型 | 必須 | 意味 |
|---|---|---|---|
| `family_id` / `attribute_code` | id / string | ○ | 複合主キー |
| `role` | enum | ○ | 同一性に効く／仕様軸（同一性に効き、値で品目を選ぶ）／説明のみ |
| `required` | boolean | ○ | 正規材料を `ACTIVE` にするのに値が必須か |
| `axis_mode` | enum | △ | 仕様軸のとき必須。登録済みの値だけ許すか、範囲内の任意の値を許すか |
| `value_range` | object | − | 許す値の範囲（`min`、`max`）。出典が必要な場合は来歴を付ける |

`material_attribute_value`（正規材料の仕様値）

| フィールド | 型 | 必須 | 意味 |
|---|---|---|---|
| `canonical_id` / `attribute_code` | id / string | ○ | 複合主キー |
| `value` | string | ○ | `canonical_format` に従った値 |
| `value_state` | enum | ○ | 値の状態 |

### 2.8 `alias` — 別名表

| フィールド | 型 | 必須 | 意味 |
|---|---|---|---|
| `alias_id` | id（主キー） | ○ | 別名の識別子 |
| `normalized_key` | string | ○ | 正規化後のキー。検索はこの列の完全一致だけで行う |
| `surface_form` | string | ○ | 代表的な表記（観測したまま、または当方が書いたもの） |
| `context_record_kind` | enum | − | この別名が有効な `record_kind`。null は文脈を問わない |
| `target_level` | enum | ○ | 解決先の階層（系列／正規材料） |
| `resolution` | enum | ○ | 一意／曖昧 |
| `target_ids` | id[] | ○ | 解決先。一意なら1件、曖昧なら2件以上（候補の一覧） |
| `alias_type` | enum | ○ | 別名の類型（正式名、文字種違い、長音違い、異体字、略称、同義語、総称、外国語名、誤記、旧名） |
| `match_strength` | enum | ○ | 正式名そのもの／人が登録した別名 |
| `evidence_kind` | enum | ○ | 根拠：当方が書いた一般語彙／許可された出典で観測／利用者が確認 |
| `normalizer_version` | string | ○ | キーを計算した正規化規則の版 |
| `status` | enum | ○ | `DRAFT` / `ACTIVE` / `DEPRECATED` |
| `license_status` | enum | ○ | 実効ライセンス状態 |
| `created_by` / `reviewed_by` | string / string | ○ / △ | 作成者／確認者（`ACTIVE` にするとき必須、作成者と別人） |
| `created_in_release` / `retired_in_release` | id / id | ○ / − | 追加・退役の版 |

制約：`ACTIVE` の中で（`normalized_key`、`context_record_kind`）は一意。全角半角・半角カナ・長音の有無のように **正規化規則だけで吸収できるゆれは行を増やさない**（同じキーに落ちるため）。行が要るのは、漢字とかなの読み替え・略称・同義語のように規則では決められないものだけである。

### 2.9 単位辞書 — `unit_def` / `unit_alias`

`unit_def`

| フィールド | 型 | 必須 | 意味 |
|---|---|---|---|
| `unit_code` | string（主キー、例 `kg`、`t`、`m2`、`m3`、`m`、`ct_mai`） | ○ | 単位の識別子 |
| `label_ja` | string | ○ | 表示（例：枚、台） |
| `dimension` | enum | ○ | 次元 |
| `base_unit_code` | string | ○ | 同じ次元の基準単位（質量 `kg`、体積 `m3`、面積 `m2`、長さ `m`）。個数は自分自身 |
| `to_base_factor` | decimal | △ | 基準単位への倍率。**定義によって決まる厳密な定数だけ**（例：t→kg）。個数・一式は null |
| `is_calculable` | boolean | ○ | 計算に使えるか。一式（`LUMP_SUM`）は偽 |

個数の単位は数え方ごとに別の `unit_code` とする（枚 `ct_mai`、本 `ct_hon`、台 `ct_dai`、基 `ct_ki`、個 `ct_ko`、箇所 `ct_kasho`、組 `ct_kumi`）。**同じ次元 `COUNT` でも、単位コードが違えば自動では換算しない。**

`unit_alias`

| フィールド | 型 | 必須 | 意味 |
|---|---|---|---|
| `alias_text_key` | string（主キー） | ○ | 単位表記のキー。NFKC と空白除去だけを掛けたもの。**大文字小文字は畳まない** |
| `unit_code` | string | ○ | 解決先 |
| `evidence_kind` / `status` | enum / enum | ○ | 根拠と状態 |

### 2.10 `unit_conversion` — 材料固有の換算（次元をまたぐもの）

| フィールド | 型 | 必須 | 意味 |
|---|---|---|---|
| `conversion_id` | id（主キー） | ○ | 換算の識別子 |
| `scope_level` / `scope_id` | enum（`FAMILY` / `MATERIAL`）/ id | ○ | 適用範囲。正規材料の行が系列の行より優先 |
| `conversion_kind` | enum | ○ | 換算の種類（下表） |
| `from_unit` / `to_unit` | string / string | ○ | 換算の向き（下表の標準方向で登録する） |
| `basis_parameter` | string | ○ | 根拠パラメータの名前（下表） |
| `basis_origin` | enum | ○ | 根拠の出所：同一性属性の値／人が登録した等価関係／外部の値 |
| `basis_attribute_code` | string | △ | `IDENTITY_ATTRIBUTE` のとき必須（例 `thickness_mm`） |
| `basis_value` | decimal | △ | `EXTERNAL_VALUE`・`CURATED_EQUIVALENCE` のときの値。不明なら null のまま |
| `basis_value_state` | enum（`value_state`） | ○ | 値の状態。`EXTERNAL_VALUE` で値が null なら `MISSING`。`IDENTITY_ATTRIBUTE` のときは値を属性側から読むので `DERIVED`（この列の値は null のまま） |
| `basis_source_id` | id（→ `source`） | △ | `EXTERNAL_VALUE`・`CURATED_EQUIVALENCE` で値があるとき必須。当方の判断による等価関係は `SELF_AUTHORED` の出典を指す |
| `basis_license_status` | enum | ○ | 根拠値のライセンス状態 |
| `applicability` | object | − | 成り立つ条件（属性の範囲、含水状態など） |
| `invertible` | boolean | ○ | 逆向きに使ってよいか（根拠値が正のときだけ真にできる） |
| `conversion_status` | enum | ○ | 使用可／根拠欠損で停止／ライセンスで停止／退役。計算で求める |
| `reviewed_by` / `created_in_release` | string / id | ○ | 確認者と追加した版 |

| `conversion_kind` | 標準方向 | `basis_parameter` | 式 |
|---|---|---|---|
| `DENSITY` | 体積 → 質量 | `density_kg_per_m3` | kg = m3 × 密度 |
| `THICKNESS` | 面積 → 体積 | `thickness_mm` | m3 = m2 × 厚さ ÷ 1000 |
| `MASS_PER_AREA` | 面積 → 質量 | `mass_per_area_kg_per_m2` | kg = m2 × 単位面積質量 |
| `MASS_PER_LENGTH` | 長さ → 質量 | `mass_per_length_kg_per_m` | kg = m × 単位長さ質量 |
| `MASS_PER_PIECE` | 個数 → 質量 | `mass_per_piece_kg` | kg = 個数 × 単位質量 |
| `AREA_PER_PIECE` | 個数 → 面積 | `area_per_piece_m2` | m2 = 個数 × 1個の面積 |
| `LENGTH_PER_PIECE` | 個数 → 長さ | `length_per_piece_m` | m = 個数 × 1個の長さ |
| `COUNT_NOUN_EQUIVALENCE` | 個数 → 個数 | `count_equivalence_ratio` | 数え方の違う個数どうしの等価比（人が系列ごとに登録） |

同じ次元の中の換算（kg と t、mm と m）は `unit_def.to_base_factor` で行い、この表には登録しない。機器の容量による按分のような **モデル計算は単位換算ではない** ので、この表に入れない（計算式研究の対象）。

### 2.11 類似グループ — `similarity_group` / `similarity_member` / `distinct_pair`

`similarity_group`

| フィールド | 型 | 必須 | 意味 |
|---|---|---|---|
| `group_id` | id（主キー） | ○ | グループの識別子 |
| `group_label_ja` | string | ○ | 表示名 |
| `grouping_basis` | string | ○ | まとめた根拠（何が同じで何が違うか） |
| `representative_id` | id | − | 代表とする正規材料。無くてよい |
| `substitution_policy` | enum | ○ | 代表での置き換えを許すか。既定は `NONE`（検索・提案だけに使う） |
| `verification_status` | enum | ○ | 置き換えの誤差を検証したか（研究プロトコル P7 の語彙）。既定は `NOT_VERIFIED` |
| `status` / `license_status` / `compartment` | enum | ○ | 状態・実効ライセンス・区画 |

`similarity_member`

| フィールド | 型 | 必須 | 意味 |
|---|---|---|---|
| `group_id` | id | ○ | グループ |
| `member_level` / `member_id` | enum / id | ○ | 構成員の階層（系列／正規材料）と識別子 |
| `decision` | enum | ○ | 機械の提案か、人が確定したか |
| `score_snapshot` | object | − | 判断時の特徴量（3.8）。しきい値を後で見直すための記録 |
| `decided_by` / `decided_at` | string / date | △ | `CONFIRMED` のとき必須 |

`distinct_pair`（「別物」と判断した組。同じ提案を繰り返さないための記録）

| フィールド | 型 | 必須 | 意味 |
|---|---|---|---|
| `left_id` / `right_id` | id / id | ○ | 組（識別子の小さい方を左に置く） |
| `reason_code` / `reason_text` | enum / string | ○ | 別物と判断した理由 |
| `decided_by` / `decided_at` | string / date | ○ | 判断者と日付 |

### 2.12 重複と統合 — `duplicate_candidate` / `merge_event`

`duplicate_candidate`

| フィールド | 型 | 必須 | 意味 |
|---|---|---|---|
| `candidate_id` | id（主キー） | ○ | 候補の識別子 |
| `level` | enum（`duplicate_level`） | ○ | 重複の水準 D0〜D4（3.7） |
| `left_id` / `right_id` | id / id | ○ | 候補の組 |
| `evidence` | object | ○ | 一致したキー、特徴量、使った `normalizer_version` |
| `state` | enum（`candidate_state`） | ○ | 未処理／統合済み／別物として維持／グループ化／阻止 |
| `blocker_code` | enum（`merge_blocker`） | △ | `BLOCKED` のとき必須 |
| `resolved_by_event` | id（→ `merge_event`） | △ | `MERGED` のとき必須 |

`merge_event`（追記専用）

| フィールド | 型 | 必須 | 意味 |
|---|---|---|---|
| `merge_event_id` | id（主キー） | ○ | 統合イベントの識別子 |
| `event_kind` | enum | ○ | 統合／分割（統合の取り消し） |
| `target_level` | enum（`FAMILY` / `MATERIAL`） | ○ | 対象の階層 |
| `survivor_id` | id | ○ | 残すレコード |
| `merged_ids` | id[] | ○ | 統合されて退くレコード |
| `duplicate_level` | enum | ○ | どの水準の重複として統合したか |
| `survivor_rule_applied` | enum | ○ | 残す側を決めた規則 |
| `field_resolutions` | object[] | ○ | 項目ごとの決着。各要素は `field`、`kept_value`、`discarded_values`、`rule` |
| `aliases_created` | id[] | ○ | この統合で作った別名 |
| `provenance_links_copied` | integer | ○ | 残す側へ写した来歴の件数 |
| `license_before` / `license_after` | enum / enum | ○ | 残す側の実効ライセンス（統合前・統合後）。悪化する統合は成立させない |
| `decided_by` / `reviewed_by` / `decided_at` | string / string / date | ○ / △ / ○ | 判断者・確認者（D2〜D4 では必須、別人）・日付 |
| `reason_text` | string | ○ | 統合した理由 |
| `release_id` | id | ○ | 反映した版 |

### 2.13 `provenance_link` — 来歴

| フィールド | 型 | 必須 | 意味 |
|---|---|---|---|
| `link_id` | id（主キー） | ○ | 来歴の識別子 |
| `record_table` / `record_id` | string / id | ○ | 対象のレコード |
| `field_name` | string | − | 対象の項目。null はレコード全体 |
| `source_id` | id（→ `source`） | ○ | 寄与した出典 |
| `raw_id` | id（→ `raw_record`） | − | 寄与した受領レコード |
| `derivation` | enum | ○ | 写した／正規化した／文字列から読み取った／人が登録した／統合で引き継いだ／計算した |
| `normalizer_version` | string | − | 正規化・解析を経た場合の規則の版 |
| `via_merge_event` | id | − | 統合で引き継いだ場合のイベント |
| `created_in_release` | id | ○ | 追加した版 |

### 2.14 版 — `release` / `change_log`

`release`

| フィールド | 型 | 必須 | 意味 |
|---|---|---|---|
| `release_id` | id（主キー、例 `REL-0001`） | ○ | 版の識別子。公開後は内容を変えない |
| `parent_release_id` | id | − | 1つ前の版 |
| `schema_version` | string | ○ | 表定義の版 |
| `normalizer_version` | string | ○ | 正規化規則の版 |
| `compartment` | enum | ○ | この版の区画 |
| `manifest_hash` | string | ○ | 全表の内容ハッシュ |
| `invariant_report` | object | ○ | 不変条件（2.19）の検査結果 |
| `status` | enum（`release_status`） | ○ | 作成中／公開／取り下げ |
| `withdrawn_reason` | string | △ | 取り下げのとき必須 |
| `built_at` | datetime | ○ | 作成日時 |

`change_log`（追記専用）

| フィールド | 型 | 必須 | 意味 |
|---|---|---|---|
| `change_id` | id（主キー） | ○ | 変更の識別子 |
| `release_id` | id | ○ | 変更が入った版 |
| `record_table` / `record_id` | string / id | ○ | 対象 |
| `change_kind` | enum | ○ | 作成／更新／統合／分割／廃止／隔離／ライセンス変更 |
| `breaking` | boolean | ○ | 過去の計算結果を変え得る変更か（3.9） |
| `before_hash` / `after_hash` | string / string | − / ○ | 変更前後の内容ハッシュ |
| `reason_text` / `actor` | string / string | ○ | 理由と実施者 |

### 2.15 `factor_binding` — 係数への参照（値を持たない）

| フィールド | 型 | 必須 | 意味 |
|---|---|---|---|
| `binding_id` | id（主キー） | ○ | 参照の識別子 |
| `canonical_id` | id | ○ | 正規材料 |
| `factor_id` | id | ○ | 別管理の係数登録簿の識別子（`FACTOR.factor_id`） |
| `binding_unit` | string（→ `unit_def`） | ○ | 係数の分母単位（`FACTOR.factor_unit` と一致） |
| `stages` | string[] | ○ | 係数が含む段階（`FACTOR.factor_stages`） |
| `license_status` | enum | ○ | 係数登録簿から写したライセンス状態 |
| `priority_rank` | integer | − | 複数の参照があるときの採用順（方針として別途決める） |
| `status` | enum | ○ | 状態 |

この表は係数登録簿との接点であり、**係数値の列は無い**。出典の違う係数は別の行として並び、平均も統合もしない。

### 2.16 `quarantine_log` — 隔離ログ（中身を保存しない）

| フィールド | 型 | 必須 | 意味 |
|---|---|---|---|
| `quarantine_id` | id（主キー） | ○ | 記録の識別子 |
| `source_id` | id | ○ | 取り込まなかった、または隔離した出典 |
| `reason_code` | enum（`quarantine_reason`） | ○ | 理由 |
| `affected_record_count` | integer | − | 影響したレコード数（分かる場合） |
| `payload_stored` | boolean | ○ | 常に偽。**名称・値などの中身は保存しない** |
| `logged_by` / `logged_at` | string / date | ○ | 記録者と日付 |
| `follow_up` | string | − | 次の手当て（権利者への照会など） |

### 2.17 `usage_link` — 部位区分との接点

| フィールド | 型 | 必須 | 意味 |
|---|---|---|---|
| `target_level` / `target_id` | enum / id | ○ | 系列または正規材料 |
| `element_group` | enum | ○ | 部位・設備の区分（指示書 第7章の9区分＋その他） |
| `typicality` | enum | ○ | 代表的な使われ方か、あり得る使われ方か |

部位区分の体系そのものは別の設計案の担当であり、本設計はこの接点だけを定める。1つの材料が複数の区分に現れてよい（多対多）。

### 2.18 `normalization_issue` — 課題（人の確認待ち）

| フィールド | 型 | 必須 | 意味 |
|---|---|---|---|
| `issue_id` | id（主キー） | ○ | 課題の識別子 |
| `raw_id` | id | ○ | 対象の受領レコード |
| `issue_code` | enum | ○ | 課題の種類 |
| `detail` | string | − | 詳細（残った文字列、候補の一覧など） |
| `state` | enum（`issue_state`） | ○ | 未解決／解決済み／対応しない |
| `resolved_by` / `resolution_ref` | string / id | △ | 解決した人と、解決に使ったレコード（別名・統合イベントなど） |

### 2.19 表をまたぐ不変条件（版を作るたびに全件検査する）

| ID | 不変条件 |
|---|---|
| I1 | `raw_record` 以外のすべてのレコードに、1件以上の `provenance_link` がある |
| I2 | 各レコードの `license_status` は、来歴でつながる全出典のうち最も制限の強い状態と一致する（順序：`PERMITTED_PUBLIC` ＜ `PERMISSION_REQUIRED` ＜ `UNKNOWN` ＜ `RESTRICTED`） |
| I3 | 区画 `PUBLIC_RELEASE` の版には `PERMITTED_PUBLIC` 以外のレコードが無く、参照先の出典はすべて `storage_policy = MAY_STORE_IN_PUBLIC_REPO` で `license_evidence_ref` を持つ |
| I4 | `ACTIVE` の `canonical_material` の中で `identity_key` が一意 |
| I5 | `ACTIVE` の `alias` の中で（`normalized_key`、`context_record_kind`）が一意。`UNIQUE` は解決先1件、`AMBIGUOUS` は2件以上 |
| I6 | 別名・係数参照・類似グループ・使われ方の参照先はすべて `ACTIVE`（統合先への付け替えが済んでいる） |
| I7 | 本表群に、係数・耐用年数・修繕率・更新周期・漏洩率・倍率・価格を表す列が存在しない |
| I8 | `merged_into` の連鎖に循環が無く、たどる深さは1 |
| I9 | 各 `canonical_material` の `declared_unit` は `unit_def` にあり、`is_calculable` が真 |
| I10 | `conversion_status = USABLE` の換算は、根拠値が `MISSING` でなく、`basis_license_status = PERMITTED_PUBLIC` |
| I11 | 類似グループは区画・`record_kind` をまたがない |
| I12 | 正規化は冪等である（正規化済みのキーをもう一度正規化しても変わらない）。受領レコードと人の判断記録から版を作り直すと同じ `manifest_hash` になる |
| I13 | 前の版との差分がすべて `change_log` に載っている |

---

## 3. 規則と手順

### 3.1 手順0：ライセンス関門（取り込みの前に行う）

1. 取り込もうとするデータの出典を `source` に登録する。この時点では中身を読み込まない。
2. `license_status` を判断し、証拠を `license_evidence_ref` に記録する。判断者と日付を残す。
3. 次の表に従って扱いを決める。

| `license_status` | 取り込み | 中身の保存 | 計算での使用 | 公開リポジトリ |
|---|---|---|---|---|
| `PERMITTED_PUBLIC`（証拠あり、`storage_policy = MAY_STORE_IN_PUBLIC_REPO`） | する | する | できる | 置ける |
| `PERMISSION_REQUIRED` | しない | しない | できない | 置けない |
| `UNKNOWN` | しない | しない | できない | 置けない |
| `RESTRICTED` | しない | しない | できない | 置けない |

4. 取り込まない出典は `quarantine_log` に理由だけを記録する（中身は書かない）。
5. 名称一覧・分類ラベル・コード表も「中身」である。**制限付きの出典に載っている名称を別名として登録することは、係数の転記と同じ扱いで禁止する。**
6. ライセンスは変わり得る。`license_valid_until` を過ぎた出典、または再確認で状態が悪化した出典は、つながるレコードの実効状態を計算し直し、次の版で `QUARANTINED` にする（`change_kind = QUARANTINE`、`breaking = true`）。
7. 区画 `PRIVATE_LICENSED` は将来のための予約であり、現時点では使わない。使う場合の規則は「非公開区画から公開区画のIDは参照してよいが、逆は禁止」とする（5章 Q7）。

### 3.2 手順1：受領と同一行の重複（D0）

1. 関門を通った出典のレコードを `raw_record` に追記する。名称・仕様・単位・分類ラベルだけを写し、係数などの数値列は写さない。
2. `content_hash` が同じ出典内で既にあれば、`intake_status = DUPLICATE_RAW`、`duplicate_of_raw` に先行レコードを入れ、先行レコードの `occurrence_count` を増やす。以降の処理には進めない。
3. 受領レコードは以後いっさい書き換えない。

### 3.3 手順2：文字列正規化（決定的・版付き）

名称欄と単位欄は別々に扱う。以下は名称欄（および仕様欄）の規則で、この順に適用する。規則一式に `normalizer_version` を付け、変更したら全件を再正規化して差分を確認する。

| 段 | 規則 | 例（すべて架空の文字列） | 注意 |
|---|---|---|---|
| N1 | Unicode の互換正規化（NFKC）。全角英数字→半角、半角カナ→全角カナ、組文字の単位記号→英数字の並び | `ﾎﾞｰﾄﾞ`→`ボード`、`Ａ`→`A`、`㎡`→`m2` | 丸数字や囲み文字も展開される。意図しない展開が無いか、実データで確認が要る |
| N2 | 制御文字・ゼロ幅文字を除く。空白を1個の半角空白にまとめ、前後を削る | 全角空白→半角空白 | 空白は仕様トークンの区切りに使うので、この段では消さない |
| N3 | 括弧と区切り記号を統一する。当方が作る装飾語リストに載る注記を `decorations` に移す | 各種の括弧→丸括弧 | 装飾語リストは自作する。括弧の中身を無条件に捨てない |
| N4 | ダッシュ類を統一する。カタカナの直後は長音記号、英数字の間はハイフン | カタカナ直後の横線→`ー` | NFKC では統一されない横線が残るため必要 |
| N5 | 英字を小文字にする（**名称キーだけ**） | `A`→`a` | 単位欄には適用しない（3.4） |
| N6 | ひらがなをカタカナに畳む | `かくう`→`カクウ` | 漢字をかなに開くことはしない（読みは一意に決まらない） |
| N7 | 仕様トークンを取り出す。`attribute_def.parse_patterns` に従い、数値と単位の組を名称から抜く | `厚12mm`、`t=12`、`12ミリ` | 単位の無い数値は `SPEC_UNIT_ASSUMED`、どの属性か決まらない数値は `SPEC_ATTRIBUTE_AMBIGUOUS` |
| N8 | 長音を含めて3文字以上のカタカナ連続の末尾の長音を除く。自作の異体字対応表で旧字体などを畳む。空白を除く | `シャッター甲`→`シャッタ甲` | 畳みすぎで別の語とぶつかった場合は I5 の検査で表面化させ、人が判断する |
| N9 | 出力：`name_key`、`spec_tokens`、`decorations`、`residual_text` | | `residual_text` が空でなければ `PARSE_INCOMPLETE`。解釈できない部分を黙って捨てない |

規則で吸収しないもの（別名表に人が登録するもの）：漢字とかなの読み替え、漢字とかなの交ぜ書き、略称、同義語、総称、外国語名、誤記。

### 3.4 手順3：単位欄の解析

1. `unit_text` に NFKC と空白除去だけを掛けて `alias_text_key` を作る。**大文字小文字は畳まない**（接頭語の大文字と小文字は別の意味を持ち得る）。
2. `unit_alias` を完全一致で引く。無ければ `UNIT_UNKNOWN`。推測で近い単位に寄せない。
3. 単位欄が空なら `UNIT_TEXT_MISSING`。名称の中の文字から単位を推測しない。
4. 同じ文字が欄によって別の意味を持つことに注意する。たとえば `t` は、単位欄では質量の単位、名称欄の `t=12` では厚さの接頭語であり得る。**欄ごとに別の解析器を使い、欄をまたいで解釈しない。**
5. 解決先が `LUMP_SUM`（一式）なら `LUMP_SUM_UNIT`。数量×係数の計算には使えない。

### 3.5 手順4：名称の解決と正規レコードの作成

1. `name_key` で `alias` を完全一致検索する（`context_record_kind` が分かっていれば絞る）。
   - 0件 → `ALIAS_UNRESOLVED`。課題に登録し、類似度による候補（3.8）を **提案として** 添える。提案を自動で採用しない。
   - `AMBIGUOUS` → `ALIAS_AMBIGUOUS`。候補の一覧を示して止める。
   - `UNIQUE` → 系列（または正規材料）が決まる。
2. 系列が決まったら、仕様トークンを系列の属性に割り当てる。属性が未確定のトークンは、系列がその単位の仕様軸を1つだけ持つ場合に限りその軸に割り当て、それ以外は `SPEC_ATTRIBUTE_AMBIGUOUS` とする。
3. 同一性キーを計算する。

```
identity_string = "v1|" + family_id + "|" + 属性コード昇順に連結( attribute_code + "=" + 正規形式の値 ; 区切り ";" )
                  ※ 対象は role が IDENTITY または VARIANT_AXIS の属性だけ
identity_key    = SHA-256( UTF-8(identity_string) ) の16進文字列
```

   数値は `canonical_format` に従う10進文字列で比較する（`12`、`12.0`、全角の`１２` は同じ `12`）。浮動小数点の等値比較はしない。
4. 同じ `identity_key` の正規材料が既にあれば、**新しく作らずにそこへ来歴を追加する**（作成時点で D1 の重複を防ぐ）。無ければ `DRAFT` で作る。
5. `required` の同一性属性が欠けている場合は `IDENTITY_INCOMPLETE` とし、`ACTIVE` にしない。
6. `DRAFT` を `ACTIVE` にできるのは確認者だけである。`DRAFT` は計算で使えない。
7. 新しい系列を作るときは、表示名を当方の一般語彙で付け、`CANONICAL_NAME` の別名を1件作る。

### 3.6 手順5：単位の扱い

**宣言単位の決め方**（`declared_unit_basis`）

1. 係数参照（`factor_binding`）が1件以上あり、分母単位がすべて同じ → その単位（`FACTOR_DENOMINATOR`）。分母単位が複数あるときは確認者が1つを選び、残りは換算で結ぶ。換算が無い係数参照は、その単位で入力された数量にしか使えない。
2. 係数参照が無く、許可された出典が単位を宣言している → その単位（`SOURCE_DECLARATION`）。
3. どちらでもない → 系列の `default_declared_unit`（`PROVISIONAL`）。現時点では係数を1件も結び付けていないので、すべてこの状態になる。

**換算先**：数量の単位から、採用する係数参照の `binding_unit` へ換算する。係数参照が無いとき、および集計上の表示は `declared_unit` を換算先とする。輸送（質量×距離）と廃棄段階（質量収支）は質量が要るので、質量への経路の有無を `mass_path_status` として別に持つ。経路が無い材料は、その段階が「0」ではなく「計算できない」になる（`MASS_PATH_UNAVAILABLE`）。

**換算経路の決め方**

1. 入力単位と換算先が同じ `unit_code` → 換算しない。
2. 同じ次元（個数以外）→ `to_base_factor` の比で換算する（定義値）。
3. 個数どうしで `unit_code` が違う → その材料または系列に `COUNT_NOUN_EQUIVALENCE` が登録されていれば使い（`COUNT_EQUIVALENCE_APPLIED` の警告）、無ければ `COUNT_UNIT_NOT_COMPARABLE` で止める。
4. 次元が違う → その材料（無ければ系列）に登録された `unit_conversion` をたどる。材料固有の換算は **最大2段** まで（例：面積→体積→質量）。
   - 経路が無い → `UNIT_DIMENSION_MISMATCH_NO_PATH`。
   - 経路上の換算が `BLOCKED_BASIS_MISSING` → `CONVERSION_BASIS_MISSING`。`BLOCKED_LICENSE` → `CONVERSION_BASIS_NOT_PERMITTED`。
   - `applicability` の条件を外れる → `CONVERSION_OUT_OF_APPLICABILITY`。
   - 使える経路が複数ある（例：単位面積質量と、厚さ×密度）→ 両方で計算し、相対差が許容差を超えれば `CONVERSION_PATH_CONFLICT` で止める。許容差は未設定（実データで決める）。収まれば材料固有の段数が少ない経路を使う。
5. 換算した数量は状態 `DERIVED` とし、使った換算の識別子と根拠値の状態を記録する（`CONVERSION_APPLIED` の警告）。

**してはならないこと**：根拠値の欠損を 0・1・「一般的な値」で補うこと。同じ `substance_class` の別材料の根拠値を黙って借りること。入力単位と宣言単位の次元が違うのに数値をそのまま使うこと。

### 3.7 手順6：重複の検出と統合

| 水準 | 定義 | 検出方法 | 扱い |
|---|---|---|---|
| `D0_RAW_EXACT` | 同じ出典の同じ内容の行 | `content_hash` の一致 | 受領時に1件へ集約（3.2）。統合イベントは作らない |
| `D1_IDENTITY` | 正規化後に `identity_key` が一致 | キーの一致 | 作成時に防ぐ（3.5）。規則の版が上がって後から一致した場合は自動統合してよい |
| `D2_UNIT_VARIANT` | 同一性は同じで単位だけが違う | `identity_key` の一致＋単位コードの不一致 | 正規材料は1件にし、別の単位は換算として登録する。根拠が無ければ `BLOCKED_BASIS_MISSING` のまま登録する（その単位が実際に現れるという事実を残す）。人の確認が必要 |
| `D3_NEAR` | 名称や仕様が似ているが一致しない | 類似度（3.8） | 人が判断する。結果は「統合」「別物として維持」「類似グループに入れる」のいずれか |
| `D4_CROSS_SOURCE` | 別の出典が同じ材料を別の値で記述している | 系列の一致＋出典の不一致 | 正規材料は1件、係数参照と換算根拠は出典ごとに別の行。**値を平均しない・選んで捨てない** |

**統合の成立条件（すべて満たすこと）**

- M1：`target_level`・`record_kind`・`form_factor` が同じ（違えば `KIND_OR_FORM_MISMATCH`）。
- M2：正規材料どうしなら同一性属性が矛盾しない（片方が欠損、または同じ値。矛盾すれば `IDENTITY_ATTRIBUTE_CONFLICT`）。系列どうしなら確認者が理由を書く。
- M3：区画が同じで（違えば `COMPARTMENT_MISMATCH`）、統合後の実効ライセンスが残す側の統合前より悪化しない。悪化するなら統合しない（`LICENSE_WOULD_DEGRADE`）。
- M4：同じ向きの換算が両方 `USABLE` で根拠が食い違う、ということが無い。あれば先にそれを解決する（`CONVERSION_CONFLICT`）。
- M5：D2〜D4 は判断者と確認者が別人。確認が済むまで候補は `BLOCKED`（`REVIEW_REQUIRED`）のままにする。

条件を満たさない候補は `duplicate_candidate.state = BLOCKED` とし、上の括弧内のコードを `blocker_code` に記録する。

**残す側の決め方**（上から順に適用）：`ACTIVE` を `DRAFT` より優先 → 同一性属性がより埋まっている方 → 識別子が古い方。

**統合の手順**

1. `merge_event`（`event_kind = MERGE`）を作り、根拠を記録する。
2. 退く側を `status = MERGED`、`merged_into = 残す側` にする。行は消さない。
3. 項目ごとに決着を付けて `field_resolutions` に記録する。表示名は残す側を保ち（`KEEP_SURVIVOR`）、退く側の名称は別名に移す（`MOVE_TO_ALIAS`）。残す側が空の属性は退く側の値で埋める（`FILL_FROM_MERGED_IF_NULL`）。ライセンスは最も厳しい方（`MOST_RESTRICTIVE`）。使われ方・係数参照・換算は和集合（`UNION`、同一行は1件に）。
4. 退く側の来歴を残す側へ写し、`via_merge_event` を付ける。
5. 別名・係数参照・換算・類似グループ・使われ方の参照先を残す側へ付け替える。
6. 系列の統合では、配下の正規材料の `identity_key` を計算し直す。一致するものが出たら、正規材料の統合を続けて行う（同じ手順）。
7. 実効ライセンス・`mass_path_status`・`conversion_status` を計算し直す。
8. `change_log` に記録する。退く側と残す側で `declared_unit` が違う場合は `breaking = true`。

**統合の取り消し**：受領レコードと来歴が残っているので、`event_kind = SPLIT` のイベントで退いたレコードを `ACTIVE` に戻し、写した来歴と別名を元に戻す。統合前の版はそのまま参照できる。

**統合後の参照**：退いたIDを参照する計算は、残す側へ読み替える（`REDIRECTED_BY_MERGE` の警告）。ただし宣言単位が違い、使える換算が無い場合は `MERGE_REDIRECT_NEEDS_CONFIRMATION` で止める。

### 3.8 手順7：類似グループ化

1. **候補の生成（ブロッキング）**：`record_kind`・`substance_class`・`form_factor` が同じ組だけを比べる。`distinct_pair` に載っている組は除く。
2. **特徴量**（`score_snapshot` に記録）：
   - `name_bigram_overlap`：`family_name_key` の文字2連の重なり
   - `identity_attribute_agreement`：同一性属性の一致数と不一致数
   - `unit_dimension_match`：宣言単位の次元が同じか
   - `usage_overlap`：`usage_link` の区分の重なり
3. **しきい値**：自動で提案に載せる下限と、人の確認を優先する上限の2つを置くが、**値は未設定** である。正解付きの実ペア（5章 D-4）が無いと決められない。
4. **人の判断**：`SUGGESTED` を `CONFIRMED` にする、または `distinct_pair` に理由付きで登録する。
5. **効果の範囲**：類似グループは検索と提案のためのもので、既定（`substitution_policy = NONE`）では計算に影響しない。
6. **代表での置き換え**（`REPRESENTATIVE_ALLOWED_WITH_FLAG`）は **近似** である。研究プロトコル P7 に従い、基準計算との誤差（特に過小評価）を検証して `verification_status` が `NOT_VERIFIED` でなくなるまで有効にしない。有効にした場合も、置き換えた事実を結果に記録する（`REPRESENTATIVE_SUBSTITUTION_APPLIED`）。
7. **まとめてはならない組**：`record_kind` が違う／区画が違う／宣言単位の次元が違い換算根拠も無い／結び付いた係数の算定境界（含む段階）が違う。

仕様値だけが違う品目（厚さ違いなど）は類似グループではなく **同じ系列の中の仕様軸** で表す。仕様軸が `CONTINUOUS` の系列は、仕様値をパラメータとする1本のモデルで扱える可能性があり、指示書 第4章③（共通パラメータモデル）の研究と接続できる。ただし可能性の指摘にとどまり、未検証である。

### 3.9 手順8：版管理

1. 版を持つものは3つ：表定義（`schema_version`）、正規化規則（`normalizer_version`）、データ（`release_id`）。
2. 版は不変条件 I1〜I13 がすべて合格したときだけ `PUBLISHED` にできる。1件でも不合格なら公開しない。
3. 公開した版の内容は変えない。修正は次の版で行う。
4. 変更の区別：

| 区分 | 例 | 扱い |
|---|---|---|
| 非破壊（`breaking = false`） | 別名の追加、正規材料の追加、換算の追加、類似グループの追加 | 既存の計算結果は変わらない |
| 破壊（`breaking = true`） | 宣言単位の変更、統合・分割、同一性属性の変更、換算根拠の変更、ライセンスの悪化、別名の解決先の変更 | 影響するIDの一覧を付ける。計算側は版を上げるときに解決をやり直し、差分を報告する |

5. 計算結果には `release_id` と `normalizer_version` を記録する。古い版に固定した計算は、その版が取り下げられない限り再現できる。
6. ライセンスの悪化で版を取り下げる場合に備え、**公開リポジトリに置く前に関門を通す**。公開後の履歴からの削除は確実にはできない。

### 3.10 計算前の解決手順（`resolve`）と停止コード

入力は（名称の文字列、単位の文字列、数量の状態、任意で `record_kind` と仕様値）。出力は `resolution_status`、`canonical_id`、換算の記録、停止コードまたは警告。画面の話ではなく、データ上の手順である。

1. 数量が `MISSING` → `QUANTITY_MISSING`（0 と扱わない）。
2. 単位欄を解析（3.4）→ 失敗なら停止。
3. 名称を正規化（3.3）→ 別名を引く（3.5）→ 系列を決める。
4. 仕様値を割り当てて正規材料を決める。仕様軸の値が無い → `VARIANT_UNSPECIFIED`。値はあるが登録が無い（`ENUMERATED` の軸）→ `VARIANT_NOT_REGISTERED`。**既定の厚さなどを黙って補わない。**
5. 状態を確認する。`MERGED` は統合先へ読み替え、`ACTIVE` でなければ `RECORD_NOT_ACTIVE`。
6. 実効ライセンスを確認する。`PERMITTED_PUBLIC` でなければ `LICENSE_NOT_PERMITTED`。
7. 単位を換算する（3.6）。
8. 係数参照の分母単位と、換算後の数量の単位が一致することを確認する。不一致なら `FACTOR_UNIT_MISMATCH`（SYS-02）。

| 停止コード | 条件 | 関連する既存の規則 |
|---|---|---|
| `QUANTITY_MISSING` | 数量が欠損 | R08、SYS-01 |
| `UNIT_TEXT_MISSING` / `UNIT_UNKNOWN` | 単位欄が空／辞書に無い | SYS-02 |
| `LUMP_SUM_UNIT` | 単位が一式 | 数量によらない推計（A13-04）の対象かどうかは別途判断 |
| `ALIAS_UNRESOLVED` / `ALIAS_AMBIGUOUS` | 名称が解決できない／候補が複数 | — |
| `VARIANT_UNSPECIFIED` / `VARIANT_NOT_REGISTERED` | 仕様値が足りない／登録が無い | — |
| `RECORD_NOT_ACTIVE` | 下書き・廃止・隔離のレコード | — |
| `LICENSE_NOT_PERMITTED` | 実効ライセンスが許可状態でない | SYS-03、QA-03、R03、R07 |
| `MERGE_REDIRECT_NEEDS_CONFIRMATION` | 統合先の宣言単位が違い換算が無い | — |
| `UNIT_DIMENSION_MISMATCH_NO_PATH` | 次元が違い、換算の登録が無い | SYS-02 |
| `COUNT_UNIT_NOT_COMPARABLE` | 数え方の違う個数で等価の登録が無い | SYS-02 |
| `CONVERSION_BASIS_MISSING` | 換算はあるが根拠値が欠損 | R08 |
| `CONVERSION_BASIS_NOT_PERMITTED` | 根拠値のライセンスが許可状態でない | R07 |
| `CONVERSION_OUT_OF_APPLICABILITY` | 換算の適用条件の外 | — |
| `CONVERSION_PATH_CONFLICT` | 複数の経路の結果が食い違う | — |
| `FACTOR_UNIT_MISMATCH` | 係数の分母単位と数量の単位が合わない | SYS-02 |

**操作数の数え方（目標 G7 の測り方）**：名称と単位の入力1回で `RESOLVED` になれば1操作。`ALIAS_AMBIGUOUS` で候補を1回選べば＋1、`VARIANT_UNSPECIFIED` で仕様値を1つ与えれば＋1。実データが無いので、操作数の分布は現時点で不明である。

---

## 4. 例題（すべて架空のレコード。実在の材料・製品・データセットではなく、係数値は含まない）

### 4.1 出典

| `source_id` | 内容 | `origin_kind` | `license_status` | `storage_policy` |
|---|---|---|---|---|
| `SRC-F01` | 架空の数量内訳書（本例題のために作った文字列） | `SYNTHETIC_FICTIONAL` | `PERMITTED_PUBLIC` | `MAY_STORE_IN_PUBLIC_REPO` |
| `SRC-F02` | 架空の材料一覧（同上） | `SYNTHETIC_FICTIONAL` | `PERMITTED_PUBLIC` | `MAY_STORE_IN_PUBLIC_REPO` |
| `SRC-F03` | 許諾が未確認だと仮定した架空の第三者データ | `THIRD_PARTY_DATASET` | `UNKNOWN` | `DO_NOT_INGEST` |
| `SRC-S01` | 当方の命名・整理判断（表示名、人が登録した等価関係） | `SELF_AUTHORED` | `PERMITTED_PUBLIC` | `MAY_STORE_IN_PUBLIC_REPO` |

`SRC-F03` は関門で止まり、`quarantine_log` に理由（`LICENSE_UNKNOWN`）だけが残る。中身は1行も保存しない。

### 4.2 受領レコードと正規化の結果

| `raw_id` | 出典 | `name_text` | `unit_text` | `name_key` | 仕様トークン | 単位 | 備考 |
|---|---|---|---|---|---|---|---|
| R-01 | F01 | `架空ボードＡ　厚１２ｍｍ` | `㎡` | `架空ボードa` | 厚さ 12 mm | `m2` | N1・N5・N7 |
| R-02 | F01 | `架空ﾎﾞｰﾄﾞA t=12` | `m2` | `架空ボードa` | 厚さ 12（単位は仮定） | `m2` | `SPEC_UNIT_ASSUMED` |
| R-03 | F02 | `かくうボードA 12ミリ` | `平米` | `カクウボードa` | 長さ系 12 mm（属性未確定） | `m2` | 別名が無く `ALIAS_UNRESOLVED` |
| R-04 | F02 | `架空ボードA 厚9mm` | `m2` | `架空ボードa` | 厚さ 9 mm | `m2` | 同じ系列の別の仕様値 |
| R-05 | F02 | `架空ボードA 厚12mm` | `枚` | `架空ボードa` | 厚さ 12 mm | `ct_mai` | 単位違い（D2） |
| R-06 | F02 | `架空ボードB 厚12mm` | `m2` | `架空ボードb` | 厚さ 12 mm | `m2` | 別の系列 |
| R-07 | F01 | `架空充填材Ｘ` | `m3` | `架空充填材x` | なし | `m3` | |
| R-08 | F02 | `架空充てん材X` | `t` | `架空充テン材x` | なし | `t` | 交ぜ書き。`ALIAS_UNRESOLVED` |
| R-09 | F01 | `架空シャッター甲` | `台` | `架空シャッタ甲` | なし | `ct_dai` | N8 で末尾の長音を除く |
| R-10 | F02 | `架空シャッタ甲` | `基` | `架空シャッタ甲` | なし | `ct_ki` | R-09 と同じキー。数え方が違う |
| R-11 | F01 | `架空ボード` | `m2` | `架空ボード` | なし | `m2` | 総称。A か B か決まらない |
| R-12 | F01 | `架空ボードＡ　厚１２ｍｍ` | `㎡` | — | — | — | R-01 と同じ内容（D0）。`DUPLICATE_RAW` |

### 4.3 処理の流れ

1. **D0**：R-12 は R-01 と `content_hash` が一致。R-01 の `occurrence_count` を 2 にし、R-12 は以降の処理に進めない。
2. **系列と正規材料の作成**：
   - R-01 → 系列 `FAM-0001`（架空ボードA、`SHEET`、仕様軸 `thickness_mm`）と正規材料 `CM-0001`（厚さ 12、宣言単位 `m2`、`PROVISIONAL`）を作る。
   - R-02 → 同じ `identity_key`。新しく作らず `CM-0001` に来歴を足す。`SPEC_UNIT_ASSUMED` の課題は確認者が「mm でよい」と確定して解決。
   - R-04 → `CM-0002`（同じ系列、厚さ 9）。
   - R-06 → 系列 `FAM-0002`（架空ボードB）と `CM-0003`。
   - R-07 → 系列 `FAM-0003`（架空充填材X、`BULK`）と `CM-0004`（宣言単位 `m3`）。
   - R-09・R-10 → 同じキーなので系列 `FAM-0004`（架空シャッター甲、`EQUIPMENT`、`DISCRETE`）と `CM-0005`（宣言単位 `ct_dai`）の1件にまとまる。
3. **解決できなかった名称**：
   - R-03（`カクウボードa`）は別名が無い。下書きの系列 `FAM-0005` と正規材料 `CM-0006` が作られ、類似度の提案として `FAM-0001` が添えられる。確認者が同じものと判断 → 統合イベント `ME-0001`（系列）と `ME-0002`（正規材料）。`カクウボードa` は `SCRIPT_VARIANT` の別名 `AL-0002` になる。属性未確定だった「12 mm」は、`FAM-0001` が mm の仕様軸を1つだけ持つので厚さに割り当てられる。
   - R-08（`架空充テン材x`）も同様に、下書き `FAM-0006`／`CM-0007`（宣言単位 `t`）→ `FAM-0003`／`CM-0004` へ統合（`ME-0003`、`ME-0004`）。別名 `AL-0006`。単位 `t` は換算として残す（次項）。
4. **単位違い（D2）**：
   - `CM-0001` に対する `枚`（R-05）：`AREA_PER_PIECE` の換算 `UC-0102` を登録するが、1枚の面積が出典に無いので `BLOCKED_BASIS_MISSING`。
   - `CM-0001` の面積→体積：`THICKNESS` の換算 `UC-0101`。根拠は同一性属性の厚さ（12 mm）そのものなので外部の値が要らず、`USABLE`。
   - `CM-0004` の体積↔質量：`DENSITY` の換算 `UC-0103`。密度が無いので `BLOCKED_BASIS_MISSING`。`mass_path_status = BLOCKED_BASIS_MISSING`。
   - `CM-0005` の `基`→`台`：確認者がこの系列に限り1対1と登録（`COUNT_NOUN_EQUIVALENCE`、`UC-0104`）。
5. **曖昧な総称**：R-11 の `架空ボード` は、`FAM-0001` と `FAM-0002` を候補とする `AMBIGUOUS` の別名 `AL-0004` として登録する。どちらかに寄せない。
6. **類似グループ**：`FAM-0001` と `FAM-0002` は名称が近いので `SG-0001` に入れる（`substitution_policy = NONE`）。統合はしない。

### 4.4 できあがったレコード（抜粋）

```json
{
  "_note": "ALL RECORDS BELOW ARE FICTIONAL PLACEHOLDERS. NO REAL MATERIAL, PRODUCT, DATASET OR FACTOR VALUE.",
  "quarantine_log": [
    {"quarantine_id": "QL-0001", "source_id": "SRC-F03", "reason_code": "LICENSE_UNKNOWN", "affected_record_count": null, "payload_stored": false, "logged_by": "reviewer_a", "logged_at": "2026-11-11", "follow_up": "許諾条件を確認するまで取り込まない"}
  ],
  "material_family": [
    {"family_id": "FAM-0001", "display_name_ja": "架空ボードA", "family_name_key": "架空ボードa", "record_kind": "MATERIAL", "substance_class": "MINERAL_BOARD", "form_factor": "SHEET", "default_declared_unit": "m2", "status": "ACTIVE", "merged_into": null, "license_status": "PERMITTED_PUBLIC", "compartment": "PUBLIC_RELEASE", "created_in_release": "REL-0001", "record_version": 2},
    {"family_id": "FAM-0005", "display_name_ja": "かくうボードA", "family_name_key": "カクウボードa", "record_kind": "MATERIAL", "substance_class": "MINERAL_BOARD", "form_factor": "SHEET", "default_declared_unit": "m2", "status": "MERGED", "merged_into": "FAM-0001", "license_status": "PERMITTED_PUBLIC", "compartment": "PUBLIC_RELEASE", "created_in_release": "REL-0001", "record_version": 2}
  ],
  "family_attribute": [
    {"family_id": "FAM-0001", "attribute_code": "thickness_mm", "role": "VARIANT_AXIS", "required": true, "axis_mode": "ENUMERATED"}
  ],
  "canonical_material": [
    {"canonical_id": "CM-0001", "family_id": "FAM-0001", "identity_string_for_illustration": "v1|FAM-0001|thickness_mm=12", "display_name_ja": "架空ボードA 厚12mm", "declared_unit": "m2", "declared_unit_basis": "PROVISIONAL", "mass_path_status": "NOT_REGISTERED", "similarity_group_id": "SG-0001", "status": "ACTIVE", "merged_into": null, "license_status": "PERMITTED_PUBLIC", "compartment": "PUBLIC_RELEASE", "record_version": 3},
    {"canonical_id": "CM-0002", "family_id": "FAM-0001", "identity_string_for_illustration": "v1|FAM-0001|thickness_mm=9", "display_name_ja": "架空ボードA 厚9mm", "declared_unit": "m2", "declared_unit_basis": "PROVISIONAL", "mass_path_status": "NOT_REGISTERED", "similarity_group_id": "SG-0001", "status": "ACTIVE", "merged_into": null, "license_status": "PERMITTED_PUBLIC", "compartment": "PUBLIC_RELEASE", "record_version": 1},
    {"canonical_id": "CM-0004", "family_id": "FAM-0003", "identity_string_for_illustration": "v1|FAM-0003|", "display_name_ja": "架空充填材X", "declared_unit": "m3", "declared_unit_basis": "PROVISIONAL", "mass_path_status": "BLOCKED_BASIS_MISSING", "similarity_group_id": null, "status": "ACTIVE", "merged_into": null, "license_status": "PERMITTED_PUBLIC", "compartment": "PUBLIC_RELEASE", "record_version": 2},
    {"canonical_id": "CM-0006", "family_id": "FAM-0001", "identity_string_for_illustration": "v1|FAM-0001|thickness_mm=12", "display_name_ja": "かくうボードA 厚12mm", "declared_unit": "m2", "declared_unit_basis": "PROVISIONAL", "mass_path_status": "NOT_REGISTERED", "similarity_group_id": null, "status": "MERGED", "merged_into": "CM-0001", "license_status": "PERMITTED_PUBLIC", "compartment": "PUBLIC_RELEASE", "record_version": 2}
  ],
  "alias": [
    {"alias_id": "AL-0001", "normalized_key": "架空ボードa", "surface_form": "架空ボードA", "context_record_kind": null, "target_level": "FAMILY", "resolution": "UNIQUE", "target_ids": ["FAM-0001"], "alias_type": "CANONICAL_NAME", "match_strength": "CANONICAL", "evidence_kind": "SELF_AUTHORED_GENERIC", "normalizer_version": "norm-0.1", "status": "ACTIVE", "license_status": "PERMITTED_PUBLIC"},
    {"alias_id": "AL-0002", "normalized_key": "カクウボードa", "surface_form": "かくうボードA", "context_record_kind": null, "target_level": "FAMILY", "resolution": "UNIQUE", "target_ids": ["FAM-0001"], "alias_type": "SCRIPT_VARIANT", "match_strength": "CURATED", "evidence_kind": "OBSERVED_IN_PERMITTED_SOURCE", "normalizer_version": "norm-0.1", "status": "ACTIVE", "license_status": "PERMITTED_PUBLIC"},
    {"alias_id": "AL-0004", "normalized_key": "架空ボード", "surface_form": "架空ボード", "context_record_kind": null, "target_level": "FAMILY", "resolution": "AMBIGUOUS", "target_ids": ["FAM-0001", "FAM-0002"], "alias_type": "GENERIC_TERM", "match_strength": "CURATED", "evidence_kind": "OBSERVED_IN_PERMITTED_SOURCE", "normalizer_version": "norm-0.1", "status": "ACTIVE", "license_status": "PERMITTED_PUBLIC"},
    {"alias_id": "AL-0006", "normalized_key": "架空充テン材x", "surface_form": "架空充てん材X", "context_record_kind": null, "target_level": "FAMILY", "resolution": "UNIQUE", "target_ids": ["FAM-0003"], "alias_type": "SCRIPT_VARIANT", "match_strength": "CURATED", "evidence_kind": "OBSERVED_IN_PERMITTED_SOURCE", "normalizer_version": "norm-0.1", "status": "ACTIVE", "license_status": "PERMITTED_PUBLIC"}
  ],
  "unit_conversion": [
    {"conversion_id": "UC-0101", "scope_level": "MATERIAL", "scope_id": "CM-0001", "conversion_kind": "THICKNESS", "from_unit": "m2", "to_unit": "m3", "basis_parameter": "thickness_mm", "basis_origin": "IDENTITY_ATTRIBUTE", "basis_attribute_code": "thickness_mm", "basis_value": null, "basis_value_state": "DERIVED", "basis_source_id": null, "basis_license_status": "PERMITTED_PUBLIC", "invertible": true, "conversion_status": "USABLE"},
    {"conversion_id": "UC-0102", "scope_level": "MATERIAL", "scope_id": "CM-0001", "conversion_kind": "AREA_PER_PIECE", "from_unit": "ct_mai", "to_unit": "m2", "basis_parameter": "area_per_piece_m2", "basis_origin": "EXTERNAL_VALUE", "basis_attribute_code": null, "basis_value": null, "basis_value_state": "MISSING", "basis_source_id": null, "basis_license_status": "UNKNOWN", "invertible": false, "conversion_status": "BLOCKED_BASIS_MISSING"},
    {"conversion_id": "UC-0103", "scope_level": "MATERIAL", "scope_id": "CM-0004", "conversion_kind": "DENSITY", "from_unit": "m3", "to_unit": "kg", "basis_parameter": "density_kg_per_m3", "basis_origin": "EXTERNAL_VALUE", "basis_attribute_code": null, "basis_value": null, "basis_value_state": "MISSING", "basis_source_id": null, "basis_license_status": "UNKNOWN", "invertible": false, "conversion_status": "BLOCKED_BASIS_MISSING"},
    {"conversion_id": "UC-0104", "scope_level": "FAMILY", "scope_id": "FAM-0004", "conversion_kind": "COUNT_NOUN_EQUIVALENCE", "from_unit": "ct_ki", "to_unit": "ct_dai", "basis_parameter": "count_equivalence_ratio", "basis_origin": "CURATED_EQUIVALENCE", "basis_attribute_code": null, "basis_value": "1", "basis_value_state": "USER_ESTIMATE", "basis_source_id": "SRC-S01", "basis_license_status": "PERMITTED_PUBLIC", "invertible": true, "conversion_status": "USABLE"}
  ],
  "merge_event": [
    {"merge_event_id": "ME-0002", "event_kind": "MERGE", "target_level": "MATERIAL", "survivor_id": "CM-0001", "merged_ids": ["CM-0006"], "duplicate_level": "D1_IDENTITY", "survivor_rule_applied": "ACTIVE_OVER_DRAFT", "field_resolutions": [{"field": "display_name_ja", "kept_value": "架空ボードA 厚12mm", "discarded_values": ["かくうボードA 厚12mm"], "rule": "KEEP_SURVIVOR"}, {"field": "license_status", "kept_value": "PERMITTED_PUBLIC", "discarded_values": [], "rule": "MOST_RESTRICTIVE"}], "aliases_created": [], "provenance_links_copied": 1, "license_before": "PERMITTED_PUBLIC", "license_after": "PERMITTED_PUBLIC", "decided_by": "system", "reviewed_by": null, "decided_at": "2026-11-11", "reason_text": "系列の統合（ME-0001）により同一性キーが一致したため", "release_id": "REL-0001"}
  ],
  "similarity_group": [
    {"group_id": "SG-0001", "group_label_ja": "架空ボード類", "grouping_basis": "素材区分と形態が同じで名称が近い。仕様と出典は別", "representative_id": null, "substitution_policy": "NONE", "verification_status": "NOT_VERIFIED", "status": "ACTIVE", "license_status": "PERMITTED_PUBLIC", "compartment": "PUBLIC_RELEASE"}
  ]
}
```

補足：`identity_key` は本来ハッシュ値だが、例では読みやすさのため、ハッシュを取る前の文字列を `identity_string_for_illustration` として示した（実際の表にこの列は無い）。`UC-0104` の値 `1` は「この架空の系列では1基と1台を同じ1個と数える」という人の判断であり、物性値でも係数でもない。

### 4.5 解決手順の結果（`resolve` の例）

| 入力の名称 | 入力の単位 | 結果 | 説明 |
|---|---|---|---|
| `架空ﾎﾞｰﾄﾞＡ　ｔ＝１２` | `ｍ２` | `RESOLVED` → `CM-0001`、警告 `SPEC_UNIT_ASSUMED` | 文字種のゆれは規則だけで吸収。別名の行は増えない |
| `かくうボードA 12ミリ` | `平米` | `RESOLVED` → `CM-0001` | 人が登録した別名 `AL-0002` を経由 |
| `架空ボードA` | `m2` | `STOPPED`：`VARIANT_UNSPECIFIED` | 厚さが無い。既定の厚さを補わない |
| `架空ボード 厚12` | `m2` | `STOPPED`：`ALIAS_AMBIGUOUS` | 候補は `FAM-0001` と `FAM-0002`。1回選べば解決（操作＋1） |
| `架空ボードA 厚15mm` | `m2` | `STOPPED`：`VARIANT_NOT_REGISTERED` | 登録済みの厚さは 9 と 12 だけ |
| `架空ボードA 厚12mm` | `枚` | `STOPPED`：`CONVERSION_BASIS_MISSING` | `UC-0102` の根拠（1枚の面積）が欠損 |
| `架空ボードA 厚12mm` | `m3` | `RESOLVED` → `CM-0001`、警告 `CONVERSION_APPLIED` | `UC-0101` を逆向きに使用。根拠は同一性属性の厚さ |
| `架空充てん材X` | `t` | `STOPPED`：`CONVERSION_BASIS_MISSING` | t→kg は定義値で換算できるが、kg→m3 の密度（`UC-0103`）が欠損 |
| `架空シャッター甲` | `基` | `RESOLVED` → `CM-0005`、警告 `COUNT_EQUIVALENCE_APPLIED` | `UC-0104`（人が登録した等価関係） |
| `架空ボードA 厚12mm` | `M2` | `STOPPED`：`UNIT_UNKNOWN` | 単位欄は大文字小文字を畳まない。この表記を単位の別名に明示登録すれば解決する |
| `架空材Z` | `kg` | `STOPPED`：`ALIAS_UNRESOLVED` | `SRC-F03` は取り込んでいないので、どこにも存在しない |

この例題は、手順が矛盾なく動くことを **架空の文字列で** 確かめたものであり、実データで有効であることの証拠ではない。

---

## 5. 未解決事項と、設計の検証に必要な実データ

### 5.1 未解決事項

| ID | 論点 | 現時点の扱い |
|---|---|---|
| Q1 | 実データにどんな表記ゆれが、どの類型で、どれだけあるか | 不明。N1〜N9 と `alias_type` の類型は想定であり、実データで過不足を確認する |
| Q2 | 材料・系列・正規材料がそれぞれ何件になるか | 不明。件数についての主張はしない |
| Q3 | 類似度のしきい値、換算経路の許容差 | 未設定。正解付きの実ペアが無いと決められない |
| Q4 | 部位区分を同一性から外してよいか（同じ材料でも部位によって係数や境界が変わる出典があるか） | 外す案を提案。変わる出典があれば、係数参照側に文脈を持たせる形で対応する想定 |
| Q5 | 複合品（`COMPOSITE`）の同一性を何で決めるか（構成の一覧か、名称か） | 未決。構成比はそれ自体がデータであり、ライセンスの確認が要る |
| Q6 | 機器（`EQUIPMENT`）の容量・能力の表記をどこまで仕様属性にするか。容量按分は単位換算ではなくモデルだが、その境目 | 未決。計算式研究の結果と合わせて決める |
| Q7 | 「内部利用は許可、再配布は不可」という許諾を得た場合の状態。現行の4状態にはそれを表す値が無い | 区画 `PRIVATE_LICENSED` を予約しただけで、状態の追加は第1章側の判断事項 |
| Q8 | 第三者ツールの名称・分類体系を別名や対応表の根拠に使ってよいか | 許諾の回答があるまで **使わない**（`RESTRICTED` として扱う） |
| Q9 | `MATERIAL.material_id`（行ID）とカタログ側の識別子の名前の衝突 | `canonical_id` と呼び分ける案。既存ファイルは変更しない |
| Q10 | 値の状態の語彙が既存資料の間で少し違う（第1章、第3章、SYS-01） | 本設計は第3章の語彙＋`SYNTHETIC_FICTIONAL` を使用。統一は別途必要 |
| Q11 | 金額を活動量とする行（`CURRENCY`）と価格基準年の扱い | 次元を予約しただけ。存在自体がシート名からの推定で未確認 |
| Q12 | 漢字の読みによる自動照合を入れるか（読み辞書の出所とライセンス） | 入れない案。別名表への手登録で対応 |
| Q13 | 仕様軸 `CONTINUOUS` を採用するか（登録の無い値を受け入れてよいか） | 構造だけ用意。採否は実データと計算式研究の結果による |

### 5.2 検証に必要な実データ

| ID | 必要なデータ | 何を検証するか | 利用の前提 |
|---|---|---|---|
| D-1 | 権利を持つ人から提供された実際の数量内訳書（複数の案件。名称・仕様・単位の列） | N1〜N9 の過不足、解釈できずに残る割合、別名の類型と件数、単位の出現分布 | 提供者の同意の記録。案件・個人を特定できる情報の除去 |
| D-2 | 再利用と再配布が許された独立の係数データまたは環境製品宣言の、材料名と宣言単位の一覧 | 宣言単位の決め方、D4（出典違い）の扱い、係数参照の接点 | 許諾の証拠（`license_evidence_ref`） |
| D-3 | 出典の明らかな換算根拠（密度、単位質量、寸法） | 換算表の構造、経路の食い違いの頻度、適用条件の表し方 | 値ごとの出典とライセンス |
| D-4 | 専門家が「同じ／別物」を判定した材料の組 | 類似度のしきい値、誤統合率、提案の適合率と再現率 | D-1・D-2 から作る |
| D-5 | 設備機器の名称・数え方・容量表記の実例 | 個数単位の扱い、`EQUIPMENT` の同一性 | D-1 と同じ |
| D-6 | 権利者からの回答（名称・分類体系・換算値の利用可否） | Q7・Q8 | `01_COMPLIANCE/PERMISSION_REQUEST.md` の照会 |

実データが届いたら測る指標（**現時点ではどれも未測定**）：自動解決率、曖昧率、未解決率、解釈残りの割合、人の確認が要る件数、停止コード別の件数、正解付きペアでの誤統合件数、1行あたりの操作数。

---

## 6. リスクと、してはならないこと

### 6.1 リスク

| リスク | 内容 | 備え |
|---|---|---|
| 制限付きデータの混入（別名経由） | 別名表や対応表は「名称の一覧」なので、第三者ツールの名称をうっかり写しやすい。記憶に頼って書いても同じことが起きる | 関門（3.1）、`evidence_kind` の必須化、確認者の2人目、I2・I3 の検査 |
| 公開後に取り消せない | 公開リポジトリに一度置いたものは履歴に残る | 関門は置く前に通す。疑わしいものは置かない |
| 誤統合 | 似た名前の別材料を1件にすると、結果が黙って変わる | 自動統合は同一性キーの完全一致だけ。それ以外は人が判断し、取り消せる |
| 畳みすぎ | 正規化規則が強すぎて別の語が同じキーになる | I5 の衝突検査、規則の版管理、全件再正規化の差分確認 |
| 黙った換算 | 根拠の無い換算や既定値での補完は、単位の誤りを隠す | 停止コード。根拠は出典とライセンス付きでしか登録できない |
| 代表での置き換え | 類似グループの代表で計算すると近似になり、過小評価が起き得る | 既定は無効。有効化は P7 の検証後だけ。使った事実を記録 |
| 設計の過剰 | 実データを見ないまま表を増やしすぎている可能性 | 本書は草案。D-1 が届いたら、使われない表・列を削る前提で見直す |
| 手作業の量 | 別名登録と重複判断にどれだけ人手が要るか不明 | D-1 で件数を測ってから体制を決める |
| 語彙の出所 | `substance_class` などの区分語彙が特定の資料の体系に似てしまう | 一般語彙から当方が選ぶ。出所を `provenance_link` に残す |

### 6.2 してはならないこと

1. J-CAT の分類表・コード表・名称一覧・原単位・耐用年数・修繕率・漏洩率・倍率を、写すことも、記憶から書くことも、別名や対応表の根拠にすることもしない。
2. 規格・基準の本文を写さない。
3. ライセンス状態が `PERMITTED_PUBLIC` でない出典の中身を、表にも例にもログにも保存しない（隔離ログは理由だけ）。
4. 係数・換算根拠などの数値を、平均・代表値・上書きで1つにまとめない。
5. 欠損を 0 や 1 や「一般的な値」で補わない。
6. 類似度だけを根拠に自動統合しない。
7. 単位欄の大文字小文字を畳まない。欄をまたいで文字の意味を解釈しない。
8. 識別子を再利用しない。識別子に分類・名称・出典の意味を埋め込まない。第三者のコードを識別子にしない。
9. 受領レコードを書き換えない。統合で行を消さない。
10. 本書の例題や架空データでの動作確認を、実データでの検証と混同しない。材料の件数や適合度を主張しない。
11. 「J-CAT と同じ分類」「互換」と受け取られる表現を使わない。
12. 画面・操作部品・アプリのコードを、この段階で作らない。
13. 既存の 01〜08 章のファイルを書き換えない。
