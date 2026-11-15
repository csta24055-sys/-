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
                                    if val is not None:
                                        elements[o]["quantities"].append({"set": qname, "name": _str(qa[0]), "kind": kind,
                                                                          "value": val, "unit": unit,
                                                                          "trace": "%s:#%d/#%d" % (doc_id, o, q)})
        elif typ == "IFCRELASSOCIATESMATERIAL":
            a = _split_args(args)
            objs, mat = _refs(a[4]), _refs(a[5])
            names = []
            for mref in mat:
                stack = [mref]
                while stack:
                    r = stack.pop()
                    if r not in ents:
                        continue
                    t2, a2 = ents[r]
                    if t2 == "IFCMATERIAL":
                        names.append(_str(_split_args(a2)[0]))
                    else:
                        stack.extend(_refs(a2))
            for o in objs:
                if o in elements:
                    elements[o]["materials"].extend(n for n in names if n)
    els = sorted(elements.values(), key=lambda e: e["step_id"])
    return {"format": "ifc", "schema": schema, "n_entities": len(ents), "elements": els,
            "no_quantities": [e["global_id"] or e["step_id"] for e in els if not e["quantities"]]}
