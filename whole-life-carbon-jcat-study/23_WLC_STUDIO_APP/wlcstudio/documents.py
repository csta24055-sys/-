"""Uploaded documents (quantity tables, IFC, PDF) -> candidate values of the material fields.

A read number never becomes a value by itself: each mapped quantity is a candidate in state 図面から計算
(from_drawing) with the trace (sheet/row/column, IFC entity, page/line) in source_detail; the user accepts it.
Guards against double counting: total/subtotal rows are not added, the same file (SHA-256) is not read twice,
and rows that map to no field or whose unit the field cannot take are listed as not used.
"""
from __future__ import annotations

import base64
import hashlib
import re

from . import fields as FL
from .importers import ifc, pdf, tabular
from .provenance import Value

KEYWORDS = [  # (field, words) — first match wins; foundation concrete is decided by the division/element
    ("m_rebar", ("鉄筋", "異形棒鋼", "rebar", "reinforc")),
    ("m_steel", ("鉄骨", "鋼材", "形鋼", "鋼管", "デッキ", "structural steel", "steel")),
    ("m_concrete", ("コンクリート", "生コン", "concrete")),
    ("m_timber", ("木材", "製材", "集成材", "合板", "clt", "timber", "wood", "lumber")),
    ("m_glass", ("ガラス", "glass")),
    ("m_aluminium", ("アルミ", "alumin")),
    ("m_masonry", ("alc", "ブロック", "れんが", "レンガ", "押出成形", "masonry", "brick")),
    ("m_membrane", ("防水", "membrane", "waterproof")),
    ("m_insulation", ("断熱", "insulation")),
    ("m_board", ("石膏ボード", "せっこうボード", "ボード", "board", "gypsum")),
    ("m_mortar", ("モルタル", "mortar", "plaster")),
    ("m_plastic", ("塩ビ", "樹脂", "pvc", "plastic", "ポリ")),
    ("m_finish", ("仕上", "塗装", "クロス", "タイル", "床材", "finish", "tile", "paint", "flooring")),
]
FOUNDATION_WORDS = ("基礎", "杭", "フーチング", "地中梁", "footing", "pile", "foundation")
TOTAL_WORDS = ("合計", "小計", "総計", "計", "total", "subtotal", "sum")
UNIT_ALIASES = {"m3": "m3", "㎥": "m3", "m³": "m3", "立米": "m3", "t": "t", "ｔ": "t", "トン": "t", "ton": "t",
                "kg": "kg", "ｋｇ": "kg", "m2": "m2", "㎡": "m2", "m²": "m2", "平米": "m2"}


def _field_for(name: str, division: str = "") -> str | None:
    low = (name or "").lower()
    for fid, words in KEYWORDS:
        if any(w in low for w in words):
            if fid == "m_concrete" and any(w in (division or "") + low for w in FOUNDATION_WORDS):
                return "m_concrete_fdn"
            return fid
    return None


def _is_total(name: str) -> bool:
    n = (name or "").strip().lower()
    return any(n == w or n.startswith(w) or n.endswith(w) for w in TOTAL_WORDS)


def _unit(u: str) -> str | None:
    return UNIT_ALIASES.get((u or "").strip().lower()) or UNIT_ALIASES.get((u or "").strip())


def kind_of(name: str, data: bytes) -> str:
    n = name.lower()
    if n.endswith(".csv"):
        return "csv"
    if n.endswith(".xlsx"):
        return "xlsx"
    if n.endswith(".ifc") or data[:20].startswith(b"ISO-10303-21"):
        return "ifc"
    if n.endswith(".pdf") or data[:5] == b"%PDF-":
        return "pdf"
    return "unknown"


