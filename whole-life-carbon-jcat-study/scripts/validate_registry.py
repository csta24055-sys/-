#!/usr/bin/env python3
"""Check published metadata and input/formula/output link integrity."""
from pathlib import Path
import json
import sys

BASE = Path(__file__).resolve().parents[1]
def load(name):
    return json.loads((BASE / name).read_text(encoding="utf-8"))

def validate():
    rights = load("01_COMPLIANCE/RULES.json")
    inputs = load("03_INPUTS/inputs.json")["fields"]
    formulas = load("04_FORMULAS/formulas.json")["formulae"]
    outputs = load("05_OUTPUTS/outputs.json")["outputs"]
    links = load("06_LINEAGE/links.json")
    inventory = load("02_SOURCES/ALL_198_SHEETS.json")
    ids = [x["id"] for x in inputs]
    fids = [x["id"] for x in formulas]
    oids = [x["output_id"] for x in outputs]
    assert len(set(ids)) == len(ids), "duplicate input ID"
    assert len(set(fids)) == len(fids), "duplicate formula ID"
    assert len(set(oids)) == len(oids), "duplicate output ID"
    assert inventory["total_sheets"] == 198
    assert len(inventory["sheets"]) == 198
    assert inventory["total_formula_nodes"] == 3818483
    assert sum(x["formula_xml_nodes"] for x in inventory["sheets"]) == 3818483
    counts = {"STD": 77, "SIM": 73, "DET": 24, "CLS": 13, "SUM": 11}
    for name, expected in counts.items():
        assert len([x for x in inventory["sheets"] if x["book"] == name]) == expected
    for formula in formulas:
        assert formula["jcat_verbatim"] is False
        assert formula["validation"] == "NOT_EXECUTED"
        assert set(formula["inputs"]).issubset(ids), formula["id"]
        assert formula["output"] in oids
    assert links["input_count"] == len(ids)
    assert links["formula_count"] == len(fids)
    assert links["output_count"] == len(oids)
    assert not links["missing_reference_errors"]
    assert set(x["input_id"] for x in links["links_by_input"]) == set(ids)
    assert set(x["formula_id"] for x in links["links_by_formula"]) == set(fids)
    assert len(rights["rules"]) >= 8
    for path in BASE.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        assert path.suffix.lower() not in {".xlsx", ".xlsm", ".zip", ".pdf"}, f"Restricted file: {path}"
    print(f"PASS: {len(ids)} fields, {len(fids)} formulas, {len(oids)} outputs, 198 sheets")
    print(f"UNLINKED INPUTS (not a pass): {links['unmapped_input_count']}; completeness is NOT guaranteed.")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(validate())
    except (OSError, KeyError, ValueError, AssertionError) as e:
        print("FAIL:", e, file=sys.stderr)
        sys.exit(1)
