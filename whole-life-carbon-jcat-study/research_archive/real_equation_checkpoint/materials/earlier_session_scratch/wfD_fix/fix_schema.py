# -*- coding: utf-8 -*-
"""taxonomy_schema.json にレビュー指摘の修正を適用する（バックアップから読み、本体へ書く。再実行可）。"""
import json

BK = "/tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/wfD_fix/backup/"
OUT = "/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/07_MATERIAL_TAXONOMY/"
S = json.load(open(BK + "taxonomy_schema.json", encoding="utf-8"))
R = S["records"]


def F(name, typ, required, description, required_when=None):
    d = {"name": name, "type": typ, "required": required}
    if required_when:
        d["required_when"] = required_when
    d["description"] = description
    return d


def fld(r, name):
    for f in R[r]["fields"]:
        if f["name"] == name:
            return f
    raise KeyError((r, name))


def setf(r, fname, **kw):
    f = fld(r, fname)
    for k, v in kw.items():
        if v is None:
            f.pop(k, None)
        else:
            f[k] = v
    return f


def delf(r, name):
    n = len(R[r]["fields"])
    R[r]["fields"] = [f for f in R[r]["fields"] if f["name"] != name]
    assert len(R[r]["fields"]) == n - 1, (r, name)


def addf(r, after, *new):
    fs = R[r]["fields"]
    i = [f["name"] for f in fs].index(after)
    R[r]["fields"] = fs[: i + 1] + list(new) + fs[i + 1:]


# ---------------------------------------------------------------- header
S["schema_version"] = "0.2.0-draft"
S["notes"].append("0.2.0-draft は、独立レビューの指摘（REVIEW_LOG.md）を反映した版である。レビューは内部整合だけを対象とし、実データによる検証は依然として行っていない。")

c = S["conventions"]
c["id_rule"] = ("ID は「接頭辞-6桁以上の連番」とし、親・階層・名称・単位・出典側のコードを埋め込まない。"
                "接頭辞はレコードの種別（分類ノードでは軸も）だけを表す。軸は変わらないので、移動で ID が変わることは無い。"
                "ID の大小から順序・新旧を読み取らない。再利用しない。レコードは物理削除しない。出典側のコードを ID に使わない。")
c["id_prefixes"].update({
    "CD": "curation_decision",
    "SEL": "selection",
    "PRJ": "案件（calc_row.project_id。案件の台帳は本定義の範囲外）",
    "ZN": "ゾーン（calc_row.zone_id。語彙は未定義）",
})
c["hash_rule"] = ("identity_key と content_hash は、定められた順の配列を正規化した JSON（UTF-8、要素の間に空白なし、"
                  "非 ASCII 文字はエスケープしない、欠損は null）にして SHA-256 を取る。"
                  "区切り文字による連結はしない（値に区切り文字が含まれても衝突しないようにするため）。")
c["record_status_meaning"] = {
    "DRAFT": "提案。計算にも公開にも使えない。",
    "ACTIVE": "有効。計算に使える唯一の状態。",
    "DEPRECATED": "統合以外の理由で廃止した（後継があれば replaced_by）。行は残す。",
    "MERGED": "統合されて退いた（merged_into が統合先）。行は残す。",
    "QUARANTINED": "許諾または内容に疑義があり、確認が済むまで計算にも公開にも使わない。行は残す。",
    "RESERVED": "分類ノードの予約。算定範囲に含めるかを決めるまで使えない。",
}
c["core"] = ("records の core = true は、次段階の最初の作業（実データの受領、名称の正規化、重複の判定）に要る最小の組を示す。"
             "false は、実データを見てから要否を決めるもの（配置、アセンブリ、束縛、版、計算行、操作の計測など）。重要度の印ではない。")

