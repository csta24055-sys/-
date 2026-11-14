"""Stage 3: synthetic adversarial tests of the text rules added in exact12 (no original data).

Generic formulas on a synthetic sheet, compared EXACTLY with the reference evaluator (Excel semantics):
  IF with text branches, IFERROR with text operands, SUBSTITUTE of a cell / of a concatenation / of a VLOOKUP result,
  with keys and range values of every type (numbers incl. tricky doubles, texts with 0..k occurrences of the old text
  at the start / end / adjacent, Japanese and astral characters, logicals, blanks, errors), texts near and beyond
  the 255-slot limit (beyond: the result must be <missing>, never wrong).
Usage: python3 -B test12.py [n]
"""
import os
import random
import sys
import time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import synth                                # noqa: E402
import exact12 as E12                       # noqa: E402
from store import Err                       # noqa: E402
from test_concat import rand_double         # noqa: E402

rng = random.Random(20261114 + 12)
OLDS = ["ab", "x/", "全/", "Q"]


def rand_text(r, old):
    parts = []
    for _ in range(r.randint(0, 6)):
        k = r.random()
        if k < 0.35:
            parts.append(old)
        elif k < 0.5:
            parts.append(old * r.randint(2, 3))                       # adjacent occurrences
        elif k < 0.6:
            parts.append(old[:-1] if len(old) > 1 else "")            # an incomplete occurrence
        else:
            parts.append("".join(chr(r.choice([r.randint(32, 126), r.randint(0x3040, 0x30FF), r.randint(0x4E00, 0x9FFF), 0x1F600]))
                                 for _ in range(r.randint(0, 6))))
    s = "".join(parts)
    if r.random() < 0.03:
        s = (old + "z") * r.randint(60, 90)                         # long texts around the 255-slot limit
    return s


def rand_value(r, old):
    k = r.random()
    if k < 0.55:
        return rand_text(r, old)
    if k < 0.75:
        return rand_double(r)
    if k < 0.85:
        return None
    if k < 0.93:
        return r.random() < 0.5
    return Err(r.choice([7, 2, 3, 4, 5, 6]))


def main(n=1500):
    results = []
    for old in OLDS:
        nk = 40
        keys = ["k%d" % i for i in range(nk)]
        colC = keys + [None] * (n - nk)
        colD = [rand_value(rng, old) for _ in range(nk)] + [None] * (n - nk)
        colE = [rand_text(rng, old) for _ in range(nk)] + [None] * (n - nk)
        A = [rng.choice(keys + ["", "nokey", 1.0, None, True]) if rng.random() < 0.9 else Err(7) for _ in range(n)]
        B = [rand_value(rng, old) for _ in range(n)]
        cols = {1: A, 2: B, 3: colC, 4: colD, 5: colE}
        formulas = [
            'SUBSTITUTE(B1,"%s","")' % old,
            'SUBSTITUTE(B1,"%s","-+")' % old,
            'SUBSTITUTE("<"&B1&">","%s","")' % old,
            'IFERROR(SUBSTITUTE(VLOOKUP(A1,$C$1:$E$%d,2,),"%s",""),"")' % (nk, old),
            'IF(A1="","",IFERROR(SUBSTITUTE(VLOOKUP(A1,$C$1:$E$%d,3,),"%s",""),""))' % (nk, old),
            'IF(A1="k1","p["&B1&"]","q["&B1&"]")',
            'IF(B1="","",B1&"%s")' % old,
            'IFERROR("v"&B1,"err")',
        ]
        for f in formulas:
            t0 = time.time()
            try:
                res = synth.run(f, cols, n, 9, E12.Exact12, mode8="A")
            except Exception as ex:
                results.append((f, "EXC", repr(ex)[:200]))
                print(f, "EXC", repr(ex)[:200], flush=True)
                continue
            wrong = [b for b in res["bad"] if b[1] != "<missing>"]
            beyond = sum(1 for i in range(n) if res["got"][i] == "<missing>")
            results.append((f, res["n"], len(wrong), res["missing"]))
            print("%-75s n=%d wrong=%d missing=%d steps=%d run=%.1fs ref=%.1fs" % (f, res["n"], len(wrong), res["missing"], res["steps"],
                                                                                   res["run_s"], res["ref_s"]), flush=True)
            for b in wrong[:5]:
                i = b[0] - 1
                print("    row", b[0], "A", repr(A[i])[:30], "B", repr(B[i])[:50], "got", repr(b[1])[:60], "want", repr(b[2])[:60])
            # every missing must be a text beyond the slot limit (domain), never anything else
            for b in [b for b in res["bad"] if b[1] == "<missing>"][:3]:
                i = b[0] - 1
                print("    missing row", b[0], "want length", len(b[2]) if isinstance(b[2], str) else b[2])
    return results


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1500)
