#!/usr/bin/env python3
"""Axis A / Axis B ranking and top-30% selection (protocol P4-P6).

Inputs
  01_LEDGER/units.json                     classification ledger
  01_LEDGER/sheet_families.json            sheet-family metadata (proxy a7)
  02_RANKING/axis_a_measurements.json      measured time / operations / memory per unit
  02_RANKING/axis_b_judges/*.json          independent judge score sheets

Outputs
  02_RANKING/axis_a.json, axis_b.json, selected_targets.json

Research tooling only. Standard library only. No product code.
"""
from __future__ import annotations

import json
import math
import re
import statistics
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[2]
LEDGER = STUDY / "01_LEDGER"
RANK = STUDY / "02_RANKING"

A_WEIGHTS = {"a1": 0.35, "a2": 0.15, "a3": 0.10, "a4": 0.10, "a5": 0.10, "a6": 0.10, "a7": 0.10}
A_VARIANTS = {
    "time_only": {"a1": 1.0},
    "equal_weights": {k: 1.0 for k in A_WEIGHTS},
    "no_proxy": {k: v for k, v in A_WEIGHTS.items() if k != "a7"},
}
B_CRITERIA = ["b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8"]
SHARE = 0.30
OPERATOR_RE = re.compile(r"sum|max|min|count|ceil|floor|\*\*|[-+*/^]")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def pct_rank(values: dict) -> dict:
    """Average-rank percentile in (0, 1]. None stays None."""
    items = sorted(((k, v) for k, v in values.items() if v is not None), key=lambda kv: kv[1])
    n = len(items)
    out = {k: None for k in values}
    i = 0
    while i < n:
        j = i
        while j + 1 < n and items[j + 1][1] == items[i][1]:
            j += 1
        avg = (i + j) / 2 + 1
        for t in range(i, j + 1):
            out[items[t][0]] = avg / n
        i = j + 1
    return out


def composite(ranks: dict, weights: dict, uid: str):
    """Weighted mean of the available percentile ranks (weights renormalised)."""
    num = den = 0.0
    for key, w in weights.items():
        r = ranks[key].get(uid)
        if r is None:
            continue
        num += w * r
        den += w
    return (num / den) if den else None


def top_share(scores: dict, share: float = SHARE):
    """Return (k, cutoff, selected ids). Ties at the cutoff are all included."""
    valid = {k: v for k, v in scores.items() if v is not None}
    n_all = len(scores)
    k = math.ceil(share * n_all)
    ordered = sorted(valid.items(), key=lambda kv: (-kv[1], kv[0]))
    if not ordered:
        return k, None, []
    cutoff = ordered[min(k, len(ordered)) - 1][1]
    return k, cutoff, [uid for uid, s in ordered if s >= cutoff - 1e-12]


def static_metrics(units: list, families: dict) -> dict:
    link_count: dict = {}
    for u in units:
        for fam in u.get("sheet_family_links") or []:
            link_count[fam] = link_count.get(fam, 0) + 1
    out = {}
    for u in units:
        loops = u.get("loop_dims") or []
        branches = u.get("branches") or []
        form = u.get("canonical_form") or ""
        n_ops = len(OPERATOR_RE.findall(form))
        proxy = 0.0
        for fam in u.get("sheet_family_links") or []:
            if fam in families:
                proxy += families[fam] / link_count[fam]
        out[u["id"]] = {
            "a4": (u.get("n_inputs") or len(u.get("inputs") or [])) + n_ops,
            "a5": len(branches) + len(loops) + max(0, len(loops) - 1),
            "a6": len(u.get("depends_on") or []) + len(u.get("feeds") or []),
            "a7": proxy,
            "n_inputs": u.get("n_inputs") or len(u.get("inputs") or []),
            "n_operators_in_canonical_form": n_ops,
        }
    return out