# ---------------------------------------------------------------- enums
E = S["enums"]
E["provenance_role"] = ["RELIED_ON", "OBSERVED_MATCH"]
E["lifecycle_stage"] = ["A1", "A2", "A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "C1", "C2", "C3", "C4"]
E["item_kind"] = ["BULK_MATERIAL", "SHAPED_PRODUCT", "EQUIPMENT_UNIT", "LINEAR_ITEM", "COMPOSITE_ITEM"]
E["material_kind"] = ["SPECIFIC", "PRODUCT_SPECIFIC"]
E["attribute_quantity_kind"] = ["DIMENSION", "NOMINAL_SIZE", "GRADE_CLASS", "CAPACITY_CLASS", "LABEL"]
E["canonical_format"] = ["DECIMAL_PLAIN", "ENUM_CODE", "TEXT_NFKC"]
E["affects"] = ["FACTOR", "MASS_CONVERSION", "SERVICE_LIFE", "REPAIR_RATE", "EOL_ROUTE", "UNKNOWN"]
E["param_source"] = ["USER_INPUT", "SPEC_TOKEN"]
E["assembly_kind"] = ["COMPOSITE_PRODUCT", "LAYERED_ASSEMBLY", "SYSTEM_KIT"]
E["binding_scope_kind"] = ["CANONICAL_MATERIAL", "PLACEMENT", "MATERIAL_TYPE", "FUNCTION_NODE"]
E["param_kind"] = ["FACTOR", "SERVICE_LIFE", "REPAIR_RATE", "EOL_ROUTE", "WASTE_RATE"]
E["intake_status"] = ["ACCEPTED", "DUPLICATE_RAW", "REJECTED_FORMAT", "OUT_OF_SCOPE"]
E["survivor_rule"] = ["ACTIVE_OVER_DRAFT", "MORE_COMPLETE_IDENTITY", "EARLIER_CREATED_RELEASE", "REVIEWER_DECISION"]
E["quantity_basis"] = ["DESIGN", "ORDERED", "AS_BUILT", "UNKNOWN"]
E["bound_from"] = ["ROW_OVERRIDE", "CANONICAL_MATERIAL", "PLACEMENT", "MATERIAL_TYPE", "FUNCTION_NODE", "NONE"]
E["normalization_flag"] = ["SPEC_UNIT_ASSUMED", "SPEC_TOKEN_UNASSIGNED", "RESIDUAL_TEXT", "UNIT_UNKNOWN",
                           "MATCHED_BY_VARIANT_KEY", "ALIAS_UNRESOLVED", "ALIAS_AMBIGUOUS"]
E["decision_kind"] = ["ALIAS_REGISTERED", "NEW_TYPE_CREATED", "AMBIGUITY_RESOLVED", "SPEC_UNIT_CONFIRMED",
                      "SPEC_TOKEN_ASSIGNED", "UNIT_VARIANT_CONFIRMED", "PLACEMENT_DECIDED", "MARKED_OUT_OF_SCOPE",
                      "PROVENANCE_ADD_REJECTED"]
E["ref_kind"] = ["ALIAS", "PLACEMENT", "PARAM_BINDING", "UNIT_CONVERSION", "ASSEMBLY_COMPONENT", "SIMILARITY_LINK",
                 "CANONICAL_MATERIAL"]
E["invariant_result"] = ["PASS", "FAIL", "NOT_RUN"]

sc = E["stop_code"]
for code, after in [("SPEC_UNIT_UNCONFIRMED", "VARIANT_NOT_REGISTERED"),
                    ("PARAM_SOURCE_CONFLICT", "CONVERSION_PATH_CONFLICT"),
                    ("BINDING_BOUNDARY_CONFLICT", "FACTOR_STAGE_MISMATCH"),
                    ("BINDING_LEVEL_CONFLICT", "BINDING_BOUNDARY_CONFLICT")]:
    sc.insert(sc.index(after) + 1, code)
wc = E["warning_code"]
wc[wc.index("BINDING_LEVEL_CONFLICT")] = "BINDING_LEVEL_ORDER_APPLIED"
wc.append("QUANTITY_BASIS_UNKNOWN")

# ---------------------------------------------------------------- forbidden values
fv = S["forbidden_value_fields"]
fv["description"] = ("次の量の「値」を入れる項目を、カタログ側のどのレコードにも作らない（版を作るたびに項目名で検査する）。"
                     "参照 ID（*_ref）と状態だけを持つ。項目名の検査だけでは防げない抜け道は、"
                     "仕様属性の量の種類（spec_attribute.quantity_kind）の制限と、自由記述の項目の確認で塞ぐ。")
fv["permitted_numbers"] = [
    "単位の定義で決まる倍率（unit_def.to_base_factor）",
    "同一性に効く仕様値（canonical_material.attribute_values。quantity_kind が許す寸法・呼び・等級・区分の表示に限る。物性値・性能値・年数・率は入れない）",
]
fv["free_text_fields_to_scan"] = {
    "description": "次の自由記述・オブジェクトの項目は、項目名の検査では値の転記を防げない。版を作るたびに ID 以外の数字を含む値を抜き出し、人が「値の転記でない」と確認するまで公開しない。",
    "fields": ["note", "definition", "includes", "excludes", "representative_basis_note", "rights_note", "applicability",
               "context_condition", "stage_note", "basis", "proxy_reason", "rank_reason", "intake_note", "outcome", "reason"],
}

# ---------------------------------------------------------------- stage requirements
stage_req = {
    "note": "暫定。係数参照を使う概念式が必要とする段階。束縛の stages がこの集合と一致しない行は FACTOR_STAGE_MISMATCH で止める（足りなければ過小評価、余れば他の段階の式との二重計上になる）。計算研究側の式の定義が確定したら合わせる。",
    "by_param_kind": {
        "FACTOR": {"required_stages": ["A1", "A2", "A3"], "used_by_formulas": ["A13-01", "A13-03"]}
    },
}

# ---------------------------------------------------------------- common fields
cf = {f["name"]: f for f in S["common_fields"]["fields"]}
cf["license_status"]["description"] = ("実効ライセンス状態。来歴のうち role = RELIED_ON の出典の中で最も制限の強い状態から計算で求め、手入力しない。"
                                       "参照先の値（係数・換算根拠）の状態は、ここではなく param_license_status・basis_license_status に持つ。")
cf["provenance"]["description"] = ("来歴。1件以上。各要素は source_id、raw_id（無ければ null）、derivation（enum:derivation）、"
                                   "role（enum:provenance_role。RELIED_ON＝内容の根拠にした出典／OBSERVED_MATCH＝同じ内容を観測しただけの出典）、"
                                   "via_merge_event_id（統合で引き継いだ要素はその統合の ID、それ以外は null）。RELIED_ON が1件以上要る。"
                                   "実効ライセンスを悪化させる RELIED_ON の追加は行わず、理由を curation_decision（PROVENANCE_ADD_REJECTED）に残す。"
                                   "自分で付けた名称・判断は origin_kind = SELF_AUTHORED の出典を指す。")
cf["reviewed_by"]["description"] = "確認者。created_by と別人（INV-22）。"
cf["status"]["description"] = "レコードの状態（各状態の意味は conventions.record_status_meaning）。ACTIVE だけが計算に使える。RESERVED は分類ノードの予約にだけ使う。"
fields = S["common_fields"]["fields"]
i = [f["name"] for f in fields].index("record_version")
fields.insert(i + 1, F("created_by", "string", True, "作成者。"))

# ---------------------------------------------------------------- classification_node
r = "classification_node"
R[r]["core"] = False
R[r]["purpose"] = "分類体系のノード。部位軸（大区分→部位グループ→部位要素）と、品目軸の第1階層（素材・品目系統）を同じ形で持つ。classification_tree.json の nodes の1要素。"
R[r]["primary_key"] = ["node_id"]
setf(r, "id", name="node_id", description="不変 ID。部位軸は FN-、品目軸は IN-（接頭辞は種別と軸だけを表す）。")
delf(r, "level")
setf(r, "level_kind", description="階層の種類。階層の番号は classification_tree.json の levels から導き、ノードには二重に持たない。")
setf(r, "parent", description="親ノードの node_id。DIVISION と SUBSTANCE_CLASS は null。GROUP の親は DIVISION、ELEMENT の親は GROUP。移動（親の変更）では node_id を変えない。")
setf(r, "code", description="人が読むための英語の符号。（軸、階層）の中で一意。集計の見出しに使う階層では、有効化後に変更しない。")
setf(r, "definition", description="このノードに入るものの定義（1〜2文）。その階層の分類原理だけで書く。定義を書けないノードは作らない。")
setf(r, "allowed_item_kinds", description="素材・品目系統だけが持つ。配下の品種に許す item_kind（INV-18）。草案の値は暫定。")
delf(r, "sort_key")
R[r]["constraints"] = [
    "GROUP の親は DIVISION、ELEMENT の親は GROUP。配置（placement）は ELEMENT だけを指す。ACTIVE のノードの親は ACTIVE。",
    "定義（含むもの）を書けない受け皿のノード（「未分類」「その他」など）は、予約としても作らない。配置できない行は calc_row.placement_state = UNPLACED、系統を決められない品種は material_type.substance_class_id = null とし、どちらも集計で別掲する。",
]

# ---------------------------------------------------------------- material_type
r = "material_type"
R[r]["core"] = True
setf(r, "substance_class_id", type="string|null",
     description="属する素材・品目系統（classification_node、axis = ITEM）。どの系統の定義にも当てはまらない間は null（品目未分類）とし、近い系統に寄せない。品目別集計では「品目未分類」として別掲する。")
setf(r, "item_kind", description="品目の種別。属する系統の allowed_item_kinds に含まれること（INV-18）。種別ごとの計算行の形（数量の種類、付随して要る入力）は未定義（README U-25）。")
setf(r, "representative_material_id",
     description="代表レコード。同じ品種の ACTIVE な正規材料レコードを指名する（代表専用のレコードや、メンバーの値を合成した代表は作らない）。null のとき、この品種は粗い指定ができない。")
setf(r, "merged_into", description="統合先の type_id。連鎖の深さは1。統合できるのは INV-17 の前提条件を満たす組だけ。統合後は配下の正規材料レコードの identity_key を計算し直す。")
R[r]["constraints"] = [
    "品種を分けるのは物が違うときだけである。宣言単位は品種ごとに1つ。出典によって単位が違うレコード（表記・数え方・次元のどれが違っても）は別の品種にせず、単位換算として登録する（根拠が無ければ BLOCKED_BASIS_MISSING）。",
    "代表レコードは同じ品種に属し、ACTIVE でなければならない。",
]

# ---------------------------------------------------------------- spec_attribute
r = "spec_attribute"
R[r]["core"] = True
setf(r, "attribute_code", description="属性の識別子（英小文字と下線）。単位は unit_code が正であり、名前に単位が含まれていても名前からは読まない。")
addf(r, "label", F("quantity_kind", "enum:attribute_quantity_kind", True,
                   "何の量か。DIMENSION＝寸法（長さ・面積・体積）／NOMINAL_SIZE＝呼び寸法・口径／GRADE_CLASS＝等級・強度区分／CAPACITY_CLASS＝容量などの区分（区分の名前であり測定値ではない）／LABEL＝それ以外の名称的な区別。密度・単位質量などの物性値、性能値、年数、率は属性にできない（INV-04）。"))
setf(r, "unit_code", description="数値の単位（unit_def.unit_code）。DECIMAL は quantity_kind が DIMENSION または NOMINAL_SIZE のときだけ使え、単位の次元は LENGTH・AREA・VOLUME に限る。")
setf(r, "canonical_format", type="enum:canonical_format",
     description="値の正規形式。DECIMAL_PLAIN＝指数表記なし・末尾の0なしの10進文字列／ENUM_CODE＝allowed_values の符号／TEXT_NFKC＝互換正規化した文字列。同一性キーの計算に使う。")
setf(r, "affects", description="この属性で変わる計算行の項目。実データを見るまで UNKNOWN とし、UNKNOWN の属性は IDENTITY として扱う（誤統合を避ける側に倒す）。")
addf(r, "allowed_values", F("allowed_values_provenance", "array<object>|null", False,
                            "許容値の系列の来歴（common_fields の provenance と同じ形）。出典の製品系列を写した系列は、その出典の許諾に従う。",
                            required_when="allowed_values が null でない"))
setf(r, "parse_patterns", description="名称・仕様欄から読み取るための表記規則。各要素は prefix_tokens、suffix_tokens、assumed_unit_code。assumed_unit_code で単位を補った値は、人が確認するまで SPEC_UNIT_UNCONFIRMED で止まる。実データの表記を見てから定める。")
R[r]["constraints"].append("role = IDENTITY の属性の集合（attribute_code・unit_code）は、品種の統合の前提条件（INV-17）に使う。")

# ---------------------------------------------------------------- canonical_material
r = "canonical_material"
setf(r, "material_kind", description="SPECIFIC＝一般品の個別仕様／PRODUCT_SPECIFIC＝特定製品。代表は種類として持たず、品種の representative_material_id で既存のレコードを指名する。")
delf(r, "derivation_rule")
setf(r, "identity_key", description="同一性キー。配列 [\"v2\", type_id, material_kind, [[attribute_code, 値], …（attribute_code の昇順）], product_key（無ければ null）] を conventions.hash_rule に従って SHA-256 にしたもの。ACTIVE の中で一意。")
setf(r, "mass_path_status", description="質量への換算経路（unit_conversion）の有無。輸送・廃棄段階に必要。計算で求める。経路が無い材料は、その段階が「0」ではなく「計算できない」になる。")
R[r]["constraints"][0] = "同じ identity_key のレコードが既にあれば新しく作らず、来歴を追加する（実効ライセンスを悪化させる追加はしない。common_fields.provenance）。"

# ---------------------------------------------------------------- alias
r = "alias"
delf(r, "created_by")
setf(r, "context_node_id", description="この別名が有効な部位ノード。null は文脈を問わない。同じキーに文脈付きの行と null の行があり、文脈が一致するときは文脈付きの行を使う。")
R[r]["constraints"] = [
    "ACTIVE の中で（normalized_key、context_node_id）は一意。",
    "別名には肯定的な根拠（evidence_kind）が要る。別名の整理の作業中は制限付きの出典を参照せず、その旨を curation_decision に残す。「制限付きの出典に載っていない」ことは、その出典の中身を保存しない以上、機械的には検査できないので、手続きで担保する。",
]

# ---------------------------------------------------------------- unit_def
R["unit_def"]["core"] = True

# ---------------------------------------------------------------- unit_conversion
r = "unit_conversion"
setf(r, "basis_parameter", description="根拠パラメータの名前（例 thickness、density、area_per_piece）。単位は名前に埋め込まず、basis_unit_code に持つ。")
addf(r, "basis_parameter", F("basis_unit_code", "string|null", False,
                             "根拠値の単位（unit_def.unit_code）。IDENTITY_ATTRIBUTE では属性の unit_code と一致すること。換算の定数は、この単位と from_unit・to_unit の to_base_factor から導き、項目名や説明文からは読まない。EXTERNAL_LEDGER の根拠値は「to_unit ÷ from_unit」の単位で表されたものに限り（台帳の単位がそれと違えば使わない）、CURATED_EQUIVALENCE は単位を持たないので、どちらも null。",
                             required_when="basis_origin が IDENTITY_ATTRIBUTE または ROW_PARAMETER"))
setf(r, "basis_origin", description="根拠の出所。IDENTITY_ATTRIBUTE＝正規材料レコードの仕様値（quantity_kind = DIMENSION の属性に限る）／ROW_PARAMETER＝行ごとに与える値／CURATED_EQUIVALENCE＝自分で登録した数え方の等価（COUNT_NOUN_EQUIVALENCE に限る。1対1）／EXTERNAL_LEDGER＝外部のパラメータ台帳。")
setf(r, "param_source_order", description="行ごとの値の取得元（片方にしか無いときにどちらから取るか）。両方にあって値または単位が違えば PARAM_SOURCE_CONFLICT で停止する。どちらにも無ければ CONVERSION_BASIS_MISSING で停止する。")
delf(r, "curated_ratio")
addf(r, "basis_ref", F("equivalence_evidence_kind", "enum:evidence_kind|null", False,
                       "等価とみなした根拠の種類。等価は同じ物の数え方の違い（1対1）に限る。入数（1箱あたりの枚数など）は製品の値なので、等価ではなく EXTERNAL_LEDGER で扱う。",
                       required_when="basis_origin = CURATED_EQUIVALENCE"))
R[r]["constraints"] = [
    "USABLE にできるのは、根拠が MISSING でなく、basis_license_status = PERMITTED_PUBLIC のときだけ。",
    "根拠の無い換算も BLOCKED_BASIS_MISSING のまま登録する（その単位が実際に現れるという事実を残す）。",
    "材料固有の換算は最大2段まで。使える経路が複数あるときは、許容差が未設定の間は常に CONVERSION_PATH_CONFLICT で停止する（許容差を定めた後は、差が許容差を超えたときだけ停止する）。",
    "質量は、この表の質量への経路（DENSITY、MASS_PER_AREA、MASS_PER_LENGTH、MASS_PER_PIECE）だけから得る。param_binding には質量換算の種別を置かない（取得元を1系統にして食い違いを作らない）。",
    "統合で退くレコードに付いていた換算は消さず、出典を保ったまま残す側の別の行として移す（merge_event.repointed_refs に記録する）。",
    "機器の容量による按分のようなモデル計算は単位換算ではないので、この表に入れない。",
]

# ---------------------------------------------------------------- assembly
r = "assembly"
R[r]["core"] = False
R[r]["purpose"] = "アセンブリ／束。1回の指定で複数の計算行を作るための定義。複合品（出典に1件として現れる製品）と、一式（層構成、機器と付属の一式）を同じ形で持つ。"
setf(r, "assembly_kind", description="COMPOSITE_PRODUCT＝複合品の構成／LAYERED_ASSEMBLY＝層構成・納まりの一式／SYSTEM_KIT＝機器と付属の配管・配線などの一式。")
addf(r, "driver_unit", F("driver_measure", "string|null", False,
                         "基準数量が何を測ったものか（どの面・どの長さか、開口などを控除するか）。語彙は未定義（README U-22）。null の間は DRIVER_IDENTITY の構成要素を持てない。"))
setf(r, "context_condition", description="この構成が成り立つ案件条件（例：主要構造）。キーは既存入力項目の PROJECT 群。根拠の無いものは置かない。")

# ---------------------------------------------------------------- assembly_component
r = "assembly_component"
R[r]["core"] = False
setf(r, "ratio_basis", description="構成量の決め方。DRIVER_IDENTITY＝基準数量そのもの（単位と測り方が基準数量と同じときだけ。INV-12）／GEOMETRIC_DEFINITION＝寸法から定義で決まる／ROW_PARAMETER＝利用者が行ごとに与える／EXTERNAL_LEDGER＝外部台帳の値（出典と許諾の確認が必要）／PLACEHOLDER＝未定。")
setf(r, "ratio_param_name", description="必要なパラメータ名（例 thickness）。単位は ratio_param_unit_code に持つ。")
addf(r, "ratio_param_name",
     F("ratio_param_unit_code", "string|null", False, "パラメータの単位（unit_def.unit_code）。定数はこの単位の to_base_factor から導く。",
       required_when="ratio_basis が GEOMETRIC_DEFINITION または ROW_PARAMETER"),
     F("component_measure", "string|null", False, "構成要素の数量が何を測ったものか。assembly.driver_measure と同じ語彙。",
       required_when="ratio_basis = DRIVER_IDENTITY"))
setf(r, "placement_id", description="展開した行に付ける配置。null は対象の品種の既定の配置（is_primary）で、その場合は展開した行の defaulted_fields に placement_id を載せる。")
delf(r, "default_included")
setf(r, "optional", description="構成として省けるか。省いた構成要素は行を消さず、除外の記録を残す。")

# ---------------------------------------------------------------- placement
r = "placement"
R[r]["purpose"] = "配置。部位要素と品種の許される組合せ（多対多）。部位から品種へ辿る経路を兼ねる（選択木を別に持たない）。"
setf(r, "entry_unit", description="この部位で数量を入れる単位。宣言単位そのもの、または宣言単位への換算が登録されている単位に限る。入力に単位が無くこの値で補った行は、defaulted_fields に entry_unit を載せる。")
setf(r, "context_condition", description="この組合せが成り立つ案件条件（例：主要構造）。根拠の無いものは置かない。")
delf(r, "sort_key")

# ---------------------------------------------------------------- similarity_link
R["similarity_link"]["core"] = True

# ---------------------------------------------------------------- param_binding
r = "param_binding"
R[r]["purpose"] = "係数・耐用年数・修繕率・廃棄経路・施工端材率への参照。値は持たない。値・版・地域・時点・出典・許諾は外部のパラメータ台帳の側で管理する。質量への換算はここではなく unit_conversion で扱う。"
setf(r, "scope_kind", description="束縛する水準。特定製品は CANONICAL_MATERIAL（material_kind = PRODUCT_SPECIFIC）として束縛し、製品だけの水準は置かない。FUNCTION_NODE の中では ELEMENT → GROUP → DIVISION の順に探す。")
setf(r, "param_kind", description="パラメータの種別。FACTOR は品目側（CANONICAL_MATERIAL／MATERIAL_TYPE）にだけ束縛できる。耐用年数と更新周期を同じ種別で扱うかは未決定（README U-07）。")
setf(r, "binding_unit", description="係数の分母単位（unit_def.unit_code）。台帳の記載と一致すること。品種の宣言単位と同じか、宣言単位からこの単位への USABLE な換算があること。どちらでもなければ FACTOR_UNIT_MISMATCH で停止する。")
setf(r, "stages", type="array<enum:lifecycle_stage>",
     description="係数が含む段階（1段階ずつの値の集合。範囲の表記は使わない）。語彙は第4章の概念式が使う段階の範囲に限る。台帳の記載と一致すること（語彙に無い段階を含む係数は、語彙を足すまで束縛しない）。factor_stage_requirements の集合と一致しなければ FACTOR_STAGE_MISMATCH で停止する。")
addf(r, "stages", F("boundary_ref", "string|null", False,
                    "係数が対象に含む範囲（付属品・下地・施工の有無など。既存入力項目の FACTOR.factor_boundary に相当）についての台帳の記載への参照。確認できていなければ null。"))
addf(r, "proxy_reason", F("proxy_link_id", "string|null", False,
                          "代用を許可した similarity_link（relation = PROXY_CANDIDATE、substitution_policy = ALLOWED_WITH_FLAG）。これが無い PROXY の束縛は ACTIVE にできない（INV-19）。",
                          required_when="link_basis = PROXY"))
addf(r, "value_state", F("param_license_status", "enum:license_status", True,
                         "参照先の値（台帳側）のライセンス状態。未束縛は UNKNOWN。レコード自身の license_status（来歴から計算する。INV-02・INV-03 の対象）とは別で、INV-14 はこちらを見る。"))
setf(r, "priority_rank", description="同じ水準・同じ種別・同じ条件に複数の参照があるときの採用順。分母単位・段階・対象範囲（boundary_ref）がすべて同じ参照どうしにだけ使える。どれかが違う参照が並んだときは、順位で選ばず BINDING_BOUNDARY_CONFLICT で停止する。出典の違う参照は別の行として並べ、平均も統合もしない。")
addf(r, "priority_rank",
     F("rank_decided_by", "string|null", False, "順位を決めた人。", required_when="priority_rank が null でない"),
     F("rank_reason", "string|null", False, "順位の理由。", required_when="priority_rank が null でない"))
R[r]["constraints"] = [
    "どの水準にも束縛が無ければ MISSING のままにし、既定値を作り出さない。",
    "束縛として数えるのは、ACTIVE で param_ref が null でない行だけである。参照の無い下書きは、計算行の bound_from に現れない。",
    "param_license_status が PERMITTED_PUBLIC でない束縛を使う行は計算しない。",
    "統合で退くレコードに付いていた束縛は消さず、出典を保ったまま残す側の別の行として移す（merge_event.repointed_refs に記録する）。その結果、境界の違う参照が並べば BINDING_BOUNDARY_CONFLICT で止まる。",
]

# ---------------------------------------------------------------- source
R["source"]["core"] = True

# ---------------------------------------------------------------- raw_record
r = "raw_record"
R[r]["core"] = True
R[r]["purpose"] = ("受領レコード。カタログ用に受領した名称・仕様・単位・見出しを、受領した姿のまま保存し、更新・削除しない。"
                   "係数などの数値列も、案件の数量も写さない（案件の数量行は calc_row になり、同一行の重複の扱い（D0）を受けない）。"
                   "正規化結果（normalized_record）はここから再生成できる派生物とする。")
setf(r, "content_hash", description="配列 [source_id, name_text, spec_text, unit_text, class_text] を conventions.hash_rule に従って SHA-256 にしたもの（同一行の重複の判定用）。")
setf(r, "duplicate_of_raw", description="同一ハッシュの先行レコード。出現回数はこれを数えて求める派生値であり、先行レコードには書き込まない。")
delf(r, "occurrence_count")
setf(r, "intake_status", description="受理／同一行の重複（別レコードとして残し、以降の処理に進めない）／形式不備／対象外（材料でない行。件数を別掲する）。")
addf(r, "intake_status", F("intake_note", "string|null", False, "受理しなかった理由。",
                           required_when="intake_status が REJECTED_FORMAT または OUT_OF_SCOPE"))
R[r]["constraints"] = [
    "同じ content_hash の後続の行は、集約せず DUPLICATE_RAW の別レコードとして残す（所在を失わないため）。先行レコードは書き換えない。",
    "この扱い（D0）はカタログ用の受領に限る。案件の数量内訳の行は、同じ名称・単位でも行ごとに calc_row にする。",
]

# ---------------------------------------------------------------- normalized_record (new)
normalized_record = {
    "core": True,
    "purpose": "正規化結果。受領レコード × 正規化規則の版ごとの派生物で、受領レコード・規則・人の判断記録から再生成できる。人の判断そのものは持たず、curation_decision に置く。同一行の重複と対象外の受領レコードには作らない。",
    "primary_key": ["raw_id", "normalizer_version"],
    "fields": [
        F("raw_id", "string", True, "元の受領レコード。"),
        F("normalizer_version", "string", True, "正規化規則の版。"),
        F("name_key", "string", True, "名称キー（名称欄の規則 N1〜N8 の結果）。"),
        F("variant_keys", "array<string>", True, "派生キー（照合用の索引。空配列可）。"),
        F("spec_tokens", "array<object>", True, "切り出した仕様トークン（空配列可）。各要素は attribute_code（割り当てられなければ null）、value、unit_code、unit_assumed（単位を仮定したか）、matched_text。"),
        F("unit_code", "string|null", True, "単位欄の解析結果（unit_def.unit_code）。解釈できなければ null。"),
        F("residual_text", "string", True, "どの規則でも解釈できずに残った文字列（N9）。空でなければ未完了とし、黙って捨てない。"),
        F("flags", "array<enum:normalization_flag>", True, "正規化と解決の過程で立った印（空配列可）。"),
        F("resolved_to", "string|null", True, "解決した正規材料レコード。未解決は null（下書きのレコードを自動では作らない）。"),
        F("resolved_in_release", "string|null", True, "解決に使ったカタログの版。未解決は null。"),
    ],
    "constraints": [
        "別名が無い名称は ALIAS_UNRESOLVED のまま止め、品種・正規材料レコードの下書きを自動では作らない。別名の登録か新しい品種の作成は人が判断し、curation_decision に残す。",
    ],
}

# ---------------------------------------------------------------- curation_decision (new)
curation_decision = {
    "core": True,
    "purpose": "人の判断記録（追記専用）。正規化の規則では決まらないことを人が決めた事実を残す。INV-15 の「人の判断記録」は、このレコードと merge_event・alias・similarity_link を指す。",
    "primary_key": ["decision_id"],
    "fields": [
        F("decision_id", "string", True, "不変 ID（CD-）。"),
        F("decision_kind", "enum:decision_kind", True, "判断の種類。別名の登録／新しい品種の作成／複数候補の解消／仮定した単位の確定／仕様トークンの割り当て／単位違いの確認／配置の決定／対象外の判定／来歴の追加の見送り。"),
        F("raw_ids", "array<string>", True, "判断の対象になった受領レコード（空配列可）。"),
        F("subject_ids", "array<string>", True, "判断の結果として作成・変更したレコードの ID（空配列可）。"),
        F("outcome", "string", True, "決めた内容。値（係数・物性値など）は書かない。"),
        F("restricted_source_not_consulted", "boolean", True, "この判断の作業中に制限付きの出典を参照していないことの申告。false の判断は、別名・分類・換算の根拠にできない。"),
        F("decided_by", "string", True, "判断者。"),
        F("reviewed_by", "string|null", False, "確認者。判断者と別人（INV-22）。"),
        F("decided_at", "date", True, "判断日。"),
        F("normalizer_version", "string", True, "判断の時点の正規化規則の版。"),
        F("release_id", "string", True, "反映した版。"),
    ],
    "constraints": [],
}

# ---------------------------------------------------------------- merge_event
r = "merge_event"
R[r]["core"] = True
R[r]["purpose"] = "統合イベント（追記専用）。重複の統合と、その取り消し（分割）を記録する。統合で行を消さない。取り消しに要る情報（付け替えた参照、引き継いだ来歴）をここに持つ。"
addf(r, "event_kind", F("reverts_event_id", "string|null", False, "取り消す統合イベント。survivor_id・merged_ids はそのイベントと同じ値にする。",
                        required_when="event_kind = SPLIT"))
setf(r, "survivor_id", description="残すレコード（SPLIT では、取り消す統合で残した側）。")
setf(r, "merged_ids", description="統合されて退くレコード（SPLIT では、元に戻すレコード）。")
setf(r, "duplicate_level", type="enum:duplicate_level|null", required=False, required_when="event_kind = MERGE",
     description="どの水準の重複として統合したか。")
setf(r, "survivor_rule_applied", type="enum:survivor_rule|null", required=False, required_when="event_kind = MERGE",
     description="残す側を決めた規則。EARLIER_CREATED_RELEASE は作成した版の順で決める（ID の大小は使わない）。規則で決まらなければ REVIEWER_DECISION とし、理由を reason に残す。")
setf(r, "field_resolutions", description="項目ごとの決着（SPLIT では空配列）。各要素は field、kept_value、discarded_values、rule（enum:field_resolution_rule）。FILL_FROM_MERGED_IF_NULL で埋めた項目は、分割のときに null へ戻す。")
setf(r, "aliases_created", description="この統合で作った別名（退く側の名称を別名に移す。SPLIT では空配列）。分割のときは、取り消す統合が作った別名を廃止（DEPRECATED）にする。")
addf(r, "aliases_created",
     F("repointed_refs", "array<object>", True, "この統合で残す側へ付け替えた参照（空配列可）。各要素は ref_kind（enum:ref_kind）、ref_id、field、from_id、to_id。別名・配置・束縛・換算・構成要素・類似関係と、品種の統合では配下の正規材料レコードの type_id を含む。退く側の束縛・換算は消さず、出典を保ったまま残す側の別の行として移す。SPLIT では、取り消す統合の repointed_refs を逆向きにしたものを載せる。"),
     F("affected_descendant_ids", "array<string>", True, "品種の統合で identity_key を計算し直した配下の正規材料レコード（空配列可）。"),
     F("caused_by_event_id", "string|null", False, "品種の統合に伴って配下の正規材料レコードを統合した場合の、元になった品種の統合イベント。その確認者の承認の範囲に含まれる。"))
setf(r, "license_before", type="enum:license_status|null", required=False, required_when="event_kind = MERGE")
setf(r, "license_after", type="enum:license_status|null", required=False, required_when="event_kind = MERGE")
setf(r, "reviewed_by", required_when="duplicate_level が D2・D3・D4、または event_kind = SPLIT")
setf(r, "reason", description="統合または分割の理由。")
R[r]["constraints"] = [
    "自動で統合してよいのは、正規化後に identity_key が完全一致する場合（D1）だけ。",
    "係数参照・換算根拠などの数値に関わる参照は、平均・代表値の選択・上書きで1つにまとめず、出典ごとに別の行として残す。",
    "品種の統合は、宣言単位・item_kind・同一性属性の集合が同じ組に限る（INV-17）。満たさない組は統合せず、similarity_link にとどめる。",
    "品種の統合に伴う配下の正規材料レコードの統合（D1）は、元の統合イベントの確認者の承認の範囲に含め、caused_by_event_id と affected_descendant_ids で結ぶ。",
    "分割（SPLIT）は、取り消す統合の repointed_refs を逆向きに戻し、FILL_FROM_MERGED_IF_NULL で埋めた項目を null に戻し、via_merge_event_id がその統合を指す来歴の要素を外す。統合の後に残す側へ加えた変更は残す側に残る。",
    "統合で退いたレコードを指す計算行は、残す側で解決し直した参照（係数参照・分母単位・段階・対象範囲・耐用年数・修繕率・廃棄経路・施工端材率）が行の記録と同じなら警告 REDIRECTED_BY_MERGE、1つでも違えば MERGE_REDIRECT_NEEDS_CONFIRMATION で停止する。",
]

# ---------------------------------------------------------------- release
r = "release"
setf(r, "manifest_hash", type="string|null", description="全レコードの内容ハッシュ。status = DRAFT の間は null でよい。")
setf(r, "invariant_report", description="不変条件の検査結果。不変条件の ID → enum:invariant_result。FAIL または NOT_RUN が1件でもあれば公開しない。")

# ---------------------------------------------------------------- calc_row
r = "calc_row"
R[r]["purpose"] = "計算研究へ渡す1行（案件側のレコード。カタログではない）。活動量・単位・係数参照・耐用年数・修繕率・廃棄経路を1行に持つ。操作の計測は持たない（selection に置く）。項目名は仮で、計算研究側の行の定義が確定したら合わせる。"
addf(r, "row_id", F("project_id", "string", True, "案件の ID（PRJ-）。二重計上の検査は案件の中で行う。"))
setf(r, "selection_id", description="同じ1回の指定から生まれた行をまとめる ID（SEL-。selection を指す）。アセンブリから展開した行は同じ値を持つ。")
setf(r, "zone_id", description="同じ材料を棟・階などで分けて持つときのゾーン（ZN-。語彙は未定義）。null は「ゾーンを分けていない」であり、二重計上の検査では、同じ案件・配置・品種のすべてのゾーンと重なるものとして扱う。")
setf(r, "entry_quantity", description="直接入力された数量。欠損は null（0 と扱わない）。アセンブリから展開した行では、利用者が構成要素の数量を直接入れた場合だけ値を持つ。")
setf(r, "entry_unit", description="入力単位（unit_def.unit_code）。配置の entry_unit か宣言単位、または宣言単位への換算が登録されている単位に限る。entry_quantity が null なら null。")
addf(r, "entry_unit",
     F("driver_quantity", "number|null", True, "アセンブリの基準数量（展開した行だけ。それ以外は null）。入力数量とは別に持つ。"),
     F("driver_unit", "string|null", True, "基準数量の単位（assembly.driver_unit）。driver_quantity が null なら null。"))
setf(r, "quantity_basis", description="設計数量／発注数量／実績数量／不明。推測で埋めず、分からなければ UNKNOWN（警告 QUANTITY_BASIS_UNKNOWN）。端材を含む数量かどうかの区別は未定義（README U-22）。")
setf(r, "conversion_params", description="換算に使った行ごとのパラメータ（空オブジェクト可）。パラメータ名 → { value、unit_code、unit_assumed、source（enum:param_source） }。")
addf(r, "factor_ref", F("factor_unit", "string|null", True, "採用した係数参照の分母単位（param_binding.binding_unit の写し）。未束縛は null。activity_unit と違うときは、宣言単位からこの単位への換算を conversion_ids に含める。"))
setf(r, "factor_stages", type="array<enum:lifecycle_stage>", description="採用した係数参照が含む段階（空配列可）。factor_stage_requirements の集合と一致しなければ FACTOR_STAGE_MISMATCH。")
addf(r, "factor_stages", F("factor_boundary_ref", "string|null", True, "採用した係数参照の対象範囲の参照（param_binding.boundary_ref の写し）。"))
setf(r, "mass_per_unit_ref", name="mass_conversion_ids", type="array<string>",
     description="質量を得るのに使う換算（unit_conversion の質量への経路）。空配列は、宣言単位が質量であるか、経路が無いことを示す（canonical_material.mass_path_status で区別する）。")
setf(r, "param_states", description="param_kind ごとの value_state、param_license_status、bound_from（enum:bound_from）、via_default_placement（既定の配置を使った行で、配置または部位ノードの束縛から決まったとき true）。5種別すべてのキーを持つ。")
setf(r, "defaulted_fields", description="既定・代表・仮定した単位を採用した項目（空配列可）。項目名で書き、単位を仮定した値は spec_unit:<attribute_code> または param_unit:<パラメータ名> と書く。1件につき承認（ACCEPT）を1回数える（INV-20）。承認の無い既定は適用しない。")
setf(r, "warnings", description="警告（空配列可）。SPEC_UNIT_ASSUMED は、仮定した単位を承認して採用したことの記録である（承認の前は SPEC_UNIT_UNCONFIRMED で停止する）。")
delf(r, "selection_path")
delf(r, "operation_count")
delf(r, "candidate_counts")
addf(r, "assembly_line_no",
     F("import_source_id", "string|null", False, "取込から作った行の出典（source）。取込でなければ null。"),
     F("import_locator", "string|null", False, "取込元の行の所在（ファイル・表・行）。取込では、同じ名称・単位の行が複数あっても行ごとに1件の計算行にする。"))
R[r]["constraints"] = [
    "絞り込みは同じ row_id の canonical_id と参照の置き換えであり、行を増やさない。",
    "同じ案件・配置・ゾーン（zone_id が null の行はすべてのゾーンと重なる）で、アセンブリから来た行と個別に指定した行が同じ品種を持つときは、置き換えか追加数量かを明示させる（決まるまで DOUBLE_COUNT_UNRESOLVED）。",
    "QUANTITY_MISSING は、直接指定の行で entry_quantity が null のときに使う。アセンブリから展開した行で構成量が得られないときは ASSEMBLY_RATIO_MISSING を使う。",
    "参照が欠けた行を、別の材料レコードへ黙って差し替えない。",
]

# ---------------------------------------------------------------- selection (new)
selection = {
    "core": False,
    "purpose": "指定1回の記録（案件側。操作の計測用）。操作の回数と候補数を、計算行とは別に持つ。計算には使わない。",
    "primary_key": ["selection_id"],
    "fields": [
        F("selection_id", "string", True, "指定の ID（SEL-）。"),
        F("project_id", "string", True, "案件の ID（PRJ-）。"),
        F("selection_path", "enum:selection_path", True, "指定の経路。"),
        F("operation_count", "object", True, "この指定に要した操作の回数。キーは pick、enter、search、accept、override。accept は、この指定から生まれた行の defaulted_fields の件数の合計と一致する（INV-20）。"),
        F("candidate_counts", "array<integer>", True, "各 pick の候補数（選択情報量 Σlog2 の計算用。空配列可）。"),
    ],
    "constraints": ["指定ごとに1件とし、行の件数で掛けない。"],
}

# ---------------------------------------------------------------- record order
order = ["classification_node", "material_type", "spec_attribute", "canonical_material", "alias", "unit_def",
         "unit_conversion", "assembly", "assembly_component", "placement", "similarity_link", "param_binding",
         "source", "raw_record", "normalized_record", "curation_decision", "merge_event", "release", "calc_row",
         "selection"]
R["normalized_record"] = normalized_record
R["curation_decision"] = curation_decision
R["selection"] = selection
assert set(order) == set(R), set(order) ^ set(R)
S["records"] = {k: R[k] for k in order}
R = S["records"]
for k in ("placement", "param_binding", "release", "calc_row"):
    R[k]["core"] = False
for k in ("canonical_material", "alias", "unit_conversion"):
    R[k]["core"] = True

# field key order
for rn, rr in R.items():
    out = []
    for f in rr["fields"]:
        g = {k: f[k] for k in ("name", "type", "required", "required_when", "description") if k in f}
        assert set(g) == set(f), (rn, f)
        out.append(g)
    rr["fields"] = out

# ---------------------------------------------------------------- resolution orders
ro = S["resolution_orders"]
ro["identity_attribute_value"] = {
    "order": ["USER_CHOSEN", "SPEC_TOKEN", "PLACEMENT_REPRESENTATIVE_OVERRIDE", "TYPE_REPRESENTATIVE_MATERIAL"],
    "note": "順序は、片方にしか無いときの取得元を示す。USER_CHOSEN と SPEC_TOKEN の両方があり値が違えば PARAM_SOURCE_CONFLICT で止める。単位を仮定した値は、確認されるまで SPEC_UNIT_UNCONFIRMED で止める。後ろの2つは resolution_mode = COARSE_ALLOWED で、かつ代表の決め方が NOT_DECIDED でないときだけ使う。使えなければ VARIANT_UNSPECIFIED で止める。該当する正規材料レコードが無い組合せは VARIANT_NOT_REGISTERED で止め、近いものへ寄せない。",
}
ro["conversion_parameter"] = {
    "order": ["IDENTITY_ATTRIBUTE", "USER_INPUT", "SPEC_TOKEN", "EXTERNAL_LEDGER"],
    "note": "順序は、片方にしか無いときの取得元を示す。USER_INPUT と SPEC_TOKEN の両方があり値または単位が違えば PARAM_SOURCE_CONFLICT で止める。単位を仮定した値は、確認されるまで SPEC_UNIT_UNCONFIRMED で止める。代表レコードや既定値からは取らない。どこにも無ければ CONVERSION_BASIS_MISSING で止める。",
}
ro["param_binding"] = {
    "order": ["ROW_OVERRIDE", "CANONICAL_MATERIAL", "PLACEMENT", "MATERIAL_TYPE", "FUNCTION_NODE"],
    "note": "暫定。耐用年数・修繕率が品目で決まるのか部位で決まるのかは実データが無いと決められない。同じ param_kind が複数の水準に束縛されているときは、順序が確定するまで、STRICT では BINDING_LEVEL_CONFLICT で停止し、COARSE_ALLOWED ではこの順で採用して警告 BINDING_LEVEL_ORDER_APPLIED を残す。FUNCTION_NODE の中は ELEMENT → GROUP → DIVISION の順。",
}
ro["alias_context"] = {
    "order": ["CONTEXT_NODE_MATCH", "NO_CONTEXT"],
    "note": "同じ normalized_key に文脈付きの別名と文脈なしの別名があるとき、文脈（部位ノード）が一致すれば文脈付きの行を使う。",
}

# ---------------------------------------------------------------- invariants
inv = {i["id"]: i for i in S["invariants"]}
inv["INV-02"]["description"] = ("各レコードの license_status は、来歴のうち role = RELIED_ON の出典の中で最も制限の強い状態と一致する"
                                "（順序：PERMITTED_PUBLIC ＜ PERMISSION_REQUIRED ＜ UNKNOWN ＜ RESTRICTED）。OBSERVED_MATCH の出典は状態を変えない。"
                                "param_license_status と basis_license_status は参照先の値の状態であり、この条件の対象外。")
inv["INV-03"]["description"] = "区画 PUBLIC_RELEASE の版には license_status が PERMITTED_PUBLIC 以外のレコードが無く、参照先の出典はすべて storage_policy = MAY_STORE_IN_PUBLIC_REPO で license_evidence_ref を持つ。"
inv["INV-04"]["description"] = ("forbidden_value_fields に挙げた量の値を入れる項目が、カタログ側のどのレコードにも存在しない。"
                                "仕様属性は quantity_kind の許す量に限り、DECIMAL の属性の単位は LENGTH・AREA・VOLUME の次元に限る。"
                                "IDENTITY_ATTRIBUTE を根拠にする換算は DIMENSION の属性だけを使う。"
                                "free_text_fields_to_scan の項目に ID 以外の数字があれば、人が確認するまで公開しない。")
inv["INV-09"]["description"] = "GROUP の親は DIVISION、ELEMENT の親は GROUP。配置は ELEMENT だけを指す。品種ごとに、有効な配置の is_primary = true はちょうど1件（配置が0件の品種は除く）。"
inv["INV-10"]["description"] = "代表レコードは同じ品種の ACTIVE な正規材料レコードである（代表専用のレコードは作らない）。"
inv["INV-11"]["description"] = "merged_into の連鎖に循環が無く、たどる深さは1。ACTIVE のレコード（品種・正規材料レコード・別名・換算・アセンブリ・構成要素・配置・類似関係・束縛）が参照するカタログ側のレコードは、分類ノードを含めてすべて ACTIVE。"
inv["INV-12"]["description"] = "アセンブリは循環しない。構成要素の component_unit は対象の宣言単位と一致する。DRIVER_IDENTITY の構成要素は、component_unit = driver_unit かつ component_measure = driver_measure（どちらも null でない）。"
inv["INV-13"]["description"] = ("段階ごとの排出量の合計について、部位グループ別の合計（未配置を別掲）、素材・品目系統別の合計（品目未分類を別掲）、全体合計が一致する"
                                "（展開した行と元の行を二重に数えない）。活動量は単位をまたいで合算しない。"
                                "どの合計にも、計算できない行の件数と、数量の基準（quantity_basis）ごとの件数を併記する。架空データでも試験できる。")
inv["INV-14"]["description"] = ("係数の参照が無い行、param_license_status が PERMITTED_PUBLIC でない束縛を使う行、係数の分母単位が宣言単位と合わず換算も無い行、"
                                "係数の含む段階が factor_stage_requirements の集合と一致しない行、分母単位・段階・対象範囲のどれかが違う参照が同じ水準に並ぶ行は、"
                                "computable = false になる。")
inv["INV-15"]["description"] = "正規化は冪等である。受領レコードと人の判断記録（curation_decision、merge_event、alias、similarity_link）から版を作り直すと、同じ normalized_record と同じ manifest_hash になる。"
S["invariants"] += [
    {"id": "INV-17", "description": "品種の統合（merge_event、target_kind = MATERIAL_TYPE）は、宣言単位、item_kind、role = IDENTITY の属性の集合（attribute_code・unit_code）が同じ組に限る。"},
    {"id": "INV-18", "description": "品種の item_kind は、属する素材・品目系統の allowed_item_kinds に含まれる（substance_class_id が null の品種は対象外）。"},
    {"id": "INV-19", "description": "link_basis = PROXY の ACTIVE な束縛は、relation = PROXY_CANDIDATE かつ substitution_policy = ALLOWED_WITH_FLAG の similarity_link を proxy_link_id に持つ。"},
    {"id": "INV-20", "description": "selection.operation_count.accept は、同じ selection_id の計算行の defaulted_fields の件数の合計と一致する（既定・代表・仮定した単位は、承認なしに適用しない）。"},
    {"id": "INV-21", "description": "SPLIT のイベントは reverts_event_id を持ち、その repointed_refs は取り消す統合の repointed_refs の逆向きである。取り消された統合を via_merge_event_id に持つ来歴の要素は、ACTIVE のレコードには残っていない。"},
    {"id": "INV-22", "description": "reviewed_by が null でないレコードでは、reviewed_by は created_by（merge_event・curation_decision・similarity_link では decided_by）と異なる。"},
]

# ---------------------------------------------------------------- top-level order
top = ["status", "verification", "schema_version", "created", "title", "notes", "conventions", "enums",
       "forbidden_value_fields", "factor_stage_requirements", "common_fields", "records", "resolution_orders", "invariants"]
S["factor_stage_requirements"] = stage_req
assert set(top) == set(S), set(top) ^ set(S)
S = {k: S[k] for k in top}

with open(OUT + "taxonomy_schema.json", "w", encoding="utf-8") as fh:
    json.dump(S, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
print("records", len(S["records"]), "core", sum(1 for v in S["records"].values() if v["core"]),
      "invariants", len(S["invariants"]), "enums", len(S["enums"]),
      "fields", sum(len(v["fields"]) for v in S["records"].values()) + len(S["common_fields"]["fields"]),
      "enum values", sum(len(v) for v in S["enums"].values()))
