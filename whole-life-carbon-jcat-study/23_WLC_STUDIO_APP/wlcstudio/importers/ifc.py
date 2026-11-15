"""Element quantities and materials from an IFC file (ISO 10303-21 text, IFC2x3/IFC4), without external libraries.

For each building element (IfcWall, IfcSlab, IfcBeam, IfcColumn, IfcFooting, IfcPile, IfcMember, IfcPlate,
IfcStair, IfcRoof, IfcCovering, IfcCurtainWall, IfcDoor, IfcWindow, IfcRailing, IfcReinforcingBar ...)
we read: GlobalId, name, quantities from IfcElementQuantity (volume, area, weight, length, count) and the
associated material names (IfcRelAssociatesMaterial). Every number keeps the element's STEP id and
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
    for eid, (typ, args) in ents.items():
        if typ == "IFCUNITASSIGNMENT":
            for r in _refs(args):
                for kind, ut in UNIT_TYPE.items():
                    f = si_factor(r, kind)
                    if f is not None:
                        defaults[kind] = f
                if r in ents and ents[r][0] != "IFCSIUNIT":
                    unit_notes.append("SI でない単位（#%d %s）があり、その単位の数量は読まない" % (r, ents[r][0]))
                    for kind, ut in UNIT_TYPE.items():
                        if ut in ents[r][1]:
                            defaults[kind] = None
    if "length" in defaults and defaults["length"] is not None:
        defaults.setdefault("area", defaults["length"] ** 2)
        defaults.setdefault("volume", defaults["length"] ** 3)
    if not any(k in defaults for k in ("area", "volume", "weight")):
        unit_notes.append("単位の割り当て（IfcUnitAssignment）が無いので、SI の基本単位（m2・m3・kg）とみなした")
    elements = {}
    for eid, (typ, args) in ents.items():
        if typ in ELEMENT_TYPES:
            a = _split_args(args)
            elements[eid] = {"step_id": eid, "type": typ, "global_id": _str(a[0]) if a else "", "name": _str(a[2]) if len(a) > 2 else "",
                             "quantities": [], "materials": []}
    qsets = {}
    for eid, (typ, args) in ents.items():
        if typ == "IFCELEMENTQUANTITY":
            a = _split_args(args)
            qsets[eid] = (_str(a[2]) if len(a) > 2 else "", _refs(a[-1]))
    for eid, (typ, args) in ents.items():
        if typ == "IFCRELDEFINESBYPROPERTIES":
            a = _split_args(args)
            objs, pdef = _refs(a[4]), _refs(a[5])
            for p in pdef:
                if p in qsets:
                    qname, qids = qsets[p]
                    for o in objs:
                        if o in elements:
                            for q in qids:
                                if q in ents and ents[q][0] in QTY:
                                    qa = _split_args(ents[q][1])
                                    kind, unit = QTY[ents[q][0]]
                                    val = _num(qa[3]) if len(qa) > 3 else None
                                    if val is None:
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
                stack, seen = [mref], set()
                while stack and len(seen) < 10000:           # a reference cycle or a huge file cannot loop forever
                    r = stack.pop()
                    if r in seen or r not in ents:
                        continue
                    seen.add(r)
                    t2, a2 = ents[r]
                    if t2 not in MATERIAL_TYPES:
                        continue
                    if t2 == "IFCMATERIAL":
                        names.append(_str(_split_args(a2)[0]))
                    else:
                        stack.extend(_refs(a2))
            for o in objs:
                if o in elements:
                    elements[o]["materials"].extend(n for n in names if n)
    els = sorted(elements.values(), key=lambda e: e["step_id"])
    return {"format": "ifc", "schema": schema, "n_entities": len(ents), "elements": els, "unit_notes": unit_notes,
            "unit_factors": {k: v for k, v in defaults.items()},
            "no_quantities": [e["global_id"] or e["step_id"] for e in els if not e["quantities"]]}