def rank_axis_a(units: list, families: dict, meas: dict) -> dict:
    ids = [u["id"] for u in units]
    stat = static_metrics(units, families)
    sizes = meas.get("size_classes", [])
    per_unit = meas.get("units", {})

    def measured_rank(field: str) -> dict:
        """Percentile rank per size class, then the median of those ranks."""
        per_size = []
        for size in sizes:
            vals = {}
            for uid in ids:
                rec = per_unit.get(uid) or {}
                val = (rec.get(field) or {}).get(size) if rec.get("measured") else None
                vals[uid] = val
            per_size.append(pct_rank(vals))
        out = {}
        for uid in ids:
            rs = [p[uid] for p in per_size if p[uid] is not None]
            out[uid] = statistics.median(rs) if rs else None
        return out

    ranks = {
        "a1": measured_rank("time_share"),
        "a2": measured_rank("operations"),
        "a3": measured_rank("peak_memory_bytes"),
    }
    for key in ("a4", "a5", "a6", "a7"):
        ranks[key] = pct_rank({uid: stat[uid][key] for uid in ids})

    main = {uid: composite(ranks, A_WEIGHTS, uid) for uid in ids}
    k, cutoff, selected = top_share(main)
    variants = {}
    for name, weights in A_VARIANTS.items():
        sc = {uid: composite(ranks, weights, uid) for uid in ids}
        vk, vcut, vsel = top_share(sc)
        variants[name] = {"weights": weights, "cutoff": vcut, "selected": vsel, "scores": sc}
    sensitivity_only = sorted({uid for v in variants.values() for uid in v["selected"]} - set(selected))

    order = sorted(ids, key=lambda uid: (-(main[uid] if main[uid] is not None else -1), uid))
    rows = []
    for pos, uid in enumerate(order, 1):
        rec = per_unit.get(uid) or {}
        rows.append({
            "rank": pos,
            "id": uid,
            "a_score": round(main[uid], 4) if main[uid] is not None else None,
            "measured": bool(rec.get("measured")),
            "not_measured_reason": rec.get("not_measured_reason"),
            "time_share": rec.get("time_share"),
            "time_ns": rec.get("time_ns"),
            "operations": rec.get("operations"),
            "peak_memory_bytes": rec.get("peak_memory_bytes"),
            "static": stat[uid],
            "percentile_ranks": {key: (round(ranks[key][uid], 4) if ranks[key][uid] is not None else None) for key in ranks},
            "in_top30_main": uid in selected,
            "in_top30_variants": [name for name, v in variants.items() if uid in v["selected"]],
        })
    return {
        "schema_version": "1.0",
        "axis": "A",
        "definition": "Computational load and complexity. Measured on the independent reference calculation with synthetic data; the original workbooks were not executed.",
        "unit_count": len(ids),
        "share": SHARE,
        "k": k,
        "weights": A_WEIGHTS,
        "cutoff_score": cutoff,
        "selected_main": selected,
        "selected_sensitivity_only": sensitivity_only,
        "variants": {name: {"weights": v["weights"], "cutoff": v["cutoff"], "selected": v["selected"]} for name, v in variants.items()},
        "measurement_source": meas.get("source"),
        "size_classes": sizes,
        "ranking": rows,
    }


