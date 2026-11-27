"""(g) Step 1 of the restart list, for the state family F4: the refrigerant units B1-02 / B1-03 / B1-04 computed
DIRECTLY FROM THE SCENARIO INPUTS with this study's own code (five_families.py), without the earlier unified system,
and compared with the frozen reference calculation on all 1,293 pairs.

Construction (05_families):
  G   : charge >= 0, GWP >= 0, annual leak rate in [0,1]  (else the device is skipped and counted, never zero-filled)
  F3  : events tau = explicit change years (t > 0) or n * service life, counted iff tau < T(1-eps); cell of an event
        k(tau) = max(1, ceil(tau(1-eps))) - 1;  year weight w_k(T) = clip(T - k, 0, 1)
  F4  : stock at the start of cell k, closed form per segment: m_k = m0 (1 - lambda)^(k - r(k)) (no top-up) or m0,
        where r(k) is the first cell after the last reset (a reset happens at the end of the event's year)
  B1-02 = sum_k m_k lambda GWP w_k(T)                          (state-amplitude continuous kernel)
  B1-03 = sum_events m_before loss GWP, m_before = m_k (1 - lambda w_k(T)) for the first event of the year, m0 after
          (atom + gated cell)
  B1-04 = m_end(T) (1 - recovery) GWP                          (terminal state)
Usage: python3 -B tools/independent_f4_refrigerant.py <foundation_checkout> <out.json>
"""
import json
import math
import os
import sys
from fractions import Fraction

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import five_families as ff  # noqa: E402

REL = 1e-9


def ok_rate(x):
    return x is not None and 0.0 <= x <= 1.0


def nonneg(x):
    return x is not None and math.isfinite(x) and x >= 0.0


def events(dev, T):
    if dev.change_years is not None:
        return sorted(float(t) for t in dev.change_years if t > 0 and t < T * (1.0 - ff.EPS))
    c = dev.service_life
    if c is None or not math.isfinite(c) or c <= 0:
        return []
    return _periodic(c, T)


def _periodic(c, T):
    out, n = [], 1
    while n * c < T * (1.0 - ff.EPS):
        out.append(n * c)
        n += 1
    return out


def cell_of(tau):
    return max(1, math.ceil(tau * (1.0 - ff.EPS))) - 1


def device_units(dev, T):
    """(B1-02, B1-03 or None, B1-04 or None, skipped flags) for one device, exact."""
    g = ff.Guard()
    if not (g.check(nonneg(dev.charge_mass_kg), "charge") and g.check(nonneg(dev.gwp), "gwp") and g.check(ok_rate(dev.annual_leak_rate), "leak")):
        return None
    m0, lam, gwp = Fraction(dev.charge_mass_kg), Fraction(dev.annual_leak_rate), Fraction(dev.gwp)
    ev = events(dev, T)
    ncell = math.ceil(T)
    resets = {}
    for t in ev:
        resets.setdefault(cell_of(t), []).append(t)
    A = Fraction(1) if dev.top_up else (1 - lam)
    seg_start = 0
    b102, b103_terms, m_end = Fraction(0), [], None
    for k in range(ncell):
        m_k = ff.f4_closed(A, 0, m0, k - seg_start)                    # F4 closed form inside the segment
        w = ff.year_weight(k, T)                                        # F3 year cell
        b102 += m_k * lam * gwp * w
        m_after = m_k if dev.top_up else m_k * (1 - lam * w)
        if k in resets:
            for j, t in enumerate(resets[k]):
                b103_terms.append(m_after if j == 0 else m0)
            m_after = m0
            seg_start = k + 1
        m_end = m_after
    if m_end is None:
        m_end = m0
    b103 = None
    if ok_rate(dev.replacement_loss_rate):
        b103 = sum((mb * Fraction(dev.replacement_loss_rate) * gwp for mb in b103_terms), Fraction(0))
    b104 = None
    if ok_rate(dev.end_of_life_recovery_rate):
        b104 = m_end * (1 - Fraction(dev.end_of_life_recovery_rate)) * gwp
    return b102, b103, b104


def same(a, b):
    if b == 0.0:
        return abs(a) <= 1e-300
    return abs(a - b) <= REL * abs(b)


def main(fnd, outp):
    code = os.path.join(fnd, "whole-life-carbon-jcat-study", "17_WHOLE_BUILDING_TIME_THEORY", "code")
    sys.path.insert(0, code)
    import canon  # noqa: F401,E402  (only to set the research_code path)
    from checks import sets_unified  # noqa: E402
    from tstudy import baseline, scenarios  # noqa: E402
    baseline.assert_frozen()
    baseline.load()
    res = {}
    tot = dict(pairs=0, values=0, bad=0, band_pairs=0, band_bad=0)
    ex = []
    for name, cases in sets_unified.build(sets_unified.ALL_SETS).items():
        r = dict(pairs=0, values=0, bad=0, band_pairs=0, band_bad=0)
        check_domain = name not in sets_unified.OUTSIDE_DOMAIN
        for label, scn, periods in cases:
            for T in periods:
                cur = scenarios.with_period(scn, T)
                if check_domain and scenarios.valid_domain(cur):
                    continue
                ref = baseline.run_reference(cur)
                s2 = s3 = s4 = Fraction(0)
                for dev in cur.refrigerants:
                    v = device_units(dev, T)
                    if v is None:
                        continue
                    s2 += v[0]
                    s3 += v[1] or 0
                    s4 += v[2] or 0
                # pairs whose explicit integer change years put T inside the band (K, K/(1-eps)] are reported apart
                band = any(dev.change_years and any(float(t) == math.floor(t) and t < T <= t / (1 - ff.EPS) * (1 + 4e-16)
                                                    for t in dev.change_years) for dev in cur.refrigerants)
                r["pairs"] += 1
                r["band_pairs"] += band
                for u, v in (("B1-02", s2), ("B1-03", s3), ("B1-04", s4)):
                    r["values"] += 1
                    good = same(float(v), ref[u]["value"])
                    if not good:
                        r["band_bad" if band else "bad"] += 1
                        if len(ex) < 20:
                            ex.append((name, label, T, u, float(v), ref[u]["value"]))
        res[name] = r
        for k in tot:
            tot[k] += r[k]
        print(name, r, flush=True)
    res["TOTAL"] = tot
    res["examples"] = ex
    json.dump(res, open(outp, "w"), indent=1, default=str)
    print("TOTAL", tot)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
