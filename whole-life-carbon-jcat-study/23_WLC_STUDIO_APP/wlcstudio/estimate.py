"""Statistical estimates with a cited dataset and an interval — and an explicit refusal where no permitted data exists.

Only one estimator is connected to real data today:

  materials  q_m = MI_m(function, structure, region) × A_floor
             MI from RASMI (Fishman et al., Scientific Data 11, 418, 2024; data DOI 10.5281/zenodo.10782341, CC BY 4.0),
             region OECD_JPN, the p50 as the point and p5–p95 as the range. The range is the spread of the RASMI pool,
             not a calibrated prediction interval for one building: it is shown as 「仮の範囲」 unless validate.py measured
             its coverage on held-out buildings (the measured coverage is quoted in the note).

  materials  q = u_s × A_floor / 10 for 生コンクリート (m3), 鋼材 (t), 木材 (m3), from 国土交通省「建設資材・労働力需要実態調査
             【建築部門】」令和6年度（令和5年度工事）面積原単位（延べ床面積 10 m2 当たり、全国、構造別）, e-Stat (政府標準利用規約 2.0,
             CC BY 4.0 compatible). A national mean has no spread, so the range shown is the RASMI relative spread (p5/p50, p95/p50)
             of the matching function × structure applied to this mean — stated as such, and 「仮の範囲」.
  operation  only a reference figure (not a candidate): 経済産業省「エネルギー消費統計調査」令和6年度 第3表B the energy use per
             floor area of the matching industry (GJ/m2) with its standard error. The engine needs electricity and gas separately
             and the table gives the total only, so it is not turned into an input value.

Equipment counts and water have no permitted statistical source connected yet; the estimator says so instead of inventing
per-m2 coefficients (implementation directive: 「ソースのない具体的な係数を生成しない」).
"""
from __future__ import annotations

import datetime as _dt
import json
import re
from pathlib import Path

from . import fields as FL
from .importers.tabular import xlsx_sheets
from .provenance import HAS_VALUE, Uncertainty, Value, competes
from .sources.net import SourceError, get

REGISTRY = Path(__file__).resolve().parent / "sources" / "registry.json"
RASMI_URL = "https://zenodo.org/api/records/10782341/files/MI_ranges_20230905.xlsx/content"
RASMI_ID = "rasmi_20230905"
RASMI_VERSION = "RASMI v20230905-B (zenodo 10782341)"
VALIDATION = Path(__file__).resolve().parents[1] / "docs" / "validation_results.json"
MLIT_URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040282146&fileKind=0"
MLIT_ID = "mlit_shizai_r6"
MLIT_VERSION = "建設資材・労働力需要実態調査【建築部門】令和6年度（令和5年度工事）面積原単位"
METI_URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040442517&fileKind=0"
METI_ID = "meti_energy_r6"
MLIT_ITEMS = {"生コンクリート": ("m_concrete", "m3", "concrete"), "鋼材": (None, "t", "steel"), "木材": ("m_timber", "m3", "wood")}
METI_ROWS = {"office": ("業務部門平均", "事務所は業種を決められないので業務部門の平均"), "school": ("学校教育", ""), "hospital": ("医療業", ""),
             "retail": ("卸売業，小売業", "卸売・小売業の平均"), "warehouse": ("倉庫業", "")}

# RASMI material -> material field (the engine class is given by the field). copper: no engine class.
RASMI_TO_FIELD = {"concrete": "m_concrete", "brick": "m_masonry", "wood": "m_timber", "glass": "m_glass",
                  "plastics": "m_plastic", "aluminum": "m_aluminium", "steel": None}
# the material fields some statistics source can estimate (国交省: concrete, steel or rebar, timber; RASMI: the rest)
ESTIMATED_FIELDS = {f for f, _u, _r in MLIT_ITEMS.values() if f} | {"m_rebar", "m_steel"} | \
    {f for f in RASMI_TO_FIELD.values() if f}
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


_mlit: dict | None = None


