"""All synthetic (data-independent) verifications of methods A and B, with generic constants only
(no coefficient or text of the original workbooks). Writes a JSON summary.
Usage: synth_all.py <out.json> [scale]"""
import os, sys, json, math, random, time, resource
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import warnings; warnings.simplefilter("ignore")
from decimal import Decimal as D
import decimal
import synth, exact8 as E8
import test_concat as TC, test_round as TR, test_value as TV

decimal.getcontext().prec = 60
SC = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
OUT = {}


def classify(res, X=None, domain=None):
    c = dict(n=0, ok=0, wrong=0, missing=0, missing_outside=0, ref_undefined=0)
    for i, (g, w) in enumerate(zip(res["got"], res["ref"])):
        if isinstance(w, str) and w.startswith("EXC"):
            c["ref_undefined"] += 1
            continue
        c["n"] += 1
        if g == "<missing>":
            if domain is not None and not domain(i, w):
                c["missing_outside"] += 1
            else:
                c["missing"] += 1
        elif synth.same(g, w)[0]:
            c["ok"] += 1
        else:
            c["wrong"] += 1
    c.update(steps=res["steps"], compile_s=round(res["compile_s"], 3), run_s=round(res["run_s"], 3),
             table_MB=round(res["table_bytes"] / 1e6, 2))
    return c


def concat():
    n = int(20000 * SC)
    A = [TC.rand_value(TC.rng) for _ in range(n)]
    B = [TC.rand_value(TC.rng) for _ in range(n)]
    for f in ('A1&"-"&B1', "A1&B1"):
        for mode in ("A", "B"):
            res = synth.run(f, {1: A, 2: B}, n, 5, E8.Exact8Final, mode8=mode)
            OUT[("concat", f, mode)] = classify(res)
            print("concat", f, mode, OUT[("concat", f, mode)], flush=True)


def rounding():
    for fn in ("ROUND", "ROUNDDOWN", "ROUNDUP"):
        for d in (0, 1, 2, 3, 6):
            X = [x for x in TR.inputs(int(4000 * SC), d) if math.isfinite(x)]
            for mode in ("A", "B"):
                res = synth.run("%s(A1,%d)" % (fn, d), {1: X}, len(X), 5, E8.Exact8Final, mode8=mode)
                OUT[("round", fn, d, mode)] = classify(res, X, domain=lambda i, w: abs(X[i]) < 9.999999999999999e36)
                print("round", fn, d, mode, OUT[("round", fn, d, mode)], flush=True)


def powlog():
    rng = random.Random(7)
    xs = [10 ** rng.uniform(-300, 300) for _ in range(int(4000 * SC))]
    xs += [rng.uniform(1e3, 1e7) for _ in range(int(4000 * SC))]
    xs += [1 + rng.uniform(-1e-6, 1e-6) for _ in range(int(1000 * SC))]
    xs += [float(2 ** k) for k in range(-1074, 1024, 7)] + [10.0 ** k for k in range(-300, 300, 13)]
    xs += [1.0, 5e-324, 2.2250738585072014e-308, 1.7976931348623157e308, 0.0, -1.0, -0.0]
    for kind, a in (("pow", 0.05), ("pow", -0.06), ("pow", 0.37), ("pow", 2.5), ("pow", -10.5), ("pow", 100.5), ("log", None)):
        f = "POWER(A1,%r)" % a if kind == "pow" else "LOG10(A1)"
        tv = []
        for x in xs:
            if x <= 0:
                tv.append(None)
            else:
                v = (D(a) * D(x).ln()).exp() if kind == "pow" else D(x).log10()
                try:
                    tv.append(float(v))
                except OverflowError:
                    tv.append(None)
        for mode in ("A", "B"):
            res = synth.run(f, {1: xs}, len(xs), 2, E8.Exact8Final, mode8=mode)
            got = res["got"]
            rec = dict(n=len(xs), steps=res["steps"], run_s=round(res["run_s"], 3), table_MB=round(res["table_bytes"] / 1e6, 2),
                       n_pos=0, eq_truth=0, wrong=0, flagged=0, max_rel=0.0, max_abs_near1=0.0, eq_libm=0, libm_correct=0,
                       overflow=0, overflow_num=0, subnormal=0, subnormal_missing=0, subnormal_equal=0)
            for x, g, t, w in zip(xs, got, tv, res["ref"]):
                if t is None:
                    continue
                if not math.isfinite(t):                                  # overflow: the reference gives #NUM!
                    rec["overflow"] += 1
                    rec["overflow_num"] += isinstance(g, E8.K.X.Err)
                    continue
                if t == 0.0 or abs(t) < 2.0 ** -1022:                     # outside the normal range (declared)
                    rec["subnormal"] += 1
                    rec["subnormal_missing"] += g == "<missing>"
                    rec["subnormal_equal"] += isinstance(g, float) and g == t
                    continue
                rec["n_pos"] += 1
                rec["libm_correct"] += w == t
                if g == "<missing>":
                    rec["flagged"] += 1
                    continue
                if isinstance(g, float) and g == t:
                    rec["eq_truth"] += 1
                else:
                    rec["wrong"] += 1
                if isinstance(g, float):
                    rec["max_rel"] = max(rec["max_rel"], abs(g - t) / abs(t))
                    if abs(x - 1) < 1e-5:
                        rec["max_abs_near1"] = max(rec["max_abs_near1"], abs(g - t))
                rec["eq_libm"] += g == w
            OUT[("powlog", kind, a, mode)] = rec
            print("powlog", kind, a, mode, rec, flush=True)


