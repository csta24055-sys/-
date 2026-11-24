"""Residual checks computed from a dumped solution ONLY (netlist JSON + records + jumps).

Does not import or call the solver; recomputes KCL, element laws, impulse-charge KCL and
energy balances from the exported numbers. (The independent verifier is expected to write
its own; this one exists so the builder's own tests do not trust the solver's internals.)
"""
from __future__ import annotations

from fractions import Fraction


def num(x):
    if x is None:
        return None
    if isinstance(x, (int, float, Fraction)) and not isinstance(x, bool):
        return x
    if isinstance(x, str):
        if "/" in x:
            p, q = x.split("/")
            return Fraction(int(p), int(q))
        try:
            return Fraction(int(x))
        except ValueError:
            return float(x)
    raise TypeError(x)


def _terminals(el):
    k = el["kind"]
    if k == "OA":
        return [(el["out"], 1)]          # norator current leaves `out` into the element
    if k in ("R", "C", "L", "V", "I", "E", "G", "F", "H", "SW", "D"):
        return [(el["a"], 1), (el["b"], -1)]
    return []


def residuals(dump):
    els = [e for e in dump["netlist"] if e["kind"] in ("R", "C", "L", "V", "I", "E", "G", "F", "H", "SW", "D", "OA")]
    exact = dump["exact"]
    out = {"records": len(dump["records"]), "kcl_max": 0, "law_max": 0, "kcl_skipped": 0,
           "law_skipped": 0, "jump_kcl_max": 0, "jump_tellegen_max": 0, "jump_cap_energy_max": 0,
           "violations": []}

    def upd(key, val, where):
        a = abs(val)
        if a > out[key]:
            out[key] = a
        tol = 0 if exact else 1e-8
        if a > tol and len(out["violations"]) < 20:
            out["violations"].append((key, where, float(a)))

    for rec in dump["records"]:
        v = {n: num(x) for n, x in rec["v"].items()}
        v["0"] = 0
        i = {n: num(x) for n, x in rec["i"].items()}
        s = {n: num(x) for n, x in rec["s"].items()}
        ds = {n: num(x) for n, x in rec["ds"].items()}
        closed = set(rec["closed"])
        don = set(rec["diode_on"])
        # KCL
        sums, bad = {}, set()
        for e in els:
            cur = i.get(e["name"])
            for node, sg in _terminals(e):
                if node == "0":
                    continue
                if cur is None:
                    bad.add(node)
                    continue
                sums[node] = sums.get(node, 0) + sg * cur
        for node, val in sums.items():
            if node in bad:
                out["kcl_skipped"] += 1
                continue
            upd("kcl_max", val, (rec["t"], rec["tag"], "node", node))
        # element laws
        for e in els:
            k, name = e["kind"], e["name"]
            cur = i.get(name)
            if k == "OA":
                a, b = v.get(e["inp"]), v.get(e["inn"])
                if a is None or b is None:
                    out["law_skipped"] += 1
                else:
                    upd("law_max", a - b, (rec["t"], name, "nullator"))
                continue
            va, vb = v.get(e["a"]), v.get(e["b"])
            vab = None if (va is None or vb is None) else va - vb
            if k == "R":
                if vab is None or cur is None:
                    out["law_skipped"] += 1
                else:
                    upd("law_max", cur - num(e["G"]) * vab, (rec["t"], name, "ohm"))
            elif k == "V":
                if vab is not None:
                    upd("law_max", vab - num(e["V"]), (rec["t"], name, "vsrc"))
            elif k == "I":
                upd("law_max", cur - num(e["I"]), (rec["t"], name, "isrc"))
            elif k == "SW":
                if name in closed:
                    if vab is not None:
                        upd("law_max", vab, (rec["t"], name, "closed"))
                else:
                    upd("law_max", cur, (rec["t"], name, "open"))
            elif k == "D":
                if name in don:
                    if vab is not None:
                        upd("law_max", vab, (rec["t"], name, "don_v"))
                    upd("law_max", min(0, cur), (rec["t"], name, "don_i"))
                else:
                    upd("law_max", cur, (rec["t"], name, "doff_i"))
                    if vab is not None:
                        upd("law_max", max(0, vab), (rec["t"], name, "doff_v"))
            elif k == "C":
                if vab is not None:
                    upd("law_max", vab - s[name], (rec["t"], name, "cap_v"))
                if cur is not None:
                    upd("law_max", cur - num(e["C"]) * ds[name], (rec["t"], name, "cap_i"))
            elif k == "L":
                upd("law_max", cur - s[name], (rec["t"], name, "ind_i"))
                if vab is not None:
                    upd("law_max", vab - num(e["L"]) * ds[name], (rec["t"], name, "ind_v"))
            elif k == "E":
                cp, cn = v.get(e["cp"]), v.get(e["cn"])
                if vab is not None and cp is not None and cn is not None:
                    upd("law_max", vab - num(e["gain"]) * (cp - cn), (rec["t"], name, "vcvs"))
            elif k == "G":
                cp, cn = v.get(e["cp"]), v.get(e["cn"])
                if cp is not None and cn is not None and cur is not None:
                    upd("law_max", cur - num(e["gm"]) * (cp - cn), (rec["t"], name, "vccs"))
            elif k == "F":
                upd("law_max", cur - num(e["gain"]) * i[e["ctrl"]], (rec["t"], name, "cccs"))
    # impulsive re-initialisations
    byname = {e["name"]: e for e in els}
    for j in dump["jumps"]:
        Q = {k: num(x) for k, x in j["Q"].items()}
        sums = {}
        for name, q in Q.items():
            for node, sg in _terminals(byname[name]):
                if node != "0":
                    sums[node] = sums.get(node, 0) + sg * q
        for node, val in sums.items():
            upd("jump_kcl_max", val, (j["t"], "jumpnode", node))
        if "W_absorbed" not in j:          # simulators that log impulse charges only
            sm = {k: num(x) for k, x in j["s_minus"].items()}
            sp = {k: num(x) for k, x in j["s_plus"].items()}
            for name in sp:
                e = byname[name]
                if e["kind"] == "C":
                    upd("jump_kcl_max", num(e["C"]) * (sp[name] - sm[name]) - Q.get(name, 0), (j["t"], name, "capQ"))
            continue
        W = {k: num(x) for k, x in j["W_absorbed"].items()}
        if all(w is not None for w in W.values()):
            upd("jump_tellegen_max", sum(W.values()), (j["t"], "tellegen"))
        # capacitor energy change equals absorbed energy on the linear path
        sm = {k: num(x) for k, x in j["s_minus"].items()}
        sp = {k: num(x) for k, x in j["s_plus"].items()}
        for name in sp:
            e = byname[name]
            if e["kind"] == "C":
                C = num(e["C"])
                dE = C * (sp[name] ** 2 - sm[name] ** 2) / 2
                upd("jump_cap_energy_max", dE - (W.get(name) or 0), (j["t"], name, "capE"))
                upd("jump_kcl_max", C * (sp[name] - sm[name]) - Q.get(name, 0), (j["t"], name, "capQ"))
    return out


def energy_balance(dump, s_initial=None):
    """Tellegen over the whole run: sum of absorbed energies (continuous + jumps) = 0, and
    capacitor/inductor absorbed energy = change of stored energy."""
    m = dump["meters"]
    cont = {k: num(x) for k, x in m["absorbed_energy_continuous"].items()}
    jmp = {k: num(x) for k, x in m["absorbed_energy_jumps_linear_path"].items()}
    total = sum(cont.values()) + sum(x for x in jmp.values() if x is not None)
    res = {"tellegen_total": total}
    els = {e["name"]: e for e in dump["netlist"]}
    if dump["records"]:
        first, last = dump["records"][0], dump["records"][-1]
        worst = 0
        for name in dump["states"]:
            e = els[name]
            a0 = num(first["s"][name]) if s_initial is None else s_initial[name]
            a1 = num(last["s"][name])
            k = num(e["C"]) if e["kind"] == "C" else num(e["L"])
            dE = k * (a1 * a1 - a0 * a0) / 2
            got = cont[name] + (jmp[name] or 0)
            worst = max(worst, abs(dE - got))
        res["storage_vs_meter_max"] = worst
    return res
