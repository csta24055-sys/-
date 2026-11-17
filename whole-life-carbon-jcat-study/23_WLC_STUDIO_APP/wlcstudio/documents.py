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
# a material followed in its word by one of these is what the item is without (石膏ボード除く, ボード別途, 断熱材含まず): like the
# part after an English excluding word, it gives no head (15 回目の攻撃)
JA_EXCL_AFTER = ("除く", "を除く", "除き", "を除き", "別途", "は別途", "含まず", "を含まず", "抜き")
# X用Y is Y for X (鉄筋用スペーサー, コンクリート用砕石, モルタル用砂, 石膏ボード用パテ, 鉄骨用高力ボルト): not X. Only when Y is a
# form of X itself is the material the item (防水用シート, 防水用塗膜 are membranes, 断熱用ボード insulation); when Y is another
# material, Y is the head anyway (防水用モルタル is mortar). X用 alone names a purpose (the next parts may name the item)
# A Japanese compound ends in its head, so Y is a form of X when it ENDS in one (防水用改質アスファルトシート, 防水用ウレタン
# 塗膜, 断熱用フォームボード, 鉄骨用ベースプレート) — or names one with no purpose product after it (断熱用ボード張り);
# 防水用シート押え金物 is hardware (13 回目)
USE_FORMS = {"m_membrane": ("シート", "塗膜", "ルーフィング", "防水層", "膜", "層", "アスファルト"),
             "m_steel": ("鋼板", "丸鋼", "鋼管", "形鋼", "プレート", "ブレース", "デッキ", "アングル", "チャンネル", "フラットバー")}
PURPOSE_PRODUCTS = ("骨材", "金物", "金具", "スペーサ", "混和", "添加", "接着", "プライマー", "釘", "ビス", "ボルト", "アンカー",
                    "インサート", "スリーブ", "セパレータ", "型枠", "剥離", "はく離", "養生", "シール", "テープ", "目地",
                    "補修", "塗料", "錆止", "さび止", "防錆", "塗材", "結束", "吊", "支持", "下地材", "ピン", "ファスナ",
                    "パテ", "押え", "押さえ")
# ボード / board at the end of Y is a form only of the materials that come as boards: 断熱用フォームボード is insulation, but
# タイル用下地ボード, クロス用下地ボード, 防水用保護ボード, 鉄骨用耐火ボード are boards (14 回目: 13 回目 made it a form of every material)
BOARD_FIELDS = frozenset(("m_insulation", "m_board"))
# a word before the form word that names another purpose or another kind of product makes Y a product of its own
# (防水用保護シート, 防水用目地シート, 防水用保護層, 断熱用下地ボード, 断熱用セメントボード: not the membrane, not insulation)
USE_QUALIFIERS = ("保護", "下地", "耐火", "化粧", "絶縁", "緩衝", "脱気", "通気", "防湿", "透湿", "遮熱", "遮音", "吸音", "防振",
                  "排水", "防根", "仮設", "捨")
BOARD_KINDS = ("セメント", "石膏", "せっこう", "ケイカル", "珪カル", "ケイ酸", "けい酸", "木毛", "木片", "パーティクル", "不燃",
               "繊維", "スレート", "フレキ", "合板")          # … before ボード: a board, not insulation
_ALL_FORMS = tuple(sorted(set(sum(USE_FORMS.values(), ())) | FORM_WORDS))   # … and after X's form: another product
_NON_ASCII_RUN = re.compile(r"[^\x00-\x7f]+")


def _use_is_form(fid: str, rest: str) -> bool:
    """Is Y of X用Y (rest: the text after 用) a form of X itself? Y is its first word (the Japanese run of it); it is a
    form when it ends in one of X's forms (ボード/board only for the materials that come as boards) with no purpose
    product after it, and no other purpose or kind of product before it."""
    words = rest.split()
    if not words:
        return False
    y = words[0]
    m = _NON_ASCII_RUN.match(y)
    if m:
        y = m.group(0)
    # (a Y that starts with ボード keeps the reading of 12 回目 for every X: 断熱用ボード, タイル用ボード)
    boards = fid in BOARD_FIELDS or y.startswith(tuple(FORM_WORDS))
    forms = USE_FORMS.get(fid, ()) + (tuple(FORM_WORDS) if boards else ())
    hits = [(y.rfind(f), y.rfind(f) + len(f), f) for f in forms if f in y]
    if not hits:
        return False
    end = max(e for _s, e, _f in hits)
    start, _e, form = min(h for h in hits if h[1] == end)          # the longest form word that ends there
    if any(p in y[end:] for p in PURPOSE_PRODUCTS + _ALL_FORMS):
        return False                       # 防水用シート押え金物 is hardware, 防水用アスファルトボード a board (14 回目)
    before = y[:start]
    return not any(q in before for q in USE_QUALIFIERS + PURPOSE_PRODUCTS + (BOARD_KINDS if form in FORM_WORDS else ()))


def _product_after(seg: str, b: int) -> bool:
    """Whether a purpose product follows seg[b:] in the same word (断熱用ボード押え金物: the item is the hardware)."""
    w = seg[b:].split(" ", 1)[0]
    return any(p in w for p in PURPOSE_PRODUCTS)


# English products of no field: a material after "in" is what they sit in (Waterstop in concrete, Dowel bars in concrete)
PRODUCTS_IN_EN = ("waterstop", "water stop", "water bar", "waterbar", "dowel", "conduit", "sleeve", "hole", "bolt", "pipe",
                  "duct", "cable", "anchor", "insert", "joint", "chase", "groove", "recess", "opening", "fixing", "box",
                  "drain", "socket")
# … but a part that names a filling, a surround or a bed is made of what follows "in" (Filling openings in brickwork,
# Pipe surround in concrete, Drainage bed in concrete): the material is the item
FILL_WORDS_EN = frozenset(("filling", "fillings", "infill", "infills", "infilling", "fill", "surround", "surrounds",
                           "surrounding", "bed", "beds", "bedding", "encasing", "encasement", "haunching", "haunchings",
                           "haunch", "benching", "base", "bases", "blinding", "backfill", "backfilling", "plug", "plugging",
                           "bedded", "encased", "surrounded", "haunched", "benched"))
# … and after "in" a metal, timber, plastic or glass is what the product is made of (Box gutters in aluminium)
MADE_OF = frozenset(("m_aluminium", "m_steel", "m_timber", "m_plastic", "m_glass"))
_PRODUCTS_IN_RX = re.compile(r"(?<![a-z])(?:%s)(?:e?s)?(?![a-z])" % "|".join(re.escape(w) for w in PRODUCTS_IN_EN))
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
# … and the four abbreviations with their dot, which qualify the head as including / excluding do (Ready mixed
# concrete incl. reinforcement is concrete, Blockwork incl. mortar is blockwork) (14 回目)
PREP_DOT = ("incl.", "inc.", "excl.", "exc.")
PLACE_PREP = frozenset(("to", "for", "on", "at", "into", "from", "under", "beneath", "below", "over", "above", "between",
                        "behind", "against", "around", "within", "across", "onto", "upon"))
# a part after an excluding word names what the item is without, never what it is: "Metal stud partition excl.
# plasterboard", "Excavation for pile caps excl. concrete" name no material (14 回目 let the excluded material be the
# head), and the excluded part does not choose the foundation card either ("Concrete C30 excl. pile caps") (15 回目)
EXCL_PREP = frozenset(("excluding", "excl", "excl.", "exc", "exc.", "without", "except", "less", "ex"))
# … also right after an opening bracket or , ; : - with no space ("Metal stud partition (excluding plasterboard)",
# "Cavity wall,excl. insulation"), and the excluded part goes on over a list (", … and …") up to the bracket that
# closes it, a ";" or the end: "Metal stud partition excl. plasterboard, insulation" names neither (15 回目の攻撃)
_EXCL_WORDS = ("excluding", "excl.", "excl", "exc.", "exc", "without", "except", "less", "ex")
_EXCL_AFTER_CHARS = "(（[［{｛【〔「『<＜,;，；、:：-‐－–—"
# (… and an excluding word followed by a colon, or a dotted one followed by the word at once: "excl.: plasterboard",
# "(excl.plasterboard)")
_SEGSPLIT = re.compile(r"[,;，；、()（）\[\]［］{}｛｝【】〔〕「」『』<>＜＞]+|\s+(%s)\s+"
                       r"|(?:(?<=[%s])|(?<=\s))(%s)(?:\s+|[:：]\s*|(?<=\.)(?=[a-z]))"
                       % ("|".join(tuple(re.escape(w) for w in PREP_DOT) + _PREP
                                   + ("without", "except", "less", "exc", "ex")),
                          re.escape(_EXCL_AFTER_CHARS), "|".join(re.escape(w) for w in _EXCL_WORDS)))
_OPENING, _CLOSING = "(（[［{｛【〔「『<＜", ")）]］}｝】〕」』>＞"
# … but not where the word does not exclude: "ex 50 x 200" (the nominal size of sawn timber), "ex works / stock / mill /
# plant / site" (where it comes from), "not less than 75mm" (a minimum), "less than 1m2", "except as noted",
# "except where …" (15 回目の攻撃)
EX_FROM = frozenset(("works", "stock", "mill", "plant", "site"))
# … nor less / ex joined by a hyphen to a word of letters before it: one word (Frame-less, Seam-less, Stain-less, Co-ex),
# whose next words name the item (15 回目 split there, and the glass of "Frame-less glass balustrade" got no field) (16 回目)
HYPHEN_WORDS = frozenset(("less", "ex"))
_DASHES = "-‐－–—"
_HYPHEN_STEM = re.compile(r"(?<![a-z0-9.])[a-z]+$")    # (a word of letters only right before the dash: not 12.5mm-less)
_WORD_AFTER = re.compile(r"\s*([^\s,;:()（）\[\]［］]+)")
_WORD_BEFORE = re.compile(r"([a-z]+)\W*$")
ASIDE = "?"            # (the preposition of a part after an aside set off by commas, see _parts)
_ASIDE_HINT = re.compile(r"[,，、]\s*(?:excluding|excl|exc|without|except|less|ex)(?![a-z])")


def _after_aside(text: str) -> bool:
    """Whether the head of a name comes from a part after an aside set off by commas ("Infill panels, without frames,
    blockwork 100mm", "Metal stud partition, excl. plasterboard, insulation"): perhaps the item, perhaps more of what is
    excluded (15 回目の攻撃)."""
    low = text.lower()[:MAX_NAME]
    if not _ASIDE_HINT.search(low):
        return False
    fid, i = _head(text)[:2]
    pp = _parts(low)
    return fid is not None and 0 <= i < len(pp) and pp[i][2] == ASIDE


def _excludes(w: str, text: str, m) -> bool:
    """Whether the excluding word w (matched by m in text) excludes here (see EX_FROM, HYPHEN_WORDS)."""
    if w in HYPHEN_WORDS:
        s = m.start(1) if m.group(1) else m.start(2)
        if s >= 2 and text[s - 1] in _DASHES and _HYPHEN_STEM.search(text, 0, s - 1):
            return False                   # (frame-less, co-ex: part of the word)
    if w not in ("ex", "less", "except"):
        return True
    nx = _WORD_AFTER.match(text, m.end())
    nxt = nx.group(1).rstrip(".") if nx else ""
    if w == "ex":
        return not (nxt[:1].isdigit() or nxt in EX_FROM)
    if w == "less":
        pv = _WORD_BEFORE.search(text, max(0, m.start() - 12), m.start())
        return nxt != "than" and not (pv and pv.group(1) in ("not", "no"))
    return nxt not in ("as", "where")


def _matches(seg: str) -> list:
    """(start, end, field, word) of every keyword in a part: the longest plain keyword at each position, and the
    word-bounded patterns."""
    out = [(m.start(), m.start() + len(m.group(1)), _PLAIN[m.group(1)], m.group(1)) for m in _KWRX.finditer(seg)]
    for fid, w, rx in _RX:
        for m in rx.finditer(seg):
            a, b = m.span()
            if b > a and not (seg[a].isascii() and seg[a].isalnum()):   # the leading "not a letter" of a word-bounded
                a += 1                                                  # pattern (既存ALC: 存 is not part of ALC)
            if b > a and not (seg[b - 1].isascii() and seg[b - 1].isalnum()):
                b -= 1
            if b > a:
                out.append((a, b, fid, w))
    return out


def _head_of(seg: str, ms: list):
    """(the head among the keyword matches of one part or None, whether the part names a product of no field). The
    head is None when every match only qualifies something else: a place (土間コンクリート下: the next parts are looked
    at), or a product of no field (断熱サッシ, 鉄筋用スペーサー: the name is no material)."""
    kept, product, purposes = [], False, []
    # a material that the word itself excludes (石膏ボード除く, 断熱材を除く, ボード別途, 押出法ポリスチレンフォーム含まず) is no
    # head: every keyword of that word before the excluding ending is left out (15 回目の攻撃)
    cut = [(seg.rfind(" ", 0, a) + 1, b) for a, b, _f, _w in ms if seg.startswith(JA_EXCL_AFTER, b)]
    for a, b, fid, w in ms:
        if cut and any(s <= a and b <= e for s, e in cut):
            continue                                     # 間仕切下地｜LGS 65形（石膏ボード除く）: not a board
        after = seg[b:]
        if after.startswith(PLACE_AFTER) and not after.startswith(PLACE_NOT):
            continue                                     # 土間コンクリート下, コンクリート面
        if after.startswith("用"):
            rest = after[1:].lstrip()
            if not rest:
                continue                                 # 防水用 alone: what it is for
            if not _use_is_form(fid, rest):
                product = True
                purposes.append(b)
                continue                                 # 鉄筋用スペーサー, コンクリート用砕石: not rebar, not concrete
        if w in ADJECTIVES and after.lstrip().startswith(PRODUCT_NOUNS):
            product = True
            continue                                     # アルミ断熱サッシ: an insulated sash, not insulation
        kept.append((a, b, fid, w))
    # a bare form word (ボード) after another material is no head of its own; after a purpose it is the head unless a
    # purpose product follows it (タイル用下地ボード is a board, 断熱用ボード押え金物 is hardware) (14 回目)
    kept = [m for m in kept if not (m[3] in FORM_WORDS and (any(o[2] != m[2] and o[1] <= m[0] for o in kept)
                                                            or (any(e <= m[0] for e in purposes)
                                                                and _product_after(seg, m[1]))))]
    if not kept:
        return None, product
    return max(kept, key=lambda m: (m[1], m[1] - m[0])), False


@functools.lru_cache(maxsize=8192)
def _parts(text: str) -> tuple:
    """(part, follows a preposition of place / purpose or an excluding word?, the preposition before it or "") of a
    lowered name, at most MAX_PARTS non-empty parts. A part after an aside set off by commas ("Infill panels, without
    frames, blockwork 100mm") has the preposition ASIDE: it may name the item or go on with what is excluded."""
    out, pos, place, prep = [], 0, False, ""
    # (the excluding word whose part goes on, the bracket depth it stands in, whether it came right after a comma; the
    # depth of an aside that ended at a comma (-1: none); whether the last split was a run of commas)
    excl, edepth, ecomma, aside, depth, comma = "", 0, False, -1, 0, False
    for m in _SEGSPLIT.finditer(text):
        w = m.group(1) or m.group(2)
        if w in EXCL_PREP and not _excludes(w, text, m):
            continue                       # (ex 50 x 200, not less than, except as noted: no part ends here)
        seg = _PUNCT.sub(" ", text[pos:m.start()]).strip()
        if seg:
            out.append((seg, place, prep))
            if len(out) >= MAX_PARTS:
                return tuple(out)
        ended = False
        if not w:                          # a run of punctuation: the bracket that closes the excluded part, or a ";"
            for ch in m.group(0):          # in it, ends it (a comma does not: a list of what is excluded; but an
                if ch in _OPENING:         # excluding word right after a comma ends at the next one, and what
                    depth += 1             # follows is perhaps the item: ASIDE)
                elif ch in _CLOSING:
                    depth = max(0, depth - 1)
                    if excl and depth < edepth:
                        excl, ended = "", True
                    if depth < aside:
                        aside, ended = -1, True
                elif ch in ";；":
                    if excl and depth <= edepth:
                        excl, ended = "", True
                    if 0 <= aside and depth <= aside:
                        aside, ended = -1, True
                elif ch in ",，、" and excl and ecomma and depth <= edepth:
                    excl, ended, aside = "", True, edepth
        elif w in EXCL_PREP and not excl:
            excl, edepth, ecomma = w, depth, comma and not seg
        comma = not w and all(ch in ",，、" for ch in m.group(0))
        if excl:
            place, prep = True, excl       # (a list after the excluding word: excl. plasterboard, insulation)
        elif w:
            place, prep = w in PLACE_PREP, w
        elif seg or ended:
            place, prep = False, ASIDE if aside >= 0 else ""
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
        if prep == "in" and i and not _matches(parts[i - 1]) and _PRODUCTS_IN_RX.search(parts[i - 1]) \
                and not FILL_WORDS_EN.intersection(parts[i - 1].split()) \
                and (_head_of(seg, _matches(seg))[0] or (0, 0, None))[2] not in MADE_OF:
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
                "木鏝", "直押え", "直均し", "直ならし", "直仕上", "刷毛引", "打放", "打ち放")
# a method word that is the whole item (現場溶接, ガス圧接, 敷込, 取付工) names the work even in a specification
LABOUR_PREFIX = ("現場", "ガス", "工場", "手", "機械", "人力")
LABOUR_SUFFIX = ("工", "作業", "のみ")
_SIZE = re.compile(r"[a-zφ]{0,3}\d[\w.×*/@~\-]*|\d[\w.×*/@~\-]*")    # D19, t12.5, φ600, 100x100, @200
WORK_WORDS = LABOUR_WORDS + METHOD_WORDS
# 打込み in the specification of a material other than concrete names how it is put in place (押出法ポリスチレンフォーム｜
# t50 打込み is cast-in insulation); for concrete it is the placing labour (13 回目)
CAST_IN = ("打込", "打ち込")
_WORKRX = re.compile("|".join(re.escape(w) for w in sorted(WORK_WORDS, key=len, reverse=True)))
# what may follow a method word before 共 / 込 / 別途 (金ごて押え共, 溶接止め込み, 取付工共)
METHOD_TAIL = ("押え", "押さえ", "仕上げ", "仕上", "止め", "止", "張り", "張", "貼り", "貼", "塗り", "塗", "工法", "工")
# のみ / 工 / 作業 / 手間 right after a method word or 打込, with or without its okurigana or a method tail (打込みのみ,
# 打込み工, 打ち込み手間, 敷込みのみ, 取付け工, 金ごて仕上げのみ), names the labour even in a specification (14 回目)
LABOUR_ONLY = ("のみ", "工", "作業", "手間")
OKURIGANA = "みけきしげ"
_LABOUR_TAILS = ("",) + tuple(sorted(METHOD_TAIL, key=len, reverse=True))   # (sorted once: _labour_only runs per match)
_LABOUR_WORDS = frozenset(x + y for x in _LABOUR_TAILS for y in LABOUR_ONLY + ("",))   # (any other word: not labour only)
# … unless the next word is a price note on the material row (取付け工 共, 取付工 込み, 取付け手間 別途, 敷込み工 別途): the
# same as when the note is in the same word (取付工共). Only these whole words, 費 before them, or a word that starts with
# 別途 (別途精算) (14 回目)
LABOUR_NOTE = frozenset(("共", "込", "込み", "含む", "とも", "別途", "は別途", "なし", "無し", "含まず", "含まない", "を除く",
                         "除く"))
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
    r"cut(?:s|ting)?|bend(?:s|ing)?|tying|formwork|shuttering|labou?r|trowel(?:s|led|ling)?|test(?:s|ing)?|sampling)")
