"""Uploaded documents (quantity tables, IFC, PDF) -> candidate values of the material fields.

A read number never becomes a value by itself: each mapped quantity is a candidate in state 図面から計算
(from_drawing) with the trace (sheet/row/column, IFC entity, page/line) in source_detail; the user accepts it.
Guards against double counting: total/subtotal rows are not added, the same file (SHA-256) is not read twice,
and rows that map to no field or whose unit the field cannot take are listed as not used.
"""
from __future__ import annotations

import base64
import bisect
import hashlib
import re
import unicodedata

from . import fields as FL
from .importers import ifc, pdf, tabular
from .provenance import Value

KEYWORDS = [  # (field, words) — first match wins; "re:" entries are regular expressions on the normalised name.
    # Specific PRODUCT words come first ("glass wool insulation" is insulation, "gypsum board" a board, "fibre reinforced
    # plastic" a plastic); then the materials; the GENERIC modifiers (断熱 / 防水 / ボード …) only after the materials, so
    # that 断熱複層ガラス is glass, 断熱アルミサッシ aluminium and 防水コンクリート concrete.
    ("m_insulation", ("グラスウール", "ロックウール", "glass wool", "glasswool", "rock wool", "rockwool", "mineral wool",
                      "foam glass", "ウレタンフォーム", "スタイロ", "ポリスチレンフォーム", "押出法", "ビーズ法", "保温板",
                      "フェノールフォーム", "polystyrene", "phenolic foam", "polyurethane foam", "pir board", "pur board",
                      "re:(^|[^a-z])(eps|xps)([^a-z]|$)", "断熱材", "insulation")),
    ("m_plastic", ("reinforced plastic", "繊維強化プラスチック", "re:(^|[^a-z])(frp|grp)([^a-z]|$)")),
    ("m_board", ("石膏ボード", "せっこうボード", "gypsum board", "plasterboard", "cement board", "ケイ酸カルシウム板")),   # (押出成形セメント板 is masonry here)
    ("m_masonry", ("re:(^|[^a-z])alc([^a-z]|$)", "ブロック", "れんが", "レンガ", "押出成形", "masonry", "brick")),
    # rebar: decided by _is_rebar() below (a reinforced-concrete name is concrete; product words make it rebar)
    ("m_rebar", ()),
    ("m_concrete", ("コンクリート", "生コン", "concrete")),
    ("m_steel", ("鉄骨", "鋼材", "形鋼", "鋼管", "デッキ", "structural steel", "steel")),
    ("m_timber", ("木材", "製材", "集成材", "合板", "clt", "timber", "wood", "lumber")),
    ("m_mortar", ("モルタル", "mortar", "plaster")),
    ("m_aluminium", ("アルミ", "alumin")),
    ("m_glass", ("ガラス", "glass")),
    ("m_insulation", ("断熱", "保温")),
    ("m_membrane", ("防水", "membrane", "waterproof")),
    ("m_board", ("ボード", "board", "gypsum")),
    ("m_plastic", ("塩ビ", "樹脂", "pvc", "plastic", "ポリ")),
    ("m_finish", ("仕上", "塗装", "クロス", "タイル", "床材", "finish", "tile", "paint", "flooring")),
]
# Rebar or reinforced concrete? Decided by words, never by a backtracking pattern (names come from uploaded files):
# - a reinforcement PRODUCT word makes it rebar even when concrete is named: 棒鋼, 異形鉄筋, 鉄筋コンクリート用 (JIS bar
#   name), コンクリート用…鉄筋, 溶接金網, ワイヤーメッシュ, rebar, SD295…SD685, "reinforcing steel / bar / mesh",
#   "reinforcement for concrete", "welded / wire mesh", "deformed bar", and "bar(s)" next to a reinforcement or concrete
#   word ("reinforced concrete bars");
# - otherwise 鉄筋 / reinforc… is rebar only when no concrete word is in the name ("steel reinforced concrete" = SRC
#   concrete, "Concrete, Reinforced" = concrete).
REBAR_SUBSTR = ("棒鋼", "異形鉄筋", "異形棒", "鉄筋コンクリート用", "溶接金網", "ワイヤーメッシュ", "rebar")
REBAR_GENERIC = ("鉄筋", "reinforc")
CONCRETE_WORDS = ("コンクリート", "生コン", "concrete")
# "reinforced" with another material is that material ("fibre reinforced cement board", "glass fibre reinforced plastic")
OTHER_REINFORCED = ("board", "plastic", "cement", "gypsum", "glass", "fibre", "fiber", "polymer", "resin", "frp", "grp",
                    "ボード", "樹脂", "ガラス", "セメント", "繊維")
