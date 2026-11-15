"""Uploaded documents (quantity tables, IFC, PDF) -> candidate values of the material fields.

A read number never becomes a value by itself: each mapped quantity is a candidate in state 図面から計算
(from_drawing) with the trace (sheet/row/column, IFC entity, page/line) in source_detail; the user accepts it.
Guards against double counting: total/subtotal rows are not added, the same file (SHA-256) is not read twice,
and rows that map to no field or whose unit the field cannot take are listed as not used.
"""
from __future__ import annotations

import base64
import bisect
import functools
import hashlib
import re
import unicodedata

from . import fields as FL
from .importers import ifc, pdf, tabular
from .provenance import Value

KEYWORDS = (  # (field, words): "re:" entries are regular expressions on the normalised name. The order does NOT decide:
    # the HEAD of the name does (see _field_for) — in a compound the material named last (エポキシ樹脂塗装鉄筋 is rebar,
    # ワイヤーメッシュ入りコンクリート concrete, FRP防水 a membrane, 防水モルタル mortar, 断熱複層ガラス glass), and of
    # several matches ending at the same place the longest (石膏ボード, ポリスチレンフォーム).
    ("m_insulation", ("グラスウール", "ガラスウール", "ロックウール", "glass wool", "glasswool", "rock wool", "rockwool",
                      "mineral wool", "foam glass", "ウレタンフォーム", "スタイロ", "ポリスチレンフォーム", "押出法", "ビーズ法", "保温板",
                      "フェノールフォーム", "polystyrene", "phenolic foam", "polyurethane foam", "pir board", "pur board",
                      "re:(?:^|[^a-z])(?:eps|xps)(?:[^a-z]|$)", "断熱材", "insulation", "断熱", "保温")),
    ("m_plastic", ("reinforced plastic", "繊維強化プラスチック", "re:(?:^|[^a-z])(?:frp|grp)(?:[^a-z]|$)", "塩ビ", "樹脂", "pvc",
                   "plastic", "ポリ", "人工木", "樹脂木")),
    ("m_board", ("石膏ボード", "せっこうボード", "gypsum board", "plasterboard", "cement board", "ケイ酸カルシウム板", "ボード",
                 "board", "gypsum")),                      # (押出成形セメント板 is masonry here)
    ("m_masonry", ("re:(?:^|[^a-z])alc(?:[^a-z]|$)", "ブロック", "れんが", "レンガ", "押出成形", "masonry", "brick")),
    ("m_rebar", ("鉄筋", "棒鋼", "異形棒", "鉄筋コンクリート用", "溶接金網", "ワイヤーメッシュ", "rebar", "reinforcement",
                 "reinforcing", "reinforcing steel", "deformed bar", "welded mesh", "wire mesh", "welded wire",
                 "re:(?:^|[^a-z])sd ?[2-6][0-9]{2}", "re:reinforced concrete bars?(?![a-z])")),
    ("m_concrete", ("コンクリート", "生コン", "concrete")),
    ("m_steel", ("鉄骨", "鋼材", "形鋼", "鋼管", "デッキプレート", "鋼製デッキ", "deck plate", "steel deck", "metal deck",
                 "structural steel", "steel")),
    ("m_timber", ("木材", "製材", "集成材", "合板", "clt", "timber", "wood", "lumber", "ウッド", "木製")),
    ("m_mortar", ("モルタル", "mortar", "plaster")),
    ("m_aluminium", ("アルミ", "alumin")),
    ("m_glass", ("ガラス", "glass")),
    ("m_membrane", ("防水", "membrane", "waterproof")),
    ("m_finish", ("仕上", "塗装", "クロス", "タイル", "床材", "finish", "tile", "paint", "flooring")),
)
_KW = tuple((fid, w, re.compile(w[3:]) if w.startswith("re:") else None) for fid, ws in KEYWORDS for w in ws)
MAX_NAME = 300                     # characters of a name that are classified (no material name is longer)
# where a name splits into parts: brackets, commas, semicolons and English prepositions. The material is the head of the
# FIRST part that names one ("Reinforcement, high yield steel bars" is rebar; "Supply and installation of plasterboard"
# is board; "Concrete for bar counter" is concrete; "鉄筋（コンクリート用）" is rebar)
_SEGSPLIT = re.compile(r"[,;，；、()（）\[\]［］{}｛｝【】〔〕「」『』<>＜＞]+|\s+(?:to|of|in|for|with|including|incl|"
                       r"excluding|excl|on|at|into|from|per)\s+")


