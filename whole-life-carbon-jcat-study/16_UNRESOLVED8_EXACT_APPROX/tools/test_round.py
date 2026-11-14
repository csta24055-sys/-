"""ROUND / ROUNDDOWN / ROUNDUP: method A (exact reproduction of the reference rounding model) and method B (the
previous improved compilation) vs the reference evaluator, adversarial inputs (ties of the decimal grid,
their binary neighbours, 15-digit boundaries, every decade, negative values, huge and tiny magnitudes)."""
import os, sys, math, random, time
from decimal import Decimal
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import synth, exact8 as E8
import test_concat as TC

r = random.Random(20261115)


def inputs(n, d):
    out = []
    for i in range(n):
        k = r.random()
        if k < 0.35:                          # decimal ties at the rounding digit, and their neighbours
            m = r.randint(0, 10 ** r.randint(1, 12))
            x = float("%d5e-%d" % (m, d + 1))
            out.append(r.choice([x, math.nextafter(x, 0), math.nextafter(x, math.inf), -x]))
        elif k < 0.5:                         # values whose 15-digit text is a tie
            m = r.randint(10 ** 13, 10 ** 14)
            x = float("%d5e%d" % (m, r.randint(-20, 10)))
            out.append(r.choice([x, -x, math.nextafter(x, 0)]))
        elif k < 0.6:
            out.append(r.uniform(-1e4, 1e4))
        elif k < 0.75:                        # exact ties of the 15-digit text (16 significant digits ending in 5)
            while True:
                j = r.randint(1, 8)
                x = (2 * r.randint(1, 10 ** 15) + 1) / 2 ** j
                t = Decimal(x).normalize().as_tuple()
                if len(t.digits) == 16 and t.digits[-1] == 5:
                    break
            out.append(r.choice([x, -x]))
        else:
            out.append(TC.rand_double(r))
    return out


def main(n=5000):
    tot = {}
    for fn in ("ROUND", "ROUNDDOWN", "ROUNDUP"):
        for d in (0, 1, 2, 3, 6):
            X = inputs(n, d)
            X = [x for x in X if math.isfinite(x)]
            f = "%s(A1,%d)" % (fn, d)
            for mode in ("A", "B"):
                res = synth.run(f, {1: X}, len(X), 5, E8.Exact8All, mode8=mode)
                c = dict(n=0, ok=0, bad=0, miss_in=0, miss_out=0, ref_undef=0)
                ex = []
                for x, g, w in zip(X, res["got"], res["ref"]):
                    if isinstance(w, str) and w.startswith("EXC"):
                        c["ref_undef"] += 1                      # the reference model itself is undefined here
                        continue
                    c["n"] += 1
                    inside = abs(x) < 9.999999999999999e36      # stated domain of method A (|x| < 10^37)
                    if g == "<missing>":
                        c["miss_in" if inside else "miss_out"] += 1
                        if inside and len(ex) < 3:
                            ex.append((x, g, w))
                    elif synth.same(g, w)[0]:
                        c["ok"] += 1
                    else:
                        c["bad"] += 1
                        if len(ex) < 3:
                            ex.append((x, g, w))
                tot[(fn, d, mode)] = c
                print(f, mode, c, "steps=%d run=%.2fs" % (res["steps"], res["run_s"]))
                for e in ex:
                    print("    ", repr(e[0]), e[1], e[2])
    return tot


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 5000)
