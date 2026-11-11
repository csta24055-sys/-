# -*- coding: utf-8 -*-
"""classification_tree.json にレビュー指摘の修正を適用する（バックアップから読み、本体へ書く。再実行可）。"""
import json

BK = "/tmp/claude-0/-home-user--/49c0bd7e-a786-5ae4-9a1e-e89e7996ede3/scratchpad/wfD_fix/backup/"
OUT = "/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/07_MATERIAL_TAXONOMY/"
T = json.load(open(BK + "classification_tree.json", encoding="utf-8"))

T.pop("evidence_level")
T["origin_kind"] = "SELF_AUTHORED"
T["taxonomy_version"] = "0.2.0-draft"
T["note"] = ("本ファイルの分類名・符号（code）は、特定の分類表・コード表・規格本文を参照せずに、一般的な建築用語から本研究で選んだ暫定案である。"
             "分類表ワークブックのシート名から中身を推測して埋めることもしていない。"
             "ただし、許諾の必要な分類表の中身は参照できないので、既存の分類表と似ていないかは照合していない。"
             "ノードを有効化する前に、権利に詳しい人が類似を確認する（README U-19）。"
             "実在の材料データセットは未入手であり、この階層が実データに適合するか、何件の材料がどのノードに入るかは不明である。"
             "全ノードは提案（DRAFT）または予約（RESERVED）であり、有効（ACTIVE）なノードは無い。")

T["axes"][0]["principle"] = "建物の中のどこで、何の役割で使うか。報告・集計の標準単位（指示書第7章の9つの区分）はこの軸の第2階層（部位グループ）に置く。"
lv = {x["level_kind"]: x for x in T["levels"]}
lv["DIVISION"]["name"] = "大区分"
lv["GROUP"]["note"] = "指示書第7章の9つの区分に対応する。報告・集計の標準単位。"
T["levels_note"] = "階層の番号（level）はこの表だけが持つ。ノードは level_kind だけを持つ。"

T["rules"] = [
    "ID（node_id）は意味を持たない連番であり、親・階層・名称を埋め込まない。接頭辞（FN-／IN-）は種別と軸だけを表す。再利用しない。並び順・階層・新旧を ID の大小から読み取らない。",
    "符号（code）は人が読むための英語の符号で、（軸、階層）の中で一意。大区分・部位グループ・素材系統の code は集計の見出しに使うため、有効化後は変更しない。",
    "定義（含むもの）を書けない受け皿のノード（「未分類」「その他」など）は、予約としても作らない。配置できない行は行の側の状態（placement_state = UNPLACED）、系統を決められない品種は substance_class_id = null とし、どちらも集計で別掲する。",
    "RESERVED のノードは、指示書の「など」に備えた予約であり、算定範囲に含めるかどうかを決めるまで使用できない。親は暫定である。",
]

sources = [{
    "source_id": "SRC-000001",
    "title": "本研究で自分で付けた分類名・符号",
    "origin_kind": "SELF_AUTHORED",
    "source_version": "0.2.0-draft",
    "retrieved_at": "2026-11-11",
    "content_kinds": ["CLASSIFICATION_LABELS"],
    "license_status": "PERMITTED_PUBLIC",
    "license_evidence_ref": "自作であること（README.md 1章の作成過程の記述）。既存の分類表との類似は未照合（README U-19）",
    "permitted_uses": ["INTERNAL_RESEARCH", "PUBLIC_REDISTRIBUTION"],
    "storage_policy": "MAY_STORE_IN_PUBLIC_REPO",
    "license_reviewed_by": "draft_author（自己申告。第三者による確認は未実施）",
    "license_reviewed_at": "2026-11-11",
    "license_valid_until": None,
}]

T["node_defaults"] = {
    "note": "各ノードでは共通項目（taxonomy_schema.json の common_fields）を省略している。全ノードに次の値が当てはまる。license_status は手入力ではなく、来歴が指す出典 SRC-000001（本ファイルの sources）の状態から導いた値である。",
    "created_in_release": "0.1.0-draft",
    "license_status": "PERMITTED_PUBLIC",
    "compartment": "PUBLIC_RELEASE",
    "provenance": [{"source_id": "SRC-000001", "raw_id": None, "derivation": "CURATED", "role": "RELIED_ON", "via_merge_event_id": None}],
    "record_version": 1,
    "created_by": "draft_author",
    "reviewed_by": None,
}

