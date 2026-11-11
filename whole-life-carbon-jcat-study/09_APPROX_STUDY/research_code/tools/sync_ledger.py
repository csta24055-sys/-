#!/usr/bin/env python3
"""Keep the unit ledger consistent with the reference calculation.

For every unit that has a reference function:
  reference_semantics  <- the function's docstring (the binding definition)
  depends_on           <- the dependencies declared in the registry
  feeds                <- inverse of depends_on (recomputed for all units)
and for every unit:
  sheet_family_links   <- inverse of related_units in sheet_family_coverage.json

Run:  cd research_code && python3 -m tools.sync_ledger
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from refcalc import registry

LEDGER = Path(__file__).resolve().parents[2] / "01_LEDGER" / "units.json"
COVERAGE = LEDGER.with_name("sheet_family_coverage.json")


def sync_families(units: list) -> None:
    """One source for the sheet-family correspondence: 01_LEDGER/sheet_family_coverage.json.

    A family whose calculation structure cannot be told from its name (status
    NOT_INSPECTED) is related to no unit. For the other families the related units are
    kept; a unit's ``sheet_family_links`` is the inverse of that list. (The first run
    also folds in links that only the unit ledger carried, so nothing inferred is lost.)
    """
    cov = json.loads(COVERAGE.read_text(encoding="utf-8"))
    order = [u["id"] for u in units]
    links: dict[str, list] = {uid: [] for uid in order}
    for fam in cov["families"]:
        fid = fam["family_id"]
        if fam["status"] == "NOT_INSPECTED":
            related = set()
            fam["status_label"] = "名称から対応を推定できない（原版の式は未調査）"
        else:
            related = set(fam["related_units"]) | {u["id"] for u in units if fid in (u.get("sheet_family_links") or [])}
        fam["related_units"] = [uid for uid in order if uid in related]
        for uid in fam["related_units"]:
            links[uid].append(fid)
    for u in units:
        u["sheet_family_links"] = sorted(links[u["id"]])
    cov["correspondence_source_note"] = ("シート族と評価単位の対応はこのファイルが唯一の出所。units.json の sheet_family_links は"
                                         "ここから tools/sync_ledger.py が機械的に作る。名称から計算構造を推定できない族（NOT_INSPECTED）は"
                                         "どの単位にも対応させない。")
    COVERAGE.write_text(json.dumps(cov, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> int:
    registry.load_all()
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    units = ledger["units"]
    ids = {u["id"] for u in units}
    changed = 0
    for u in units:
        ref = registry.UNITS.get(u["id"])
        if ref is None:
            u["reference_semantics"] = None
            continue
        doc = re.sub(r"\s*\n\s*", "", ref.doc)
        deps = sorted(ref.depends_on)
        missing = [d for d in deps if d not in ids]
        if missing:
            raise SystemExit(f"{u['id']} depends on units missing from the ledger: {missing}")
        if u.get("reference_semantics") != doc or u["depends_on"] != deps:
            changed += 1
        u["reference_semantics"] = doc
        u["depends_on"] = deps
    sync_families(units)
    feeds: dict[str, set] = {uid: set() for uid in ids}
    for u in units:
        for d in u["depends_on"]:
            feeds[d].add(u["id"])
    for u in units:
        u["feeds"] = sorted(feeds[u["id"]])
    ledger["reference_note"] = ("reference_semantics は基準計算（research_code/refcalc）の関数の説明文そのもので、"
                                "本研究が採用した定義。reference_semantics_proposal（分析担当の提案）と異なる場合は reference_semantics が優先する。")
    LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"synced {len(units)} units ({changed} changed); reference functions: {len(registry.UNITS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
