# -*- coding: utf-8 -*-
"""検査スクリプトが実際に違反を検出するかを、わざと壊した写しで確かめる。"""
import json, os, shutil, subprocess, sys, tempfile
SRC = "/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/07_MATERIAL_TAXONOMY/"
HERE = os.path.dirname(os.path.abspath(__file__))

def find(E, sec, key, val):
    return [r for r in E[sec] if r[key] == val][0]

def m1(S, T, E, R): find(E, "placement", "placement_id", "PL-FICT-0001")["function_node_id"] = "FN-000025"
def m2(S, T, E, R): find(E, "selection", "selection_id", "SEL-FICT-0001")["operation_count"]["accept"] = 1
def m3(S, T, E, R): find(E, "param_binding", "binding_id", "PB-FICT-0001")["license_status"] = "UNKNOWN"
def m4(S, T, E, R): find(E, "merge_event", "merge_event_id", "ME-FICT-0004")["repointed_refs"] = []
def m5(S, T, E, R): find(E, "canonical_material", "canonical_id", "CM-FICT-0004")["identity_key"] = "0" * 64
def m6(S, T, E, R): find(E, "calc_row", "row_id", "ROW-FICT-0004")["blocking_reasons"].remove("DOUBLE_COUNT_UNRESOLVED")
def m7(S, T, E, R): T["nodes"].append({"node_id": "FN-000052", "axis": "FUNCTION", "level_kind": "ELEMENT", "code": "OTHER_CONVEYANCE", "name": "その他搬送", "parent": "FN-000011", "status": "DRAFT", "note": "x"})
def m8(S, T, E, R): S["invariants"].pop()
def m9(S, T, E, R): find(E, "material_type", "type_id", "MT-FICT-0005")["declared_unit"] = "m3"
def m10(S, T, E, R): find(E, "material_type", "type_id", "MT-FICT-0006")["item_kind"] = "BULK_MATERIAL"
def m11(S, T, E, R): find(E, "calc_row", "row_id", "ROW-FICT-0002")["activity"] = 20000
def m12(S, T, E, R): find(E, "canonical_material", "canonical_id", "CM-FICT-0005")["density"] = 1.5
def m13(S, T, E, R): find(E, "assembly", "assembly_id", "AS-FICT-0001")["driver_measure"] = "OTHER"
def m14(S, T, E, R): R[0] = R[0].replace("68ノード", "70ノード")
def m15(S, T, E, R):
    r = find(E, "raw_record", "raw_id", "RAW-FICT-0005"); r["intake_status"] = "ACCEPTED"; r["duplicate_of_raw"] = None
def m16(S, T, E, R): find(E, "alias", "alias_id", "AL-FICT-0002")["reviewed_by"] = "reviewer_a"
def m17(S, T, E, R): find(E, "calc_row", "row_id", "ROW-FICT-0001")["entry_unit"] = "kg"
def m18(S, T, E, R): find(E, "unit_conversion", "conversion_id", "UC-FICT-0001")["basis_unit_code"] = "m"
def m19(S, T, E, R): find(E, "material_type", "type_id", "MT-FICT-0001")["spec_attributes"][0]["quantity_kind"] = "LABEL"
def m20(S, T, E, R): find(E, "calc_row", "row_id", "ROW-FICT-0005")["entry_quantity"] = 50
def m21(S, T, E, R): find(E, "canonical_material", "canonical_id", "CM-FICT-0004")["provenance"][0]["role"] = "OBSERVED_MATCH"  # 根拠にした出典が無くなる
def m22(S, T, E, R): find(E, "similarity_link", "link_id", "SL-FICT-0001")["basis"] = "係数は 12.5 である"
def m23(S, T, E, R): R[0] = R[0].replace("`param_binding`（`WASTE_RATE`）", "`param_binding`（`WASTE_RATIO`）")
def m24(S, T, E, R): T["nodes"][10]["code"] = T["nodes"][9]["code"]

muts = [v for k, v in sorted(globals().items(), key=lambda kv: int(kv[0][1:]) if kv[0][0] == "m" and kv[0][1:].isdigit() else 0) if k[0] == "m" and k[1:].isdigit()]
bad = 0
for fn in muts:
    d = tempfile.mkdtemp(dir=HERE)
    S, T, E = (json.load(open(SRC + n, encoding="utf-8")) for n in ("taxonomy_schema.json", "classification_tree.json", "example_records.json"))
    R = [open(SRC + "README.md", encoding="utf-8").read()]
    fn(S, T, E, R)
    for n, o in (("taxonomy_schema.json", S), ("classification_tree.json", T), ("example_records.json", E)):
        json.dump(o, open(os.path.join(d, n), "w", encoding="utf-8"), ensure_ascii=False)
    open(os.path.join(d, "README.md"), "w", encoding="utf-8").write(R[0])
    p = subprocess.run([sys.executable, os.path.join(HERE, "validate.py")], env=dict(os.environ, TAXO_DIR=d + "/"), capture_output=True, text=True)
    errs = [l for l in p.stdout.splitlines() if l.startswith("  - ")]
    print(fn.__name__, "detected" if p.returncode else "NOT DETECTED", len(errs), "|", (errs[0][:110] if errs else p.stderr[-200:]))
    bad += (p.returncode == 0)
    shutil.rmtree(d)
print("undetected mutations:", bad, "of", len(muts))
