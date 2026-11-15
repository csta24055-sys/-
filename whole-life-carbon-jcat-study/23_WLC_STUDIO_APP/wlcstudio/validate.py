"""Accuracy check of the material estimators on real, openly licensed building data (not on the fictional demo).

Test data: the Material Intensity Research Database (Heeren & Fishman, Scientific Data 2019; v1.2, Zenodo record 10131536,
CC BY 4.0; the GitHub file used here is byte-identical to the Zenodo release). Each row is one building (or building type)
with kg of material per m2 of floor area, taken from a cited publication.

What is measured (definitions fixed before looking at the numbers):
  * material quantity error: APE = |predicted − actual| / actual, per building and material, for concrete, steel, wood,
    and for their sum (total mass);
  * a proxy of the A1-A3 error: the same materials weighted by the FICTIONAL factor set (not a real emission error);
  * share of buildings with APE ≤ 10 % (target ≥ 90 %, stretch 95 %) and ≤ 5 %, median, p90, p95, bias (median signed error);
  * coverage of the predicted 5–95 % range (should be about 90 % if the range were calibrated).

Methods:
  holdout  median of the other buildings with the same function and structure, never using any building from the same
           publication as the tested one (group hold-out against near-duplicates); region widened Japan → OECD → world
           only when fewer than 5 remain; its range is the 5–95 % of that pool.
  rasmi    the RASMI p50 / p5–p95 actually shown in the app. RASMI was built from this same database, so this is IN-SAMPLE
           (leakage) and is reported only to show how optimistic an in-sample check is.
  mlit     the national mean of 国交省「建設資材・労働力需要実態調査」 (steel only: t per 10 m2 → kg/m2; concrete and wood are in
           m3 and are not converted, because no density is assumed). External to the test data.
The fictional demo is never part of this check.
"""
from __future__ import annotations

import csv
import io
import json
import math
import statistics
import sys
from pathlib import Path

from . import estimate
from .sources.net import get

MIRDB_URL = "https://raw.githubusercontent.com/nheeren/material_intensity_db/master/data/buildings.csv"
MIRDB_ID = "mirdb_v1_2"
STRUCT = {"C": "RC", "S": "S", "T": "W"}          # MIRDB top-level structure -> app structure (M masonry, U unknown: not tested)
MATS = ("concrete", "steel", "wood")
MIN_POOL = 5


def _f(x):
    try:
        v = float(x)
        return v if math.isfinite(v) and v >= 0 else None
    except (TypeError, ValueError):
        return None


def load_mirdb(data: bytes | None = None) -> list[dict]:
    if data is None:
        data, _ = get(MIRDB_URL, timeout=60, max_age=365 * 86400)
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8", errors="replace"))))
    out = []
    for r in rows:
        st = STRUCT.get(r.get("structure"))
        fn = r.get("function")
        if st is None or fn not in ("NR", "RM", "RS"):
            continue
        mi = {m: _f(r.get(m)) for m in MATS}
        out.append({"id": r["id"], "country": r.get("country", "").strip(), "oecd": r.get("R5.2") == "R5.2OECD",
                    "function": fn, "structure": st, "group": (r.get("authors", "")[:60], r.get("publication_year", "")),
                    "mi": mi})
    return out


