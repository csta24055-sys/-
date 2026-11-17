"""Element quantities and materials from an IFC file (ISO 10303-21 text, IFC2x3/IFC4), without external libraries.

For each building element (IfcWall, IfcSlab, IfcBeam, IfcColumn, IfcFooting, IfcPile, IfcMember, IfcPlate,
IfcStair, IfcRoof, IfcCovering, IfcCurtainWall, IfcDoor, IfcWindow, IfcRailing, IfcReinforcingBar ...)
we read: GlobalId, name, quantities from IfcElementQuantity (volume, area, weight, length, count), the
associated material names (IfcRelAssociatesMaterial) and the renovation status of Pset_<…>Common.Status when it is
DEMOLISH, EXISTING or TEMPORARY (the element is then no new material). Every number keeps the element's STEP id and
GlobalId as its trace. Geometry is NOT measured: an element without quantity sets yields no number
(listed as 'no_quantities'), never 0.
"""
from __future__ import annotations

import re

ELEMENT_TYPES = {"IFCWALL", "IFCWALLSTANDARDCASE", "IFCSLAB", "IFCBEAM", "IFCCOLUMN", "IFCFOOTING", "IFCPILE", "IFCMEMBER",
                 "IFCPLATE", "IFCSTAIR", "IFCSTAIRFLIGHT", "IFCROOF", "IFCCOVERING", "IFCCURTAINWALL", "IFCDOOR",
                 "IFCWINDOW", "IFCRAILING", "IFCREINFORCINGBAR", "IFCREINFORCINGMESH", "IFCBUILDINGELEMENTPROXY",
                 "IFCRAMP", "IFCCHIMNEY", "IFCSHADINGDEVICE"}
QTY = {"IFCQUANTITYVOLUME": ("volume", "m3"), "IFCQUANTITYAREA": ("area", "m2"), "IFCQUANTITYWEIGHT": ("weight", "kg"),
       "IFCQUANTITYLENGTH": ("length", "m"), "IFCQUANTITYCOUNT": ("count", "")}
UNIT_TYPE = {"volume": "VOLUMEUNIT", "area": "AREAUNIT", "weight": "MASSUNIT", "length": "LENGTHUNIT"}
PREFIX = {"EXA": 1e18, "PETA": 1e15, "TERA": 1e12, "GIGA": 1e9, "MEGA": 1e6, "KILO": 1e3, "HECTO": 1e2, "DECA": 1e1,
          "DECI": 1e-1, "CENTI": 1e-2, "MILLI": 1e-3, "MICRO": 1e-6, "NANO": 1e-9, "PICO": 1e-12, "FEMTO": 1e-15, "ATTO": 1e-18}
# SI unit name -> (power of the prefix, factor to the app unit): m2, m3, kg, m
SI_NAME = {"SQUARE_METRE": (2, 1.0), "CUBIC_METRE": (3, 1.0), "GRAM": (1, 1e-3), "METRE": (1, 1.0)}
# only these entities lead from a material association to IfcMaterial (no free walk over every reference)
MATERIAL_TYPES = {"IFCMATERIAL", "IFCMATERIALLIST", "IFCMATERIALLAYERSETUSAGE", "IFCMATERIALLAYERSET", "IFCMATERIALLAYER",
                  "IFCMATERIALCONSTITUENTSET", "IFCMATERIALCONSTITUENT", "IFCMATERIALPROFILESETUSAGE",
                  "IFCMATERIALPROFILESET", "IFCMATERIALPROFILE"}