_SD = re.compile(r"(?:^|[^a-z])sd ?[2-6][0-9]{2}")
MAX_NAME = 300                     # characters of a name that are classified (no material name is longer)


def _is_rebar(low: str) -> bool:
    toks = low.split()
    concrete = any(w in low for w in CONCRETE_WORDS)
    generic = any(w in low for w in REBAR_GENERIC)
    if any(w in low for w in REBAR_SUBSTR) or _SD.search(low):
        return True
    k = low.find("コンクリート用")
    if k >= 0 and "鉄筋" in low[k:]:
        return True
    for z, a, b, c in zip([""] + toks, toks, toks[1:] + [""], toks[2:] + ["", ""]):
        if a.startswith("reinforc") and (b in ("steel", "bar", "bars", "mesh") or (b == "for" and c == "concrete")):
            return True
        if (a == "deformed" and b in ("bar", "bars")) or (a in ("welded", "wire") and b in ("mesh", "wire")):
            return True
        # "bar" right after a reinforcement word, or after "reinforced concrete" ("reinforced concrete bars"); not a
        # "precast concrete bar", a "concrete bar counter" or "bar chairs"
        if b in ("bar", "bars") and c not in ("chair", "chairs", "counter") and \
                (a.startswith("reinforc") or a in ("rebar", "鉄筋") or (a == "concrete" and z.startswith("reinforc"))):
            return True
    if generic and any(w in low for w in OTHER_REINFORCED):
        return False
    return generic and not concrete


FOUNDATION_WORDS = ("基礎", "杭", "フーチング", "地中梁", "footing", "pile", "foundation")
TOTAL_WORDS = ("合計", "小計", "総計", "計", "total", "subtotal", "sum")
UNIT_ALIASES = {"m3": "m3", "m^3": "m3", "m**3": "m3", "立米": "m3", "立方メートル": "m3", "cum": "m3", "cu.m": "m3",
                "t": "t", "トン": "t", "ton": "t", "tonne": "t", "tonnes": "t", "tons": "t",
                "kg": "kg", "キログラム": "kg", "m2": "m2", "m^2": "m2", "m**2": "m2", "平米": "m2", "平方メートル": "m2",
                "sqm": "m2", "sq.m": "m2"}
# rows that repeat a material quantity as work (a 内訳書 lists 加工組立・運搬・打設 with the same quantity as the material)
WORK_WORDS = ("加工", "組立", "組み立て", "組立て", "運搬", "打設", "打込", "打ち込", "圧送", "ポンプ", "手間", "建方", "建て方",
              "製作", "養生", "締固め", "揚重", "労務", "工賃", "損料", "配筋", "型枠")
# a work word followed by one of these names a product (加工鉄筋, 加工済, 工場加工品, 製作金物): not a work row
PRODUCT_AFTER = ("済", "品", "材", "鉄筋", "鋼", "木", "板", "金物", "ボード", "ガラス")
WORK_WORDS_EN = ("placing", "placement", "pumping", "pump", "pour", "pouring", "fixing", "erection", "erect", "erecting",
                 "fabrication", "fabricate", "fabricating", "cutting", "bending", "tying", "labour", "labor", "transport",
                 "delivery", "formwork", "curing", "installation", "hoisting")
_PUNCT = re.compile(r"[\s,，、。・/／_\-‐－–—:：;；()（）\[\]［］{}｛｝【】「」『』<>＜＞]+")


def normalise_name(name: str) -> str:
    """NFKC (full-width letters and digits, ㎥ …), lower case, punctuation as single spaces; at most MAX_NAME characters
    (cut before and after NFKC, which can lengthen a string)."""
    n = unicodedata.normalize("NFKC", (name or "")[:MAX_NAME]).lower()[:MAX_NAME]
    return _PUNCT.sub(" ", n).strip()


def _hit(words, low: str) -> bool:
    return any((re.search(w[3:], low) is not None) if w.startswith("re:") else (w in low) for w in words)


def _field_for(name: str, division: str = "") -> str | None:
    low = normalise_name(name)
    div = normalise_name(division)
    for fid, words in KEYWORDS:
        if fid == "m_rebar":
            if _is_rebar(low):
                return fid
            continue
        if _hit(words, low):
            if fid == "m_concrete" and any(w in div + " " + low for w in FOUNDATION_WORDS):
                return "m_concrete_fdn"
            return fid
    return None


NOT_TOTAL_ENDINGS = ("設計", "統計", "会計", "時計", "家計", "余計", "生計", "温度計", "湿度計", "圧力計", "流量計", "水位計",
                     "電力計", "電流計", "電圧計", "風速計", "照度計")


_SPLIT = re.compile(r"[\s　,、・/／:：;；。.．*＊=＝~〜()（）\[\]［］{}｛｝【】「」『』〔〕《》〈〉<>＜＞\-‐－–—]+")