def _last(w: str, rx, seg: str):
    """(start, end) of the last occurrence of a keyword in a part, or None (linear)."""
    if rx is None:
        k = seg.rfind(w)
        return None if k < 0 else (k, k + len(w))
    m = None
    for m in rx.finditer(seg):
        pass
    if m is None:
        return None
    a, b = m.span()
    if b > a and not seg[a].isalnum():                  # the leading "not a letter" of a word-bounded pattern
        a += 1
    if b > a and not seg[b - 1].isalnum():
        b -= 1
    return a, b


@functools.lru_cache(maxsize=8192)
def _head(text: str) -> tuple:
    """(field or None, part index, head start, head end, parts) of an NFKC-normalised name."""
    parts = tuple(_PUNCT.sub(" ", x).strip() for x in _SEGSPLIT.split(text.lower()[:MAX_NAME]))
    for i, seg in enumerate(parts):
        best = None
        for fid, w, rx in _KW:
            hit = _last(w, rx, seg)
            if hit and (best is None or (hit[1], hit[1] - hit[0]) > best[0]):
                best = ((hit[1], hit[1] - hit[0]), fid, hit[0], hit[1])
        if best:
            return best[1], i, best[2], best[3], parts
    return None, -1, 0, 0, parts


FOUNDATION_WORDS = ("基礎", "杭", "フーチング", "地中梁", "footing", "pile", "foundation")
TOTAL_WORDS = ("合計", "小計", "総計", "計", "total", "subtotal", "sum")
UNIT_ALIASES = {"m3": "m3", "m^3": "m3", "m**3": "m3", "立米": "m3", "立方メートル": "m3", "cum": "m3", "cu.m": "m3",
                "t": "t", "トン": "t", "ton": "t", "tonne": "t", "tonnes": "t", "tons": "t",
                "kg": "kg", "キログラム": "kg", "m2": "m2", "m^2": "m2", "m**2": "m2", "平米": "m2", "平方メートル": "m2",
                "sqm": "m2", "sq.m": "m2"}
QTY_UNITS = ("m3", "m2", "t", "kg")
# rows that repeat a material quantity as work (a 内訳書 lists 加工組立・運搬・打設 with the same quantity as the material)
WORK_WORDS = ("加工", "組立", "組み立て", "組立て", "運搬", "打設", "打込", "打ち込", "圧送", "ポンプ", "手間", "建方", "建て方",
              "製作", "養生", "締固め", "揚重", "労務", "工賃", "損料", "配筋", "型枠")
# a work word followed by one of these names a product or a price that includes the material (加工鉄筋, 加工済, 工場加工品,
# 製作金物, 型枠ブロック, 打設共, 建方込み): not a work row
PRODUCT_AFTER = ("済", "品", "材", "鉄筋", "鋼", "木", "板", "金物", "ボード", "ガラス", "ブロック", "共", "込", "含", "とも")
WORK_WORDS_EN = ("placing", "placement", "pumping", "pump", "pour", "pouring", "fixing", "erection", "erect", "erecting",
                 "fabrication", "fabricate", "fabricating", "cutting", "bending", "tying", "labour", "labor", "transport",
                 "delivery", "formwork", "curing", "installation", "hoisting")
