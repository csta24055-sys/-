"""SUMIF / COUNTIF with a criterion built by concatenation (cell & constant text): method A vs the reference
evaluator on adversarial criteria (operators, wildcards, escapes, case folding, order comparisons) and
criteria-range texts."""
import os, sys, random, time
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import synth, exact8 as E8
from store import Err

r = random.Random(20261116)
SUFFIX = "合計"
BASES_ALL = ["コンクリート", "鉄筋", "型枠", "abc", "ABC", "Abc", "x", "", "a b", "ß", "ẞ", "SS", "ſ", "s", "K", "k", "K", "ı", "i", "I",
         "µ", "μ", "Σ", "σ", "ς", "İ", "1", "1.5", "TRUE", "数", "", "😀", "\U00010400", "\U00010428"]
NOBAD = bool(int(os.environ.get("NOBAD", "0")))       # 1: no character of exact8.ORDER_BAD (Σ, İ, U+F8F3)
BASES = [b for b in BASES_ALL if not (NOBAD and any(ord(c) in E8.ORDER_BAD for c in b))]
WILD = ["*", "?", "~", "~*", "~?", "~~", "*~", "a*", "*c", "?bc", "a?c", "**", "~~*", "~~~*", "*?*", "?", "??"]
OPS = ["", "=", "<>", "<", ">", "<=", ">=", "=<", "><", "==", "<<"]


def rand_text(k):
    t = []
    for _ in range(k):
        x = r.random()
        if x < 0.3:
            t.append(r.choice(BASES))
        elif x < 0.5:
            t.append(r.choice(WILD))
        else:
            c = chr(r.choice([r.randint(0x41, 0x7a), r.randint(0x3041, 0x30f6), r.randint(0x4e00, 0x4e20), r.randint(0x370, 0x3ff)]))
            t.append("x" if NOBAD and ord(c) in E8.ORDER_BAD else c)
    return "".join(t)


def crit_value():
    x = r.random()
    if x < 0.55:
        return r.choice(OPS) + rand_text(r.randint(0, 3))
    if x < 0.7:
        return r.choice(OPS) + r.choice(BASES)
    if x < 0.8:
        return r.choice([1.0, 2.5, -3.0, 1e20, 0.1])
    if x < 0.87:
        return None
    if x < 0.94:
        return r.random() < 0.5
    return Err(r.choice([7, 2]))


def range_value(crits):
    x = r.random()
    if x < 0.35:
        c = r.choice(crits)
        base = c if isinstance(c, str) else ""
        base = base.lstrip("<>=")
        t = "".join(ch for ch in base if r.random() < 0.9) + SUFFIX
        t = t + r.choice(["", "", "", "\n", "\n\n", "\r"])        # a final newline: the reference's regex '$'
        return t.upper() if r.random() < 0.2 else t
    if x < 0.6:
        return rand_text(r.randint(0, 3)) + (SUFFIX if r.random() < 0.6 else "")
    if x < 0.7:
        return float(r.randint(-5, 5))
    if x < 0.8:
        return None
    if x < 0.85:
        return r.random() < 0.5
    if x < 0.9:
        return Err(7)
    return r.choice(BASES) + SUFFIX


def main(n_inst=120, n_cells=600, rounds=3):
    tot = dict(n=0, bad=0, missing=0)
    for k in range(rounds):
        A = [crit_value() for _ in range(n_inst)]
        Cc = [range_value(A) for _ in range(n_cells)]
        Dd = [r.choice([float(r.randint(1, 99)), r.uniform(0, 10), None, "t", True, Err(2) if r.random() < 0.02 else 1.0]) for _ in range(n_cells)]
        for f in ('SUMIF(C:C,A1&"%s",D:D)' % SUFFIX, 'COUNTIF(C:C,A1&"%s")' % SUFFIX):
            res = synth.run(f, {1: A, 3: Cc, 4: Dd}, n_inst, 6, E8.Exact8Text, mode8="A")
            tot["n"] += res["n"]; tot["bad"] += len(res["bad"]); tot["missing"] += res["missing"]
            print(f, "round", k, "n=%d bad=%d missing=%d steps=%d compile=%.1fs run=%.2fs table=%.1fMB" % (
                res["n"], len(res["bad"]), res["missing"], res["steps"], res["compile_s"], res["run_s"], res["table_bytes"] / 1e6))
            nflag = sum(1 for b in res["bad"] if b[1] == "<missing>" and isinstance(A[b[0] - 1], str) and A[b[0] - 1][:1] in "<>" and A[b[0] - 1][:2] != "<>")
            print("      missing with an order operator (stated domain: ORDER_BAD before the deciding position):", nflag)
            for b in res["bad"][:6]:
                print("    crit", repr(A[b[0] - 1]), "got", repr(b[1])[:40], "want", repr(b[2])[:40])
    print("total", tot)


if __name__ == "__main__":
    main(*[int(a) for a in sys.argv[1:]])