WORK_PHRASES_EN = ("power float", "float finish", "floated finish", "trowel finish", "trowelled finish")
# after the material, only a work NOUN makes the row work (Rebar fixing, Steel erection, Concrete pumping, Placing of
# concrete): a participle describes the supply-and-fix item (poured against earth; cut, bent and fixed; laid in slabs;
# fabricated and erected; delivered to site)
_WORK_NOUN_EN = re.compile(r"[a-z]*(?:ing|ion|ment)|labou?r|formwork|shuttering|deliver(?:y|ies)|transport|assembly|pumps?|pours?")
# after the material, a participle describes the supply-and-fix item (poured against earth; cut, bent and fixed; laid in
# slabs); a base verb or a noun names labour (fix only, place and compact, erect only, hoist and fix, Rebar fixing)
_PARTICIPLE_EN = re.compile(r"[a-z]+ed|laid")
# "cut" after the material is the participle when to / into / from and one of these words follow (cut to length / size /
# fit, cut into lengths, cut from plate) or another participle does (cut, bent and fixed); "cut only", "cut and bend" are
# labour (13 回目). cut out / off / back / on / at / in name removal or trimming work or where the labour is done (pile
# cut-off, cut out for opening, cut back to sound concrete, cut on site), and so does cut to / into / from anything else
# (cut to form opening, cut to expose reinforcement, cut to receive lintel, cut from existing): work (14 回目)
CUT_PARTICIPLE_NEXT = {"to": frozenset(("length", "lengths", "size", "sizes", "fit", "suit")),
                       "into": frozenset(("length", "lengths", "piece", "pieces")),
                       "from": frozenset(("plate", "plates", "sheet", "sheets", "bar", "bars", "stock", "coil", "coils"))}
WORK_WORDS_EN = ("placing", "placement", "pumping", "pump", "pour", "pouring", "fixing", "erection", "erect", "erecting",
                 "fabrication", "fabricate", "fabricating", "cutting", "bending", "tying", "labour", "labor", "transport",
                 "delivery", "formwork", "curing", "installation", "hoisting")        # (examples; _WORK_EN decides)
EXCLUDING_EN = ("excluding", "excl", "without", "less", "except", "exclusive", "ex")
# a row that says it supplies the material is a material row even when it also names the work (材工共, supply and erect)
SUPPLY_JA = ("材工共", "材工とも", "材工込", "材料共", "材料とも", "材料込", "材共", "材工一式")
SUPPLY_EN = ("supply", "supplying", "supplied", "provide", "providing", "furnish", "furnishing", "furnished")
# … but not a supply word that is negated or given to others: "placing excluding supply", "fix only, supply by others",
# "supplied by client", "supply measured elsewhere", "free issue supply", "client supplied", 支給材料共: then the work
# rules decide ("… only" is work) (15 回目)
SUPPLY_PARTIES = (("by", "others"), ("by", "client"), ("by", "employer"), ("by", "main", "contractor"), ("elsewhere",),
                  ("measured", "elsewhere"))
_SUPPLY_JA_RX = re.compile("|".join(re.escape(w) for w in sorted(SUPPLY_JA, key=len, reverse=True)))
INCLUSIVE_EN = ("including", "incl", "inclusive", "includes")
INCL_DOT = ("incl.", "inc.")        # (the work check only: after them a removal word stays removal, see _demolish)


def _incl(tok: str) -> bool:
    """including, incl … and the abbreviations incl. and inc. (a word keeps its dot: _PUNCT has no ".") (14 回目)."""
    return tok in INCLUSIVE_EN or tok in INCL_DOT


def _excl(tok: str) -> bool:
    """excluding, excl … and the abbreviations excl. and exc. (14 回目)."""
    return tok in EXCLUDING_EN or tok in ("excl.", "exc.")


def _supply_given_away(toks: list, i: int) -> bool:
    """Whether the supply word toks[i] is negated or given to others (15 回目): after an excluding word (excluding,
    excl., exc., without, less, except, ex), after "free issue" or "client", or followed — directly or after "and" /
    "&" and one word (supply and fabrication by others) — by "by others / client / employer / main contractor",
    "elsewhere" or "measured elsewhere"."""
    if i and (_excl(toks[i - 1]) or toks[i - 1] in EXCL_PREP or toks[i - 1] == "client"):
        return True
    if toks[max(0, i - 2):i] == ["free", "issue"]:
        return True
    for j in (i + 1, i + 3) if toks[i + 1:i + 2] in (["and"], ["&"]) else (i + 1,):
        w = toks[j:j + 4]
        if w[1:2] == ["the"] and w[:1] == ["by"]:
            w = w[:1] + w[2:]                        # (by the client, by the main contractor)
        if any(tuple(w[:len(p)]) == p for p in SUPPLY_PARTIES):
            return True
    return False


def _supply_ja(compact: str) -> bool:
    """A Japanese supply word (材工共, 材料共 …) that is not 支給 (given by the client: 支給材料共) (15 回目)."""
    return any(not compact[:m.start()].endswith("支給") for m in _SUPPLY_JA_RX.finditer(compact))


_PUNCT = re.compile(r"[\s,，、。・/／_\-‐－–—:：;；()（）\[\]［］{}｛｝【】「」『』<>＜＞]+")
_TOKEN = re.compile(r"[^\s,，、。・/／_\-‐－–—:：;；()（）\[\]［］{}｛｝【】「」『』<>＜＞]+")     # (the words _PUNCT leaves)
# where the reach of an inclusive word (including, incl., inc.) ends: a part separator — ; , 、 。 a bracket, a colon
# that is not between two digits (1:3 mortar), a dash with a space beside it (cast-in-place is one word). "Plasterboard
# incl. screws; fix", "Blockwork incl. mortar (labour)": the work word is outside what is included (15 回目)
# … and a line break (a cell written on two lines: "Plasterboard 12.5mm incl. screws⏎Fix") or a full stop that ends a
# sentence (followed by a space or the end, and not the dot of incl. inc. excl. exc. no. nr. approx.: "Reinforcement incl.
# tying wire. Fix") (15 回目の攻撃)
_CLAUSE_SEP = re.compile(r"[;；,，、。()（）\[\]［］{}｛｝【】「」『』<>＜＞\r\n]|(?<!\d)[:：]|[:：](?!\d)|\s[\-‐－–—]|[\-‐－–—]\s"
                         r"|\.(?=\s|$)(?<!\bincl\.)(?<!\binc\.)(?<!\bexcl\.)(?<!\bexc\.)(?<!\bno\.)(?<!\bnr\.)"
                         r"(?<!\bapprox\.)")
# the reach of a spelled including before a removal word ("Floor tiles including adhesive, grout and disposal" is a
# note): only ";" and a round bracket end it, so that the list of what is included keeps its last item (15 回目の攻撃:
# the commas and dashes of _CLAUSE_SEP made that list a removal). Not a line break: within one part of the name a
# removal word after it would be a sure removal ("Plasterboard includes screws⏎disposal"); after ";" or a bracket it is
# in a later part, "maybe" at most
_DEM_CLAUSE_SEP = re.compile(r"[;；()（）]")


def _clauses(n: str, n_toks: int, sep=_CLAUSE_SEP) -> list:
    """The clause of each word of normalise_name(n) (the part between two separators of `sep` it stands in).
    When the words do not line up with normalise_name's (they always do), every word is its own clause (no word is
    then within an inclusive word's reach)."""
    low = unicodedata.normalize("NFKC", (n or "")[:MAX_NAME]).lower()[:MAX_NAME]
    cuts = [m.start() for m in sep.finditer(low)]
    out = [bisect.bisect_right(cuts, m.start()) for m in _TOKEN.finditer(low)]
    return out if len(out) == n_toks else list(range(n_toks))


def _within_incl(toks: list, clause: list, i: int) -> bool:
    """Whether the word toks[i] is within the reach of an inclusive word before it: in the same clause (14 回目 let
    any earlier incl. reach every later word, so "incl. screws; fix" was the material row) (15 回目)."""
    return clause is not None and any(_incl(toks[j]) and clause[j] == clause[i] for j in range(i))


def normalise_name(name: str) -> str:
    """NFKC (full-width letters and digits, ㎥ …), lower case, punctuation as single spaces; at most MAX_NAME characters
    (cut before and after NFKC, which can lengthen a string)."""
    n = unicodedata.normalize("NFKC", (name or "")[:MAX_NAME]).lower()[:MAX_NAME]
    return _PUNCT.sub(" ", n).strip()


def _prep(s: str) -> str:
    """NFKC once, cut before and after (the checks then work on at most MAX_NAME characters)."""
    return unicodedata.normalize("NFKC", (s or "")[:MAX_NAME])[:MAX_NAME]


# a space-justified Japanese text: the usual 内訳書 spaces a short name out to the width of its column (撤　　去, 加　工　組　立,
# 鉄　　骨, 取　付　手　間). A run of two or more words of ONE kanji or kana each, with only spaces between them, is one word;
# words of two or more letters keep their spaces (既存　撤去; コンクリート　打　設 is コンクリート 打設). The material is read
# from the closed-up text; a mark that leaves a row out (合計, 再掲・うち・内, 控除, 撤去, 作業) is looked for in the text as
# written AND closed up, so that closing up never loses one (内　柱 is still "of which columns") (15 回目)
# (hiragana, katakana with its long-vowel mark but not the middle dot, the iteration mark, the CJK ideographs)
_JCHAR = "".join("%s-%s" % (chr(a), chr(b)) for a, b in ((0x3041, 0x3096), (0x309D, 0x309F), (0x30A1, 0x30FA),
                                                          (0x30FC, 0x30FF), (0x3005, 0x3005), (0x3400, 0x4DBF),
                                                          (0x4E00, 0x9FFF), (0xF900, 0xFAFF)))
_JUSTIFIED = re.compile(r"(?<!\S)[%s](?:\s+[%s](?!\S))+" % (_JCHAR, _JCHAR))
_SPACES = re.compile(r"\s+")


def _justify(s: str) -> str:
    """The text with each space-justified run of single kanji / kana closed up (撤　　去 is 撤去)."""
    return _JUSTIFIED.sub(lambda m: _SPACES.sub("", m.group(0)), s) if s else s


def _both(check, s: str):
    """check(s) or, when closing up changes s, check of the closed-up text (a mark is found in either)."""
    got = check(s)
    j = _justify(s)
    return (got or check(j)) if j != s else got


_RANK = {None: 0, False: 0, "maybe": 1, "sure": 2}


def _stronger(a, b):
    """The stronger of two answers None / MAYBE / SURE."""
    return a if _RANK.get(a, 0) >= _RANK.get(b, 0) else b


def _classify(text: str, division: str = "", n_name: int | None = None) -> str | None:
    """The field of an NFKC-normalised name (the head of its first part that names a material). With `n_name` (the
    number of parts of the name), a うち / 内 / of which note in the specification is left out of the words that say
    foundation: 普通コンクリート｜Fc24（うち基礎 40m3） is not foundation concrete (14 回目)."""
    fid = _head(text)[0]
    if fid == "m_concrete":
        parts = _outside_notes(text, MAX_PARTS if n_name is None else n_name)   # (without the excluded parts)
        low = normalise_name(division) + " " + " ".join(parts)
        if any(w in low for w in FOUNDATION_WORDS):
            return "m_concrete_fdn"
    return fid


def _outside_notes(text: str, n_name: int) -> list:
    """The parts of a name ; specification, with each part of the specification cut at its うち / 内 / 内訳 word and
    without a part that starts "of which", and without a part after an excluding word (15 回目)."""
    out = []
    for j, (seg, _place, prep) in enumerate(_parts(text.lower()[:MAX_NAME])):
        if prep in EXCL_PREP:
            continue
        if j >= n_name:
            ws = seg.split()
            if prep == "of" and ws[:1] == ["which"]:
                continue
            for q, w in enumerate(ws):
                if (w.startswith("うち") and not w.startswith(_UCHI_WORDS)) or w == "内" or w.startswith("内訳"):
                    ws = ws[:q]
                    break
            seg = " ".join(ws)
        out.append(seg)
    return out


def _field_for(name: str, division: str = "") -> str | None:
    return _classify(_justify(_prep(name)), _justify(_prep(division)))     # (撤　　去, 鉄　　骨 closed up: 15 回目)


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
    return _both(_total, _prep(name))


MAX_ROWS_CLASSIFIED = 20_000          # quantity rows classified per document (a real bill of quantities is far smaller)
MAX_PREP_CHARS = 3_000_000            # characters normalised (NFKC) per document: distinct texts only, each once


# one okurigana after a labour word, before the next word of the run or the note after it (打込み手間共, 打込み共,
# 打込み別途: as 打込手間共, 打込共, 打込別途) (15 回目)
CHAIN_OKURIGANA = "みけてし"


def _chain_end(seg: str, e: int, word: str = "") -> tuple:
    """(the end of a run of work words that starts before e with `word`, its last word) (加工組立, 製作・建方, ポンプ打設,
    打設及び養生, 打込み手間: one okurigana after a labour word, 15 回目)."""
    while True:
        e1 = e + 1 if word in LABOUR_WORDS and seg[e:e + 1] and seg[e] in CHAIN_OKURIGANA else e
        m = _CHAIN_SEP.match(seg, e1)
        e2 = m.end() if m else e1
        w2 = _WORKRX.match(seg, e2) or _CHAIN_MORE.match(seg, e2)
        if not w2 or w2.end() == e2:
            return e, word
        e, word = w2.end(), w2.group(0)


@functools.lru_cache(maxsize=8192)
def _work(n: str, n_name: int | None = None) -> bool:
    """`n` is the name, or "name ; specification" with `n_name` the number of parts of the name (the parts after
    them are the specification)."""
    fid, hs, a, b, parts = _head(n)
    if n_name is None:
        n_name = len(parts)
    norm = normalise_name(n)
    toks = norm.split()                            # the whole name: "including" is where the parts split
    clause = _clauses(n, len(toks)) if any(_incl(t) for t in toks) else None
    spec_words = " ".join(parts[n_name:]).split()  # (the words of the specification)
    compact = re.sub(r"\s+", "", n)
    if _supply_ja(compact) or any(t in SUPPLY_EN and not _supply_given_away(toks, i) for i, t in enumerate(toks)):
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
        if i and _excl(toks[i - 1]):
            continue                               # "excluding placing", "excl. placing": the material without its placing
        if " ".join(toks[i + 1:i + 3]) in ("by others",) or (i + 1 < len(toks) and toks[i + 1] == "separately"):
            continue
        if t.endswith("ed") and head_tok is not None and i < head_tok:
            continue                               # "fabricated steelwork", "pumped concrete": the material
        if t in ("place", "placed") and i and toks[i - 1] == "in":
            continue                               # "cast-in-place concrete", "in-place concrete": the material
        if t in ("test", "tests") and toks[i + 1:i + 2] and toks[i + 1].startswith("pile"):
            continue                               # "test piles" are piles (試験杭), not testing
        if head_tok is not None and i > head_tok and toks[i + 1:i + 2] != ["only"] and (
                _PARTICIPLE_EN.fullmatch(t)
                or (t == "cut" and (toks[i + 2:i + 3] and toks[i + 2] in CUT_PARTICIPLE_NEXT.get(toks[i + 1], ())
                                    and toks[i + 3:i + 4] != ["only"]
                                    or any(_PARTICIPLE_EN.fullmatch(x) or x == "bent" for x in toks[head_tok + 1:])))
                or (t.endswith("s") and not _WORK_NOUN_EN.fullmatch(t) and t != "tests")):
            continue                               # "concrete C20; poured against earth", "bars; cut, bent and fixed",
            #                                        "thrust blocks to drainage bends" (a plural noun, not a verb)
        if toks[i + 1:i + 2] != ["only"] and _within_incl(toks, clause, i):
            continue                               # "concrete including placing and compacting", "incl. cube testing"
            #                                        (but "incl. screws; fix only" is the labour, 14 回目, and so is
            #                                        "incl. screws; fix": outside what is included, 15 回目)
        return True
    for i, seg in enumerate(parts):
        m = _WORKRX.search(seg)
        while m:
            k, e = m.span()
            cast = m.group(0) in CAST_IN and 0 <= hs < len(parts) \
                and not any(c in parts[hs][a:b] for c in ("コンクリート", "生コン", "concrete"))
            method = m.group(0) in METHOD_WORDS or cast
            if i >= n_name and method and 0 <= hs < n_name and parts[hs][a:b] not in ("仕上", "finish") \
                    and not _bare_method(seg, k, e) and not _labour_only(seg, k, e, parts[i + 1] if i + 1 < len(parts) else "") \
                    and not (cast and _cast_alone(spec_words, m.group(0))):
                m = _WORKRX.search(seg, e)         # 床下敷込, 溶接止め, 金ごて仕上 in the specification of a named material
                continue
            in_head = i == hs and k < b and e > a
            # a work word inside the head's own word, before the material, qualifies it (加工鉄筋, 型枠ブロック)
            # (but not before 仕上: 金ごて仕上・打放し仕上 are labour on the slab, no finish material)
            modifier = i == hs and e <= a and seg.rfind(" ", 0, a) < k and seg[a:b] not in ("仕上", "finish")
            end, last = _chain_end(seg, e, m.group(0))
            after = seg[end:]
            if last in LABOUR_WORDS and after[:1] and after[0] in CHAIN_OKURIGANA:
                after = after[1:]                  # 打込み共, 打込み別途, 加工組立て 込み (15 回目)
            if m.group(0) in METHOD_WORDS and after.startswith(METHOD_TAIL):
                after = after[next(len(x) for x in METHOD_TAIL if after.startswith(x)):]   # 金ごて押え共
            if after.startswith("費"):
                after = after[1:]                  # 運搬費込, 打設費別
            before = seg[:k].rstrip()
            excluded = after.lstrip().startswith(EXCLUDED_AFTER) or before.endswith(("別途", "除く", "除き"))
            # … and a price note as the next word (加工組立て 込み, 製作 建方 共: as 加工組立て込み, 製作建方共) (15 回目)
            noted = last in LABOUR_WORDS and after[:1].isspace() and _labour_note(after.split()[:1])
            if not in_head and not modifier and not excluded and not noted and not after.startswith(PRODUCT_AFTER):
                return True
            m = _WORKRX.search(seg, max(end, k + 1))
    return False


def _bare_method(seg: str, k: int, e: int) -> bool:
    """Whether the method word at seg[k:e] is the whole word it stands in (現場溶接, ガス圧接, 敷込, 取付工): the item is the
    work. 床下敷込, 溶接止め, 金ごて仕上, 試験杭 say how (or as what) the material is put in place."""
    ws = seg.rfind(" ", 0, k) + 1
    we = seg.find(" ", e)
    core = seg[ws:len(seg) if we < 0 else we]
    word = seg[k:e]
    for p in LABOUR_PREFIX:
        if core.startswith(p) and core[len(p):].startswith(word):
            core = core[len(p):]
            break
    if not (core == word or any(core == word + x for x in LABOUR_SUFFIX)):
        return False
    # the rest of the part is only sizes (ガス圧接 D19): the item is the work; anything else describes the material
    # (石膏ボード｜t12.5 GL工法 取付 is the board, fixed by GL bonding)
    rest = (seg[:ws] + " " + seg[len(seg) if we < 0 else we:]).split()
    return all(_SIZE.fullmatch(x) for x in rest)


def _labour_note(words: list) -> bool:
    """Whether the first of these words is a price note on the material row (共, 込み, 別途, 費別途 …: LABOUR_NOTE, and
    a word that starts with 別途)."""
    w = words[0] if words else ""
    if w[:1] == "費":
        w = w[1:]
    return w in LABOUR_NOTE or w.startswith(("別途", "は別途"))      # (別途精算, 別途工事)


