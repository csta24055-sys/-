"""Where the existing engine and the input model live, and how to import them (read-only)."""
from __future__ import annotations

import hashlib
import os
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.normpath(os.path.join(HERE, ".."))
STUDY_ROOT = os.path.normpath(os.path.join(APP_ROOT, ".."))
ENGINE_CODE = os.path.join(STUDY_ROOT, "10_TRANSFORM_STUDY", "research_code")
MODEL_CODE = os.path.join(STUDY_ROOT, "09_APPROX_STUDY", "research_code")
INVENTORY = os.path.join(STUDY_ROOT, "03_INPUTS", "inputs.json")

ENGINE_PARTS = ("tstudy", "specs")      # packages of the two-structure engine
MODEL_PARTS = ("synth",)                # dataclasses of the engine's input model (frozen)

# Source hashes of the engine and of its input model at the time this app was verified against
# them (2026-11-12, research commit b93201e). ``fingerprint()`` says whether the code in use
# is still that code; a difference means the app has to be verified again.
VERIFIED_ENGINE_SHA256 = "322df5b73607ba42f1c5d158cd12cacb804017584707bfd57c8da79d6cc15427"
VERIFIED_MODEL_SHA256 = "f156112f43eda1e472fd5d1cdaf735923804308be83582cd7a9164bfb4ebda16"

_fingerprint: dict | None = None


def setup() -> None:
    """Make the engine and its input model importable. Appended, so nothing of the app is shadowed."""
    sys.dont_write_bytecode = True
    for path in (ENGINE_CODE, MODEL_CODE):
        if path not in sys.path:
            sys.path.append(path)


def model():
    setup()
    from synth import model as m
    return m


def model_io():
    setup()
    from synth import io
    return io


def generator():
    setup()
    from synth import generate
    return generate


def unified():
    setup()
    from tstudy import unified as u
    return u


def _hash_tree(root: str, parts: tuple[str, ...]) -> str:
    h = hashlib.sha256()
    for part in parts:
        base = os.path.join(root, part)
        for folder, dirs, files in os.walk(base):
            dirs[:] = sorted(d for d in dirs if d != "__pycache__")
            for name in sorted(files):
                if name.endswith(".py"):
                    full = os.path.join(folder, name)
                    h.update(os.path.relpath(full, root).replace(os.sep, "/").encode())
                    with open(full, "rb") as fh:
                        h.update(fh.read())
    return h.hexdigest()


def fingerprint() -> dict:
    """Identity of the calculation code actually used (source hashes, step counts, library versions)."""
    global _fingerprint
    if _fingerprint is None:
        setup()
        import platform

        import numpy
        from tstudy import unified as u
        _fingerprint = {
            "engine": "two-structure engine (masked sum-product / knot spectrum), tstudy.unified.System",
            "engine_source_sha256": _hash_tree(ENGINE_CODE, ENGINE_PARTS),
            "model_source_sha256": _hash_tree(MODEL_CODE, MODEL_PARTS),
            "steps": {"P1": len(u.P1.steps), "TIME": len(u.P_TIME.steps), "AGG": len(u.P_AGG.steps)},
            "python": platform.python_version(),
            "numpy": numpy.__version__,
        }
        _fingerprint["engine_is_verified_version"] = (
            _fingerprint["engine_source_sha256"] == VERIFIED_ENGINE_SHA256
            and _fingerprint["model_source_sha256"] == VERIFIED_MODEL_SHA256)
    return dict(_fingerprint)
