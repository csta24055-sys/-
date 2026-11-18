#!/usr/bin/env python3
"""Audit workbook XML locally, without executing Excel/VBA.

Requires: Python 3.10+ standard library.
Only writes to local-only/; those files MUST NOT be pushed to GitHub.
This does not reconstruct formula semantics or grant redistribution rights.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile
import xml.etree.ElementTree as ET

X = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
P = "{http://schemas.openxmlformats.org/package/2006/relationships}"
EXPECTED = {
    "Standard": 77,
    "Simplified": 73,
    "Detailed": 24,
    "Classfication": 13,
    "Classification": 13,
    "Summary": 11,
}

def workbook_sheets(zfile):
    root = ET.fromstring(zfile.read("xl/workbook.xml"))
    rel_root = ET.fromstring(zfile.read("xl/_rels/workbook.xml.rels"))
    rels = {r.attrib["Id"]: r.attrib["Target"] for r in rel_root.findall(f"{P}Relationship")}
    out = []
    for s in root.findall(f".//{X}sheet"):
        rid = s.attrib.get(f"{R}id")
        if rid not in rels:
            continue
        dest = rels[rid].lstrip("/")
        if not dest.startswith("xl/"):
            dest = "xl/" + dest
        out.append((s.attrib.get("name", ""), dest, s.attrib.get("state", "visible")))
    return out

def audit_member(file_name, buf, manifest_writer=None):
    result = {"source_name": file_name, "sheets": [], "formula_xml_nodes": 0}
    with zipfile.ZipFile(io.BytesIO(buf)) as book:
        sheets = workbook_sheets(book)
        for number, (name, path, state) in enumerate(sheets, 1):
            if path not in book.namelist():
                raise ValueError(f"Missing worksheet XML: {path}")
            formulas = 0
            seen_cells = 0
            shared = 0
            with book.open(path) as xml_file:
                cell_addr = ""
                for event, node in ET.iterparse(xml_file, events=("start", "end")):
                    if event == "start" and node.tag == X + "c":
                        cell_addr = node.attrib.get("r", "")
                    elif event == "end":
                        if node.tag == X + "f":
                            formulas += 1
                            f_type = node.attrib.get("t", "normal")
                            if f_type == "shared":
                                shared += 1
                            if manifest_writer:
                                # Full original formulas are NEVER exported;
                                # a hash is retained locally for change detection.
                                expression = node.text or ""
                                record = {
                                    "source": file_name, "sheet": name, "cell": cell_addr,
                                    "formula_kind": f_type,
                                    "sha256": hashlib.sha256(expression.encode("utf-8")).hexdigest()
                                    if expression else None,
                                    "has_formula_body": bool(expression)
                                }
                                manifest_writer.write((json.dumps(record, ensure_ascii=False) + "\n").encode())
                        elif node.tag == X + "c":
                            seen_cells += 1
                            node.clear()
                        elif node.tag == X + "row":
                            node.clear()
            row = {
                "sheet_index": number, "sheet_name": name, "visibility": state,
                "formula_xml_nodes": formulas, "shared_formula_nodes": shared,
                "cell_nodes": seen_cells
            }
            result["sheets"].append(row)
            result["formula_xml_nodes"] += formulas
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("source_zip", type=Path, help="Own authorized source ZIP; never commit it.")
    p.add_argument("--output-dir", type=Path, default=Path("local-only"))
    p.add_argument("--hash-per-cell", action="store_true", help="Very large local-only file (~millions of rows).")
    args = p.parse_args()
    if not args.source_zip.is_file():
        p.error("source file does not exist")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    members = []
    count = 0
    with zipfile.ZipFile(args.source_zip) as z:
        excel = [x for x in z.namelist() if x.lower().endswith((".xlsx", ".xlsm"))]
        if not excel:
            p.error("no Excel workbooks in archive")
        writer = gzip.open(args.output_dir / "formula_hash_manifest.jsonl.gz", "wb") if args.hash_per_cell else None
        try:
            for name in excel:
                print("Scan:", name, file=sys.stderr)
                record = audit_member(name, z.read(name), writer)
                members.append(record)
                count += record["formula_xml_nodes"]
        finally:
            if writer:
                writer.close()
    result = {
        "warning": "LOCAL-ONLY metadata. No original formula text, parameter values, VBA, or factors included.",
        "source_zip_basename": args.source_zip.name,
        "workbooks": members, "sheet_count": sum(len(x["sheets"]) for x in members),
        "formula_xml_nodes": count
    }
    path = args.output_dir / "sheet_formula_metadata.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Workbooks: {len(members)}, sheets: {result['sheet_count']}, formula XML nodes: {count:,}")
    print("Local metadata saved:", path)
    if args.hash_per_cell:
        print("Local hashed per-cell inventory saved; do NOT upload local-only/ to GitHub.")

if __name__ == "__main__":
    main()