def rank_axis_b(units: list, judge_files: list) -> dict:
    ids = [u["id"] for u in units]
    sheets = {}
    for path in judge_files:
        data = load(path)
        rows = data["scores"] if isinstance(data, dict) else data
        sheets[path.stem] = {r["id"]: r for r in rows}
    missing = {name: sorted(set(ids) - set(sheet)) for name, sheet in sheets.items()}
    missing = {k: v for k, v in missing.items() if v}
    if missing:
        raise SystemExit(f"judge sheets incomplete: {missing}")
    scores = {}
    detail = {}
    for uid in ids:
        med = {c: statistics.median(sheet[uid][c] for sheet in sheets.values()) for c in B_CRITERIA}
        totals = {name: sum(sheet[uid][c] for c in B_CRITERIA) for name, sheet in sheets.items()}
        scores[uid] = sum(med.values())
        detail[uid] = {
            "median_by_criterion": med,
            "judge_totals": totals,
            "judge_spread": max(totals.values()) - min(totals.values()),
            "rationales": {name: sheet[uid].get("rationale") for name, sheet in sheets.items()},
            "replacement_ideas": {name: sheet[uid].get("replacement_idea") for name, sheet in sheets.items()},
        }
    k, cutoff, selected = top_share(scores)
    order = sorted(ids, key=lambda uid: (-scores[uid], -statistics.mean(detail[uid]["judge_totals"].values()), uid))
    rows = []
    for pos, uid in enumerate(order, 1):
        d = detail[uid]
        rows.append({
            "rank": pos,
            "id": uid,
            "b_score": scores[uid],
            "disputed": d["judge_spread"] >= 6,
            **d,
            "in_top30": uid in selected,
        })
    return {
        "schema_version": "1.0",
        "axis": "B",
        "definition": "Room for simplification, approximation and unification. Eight criteria scored 0-3 by three independent judges; the score is the sum of per-criterion medians (0-24).",
        "unit_count": len(ids),
        "share": SHARE,
        "k": k,
        "cutoff_score": cutoff,
        "judges": sorted(sheets),
        "selected": selected,
        "disputed_units": [r["id"] for r in rows if r["disputed"]],
        "ranking": rows,
    }


def main() -> int:
    ledger = load(LEDGER / "units.json")
    units = ledger["units"]
    fam = {f["family_id"]: f["share_of_all_nodes"] for f in load(LEDGER / "sheet_families.json")["families"]}
    meas = load(RANK / "axis_a_measurements.json")
    judge_files = sorted((RANK / "axis_b_judges").glob("*.json"))
    if len(judge_files) < 3:
        raise SystemExit("need three independent judge sheets")
    a = rank_axis_a(units, fam, meas)
    b = rank_axis_b(units, judge_files)
    names = {u["id"]: u["name"] for u in units}
    stages = {u["id"]: u["stage"] for u in units}
    sel_a, sel_as, sel_b = set(a["selected_main"]), set(a["selected_sensitivity_only"]), set(b["selected"])
    arank = {r["id"]: r for r in a["ranking"]}
    brank = {r["id"]: r for r in b["ranking"]}
    targets = []
    for uid in [u["id"] for u in units]:
        basis = []
        if uid in sel_a:
            basis.append("A_TOP30")
        if uid in sel_as:
            basis.append("A_SENSITIVITY")
        if uid in sel_b:
            basis.append("B_TOP30")
        if not basis:
            continue
        targets.append({
            "id": uid,
            "name": names[uid],
            "stage": stages[uid],
            "selection_basis": basis,
            "a_rank": arank[uid]["rank"],
            "a_score": arank[uid]["a_score"],
            "a_measured": arank[uid]["measured"],
            "b_rank": brank[uid]["rank"],
            "b_score": brank[uid]["b_score"],
            "b_disputed": brank[uid]["disputed"],
        })
    selected = {
        "schema_version": "1.0",
        "scope_statement": "Top 30 percent of the evaluation units that could be established for the independent conceptual model. This is NOT the top 30 percent of the original workbooks, whose formula bodies were not inspected.",
        "unit_count": len(units),
        "k_per_axis": a["k"],
        "count_a_top30": len(sel_a),
        "count_a_sensitivity_only": len(sel_as),
        "count_b_top30": len(sel_b),
        "count_both_axes": len((sel_a | sel_as) & sel_b),
        "count_targets": len(targets),
        "targets": targets,
    }
    for name, obj in (("axis_a.json", a), ("axis_b.json", b), ("selected_targets.json", selected)):
        (RANK / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"units={len(units)} k={a['k']} A={len(sel_a)} A_sens_only={len(sel_as)} B={len(sel_b)} "
          f"both={selected['count_both_axes']} targets={len(targets)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
