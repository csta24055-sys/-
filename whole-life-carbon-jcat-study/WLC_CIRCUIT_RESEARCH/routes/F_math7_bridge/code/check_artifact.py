"""Check a DOWNLOADED `math-ir-efficient-result` artifact (result.json only)
against route F's expected sidecar. Not run yet: no seven-engine artifact exists.

Usage: math7-py -B code/check_artifact.py INPUT.json EXPECTED.json result.json

In mode 'full-seven', portable.py verify-full has already required the SageMath
and MATLAB exact values to equal the SymPy exact value per case, so comparing
result.json 'exact' with the expected value covers all three exact engines.
The script refuses to call anything seven-engine unless mode == 'full-seven'
and engine_coverage lists SageMath and MATLAB.
"""
import json
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ir import node_to_fraction  # noqa: E402
sys.path.pop(0)
import hashlib  # noqa: E402


def canonical_sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode()).hexdigest()


def main(inp, side, res):
    bundle = json.loads(Path(inp).read_text())
    exp = {e["case_id"]: Fraction(e["expected"]) for e in json.loads(Path(side).read_text())}
    r = json.loads(Path(res).read_text())
    ok = r["input_sha256"] == canonical_sha(bundle)
    print("input hash matches artifact:", ok)
    seven = r["mode"] == "full-seven" and {"SageMath", "MATLAB"} <= set(r["engine_coverage"])
    print("artifact mode:", r["mode"], "| seven-engine:", seven)
    for c in r["cases"]:
        v = node_to_fraction(c["exact"])
        good = v == exp[c["case_id"]]
        ok &= good
        print("PASS" if good else "FAIL", c["case_id"], v, "expected", exp[c["case_id"]])
    print("ARTIFACT EXPECTED-VALUE CHECK:", "PASS" if ok else "FAIL",
          "(seven-engine)" if seven else "(NOT a seven-engine artifact)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
