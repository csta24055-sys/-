"""Statistical estimates with a cited dataset and an interval — and an explicit refusal where no permitted data exists.

Only one estimator is connected to real data today:

  materials  q_m = MI_m(function, structure, region) × A_floor
             MI from RASMI (Fishman et al., Scientific Data 11, 418, 2024; data DOI 10.5281/zenodo.10782341, CC BY 4.0),
             region OECD_JPN, the p50 as the point and p5–p95 as the range. The range is the spread of the RASMI pool,
             not a calibrated prediction interval for one building: it is shown as 「仮の範囲」 unless validate.py measured
             its coverage on held-out buildings (the measured coverage is quoted in the note).

Equipment counts, operational energy and water have no permitted statistical source connected yet; the estimator says
so instead of inventing per-m2 coefficients (implementation directive: 「ソースのない具体的な係数を生成しない」).
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from . import fields as FL
from .importers.tabular import xlsx_sheets
from .provenance import HAS_VALUE, Uncertainty, Value
from .sources.net import SourceError, get

REGISTRY = Path(__file__).resolve().parent / "sources" / "registry.json"
RASMI_URL = "https://zenodo.org/api/records/10782341/files/MI_ranges_20230905.xlsx/content"
RASMI_ID = "rasmi_20230905"
RASMI_VERSION = "RASMI v20230905-B (zenodo 10782341)"
VALIDATION = Path(__file__).resolve().parents[1] / "docs" / "validation_results.json"

# RASMI material -> material field (the engine class is given by the field). copper: no engine class.
RASMI_TO_FIELD = {"concrete": "m_concrete", "brick": "m_masonry", "wood": "m_timber", "glass": "m_glass",
                  "plastics": "m_plastic", "aluminum": "m_aluminium", "steel": None}
STRUCTURE_TO_RASMI = {"RC": ("C", ""), "SRC": ("C", "SRC は RASMI に無いのでコンクリート造（C）の範囲を使った（仮定）"),
                      "S": ("S", ""), "W": ("T", "")}


def function_for(use: str, structure: str) -> tuple[str, str]:
    if use == "residential":
        return ("RS", "木造の住宅は戸建て（RS）の範囲を使った（仮定）") if structure == "W" else \
               ("RM", "住宅は共同住宅（RM）の範囲を使った（仮定）")
    return "NR", "非住宅（NR）の範囲を使った"


def registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


_ranges: dict | None = None


def load_ranges(data: bytes | None = None) -> dict:
    """{(material, function, structure, region): {p5..p95, counts}} from the RASMI ranges workbook (cached download)."""
    global _ranges
    if _ranges is not None and data is None:
        return _ranges
    if data is None:
        data, _ = get(RASMI_URL, timeout=120, max_age=365 * 86400)
    out = {}
    for name, rows in xlsx_sheets(data):
        if not rows:
            continue
        head = rows[0]
        idx = {h: j for j, h in enumerate(head) if h}
        for r in rows[1:]:
            if not r or len(r) <= idx.get("p_95", 99):
                continue
            try:
                rec = {k: float(r[idx[k]]) for k in ("p_0", "p_5", "p_25", "p_50", "p_75", "p_95", "p_100")}
                rec.update(raw=int(float(r[idx["raw_HF_db_count"]])), n=int(float(r[idx["incremented_count"]])),
                           iterations=int(float(r[idx["increment_iterations"]])))
            except (TypeError, ValueError, KeyError):
                continue
            out[(name, r[idx["function"]], r[idx["structure"]], r[idx["R5_32"]])] = rec
    _ranges = out
    return out


def _coverage_note() -> str:
    try:
        v = json.loads(VALIDATION.read_text(encoding="utf-8"))
        c = v["rasmi_in_sample"]["coverage_p5_p95"]
        h = v["holdout"]["coverage_p5_p95"]
        return "（検証：取り置いた建物での 5〜95% 範囲の当たり率 %.0f%%、RASMI そのものの範囲では %.0f%%（同じデータを含む））" % (100 * h, 100 * c)
    except Exception:
        return "（この範囲の当たり率はまだ検証していない）"


def estimate_materials(values: dict[str, Value], structure: str, only: str | None = None, ranges: dict | None = None) -> tuple[list[Value], list[str]]:
    msgs, out = [], []
    gfa, use = values.get("b_gfa"), values.get("b_use")
    if not (gfa and gfa.state in HAS_VALUE and use and use.state in HAS_VALUE):
        return [], ["材料の統計概算には延床面積と用途が要る（基本情報で入れるか、住所から調べる）"]
    try:
        R = ranges if ranges is not None else load_ranges()
    except SourceError as e:
        return [], ["RASMI の範囲表を取得できなかった：%s" % e]
    fn, fn_note = function_for(use.value, structure)
    st, st_note = STRUCTURE_TO_RASMI[structure]
    area = float(gfa.value)
    gfa_note = "" if gfa.state == "confirmed" else "延床面積が「%s」なので、その不確かさは範囲に含まれていない。" % gfa.label
    today = _dt.date.today().isoformat()
    cov = _coverage_note()
    for mat in ("concrete", "steel", "wood", "glass", "aluminum", "brick", "plastics", "copper"):
        rec = R.get((mat, fn, st, "OECD_JPN"))
        if mat == "copper":
            msgs.append("RASMI の銅（copper）はエンジンの材料分類に無いので使わない（反映外）")
            continue
        fid = RASMI_TO_FIELD[mat]
        notes = [n for n in (fn_note, st_note) if n]
        if mat == "steel":
            fid = "m_steel" if structure in ("S", "SRC") else "m_rebar"
            notes.append("RASMI の鉄（steel）は鉄筋と鉄骨を分けていない。%s では全量を「%s」とした（仮定）"
                         % (structure, FL.FIELDS[fid]["label"]))
        if only and fid != only:
            continue
        if rec is None:
            msgs.append("RASMI に %s・%s・%s・日本 の範囲が無い" % (mat, fn, st))
            continue
        cur = values.get(fid)
        if cur and cur.state in ("confirmed", "from_drawing"):
            msgs.append("「%s」には%sの値があるので統計の候補は作らない" % (FL.FIELDS[fid]["label"], cur.label))
            continue
        if mat == "concrete":
            fdn = values.get("m_concrete_fdn")
            if fdn and fdn.state in HAS_VALUE:
                msgs.append("基礎のコンクリートが別に入っているので、基礎を含む統計の全体量は候補にしない（二重計上を防ぐ）")
                continue
            notes.append("基礎・杭を含む建物全体の量。採用したら基礎の欄には別の値を入れない（入れると基礎の行は作らず、二重計上を防ぐ）")
        k = 1000.0   # kg -> t
        v = Value(fid, "statistical", round(rec["p_50"] * area / k, 3), "t", method="rasmi_mi_x_gfa", source_id=RASMI_ID,
                  source_detail="%s / %s / %s / OECD_JPN：中央値 %.1f kg/m2（元データ %d 件、補った後 %d 件、拡張 %d 回）"
                                % (mat, fn, st, rec["p_50"], rec["raw"], rec["n"], rec["iterations"]),
                  retrieved_at=today, factor_version=RASMI_VERSION, permission="CC-BY-4.0",
                  uncertainty=Uncertainty("interval", round(rec["p_5"] * area / k, 3), round(rec["p_95"] * area / k, 3), 0.9, False,
                                          "RASMI の 5〜95 パーセンタイル × 延床面積 %.1f m2" % area + cov),
                  note="；".join(notes + [gfa_note] if gfa_note else notes))
        out.append(v)
    msgs.append("出典：RASMI（Fishman ほか 2024、CC BY 4.0）。日本の元データは少なく、近い地域のデータで補われている（件数を候補に表示）。")
    return out, msgs


def run(values: dict[str, Value], structure: str, screen: str | None = None, field: str | None = None, demo: bool = False) -> dict:
    proposals, msgs = [], []
    target_screen = FL.FIELDS[field]["screen"] if field in FL.FIELDS else screen
    if target_screen == "material":
        if field and FL.FIELDS[field].get("role") != "material":
            msgs.append("「%s」の統計の出典はつないでいない（共通条件は資料か仮定で入れる）" % FL.FIELDS[field]["label"])
        else:
            p, m = estimate_materials(values, structure, only=field)
            proposals += p
            msgs += m
    elif target_screen == "basic":
        msgs.append("基本情報の候補は「住所から調べる」（国土地理院・PLATEAU）で作る。延床面積は PLATEAU の屋根面積×階数の仮定値になる。")
    elif target_screen == "equipment":
        msgs.append("設備の台数・質量の統計は、権利を確認できた出典がまだ無いので概算しない（仮の係数を作らない）。"
                    "メーカーの仕様書（質量）や設計図の機器表から入れる。台数が分からないときは「あとで確認」にする。")
    elif target_screen == "operation":
        msgs.append("運用のエネルギー・水の統計（例：非住宅建築物の環境関連データベース DECC）は、利用条件を確認できていないので使っていない。"
                    "請求書・検針の実績が一番よい。次が設計の計算、最後が統計。")
    else:
        msgs.append("どの画面の概算かが分からない")
    return {"proposals": proposals, "message": msgs[0] if msgs and not proposals else "", "messages": msgs}
