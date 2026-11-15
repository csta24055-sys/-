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
import unicodedata

from . import fields as FL
from .importers import ifc, pdf, tabular
from .provenance import Value

KEYWORDS = [  # (field, words) — first match wins; "re:" entries are regular expressions on the normalised name
    ("m_masonry", ("re:(^|[^a-z])alc([^a-z]|$)", "ブロック", "れんが", "レンガ", "押出成形", "masonry", "brick")),
    # rebar: see REBAR_PRODUCT / REBAR_GENERIC below (a reinforced-concrete name is concrete)
    ("m_rebar", ()),
    ("m_concrete", ("コンクリート", "生コン", "concrete")),
    ("m_steel", ("鉄骨", "鋼材", "形鋼", "鋼管", "デッキ", "structural steel", "steel")),
    ("m_timber", ("木材", "製材", "集成材", "合板", "clt", "timber", "wood", "lumber")),
    ("m_glass", ("ガラス", "glass")),
    ("m_aluminium", ("アルミ", "alumin")),
    ("m_membrane", ("防水", "membrane", "waterproof")),
    ("m_insulation", ("断熱", "insulation")),
    ("m_board", ("石膏ボード", "せっこうボード", "ボード", "board", "gypsum")),
    ("m_mortar", ("モルタル", "mortar", "plaster")),
    ("m_plastic", ("塩ビ", "樹脂", "pvc", "plastic", "ポリ")),
    ("m_finish", ("仕上", "塗装", "クロス", "タイル", "床材", "finish", "tile", "paint", "flooring")),
]
# words that name a reinforcement PRODUCT, also when the name mentions concrete (JIS: 鉄筋コンクリート用棒鋼;
# "reinforcement for concrete"; welded mesh; grades SD295…SD685). Bar sizes (D13) alone are not used: "board d10".
REBAR_PRODUCT = ("棒鋼", "異形鉄筋", "鉄筋コンクリート用", "re:コンクリート用.*鉄筋", "溶接金網", "ワイヤーメッシュ", "rebar",
                 "re:deformed bars?", "re:(welded|wire|steel) (wire )?mesh", "re:(^|[^a-z])sd ?[2-6]\\d{2}",
                 "re:reinforc[a-z]* (steel|bars?|mesh)", "re:steel reinforc", "re:reinforc[a-z]* for concrete")
# words that may mean the reinforcement or the reinforced concrete: rebar only when the name does not name concrete
REBAR_GENERIC = ("鉄筋", "reinforc")
CONCRETE_WORDS = ("コンクリート", "生コン", "concrete")
FOUNDATION_WORDS = ("基礎", "杭", "フーチング", "地中梁", "footing", "pile", "foundation")
TOTAL_WORDS = ("合計", "小計", "総計", "計", "total", "subtotal", "sum")
UNIT_ALIASES = {"m3": "m3", "㎥": "m3", "m³": "m3", "立米": "m3", "t": "t", "ｔ": "t", "トン": "t", "ton": "t",
                "kg": "kg", "ｋｇ": "kg", "m2": "m2", "㎡": "m2", "m²": "m2", "平米": "m2"}
_PUNCT = re.compile(r"[\s,，、。・/／_\-‐－–—:：;；()（）\[\]［］{}｛｝【】「」『』<>＜＞]+")


def normalise_name(name: str) -> str:
    """NFKC (full-width letters and digits, ㎥ …), lower case, punctuation as single spaces."""
    n = unicodedata.normalize("NFKC", name or "").lower()
    return _PUNCT.sub(" ", n).strip()


def _hit(words, low: str) -> bool:
    return any((re.search(w[3:], low) is not None) if w.startswith("re:") else (w in low) for w in words)


def _field_for(name: str, division: str = "") -> str | None:
    low = normalise_name(name)
    div = normalise_name(division)
    for fid, words in KEYWORDS:
        if fid == "m_rebar":
            if _hit(REBAR_PRODUCT, low) or (_hit(REBAR_GENERIC, low) and not _hit(CONCRETE_WORDS, low)):
                return fid
            continue
        if _hit(words, low):
            if fid == "m_concrete" and any(w in div + " " + low for w in FOUNDATION_WORDS):
                return "m_concrete_fdn"
            return fid
    return None


