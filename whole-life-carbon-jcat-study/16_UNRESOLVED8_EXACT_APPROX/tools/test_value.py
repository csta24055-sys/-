"""VALUE(LEFT(x, n)) method A vs the reference evaluator: numbers (general-format text), numeric-looking
texts from a grammar (signs, digit groups, decimal point, exponents, percent, white space, full-width and
other Unicode digits), logicals, blanks, errors."""
import os, sys, random
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import synth, exact8 as E8
import test_concat as TC
from store import Err

r = random.Random(20261117)
ATOMS = list("0123456789") * 3 + ["+", "-", ".", ",", "e", "E", "%", " ", "　", "\t", "０", "５", "．", "，", "－", "＋", "％",
                                   "٣", "१", "x", "Ｅ", "_", "1,000", "1,0", "e+", "e-", ".5", "5."]


def text_value():
    k = r.random()
    if k < 0.7:
        return "".join(r.choice(ATOMS) for _ in range(r.randint(0, 9)))
    if k < 0.85:
        return r.choice(["1e-320", "2.5e-324", "1.5e-323", "4.9e-324", "2.2250738585072011e-308", "123456789012345e-330",
                         "1e308", "1.7976931348623157e308", "1.7976931348623159e308", "9007199254740993", "0.1e-1", "1,234,567.5e-3",
                         "１，２３４．５", "  -.5e+2 %", "1e-22", "1e22", "1e-23", "123e-25", "7e-300", "3e-291", "5e-310", " 12 ", "1e99", "9e-9", "1e23", "2e23", "8e23", "5e22", "1e-5", ".1e9", "1.e5", "+.5", "-0", "0%", "12%",
                         "1 %", "% 1", "1%%", "%", "", " ", "1,234", "12,3", "1,23", "1e", "e1", "1e+", "--1", "1.2.3", "１２３４", "TRUE"])
    return "%.*g" % (r.randint(1, 6), r.uniform(-1e5, 1e5))


def value():
    k = r.random()
    if k < 0.55:
        return text_value()
    if k < 0.85:
        return TC.rand_double(r)
    if k < 0.9:
        return None
    if k < 0.95:
        return r.random() < 0.5
    return Err(r.choice([7, 2]))


def main(n=6000):
    X = [value() for _ in range(n)]
    tot = {}
    for L in (4, 1, 2, 6, 15):
        res = synth.run("VALUE(LEFT(A1,%d))" % L, {1: X}, n, 5, E8.Exact8Value, mode8="A")
        tot[L] = (len(res["bad"]), res["missing"])
        print("VALUE(LEFT(A1,%d))" % L, "n=%d bad=%d missing=%d steps=%d compile=%.1fs run=%.2fs table=%.1fMB" % (
            n, len(res["bad"]), res["missing"], res["steps"], res["compile_s"], res["run_s"], res["table_bytes"] / 1e6))
        for b in res["bad"][:8]:
            print("    ", repr(X[b[0] - 1])[:40], "got", repr(b[1])[:40], "want", repr(b[2])[:40])
    return tot


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 6000)
