"""Phase 3: structured, restricted Math IR between SageMath and MATLAB."""
from __future__ import annotations
import copy
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import phase1


def dump(path, value):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(phase1.canonical(value) + "\n", encoding="utf8")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


def prepare(directory):
    bundle = phase1.make_cases()
    manifest = {
        "schema": "math-ir-phase3/1",
        "bundle_sha256": phase1.digest(bundle),
        "cases": [
            {
                "case_id": c["case_id"],
                "input_sha256": phase1.digest(c),
                "metadata_sha256": phase1.digest({
                    "unit": c["unit"], "symbols": c["symbols"],
                    "substitution": c["substitution"], "exact": c["exact"]
                }),
                "unit": c["unit"]
            }
            for c in bundle["cases"]
        ]
    }
    dump(Path(directory) / "input.json", bundle)
    dump(Path(directory) / "manifest.json", manifest)
    print("PHASE3 INPUT: 5 exact synthetic cases prepared")


def verify(directory):
    p = Path(directory)
    bundle, manifest = read(p / "input.json"), read(p / "manifest.json")
    sage, matlab = read(p / "sage_result.json"), read(p / "matlab_result.json")
    phase1.require(bundle["schema"] == phase1.SCHEMA, "invalid input schema")
    phase1.require(manifest["schema"] == "math-ir-phase3/1", "invalid manifest schema")
    phase1.require(manifest["bundle_sha256"] == phase1.digest(bundle), "input hash mismatch")
    cases = bundle["cases"]
    phase1.require(type(cases) is list and len(cases) == 5, "wrong case count")
    phase1.require(type(manifest["cases"]) is list and len(manifest["cases"]) == 5, "wrong manifest count")
    for c, m in zip(cases, manifest["cases"]):
        phase1.check_envelope(c)
        expected = {
            "case_id": c["case_id"], "input_sha256": phase1.digest(c),
            "metadata_sha256": phase1.digest({
                "unit": c["unit"], "symbols": c["symbols"],
                "substitution": c["substitution"], "exact": c["exact"]
            }), "unit": c["unit"]
        }
        phase1.require(m == expected, "manifest differs from canonical source")
    phase1.require(sage["schema"] == phase1.SCHEMA and sage["engine"] == "SageMath", "wrong SageMath output")
    phase1.require(sage["source"] == bundle and sage["source_sha256"] == phase1.digest(bundle), "Sage source changed")
    phase1.require(matlab["engine"] == "MATLAB" and matlab["schema"] == "math-ir-phase3/1", "wrong MATLAB output")
    phase1.require(matlab["bundle_sha256"] == manifest["bundle_sha256"], "MATLAB bundle mismatch")
    ids = [c["case_id"] for c in cases]
    for engine, output in (("sage", sage), ("matlab", matlab)):
        rows = output["results"]
        phase1.require(type(rows) is list and len(rows) == len(cases), "missing results")
        phase1.require([r["case_id"] for r in rows] == ids, "reordered or duplicated results")
        for i, (c, m, row) in enumerate(zip(cases, manifest["cases"], rows)):
            expected_fields = {"case_id", "input_sha256", "result"}
            if engine == "matlab":
                expected_fields |= {"metadata_sha256", "unit", "upstream_result"}
            phase1.exact_fields(row, expected_fields, "result row")
            phase1.require(row["input_sha256"] == m["input_sha256"], "wrong input lineage")
            if engine == "matlab":
                phase1.require(row["metadata_sha256"] == m["metadata_sha256"], "metadata lost")
                phase1.require(row["unit"] == c["unit"], "unit lost")
                phase1.require(row["upstream_result"] == sage["results"][i]["result"],
                               "SageMath output was not transferred exactly")
            phase1.check_node(row["result"], set())
            phase1.require(row["result"]["op"] == "rational", "result not an exact rational")
            phase1.require(row["result"] == phase1.sympy_eval(c), "mathematical disagreement")
            print("PASS", engine, c["case_id"], row["result"]["numerator"] + "/" + row["result"]["denominator"])
    print("PHASE 3: PASS 5 exact results in SageMath -> MATLAB -> SymPy, with metadata and hashes")


def negative(directory):
    p = Path(directory)
    original = {name: read(p / name) for name in
                ("input.json", "manifest.json", "sage_result.json", "matlab_result.json")}
    tests = {
        "matlab_value": ("matlab_result.json", lambda x: x["results"][0]["result"].update(numerator="999")),
        "matlab_unit": ("matlab_result.json", lambda x: x["results"][0].update(unit="1")),
        "matlab_input_hash": ("matlab_result.json", lambda x: x["results"][1].update(input_sha256="0" * 64)),
        "matlab_metadata_hash": ("matlab_result.json", lambda x: x["results"][2].update(metadata_sha256="0" * 64)),
        "matlab_upstream": ("matlab_result.json", lambda x: x["results"][0]["upstream_result"].update(numerator="999")),
        "sage_value": ("sage_result.json", lambda x: x["results"][0]["result"].update(numerator="999")),
        "source_assumptions": ("input.json", lambda x: x["cases"][2]["symbols"][0].update(constraints=[])),
        "missing_row": ("matlab_result.json", lambda x: x["results"].pop())
    }
    with TemporaryDirectory() as tmp:
        for title, (name, mutate) in tests.items():
            for n, value in original.items():
                dump(Path(tmp) / n, value)
            altered = copy.deepcopy(original[name])
            mutate(altered)
            dump(Path(tmp) / name, altered)
            try:
                verify(tmp)
            except (ValueError, TypeError, KeyError, AssertionError):
                print("PASS corruption rejected:", title)
            else:
                raise AssertionError("Accepted altered data: " + title)
    print("PHASE 3 NEGATIVE: PASS", len(tests), "cases")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in {"prepare", "verify", "negative"}:
        raise SystemExit("usage: phase3.py prepare|verify|negative DIRECTORY")
    {"prepare": prepare, "verify": verify, "negative": negative}[sys.argv[1]](sys.argv[2])
