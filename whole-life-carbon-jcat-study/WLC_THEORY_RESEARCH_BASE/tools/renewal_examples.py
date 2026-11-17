#!/usr/bin/env python3
"""Renewal-process examples for the WLC theory research base (document 15).

Pure python3, deterministic (fixed seeds), no third-party packages. All parameters are ILLUSTRATIVE
assumptions (mean life 15 years, Weibull shapes, a hypothetical efficiency-decline rate, ...). They are
not measured data and say nothing about real equipment or real buildings.

What it computes (sections of data/renewal_examples.json):
  fixed_cycle        counts of a fixed cycle c under the concept-model event rule (the existing atom kernel
                     h(T; tau, 0, tau) of 10_TRANSFORM_STUDY/research_code/tstudy/rampstep.py, imported
                     read-only) against the closed forms ceil(T(1-eps)/c)-1 and floor(t/c)
  renewal_function   m_F(t) = E[N_F(t)] = sum_k F^{*k}(t) for Weibull / exponential / lognormal lifetimes,
                     by solving the renewal equation m = F + F * dm (Riemann-Stieltjes midpoint scheme),
                     with convergence in the step h, the exact exponential case, the asymptote
                     t/mu + (sigma^2 - mu^2)/(2 mu^2), and the variance of N_F(t)
  blackwell          expected replacements per year m_F(y) - m_F(y-1) against 1/mu
  units              expected replacement emissions of n_u = 1, 10, 1000 independent units (closed form
                     n_u * u * m_F) and a seeded Monte Carlo check (single realisations and group statistics)
  fixed_vs_renewal   "replace every 15 years" (fixed cycle) vs "mean life 15 years" (renewal) vs
                     "aggregate the expected curve every 15 years"
  limit_beta         Weibull shape beta -> infinity: m_F(t) -> floor(t/c) away from the knots kc
  age_functions      E[g(a(t))] for the age a(t) since the last renewal: efficiency decline g(a) = exp(b a)
                     and a decaying refrigerant stock g(a) = q^a; key renewal theorem limit; Jensen gap
  first_vs_renewal   first-replacement distribution F(t) vs the renewal function m_F(t)
  discrete_renewal   integer (whole-year) lifetimes: u_n = sum_k f_k u_{n-k}, aperiodic vs lattice support

Run (from anywhere):
  WLCSTUDIO_OFFLINE=1 python3 -B tools/renewal_examples.py [--out PATH] [--quick]
The default output is data/renewal_examples.json next to this tools/ folder.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True  # never write __pycache__ (also run with python3 -B)

import argparse
import importlib.util
import json
import math
import operator
import os
import platform
import random

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)                       # WLC_THEORY_RESEARCH_BASE
STUDY = os.path.dirname(BASE)                      # whole-life-carbon-jcat-study
RAMPSTEP = os.path.join(STUDY, "10_TRANSFORM_STUDY", "research_code", "tstudy", "rampstep.py")

VERSION = "1.0"
MU = 15.0            # illustrative mean life [years]
TMAX = 130           # same horizon as the concept model's annual table (H = 130)
SEED = 20261117
EPS_MODEL = 1e-9     # epsilon of the concept-model event rule


# ----------------------------------------------------------------------------------------------
# distributions
# ----------------------------------------------------------------------------------------------
class Weibull:
    def __init__(self, beta: float, mean: float = MU):
        self.beta = beta
        self.eta = mean / math.gamma(1.0 + 1.0 / beta)
        self.mean = mean
        g1 = math.gamma(1.0 + 1.0 / beta)
        g2 = math.gamma(1.0 + 2.0 / beta)
        self.var = self.eta ** 2 * (g2 - g1 * g1)
        self.name = f"weibull_beta{beta:g}"

    def cdf(self, x: float) -> float:
        if x <= 0.0:
            return 0.0
        return -math.expm1(-((x / self.eta) ** self.beta))

    def sf(self, x: float) -> float:
        if x <= 0.0:
            return 1.0
        return math.exp(-((x / self.eta) ** self.beta))

    def cumhaz(self, x: float) -> float:
        return 0.0 if x <= 0.0 else (x / self.eta) ** self.beta

    def hazard(self, x: float) -> float:
        if x <= 0.0:
            return 0.0 if self.beta > 1 else (1.0 / self.eta if self.beta == 1 else math.inf)
        return self.beta / self.eta * (x / self.eta) ** (self.beta - 1.0)

    def sample(self, rng: random.Random) -> float:
        u = rng.random()                                # in [0, 1)
        return self.eta * (-math.log1p(-u)) ** (1.0 / self.beta)

    def params(self) -> dict:
        return {"family": "weibull", "beta": self.beta, "eta": self.eta, "mean": self.mean,
                "sd": math.sqrt(self.var), "cv": math.sqrt(self.var) / self.mean}


class LogNormal:
    def __init__(self, cv: float, mean: float = MU):
        self.s2 = math.log(1.0 + cv * cv)
        self.s = math.sqrt(self.s2)
        self.m = math.log(mean) - self.s2 / 2.0
        self.mean = mean
        self.var = (cv * mean) ** 2
        self.name = f"lognormal_cv{cv:.3f}"
        self.cv = cv

    def cdf(self, x: float) -> float:
        if x <= 0.0:
            return 0.0
        return 0.5 * math.erfc(-(math.log(x) - self.m) / (self.s * math.sqrt(2.0)))

    def sf(self, x: float) -> float:
        if x <= 0.0:
            return 1.0
        return 0.5 * math.erfc((math.log(x) - self.m) / (self.s * math.sqrt(2.0)))

    def cumhaz(self, x: float) -> float:
        sf = self.sf(x)
        return -math.log(sf) if sf > 0 else math.inf

    def hazard(self, x: float) -> float:
        if x <= 0.0:
            return 0.0
        z = (math.log(x) - self.m) / self.s
        pdf = math.exp(-0.5 * z * z) / (x * self.s * math.sqrt(2.0 * math.pi))
        sf = self.sf(x)
        return pdf / sf if sf > 0 else math.inf

    def sample(self, rng: random.Random) -> float:
        return math.exp(self.m + self.s * rng.gauss(0.0, 1.0))

    def params(self) -> dict:
        return {"family": "lognormal", "mu_ln": self.m, "sigma_ln": self.s, "mean": self.mean,
                "sd": math.sqrt(self.var), "cv": self.cv}


# ----------------------------------------------------------------------------------------------
# renewal equation solver
# ----------------------------------------------------------------------------------------------
def solve_renewal(dist, spy: int, tmax: int = TMAX):
    """m(t_i), t_i = i/spy, from m(t) = F(t) + int_0^t F(t - x) dm(x).

    Riemann-Stieltjes midpoint scheme (the 'RS method'): the integral over (t_{j-1}, t_j] is
    F(t_i - t_{j-1/2}) * (m_j - m_{j-1}). Solving for m_i gives
        m_i = (F_i + sum_{j=1}^{i-1} Fh[i-j] dm_j - Fh[0] m_{i-1}) / (1 - Fh[0]),  Fh[k] = F((k+1/2)/spy).
    Returns (m, dm) as lists of length n+1 (dm[0] = 0).
    """
    n = tmax * spy
    h = 1.0 / spy
    F = [dist.cdf(i * h) for i in range(n + 1)]
    Fh = [dist.cdf((k + 0.5) * h) for k in range(n + 1)]
    m = [0.0] * (n + 1)
    dm = [0.0] * (n + 1)
    denom = 1.0 - Fh[0]
    mul = operator.mul
    for i in range(1, n + 1):
        # sum_{j=1}^{i-1} Fh[i-j] * dm[j]
        s = sum(map(mul, dm[1:i], Fh[i - 1:0:-1])) if i > 1 else 0.0
        mi = (F[i] + s - Fh[0] * m[i - 1]) / denom
        m[i] = mi
        dm[i] = mi - m[i - 1]
    return m, dm


def second_moment(m, dm, spy: int):
    """E[N(t)^2] = m(t) + 2 int_0^t m(t - s) dm(s) on the grid (midpoint values of m)."""
    n = len(m) - 1
    mh = [0.5 * (m[k] + m[k + 1]) for k in range(n)]   # m((k+1/2)h)
    mul = operator.mul
    out = [0.0] * (n + 1)
    for i in range(1, n + 1):
        s = sum(map(mul, dm[1:i + 1], mh[i - 1::-1])) if i >= 1 else 0.0
        out[i] = m[i] + 2.0 * s
    return out


def age_expectation(dist, g, dm, spy: int, idx):
    """E[g(a(t))] = g(t) Fbar(t) + int_0^t g(t-s) Fbar(t-s) dm(s) at grid indices idx."""
    h = 1.0 / spy
    out = {}
    nmax = max(idx)
    G = [g((k + 0.5) * h) * dist.sf((k + 0.5) * h) for k in range(nmax + 1)]
    mul = operator.mul
    for i in idx:
        s = sum(map(mul, dm[1:i + 1], G[i - 1::-1])) if i >= 1 else 0.0
        t = i * h
        out[i] = g(t) * dist.sf(t) + s
    return out


def key_renewal_limit(dist, g, xmax: float = 600.0, steps: int = 600000):
    """(1/mu) int_0^inf g(x) Fbar(x) dx by composite Simpson on [0, xmax]."""
    h = xmax / steps
    acc = g(0.0) * dist.sf(0.0) + g(xmax) * dist.sf(xmax)
    for k in range(1, steps):
        x = k * h
        acc += (4.0 if k % 2 else 2.0) * g(x) * dist.sf(x)
    return acc * h / 3.0 / dist.mean


# ----------------------------------------------------------------------------------------------
# fixed cycle under the concept-model rule (existing kernel, read-only import)
# ----------------------------------------------------------------------------------------------
def load_rampstep():
    if not os.path.exists(RAMPSTEP):
        return None
    spec = importlib.util.spec_from_file_location("rampstep_readonly", RAMPSTEP)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod          # dataclasses need the module registered
    spec.loader.exec_module(mod)          # sys.dont_write_bytecode is set: no __pycache__
    return mod


def fixed_cycle_section(rs, c: float = MU, H: float = float(TMAX)):
    out = {"c": c, "H": H, "rule": "event at tau counted iff tau < T*(1-eps) (atom kernel h(T; tau, 0, tau))",
           "kernel_source": "10_TRANSFORM_STUDY/research_code/tstudy/rampstep.py (h, periodic_times; read-only)"
           if rs else "rampstep.py not found: closed form only"}
    taus = rs.periodic_times(H, c) if rs else [n * c for n in range(1, 100) if n * c < H * (1 - EPS_MODEL)]
    out["knots"] = taus

    def count_kernel(T):
        if rs:
            return sum(rs.h(T, tau, 0.0, tau) for tau in taus)
        return sum(1.0 for tau in taus if tau < T * (1 - EPS_MODEL))

    def count_closed(T):
        # ceil(T(1-eps)/c) - 1, the real-number rule; also floor for comparison
        return math.ceil(T * (1.0 - EPS_MODEL) / c) - 1

    grid = [k / 4.0 for k in range(1, int(H * 4) + 1)]
    special = []
    for tau in taus:
        for d in (-1e-6, -1e-9 * tau, 0.0, 0.5e-9 * tau, 1e-9 * tau, 2e-9 * tau, 1e-7, 1e-6):
            T = tau + d
            if 0 < T <= H:
                special.append(T)
    mism = 0
    rows = []
    for T in sorted(set(grid + special)):
        a = count_kernel(T)
        b = count_closed(T)
        if a != b:
            mism += 1
        if T in special:
            rows.append({"T": T, "count_kernel": a, "count_closed_ceil": b,
                         "floor_T_over_c": math.floor(T / c)})
    out["n_compared"] = len(set(grid + special))
    out["mismatch_kernel_vs_closed"] = mism
    out["around_knots"] = rows[:40]
    # time average of the sawtooth N_c(T) - T/c over (0, H]: exact for the floor form
    # int_0^H floor(s/c) ds = c * sum_{k<K} k + (H - K c) K, K = floor(H/c)
    K = math.floor(H / c)
    integral = c * K * (K - 1) / 2.0 + (H - K * c) * K
    out["mean_of_floor_minus_t_over_c_on_0_H"] = integral / H - H / (2.0 * c)
    out["note"] = ("count_kernel equals ceil(T(1-eps)/c)-1 except possibly in bands of relative width ~1e-9 at "
                   "the knots (switching point sw(tau) of lemma L-2); floor(T/c) is the right-continuous renewal "
                   "convention N(t) = #{n: tau_n <= t}. At T = kc exactly the concept model does not count the "
                   "k-th event (0 at T = 15 for c = 15).")
    return out


# ----------------------------------------------------------------------------------------------
# Monte Carlo
# ----------------------------------------------------------------------------------------------
def simulate(dist, n_units: int, seed: int, tmax: int = TMAX, age_times=()):
    """Independent unit histories on [0, tmax]: installation at t = 0, renewal epochs tau_n = X_1+...+X_n.
    Returns annual counts per unit (year y holds tau in (y-1, y]) and the age at each age_time."""
    rng = random.Random(seed)
    counts = []
    ages = {t: [] for t in age_times}
    for _ in range(n_units):
        a = [0] * (tmax + 1)
        t = 0.0
        last = 0.0
        epochs = []
        while True:
            t += dist.sample(rng)
            if t > tmax:
                break
            epochs.append(t)
            a[max(1, math.ceil(t))] += 1
        counts.append(a)
        if age_times:
            j = 0
            for at in sorted(age_times):
                while j < len(epochs) and epochs[j] <= at:
                    last = epochs[j]
                    j += 1
                ages[at].append(at - (last if j > 0 else 0.0))
    return counts, ages


def group_stats(counts, group: int, years):
    """Cumulative counts per group of `group` units at the given years: mean and sd across groups (per unit)."""
    ngroups = len(counts) // group
    res = {}
    for y in years:
        vals = []
        for g in range(ngroups):
            tot = 0
            for u in counts[g * group:(g + 1) * group]:
                tot += sum(u[1:y + 1])
            vals.append(tot / group)
        mean = sum(vals) / ngroups
        var = sum((v - mean) ** 2 for v in vals) / (ngroups - 1) if ngroups > 1 else float("nan")
        res[y] = {"mean_per_unit": mean, "sd_per_unit_across_groups": math.sqrt(var) if ngroups > 1 else None,
                  "n_groups": ngroups}
    return res


# ----------------------------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------------------------
def r6(x):
    return None if x is None else float(f"{x:.6g}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(BASE, "data", "renewal_examples.json"))
    ap.add_argument("--quick", action="store_true", help="coarser grids and fewer Monte Carlo units")
    args = ap.parse_args(argv)

    spy_main = 20 if args.quick else 40                 # steps per year: h = 0.05 or 0.025
    pool = 4000 if args.quick else 20000
    years = list(range(0, TMAX + 1))
    out = {"meta": {
        "tool": "WLC_THEORY_RESEARCH_BASE/tools/renewal_examples.py", "version": VERSION,
        "python": platform.python_version(), "seed": SEED, "quick": args.quick,
        "mean_life_years": MU, "horizon_years": TMAX, "grid_steps_per_year": spy_main,
        "monte_carlo_units_per_distribution": pool,
        "status": "ILLUSTRATIVE assumptions only (fictional parameters). Numerical results are [F] "
                  "(floating point); the theorems they illustrate are [L] (standard renewal theory); "
                  "their application to buildings is [H].",
        "replacement_emission_per_event": "u = 1 (normalised; multiply by the emission of one replacement)",
    }}

    rs = load_rampstep()
    out["fixed_cycle"] = fixed_cycle_section(rs)

    dists = [Weibull(1.0), Weibull(2.0), Weibull(3.5), Weibull(6.0), Weibull(10.0), Weibull(20.0),
             Weibull(50.0), LogNormal(Weibull(3.5).params()["cv"])]
    sol = {}
    rf = {}
    for d in dists:
        m, dm = solve_renewal(d, spy_main)
        sol[d.name] = (d, m, dm)
        mu, var = d.mean, d.var
        const = (var - mu * mu) / (2 * mu * mu)
        idx = [y * spy_main for y in years]
        m2 = second_moment(m, dm, spy_main)
        rf[d.name] = {
            "params": {k: r6(v) for k, v in d.params().items() if not isinstance(v, str)} | {"family": d.params()["family"]},
            "asymptote_constant_(sigma2-mu2)/(2mu2)": r6(const),
            "t": years,
            "F": [r6(d.cdf(y)) for y in years],
            "m": [r6(m[i]) for i in idx],
            "annual_increment_m(y)-m(y-1)": [None] + [r6(m[idx[k]] - m[idx[k - 1]]) for k in range(1, len(idx))],
            "m_minus_asymptote": [r6(m[i] - (i / spy_main) / mu - const) for i in idx],
            "var_N": [r6(m2[i] - m[i] ** 2) for i in idx],
            "var_N_asymptotic_t_sigma2_over_mu3": [r6(y * var / mu ** 3) for y in years],
        }
    out["renewal_function"] = rf

    # convergence in h and the exact exponential case
    conv = {}
    for d in (Weibull(1.0), Weibull(3.5), Weibull(10.0), Weibull(50.0)):
        ms = {}
        for spy in ((10, 20, 40) if not args.quick else (10, 20)):
            m, _ = solve_renewal(d, spy)
            ms[spy] = [m[y * spy] for y in years]
        keys = sorted(ms)
        diffs = []
        for a, b in zip(keys, keys[1:]):
            diffs.append({"h_coarse": 1 / a, "h_fine": 1 / b,
                          "max_abs_diff_yearly": r6(max(abs(x - z) for x, z in zip(ms[a], ms[b])))})
        entry = {"differences": diffs}
        if len(diffs) >= 2 and diffs[1]["max_abs_diff_yearly"]:
            entry["observed_order"] = r6(math.log2(diffs[0]["max_abs_diff_yearly"] / diffs[1]["max_abs_diff_yearly"]))
        if d.beta == 1.0:
            entry["exponential_max_abs_error_vs_t_over_mu"] = {
                str(1 / spy): r6(max(abs(ms[spy][k] - years[k] / d.mean) for k in range(len(years)))) for spy in keys}
        conv[d.name] = entry
    out["convergence"] = conv

    # Blackwell: expected replacements per year vs 1/mu
    bw = {"1_over_mu": r6(1 / MU), "years": [5, 10, 15, 20, 30, 45, 60, 90, 120, 130], "by_distribution": {}}
    for name, (d, m, dm) in sol.items():
        inc = {y: m[y * spy_main] - m[(y - 1) * spy_main] for y in range(1, TMAX + 1)}
        row = {str(y): r6(inc[y]) for y in bw["years"]}
        win = {}
        for lo, hi in ((1, 30), (31, 60), (61, 90), (91, 130)):
            win[f"{lo}-{hi}"] = r6(max(abs(inc[y] - 1 / MU) for y in range(lo, hi + 1)) * MU)
        bw["by_distribution"][name] = {"annual_expected_replacements": row,
                                       "max_relative_deviation_from_1_over_mu_by_window": win}
    out["blackwell"] = bw

    # fixed cycle vs renewal vs 15-year aggregation
    c = MU
    marks = [14.5, 15.0, 15.000001, 15.5, 29.999, 30.0, 30.000001, 45.0, 60.0, 60.000001, 75.0, 90.0, 105.0, 120.0, 130.0]
    fv = {"c": c, "rows": []}
    for T in marks:
        row = {"T": T,
               "fixed_cycle_existing_rule": math.ceil(T * (1 - EPS_MODEL) / c) - 1,
               "fixed_cycle_right_continuous_floor": math.floor(T / c)}
        for name in ("weibull_beta1", "weibull_beta3.5", "weibull_beta10", "weibull_beta50"):
            d, m, dm = sol[name]
            x = T * spy_main
            i0 = min(int(math.floor(x)), len(m) - 2)
            w = x - i0
            row[f"m_{name}"] = r6(m[i0] * (1 - w) + m[i0 + 1] * w)
        fv["rows"].append(row)
    # aggregation of the expected curve of the Weibull beta=3.5 renewal into 15-year bins
    d, m, dm = sol["weibull_beta3.5"]
    bins = []
    for k in range(1, int(TMAX // c) + 2):
        lo, hi = (k - 1) * c, min(k * c, TMAX)
        if lo >= TMAX:
            break
        inc = m[int(round(hi * spy_main))] - m[int(round(lo * spy_main))]
        bins.append({"bin": f"({lo:g},{hi:g}]", "expected_replacements_in_bin": r6(inc),
                     "fixed_cycle_events_in_bin_(right-closed)": 1 if hi == k * c else 0})
    fv["aggregation_15y_of_weibull_beta3.5"] = bins
    out["fixed_vs_renewal"] = fv

    # beta -> infinity
    lim = {"c_equals_mean": MU, "rows": []}
    for name in ("weibull_beta10", "weibull_beta20", "weibull_beta50"):
        d, m, dm = sol[name]
        eta = d.eta
        devs = {}
        for wwin in (1.0, 2.0, 3.0):
            mx = 0.0
            for i in range(1, len(m)):
                t = i / spy_main
                if t > TMAX:
                    break
                k = round(t / MU)
                if abs(t - k * MU) <= wwin:
                    continue
                mx = max(mx, abs(m[i] - math.floor(t / MU)))
            devs[f"outside_pm{wwin:g}y_of_knots"] = r6(mx)
        mids = {str(t): r6(m[int(t * spy_main)]) for t in (7.5, 22.5, 37.5, 52.5, 67.5, 97.5, 127.5)}
        lim["rows"].append({"dist": name, "eta": r6(eta), "sd": r6(math.sqrt(d.var)),
                            "max_abs_m_minus_floor_t_over_c": devs, "m_at_midpoints_between_knots": mids})
    out["limit_beta"] = lim

    # Monte Carlo
    mc = {"pool_units": pool, "seed_base": SEED, "groups": [1, 10, 1000], "by_distribution": {}}
    sel_years = [10, 15, 20, 30, 45, 60, 90, 120, 130]
    age_times = (15, 30, 60, 90, 130)
    for k, name in enumerate(("weibull_beta3.5", "weibull_beta1", "weibull_beta50")):
        d, m, dm = sol[name]
        counts, ages = simulate(d, pool, SEED + k, TMAX, age_times)
        entry = {"closed_form_m": {str(y): r6(m[y * spy_main]) for y in sel_years}}
        gs = {}
        m2 = second_moment(m, dm, spy_main)
        for g in mc["groups"]:
            if pool // g < 2:
                continue
            st = group_stats(counts, g, sel_years)
            rows = {}
            for y in sel_years:
                th_mean = m[y * spy_main]
                th_sd = math.sqrt(max(0.0, (m2[y * spy_main] - th_mean ** 2) / g))
                s = st[y]
                se = s["sd_per_unit_across_groups"] / math.sqrt(s["n_groups"])
                rows[str(y)] = {"mc_mean_per_unit": r6(s["mean_per_unit"]),
                                "mc_sd_per_unit_across_groups": r6(s["sd_per_unit_across_groups"]),
                                "theory_sd_per_unit_sqrt(VarN/n_u)": r6(th_sd),
                                "z_mean_minus_theory_over_se": r6((s["mean_per_unit"] - th_mean) / se) if se > 0 else None,
                                "n_groups": s["n_groups"]}
            gs[str(g)] = rows
        entry["group_statistics"] = gs
        # single realisations of annual counts for n_u = 1, 10, 1000 (first group) and the expectation
        if name == "weibull_beta3.5":
            real = {}
            for g in (1, 10, 1000):
                ser = [0] * (TMAX + 1)
                for u in counts[:g]:
                    for y in range(1, TMAX + 1):
                        ser[y] += u[y]
                exp = [g * (m[y * spy_main] - m[(y - 1) * spy_main]) for y in range(1, TMAX + 1)]
                dev = [abs(ser[y] - exp[y - 1]) for y in range(1, TMAX + 1)]
                cum = 0
                cdev = 0.0
                for y in range(1, TMAX + 1):
                    cum += ser[y]
                    cdev = max(cdev, abs(cum - g * m[y * spy_main]) / g)
                real[str(g)] = {"annual_counts_y1_to_y130": ser[1:],
                                "expected_annual_y1_to_y130": [r6(x) for x in exp],
                                "max_abs_annual_deviation": r6(max(dev)),
                                "max_abs_cumulative_deviation_per_unit": r6(cdev)}
            entry["single_realisations"] = real
        # ages: Monte Carlo vs renewal-equation expectation
        ag = {}
        b = 0.01
        q = 0.9
        for at in age_times:
            vals = ages[at]
            g1 = sum(math.exp(b * a) for a in vals) / len(vals)
            g2 = sum(q ** a for a in vals) / len(vals)
            ag[str(at)] = {"mc_E_exp_b_age": r6(g1), "mc_E_q_pow_age": r6(g2), "mc_mean_age": r6(sum(vals) / len(vals))}
        entry["ages_mc"] = ag
        mc["by_distribution"][name] = entry
    out["monte_carlo"] = mc

    # age functions (efficiency decline, decaying refrigerant stock)
    b = 0.01   # hypothetical efficiency-decline rate [1/yr] (illustrative)
    q = 0.9    # hypothetical annual retention of a non-refilled stock (illustrative)
    afs = {"b_per_year": b, "q_per_year": q,
           "g_efficiency": "exp(b * a): electricity multiplier 1/eta(a) * eta_0 for eta(a) = eta_0 exp(-b a)",
           "g_stock": "q ** a: remaining fraction of a stock charged at the last renewal", "by_distribution": {}}
    for name in ("weibull_beta3.5", "weibull_beta1", "weibull_beta50"):
        d, m, dm = sol[name]
        idx = [t * spy_main for t in (0, 5, 10, 15, 20, 30, 45, 60, 90, 130)]
        e1 = age_expectation(d, lambda a: math.exp(b * a), dm, spy_main, idx)
        e2 = age_expectation(d, lambda a: q ** a, dm, spy_main, idx)
        e0 = age_expectation(d, lambda a: 1.0, dm, spy_main, idx)
        ea = age_expectation(d, lambda a: a, dm, spy_main, idx)
        lim1 = key_renewal_limit(d, lambda a: math.exp(b * a))
        lim2 = key_renewal_limit(d, lambda a: q ** a)
        lima = key_renewal_limit(d, lambda a: a)
        afs["by_distribution"][name] = {
            "t": [i // spy_main for i in idx],
            "E_exp_b_age": [r6(e1[i]) for i in idx],
            "E_q_pow_age": [r6(e2[i]) for i in idx],
            "q_pow_E_age_(Jensen_comparison)": [r6(q ** ea[i]) for i in idx],
            "E_age": [r6(ea[i]) for i in idx],
            "check_E_1_minus_1_max_abs": r6(max(abs(e0[i] - 1.0) for i in idx)),
            "key_renewal_limit_exp_b_age": r6(lim1),
            "key_renewal_limit_q_pow_age": r6(lim2),
            "key_renewal_limit_age_=E[X^2]/(2mu)": r6(lima),
            "E[X^2]/(2mu)": r6((d.var + d.mean ** 2) / (2 * d.mean)),
        }
    # fixed-cycle sawtooth equivalents (deterministic age t - c floor(t/c)), time averages over one cycle
    c = MU
    afs["fixed_cycle"] = {
        "t": [0, 5, 10, 15, 20, 30, 45, 60, 90, 130],
        "age_right_continuous": [t - c * math.floor(t / c) for t in (0, 5, 10, 15, 20, 30, 45, 60, 90, 130)],
        "exp_b_age": [r6(math.exp(b * (t - c * math.floor(t / c)))) for t in (0, 5, 10, 15, 20, 30, 45, 60, 90, 130)],
        "cycle_average_exp_b_age_(e^{bc}-1)/(bc)": r6(math.expm1(b * c) / (b * c)),
        "cycle_average_q_pow_age_(q^c-1)/(c ln q)": r6((q ** c - 1) / (c * math.log(q))),
    }
    out["age_functions"] = afs

    # first replacement vs renewal
    fr = {"t": [10, 15, 20, 30, 45, 60, 90, 130], "by_distribution": {}}
    for name in ("weibull_beta1", "weibull_beta3.5", "weibull_beta10"):
        d, m, dm = sol[name]
        fr["by_distribution"][name] = {
            "F_first_replacement_by_t": [r6(d.cdf(t)) for t in fr["t"]],
            "m_renewal_function": [r6(m[t * spy_main]) for t in fr["t"]],
            "m_minus_F_(second_and_later)": [r6(m[t * spy_main] - d.cdf(t)) for t in fr["t"]],
            "Lambda_cumulative_hazard_(minimal_repair_NHPP_mean)": [r6(d.cumhaz(t)) for t in fr["t"]]}
    out["first_vs_renewal"] = fr

    # discrete (whole-year) lifetimes: X_int = ceil(X); renewal sequence u_n
    dr = {"note": "u_n = P(a renewal in year n) for integer lifetimes; u_0 = 1, u_n = sum_k f_k u_{n-k}"}
    d35 = Weibull(3.5)
    f = [0.0] + [d35.cdf(k) - d35.cdf(k - 1) for k in range(1, 400)]
    mean_int = sum(k * f[k] for k in range(len(f)))
    u = [1.0] + [0.0] * TMAX
    for n in range(1, TMAX + 1):
        u[n] = sum(f[k] * u[n - k] for k in range(1, n + 1))
    dr["aperiodic_ceil_weibull_beta3.5"] = {"mean_integer_life": r6(mean_int), "1_over_mean": r6(1 / mean_int),
                                           "u_n_selected": {str(n): r6(u[n]) for n in (10, 15, 16, 20, 30, 60, 90, 130)},
                                           "max_abs_u_minus_1_over_mean_n_100_130": r6(max(abs(u[n] - 1 / mean_int) for n in range(100, TMAX + 1)))}
    # lattice: lifetimes 15 or 30 years (gcd 15), probability 1/2 each
    fl = [0.0] * 31
    fl[15] = 0.5
    fl[30] = 0.5
    ul = [1.0] + [0.0] * TMAX
    for n in range(1, TMAX + 1):
        ul[n] = sum(fl[k] * ul[n - k] for k in range(1, min(n, 30) + 1))
    dr["lattice_15_or_30"] = {"mean": 22.5, "span_d": 15,
                              "u_n_at_multiples_of_15": {str(n): r6(ul[n]) for n in range(15, TMAX + 1, 15)},
                              "u_n_elsewhere_max": r6(max(ul[n] for n in range(1, TMAX + 1) if n % 15)),
                              "lattice_limit_d_over_mu": r6(15 / 22.5)}
    out["discrete_renewal"] = dr

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print("wrote", args.out)
    return out


if __name__ == "__main__":
    main()