def _labour_only(seg: str, k: int, e: int, later: str = "") -> bool:
    """Whether the method word at seg[k:e] is followed in its word by のみ / 工 / 作業 / 手間, after its okurigana or a
    method tail if any (打込みのみ, 打込み工, 打ち込み手間, 敷込みのみ, 取付け工, 金ごて仕上げのみ), or by a next word のみ / 作業
    (打込み のみ): the item is the labour, whatever else the specification says (14 回目). Not when the next word is a
    price note on the material row (取付け工 共, 取付け手間 別途: as 取付工共). `later` is the next part (the next word may
    be there: 取付け工、共)."""
    we = seg.find(" ", e)
    t = seg[e:len(seg) if we < 0 else we]
    if t[:1] and t[0] in OKURIGANA:
        t = t[1:]
    if t not in _LABOUR_WORDS:
        return False                                 # (the loop below could not find のみ / 工 / 作業 / 手間 or the word end)
    for tail in _LABOUR_TAILS:
        if t.startswith(tail):
            rest = t[len(tail):]
            if rest in LABOUR_ONLY:
                return not _labour_note(_next_words(seg, we, later))
            if not rest:
                nxt = _next_words(seg, we, later)
                return nxt[:1] in (["のみ"], ["作業"]) and not _labour_note(nxt[1:])
    return False


_NEXT2 = re.compile(r"\s*(\S+)(?:\s+(\S+))?")


def _next_words(seg: str, we: int, later: str) -> list:
    """The (at most two) words after seg[:we], going on into `later` (the next part) (a bounded match, not a split)."""
    m = _NEXT2.match(seg, we) if we >= 0 else None
    out = [w for w in m.groups() if w] if m else []
    if len(out) < 2:
        m = _NEXT2.match(later)
        out += [w for w in m.groups() if w][:2 - len(out)] if m else []
    return out


def _cast_alone(spec_words: list, word: str) -> bool:
    """Whether the specification is only 打込 / 打込み (with a labour prefix if any): the item is the placing labour, as in
    12 回目 (with a size, 押出法ポリスチレンフォーム｜t50 打込み is the cast-in material) (14 回目)."""
    if len(spec_words) != 1:
        return False
    w = spec_words[0]
    for p in LABOUR_PREFIX:
        if w.startswith(p) and w[len(p):].startswith(word):
            w = w[len(p):]
            break
    return w == word or (w[:-1] == word and w[-1] in OKURIGANA)


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
        nm, sp = _prep(name), _prep(spec)
        if _work(nm + " ; " + sp, len(_parts(nm.lower()[:MAX_NAME]))):
            return True
        jn, js = _justify(nm), _justify(sp)                     # (加　工　組　立: 15 回目)
        return (jn, js) != (nm, sp) and _work(jn + " ; " + js, len(_parts(jn.lower()[:MAX_NAME])))
    return bool(_both(_work, _prep(name)))


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
# … matched as whole words (not strip outlet), and where they stand: in a part of place or after the material at most
# "maybe" (Plasterboard 12.5mm; take down ceiling: perhaps a note on the material row). Followed by one of these words
# they name a room or place, not removal: no removal in a part of place or after the material ("Carpet tiles to
# break-out area"), and "maybe" elsewhere ("Break-out area: carpet tiles"). 15 回目 made every one a sure removal, also
# in IFC names (16 回目)
DEMOLISH_PLACE_EN = ("area", "room", "space", "zone", "lounge", "bay")
_DEM_PHRASE = re.compile(r"(?<![a-z0-9])(?:%s)s?(?![a-z0-9])(\s+(?:%s)s?(?![a-z0-9]))?"
                         % ("|".join(re.escape(p) for p in DEMOLISH_PHRASES_EN),
                            "|".join(re.escape(p) for p in DEMOLISH_PLACE_EN)))
_DEMRX = re.compile("|".join(re.escape(w) for w in sorted(DEMOLISH_JA, key=len, reverse=True)))
# a removal word followed by these is a price note on a material row (端材処分共, 殻処分費別途, 処分費込み)
NOTE_AFTER_JA = ("共", "込", "含", "とも", "別途", "は別", "別", "を除く", "除く", "除き", "なし", "無し")
_DEM_CHAIN = re.compile(r"[\s・、,＋+&]*(?:%s|運搬|積込|積み込み|費)" % "|".join(re.escape(w) for w in DEMOLISH_JA))
NOTE_OF_EN = ("offcuts", "off", "surplus", "waste", "packaging", "arisings", "excess", "cuttings")
DEMOLISH_STRONG = ("撤去", "解体", "はつり", "斫り", "斫", "取壊", "取り壊", "取りこわ")   # never a price note
# (殻 is removal in the name: コンクリート殻運搬・処分共; after the material, 殻処分費別途 is a price note on the row)
DEMOLISH_WEAK_EN = frozenset(("disposal", "dispose", "disposed", "disposing"))
# a removal word followed by 後 / の上 and a new installation (撤去後 新設, 撤去の上 新規, 撤去後に張替え): see _demolish
_SEQ_NEW = re.compile(r"\s*(?:後に?|の上|のうえ)\s*(新設|新規|張替|張り替|取替|取り替|更新|やり替)(え?)")
# … the rest of that word may only be one of these (新設共, 新設込み: the row includes the new installation) (14 回目), or
# one of these longer forms of the new installation (新規張り, 新規施工, 新設取付, 張替え工事) (15 回目)
SEQ_ATTACHED = ("", "共", "とも", "込", "込み", "含む", "は含む")
SEQ_LONGER = {"新規": ("張り", "貼り", "施工", "設置", "取付", "取付け"), "新設": ("取付",), "張替え": ("工事",)}
# … and after it the specification may hold only these words: one of SEQ_ATTACHED, a size or grade (t12.5, Fc24, 3種b,
# 12.5 mm) or a disposal price note (処分共, 処分費込み). Any other word may say that the new installation is not in this
# row (他工事, B工事, 次項, 支給品, 計上せず, 別途 …): 14 回目 read every word not on a short list of such notes as "in this
# row" (15 回目)
_SEQ_PRICE = re.compile(r"(?:残材|端材|発生材)?処分費?(?:共|とも|込|込み|含む|別途)")
# (a size or grade has a prefix or a unit: a bare number, No12 or a dash may say "none" or point to another item)
_SEQ_SIZE = re.compile(r"(?:t|fc|d|sd|φ|@)\d+(?:\.\d+)?|\d+(?:\.\d+)?(?:mm|cm|kg|種[a-z]?)|\d+(?:\.\d+)?[x×*]\d+(?:\.\d+)?(?:mm)?")
_SEQ_DASH = re.compile(r"[\-‐－–—―]")
EXISTING_WORDS = ("既存", "既設")
# … and a name marked as what is there by these words also stays removal (在来石膏ボード, 旧石膏ボード, 石膏ボード 現状) (15 回目)
SEQ_EXISTING = ("在来", "旧", "現況", "現状")
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
    if any(_both(_again, _prep(t)) for t in texts):
        return "再掲・内数（うち・内訳）の行は足さない（ほかの行に含まれている。二重計上を防ぐ）"
    return None


_DEDUCT_NOTE = re.compile(r"発生材(?:の)?(?:処分|運搬|積込|片付け?)+費?(?:共|込|含|とも|別途|は別|別)")
# in a specification (摘要), a price note: スクラップ控除別途, スクラップ控除なし, 控除後 … (14 回目); with は / を between
# (スクラップ控除は別途, 控除を含む) and せず, しない, 含まず, 済, 済み (スクラップ控除せず, 控除済) (15 回目)
_DEDUCT_PRICE = re.compile(r"(?:(?:売却|評価|買取|引取|有価)(?:益|額|代|分|価格|物)?)?控除(?:は|を)?"
                           r"(?:別途|なし|無し|共|含む|込み?|後|せず|しない|含まず|済み?)")
#                            (スクラップ評価控除後, スクラップ売却益控除別途, スクラップ評価額控除後, 有価物控除なし: the same
#                            price note, 15 回目の攻撃)
# … but not on a row that names the scrap itself (鉄筋スクラップ, 鉄くず; not スクラップ処分, a price note on work)
_SCRAP_NAME = re.compile(r"(?:スクラップ|くず|屑)(?!\s*(?:処分|運搬|積込|積み込|片付|搬出))")
# … and a reference to another document, not a breakdown row (14 回目)
_AGAIN_REF = re.compile("|".join(r"\s*".join(w) for w in ("内訳書による", "内訳別紙", "内訳書参照", "別紙内訳", "別紙による")))
# the marks that say outright that the row repeats a quantity listed elsewhere: sure in the specification as well
AGAIN_EXPLICIT_EN = tuple(w for w in AGAIN_EN if w not in ("of which", "see item"))


# a sale or valuation of the scrap is its credit: スクラップ売却, スクラップ買取, 鉄筋スクラップ｜評価, 鉄くず｜有価物 (15 回目)
SCRAP_SALE = ("売却", "評価", "買取", "買い取", "引取", "引き取", "有価")


def _scrap_sale(n: str) -> bool:
    """Whether a sale / valuation word (売却, 評価, 買取, 引取, 有価) comes after the scrap (スクラップ, くず, 屑; not
    スクラップ処分 or 運搬)."""
    compact = _SPACES.sub("", n)
    m = _SCRAP_NAME.search(compact)
    return bool(m) and any(w in compact[m.end():] for w in SCRAP_SALE)


@functools.lru_cache(maxsize=8192)
def _scrap_itself(n: str) -> bool:
    """Whether a name names the scrap itself: its first scrap word is in the word of its material or before it, or it
    names no material (鉄筋スクラップ, スクラップ 鉄筋, スクラップ買取, 鉄くず). A scrap word after the material in a later word
    is a note on the material row, as in a specification (one name column: 異形鉄筋 SD345 D13 スクラップ買取共) (15 回目の
    攻撃)."""
    fid, hi, _a, b, parts = _head(n)
    for j, seg in enumerate(parts):
        m = _SCRAP_NAME.search(seg)
        if m:
            if fid is None or hi < 0 or j < hi:
                return True
            if j > hi:
                return False
            we = seg.find(" ", b)
            return m.start() < (len(seg) if we < 0 else we)
    return False


@functools.lru_cache(maxsize=8192)
def _deduct(n: str, spec: bool = False) -> bool:
    toks = normalise_name(n).split()
    compact = _DEDUCT_NOTE.sub("", re.sub(r"\s+", "", n))    # 発生材処分別途: a price note, not a credit
    if spec:
        compact = _DEDUCT_PRICE.sub("", compact)
    # (a sale after the scrap: in a name only when the name is the scrap itself, 15 回目の攻撃)
    return any(w in compact for w in DEDUCT_JA) or any(t in DEDUCT_EN for t in toks) or (toks[:1] == ["less"]) \
        or (_scrap_sale(compact) and (spec or _scrap_itself(n)))


@functools.lru_cache(maxsize=8192)
def _again_spec(n: str):
    """None, SURE or MAYBE for a specification (摘要): a reference (内訳書による, 別紙内訳 …) is no breakdown; an
    explicit mark (再掲, 別掲, (再), 上記に含む, 内数, included above …) is SURE; うち・内訳・of which may be a note on the
    material row itself (Fc24（うち基礎 40m3）): MAYBE (14 回目)."""
    t = _AGAIN_REF.sub(" ", n)
    if not _again(t):
        return None
    compact, low = re.sub(r"\s+", "", t), t.lower()
    if any(w in compact for w in AGAIN_JA) or any(w in low for w in AGAIN_EXPLICIT_EN):
        return SURE
    return MAYBE


def _is_deduction(*texts: str) -> bool:
    """A deduction (スクラップ控除, 発生材, 差引, deduct, credit, "less …"), often written with a positive quantity and a
    negative price: never added and never subtracted silently."""
    return any(_both(_deduct, _prep(t)) for t in texts)


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


def _seq_after(w: str) -> bool:
    """Whether a word after 撤去後 新設 leaves the new installation in this row: SEQ_ATTACHED, a size or grade, a disposal
    price note."""
    return w in SEQ_ATTACHED or bool(_SEQ_SIZE.fullmatch(w)) or bool(_SEQ_PRICE.fullmatch(w))


def _seq_new(parts: tuple, i: int, seg: str, e: int, cut: bool = False, raw: str = "") -> bool:
    """Whether the removal word that ends at seg[:e] (part i) is followed by 後 / の上 and a new installation that is in
    this row: nothing but SEQ_ATTACHED, sizes and disposal price notes after it (撤去後 新設, 撤去後新設共, 撤去の上 新規,
    撤去後 新設 t12.5); not 新設は別途, 新設 別途, 張替え別途工事, 新設（別途）, 新設なし (14 回目), 新設 他工事, 新設 B工事,
    新設 次項, 新設 - (15 回目). `cut`: the text is not read to its end (the note may go on); `raw`: the lowered text with
    its punctuation (a dash after the new installation is a word: "none")."""
    m = _SEQ_NEW.match(seg, e)
    if not m or cut:
        return False
    we = seg.find(" ", m.end())
    rest = seg[m.end():len(seg) if we < 0 else we]
    word = m.group(1) + m.group(2)
    if rest not in SEQ_ATTACHED and rest not in SEQ_LONGER.get(word, ()):
        return False
    after = (seg[we:].split() if we >= 0 else []) + " ".join(parts[i + 1:]).split()
    if not all(_seq_after(w) for w in after):
        return False
    k = raw.rfind(word + rest)
    return k >= 0 and not _SEQ_DASH.search(raw, k + len(word + rest))


@functools.lru_cache(maxsize=8192)
def _dem_kind(n: str, n_name: int | None = None) -> tuple:
    """(_demolish's answer, whether its MAYBE comes only from a removal phrase that names a room or place: Break-out
    area: carpet tiles) (16 回目)."""
    fid, hs, _a, _b, parts = _head(n)
    norm = normalise_name(n)
    toks = norm.split()
    found, other = None, False
    existing = 0 <= hs < len(parts) and ("既存" in parts[hs][:_a] or "existing" in parts[hs][:_a].split())

    def kind(i):
        return MAYBE if 0 <= hs < i and not existing else SURE

    # in the specification of a name with no removal word that does not name what is there (既存, 既設, existing
    # anywhere in it), 撤去後 新設 says in which order the work is done: the row is the new material (既存撤去後 新設,
    # 既存防水撤去の上 新規). Not when the new installation is said to be elsewhere (新設は別途, 新設 別途) (14 回目)
    nn = len(parts) if n_name is None else min(n_name, len(parts))
    name_txt = " ".join(parts[:nn])
    seq_ok = nn < len(parts) and not existing and not any(w in name_txt for w in EXISTING_WORDS + SEQ_EXISTING) \
        and "existing" not in name_txt.split() \
        and not _DEMRX.search(name_txt) and not any(t in DEMOLISH_EN for t in name_txt.split()) \
        and not any(p in name_txt for p in DEMOLISH_PHRASES_EN)
    cut = len(n) > MAX_NAME or len(parts) >= MAX_PARTS      # (not read to its end: what follows 新設 is not known)
    for i, seg in enumerate(parts):
        for m in _DEMRX.finditer(seg):
            e = m.end()
            while True:
                c = _DEM_CHAIN.match(seg, e)
                if not c or c.end() == e:
                    break
                e = c.end()
            if seq_ok and i >= nn and _seq_new(parts, i, seg, e, cut, n.lower()):
                continue
            after, before = seg[e:].lstrip(), seg[:m.start()].rstrip()
            run = seg[m.start():e]
            strong = any(w in run for w in DEMOLISH_STRONG) or ("殻" in run and kind(i) == SURE)
            if not strong and (after.startswith(NOTE_AFTER_JA) or before.endswith(("別途", "別"))):
                continue                         # 端材処分共, 別途処分: a price note
            k = kind(i)
            if k == SURE:
                return SURE, False
            found, other = MAYBE, True
    where = None
    # "including disposal" is a note on the material row, but not on a row of what is there (Existing floor tiles
    # including disposal, Floor tiles (existing) including removal). incl. / inc. with their dot are no such note here:
    # a removal word after them stays removal (Existing floor tiles; take up incl. disposal; "incl. disposal of surplus"
    # is a note by NOTE_OF_EN) (14 回目)
    j_incl = next((j for j, x in enumerate(toks) if x in INCLUSIVE_EN), None)
    note_ok = j_incl is not None and not existing
    # … and only within what follows it, up to the next ";" or round bracket (15 回目: Floor tiles including adhesive;
    # take up and dispose is the removal; a comma, a dash or a line break does not end it: including adhesive, grout and
    # disposal is the note, 15 回目の攻撃)
    clause = _clauses(n, len(toks), _DEM_CLAUSE_SEP) if note_ok else None
    if note_ok and "existing" in toks[:j_incl]:      # … in a part that says what the item is, not where it goes
        where = _token_parts(toks, parts)            # (Floor tiles to existing floor including disposal: new tiles)
        place = [pl for _s, pl, _p in _parts(n.lower()[:MAX_NAME])]
        note_ok = not any(t == "existing" and where[q] is not None and not place[where[q]]
                          for q, t in enumerate(toks[:j_incl]))
    for i, t in enumerate(toks):
        if t not in DEMOLISH_EN:
            continue
        nxt = toks[i + 1:i + 3]
        if (note_ok and any(toks[j] in INCLUSIVE_EN and clause[j] == clause[i] for j in range(i))) \
                or (nxt[:1] == ["of"] and toks[i + 2:i + 3] and toks[i + 2] in NOTE_OF_EN):
            continue                             # "including disposal", "removal of offcuts": a note
        if t in DEMOLISH_WEAK_EN and (" ".join(nxt) in ("by others",) or nxt[:1] in (["separately"], ["elsewhere"])):
            continue                             # "disposal by others": a price note
        if where is None:
            where = _token_parts(toks, parts)
        k = kind(where[i]) if where[i] is not None else SURE
        if k == SURE:
            return SURE, False
        found, other = MAYBE, True
    by_place = False
    for m in _DEM_PHRASE.finditer(norm):
        # where the phrase stands: in a part of place (or an excluded part), or after the material's head word (16 回目)
        if where is None:
            where = _token_parts(toks, parts)
        q = len(norm[:m.start()].split())
        j = where[q] if q < len(where) else None
        in_place = j is not None and _parts(n.lower()[:MAX_NAME])[j][1]
        head_end = None
        if 0 <= hs < len(parts) and _b > _a:
            nth = len(parts[hs][:_b].split())
            mine = [x for x, p_ in enumerate(where) if p_ == hs]
            head_end = mine[nth - 1] if 0 < nth <= len(mine) else None
        after = head_end is not None and q > head_end
        if m.group(1):                   # break-out area, strip out zone: the name of a place
            if not (in_place or after) or existing:
                found, by_place = MAYBE, True    # (Break-out area: carpet tiles; Existing slab, break out area)
            continue
        if (in_place or after) and not existing:
            found, other = MAYBE, True   # (Plasterboard 12.5mm; take down ceiling: perhaps a note on the material row)
            continue
        return SURE, False
    return found, found == MAYBE and by_place and not other


def _demolish(n: str, n_name: int | None = None):
    """None, SURE (removal of what is there: 既存コンクリート撤去, コンクリート殻処分, Demolition of existing slab) or MAYBE (a
    removal word only after the material, in a later part or the specification: perhaps a note on the material row).
    Not removal: a price note (端材処分共, 殻処分費別途, 別途処分, including disposal of surplus, disposal of offcuts by
    others)."""
    return _dem_kind(n, n_name)[0]


