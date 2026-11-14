"""LaTeX of a compiled program (the converted form of one rule), written mechanically from the engine
specification (every step), with the legend of variables (which original reference fills which column)."""
import re

import numpy as np

COMP_TEX = {"t": "t", "n": "n", "s": "s", "k": "k", "e": "e", "p": "p", "q": "q", "w": "w", "o": "o"}
TABLE_TEX = {}


def num(x):
    if isinstance(x, str):
        return r"\text{%s}" % x
    if x == int(x) and abs(x) < 1e15:
        return "%d" % int(x)
    return repr(float(x)).replace("e", r"\mathrm{e}")


class Namer:
    def __init__(self):
        self.map = {}
        self.cells = {}

    def col(self, name):
        if name in self.map:
            return self.map[name]
        m = re.match(r"^(c|lx)(\d+)\.(?:lex\.)?(\w+)$", name)
        if m:
            tex = r"%s^{(%s)}_{%s}" % (m.group(3).replace("_", r"\_"), m.group(2), "i")
        elif name.startswith("_"):
            tex = r"\mathrm{%s}" % name.replace("_", r"\_")
        elif re.match(r"^(s\.|a\d+\.)?[tnskepqwo]$", name):
            tex = r"\mathrm{%s}" % name.replace(".", r".\,")
        elif name.startswith("lex."):
            tex = r"\mathrm{%s}" % name.replace(".", r".\,")
        else:
            m2 = re.match(r"^([a-zA-Z]+)(\d+)$", name)
            tex = r"v_{%s}" % m2.group(2) if m2 else r"\mathrm{%s}" % name.replace("_", r"\_")
        self.map[name] = tex
        return tex


def operand(op, nm, table):
    if isinstance(op, str):
        return nm.col(op)
    if "const" in op:
        return num(op["const"])
    if "via" in op:
        return r"%s[%s]" % (nm.col(op["col"]), nm.col(op["via"]))
    if "of" in op:
        return r"%s^{\mathrm{%s}}" % (nm.col(op["col"]), op["of"])
    return "?"


def factor(f, nm, table):
    if isinstance(f, dict) and "pred" in f:
        a = operand(f["a"], nm, table)
        neg = f.get("not")
        if f["pred"] == "present":
            return r"[%s\ \text{%s}]" % (a, "missing" if neg else "present")
        if f["pred"] == "eq":
            return r"[%s %s %s]" % (a, r"\ne" if neg else "=", operand(f["b"], nm, table))
        if f["pred"] == "le":
            return r"[%s %s %s]" % (a, ">" if neg else r"\le", operand(f["b"], nm, table))
        return r"[\mathrm{%s}(%s)]" % (f["pred"], a)
    if isinstance(f, dict) and "fn" in f:
        a = operand(f["a"], nm, table)
        return {"inv": r"\frac{1}{%s}" % a, "one_minus": r"(1-%s)" % a}.get(f["fn"], r"\mathrm{%s}(%s)" % (f["fn"], a))
    return operand(f, nm, table)


def step_tex(st, nm):
    if st["op"] == "match":
        keys = ", ".join(operand(k, nm, st["table"]) for k in st["keys"])
        on = ", ".join(nm.col(o) for o in st["on"])
        return r"%s(x) &= \min\{\, y \in \mathcal{T}_{\mathrm{%s}} : (%s)(y) = (%s)(x) \,\} \quad (x \in \mathcal{T}_{\mathrm{%s}})" % (
            nm.col(st["out"]), st["into"].replace("_", r"\_"), on, keys, st["table"].replace("_", r"\_"))
    terms = []
    for term in st["terms"]:
        fs = [factor(f, nm, st["table"]) for f in term]
        terms.append(r" \cdot ".join(fs) if fs else "1")
    body = " + ".join(terms)
    g = st.get("group", "none")
    tab = st["table"].replace("_", r"\_")
    if g == "none":
        return r"%s(x) &= %s \quad (x \in \mathcal{T}_{\mathrm{%s}})" % (nm.col(st["out"]), body, tab)
    if g == "total":
        return r"%s &= \sum_{x \in \mathcal{T}_{\mathrm{%s}}} \left( %s \right)" % (nm.col(st["out"]), tab, body)
    return r"%s(g) &= \sum_{x \in \mathcal{T}_{\mathrm{%s}},\ %s(x) = g} \left( %s \right)" % (nm.col(st["out"]), tab, nm.col(g["by"]), body)