LINE = re.compile(r"#(\d+)\s*=\s*([A-Z0-9_]+)\s*\((.*)\)\s*;\s*$", re.S)
MAX_WALK, MAX_QUANTITIES, MAX_NAMES = 500_000, 200_000, 20       # budgets for one file
MAX_STATUS = 2_000_000             # properties of the Pset_…Common sets read, and elements given a status (15 回目)
MAX_STATUS_PROPS = 8               # properties named Status read in one set (a set has one)
# the renovation status of an element: Pset_<…>Common.Status (PEnum_ElementStatus: NEW, EXISTING, DEMOLISH, TEMPORARY,
# OTHER, NOTKNOWN, UNSET), as an IfcPropertySingleValue or an IfcPropertyEnumeratedValue, in any letter case (IFC2x3
# writes Demolish, IFC4 DEMOLISH). Only the values that leave an element out are kept (15 回目)
_PSET_COMMON = re.compile(r"pset_\w*common", re.I)
_STATUS_ARG = re.compile(r"\s*'\s*status\s*'", re.I)
_PSET_NAME = re.compile(r"\s*'(?:[^']|'')*'\s*,\s*(?:\$|#\d+)\s*,\s*'pset_\w*common'\s*,", re.I)
STATUS_OUT = {"DEMOLISH": "DEMOLISH", "DEMOLISHED": "DEMOLISH", "EXISTING": "EXISTING", "TEMPORARY": "TEMPORARY"}
_STATUS_RANK = {"DEMOLISH": 3, "EXISTING": 2, "TEMPORARY": 1}


def _split_args(s: str) -> list:
    """Split a STEP argument list at top-level commas, keeping nested lists and quoted strings."""
    out, depth, cur, q = [], 0, [], False
    i = 0
    while i < len(s):
        ch = s[i]
        if q:
            cur.append(ch)
            if ch == "'":
                if i + 1 < len(s) and s[i + 1] == "'":
                    cur.append("'")
                    i += 1
                else:
                    q = False
        elif ch == "'":
            q = True
            cur.append(ch)
        elif ch == "(":
            depth += 1
            cur.append(ch)
        elif ch == ")":
            depth -= 1
            cur.append(ch)
        elif ch == "," and depth == 0:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
        i += 1
    if cur or out:
        out.append("".join(cur).strip())
    return out


def _str(a: str) -> str:
    a = a.strip()
    if a.startswith("'") and a.endswith("'"):
        t = a[1:-1].replace("''", "'")
        # IFC \X2\...\X0\ encoding of non-ASCII text
        def x2(m):
            h = m.group(1)
            return "".join(chr(int(h[k:k + 4], 16)) for k in range(0, len(h), 4))
        return re.sub(r"\\X2\\([0-9A-Fa-f]+)\\X0\\", x2, t)
    return ""


def _refs(a: str) -> list[int]:
    return [int(x) for x in re.findall(r"#(\d+)", a)]


def _num(a: str):
    a = a.strip()
    m = re.fullmatch(r"(?:[A-Z]+\()?(-?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?)\)?", a)
    return float(m.group(1)) if m else None


