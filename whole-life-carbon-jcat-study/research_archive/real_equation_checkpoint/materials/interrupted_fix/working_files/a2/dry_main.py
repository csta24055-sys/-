"""Dry run of bench.verify_unified.main() with every output path redirected to the scratch folder."""
import sys
from pathlib import Path

from bench import mechanism_probe, verify_unified as vu

dry = Path(sys.argv[1])
vu.OUT = dry / "unified_model_exactness.json"
vu.OUT_LOAD = dry / "unified_model_load.json"
assert mechanism_probe.OUT.name == "mechanism_probe.json"
sys.argv = ["verify_unified", "--population", "6", "--dirty", "3", "--sweep", "2", "--repeats", "1"]
code = vu.main()
print("exit code", code, sorted(p.name for p in dry.iterdir()))
