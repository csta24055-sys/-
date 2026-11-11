import json, re, hashlib, sys, collections, unicodedata
B="/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/07_MATERIAL_TAXONOMY/"
S=json.load(open(B+"taxonomy_schema.json",encoding="utf-8"))
T=json.load(open(B+"classification_tree.json",encoding="utf-8"))
E=json.load(open(B+"example_records.json",encoding="utf-8"))
enums=S["enums"]; recs=S["records"]
common={f["name"]:f for f in S["common_fields"]["fields"]}
applies=set(S["common_fields"]["applies_to"])
def check_type(val, typ, where):
    nullable = typ.endswith("|null")
    t = typ[:-5] if nullable else typ
    if val is None:
        if not nullable: print("  NULL not allowed", where, typ)
        return
    if t.startswith("enum:"):
        en=t[5:]
        if val not in enums[en]: print("  BAD ENUM", where, val, en)
    elif t.startswith("array<"):
        if not isinstance(val,list): print("  NOT ARRAY", where); return
        inner=t[6:-1]
        for v in val: 
            if inner.startswith("enum:") and v not in enums[inner[5:]]: print("  BAD ENUM in array", where, v)
    elif t=="string":
        if not isinstance(val,str): print("  NOT STRING", where, val)
    elif t=="integer":
        if not isinstance(val,int): print("  NOT INT", where, val)
    elif t=="number":
        if not isinstance(val,(int,float)): print("  NOT NUM", where, val)
    elif t=="boolean":
        if not isinstance(val,bool): print("  NOT BOOL", where, val)
    elif t=="object":
        if not isinstance(val,dict): print("  NOT OBJ", where, val)
for rn,r in recs.items():
    if rn in ("classification_node","spec_attribute"): continue
    rows=E.get(rn,[])
    fields={f["name"]:f for f in r["fields"]}
    allf=dict(fields)
    if rn in applies: allf.update(common)
    print("==",rn,len(rows))
    for row in rows:
        rid=next(iter([row[k] for k in r["primary_key"] if k in row]),None)
        for fn,f in allf.items():
            if fn not in row:
                if f["required"] is True: print("  MISSING required", rid, fn)
                continue
            check_type(row[fn], f["type"], f"{rn}:{rid}.{fn}")
        extra=set(row)-set(allf)-{"record_flag","explanation"}
        if extra: print("  EXTRA fields", rid, sorted(extra))
        if row.get("record_flag")!="FICTIONAL_PLACEHOLDER": print("  NO FLAG", rid)
# spec attributes
sa={f["name"]:f for f in recs["spec_attribute"]["fields"]}
for mt in E["material_type"]:
    for a in mt["spec_attributes"]:
        for fn,f in sa.items():
            if fn not in a:
                if f["required"] is True: print("  spec attr missing", mt["type_id"], fn)
                continue
            check_type(a[fn], f["type"], f"spec:{mt['type_id']}.{fn}")
# other keys in E not in records
print("non-record keys:", [k for k in E if k not in recs])
# identity key check
for cm in E["canonical_material"]:
    s=cm["identity_string_for_illustration"]
    h=hashlib.sha256(s.encode("utf-8")).hexdigest()
    print(cm["canonical_id"], cm["status"], h==cm["identity_key"], s)
print(hashlib.sha256("v1|MT-FICT-0005|thickness_mm=12|GENERIC".encode()).hexdigest())
print(hashlib.sha256("v1|MT-FICT-0005||GENERIC".encode()).hexdigest())
# content hash attempts
for rw in E["raw_record"]:
    cands=["|".join(str(rw[k]) if rw[k] is not None else "" for k in ("source_id","name_text","spec_text","unit_text","class_text")),
           "\x1f".join(str(rw[k]) if rw[k] is not None else "" for k in ("source_id","name_text","spec_text","unit_text","class_text")),
           json.dumps([rw[k] for k in ("source_id","name_text","spec_text","unit_text","class_text")],ensure_ascii=False)]
    print(rw["raw_id"], [hashlib.sha256(c.encode()).hexdigest()==rw["content_hash"] for c in cands])