# a row that says it supplies the material is a material row even when it also names the work (材工共, supply and erect)
SUPPLY_JA = ("材工共", "材工とも", "材工込", "材料共", "材料とも", "材料込", "材共", "材工一式")
SUPPLY_EN = ("supply", "supplying", "supplied", "provide", "providing", "furnish", "furnishing", "furnished")
INCLUSIVE_EN = ("including", "incl", "inclusive", "includes")
_PUNCT = re.compile(r"[\s,，、。・/／_\-‐－–—:：;；()（）\[\]［］{}｛｝【】「」『』<>＜＞]+")


def normalise_name(name: str) -> str:
    """NFKC (full-width letters and digits, ㎥ …), lower case, punctuation as single spaces; at most MAX_NAME characters
    (cut before and after NFKC, which can lengthen a string)."""
    n = unicodedata.normalize("NFKC", (name or "")[:MAX_NAME]).lower()[:MAX_NAME]
    return _PUNCT.sub(" ", n).strip()


def _prep(s: str) -> str:
    """NFKC once, cut before and after (the checks then work on at most MAX_NAME characters)."""
    return unicodedata.normalize("NFKC", (s or "")[:MAX_NAME])[:MAX_NAME]


def _classify(text: str, division: str = "") -> str | None:
    """The field of an NFKC-normalised name (the head of its first part that names a material)."""
    fid = _head(text)[0]
    if fid == "m_concrete":
        low = normalise_name(division) + " " + " ".join(_head(text)[4])
        if any(w in low for w in FOUNDATION_WORDS):
            return "m_concrete_fdn"
    return fid


def _field_for(name: str, division: str = "") -> str | None:
    return _classify(_prep(name), _prep(division))


NOT_TOTAL_ENDINGS = ("設計", "統計", "会計", "時計", "家計", "余計", "生計", "温度計", "湿度計", "圧力計", "流量計", "水位計",
                     "電力計", "電流計", "電圧計", "風速計", "照度計")


_SPLIT = re.compile(r"[\s　,、・/／:：;；。.．*＊=＝~〜()（）\[\]［］{}｛｝【】「」『』〔〕《》〈〉<>＜＞\-‐－–—]+")


def _words(n: str) -> list:
    """Words of a name split at spaces, punctuation and every kind of bracket (linear; no backtracking)."""
    return [w for w in _SPLIT.split(n) if w]


@functools.lru_cache(maxsize=8192)
def _total(n: str) -> bool:
    if any(w in n for w in ("合計", "小計", "総計")):
        return True
    if any(w.endswith("計") and not w.endswith(NOT_TOTAL_ENDINGS) for w in _words(n)):
        return True
    return re.search(r"(?:^|[^a-z])(?:total|totals|subtotal|sum)(?:$|[^a-z])", n.lower()) is not None


def _is_total(name: str) -> bool:
    """A total / subtotal row: a word ending in 計 (鉄筋計, コンクリート 計, （鉄筋 計）, 【鉄骨 計】, 鉄筋計（SD345）t,
    鉄筋計:SD345, 合　計 …) unless 計 is not a total there (設計, 統計, 温度計 …); 合計・小計・総計 anywhere; or total /
    subtotal / sum / totals as English whole words."""
    return _total(_prep(name))


MAX_ROWS_CLASSIFIED = 20_000          # quantity rows classified per document (a real bill of quantities is far smaller)
MAX_PREP_CHARS = 3_000_000            # characters normalised (NFKC) per document: distinct texts only, each once


@functools.lru_cache(maxsize=8192)
def _work(n: str) -> bool:
    fid, hs, a, b, parts = _head(n)
    toks = normalise_name(n).split()              # the whole name: "including" is where the parts split
    compact = re.sub(r"\s+", "", n)
    if any(w in compact for w in SUPPLY_JA) or any(t in SUPPLY_EN for t in toks):
        return False
    for i, t in enumerate(toks):
        if t in WORK_WORDS_EN:
            # "concrete including placing and compacting" is the material with its placing included
            return not any(x in INCLUSIVE_EN for x in toks[:i])
    for i, seg in enumerate(parts):
        for w in WORK_WORDS:
            k = seg.find(w)
            while k >= 0:
                e = k + len(w)
                in_head = i == hs and k < b and e > a
                # a work word inside the head's own word, before the material, qualifies it (加工鉄筋, 型枠ブロック)
                modifier = i == hs and e <= a and seg.rfind(" ", 0, a) < k
                if not in_head and not modifier and not seg[e:].startswith(PRODUCT_AFTER):
                    return True
                k = seg.find(w, k + 1)
    return False


