# -*- coding: utf-8 -*-
"""07_MATERIAL_TAXONOMY の4ファイルの内部整合を検査する（一時スクリプト。リポジトリには収録しない）。"""
import json, re, hashlib, collections, sys

import os
B = os.environ.get("TAXO_DIR", "/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/07_MATERIAL_TAXONOMY/")
ERR, OKS = [], []


def err(*a):
    ERR.append(" ".join(str(x) for x in a))


_mark = [0]


def ok(msg):
    OKS.append(("OK  " if len(ERR) == _mark[0] else "NG  ") + msg)
    _mark[0] = len(ERR)


def dup_hook(pairs):
    keys = [k for k, _ in pairs]
    d = [k for k, c in collections.Counter(keys).items() if c > 1]
    if d:
        err("DUPLICATE KEYS", d)
    return dict(pairs)


def load(name):
    return json.load(open(B + name, encoding="utf-8"), object_pairs_hook=dup_hook)


S, T, E = load("taxonomy_schema.json"), load("classification_tree.json"), load("example_records.json")
README = open(B + "README.md", encoding="utf-8").read()
ok("A: 3つの JSON が読み込め、重複キーが無い")
EN, RS = S["enums"], S["records"]
COMMON = {f["name"]: f for f in S["common_fields"]["fields"]}
APPLIES = set(S["common_fields"]["applies_to"])
LIC_ORDER = ["PERMITTED_PUBLIC", "PERMISSION_REQUIRED", "UNKNOWN", "RESTRICTED"]


