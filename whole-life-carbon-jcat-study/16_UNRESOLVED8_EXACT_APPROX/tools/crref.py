"""A variant of the reference evaluator whose non-integer powers and log10 are CORRECTLY ROUNDED
(exact value computed in 100-digit decimal arithmetic, then rounded once to the nearest double). Everything
else is the reference evaluator unchanged. Use:  with crref.correctly_rounded(): X.evaluate(...)"""
import contextlib
import decimal
import math
from decimal import Decimal as D

import excel_ref as X

_CTX = decimal.Context(prec=100, Emax=10 ** 6, Emin=-10 ** 6)


def cr_pow(a, b):
    with decimal.localcontext(_CTX):
        v = (D(b) * D(a).ln()).exp()
    try:
        r = float(v)
    except OverflowError:
        return X.NUM
    return X.NUM if not math.isfinite(r) else r


def cr_log10(x):
    with decimal.localcontext(_CTX):
        return float(D(x).log10())


@contextlib.contextmanager
def correctly_rounded():
    orig_arith, orig_log = X.arith, X.FUNCS["LOG10"]

    def arith(op, a, b):
        if op == "^":
            a2, b2 = X.to_num(a), X.to_num(b)
            if isinstance(a2, float) and isinstance(b2, float) and a2 > 0 and b2 != int(b2):
                return cr_pow(a2, b2)
        return orig_arith(op, a, b)

    def f_log10(args, ctx):
        x = X.to_num(X.val(args[0], ctx))
        if isinstance(x, X.Err):
            return x
        return X.NUM if x <= 0 else cr_log10(x)

    X.arith = arith
    X.FUNCS["LOG10"] = f_log10
    try:
        yield
    finally:
        X.arith = orig_arith
        X.FUNCS["LOG10"] = orig_log