def load_mlit(data: bytes | None = None) -> dict:
    """{structure: {item: (value per 10 m2, unit)}} from the 面積原単位 sheet."""
    global _mlit
    if _mlit is not None and data is None:
        return _mlit
    if data is None:
        data, _ = get(MLIT_URL, timeout=60, max_age=365 * 86400)
    out = {}
    for name, rows in xlsx_sheets(data):
        if "面積" not in (name or ""):
            continue
        head = next((r for r in rows if r and any(str(x or "").startswith("資材") for x in r)), None)
        if head is None:
            continue
        cols = {}
        for j, h in enumerate(head):
            m = re.search(r"\((W|SRC|RC|S)\)", str(h or ""))   # 木造(W) / 鉄骨鉄筋ｺﾝｸﾘｰﾄ造(SRC) / 鉄筋ｺﾝｸﾘｰﾄ造(RC) / 鉄骨造(S)
            if m:
                cols[m.group(1)] = j
        for r in rows:
            item = str(r[1] if len(r) > 1 else "" or "").strip()
            if item in MLIT_ITEMS:
                for st, j in cols.items():
                    try:
                        out.setdefault(st, {})[item] = (float(r[j]), str(r[2]))
                    except (TypeError, ValueError, IndexError):
                        pass
    if not out:
        raise SourceError("建設資材・労働力需要実態調査の面積原単位の表を読めなかった（形式が変わった可能性）")
    _mlit = out
    return out


def load_meti(data: bytes | None = None) -> dict:
    """{row label: (GJ/m2, standard error)} from sheet ３－B (熱量単位表)."""
    if data is None:
        data, _ = get(METI_URL, timeout=60, max_age=365 * 86400)
    out = {}
    for name, rows in xlsx_sheets(data):
        if "B" not in (name or ""):
            continue
        for r in rows:
            if len(r) < 11:
                continue
            label = str(r[2] or r[1] or "").strip()
            for key, _ in METI_ROWS.values():
                if key in label and key not in out:
                    try:
                        out[key] = (float(r[9]), float(r[10]))
                    except (TypeError, ValueError):
                        pass
    return out


def _coverage_note(mat: str, method: str = "rasmi") -> str:
    """The coverage of the 5–95 % range measured by validate.py for this material (Japanese buildings), if any."""
    try:
        v = json.loads(VALIDATION.read_text(encoding="utf-8"))["japan"]
    except Exception:
        return "（この範囲の当たり率はまだ検証していない：仮の範囲）"
    h = (v.get("holdout") or {}).get(mat) or {}
    r = (v.get("rasmi_in_sample") or {}).get(mat) or {}
    if method == "mlit":
        return "（この組み合わせの範囲の当たり率は検証していない：仮の範囲）"
    if not h.get("n"):
        return "（この材料は検証データが無い：仮の範囲）"
    return ("（検証：日本の建物 %d 件の取り置き検証で 5〜95%% 範囲の当たり率 %.0f%%、誤差の中央値 %.0f%%。"
            "RASMI の範囲そのものでは %s（同じデータを含むので甘い）。校正済みとは言えない：仮の範囲）"
            % (h["n"], 100 * (h.get("coverage_p5_p95") or 0), 100 * h["median_ape"],
               ("%.0f%%" % (100 * r["coverage_p5_p95"])) if r.get("coverage_p5_p95") is not None else "—"))


def _other_steel(fid: str) -> str:
    return "m_steel" if fid == "m_rebar" else "m_rebar"


