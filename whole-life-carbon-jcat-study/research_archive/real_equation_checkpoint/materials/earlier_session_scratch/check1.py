import json, re, hashlib, sys, collections
B="/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/07_MATERIAL_TAXONOMY/"
S=json.load(open(B+"taxonomy_schema.json",encoding="utf-8"))
T=json.load(open(B+"classification_tree.json",encoding="utf-8"))
E=json.load(open(B+"example_records.json",encoding="utf-8"))
enums=S["enums"]; recs=S["records"]
# 1. enum refs in schema types
used=set()
for rn,r in recs.items():
    for f in r["fields"]:
        for m in re.findall(r"enum:([a-z_]+)", f["type"]):
            used.add(m)
            if m not in enums: print("UNDEFINED ENUM", rn, f["name"], m)
for f in S["common_fields"]["fields"]:
    for m in re.findall(r"enum:([a-z_]+)", f["type"]):
        used.add(m)
        if m not in enums: print("UNDEFINED ENUM common", f["name"], m)
print("enums unused by any field type:", sorted(set(enums)-used))
# 2. tree nodes
nodes={n["id"]:n for n in T["nodes"]}
print("nodes",len(nodes), collections.Counter((n["axis"],n["level_kind"],n["status"]) for n in T["nodes"]))
for n in T["nodes"]:
    if n["parent"] is not None:
        p=nodes[n["parent"]]
        if p["level"]!=n["level"]-1: print("LEVEL MISMATCH",n["id"])
    if n["axis"] not in enums["axis"] or n["level_kind"] not in enums["level_kind"] or n["status"] not in enums["record_status"]: print("ENUM BAD", n["id"])
# sibling code uniqueness and global code uniqueness
codes=collections.Counter(n["code"] for n in T["nodes"])
print("dup codes global:", [c for c,k in codes.items() if k>1])
# node fields vs schema
nf={f["name"] for f in recs["classification_node"]["fields"]}|{f["name"] for f in S["common_fields"]["fields"]}
for n in T["nodes"]:
    extra=set(n)-nf
    if extra: print("node extra fields", n["id"], extra); break
req=[f["name"] for f in recs["classification_node"]["fields"] if f["required"] is True]
miss=[(n["id"],[r for r in req if r not in n]) for n in T["nodes"] if any(r not in n for r in req)]
print("nodes missing required:", miss[:3], len(miss))
print("node keys sample:", list(T["nodes"][0].keys()))
# default_input_group, sort_key, definition presence
print("any default_input_group:", any("default_input_group" in n for n in T["nodes"]), "allowed_item_kinds:", any("allowed_item_kinds" in n for n in T["nodes"]))
# 3. id format
pat=re.compile(r"^[A-Z]+-\d{6,}$")
print("tree id format ok:", all(pat.match(i) for i in nodes))
# directive mapping
for m in T["directive_group_mapping"]:
    n=nodes[m["node_id"]]
    assert n["code"]==m["code"] and n["name"]==m["directive_group"], m
print("mapping ok")
