"""Build restricted Math IR 0.1 inputs (<= 20 cases each) for the WLC study's
EXPRESSIBLE arithmetic identities, plus expected-value sidecars whose values are
read at build time from the routes' published result files (not retyped).

Usage: math7-py -B code/build_inputs.py   (run from anywhere; paths are absolute)

What is NOT encoded (outside Math IR 0.1, see results/probes.json):
  floor / event counting, min/max/clip kernels, comparisons, piecewise,
  sqrt, sin/cos, pi, integrals, recurrences, masked sum-products.
Where a case needs an event count n10/n20/nR or a clip value min(t,10), the
VALUE is computed here in Python (documented per case) and passed as a rational
substitution: Math7 then checks only the arithmetic, not the event counting.
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ir import R, S, add, mul, pw, neg, case  # noqa: E402

F = HERE.parent
ROUTES = F.parent
REPO = ROUTES.parents[2]
A_POINTS = ROUTES / "A_waveform/results/points.json"
E_POINTS = ROUTES / "E_resistor_energy/results/points.json"
E_NUMS = ROUTES / "E_resistor_energy/results/e_numbers.json"


def rel(p: Path) -> str:
    return str(p.relative_to(REPO))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git_blob(p: Path) -> str:
    out = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD:" + rel(p)],
                         capture_output=True, text=True)
    return out.stdout.strip() or "untracked"


def point(path: Path, name: str, conv: str, t: str) -> Fraction:
    d = json.loads(path.read_text())
    rows = d["rows"] if isinstance(d, dict) else d
    vals = {r["value"] for r in rows
            if r["case"] == name and r.get("convention") == conv and r["t"] == t}
    if len(vals) != 1:
        raise SystemExit(f"ambiguous/missing {name} {conv} {t} in {path}: {vals}")
    return Fraction(vals.pop())


def enum(*keys):
    d = json.loads(E_NUMS.read_text())
    for k in keys:
        d = d[k]
    return d


def sq_of_published_sqrt(s: str) -> Fraction:
    """Square a published cross term of the forms 'a*sqrt(7)', 'a*sqrt(7)/b', '0'.
    Plain string parsing, no SymPy."""
    if s == "0":
        return Fraction(0)
    num, _, den = s.partition("/")
    coef, rad = num.split("*sqrt(")
    rad = rad.rstrip(")")
    return Fraction(int(coef)) ** 2 * int(rad) / (Fraction(int(den)) ** 2 if den else 1)


def n_right(t: Fraction, period: int) -> int:
    """Right-continuous event count on (0, t]: events at period, 2*period, ...
    (contract 'right' convention; no event at t=0). Computed HERE, outside Math IR."""
    return math.floor(t / period) if t > 0 else 0


def P0_expr():
    # G(t) = 100 + 4 t + 20 n10 + 35 n20   [kgCO2e, synthetic]
    return add(R(100), mul(R(4), S("t")), mul(R(20), S("n10")), mul(R(35), S("n20")))


def P1_expr():
    # P1: renovation at 20 (A_R = 50). sigma=1 substitute (the year-20 AC+pipe
    # charges are replaced), sigma=0 additional.
    return add(P0_expr(), mul(R(50), S("nR")),
               neg(mul(S("sigma"), mul(R(55), S("nR")))))


def P2_expr():
    # P2: operational 4/yr on [0,10), 3/yr after; m = min(t,10), q = max(t-10,0)
    return add(R(100), mul(R(4), S("m")), mul(R(3), S("q")),
               mul(R(20), S("n10")), mul(R(35), S("n20")))


def build_pilots():
    cases, exp = [], []
    for t in ["0", "1", "9.999999", "10", "10.000001", "20", "20.000001", "30", "40", "60"]:
        tf = Fraction(t)
        cid = "P0_right_t" + t.replace(".", "p")
        subs = {"t": tf, "n10": n_right(tf, 10), "n20": n_right(tf, 20)}
        cases.append(case(cid, P0_expr(), subs, "kgCO2e"))
        exp.append(dict(case_id=cid, identity="100+4t+20*n10+35*n20 (counts supplied)",
                        expected=point(A_POINTS, "P0", "right", t), source=A_POINTS,
                        key=f"rows[case=P0,convention=right,t={t}].value",
                        note="n10,n20 computed outside IR (floor); IR checks arithmetic only"))
    for name, sigma in (("P1-substitute", 1), ("P1-additional", 0)):
        for t in ["20", "60"]:
            tf = Fraction(t)
            cid = f"P1_{'sub' if sigma else 'add'}_right_t{t}"
            subs = {"t": tf, "n10": n_right(tf, 10), "n20": n_right(tf, 20),
                    "nR": 1 if tf >= 20 else 0, "sigma": sigma}
            cases.append(case(cid, P1_expr(), subs, "kgCO2e"))
            exp.append(dict(case_id=cid,
                            identity="P0 + 50*nR - sigma*55*nR (counts, policy supplied)",
                            expected=point(A_POINTS, name, "right", t), source=A_POINTS,
                            key=f"rows[case={name},convention=right,t={t}].value",
                            note="nR, sigma, n10, n20 supplied; event logic not checked"))
    for t in ["20", "30", "60"]:
        tf = Fraction(t)
        cid = "P2_right_t" + t
        subs = {"m": min(tf, 10), "q": max(tf - 10, 0),
                "n10": n_right(tf, 10), "n20": n_right(tf, 20)}
        cases.append(case(cid, P2_expr(), subs, "kgCO2e"))
        exp.append(dict(case_id=cid, identity="100+4m+3q+20*n10+35*n20 (m,q,counts supplied)",
                        expected=point(E_POINTS, "P2", "right", t), source=E_POINTS,
                        key=f"rows[case=P2,convention=right,t={t}].value",
                        note="m=min(t,10), q=max(t-10,0) and counts computed outside IR; "
                             "also equals routes/A_waveform/results/points.json P2 right"))
        assert point(A_POINTS, "P2", "right", t) == exp[-1]["expected"]
    return cases, exp


def build_route_e():
    cases, exp = [], []
    P = mul(pw(S("I0"), 2), S("R"))           # I0^2 R
    base = {"I0": 2, "R": 3}

    def add_case(cid, expr, subs, unit, identity, expected, src, key, note=""):
        cases.append(case(cid, expr, subs, unit))
        exp.append(dict(case_id=cid, identity=identity, expected=Fraction(expected),
                        source=src, key=key, note=note))

    add_case("E_power_W", P, base, "1", "I0^2*R = 12 W", enum("basics", "P_W"),
             E_NUMS, "basics.P_W")
    add_case("E_joule_5s_J", mul(P, S("t")), {**base, "t": 5}, "1",
             "I0^2*R*t at t=5 = 60 J", enum("basics", "E_5s_J"), E_NUMS, "basics.E_5s_J")
    add_case("E_kappa_5s_kg", mul(S("k"), P, S("t")), {**base, "t": 5, "k": Fraction(1, 3)},
             "kgCO2e", "kappa*I0^2*R*t = 20 kg",
             Fraction(enum("basics", "kappa_kg_per_J")) * Fraction(enum("basics", "E_5s_J")),
             E_NUMS, "basics.kappa_kg_per_J * basics.E_5s_J",
             "expected is the product of two published values (no single published '20')")
    add_case("E_ac_5periods_J", mul(pw(S("Irms"), 2), S("R"), S("t")),
             {"Irms": 2, "R": 3, "t": 5}, "1",
             "Irms^2*R*t at t=5 (sin terms cancel at whole periods)",
             enum("basics", "ac_5periods_J"), E_NUMS, "basics.ac_5periods_J",
             "the trigonometric cancellation sin(2wt+2phi)-sin(2phi)=0 at t in Z is "
             "NOT checked: sin is outside Math IR 0.1")
    add_case("E_thermal_E60_J", mul(P, S("t")), {**base, "t": 60}, "1",
             "I0^2*R*60 = 720 J", enum("thermal", "E60_J"), E_NUMS, "thermal.E60_J")
    for label, key in (("rho1", "equal_aligned"), ("rho1_2", "widths_w_4w"),
                       ("rho1_3", "widths_w_9w"), ("rho0", "walsh_pair")):
        tab = enum("D_pass1", "cross_table", key)
        add_case("E_cross_sq_" + label,
                 mul(R(4), S("A1"), S("A2"), pw(S("rho"), 2)),
                 {"A1": 20, "A2": 35, "rho": Fraction(tab["rho"])}, "1",
                 "(2*sqrt(A1*A2)*rho)^2 = 4*A1*A2*rho^2  [kg^2]",
                 sq_of_published_sqrt(tab["cross_kg"]), E_NUMS,
                 f"D_pass1.cross_table.{key}.cross_kg squared",
                 "sqrt not in IR: only the SQUARED identity is checked; sign/branch "
                 "and the L2 inner product giving rho are not checked; unit label '1' "
                 "because kg^2 is not an allowed unit")
    k1, k2 = Fraction(1, 3), Fraction(1, 4)
    for t in ("20", "60"):
        tf = Fraction(t)
        m, q = min(tf, 10), max(tf - 10, 0)
        add_case(f"HE4_convert_then_integrate_t{t}",
                 add(mul(S("k1"), P, S("m")), mul(S("k2"), P, S("q"))),
                 {**base, "k1": k1, "k2": k2, "m": m, "q": q}, "kgCO2e",
                 "k1*P*min(t,10) + k2*P*max(t-10,0)",
                 enum("HE4", t, "convert_then_integrate"), E_NUMS,
                 f"HE4.{t}.convert_then_integrate", "m,q computed outside IR")
        add_case(f"HE4_meter_current_t{t}", mul(S("k2"), P, S("t")),
                 {**base, "k2": k2, "t": tf}, "kgCO2e", "kappa(t)*P*t (kappa(t)=1/4, t>=10)",
                 enum("HE4", t, "meter_then_convert_current"), E_NUMS,
                 f"HE4.{t}.meter_then_convert_current",
                 "branch kappa(t)=1/4 selected outside IR (no comparator)")
        add_case(f"HE4_meter_initial_t{t}", mul(S("k1"), P, S("t")),
                 {**base, "k1": k1, "t": tf}, "kgCO2e", "(1/3)*P*t",
                 enum("HE4", t, "meter_then_convert_initial"), E_NUMS,
                 f"HE4.{t}.meter_then_convert_initial")
    w = Fraction(enum("D_pass1", "w"))
    add_case("E_walsh_window_t20", add(mul(S("k"), P, S("w")), R(20), R(35)),
             {**base, "k": Fraction(1, 3), "w": w}, "kgCO2e",
             "kappa*I0^2*R*w + 20 + 35 (cross terms = 0 assumed)",
             enum("D_pass1", "walsh_window_t20_kg"), E_NUMS, "D_pass1.walsh_window_t20_kg",
             "orthogonality / zero-mean of the Walsh pulses (the vanishing cross "
             "integrals) is NOT checked; only the remaining arithmetic is")
    add_case("E_walsh_P0_after_60w",
             add(R(100), mul(S("k"), P, add(R(60), S("w"))), mul(R(20), S("n10")),
                 mul(R(35), S("n20"))),
             {**base, "k": Fraction(1, 3), "w": w, "n10": 6, "n20": 3}, "kgCO2e",
             "100 + kappa*P*(60+w) + 20*6 + 35*3",
             enum("D_pass1", "walsh_P0_G_after_60_plus_w"), E_NUMS,
             "D_pass1.walsh_P0_G_after_60_plus_w", "counts supplied; cross terms assumed 0")
    return cases, exp


def build_negative():
    """Deliberately WRONG expected values. Math7 itself has no 'expected' field, so
    the portable pipeline is expected to PASS; route F's comparator must FAIL."""
    P = mul(pw(S("I0"), 2), S("R"))
    w = Fraction(enum("D_pass1", "w"))
    good = Fraction(enum("D_pass1", "walsh_window_t20_kg"))
    wrong = good - Fraction(1, 25)              # 1375/25 = 55 (drops the DC part)
    subs = {"I0": 2, "R": 3, "k": Fraction(1, 3), "w": w}
    val = add(mul(S("k"), P, S("w")), R(20), R(35))
    cases = [case("NEG_walsh_value_wrong_expected", val, subs, "kgCO2e"),
             case("NEG_walsh_residual_vs_wrong", add(val, neg(R(wrong))), subs, "1")]
    exp = [dict(case_id=cases[0]["case_id"], identity="walsh window, WRONG expected 55",
                expected=wrong, source=E_NUMS, key="D_pass1.walsh_window_t20_kg minus 1/25",
                note="NEGATIVE CONTROL: deliberately wrong"),
           dict(case_id=cases[1]["case_id"], identity="value - 55 must be 0 (it is 1/25)",
                expected=Fraction(0), source=E_NUMS,
                key="residual against deliberately wrong value",
                note="NEGATIVE CONTROL: residual form")]
    return cases, exp


def write(name, cases, exp):
    assert 1 <= len(cases) <= 20
    (F / "inputs").mkdir(exist_ok=True)
    (F / "inputs" / f"{name}.json").write_text(
        json.dumps({"schema": "math-ir/0.1", "cases": cases}, indent=1) + "\n")
    side = [{**e, "expected": str(e["expected"]), "source": rel(e["source"]),
             "source_sha256": sha(e["source"]), "source_git_blob_at_HEAD": git_blob(e["source"])}
            for e in exp]
    (F / "inputs" / f"{name}.expected.json").write_text(json.dumps(side, indent=1) + "\n")
    print(f"wrote inputs/{name}.json ({len(cases)} cases)")


if __name__ == "__main__":
    write("wlc_pilots_p0_p1_p2", *build_pilots())
    write("wlc_route_e_identities", *build_route_e())
    write("negative_wrong_expected", *build_negative())
