"""Inputs that DISCRIMINATE rounding models of ROUND(x, d) (generic values, no workbook data):
  M15  : the reference model, round the 15-significant-digit decimal text of x half up (method A);
  BIN  : round the exact binary value of x half up (no 15-digit step);
  HU   : method B, floor(|x| 10^d + 1/2 + half a unit of the 15th digit).
Writes an .xlsx with the inputs, the formulas ROUND / ROUNDDOWN / ROUNDUP and the model values, so that the
behaviour of a spreadsheet application can be read off directly.
Usage: round_probe.py <out.xlsx> <out.json>"""
import os, sys, json, math, random
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import warnings; warnings.simplefilter("ignore")
from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN, ROUND_UP, localcontext
import synth, exact8 as E8


def m15(x, d, mode):
    q = Decimal(1).scaleb(-d)
    rm = {"round": ROUND_HALF_UP, "down": ROUND_DOWN, "up": ROUND_UP}[mode]
    with localcontext() as c:
        c.prec = 60
        return float(Decimal("%.15g" % x).quantize(q, rounding=rm))


def binr(x, d, mode):
    q = Decimal(1).scaleb(-d)
    rm = {"round": ROUND_HALF_UP, "down": ROUND_DOWN, "up": ROUND_UP}[mode]
    with localcontext() as c:
        c.prec = 400
        return float(Decimal(x).quantize(q, rounding=rm))


def candidates(r, n):
    out = []
    for _ in range(n):
        d = r.choice([0, 1, 2, 3])
        m = r.randint(0, 10 ** r.randint(1, 9))
        tie = Decimal(m) + Decimal("0.5")
        x = float(tie.scaleb(-d))
        for k in range(-3, 4):
            y = x
            for _ in range(abs(k)):
                y = math.nextafter(y, math.inf if k > 0 else 0.0)
            out.append((y, d))
            out.append((-y, d))
        # 15-digit ties: numbers whose %.15g text ends in 5 at the rounding digit with more digits below
        xx = float("%d5e-%d" % (r.randint(10 ** 12, 10 ** 13), 14 - r.randint(0, 6)))
        out.append((xx, r.choice([0, 1, 2, 3])))
    return out


def ties15(r, n):
    """Doubles whose EXACT value has 16 significant digits ending in 5: an exact tie of the 15-digit text
    (the reference model resolves it half-to-even, a half-up 15-digit step would not)."""
    out = []
    while len(out) < n:
        j = r.randint(1, 8)
        k = r.randint(1, 10 ** 15)
        x = (2 * k + 1) / 2 ** j
        dx = Decimal(x)
        digits = dx.normalize().as_tuple()
        if len(digits.digits) == 16 and digits.digits[-1] == 5:
            out.append((x, r.choice([0, 1, 2, 3])))
            out.append((-x, r.choice([0, 1, 2, 3])))
    return out


def main(xlsx, js):
    r = random.Random(20261119)
    cands = candidates(r, 4000) + ties15(r, 3000)
    rows = []
    for x, d in cands:
        for mode in ("round", "down", "up"):
            a, b = m15(x, d, mode), binr(x, d, mode)
            rows.append((x, d, mode, a, b))
    # method B on the same inputs (compiled once per (d, mode))
    by = {}
    for x, d, mode, a, b in rows:
        by.setdefault((d, mode), []).append(x)
    hu = {}
    for (d, mode), xs in by.items():
        f = {"round": "ROUND", "down": "ROUNDDOWN", "up": "ROUNDUP"}[mode]
        res = synth.run("%s(A1,%d)" % (f, d), {1: xs}, len(xs), 5, E8.Exact8Final, mode8="B")
        for x, g in zip(xs, res["got"]):
            hu[(x, d, mode)] = g
    seen, out = set(), []
    for x, d, mode, a, b in rows:
        if (x, d, mode) in seen:
            continue
        seen.add((x, d, mode))
        h = hu.get((x, d, mode))
        if a != b or a != h:
            out.append(dict(x=repr(x), d=d, mode=mode, M15=a, BIN=b, HU=h))
    # keep every row where method A (M15) and method B (HU) differ, then fill up to 400 rows
    diff = [o for o in out if o["M15"] != o["HU"]]
    rest = [o for o in out if o["M15"] == o["HU"]]
    print("A != B rows", len(diff), "M15 != BIN rows", sum(1 for o in out if o["M15"] != o["BIN"]))
    out = diff[:250] + rest[:400 - min(250, len(diff))]
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "round_probe"
    ws.append(["x (exact double)", "digits", "function", "application result", "M15 (15-digit text, half up)", "BIN (binary value)",
               "HU (method B)", "= M15 ?", "= BIN ?"])
    for i, o in enumerate(out, start=2):
        f = {"round": "ROUND", "down": "ROUNDDOWN", "up": "ROUNDUP"}[o["mode"]]
        ws.append([float(o["x"]), o["d"], f, "=%s(A%d,B%d)" % (f, i, i), o["M15"], o["BIN"], o["HU"], "=D%d=E%d" % (i, i), "=D%d=F%d" % (i, i)])
    ws2 = wb.create_sheet("summary")
    ws2.append(["rows", len(out)])
    ws2.append(["application = M15", "=COUNTIF(round_probe!H2:H%d,TRUE)" % (len(out) + 1)])
    ws2.append(["application = BIN", "=COUNTIF(round_probe!I2:I%d,TRUE)" % (len(out) + 1)])
    wb.save(xlsx)
    json.dump(out, open(js, "w"), indent=0)
    print("rows written", len(out), "of candidates", len(cands) * 3,
          "HU==M15", sum(1 for o in out if o["HU"] == o["M15"]), "HU==BIN", sum(1 for o in out if o["HU"] == o["BIN"]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