def _is_work(name: str) -> bool:
    """A labour / process row (鉄筋加工組立, コンクリート打設手間, 鉄骨建て方, 鉄筋｜加工組立, Rebar fixing …): it repeats
    the material quantity. Not work: a work word that qualifies the product (加工鉄筋, プレカット加工済, 工場加工品,
    型枠ブロック), a price that includes the material (材工共, 打設共, supply and erect, supply and pour), "concrete
    including placing"."""
    return _work(_prep(name))


# words that start with うち but are not "of which": 打ち放し (うちっぱなし), 内断熱 (うちだんねつ), 内張り / 内貼り
_UCHI_WORDS = ("うちっぱなし", "うちはなし", "うち放し", "うち断熱", "うちだんねつ", "うち張", "うち貼", "うちばり")
AGAIN_JA = ("再掲", "別掲", "上記に含", "前記に含", "上記の内", "上記のうち", "前記の内", "前記のうち", "(再)", "内数")
AGAIN_EN = ("of which", "included above", "already included", "included in item", "included in the item",
            "included elsewhere", "incl. above", "incl above", "measured elsewhere", "see item")
DEDUCT_JA = ("控除", "差引", "差し引", "減額", "発生材")
DEDUCT_EN = ("deduct", "deducted", "deduction", "deductions", "credit", "credits")


@functools.lru_cache(maxsize=8192)
def _again(n: str) -> bool:
    low = n.lower()
    compact = re.sub(r"\s+", "", n)               # 再　掲・う　ち (space-justified) are the same words
    words = _words(n) + _words(compact)
    uchi = any(w.startswith("うち") and not w.startswith(_UCHI_WORDS) for w in words)
    return bool(any(w in compact for w in AGAIN_JA) or uchi
                or any(w in ("内", "内訳") or w.startswith("内訳") for w in words)
                or any(w in low for w in AGAIN_EN))


def _not_added(*texts: str) -> str | None:
    """A row that repeats or breaks down quantities listed elsewhere (再掲, 別掲, 内数, うち…, 内訳…, (内), (再), 上記に含む,
    "of which", "included above" …): not added. Looked for in the name, the specification and the division, at the
    start of any word (after any bracket or punctuation, also when the word is spaced out: 再　掲); うちっぱなし (打ち放し)
    or うち断熱 (内断熱) are not breakdowns."""
    if any(_again(_prep(t)) for t in texts):
        return "再掲・内数（うち・内訳）の行は足さない（ほかの行に含まれている。二重計上を防ぐ）"
    return None


@functools.lru_cache(maxsize=8192)
def _deduct(n: str) -> bool:
    toks = normalise_name(n).split()
    compact = re.sub(r"\s+", "", n)
    return any(w in compact for w in DEDUCT_JA) or any(t in DEDUCT_EN for t in toks) or (toks[:1] == ["less"])


def _is_deduction(*texts: str) -> bool:
    """A deduction (スクラップ控除, 発生材, 差引, deduct, credit, "less …"), often written with a positive quantity and a
    negative price: never added and never subtracted silently."""
    return any(_deduct(_prep(t)) for t in texts)


def _unit(u: str) -> str | None:
    """ｍ３, ㎥, m³, Ｍ３ … are m3 (NFKC), likewise m2, t, kg."""
    k = unicodedata.normalize("NFKC", (u or "")[:40]).strip().lower().replace(" ", "")
    return UNIT_ALIASES.get(k)


class _Budget(Exception):
    pass