def _words(n: str) -> list:
    """Words of a name split at spaces, punctuation and every kind of bracket (linear; no backtracking)."""
    return [w for w in _SPLIT.split(n) if w]


def _is_total(name: str) -> bool:
    """A total / subtotal row: a word ending in 計 (鉄筋計, コンクリート 計, （鉄筋 計）, 【鉄骨 計】, 鉄筋計（SD345）t,
    鉄筋計:SD345 …) unless 計 is not a total there (設計, 統計, 温度計 …); 合計・小計・総計 anywhere; or total / subtotal /
    sum / totals as English whole words."""
    n = unicodedata.normalize("NFKC", (name or "")[:MAX_NAME])[:MAX_NAME]
    if any(w in n for w in ("合計", "小計", "総計")):
        return True
    if any(w.endswith("計") and not w.endswith(NOT_TOTAL_ENDINGS) for w in _words(n)):
        return True
    return re.search(r"(?:^|[^a-z])(?:total|totals|subtotal|sum)(?:$|[^a-z])", n.lower()) is not None


MAX_ROWS_CLASSIFIED = 20_000          # quantity rows classified per document (a real bill of quantities is far smaller)


def _prep(s: str) -> str:
    """NFKC once, cut before and after (the checks then work on at most MAX_NAME characters)."""
    return unicodedata.normalize("NFKC", (s or "")[:MAX_NAME])[:MAX_NAME]


def _is_work(name: str) -> bool:
    """A labour / process row (鉄筋加工組立, コンクリート打設手間, 鉄骨建て方, Rebar fixing …): it repeats the material
    quantity. A work word that qualifies a product (加工鉄筋, プレカット加工済, 工場加工品) does not make a work row."""
    n = unicodedata.normalize("NFKC", (name or "")[:MAX_NAME])[:MAX_NAME]
    for w in WORK_WORDS:
        k = n.find(w)
        while k >= 0:
            if not n[k + len(w):].startswith(PRODUCT_AFTER):
                return True
            k = n.find(w, k + 1)
    return any(w in WORK_WORDS_EN for w in _words(n.lower()))


# words that start with うち but are not "of which": 打ち放し (うちっぱなし), 内断熱 (うちだんねつ), 内張り / 内貼り
_UCHI_WORDS = ("うちっぱなし", "うちはなし", "うち放し", "うち断熱", "うちだんねつ", "うち張", "うち貼", "うちばり")


def _not_added(*texts: str) -> str | None:
    """A row that repeats or breaks down quantities listed elsewhere (再掲, 内数, うち…, 内訳…, (内), "of which"): not
    added. Looked for in the name, the specification and the division, at the start of any word (after any bracket or
    punctuation); うちっぱなし (打ち放し) or うち断熱 (内断熱) are not breakdowns."""
    for name in texts:
        n = unicodedata.normalize("NFKC", (name or "")[:MAX_NAME])[:MAX_NAME]
        low = n.lower()
        words = _words(n)
        uchi = any(w.startswith("うち") and not w.startswith(_UCHI_WORDS) for w in words)
        if "再掲" in n or uchi or any(w in ("内数", "内", "内訳") or w.startswith("内訳") for w in words) \
                or "of which" in low or "included above" in low or "already included" in low:
            return "再掲・内数（うち・内訳）の行は足さない（ほかの行に含まれている。二重計上を防ぐ）"
    return None