withdrawn = {
    "FN-000014": "「その他設備」（予約）。含むものを定義できない受け皿だったので取り下げた。4つの設備グループに入らない設備（防災系など）は、定義したグループを足すまで未配置とする（README U-03）。",
    "FN-000052": "「その他搬送」。含むものを定義できない受け皿だったので取り下げた。エレベーター・エスカレーターに当たらない搬送設備は、定義した部位要素を足すまで未配置とする。",
}
allowed = {}
for c in ["CEMENTITIOUS", "FERROUS_METAL", "NONFERROUS_METAL", "TIMBER", "MASONRY_CERAMIC", "STONE_AGGREGATE_EARTH", "GLASS",
          "MINERAL_BOARD", "INSULATION", "WATERPROOFING_SEALANT", "COATING", "POLYMER"]:
    allowed[c] = ["BULK_MATERIAL"]
allowed["FORMED_PRODUCT"] = ["SHAPED_PRODUCT"]
for c in ["MACHINE_UNIT", "TERMINAL_FIXTURE", "PANEL_CONTROL"]:
    allowed[c] = ["EQUIPMENT_UNIT"]
allowed["DISTRIBUTION_LINE"] = ["LINEAR_ITEM"]
allowed["COMPOSITE"] = ["COMPOSITE_ITEM"]

note_override = {
    "FN-000011": "人・物を運ぶ設備。エレベーター・エスカレーターに当たらない搬送設備は、定義した部位要素を足すまで未配置とする。",
    "FN-000012": "予約。算定範囲に含めるかは未決定。親（建築）は暫定で、どの大区分の下に置くかも未決定。",
    "FN-000013": "予約。建物に残らないもの（型枠・足場など）。施工段階の扱いと合わせて決める。親（建築）は暫定。",
    "FN-000005": "外気に接する面の非耐力の層（仕上げ・下地・断熱・防水）。指示書の区分に従って同じグループとし、屋根と外壁は部位要素で分ける。",
    "IN-000018": "複数の品目を決まった構成で含み、ひとつの単位で数量を拾うもの。構成が得られれば構成品の行へ展開する。",
}
division_group = {"FN-000001": "MATERIAL", "FN-000002": "EQUIPMENT"}
nodes = []
for n in T["nodes"]:
    if n["id"] in withdrawn:
        continue
    m = {"node_id": n["id"], "axis": n["axis"], "level_kind": n["level_kind"], "code": n["code"], "name": n["name"],
         "parent": n["parent"], "status": n["status"]}
    if n["level_kind"] == "GROUP":
        m["default_input_group"] = division_group[n["parent"]]
    if n["level_kind"] == "SUBSTANCE_CLASS":
        m["allowed_item_kinds"] = allowed[n["code"]]
    m["note"] = note_override.get(n["id"], n["note"])
    nodes.append(m)
assert len(nodes) == len(T["nodes"]) - 2

T["known_weaknesses"] += [
    "素材・品目系統18件の網羅性は確認していない。どの系統の定義にも当てはまらない品種は、近い系統に寄せず品目未分類（substance_class_id = null）にする。allowed_item_kinds と default_input_group の値は暫定である。",
    "設備の部位要素（系統の分け方）は一般的な用語から選んだもので、業界で広く使われる内訳の区分と似た形になりうる。既存の分類表との類似は照合していない。",
]

out = {}
for k in ["status", "verification", "origin_kind", "taxonomy_version", "created", "note", "related_files", "axes", "levels",
          "levels_note", "levels_not_in_this_file", "directive_group_mapping", "rules"]:
    out[k] = T[k]
out["sources"] = sources
out["node_defaults"] = T["node_defaults"]
out["nodes"] = nodes
out["withdrawn_draft_ids"] = {
    "note": "草案の段階（公開した版は無い）で取り下げたノードの ID。欠番とし、再利用しない。",
    "ids": [{"node_id": k, "reason": v} for k, v in withdrawn.items()],
}
out["known_weaknesses"] = T["known_weaknesses"]
assert set(T) - set(out) == {"nodes"} - {"nodes"} or set(T) <= set(out) | set(), set(T) - set(out)

with open(OUT + "classification_tree.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
import collections
print(len(nodes), collections.Counter((n["axis"], n["level_kind"], n["status"]) for n in nodes))
