"""Stage 3 of the unified-theory study: the remaining text rules, written ONLY with the two existing structures
(masked sum-product `sp` / `match` of the unchanged engine tstudy/msp.py; knot spectra are not needed here).

Builds on chapter 16 (exact8.Exact8Final): a text is a union of CHARACTER INDEX SETS (rows: instance, output position,
character code, validity), built by '&'. This module adds, in the same representation:

  IF(cond, a, b)        with text branches: the segments of both branches, each gated by the exclusive condition
                        masks; the error of the condition or of the chosen branch is the error of the result
  IFERROR(x, y)         x's segments where x is not an error, y's where it is
  SUBSTITUTE(x, old, new)   constant old (non-empty, border-free: no proper prefix equals a suffix, so occurrences
                        never overlap and "left-to-right, non-overlapping" = "all occurrences") and constant new;
                        x a cell, a '&' text, or a VLOOKUP result. Slot table (instance, j < LM):
                          code_j  = the character at position j (match into the union of the source segments)
                          occ_j   = prod_t [code_{j+t} = old_t]                       (matches at j+t)
                          del_j   = sum_{t<m} occ_{j-t}
                          cnt_j   = sum_{i<j} occ_i   (prefix sum by doubling: 8 match+sp steps, W = 256 >= LM)
                          out position = j - m cnt_j + len(new) cnt_j   for kept characters,
                          new characters at (j - m cnt_j + len(new) cnt_j + t) for every occurrence j
                        texts longer than LM characters are outside the compiled domain (result missing)
  VLOOKUP result as a text: the characters of the matched cell of the range (character table of the range's cells,
                        selected by a match on (matched cell, position)), or the general number format of a numeric
                        result, or TRUE/FALSE.
"""
from __future__ import annotations

import collections
import math
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import exact8 as E8                                          # noqa: E402
from exact8 import K, C, EQ, LE, PRESENT, isc, V, T0, T1, T2, T3, T4, TXV   # noqa: E402

LM = 255                 # slots per instance (texts up to 255 characters)
DOUBLING = (1, 2, 4, 8, 16, 32, 64, 128)


def _border_free(s: str) -> bool:
    return all(s[:k] != s[-k:] for k in range(1, len(s)))