def _dem_place(forms) -> bool:
    """Whether every MAYBE of _demolish over these (name, specification) forms (closed up and as written) comes only from
    a removal phrase that names a room or place (16 回目)."""
    kinds = {_dem_kind(nm + " ; " + sp if sp else nm, len(_parts(nm.lower()[:MAX_NAME])) if sp else None)
             for nm, sp in forms}
    return any(k == MAYBE for k, _f in kinds) and all(f for k, f in kinds if k == MAYBE)


def _is_demolition(*texts: str) -> bool:
    """Removal of what is there (撤去, 解体, はつり, 殻, 処分, demolition, break out, removal, disposal, rubble): not a new
    material, never added. A price note is not removal (端材処分共, 殻処分費別途, including disposal of surplus)."""
    return any(_both(_demolish, _prep(t)) for t in texts)


def _unit(u: str) -> str | None:
    """ｍ３, ㎥, m³, Ｍ３ … are m3 (NFKC), likewise m2, t, kg."""
    k = unicodedata.normalize("NFKC", (u or "")[:40]).strip().lower().replace(" ", "")
    return UNIT_ALIASES.get(k)


class _Budget(Exception):
    pass


class _Prep:
    """NFKC of each distinct text once per document, within a character budget (an upload must not hold the worker)."""

    def __init__(self, budget: int = MAX_PREP_CHARS):
        self.cache, self.left, self.charged = {}, budget, set()

    def charge(self, s: str) -> None:
        """Charge a text read once more (a closed-up text, read again for its marks) to the same budget, once per
        distinct text (15 回目の攻撃)."""
        if s not in self.charged:
            self.charged.add(s)
            self.left -= len(s)
            if self.left < 0:
                raise _Budget()

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


def _family(fid):
    """The material a field holds, as the engine sees it (its material class): コンクリート（上部構造）and コンクリート
    （基礎・杭）are one material in two fields (the only such pair: every other field has its own class)."""
    if fid is None:
        return None
    return FL.FIELDS.get(fid, {}).get("material_class") or fid


_GETPIVOT = re.compile("GETPIVOTDATA", re.I)
R_GETPIVOT_UNKNOWN = "GETPIVOTDATA の参照先にピボットテーブルが見つからないので確かめられない。必要なら手で入れる"
MAX_PENDING = 2                        # rows whose dimensions one block keeps (two rows already make a copy)
MAX_DIM_ROWS = 8                       # rows whose single dimension a formula's frame keeps
MAX_SOURCES = 16                       # blocks reached by adding that a formula's frame keeps (more: only flagged)
HELPER_CELLS = 4_096                   # cells of a block looked at one by one (whether all are formula cells)
HELPER_STEPS = 1_000_000               # rectangles kept and looked at by _Helpers per document (a budget of its own)
_CB, _RB = 16, 64                      # columns and rows of one bucket of _Helpers' index
MAX_BUCKETS = 16                       # a rectangle over more buckets is kept in a list of its own (a whole column …)
UNION_CELLS = 64                       # a block up to this size may be held by several kept rectangles together
UNION_RECTS = 16                       # … of at most this many
PICKED, SCALED, ALONE = tabular.PICKED, tabular.SCALED, tabular.ALONE
# how a counted row sums a kept rectangle (see _helper_parts): surely, perhaps, or chosen by a criterion / looked up
PART_SURE, PART_MAYBE, PART_CHOSEN = 2, 1, 0


def _col_letters(c: int) -> str:
    s, c = "", c + 1
    while c:
        c, r = divmod(c - 1, 26)
        s = chr(65 + r) + s
    return s


def _cells_label(disp: dict, blk) -> str:
    """明細 C3:C5, 階別 B2:D2, 階別 B:B (a block as said in a reason)."""
    t, c1, c2, r1, r2 = blk
    if r1 <= 1 and r2 >= tabular.MAX_ROW_NUMBER:
        at = "%s:%s" % (_col_letters(c1), _col_letters(c2))
    else:
        at = "%s%d" % (_col_letters(c1), r1) + ("" if (c1, r1) == (c2, r2) else ":%s%d" % (_col_letters(c2), r2))
    return "%s %s" % (tabular.sheet_label(disp.get(t, t)), at)


class _HelperBudget(Exception):
    """_Helpers went over its budget (HELPER_STEPS)."""


class _Rects:
    """The rectangles kept for one material family on one sheet: each distinct rectangle once ([c1, c2, r1, r2, owner,
    how it is summed: PART_SURE / PART_MAYBE / PART_CHOSEN]) in `seen`. A single cell is filed in `cells` by its bucket
    (_CB columns × _RB rows); a larger rectangle in `grid`, in each bucket it lies over, or in `big` when it lies over
    more than MAX_BUCKETS of them. `ckeys` / `gkeys` list the filled row buckets of each column bucket (sorted)."""
    __slots__ = ("seen", "cells", "ckeys", "grid", "gkeys", "big")

    def __init__(self):
        self.seen, self.cells, self.ckeys, self.grid, self.gkeys, self.big = {}, {}, {}, {}, {}, []