def _unit(u: str) -> str | None:
    """ｍ３, ㎥, m³, Ｍ３ … are m3 (NFKC), likewise m2, t, kg."""
    k = unicodedata.normalize("NFKC", (u or "")[:40]).strip().lower().replace(" ", "")
    return UNIT_ALIASES.get(k)


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
        warnings += parsed.get("warnings", [])
        n_classified = 0
        material_rows = {}                 # (sheet, row) -> quantity column, for the rows that are material quantities
        later = []                         # rows that reference another sheet: judged after every sheet is classified
        for sh in parsed["sheets"]:
            if sh.get("error"):
                warnings.append("%s：%s" % (sh["sheet"], sh["error"]))
            for s in sh.get("skipped", []):
                unused.append({"trace": s["trace"], "name": s["name"][:80], "reason": s["reason"]})
            for r in sh["rows"]:
                n_classified += 1
                if n_classified > MAX_ROWS_CLASSIFIED:
                    if n_classified == MAX_ROWS_CLASSIFIED + 1:
                        warnings.append("数量の行が多すぎるので、最初の %d 行だけを読んだ（残りは読んでいない）" % MAX_ROWS_CLASSIFIED)
                    continue
                # each text normalised once (NFKC can lengthen a string many times): the checks below work on these
                r = dict(r, name=_prep(r["name"]), specification=_prep(r.get("specification", "")),
                         division=_prep(r.get("division", "")))
                # a row of material quantities (also a subtotal, a 再掲 or a work row of them): a formula on another
                # sheet that references it copies a quantity; rows that name no material (延床面積, 比重 …) are not
                key = (str(sh["sheet"]).casefold(), r["row"])
                material_rows[key] = sh.get("qcol")
                if _is_total(r["name"]):
                    unused.append({"trace": r["trace"], "name": r["name"][:80], "reason": "合計・小計の行は足さない（二重計上を防ぐ）"})
                    continue
                why = _not_added(r["name"], r.get("specification", ""), r.get("division", ""))
                if why:
                    unused.append({"trace": r["trace"], "name": r["name"][:80], "reason": why})
                    continue
                if _is_work(r["name"]):
                    unused.append({"trace": r["trace"], "name": r["name"][:80],
                                   "reason": "作業の行（加工・運搬・打設など。材料の量を繰り返す）は足さない（二重計上を防ぐ）"})
                    continue
                if r["quantity"] < 0:
                    unused.append({"trace": r["trace"], "name": r["name"][:80], "reason": "負の数量は読まない（差し引きにしない）"})
                    continue
                fid = _field_for(r["name"] + " " + r.get("specification", ""), r.get("division", ""))
                u = _unit(r["unit"])
                if fid is None:
                    material_rows.pop(key, None)
                    unused.append({"trace": r["trace"], "name": r["name"][:80], "reason": "どの材料の欄にも当てはまらない"})
                    continue
                if u not in FL.FIELDS[fid]["units"]:
                    if u is None:                  # not a quantity unit at all (比重 t/m3, 単価 …): not a material row
                        material_rows.pop(key, None)
                    unused.append({"trace": r["trace"], "name": r["name"][:80],
                                   "reason": "単位 %r は「%s」に使えない（%s）" % (r["unit"], FL.FIELDS[fid]["label"], "・".join(FL.FIELDS[fid]["units"]))})
                    continue
                if r.get("xrefs"):
                    later.append((r, fid, u))
                    continue
                sums.setdefault((fid, u), []).append((r["quantity"], r["trace"]))
        by_sheet = {}                      # sheet -> (quantity column, sorted material rows)
        for (msh, mrow), qcol in material_rows.items():
            by_sheet.setdefault(msh, (qcol, []))[1].append(mrow)
        for _q, rws in by_sheet.values():
            rws.sort()
        for r, fid, u in later:
            hit = None
            for shf, lo, hi, rlo, rhi in r["xrefs"]:
                qcol, rws = by_sheet.get(shf, (None, []))
                if qcol is None or not lo <= qcol <= hi:
                    continue
                k = bisect.bisect_left(rws, rlo if rlo is not None else -1)
                if k < len(rws) and (rhi is None or rws[k] <= rhi):
                    hit = shf
                    break
            if hit:
                unused.append({"trace": r["trace"], "name": r["name"][:80],
                               "reason": "別のシート（%s）の材料の数量を参照した行は足さない（そのシートも読んでいるので二重計上になる）" % hit})
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
        for c in parsed.get("refused", []):
            unused.append({"trace": c["trace"], "name": c["name"][:80], "reason": c["reason"]})
        for c in parsed["candidates"]:
            if c["quantity"] < 0:
                unused.append({"trace": c["trace"], "name": c["name"][:80], "reason": "負の数量は読まない"})
                continue
            fid = _field_for(c["name"])
            u = _unit(c["unit"])
            if fid is None or u not in FL.FIELDS.get(fid, {}).get("units", []):
                unused.append({"trace": c["trace"], "name": c["name"][:80], "reason": "材料の欄・単位に当てはまらない"})
                continue
            if _is_total(c["name"]):
                unused.append({"trace": c["trace"], "name": c["name"][:80], "reason": "合計の行は候補にしない"})
                continue
            if _not_added(c["name"]):
                unused.append({"trace": c["trace"], "name": c["name"][:80], "reason": _not_added(c["name"])})
                continue
            if _is_work(c["name"]):
                unused.append({"trace": c["trace"], "name": c["name"][:80], "reason": "作業の行（材料の量を繰り返す）は候補にしない"})
                continue
            per_field.setdefault(fid, []).append((c, u))
        proposals = []
        for fid, cs in per_field.items():
            for c, u in cs[5:]:          # said, not silently dropped
                unused.append({"trace": c["trace"], "name": c["name"][:80],
                               "reason": "同じ材料の PDF の候補は 5 行まで（残りは原本で確かめて手で入れる）"})
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
