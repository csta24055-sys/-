"""Uploaded documents (quantity tables, IFC, PDF) -> candidate values of the material fields.

A read number never becomes a value by itself: each mapped quantity is a candidate in state 図面から計算
(from_drawing) with the trace (sheet/row/column, IFC entity, page/line) in source_detail; the user accepts it.
Every candidate of a quantity table carries its evidence: the rows it added up, and the rows that name the same
material but were not added, each with its reason, so that a wrong guess is visible before it is accepted.
Guards against double counting: total/subtotal rows are not added, the same file (SHA-256) is not read twice,
a quantity whose formula reaches another material row's quantity is not added, and rows that map to no field or whose
unit the field cannot take are listed as not used.
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
    # the HEAD of the name does (see _head) — in a compound the material named last (エポキシ樹脂塗装鉄筋 is rebar,
    # ワイヤーメッシュ入りコンクリート concrete, FRP防水 a membrane, 防水モルタル mortar, 断熱複層ガラス glass), and of
    # several matches ending at the same place the longest (石膏ボード, ポリスチレンフォーム, reinforcement steel). A form
    # word (ボード, board) after another material names that material's form (グラスウールボード is insulation); 断熱
    # before a product (サッシ, ドア, パネル) is an adjective; a material followed by 下・上・裏・用・面 names a place or a
    # purpose (砂利地業（土間コンクリート下）is not concrete).
    ("m_insulation", ("グラスウール", "ガラスウール", "ロックウール", "glass wool", "glasswool", "rock wool", "rockwool",
                      "mineral wool", "foam glass", "glass fibre", "glass fiber", "fiberglass", "fibreglass", "ウレタンフォーム", "スタイロ", "ポリスチレンフォーム", "押出法", "ビーズ法", "保温板",
                      "フェノールフォーム", "polystyrene", "phenolic foam", "polyurethane foam", "pir board", "pur board",
                      "re:(?:^|[^a-z])(?:eps|xps)(?:[^a-z]|$)", "断熱材", "insulation", "断熱", "保温")),
    ("m_plastic", ("reinforced plastic", "繊維強化プラスチック", "re:(?:^|[^a-z])(?:frp|grp)(?:[^a-z]|$)", "塩ビ", "樹脂", "pvc",
                   "plastic", "ポリ", "人工木", "樹脂木")),
    ("m_board", ("石膏ボード", "せっこうボード", "gypsum board", "plasterboard", "cement board", "ケイ酸カルシウム板", "ボード",
                 "board", "gypsum")),                      # (押出成形セメント板 is masonry here)
    ("m_masonry", ("re:(?:^|[^a-z])alc(?:[^a-z]|$)", "ブロック", "れんが", "レンガ", "押出成形", "masonry", "brick",
                   "re:(?:^|[^a-z])block(?:s|work)?(?![a-z])")),
    ("m_rebar", ("鉄筋", "棒鋼", "異形棒", "鉄筋コンクリート用", "溶接金網", "ワイヤーメッシュ", "主筋", "帯筋", "あばら筋", "スラブ筋",
                 "壁筋", "フープ", "スパイラル筋", "差し筋", "差筋", "補強筋", "肋筋", "スターラップ",
                 "rebar", "reinforcement", "reinforcing", "reinforcing steel", "reinforcement steel", "rebar steel",
                 "steel reinforcement", "bar reinforcement", "steel bar", "high yield", "high tensile bar", "mild steel bar",
                 "deformed bar", "deformed steel", "tor steel", "stirrup", "welded mesh", "wire mesh", "welded wire",
                 "fabric reinforcement", "steel fabric", "welded fabric", "mesh reinforcement",
                 "re:(?:^|[^a-z])mesh(?![a-z])(?! ?(?:fenc|screen|tray|ceiling|guard|gate|door|insect|filter|panel))",
                 "re:(?:^|[^a-z])(?:tmt|hysd)(?:[^a-z]|$)", "re:(?:^|[^a-z])sd ?[2-6][0-9]{2}",
                 "re:reinforced concrete bars?(?![a-z])")),
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
FORM_WORDS = frozenset(("ボード", "board"))           # a form: グラスウールボード, insulation board, timber board
ADJECTIVES = frozenset(("断熱",))                    # 断熱 before a product: アルミ断熱サッシ, 断熱ドア, ALC断熱パネル
PRODUCT_NOUNS = ("サッシ", "窓", "ドア", "扉", "建具", "パネル", "シャッター", "カーテンウォール")
PLACE_AFTER = ("下", "上", "裏", "廻り", "まわり", "回り", "面", "際")   # コンクリート下: where it goes, not what it is
PLACE_NOT = ("下地", "上塗", "上張", "上貼", "面材", "面積", "上屋", "上端", "下端", "上弦", "下弦", "下塗")   # 鉄骨下地, 鉄骨上屋,
                                                                                         # 鉄筋上端筋: the material
# 用 names a purpose only before a product of no field (鉄筋用スペーサー, コンクリート用混和剤, 鉄骨用錆止め塗料); before
# anything else the material is the item (防水用シート, 防水用塗膜 are membranes)
PURPOSE_PRODUCTS = ("骨材", "金物", "金具", "スペーサ", "混和", "添加", "接着", "プライマー", "釘", "ビス", "ボルト", "アンカー",
                    "インサート", "スリーブ", "セパレータ", "型枠", "剥離", "はく離", "養生", "シール", "テープ", "目地",
                    "補修", "塗料", "錆止", "さび止", "防錆", "塗材", "結束", "吊", "支持", "下地材")
# English products of no field: a material after "in" is what they sit in (Waterstop in concrete, Dowel bars in concrete)
PRODUCTS_IN_EN = ("waterstop", "water stop", "water bar", "waterbar", "dowel", "conduit", "sleeve", "hole", "bolt", "pipe",
                  "duct", "cable", "anchor", "insert", "joint", "chase", "groove", "recess", "opening", "fixing", "box",
                  "drain", "socket")
_PLAIN = {}
_RX = []
for _fid, _ws in KEYWORDS:
    for _w in _ws:
        if _w.startswith("re:"):
            _RX.append((_fid, _w, re.compile(_w[3:])))
        else:
            _PLAIN.setdefault(_w, _fid)
# every plain keyword in one pass: at each position the longest keyword that starts there
_KWRX = re.compile("(?=(%s))" % "|".join(re.escape(w) for w in sorted(_PLAIN, key=len, reverse=True)))
_KW = tuple((fid, w, rx) for fid, w, rx in _RX)       # (kept for older callers)
MAX_NAME = 300                     # characters of a name that are classified (no material name is longer)
MAX_PARTS = 8                      # parts of a name looked at for its head (the head is in the first ones)
# where a name splits into parts: brackets, commas, semicolons and English prepositions. The material is the head of the
# FIRST part that names one ("Reinforcement, high yield steel bars" is rebar; "Supply and installation of plasterboard"
# is board; "Concrete for bar counter" is concrete; "鉄筋（コンクリート用）" is rebar). A part after a preposition of
# place or purpose names where the item goes or what it is for, never what it is ("Hardcore under concrete slab",
# "Sand for mortar", "Insulation between timber joists").
_PREP = ("to", "of", "in", "for", "with", "including", "incl", "excluding", "excl", "on", "at", "into", "from", "per",
         "under", "beneath", "below", "over", "above", "between", "behind", "against", "around", "within", "across",
         "onto", "upon")
PLACE_PREP = frozenset(("to", "for", "on", "at", "into", "from", "under", "beneath", "below", "over", "above", "between",
                        "behind", "against", "around", "within", "across", "onto", "upon"))
_SEGSPLIT = re.compile(r"[,;，；、()（）\[\]［］{}｛｝【】〔〕「」『』<>＜＞]+|\s+(%s)\s+" % "|".join(_PREP))


def _matches(seg: str) -> list:
    """(start, end, field, word) of every keyword in a part: the longest plain keyword at each position, and the
    word-bounded patterns."""
    out = [(m.start(), m.start() + len(m.group(1)), _PLAIN[m.group(1)], m.group(1)) for m in _KWRX.finditer(seg)]
    for fid, w, rx in _RX:
        for m in rx.finditer(seg):
            a, b = m.span()
            if b > a and not seg[a].isalnum():           # the leading "not a letter" of a word-bounded pattern
                a += 1
            if b > a and not seg[b - 1].isalnum():
                b -= 1
            if b > a:
                out.append((a, b, fid, w))
    return out


def _head_of(seg: str, ms: list):
    """(the head among the keyword matches of one part or None, whether the part names a product of no field). The
    head is None when every match only qualifies something else: a place (土間コンクリート下: the next parts are looked
    at), or a product of no field (断熱サッシ, 鉄筋用スペーサー: the name is no material)."""
    kept, product = [], False
    for a, b, fid, w in ms:
        after = seg[b:]
        if after.startswith(PLACE_AFTER) and not after.startswith(PLACE_NOT):
            continue                                     # 土間コンクリート下, コンクリート面
        if after.startswith("用") and after[1:].lstrip().startswith(PURPOSE_PRODUCTS):
            product = True
            continue                                     # 鉄筋用スペーサー: a spacer, not rebar
        if w in ADJECTIVES and after.lstrip().startswith(PRODUCT_NOUNS):
            product = True
            continue                                     # アルミ断熱サッシ: an insulated sash, not insulation
        kept.append((a, b, fid, w))
    kept = [m for m in kept if not (m[3] in FORM_WORDS and any(o[2] != m[2] and o[1] <= m[0] for o in kept))]
    if not kept:
        return None, product
    return max(kept, key=lambda m: (m[1], m[1] - m[0])), False


def _parts(text: str) -> tuple:
    """(part, follows a preposition of place / purpose?, the preposition before it or "") of a lowered name, at most
    MAX_PARTS non-empty parts."""
    out, pos, place, prep = [], 0, False, ""
    for m in _SEGSPLIT.finditer(text):
        seg = _PUNCT.sub(" ", text[pos:m.start()]).strip()
        if seg:
            out.append((seg, place, prep))
            if len(out) >= MAX_PARTS:
                return tuple(out)
        if m.group(1):
            place, prep = m.group(1) in PLACE_PREP, m.group(1)
        elif seg:
            place, prep = False, ""
        pos = m.end()
    seg = _PUNCT.sub(" ", text[pos:]).strip()
    if seg and len(out) < MAX_PARTS:
        out.append((seg, place, prep))
    return tuple(out)


@functools.lru_cache(maxsize=8192)
def _head(text: str) -> tuple:
    """(field or None, part index, head start, head end, parts) of an NFKC-normalised name."""
    pp = _parts(text.lower()[:MAX_NAME])
    parts = tuple(p for p, _, _ in pp)
    for i, (seg, place, prep) in enumerate(pp):
        if place:
            continue                       # "… under concrete slab", "… for mortar": not what the item is
        if prep == "in" and i and not _matches(parts[i - 1]) and any(w in parts[i - 1] for w in PRODUCTS_IN_EN):
            return None, -1, 0, 0, parts   # "Waterstop in concrete", "Dowel bars in concrete": what it sits in
        ms = _matches(seg)
        if ms:
            h, product = _head_of(seg, ms)
            if h is None:
                if product:
                    return None, i, 0, 0, parts      # it names a product of no field (断熱サッシ, 鉄筋用スペーサー)
                continue                             # only a place (土間コンクリート下): the next parts may name it
            return h[2], i, h[0], h[1], parts
    return None, -1, 0, 0, parts


FOUNDATION_WORDS = ("基礎", "杭", "フーチング", "地中梁", "footing", "pile", "foundation")
TOTAL_WORDS = ("合計", "小計", "総計", "計", "total", "subtotal", "sum")
UNIT_ALIASES = {"m3": "m3", "m^3": "m3", "m**3": "m3", "立米": "m3", "立方メートル": "m3", "cum": "m3", "cu.m": "m3",
                "t": "t", "トン": "t", "ton": "t", "tonne": "t", "tonnes": "t", "tons": "t",
                "kg": "kg", "キログラム": "kg", "m2": "m2", "m^2": "m2", "m**2": "m2", "平米": "m2", "平方メートル": "m2",
                "sqm": "m2", "sq.m": "m2"}
QTY_UNITS = ("m3", "m2", "t", "kg")
# rows that repeat a material quantity as work (a 内訳書 lists 加工組立・運搬・打設 with the same quantity as the material),
# and finishing work on a material (金ごて仕上 is labour on the slab, not a finish material). Labour words make a row
# work wherever they are; words that name how a material is put in place (敷込, 取付, 溶接止め, 金ごて, 打放し, 試験杭)
# make it work only in the NAME: in the specification of a material they describe the material item (押出法ポリスチレン
# フォーム｜床下敷込, デッキプレート｜溶接止め, 土間コンクリート｜金ごて仕上, 鋼管杭｜試験杭)
LABOUR_WORDS = ("加工", "組立", "組み立て", "組立て", "運搬", "小運搬", "搬入", "荷揚げ", "荷揚", "打設", "打込", "打ち込", "圧送",
                "ポンプ", "手間", "建方", "建て方", "製作", "養生", "締固め", "揚重", "労務", "工賃", "損料", "配筋", "型枠")
METHOD_WORDS = ("溶接", "圧接", "据付", "据え付", "取付", "取り付", "敷込", "敷き込", "敷設", "試験", "金ごて", "金鏝", "木ごて",
                "木鏝", "直押え", "刷毛引", "打放", "打ち放")
WORK_WORDS = LABOUR_WORDS + METHOD_WORDS
_WORKRX = re.compile("|".join(re.escape(w) for w in sorted(WORK_WORDS, key=len, reverse=True)))
# what may follow a method word before 共 / 込 / 別途 (金ごて押え共, 溶接止め込み, 取付工共)
METHOD_TAIL = ("押え", "押さえ", "仕上げ", "仕上", "止め", "止", "張り", "張", "貼り", "貼", "塗り", "塗", "工法", "工")
# a work word (or a run of them: 加工組立共, 製作・建方共) followed by one of these names a product or a price that
# includes the material (加工鉄筋, 加工済, 工場加工品, 製作金物, 型枠ブロック, 打設共, 建方込み, 運搬費込): not a work row
PRODUCT_AFTER = ("済", "品", "材", "鉄筋", "鋼", "木", "板", "金物", "ボード", "ガラス", "ブロック", "杭", "共", "込", "含", "とも")
# … or says that the work is priced elsewhere (建方別途, 打設費別, 加工を除く): the row is the material
EXCLUDED_AFTER = ("別途", "は別", "別", "を除く", "除く", "除き", "抜き", "なし", "無し", "含まず", "含まない")
_CHAIN_SEP = re.compile(r"[\s・、,＋+&]+|及び|および|と(?!も)")
# other things a price may include, in a run with work words (製作・運搬・建方・残材処分共, 加工組立・スクラップ処分共)
_CHAIN_MORE = re.compile(r"(?:残材|端材|スクラップ|梱包材|発生材|殻)?(?:処分|片付け|片付|清掃|後片付け)")
_WORK_EN = re.compile(
    r"(?:plac(?:e|ed|es|ing|ement)|lay|lays|laying|laid|compact(?:s|ed|ing|ion)?|vibrat(?:e|es|ed|ing|ion)|"
    r"hoist(?:s|ed|ing)?|install(?:s|ed|ing|ation)?|unload(?:s|ed|ing)?|weld(?:s|ed|ing)?|assembl(?:e|es|ed|ing|y)|"
    r"handl(?:e|es|ed|ing)|erect(?:s|ed|ing|ion)?|fix(?:es|ed|ing)?|pour(?:s|ed|ing)?|pump(?:s|ed|ing)?|"
    r"cur(?:e|es|ed|ing)|transport(?:s|ed|ing|ation)?|deliver(?:y|ies|ed|ing)?|fabricat(?:e|es|ed|ing|ion)|"
    r"cut(?:s|ting)?|bend(?:s|ing)?|tying|formwork|shuttering|labou?r|trowel(?:s|led|ling)?)")
WORK_PHRASES_EN = ("power float", "float finish", "floated finish", "trowel finish", "trowelled finish")
# after the material, only a work NOUN makes the row work (Rebar fixing, Steel erection, Concrete pumping, Placing of
# concrete): a participle describes the supply-and-fix item (poured against earth; cut, bent and fixed; laid in slabs;
# fabricated and erected; delivered to site)
_WORK_NOUN_EN = re.compile(r"[a-z]*(?:ing|ion|ment)|labou?r|formwork|shuttering|deliver(?:y|ies)|transport|assembly|pumps?|pours?")
WORK_WORDS_EN = ("placing", "placement", "pumping", "pump", "pour", "pouring", "fixing", "erection", "erect", "erecting",
                 "fabrication", "fabricate", "fabricating", "cutting", "bending", "tying", "labour", "labor", "transport",
                 "delivery", "formwork", "curing", "installation", "hoisting")        # (examples; _WORK_EN decides)
EXCLUDING_EN = ("excluding", "excl", "without", "less", "except", "exclusive", "ex")
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


def _chain_end(seg: str, e: int) -> int:
    """The end of a run of work words that starts before e (加工組立, 製作・建方, ポンプ打設, 打設及び養生)."""
    while True:
        m = _CHAIN_SEP.match(seg, e)
        e2 = m.end() if m else e
        w2 = _WORKRX.match(seg, e2) or _CHAIN_MORE.match(seg, e2)
        if not w2 or w2.end() == e2:
            return e
        e = w2.end()


@functools.lru_cache(maxsize=8192)
def _work(n: str, n_name: int | None = None) -> bool:
    """`n` is the name, or "name ; specification" with `n_name` the number of parts of the name (the parts after
    them are the specification)."""
    fid, hs, a, b, parts = _head(n)
    if n_name is None:
        n_name = len(parts)
    norm = normalise_name(n)
    toks = norm.split()                            # the whole name: "including" is where the parts split
    compact = re.sub(r"\s+", "", n)
    if any(w in compact for w in SUPPLY_JA) or any(t in SUPPLY_EN for t in toks):
        return False
    head_words = set(parts[hs][a:b].split()) if 0 <= hs < len(parts) and b > a else set()
    head_tok = None
    if head_words:                                 # the head's position among the tokens (for "-ed" modifiers)
        hw = parts[hs][a:b].split()[-1]
        head_tok = next((i for i, t in enumerate(toks) if hw in t), None)
    if any(p in norm for p in WORK_PHRASES_EN):
        return True
    for i, t in enumerate(toks):
        if not _WORK_EN.fullmatch(t) or t in head_words:
            continue                               # "welded mesh" is the product
        if i and toks[i - 1] in EXCLUDING_EN:
            continue                               # "excluding placing": the material without its placing
        if " ".join(toks[i + 1:i + 3]) in ("by others",) or (i + 1 < len(toks) and toks[i + 1] == "separately"):
            continue
        if t.endswith("ed") and head_tok is not None and i < head_tok:
            continue                               # "fabricated steelwork", "pumped concrete": the material
        if head_tok is not None and i > head_tok and not _WORK_NOUN_EN.fullmatch(t):
            continue                               # "concrete C20; poured against earth", "bars; cut, bent and fixed"
        if any(x in INCLUSIVE_EN for x in toks[:i]):
            continue                               # "concrete including placing and compacting"
        return True
    for i, seg in enumerate(parts):
        m = _WORKRX.search(seg)
        while m:
            k, e = m.span()
            if i >= n_name and m.group(0) in METHOD_WORDS:
                m = _WORKRX.search(seg, e)         # 床下敷込, 溶接止め, 金ごて仕上 in a material's specification
                continue
            in_head = i == hs and k < b and e > a
            # a work word inside the head's own word, before the material, qualifies it (加工鉄筋, 型枠ブロック)
            # (but not before 仕上: 金ごて仕上・打放し仕上 are labour on the slab, no finish material)
            modifier = i == hs and e <= a and seg.rfind(" ", 0, a) < k and seg[a:b] not in ("仕上", "finish")
            end = _chain_end(seg, e)
            after = seg[end:]
            if m.group(0) in METHOD_WORDS and after.startswith(METHOD_TAIL):
                after = after[next(len(x) for x in METHOD_TAIL if after.startswith(x)):]   # 金ごて押え共
            if after.startswith("費"):
                after = after[1:]                  # 運搬費込, 打設費別
            before = seg[:k].rstrip()
            excluded = after.lstrip().startswith(EXCLUDED_AFTER) or before.endswith(("別途", "除く", "除き"))
            if not in_head and not modifier and not excluded and not after.startswith(PRODUCT_AFTER):
                return True
            m = _WORKRX.search(seg, max(end, k + 1))
    return False


def _is_work(name: str, spec: str = "") -> bool:
    """A labour / process row (鉄筋加工組立, コンクリート打設手間, 鉄骨建て方, 鉄骨 搬入, 鉄骨 現場溶接, 金ごて仕上,
    Rebar fixing, Place concrete in slabs, Hoist and install steelwork, Power float finish …): it repeats the material
    quantity. Not work: a work word that qualifies the product (加工鉄筋, プレカット加工済, 工場加工品, 型枠ブロック,
    fabricated steelwork, welded mesh), a price that includes the material or the work (材工共, 打設共, 加工組立共,
    製作・建方共, 運搬費込, supply and erect, concrete including placing), work priced elsewhere (建方別途, 打設費別,
    excluding placing, fixing by others), and in a specification a word that says how the material is put in place
    (床下敷込, 取付, 溶接止め, 金ごて仕上, 打放し, 試験杭) or a participle after the material (poured against earth; cut, bent and
    fixed; laid in slabs)."""
    if spec:
        nm = _prep(name)
        return _work(nm + " ; " + _prep(spec), len(_parts(nm.lower()[:MAX_NAME])))
    return _work(_prep(name))


# words that start with うち but are not "of which": 打ち放し (うちっぱなし), 内断熱 (うちだんねつ), 内張り / 内貼り
_UCHI_WORDS = ("うちっぱなし", "うちはなし", "うち放し", "うち断熱", "うちだんねつ", "うち張", "うち貼", "うちばり")
AGAIN_JA = ("再掲", "別掲", "上記に含", "前記に含", "上記の内", "上記のうち", "前記の内", "前記のうち", "(再)", "内数")
AGAIN_EN = ("of which", "included above", "already included", "included in item", "included in the item",
            "included elsewhere", "incl. above", "incl above", "measured elsewhere", "see item")
DEDUCT_JA = ("控除", "差引", "差し引", "減額", "発生材")
DEDUCT_EN = ("deduct", "deducted", "deduction", "deductions", "credit", "credits")
# removing what is there is not a new material (既存コンクリート撤去, コンクリート殻処分, Demolition of existing slab)
DEMOLISH_JA = ("撤去", "解体", "はつり", "斫り", "斫", "殻", "処分", "産廃", "取壊", "取り壊", "取りこわ")
DEMOLISH_EN = ("demolition", "demolish", "demolished", "demolishing", "removal", "remove", "removed", "removing",
               "disposal", "dispose", "disposed", "disposing", "rubble", "debris")
DEMOLISH_PHRASES_EN = ("break out", "breaking out", "broken out", "strip out", "stripping out", "take down", "taking down")
_DEMRX = re.compile("|".join(re.escape(w) for w in sorted(DEMOLISH_JA, key=len, reverse=True)))
# a removal word followed by these is a price note on a material row (端材処分共, 殻処分費別途, 処分費込み)
NOTE_AFTER_JA = ("共", "込", "含", "とも", "別途", "は別", "別", "を除く", "除く", "除き", "なし", "無し")
_DEM_CHAIN = re.compile(r"[\s・、,＋+&]*(?:%s|運搬|積込|積み込み|費)" % "|".join(re.escape(w) for w in DEMOLISH_JA))
NOTE_OF_EN = ("offcuts", "off", "surplus", "waste", "packaging", "arisings", "excess", "cuttings")
SURE, MAYBE = "sure", "maybe"


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


_DEDUCT_NOTE = re.compile(r"発生材(?:の)?(?:処分|運搬|積込|片付け?)+費?(?:共|込|含|とも|別途|は別|別)")


@functools.lru_cache(maxsize=8192)
def _deduct(n: str) -> bool:
    toks = normalise_name(n).split()
    compact = _DEDUCT_NOTE.sub("", re.sub(r"\s+", "", n))    # 発生材処分別途: a price note, not a credit
    return any(w in compact for w in DEDUCT_JA) or any(t in DEDUCT_EN for t in toks) or (toks[:1] == ["less"])


def _is_deduction(*texts: str) -> bool:
    """A deduction (スクラップ控除, 発生材, 差引, deduct, credit, "less …"), often written with a positive quantity and a
    negative price: never added and never subtracted silently."""
    return any(_deduct(_prep(t)) for t in texts)


def _token_parts(toks: list, parts: tuple) -> list:
    """The part index of each token of a name (None for a preposition between parts)."""
    where, p = [None] * len(toks), 0
    for j, seg in enumerate(parts):
        for w in seg.split():
            q = p
            while q < len(toks) and toks[q] != w:
                q += 1
            if q < len(toks):
                where[q], p = j, q + 1
    return where


@functools.lru_cache(maxsize=8192)
def _demolish(n: str, n_name: int | None = None):
    """None, SURE (removal of what is there: 既存コンクリート撤去, コンクリート殻処分, Demolition of existing slab) or MAYBE (a
    removal word only after the material, in a later part or the specification: perhaps a note on the material row).
    Not removal: a price note (端材処分共, 殻処分費別途, 別途処分, including disposal of surplus, disposal of offcuts by
    others)."""
    fid, hs, _a, _b, parts = _head(n)
    norm = normalise_name(n)
    toks = norm.split()
    found = None

    def kind(i):
        return MAYBE if 0 <= hs < i else SURE

    for i, seg in enumerate(parts):
        for m in _DEMRX.finditer(seg):
            e = m.end()
            while True:
                c = _DEM_CHAIN.match(seg, e)
                if not c or c.end() == e:
                    break
                e = c.end()
            after, before = seg[e:].lstrip(), seg[:m.start()].rstrip()
            if after.startswith(NOTE_AFTER_JA) or before.endswith(("別途", "別")):
                continue
            k = kind(i)
            if k == SURE:
                return SURE
            found = MAYBE
    where = None
    for i, t in enumerate(toks):
        if t not in DEMOLISH_EN:
            continue
        nxt = toks[i + 1:i + 3]
        if any(x in INCLUSIVE_EN for x in toks[:i]) or " ".join(nxt) in ("by others",) or nxt[:1] in (["separately"], ["elsewhere"]) \
                or (nxt[:1] == ["of"] and toks[i + 2:i + 3] and toks[i + 2] in NOTE_OF_EN):
            continue
        if where is None:
            where = _token_parts(toks, parts)
        k = kind(where[i]) if where[i] is not None else SURE
        if k == SURE:
            return SURE
        found = MAYBE
    if any(p_ in norm for p_ in DEMOLISH_PHRASES_EN):
        return SURE
    return found


def _is_demolition(*texts: str) -> bool:
    """Removal of what is there (撤去, 解体, はつり, 殻, 処分, demolition, break out, removal, disposal, rubble): not a new
    material, never added. A price note is not removal (端材処分共, 殻処分費別途, including disposal of surplus)."""
    return any(_demolish(_prep(t)) for t in texts)


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


MAX_FOLLOW_STEPS = 1_000_000          # formula cells, blocks and rows looked at per document while following formulas
_FollowBudget = tabular.FollowBudget
CUT_SHEET = "非表示のシート（%s）が大きすぎて途中から読んでいないので、そこへの参照は確かめられない。必要なら手で入れる"


class _Cells:
    """What a quantity formula reaches, followed through the formulas of every sheet (helper cells, other columns,
    other sheets, hidden helpers, array formulas, defined names, tables). A quantity is a copy when it reaches the
    QUANTITY of another material row (a row that names a material in a unit its field takes, or a total / 再掲 / work /
    deduction / removal row on a sheet that lists materials): a cell in its quantity columns (数量, 所要数量, 体積, 重量 …)
    or a cell added into its quantity (a calculation column, per-floor columns), reached in any way; or any other number
    of that row ADDED up by the quantity (集計!1F = 明細!C2 where C2 is a typed per-floor quantity, SUMPRODUCT, table
    references), unless its column names money or a factor. A number of another row that is only multiplied or looked up
    (a unit mass, a density, a lookup table beside the bill) is a factor, not a copy. Cells of the quantity's own row are
    parts of it. Every formula cell and every range is followed once per document (the results are kept), and every
    step, block and name expansion counts against MAX_FOLLOW_STEPS."""

    def __init__(self, parsed: dict):
        self.cells = parsed.get("cells") or {}
        self.names = parsed.get("names") or {}
        self.tables = parsed.get("tables") or {}
        self.disp = parsed.get("sheet_names") or {}
        self.frows = {sh: sorted(rows) for sh, rows in self.cells.items()}
        self.fcols = {}
        self.targets, self.tcols, self.owned = {}, {}, {}
        self.ncols = {}                    # (sheet, row) -> the row's numbers outside money / factor columns
        self.cut_sheets = set(parsed.get("cut_sheets") or ())
        self.memo, self.name_memo = {}, {}
        self.left = MAX_FOLLOW_STEPS
        self.cut = 0

    def _spend(self, n: int = 1):
        self.left -= n
        if self.left < 0:
            raise _FollowBudget()

    def _ctx(self, sh, rn, ci):
        return {"sheet": self.disp.get(sh, sh), "names": self.names, "tables": self.tables, "row": rn, "col": ci,
                "spend": self._spend, "name_memo": self.name_memo}

    def _children(self, node, fr):
        """(child, added?) of a node. A frame is [node, children, why, rows reached, rows reached by adding, added?]."""
        if node[0] == "c":
            _k, sh, rn, ci = node
            self._spend()
            if sh in self.cut_sheets:
                fr[2] = (CUT_SHEET % self.disp.get(sh, sh), node)
                return iter(())
            why, blocks = tabular.formula_walk(self.cells[sh][rn][ci], self._ctx(sh, rn, ci))
            if why:
                fr[2] = (why, node)
                return iter(())
            self._spend(len(blocks))
            return iter([(("b", b[0] or sh, b[1], b[2], b[3], b[4]), b[5]) for b in blocks])
        _k, t, c1, c2, r1, r2 = node
        if t in self.cut_sheets:
            fr[2] = (CUT_SHEET % self.disp.get(t, t), node)
            return iter(())
        lo = 0 if r1 is None else r1
        hi = tabular.MAX_ROW_NUMBER if r2 is None else r2
        trows, tc = self.targets.get(t), self.tcols.get(t, ())
        if trows:
            k = bisect.bisect_left(trows, lo)
            while k < len(trows) and trows[k] <= hi and len(fr[3]) < 2:
                self._spend()
                key = (t, trows[k])
                if key not in fr[3]:
                    cols = self.owned.get(key, tc)    # the quantity columns, and the cells added into them
                    j = bisect.bisect_left(cols, c1)
                    if j < len(cols) and cols[j] <= c2:
                        fr[3].append(key)
                    elif key not in fr[4] and len(fr[4]) < 2:
                        lc = self.ncols.get(key, ())  # another number of the row: a copy only when it is added up
                        j = bisect.bisect_left(lc, c1)
                        if j < len(lc) and lc[j] <= c2:
                            fr[4].append(key)
                k += 1
        return ((c, True) for c in self._formula_cells(t, c1, c2, lo, hi))

    def own_parts(self, sh: str, row: int):
        """The cells of a material row that are added into its quantity (ROUND(F2), SUM(B2:D2): a calculation column,
        per-floor columns): another row that reaches one of them copies part of this row's quantity. A factor of the
        row (a density, a unit mass multiplied by a length) is not a part of it."""
        tc = self.tcols.get(sh, ())
        rowcells = self.cells.get(sh, {}).get(row) or {}
        owned, todo, seen = set(tc), [c for c in tc if c in rowcells], set()
        while todo:
            c = todo.pop()
            if c in seen:
                continue
            seen.add(c)
            try:
                blocks = tabular.added_blocks(rowcells[c], self._ctx(sh, row, c))
            except _FollowBudget:
                break
            for bsh, c1, c2, r1, r2 in blocks:
                if (bsh is None or bsh == sh) and r1 == row and r2 == row and c2 - c1 < 256:
                    for cc in range(c1, c2 + 1):
                        owned.add(cc)
                        if cc in rowcells:
                            todo.append(cc)
        if owned != set(tc):
            self.owned[(sh, row)] = sorted(owned)

    def _formula_cells(self, t, c1, c2, lo, hi):
        frs = self.frows.get(t, ())
        k = bisect.bisect_left(frs, lo)
        while k < len(frs) and frs[k] <= hi:
            rn = frs[k]
            self._spend()
            cols = self.fcols.get((t, rn))
            if cols is None:
                cols = self.fcols[(t, rn)] = sorted(self.cells[t][rn])
            j = bisect.bisect_left(cols, c1)
            while j < len(cols) and cols[j] <= c2:
                self._spend()
                yield ("c", t, rn, cols[j])
                j += 1
            k += 1

    @staticmethod
    def _merge(fr, res, added):
        why, hits, adds = res
        if why and fr[2] is None:
            fr[2] = why
        for h in hits:
            if h not in fr[3] and len(fr[3]) < 2:
                fr[3].append(h)
        if added:                                        # numbers reached by adding stay "added" only through sums
            for h in adds:
                if h not in fr[4] and h not in fr[3] and len(fr[4]) < 2:
                    fr[4].append(h)

    def _result(self, root):
        """(why it cannot be checked: (text, node) or None; up to two (sheet, row) material rows whose quantity is
        reached; up to two whose other numbers are reached by adding only)."""
        memo = self.memo
        if root in memo:
            return memo[root]
        stack, on = [[root, None, None, [], [], True]], {root}
        while stack:
            fr = stack[-1]
            if fr[1] is None:
                fr[1] = self._children(fr[0], fr)
            nxt = next(fr[1], None) if fr[2] is None and len(fr[3]) < 2 else None
            if nxt is None:
                res = memo[fr[0]] = (fr[2], tuple(fr[3]), tuple(fr[4]))
                on.discard(fr[0])
                stack.pop()
                if stack:
                    self._merge(stack[-1], res, fr[5])
                continue
            child, added = nxt
            got = memo.get(child)
            if got is not None:
                self._spend()
                self._merge(fr, got, added)
            elif child in on:
                fr[2] = ("循環する参照（数式が自分自身にたどり着く）は確かめられない。必要なら手で入れる", fr[0])
            else:
                on.add(child)
                stack.append([child, None, None, [], [], added])
        return memo[root]

    def copy_of(self, sh: str, row: int, col: int, qf=None):
        """None, ("copy", sheet, row), ("unchecked", reason) or ("budget", reason)."""
        node = ("c", sh, row, col)
        if col not in (self.cells.get(sh, {}).get(row) or {}):
            if qf is None:
                return None
            self.cells.setdefault(sh, {}).setdefault(row, {})[col] = qf
            self.frows[sh] = sorted(self.cells[sh])
            self.fcols.pop((sh, row), None)
        try:
            why, hits, adds = self._result(node)
        except _FollowBudget:
            self.cut += 1
            return ("budget", "数式のたどる先が多すぎて確かめられない（1 つの資料で %d 歩まで）。必要なら手で入れる"
                    % MAX_FOLLOW_STEPS)
        others = [h for h in list(hits) + list(adds) if h != (sh, row)]
        if others:
            return ("copy",) + others[0]
        if why:
            text, at = why
            if at == node:
                return ("unchecked", text)
            return ("unchecked", "参照先の数式（%s）：%s" % (self.disp.get(at[1], at[1]), text))
        return None


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


def _row_class(prep: _Prep, r: dict) -> dict:
    name, spec, div = prep(r.get("name")), prep(r.get("specification")), prep(r.get("division"))
    text = name + " ; " + spec if spec else name
    n_name = len(_parts(name.lower()[:MAX_NAME])) if spec else None     # the parts after these are the specification
    fid = _classify(text, div)
    total = _total(name) or (_total(spec) if spec else False)
    again = _again(name) or (_again(spec) if spec else False) or (_again(div) if div else False)
    deduct = _deduct(name) or (_deduct(spec) if spec else False)
    demolish = _demolish(text, n_name)
    work = _work(text, n_name)
    return {"name": name, "fid": fid, "u": _unit(r.get("unit")), "total": total, "again": again, "deduct": deduct,
            "demolish": demolish, "work": work}


# why a row that names a field's material was not added, and whether adding it might have been right (then the
# candidate may be too low: the card says so). Totals, 再掲, deductions, removals and negative rows are surely not part.
R_TOTAL = "合計・小計の行は足さない（二重計上を防ぐ）"
R_AGAIN = "再掲・内数（うち・内訳）の行は足さない（ほかの行に含まれている。二重計上を防ぐ）"
R_DEDUCT = "控除・差し引き（スクラップ・発生材など）の行は足さない（差し引きにもしない。必要なら手で直す）"
R_DEMOLISH = "撤去・解体・処分の行（今ある物を取り除く。新しい材料ではない）は足さない"
R_DEMOLISH_MAYBE = "材料の後に撤去・解体・処分の語がある（取り除く行か、材料の行の注記か分からない）ので足さない。材料の行なら手で入れる"
R_WORK = "作業の行（加工・運搬・打設など。材料の量を繰り返す）は足さない（二重計上を防ぐ）"
R_NEG = "負の数量は読まない（差し引きにしない）"
SURELY_NOT = (R_TOTAL, R_AGAIN, R_DEDUCT, R_DEMOLISH, R_NEG, tabular.HEADING)
MAX_EVIDENCE = 200


def read(name: str, data_b64: str, doc_id: str) -> dict:
    """Parse one uploaded file. Returns {kind, sha256, parsed_summary, proposals:[Value...], evidence:{field: {rows,
    n_rows, excluded, n_excluded, n_maybe}}, unused:[...], warnings:[...]}."""
    try:
        data = base64.b64decode(data_b64, validate=True)
    except Exception:
        raise ValueError("ファイルの中身を読めない（base64 でない）") from None
    kind = kind_of(name, data)
    sha = hashlib.sha256(data).hexdigest()
    warnings, unused, sums, excluded = [], [], {}, {}

    def leave(fid, r_trace, r_name, reason, qty=None, unit=None):
        """A row not added: listed as unused and, when it names a field's material, on that field's candidate (with
        its quantity and unit when it has them, so that a possible shortfall can be judged on the card)."""
        unused.append({"trace": r_trace, "name": r_name[:80], "reason": reason})
        if fid:
            x = {"trace": r_trace, "name": r_name[:80], "reason": reason, "maybe": reason not in SURELY_NOT}
            if qty is not None and qty != "":
                x["quantity"] = qty if isinstance(qty, (int, float)) else str(qty)[:40]
            if unit:
                x["unit"] = str(unit)[:20]
            excluded.setdefault(fid, []).append(x)

    if kind in ("csv", "xlsx"):
        parsed = tabular.read_csv(data, doc_id) if kind == "csv" else tabular.read_xlsx(data, doc_id)
        warnings += parsed.get("warnings", [])
        prep, cells = _Prep(), _Cells(parsed)
        classed = []                       # (sheet casefolded, row, class) of the candidate rows, in reading order
        n_classified, stopped = 0, None
        for sh in parsed["sheets"]:
            if sh.get("error"):
                warnings.append("%s：%s" % (sh["sheet"], sh["error"]))
            shf = str(sh["sheet"]).casefold()
            mats, marks, nums = [], [], {}
            xcols = set(sh.get("xcols") or ())
            for r, cand in [(x, False) for x in sh.get("skipped", [])] + [(x, True) for x in sh["rows"]]:
                if stopped:
                    if not cand:
                        unused.append({"trace": r["trace"], "name": r["name"][:80], "reason": r["reason"]})
                    continue
                n_classified += 1
                if n_classified > MAX_ROWS_CLASSIFIED:
                    stopped = "数量の行が多すぎるので、最初の %d 行だけを読んだ（残りは読んでいない）" % MAX_ROWS_CLASSIFIED
                    if not cand:
                        unused.append({"trace": r["trace"], "name": r["name"][:80], "reason": r["reason"]})
                    continue
                try:
                    c = _row_class(prep, r)
                except _Budget:
                    stopped = "文字が多すぎるので、最初の %d 行だけを読んだ（残りは読んでいない）" % (n_classified - 1)
                    if not cand:
                        unused.append({"trace": r["trace"], "name": r["name"][:80], "reason": r["reason"]})
                    continue
                # a material row (also when this row itself is not added: a SUM subtotal, a non-numeric quantity …)
                # in a unit its field takes: a quantity elsewhere that reaches its quantity copies it. Total / 再掲 /
                # work / deduction / removal rows count only on a sheet that lists materials (延床面積 合計 on a
                # dimensions sheet is not a material quantity)
                if c["fid"] and c["u"] in FL.FIELDS[c["fid"]]["units"]:
                    mats.append(r["row"])
                    nums[r["row"]] = r.get("ncols") or ()
                elif c["total"] or c["again"] or c["work"] or c["deduct"] or c["demolish"]:
                    marks.append(r["row"])
                    nums[r["row"]] = r.get("ncols") or ()
                if cand:
                    classed.append((shf, r, c))
                elif r.get("heading"):
                    leave(None, r["trace"], r["name"], r["reason"])   # コンクリート工事: no row of a material
                else:
                    leave(c["fid"], r["trace"], r["name"], r["reason"], r.get("qtext"), r.get("unit"))
            if mats:
                cells.targets[shf] = sorted(set(mats + marks))
                cells.tcols[shf] = list(sh.get("qcols") or [sh.get("qcol") or 0])
                for rn in cells.targets[shf]:
                    cells.ncols[(shf, rn)] = sorted(set(nums.get(rn) or ()) - xcols)
                    cells.own_parts(shf, rn)
        if stopped:
            warnings.append(stopped)
        for shf, r, c in classed:
            why = None
            if c["total"]:
                why = R_TOTAL
            elif c["again"]:
                why = R_AGAIN
            elif c["deduct"]:
                why = R_DEDUCT
            elif c["demolish"]:
                why = R_DEMOLISH if c["demolish"] == SURE else R_DEMOLISH_MAYBE
            elif c["work"]:
                why = R_WORK
            elif r["quantity"] < 0:
                why = R_NEG
            elif c["fid"] is None:
                why = "どの材料の欄にも当てはまらない"
            elif c["u"] not in FL.FIELDS[c["fid"]]["units"]:
                f_ = FL.FIELDS[c["fid"]]
                why = "単位 %r は「%s」に使えない（%s）。必要なら換算して手で入れる" % (r["unit"], f_["label"], "・".join(f_["units"]))
            elif r.get("qf"):
                got = cells.copy_of(shf, r["row"], sh_qcol(parsed, shf), r["qf"])
                if got and got[0] == "copy":
                    _k, tsh, trow = got
                    if tsh == shf:
                        why = "同じシートのほかの材料の行（%d 行目）の数量から計算した値（合計・再掲・割増のおそれ）は足さない。" \
                              "別の材料を比率で出した行など、足すべき行なら手で入れる" % trow
                    else:
                        why = "別のシート（%s）の材料の行（%d 行目）の数量を参照した値は足さない（そのシートも読んでいるので二重計上になる）" \
                              % (parsed.get("sheet_names", {}).get(tsh, tsh), trow)
                elif got:
                    why = got[1]
            if why:
                leave(c["fid"], r["trace"], c["name"], why, r["quantity"], r.get("unit"))
                continue
            sums.setdefault((c["fid"], c["u"]), []).append((r["quantity"], r["trace"], c["name"]))
        if cells.cut:
            warnings.append("数式のたどる先が多すぎるので、%d 行は確かめられず足していない（1 つの資料で %d 歩まで）。"
                            "その行は「使わなかった行」にある" % (cells.cut, MAX_FOLLOW_STEPS))
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
            label = "%s %s" % (e["type"], e["name"])
            if fid is None:
                unused.append({"trace": "%s:#%d" % (doc_id, e["step_id"]), "name": label,
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
                leave(fid, "%s:#%d" % (doc_id, e["step_id"]), label,
                      "「%s」に使える数量（%s）が IFC の数量セットに無い（形状からは測らない）"
                      % (FL.FIELDS[fid]["label"], "・".join(FL.FIELDS[fid]["units"])))
                continue
            u, q = picked
            sums.setdefault((fid, u), []).append((q["value"], q["trace"], label))
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
            if _is_demolition(c["name"]):
                unused.append({"trace": c["trace"], "name": c["name"][:80], "reason": "撤去・解体・処分の行は候補にしない"})
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
                "proposals": proposals, "evidence": {}, "left_out": {}, "unused": unused, "warnings": warnings}
    else:
        raise ValueError("この形式は読めない（CSV・XLSX・IFC・PDF）")
    proposals, evidence = [], {}
    to_t = {"t": 1.0, "kg": 0.001}
    by_field = {}
    for (fid, u), items in sums.items():
        by_field.setdefault(fid, {}).setdefault("mass" if u in to_t else u, []).extend((q, t, u, nm) for q, t, nm in items)
    for fid, dims in by_field.items():
        # one field holds one value: t and kg rows are added in t; rows of another dimension (m3 next to t) cannot be
        # added. The dimension with more rows is proposed and the other rows are listed; when as many rows have one
        # dimension as another, neither is more likely the field's quantity, and nothing is proposed
        label = FL.FIELDS[fid]["label"]
        counts = sorted(((len(v), k) for k, v in dims.items()), reverse=True)
        if len(counts) > 1 and counts[0][0] == counts[1][0]:
            desc = "・".join("%s の行 %d" % ("t・kg" if k == "mass" else k, n) for n, k in counts)
            for rows_ in dims.values():
                for q, t, u, nm in rows_:
                    leave(fid, t, nm, "同じ材料の行の単位が混ざっていて（%s）、どれが「%s」の量か決められない：確かめて手で入れる"
                          % (desc, label), q, u)
            continue
        dim = counts[0][1]
        for other, rows_ in dims.items():
            if other != dim:
                for q, t, u, nm in rows_:
                    leave(fid, t, nm, "同じ材料の別の行と単位の次元が違う（%s と %s）ので合計できない：確かめて手で入れる"
                          % (u, "t" if dim == "mass" else dim), q, u)
        items = dims[dim]
        if dim == "mass":
            total, u = sum(q * to_t[uu] for q, _, uu, _n in items), "t"
        else:
            total, u = sum(q for q, _, _, _n in items), dim
        traces = [t for _, t, _, _n in items]
        detail = "%d 行の合計：%s%s" % (len(items), "、".join(traces[:12]), "…" if len(traces) > 12 else "")
        ex = excluded.get(fid, [])
        n_maybe = sum(1 for x in ex if x["maybe"])
        note = "資料「%s」から。分類はキーワードによるので、足した行と足さなかった行を確かめる" % doc_id
        if ex:
            note += "（この欄の材料の行で足さなかった行 %d 行" % len(ex)
            note += ("。うち %d 行は足すべき行かもしれない。そうなら、この候補は少なめ）" % n_maybe) if n_maybe else "）"
        proposals.append(Value(fid, "from_drawing", round(total, 6), u, method="%s_quantity_sum" % kind, source_id=doc_id,
                               source_detail=detail, note=note))
        evidence[fid] = {"rows": [{"trace": t, "name": nm, "quantity": q, "unit": uu} for q, t, uu, nm in items[:MAX_EVIDENCE]],
                         "n_rows": len(items),
                         "excluded": ex[:MAX_EVIDENCE], "n_excluded": len(ex), "n_maybe": n_maybe}
    # rows that name a field's material although the field got no candidate (every row was left out): said in the
    # import's summary, so that a field that stays empty is not taken for "nothing of that material in the file"
    left_out = {fid: {"n_excluded": len(ex), "n_maybe": sum(1 for x in ex if x["maybe"]), "excluded": ex[:20]}
                for fid, ex in excluded.items() if fid not in evidence}
    summ = {"n_rows": sum(len(s["rows"]) for s in parsed["sheets"])} if kind in ("csv", "xlsx") else \
        {"n_elements": len(parsed["elements"]), "schema": parsed["schema"]}
    if len(unused) > 2000:
        warnings.append("使わなかった行が多いので、最初の 2000 行だけを記録した（全部で %d 行）" % len(unused))
        unused = unused[:2000]
    return {"kind": kind, "sha256": sha, "parsed_summary": summ, "proposals": proposals, "evidence": evidence,
            "left_out": left_out, "unused": unused, "warnings": warnings}
