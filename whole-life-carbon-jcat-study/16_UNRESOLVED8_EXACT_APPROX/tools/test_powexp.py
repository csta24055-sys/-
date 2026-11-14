"""x^a method A over many exponents (including |a| >> 1) against the correctly rounded truth (100-digit
decimal): counts of equal / wrong / missing / refused exponents."""
import os, sys, math, random
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import warnings; warnings.simplefilter("ignore")
from decimal import Decimal as D
import decimal
import synth, exact8 as E8, compile2 as K

decimal.getcontext().prec = 100


def truth(x, a):
    v = (D(a) * D(x).ln()).exp()
    try:
        r = float(v)
    except OverflowError:
        return None
    return r if math.isfinite(r) else None


def main(n=1500):
    r = random.Random(11)
    out = {}
    for a in (0.05, -0.06, 0.37, 0.95, -0.99, 1.5, 2.5, -2.5, 3.5, 6.5, 7.3, 10.5, -10.5, 15.25, 20.5, -20.5, 30.5, 45.5, 60.5, -60.5, 100.5, -100.5, 300.5):
        xs = [10 ** r.uniform(-300, 300) for _ in range(n // 2)] + [r.uniform(0.01, 100) for _ in range(n // 2)]
        xs += [5e-324, 2.2250738585072014e-308, 1.7976931348623157e308, 1.0, 2.0, 0.5]
        try:
            res = synth.run("POWER(A1,%r)" % a, {1: xs}, len(xs), 2, E8.Exact8Final, mode8="A")
        except K.Unsupported as e:
            out[a] = "refused: %s" % e
            print(a, out[a], flush=True)
            continue
        c = dict(n=0, equal=0, wrong=0, missing=0, num_error=0)
        for x, g in zip(xs, res["got"]):
            t = truth(x, a)
            if t is None or t == 0.0 or abs(t) < 2.0 ** -1022:      # overflow / underflow: reference error or subnormal
                continue
            c["n"] += 1
            if g == "<missing>":
                c["missing"] += 1
            elif isinstance(g, float) and g == t:
                c["equal"] += 1
            else:
                c["wrong"] += 1
        out[a] = c
        print(a, c, "steps", res["steps"], flush=True)
    return out


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1500)