def compress(steps):
    """Runs of the dyadic bisection of the integer-lattice knot spectrum are written as one line."""
    out, i = [], 0
    while i < len(steps):
        st = steps[i]
        if st["op"] == "sp" and st["out"].startswith("fb"):
            j = i
            while j < len(steps) and steps[j]["op"] == "sp" and steps[j]["out"].startswith("fb"):
                j += 1
            out.append(("bisect", steps[i], steps[j - 1], j - i))
            i = j
            continue
        out.append(("step", st))
        i += 1
    return out


def program_tex(spec_steps, out_comps, nm=None):
    nm = nm or Namer()
    lines = []
    for item in compress(spec_steps):
        if item[0] == "bisect":
            _, a, b, n = item
            src = a["terms"][0][0]
            lines.append(r"%s(x) &= r_0(x) - \sum_{j=0}^{%d} 2^{j}\,\beta_j(x),\quad \beta_j = [2^{j} \le r_{%d-j}],\ r_{m+1} = r_m - 2^{%d-m}\beta_{%d-m},\ r_0 = %s"
                         r" \quad \text{(integer-lattice knot spectrum } F(x)=\textstyle\sum_{m\ge1}[m\le x]\text{, %d exact steps)}"
                         % (nm.col(b["out"]), n - 1, n - 1, n - 1, n - 1, operand(src, nm, a["table"]), n))
        else:
            lines.append(step_tex(item[1], nm))
    res = []
    for c in ("t", "n", "s", "e"):
        o = out_comps.get(c)
        if o is None:
            continue
        res.append(r"%s_{\mathrm{out}}(i) &= %s" % (c, operand(o, nm, "G")))
    return lines, res, nm


def legend(builder, nm):
    """Which original reference fills which column (data layout), per recipe."""
    rows = []
    for rec in builder.recipes:
        if rec[0] == "G":
            _, prefix, sheet, rr, cc, bad = rec
            name = prefix.rstrip(".")
            dr = sorted(set((np.asarray(rr) - builder.rows).tolist()))
            dc = sorted(set((np.asarray(cc) - builder.cols).tolist()))
            ar = sorted(set(np.asarray(rr).tolist()))
            ac = sorted(set(np.asarray(cc).tolist()))
            rows.append(dict(kind="cell", column=name, sheet=sheet.name,
                             row=("abs %d" % ar[0]) if len(ar) == 1 and len(dr) > 1 else ("i%+d" % dr[0] if len(dr) == 1 else "varies"),
                             col=("abs %d" % ac[0]) if len(ac) == 1 and len(dc) > 1 else ("j%+d" % dc[0] if len(dc) == 1 else "varies")))
        elif rec[0] == "T":
            _, table, prefix, sheet, rr, cc = rec
            rows.append(dict(kind="range cells", column=table + (":" + prefix if prefix else ""), sheet=sheet.name,
                             row="%d..%d" % (int(np.min(rr)), int(np.max(rr))) if len(rr) else "-",
                             col="%d..%d" % (int(np.min(cc)), int(np.max(cc))) if len(cc) else "-"))
        elif rec[0] == "W":
            rows.append(dict(kind="all cells (computed position)", column=rec[1], sheet=rec[2].name, row="*", col="*"))
        elif rec[0] in ("lex", "lexG"):
            rows.append(dict(kind="lexical companions (improvement)", column=str(rec[1]), sheet=rec[2].name if rec[0] == "lexG" else rec[2].name,
                             row="", col=""))
        elif rec[0] == "copy":
            rows.append(dict(kind="key line (copy of range cells)", column=rec[2], sheet="", row="", col=""))
    return rows
