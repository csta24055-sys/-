#!/usr/bin/env python3
"""Axis A / Axis B ranking and research priority order (protocol P4-P6, version 1.1).

Since directive amendment 01 the rankings no longer limit the research scope:
EVERY evaluation unit is a research target. The two axes only decide the order
in which units are taken up. The former top-30% sets are kept as reference
information (`reference_top30`).

Inputs
  01_LEDGER/units.json                     classification ledger
  01_LEDGER/sheet_families.json            sheet-family metadata (proxy a7)
  02_RANKING/axis_a_measurements.json      measured time / operations / memory per unit
  02_RANKING/axis_b_judges/*.json          independent judge score sheets

Outputs
  02_RANKING/axis_a.json, axis_b.json, research_priority.json

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
B_UNIFICATION = ["b2", "b3", "b4", "b8"]  # criteria about merging different formulas
PRIORITY_WEIGHTS = {"axis_b": 0.35, "unification": 0.30, "axis_a": 0.35}
N_WAVES = 3
SHARE = 0.30  # reference only; does not limit the research scope
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


def _positions(scores: dict) -> dict:
    """1-based rank position per unit (None scores go last)."""
    order = sorted(scores, key=lambda uid: (-(scores[uid] if scores[uid] is not None else -1), uid))
    return {uid: pos for pos, uid in enumerate(order, 1)}


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
            "reference_top30_main": uid in selected,
            "reference_top30_variants": [name for name, v in variants.items() if uid in v["selected"]],
        })
    return {
        "schema_version": "1.0",
        "axis": "A",
        "definition": "Computational load and complexity. Measured on the independent reference calculation with synthetic data; the original workbooks were not executed.",
        "use": "Decides the order of work only. All units are research targets (directive amendment 01).",
        "unit_count": len(ids),
        "weights": A_WEIGHTS,
        "scores": {uid: main[uid] for uid in ids},
        "reference_top30": {
            "note": "Former selection rule, kept for reference. It does not limit the research scope.",
            "share": SHARE,
            "k": k,
            "cutoff_score": cutoff,
            "main": selected,
            "sensitivity_only": sensitivity_only,
            "variants": {name: {"weights": v["weights"], "cutoff": v["cutoff"], "members": v["selected"]} for name, v in variants.items()},
        },
        "rank_by_variant": {name: _positions(v["scores"]) for name, v in variants.items()},
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
            "unification_subscore": sum(med[c] for c in B_UNIFICATION),
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
            "reference_top30": uid in selected,
        })
    return {
        "schema_version": "1.0",
        "axis": "B",
        "definition": "Room for simplification, approximation and unification. Eight criteria scored 0-3 by three independent judges; the score is the sum of per-criterion medians (0-24).",
        "use": "Decides the order of work only. All units are research targets (directive amendment 01).",
        "unit_count": len(ids),
        "judges": sorted(sheets),
        "scores": scores,
        "unification_subscores": {uid: detail[uid]["unification_subscore"] for uid in ids},
        "unification_criteria": B_UNIFICATION,
        "reference_top30": {
            "note": "Former selection rule, kept for reference. It does not limit the research scope.",
            "share": SHARE,
            "k": k,
            "cutoff_score": cutoff,
            "members": selected,
        },
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
    ids = [u["id"] for u in units]
    arank = {r["id"]: r for r in a["ranking"]}
    brank = {r["id"]: r for r in b["ranking"]}
    pa = pct_rank(a["scores"])
    pb = pct_rank(b["scores"])
    pu = pct_rank(b["unification_subscores"])
    priority = {}
    for uid in ids:
        parts = {"axis_b": pb[uid], "unification": pu[uid], "axis_a": pa[uid]}
        num = sum(PRIORITY_WEIGHTS[key] * val for key, val in parts.items() if val is not None)
        den = sum(PRIORITY_WEIGHTS[key] for key, val in parts.items() if val is not None)
        priority[uid] = num / den if den else 0.0
    order = sorted(ids, key=lambda uid: (-priority[uid], uid))
    wave_size = math.ceil(len(order) / N_WAVES)
    rows = []
    for pos, uid in enumerate(order, 1):
        rows.append({
            "order": pos,
            "wave": min(N_WAVES, (pos - 1) // wave_size + 1),
            "id": uid,
            "name": names[uid],
            "stage": stages[uid],
            "priority_score": round(priority[uid], 4),
            "a_rank": arank[uid]["rank"],
            "a_score": arank[uid]["a_score"],
            "a_measured": arank[uid]["measured"],
            "b_rank": brank[uid]["rank"],
            "b_score": brank[uid]["b_score"],
            "b_unification_subscore": brank[uid]["unification_subscore"],
            "b_disputed": brank[uid]["disputed"],
            "reference_top30": [tag for tag, hit in (
                ("A", arank[uid]["reference_top30_main"]),
                ("A_SENSITIVITY", bool(arank[uid]["reference_top30_variants"]) and not arank[uid]["reference_top30_main"]),
                ("B", brank[uid]["reference_top30"]),
            ) if hit],
        })
    plan = {
        "schema_version": "1.1",
        "scope_statement": "Every evaluation unit established for the independent conceptual model is a research target (directive amendment 01). The order below only says which units are taken up first. It is not a ranking of the original workbooks, whose formula bodies were not inspected.",
        "unit_count": len(ids),
        "research_target_count": len(ids),
        "priority_formula": "0.35 * pct(axis B) + 0.30 * pct(unification criteria b2+b3+b4+b8) + 0.35 * pct(axis A)",
        "priority_weights": PRIORITY_WEIGHTS,
        "waves": {str(w): [r["id"] for r in rows if r["wave"] == w] for w in range(1, N_WAVES + 1)},
        "reference_top30_counts": {
            "k_per_axis": a["reference_top30"]["k"],
            "A": len(a["reference_top30"]["main"]),
            "A_sensitivity_only": len(a["reference_top30"]["sensitivity_only"]),
            "B": len(b["reference_top30"]["members"]),
            "union": len(set(a["reference_top30"]["main"]) | set(a["reference_top30"]["sensitivity_only"]) | set(b["reference_top30"]["members"])),
        },
        "units": rows,
    }
    for name, obj in (("axis_a.json", a), ("axis_b.json", b), ("research_priority.json", plan)):
        (RANK / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    stale = RANK / "selected_targets.json"
    if stale.exists():
        stale.unlink()
    print(f"units={len(ids)} research_targets={len(ids)} waves={[len(v) for v in plan['waves'].values()]} "
          f"reference_top30={plan['reference_top30_counts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