NOT_TOTAL_ENDINGS = ("設計", "統計", "会計", "時計", "家計", "余計", "生計", "温度計", "湿度計", "圧力計", "流量計", "水位計",
                     "電力計", "電流計", "電圧計", "風速計", "照度計")
_TRAIL = re.compile(r"(\([^()]*\)|\[[^\[\]]*\])+$")


def _is_total(name: str) -> bool:
    """A total / subtotal row: a word ending in 計 (鉄筋計, コンクリート 計, 鉄筋計（SD345）, 合計 t …) unless 計 is not a
    total there (設計, 統計, 温度計 …); 合計・小計・総計 anywhere; or total/subtotal/sum/totals as English whole words."""
    n = unicodedata.normalize("NFKC", name or "")
    if any(w in n for w in ("合計", "小計", "総計")):
        return True
    for tok in re.split(r"[\s　,、・/]+", n):
        tok = _TRAIL.sub("", tok)                       # 鉄筋計(SD345) -> 鉄筋計
        if tok.endswith("計") and not tok.endswith(NOT_TOTAL_ENDINGS):
            return True
    return re.search(r"(^|[^a-z])(total|totals|subtotal|sum)($|[^a-z])", n.lower()) is not None


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
                if r["quantity"] < 0:
                    unused.append({"trace": r["trace"], "name": r["name"], "reason": "負の数量は読まない（差し引きにしない）"})
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
            if e["type"] in ("IFCREINFORCINGBAR", "IFCREINFORCINGMESH"):
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
        warnings += parsed.get("unit_notes", [])
        for e in parsed["elements"]:
            for pr in e.get("unit_problems", []):
                unused.append({"trace": pr.split("（")[0], "name": "%s %s" % (e["type"], e["name"]),
                               "reason": pr.split("（", 1)[1].rstrip("）") if "（" in pr else "使えない数量"})
    elif kind == "pdf":
        parsed = pdf.read(data, doc_id)
        if parsed.get("error"):
            raise ValueError(parsed["error"])
        if parsed["pages_without_text"]:
            warnings.append("文字の無いページ（スキャン画像）は読んでいない：%s" % parsed["pages_without_text"][:20])
        per_field = {}
        for c in parsed["candidates"]:
            if c["quantity"] < 0:
                unused.append({"trace": c["trace"], "name": c["name"], "reason": "負の数量は読まない"})
                continue
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
    to_t = {"t": 1.0, "kg": 0.001}
    by_field = {}
    for (fid, u), items in sums.items():
        by_field.setdefault(fid, {}).setdefault("mass" if u in to_t else u, []).extend((q, t, u) for q, t in items)
    for fid, dims in by_field.items():
        # one field holds one value: t and kg rows are added in t; rows of another dimension (m3 next to t) cannot be
        # added, so the dimension with more rows is proposed and the other rows are listed as not used
        dim = max(dims, key=lambda k: (len(dims[k]), k == "mass"))
        for other, rows_ in dims.items():
            if other != dim:
                for q, t, u in rows_:
                    unused.append({"trace": t, "name": FL.FIELDS[fid]["label"],
                                   "reason": "同じ材料の別の行と単位の次元が違う（%s と %s）ので合計できない：確認して入れる" % (u, dim)})
        items = dims[dim]
        if dim == "mass":
            total, u = sum(q * to_t[uu] for q, _, uu in items), "t"
        else:
            total, u = sum(q for q, _, _ in items), dim
        traces = [t for _, t, _ in items]
        detail = "%d 行の合計：%s%s" % (len(items), "、".join(traces[:12]), "…" if len(traces) > 12 else "")
        proposals.append(Value(fid, "from_drawing", round(total, 6), u, method="%s_quantity_sum" % kind, source_id=doc_id,
                               source_detail=detail, note="資料「%s」から。分類はキーワードによるので確認する" % doc_id))
    summ = {"n_rows": sum(len(s["rows"]) for s in parsed["sheets"])} if kind in ("csv", "xlsx") else \
        {"n_elements": len(parsed["elements"]), "schema": parsed["schema"]}
    if len(unused) > 2000:
        warnings.append("使わなかった行が多いので、最初の 2000 行だけを記録した（全部で %d 行）" % len(unused))
        unused = unused[:2000]
    return {"kind": kind, "sha256": sha, "parsed_summary": summ, "proposals": proposals, "unused": unused, "warnings": warnings}