def _other_steel_has_value(values: dict, fid: str) -> bool:
    """An all-steel estimate (rebar + structural steel together) must not sit next to a value in the other steel field."""
    return competes(values.get(_other_steel(fid)))


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
    try:
        M = load_mlit().get(structure, {})
    except SourceError as e:
        M = {}
        msgs.append("建設資材・労働力需要実態調査を取得できなかった：%s" % e)
    for item, (fid0, unit, rmat) in MLIT_ITEMS.items():
        if item not in M:
            continue
        fid = fid0 or ("m_steel" if structure in ("S", "SRC") else "m_rebar")
        if only and fid != only:
            continue
        if fid0 is None and _other_steel_has_value(values, fid):
            msgs.append("「%s」に値があるので、鉄の全量（鉄筋＋鉄骨）の統計（国交省）は候補にしない（二重計上を防ぐ）"
                        % FL.FIELDS[_other_steel(fid)]["label"])
            continue
        cur = values.get(fid)
        if cur and cur.state in ("confirmed", "from_drawing"):
            continue
        if fid == "m_concrete":
            fdn = values.get("m_concrete_fdn")
            if competes(fdn):
                msgs.append("基礎のコンクリートが別に入っているので、全体量の統計（国交省）は候補にしない（二重計上を防ぐ）")
                continue
        per10, u = M[item]
        q = per10 * area / 10.0
        rr = R.get((rmat, fn, st, "OECD_JPN"))
        lo = hi = None
        if rr and rr["p_50"] > 0:
            lo, hi = q * rr["p_5"] / rr["p_50"], q * rr["p_95"] / rr["p_50"]
        notes = ["全国の平均（構造別・用途は区別しない）。資材には加工品に含まれるものを含む（調査の注 1）"]
        if item == "鋼材":
            notes.append("鋼材は鉄筋と鉄骨を分けていない。%s では全量を「%s」とした（仮定）" % (structure, FL.FIELDS[fid]["label"]))
        if fid == "m_concrete":
            notes.append("基礎・杭を含む建物全体の量。採用したら基礎の欄には別の値を入れない")
        if gfa_note:
            notes.append(gfa_note)
        unc = (Uncertainty("interval", round(lo, 3), round(hi, 3), 0.9, False,
                           "国交省の平均に RASMI（%s・%s・日本）の 5〜95%% の比（%.2f〜%.2f）を当てた仮の範囲%s"
                           % (fn, st, rr["p_5"] / rr["p_50"], rr["p_95"] / rr["p_50"], _coverage_note(rmat, "mlit")))
               if lo is not None else Uncertainty("interval", round(q * 0.5, 3), round(q * 1.5, 3), 0.9, False,
                                                  "散らばりの資料が無いので ±50% を仮に置いた（根拠なし・仮の範囲）"))
        out.append(Value(fid, "statistical", round(q, 3), unit, method="mlit_area_unit_x_gfa", source_id=MLIT_ID,
                         depends={"b_gfa": area, "b_structure": structure},          # MLIT: by structure, all uses
                         scope="whole_building" if fid == "m_concrete" else ("all_steel" if fid0 is None else ""),
                         source_detail="%s（%s）：%s %.4f %s / 延べ床 10 m2 × %.1f m2" % (MLIT_VERSION, structure, item, per10, u, area),
                         retrieved_at=today, factor_version=MLIT_VERSION, permission="政府標準利用規約2.0（e-Stat）",
                         uncertainty=unc, note="；".join(notes)))
    for mat in ("concrete", "steel", "wood", "glass", "aluminum", "brick", "plastics", "copper"):
        rec = R.get((mat, fn, st, "OECD_JPN"))
        if mat == "copper":
            if not only:
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
        if mat == "steel" and _other_steel_has_value(values, fid):
            msgs.append("「%s」に値があるので、鉄の全量（鉄筋＋鉄骨）の統計（RASMI）は候補にしない（二重計上を防ぐ）"
                        % FL.FIELDS[_other_steel(fid)]["label"])
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
            if competes(fdn):
                msgs.append("基礎のコンクリートが別に入っているので、基礎を含む統計の全体量は候補にしない（二重計上を防ぐ）")
                continue
            notes.append("基礎・杭を含む建物全体の量。採用したら基礎の欄には別の値を入れない（入れると基礎の行は作らず、二重計上を防ぐ）")
        k = 1000.0   # kg -> t
        v = Value(fid, "statistical", round(rec["p_50"] * area / k, 3), "t", method="rasmi_mi_x_gfa", source_id=RASMI_ID,
                  depends={"b_gfa": area, "b_structure": structure,
                           "b_use_group": "residential" if use.value == "residential" else "non_residential"},
                  scope="whole_building" if mat == "concrete" else ("all_steel" if mat == "steel" else ""),
                  source_detail="%s / %s / %s / OECD_JPN：中央値 %.1f kg/m2（元データ %d 件、補った後 %d 件、拡張 %d 回）"
                                % (mat, fn, st, rec["p_50"], rec["raw"], rec["n"], rec["iterations"]),
                  retrieved_at=today, factor_version=RASMI_VERSION, permission="CC-BY-4.0",
                  uncertainty=Uncertainty("interval", round(rec["p_5"] * area / k, 3), round(rec["p_95"] * area / k, 3), 0.9, False,
                                          "RASMI の 5〜95 パーセンタイル × 延床面積 %.1f m2" % area + _coverage_note(mat)),
                  note="；".join(notes + [gfa_note] if gfa_note else notes))
        out.append(v)
    if any(v.method == "rasmi_mi_x_gfa" for v in out):        # the attribution goes with a RASMI candidate only
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
            if field and not p and field not in ESTIMATED_FIELDS:
                msgs.insert(0, "「%s」の統計の出典はつないでいない%s" % (
                    FL.FIELDS[field]["label"],
                    "（基礎のコンクリートは、上部構造の欄の建物全体の推定に含まれる）" if field == "m_concrete_fdn" else
                    "（資料か仮定で入れる）"))
            elif field and not p and not m:
                msgs.append("「%s」の統計の候補は作らなかった（条件が合わない）" % FL.FIELDS[field]["label"])
    elif target_screen == "basic":
        msgs.append("基本情報の候補は「住所から調べる」（国土地理院・PLATEAU）で作る。延床面積は PLATEAU の屋根面積×階数の仮定値になる。")
    elif target_screen == "equipment":
        msgs.append("設備の台数・質量の統計は、権利を確認できた出典がまだ無いので概算しない（仮の係数を作らない）。"
                    "メーカーの仕様書（質量）や設計図の機器表から入れる。台数が分からないときは「あとで確認」にする。")
    elif target_screen == "operation":
        msgs.append("運用の入力は、請求書・検針の実績が一番よい。次が設計の計算、最後が統計。")
        use, gfa = values.get("b_use"), values.get("b_gfa")
        row = METI_ROWS.get(use.value) if use and use.state in HAS_VALUE else None
        if row and gfa and gfa.state in HAS_VALUE:
            try:
                meti = load_meti()
            except SourceError as e:
                meti = {}
                msgs.append("エネルギー消費統計を取得できなかった：%s" % e)
            if row[0] in meti:
                gj, se = meti[row[0]]
                msgs.append("参考（入力の候補にはしない）：経済産業省「エネルギー消費統計調査」令和6年度 第3表B の「%s」は 延床面積あたり %.3f GJ/m2"
                            "（標準誤差 %.3f）。この建物（%.0f m2）では年 %.0f GJ 程度。%s電力とガスなどの内訳が無いので、エンジンの入力（電力 kWh・ガス m3）には"
                            "分けられない。事業所の平均であって、建物の用途の平均ではない。"
                            % (row[0], gj, se, float(gfa.value), gj * float(gfa.value), (row[1] + "。") if row[1] else ""))
        elif use and use.state in HAS_VALUE and use.value == "residential":
            msgs.append("住宅（家庭部門）のエネルギー統計はまだつないでいない。")
        msgs.append("上水・下水・一般廃棄物の統計は、権利を確認できた出典がまだ無いので概算しない。")
    else:
        msgs.append("どの画面の概算かが分からない")
    return {"proposals": proposals, "message": msgs[0] if msgs and not proposals else "", "messages": msgs}