class _Prep:
    """NFKC of each distinct text once per document, within a character budget (an upload must not hold the worker)."""

    def __init__(self, budget: int = MAX_PREP_CHARS):
        self.cache, self.left = {}, budget

    def __call__(self, s) -> str:
        s = (s or "")[:MAX_NAME]
        got = self.cache.get(s)
        if got is None:
            self.left -= len(s)
            if self.left < 0:
                raise _Budget()
            got = self.cache[s] = unicodedata.normalize("NFKC", s)[:MAX_NAME]
        return got


MAX_FOLLOW_STEPS = 200_000            # cells visited per document while following what quantity formulas reach
MAX_FOLLOW_DEPTH = 16


class _Cells:
    """What a quantity formula reaches, followed through the formulas of every read sheet (helper cells, other columns,
    other sheets, defined names). A quantity is a copy when it reaches another MATERIAL ROW of a read quantity sheet —
    any of its columns: a detail row, a subtotal (typed or a SUM), a 再掲, a work row, an allowance row. Rows that name no
    material (延床面積, 比重, 単価) and cells of the quantity's own row (per-floor columns, a calculation column) are not."""

    def __init__(self, parsed: dict):
        self.cells = parsed.get("cells") or {}
        self.names = parsed.get("names") or {}
        self.disp = parsed.get("sheet_names") or {}
        self.frows = {sh: sorted(rows) for sh, rows in self.cells.items()}
        self.material = {}
        self.left = MAX_FOLLOW_STEPS

    def copy_of(self, sh: str, row: int, col: int, qf):
        """None, ("copy", sheet, row) or ("unchecked", reason)."""
        stack, seen = [(sh, qf, 0)], {(sh, row, col)}
        while stack:
            s_, f, depth = stack.pop()
            why, refs = tabular.formula_refs(f, {"sheet": self.disp.get(s_, s_), "names": self.names})
            if why:
                return ("unchecked", why if s_ == sh and depth == 0 else "参照先の数式（%s）：%s" % (self.disp.get(s_, s_), why))
            for rs, c1, c2, r1, r2 in refs:
                t = s_ if rs is None else rs
                lo = 0 if r1 is None else r1
                hi = tabular.MAX_ROW_NUMBER if r2 is None else r2
                mrows = self.material.get(t, ())
                k = bisect.bisect_left(mrows, lo)
                while k < len(mrows) and mrows[k] <= hi:
                    if not (t == sh and mrows[k] == row):
                        return ("copy", t, mrows[k])
                    k += 1
                frs = self.frows.get(t, ())
                k = bisect.bisect_left(frs, lo)
                while k < len(frs) and frs[k] <= hi:
                    self.left -= 1
                    if self.left < 0:
                        return ("unchecked", "数式の参照が多すぎて確かめられない。必要なら手で入れる")
                    for ci, ff in self.cells[t][frs[k]].items():
                        key = (t, frs[k], ci)
                        if c1 <= ci <= c2 and key not in seen:
                            if depth >= MAX_FOLLOW_DEPTH:
                                return ("unchecked", "数式の参照が深すぎて確かめられない（%d 段まで）。必要なら手で入れる" % MAX_FOLLOW_DEPTH)
                            seen.add(key)
                            stack.append((t, ff, depth + 1))
                    k += 1
        return None


def _row_class(prep: _Prep, r: dict) -> dict:
    name, spec, div = prep(r.get("name")), prep(r.get("specification")), prep(r.get("division"))
    text = name + " ; " + spec if spec else name
    fid = _classify(text, div)
    total = _total(name) or (_total(spec) if spec else False)
    again = _again(name) or (_again(spec) if spec else False) or (_again(div) if div else False)
    deduct = _deduct(name) or (_deduct(spec) if spec else False)
    work = _work(text)
    return {"name": name, "fid": fid, "u": _unit(r.get("unit")), "total": total, "again": again, "deduct": deduct,
            "work": work}


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


