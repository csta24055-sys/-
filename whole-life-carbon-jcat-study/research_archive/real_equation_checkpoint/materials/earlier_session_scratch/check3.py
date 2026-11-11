import json, re, collections
B="/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/07_MATERIAL_TAXONOMY/"
def dup_hook(pairs):
    keys=[k for k,_ in pairs]
    d=[k for k,c in collections.Counter(keys).items() if c>1]
    if d: print("DUPLICATE KEYS", d)
    return dict(pairs)
S=json.load(open(B+"taxonomy_schema.json",encoding="utf-8"),object_pairs_hook=dup_hook)
T=json.load(open(B+"classification_tree.json",encoding="utf-8"),object_pairs_hook=dup_hook)
E=json.load(open(B+"example_records.json",encoding="utf-8"),object_pairs_hook=dup_hook)
ids=set(n["id"] for n in T["nodes"])
nodes={n["id"]:n for n in T["nodes"]}
pk={"material_type":"type_id","canonical_material":"canonical_id","alias":"alias_id","unit_conversion":"conversion_id","assembly":"assembly_id","placement":"placement_id","similarity_link":"link_id","param_binding":"binding_id","source":"source_id","raw_record":"raw_id","merge_event":"merge_event_id","release":"release_id","calc_row":"row_id","unit_def":"unit_code"}
idx={}
for rn,k in pk.items():
    for r in E[rn]:
        if r[k] in idx: print("DUP ID", r[k])
        idx[r[k]]=(rn,r)
allids=set(idx)|ids
def ref(x, where):
    if x is None: return
    if x not in allids: print("BROKEN REF", where, x)
for r in E["material_type"]:
    ref(r["substance_class_id"],"mt.sub"); ref(r["declared_unit"],"mt.unit"); ref(r["merged_into"],"mt.merged"); ref(r["representative_material_id"],"mt.rep")
    for p in r["provenance"]: ref(p["source_id"],"prov"); ref(p["raw_id"],"prov")
    for x in r["replaced_by"]: ref(x,"repl")
    ref(r["created_in_release"],"rel")
for r in E["canonical_material"]:
    ref(r["type_id"],"cm.type"); ref(r["merged_into"],"cm.merged")
    for p in r["provenance"]: ref(p["source_id"],"prov"); ref(p["raw_id"],"prov")
for r in E["alias"]:
    for t in r["target_ids"]: ref(t,"alias.target")
    for p in r["provenance"]: ref(p["source_id"],"prov"); ref(p["raw_id"],"prov")
for r in E["unit_conversion"]:
    ref(r["scope_id"],"uc.scope"); ref(r["from_unit"],"uc.from"); ref(r["to_unit"],"uc.to")
for r in E["placement"]:
    ref(r["function_node_id"],"pl.fn"); ref(r["type_id"],"pl.type"); ref(r["entry_unit"],"pl.unit")
    print("placement", r["placement_id"], nodes[r["function_node_id"]]["level_kind"], nodes[r["function_node_id"]]["name"], nodes[r["function_node_id"]]["status"])
for r in E["assembly"]:
    ref(r["function_node_id"],"as.fn"); ref(r["driver_unit"],"as.unit")
for r in E["assembly_component"]:
    ref(r["assembly_id"],"ac.as"); ref(r["target_id"],"ac.target"); ref(r["component_unit"],"ac.unit"); ref(r["placement_id"],"ac.pl")
for r in E["param_binding"]:
    ref(r["scope_id"],"pb.scope")
for r in E["raw_record"]:
    ref(r["source_id"],"raw.src"); ref(r["duplicate_of_raw"],"raw.dup"); ref(r["ingested_in_release"],"raw.rel")
for r in E["merge_event"]:
    ref(r["survivor_id"],"me.s"); [ref(x,"me.m") for x in r["merged_ids"]]; [ref(x,"me.al") for x in r["aliases_created"]]; ref(r["release_id"],"me.rel")
for r in E["similarity_link"]:
    ref(r["left_id"],"sl"); ref(r["right_id"],"sl")
for r in E["calc_row"]:
    ref(r["canonical_id"],"row.cm"); ref(r["placement_id"],"row.pl"); ref(r["entry_unit"],"row.eu"); ref(r["activity_unit"],"row.au"); ref(r["release_id"],"row.rel"); ref(r["assembly_id"],"row.as")
    [ref(x,"row.conv") for x in r["conversion_ids"]]
    cm=idx[r["canonical_id"]][1]; mt=idx[cm["type_id"]][1]
    pl=idx[r["placement_id"]][1]
    print(r["row_id"], "type",mt["type_id"],"decl",mt["declared_unit"],"act_unit",r["activity_unit"],"pl.type",pl["type_id"], "pl.entry",pl["entry_unit"], "row.entry", r["entry_unit"])
for r in E["normalization_trace"]:
    ref(r["raw_id"],"nt.raw"); ref(r["resolved_to"],"nt.res")
for r in E["duplicate_handling"]+E["what_this_shows"]:
    [ref(x,"dh") for x in r["records"]]
# which raw ids have no normalization trace
print("raw without trace:", [r["raw_id"] for r in E["raw_record"] if r["raw_id"] not in {t["raw_id"] for t in E["normalization_trace"]}])
# license/compartment invariant checks on examples
rel={r["release_id"]:r for r in E["release"]}
for rn in ["material_type","canonical_material","alias","unit_conversion","assembly","placement","similarity_link","param_binding"]:
    for r in E[rn]:
        if r["compartment"]=="PUBLIC_RELEASE" and r["license_status"]!="PERMITTED_PUBLIC":
            print("INV-03 violation:", rn, r[pk[rn]], r["license_status"], r["status"])
        srcs=[idx[p["source_id"]][1]["license_status"] for p in r["provenance"]]
        order=["PERMITTED_PUBLIC","PERMISSION_REQUIRED","UNKNOWN","RESTRICTED"]
        worst=max(srcs,key=order.index)
        if worst!=r["license_status"]: print("INV-02 mismatch:", rn, r[pk[rn]], "record",r["license_status"],"computed",worst)
        if r["status"]=="ACTIVE" and not r.get("reviewed_by"): print("ACTIVE without reviewer", r[pk[rn]])
# ACTIVE records referencing non-ACTIVE
for r in E["placement"]:
    if r["status"]=="ACTIVE" and nodes[r["function_node_id"]]["status"]!="ACTIVE": print("INV-11: ACTIVE placement -> non-ACTIVE node", r["placement_id"], nodes[r["function_node_id"]]["status"])
for r in E["material_type"]:
    if r["status"]=="ACTIVE" and nodes[r["substance_class_id"]]["status"]!="ACTIVE": print("ACTIVE type -> non-ACTIVE substance class", r["type_id"])
for r in E["canonical_material"]:
    if r["status"]=="ACTIVE":
        mt=idx[r["type_id"]][1]
        reqattrs=[a["attribute_code"] for a in mt["spec_attributes"] if a["required"] and a["role"]=="IDENTITY"]
        miss=[a for a in reqattrs if a not in r["attribute_values"]]
        if miss: print("ACTIVE cm missing identity attr", r["canonical_id"], miss)
# identity key uniqueness among ACTIVE
c=collections.Counter(r["identity_key"] for r in E["canonical_material"] if r["status"]=="ACTIVE"); print("dup active identity:", [k for k,v in c.items() if v>1])
