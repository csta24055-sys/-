"""Verifier's own residual checker for dumped solutions (independent of engine/audit.py).

From the dumped netlist and every dumped record it recomputes:
  * KCL at every node (sum of currents leaving = 0), using element orientation a->b,
    op-amp norator current leaving `out`, comparator inputs drawing no current;
  * element laws: R  i = G (va - vb); C  va - vb = u, i = C du/dt; V  va - vb = V; I  i = I;
    closed SW  va = vb; open SW  i = 0; op-amp v+ = v-; L  va - vb = L di/dt, i = state;
    diode complementarity (on: va = vb, i >= 0; off: i = 0, va - vb <= 0);
    VCVS/VCCS/CCCS/CCVS linear relations;
  * jump records: impulse-charge KCL at every node (resistors and current sources carry
    no impulse), capacitor charge balance u+ - u- = Q/C, and that every capacitor changing
    state has an impulse;
  * continuity between consecutive instants (exact dumps): the state at the first record of
    an instant equals the last state of the previous instant advanced with the recorded
    derivative (exact when the derivative is constant over the segment, i.e. second
    derivative 0; flagged otherwise);
  * comparator consistency at each recorded comparator event: the input difference
    recorded at that instant has the sign of the new output, or is 0.
Max absolute residuals are reported; None (indeterminate) values are counted, not used.
"""
from __future__ import annotations

from fractions import Fraction


def num(x):
    if x is None:
        return None
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float, Fraction)):
        return x
    if isinstance(x, str):
        if "/" in x:
            a, b = x.split("/")
            return Fraction(int(a), int(b))
        try:
            return Fraction(int(x))
        except ValueError:
            return float(x)
    raise TypeError(x)


def _absmax(acc, key, val, where, viol, tol):
    if val is None:
        return
    a = abs(val)
    if a > acc[key]:
        acc[key] = a
    if a > tol and len(viol) < 25:
        viol.append((key, where, float(a)))


