# -*- coding: utf-8 -*-
"""example_records.json を、修正後の taxonomy_schema.json に合わせて作り直す（すべて架空のプレースホルダ）。"""
import json, hashlib

OUT = "/home/user/-/whole-life-carbon-jcat-study/09_APPROX_STUDY/07_MATERIAL_TAXONOMY/"
S = json.load(open(OUT + "taxonomy_schema.json", encoding="utf-8"))
RS = S["records"]
COMMON = [f["name"] for f in S["common_fields"]["fields"]]
APPLIES = set(S["common_fields"]["applies_to"])
ILLUS = ["identity_array_for_illustration", "gate_result", "input_for_illustration"]

REL, NV, PRJ = "REL-FICT-0001", "norm-fict-0.1", "PRJ-FICT-0001"
DAY = "2026-11-11"
ORDER = ["PERMITTED_PUBLIC", "PERMISSION_REQUIRED", "UNKNOWN", "RESTRICTED"]


def h(arr):
    return hashlib.sha256(json.dumps(arr, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def empty(typ):
    if typ.startswith("array"):
        return []
    return None


def mk(rn, vals, common=None, explanation=None):
    """スキーマの項目順に並べ、必須項目の欠落と未定義の項目を検出する。"""
    vals = dict(vals)
    out = {"record_flag": "FICTIONAL_PLACEHOLDER"}
    for f in RS[rn]["fields"]:
        n = f["name"]
        if n in vals:
            out[n] = vals.pop(n)
        elif f["required"] is True:
            raise KeyError((rn, n, "required"))
        else:
            assert f["type"].endswith("|null") or f["type"].startswith("array"), (rn, n)
            out[n] = empty(f["type"])
        if n == "identity_key" and "identity_array_for_illustration" in vals:
            out["identity_array_for_illustration"] = vals.pop("identity_array_for_illustration")
        if n == "resolution_mode" and "input_for_illustration" in vals:
            out["input_for_illustration"] = vals.pop("input_for_illustration")
    for k in ILLUS:
        if k in vals:
            out[k] = vals.pop(k)
    assert not vals, (rn, vals)
    if rn in APPLIES:
        assert common is not None, rn
        for n in COMMON:
            out[n] = common[n]
    else:
        assert common is None, rn
    if explanation:
        out["explanation"] = explanation
    return out


# ------------------------------------------------------------------ sources
SRC_LIC = {"SRC-FICT-0000": "PERMITTED_PUBLIC", "SRC-FICT-0001": "PERMITTED_PUBLIC", "SRC-FICT-0002": "PERMITTED_PUBLIC",
           "SRC-FICT-0003": "UNKNOWN"}


def src(sid, title, origin, kinds, gate=None):
    ok = SRC_LIC[sid] == "PERMITTED_PUBLIC"
    v = dict(source_id=sid, title=title, origin_kind=origin, source_version="fict-0.1", retrieved_at=DAY, content_kinds=kinds,
             license_status=SRC_LIC[sid],
             license_evidence_ref=("本例のために自分で書いた文字列" if origin == "SELF_AUTHORED" else "本例のために作成した架空の文字列") if ok else None,
             permitted_uses=["INTERNAL_RESEARCH", "PUBLIC_REDISTRIBUTION"] if ok else [],
             storage_policy="MAY_STORE_IN_PUBLIC_REPO" if ok else "DO_NOT_INGEST",
             license_reviewed_by="reviewer_a", license_reviewed_at=DAY, license_valid_until=None)
    if gate:
        v["gate_result"] = gate
    return mk("source", v)


source = [
    src("SRC-FICT-0000", "本例の命名・整理判断（表示名、別名、等価関係）", "SELF_AUTHORED", ["NAMES", "SPEC_ATTRIBUTES"]),
    src("SRC-FICT-0001", "架空の数量内訳書（本例のために作った文字列。名称・単位・見出しだけを受領し、数量は受領しない）", "SYNTHETIC_FICTIONAL",
        ["NAMES", "UNITS", "CLASSIFICATION_LABELS"]),
    src("SRC-FICT-0002", "架空の材料一覧（本例のために作った文字列）", "SYNTHETIC_FICTIONAL", ["NAMES", "UNITS"]),
    src("SRC-FICT-0003", "許諾が未確認だと仮定した架空の第三者データ", "THIRD_PARTY_DATASET", ["NAMES"],
        gate="取り込まない。中身は1行も保存せず、理由（許諾未確認）だけを記録する。この出典にしか無い名称は、どのレコードにも現れない。"),
]


def P(sid, raw=None, der="CURATED", role="RELIED_ON", via=None):
    return {"source_id": sid, "raw_id": raw, "derivation": der, "role": role, "via_merge_event_id": via}


SELF = [P("SRC-FICT-0000")]


def C(prov=None, status="ACTIVE", ver=1, by="reviewer_a", rev="reviewer_b", retired=None, replaced=None):
    prov = prov or SELF
    relied = [SRC_LIC[p["source_id"]] for p in prov if p["role"] == "RELIED_ON"]
    assert relied
    return dict(status=status, created_in_release=REL, retired_in_release=retired, replaced_by=replaced or [],
                license_status=max(relied, key=ORDER.index), compartment="PUBLIC_RELEASE", provenance=prov,
                record_version=ver, created_by=by, reviewed_by=rev)


# ------------------------------------------------------------------ raw records
def raw(n, sid, loc, name, unit, cls, status="ACCEPTED", dup=None, note=None):
    return mk("raw_record", dict(raw_id="RAW-FICT-%04d" % n, source_id=sid, source_locator=loc, name_text=name, spec_text=None,
                                 unit_text=unit, class_text=cls, content_hash=h([sid, name, None, unit, cls]),
                                 duplicate_of_raw=dup, intake_status=status, intake_note=note, ingested_in_release=REL))


raw_record = [
    raw(1, "SRC-FICT-0001", "架空の内訳書 行1", "架空ボードＡ　厚１２ｍｍ", "㎡", "外壁"),
    raw(2, "SRC-FICT-0001", "架空の内訳書 行2", "架空ﾎﾞｰﾄﾞA t=12", "m2", "外壁"),
    raw(3, "SRC-FICT-0002", "架空の一覧 行1", "かくうボードA 12ミリ", "平米", None),
    raw(4, "SRC-FICT-0002", "架空の一覧 行2", "架空ボードA 厚12mm", "枚", None),
    raw(5, "SRC-FICT-0001", "架空の内訳書 行7", "架空ボードＡ　厚１２ｍｍ", "㎡", "外壁", status="DUPLICATE_RAW", dup="RAW-FICT-0001"),
    raw(6, "SRC-FICT-0001", "架空の内訳書 行9", "架空ボード", "m2", "内装"),
    raw(7, "SRC-FICT-0002", "架空の一覧 行3", "架空充填材X", "kg", None),
    raw(8, "SRC-FICT-0001", "架空の内訳書 行12", "架空の共通経費", "式", None, status="OUT_OF_SCOPE",
        note="材料でない行（架空の判断。CD-FICT-0005）"),
    raw(9, "SRC-FICT-0002", "架空の一覧 行4", "架空板A 厚12mm", "m2", None),
]
assert raw_record[0]["content_hash"] == raw_record[4]["content_hash"]


# ------------------------------------------------------------------ normalized records
def tok(code, val, unit, assumed, text):
    return {"attribute_code": code, "value": val, "unit_code": unit, "unit_assumed": assumed, "matched_text": text}


def norm(n, key, tokens, unit, flags, resolved, expl):
    return mk("normalized_record", dict(raw_id="RAW-FICT-%04d" % n, normalizer_version=NV, name_key=key, variant_keys=[],
                                        spec_tokens=tokens, unit_code=unit, residual_text="", flags=flags, resolved_to=resolved,
                                        resolved_in_release=REL if resolved else None), explanation=expl)


normalized_record = [
    norm(1, "架空ボードa", [tok("thickness_mm", "12", "mm", False, "厚12mm")], "m2", [], "CM-FICT-0001",
         "全角英数字と全角空白は互換正規化で統一される。単位欄の「㎡」も互換正規化で m2 になる。別名の行は増えない。"),
    norm(2, "架空ボードa", [tok("thickness_mm", "12", "mm", True, "t=12")], "m2", ["SPEC_UNIT_ASSUMED"], "CM-FICT-0001",
         "半角カナは互換正規化で統一される。名称欄の t= は厚さの接頭語として読み、単位欄の t（質量）とは別の解析器で扱う。数値に単位が無いので、仮定した単位は確認されるまで止まる（SPEC_UNIT_UNCONFIRMED）。確認者が mm と確定した記録が CD-FICT-0001 である。"),
    norm(3, "カクウボードa", [tok("thickness_mm", "12", "mm", False, "12ミリ")], "m2", [], "CM-FICT-0001",
         "ひらがなはカタカナに畳むが、漢字とかなの読み替えは規則では行わない。別名が無い間は ALIAS_UNRESOLVED で止まり、下書きの品種は自動では作られない。人が別名 AL-FICT-0002 を登録した（CD-FICT-0002）後の再正規化で解決した。単位欄の「平米」は unit_def の表記として登録済み。"),
    norm(4, "架空ボードa", [tok("thickness_mm", "12", "mm", False, "厚12mm")], "ct_mai", [], "CM-FICT-0001",
         "同一性は同じで単位だけが違う（D2）。別の材料にせず、枚→m2 の換算 UC-FICT-0002 を登録する（CD-FICT-0003）。1枚の面積が出典に無いので換算は停止状態のまま残る。"),
    norm(6, "架空ボード", [], "m2", ["ALIAS_AMBIGUOUS"], None,
         "総称。別名 AL-FICT-0003 が2つの品種を候補に持つ。どちらかへ自動で寄せず、人が1回選ぶまで未解決のままにする。"),
    norm(7, "架空充填材x", [], "kg", [], "CM-FICT-0004",
         "同じ材料が、宣言単位（m3）とは次元の違う単位（kg）で現れた例。別の品種にせず、質量と体積の間の換算 UC-FICT-0004 で表す（CD-FICT-0004）。密度の参照が無いので換算は停止状態のままで、kg で入力された数量は計算せずに止まる。"),
    norm(9, "架空板a", [tok("thickness_mm", "12", "mm", False, "厚12mm")], "m2", [], "CM-FICT-0001",
         "別名が無かったので未解決で止まり、判断者が新しい品種の下書きを作った（CD-FICT-0006）。その後、同じ品種と確認されて統合され（ME-FICT-0001）、別名 AL-FICT-0005 を通じて解決するようになった。"),
]


# ------------------------------------------------------------------ curation decisions
def cd(n, kind, raws, subjects, outcome, by="reviewer_a", rev="reviewer_b"):
    return mk("curation_decision", dict(decision_id="CD-FICT-%04d" % n, decision_kind=kind, raw_ids=raws, subject_ids=subjects,
                                        outcome=outcome, restricted_source_not_consulted=True, decided_by=by, reviewed_by=rev,
                                        decided_at=DAY, normalizer_version=NV, release_id=REL))


curation_decision = [
    cd(1, "SPEC_UNIT_CONFIRMED", ["RAW-FICT-0002"], ["CM-FICT-0001"], "名称欄の t= に続く数値の単位を mm と確定した（架空の判断）。"),
    cd(2, "ALIAS_REGISTERED", ["RAW-FICT-0003"], ["AL-FICT-0002"], "かな書きの名称が架空ボードAを指すと判断し、別名を登録した。新しい品種は作っていない（架空の判断）。"),
    cd(3, "UNIT_VARIANT_CONFIRMED", ["RAW-FICT-0004"], ["UC-FICT-0002"], "同じ材料が枚で数えられていると確認し、換算を停止状態で登録した（架空の判断）。"),
    cd(4, "UNIT_VARIANT_CONFIRMED", ["RAW-FICT-0007"], ["UC-FICT-0004"], "同じ材料が質量で数えられていると確認した。品種は分けず、既存の換算に観測の来歴を足した（架空の判断）。"),
    cd(5, "MARKED_OUT_OF_SCOPE", ["RAW-FICT-0008"], [], "材料でない行（経費）として対象外にした（架空の判断）。"),
    cd(6, "NEW_TYPE_CREATED", ["RAW-FICT-0009"], ["MT-FICT-0005", "CM-FICT-0003"], "既存の品種に当たらないと考え、新しい品種の下書きを作った（架空の判断。後に統合された）。",
       by="reviewer_c", rev=None),
]

# ------------------------------------------------------------------ units
def ud(code, label, dim, base, factor, aliases):
    return mk("unit_def", dict(unit_code=code, label=label, dimension=dim, base_unit_code=base, to_base_factor=factor,
                               is_calculable=True, text_aliases=aliases))


unit_def = [
    ud("m2", "平方メートル", "AREA", "m2", "1", ["m2", "平米"]),
    ud("m3", "立方メートル", "VOLUME", "m3", "1", ["m3"]),
    ud("kg", "キログラム", "MASS", "kg", "1", ["kg"]),
    ud("m", "メートル", "LENGTH", "m", "1", ["m"]),
    ud("mm", "ミリメートル", "LENGTH", "m", "0.001", ["mm"]),
    ud("ct_mai", "枚", "COUNT", "ct_mai", None, ["枚"]),
    ud("ct_dai", "台", "COUNT", "ct_dai", None, ["台"]),
]


# ------------------------------------------------------------------ material types
def thickness(parse):
    return {"attribute_code": "thickness_mm", "label": "厚さ", "quantity_kind": "DIMENSION", "value_type": "DECIMAL", "unit_code": "mm",
            "canonical_format": "DECIMAL_PLAIN", "role": "IDENTITY", "affects": ["UNKNOWN"], "required": True,
            "axis_mode": "ENUMERATED", "allowed_values": None, "allowed_values_provenance": None, "parse_patterns": parse}


capacity = {"attribute_code": "capacity_class", "label": "容量区分", "quantity_kind": "CAPACITY_CLASS", "value_type": "ENUM",
            "unit_code": None, "canonical_format": "ENUM_CODE", "role": "IDENTITY", "affects": ["UNKNOWN"], "required": True,
            "axis_mode": "ENUMERATED", "allowed_values": ["FICT_CLASS_S", "FICT_CLASS_L"],
            "allowed_values_provenance": [P("SRC-FICT-0000")], "parse_patterns": []}
PARSE_A = [{"prefix_tokens": ["厚", "t=", "t"], "suffix_tokens": ["mm", "ミリ"], "assumed_unit_code": "mm"}]


def mt(n, cls, name, key, kind, unit, attrs, common, dep=None, merged=None, expl=None):
    return mk("material_type", dict(type_id="MT-FICT-%04d" % n, substance_class_id=cls, name=name, name_key=key, item_kind=kind,
                                    declared_unit=unit, declared_unit_basis="PROVISIONAL", spec_attributes=attrs,
                                    representative_material_id=None, representative_rule="NOT_DECIDED",
                                    representative_basis_note=None, spread_class="UNKNOWN", dependent_requirements=dep or [],
                                    biogenic_flag=None, calc_class=None, merged_into=merged), common, expl)


material_type = [
    mt(1, "IN-000008", "架空ボードA", "架空ボードa", "BULK_MATERIAL", "m2", [thickness(PARSE_A)],
       C([P("SRC-FICT-0001", "RAW-FICT-0001", "NORMALIZED"), P("SRC-FICT-0000"),
          P("SRC-FICT-0002", "RAW-FICT-0009", "MERGED", via="ME-FICT-0001")], ver=2)),
    mt(2, "IN-000009", "架空充填材X", "架空充填材x", "BULK_MATERIAL", "m3", [], C()),
    mt(3, "IN-000002", "架空下地材Y", "架空下地材y", "BULK_MATERIAL", "kg", [], C()),
    mt(4, "IN-000008", "架空ボードB", "架空ボードb", "BULK_MATERIAL", "m2", [thickness([])], C()),
    mt(5, "IN-000008", "架空板A", "架空板a", "BULK_MATERIAL", "m2", [thickness([])],
       C([P("SRC-FICT-0002", "RAW-FICT-0009", "NORMALIZED"), P("SRC-FICT-0000")], status="MERGED", ver=2, by="reviewer_c", rev=None,
         retired=REL, replaced=["MT-FICT-0001"]), merged="MT-FICT-0001",
       expl="RAW-FICT-0009 の名称が解決できなかったとき、判断者が下書きとして作った（CD-FICT-0006。自動では作られない）。宣言単位・種別・同一性属性が MT-FICT-0001 と同じなので統合でき（INV-17）、ME-FICT-0001 で統合された。行は消さずに残す。"),
    mt(6, "IN-000014", "架空機器Q", "架空機器q", "EQUIPMENT_UNIT", "ct_dai", [capacity], C(), dep=["REFRIGERANT_CHARGE"],
       expl="設備の最小の例（台で数える機器）。容量は区分の名前として持ち、容量の値や、容量を活動量にする計算は持たない（README U-13）。付随して要る入力（冷媒）は、値を補わずに未入力の要求として行に残る。"),
    mt(7, "IN-000017", "架空配管R", "架空配管r", "LINEAR_ITEM", "m", [], C(),
       expl="設備の最小の例（長さで数える線状品）。口径などの仕様属性は例では省略した。"),
]


# ------------------------------------------------------------------ canonical materials
def ident(type_id, kind, attrs, product_key):
    return ["v2", type_id, kind, [[k, attrs[k]] for k in sorted(attrs)], product_key]


def cm(n, type_id, kind, attrs, pkey, name, mass, common, merged=None, expl=None):
    arr = ident(type_id, kind, attrs, pkey)
    return mk("canonical_material", dict(canonical_id="CM-FICT-%04d" % n, type_id=type_id, material_kind=kind, attribute_values=attrs,
                                         product_key=pkey, identity_key=h(arr), identity_array_for_illustration=arr, name=name,
                                         mass_path_status=mass, merged_into=merged), common, expl)


KEY_AT_CREATION = h(ident("MT-FICT-0005", "SPECIFIC", {"thickness_mm": "12"}, None))
canonical_material = [
    cm(1, "MT-FICT-0001", "SPECIFIC", {"thickness_mm": "12"}, None, "架空ボードA 厚12mm", "NOT_REGISTERED",
       C([P("SRC-FICT-0001", "RAW-FICT-0001", "PARSED_FROM_TEXT"),
          P("SRC-FICT-0001", "RAW-FICT-0002", "PARSED_FROM_TEXT", role="OBSERVED_MATCH"),
          P("SRC-FICT-0002", "RAW-FICT-0004", "PARSED_FROM_TEXT", role="OBSERVED_MATCH"),
          P("SRC-FICT-0002", "RAW-FICT-0003", "PARSED_FROM_TEXT", role="OBSERVED_MATCH"),
          P("SRC-FICT-0002", "RAW-FICT-0009", "MERGED", via="ME-FICT-0002")], ver=3),
       expl="内容の根拠にした出典（RELIED_ON）は最初の1件で、同じ内容を観測しただけの受領レコードは OBSERVED_MATCH として足す。実効ライセンスは RELIED_ON の出典だけから計算する。"),
    cm(3, "MT-FICT-0001", "SPECIFIC", {"thickness_mm": "12"}, None, "架空板A 厚12mm", "NOT_REGISTERED",
       C([P("SRC-FICT-0002", "RAW-FICT-0009", "PARSED_FROM_TEXT")], status="MERGED", ver=2, by="reviewer_c", rev=None, retired=REL,
         replaced=["CM-FICT-0001"]), merged="CM-FICT-0001",
       expl="作成時は下書きの品種 MT-FICT-0005 に属していた（その時点の同一性キーは " + KEY_AT_CREATION + "）。品種の統合 ME-FICT-0001 で type_id が MT-FICT-0001 に付け替えられ、計算し直したキーが CM-FICT-0001 と一致したので、ME-FICT-0002 で統合された。一意であるべきなのは ACTIVE の中だけである。"),
    cm(4, "MT-FICT-0002", "SPECIFIC", {}, None, "架空充填材X", "BLOCKED_BASIS_MISSING", C()),
    cm(5, "MT-FICT-0003", "SPECIFIC", {}, None, "架空下地材Y", "DIRECT", C()),
    cm(6, "MT-FICT-0004", "PRODUCT_SPECIFIC", {"thickness_mm": "12"}, "FICT-B1", "架空ボードB 厚12mm 架空製品B1", "NOT_REGISTERED", C(ver=3),
       expl="特定製品の例。束縛するときは CANONICAL_MATERIAL の水準を使う（製品だけの水準は無い）。CM-FICT-0007 と一度統合され（ME-FICT-0003）、取り消された（ME-FICT-0004）。統合で引き継いだ来歴は、取り消しのときに外した。"),
    cm(7, "MT-FICT-0004", "PRODUCT_SPECIFIC", {"thickness_mm": "12"}, "FICT-B-1", "架空ボードB 厚12mm 架空製品B-1", "NOT_REGISTERED", C(ver=3),
       expl="ME-FICT-0003 で CM-FICT-0006 に統合されて MERGED になり、ME-FICT-0004 の分割で統合前の状態（ACTIVE、merged_into = null、換算 UC-FICT-0005 の適用範囲）に戻った。"),
    cm(8, "MT-FICT-0006", "SPECIFIC", {"capacity_class": "FICT_CLASS_S"}, None, "架空機器Q 区分S", "NOT_REGISTERED", C()),
    cm(9, "MT-FICT-0007", "SPECIFIC", {}, None, "架空配管R", "NOT_REGISTERED", C()),
]
assert canonical_material[0]["identity_key"] == canonical_material[1]["identity_key"] != KEY_AT_CREATION


# ------------------------------------------------------------------ aliases
def al(n, key, surface, typ, targets, common, tk="MATERIAL_TYPE", expl=None):
    return mk("alias", dict(alias_id="AL-FICT-%04d" % n, normalized_key=key, surface_form=surface, alias_type=typ, target_kind=tk,
                            resolution="UNIQUE" if len(targets) == 1 else "AMBIGUOUS", target_ids=targets, context_node_id=None,
                            evidence_kind="SYNTHETIC_FICTIONAL", rights_note=None, normalizer_version=NV), common, expl)


alias = [
    al(1, "架空ボードa", "架空ボードA", "CANONICAL_NAME", ["MT-FICT-0001"], C(),
       expl="「架空ボードＡ」「架空ﾎﾞｰﾄﾞA」「架空ﾎﾞｰﾄﾞＡ」は正規化で同じキーに落ちるので、この1行で足りる。"),
    al(2, "カクウボードa", "かくうボードA", "READING_KANA", ["MT-FICT-0001"], C([P("SRC-FICT-0002", "RAW-FICT-0003", "NORMALIZED")]),
       expl="漢字とかなの読み替えは規則では決められないので、人が登録する行になる（CD-FICT-0002）。"),
    al(3, "架空ボード", "架空ボード", "GENERIC_TERM", ["MT-FICT-0001", "MT-FICT-0004"], C([P("SRC-FICT-0001", "RAW-FICT-0006", "NORMALIZED")]),
       expl="総称。候補を2件返し、どちらかへ自動で寄せない。"),
    al(4, "架空ボードb", "架空ボードB", "CANONICAL_NAME", ["MT-FICT-0004"], C()),
    al(5, "架空板a", "架空板A", "SYNONYM", ["MT-FICT-0001"], C([P("SRC-FICT-0002", "RAW-FICT-0009", "MERGED", via="ME-FICT-0001")]),
       expl="統合 ME-FICT-0001 で、退く側の名称を別名に移して作られた。"),
    al(6, "架空充填材x", "架空充填材X", "CANONICAL_NAME", ["MT-FICT-0002"], C(),
       expl="架空下地材Y・架空機器Q・架空配管R と特定製品の正式名の別名は、例では省略した。"),
    al(7, "架空製品b-1", "架空製品B-1", "LEGACY_NAME", ["CM-FICT-0006"],
       C([P("SRC-FICT-0000", None, "MERGED", via="ME-FICT-0003")], status="DEPRECATED", ver=2, retired=REL), tk="CANONICAL_MATERIAL",
       expl="統合 ME-FICT-0003 が作った別名。分割 ME-FICT-0004 で廃止（DEPRECATED）にした。行は消さずに残す。"),
]


# ------------------------------------------------------------------ unit conversions
def uc(n, sk, sid, kind, fu, tu, param, punit, origin, attr, order, vstate, blic, inv, cstat, common, expl):
    return mk("unit_conversion", dict(conversion_id="UC-FICT-%04d" % n, scope_kind=sk, scope_id=sid, conversion_kind=kind, from_unit=fu,
                                      to_unit=tu, basis_parameter=param, basis_unit_code=punit, basis_origin=origin,
                                      basis_attribute_code=attr, param_source_order=order, basis_ref=None,
                                      equivalence_evidence_kind=None, basis_value_state=vstate, basis_license_status=blic,
                                      applicability=None, invertible=inv, conversion_status=cstat), common, expl)


unit_conversion = [
    uc(1, "MATERIAL_TYPE", "MT-FICT-0001", "THICKNESS", "m2", "m3", "thickness", "mm", "IDENTITY_ATTRIBUTE", "thickness_mm", [], "DERIVED",
       "PERMITTED_PUBLIC", True, "USABLE", C(),
       "m3 = m2 × 厚さ。厚さの単位は basis_unit_code（mm）で持ち、定数は単位辞書の倍率（mm は m の 0.001 倍）から導く。根拠は正規材料レコード自身の寸法なので、外部の値が要らない。"),
    uc(2, "CANONICAL_MATERIAL", "CM-FICT-0001", "AREA_PER_PIECE", "ct_mai", "m2", "area_per_piece", None, "EXTERNAL_LEDGER", None, [], "MISSING",
       "UNKNOWN", False, "BLOCKED_BASIS_MISSING", C([P("SRC-FICT-0002", "RAW-FICT-0004", "NORMALIZED")]),
       "「枚」で数える行が実際に現れたという事実を残すために登録する。1枚の面積が無いので、枚で入力された数量は計算せずに止まる（CONVERSION_BASIS_MISSING）。"),
    uc(3, "MATERIAL_TYPE", "MT-FICT-0002", "THICKNESS", "m2", "m3", "thickness", "mm", "ROW_PARAMETER", None, ["USER_INPUT", "SPEC_TOKEN"], "DERIVED",
       "PERMITTED_PUBLIC", True, "USABLE", C(),
       "充填する厚さは材料の属性ではなく使い方で決まるので、行ごとに与える。名称にも入力にも無ければ止まり、既定の厚さは補わない。両方にあって食い違えば止まる。"),
    uc(4, "MATERIAL_TYPE", "MT-FICT-0002", "DENSITY", "m3", "kg", "density", None, "EXTERNAL_LEDGER", None, [], "MISSING", "UNKNOWN", True,
       "BLOCKED_BASIS_MISSING", C([P("SRC-FICT-0000"), P("SRC-FICT-0002", "RAW-FICT-0007", "NORMALIZED", role="OBSERVED_MATCH")], ver=2),
       "密度の参照が無いので質量への経路が無い。この材料の輸送・廃棄段階は「0」ではなく「計算できない」になる。同じ材料が kg で現れた事実（RAW-FICT-0007）も、別の品種ではなくこの換算に残す。"),
    uc(5, "CANONICAL_MATERIAL", "CM-FICT-0007", "AREA_PER_PIECE", "ct_mai", "m2", "area_per_piece", None, "EXTERNAL_LEDGER", None, [], "MISSING",
       "UNKNOWN", False, "BLOCKED_BASIS_MISSING", C(ver=3),
       "統合 ME-FICT-0003 で適用範囲が CM-FICT-0006 に付け替えられ、分割 ME-FICT-0004 で CM-FICT-0007 に戻った（付け替えは merge_event.repointed_refs に残る）。"),
]


# ------------------------------------------------------------------ placements
def pl(n, node, type_id, primary, unit, expl):
    return mk("placement", dict(placement_id="PL-FICT-%04d" % n, function_node_id=node, type_id=type_id, material_ids_limit=[],
                                is_primary=primary, entry_unit=unit, representative_override_id=None, context_condition=None), C(), expl)


placement = [
    pl(1, "FN-000026", "MT-FICT-0001", True, "m2", "屋根・外壁の「外壁下地」での使用。"),
    pl(2, "FN-000034", "MT-FICT-0001", False, "m2", "内装の「間仕切」での使用。同じ品種が2つの部位グループで使われるが、品種と正規材料レコードは複製せず、配置を増やすだけである。"),
    pl(3, "FN-000027", "MT-FICT-0002", True, "m2", "屋根・外壁の「外壁断熱」での使用。数量は面積で入れ、宣言単位 m3 へは UC-FICT-0003 で換算する。"),
    pl(4, "FN-000026", "MT-FICT-0003", True, "kg", "屋根・外壁の「外壁下地」での使用。"),
    pl(5, "FN-000040", "MT-FICT-0006", True, "ct_dai", "空調設備の「熱源」での使用。"),
    pl(6, "FN-000043", "MT-FICT-0007", True, "m", "空調設備の「空調配管」での使用。"),
]

# ------------------------------------------------------------------ assemblies
M_WALL, M_UNITS = "FICT_MEASURE_WALL_AREA", "FICT_MEASURE_UNIT_COUNT"
assembly = [
    mk("assembly", dict(assembly_id="AS-FICT-0001", name="架空外壁構成Z", assembly_kind="LAYERED_ASSEMBLY", function_node_id="FN-000005",
                        composite_material_id=None, driver_dimension="AREA", driver_unit="m2", driver_measure=M_WALL,
                        expansion_mode="EXPAND_TO_ROWS", context_condition=None,
                        stage_note="構成要素の係数は未束縛。束縛するときは、含む段階が構成要素の間でそろっていることを確認する。"), C(),
       "基準数量が何を測った面積か（driver_measure）は架空の符号で、語彙は未定義である。"),
    mk("assembly", dict(assembly_id="AS-FICT-0002", name="架空機器一式S", assembly_kind="SYSTEM_KIT", function_node_id="FN-000009",
                        composite_material_id=None, driver_dimension="COUNT", driver_unit="ct_dai", driver_measure=M_UNITS,
                        expansion_mode="EXPAND_TO_ROWS", context_condition=None, stage_note=None), C(),
       "設備の最小の例（機器と付属の配管の一式）。基準数量は機器の台数。"),
]


def ac(aid, line, target, unit, basis, pname, punit, measure, vstate, plc, optional, expl):
    return mk("assembly_component", dict(assembly_id=aid, line_no=line, target_kind="CANONICAL_MATERIAL", target_id=target,
                                         component_unit=unit, ratio_basis=basis, ratio_ref=None, ratio_param_name=pname,
                                         ratio_param_unit_code=punit, component_measure=measure, ratio_value_state=vstate,
                                         placement_id=plc, optional=optional, substitutable=True), None, expl)


assembly_component = [
    ac("AS-FICT-0001", 1, "CM-FICT-0001", "m2", "DRIVER_IDENTITY", None, None, M_WALL, "DERIVED", "PL-FICT-0001", False,
       "基準数量そのものが構成要素の数量になる。単位と測り方が基準数量と同じなので許される。"),
    ac("AS-FICT-0001", 2, "CM-FICT-0004", "m3", "GEOMETRIC_DEFINITION", "thickness", "mm", None, "DERIVED", "PL-FICT-0003", False,
       "面積 × 厚さで決まる。厚さは行ごとに与え、単位は ratio_param_unit_code（mm）で持つ。"),
    ac("AS-FICT-0001", 3, "CM-FICT-0005", "kg", "EXTERNAL_LEDGER", None, None, None, "MISSING", "PL-FICT-0004", True,
       "面積あたりの質量は出典と許諾の確認できた値が必要で、未入手。値は置かず、参照が null のまま残る。"),
    ac("AS-FICT-0002", 1, "CM-FICT-0008", "ct_dai", "DRIVER_IDENTITY", None, None, M_UNITS, "DERIVED", "PL-FICT-0005", False,
       "基準数量（台数）そのものが機器の数量になる。"),
    ac("AS-FICT-0002", 2, "CM-FICT-0009", "m", "EXTERNAL_LEDGER", None, None, None, "MISSING", "PL-FICT-0006", True,
       "1台あたりの配管の長さは未入手。値は置かず、参照が null のまま残る。"),
]


# ------------------------------------------------------------------ similarity links
def sl(n, tk, left, right, rel, basis, rev, expl):
    return mk("similarity_link", dict(link_id="SL-FICT-%04d" % n, target_kind=tk, left_id=left, right_id=right, relation=rel, basis=basis,
                                      substitution_policy="NONE", verification_status="NOT_VERIFIED", decided_by="reviewer_a",
                                      decided_at=DAY), C(rev=rev), expl)


similarity_link = [
    sl(1, "MATERIAL_TYPE", "MT-FICT-0001", "MT-FICT-0004", "SIMILAR", "素材系統と宣言単位が同じで名称が近い。仕様と出典は別（架空の判断）。",
       "reviewer_b", "検索と提案にだけ使う。計算での置き換えは許していない。"),
    sl(2, "CANONICAL_MATERIAL", "CM-FICT-0006", "CM-FICT-0007", "DISTINCT_CONFIRMED", "識別文字列は似ているが別の製品（架空の判断）。",
       "reviewer_c", "分割 ME-FICT-0004 の結論を残し、同じ統合の提案を繰り返さないようにする。"),
]


# ------------------------------------------------------------------ param bindings (drafts only)
def pb(n, sk, sid, kind, expl):
    return mk("param_binding", dict(binding_id="PB-FICT-%04d" % n, scope_kind=sk, scope_id=sid, param_kind=kind, param_ref=None,
                                    binding_unit=None, stages=[], boundary_ref=None, link_basis=None, proxy_reason=None,
                                    proxy_link_id=None, context_condition=None, value_state="MISSING",
                                    param_license_status="UNKNOWN", priority_rank=None, rank_decided_by=None, rank_reason=None),
              C(status="DRAFT", rev=None), expl)


param_binding = [
    pb(1, "CANONICAL_MATERIAL", "CM-FICT-0001", "FACTOR",
       "係数の置き場だけを示す下書き。参照が無いので束縛としては数えず、この材料の行は計算できない。レコード自身の license_status は来歴（自作）から PERMITTED_PUBLIC、参照先の値の状態は param_license_status = UNKNOWN と、別々に持つ。"),
    pb(2, "FUNCTION_NODE", "FN-000026", "SERVICE_LIFE", "耐用年数を部位要素の水準に束縛する場合の置き場。値は持たない。"),
    pb(3, "MATERIAL_TYPE", "MT-FICT-0001", "EOL_ROUTE", "廃棄経路を品種の水準に束縛する場合の置き場。値は持たない。"),
]


# ------------------------------------------------------------------ merge events
def fr(field, kept, discarded, rule):
    return {"field": field, "kept_value": kept, "discarded_values": discarded, "rule": rule}


def rp(kind, rid, field, a, b):
    return {"ref_kind": kind, "ref_id": rid, "field": field, "from_id": a, "to_id": b}


LIC = fr("license_status", "PERMITTED_PUBLIC", [], "MOST_RESTRICTIVE")
merge_event = [
    mk("merge_event", dict(
        merge_event_id="ME-FICT-0001", event_kind="MERGE", reverts_event_id=None, target_kind="MATERIAL_TYPE", survivor_id="MT-FICT-0001",
        merged_ids=["MT-FICT-0005"], duplicate_level="D3_NEAR", survivor_rule_applied="ACTIVE_OVER_DRAFT",
        field_resolutions=[fr("name", "架空ボードA", ["架空板A"], "MOVE_TO_ALIAS"), fr("spec_attributes", ["thickness_mm"], [], "KEEP_SURVIVOR"),
                           fr("provenance", None, [], "UNION"), LIC],
        aliases_created=["AL-FICT-0005"], repointed_refs=[rp("CANONICAL_MATERIAL", "CM-FICT-0003", "type_id", "MT-FICT-0005", "MT-FICT-0001")],
        affected_descendant_ids=["CM-FICT-0003"], caused_by_event_id=None, license_before="PERMITTED_PUBLIC", license_after="PERMITTED_PUBLIC",
        decided_by="reviewer_a", reviewed_by="reviewer_b", decided_at=DAY,
        reason="別の表記で作られた下書きの品種が、同じ品種を指すと確認した。宣言単位・種別・同一性属性は同じである（架空の判断）。", release_id=REL)),
    mk("merge_event", dict(
        merge_event_id="ME-FICT-0002", event_kind="MERGE", reverts_event_id=None, target_kind="CANONICAL_MATERIAL", survivor_id="CM-FICT-0001",
        merged_ids=["CM-FICT-0003"], duplicate_level="D1_IDENTITY", survivor_rule_applied="ACTIVE_OVER_DRAFT",
        field_resolutions=[fr("name", "架空ボードA 厚12mm", ["架空板A 厚12mm"], "KEEP_SURVIVOR"), fr("provenance", None, [], "UNION"), LIC],
        aliases_created=[], repointed_refs=[], affected_descendant_ids=[], caused_by_event_id="ME-FICT-0001",
        license_before="PERMITTED_PUBLIC", license_after="PERMITTED_PUBLIC", decided_by="system", reviewed_by=None, decided_at=DAY,
        reason="品種の統合により同一性キーが完全に一致したため。元の統合 ME-FICT-0001 の確認者の承認の範囲に含まれる。", release_id=REL)),
    mk("merge_event", dict(
        merge_event_id="ME-FICT-0003", event_kind="MERGE", reverts_event_id=None, target_kind="CANONICAL_MATERIAL", survivor_id="CM-FICT-0006",
        merged_ids=["CM-FICT-0007"], duplicate_level="D3_NEAR", survivor_rule_applied="REVIEWER_DECISION",
        field_resolutions=[fr("product_key", "FICT-B1", ["FICT-B-1"], "MOVE_TO_ALIAS"), fr("provenance", None, [], "UNION"), LIC],
        aliases_created=["AL-FICT-0007"], repointed_refs=[rp("UNIT_CONVERSION", "UC-FICT-0005", "scope_id", "CM-FICT-0007", "CM-FICT-0006")],
        affected_descendant_ids=[], caused_by_event_id=None, license_before="PERMITTED_PUBLIC", license_after="PERMITTED_PUBLIC",
        decided_by="reviewer_a", reviewed_by="reviewer_b", decided_at=DAY,
        reason="製品の識別文字列の表記ゆれと判断した。どちらも有効で作成した版も同じなので、残す側は判断者が決めた（架空の判断。後に ME-FICT-0004 で取り消した）。",
        release_id=REL)),
    mk("merge_event", dict(
        merge_event_id="ME-FICT-0004", event_kind="SPLIT", reverts_event_id="ME-FICT-0003", target_kind="CANONICAL_MATERIAL",
        survivor_id="CM-FICT-0006", merged_ids=["CM-FICT-0007"], duplicate_level=None, survivor_rule_applied=None, field_resolutions=[],
        aliases_created=[], repointed_refs=[rp("UNIT_CONVERSION", "UC-FICT-0005", "scope_id", "CM-FICT-0006", "CM-FICT-0007")],
        affected_descendant_ids=[], caused_by_event_id=None, license_before=None, license_after=None, decided_by="reviewer_a",
        reviewed_by="reviewer_c", decided_at=DAY,
        reason="別の製品であることが分かったので、統合を取り消した。付け替えた換算を戻し、統合で引き継いだ来歴を外し、統合が作った別名 AL-FICT-0007 を廃止した。結論は SL-FICT-0002 に残した（架空の判断）。",
        release_id=REL)),
]

# ------------------------------------------------------------------ selections and calc rows
KINDS = S["enums"]["param_kind"]
NO_PARAMS = {k: {"value_state": "MISSING", "param_license_status": "UNKNOWN", "bound_from": "NONE", "via_default_placement": False} for k in KINDS}


def sel(n, path, pick, enter, search, accept, cands):
    return mk("selection", dict(selection_id="SEL-FICT-%04d" % n, project_id=PRJ, selection_path=path,
                                operation_count={"pick": pick, "enter": enter, "search": search, "accept": accept, "override": 0},
                                candidate_counts=cands))


selection = [
    sel(1, "ALIAS_SEARCH", 0, 1, 1, 3, []),
    sel(2, "TREE", 3, 2, 0, 0, [9, 5, 1]),
    sel(3, "ASSEMBLY", 2, 2, 0, 0, [9, 1]),
    sel(4, "ASSEMBLY", 2, 2, 0, 0, [9, 1]),
]


def row(n, seln, inp, canonical, plc, zone, eq, eu, dq, du, act, au, astate, conv_ids, conv_params, rep, defaulted, asm, line, deps,
        blocking, warnings, expl):
    return mk("calc_row", dict(
        row_id="ROW-FICT-%04d" % n, project_id=PRJ, selection_id="SEL-FICT-%04d" % seln, release_id=REL, resolution_mode="STRICT",
        input_for_illustration=inp, canonical_id=canonical, placement_state="PLACED", placement_id=plc, zone_id=zone,
        entry_quantity=eq, entry_unit=eu, driver_quantity=dq, driver_unit=du, quantity_basis="DESIGN", activity=act, activity_unit=au,
        activity_state=astate, conversion_ids=conv_ids, conversion_params=conv_params, factor_ref=None, factor_unit=None,
        factor_stages=[], factor_boundary_ref=None, mass_conversion_ids=[], service_life_ref=None, repair_rate_ref=None,
        eol_route_ref=None, waste_rate_ref=None, param_states=NO_PARAMS, representativeness=rep, defaulted_fields=defaulted,
        assembly_id=asm, assembly_line_no=line, import_source_id=None, import_locator=None, dependent_requirements=deps,
        computable=False, blocking_reasons=blocking, warnings=warnings), None, expl)


TH = {"thickness": {"value": 100, "unit_code": "mm", "unit_assumed": False, "source": "USER_INPUT"}}
IN_Z = {"path": ["屋根・外壁", "架空外壁構成Z"], "driver_quantity": 50, "thickness": 100, "thickness_unit": "mm"}
IN_S = {"path": ["空調設備", "架空機器一式S"], "driver_quantity": 2, "direct_quantity_line_2": 50}
calc_row = [
    row(1, 1, {"name_text": "架空ﾎﾞｰﾄﾞＡ　ｔ＝１２", "quantity": 100}, "CM-FICT-0001", "PL-FICT-0001", None, 100, "m2", None, None, 100, "m2",
        "USER_ESTIMATE", [], {}, "REFINED", ["placement_id", "entry_unit", "spec_unit:thickness_mm"], None, None, [],
        ["FACTOR_MISSING", "DOUBLE_COUNT_UNRESOLVED"], ["SPEC_UNIT_ASSUMED", "MASS_PATH_UNAVAILABLE"],
        "名称の入力1回と数量の入力1回に、承認が3回付く（既定の配置、その配置の入力単位、仮定した厚さの単位 mm）。承認の無い既定は適用しない。全角・半角カナのゆれは規則で吸収され、別名 AL-FICT-0001 に一致する。係数の参照が無いので計算はできない。ROW-FICT-0003 と同じ配置・同じ品種なので、置き換えか追加数量かを決めるまで二重計上の検査で止まる。回数は、別名が登録済みで既定が当たる場合の構造上の下限であり、測定値ではない。"),
    row(2, 2, {"path": ["屋根・外壁", "外壁断熱", "架空充填材X"], "thickness": 100, "thickness_unit": "mm", "quantity": 200}, "CM-FICT-0004",
        "PL-FICT-0003", "ZN-FICT-B", 200, "m2", None, None, 20, "m3", "DERIVED", ["UC-FICT-0003"], TH, "EXACT", [], None, None, [],
        ["FACTOR_MISSING", "DOUBLE_COUNT_UNRESOLVED"], ["CONVERSION_APPLIED", "MASS_PATH_UNAVAILABLE"],
        "単位換算の例。選んだ配置が入力単位を m2 に決めるので、単位を選ぶ操作は無い（自分で選んだ配置の単位なので既定の承認にも当たらない）。200 m2 × 100 mm = 20 m3。換算した活動量は DERIVED とし、元の入力値・換算 ID・厚さの値と単位と取得元を残す。ゾーンを分けていない ROW-FICT-0004（同じ配置・同じ品種）はすべてのゾーンと重なるので、二重計上の検査で止まる。候補数 [9, 5, 1] の最後の 1 は、この例に配置が1件しか無いためで、実際の候補数を示すものではない。"),
    row(3, 3, IN_Z, "CM-FICT-0001", "PL-FICT-0001", None, None, None, 50, "m2", 50, "m2", "DERIVED", [], {}, "EXACT", [], "AS-FICT-0001", 1, [],
        ["FACTOR_MISSING", "DOUBLE_COUNT_UNRESOLVED"], ["MASS_PATH_UNAVAILABLE"],
        "アセンブリの例（1行目）。部位グループとアセンブリを選び、基準数量と厚さを入れる4操作で3行ができる。基準数量は入力数量とは別の項目（driver_quantity）に持つ。構成量は基準数量そのもの。ROW-FICT-0001 と同じ配置・同じ品種なので、二重計上の検査で止まる。"),
    row(4, 3, IN_Z, "CM-FICT-0004", "PL-FICT-0003", None, None, None, 50, "m2", 5, "m3", "DERIVED", [], TH, "EXACT", [], "AS-FICT-0001", 2, [],
        ["FACTOR_MISSING", "DOUBLE_COUNT_UNRESOLVED"], ["MASS_PATH_UNAVAILABLE"],
        "アセンブリの例（2行目）。50 m2 × 100 mm = 5 m3。ゾーンを分けていない行はすべてのゾーンと重なるものとして扱うので、ゾーン ZN-FICT-B の ROW-FICT-0002 と二重計上の検査に掛かる。"),
    row(5, 3, IN_Z, "CM-FICT-0005", "PL-FICT-0004", None, None, None, 50, "m2", None, "kg", "MISSING", [], {}, "EXACT", [], "AS-FICT-0001", 3, [],
        ["ASSEMBLY_RATIO_MISSING", "FACTOR_MISSING"], [],
        "アセンブリの例（3行目）。構成量の参照が無いので活動量は欠損のまま（0 にしない）。基準数量（m2）を、kg で数える行の入力数量として扱うことはしない。利用者が数量を直接入れれば、入力が1回増えて行が完成する（ROW-FICT-0007 がその例）。"),
    row(6, 4, IN_S, "CM-FICT-0008", "PL-FICT-0005", None, None, None, 2, "ct_dai", 2, "ct_dai", "DERIVED", [], {}, "EXACT", [], "AS-FICT-0002", 1,
        [{"kind": "REFRIGERANT_CHARGE", "state": "MISSING"}], ["FACTOR_MISSING"], ["MASS_PATH_UNAVAILABLE"],
        "設備の例（機器。台で数える）。基準数量（台数）がそのまま活動量になる。付随して要る入力（冷媒）は、値を補わずに未入力の要求として残る。"),
    row(7, 4, IN_S, "CM-FICT-0009", "PL-FICT-0006", None, 50, "m", 2, "ct_dai", 50, "m", "USER_ESTIMATE", [], {}, "EXACT", [], "AS-FICT-0002", 2, [],
        ["FACTOR_MISSING"], ["MASS_PATH_UNAVAILABLE"],
        "設備の例（線状品。長さで数える）。1台あたりの配管の長さが無いので、利用者が長さを直接入れた（入力が1回増える）。基準数量とは別に、入力数量として残す。"),
]

# ------------------------------------------------------------------ illustration-only sections
def ill(d):
    return dict({"record_flag": "FICTIONAL_PLACEHOLDER"}, **d)


duplicate_handling = [
    ill({"duplicate_level": "D0_RAW_EXACT", "records": ["RAW-FICT-0001", "RAW-FICT-0005"],
         "handling": "同じ出典の同じ内容の行。content_hash が一致するので、RAW-FICT-0005 は別レコードのまま DUPLICATE_RAW として残し、以降の処理に進めない。先行レコードは書き換えず、出現回数は duplicate_of_raw を数えて求める。統合イベントは作らない。案件の数量行にはこの扱いをしない。"}),
    ill({"duplicate_level": "D1_IDENTITY", "records": ["RAW-FICT-0001", "RAW-FICT-0002"],
         "handling": "表記は違うが正規化後の同一性キーが一致する。2件目は新しいレコードを作らず、CM-FICT-0001 に来歴（OBSERVED_MATCH）を足す。"}),
    ill({"duplicate_level": "D2_UNIT_VARIANT", "records": ["RAW-FICT-0001", "RAW-FICT-0004"],
         "handling": "同一性は同じで単位だけが違う（面積と枚）。正規材料レコードは1件のままにし、単位換算 UC-FICT-0002 を登録する。"}),
    ill({"duplicate_level": "D2_UNIT_VARIANT", "records": ["CM-FICT-0004", "RAW-FICT-0007"],
         "handling": "同じ材料が体積（宣言単位）と質量で現れる。次元が違っても別の品種にせず、換算 UC-FICT-0004 で表す。根拠（密度の参照）が無いので停止状態のままになる。"}),
    ill({"duplicate_level": "D3_NEAR", "records": ["MT-FICT-0001", "MT-FICT-0005"],
         "handling": "名称が近いが規則では一致しない。宣言単位・種別・同一性属性が同じであることを確かめたうえで、人が同じ品種と確認して統合した（ME-FICT-0001）。配下のレコードの統合（ME-FICT-0002）は、その承認の範囲に含まれる。"}),
    ill({"duplicate_level": "D3_NEAR", "records": ["MT-FICT-0001", "MT-FICT-0004"],
         "handling": "名称が近いが別の品種。統合せず、類似関係 SL-FICT-0001 として残す。"}),
    ill({"duplicate_level": "D3_NEAR", "records": ["CM-FICT-0006", "CM-FICT-0007"],
         "handling": "一度統合した（ME-FICT-0003）が、別の製品と分かって取り消した（ME-FICT-0004）。付け替えた参照を戻し、結論を SL-FICT-0002（DISTINCT_CONFIRMED）に残す。"}),
]

what_this_shows = [
    ill({"topic": "別名（名称ゆれ）", "records": ["AL-FICT-0001", "AL-FICT-0002", "AL-FICT-0003", "RAW-FICT-0001", "RAW-FICT-0002", "RAW-FICT-0003", "RAW-FICT-0006"],
         "point": "規則で吸収できるゆれは行を増やさない。規則で決められないゆれは人が別名に登録し、判断記録を残す。総称は候補を返して止める。"}),
    ill({"topic": "単位換算", "records": ["UC-FICT-0001", "UC-FICT-0002", "UC-FICT-0003", "UC-FICT-0004", "RAW-FICT-0007", "ROW-FICT-0002"],
         "point": "根拠が寸法の仕様値または行ごとの入力なら換算できる。外部の値が要る換算は、参照が無ければ止まる。次元の違う単位で現れても品種は分けない。"}),
    ill({"topic": "重複の統合と取り消し", "records": ["RAW-FICT-0005", "RAW-FICT-0004", "MT-FICT-0005", "CM-FICT-0003", "ME-FICT-0001", "ME-FICT-0002", "ME-FICT-0003", "ME-FICT-0004", "SL-FICT-0001", "SL-FICT-0002"],
         "point": "重複の水準ごとに扱いが違う。統合しても行は消さず、付け替えた参照を記録するので取り消せる。似ているだけのものは統合しない。"}),
    ill({"topic": "人の判断記録", "records": ["CD-FICT-0001", "CD-FICT-0002", "CD-FICT-0003", "CD-FICT-0004", "CD-FICT-0005", "CD-FICT-0006"],
         "point": "規則で決まらないこと（仮定した単位の確定、別名の登録、対象外の判定、新しい品種の作成）は、人の判断として残す。下書きは自動では作られない。"}),
    ill({"topic": "アセンブリ", "records": ["AS-FICT-0001", "ROW-FICT-0003", "ROW-FICT-0004", "ROW-FICT-0005"],
         "point": "1回の指定を構成要素ごとの行に展開する。構成量の値は持たず、欠けた行は欠けたまま残る。"}),
    ill({"topic": "設備の最小の例", "records": ["MT-FICT-0006", "MT-FICT-0007", "AS-FICT-0002", "ROW-FICT-0006", "ROW-FICT-0007"],
         "point": "台で数える機器、長さで数える線状品、機器と付属の一式が、建築の材料と同じレコードで組める。組めることだけを示し、設備の分類の妥当性は示さない。"}),
    ill({"topic": "複数の部位で使う材料", "records": ["PL-FICT-0001", "PL-FICT-0002"], "point": "品目は1回だけ登録し、配置を増やす。"}),
    ill({"topic": "許諾の関門と対象外", "records": ["SRC-FICT-0003", "RAW-FICT-0008"],
         "point": "許諾が確認できない出典は、中身を保存せずに止める。材料でない行は、理由を付けて対象外にする。"}),
    ill({"topic": "二重計上の検査", "records": ["ROW-FICT-0001", "ROW-FICT-0003", "ROW-FICT-0002", "ROW-FICT-0004"],
         "point": "アセンブリ由来の行と個別指定の行が、同じ案件・同じ配置・同じ品種で重なったら止める。ゾーンを分けていない行は、すべてのゾーンと重なるものとして扱う。"}),
    ill({"topic": "操作の計測", "records": ["SEL-FICT-0001", "SEL-FICT-0002", "SEL-FICT-0003", "SEL-FICT-0004"],
         "point": "操作の回数は計算行ではなく指定ごとの記録に持つ。既定・仮定の承認も数える。回数は構造上の下限であり、測定値ではない。"}),
]

RUN = ["INV-01", "INV-02", "INV-03", "INV-04", "INV-05", "INV-06", "INV-07", "INV-08", "INV-09", "INV-10", "INV-11", "INV-12", "INV-14",
       "INV-17", "INV-18", "INV-19", "INV-20", "INV-21", "INV-22"]
release = [mk("release", dict(
    release_id=REL, parent_release_id=None, schema_version=S["schema_version"], normalizer_version=NV, compartment="PUBLIC_RELEASE",
    manifest_hash=None, invariant_report={i["id"]: ("PASS" if i["id"] in RUN else "NOT_RUN") for i in S["invariants"]},
    breaking_change_ids=["MT-FICT-0005", "CM-FICT-0003", "CM-FICT-0006", "CM-FICT-0007"], status="DRAFT"),
    explanation="invariant_report は、この例に対して一時的なスクリプトで検査した結果である（INV-11 は assumed_active_nodes の仮定の下で）。INV-13・INV-15・INV-16 は実行していないので、この版は公開できない状態（DRAFT）のままである。")]

doc = {
    "status": "DESIGN_DRAFT",
    "verification": "NOT_VERIFIED",
    "all_records_flag": "FICTIONAL_PLACEHOLDER",
    "created": DAY,
    "note": "本ファイルのレコードはすべて架空のプレースホルダである。「架空ボードA」「架空ボードB」「架空板A」「架空充填材X」「架空下地材Y」「架空機器Q」「架空配管R」「架空外壁構成Z」「架空機器一式S」という材料・製品・構成、および出典 SRC-FICT-* は実在しない。排出係数・耐用年数・修繕率・密度・構成比の値は1つも含まない（参照はすべて null）。数量（100、200、50、2）と厚さ（12、100）は説明のために置いた入力値である。この例が示すのは、レコードどうしが矛盾なく組めることだけであり、実データへの適合や実用上の妥当性は示さない。例は建築の一部（屋根・外壁、内装）と空調設備の最小の例だけで、基礎・躯体・開口部・電気設備・給排水設備・搬送設備の例は無い。",
    "id_note": "ID に含まれる FICT は例示用の印であり、taxonomy_schema.json の ID 形式にわざと一致させていない。部位・素材系統のノード ID（FN-、IN-）だけは classification_tree.json の草案ノードを指す。",
    "schema": "taxonomy_schema.json",
    "illustration_only": {
        "note": "次の節と項目は説明用であり、taxonomy_schema.json の定義には無い。",
        "sections": ["assumed_active_nodes", "duplicate_handling", "what_this_shows"],
        "fields": ["record_flag", "explanation", "identity_array_for_illustration", "gate_result", "input_for_illustration"],
    },
    "assumed_active_nodes": {
        "note": "classification_tree.json のノードはすべて DRAFT または RESERVED である。この例の中に限り、架空の版 REL-FICT-0001 で次のノード（例が参照するノードとその親）が定義を与えられて ACTIVE になったと仮定する。INV-11 はこの仮定の下で検査した。実際のノードの状態は変えていない。",
        "node_ids": ["FN-000001", "FN-000002", "FN-000005", "FN-000007", "FN-000009", "FN-000026", "FN-000027", "FN-000034", "FN-000040",
                     "FN-000043", "IN-000002", "IN-000008", "IN-000009", "IN-000014", "IN-000017"],
    },
    "release": release, "source": source, "raw_record": raw_record, "normalized_record": normalized_record,
    "curation_decision": curation_decision, "unit_def": unit_def, "material_type": material_type,
    "canonical_material": canonical_material, "alias": alias, "unit_conversion": unit_conversion, "placement": placement,
    "duplicate_handling": duplicate_handling, "merge_event": merge_event, "similarity_link": similarity_link, "assembly": assembly,
    "assembly_component": assembly_component, "param_binding": param_binding, "selection": selection, "calc_row": calc_row,
    "what_this_shows": what_this_shows,
}


# ------------------------------------------------------------------ writer
def js(v):
    return json.dumps(v, ensure_ascii=False, separators=(", ", ": "))


def dump_obj(o, ind, width=230):
    """1行に収まれば1行、収まらなければ項目を幅いっぱいまで詰めて折り返す。"""
    one = js(o)
    if len(one) <= width:
        return ind + one
    items = [js(k) + ": " + js(v) for k, v in o.items()]
    lines, cur = [], ""
    for it in items:
        if cur and len(cur) + len(it) + 2 > width:
            lines.append(cur)
            cur = it
        else:
            cur = it if not cur else cur + ", " + it
    lines.append(cur)
    return ind + "{\n" + ",\n".join(ind + "  " + l for l in lines) + "\n" + ind + "}"


parts = []
for k, v in doc.items():
    if isinstance(v, list):
        parts.append("  " + js(k) + ": [\n" + ",\n".join(dump_obj(r, "    ") for r in v) + "\n  ]")
    elif isinstance(v, dict):
        parts.append("  " + js(k) + ": " + dump_obj(v, "  ").lstrip())
    else:
        parts.append("  " + js(k) + ": " + js(v))
text = "{\n" + ",\n".join(parts) + "\n}\n"
json.loads(text)
open(OUT + "example_records.json", "w", encoding="utf-8").write(text)
print({k: len(v) for k, v in doc.items() if isinstance(v, list)})
print("bytes", len(text.encode("utf-8")), "lines", text.count("\n"))
