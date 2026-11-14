"""Stage 1: why the density amplitudes are kept as rates (record of the first version, regenerated).

Chapter 11 stores a constant density as the product a*H (a float) and evaluates (a*H) * clip(T/H). Evaluated EXACTLY,
fl(a*H)/H differs from a, so a stage that the reference returns as exactly 0 can come out as a small residual. This
script evaluates the B3 stage of every scenario of dev_edge at its periods both ways (exact rationals) and records the
residuals where the reference is exactly 0.

Usage (from this folder): python3 -B density_check.py <out.json>
"""
import json
import sys
from fractions import Fraction

sys.dont_write_bytecode = True
import canon                                   # noqa: E402
from checks import sets_unified                # noqa: E402
from tstudy import baseline, scenarios         # noqa: E402


def main(outp):
    baseline.assert_frozen()
    baseline.load()
    from synth import population
    out = []
    for label, scn, periods in sets_unified.build(["dev_edge"])["dev_edge"]:
        sysm = canon.make_system(scn, population.BASELINES)
        can = canon.build(sysm)
        H = Fraction(can.H)
        for T in periods:
            cur = scenarios.with_period(scn, T)
            if scenarios.valid_domain(cur):
                continue
            ref = baseline.run_reference(cur)["X-02"]["by_stage"]
            if "B3" not in ref:
                continue
            ts = can.stage_terms("B3")
            rate = sum((t.amp * t.h(T) for t in ts), Fraction(0))
            # the chapter-11 storage: density amplitude rounded as fl(a*H), applied as amp * min(T, H)/H
            prod = Fraction(0)
            for t in ts:
                if t.kind == "density":
                    amp = Fraction(float(t.amp) * float(t.length))       # fl(a * H)
                    prod += amp * min(Fraction(T), Fraction(t.length)) / Fraction(t.length)
                else:
                    prod += t.amp * t.h(T)
            out.append(dict(label=label, T=T, reference=ref["B3"], rate_form=float(rate), product_form=float(prod)))
    zero = [x for x in out if x["reference"] == 0.0]
    res = dict(n=len(out), n_reference_zero=len(zero), rate_form_nonzero_where_reference_zero=sum(1 for x in zero if x["rate_form"] != 0.0),
               product_form_nonzero_where_reference_zero=sum(1 for x in zero if x["product_form"] != 0.0),
               examples=[x for x in zero if x["product_form"] != 0.0][:5])
    json.dump(res, open(outp, "w"), indent=1, ensure_ascii=False)
    print({k: v for k, v in res.items() if k != "examples"}, res["examples"][:2])


if __name__ == "__main__":
    main(sys.argv[1])
