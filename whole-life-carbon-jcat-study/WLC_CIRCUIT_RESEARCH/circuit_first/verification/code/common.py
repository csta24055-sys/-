"""Shared helpers for the verifier (V1). Imports the builder's FROZEN snapshot read-only."""
from __future__ import annotations

import json
import os
import sys
from fractions import Fraction as F

sys.dont_write_bytecode = True

SNAP = os.environ.get(
    "CF_SNAPSHOT",
    "/tmp/claude-0/-home-user--/d16c9837-8c7c-5bcc-8b70-730caf3a5491/scratchpad/cf_snapshot_A/"
    "whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/circuit_first")
HERE = os.path.dirname(os.path.abspath(__file__))
VROOT = os.path.dirname(HERE)
RESULTS = os.environ.get("CF_RESULTS", os.path.join(VROOT, "results"))


def builder():
    """Import the snapshot's model/adapter (no bytecode written)."""
    if SNAP not in sys.path:
        sys.path.insert(0, SNAP)
    import adapter  # noqa
    import model    # noqa
    return model, adapter


def fstr(x):
    if isinstance(x, F):
        return f"{x.numerator}/{x.denominator}" if x.denominator != 1 else str(x.numerator)
    return x


def _default(o):
    if isinstance(o, F):
        return fstr(o)
    if isinstance(o, (set, frozenset, tuple)):
        return [ _default(x) if isinstance(x, F) else x for x in o]
    return str(o)


def save(name, obj):
    os.makedirs(RESULTS, exist_ok=True)
    p = os.path.join(RESULTS, name)
    with open(p, "w") as f:
        json.dump(obj, f, indent=1, default=_default)
    return p


def rel(a, b):
    a, b = F(a), F(b)
    if a == b:
        return F(0)
    return abs(a - b) / max(abs(b), F(1))