class Exact12(E8.Exact8Final):

    # ---- helpers -------------------------------------------------------------------------------------
    def _gref(self, x):
        return x if isc(x) else {"col": x, "via": "_parent"}

    def _gate(self, segs, mask):
        """Segments valid only where the G column `mask` is 1."""
        out = []
        for table, opos, code, valid in segs:
            if isc(valid) and valid["const"] == 0.0:
                continue
            if isc(mask):
                if mask["const"] == 0.0:
                    continue
                out.append((table, opos, code, valid))
                continue
            terms = [[self._gref(mask)]] if isc(valid) else [[valid, self._gref(mask)]]
            out.append((table, opos, code, self.sp(terms, table=table, hint="gv")))
        return out

    def _txv(self, segs, L, ef, ec):
        t = self.sp([[EQ(ef, C(1.0)), C(T4)], [EQ(ef, C(1.0), True), C(T2)]], hint="tt")
        v = TXV({"t": t, "e": self.sp([[EQ(ef, C(1.0)), ec]], hint="te")}, {T2, T4})
        v.tx = dict(segs=segs, L=L, ef=ef)
        return v

    def _txv_err(self, v):
        """(ef, ec) of a TXV."""
        return v.tx["ef"], v.c["e"]

    def as_txv(self, node):
        """Any text-valued operand as a TXV (a '&' text, a text constant, a cell, or a TXV-producing call)."""
        k = node[0]
        if k == "const" and isinstance(node[1], str):
            segs = [self.seg_const(node[1])] if node[1] else []
            return self._txv(segs, C(float(len(node[1]))), C(0.0), C(0.0))
        if k == "bin" and node[1] == "&" and self.has_cell(node):
            return self.ev(node)
        if k == "call" and node[1] in ("IF", "IFERROR", "SUBSTITUTE"):
            v = self.ev(node)
            if isinstance(v, TXV):
                return v
            raise K.Unsupported("text operand %s that is not a text" % node[1])
        if k == "R":
            segs, (ef, ec) = self.to_text_segs(node)
            out, L, (ef2, ec2) = self.concat_segs([(segs, (ef, ec))])
            return self._txv(out, L, ef2, ec2)
        if k == "call" and node[1] == "VLOOKUP":
            return self.vlookup_text(node)
        raise K.Unsupported("text operand of kind %s" % k)

    @staticmethod
    def _texty(node):
        k = node[0]
        return (k == "const" and isinstance(node[1], str)) or (k == "bin" and node[1] == "&") or \
            (k == "call" and node[1] in ("SUBSTITUTE",)) or (k == "call" and node[1] in ("IF", "IFERROR") and
                                                             any(Exact12._texty(a) for a in node[2][1:]))

    # ---- dispatch --------------------------------------------------------------------------------------
    def ev(self, node):
        if node[0] == "call" and self.mode8 == "A":
            name, args = node[1], node[2]
            if name == "IF" and len(args) == 3 and self.has_cell(node) and (self._texty(args[1]) or self._texty(args[2])) \
                    and all(self._texty(a) or a[0] == "R" for a in args[1:]):
                return self.if_text(args)
            if name == "IFERROR" and len(args) == 2 and self.has_cell(node) and self._texty(args[0]) and self._texty(args[1]):
                return self.iferror_text(args)
            if name == "SUBSTITUTE" and len(args) == 3 and self.has_cell(node):
                return self.substitute_text(args)
        return E8.Exact8Final.ev(self, node)

    # ---- IF / IFERROR on texts -----------------------------------------------------------------------
    def if_text(self, args):
        cb, ef, ec = self.to_bool(self.val(args[0]))
        a, b = self.as_txv(args[1]), self.as_txv(args[2])
        ok = EQ(ef, C(1.0), True)
        my = self.sp([[ok, EQ(cb, C(1.0))]], hint="my")
        mn = self.sp([[ok, EQ(cb, C(1.0), True)]], hint="mn")
        segs = self._gate(a.tx["segs"], my) + self._gate(b.tx["segs"], mn)
        L = self.sp([[my, a.tx["L"]], [mn, b.tx["L"]]], hint="ifl")
        aef, aec = self._txv_err(a)
        bef, bec = self._txv_err(b)
        ef2 = self.sp([[EQ(ef, C(1.0))], [my, EQ(aef, C(1.0))], [mn, EQ(bef, C(1.0))]], hint="ife")
        ec2 = self.sp([[EQ(ef, C(1.0)), ec], [my, EQ(aef, C(1.0)), aec], [mn, EQ(bef, C(1.0)), bec]], hint="ifc")
        self.notes["IF with text branches: union of gated character index sets"] += 1
        return self._txv(segs, L, ef2, ec2)

    def iferror_text(self, args):
        x, y = self.as_txv(args[0]), self.as_txv(args[1])
        xef, xec = self._txv_err(x)
        yef, yec = self._txv_err(y)
        isx = self.sp([[EQ(xef, C(1.0), True)]], hint="ix")
        isy = self.sp([[EQ(xef, C(1.0))]], hint="iy")
        segs = self._gate(x.tx["segs"], isx) + self._gate(y.tx["segs"], isy)
        L = self.sp([[isx, x.tx["L"]], [isy, y.tx["L"]]], hint="iel")
        ef2 = self.sp([[isy, EQ(yef, C(1.0))]], hint="iee")
        ec2 = self.sp([[isy, EQ(yef, C(1.0)), yec]], hint="iec")
        self.notes["IFERROR with text operands: gated character index sets"] += 1
        return self._txv(segs, L, ef2, ec2)

    # ---- VLOOKUP result as characters ------------------------------------------------------------------
    def _rowid(self, table):
        """A numeric copy of the row position (data layout: an index column; reference columns cannot enter products)."""
        d = self.tabs.data[table]
        if "rowid" not in d:
            d["rowid"] = np.arange(self.tabs.rows[table], dtype=float)
            d["rowid?"] = np.ones(self.tabs.rows[table], dtype=bool)

    def fill(self, rec, src):
        E8.Exact8Final.fill(self, rec, src)
        if rec[0] == "T" and "rowid" in self.tabs.data.get(rec[1], {}):
            self.tabs.data[rec[1]]["rowid"] = np.arange(self.tabs.rows[rec[1]], dtype=float)
            self.tabs.data[rec[1]]["rowid?"] = np.ones(self.tabs.rows[rec[1]], dtype=bool)

    def vlookup_text(self, node):
        cap = {}
        orig = self.lookup_value

        def capture(Rc, rid, i, j):
            cell = orig(Rc, rid, i, j)
            cap["Rc"], cap["cell"] = Rc, cell
            return cell
        self.lookup_value = capture
        try:
            v = self.scalar(self.ev(node))
        finally:
            self.lookup_value = orig
        if "Rc" not in cap:
            raise K.Unsupported("VLOOKUP without a result cell")
        Rc, cell = cap["Rc"], cap["cell"]
        rec0 = [r for r in self.recipes if r[0] == "T" and r[1] == Rc and r[2] == ""][0]
        CH = Rc + ".ch"
        if CH not in self.tabs.rows:
            rec = ("charsT", CH, rec0[3], rec0[4], rec0[5])
            self.recipes.append(rec)
            self.fill(rec, self.cache)
        tv = v.op("t")
        self._rowid(Rc)
        crow = self.sp([[PRESENT(cell), {"col": "rowid", "via": cell}], [PRESENT(cell, True), C(-1.0)]], hint="crow")
        name = self.nm("G.vs")
        self.table(name, {"_parent": np.repeat(np.arange(self.n), LM), "j": np.tile(np.arange(LM), self.n)})
        m = self.match([{"col": crow, "via": "_parent"}, "j"], CH, ["_parent", "pos"], table=name, hint="vm")
        istext = self.sp([[EQ(tv, C(T2))]], hint="vtx")
        code = self.sp([[PRESENT(m), {"col": "code", "via": m}]], table=name, hint="vcd")
        valid = self.sp([[PRESENT(m), {"col": istext, "via": "_parent"}]], table=name, hint="vvd")
        # texts longer than LM: outside the compiled domain
        ylen = self.sp([[C(1.0)]], table=CH, group={"by": "_parent"}, hint="vyl")
        ym = self.match([crow], Rc, ["_row"], hint="vym")
        plen = self.sp([[PRESENT(ym), EQ(tv, C(T2)), {"col": ylen, "via": ym}]], hint="vpl")
        self.flag(self.sp([[LE(C(float(LM) + 0.5), plen)]], hint="vlong"))
        isnum = self.sp([[EQ(tv, C(T1))]], hint="vnum")
        segs = [(name, "j", code, valid),
                self.number_text(self.sp([[EQ(tv, C(T1)), v.op("n")]], hint="vnv"), isnum),
                self.seg_const("TRUE", self.sp([[EQ(tv, C(T3)), EQ(v.op("n"), C(1.0))]], hint="vbt")),
                self.seg_const("FALSE", self.sp([[EQ(tv, C(T3)), EQ(v.op("n"), C(1.0), True)]], hint="vbf"))]
        ef = self.sp([[EQ(tv, C(T4))]], hint="vef")
        ec = self.sp([[EQ(tv, C(T4)), v.op("e")]], hint="vec")
        out, L, (ef2, ec2) = self.concat_segs([(segs, (ef, ec))])
        self.notes["look-up result as characters: match on (matched cell, position) into the range's character table"] += 1
        return self._txv(out, L, ef2, ec2)

    # ---- SUBSTITUTE --------------------------------------------------------------------------------------
    def substitute_text(self, args):
        if args[1][0] != "const" or args[2][0] != "const" or not isinstance(args[1][1], str) or not isinstance(args[2][1], str):
            raise K.Unsupported("SUBSTITUTE with a computed old or new text")
        old, new = args[1][1], args[2][1]
        src = self.as_txv(args[0])
        if old == "":
            return src
        if not _border_free(old):
            raise K.Unsupported("SUBSTITUTE with an old text that can overlap itself")
        m, ln = len(old), len(new)
        # 1. unified slots: the character at every position of the source text
        U = self.nm("G.su")
        self.table(U, {"_parent": np.repeat(np.arange(self.n), LM), "j": np.tile(np.arange(LM), self.n)})
        code_t, pres_t = [], []
        for table, opos, code, valid in src.tx["segs"]:
            if isc(valid) and valid["const"] == 0.0:
                continue
            if isc(valid):
                mt = self.match(["_parent", "j"], table, ["_parent", opos], table=U, hint="sm")
            else:
                mt = self.match(["_parent", "j", C(1.0)], table, ["_parent", opos, valid], table=U, hint="sm")
            code_t.append([PRESENT(mt), {"col": code, "via": mt}])
            pres_t.append([PRESENT(mt)])
        code_u = self.sp(code_t or [[C(0.0)]], table=U, hint="scd")
        pres_u = self.sp(pres_t or [[C(0.0)]], table=U, hint="spr")
        # source length beyond the slots: outside the compiled domain
        self.flag(self.sp([[LE(C(float(LM) + 0.5), src.tx["L"])]], hint="slong"))
        # 2. occurrences (old is border-free: they never overlap)
        facs = [EQ(pres_u, C(1.0)), EQ(code_u, C(float(ord(old[0]))))]
        for t in range(1, m):
            mt = self.match(["_parent", self.sp([["j"], [C(float(t))]], table=U, hint="sj")], U, ["_parent", "j"], table=U, hint="so")
            facs += [PRESENT(mt), EQ({"col": pres_u, "via": mt}, C(1.0)), EQ({"col": code_u, "via": mt}, C(float(ord(old[t]))))]
        occ = self.sp([facs], table=U, hint="occ")
        dl = [[occ]]
        for t in range(1, m):
            mt = self.match(["_parent", self.sp([["j"], [C(-float(t))]], table=U, hint="sj")], U, ["_parent", "j"], table=U, hint="sd")
            dl.append([PRESENT(mt), {"col": occ, "via": mt}])
        dele = self.sp(dl, table=U, hint="del")
        # 3. occurrences strictly before j: prefix sum by doubling
        mt = self.match(["_parent", self.sp([["j"], [C(-1.0)]], table=U, hint="sj")], U, ["_parent", "j"], table=U, hint="sp1")
        acc = self.sp([[PRESENT(mt), {"col": occ, "via": mt}]], table=U, hint="cnt")
        for w in DOUBLING:
            mt = self.match(["_parent", self.sp([["j"], [C(-float(w))]], table=U, hint="sj")], U, ["_parent", "j"], table=U, hint="spw")
            acc = self.sp([[acc], [PRESENT(mt), {"col": acc, "via": mt}]], table=U, hint="cnt")
        # acc_j = sum_{t=1}^{2 W} occ_{j-t} (W = 128 steps double from 1: covers every j < LM = 255)
        shift = float(ln - m)
        opos = self.sp([["j"], [C(shift), acc]], table=U, hint="sop")
        keep = self.sp([[EQ(pres_u, C(1.0)), EQ(dele, C(0.0))]], table=U, hint="skp")
        segs = [(U, opos, code_u, keep)]
        if ln:
            N = self.nm("G.sn")
            par = np.repeat(np.arange(self.n), LM * ln)
            jj = np.tile(np.repeat(np.arange(LM), ln), self.n)
            tt = np.tile(np.arange(ln), self.n * LM)
            self.table(N, {"_parent": par, "j": jj, "t": tt,
                           "code": np.array([float(ord(new[i])) for i in tt]) if len(tt) else np.zeros(0)})
            mo = self.match(["_parent", "j"], U, ["_parent", "j"], table=N, hint="snm")
            vn = self.sp([[PRESENT(mo), {"col": occ, "via": mo}]], table=N, hint="snv")
            onp = self.sp([["j"], ["t"], [PRESENT(mo), C(shift), {"col": acc, "via": mo}]], table=N, hint="snp")
            segs.append((N, onp, "code", vn))
        nkeep = self.sp([[keep]], table=U, group={"by": "_parent"}, hint="sL")
        nocc = self.sp([[occ]], table=U, group={"by": "_parent"}, hint="sO")
        L = self.sp([[nkeep], [C(float(ln)), nocc]], hint="sLL")
        ef, ec = self._txv_err(src)
        self.notes["SUBSTITUTE: slot table, occurrence product, doubling prefix count, compacted positions"] += 1
        return self._txv(segs, L, ef, ec)
