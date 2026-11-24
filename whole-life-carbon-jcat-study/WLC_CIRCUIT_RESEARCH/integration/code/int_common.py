"""G4 integration: paths, read-only loaders and hygiene checks (fictional data only).

Run every integration script as
    PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 -B <script>
Nothing here writes outside `WLC_CIRCUIT_RESEARCH/integration/`.

Loaded read-only (never edited, never byte-compiled):
  * frozen original code: 10_TRANSFORM_STUDY/research_code/tstudy (+ specs, refcalc via baseline), and
    17_WHOLE_BUILDING_TIME_THEORY/code (canon, timechar) -- only after tstudy.baseline.assert_frozen();
  * route B `grammar.py` (D-verified kernel netlists + late-reset refrigerant automaton) -- Psi side;
  * route D `oracle_d.py` (rational event-ledger oracle) -- used ONLY as the test oracle for the Phi side.
Route modules are loaded by file path with importlib (sys.dont_write_bytecode is set first).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import platform
import subprocess
import sys

sys.dont_write_bytecode = True
os.environ.setdefault("GIT_OPTIONAL_LOCKS", "0")

HERE = os.path.dirname(os.path.abspath(__file__))
INTEG = os.path.dirname(HERE)
RESEARCH = os.path.dirname(INTEG)
STUDY = os.path.dirname(RESEARCH)
REPO = os.path.dirname(STUDY)
ROUTES = os.path.join(RESEARCH, "routes")
TSTUDY = os.path.join(STUDY, "10_TRANSFORM_STUDY", "research_code")
CANON_DIR = os.path.join(STUDY, "17_WHOLE_BUILDING_TIME_THEORY", "code")
UNITS70 = os.path.join(STUDY, "WLC_THEORY_RESEARCH_BASE", "data", "units70.json")
RESULTS = os.path.join(INTEG, "results")
FROZEN_DIRS = [os.path.join(STUDY, d) for d in ("09_APPROX_STUDY", "10_TRANSFORM_STUDY",
                                                 "17_WHOLE_BUILDING_TIME_THEORY", "WLC_THEORY_RESEARCH_BASE")]

B_GRAMMAR = os.path.join(ROUTES, "B_formula_network", "code", "grammar.py")
D_ORACLE = os.path.join(ROUTES, "D_verification", "code", "oracle_d.py")
A_POINTS = os.path.join(ROUTES, "A_waveform", "results", "points.json")

# Scenarios for the Psi composition: evaluation_set(12) (seed 720002) items NOT used by any route:
# B used benchmark S/M + EV3, EV11; D used EV6, EV10 (+ BM-S/BM-M re-measurements); C used benchmark S/M/L + 2 edge.
PSI_SCENARIOS = {"EV2": 2, "EV9": 9}

_MODS: dict = {}


def _load(name: str, path: str):
    if name in _MODS:
        return _MODS[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _MODS[name] = mod
    return mod


def route_b_grammar():
    return _load("int_B_grammar", B_GRAMMAR)


def route_d_oracle():
    return _load("int_D_oracle", D_ORACLE)


def frozen():
    """Frozen modules after assert_frozen(); SystemExit if the baseline changed (coordinator rule: stop)."""
    if "frozen" in _MODS:
        return _MODS["frozen"]
    if TSTUDY not in sys.path:
        sys.path.insert(0, TSTUDY)
    from tstudy import baseline
    try:
        trees = baseline.assert_frozen()
    except Exception as ex:  # noqa: BLE001
        raise SystemExit(f"assert_frozen FAILED: {ex!r}")
    baseline.load()
    from tstudy import scenarios, unified
    from specs import system as specs_system
    _MODS["frozen"] = {"baseline": baseline, "scenarios": scenarios, "unified": unified,
                       "system": specs_system, "trees": trees}
    return _MODS["frozen"]


def canon_modules():
    frozen()
    if CANON_DIR not in sys.path:
        sys.path.insert(0, CANON_DIR)
    import canon
    import timechar
    from synth import population
    return canon, timechar, population


def psi_scenario(tag: str):
    fz = frozen()
    if tag.endswith("-noB2"):
        import copy
        s = copy.deepcopy(psi_scenario(tag[:-5]))
        s.boundary.included_lifecycle_stages = [x for x in s.boundary.included_lifecycle_stages if x != "B2"]
        s.meta.scenario_id += "-noB2"
        return s
    return fz["scenarios"].evaluation_set(12)[PSI_SCENARIOS[tag]]


def refcalc_at(scn, T: float) -> dict:
    fz = frozen()
    return fz["baseline"].run_reference(fz["scenarios"].with_period(scn, float(T)))


def domain_violations(scn, T: float) -> list:
    """Reasons (scn, T) is outside scenarios.valid_domain; EMPTY list = usable."""
    fz = frozen()
    return fz["scenarios"].valid_domain(fz["scenarios"].with_period(scn, float(T)))


def units70() -> dict:
    with open(UNITS70, encoding="utf-8") as f:
        return json.load(f)


def pycache_dirs() -> list:
    out = []
    for d, sub, _ in os.walk(REPO):
        if ".git" in sub:
            sub.remove(".git")
        if "__pycache__" in sub:
            out.append(os.path.join(d, "__pycache__"))
    return out


def sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def head_sha() -> str:
    return subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"], capture_output=True, text=True,
                          env=dict(os.environ, GIT_OPTIONAL_LOCKS="0")).stdout.strip()


def provenance() -> dict:
    return {"head": head_sha(), "python": platform.python_version(), "machine": platform.machine(),
            "inputs_sha256": {os.path.relpath(p, RESEARCH): sha256(p) for p in (B_GRAMMAR, D_ORACLE, A_POINTS, UNITS70)}}


def rel(a, b) -> float:
    a, b = float(a), float(b)
    if a == b:
        return 0.0
    return abs(a - b) / abs(b) if b != 0 else abs(a)


def dump(name: str, obj) -> str:
    os.makedirs(RESULTS, exist_ok=True)
    p = os.path.join(RESULTS, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, default=str, ensure_ascii=False)
    return p
