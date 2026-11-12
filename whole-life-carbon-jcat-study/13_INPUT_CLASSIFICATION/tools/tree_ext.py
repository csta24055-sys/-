"""Complete classification tree: the received tree v0.1 plus detail nodes, one added branch and the
"needs review" category. Pure data and a builder; no content of the originals is in this file.

Node ids: <category>.<branch>.<detail>. Ids of v0.1 categories and branches are kept unchanged.
A detail whose label is one of the items of the v0.1 branch carries ``from_v01 = True``.
"""
from __future__ import annotations

NEW = "追加"          # detail or branch that is not in v0.1

DETAILS: dict[str, list[tuple[str, str, str]]] = {
    "building.identity": [("name", "建物名称", ""), ("assessor", "算定者・事業者", ""), ("location", "所在地", ""),
                          ("calc_date", "算定日", ""), ("completion_year", "竣工年", ""),
                          ("design_stage", "算定段階（計画・設計・着工・竣工など）", "")],
    "building.geometry": [("main_use", "主用途", ""), ("use_floor_areas", "用途別床面積", ""), ("gross_floor_area", "延床面積", ""),
                          ("floors", "地上・地下階数", ""), ("height", "建物高さ", ""), ("typical_floor_area", "基準階面積", ""),
                          ("shape", "形状・セットバック", ""), ("max_span", "最大スパン", "")],
    "building.structure": [("main_structure", "主要構造（RC・S・SRC・木造等）", ""), ("foundation", "基礎・杭の方式", ""),
                           ("roof_spec", "主要屋根仕様", ""), ("facade_spec", "主要外壁仕様", "")],
    "building.boundary": [("project_type", "新築・既存・改修の区別", ""), ("study_period", "評価期間", ""),
                          ("replacement_cycle", "建替周期", ""), ("stages", "計上する工事とライフサイクル段階", ""),
                          ("site_scope", "敷地・工事負担の算定範囲", "")],
    "construction.ground": [("earthwork", "土工事", ""), ("ground_improvement", "地業・砕石・地盤改良", ""),
                            ("pile_foundation", "杭・基礎", ""), ("formwork", "型枠", "")],
    "construction.frame": [("concrete", "コンクリート", ""), ("rebar", "鉄筋", ""), ("steel", "鉄骨", ""), ("timber", "木材", ""),
                           ("other_frame", "デッキプレート・その他躯体", "")],
    "construction.external": [("roof", "屋根・防水", ""), ("exterior_wall", "外壁", ""), ("exterior_opening", "外部開口部", ""),
                              ("exterior_insulation", "外部断熱", ""), ("exterior_misc", "外部雑・外構", "")],
    "construction.internal": [("floor", "内部床", ""), ("partition", "内壁・間仕切り", ""), ("interior_opening", "内部開口部", ""),
                              ("ceiling", "天井", ""), ("interior_insulation", "内部断熱・吸音", ""),
                              ("interior_misc", "内部雑・ユニットバス", "")],
    "construction.temporary": [("direct_temporary", "直接仮設", ""), ("common_cost", "共通仮設・現場経費", ""),
                               ("site_fuel", "施工燃料", ""), ("site_power_gas", "施工電力・ガス", ""), ("testing", "試験・調整", ""),
                               ("site_transport", "現場内運搬", ""), ("site_water", "施工時の上水・下水", NEW)],
    "construction.transport": [("delivery", "資機材の現場輸送", ""), ("waste_hauling", "廃材の搬出", ""),
                               ("offcut_waste", "端材・廃棄物の数量", ""), ("reuse_recycle", "リユース・リサイクル・埋立区分", "")],
    "construction.item_details": [("spec", "名称・仕様・寸法", ""), ("code", "材料コード・工事分類", ""), ("quantity", "数量", ""),
                                  ("quantity_unit", "数量単位", ""), ("physical", "必要な場合の重量・体積・面積・長さ", ""),
                                  ("cost", "必要な場合の単価・工事金額", ""), ("timber_carbon", "木材の樹種・炭素貯蔵関連", ""),
                                  ("concrete_fixation", "コンクリートのCO2固定関連", "")],
    "equipment.electrical": [("substation", "受変電・変圧器・配電盤", ""), ("wiring", "電力配線・ケーブル", ""), ("lighting", "照明", ""),
                             ("low_voltage", "弱電・通信・防災", ""), ("pv", "太陽光発電などの設備", ""),
                             ("cost", "電気設備の工事費", NEW), ("standard_table", "電気設備の用途別・規模別の標準値表", NEW),
                             ("code_table", "電気設備のコード表・主要機器表", NEW)],
    "equipment.hvac": [("heat_source", "熱源・冷凍機・ボイラ", ""), ("air_handling", "空気調和機・ファン・ポンプ", ""),
                       ("piping", "配管・継手・バルブ", ""), ("duct", "ダクト・制気口・ダンパー", ""),
                       ("insulation_control", "保温・塗装・自動制御", ""), ("cost", "空調設備の工事費", NEW),
                       ("standard_table", "空調設備の用途別・規模別の標準値表", NEW), ("code_table", "空調設備のコード表", NEW)],
    "equipment.plumbing": [("water_supply", "受水槽・給水設備", ""), ("drainage", "排水・通気・ポンプ", ""), ("hot_water", "給湯", ""),
                           ("fixtures_fire", "衛生器具・消火設備", ""), ("piping", "配管・継手・弁類", ""),
                           ("cost", "衛生設備の工事費", NEW), ("standard_table", "衛生設備の用途別・規模別の標準値表", NEW),
                           ("code_table", "衛生設備のコード表", NEW)],
    "equipment.elevator": [("elevator", "エレベーター", ""), ("escalator", "エスカレーター・搬送設備", ""),
                           ("cost", "昇降機設備の工事費", NEW), ("standard_table", "昇降機設備の用途別・規模別の標準値表", NEW),
                           ("code_table", "昇降機設備のコード表", NEW)],
    "equipment.eq_details": [("spec", "設備名称・型式・仕様", ""), ("count", "台数", ""), ("weight", "機器重量", ""),
                             ("capacity", "能力・容量", ""), ("pipe_cable_length", "配管・ケーブル長", ""),
                             ("duct_spec", "ダクト面積・板厚・比重", ""), ("cost", "必要に応じた工事費", ""),
                             ("usage_location", "設備の用途・設置箇所", "")],
    "equipment.refrigerant_equipment": [("substance", "冷媒・温室効果ガスの種類", ""), ("charge", "充填・使用量", ""),
                                        ("application", "用途（空調・断熱・消火など）", ""), ("device_link", "冷媒を使う機器との対応", ""),
                                        ("recovery_cost", "回収・処理の費用", NEW)],
    "operation.energy": [("electricity", "電力使用量", ""), ("city_gas", "都市ガス使用量", ""), ("oil_fuel", "石油・燃料使用量", ""),
                         ("other_energy", "その他エネルギー使用量", ""), ("yearly_table", "年間推移・年次テーブル", ""),
                         ("annual_use", "年間消費エネルギー量（種類別の表）", NEW), ("fm_ratio", "施設管理諸室の消費割合", NEW)],
    "operation.utility": [("water", "上水使用量", ""), ("sewage", "下水排水量", ""), ("municipal_waste", "一般廃棄物量", "")],
    "operation.generation": [("generation", "発電量", ""), ("self_use_export", "自家消費・外部供給などの区分", "")],
    "operation.maintenance": [("material_cycle", "材料の更新周期", ""), ("equipment_life", "設備の耐用年数・更新周期", ""),
                              ("repair_rate", "修繕率", ""), ("replacement_timing", "予定・実際の更新時期", ""),
                              ("repair_conditions", "対象に応じた補修・交換条件", ""), ("cycle_summary", "更新周期の集計表", NEW),
                              ("yearly_series", "経年の排出系列の表", NEW)],
    "operation.leakage": [("leak_rate", "漏洩率", ""), ("top_up", "補充条件", ""), ("recovery_rate", "廃棄時回収率", ""),
                          ("change_timing", "交換時期", ""), ("service_period", "機器の使用期間", "")],
    "operation.end_of_life": [("demolition", "解体・撤去", ""), ("waste_transport", "廃棄物輸送", ""),
                              ("treatment_share", "処理・再利用・最終処分の割合", ""), ("end_timing", "解体時点・評価期間末の扱い", ""),
                              ("waste_analysis", "廃棄物・資源量の分析表", NEW)],
    "assessment.method": [("method_level", "簡易／標準／詳細の区分", ""), ("stages", "対象段階（A1～C4等）", ""),
                          ("gas_scope", "CO2とGHGの評価範囲", ""), ("module_d", "補足D区分の扱い", ""), ("purpose", "算定用途・目的", ""),
                          ("system_boundary", "システム境界の選択", NEW)],
    "assessment.factors": [("material_factor", "材料の排出原単位", ""), ("energy_factor", "電力・ガスなどの排出係数", ""),
                           ("epd", "EPD製品の選択", ""), ("factor_scope", "原単位の単位・適用範囲", ""),
                           ("factor_source", "原単位の参照元・版", ""), ("composite_factor", "複合原単位", NEW),
                           ("gas_factor_db", "ガス別の排出原単位データベース", NEW), ("gwp", "地球温暖化係数・オゾン層破壊係数", NEW)],
    "assessment.conversions": [("conversion_method", "重量・体積・面積・長さ・能力・金額の換算方式", ""),
                               ("dimension_density", "材料寸法や比重による換算", ""), ("work_multiplier", "工事金額比率・工事分倍率", ""),
                               ("equipment_standard", "設備標準値", ""), ("unquantified", "未数量化工事の補完方法", ""),
                               ("composite_definition", "複合原単位の資材構成", NEW), ("price_correction", "物価補正", NEW),
                               ("quantity_per_area", "延床面積あたりの標準物量", NEW), ("calc_class", "算出分類", NEW),
                               ("external_lca_reference", "外部の計算結果の参照欄", NEW)],
    "assessment.assumptions": [("standard_cycle", "設備・資材の標準更新周期", ""), ("standard_repair_rate", "標準修繕率", ""),
                               ("standard_leak_rate", "標準漏洩率", ""), ("carbon_coefficients", "炭素固定・炭素貯蔵の係数", ""),
                               ("grid_future", "電力排出係数の将来変化", ""), ("standard_values", "標準値の管理表", NEW),
                               ("parameters", "各種パラメータ", NEW), ("energy_statistics", "エネルギー統計値", NEW),
                               ("internal_parameter_tables", "内部パラメータ表", NEW)],
    "assessment.check": [("duplicate_check", "数量の重複・漏れ確認", ""), ("unit_check", "単位換算の妥当性", ""),
                         ("scope_check", "使用する算定範囲の確認", ""), ("missing_check", "不足入力の確認", ""),
                         ("basis_notes", "元の算定根拠・注記", ""), ("checklist", "チェックリスト", NEW),
                         ("tool_info", "ツールの版・更新履歴・注意書き", NEW)],
    "assessment.display": [("display_options", "結果の表示の選択", NEW), ("result_tables", "算定結果の表", NEW)],
}
NEW_BRANCHES = {"assessment": [("display", "結果表示・報告の設定", "selection",
                                "算定結果のシートにある表示の切替えと、結果の表。入力ではないが、設定値として存在する。")]}