def sh_qcol(parsed: dict, shf: str) -> int:
    for sh in parsed["sheets"]:
        if str(sh["sheet"]).casefold() == shf:
            return sh.get("qcol") or 0
    return 0


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
        prep, cells = _Prep(), _Cells(parsed)
        classed = []                       # (sheet casefolded, row, class, candidate?) in reading order
        n_classified, stopped = 0, None
        for sh in parsed["sheets"]:
            if sh.get("error"):
                warnings.append("%s：%s" % (sh["sheet"], sh["error"]))
            shf = str(sh["sheet"]).casefold()
            mats, marks = [], []
            for r, cand in [(x, False) for x in sh.get("skipped", [])] + [(x, True) for x in sh["rows"]]:
                if not cand:
                    unused.append({"trace": r["trace"], "name": r["name"][:80], "reason": r["reason"]})
                if stopped:
                    continue
                n_classified += 1
                if n_classified > MAX_ROWS_CLASSIFIED:
                    stopped = "数量の行が多すぎるので、最初の %d 行だけを読んだ（残りは読んでいない）" % MAX_ROWS_CLASSIFIED
                    continue
                try:
                    c = _row_class(prep, r)
                except _Budget:
                    stopped = "文字が多すぎるので、最初の %d 行だけを読んだ（残りは読んでいない）" % (n_classified - 1)
                    continue
                # a material row (also when this row itself is not added: a SUM subtotal, a non-numeric quantity …):
                # a quantity elsewhere that reaches it copies it. Total / 再掲 / work / deduction rows count only on a
                # sheet that lists materials (延床面積 合計 on a dimensions sheet is not a material quantity)
                if c["fid"] and c["u"] in QTY_UNITS:
                    mats.append(r["row"])
                elif c["total"] or c["again"] or c["work"] or c["deduct"]:
                    marks.append(r["row"])
                if cand:
                    classed.append((shf, r, c))
            if mats:
                cells.material[shf] = sorted(set(mats + marks))
        if stopped:
            warnings.append(stopped)
        for shf, r, c in classed:
            name = c["name"][:80]
            why = None
            if c["total"]:
                why = "合計・小計の行は足さない（二重計上を防ぐ）"
            elif c["again"]:
                why = "再掲・内数（うち・内訳）の行は足さない（ほかの行に含まれている。二重計上を防ぐ）"
            elif c["deduct"]:
                why = "控除・差し引き（スクラップ・発生材など）の行は足さない（差し引きにもしない。必要なら手で直す）"
            elif c["work"]:
                why = "作業の行（加工・運搬・打設など。材料の量を繰り返す）は足さない（二重計上を防ぐ）"
            elif r["quantity"] < 0:
                why = "負の数量は読まない（差し引きにしない）"
            elif c["fid"] is None:
                why = "どの材料の欄にも当てはまらない"
            elif c["u"] not in FL.FIELDS[c["fid"]]["units"]:
                f_ = FL.FIELDS[c["fid"]]
                why = "単位 %r は「%s」に使えない（%s）" % (r["unit"], f_["label"], "・".join(f_["units"]))
            elif r.get("qf"):
                got = cells.copy_of(shf, r["row"], sh_qcol(parsed, shf), r["qf"])
                if got and got[0] == "copy":
                    _k, tsh, trow = got
                    if tsh == shf:
                        why = "同じシートのほかの材料の行（%d 行目）の値から計算した数量（合計・再掲・割増のおそれ）は足さない。必要なら手で入れる" % trow
                    else:
                        why = "別のシート（%s）の材料の行（%d 行目）の値を参照した数量は足さない（そのシートも読んでいるので二重計上になる）" \
                              % (parsed.get("sheet_names", {}).get(tsh, tsh), trow)
                elif got:
                    why = got[1]
            if why:
                unused.append({"trace": r["trace"], "name": name, "reason": why})
                continue
            sums.setdefault((c["fid"], c["u"]), []).append((r["quantity"], r["trace"]))
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
            if _is_deduction(c["name"]):
                unused.append({"trace": c["trace"], "name": c["name"][:80], "reason": "控除・差し引きの行は候補にしない"})
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
