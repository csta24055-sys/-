"""Method A for concatenation: adversarial synthetic inputs vs the reference evaluator (Excel semantics)."""
import os, sys, math, random, struct, time
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import synth
import exact8 as E8
from store import Err

rng = random.Random(20261114)


def rand_double(r):
    k = r.random()
    if k < 0.15:
        return struct.unpack("<d", struct.pack("<Q", r.getrandbits(64) & 0x7FEFFFFFFFFFFFFF | (r.getrandbits(1) << 63)))[0]
    if k < 0.3:
        return r.choice([-1, 1]) * r.randint(0, 10 ** r.randint(1, 17)) / 10 ** r.randint(0, 12)
    if k < 0.45:
        e = r.randint(-12, 20)
        return float("%.*g" % (r.randint(1, 17), r.uniform(1, 10) * 10.0 ** e)) * r.choice([-1, 1])
    if k < 0.55:
        return r.uniform(-1e6, 1e6)
    if k < 0.65:
        # decade boundaries and their neighbours
        e = r.randint(-320, 308)
        x = float("1e%d" % e)
        return r.choice([x, math.nextafter(x, 0), math.nextafter(x, math.inf), -x])
    if k < 0.75:
        # values whose 15-digit rounding is a tie or near one
        m = r.randint(10 ** 14, 10 ** 15 - 1)
        e = r.randint(-20, 25)
        x = float("%d5e%d" % (m, e - 15))
        return r.choice([x, math.nextafter(x, 0), math.nextafter(x, math.inf)])
    if k < 0.85:
        return float(r.randint(-10 ** 16, 10 ** 16))
    return r.choice([0.0, -0.0, 1.0, -1.0, 0.1, 0.2 + 0.1, 1e15, 1e15 - 1, 1e15 + 2, 999999999999999.0, 99999999999999.9,
                     0.0001, 0.00001, 0.000123456789012345, 1e-5, 9.99999999999999e-5, 5e-324, 2.2250738585072014e-308,
                     1.7976931348623157e308, 123456789012345678.0, 0.5, 2.5, 1e21, 1e22, 1e23, 1e100, 1e-100, 4.35, 1.005])


TEXTS = ["", "a", "ABC", "x-1", " 2.5 ", "合計", "コンクリート", "１２３", "TRUE", "~*?", "Straße", "İstanbul", "😀a", "\t\n",
         "a" * 40, "-", "0", "1E+05"]


def rand_value(r):
    k = r.random()
    if k < 0.45:
        return rand_double(r)
    if k < 0.75:
        if r.random() < 0.5:
            return r.choice(TEXTS)
        return "".join(chr(r.choice([r.randint(32, 126), r.randint(0x3040, 0x30FF), r.randint(0x4E00, 0x9FFF), r.randint(0xA0, 0x2FFF)]))
                       for _ in range(r.randint(0, 12)))
    if k < 0.85:
        return None
    if k < 0.93:
        return r.random() < 0.5
    return Err(r.choice([7, 2, 3, 4, 5, 6]))


def main(n=3000):
    A = [rand_value(rng) for _ in range(n)]
    B = [rand_value(rng) for _ in range(n)]
    for formula in ('A1&"-"&B1', "A1&B1"):
        t0 = time.time()
        res = synth.run(formula, {1: A, 2: B}, n, 5, E8.Exact8All, mode8="A")
        print(formula, "n=%d bad=%d missing=%d steps=%d compile=%.2fs run=%.2fs ref=%.2fs table=%.1fMB" % (
            res["n"], len(res["bad"]), res["missing"], res["steps"], res["compile_s"], res["run_s"], res["ref_s"], res["table_bytes"] / 1e6))
        for b in res["bad"][:10]:
            i = b[0] - 1
            print("   row", b[0], repr(A[i])[:40], repr(B[i])[:40], "got", repr(b[1])[:60], "want", repr(b[2])[:60])


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3000)