REVIEW = {"id": "review", "label": "要確認・未分類", "branches": [
    ("unknown", "不明・未分類", "値はあるが、意味や適切な分類が分からない"),
    ("blank", "空欄・未入力", "入力欄はあるが値がなく、見出しからも分類できない"),
    ("purpose_unknown", "用途不明", "何の計算に使う値か分からない"),
    ("broken_ref", "参照不明・参照切れ", "参照先を追跡できない"),
    ("duplicate", "重複・統合候補", "別の項目と実質的に同じ可能性がある"),
]}


def build(v01: dict) -> dict:
    """The complete tree as a dict (categories -> branches -> details)."""
    out = {"name": "J-CAT入力分類ツリー（完全分類・構造のみ）", "version": "1.0", "based_on": {"name": v01.get("name"), "version": v01.get("version")},
           "source_scope": v01.get("source_scope"), "rules": v01.get("rules"), "categories": []}
    for cat in v01["categories"]:
        branches = []
        for br in cat["branches"]:
            node_id = "%s.%s" % (cat["id"], br["id"])
            details = [{"id": "%s.%s" % (node_id, d), "label": label, "from_v01": tag != NEW}
                       for d, label, tag in DETAILS.get(node_id, [])]
            branches.append({"id": node_id, "label": br["label"], "handling": br.get("handling"), "from_v01": True,
                             "v01_items": br.get("items", []), "notes": br.get("notes"), "details": details})
        for bid, label, handling, note in NEW_BRANCHES.get(cat["id"], []):
            node_id = "%s.%s" % (cat["id"], bid)
            pos = len(branches) - 1 if branches and branches[-1]["id"].endswith(".other") else len(branches)
            branches.insert(pos, {"id": node_id, "label": label, "handling": handling, "from_v01": False, "v01_items": [], "notes": note,
                                  "details": [{"id": "%s.%s" % (node_id, d), "label": l2, "from_v01": False}
                                              for d, l2, _ in DETAILS.get(node_id, [])]})
        out["categories"].append({"id": cat["id"], "label": cat["label"], "branches": branches})
    out["categories"].append({"id": REVIEW["id"], "label": REVIEW["label"], "branches": [
        {"id": "review.%s" % bid, "label": label, "handling": "review", "from_v01": False, "v01_items": [], "notes": note, "details": []}
        for bid, label, note in REVIEW["branches"]]})
    return out


def node_index(tree: dict) -> dict:
    """node id -> (category label, branch label, detail label)."""
    idx = {}
    for cat in tree["categories"]:
        for br in cat["branches"]:
            idx[br["id"]] = (cat["label"], br["label"], "")
            for d in br["details"]:
                idx[d["id"]] = (cat["label"], br["label"], d["label"])
    return idx