def value():
    n = int(12000 * SC)
    Xv = [TV.value() for _ in range(n)]
    for L in (1, 2, 4, 6, 15):
        for mode in ("A", "B"):
            res = synth.run("VALUE(LEFT(A1,%d))" % L, {1: Xv}, n, 5, E8.Exact8Final, mode8=mode)
            OUT[("value", L, mode)] = classify(res, domain=lambda i, w: not (isinstance(w, float) and math.isinf(w)))
            print("value", L, mode, OUT[("value", L, mode)], flush=True)


def sumif():
    import importlib
    for nobad in ("1", "0"):
        os.environ["NOBAD"] = nobad
        import test_sumif as TS
        TS = importlib.reload(TS)
        TS.SUFFIX = "合計"
        tot = {}
        for k in range(3):
            A = [TS.crit_value() for _ in range(int(80 * SC))]
            Cc = [TS.range_value(A) for _ in range(int(400 * SC))]
            Dd = [TS.r.choice([float(TS.r.randint(1, 99)), TS.r.uniform(0, 10), None, "t", True, 1.0]) for _ in range(int(400 * SC))]
            for f in ('SUMIF(C:C,A1&"合計",D:D)', 'COUNTIF(C:C,A1&"合計")'):
                for mode in ("A", "B"):
                    res = synth.run(f, {1: A, 3: Cc, 4: Dd}, len(A), 6, E8.Exact8Final, mode8=mode)
                    c = classify(res)
                    key = ("sumif", f.split("(")[0], "no_order_bad" if nobad == "1" else "with_order_bad", mode)
                    t = OUT.setdefault(key, dict(n=0, ok=0, wrong=0, missing=0, steps=c["steps"], run_s=0.0, table_MB=c["table_MB"]))
                    for kk in ("n", "ok", "wrong", "missing"):
                        t[kk] += c[kk]
                    t["run_s"] = round(t["run_s"] + c["run_s"], 3)
        for key in [k for k in OUT if k[0] == "sumif"]:
            print(key, OUT[key], flush=True)


if __name__ == "__main__":
    t0 = time.time()
    parts = [globals()[p] for p in sys.argv[3:]] or [concat, rounding, powlog, value, sumif]
    if sys.argv[3:] and os.path.exists(sys.argv[1]):
        old = json.load(open(sys.argv[1], encoding="utf-8"))
        OUT.update({tuple(k.split("|")): v for k, v in old.items() if not any(k.startswith(p.__name__ if p.__name__ != "rounding" else "round") for p in parts)})
    for part in parts:
        part()
        json.dump({"|".join(map(str, k)): v for k, v in OUT.items()}, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
    print("total s", round(time.time() - t0), "peak RSS MB", resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024)