def _q(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def _metrics(pairs: list[tuple[float, float, float | None, float | None]]) -> dict:
    """pairs: (predicted, actual, low, high) with actual > 0."""
    ape = [abs(p - a) / a for p, a, _, _ in pairs]
    sgn = [(p - a) / a for p, a, _, _ in pairs]
    cov = [lo <= a <= hi for p, a, lo, hi in pairs if lo is not None and hi is not None]
    n = len(ape)
    if not n:
        return {"n": 0}
    return {"n": n, "share_ape_le_10": sum(e <= 0.10 for e in ape) / n, "share_ape_le_5": sum(e <= 0.05 for e in ape) / n,
            "median_ape": statistics.median(ape), "p90_ape": _q(ape, 0.90), "p95_ape": _q(ape, 0.95),
            "bias_median_signed": statistics.median(sgn), "coverage_p5_p95": (sum(cov) / len(cov)) if cov else None,
            "n_with_range": len(cov)}


def holdout_predict(test: dict, data: list[dict], mat: str) -> tuple[float, float, float, str] | None:
    def pool(cond):
        return [d["mi"][mat] for d in data if d["group"] != test["group"] and d["function"] == test["function"]
                and d["structure"] == test["structure"] and d["mi"][mat] is not None and cond(d)]
    for level, cond in (("日本", lambda d: d["country"] == "Japan"), ("OECD", lambda d: d["oecd"]), ("世界", lambda d: True)):
        xs = pool(cond)
        if len(xs) >= MIN_POOL:
            return statistics.median(xs), _q(xs, 0.05), _q(xs, 0.95), level
    return None


def run(mirdb: list[dict], ranges: dict, mlit: dict, factor_weights: dict[str, float], countries=("Japan",)) -> dict:
    tests = [d for d in mirdb if d["country"] in countries] if countries else mirdb
    res = {"holdout": {}, "rasmi_in_sample": {}, "mlit_external": {}}
    by_level, per_building = {}, []
    fn_of = {"RC": "C", "S": "S", "W": "T"}
    for mat in MATS:
        hp, rp, mp = [], [], []
        for t in tests:
            a = t["mi"][mat]
            if a is None or a <= 0:
                continue
            h = holdout_predict(t, mirdb, mat)
            if h:
                hp.append((h[0], a, h[1], h[2]))
                by_level.setdefault(h[3], []).append((h[0], a, h[1], h[2]))
            r = ranges.get((mat, t["function"], fn_of[t["structure"]], "OECD_JPN"))
            if r:
                rp.append((r["p_50"], a, r["p_5"], r["p_95"]))
            if mat == "steel" and t["structure"] in mlit and "鋼材" in mlit[t["structure"]]:
                mp.append((mlit[t["structure"]]["鋼材"][0] * 100.0, a, None, None))     # t / 10 m2 -> kg / m2
        res["holdout"][mat] = _metrics(hp)
        res["rasmi_in_sample"][mat] = _metrics(rp)
        if mp:
            res["mlit_external"][mat] = _metrics(mp)
    # total mass and the fictional-factor proxy, buildings with all three materials
    tot, prox = [], []
    for t in tests:
        if any(t["mi"][m] is None for m in MATS) or sum(t["mi"][m] for m in MATS) <= 0:
            continue
        hs = [holdout_predict(t, mirdb, m) for m in MATS]
        if any(h is None for h in hs):
            continue
        a = sum(t["mi"][m] for m in MATS)
        p = sum(h[0] for h in hs)
        tot.append((p, a, sum(h[1] for h in hs), sum(h[2] for h in hs)))
        aw = sum(t["mi"][m] * factor_weights[m] for m in MATS)
        pw = sum(h[0] * factor_weights[m] for h, m in zip(hs, MATS))
        if aw > 0:
            prox.append((pw, aw, None, None))
        per_building.append({"id": t["id"], "structure": t["structure"], "function": t["function"],
                             "actual_total_kg_m2": round(a, 1), "predicted_total_kg_m2": round(p, 1),
                             "ape_total": round(abs(p - a) / a, 3)})
    res["holdout"]["total_mass"] = _metrics(tot)
    res["holdout"]["a13_proxy_fictional_factors"] = _metrics(prox)
    res["holdout_by_pool_level"] = {k: _metrics(v) for k, v in by_level.items()}
    by_struct = {}
    for t in tests:
        for mat in MATS:
            a = t["mi"][mat]
            h = holdout_predict(t, mirdb, mat) if a else None
            if h and a > 0:
                by_struct.setdefault("%s/%s" % (t["structure"], mat), []).append((h[0], a, h[1], h[2]))
    res["holdout_by_structure_material"] = {k: _metrics(v) for k, v in sorted(by_struct.items())}
    res["n_test_buildings"] = len(tests)
    res["per_building_total"] = per_building
    return res


def _pct(x):
    return "—" if x is None else "%.0f%%" % (100 * x)


def report_md(jp: dict, oecd: dict, meta: dict) -> str:
    def table(block: dict, title: str) -> str:
        lines = ["| %s | n | APE≦10%% | APE≦5%% | 中央値 | p90 | p95 | 偏り（中央値） | 5〜95%% の当たり率 |" % title,
                 "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for k, m in block.items():
            if not m.get("n"):
                continue
            lines.append("| %s | %d | %s | %s | %s | %s | %s | %+.0f%% | %s |" % (
                k, m["n"], _pct(m["share_ape_le_10"]), _pct(m["share_ape_le_5"]), _pct(m["median_ape"]), _pct(m["p90_ape"]),
                _pct(m["p95_ape"]), 100 * m["bias_median_signed"], _pct(m.get("coverage_p5_p95"))))
        return "\n".join(lines)
    met = jp["holdout"]["total_mass"].get("share_ape_le_10")
    verdict = ("**目標（APE≦10% の建物が 90% 以上）は達成していない。**" if (met is None or met < 0.9)
               else "目標（APE≦10% の建物が 90% 以上）を満たした。")
    return "\n".join([
        "# 精度の検証（材料の統計概算）",
        "",
        "生成：`python3 -B -m wlcstudio validate`（%s）。架空デモとは別の、公開の実データによる検証。" % meta["generated"],
        "",
        "## 結論",
        "",
        verdict + " 延床面積と構造・用途だけからの材料の概算は、1 棟ごとには大きく外れる。"
        "延床面積あたりの量は、同じ構造・用途の中でも数倍ばらつくためで、住所検索や延床面積だけで「90〜95% の精度」を言うことはできない。",
        "",
        "- 図面・数量表・BIM から読んだ数量（状態「図面から計算」）がある材料は、この概算を使わない。",
        "- 統計の候補の範囲（5〜95%）は「仮の範囲」と表示する（下の当たり率を参照）。",
        "- **ライフサイクルの排出量（LCA）の精度は検証できていない。** 登録されている原単位が架空なので、同じ範囲・同じ原単位・同じ期間での比較ができない。"
        "下の「A1-A3 の代理」は、架空の原単位で材料の誤差に重みを付けただけのもので、実際の排出量の誤差ではない。",
        "",
        "## 検証の設計（数字を見る前に決めたこと）",
        "",
        "- 対象：Material Intensity Research Database v1.2（Heeren & Fishman 2019, Zenodo 10131536, CC BY 4.0）のうち、"
        "構造が RC（C）・S・木造（T）、用途が非住宅（NR）・共同住宅（RM）・戸建て（RS）の建物。日本の建物 %d 件（参考に OECD 全体 %d 件）。"
        % (jp["n_test_buildings"], oecd["n_test_buildings"]),
        "- 取り置き（holdout）：調べる建物と同じ文献の建物は、予測の材料に一切使わない（同じ調査の似た建物による水増しを防ぐ）。"
        "同じ構造・用途の他の建物の中央値を予測、5〜95% を範囲とする。日本だけで 5 件に満たないときは OECD、世界へ広げる。",
        "- RASMI（アプリで使う範囲）は、この同じデータベースから作られているので、その検証は**データの重複（リーク）を含む参考値**。",
        "- 国交省の面積原単位は全国平均で、外部の資料。鋼材だけ比べた（生コン・木材は m3 で、密度を仮定しないので比べない）。",
        "",
        "## 日本の建物（主な結果）",
        "",
        table(jp["holdout"], "取り置き：材料"),
        "",
        table(jp["rasmi_in_sample"], "RASMI（リークあり）"),
        "",
        table(jp["mlit_external"], "国交省（外部）"),
        "",
        "予測の材料にした範囲（日本 → OECD → 世界）ごと：",
        "",
        table(jp["holdout_by_pool_level"], "範囲"),
        "",
        "構造・材料ごと：",
        "",
        table(jp["holdout_by_structure_material"], "構造/材料"),
        "",
        "## 参考：OECD の建物（日本以外を含む）",
        "",
        table(oecd["holdout"], "取り置き：材料"),
        "",
        "## 限界",
        "",
        "- 日本の建物は %d 件だけで、木造の伝統的な住宅と一つの文献に偏っている。非住宅の RC はほとんど無い。" % jp["n_test_buildings"],
        "- データベースの値は文献ごとに範囲（基礎・仕上げ・設備を含むか）と面積の定義（延床・床面積）が違う。",
        "- 鉄は鉄筋と鉄骨を分けていない（アプリでは構造で振り分けている＝仮定）。",
        "- 実在の建物の WLC の精度の検証には、権利を確認した実際の原単位セットと、同じ範囲で算定した実例（正解）が要る。",
        "",
        "出典：Heeren N., Fishman T. A database seed for a community-driven material intensity research platform. Scientific Data 6, 23 (2019)；"
        "Fishman T. et al. RASMI. Scientific Data 11, 418 (2024)；国土交通省「建設資材・労働力需要実態調査【建築部門】」令和6年度（e-Stat）をもとに作成。",
        ""])


def main(out_dir: str) -> int:
    import datetime as _dt
    sys.dont_write_bytecode = True
    mirdb = load_mirdb()
    ranges = estimate.load_ranges()
    mlit = estimate.load_mlit()
    from .engine import FICTIONAL_REFSET
    F = json.loads(Path(FICTIONAL_REFSET).read_text(encoding="utf-8"))["data"]["factors"]
    w = {"concrete": F["F-MATKG-CONCRETE-01"]["value"], "steel": F["F-MAT-REBAR-01"]["value"], "wood": F["F-MATKG-TIMBER-01"]["value"]}
    jp = run(mirdb, ranges, mlit, w, ("Japan",))
    oecd = run(mirdb, ranges, mlit, w, tuple(sorted({d["country"] for d in mirdb if d["oecd"]})))
    meta = {"generated": _dt.date.today().isoformat(), "test_data": MIRDB_ID, "min_pool": MIN_POOL,
            "fictional_weights_for_proxy": w, "target": "share of buildings with APE ≤ 10 % ≥ 0.90 (stretch 0.95)"}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    payload = {"meta": meta, "japan": {k: v for k, v in jp.items() if k != "per_building_total"},
               "oecd": {k: v for k, v in oecd.items() if k != "per_building_total"},
               "holdout": jp["holdout"]["total_mass"], "rasmi_in_sample": jp["rasmi_in_sample"]["concrete"]}
    (out / "validation_results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "accuracy_report.md").write_text(report_md(jp, oecd, meta), encoding="utf-8")
    print(json.dumps({"japan_total_mass": jp["holdout"]["total_mass"], "oecd_total_mass": oecd["holdout"]["total_mass"]},
                     ensure_ascii=False, indent=1))
    return 0
