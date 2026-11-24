#!/usr/bin/env python3
"""Read-only plan/config audit and small **synthetic** mathematical smoke checks.

Run from any directory:
  PYTHONDONTWRITEBYTECODE=1 python3 -B whole-life-carbon-jcat-study/WLC_CIRCUIT_RESEARCH/tools/audit_project_plan.py

NO network calls, GitHub Actions dispatch, repository writes, or non-stdlib dependencies.
PASS means only the file configuration and these toy identities passed. This is NOT
proof of the WLC circuit research, actual model access, or 7-engine verification.
"""
from __future__ import annotations

import json
import math
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
STUDY = REPO / "whole-life-carbon-jcat-study" / "WLC_CIRCUIT_RESEARCH"
THEORY = REPO / "whole-life-carbon-jcat-study" / "WLC_THEORY_RESEARCH_BASE"
AGENTS = REPO / ".claude" / "agents"

EXPECTED_AGENTS = {
    "wlc-architect": ("claude-fable-5-2", "high"),
    "wlc-waveform": ("claude-opus-5-5", "medium"),
    "wlc-formula-network": ("claude-opus-5-5", "medium"),
    "wlc-unit-mapper": ("claude-opus-5-5", "medium"),
    "wlc-resistor-energy": ("claude-opus-5-5", "medium"),
    "wlc-math7-orchestrator": ("claude-opus-5-5", "medium"),
    "wlc-verifier": ("claude-opus-5-5", "high"),
    "wlc-integrator": ("claude-opus-5-5", "high"),
    "wlc-replanner": ("claude-fable-5-2", "high"),
}

REQUIRED = (
    REPO / "CLAUDE.md",
    REPO / "AGENTS.md",
    REPO / ".github" / "copilot-instructions.md",
    STUDY / "07_SHARED_CONTRACT.md",
    STUDY / "08_AUTONOMOUS_START.md",
    STUDY / "10_MODEL_ROUTING.md",
    STUDY / "11_MATH7_INTEGRATION.md",
    STUDY / "12_FINAL_OPERATING_PLAN.md",
    THEORY / "00_README.md",
    THEORY / "13_別チャット引継ぎ文.md",
)


def frontmatter(path: Path) -> dict[str, str]:
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        return {}
    _, block, _ = content.split("---", 2)
    result: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
    return result


def run() -> int:
    problems: list[str] = []
    checks = 0

    def expect(condition: bool, msg: str) -> None:
        nonlocal checks
        checks += 1
        if not condition:
            problems.append(msg)

    for path in REQUIRED:
        expect(path.is_file(), f"Missing required reference: {path.relative_to(REPO)}")

    settings_path = REPO / ".claude" / "settings.json"
    if settings_path.is_file():
        try:
            cfg = json.loads(settings_path.read_text(encoding="utf-8"))
            expect(cfg.get("model") == "claude-fable-5-2", "Unexpected startup model")
            expect(cfg.get("effortLevel") == "high", "Unexpected startup effort")
        except (ValueError, OSError) as ex:
            problems.append(f"Invalid Claude project settings: {ex}")
    else:
        problems.append("Missing .claude/settings.json")

    for name, (model, effort) in EXPECTED_AGENTS.items():
        path = AGENTS / f"{name}.md"
        expect(path.is_file(), f"Missing subagent: {name}")
        if path.is_file():
            d = frontmatter(path)
            expect(d.get("name") == name, f"Agent name mismatch: {name}")
            expect(d.get("model") == model, f"Agent model mismatch: {name}")
            expect(d.get("effort") == effort, f"Agent effort mismatch: {name}")
            expect("12_FINAL_OPERATING_PLAN.md" in path.read_text(encoding="utf-8"),
                   f"Agent did not adopt audited runbook: {name}")

    for route in ("A_waveform", "B_formula_network", "C_70_units",
                  "D_verification", "E_resistor_energy", "F_math7_bridge"):
        expect((STUDY / "routes" / route / "README.md").is_file(),
               f"Missing route: {route}")

    text = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    expect("12_FINAL_OPERATING_PLAN.md" in text, "Root instructions miss execution authority")
    expect("main" in text and "math_tools_v2" in text,
           "Math7 main-branch separation missing")

    # Common P0 example, right-continuous event inclusion only.
    def emissions_at(years: Fraction) -> Fraction:
        events_ac = int(years // 10)
        events_pipe = int(years // 20)
        return Fraction(100) + Fraction(4) * years + 20 * events_ac + 35 * events_pipe

    for t, expected in ((10, 160), (20, 255), (30, 315), (40, 410)):
        expect(emissions_at(Fraction(t)) == expected, f"Toy event ledger mismatch: {t} years")
    expect(emissions_at(Fraction(20) - Fraction(1, 1000000)) <
           emissions_at(Fraction(20)), "Boundary jump not represented")
    expect(emissions_at(Fraction(20) + Fraction(1, 1000000)) >
           emissions_at(Fraction(20)), "Continuous growth after event omitted")

    # Joule heat is cumulative dissipated energy, not temperature or capacitor energy.
    current, resistance, seconds = 2, 3, 5
    power = current * current * resistance
    energy = power * seconds
    expect(power == 12 and energy == 60, "DC Joule heat identity failed")
    omega = 2 * math.pi
    e_ac = (current * current * resistance) * (
        seconds - math.sin(2 * omega * seconds) / (2 * omega))
    expect(math.isclose(e_ac, 60, rel_tol=1e-12, abs_tol=1e-12),
           "AC RMS energy integral failed at five full cycles")

    print(f"Config checks executed: {checks}")
    print("Research outcome: NOT_RUN; independent 7-engine WLC validation: NOT_RUN")
    if problems:
        print(f"CONFIG FAIL ({len(problems)}):")
        for item in problems:
            print(" -", item)
        return 1
    print("CONFIG PASS: static project wiring + toy mathematical identities only")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
