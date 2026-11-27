"""Freeze record of the prior research that this study builds on (read-only; nothing in the prior checkouts is modified).

Usage:
  python3 -I tools/freeze_baseline.py <foundation_checkout> <theorybase_checkout> <out.json>

<foundation_checkout>: git worktree of csta24055-sys/- at 761da13d6cab68eb76a7bd7eba0262b82b7fde29
                       (branch claude/jcat-lca-app-foundation-c33936, tip on 2026-11-27)
<theorybase_checkout>: git worktree at 9416a1bbb3c48d6fd9589789dcb045c0eb6e03be
                       (branch claude/wlc-theory-research-base-c33936)
Records the commit of each checkout and the SHA-256 of every file this study reads.
"""
import hashlib
import json
import os
import subprocess
import sys

STUDY = "whole-life-carbon-jcat-study"
FOUNDATION_FILES = [
    "01_COMPLIANCE/README.md",
    "01_COMPLIANCE/RULES.json",
    "10_TRANSFORM_STUDY/11_UNIFIED_SYSTEM/UNITS_70.md",
    "10_TRANSFORM_STUDY/research_code/tstudy/msp.py",
    "10_TRANSFORM_STUDY/research_code/tstudy/unified.py",
    "10_TRANSFORM_STUDY/research_code/specs/system.py",
    "10_TRANSFORM_STUDY/research_code/checks/sets_unified.py",
    "14_EQUATION_DISCLOSURE/07_建物全体の統一方程式_完全版.md",
    "14_EQUATION_DISCLOSURE/original_formula_counts.json",
    "15_JCAT_CONVERSION/01_分類と変換状態_667件.csv",
    "15_JCAT_CONVERSION/README.md",
    "15_JCAT_CONVERSION/06_分類の手順.md",
    "16_UNRESOLVED8_EXACT_APPROX/README.md",
    "17_WHOLE_BUILDING_TIME_THEORY/01_理想方程式.md",
    "17_WHOLE_BUILDING_TIME_THEORY/03_時間特性の定理と証明.md",
    "17_WHOLE_BUILDING_TIME_THEORY/06_70単位の時間特性.md",
    "17_WHOLE_BUILDING_TIME_THEORY/code/canon.py",
    "19_JCAT_REMAINING12/README.md",
    "21_UNIFIED_THEORY_REPORT/README.md",
    "22_WLC_COMPLETE_TEXTBOOK/README.md",
]
THEORY_FILES = [
    "WLC_THEORY_RESEARCH_BASE/data/units70.csv",
    "WLC_THEORY_RESEARCH_BASE/data/unit_dependencies.csv",
    "WLC_THEORY_RESEARCH_BASE/02_70評価単位の完全台帳.md",
    "WLC_THEORY_RESEARCH_BASE/04_マスク積和の理論.md",
    "WLC_THEORY_RESEARCH_BASE/09_未解決問題と限界.md",
]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def head(repo):
    return subprocess.check_output(["git", "-C", repo, "rev-parse", "HEAD"], text=True).strip()


def main(fnd, thb, out):
    rec = {"foundation": {"commit": head(fnd), "files": {}}, "theory_base": {"commit": head(thb), "files": {}}}
    for rel in FOUNDATION_FILES:
        rec["foundation"]["files"][rel] = sha(os.path.join(fnd, STUDY, rel))
    for rel in THEORY_FILES:
        rec["theory_base"]["files"][rel] = sha(os.path.join(thb, STUDY, rel))
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    print("frozen", len(rec["foundation"]["files"]) + len(rec["theory_base"]["files"]), "files")


if __name__ == "__main__":
    main(*sys.argv[1:4])