def registry_markdown() -> str:
    """docs/sources_rights.md: the rights ledger of every data source, from sources/registry.json."""
    R = registry()
    st = {"connected": "接続済み（自動取得）", "reference_only": "参考値だけ", "used_for_validation": "精度検証だけ",
          "link_and_manual_note": "リンクと手書きの記録だけ", "manual_upload_only": "利用者が読み込むだけ", "not_used": "使わない",
          "demo_only": "デモだけ"}
    lines = ["# データ源の権利台帳", "", "生成：`python3 -B -m wlcstudio sources --md docs/sources_rights.md`（元は `wlcstudio/sources/registry.json`、確認日 %s）。"
             "利用条件は変わるので、公開・商用利用の前に原文で確かめ直す。" % R["checked_at"], "",
             "| データ源 | 提供 | 使い方 | 自動取得 | 権利・条件 | 再配布 | 限界 |", "|---|---|---|---|---|---|---|"]
    for x in R["sources"]:
        lines.append("| %s（`%s`） | %s | %s | %s | %s | %s | %s |" % (
            x["name"], x["id"], x.get("provider", ""), st.get(x.get("status"), x.get("status", "")), "する" if x.get("automated") else "しない",
            x.get("licence", "—"), x.get("redistribution", "—"), x.get("limits", "—")))
    lines += ["", "## 守っていること", "",
              "- J-CAT の係数・数式・マクロ・有償データ・名称は使わない（アプリ名は WLC Studio。計算の核は独立の概念モデル）。",
              "- 国土地理院・PLATEAU・e-Stat のデータは出典を示し、加工したことを書く（画面の「このアプリについて」）。",
              "- KuniJiban は自動で取得しない（トップページへのリンクと、利用者が調べた結果の書き留めだけ）。ボーリングは近くの地点の記録であって敷地の地盤ではない。",
              "- メーカーの BIM・製品データは自動で集めず、原本を保存しない。性能値は製造時の CO2e ではなく、EPD が無ければ製品の CO2e を断定しない。",
              "- 統計の値は、出典・版・単位・範囲・許諾を候補に付ける。出典の無い係数は作らない（設備の台数・水の量は概算しない）。",
              ""]
    return "\n".join(lines)