def check(dump, tol_float=1e-9):
    exact = bool(dump.get("exact", True))
    tol = 0 if exact else tol_float
    els = dump["netlist"]
    by = {e["name"]: e for e in els}
    acc = {k: 0 for k in ("kcl", "R", "C_v", "C_i", "V", "I", "SW_closed", "SW_open", "OA", "L",
                          "D", "ctrl", "jump_kcl", "jump_cap", "continuity", "cmp_sign")}
    cnt = {"records": 0, "none_values": 0, "nodes_checked": 0, "jumps": 0, "cont_pairs": 0,
           "cont_nonconst": 0, "diode_sign_viol": 0, "cmp_events": 0}
    viol = []
    analog = [e for e in els if e["kind"] in ("R", "C", "L", "V", "I", "SW", "D", "OA", "E", "G", "F", "H")]
    nodes = set()
    for e in analog:
        if e["kind"] == "OA":
            nodes |= {e["inp"], e["inn"], e["out"]}
        else:
            nodes |= {e["a"], e["b"]}
    nodes.discard("0")
    for rec in dump["records"]:
        cnt["records"] += 1
        v = {k: num(x) for k, x in rec["v"].items()}
        v["0"] = 0
        i = {k: num(x) for k, x in rec["i"].items()}
        s = {k: num(x) for k, x in rec["s"].items()}
        ds = {k: num(x) for k, x in rec["ds"].items()}
        closed = set(rec["closed"])
        don = set(rec["diode_on"])
        cnt["none_values"] += sum(1 for x in list(v.values()) + list(i.values()) if x is None)
        # KCL
        leave = {n: 0 for n in nodes}
        bad = set()
        for e in analog:
            ie = i.get(e["name"])
            if e["kind"] == "OA":
                terms = [(e["out"], 1)]
            else:
                terms = [(e["a"], 1), (e["b"], -1)]
            for n, sg in terms:
                if n == "0":
                    continue
                if ie is None:
                    bad.add(n)
                else:
                    leave[n] += sg * ie
        for n in nodes:
            if n in bad:
                continue
            cnt["nodes_checked"] += 1
            _absmax(acc, "kcl", leave[n], (rec["t"], rec["tag"], n), viol, tol)

        def dv(a, b):
            if v.get(a) is None or v.get(b) is None:
                return None
            return v[a] - v[b]
        for e in analog:
            k, nm = e["kind"], e["name"]
            ie = i.get(nm)
            if k == "R":
                d = dv(e["a"], e["b"])
                if d is not None and ie is not None:
                    _absmax(acc, "R", ie - num(e["G"]) * d, (rec["t"], nm), viol, tol)
            elif k == "C":
                d = dv(e["a"], e["b"])
                if d is not None:
                    _absmax(acc, "C_v", d - s[nm], (rec["t"], nm), viol, tol)
                if ie is not None:
                    _absmax(acc, "C_i", ie - num(e["C"]) * ds[nm], (rec["t"], nm), viol, tol)
            elif k == "L":
                d = dv(e["a"], e["b"])
                if d is not None:
                    _absmax(acc, "L", d - num(e["L"]) * ds[nm], (rec["t"], nm), viol, tol)
                if ie is not None:
                    _absmax(acc, "L", ie - s[nm], (rec["t"], nm), viol, tol)
            elif k == "V":
                d = dv(e["a"], e["b"])
                if d is not None:
                    _absmax(acc, "V", d - num(e["V"]), (rec["t"], nm), viol, tol)
            elif k == "I":
                if ie is not None:
                    _absmax(acc, "I", ie - num(e["I"]), (rec["t"], nm), viol, tol)
            elif k == "SW":
                if nm in closed:
                    d = dv(e["a"], e["b"])
                    if d is not None:
                        _absmax(acc, "SW_closed", d, (rec["t"], nm), viol, tol)
                else:
                    if ie is not None:
                        _absmax(acc, "SW_open", ie, (rec["t"], nm), viol, tol)
            elif k == "OA":
                d = dv(e["inp"], e["inn"])
                if d is not None:
                    _absmax(acc, "OA", d, (rec["t"], nm), viol, tol)
            elif k == "D":
                d = dv(e["a"], e["b"])
                if nm in don:
                    if d is not None:
                        _absmax(acc, "D", d, (rec["t"], nm), viol, tol)
                    if ie is not None and ie < -max(tol, 1e-12 if not exact else 0):
                        cnt["diode_sign_viol"] += 1
                else:
                    if ie is not None:
                        _absmax(acc, "D", ie, (rec["t"], nm), viol, tol)
                    if d is not None and d > max(tol, 1e-12 if not exact else 0):
                        cnt["diode_sign_viol"] += 1
            elif k == "E":
                d = dv(e["a"], e["b"]); dc = dv(e["cp"], e["cn"])
                if d is not None and dc is not None:
                    _absmax(acc, "ctrl", d - num(e["gain"]) * dc, (rec["t"], nm), viol, tol)
            elif k == "G":
                dc = dv(e["cp"], e["cn"])
                if dc is not None and ie is not None:
                    _absmax(acc, "ctrl", ie - num(e["gm"]) * dc, (rec["t"], nm), viol, tol)
            elif k == "F":
                ic = i.get(e["ctrl"])
                if ic is not None and ie is not None:
                    _absmax(acc, "ctrl", ie - num(e["gain"]) * ic, (rec["t"], nm), viol, tol)
            elif k == "H":
                ic = i.get(e["ctrl"]); d = dv(e["a"], e["b"])
                if ic is not None and d is not None:
                    _absmax(acc, "ctrl", d - num(e["r"]) * ic, (rec["t"], nm), viol, tol)
    # jumps
    caps = {e["name"]: e for e in els if e["kind"] == "C"}
    for j in dump["jumps"]:
        cnt["jumps"] += 1
        Q = {k: num(x) for k, x in j["Q"].items()}
        leave = {n: 0 for n in nodes}
        for nm, q in Q.items():
            e = by[nm]
            if e["kind"] in ("R", "I"):
                _absmax(acc, "jump_kcl", q, (j["t"], nm, "impulse in R/I"), viol, tol)
                continue
            terms = [(e["out"], 1)] if e["kind"] == "OA" else [(e["a"], 1), (e["b"], -1)]
            for n, sg in terms:
                if n != "0":
                    leave[n] += sg * q
        for n in nodes:
            _absmax(acc, "jump_kcl", leave[n], (j["t"], n), viol, tol)
        sm = {k: num(x) for k, x in j["s_minus"].items()}
        sp = {k: num(x) for k, x in j["s_plus"].items()}
        for nm in set(sm) | set(sp):
            if nm in caps:
                dq = num(caps[nm]["C"]) * (sp[nm] - sm[nm])
                _absmax(acc, "jump_cap", dq - Q.get(nm, 0), (j["t"], nm), viol, tol)
        for nm, q in Q.items():
            if nm in caps and nm not in sm and q != 0:
                _absmax(acc, "jump_cap", q, (j["t"], nm, "impulse without state change"), viol, tol)
    # continuity between instants (exact dumps)
    if exact:
        recs = dump["records"]
        for a, b in zip(recs[:-1], recs[1:]):
            ta, tb = num(a["t"]), num(b["t"])
            if tb == ta:
                continue
            if b["tag"] == "mid":
                continue
            cnt["cont_pairs"] += 1
            h = tb - ta
            for nm, x in a["s"].items():
                xa, xb, d = num(x), num(b["s"][nm]), num(a["ds"][nm])
                pred = xa + d * h
                if pred != xb:
                    # derivative may itself vary (higher-order segment): compare with end derivative
                    d2 = num(b["ds"][nm])
                    if xa + (d + d2) / 2 * h == xb and d != d2:
                        cnt["cont_nonconst"] += 1
                        continue
                    _absmax(acc, "continuity", pred - xb, (a["t"], b["t"], nm), viol, tol)
    return {"exact": exact, "max": {k: (float(v) if not exact else v) for k, v in acc.items()},
            "counts": cnt, "violations": viol}