def parse(text: str, doc_id: str) -> dict:
    if "ISO-10303-21" not in text[:200]:
        raise ValueError("IFC（ISO 10303-21 のテキスト形式）として読めない")
    data = text.split("DATA;", 1)[-1]
    ents = {}
    buf = ""
    for raw in data.splitlines():
        buf += raw.strip()
        if buf.endswith(";"):
            m = LINE.match(buf)
            if m:
                ents[int(m.group(1))] = (m.group(2), m.group(3))
            buf = ""
    schema = "IFC4" if "IFC4" in text[:2000] else ("IFC2X3" if "IFC2X3" in text[:2000] else "unknown")

    def si_factor(ref: int, kind: str):
        """Factor from a unit entity to the app unit (m3 / m2 / kg / m), or None if it is not a plain SI unit."""
        if ref not in ents or ents[ref][0] != "IFCSIUNIT":
            return None
        a = _split_args(ents[ref][1])
        if len(a) < 4:
            return None
        utype, pre, name = a[1].strip("."), a[2].strip("."), a[3].strip(".")
        if UNIT_TYPE.get(kind) != utype or name not in SI_NAME:
            return None
        power, base = SI_NAME[name]
        p = 1.0 if a[2] in ("$", "") else PREFIX.get(pre)
        return None if p is None else (p ** power) * base

    defaults, unit_notes = {}, []
    assigned = False
    for eid, (typ, args) in ents.items():
        if typ == "IFCUNITASSIGNMENT":
            assigned = True
            for r in _refs(args):
                for kind, ut in UNIT_TYPE.items():
                    f = si_factor(r, kind)
                    if f is not None:
                        defaults[kind] = f
                if r in ents and ents[r][0] == "IFCCONVERSIONBASEDUNIT":
                    # only units of length / area / volume / mass matter here (currency, derived units etc. are ignored)
                    a = _split_args(ents[r][1])
                    utype = a[1].strip(".") if len(a) > 1 else ""
                    for kind, ut in UNIT_TYPE.items():
                        if ut == utype:
                            defaults[kind] = None
                            unit_notes.append("%s が SI でない単位（%s）なので、その単位の数量は読まない" % (ut, _str(a[2]) if len(a) > 2 else "?"))
    # area and volume follow the length unit only when they are not assigned themselves; a non-SI length (e.g. feet)
    # makes undeclared areas and volumes unusable instead of reading them as m2 / m3
    if "length" in defaults:
        for kind, power in (("area", 2), ("volume", 3)):
            if kind not in defaults:
                defaults[kind] = None if defaults["length"] is None else defaults["length"] ** power
    if not assigned:
        unit_notes.append("単位の割り当て（IfcUnitAssignment）が無いので、SI の基本単位（m2・m3・kg）とみなした")
    budget = {"walk": MAX_WALK, "q": MAX_QUANTITIES, "s": MAX_STATUS}
    qcache: dict[int, list] = {}
    memo: dict[int, list] = {}

    def material_names(ref: int) -> list:
        """Names of the IfcMaterial reachable from one material reference, following material entities only.
        Memoised per reference and bounded by a budget for the whole file, so cycles, long chains shared by many
        elements or huge lists cannot stall the (single-threaded) server."""
        if ref in memo:
            return memo[ref]
        out, stack, seen = [], [ref], set()
        while stack:
            r = stack.pop()
            if r in seen or r not in ents:
                continue
            seen.add(r)
            budget["walk"] -= 1
            if budget["walk"] < 0:
                raise ValueError("IFC の材料の参照が多すぎる")
            t2, a2 = ents[r]
            if t2 not in MATERIAL_TYPES:
                continue
            if t2 == "IFCMATERIAL":
                n = _str(_split_args(a2)[0])
                if n and n not in out and len(out) < MAX_NAMES:
                    out.append(n)
            else:
                stack.extend(_refs(a2))
        memo[ref] = out
        return out

    elements = {}
    for eid, (typ, args) in ents.items():
        if typ in ELEMENT_TYPES:
            a = _split_args(args)
            elements[eid] = {"step_id": eid, "type": typ, "global_id": _str(a[0]) if a else "", "name": _str(a[2]) if len(a) > 2 else "",
                             "quantities": [], "materials": [], "status": None}
    qsets, psets, pstatus = {}, {}, {}
    for eid, (typ, args) in ents.items():
        if typ == "IFCELEMENTQUANTITY":
            a = _split_args(args)
            qsets[eid] = (_str(a[2]) if len(a) > 2 else "", _refs(a[-1]))
        elif typ == "IFCPROPERTYSET" and _PSET_COMMON.search(args):      # (only a Pset_…Common is read)
            m = _PSET_NAME.match(args)
            if m:                                    # (GlobalId, OwnerHistory, 'Pset_…Common', …: the refs of the set's
                psets[eid] = _refs(args[m.end():])   # properties are the refs after its name)
            else:
                a = _split_args(args)
                if len(a) > 4 and _PSET_COMMON.fullmatch(_str(a[2])):
                    psets[eid] = _refs(a[4])

    def spend_status():
        budget["s"] -= 1
        if budget["s"] < 0:
            raise ValueError("IFC の状態（Status）の記録が多すぎる（%d 個まで）" % MAX_STATUS)

    def status_of(p: int):
        """The status that leaves an element out (DEMOLISH, EXISTING, TEMPORARY) given by the Pset_…Common p, or None
        (once per property set; every property looked at costs)."""
        if p in pstatus:
            return pstatus[p]
        got, seen = None, 0
        for r in dict.fromkeys(psets[p]):
            spend_status()
            if r not in ents or ents[r][0] not in ("IFCPROPERTYSINGLEVALUE", "IFCPROPERTYENUMERATEDVALUE") \
                    or not _STATUS_ARG.match(ents[r][1]):
                continue                             # (only a property named Status is split)
            pa = _split_args(ents[r][1])
            if len(pa) < 3 or _str(pa[0]).strip().lower() != "status":
                continue
            for v in re.findall(r"'((?:[^']|'')*)'|\.([A-Z_]+)\.", pa[2])[:MAX_NAMES]:
                s = STATUS_OUT.get(re.sub(r"[\s_\-]+", "", (v[0] or v[1])).upper())
                if s and _STATUS_RANK[s] > _STATUS_RANK.get(got, 0):
                    got = s
            seen += 1
            if seen >= MAX_STATUS_PROPS or got == "DEMOLISH":
                break                                # (a set has one Status; DEMOLISH is the strongest)
        pstatus[p] = got
        return got
    for eid, (typ, args) in ents.items():
        if typ == "IFCRELDEFINESBYPROPERTIES":
            a = _split_args(args)
            objs, pdef = list(dict.fromkeys(_refs(a[4]))), list(dict.fromkeys(_refs(a[5])))   # a repeated ref adds nothing
            for p in pdef:
                if p in psets:
                    s = status_of(p)
                    for o in (objs if s else ()):
                        spend_status()                       # (every pair tried costs, as for the quantities)
                        if o in elements and _STATUS_RANK[s] > _STATUS_RANK.get(elements[o]["status"], 0):
                            elements[o]["status"] = s
                    continue
                if p in qsets:
                    qname, qids = qsets[p]
                    qids = list(dict.fromkeys(qids))
                    for o in objs:
                        if o in elements:
                            for q in qids:
                                budget["q"] -= 1             # every pair tried costs, valid or not
                                if budget["q"] < 0:
                                    raise ValueError("IFC の数量が多すぎる（%d 個まで）" % MAX_QUANTITIES)
                                if q in ents and ents[q][0] in QTY:
                                    qa = qcache.get(q)
                                    if qa is None:
                                        qa = qcache[q] = _split_args(ents[q][1])
                                    kind, unit = QTY[ents[q][0]]
                                    val = _num(qa[3]) if len(qa) > 3 else None
                                    if val is None:
                                        continue
                                    if val < 0:
                                        elements[o].setdefault("unit_problems", []).append("%s:#%d/#%d（負の数量は読まない）" % (doc_id, o, q))
                                        continue
                                    factor = 1.0
                                    if kind != "count":
                                        uref = _refs(qa[2]) if len(qa) > 2 else []
                                        factor = si_factor(uref[0], kind) if uref else defaults.get(kind, 1.0)
                                    if factor is None:
                                        elements[o].setdefault("unit_problems", []).append(
                                            "%s:#%d/#%d（単位を m2・m3・kg に換算できない）" % (doc_id, o, q))
                                        continue
                                    elements[o]["quantities"].append({"set": qname, "name": _str(qa[0]), "kind": kind,
                                                                      "value": val * factor, "unit": unit, "raw_value": val,
                                                                      "factor": factor,
                                                                      "trace": "%s:#%d/#%d" % (doc_id, o, q)})
        elif typ == "IFCRELASSOCIATESMATERIAL":
            a = _split_args(args)
            objs, mat = _refs(a[4]), _refs(a[5])
            names = []
            for mref in mat:
                names += material_names(mref)
            for o in objs:
                if o in elements:
                    have = elements[o]["materials"]
                    for n in names:
                        if n and n not in have and len(have) < MAX_NAMES:
                            have.append(n)
    els = sorted(elements.values(), key=lambda e: e["step_id"])
    return {"format": "ifc", "schema": schema, "n_entities": len(ents), "elements": els, "unit_notes": unit_notes,
            "unit_factors": {k: v for k, v in defaults.items()},
            "no_quantities": [e["global_id"] or e["step_id"] for e in els if not e["quantities"]]}