class _Helpers:
    """The cells that counted material rows SUM from rows that are no material rows (a helper sheet with no bill header,
    per-floor take-off 部位｜1F｜2F｜3F, hidden detail rows, lines without a unit), per material family, as rectangles:
    which counted row summed them, and how (see _helper_parts: surely, perhaps, or chosen by a criterion / looked up)
    (15 回目: two quantities that summed the same cells were both added).
    Every rectangle kept and every bucket and rectangle looked at costs one step of a budget of its own (15 回目の攻撃:
    the cells were kept and looked at one by one, 4,096 per block, on the walk's budget, so that a sheet of conditional
    sums used it up and unrelated rows were no longer checked). When the budget runs out, nothing more is kept and a
    quantity that reaches such cells cannot be checked (see read)."""

    def __init__(self, budget: int = HELPER_STEPS):
        self.left = budget
        self.full = False
        self.by = {}                       # (family, sheet) -> _Rects
        self.size = {}                     # (family, owner) -> the number of cells that row sums surely (PART_SURE)

    def spend(self, n: int = 1):
        self.left -= n
        if self.left < 0:
            self.full = True
            raise _HelperBudget()

    @staticmethod
    def _file(grid, keys, cb, rb, rec):
        lst = grid.get((cb, rb))
        if lst is None:
            lst = grid[(cb, rb)] = []
            ks = keys.get(cb)
            if ks is None:
                ks = keys[cb] = []
            bisect.insort(ks, rb)
        lst.append(rec)

    def add(self, fam, owner, parts):
        """Keep the blocks [(block, how: PART_SURE / PART_MAYBE / PART_CHOSEN)] that a counted row (owner: (sheet, row))
        sums."""
        if self.full:
            raise _HelperBudget()
        n = sum((c2 - c1 + 1) * (r2 - r1 + 1) for (_t, c1, c2, r1, r2), how in parts if how == PART_SURE)
        if n:
            self.size[(fam, owner)] = self.size.get((fam, owner), 0) + n
        for (t, c1, c2, r1, r2), how in parts:
            self.spend()
            R = self.by.get((fam, t))
            if R is None:
                R = self.by[(fam, t)] = _Rects()
            rec = R.seen.get((c1, c2, r1, r2))
            if rec is not None:
                if how > rec[5]:                   # summed more surely by this row: name it
                    rec[4], rec[5] = owner, how
                continue
            rec = R.seen[(c1, c2, r1, r2)] = [c1, c2, r1, r2, owner, how]
            b1, b2, b3, b4 = c1 // _CB, c2 // _CB, r1 // _RB, r2 // _RB
            if c1 == c2 and r1 == r2:
                self._file(R.cells, R.ckeys, b1, b3, rec)
                continue
            nb = (b2 - b1 + 1) * (b4 - b3 + 1)
            if nb > MAX_BUCKETS:
                R.big.append(rec)
                continue
            self.spend(nb)
            for cb in range(b1, b2 + 1):
                for rb in range(b3, b4 + 1):
                    self._file(R.grid, R.gkeys, cb, rb, rec)

    def _meeting(self, R, c1, c2, r1, r2, low):
        """The kept rectangles that meet the block (each once), of those summed at least as `low`."""
        b1, b2, b3, b4 = c1 // _CB, c2 // _CB, r1 // _RB, r2 // _RB
        met = set()
        for grid, keys in ((R.cells, R.ckeys), (R.grid, R.gkeys)):
            if b2 - b1 + 1 > len(keys):
                self.spend(len(keys) + 1)
                cbs = sorted(cb for cb in keys if b1 <= cb <= b2)
            else:
                self.spend(b2 - b1 + 2)
                cbs = [cb for cb in range(b1, b2 + 1) if cb in keys]
            for cb in cbs:
                ks = keys[cb]
                k = bisect.bisect_left(ks, b3)
                while k < len(ks) and ks[k] <= b4:
                    self.spend()
                    for rec in grid[(cb, ks[k])]:
                        self.spend()
                        if id(rec) not in met and rec[5] >= low and rec[0] <= c2 and c1 <= rec[1] and rec[2] <= r2 \
                                and r1 <= rec[3]:
                            met.add(id(rec))
                            yield rec
                    k += 1
        for rec in R.big:
            self.spend()
            if rec[5] >= low and rec[0] <= c2 and c1 <= rec[1] and rec[2] <= r2 and r1 <= rec[3]:
                yield rec

    def cover(self, fam, blk, picked=False):
        """("all", owner, how) when counted rows of this family sum every cell of the block (one kept rectangle holds
        it, or a few hold a small block together; `how` the least sure of them); ("some", owner, PART_CHOSEN) when they
        sum some of its cells; None when none. A block that is itself chosen by a criterion or looked up (`picked`) is
        not compared with cells a counted row chose or looked up: two criteria choose other cells (15 回目の攻撃)."""
        if self.full:
            raise _HelperBudget()
        t, c1, c2, r1, r2 = blk
        R = self.by.get((fam, t))
        if R is None:
            return None
        low = PART_MAYBE if picked else PART_CHOSEN
        self.spend()
        rec = R.seen.get((c1, c2, r1, r2))
        if rec is not None and rec[5] >= low:
            return ("all", rec[4], rec[5])
        # a larger rectangle that holds the block holds its first cell: it is filed in that cell's bucket, or is big
        for rec in R.grid.get((c1 // _CB, r1 // _RB), ()):
            self.spend()
            if rec[5] >= low and rec[0] <= c1 and c2 <= rec[1] and rec[2] <= r1 and r2 <= rec[3]:
                return ("all", rec[4], rec[5])
        for rec in R.big:
            self.spend()
            if rec[5] >= low and rec[0] <= c1 and c2 <= rec[1] and rec[2] <= r1 and r2 <= rec[3]:
                return ("all", rec[4], rec[5])
        if c1 == c2 and r1 == r2:
            return None                          # (a single cell is held by itself or by a larger rectangle)
        n = (c2 - c1 + 1) * (r2 - r1 + 1)
        met = []
        for rec in self._meeting(R, c1, c2, r1, r2, low):
            met.append(rec)
            if n > UNION_CELLS or len(met) > UNION_RECTS:
                return ("some", met[0][4], PART_CHOSEN)
        if not met:
            return None
        self.spend(n * len(met))                 # a small block held by several rectangles together (B3, C3, D3)?
        for c in range(c1, c2 + 1):
            for r in range(r1, r2 + 1):
                if not any(x[0] <= c <= x[1] and x[2] <= r <= x[3] for x in met):
                    return ("some", met[0][4], PART_CHOSEN)
        return ("all", met[0][4], min(x[5] for x in met))


def _one_cell_block(b) -> bool:
    return b[1] == b[2] and b[3] == b[4]


def _item_key(prep, r: dict) -> str:
    """A row's name and specification as one text, for whether two rows name the same item (NFKC, lower case, with no
    spaces or punctuation: 普通コンクリート｜Fc24 and 普通コンクリート Fc24 in one column are the same). `prep` is the
    document's _Prep: the texts were normalised once when the row was classified."""
    return _PUNCT.sub("", (prep(r.get("name")) + " " + prep(r.get("specification"))).lower())


def _same_quantity(a, b) -> bool:
    """Two rows' quantities (the values the file holds for their cells) are the same but for the last digits of floating
    point. A row that sums the cells a counted row sums but holds another number is no copy of that row: it adds them
    twice (SUM(X)+SUM(X), SUM(X,X), the cells listed twice: the boards on both faces of a wall), adds a number to them or
    takes another function of them (AVERAGE, MAX, PRODUCT) (16 回目の攻撃: such a row was dropped surely as a copy)."""
    return abs(a - b) <= 1e-6 * max(1.0, abs(a), abs(b))


def _helper_parts(srcs) -> list:
    """[(block, how)] of the blocks a counted row SUMS (level 2) — the parts of its quantity, as own_parts reads a bill
    row's — and how. Not parts: a cell it only multiplies by another reference (面積×厚さ, 長さ × 単位質量: level 1), and
    a single cell it only scales by numbers (延床面積 × 0.6, 12.5 × 戸数, 1200 × 早見表の単位質量 / 1000: a driver or a
    factor that other rows of the material scale too). PART_SURE only for an unconditional sum of more than one cell that
    is not scaled (SUM(階別!B2:D2), B3+C3+D3); PART_MAYBE for a single cell, or cells scaled (SUM(…)*1.05, 面積の合計 ×
    0.15); PART_CHOSEN for cells it chooses by a criterion (SUMIF, SUMIFS, SUMPRODUCT with a condition, FILTER) or a value
    it looks up (VLOOKUP, INDEX …): another row's criterion or key chooses other cells (15 回目の攻撃)."""
    parts = [(b, m) for b, lv, m in srcs if lv == 2 and not m & PICKED and not (m & ALONE and _one_cell_block(b))]
    n = sum((b[2] - b[1] + 1) * (b[4] - b[3] + 1) for b, _m in parts)
    how = PART_SURE if n > 1 and not any(m & SCALED for _b, m in parts) else PART_MAYBE
    return [(b, how) for b, _m in parts] + [(b, PART_CHOSEN) for b, lv, m in srcs if lv == 2 and m & PICKED]


def _helper_copy(cells, helpers, fam, srcs, over):
    """("all" | "unsure" | "some", owner, a block, the number of those cells it adds) when the blocks a quantity reaches
    by adding are cells that counted rows of its family sum: all of them surely, by plain reference or sum ("all": a
    copy); all of them, but summed by a row only perhaps, or looked up, chosen by a criterion or scaled here ("unsure");
    only some of them ("some"). A single cell it only multiplies by another reference that no counted row sums is a
    factor, and a block of formula cells that no counted row sums stands for what its formulas reach; neither counts
    against "all". None when it meets none of those cells. Raises _HelperBudget.
    A quantity that scales the cells (the wall area = the floor areas × 2.5) is "unsure" as a counted row that scales them
    is: a waste allowance on the same quantity, or another item worked out from the same areas (16 回目: it was a sure
    copy, and which of the two rows was dropped surely depended on the order of the sheets). The caller keeps "all" a
    sure copy only when it adds as many cells as the counted row sums (the same cells) and names the same item."""
    hit, partial, unsure, met = None, False, False, set()
    for blk, lv, m in srcs:
        got = helpers.cover(fam, blk, bool(m & PICKED))
        if got is not None:
            met.add(blk)
            if hit is None:
                hit = (got[1], blk)
            elif blk[0] == hit[1][0]:            # the cells met on that sheet, said as one range
                b = hit[1]
                hit = (hit[0], (b[0], min(b[1], blk[1]), max(b[2], blk[2]), min(b[3], blk[3]), max(b[4], blk[4])))
            if got[0] == "some":
                partial = True
            elif got[2] != PART_SURE or m & (PICKED | SCALED):
                unsure = True
            continue
        if lv == 1 and _one_cell_block(blk):
            continue                                 # a factor (a rate cell, a thickness)
        if cells.transparent(blk, helpers.spend):
            continue                                 # formula cells: what they reach is in srcs
        partial = True
    if hit is None:
        return None
    return ("some" if partial or over else "unsure" if unsure else "all",) + hit + \
        (sum((b[2] - b[1] + 1) * (b[4] - b[3] + 1) for b in met),)


class _Cells:
    """What a quantity formula reaches, followed through the formulas of every sheet (helper cells, other columns,
    other sheets, hidden helpers, array formulas, defined names, tables). A quantity is a copy when it reaches the
    QUANTITY of another material row (a row that names a material in a unit its field takes, or a total / 再掲 / work /
    deduction / removal row on a sheet that lists materials): a cell in its quantity columns (数量, 所要数量, 体積, 重量 …)
    or a cell its quantity SUMS (a calculation column, per-floor or per-type columns, whatever their header), reached in
    any way; or any other number of that row ADDED up by the quantity (集計!1F = 明細!C2 where C2 is a typed per-floor
    quantity, SUMPRODUCT, table references, a lookup keyed on the bill's name column), unless its column names money or
    a factor. A DIMENSION of another row (a cell that row's own quantity only multiplies: 面積×厚さ, 長さ×単重) is a copy
    when it is summed (集計 = 明細!D2) or when two of that row's numbers are reached (集計 = 明細!C2*明細!D2 recomputes
    it), not when the formula multiplies that one dimension by a number of its own row's size (土間 = C3*$D$2, 14 回目);
    times a header or constant cell (集計 = 明細!C2*明細!$G$1) it is a copy (14 回目の攻撃). A value looked up from a
    bill by its name / 規格 / 区分 column is one cell of one row (see _one_cell). A number of another row that is only
    looked up from a table beside the bill (a unit mass, a density) is a factor, not a copy. GETPIVOTDATA reads a pivot
    table: the pivot table's reason (see _pivot_read).
    Cells of the quantity's own row are parts of it. Every formula cell and every range is followed once per document
    (the results are kept), and every step, block, row and name expansion counts against MAX_FOLLOW_STEPS."""

    def __init__(self, parsed: dict):
        self.cells = parsed.get("cells") or {}
        self.names = parsed.get("names") or {}
        self.tables = parsed.get("tables") or {}
        self.disp = parsed.get("sheet_names") or {}
        self.frows = {sh: sorted(rows) for sh, rows in self.cells.items()}
        self.fcols = {}
        self.targets, self.tcols, self.owned = {}, {}, {}
        self.ncols = {}                    # (sheet, row) -> the row's numbers outside money / factor columns
        self.xcols = {}                    # sheet -> its money / factor columns (単価, 単位質量, 比重 …)
        self.dims = {}                     # (sheet, row) -> cells the row's own quantity only multiplies (dimensions)
        self.rnums = {}                    # (sheet, row) -> the columns of the row that hold numbers (sorted)
        self.sizecols = {}                 # sheet -> its columns of a row's own size (面積, 長さ, 本数 …: _own_number)
        self.pivots = parsed.get("pivots") or {}       # sheet -> its pivot tables' areas, with their reasons
        self.keycols = {}                  # sheet -> its name / specification / division columns (see _keyed)
        self.cut_sheets = set(parsed.get("cut_sheets") or ())
        self.memo, self.name_memo, self.walks = {}, {}, {}
        self.fam_rows, self.same_memo = {}, {}
        self.pv_index = {}                 # sheet -> its pivot tables by stretches of rows (see _pivot_at)
        self.last_hits = ()
        self.left = MAX_FOLLOW_STEPS
        self.cut = 0

    def _spend(self, n: int = 1):
        self.left -= n
        if self.left < 0:
            raise _FollowBudget()

    def _ctx(self, sh, rn, ci):
        return {"sheet": self.disp.get(sh, sh), "names": self.names, "tables": self.tables, "row": rn, "col": ci,
                "spend": self._spend, "name_memo": self.name_memo, "ones": True}

    def _walk(self, sh, rn, ci):
        """formula_walk of one formula cell, kept per document (a row's parts, the copy walk and the check of a copy
        on another sheet read the same cell; what names give is charged to the budget the first time)."""
        key = (sh, rn, ci)
        got = self.walks.get(key)
        if got is None:
            got = self.walks[key] = tabular.formula_walk(self.cells[sh][rn][ci], self._ctx(sh, rn, ci))
        return got

    def _keyed(self, sh, keys) -> bool:
        """Is a looked-up block keyed on a column that tells the rows of a bill apart (its name, specification or
        division column, on a sheet that lists materials: XLOOKUP("コンクリート", 明細!A:A, 明細!C:C), VLOOKUP over
        明細!A:E, INDEX(明細!C:C, MATCH(…, 明細!A:A, 0)))? Then it returns a row's own number, as a reference to it
        would (14 回目). A table beside the bill keyed on its own column (a unit-mass 早見表) is not."""
        for kb, how in keys:
            t = kb[0] or sh
            kc = self.keycols.get(t)
            if not kc or t not in self.targets:
                continue
            if (how == "col" and kb[1] in kc) or (how == "all" and any(kb[1] <= c <= kb[2] for c in kc)):
                return True
        return False

    def _pivot_read(self, sh, rn, ci, blocks):
        """A formula that reads a pivot table with GETPIVOTDATA("数量", 集計!$A$3, "名称", "コンクリート") (Excel writes
        this when a pivot table's cell is clicked while typing a formula): it reaches only the pivot table's corner,
        which is no material row, and was added (14 回目の攻撃). (the pivot table's reason, node, "pivot") when one of
        the formula's blocks lies in a pivot table (the same reason as the pivot table's own cells: surely not added
        when its source table is read here); (why it cannot be checked, node) when none does; None without
        GETPIVOTDATA. Every pivot table looked at counts against the budget."""
        text = tabular._formula_tuple(self.cells[sh][rn][ci])[0]
        if not _GETPIVOT.search(text) or "GETPIVOTDATA" not in tabular._formula_parts(text)[0]:
            return None
        node = ("c", sh, rn, ci)
        for b in blocks:
            t = b[0] or sh
            for pv in self.pivots.get(t, ()):
                self._spend()
                if pv["c1"] <= b[2] and b[1] <= pv["c2"] and (b[4] is None or pv["r1"] <= b[4]) \
                        and (b[3] is None or b[3] <= pv["r2"]):
                    return (pv["reason"], node, "pivot", pv)
        return (R_GETPIVOT_UNKNOWN, node)

    def _pivot_index(self, t):
        """(first row of each stretch of rows, [(order, c1, c2) of the pivot tables over that stretch, in the workbook's
        order]) of sheet t, built once per sheet (a sweep over the pivot tables' rows) and charged to the budget, so
        that a block is found by bisection (15 回目)."""
        got = self.pv_index.get(t)
        if got is None:
            pvs = self.pivots.get(t) or ()
            self._spend(len(pvs) + 1)
            ivs = sorted((pv["r1"], pv["r2"], i, pv["c1"], pv["c2"]) for i, pv in enumerate(pvs))
            starts, active, on, j = [], [], {}, 0
            for b in sorted({iv[0] for iv in ivs} | {iv[1] + 1 for iv in ivs}):
                while j < len(ivs) and ivs[j][0] <= b:
                    on[ivs[j][2]] = ivs[j]
                    j += 1
                for i in [i for i, iv in on.items() if iv[1] < b]:   # pivot tables that end above this row
                    del on[i]
                self._spend(len(on) + 1)
                starts.append(b)
                active.append(tuple((i, on[i][3], on[i][4]) for i in sorted(on)))
            got = self.pv_index[t] = (starts, active)
        return got

    def _pivot_at(self, t, c1, c2, lo, hi):
        """The first pivot table (in the workbook's order) of sheet t whose area (with its page fields) meets the block
        c1..c2 × lo..hi, or None. Every stretch and pivot table looked at counts against the budget."""
        if t not in self.pivots:
            return None
        starts, active = self._pivot_index(t)
        k = max(bisect.bisect_right(starts, lo) - 1, 0)
        best = None
        while k < len(starts) and starts[k] <= hi:
            self._spend()
            for i, pc1, pc2 in active[k]:
                if best is not None and i >= best:
                    break
                self._spend()
                if pc1 <= c2 and c1 <= pc2:
                    best = i
                    break
            k += 1
        return self.pivots[t][best] if best is not None else None

    def _children(self, node, fr):
        """(child, level) of a node: 2 the child's value is summed into the node's, 1 it is a factor of a product of
        references, 0 not added. A frame is [node, children, why, rows reached, rows reached by adding, level,
        dimensions reached {(sheet, row): (columns, level)}]."""
        if node[0] == "c":
            _k, sh, rn, ci = node
            self._spend()
            if sh in self.cut_sheets:
                fr[2] = (CUT_SHEET % tabular.sheet_label(self.disp.get(sh, sh)), node)
                return iter(())
            why, blocks = self._walk(sh, rn, ci)
            if why:
                fr[2] = (why, node)
                return iter(())
            pv = self._pivot_read(sh, rn, ci, blocks)
            if pv:
                fr[2] = pv
                return iter(())
            self._spend(len(blocks))
            # a value looked up from a bill by its name / 規格 / 区分 column and multiplied: one cell of one row of the
            # block, reached as a factor ("k": see _one_cell)
            # (the third item: how the block makes the value besides its level, see tabular._additive's MARKS; a
            # value looked up is PICKED)
            return iter([(("k", b[0] or sh, b[1], b[2], b[3], b[4]), 1, PICKED) if b[5] == 0 and b[6] and self._keyed(sh, b[6])
                         else (("b", b[0] or sh, b[1], b[2], b[3], b[4]), b[5], b[7] if len(b) > 7 else 0) for b in blocks])
        kind, t, c1, c2, r1, r2 = node
        one = kind == "k"
        if t in self.cut_sheets:
            fr[2] = (CUT_SHEET % tabular.sheet_label(self.disp.get(t, t)), node)
            return iter(())
        lo = 0 if r1 is None else r1
        hi = tabular.MAX_ROW_NUMBER if r2 is None else r2
        # a block that meets a pivot table reads that summary of another table, whatever the formula does with it (a
        # plain reference, a factor, SUM, a name, LET, GETPIVOTDATA inside a name): the pivot table's reason. Its cells
        # are no material rows here (see read), so the material rows the block also reaches still make a copy (15 回目).
        # The pivot table met is kept apart from `why`, so that the walk goes on to the other blocks of the formula
        # (15 回目の攻撃: SUMIF(明細!A:A, 前回集計!A4, 明細!C:C) stopped at the pivot table's label and lost the copy)
        pv = self._pivot_at(t, c1, c2, lo, hi)
        if pv is not None and fr[10] is None:
            fr[10] = (pv["reason"], node, "pivot", pv)
        trows, tc = self.targets.get(t), self.tcols.get(t, ())
        if trows:
            k = bisect.bisect_left(trows, lo)
            while k < len(trows) and trows[k] <= hi and len(fr[3]) < 2:
                self._spend()
                key = (t, trows[k])
                if key not in fr[3]:
                    cols = self.owned.get(key, tc)    # the quantity columns, and the cells summed into them
                    j = bisect.bisect_left(cols, c1)
                    if j < len(cols) and cols[j] <= c2:
                        fr[3].append(key)
                    elif key not in fr[4] and len(fr[4]) < 2:
                        lc = self.ncols.get(key, ())  # another number of the row: a copy only when it is added up
                        j = bisect.bisect_left(lc, c1)
                        if j < len(lc) and lc[j] <= c2:
                            fr[4].append(key)
                        elif key in self.dims and (key in fr[6] or len(fr[6]) < (1 if one else MAX_PENDING)):
                            dc = self.dims[key]       # a dimension of the row: see _merge
                            j = bisect.bisect_left(dc, c1)
                            got = []
                            while j < len(dc) and dc[j] <= c2 and len(got) < 2:
                                got.append(dc[j])
                                j += 1
                            if got:
                                # a factor column's cell (単位質量, 単重) is never a copy by itself, even summed
                                # ($F$2*1000/1000): only with another number of its row
                                xc = self.xcols.get(t, ())
                                lv = 2 if any(c_ not in xc for c_ in got) else 1
                                old = fr[6].get(key)
                                fr[6][key] = (old[0] | frozenset(got), max(lv, old[1])) if old else (frozenset(got), lv)
                k += 1
        return ((c, 2, 0) for c in self._formula_cells(t, c1, c2, lo, hi))

    def own_parts(self, sh: str, row: int):
        """The cells of a material row that its quantity SUMS (ROUND(F2), SUM(B2:D2), C2+D2, SUM(C2:E2)*1.05: a
        calculation column, per-floor or per-type columns, whatever their header): another row that reaches one of them
        copies part of this row's quantity. The cells its quantity only multiplies by another reference (面積×厚さ,
        長さ×本数×単重, a rate cell) or looks up from a column of the bill (INDEX($F$2:$F$9, MATCH(B2, …)): a unit mass
        on each row) are its dimensions and factors, not parts of it (14 回目: round 13 made every factor of a product a
        part, and then skipped money / factor columns, which also dropped summed per-type columns)."""
        tc = self.tcols.get(sh, ())
        rowcells = self.cells.get(sh, {}).get(row) or {}
        owned, dims = set(tc), set()
        todo, seen = [(c, 2) for c in tc if c in rowcells], {}
        while todo:
            c, lv = todo.pop()
            if seen.get(c, -1) >= lv:
                continue
            seen[c] = lv
            try:
                why, blocks = self._walk(sh, row, c)
                blocks = [b[:6] for b in blocks if b[5] or b[6]] if why is None else \
                    tabular.added_blocks(rowcells[c], None, levels=True)     # its own references only
            except _FollowBudget:
                break
            for bsh, c1, c2, r1, r2, blv in blocks:
                if (bsh is not None and bsh != sh) or c2 - c1 >= 256:
                    continue
                if blv == 0:                     # a value looked up from a column of the bill (a unit mass by 規格)
                    if (r1 is None or r1 <= row) and (r2 is None or row <= r2):
                        dims.update(range(c1, c2 + 1))
                    continue
                if r1 == row and r2 == row:
                    lv2 = min(lv, blv)
                    for cc in range(c1, c2 + 1):
                        (owned if lv2 == 2 else dims).add(cc)
                        if cc in rowcells:
                            todo.append((cc, lv2))
        dims -= owned
        if owned != set(tc):
            self.owned[(sh, row)] = sorted(owned)
        if dims:
            self.dims[(sh, row)] = sorted(dims)

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

    def _merge(self, fr, res, level, mark=0):
        """Merge a child's result into its parent's frame; `level` is how the child's value makes the parent's, `mark`
        how else (PICKED | SCALED | ALONE, see tabular._additive). The dimensions reached keep the lowest level of the
        path (MAX_DIM_ROWS rows, two columns each are enough); copy_of judges them (see _dim_copy). The blocks reached by
        adding keep the lowest level of the path too, and the marks on it (MAX_SOURCES of them; more are only flagged):
        read compares them with the cells counted rows sum (15 回目). A block reached in two ways keeps the higher level
        and the marks common to both."""
        why, hits, adds, dims, srcs, over, pvm = res
        if why and fr[2] is None:
            fr[2] = why
        if pvm and fr[10] is None:
            fr[10] = pvm
        for h in hits:
            if h not in fr[3] and len(fr[3]) < 2:
                fr[3].append(h)
        if not level:
            return
        for h in adds:                                   # numbers reached by adding stay "added" only through sums
            if h not in fr[4] and h not in fr[3] and len(fr[4]) < 2:
                fr[4].append(h)
        pend = fr[6]
        for key, cols, lv in dims:
            lv = min(level, lv)
            old = pend.get(key)
            if old is None:
                if len(pend) < MAX_DIM_ROWS:
                    pend[key] = (cols, lv)
            elif len(old[0]) < 2 or lv > old[1]:
                pend[key] = (frozenset(sorted(old[0] | cols)[:2]), max(lv, old[1]))
        if over:
            fr[8] = True
        if srcs and not fr[8]:
            mine = fr[7]
            self._spend(len(srcs))
            for blk, (lv, m) in srcs:
                lv, m = min(level, lv), m | mark
                old = mine.get(blk)
                if old is None:
                    if len(mine) >= MAX_SOURCES:
                        fr[8] = True
                        break
                    mine[blk] = (lv, m)
                elif lv > old[0] or old[1] & ~m:
                    mine[blk] = (max(lv, old[0]), old[1] & m)

    def _one_cell(self, dims: dict) -> dict:
        """The dimensions a looked-up value ("k" node) can bring: one cell of one row (a lookup returns one cell; one
        outside money / factor columns when there is one, the conservative cell). Without this the lookup's whole
        block counted as the dimensions of two rows, a copy (14 回目の攻撃: XLOOKUP(B2, 明細!B:B, 明細!E:E) of a bill
        of three rows). A looked-up 単位質量 or 割増率 alone is then a factor (see _dim_copy); two looked-up numbers of
        one row (INDEX(明細!C:C, …) + INDEX(明細!D:D, …)) are still two numbers of that row."""
        first = None
        for key, (cols, lv) in dims.items():
            xc = self.xcols.get(key[0], ())
            cs = [c for c in sorted(cols) if c not in xc]
            if cs:
                return {key: (frozenset(cs[:1]), lv)}
            if first is None:
                first = {key: (frozenset(sorted(cols)[:1]), lv)}
        return first or {}

    def _dim_copy(self, dims, own, own_number) -> list:
        """The rows whose dimensions make a formula a copy: a dimension summed all the way (集計 = 明細!D2), two numbers
        of one row (明細!C2*明細!D2 recomputes it, whatever their columns), or dimensions of two other rows. A single
        cell of a money / factor column (単位質量, 単重, 割増率) is a factor, never a copy by itself (as in c3d4436 and
        e2199b2: $F$2*1000/1000, AVERAGE(明細!E2:E4)*C2, a 単位質量 looked up in a helper cell), and does not count
        towards the two rows. One dimension of one row is not a copy only when the formula multiplies it by a number
        of its own row's size (土間 = C3*$D$2, 14 回目): `own_number()` says so (see _own_number). Multiplied by a
        header or constant cell (集計 = 明細!C2*明細!$G$1: 設計 × 割増, a per-type share × 戸数) it recomputes that
        row's quantity: a copy (14 回目の攻撃)."""
        other, single = [], []
        for k, c, lv in dims:
            if k == own:
                continue
            if lv == 2 or len(c) > 1:
                other.append(k)
            elif next(iter(c)) not in self.xcols.get(k[0], ()):
                single.append(k)
        if len(single) > 1:
            return other + single
        return other + [k for k in single if not own_number()]

    def _own_number(self, sh: str, row: int, col: int) -> bool:
        """Does the quantity formula multiply a number of its own row's size (C3 in 土間 = C3*$D$2, its own area; C3 and
        D3 in C3*D3*$E$2, its length and count)? A reference of the formula itself to a cell or a block of its own row
        that is a factor of a product of references (level 1), in a column whose header names a size (面積, 長さ, 本数,
        設計数量 …: tabular.SIZE_WORDS; an own 割増, 戸数 or unlabeled 1.05 times another row's 設計 or per-type share
        recomputes that row), holding a typed number or a formula of that row's own cells only (=C3, =20*20; not
        =明細!C2, which would bring the other row's number in)."""
        try:
            self._spend()
            why, blocks = self._walk(sh, row, col)
        except _FollowBudget:
            return False
        if why:
            return False
        rowcells = self.cells.get(sh, {}).get(row) or {}
        nums = self.rnums.get((sh, row), ())
        xc, size = self.xcols.get(sh, ()), self.sizecols.get(sh, ())
        try:
            for b in blocks:
                self._spend()
                if b[0] not in (None, sh) or b[3] != row or b[4] != row or b[5] != 1:
                    continue
                j = bisect.bisect_left(nums, b[1])
                while j < len(nums) and nums[j] <= b[2]:
                    c = nums[j]
                    j += 1
                    self._spend()
                    if c == col or c in xc or c not in size:
                        continue
                    if c not in rowcells:
                        return True
                    w2, b2 = self._walk(sh, row, c)
                    self._spend(len(b2))
                    if w2 is None and all(x[0] in (None, sh) and x[3] == row and x[4] == row for x in b2):
                        return True
        except _FollowBudget:                    # unsure: the conservative answer (a copy)
            return False
        return False

    def _result(self, root):
        """(why it cannot be checked: (text, node) or None; up to two (sheet, row) material rows whose quantity is
        reached; up to two whose other numbers are reached by adding; a dimension reached ((sheet, row), columns,
        level) that is not a copy by itself)."""
        memo = self.memo
        if root in memo:
            return memo[root]
        stack, on = [self._frame(root, 2)], {root}
        while stack:
            fr = stack[-1]
            if fr[1] is None:
                fr[1] = self._children(fr[0], fr)
            nxt = next(fr[1], None) if fr[2] is None and len(fr[3]) < 2 else None
            if nxt is None:
                dims = fr[6] if fr[0][0] != "k" else self._one_cell(fr[6])
                res = memo[fr[0]] = (fr[2], tuple(fr[3]), tuple(fr[4]), tuple((k, v[0], v[1]) for k, v in dims.items()),
                                     tuple(fr[7].items()), fr[8], fr[10])
                on.discard(fr[0])
                stack.pop()
                if stack:
                    self._merge(stack[-1], res, fr[5], fr[9])
                continue
            child, level, mark = nxt
            got = memo.get(child)
            if got is not None:
                self._spend()
                self._merge(fr, got, level, mark)
            elif child in on:
                fr[2] = ("循環する参照（数式が自分自身にたどり着く）は確かめられない。必要なら手で入れる", fr[0])
            else:
                on.add(child)
                stack.append(self._frame(child, level, mark))
        return memo[root]

    @staticmethod
    def _frame(node, level, mark=0):
        """[node, children, why, rows reached, rows reached by adding, level, dimensions reached, blocks reached by
        adding {block: (level, marks)}, more blocks than kept?, the marks of the way to the node, the first pivot table
        met (its reason, node, "pivot", the pivot table) or None]; a block node reaches itself (rows as numbers: 1 to the
        last)."""
        srcs = {}
        if node[0] != "c":
            _k, t, c1, c2, r1, r2 = node
            srcs[(t, c1, c2, 1 if r1 is None else r1, tabular.MAX_ROW_NUMBER if r2 is None else r2)] = (2, 0)
        return [node, None, None, [], [], level, {}, srcs, False, mark, None]

    def _on_targets(self, t, r1, r2) -> bool:
        """Does the block's sheet list materials with a material (or marked) row in rows r1..r2? (Those rows' cells are
        judged as parts, numbers and dimensions of the rows, not as cells a counted row sums.)"""
        rows = self.targets.get(t)
        if not rows:
            return False
        k = bisect.bisect_left(rows, r1)
        return k < len(rows) and rows[k] <= r2

    def sources(self, sh: str, row: int, col: int):
        """After copy_of found nothing: ([(block, level, marks)] the quantity reaches by adding, outside its own row and
        the material rows of quantity tables (a helper sheet, per-floor take-off, hidden detail rows, lines without a
        unit); whether more were reached than kept). Level 2: summed (alone, in a sum, scaled by a number); 1: a factor
        of a product of references. Marks (see tabular._additive): PICKED, a lookup (VLOOKUP, INDEX …) or a criterion
        (SUMIF …) is on the way; SCALED, multiplied or divided on the way; ALONE, a lone reference scaled by numbers."""
        res = self.memo.get(("c", sh, row, col))
        if res is None:
            return [], True
        out = []
        for blk, (lv, m) in res[4]:
            t, c1, c2, r1, r2 = blk
            self._spend()
            if (t == sh and r1 == row and r2 == row) or self._on_targets(t, r1, r2):
                continue
            out.append((blk, lv, m))
        return out, res[5]

    def transparent(self, blk, spend) -> bool:
        """Is every cell of a (small) block a formula cell? Its formulas are followed, so what they reach stands for it.
        Each row looked at is charged to `spend` (by bisection in the sheet's formula rows and columns, not cell by cell:
        15 回目の攻撃)."""
        t, c1, c2, r1, r2 = blk
        if (c2 - c1 + 1) * (r2 - r1 + 1) > HELPER_CELLS:
            return False
        frs = self.frows.get(t, ())
        k = bisect.bisect_left(frs, r1)
        for r in range(r1, r2 + 1):
            spend()
            if k >= len(frs) or frs[k] != r:
                return False
            cols = self.fcols.get((t, r))
            if cols is None:
                spend(len(self.cells[t][r]))
                cols = self.fcols[(t, r)] = sorted(self.cells[t][r])
            j = bisect.bisect_left(cols, c1)
            if j + c2 - c1 >= len(cols) or cols[j] != c1 or cols[j + c2 - c1] != c2:
                return False
            k += 1
        return True

    def _family_rows(self, t: str, fam, row_fid: dict) -> list:
        """The rows of sheet t (sorted) that name a material of this family, or a total / work row of no material."""
        key = (t, fam)
        got = self.fam_rows.get(key)
        if got is None:
            rows = self.targets.get(t, ())
            self._spend(len(rows) + 1)
            got = self.fam_rows[key] = [r for r in rows if (t, r) in row_fid
                                        and (row_fid[(t, r)] is None or _family(row_fid[(t, r)]) == fam)]
        return got

    def reaches_same(self, sh: str, row: int, col: int, fid: str, row_fid: dict) -> bool:
        """After a copy on another sheet: does the quantity reach a row of the same material there (コンクリート and
        基礎のコンクリート are one: _family), or a total / work row that names none? The rows the walk kept, and every
        material row of another sheet inside the blocks the formula names itself (a mask or a SUMIF over the whole bill
        reaches the row of its own material even when the walk stopped at the first two rows), found by bisection in
        each sheet's rows of that material; every block counts against the budget. Unsure (the formula cannot be read
        again, or the budget runs out): yes."""
        fam = _family(fid)
        if any(h in row_fid and (row_fid[h] is None or _family(row_fid[h]) == fam) for h in self.last_hits):
            return True
        if col not in (self.cells.get(sh, {}).get(row) or {}):
            return True
        try:
            self._spend()
            why, blocks = self._walk(sh, row, col)
            if why:
                return True
            for b in blocks:
                self._spend()
                t = b[0] or sh
                if t == sh:
                    continue
                mkey = (t, b[3], b[4], fam)
                got = self.same_memo.get(mkey)
                if got is None:
                    rows = self._family_rows(t, fam, row_fid)
                    k = bisect.bisect_left(rows, 0 if b[3] is None else b[3])
                    hi = tabular.MAX_ROW_NUMBER if b[4] is None else b[4]
                    got = self.same_memo[mkey] = k < len(rows) and rows[k] <= hi
                if got:
                    return True
        except _FollowBudget:
            return True
        return False

    def copy_of(self, sh: str, row: int, col: int, qf=None):
        """None, ("copy", sheet, row), ("unchecked", reason), ("pivot", reason, pivot table or None) or ("budget",
        reason)."""
        node = ("c", sh, row, col)
        if col not in (self.cells.get(sh, {}).get(row) or {}):
            if qf is None:
                return None
            self.cells.setdefault(sh, {}).setdefault(row, {})[col] = qf
            self.frows[sh] = sorted(self.cells[sh])
            self.fcols.pop((sh, row), None)
        try:
            res = self._result(node)
            why, hits, adds, dims, pvm = res[0], res[1], res[2], res[3], res[6]
        except _FollowBudget:
            self.cut += 1
            return ("budget", "数式のたどる先が多すぎて確かめられない（1 つの資料で %d 歩まで）。必要なら手で入れる"
                    % MAX_FOLLOW_STEPS)
        others = [h for h in list(hits) + list(adds) if h != (sh, row)]
        others += [k for k in self._dim_copy(dims, (sh, row), lambda: self._own_number(sh, row, col)) if k not in others]
        if others:
            self.last_hits = tuple(others)       # every material row reached (up to four): the caller compares fields
            return ("copy",) + others[0]
        if why:
            text, at = why[:2]
            if len(why) > 2:                     # it reads a pivot table: that table's reason
                return ("pivot", text, why[3] if len(why) > 3 else None)
            if at == node:
                return ("unchecked", text)
            return ("unchecked", "参照先の数式（%s）：%s" % (tabular.sheet_label(self.disp.get(at[1], at[1])), text))
        if pvm:                                  # it reads a pivot table and reaches no material row
            return ("pivot", pvm[0], pvm[3])
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


def _marks(name: str, spec: str, div: str) -> tuple:
    """(total, again, deduct, demolish, work) of one row's name, specification and division."""
    text = name + " ; " + spec if spec else name
    n_name = len(_parts(name.lower()[:MAX_NAME])) if spec else None     # the parts after these are the specification
    total = _total(name) or (_total(spec) if spec else False)
    # a 再掲 / 内訳 / 控除 mark in the name or the division is sure; one only in the specification (摘要) may be a note on
    # the material row: an exclusion with "maybe", unless it is an explicit 再掲 (14 回目)
    again = SURE if _again(name) or (_again(div) if div else False) else (_again_spec(spec) if spec else None)
    # a row that names the scrap itself (鉄筋スクラップ｜控除 別途精算, 鉄骨スクラップ｜控除共) is the deduction: the price-note
    # shapes of the specification are no price note there (14 回目). It is a deduction whatever the specification says
    # (スクラップ｜鉄筋 D13, 鉄筋スクラップ alone): "maybe", and sure with a deduction word or a sale after the scrap
    # (鉄筋スクラップ｜売却, スクラップ買取｜鉄骨) (15 回目)
    if _SCRAP_NAME.search(name) and _scrap_itself(name):
        deduct = SURE if _deduct(name) or (spec and (_deduct(spec) or _scrap_sale(name + " " + spec))) else MAYBE
    elif _SCRAP_NAME.search(name):
        # … but a scrap word after the material in a later word of a one-column name is a note on the material row, as
        # in a specification (異形鉄筋 SD345 D13 スクラップ買取共, 鉄骨 SN490B スクラップ評価額別途): "maybe" at most, never
        # sure by the sale word (sure only by a deduction word of the name, as before 15 回目) (15 回目の攻撃)
        deduct = SURE if _deduct(name) else MAYBE
    else:
        deduct = SURE if _deduct(name) else (MAYBE if spec and _deduct(spec, True) else None)
    return total, again, deduct, _demolish(text, n_name), _work(text, n_name)


# ordinary words that start with 内 (16 回目): a name or division cell that is one space-justified run closing up into
# exactly one of them (内　　壁, 内　部, 内　装, 内　装　材, 内　法) has its 内 only as written: perhaps a letter of the word,
# perhaps the breakdown mark (15 回目 kept every such 内 sure, and 内　　壁｜石膏ボード was surely left out)
NAI_CELLS = ("内壁", "内部", "内装", "内装材", "内法")


def _nai_cell(s: str) -> bool:
    """Whether a name or division cell as written is one space-justified run that closes up into a word of NAI_CELLS."""
    t = s.strip() if s and "内" in s else ""
    return bool(t) and bool(_JUSTIFIED.fullmatch(t)) and _SPACES.sub("", t) in NAI_CELLS


def _row_class(prep: _Prep, r: dict) -> dict:
    shown, spec0, div0 = prep(r.get("name")), prep(r.get("specification")), prep(r.get("division"))
    # the material is read with each space-justified run closed up (鉄　　骨, ガ　ラ　ス); the marks are looked for in the
    # text as written and closed up (撤　　去, 加　工　組　立, 取　付　手　間; 内　柱 stays a breakdown) (15 回目). The name
    # is shown as written
    name, spec, div = _justify(shown), _justify(spec0), _justify(div0)
    text = name + " ; " + spec if spec else name
    fid = _classify(text, div)
    total, again, deduct, demolish, work = _marks(name, spec, div)
    nai = False
    if (name, spec, div) != (shown, spec0, div0):
        for closed, written in ((name, shown), (spec, spec0), (div, div0)):
            if closed != written:
                prep.charge(closed)            # (the second reading is charged to the budget: 15 回目の攻撃)
        t0, a0, d0, m0, w0 = _marks(shown, spec0, div0)
        total, work = total or t0, work or w0
        if a0 == SURE and again != SURE and (_nai_cell(shown) or _nai_cell(div0)):
            # the mark as written, without the 内 of such a cell (内　　壁, 内　部): when only that 内 makes it sure, the row
            # is "maybe" with its quantity, never sure. Not in a specification, a one-column name or a PDF line, and an
            # explicit mark stays sure (内　壁　内　訳 closes up into no word of NAI_CELLS) (16 回目)
            a1 = SURE if (not _nai_cell(shown) and _again(shown)) or (div0 and not _nai_cell(div0) and _again(div0)) \
                else (_again_spec(spec0) if spec0 else None)
            nai = a1 != SURE
            a0 = MAYBE if nai else a0
        again, deduct, demolish = _stronger(again, a0), _stronger(deduct, d0), _stronger(demolish, m0)
    if again and spec and fid == "m_concrete_fdn":
        n_name = len(_parts(name.lower()[:MAX_NAME]))
        fid = _classify(text, div, n_name)     # 基礎 only inside a うち note: the row is not foundation concrete
        if fid == "m_concrete_fdn" and spec != spec0 and _classify(name + " ; " + spec0, div, n_name) == "m_concrete":
            fid = "m_concrete"                 # (… also a note written 内　杭, which closes up into one word: 15 回目)
    u = _unit(r.get("unit"))
    fid = _block_as_concrete(fid, text, div, u)
    scrap = None
    if deduct == MAYBE and _SCRAP_NAME.search(name):        # (the maybe is the scrap name's)
        scrap = R_SCRAP_MAYBE if _scrap_itself(name) else R_SCRAP_NOTE_MAYBE
    # a name that is only one space-justified material word, with no specification (鉄　　骨, 鉄　　筋 on a 科目別 sheet): the
    # usual 内訳書 writes the summary of a material so; it may repeat the detail rows (15 回目の攻撃)
    just = bool(fid) and not spec0.strip() and bool(_JUSTIFIED.fullmatch(shown.strip()))
    # a removal "maybe" that comes only from a phrase naming a room or place (Break-out area: carpet tiles) (16 回目)
    dplace = demolish == MAYBE and _dem_place(((name, spec), (shown, spec0)))
    # the safety net (16 回目): a row with no field and no mark whose name or specification names a material in some part
    # (after an excluding word, in a part of place or purpose, before 除く・別途) of a field that takes the row's unit. Read
    # once more per row, at most MAX_PARTS parts of MAX_NAME characters (not charged to the document's budget)
    net = None
    if not fid and u and not (total or again or deduct or demolish or work):
        net = _named_anywhere(text, div, lambda f: u in FL.FIELDS[f]["units"])
    return {"name": shown, "fid": fid, "u": u, "total": total, "again": again, "deduct": deduct,
            "demolish": demolish, "work": work, "ref": bool(spec0 and _AGAIN_REF.search(spec0)),
            "scrap": scrap, "just": just, "aside": bool(fid) and _after_aside(text), "nai": nai, "dplace": dplace,
            "net": net}


_JA_EXCL_RX = re.compile("|".join(re.escape(w) for w in sorted(JA_EXCL_AFTER, key=len, reverse=True)))


def _named_anywhere(text: str, div: str, fits):
    """The safety net for a row that names no field (16 回目): the field of the first material that a part of the name or
    specification names (also a part after an excluding word: excl. plasterboard; a part of place or purpose: under
    concrete slab; a material before a Japanese excluding ending: 石膏ボード除く) and for which fits(field) holds (the row's
    unit is one of the field's). The row is then listed on that field's card as "may belong", with its quantity, instead
    of only among the rows not used. A product of no field (鉄筋用スペーサー, 断熱サッシ) names none."""
    return next((f for f in _named_fields(text, div) if fits(f)), None)


@functools.lru_cache(maxsize=8192)
def _named_fields(text: str, div: str) -> tuple:
    """The fields that the parts of a name name, in order (see _named_anywhere; at most MAX_PARTS parts of MAX_NAME
    characters, as _head reads it)."""
    low, out = text.lower()[:MAX_NAME], []
    fdn = any(w in normalise_name(div) + " " + low for w in FOUNDATION_WORDS)
    for seg, _place, _prep in _parts(low):
        seg = _JA_EXCL_RX.sub(" ", seg)
        ms = _matches(seg)
        h = _head_of(seg, ms)[0] if ms else None
        if h is not None:
            fid = "m_concrete_fdn" if h[2] == "m_concrete" and fdn else h[2]
            if fid not in out:
                out.append(fid)
    return tuple(out)


_BLOCK_WORD = re.compile(r"(?i)blocks?|ブロック")


def _block_as_concrete(fid, text: str, div: str, u) -> str | None:
    """A concrete block row measured in m3 is concrete (foundation concrete when the rest of the name or the division
    says so), on every path that reads a table, a PDF or an IFC (13 回目: the word is taken out in any letter case)."""
    if fid == "m_masonry" and u == "m3" and _concrete_block(text):
        return "m_concrete_fdn" if _classify(_BLOCK_WORD.sub(" ", text), div) == "m_concrete_fdn" else "m_concrete"
    return fid


@functools.lru_cache(maxsize=8192)
def _concrete_block(text: str) -> bool:
    """A block row that names concrete (Mass concrete anchor blocks, コンクリートブロック): in m3 it is cast or precast
    concrete, not blockwork (measured in m2)."""
    fid, hs, a, b, parts = _head(text)
    if not (0 <= hs < len(parts)):
        return False
    w = parts[hs][a:b]
    low = text.lower()
    return w in ("block", "blocks", "ブロック") and ("concrete" in low or "コンクリート" in low)


# why a row that names a field's material was not added, and whether adding it might have been right (then the
# candidate may be too low: the card says so). Totals, 再掲, deductions, removals and negative rows are surely not part.
R_TOTAL = "合計・小計の行は足さない（二重計上を防ぐ）"
R_AGAIN = "再掲・内数（うち・内訳）の行は足さない（ほかの行に含まれている。二重計上を防ぐ）"
R_DEDUCT = "控除・差し引き（スクラップ・発生材など）の行は足さない（差し引きにもしない。必要なら手で直す）"
R_DEMOLISH = "撤去・解体・処分の行（今ある物を取り除く。新しい材料ではない）は足さない"
R_DEMOLISH_MAYBE = "材料の後に撤去・解体・処分の語がある（取り除く行か、材料の行の注記か分からない）ので足さない。材料の行なら手で入れる"
# a mark only in the specification (摘要): perhaps a note on the material row (14 回目)
R_AGAIN_MAYBE = "規格・摘要にうち・内訳などの語がある（ほかの行の内訳か、材料の行の注記か分からない）ので足さない。材料の行なら手で入れる"
R_DEDUCT_MAYBE = "規格・摘要に控除などの語がある（控除の行か、材料の行の値段の注記か分からない）ので足さない。材料の行なら手で入れる"
# a row whose name is the scrap itself, with no deduction or sale word (15 回目)
R_SCRAP_MAYBE = "名前がスクラップ・くずの行（スクラップの控除・売却か、材料の行か分からない）なので足さない。材料の行なら手で入れる"
# … and a scrap note after the material in a one-column name (異形鉄筋 SD345 D13 スクラップ買取共) (15 回目の攻撃)
R_SCRAP_NOTE_MAYBE = "名前の材料の後にスクラップの注記がある（スクラップの控除・売却の行か、材料の行の値段の注記か分からない）" \
                     "ので足さない。材料の行なら手で入れる"
# the material named after an excluding word set off by commas: the rest of what is excluded, or the item (15 回目の攻撃)
R_ASIDE_MAYBE = "読点の後の除く語（excluding・without など）のさらに読点の後に材料の名前がある（除く物の続きか、この行の材料か" \
                "分からない）ので足さない。この行の材料なら手で入れる"
# a name that is only one space-justified material word, with no specification (15 回目の攻撃)
R_JUSTIFIED_MAYBE = "字間をそろえた科目名だけの行（鉄　　骨 など。規格の無い集計の行で、明細の行と二重になるかもしれない）" \
                    "なので足さない。材料の行なら手で入れる"
# a name or division cell that is only a space-justified 内 word (内　　壁, 内　部, 内　装): the 内 may be a letter of the
# word or the breakdown mark (16 回目)
R_AGAIN_NAI_MAYBE = "名前・区分の欄が字間をそろえた「内」の語だけ（内　　壁・内　部 など。内訳の印か、語の 1 字か分からない）" \
                    "なので足さない。材料の行なら手で入れる"
# a removal phrase that is the name of a room or place (break-out area, strip out zone) before the material, or in a name
# with no material (16 回目)
R_DEMOLISH_PLACE_MAYBE = "撤去の語（break out・strip out など）が部屋・場所の名前（break-out area など）にある（取り除く行か、" \
                         "その場所の新しい材料の行か分からない）ので足さない。材料の行なら手で入れる"
# a row that names no field, while a material word is in a part after an excluding word, in a part of place or purpose,
# or before a Japanese excluding ending, and the row's unit is one of that material's (16 回目: the safety net)
R_PART_MAYBE = "材料の名前が、除く物・置く場所・用途などを言う部分（excluding・without・under・for などの後や、除く・別途の前）" \
               "にだけある（この行の材料か分からない）ので足さない。この行の材料なら手で入れる"
# 内訳書による on a row of a workbook whose other sheet counts rows of the same material (14 回目; 15 回目: only rows that
# are counted, decided once every row is read)
R_REF_MAYBE = "規格・摘要に内訳書による・内訳別紙などの注記があり、同じ資料の別のシート（%s）で同じ材料の行（%d 行目）を" \
              "数えている（その内訳と二重になるおそれ）ので足さない。材料の行なら手で入れる"
_FAMILY = {"m_concrete_fdn": "m_concrete"}     # (a breakdown may split concrete into foundation and the rest)
# cells of rows that are not material rows (a helper sheet with no bill header, per-floor take-off, hidden detail rows)
# that a counted row of the same material already sums (15 回目)
R_COPY_HELPER = "別のシート（%s）の材料の行（%d 行目）が足し上げたセル（%s）を足した値は足さない（その行で数えているので" \
                "二重計上になる）"
R_COPY_HELPER_SAME = "同じシートの材料の行（%d 行目）が足し上げたセル（%s）を足した値は足さない（再掲・検算のおそれ）。" \
                     "足すべき行なら手で入れる"
R_COPY_HELPER_SOME = "材料の行（%s の %d 行目）が足し上げたセル（%s）の一部を足した値は足さない（二重計上のおそれ）。" \
                     "足すべき行なら手で入れる"
# … all of them, but that row uses a single cell or scales them, or this row looks them up or chooses them by a criterion
# (15 回目の攻撃)
R_COPY_HELPER_MAYBE = "材料の行（%s の %d 行目）が数量に使ったセル（%s）を足した値は足さない（同じ量を二重に数えるおそれ）。" \
                      "足すべき行なら手で入れる"
R_HELPER_BUDGET = "数えた行が足し上げたセルとの照合が多すぎて確かめられない（1 つの資料で %d 歩まで）。必要なら手で入れる"
# a copy of a row that is itself left out as "may belong" (内訳書による, うち, 撤去 after the material …): that row is not
# counted, so the copy is no sure double count (15 回目の攻撃)
R_COPY_LEFT = "別のシート（%s）の材料の行（%d 行目）の数量を参照した値は足さない。その行も「足すべきかもしれない行」として" \
              "足していないので、足すべきならどちらか一方だけを手で入れる"
# … the same for a row that sums the cells a row of another sheet summed, when that row is not counted either (16 回目)
R_COPY_HELPER_LEFT = "別のシート（%s）の材料の行（%d 行目）が足し上げたセル（%s）を足した値は足さない。その行も「足すべき" \
                     "かもしれない行」として足していないので、足すべきならどちらか一方だけを手で入れる"
# a pivot table of a visible sheet with no quantity header, read by one row only (15 回目の攻撃)
R_PIVOT_ONLY = "%s の %d 行目はピボットテーブル（%s）の値を参照しているが、元の表 %s の数量は資料のほかの行で数えていないので足した"
# … one warning per pivot table when it is so read by rows of several materials, each the only row of its material (16 回目:
# one warning per row held the server and filled the answer)
R_PIVOT_ONLY_N = "ピボットテーブル（%s）の値を参照している %d 行（%s）は、元の表 %s の数量を資料のほかの行で数えておらず、" \
                 "どれもその材料でピボットテーブルの値を参照するただ 1 つの行なので足した"
# … read by two or more rows of one material (the parts and the whole of コンクリート): a subtotal and the grand total cannot be
# told apart, so none is added and each names the others (16 回目: every one was added, twice the quantity)
R_PIVOT_MANY = "ピボットテーブル（%s）の値を参照した値は足さない（元の表 %s の集計）。同じ材料のほかの行（%s）もピボット" \
               "テーブルの値を参照していて、小計と総計を重ねて数えるおそれがあるので、どれも足していない。足すべき行なら元の表を" \
               "確かめて、重ならない行だけを手で入れる"
# a value read from a pivot table of a source that is read here, while its material is counted nowhere in the file
R_PIVOT_REF_ALONE = "ピボットテーブル（%s）の値を参照した値は足さない（元の表 %s の集計）。この材料は資料のどこでも数えて" \
                    "いないので、足すべき行なら元の表を確かめて手で入れる"
R_WORK = "作業の行（加工・運搬・打設など。材料の量を繰り返す）は足さない（二重計上を防ぐ）"
R_NEG = "負の数量は読まない（差し引きにしない）"
R_COPY_SHEET = "別のシート（%s）の材料の行（%d 行目）の数量を参照した値は足さない（そのシートも読んでいるので二重計上になる）"
# … but a row of ANOTHER material worked out from it (鉄筋 = 明細のコンクリート × 0.12) may belong: maybe, when no row of
# its own material is counted anywhere in the file (13 回目); when one is, it is surely not added (14 回目)
R_COPY_SHEET_OTHER = "別のシート（%s）のほかの材料の行（%d 行目）の数量から計算した値は足さない（二重計上のおそれ）。" \
                     "別の材料を比率で出した行など、足すべき行なら手で入れる"
R_COPY_SHEET_COUNTED = "別のシート（%s）のほかの材料の行（%d 行目）の数量から計算した値は足さない（その材料は %s の %d 行目で" \
                       "数えている。二重計上を防ぐ）"
# … counted only in the other field of the same material (コンクリート（上部構造） for a 基礎 row): it may still belong
R_COPY_SHEET_KIN = "別のシート（%s）のほかの材料の行（%d 行目）の数量から計算した値は足さない（二重計上のおそれ）。" \
                   "%sは %s の %d 行目で数えている。%sの分なら手で入れる"
# an IFC element whose renovation status (Pset_…Common.Status) says it is no new material (15 回目)
R_IFC_DEMOLISH = "IFC の部材の状態（Status）が解体（DEMOLISH）：今ある物を取り除く部材で、新しい材料ではないので足さない"
R_IFC_EXISTING = "IFC の部材の状態（Status）が既存（EXISTING）：今ある部材で、新しい材料ではないので足さない"
R_IFC_TEMPORARY = "IFC の部材の状態（Status）が仮設（TEMPORARY）：建物に残らない部材かもしれないので足さない。" \
                  "残る部材なら手で入れる"
R_IFC_STATUS = {"DEMOLISH": R_IFC_DEMOLISH, "EXISTING": R_IFC_EXISTING, "TEMPORARY": R_IFC_TEMPORARY}
# … and a part with no status of its own, of a whole with that status (15 回目の攻撃)
R_IFC_STATUS_WORD = {"DEMOLISH": "解体（DEMOLISH）", "EXISTING": "既存（EXISTING）", "TEMPORARY": "仮設（TEMPORARY）"}
R_IFC_PART = "IFC でこの部材を含む部材（%s）の状態（Status）が%s：この部材には状態の記録が無いが、同じく新しい材料ではない" \
             "かもしれないので足さない。新しい部材なら手で入れる"
SURELY_NOT = (R_TOTAL, R_AGAIN, R_DEDUCT, R_DEMOLISH, R_NEG, tabular.HEADING, R_IFC_DEMOLISH, R_IFC_EXISTING)
# reasons with a place in them that are surely not part of the total (a copy of what another sheet counts, a pivot
# table of a sheet that is read)
_SURELY_NOT_RX = re.compile("|".join("(?:%s)" % re.escape(r).replace(re.escape("%s"), ".*").replace(re.escape("%d"), r"\d+")
                                     for r in (R_COPY_SHEET, R_COPY_SHEET_COUNTED, tabular.R_PIVOT, R_COPY_HELPER)), re.S)


def _maybe(reason: str) -> bool:
    """Whether a row left out for this reason might belong in the total (then the candidate may be too low)."""
    return reason not in SURELY_NOT and not _SURELY_NOT_RX.fullmatch(reason)


MAX_EVIDENCE = 200
_TO_T = {"t": 1.0, "kg": 0.001}


def _by_dimension(sums: dict) -> dict:
    """{field: {"mass" or unit: [(quantity, trace, unit, name) …]}} of the rows added (t and kg are one dimension)."""
    by_field = {}
    for (fid, u), items in sums.items():
        by_field.setdefault(fid, {}).setdefault("mass" if u in _TO_T else u, []).extend((q, t, u, nm) for q, t, nm in items)
    return by_field


def _chosen_dim(dims: dict):
    """(the dimension whose rows are proposed, or None when as many rows have another; the counts)."""
    counts = sorted(((len(v), k) for k, v in dims.items()), reverse=True)
    if len(counts) > 1 and counts[0][0] == counts[1][0]:
        return None, counts
    return counts[0][1], counts


def _counted_traces(sums: dict) -> set:
    """The traces of the rows that end in a proposal (the rows of a dimension that is not proposed do not)."""
    out = set()
    for dims in _by_dimension(sums).values():
        dim = _chosen_dim(dims)[0]
        if dim is not None:
            out.update(t for _q, t, _u, _n in dims[dim])
    return out


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
        its quantity and unit when it has them, so that a possible shortfall can be judged on the card). Returns the
        entries made (a reason decided later is written into them)."""
        u_ = {"trace": r_trace, "name": r_name[:80], "reason": reason}
        unused.append(u_)
        if not fid:
            return (u_,)
        x = {"trace": r_trace, "name": r_name[:80], "reason": reason, "maybe": _maybe(reason)}
        if qty is not None and qty != "":
            x["quantity"] = qty if isinstance(qty, (int, float)) else str(qty)[:40]
        if unit:
            x["unit"] = str(unit)[:20]
        excluded.setdefault(fid, []).append(x)
        return u_, x

    if kind in ("csv", "xlsx"):
        parsed = tabular.read_csv(data, doc_id) if kind == "csv" else tabular.read_xlsx(data, doc_id)
        warnings += parsed.get("warnings", [])
        prep, cells = _Prep(), _Cells(parsed)
        classed = []                       # (sheet casefolded, row, class) of the candidate rows, in reading order
        status = {}                        # (sheet, row) -> the entries of a row left out, or the trace of a row added
        row_fid = {}                       # (sheet casefolded, row) -> the field a material / marked row names (or None)
        n_classified, stopped = 0, None
        for sh in parsed["sheets"]:
            if sh.get("error"):
                warnings.append("%s：%s" % (tabular.sheet_label(sh["sheet"]), sh["error"]))
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
                # dimensions sheet is not a material quantity). A pivot table's cells are no such rows: a quantity
                # that reaches them reads the pivot table (its reason, see _Cells._children; 15 回目)
                if r.get("pivot"):
                    pass
                elif c["fid"] and c["u"] in FL.FIELDS[c["fid"]]["units"]:
                    mats.append(r["row"])
                    nums[r["row"]] = r.get("ncols") or ()
                    row_fid[(shf, r["row"])] = c["fid"]
                elif c["total"] or c["again"] or c["work"] or c["deduct"] or c["demolish"]:
                    marks.append(r["row"])
                    nums[r["row"]] = r.get("ncols") or ()
                    row_fid[(shf, r["row"])] = c["fid"]
                if cand:
                    classed.append((shf, r, c))
                elif r.get("heading"):
                    leave(None, r["trace"], r["name"], r["reason"])   # コンクリート工事: no row of a material
                else:
                    status[(shf, r["row"])] = leave(c["fid"], r["trace"], r["name"], r["reason"], r.get("qtext"),
                                                    r.get("unit"))
            if mats:
                cells.targets[shf] = sorted(set(mats + marks))
                cells.tcols[shf] = list(sh.get("qcols") or [sh.get("qcol") or 0])
                cells.xcols[shf] = xcols
                cells.keycols[shf] = tuple(sh.get("keycols") or ())
                cells.sizecols[shf] = frozenset(sh.get("sizecols") or ())
                for rn in cells.targets[shf]:
                    cells.rnums[(shf, rn)] = tuple(sorted(set(nums.get(rn) or ())))
                    cells.own_parts(shf, rn)        # its parts and dimensions; its other numbers outside them
                    cells.ncols[(shf, rn)] = sorted(set(nums.get(rn) or ()) - xcols - set(cells.dims.get((shf, rn), ())))
        if stopped:
            warnings.append(stopped)
        names_ = parsed.get("sheet_names", {})
        # the rows added (in reading order, with their place in it), rows that copy another material, rows with a
        # reference note (内訳書による) and rows that read a pivot table of a source read here: the last three are decided
        # once every row is read (15 回目)
        added, others, refs, pivot_refs = [], [], [], []
        helpers = _Helpers()
        helper_cut = [0]                   # rows not checked for want of _Helpers' budget
        # (entries, (sheet, row), rows reached, the reason when none of them is counted) of the rows left out as a sure
        # copy: of another sheet's material row, or of the cells such a row sums (16 回目)
        copies = []
        lone = []                          # rows that read a pivot table of a visible sheet with no quantity header
        pv_readers = {}                    # family -> (sheet, row) of every row of it that reads such a pivot table
        row_at = {(shf, r["row"]): r for shf, r, _c in classed}
        # the sheets such pivot tables summarise: every block of them that a counted row reaches is kept (see below)
        watched = {pv["src"] for pvs in (parsed.get("pivots") or {}).values() for pv in pvs
                   if pv.get("kind") == "unread" and pv.get("src_seen")}
        reach_unknown = [False]            # a counted row reaches more blocks than kept, or could not be followed

        def helper_parts(shf, row, fid):
            """Keep the cells an added row sums from rows that are no material rows (see _Helpers), and every block it
            reaches by adding on a watched sheet."""
            try:
                srcs, over = cells.sources(shf, row, sh_qcol(parsed, shf))
            except _FollowBudget:
                reach_unknown[0] = True
                return                     # (the row is added; the next rows are not checked for want of budget)
            try:
                helpers.add(_family(fid), (shf, row), _helper_parts(srcs))
                if watched:
                    if over:
                        reach_unknown[0] = True
                    helpers.add("*", (shf, row), [(b, PART_MAYBE) for b, _lv, _m in srcs if b[0] in watched])
            except _HelperBudget:
                reach_unknown[0] = True

        for seq, (shf, r, c) in enumerate(classed):
            why = None
            lf = c["fid"]                  # (the field whose card lists the row if it is left out)
            pref = None
            sure_copy = None               # (sheet, row) of the row this one surely copies, the rows it reaches,
            left_why = None                # … and its reason when none of them is counted (see `copies`)
            if c["total"]:
                why = R_TOTAL
            elif c["again"] == SURE:
                why = R_AGAIN
            elif c["deduct"] == SURE:
                why = R_DEDUCT
            elif c["demolish"] == SURE:
                why = R_DEMOLISH
            elif c["again"] or c["deduct"]:    # a mark only in the specification (14 回目): "maybe", unless negative
                why = R_NEG if r["quantity"] < 0 else (R_AGAIN_NAI_MAYBE if c.get("nai") else R_AGAIN_MAYBE) \
                    if c["again"] else c.get("scrap") or R_DEDUCT_MAYBE
            elif c["demolish"]:
                why = R_DEMOLISH_PLACE_MAYBE if c.get("dplace") else R_DEMOLISH_MAYBE
            elif c["work"]:
                why = R_WORK
            elif r["quantity"] < 0:
                why = R_NEG
            elif r.get("pivot"):
                why = r["pivot"]           # a pivot table's cell: a summary of another table (14 回目)
            elif c["fid"] is None:
                # … but a material named in some part whose field takes the row's unit: on that field's card as "may
                # belong", with its quantity (16 回目: the safety net)
                lf = c.get("net")
                why = R_PART_MAYBE if lf else "どの材料の欄にも当てはまらない"
            elif c["u"] not in FL.FIELDS[c["fid"]]["units"]:
                f_ = FL.FIELDS[c["fid"]]
                why = "単位 %r は「%s」に使えない（%s）。必要なら換算して手で入れる" % (r["unit"], f_["label"], "・".join(f_["units"]))
            elif r.get("qf"):
                got = cells.copy_of(shf, r["row"], sh_qcol(parsed, shf), r["qf"])
                other = None
                if got and got[0] == "copy":
                    _k, tsh, trow = got
                    if tsh == shf:
                        why = "同じシートのほかの材料の行（%d 行目）の数量から計算した値（合計・再掲・割増のおそれ）は足さない。" \
                              "別の材料を比率で出した行など、足すべき行なら手で入れる" % trow
                    elif cells.reaches_same(shf, r["row"], sh_qcol(parsed, shf), c["fid"], row_fid):
                        # it reaches a row of the same material (or a total of no material): a copy of what that sheet
                        # counts. Only rows of other materials: it may belong (鉄筋 = 明細のコンクリート × 0.12)
                        why = R_COPY_SHEET % (tabular.sheet_label(names_.get(tsh, tsh)), trow)
                        sure_copy = ((tsh, trow), cells.last_hits)
                        left_why = R_COPY_LEFT % (tabular.sheet_label(names_.get(tsh, tsh)), trow)
                    else:                  # only another material's row there: decided once every row is read
                        why = R_COPY_SHEET_OTHER % (tabular.sheet_label(names_.get(tsh, tsh)), trow)
                        other = (tsh, trow)
                elif got and got[0] == "pivot" and got[2] is not None and not _maybe(got[1]):
                    # a pivot table whose source is read here: surely not added when its material is counted (decided
                    # once every row is read)
                    why, pref = got[1], got[2]
                elif got and got[0] == "pivot" and got[2] is not None and got[2].get("kind") == "unread" \
                        and got[2].get("src_seen"):
                    # a pivot table of a visible sheet with no quantity header: perhaps the only count of those
                    # cells, decided once every row is read (15 回目の攻撃). A space-justified name alone or a material
                    # after an aside "may belong" first, as on any row (16 回目: such a row skipped those checks and
                    # was added); it is still one of the rows of its material that read such a pivot table
                    pv_readers.setdefault(_family(c["fid"]), []).append((shf, r["row"]))
                    if c.get("just") or c.get("aside"):
                        why = R_JUSTIFIED_MAYBE if c.get("just") else R_ASIDE_MAYBE
                        # (what it reads still counts as a read of those cells: another row reading the same cell is
                        # then no only reader of it, as before 16 回目. No entries: it is decided here, not below)
                        lone.append((seq, shf, r, c, None, got[2]))
                    else:
                        ents = status[(shf, r["row"])] = leave(c["fid"], r["trace"], c["name"], got[1], r["quantity"],
                                                               r.get("unit"))
                        lone.append((seq, shf, r, c, ents, got[2]))
                        continue
                elif got:
                    why = got[1]
                else:
                    # cells of rows that are no material rows, which a counted row of the same material already sums
                    # (a helper sheet, per-floor take-off, hidden detail rows): a copy (15 回目)
                    try:
                        srcs, over = cells.sources(shf, r["row"], sh_qcol(parsed, shf))
                        hk = _helper_copy(cells, helpers, _family(c["fid"]), srcs, over)
                    except _FollowBudget:
                        cells.cut += 1
                        hk = ("budget",)
                    except _HelperBudget:
                        helper_cut[0] += 1
                        hk = ("helper budget",)
                    if hk and hk[0] == "budget":
                        why = "数式のたどる先が多すぎて確かめられない（1 つの資料で %d 歩まで）。必要なら手で入れる" % MAX_FOLLOW_STEPS
                    elif hk and hk[0] == "helper budget":
                        why = R_HELPER_BUDGET % HELPER_STEPS
                    elif hk:
                        kind_, (osh, orow), blk, n_met = hk
                        at_ = _cells_label(names_, blk)
                        if kind_ == "some":
                            why = R_COPY_HELPER_SOME % (tabular.sheet_label(names_.get(osh, osh)), orow, at_)
                        elif kind_ == "unsure":
                            why = R_COPY_HELPER_MAYBE % (tabular.sheet_label(names_.get(osh, osh)), orow, at_)
                        elif osh == shf:
                            why = R_COPY_HELPER_SAME % (orow, at_)
                        elif (osh, orow) not in row_at or _item_key(prep, row_at[(osh, orow)]) != _item_key(prep, r) or \
                                n_met != helpers.size.get((_family(c["fid"]), (osh, orow))) or \
                                not _same_quantity(r["quantity"], row_at[(osh, orow)]["quantity"]):
                            # another item of the same material from the same cells (the floor finish and the ceiling
                            # paint of the same rooms), or only some of the cells that row sums (one room of the floor
                            # finish): perhaps a copy only (16 回目: it was dropped surely, and which of two rows was
                            # dropped surely depended on the order of the sheets). So is the same item from the same
                            # cells with another quantity: the cells added twice (the boards on both faces of a wall:
                            # SUM(X)+SUM(X), SUM(X,X), the cells listed twice, whose blocks are met once), a number added,
                            # or another function of them (16 回目の攻撃)
                            why = R_COPY_HELPER_MAYBE % (tabular.sheet_label(names_.get(osh, osh)), orow, at_)
                        else:
                            why = R_COPY_HELPER % (tabular.sheet_label(names_.get(osh, osh)), orow, at_)
                            sure_copy = ((osh, orow), ((osh, orow),))
                            left_why = R_COPY_HELPER_LEFT % (tabular.sheet_label(names_.get(osh, osh)), orow, at_)
                # rows decided once every row is read keep their entries in `status` too: a copy of them is no sure
                # double count while they are not counted (16 回目)
                if other:
                    ents = status[(shf, r["row"])] = leave(c["fid"], r["trace"], c["name"], why, r["quantity"],
                                                           r.get("unit"))
                    others.append((ents, c["fid"], other))
                    continue
                if pref is not None:
                    ents = status[(shf, r["row"])] = leave(c["fid"], r["trace"], c["name"], why, r["quantity"],
                                                           r.get("unit"))
                    pivot_refs.append((ents, c["fid"], pref))
                    continue
            if not why and c.get("just"):
                why = R_JUSTIFIED_MAYBE        # 鉄　　骨 alone: perhaps the summary of the detail rows (15 回目の攻撃)
            if not why and c.get("aside"):
                why = R_ASIDE_MAYBE            # Infill panels, without frames, blockwork 100mm (15 回目の攻撃)
            if why:
                ents = status[(shf, r["row"])] = leave(lf, r["trace"], c["name"], why, r["quantity"], r.get("unit"))
                if sure_copy:
                    copies.append((ents, sure_copy[0], sure_copy[1], left_why, _family(c["fid"])))
                continue
            if c["ref"]:
                # 内訳書による: decided once every row is read (listed here for now, in reading order)
                ents = status[(shf, r["row"])] = leave(c["fid"], r["trace"], c["name"], R_REF_MAYBE, r["quantity"],
                                                       r.get("unit"))
                refs.append((seq, shf, r, c, ents))
                if r.get("qf") and watched:          # (it may be added: what it reaches is kept, see `lone`)
                    try:
                        srcs, over = cells.sources(shf, r["row"], sh_qcol(parsed, shf))
                        reach_unknown[0] = reach_unknown[0] or over
                        helpers.add("*", (shf, r["row"]), [(b, PART_MAYBE) for b, _lv, _m in srcs if b[0] in watched])
                    except (_FollowBudget, _HelperBudget):
                        reach_unknown[0] = True
                continue
            added.append((seq, shf, r, c))
            if r.get("qf"):
                helper_parts(shf, r["row"], c["fid"])
        listed_now = set()                 # the entries of rows that are added after all (taken out once, below)
        if lone:
            # a quantity that reads a pivot table of a visible sheet with no quantity header (拾い表 → ピボットテーブル →
            # 集計) is the only count of those cells when: no cell of that pivot table is a row of a quantity table, no
            # counted row reaches the table it summarises, no other row counts its material, and this row reads one
            # cell of it (nothing else) that no other such row reads. Otherwise it stays "may belong" (15 回目の攻撃:
            # the only count was dropped). It must also be the only row of its material that reads such a pivot table
            # anywhere in the file: two or more (the parts and the whole of コンクリート, two pivot tables of one take-off)
            # cannot be told apart, so none is added and each names the others (16 回目: every one was added)
            pv_rows = {}                   # sheet -> sorted rows of pivot table cells that are candidate rows
            for sh in parsed["sheets"]:
                for x in list(sh.get("rows") or ()) + list(sh.get("skipped") or ()):
                    if x.get("pivot"):
                        pv_rows.setdefault(str(sh["sheet"]).casefold(), []).append(x["row"])
            for v in pv_rows.values():
                v.sort()
            # the reads of each pivot table, indexed once: a single cell by the cell, a larger block in a list of the
            # pivot table looked at only for the few rows that may be added (16 回目: every row was compared with every
            # read, which held the server for 45 s on 19,000 rows)
            cell_reads, block_reads, one_cell = {}, {}, []
            for seq, shf, r, c, ents, pv in lone:
                cell = None
                try:
                    srcs, over = cells.sources(shf, r["row"], sh_qcol(parsed, shf))
                except _FollowBudget:
                    srcs, over = [], True
                inside = [b for b, _lv, _m in srcs if b[0] == pv["sheet"] and b[1] <= pv["c2"] and pv["c1"] <= b[2]
                          and b[3] <= pv["r2"] and pv["r1"] <= b[4]]
                if over:                   # (what it reads is not all known: as if it read the whole pivot table)
                    inside.append((pv["sheet"], pv["c1"], pv["c2"], pv["r1"], pv["r2"]))
                for b in inside:
                    if _one_cell_block(b):
                        cell_reads[(id(pv), b)] = cell_reads.get((id(pv), b), 0) + 1
                    else:
                        block_reads.setdefault(id(pv), []).append(b)
                if not over and len(inside) == len(srcs) == 1 and _one_cell_block(inside[0]):
                    cell = inside[0]
                one_cell.append(cell)
            # the material families counted elsewhere (or perhaps counted: a row with a reference note): the pivot table's
            # value may then repeat them, and the row stays "may belong"
            fams = {_family(c_["fid"]) for _s, _sh, _r, c_ in added} | {_family(x[3]["fid"]) for x in refs}
            added_from = {}                # id(pivot table) -> (pivot table, [(sheet, row)] of the rows added)
            for (seq, shf, r, c, ents, pv), cell in zip(lone, one_cell):
                if ents is None:
                    continue               # a justified name or an aside: "may belong" for its name (above)
                group = pv_readers.get(_family(c["fid"]), ())
                if len(group) > 1:
                    them = [x for x in group[:4] if x != (shf, r["row"])][:3]
                    said = "、".join("%s の %d 行目" % (tabular.sheet_label(names_.get(x[0], x[0])), x[1]) for x in them)
                    if len(group) - 1 > len(them):
                        said += " ほか %d 行" % (len(group) - 1 - len(them))
                    reason = R_PIVOT_MANY % (pv.get("name") or "名前なし", pv.get("label") or "", said)
                    for e in ents:
                        e["reason"] = reason
                        if "maybe" in e:
                            e["maybe"] = _maybe(reason)
                    continue
                if cell is None or reach_unknown[0] or helpers.full or _family(c["fid"]) in fams:
                    continue
                try:
                    n_reads = cell_reads.get((id(pv), cell), 0)
                    for b in block_reads.get(id(pv), ()):
                        helpers.spend()
                        if b[1] <= cell[1] <= b[2] and b[3] <= cell[3] <= b[4]:
                            n_reads += 1
                            break
                except _HelperBudget:
                    continue
                if n_reads != 1:
                    continue               # another row reads that cell too
                rows_ = pv_rows.get(pv["sheet"], ())
                k = bisect.bisect_left(rows_, pv["r1"])
                if k < len(rows_) and rows_[k] <= pv["r2"]:
                    continue               # the pivot table's cells are rows of a quantity table
                sb = pv.get("sref") or (0, tabular.MAX_COLS - 1, 1, tabular.MAX_ROW_NUMBER)
                try:
                    if helpers.cover("*", (pv["src"], sb[0], sb[1], sb[2], sb[3])) is not None:
                        continue           # a counted row reaches the table it summarises
                except _HelperBudget:
                    continue
                listed_now.update(id(e) for e in ents)
                status[(shf, r["row"])] = r["trace"]
                added.append((seq, shf, r, c))
                helper_parts(shf, r["row"], c["fid"])
                added_from.setdefault(id(pv), (pv, []))[1].append((shf, r["row"]))
            for pv, rows_ in added_from.values():      # one warning per pivot table (16 回目: one per row)
                if len(rows_) == 1:
                    warnings.append(R_PIVOT_ONLY % (tabular.sheet_label(names_.get(rows_[0][0], rows_[0][0])), rows_[0][1],
                                                    pv.get("name") or "名前なし", pv.get("label") or ""))
                else:
                    said = "、".join("%s の %d 行目" % (tabular.sheet_label(names_.get(x[0], x[0])), x[1]) for x in rows_[:3])
                    if len(rows_) > 3:
                        said += " ほか %d 行" % (len(rows_) - 3)
                    warnings.append(R_PIVOT_ONLY_N % (pv.get("name") or "名前なし", len(rows_), said, pv.get("label") or ""))
            added.sort(key=lambda x: x[0])
        if refs:
            # 内訳書による / 別紙による on a row of a workbook whose other sheet COUNTS rows of the same material (コンクリート
            # with 基礎のコンクリート): perhaps that breakdown, so "may belong", naming the counted row. Rows that are never
            # counted (pivot table cells, copies — above all copies of this row —, total / 再掲 / work / deduction /
            # removal rows) are no breakdown; on a single sheet, or with no such row elsewhere, the note only points to
            # another document and the row is added (14 回目; 15 回目: the rule was fed by every row that named the
            # material and dropped the only real row)
            sums0 = {}
            for _s, _shf, r, c in added:
                sums0.setdefault((c["fid"], c["u"]), []).append((r["quantity"], r["trace"], c["name"]))
            kept0, first = _counted_traces(sums0), {}
            for _s, shf, r, c in added:
                if r["trace"] in kept0:
                    first.setdefault(_family(c["fid"]), {}).setdefault(shf, r["row"])
            for seq, shf, r, c, ents in refs:
                elsewhere = [(s_, rw) for s_, rw in first.get(_family(c["fid"]), {}).items() if s_ != shf]
                if elsewhere:
                    osh, orow = elsewhere[0]
                    for e in ents:
                        e["reason"] = R_REF_MAYBE % (tabular.sheet_label(names_.get(osh, osh)), orow)
                    continue
                listed_now.update(id(e) for e in ents)
                status[(shf, r["row"])] = r["trace"]
                added.append((seq, shf, r, c))
                if r.get("qf"):
                    helper_parts(shf, r["row"], c["fid"])
            added.sort(key=lambda x: x[0])
        if listed_now:
            unused[:] = [u_ for u_ in unused if id(u_) not in listed_now]
            for fid in list(excluded):
                excluded[fid] = [x for x in excluded[fid] if id(x) not in listed_now]
                if not excluded[fid]:
                    del excluded[fid]
        where = {}                         # trace -> (field, (sheet, row)) of the rows added
        for _s, shf, r, c in added:
            sums.setdefault((c["fid"], c["u"]), []).append((r["quantity"], r["trace"], c["name"]))
            where[r["trace"]] = (c["fid"], (shf, r["row"]))
            status[(shf, r["row"])] = r["trace"]
        kept, counted, kin = _counted_traces(sums), {}, {}
        for t, (fid, at) in where.items():
            if t in kept:
                counted.setdefault(fid, at)
                kin.setdefault(_family(fid), (fid, at))
        if others:
            # a row worked out from another material's row (鉄筋 = 明細のコンクリート × 0.12) may belong only when its own
            # field is counted nowhere in the file; when it is, the row repeats it (14 回目). When only the other field
            # of its material is counted (基礎のコンクリート next to 上部構造のコンクリート), it may still belong: that row
            # is named and the row stays "may belong" (14 回目の攻撃: the foundations were dropped without a word)
            for ents, fid, (tsh, trow) in others:
                at = counted.get(fid)
                if at is not None:
                    reason = R_COPY_SHEET_COUNTED % (tabular.sheet_label(names_.get(tsh, tsh)), trow,
                                                     tabular.sheet_label(names_.get(at[0], at[0])), at[1])
                elif _family(fid) in kin:
                    # counted only in the other field of its material (基礎のコンクリート next to 上部構造のコンクリート):
                    # still may belong, the scope (foundations) is not dropped silently (14 回目の攻撃)
                    kfid, at = kin[_family(fid)]
                    reason = R_COPY_SHEET_KIN % (tabular.sheet_label(names_.get(tsh, tsh)), trow, FL.FIELDS[kfid]["label"],
                                                 tabular.sheet_label(names_.get(at[0], at[0])), at[1],
                                                 FL.FIELDS[fid]["label"])
                else:
                    continue
                for e in ents:
                    e["reason"] = reason
                    if "maybe" in e:
                        e["maybe"] = _maybe(reason)
        for ents, fid, pv in pivot_refs:
            # a value read from a pivot table of a source read here repeats what that source counts; when its material
            # is counted nowhere in the file (a ratio of another material, a source row left out), it may belong (15 回目).
            # The material, not the field: 基礎コンクリート = the pivot table's concrete repeats the source's concrete
            # whatever field the row names (15 回目の攻撃: it said the material was counted nowhere)
            if fid in counted or _family(fid) in kin:
                continue
            reason = R_PIVOT_REF_ALONE % (pv.get("name") or "名前なし", pv.get("label") or "")
            for e in ents:
                e["reason"] = reason
                if "maybe" in e:
                    e["maybe"] = _maybe(reason)
        # the rows that read a take-off's pivot table and are left out, with their field (see `uncounted`)
        pv_left = {(shf_, r_["row"]): c_["fid"] for _q, shf_, r_, c_, ents_, _pv in lone if ents_ is not None}
        for ents, (tsh, trow), reached, reason, fam in copies:
            # a sure copy of rows that are themselves not counted: each was left out as "may belong" (内訳書による, うち,
            # 撤去 after the material …) or added in a unit that is not proposed. Then the quantity is counted nowhere,
            # and the copy may belong too (15 回目の攻撃: it said "that sheet is read, a double count"). When one row it
            # reaches is counted, or left out surely (a total, 再掲: its parts are counted), it stays a sure copy. The rows
            # decided once every row is read (worked out from another material, read from a pivot table) and the counted
            # row whose cells a copy sums are looked at the same way, and only the rows reached of its own material (or
            # of none: a total) count: the concrete that 概算の鉄筋 = 明細のコンクリート × 0.12 also reaches does not count
            # the rebar (16 回目). A row that reads a take-off's pivot table and is left out while its own field is counted
            # elsewhere in the file is counted for this: the pivot table's value may repeat that count, and the copy
            # stays sure, as before 16 回目 (16 回目の攻撃: the copy said "add one of them by hand" of a quantity the
            # bill counts)
            def uncounted(at):
                st = status.get(at)
                if st is None:
                    return False
                if isinstance(st, str):
                    return st not in kept
                if at in pv_left and pv_left[at] in counted:
                    return False
                return _maybe(st[0]["reason"])
            reached = reached or ((tsh, trow),)
            mine = [at for at in reached if _family(row_fid.get(at)) in (None, fam)] or reached
            if not all(uncounted(at) for at in mine):
                continue
            for e in ents:
                e["reason"] = reason
                if "maybe" in e:
                    e["maybe"] = _maybe(reason)
        if cells.cut:
            warnings.append("数式のたどる先が多すぎるので、%d 行は確かめられず足していない（1 つの資料で %d 歩まで）。"
                            "その行は「使わなかった行」にある" % (cells.cut, MAX_FOLLOW_STEPS))
        if helper_cut[0]:
            warnings.append("数えた行が足し上げたセルとの照合が多すぎるので、%d 行は確かめられず足していない（1 つの資料で %d 歩"
                            "まで）。その行は「使わなかった行」にある" % (helper_cut[0], HELPER_STEPS))
    elif kind == "ifc":
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("latin-1")
        parsed = ifc.parse(text, doc_id)
        want = {"m3": "volume", "m2": "area", "kg": "weight", "t": "weight"}

        def ifc_why(e):
            """Why an element is no new material whatever its material, or None: by its status (Pset_…Common.Status
            DEMOLISH / EXISTING surely, TEMPORARY perhaps), by its name as a table row is (既存壁 撤去, Existing slab - to
            be demolished) (15 回目), or by the status of the whole it is part of (15 回目の攻撃)."""
            why = R_IFC_STATUS.get(e.get("status"))
            if why is None and e["name"]:
                en_ = _prep(e["name"])
                dem = _both(_demolish, en_)
                why = R_DEMOLISH if dem == SURE else None if not dem else \
                    R_DEMOLISH_PLACE_MAYBE if _dem_place(((en_, ""), (_justify(en_), ""))) else R_DEMOLISH_MAYBE
            if why is None and e.get("part_of"):
                # a part (IfcRelAggregates, IfcRelNests) with no status of its own, of a whole that is DEMOLISH, EXISTING
                # or TEMPORARY: perhaps the same (the panels of a curtain wall that is taken down) (15 回目の攻撃)
                po = e["part_of"]
                why = R_IFC_PART % (("%s %s" % (po["type"], po["name"]))[:60], R_IFC_STATUS_WORD.get(po["status"], ""))
            return why

        for e in parsed["elements"]:
            mats = " ".join(e["materials"]) + " " + e["name"]
            fdiv = "footing" if e["type"] in ("IFCFOOTING", "IFCPILE") else ""
            fid = _field_for(mats, fdiv)
            if e["type"] in ("IFCREINFORCINGBAR", "IFCREINFORCINGMESH"):
                fid = "m_rebar"
            elif fid == "m_masonry" and e["type"] in ("IFCFOOTING", "IFCPILE") and _concrete_block(_justify(_prep(mats))):
                fid = "m_concrete_fdn"           # a concrete block footing (anchor / thrust block) is foundation concrete
            label = "%s %s" % (e["type"], e["name"])
            net = False
            if fid is None:
                # the safety net (16 回目), only after the status check: an element with no status or removal reason whose
                # materials or name name a material in some part, with a quantity that material's field takes, is listed
                # on that card as "may belong". One with such a reason stays among the elements not used, as before
                kinds_ = {x["kind"] for x in e["quantities"]}
                if ifc_why(e) is None:
                    fid = _named_anywhere(_justify(_prep(mats)), _justify(_prep(fdiv)),
                                          lambda f: any(want[u] in kinds_ for u in FL.FIELDS[f]["units"]))
                if fid is None:
                    unused.append({"trace": "%s:#%d" % (doc_id, e["step_id"]), "name": label,
                                   "reason": "材料名から分類できない（%s）" % ("・".join(e["materials"]) or "材料の記録なし")})
                    continue
                net = True
            picked = None
            for u in FL.FIELDS[fid]["units"]:
                q = [x for x in e["quantities"] if x["kind"] == want[u]]
                if q:
                    # prefer net over gross when both exist (gross double-counts openings)
                    q.sort(key=lambda x: 0 if "net" in x["name"].lower() else 1)
                    picked = (u if u != "t" else "kg", q[0])
                    break
            # an element that is there, or is taken away, is no new material (see ifc_why); a material of the safety net
            # "may belong"
            why = ifc_why(e) or (R_PART_MAYBE if net else None)
            if why:
                if picked:
                    leave(fid, picked[1]["trace"], label, why, picked[1]["value"], picked[0])
                else:
                    leave(fid, "%s:#%d" % (doc_id, e["step_id"]), label, why)
                continue
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
            fid = _block_as_concrete(fid, _justify(_prep(c["name"])), "", u)
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
    to_t = _TO_T
    for fid, dims in _by_dimension(sums).items():
        # one field holds one value: t and kg rows are added in t; rows of another dimension (m3 next to t) cannot be
        # added. The dimension with more rows is proposed and the other rows are listed; when as many rows have one
        # dimension as another, neither is more likely the field's quantity, and nothing is proposed
        label = FL.FIELDS[fid]["label"]
        dim, counts = _chosen_dim(dims)
        if dim is None:
            desc = "・".join("%s の行 %d" % ("t・kg" if k == "mass" else k, n) for n, k in counts)
            for rows_ in dims.values():
                for q, t, u, nm in rows_:
                    leave(fid, t, nm, "同じ材料の行の単位が混ざっていて（%s）、どれが「%s」の量か決められない：確かめて手で入れる"
                          % (desc, label), q, u)
            continue
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
        ex = sorted(excluded.get(fid, []), key=lambda x: not x["maybe"])    # (stable: reading order within each)
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
    left_out = {fid: {"n_excluded": len(ex), "n_maybe": sum(1 for x in ex if x["maybe"]),
                      "excluded": sorted(ex, key=lambda x: not x["maybe"])[:20]}
                for fid, ex in excluded.items() if fid not in evidence}
    summ = {"n_rows": sum(len(s["rows"]) for s in parsed["sheets"])} if kind in ("csv", "xlsx") else \
        {"n_elements": len(parsed["elements"]), "schema": parsed["schema"]}
    if len(unused) > 2000:
        warnings.append("使わなかった行が多いので、最初の 2000 行だけを記録した（全部で %d 行）" % len(unused))
        unused = unused[:2000]
    return {"kind": kind, "sha256": sha, "parsed_summary": summ, "proposals": proposals, "evidence": evidence,
            "left_out": left_out, "unused": unused, "warnings": warnings}