def h(arr):
    return hashlib.sha256(json.dumps(arr, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ B. schema self-consistency
used = set()
for rn, r in list(RS.items()) + [("common", S["common_fields"])]:
    names = [f["name"] for f in r["fields"]]
    if len(names) != len(set(names)):
        err("dup field", rn)
    for f in r["fields"]:
        if list(f) != [k for k in ("name", "type", "required", "required_when", "description") if k in f]:
            err("field key order", rn, f["name"])
        for m in re.findall(r"enum:([a-z_]+)", f["type"]):
            used.add(m)
            if m not in EN:
                err("UNDEFINED ENUM", rn, f["name"], m)
        if f["required"] not in (True, False):
            err("required not bool", rn, f["name"])
    if rn != "common":
        for k in r["primary_key"]:
            if k not in names and not (rn == "spec_attribute" and k == "type_id"):
                err("pk not a field", rn, k)
        if not isinstance(r["core"], bool):
            err("core not bool", rn)
# enums referenced only inside object descriptions (documented use)
described = {"derivation", "provenance_role", "field_resolution_rule", "ref_kind", "bound_from", "param_source", "invariant_result"}
alltext = json.dumps(S, ensure_ascii=False)
for e in EN:
    if e not in used and ("enum:" + e) not in alltext:
        err("enum never referenced", e)
for e, vals in EN.items():
    if len(vals) != len(set(vals)):
        err("dup enum value", e)
if set(APPLIES) - set(RS):
    err("applies_to unknown", set(APPLIES) - set(RS))
for k, v in S["factor_stage_requirements"]["by_param_kind"].items():
    if k not in EN["param_kind"] or set(v["required_stages"]) - set(EN["lifecycle_stage"]):
        err("stage requirement enum", k)
if set(S["resolution_orders"]["param_binding"]["order"]) - set(EN["bound_from"]):
    err("resolution order param_binding not in bound_from")
if not set(EN["param_source"]) <= set(S["resolution_orders"]["conversion_parameter"]["order"]):
    err("param_source not in conversion order")
allfields = {f["name"] for r in RS.values() for f in r["fields"]} | set(COMMON)
for f in S["forbidden_value_fields"]["free_text_fields_to_scan"]["fields"]:
    if f not in allfields:
        err("free text field not defined anywhere", f)
for p in S["conventions"]["id_prefixes"]:
    pass
inv_ids = [i["id"] for i in S["invariants"]]
if inv_ids != ["INV-%02d" % (i + 1) for i in range(len(inv_ids))]:
    err("invariant ids not sequential", inv_ids)
# every INV-nn / stop code / warning code mentioned in the schema text exists
for m in set(re.findall(r"INV-(\d\d)", alltext)):
    if "INV-" + m not in inv_ids:
        err("schema mentions undefined", "INV-" + m)
CODES = set(EN["stop_code"]) | set(EN["warning_code"])
for m in set(re.findall(r"\b[A-Z][A-Z_]{5,}\b", alltext)):
    pass
# removed names must not survive anywhere in the three JSON files
REMOVED = ["TYPE_REPRESENTATIVE\"", "STARTER_SET", "OLDER_ID", "curated_ratio", "occurrence_count", "mass_per_unit_ref", "MASS_PER_UNIT",
           "sort_key", "default_included", "derivation_rule", "operation_count\": {\"pick\": 2, \"enter\": 2, \"search\": 0, \"accept\": 0, \"override\": 0}, \"candidate_counts\": [9, 1],\n      \"assembly_id",
           "evidence_level", "thickness_m\"", "normalization_trace", "identity_string_for_illustration", "\"PRODUCT\"", "FORMED_PRODUCT\", \"EQUIPMENT_UNIT"]
for name, doc in (("schema", S), ("tree", T), ("examples", E)):
    txt = json.dumps(doc, ensure_ascii=False)
    for w in REMOVED:
        if w in txt:
            err("removed name survives in", name, w)
ok("B: レコード定義の自己整合（列挙の参照、主キー、項目の重複、不変条件の連番、廃止した名前が残っていない）")

# ------------------------------------------------------------------ C. tree
NODE_F = {f["name"]: f for f in RS["classification_node"]["fields"]}
nodes = {}
for n in T["nodes"]:
    if n["node_id"] in nodes:
        err("dup node", n["node_id"])
    nodes[n["node_id"]] = n
    extra = set(n) - set(NODE_F) - set(COMMON)
    if extra:
        err("node extra field", n["node_id"], extra)
    for fn, f in NODE_F.items():
        if f["required"] is True and fn not in n:
            err("node missing", n["node_id"], fn)
    if n["axis"] not in EN["axis"] or n["level_kind"] not in EN["level_kind"] or n["status"] not in EN["record_status"]:
        err("node enum", n["node_id"])
    if not re.match(r"^(FN|IN)-\d{6,}$", n["node_id"]):
        err("node id format", n["node_id"])
    if (n["node_id"][:2] == "FN") != (n["axis"] == "FUNCTION"):
        err("prefix/axis", n["node_id"])
    if re.search(r"その他|未分類", n["name"]) or re.search(r"OTHER|MISC|UNCLASS", n["code"] or ""):
        err("catch-all node", n["node_id"], n["name"])
    if ("default_input_group" in n) != (n["level_kind"] == "GROUP"):
        err("default_input_group placement", n["node_id"])
    if "default_input_group" in n and n["default_input_group"] not in EN["input_group"]:
        err("input_group enum", n["node_id"])
    if ("allowed_item_kinds" in n) != (n["level_kind"] == "SUBSTANCE_CLASS"):
        err("allowed_item_kinds placement", n["node_id"])
    if set(n.get("allowed_item_kinds", [])) - set(EN["item_kind"]):
        err("item_kind enum", n["node_id"])
    if n["status"] == "ACTIVE":
        err("tree has ACTIVE node (should be none in draft)", n["node_id"])
PARENT_KIND = {"DIVISION": None, "SUBSTANCE_CLASS": None, "GROUP": "DIVISION", "ELEMENT": "GROUP"}
for n in T["nodes"]:
    pk = PARENT_KIND[n["level_kind"]]
    if pk is None:
        if n["parent"] is not None:
            err("parent should be null", n["node_id"])
    elif n["parent"] not in nodes or nodes[n["parent"]]["level_kind"] != pk or nodes[n["parent"]]["axis"] != n["axis"]:
        err("parent kind", n["node_id"])
c = collections.Counter((n["axis"], n["level_kind"], n["code"]) for n in T["nodes"])
if [k for k, v in c.items() if v > 1]:
    err("code not unique in (axis, level)")
for m in T["directive_group_mapping"]:
    n = nodes.get(m["node_id"])
    if not n or n["code"] != m["code"] or n["name"] != m["directive_group"] or n["level_kind"] != "GROUP" or n["status"] == "RESERVED":
        err("directive mapping", m)
if len(T["directive_group_mapping"]) != 9:
    err("directive mapping count")
for w in T["withdrawn_draft_ids"]["ids"]:
    if w["node_id"] in nodes:
        err("withdrawn id still present", w["node_id"])
lvk = {(x["axis"], x["level_kind"]): x["level"] for x in T["levels"]}
if set(k[1] for k in lvk) != set(EN["level_kind"]):
    err("levels table vs level_kind enum")
SRC_F = {f["name"]: f for f in RS["source"]["fields"]}
tsrc = {s_["source_id"]: s_ for s_ in T["sources"]}
for s_ in T["sources"]:
    if set(s_) != set(SRC_F):
        err("tree source fields", set(s_) ^ set(SRC_F))
    if s_["license_status"] == "PERMITTED_PUBLIC" and not s_["license_evidence_ref"]:
        err("tree source evidence")
nd = T["node_defaults"]
if set(nd) - {"note"} != set(COMMON) - {"status", "retired_in_release", "replaced_by"}:
    err("node_defaults fields", set(nd) ^ set(COMMON))
relied = [tsrc[p["source_id"]]["license_status"] for p in nd["provenance"] if p["role"] == "RELIED_ON"]
if not relied or max(relied, key=LIC_ORDER.index) != nd["license_status"]:
    err("node_defaults license not derived from provenance")
cnt = collections.Counter((n["axis"], n["level_kind"]) for n in T["nodes"])
N_NODES, N_FUNC, N_ITEM = len(nodes), sum(v for k, v in cnt.items() if k[0] == "FUNCTION"), sum(v for k, v in cnt.items() if k[0] == "ITEM")
N_ELEM, N_RESERVED = cnt[("FUNCTION", "ELEMENT")], sum(1 for n in T["nodes"] if n["status"] == "RESERVED")
ok("C: 分類階層（%dノード＝部位軸%d＋品目軸%d、部位要素%d、予約%d。親子・符号の一意・受け皿ノード無し・9区分の対応・出典から導いた状態）"
   % (N_NODES, N_FUNC, N_ITEM, N_ELEM, N_RESERVED))

# ------------------------------------------------------------------ D. example records: fields, types, enums
ILL = E["illustration_only"]
ILL_F = set(ILL["fields"])
for k in E:
    if isinstance(E[k], (list, dict)) and k not in RS and k not in ILL["sections"] and k != "illustration_only":
        err("example section not in schema and not declared illustration-only", k)
for k in ILL["sections"]:
    if k not in E:
        err("illustration section missing", k)


def check_type(val, typ, where):
    nullable = typ.endswith("|null")
    t = typ[:-5] if nullable else typ
    if val is None:
        if not nullable:
            err("NULL not allowed", where, typ)
        return
    if t.startswith("enum:"):
        if val not in EN[t[5:]]:
            err("BAD ENUM", where, val)
    elif t.startswith("array<"):
        if not isinstance(val, list):
            return err("NOT ARRAY", where)
        inner = t[6:-1]
        for v in val:
            if inner.startswith("enum:") and v not in EN[inner[5:]]:
                err("BAD ENUM in array", where, v)
            if inner == "string" and not isinstance(v, str):
                err("array elem not string", where, v)
            if inner == "integer" and not isinstance(v, int):
                err("array elem not int", where, v)
            if inner == "object" and not isinstance(v, dict):
                err("array elem not object", where, v)
    elif t in ("string", "date"):
        if not isinstance(val, str):
            err("NOT STRING", where, val)
        if t == "date" and not re.match(r"^\d{4}-\d{2}-\d{2}$", val):
            err("NOT DATE", where, val)
    elif t == "integer":
        if not isinstance(val, int) or isinstance(val, bool):
            err("NOT INT", where, val)
    elif t == "number":
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            err("NOT NUM", where, val)
    elif t == "boolean":
        if not isinstance(val, bool):
            err("NOT BOOL", where, val)
    elif t == "object":
        if not isinstance(val, dict):
            err("NOT OBJ", where, val)
    else:
        err("unknown type", where, typ)


PK = {rn: r["primary_key"] for rn, r in RS.items()}
n_rec = 0
for rn, r in RS.items():
    if rn in ("classification_node", "spec_attribute"):
        continue
    rows = E.get(rn)
    if rows is None:
        err("no examples for record", rn)
        continue
    allf = {f["name"]: f for f in r["fields"]}
    if rn in APPLIES:
        allf.update(COMMON)
    for row in rows:
        n_rec += 1
        rid = "/".join(str(row.get(k)) for k in PK[rn])
        if row.get("record_flag") != "FICTIONAL_PLACEHOLDER":
            err("NO FLAG", rn, rid)
        for fn, f in allf.items():
            if fn not in row:
                err("MISSING field", rn, rid, fn)
                continue
            check_type(row[fn], f["type"], "%s:%s.%s" % (rn, rid, fn))
        extra = set(row) - set(allf) - ILL_F
        if extra:
            err("EXTRA fields", rn, rid, sorted(extra))
        keys = [k for k in row if k in allf]
        want = [f["name"] for f in r["fields"]] + ([f["name"] for f in S["common_fields"]["fields"]] if rn in APPLIES else [])
        if keys != want:
            err("field order differs from schema", rn, rid)
for sec in ILL["sections"]:
    if isinstance(E[sec], list):
        for x in E[sec]:
            if x.get("record_flag") != "FICTIONAL_PLACEHOLDER":
                err("NO FLAG in", sec)
SA = {f["name"]: f for f in RS["spec_attribute"]["fields"]}
for mt in E["material_type"]:
    for a in mt["spec_attributes"]:
        if list(a) != list(SA):
            err("spec attr fields", mt["type_id"], set(a) ^ set(SA))
        for fn, f in SA.items():
            if fn in a:
                check_type(a[fn], f["type"], "spec:%s.%s" % (mt["type_id"], fn))
ok("D: 例示レコード %d 件の必須項目・型・列挙値・項目の過不足と順序（定義に無い項目は illustration_only に列挙したものだけ）" % n_rec)

# ------------------------------------------------------------------ E. references
idx = {}
for rn in RS:
    if rn in ("classification_node", "spec_attribute", "assembly_component", "normalized_record"):
        continue
    for r in E[rn]:
        k = r[PK[rn][0]]
        if k in idx:
            err("DUP ID", k)
        idx[k] = (rn, r)
ASSUMED = set(E["assumed_active_nodes"]["node_ids"])
for x in ASSUMED:
    if x not in nodes:
        err("assumed-active node not in tree", x)
    elif nodes[x]["status"] == "RESERVED":
        err("assumed-active node is RESERVED", x)
    elif nodes[x]["parent"] and nodes[x]["parent"] not in ASSUMED:
        err("assumed-active node's parent not assumed active", x)


def ref(x, kinds, where):
    """kinds: 許される参照先の種別（'node' は分類ノード）。"""
    if x is None:
        return None
    if x in nodes:
        if "node" not in kinds:
            err("REF wrong kind", where, x)
        return nodes[x]
    if x not in idx:
        err("BROKEN REF", where, x)
        return None
    if idx[x][0] not in kinds:
        err("REF wrong kind", where, x, idx[x][0])
    return idx[x][1]


def status_of(x):
    if x in nodes:
        return "ACTIVE" if x in ASSUMED else nodes[x]["status"]
    return idx[x][1].get("status")


catalog_refs = collections.defaultdict(list)   # record id -> referenced catalog ids (for INV-11)


def cref(owner, x, kinds, where):
    r = ref(x, kinds, where)
    if x is not None:
        catalog_refs[owner].append(x)
    return r


def check_prov(owner, prov, where):
    if not prov:
        err("INV-01 no provenance", where)
    for p in prov:
        if list(p) != ["source_id", "raw_id", "derivation", "role", "via_merge_event_id"]:
            err("provenance keys", where, list(p))
            continue
        ref(p["source_id"], {"source"}, where + ".prov")
        ref(p["raw_id"], {"raw_record"}, where + ".prov")
        ref(p["via_merge_event_id"], {"merge_event"}, where + ".prov")
        if p["derivation"] not in EN["derivation"] or p["role"] not in EN["provenance_role"]:
            err("provenance enum", where)
        if p["raw_id"] and idx.get(p["raw_id"]) and idx[p["raw_id"]][1]["source_id"] != p["source_id"]:
            err("provenance raw/source mismatch", where)
        if p["raw_id"] and idx.get(p["raw_id"]) and idx[p["raw_id"]][1]["intake_status"] != "ACCEPTED":
            err("provenance points to non-accepted raw", where, p["raw_id"])
        if p["source_id"] in idx and idx[p["source_id"]][1]["storage_policy"] == "DO_NOT_INGEST":
            err("provenance points to non-ingested source", where)


for r in E["release"]:
    ref(r["parent_release_id"], {"release"}, "rel.parent")
    if r["schema_version"] != S["schema_version"]:
        err("release schema_version != schema", r["release_id"])
    if set(r["invariant_report"]) != set(inv_ids) or set(r["invariant_report"].values()) - set(EN["invariant_result"]):
        err("invariant_report keys/values")
    for x in r["breaking_change_ids"]:
        ref(x, set(RS), "rel.breaking")
    if r["status"] == "PUBLISHED" and (set(r["invariant_report"].values()) != {"PASS"} or r["manifest_hash"] is None):
        err("published release with non-PASS invariants")
for r in E["raw_record"]:
    ref(r["source_id"], {"source"}, "raw.src")
    ref(r["duplicate_of_raw"], {"raw_record"}, "raw.dup")
    ref(r["ingested_in_release"], {"release"}, "raw.rel")
    s_ = idx[r["source_id"]][1]
    if s_["license_status"] != "PERMITTED_PUBLIC" or s_["storage_policy"] == "DO_NOT_INGEST":
        err("raw record from a source that did not pass the gate", r["raw_id"])
    if r["class_text"] is not None and "CLASSIFICATION_LABELS" not in s_["content_kinds"]:
        err("class_text stored though source content_kinds does not allow", r["raw_id"])
    if (r["intake_status"] == "DUPLICATE_RAW") != (r["duplicate_of_raw"] is not None):
        err("duplicate_of_raw required_when", r["raw_id"])
    if (r["intake_status"] in ("REJECTED_FORMAT", "OUT_OF_SCOPE")) != (r["intake_note"] is not None):
        err("intake_note required_when", r["raw_id"])
    if r["content_hash"] != h([r["source_id"], r["name_text"], r["spec_text"], r["unit_text"], r["class_text"]]):
        err("content_hash mismatch", r["raw_id"])
    if r["duplicate_of_raw"] and idx[r["duplicate_of_raw"]][1]["content_hash"] != r["content_hash"]:
        err("duplicate hash differs", r["raw_id"])
seen = {}
for r in E["raw_record"]:
    if r["content_hash"] in seen and r["intake_status"] != "DUPLICATE_RAW":
        err("same content_hash but not marked duplicate", r["raw_id"])
    seen.setdefault(r["content_hash"], r["raw_id"])
for s_ in E["source"]:
    if (s_["license_status"] == "PERMITTED_PUBLIC") != (s_["license_evidence_ref"] is not None):
        err("license_evidence_ref required_when", s_["source_id"])
    if s_["license_status"] != "PERMITTED_PUBLIC" and s_["storage_policy"] != "DO_NOT_INGEST":
        err("gate: non-permitted source must not be ingested", s_["source_id"])
NT = {}
for r in E["normalized_record"]:
    raw = ref(r["raw_id"], {"raw_record"}, "norm.raw")
    if raw and raw["intake_status"] != "ACCEPTED":
        err("normalized_record for non-accepted raw", r["raw_id"])
    ref(r["resolved_to"], {"canonical_material"}, "norm.resolved")
    ref(r["resolved_in_release"], {"release"}, "norm.rel")
    ref(r["unit_code"], {"unit_def"}, "norm.unit")
    if (r["resolved_to"] is None) != (r["resolved_in_release"] is None):
        err("resolved_in_release consistency", r["raw_id"])
    if r["resolved_to"] and status_of(r["resolved_to"]) != "ACTIVE":
        err("normalized_record resolved to non-ACTIVE", r["raw_id"])
    for t_ in r["spec_tokens"]:
        if list(t_) != ["attribute_code", "value", "unit_code", "unit_assumed", "matched_text"]:
            err("spec_token keys", r["raw_id"])
        ref(t_["unit_code"], {"unit_def"}, "norm.token.unit")
        if t_["unit_assumed"] != ("SPEC_UNIT_ASSUMED" in r["flags"]):
            err("SPEC_UNIT_ASSUMED flag vs token", r["raw_id"])
    if (r["raw_id"], r["normalizer_version"]) in NT:
        err("dup normalized_record", r["raw_id"])
    NT[(r["raw_id"], r["normalizer_version"])] = r
    if r["residual_text"] and "RESIDUAL_TEXT" not in r["flags"]:
        err("residual without flag", r["raw_id"])
    if r["resolved_to"] is None and not (set(r["flags"]) & {"ALIAS_UNRESOLVED", "ALIAS_AMBIGUOUS", "SPEC_TOKEN_UNASSIGNED", "RESIDUAL_TEXT", "UNIT_UNKNOWN"}):
        err("unresolved without a reason flag", r["raw_id"])
for r in E["raw_record"]:
    has = any(k[0] == r["raw_id"] for k in NT)
    if has != (r["intake_status"] == "ACCEPTED"):
        err("normalized_record coverage (ACCEPTED raw <-> normalized)", r["raw_id"])
for r in E["curation_decision"]:
    for x in r["raw_ids"]:
        ref(x, {"raw_record"}, "cd.raw")
    for x in r["subject_ids"]:
        ref(x, set(RS), "cd.subject")
    ref(r["release_id"], {"release"}, "cd.rel")
    if r["restricted_source_not_consulted"] is not True:
        err("decision consulted restricted source", r["decision_id"])
    if r["reviewed_by"] is not None and r["reviewed_by"] == r["decided_by"]:
        err("INV-22 decision", r["decision_id"])
# every assumed spec unit that got resolved has a SPEC_UNIT_CONFIRMED decision; every OUT_OF_SCOPE raw has a decision
conf = {x for r in E["curation_decision"] if r["decision_kind"] == "SPEC_UNIT_CONFIRMED" for x in r["raw_ids"]}
oos = {x for r in E["curation_decision"] if r["decision_kind"] == "MARKED_OUT_OF_SCOPE" for x in r["raw_ids"]}
for r in E["normalized_record"]:
    if "SPEC_UNIT_ASSUMED" in r["flags"] and r["resolved_to"] and r["raw_id"] not in conf:
        err("assumed unit resolved without SPEC_UNIT_CONFIRMED decision", r["raw_id"])
for r in E["raw_record"]:
    if r["intake_status"] == "OUT_OF_SCOPE" and r["raw_id"] not in oos:
        err("OUT_OF_SCOPE without decision", r["raw_id"])
UD = {u["unit_code"]: u for u in E["unit_def"]}
for u in E["unit_def"]:
    ref(u["base_unit_code"], {"unit_def"}, "ud.base")
    if (u["dimension"] not in ("COUNT", "LUMP_SUM")) != (u["to_base_factor"] is not None):
        err("to_base_factor required_when", u["unit_code"])
    if u["base_unit_code"] in UD and UD[u["base_unit_code"]]["dimension"] != u["dimension"]:
        err("base unit dimension", u["unit_code"])
MT = {m["type_id"]: m for m in E["material_type"]}
CM = {m["canonical_id"]: m for m in E["canonical_material"]}
for m in E["material_type"]:
    o = m["type_id"]
    cref(o, m["substance_class_id"], {"node"}, "mt.class")
    if m["substance_class_id"] and nodes[m["substance_class_id"]]["level_kind"] != "SUBSTANCE_CLASS":
        err("substance class kind", o)
    ref(m["declared_unit"], {"unit_def"}, "mt.unit")
    ref(m["merged_into"], {"material_type"}, "mt.merged")
    cref(o, m["representative_material_id"], {"canonical_material"}, "mt.rep")
    ref(m["created_in_release"], {"release"}, "mt.rel")
    for x in m["replaced_by"]:
        ref(x, {"material_type"}, "mt.repl")
    if (m["representative_rule"] != "NOT_DECIDED") != (m["representative_basis_note"] is not None):
        err("representative_basis_note required_when", o)
    codes = [a["attribute_code"] for a in m["spec_attributes"]]
    if len(codes) != len(set(codes)):
        err("dup attribute_code", o)
    for a in m["spec_attributes"]:
        ref(a["unit_code"], {"unit_def"}, "attr.unit")
        if (a["value_type"] == "DECIMAL") != (a["unit_code"] is not None):
            err("attr unit required_when", o)
        if (a["role"] == "IDENTITY") and a["axis_mode"] is None:
            err("axis_mode required_when", o)
        if (a["value_type"] == "ENUM") != (a["allowed_values"] is not None):
            err("allowed_values required_when", o)
        if (a["allowed_values"] is not None) != (a["allowed_values_provenance"] is not None):
            err("allowed_values_provenance required_when", o)
        if a["allowed_values_provenance"]:
            check_prov(o, a["allowed_values_provenance"], o + ".allowed_values")
        if "UNKNOWN" in a["affects"] and a["role"] != "IDENTITY":
            err("UNKNOWN affects must be IDENTITY", o)
        want = {"DECIMAL": "DECIMAL_PLAIN", "ENUM": "ENUM_CODE", "TEXT": "TEXT_NFKC"}[a["value_type"]]
        if a["canonical_format"] != want:
            err("canonical_format vs value_type", o)
        for pp in a["parse_patterns"]:
            if list(pp) != ["prefix_tokens", "suffix_tokens", "assumed_unit_code"]:
                err("parse_pattern keys", o)
            ref(pp["assumed_unit_code"], {"unit_def"}, "parse.unit")
for m in E["canonical_material"]:
    o = m["canonical_id"]
    t_ = cref(o, m["type_id"], {"material_type"}, "cm.type")
    ref(m["merged_into"], {"canonical_material"}, "cm.merged")
    for x in m["replaced_by"]:
        ref(x, {"canonical_material"}, "cm.repl")
    if (m["material_kind"] == "PRODUCT_SPECIFIC") != (m["product_key"] is not None):
        err("product_key required_when", o)
    arr = ["v2", m["type_id"], m["material_kind"], [[k, m["attribute_values"][k]] for k in sorted(m["attribute_values"])], m["product_key"]]
    if m["identity_array_for_illustration"] != arr or m["identity_key"] != h(arr):
        err("identity_key mismatch", o)
    if t_:
        ident = {a["attribute_code"]: a for a in t_["spec_attributes"] if a["role"] == "IDENTITY"}
        if set(m["attribute_values"]) - set(ident):
            err("attribute_values has non-identity attr", o)
        if m["status"] == "ACTIVE":
            miss = [k for k, a in ident.items() if a["required"] and k not in m["attribute_values"]]
            if miss:
                err("ACTIVE cm missing identity attr", o, miss)
        for k, v in m["attribute_values"].items():
            a = ident.get(k)
            if a and a["value_type"] == "ENUM" and v not in a["allowed_values"]:
                err("attr value not allowed", o, k, v)
            if a and a["value_type"] == "DECIMAL" and not re.match(r"^(0|[1-9]\d*)(\.\d*[1-9])?$", v):
                err("attr value not DECIMAL_PLAIN", o, k, v)
        # mass path status must be derivable
        decl = t_["declared_unit"]
        if UD[decl]["dimension"] == "MASS":
            want = "DIRECT"
        else:
            paths = [u for u in E["unit_conversion"] if u["status"] == "ACTIVE" and u["scope_id"] in (o, m["type_id"]) and UD[u["to_unit"]]["dimension"] == "MASS"]
            want = "NOT_REGISTERED" if not paths else ("CONVERTIBLE" if any(u["conversion_status"] == "USABLE" for u in paths) else "BLOCKED_BASIS_MISSING")
        if m["status"] == "ACTIVE" and m["mass_path_status"] != want:
            err("mass_path_status not derivable", o, m["mass_path_status"], want)
for a in E["alias"]:
    o = a["alias_id"]
    kinds = {"FUNCTION_NODE": {"node"}, "MATERIAL_TYPE": {"material_type"}, "CANONICAL_MATERIAL": {"canonical_material"}, "ASSEMBLY": {"assembly"}}[a["target_kind"]]
    for x in a["target_ids"]:
        cref(o, x, kinds, "alias.target")
    cref(o, a["context_node_id"], {"node"}, "alias.ctx")
for u in E["unit_conversion"]:
    o = u["conversion_id"]
    sc_ = cref(o, u["scope_id"], {"MATERIAL_TYPE": {"material_type"}, "CANONICAL_MATERIAL": {"canonical_material"}}[u["scope_kind"]], "uc.scope")
    ref(u["from_unit"], {"unit_def"}, "uc.from")
    ref(u["to_unit"], {"unit_def"}, "uc.to")
    ref(u["basis_unit_code"], {"unit_def"}, "uc.basis_unit")
    dims = {"DENSITY": ("VOLUME", "MASS"), "THICKNESS": ("AREA", "VOLUME"), "MASS_PER_AREA": ("AREA", "MASS"), "MASS_PER_LENGTH": ("LENGTH", "MASS"),
            "MASS_PER_PIECE": ("COUNT", "MASS"), "AREA_PER_PIECE": ("COUNT", "AREA"), "LENGTH_PER_PIECE": ("COUNT", "LENGTH"),
            "COUNT_NOUN_EQUIVALENCE": ("COUNT", "COUNT")}[u["conversion_kind"]]
    if (UD[u["from_unit"]]["dimension"], UD[u["to_unit"]]["dimension"]) != dims:
        err("conversion direction/dimension", o)
    if (u["basis_origin"] in ("IDENTITY_ATTRIBUTE", "ROW_PARAMETER")) != (u["basis_unit_code"] is not None):
        err("basis_unit_code required_when", o)
    if (u["basis_origin"] == "IDENTITY_ATTRIBUTE") != (u["basis_attribute_code"] is not None):
        err("basis_attribute_code required_when", o)
    if (u["basis_origin"] == "ROW_PARAMETER") != bool(u["param_source_order"]):
        err("param_source_order required_when", o)
    if (u["basis_origin"] == "CURATED_EQUIVALENCE") != (u["equivalence_evidence_kind"] is not None):
        err("equivalence_evidence_kind required_when", o)
    if u["basis_origin"] == "CURATED_EQUIVALENCE" and u["conversion_kind"] != "COUNT_NOUN_EQUIVALENCE":
        err("curated equivalence only for count nouns", o)
    if u["basis_origin"] == "EXTERNAL_LEDGER" and (u["basis_ref"] is None) != (u["basis_value_state"] == "MISSING"):
        err("basis_value_state vs basis_ref", o)
    if re.search(r"_(mm|m|m2|m3|kg)$|_per_", u["basis_parameter"]) and u["basis_parameter"] not in ("area_per_piece", "length_per_piece", "mass_per_piece", "mass_per_area", "mass_per_length"):
        err("unit embedded in basis_parameter name", o, u["basis_parameter"])
    if u["basis_origin"] == "IDENTITY_ATTRIBUTE":
        t_ = sc_ if u["scope_kind"] == "MATERIAL_TYPE" else MT[sc_["type_id"]]
        a = {a["attribute_code"]: a for a in t_["spec_attributes"]}.get(u["basis_attribute_code"])
        if not a or a["quantity_kind"] != "DIMENSION" or a["unit_code"] != u["basis_unit_code"] or a["role"] != "IDENTITY":
            err("INV-04 identity-attribute basis must be a DIMENSION attribute with the same unit", o)
    want = "USABLE"
    if u["basis_value_state"] == "MISSING":
        want = "BLOCKED_BASIS_MISSING"
    elif u["basis_license_status"] != "PERMITTED_PUBLIC":
        want = "BLOCKED_LICENSE"
    if u["conversion_status"] != want and u["conversion_status"] != "RETIRED":
        err("INV-08 conversion_status not derivable", o, u["conversion_status"], want)
for p in E["placement"]:
    o = p["placement_id"]
    n = cref(o, p["function_node_id"], {"node"}, "pl.node")
    if n and n["level_kind"] != "ELEMENT":
        err("INV-09 placement not on ELEMENT", o)
    t_ = cref(o, p["type_id"], {"material_type"}, "pl.type")
    ref(p["entry_unit"], {"unit_def"}, "pl.unit")
    for x in p["material_ids_limit"]:
        cref(o, x, {"canonical_material"}, "pl.limit")
    cref(o, p["representative_override_id"], {"canonical_material"}, "pl.rep")
    if t_ and p["entry_unit"] and p["entry_unit"] != t_["declared_unit"]:
        if not [u for u in E["unit_conversion"] if u["scope_id"] == p["type_id"] and u["from_unit"] == p["entry_unit"] and u["to_unit"] == t_["declared_unit"]]:
            err("placement entry_unit has no registered conversion to declared unit", o)
AS = {a["assembly_id"]: a for a in E["assembly"]}
for a in E["assembly"]:
    o = a["assembly_id"]
    n = cref(o, a["function_node_id"], {"node"}, "as.node")
    if n and n["level_kind"] not in ("ELEMENT", "GROUP"):
        err("assembly node kind", o)
    cref(o, a["composite_material_id"], {"canonical_material"}, "as.comp")
    ref(a["driver_unit"], {"unit_def"}, "as.unit")
    if UD[a["driver_unit"]]["dimension"] != a["driver_dimension"]:
        err("driver_dimension vs driver_unit", o)
    if (a["assembly_kind"] != "COMPOSITE_PRODUCT") != (a["function_node_id"] is not None) or (a["assembly_kind"] == "COMPOSITE_PRODUCT") != (a["composite_material_id"] is not None):
        err("assembly required_when", o)
seen_ac = set()
for c in E["assembly_component"]:
    o = c["assembly_id"]
    a = ref(c["assembly_id"], {"assembly"}, "ac.as")
    tgt = cref(o, c["target_id"], {"MATERIAL_TYPE": {"material_type"}, "CANONICAL_MATERIAL": {"canonical_material"}}[c["target_kind"]], "ac.target")
    ref(c["component_unit"], {"unit_def"}, "ac.unit")
    ref(c["ratio_param_unit_code"], {"unit_def"}, "ac.punit")
    pl_ = cref(o, c["placement_id"], {"placement"}, "ac.pl")
    typ = tgt if c["target_kind"] == "MATERIAL_TYPE" else MT[tgt["type_id"]]
    if c["component_unit"] != typ["declared_unit"]:
        err("INV-12 component_unit != declared unit", o, c["line_no"])
    if pl_ and pl_["type_id"] != typ["type_id"]:
        err("component placement type mismatch", o, c["line_no"])
    if (c["ratio_basis"] in ("GEOMETRIC_DEFINITION", "ROW_PARAMETER")) != (c["ratio_param_name"] is not None) or (c["ratio_param_name"] is None) != (c["ratio_param_unit_code"] is None):
        err("ratio_param required_when", o, c["line_no"])
    if (c["ratio_basis"] == "DRIVER_IDENTITY") != (c["component_measure"] is not None):
        err("component_measure required_when", o, c["line_no"])
    if c["ratio_basis"] == "DRIVER_IDENTITY" and not (a["driver_measure"] and c["component_measure"] == a["driver_measure"] and c["component_unit"] == a["driver_unit"]):
        err("INV-12 DRIVER_IDENTITY needs same unit and measure", o, c["line_no"])
    if c["ratio_basis"] == "EXTERNAL_LEDGER" and (c["ratio_ref"] is None) != (c["ratio_value_state"] == "MISSING"):
        err("ratio_value_state vs ratio_ref", o, c["line_no"])
    if (o, c["line_no"]) in seen_ac or (o, typ["type_id"]) in seen_ac:
        err("assembly has duplicate line or duplicate type", o, c["line_no"])
    seen_ac |= {(o, c["line_no"]), (o, typ["type_id"])}
for l in E["similarity_link"]:
    o = l["link_id"]
    kinds = {"MATERIAL_TYPE": {"material_type"}, "CANONICAL_MATERIAL": {"canonical_material"}}[l["target_kind"]]
    cref(o, l["left_id"], kinds, "sl.left")
    cref(o, l["right_id"], kinds, "sl.right")
    if l["substitution_policy"] == "ALLOWED_WITH_FLAG" and l["verification_status"] == "NOT_VERIFIED":
        err("substitution allowed without verification", o)
    if l["reviewed_by"] is not None and l["reviewed_by"] == l["decided_by"]:
        err("INV-22 link", o)
for b in E["param_binding"]:
    o = b["binding_id"]
    kinds = {"CANONICAL_MATERIAL": {"canonical_material"}, "PLACEMENT": {"placement"}, "MATERIAL_TYPE": {"material_type"}, "FUNCTION_NODE": {"node"}}[b["scope_kind"]]
    cref(o, b["scope_id"], kinds, "pb.scope")
    ref(b["binding_unit"], {"unit_def"}, "pb.unit")
    lk = ref(b["proxy_link_id"], {"similarity_link"}, "pb.proxy")
    if b["param_kind"] == "FACTOR" and b["scope_kind"] not in ("CANONICAL_MATERIAL", "MATERIAL_TYPE"):
        err("FACTOR bound outside item side", o)
    bound = b["param_kind"] == "FACTOR" and b["param_ref"] is not None
    if bound and (b["binding_unit"] is None or not b["stages"] or b["link_basis"] is None):
        err("factor binding required_when", o)
    if (b["link_basis"] == "PROXY") != (b["proxy_reason"] is not None) or (b["link_basis"] == "PROXY") != (b["proxy_link_id"] is not None):
        err("proxy required_when", o)
    if b["link_basis"] == "PROXY" and b["status"] == "ACTIVE" and not (lk and lk["relation"] == "PROXY_CANDIDATE" and lk["substitution_policy"] == "ALLOWED_WITH_FLAG"):
        err("INV-19", o)
    if (b["priority_rank"] is not None) != (b["rank_decided_by"] is not None) or (b["priority_rank"] is not None) != (b["rank_reason"] is not None):
        err("rank required_when", o)
    if (b["param_ref"] is None) != (b["value_state"] == "MISSING"):
        err("binding value_state vs param_ref", o)
    if b["param_ref"] is None and b["param_license_status"] != "UNKNOWN":
        err("unbound binding param_license_status must be UNKNOWN", o)
    if b["status"] == "ACTIVE" and b["param_ref"] is None:
        err("ACTIVE binding without param_ref", o)
ME = {m["merge_event_id"]: m for m in E["merge_event"]}
for m in E["merge_event"]:
    o = m["merge_event_id"]
    kinds = {"MATERIAL_TYPE": {"material_type"}, "CANONICAL_MATERIAL": {"canonical_material"}}[m["target_kind"]]
    ref(m["survivor_id"], kinds, "me.surv")
    for x in m["merged_ids"]:
        ref(x, kinds, "me.merged")
    for x in m["aliases_created"]:
        ref(x, {"alias"}, "me.alias")
    for x in m["affected_descendant_ids"]:
        ref(x, {"canonical_material"}, "me.desc")
    ref(m["reverts_event_id"], {"merge_event"}, "me.reverts")
    ref(m["caused_by_event_id"], {"merge_event"}, "me.cause")
    ref(m["release_id"], {"release"}, "me.rel")
    RK = {"ALIAS": "alias", "PLACEMENT": "placement", "PARAM_BINDING": "param_binding", "UNIT_CONVERSION": "unit_conversion",
          "SIMILARITY_LINK": "similarity_link", "CANONICAL_MATERIAL": "canonical_material"}
    for rp in m["repointed_refs"]:
        if list(rp) != ["ref_kind", "ref_id", "field", "from_id", "to_id"] or rp["ref_kind"] not in EN["ref_kind"]:
            err("repointed_refs shape", o)
            continue
        tgt = ref(rp["ref_id"], {RK[rp["ref_kind"]]}, "me.repoint")
        ref(rp["from_id"], set(RS), "me.repoint.from")
        ref(rp["to_id"], set(RS), "me.repoint.to")
        if tgt is not None and rp["field"] not in tgt:
            err("repointed field not on record", o, rp)
    for f_ in m["field_resolutions"]:
        if list(f_) != ["field", "kept_value", "discarded_values", "rule"] or f_["rule"] not in EN["field_resolution_rule"]:
            err("field_resolutions shape", o)
    is_merge = m["event_kind"] == "MERGE"
    for fn in ("duplicate_level", "survivor_rule_applied", "license_before", "license_after"):
        if is_merge != (m[fn] is not None):
            err("merge_event required_when", o, fn)
    if is_merge != (m["reverts_event_id"] is None):
        err("reverts_event_id required_when", o)
    need_review = (m["duplicate_level"] in ("D2_UNIT_VARIANT", "D3_NEAR", "D4_CROSS_SOURCE")) or not is_merge
    if need_review and m["reviewed_by"] is None:
        err("merge_event reviewer required", o)
    if m["reviewed_by"] is not None and m["reviewed_by"] == m["decided_by"]:
        err("INV-22 merge_event", o)
    if m["decided_by"] == "system" and m["duplicate_level"] != "D1_IDENTITY":
        err("automatic merge only for D1", o)
    if is_merge and m["license_before"] and LIC_ORDER.index(m["license_after"]) > LIC_ORDER.index(m["license_before"]):
        err("merge worsens license", o)
    if is_merge and m["duplicate_level"] == "D1_IDENTITY":
        ks = {idx[x][1]["identity_key"] for x in [m["survivor_id"]] + m["merged_ids"]}
        if len(ks) != 1:
            err("D1 merge with different identity_key", o)
ok("E: 参照（%d件の ID）がすべて解決し、参照先の種別が合い、required_when の条件と導出値（換算の状態、質量経路、ハッシュ）が定義と一致" % len(idx))

# ------------------------------------------------------------------ G. invariants on examples
CAT = [rn for rn in RS if rn in APPLIES and rn != "classification_node"]
SRC = {s_["source_id"]: s_ for s_ in E["source"]}
REVERTED = {m["reverts_event_id"] for m in E["merge_event"] if m["event_kind"] == "SPLIT"}
REL = {r["release_id"]: r for r in E["release"]}
for rn in CAT:
    for r in E[rn]:
        o = r[PK[rn][0]]
        check_prov(o, r["provenance"], "%s:%s" % (rn, o))                                   # INV-01
        relied = [SRC[p["source_id"]]["license_status"] for p in r["provenance"] if p["role"] == "RELIED_ON" and p["source_id"] in SRC]
        if not relied:
            err("INV-01/02 no RELIED_ON provenance", o)
        elif max(relied, key=LIC_ORDER.index) != r["license_status"]:
            err("INV-02 mismatch", o, r["license_status"])
        ref(r["created_in_release"], {"release"}, "common.rel")
        ref(r["retired_in_release"], {"release"}, "common.retired")
        rel = REL.get(r["created_in_release"])
        if r["compartment"] == "PUBLIC_RELEASE":                                           # INV-03
            if r["license_status"] != "PERMITTED_PUBLIC":
                err("INV-03 non-permitted record in PUBLIC_RELEASE", o)
            for p in r["provenance"]:
                s_ = SRC.get(p["source_id"])
                if s_ and (s_["storage_policy"] != "MAY_STORE_IN_PUBLIC_REPO" or not s_["license_evidence_ref"]):
                    err("INV-03 source", o, p["source_id"])
        if rel and rel["compartment"] != r["compartment"]:
            err("record compartment != release compartment", o)
        if r["status"] == "ACTIVE" and not r["reviewed_by"]:
            err("ACTIVE without reviewer", o)
        if r["reviewed_by"] is not None and r["reviewed_by"] == r["created_by"]:
            err("INV-22", o)
        if (r["status"] in ("MERGED", "DEPRECATED")) != (r["retired_in_release"] is not None):
            err("retired_in_release vs status", o)
        if r["status"] == "MERGED" and (r.get("merged_into") is None or r["replaced_by"] != [r["merged_into"]]):
            err("MERGED needs merged_into = replaced_by", o)
        if r["status"] != "MERGED" and r.get("merged_into") is not None:
            err("merged_into set on non-MERGED", o)
        if r["status"] == "RESERVED":
            err("RESERVED outside classification_node", o)
        if r["status"] == "ACTIVE":
            for p in r["provenance"]:
                if p["via_merge_event_id"] in REVERTED:
                    err("INV-21 provenance from a reverted merge remains", o)
            for x in catalog_refs.get(o, []):                                               # INV-11
                if status_of(x) != "ACTIVE":
                    err("INV-11 ACTIVE record references non-ACTIVE", o, x, status_of(x))
for c in E["assembly_component"]:                                                           # INV-11 for components
    if AS[c["assembly_id"]]["status"] == "ACTIVE":
        for x in (c["target_id"], c["placement_id"]):
            if x and status_of(x) != "ACTIVE":
                err("INV-11 component references non-ACTIVE", c["assembly_id"], x)
for rn, key in (("material_type", "type_id"), ("canonical_material", "canonical_id")):     # INV-11 chain depth
    for r in E[rn]:
        if r["merged_into"]:
            tgt = idx[r["merged_into"]][1]
            if tgt["merged_into"] is not None or tgt["status"] != "ACTIVE":
                err("INV-11 merged_into chain deeper than 1 or target not ACTIVE", r[key])
            if not [m for m in E["merge_event"] if m["event_kind"] == "MERGE" and r[key] in m["merged_ids"] and m["survivor_id"] == r["merged_into"]
                    and m["merge_event_id"] not in REVERTED]:
                err("MERGED record without a live merge_event", r[key])
# INV-04: forbidden value fields by name, attribute kinds, free-text scan
FORBID = re.compile(r"(emission|factor_value|gwp|service_life(?!_ref)|life_years|repair_rate(?!_ref)|leak|multiplier|price|cost|density(?!_)|mass_fraction|"
                    r"composition|ratio_value(?!_state)|curated_ratio|share)", re.I)
for rn, r in RS.items():
    if rn in ("calc_row", "selection"):
        continue
    for f in r["fields"]:
        if FORBID.search(f["name"]) and not f["name"].endswith(("_ref", "_state", "_id", "_note")):
            err("INV-04 forbidden value field name", rn, f["name"])
for m in E["material_type"]:
    for a in m["spec_attributes"]:
        if a["quantity_kind"] not in EN["attribute_quantity_kind"]:
            err("INV-04 quantity_kind", m["type_id"])
        if a["value_type"] == "DECIMAL":
            if a["quantity_kind"] not in ("DIMENSION", "NOMINAL_SIZE") or UD[a["unit_code"]]["dimension"] not in ("LENGTH", "AREA", "VOLUME"):
                err("INV-04 DECIMAL attribute must be a dimension/nominal size in LENGTH/AREA/VOLUME", m["type_id"], a["attribute_code"])
        if re.search(r"density|mass|weight|life|rate|factor|gwp|price", a["attribute_code"]):
            err("INV-04 attribute looks like a property/rate", m["type_id"], a["attribute_code"])
SCAN = set(S["forbidden_value_fields"]["free_text_fields_to_scan"]["fields"])
IDPAT = re.compile(r"[A-Z]{2,4}-(FICT-)?\d{4,}|U-\d\d|INV-\d\d")


def scan(o, where):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in SCAN and v is not None:
                txt = IDPAT.sub("", json.dumps(v, ensure_ascii=False))
                if re.search(r"[0-9０-９]", txt):
                    err("INV-04 digit in free-text field (needs human confirmation)", where, k, txt[:60])
            scan(v, where + "." + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            scan(v, where)


for rn in RS:
    if rn in E and rn not in ("calc_row", "selection"):
        scan(E[rn], rn)
scan(T["nodes"], "tree")
# INV-05 / INV-06 / INV-07
c = collections.Counter(r["identity_key"] for r in E["canonical_material"] if r["status"] == "ACTIVE")
if [k for k, v in c.items() if v > 1]:
    err("INV-05 duplicate identity among ACTIVE")
c = collections.Counter((a["normalized_key"], a["context_node_id"]) for a in E["alias"] if a["status"] == "ACTIVE")
if [k for k, v in c.items() if v > 1]:
    err("INV-06 duplicate alias key among ACTIVE")
for a in E["alias"]:
    if (a["resolution"] == "UNIQUE") != (len(a["target_ids"]) == 1) or (a["resolution"] == "AMBIGUOUS") != (len(a["target_ids"]) >= 2):
        err("INV-06 resolution vs targets", a["alias_id"])
for m in E["material_type"]:
    u = UD.get(m["declared_unit"])
    if not u or not u["is_calculable"]:
        err("INV-07", m["type_id"])
# INV-09 primary placement
for tid in MT:
    ps = [p for p in E["placement"] if p["type_id"] == tid and p["status"] == "ACTIVE"]
    if ps and sum(1 for p in ps if p["is_primary"]) != 1:
        err("INV-09 is_primary count", tid)
c = collections.Counter((p["function_node_id"], p["type_id"]) for p in E["placement"] if p["status"] == "ACTIVE")
if [k for k, v in c.items() if v > 1]:
    err("placement (node, type) not unique")
# INV-10
for m in E["material_type"]:
    rid = m["representative_material_id"]
    if rid and (CM[rid]["type_id"] != m["type_id"] or CM[rid]["status"] != "ACTIVE"):
        err("INV-10", m["type_id"])
# INV-17
for m in E["merge_event"]:
    if m["event_kind"] == "MERGE" and m["target_kind"] == "MATERIAL_TYPE":
        def sig(t):
            return (t["declared_unit"], t["item_kind"], sorted((a["attribute_code"], a["unit_code"]) for a in t["spec_attributes"] if a["role"] == "IDENTITY"))
        for x in m["merged_ids"]:
            if sig(MT[x]) != sig(MT[m["survivor_id"]]):
                err("INV-17 type merge preconditions", m["merge_event_id"])
        desc = [cm_["canonical_id"] for cm_ in E["canonical_material"]
                if any(rp["ref_id"] == cm_["canonical_id"] and rp["field"] == "type_id" for rp in m["repointed_refs"])]
        if sorted(desc) != sorted(m["affected_descendant_ids"]):
            err("affected_descendant_ids vs repointed type_id refs", m["merge_event_id"])
    if m["caused_by_event_id"]:
        cause = ME[m["caused_by_event_id"]]
        if cause["target_kind"] != "MATERIAL_TYPE" or not set(m["merged_ids"]) <= set(cause["affected_descendant_ids"]):
            err("caused_by_event_id consistency", m["merge_event_id"])
# INV-18
for m in E["material_type"]:
    if m["substance_class_id"] and m["item_kind"] not in nodes[m["substance_class_id"]]["allowed_item_kinds"]:
        err("INV-18", m["type_id"])
# INV-21
for m in E["merge_event"]:
    if m["event_kind"] == "SPLIT":
        orig = ME[m["reverts_event_id"]]
        rev = [{"ref_kind": r["ref_kind"], "ref_id": r["ref_id"], "field": r["field"], "from_id": r["to_id"], "to_id": r["from_id"]} for r in orig["repointed_refs"]]
        if orig["event_kind"] != "MERGE" or m["repointed_refs"] != rev or m["survivor_id"] != orig["survivor_id"] or m["merged_ids"] != orig["merged_ids"]:
            err("INV-21 split does not mirror the merge", m["merge_event_id"])
        for rp in m["repointed_refs"]:                         # state really returned
            if idx[rp["ref_id"]][1][rp["field"]] != rp["to_id"]:
                err("INV-21 repointed ref not restored", rp)
        for x in m["merged_ids"]:
            if idx[x][1]["status"] != "ACTIVE" or idx[x][1]["merged_into"] is not None:
                err("INV-21 split record not restored", x)
        for x in orig["aliases_created"]:
            if idx[x][1]["status"] != "DEPRECATED":
                err("INV-21 alias created by reverted merge not deprecated", x)
    elif m["merge_event_id"] not in REVERTED:
        for rp in m["repointed_refs"]:
            if idx[rp["ref_id"]][1][rp["field"]] != rp["to_id"]:
                err("repointed ref not applied", rp)
        for x in m["merged_ids"]:
            if idx[x][1]["status"] != "MERGED" or idx[x][1]["merged_into"] != m["survivor_id"]:
                err("merged record state", x)
        for x in m["aliases_created"]:
            if idx[x][1]["status"] != "ACTIVE" or m["survivor_id"] not in idx[x][1]["target_ids"]:
                err("alias created by merge", x)
ok("G: 例に対して検査できる不変条件（INV-01〜12、14、17〜22。INV-11 は assumed_active_nodes の仮定の下）")

# ------------------------------------------------------------------ H. calc rows and selections
SEL = {s_["selection_id"]: s_ for s_ in E["selection"]}
rows_by_sel = collections.defaultdict(list)
REQ_STAGES = set(S["factor_stage_requirements"]["by_param_kind"]["FACTOR"]["required_stages"])
for r in E["calc_row"]:
    o = r["row_id"]
    rows_by_sel[r["selection_id"]].append(r)
    s_ = ref(r["selection_id"], {"selection"}, "row.sel")
    if s_ and s_["project_id"] != r["project_id"]:
        err("row/selection project mismatch", o)
    ref(r["release_id"], {"release"}, "row.rel")
    cm_ = ref(r["canonical_id"], {"canonical_material"}, "row.cm")
    pl_ = ref(r["placement_id"], {"placement"}, "row.pl")
    for fn in ("entry_unit", "driver_unit", "activity_unit", "factor_unit"):
        ref(r[fn], {"unit_def"}, "row." + fn)
    for x in r["conversion_ids"] + r["mass_conversion_ids"]:
        ref(x, {"unit_conversion"}, "row.conv")
    a = ref(r["assembly_id"], {"assembly"}, "row.as")
    ref(r["import_source_id"], {"source"}, "row.import")
    if (r["placement_state"] == "PLACED") != (r["placement_id"] is not None):
        err("placement_state vs placement_id", o)
    if r["zone_id"] and not r["zone_id"].startswith("ZN-"):
        err("zone id prefix", o)
    if not r["project_id"].startswith("PRJ-") or not r["selection_id"].startswith("SEL-"):
        err("project/selection id prefix", o)
    typ = MT[cm_["type_id"]] if cm_ else None
    if cm_ and (cm_["status"] != "ACTIVE") != ("RECORD_NOT_ACTIVE" in r["blocking_reasons"]):
        err("RECORD_NOT_ACTIVE consistency", o)
    if typ and r["activity_unit"] != typ["declared_unit"]:
        err("activity_unit != declared unit", o)
    if pl_ and typ and pl_["type_id"] != typ["type_id"]:
        err("row placement type mismatch", o)
    if (r["entry_quantity"] is None) != (r["entry_unit"] is None) or (r["driver_quantity"] is None) != (r["driver_unit"] is None):
        err("quantity/unit null consistency", o)
    if r["entry_unit"] and pl_ and typ and r["entry_unit"] not in (pl_["entry_unit"], typ["declared_unit"]):
        if not [u for u in E["unit_conversion"] if u["scope_id"] in (typ["type_id"], cm_["canonical_id"]) and u["from_unit"] == r["entry_unit"]]:
            err("entry_unit not allowed for this placement/type", o)
    if (a is not None) != (r["driver_quantity"] is not None) or (a is not None) != (r["assembly_line_no"] is not None):
        err("driver/assembly consistency", o)
    comp = None
    if a:
        if r["driver_unit"] != a["driver_unit"]:
            err("driver_unit != assembly.driver_unit", o)
        comp = [c for c in E["assembly_component"] if c["assembly_id"] == r["assembly_id"] and c["line_no"] == r["assembly_line_no"]]
        comp = comp[0] if comp else err("assembly line not found", o)
        if comp and (comp["target_id"] != r["canonical_id"] or comp["placement_id"] != r["placement_id"]):
            err("row does not match assembly component", o)
    # activity derivation
    exp, state = None, None
    if comp and r["entry_quantity"] is None:
        if comp["ratio_basis"] == "DRIVER_IDENTITY":
            exp, state = r["driver_quantity"], "DERIVED"
        elif comp["ratio_basis"] == "GEOMETRIC_DEFINITION":
            p_ = r["conversion_params"].get(comp["ratio_param_name"])
            if not p_ or p_["unit_code"] != comp["ratio_param_unit_code"]:
                err("geometric parameter missing or wrong unit", o)
            else:
                f_ = float(UD[p_["unit_code"]]["to_base_factor"])
                exp, state = r["driver_quantity"] * p_["value"] * f_, "DERIVED"
        else:
            exp, state = None, "MISSING"
            if "ASSEMBLY_RATIO_MISSING" not in r["blocking_reasons"]:
                err("ratio missing but no ASSEMBLY_RATIO_MISSING", o)
    elif r["entry_quantity"] is not None:
        if r["entry_unit"] == r["activity_unit"]:
            exp, state = r["entry_quantity"], r["activity_state"]
            if r["conversion_ids"]:
                err("conversion listed though units equal", o)
        else:
            us = [idx[x][1] for x in r["conversion_ids"]]
            if len(us) != 1 or us[0]["from_unit"] != r["entry_unit"] or us[0]["to_unit"] != r["activity_unit"] or us[0]["conversion_status"] != "USABLE":
                err("conversion path for entry->declared", o)
            else:
                u = us[0]
                p_ = r["conversion_params"].get(u["basis_parameter"])
                if u["basis_origin"] == "ROW_PARAMETER":
                    if not p_ or p_["unit_code"] != u["basis_unit_code"] or p_["source"] not in u["param_source_order"]:
                        err("row parameter missing/unit/source", o)
                    else:
                        exp, state = r["entry_quantity"] * p_["value"] * float(UD[p_["unit_code"]]["to_base_factor"]), "DERIVED"
                if "CONVERSION_APPLIED" not in r["warnings"]:
                    err("CONVERSION_APPLIED warning missing", o)
    else:
        if "QUANTITY_MISSING" not in r["blocking_reasons"]:
            err("no quantity but no QUANTITY_MISSING", o)
    if exp is None:
        if r["activity"] is not None or r["activity_state"] != "MISSING":
            err("activity should be missing", o)
    elif r["activity"] is None or abs(r["activity"] - exp) > 1e-9 or r["activity_state"] != state:
        err("activity value/state", o, r["activity"], exp, state)
    for k, p_ in r["conversion_params"].items():
        if list(p_) != ["value", "unit_code", "unit_assumed", "source"] or p_["source"] not in EN["param_source"]:
            err("conversion_params shape", o)
        ref(p_["unit_code"], {"unit_def"}, "row.param.unit")
        if p_["unit_assumed"] and ("param_unit:" + k) not in r["defaulted_fields"]:
            err("assumed param unit not in defaulted_fields", o)
    # params
    if set(r["param_states"]) != set(EN["param_kind"]):
        err("param_states keys", o)
    for k, st in r["param_states"].items():
        if list(st) != ["value_state", "param_license_status", "bound_from", "via_default_placement"]:
            err("param_states shape", o, k)
            continue
        if st["value_state"] not in EN["value_state"] or st["param_license_status"] not in EN["license_status"] or st["bound_from"] not in EN["bound_from"]:
            err("param_states enum", o, k)
        refname = {"FACTOR": "factor_ref", "SERVICE_LIFE": "service_life_ref", "REPAIR_RATE": "repair_rate_ref", "EOL_ROUTE": "eol_route_ref", "WASTE_RATE": "waste_rate_ref"}[k]
        if (r[refname] is None) != (st["bound_from"] == "NONE") or (r[refname] is None) != (st["value_state"] == "MISSING"):
            err("param_states vs ref", o, k)
        if st["via_default_placement"] and "placement_id" not in r["defaulted_fields"]:
            err("via_default_placement without default placement", o)
    # INV-14
    reasons = set(r["blocking_reasons"])
    if (r["factor_ref"] is None) != ("FACTOR_MISSING" in reasons):
        err("INV-14 FACTOR_MISSING", o)
    if r["factor_ref"] is None and (r["factor_unit"] or r["factor_stages"] or r["factor_boundary_ref"]):
        err("factor copies set without factor_ref", o)
    if r["factor_ref"] is not None:
        if set(r["factor_stages"]) != REQ_STAGES and "FACTOR_STAGE_MISMATCH" not in reasons:
            err("INV-14 stage mismatch not stopped", o)
        if r["param_states"]["FACTOR"]["param_license_status"] != "PERMITTED_PUBLIC" and "LICENSE_NOT_PERMITTED" not in reasons:
            err("INV-14 license not stopped", o)
    if r["computable"] != (not reasons):
        err("computable vs blocking_reasons", o)
    # warnings
    if cm_ and (cm_["mass_path_status"] in ("NOT_REGISTERED", "BLOCKED_BASIS_MISSING")) != ("MASS_PATH_UNAVAILABLE" in r["warnings"]):
        err("MASS_PATH_UNAVAILABLE consistency", o)
    if (r["quantity_basis"] == "UNKNOWN") != ("QUANTITY_BASIS_UNKNOWN" in r["warnings"]):
        err("QUANTITY_BASIS_UNKNOWN consistency", o)
    assumed = [d for d in r["defaulted_fields"] if d.startswith(("spec_unit:", "param_unit:"))]
    if bool(assumed) != ("SPEC_UNIT_ASSUMED" in r["warnings"]):
        err("SPEC_UNIT_ASSUMED warning vs defaulted_fields", o)
    for d in r["defaulted_fields"]:
        if ":" in d:
            kind, name = d.split(":")
            if kind == "spec_unit" and name not in cm_["attribute_values"]:
                err("defaulted spec unit names unknown attribute", o, d)
        elif d not in r:
            err("defaulted field is not a row field", o, d)
    if pl_ and ("placement_id" in r["defaulted_fields"]) and not pl_["is_primary"]:
        err("defaulted placement is not the primary placement", o)
    deps = {d["kind"] for d in r["dependent_requirements"]}
    if typ and deps != set(typ["dependent_requirements"]):
        err("dependent_requirements vs type", o)
    if "SPEC_UNIT_UNCONFIRMED" in reasons and assumed:
        err("unit both unconfirmed and accepted", o)
# double counting: same project, placement, type; zones overlap if equal or either is null; assembly row vs individually specified row
for r in E["calc_row"]:
    hit = False
    for q in E["calc_row"]:
        if q is r or q["project_id"] != r["project_id"] or q["placement_id"] != r["placement_id"]:
            continue
        if CM[q["canonical_id"]]["type_id"] != CM[r["canonical_id"]]["type_id"]:
            continue
        if not (q["zone_id"] is None or r["zone_id"] is None or q["zone_id"] == r["zone_id"]):
            continue
        if (q["assembly_id"] is None) != (r["assembly_id"] is None):
            hit = True
    if hit != ("DOUBLE_COUNT_UNRESOLVED" in r["blocking_reasons"]):
        err("DOUBLE_COUNT_UNRESOLVED consistency", r["row_id"], hit)
# selections (INV-20) and candidate counts against the tree
groups = [n for n in T["nodes"] if n["level_kind"] == "GROUP" and n["status"] != "RESERVED"]
for s_ in E["selection"]:
    o = s_["selection_id"]
    rws = rows_by_sel.get(o, [])
    if not rws:
        err("selection without rows", o)
    oc = s_["operation_count"]
    if list(oc) != ["pick", "enter", "search", "accept", "override"]:
        err("operation_count keys", o)
    if oc["accept"] != sum(len(r["defaulted_fields"]) for r in rws):
        err("INV-20 accept != defaulted_fields", o)
    if len(s_["candidate_counts"]) != oc["pick"]:
        err("candidate_counts length != pick", o)
    if s_["selection_path"] in ("TREE", "ASSEMBLY") and s_["candidate_counts"][0] != len(groups):
        err("first candidate count != number of usable groups", o)
    if s_["selection_path"] == "TREE":
        el = nodes[idx[rws[0]["placement_id"]][1]["function_node_id"]]
        sib = [n for n in T["nodes"] if n["parent"] == el["parent"]]
        if s_["candidate_counts"][1] != len(sib):
            err("second candidate count != elements in group", o, len(sib))
        if s_["candidate_counts"][2] != len([p for p in E["placement"] if p["function_node_id"] == el["node_id"]]):
            err("third candidate count != placements on element", o)
    if s_["selection_path"] == "ASSEMBLY":
        a = AS[rws[0]["assembly_id"]]
        if len(rws) != len([c for c in E["assembly_component"] if c["assembly_id"] == a["assembly_id"]]):
            err("assembly expanded rows != components", o)
        if (s_["selection_path"] == "ASSEMBLY") and any(r["assembly_id"] != a["assembly_id"] for r in rws):
            err("mixed assemblies in a selection", o)
    if (s_["selection_path"] != "ASSEMBLY") and any(r["assembly_id"] for r in rws):
        err("assembly rows in non-assembly selection", o)
    if (s_["selection_path"] == "IMPORT_MAPPING") != any(r["import_source_id"] for r in rws):
        err("import fields vs path", o)
ok("H: 計算行 %d 件と指定 %d 件（単位、活動量の換算の再計算、二重計上の規則、停止理由と警告、承認の回数、候補数）" % (len(E["calc_row"]), len(E["selection"])))

# ------------------------------------------------------------------ I. illustration-only sections
for sec in ("duplicate_handling", "what_this_shows"):
    for x in E[sec]:
        for rid in x["records"]:
            if rid not in idx and rid not in nodes:
                err("illustration refers to unknown record", sec, rid)
        if "duplicate_level" in x and x["duplicate_level"] not in EN["duplicate_level"]:
            err("illustration enum", sec)
explained = set()
for sec in ("what_this_shows", "duplicate_handling"):
    for x in E[sec]:
        explained |= set(x["records"])
# every ID mentioned in any explanation text exists
alltxt = json.dumps(E, ensure_ascii=False)
for m in set(re.findall(r"\b(?:[A-Z]{2,3})-FICT-\d{4}\b", alltxt)):
    if m not in idx and not m.startswith(("PRJ-", "ZN-")):
        err("text mentions unknown example id", m)
for m in set(re.findall(r"\b(?:FN|IN)-\d{6}\b", alltxt)):
    if m not in nodes:
        err("examples mention unknown node", m)
ok("I: 説明用の節と説明文に現れる ID がすべて実在する")

# ------------------------------------------------------------------ J. README consistency
def need(pattern, expected, label):
    ms = re.findall(pattern, README)
    if not ms:
        err("README: pattern not found:", label, pattern)
    for m in ms:
        if str(m) != str(expected):
            err("README count mismatch:", label, "README=%s JSON=%s" % (m, expected))


n_core = sum(1 for r in RS.values() if r["core"])
need(r"レコード定義（(\d+)種", len(RS), "record kinds")
need(r"列挙値、不変条件(\d+)件", len(inv_ids), "invariants")
need(r"分類階層の草案（(\d+)ノード", N_NODES, "nodes")
need(r"部位軸(\d+)、品目軸", N_FUNC, "function nodes")
need(r"品目軸(\d+)）", N_ITEM, "item nodes")
need(r"部位要素(\d+)件", N_ELEM, "elements")
need(r"予約ノード(\d+)件", N_RESERVED, "reserved")
need(r"INV-01〜(\d+)）を全件検査", len(inv_ids), "INV range")
need(r"（(\d+)種のレコード", len(RS), "U-16 record kinds")
need(r"`core = true`[^|]*?（(\d+)種）", n_core, "core kinds")
need(r"(\d+)系統", N_ITEM, "substance classes")
for m in set(re.findall(r"INV-(\d\d)", README)):
    if "INV-" + m not in inv_ids:
        err("README mentions undefined INV-" + m)
u_ids = re.findall(r"^\| (U-\d\d) \|", README, re.M)
if u_ids != ["U-%02d" % (i + 1) for i in range(len(u_ids))]:
    err("README U ids not sequential", u_ids)
for m in set(re.findall(r"U-(\d\d)", README + json.dumps(S, ensure_ascii=False) + json.dumps(T, ensure_ascii=False) + alltxt)):
    if "U-" + m not in u_ids:
        err("reference to undefined U-" + m)
d_ids = re.findall(r"^\| (D-\d) \|", README, re.M)
for m in set(re.findall(r"D-(\d)", README)):
    if "D-" + m not in d_ids:
        err("README mentions undefined D-" + m)
# every backticked identifier in README exists somewhere in the JSON files (field, record, enum value, code)
vocab = set(RS) | allfields | {v for vs in EN.values() for v in vs} | set(EN) | {n["code"] for n in T["nodes"]} | set(E) | set(S)
vocab |= {f["name"] for f in RS["spec_attribute"]["fields"]}
for sec in S["resolution_orders"].values():
    vocab |= set(sec["order"])
known_other = {"README.md", "DESIGN_DRAFT", "NOT_VERIFIED", "FICTIONAL_PLACEHOLDER", "code", "t", "core = true", "PICK", "ENTER", "SEARCH", "ACCEPT", "OVERRIDE",
               "ENVELOPE", "LOOKUP_JOIN", "MATRIX_EXPANSION", "REVIEW_LOG.md"}
inputs = json.load(open("/home/user/-/whole-life-carbon-jcat-study/03_INPUTS/inputs.json", encoding="utf-8"))
input_ids = {f["id"] for f in inputs["fields"]}
formulas = json.load(open("/home/user/-/whole-life-carbon-jcat-study/04_FORMULAS/formulas.json", encoding="utf-8"))
formula_ids = {f["id"] for f in formulas["formulae"]}
for tok in sorted(set(re.findall(r"`([^`\n]+)`", README))):
    t0 = tok.strip()
    if t0 in vocab or t0 in known_other or t0 in input_ids:
        continue
    if re.match(r"^[A-Z]+\.\*$", t0):
        continue
    m = re.match(r"^([a-z_]+) = ([A-Za-z_]+)$", t0)
    if m and m.group(1) in allfields and (m.group(2) in vocab or m.group(2) in ("null", "true")):
        continue
    err("README backticked token not found in JSON/inputs:", t0)
# formula ids mentioned in section 5 exist
sec5 = README[README.index("## 5. "):README.index("## 6. ")]
for m in set(re.findall(r"\b(?:A13|A4|A5|B\d|C\d?|SYS|QA|SUM|STO)-\d\d\b", sec5)):
    if m not in formula_ids:
        err("README section 5 mentions unknown formula", m)
for m in set(re.findall(r"\b[A-Z_]+\.[a-z_]+\b", sec5)):
    if m not in input_ids and m != "README.md":
        err("README section 5 mentions unknown input", m)
for f_ in S["factor_stage_requirements"]["by_param_kind"]["FACTOR"]["used_by_formulas"]:
    if f_ not in formula_ids:
        err("unknown formula in stage requirements", f_)
for w in ["OTHER_SERVICES", "その他搬送", "その他設備", "並び順", "17種", "70ノード", "38件", "occurrence", "TYPE_REPRESENTATIVE", "STARTER", "出発点の一式",
          "mass_per_unit_ref", "MASS_PER_UNIT", "normalization_trace", "→ 製品 →", "言えること"]:
    if w in README:
        err("README still contains", w)
# relative links resolve
import os
for m in re.findall(r"\]\(([^)#]+)\)", README):
    if not m.startswith("http") and not os.path.exists(os.path.normpath(os.path.join("/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/07_MATERIAL_TAXONOMY/", m))):
        err("README broken link", m)
ok("J: README の件数（レコード%d種・うち最小の組%d種、不変条件%d件、%dノード＝%d＋%d、部位要素%d、予約%d）と、README に現れる項目名・列挙値・式ID・入力ID・U/D 番号・リンクが JSON と一致"
   % (len(RS), n_core, len(inv_ids), N_NODES, N_FUNC, N_ITEM, N_ELEM, N_RESERVED))

# ------------------------------------------------------------------ K. licensed-data guard
def numbers(o, path, out):
    if isinstance(o, bool):
        return
    if isinstance(o, (int, float)):
        out.append((path, o))
    elif isinstance(o, dict):
        for k, v in o.items():
            numbers(v, path + "." + k, out)
    elif isinstance(o, list):
        for v in o:
            numbers(v, path, out)


nums = []
numbers(E, "E", nums)
allowed_num_fields = ("line_no", "record_version", "entry_quantity", "driver_quantity", "activity", "candidate_counts", "operation_count",
                      "input_for_illustration", "conversion_params", "assembly_line_no")
for p_, v in nums:
    if not any(a in p_ for a in allowed_num_fields):
        err("unexpected number in examples", p_, v)
nums = []
numbers(T, "T", nums)
for p_, v in nums:
    if not (p_.endswith(".level") or p_.endswith(".record_version")):
        err("unexpected number in tree", p_, v)
nums = []
numbers(S, "S", nums)
if nums:
    err("unexpected number in schema", nums)
for r in E["calc_row"]:
    for fn in ("factor_ref", "service_life_ref", "repair_rate_ref", "eol_route_ref", "waste_rate_ref", "factor_boundary_ref"):
        if r[fn] is not None:
            err("example row carries a parameter reference", r["row_id"], fn)
for b in E["param_binding"]:
    if b["param_ref"] is not None:
        err("example binding carries a reference", b["binding_id"])
for u in E["unit_conversion"]:
    if u["basis_ref"] is not None:
        err("example conversion carries a ledger reference", u["conversion_id"])
for c in E["assembly_component"]:
    if c["ratio_ref"] is not None:
        err("example component carries a ledger reference")
if E["all_records_flag"] != "FICTIONAL_PLACEHOLDER":
    err("all_records_flag")
ok("K: 例・階層・定義に、係数・耐用年数・修繕率・密度・構成比の値が無い（数値は階層番号・版番号・行番号・説明用の数量と厚さ・操作回数だけ。参照はすべて null）")

print("\n".join(OKS))
print("\nERRORS: %d" % len(ERR))
for e in ERR:
    print("  -", e)
sys.exit(1 if ERR else 0)