def read(name: str, data_b64: str, doc_id: str) -> dict:
    """Parse one uploaded file. Returns {kind, sha256, parsed, proposals:[Value...], unused:[...], warnings:[...]}."""
    try:
        data = base64.b64decode(data_b64, validate=True)
    except Exception:
        raise ValueError("ファイルの中身を読めない（base64 でない）") from None
    kind = kind_of(name, data)
    sha = hashlib.sha256(data).hexdigest()
    warnings, unused, sums = [], [], {}
    if kind in ("csv", "xlsx"):
        parsed = tabular.read_csv(data, doc_id) if kind == "csv" else tabular.read_xlsx(data, doc_id)
        for sh in parsed["sheets"]:
            if sh.get("error"):
                warnings.append("%s：%s" % (sh["sheet"], sh["error"]))
            for s in sh.get("skipped", []):
                unused.append({"trace": s["trace"], "name": s["name"], "reason": s["reason"]})
            for r in sh["rows"]:
                if _is_total(r["name"]):
                    unused.append({"trace": r["trace"], "name": r["name"], "reason": "合計・小計の行は足さない（二重計上を防ぐ）"})
                    continue
                fid = _field_for(r["name"] + " " + r.get("specification", ""), r.get("division", ""))
                u = _unit(r["unit"])
                if fid is None:
                    unused.append({"trace": r["trace"], "name": r["name"], "reason": "どの材料の欄にも当てはまらない"})
                    continue
                if u not in FL.FIELDS[fid]["units"]:
                    unused.append({"trace": r["trace"], "name": r["name"],
                                   "reason": "単位 %r は「%s」に使えない（%s）" % (r["unit"], FL.FIELDS[fid]["label"], "・".join(FL.FIELDS[fid]["units"]))})
                    continue
                sums.setdefault((fid, u), []).append((r["quantity"], r["trace"]))
    elif kind == "ifc":
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("latin-1")
        parsed = ifc.parse(text, doc_id)
        for e in parsed["elements"]:
            mats = " ".join(e["materials"]) + " " + e["name"]
            fid = _field_for(mats, "footing" if e["type"] in ("IFCFOOTING", "IFCPILE") else "")
            if e["type"] == "IFCREINFORCINGBAR":
                fid = "m_rebar"
            if fid is None:
                unused.append({"trace": "%s:#%d" % (doc_id, e["step_id"]), "name": "%s %s" % (e["type"], e["name"]),
                               "reason": "材料名から分類できない（%s）" % ("・".join(e["materials"]) or "材料の記録なし")})
                continue
            want = {"m3": "volume", "m2": "area", "kg": "weight", "t": "weight"}
            picked = None
            for u in FL.FIELDS[fid]["units"]:
                q = [x for x in e["quantities"] if x["kind"] == want[u]]
                if q:
                    # prefer net over gross when both exist (gross double-counts openings)
                    q.sort(key=lambda x: 0 if "net" in x["name"].lower() else 1)
                    picked = (u if u != "t" else "kg", q[0])
                    break
            if picked is None:
                unused.append({"trace": "%s:#%d" % (doc_id, e["step_id"]), "name": "%s %s" % (e["type"], e["name"]),
                               "reason": "「%s」に使える数量（%s）が IFC の数量セットに無い（形状からは測らない）"
                                         % (FL.FIELDS[fid]["label"], "・".join(FL.FIELDS[fid]["units"]))})
                continue
            u, q = picked
            sums.setdefault((fid, u), []).append((q["value"], q["trace"]))
        if parsed["no_quantities"]:
            warnings.append("数量セットの無い部材 %d 個は数えていない（0 にしない）" % len(parsed["no_quantities"]))
    elif kind == "pdf":
        parsed = pdf.read(data, doc_id)
        if parsed.get("error"):
            raise ValueError(parsed["error"])
        if parsed["pages_without_text"]:
            warnings.append("文字の無いページ（スキャン画像）は読んでいない：%s" % parsed["pages_without_text"][:20])
        per_field = {}
        for c in parsed["candidates"]:
            fid = _field_for(c["name"])
            u = _unit(c["unit"])
            if fid is None or u not in FL.FIELDS.get(fid, {}).get("units", []):
                unused.append({"trace": c["trace"], "name": c["name"], "reason": "材料の欄・単位に当てはまらない"})
                continue
            if _is_total(c["name"]):
                unused.append({"trace": c["trace"], "name": c["name"], "reason": "合計の行は候補にしない"})
                continue
            per_field.setdefault(fid, []).append((c, u))
        proposals = []
        for fid, cs in per_field.items():
            for c, u in cs[:5]:          # PDF lines are never added up: each is a separate candidate to check
                proposals.append(Value(fid, "from_drawing", c["quantity"], u, method="pdf_text_line", source_id=doc_id,
                                       source_detail=c["trace"], note="PDF の 1 行「%s」。寸法・合計を拾うことがあるので原本で確認" % c["line"][:60]))
        return {"kind": kind, "sha256": sha, "parsed_summary": {"n_pages": parsed["n_pages"], "n_lines": len(parsed["candidates"])},
                "proposals": proposals, "unused": unused, "warnings": warnings}
    else:
        raise ValueError("この形式は読めない（CSV・XLSX・IFC・PDF）")
    proposals = []
    for (fid, u), items in sums.items():
        total = sum(q for q, _ in items)
        traces = [t for _, t in items]
        detail = "%d 行の合計：%s%s" % (len(items), "、".join(traces[:12]), "…" if len(traces) > 12 else "")
        proposals.append(Value(fid, "from_drawing", round(total, 6), u, method="%s_quantity_sum" % kind, source_id=doc_id,
                               source_detail=detail, note="資料「%s」から。分類はキーワードによるので確認する" % doc_id))
    summ = {"n_rows": sum(len(s["rows"]) for s in parsed["sheets"])} if kind in ("csv", "xlsx") else \
        {"n_elements": len(parsed["elements"]), "schema": parsed["schema"]}
    return {"kind": kind, "sha256": sha, "parsed_summary": summ, "proposals": proposals, "unused": unused, "warnings": warnings}
