#!/usr/bin/env python3
"""Keep the unit ledger consistent with the reference calculation.

For every unit that has a reference function:
  reference_semantics  <- the function's docstring (the binding definition)
  depends_on           <- the dependencies declared in the registry
  feeds                <- inverse of depends_on (recomputed for all units)

Run:  cd research_code && python3 -m tools.sync_ledger
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from refcalc import registry

LEDGER = Path(__file__).resolve().parents[2] / "01_LEDGER" / "units.json"


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
