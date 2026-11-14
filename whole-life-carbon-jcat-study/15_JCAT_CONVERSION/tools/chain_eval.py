"""Connection to the building-level unified equation: the whole workbook evaluated ONLY by the converted
rules, composed along the cell dependencies.

Start: every formula cell of the book is blank (no cached result is used), inputs and constants are the
workbook's. Units = (pattern, sheet) groups with all their instances. Unit U depends on unit V when U reads
a cell computed by V. Strongly connected components are evaluated in topological order; inside a
component the units are re-evaluated until no value changes (fixed point). Units whose rule is not
converted take Excel's cached values (external data, counted). At the end every formula cell is compared
with Excel's cached value.

Usage: chain_eval.py <scan> <instances.pkl> <book> <improve 0|1> <out.pkl>"""
import sys, os
sys.dont_write_bytecode = True
sys.setrecursionlimit(100000)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "jcat_tools"))
import collections, pickle, time, traceback
import numpy as np
import fx
import excel_ref as X
import compile2 as K
import run_compile as RC
from store import KEY_SHIFT, Err
from validate_ref import same


class StateSource(K.SheetCache):
    """Mutable value source: the baseline cells with the formula cells replaced by the computed values."""

    def __init__(self, base, sd):
        self.base, self.sd = base, sd
        self.memo = {}
        self.arrays = {}

    def sheet_arrays(self, sheet):
        a = self.arrays.get(sheet.sid)
        if a is None:
            ks, m = self.base.sheet_arrays(sheet)
            a = self.arrays[sheet.sid] = (ks, m.copy())
        return a

    def set_values(self, sheet, keys, values):
        ks, m = self.sheet_arrays(sheet)
        idx = np.searchsorted(ks, keys)
        assert np.all(ks[idx] == keys)
        enc = np.array([self.sd.enc(v) for v in values], dtype=float).reshape(len(values), len(K.COMPS))
        changed = np.any(m[idx] != enc, axis=1)
        m[idx] = enc
        return int(np.sum(changed))

    def raw(self, sheet, key):
        ks, m = self.sheet_arrays(sheet)
        i = np.searchsorted(ks, key)
        if i < len(ks) and ks[i] == key:
            row = m[i]
            return self.sd.dec(row[0], row[1], row[2], row[4]) if row[0] != 0 else None
        return None


def tarjan(n, adj):
    index, low, on, st, out = [None] * n, [0] * n, [False] * n, [], []
    counter = [0]
    for root in range(n):
        if index[root] is not None:
            continue
        work = [(root, iter(adj[root]))]
        index[root] = low[root] = counter[0]; counter[0] += 1; st.append(root); on[root] = True
        while work:
            v, it = work[-1]
            pushed = False
            for w in it:
                if index[w] is None:
                    index[w] = low[w] = counter[0]; counter[0] += 1; st.append(w); on[w] = True
                    work.append((w, iter(adj[w])))
                    pushed = True
                    break
                elif on[w]:
                    low[v] = min(low[v], index[w])
            if pushed:
                continue
            work.pop()
            if work:
                low[work[-1][0]] = min(low[work[-1][0]], low[v])
            if low[v] == index[v]:
                comp = []
                while True:
                    w = st.pop(); on[w] = False; comp.append(w)
                    if w == v:
                        break
                out.append(comp)
    return out          # reverse topological order of the condensation (sinks first)


def main():
    scan, inst, book, improve, outp = sys.argv[1:6]
    improve = bool(int(improve))
    t0 = time.time()
    RC.setup(scan, inst)
    units = []
    for pid, d in RC.DATA["instances"].items():
        p = RC.DATA["patterns"][pid]
        for (bk, sheet), arr in d.items():
            if bk != book:
                continue
            units.append(dict(pid=pid, sheet=sheet, arr=arr, sid=RC.STORE.sheet(bk, sheet).sid))
    owner = {}
    for ui, u in enumerate(units):
        for r, c in u["arr"].tolist():
            owner[(u["sid"], r * KEY_SHIFT + c)] = ui
    state = StateSource(RC.CACHE, RC.SD)
    # all formula cells of the book start blank
    by_sheet = collections.defaultdict(list)
    for (sid, key) in owner:
        by_sheet[sid].append(key)
    sheets = {sh.sid: sh for sh in RC.STORE.sheets.values()}
    for sid, keys in by_sheet.items():
        ks = np.array(sorted(keys), dtype=np.int64)
        state.set_values(sheets[sid], ks, [None] * len(ks))
    # compile every unit on all its instances (baseline source only for compiling; values are refilled)
    built, external = {}, []
    for ui, u in enumerate(units):
        p = RC.DATA["patterns"][u["pid"]]
        try:
            ast = fx.Parser(fx.tokenize(p["text"])).parse()
            tree = X.prepare(ast, p["row"], RC.col_num(p["col"]), RC.STORE, book, u["sheet"])
            b = K.Builder(RC.STORE, RC.SD, RC.CACHE, book, u["sheet"], u["arr"][:, 0], u["arr"][:, 1])
            b.improve = improve
            v = b.finish(b.ev(tree))
            b.program()
            built[ui] = (b, v)
        except K.Unsupported as e:
            external.append((ui, str(e)))
    print("units", len(units), "compiled", len(built), "external (not converted)", len(external), round(time.time() - t0), "s", flush=True)
    # dependencies
    adj = [set() for _ in units]
    for ui, (b, v) in built.items():
        for rec in b.recipes:
            if rec[0] in ("G", "T", "lex", "lexG"):
                sheet = rec[2] if rec[0] in ("G", "lexG", "lex") and not isinstance(rec[2], str) else rec[3]
                if rec[0] == "T":
                    sheet, rr, cc = rec[3], rec[4], rec[5]
                elif rec[0] == "G":
                    sheet, rr, cc = rec[2], rec[3], rec[4]
                else:
                    sheet, rr, cc = rec[2], rec[3], rec[4]
                for k in set((np.asarray(rr, dtype=np.int64) * KEY_SHIFT + np.asarray(cc, dtype=np.int64)).tolist()):
                    w = owner.get((sheet.sid, k))
                    if w is not None:
                        adj[ui].add(w)
            elif rec[0] == "W":
                sid = rec[2].sid
                for k in by_sheet.get(sid, []):
                    adj[ui].add(owner[(sid, k)])
    comps = tarjan(len(units), [list(a) for a in adj])      # sinks first = dependencies first
    print("components", len(comps), "largest", max(len(c) for c in comps), round(time.time() - t0), "s", flush=True)
    # external units: cached values
    for ui, why in external:
        u = units[ui]
        sh = sheets[u["sid"]]
        keys = np.array(sorted(r * KEY_SHIFT + c for r, c in u["arr"].tolist()), dtype=np.int64)
        state.set_values(sh, keys, [sh.values.get(int(k)) for k in keys])
    ext_set = {ui for ui, _ in external}
    evals, iters_max = 0, 0
    nonconv = []
    for comp in comps:
        members = [ui for ui in comp if ui in built]
        if not members:
            continue
        cyclic = len(comp) > 1 or comp[0] in adj[comp[0]]
        for it in range(1, 2001):
            changed = 0
            for ui in members:
                b, v = built[ui]
                b.refresh(state)
                got, _, _ = b.run(v)
                evals += 1
                u = units[ui]
                keys = u["arr"][:, 0].astype(np.int64) * KEY_SHIFT + u["arr"][:, 1].astype(np.int64)
                vals = [None if g == "<missing>" else g for g in got]
                changed += state.set_values(sheets[u["sid"]], keys, vals)
            iters_max = max(iters_max, it)
            if not cyclic or changed == 0:
                break
        else:
            nonconv.append(comp)
    print("evaluations", evals, "max iterations", iters_max, "not converged", len(nonconv), round(time.time() - t0), "s", flush=True)
    # compare every formula cell with Excel's cached value
    tot = collections.Counter()
    ex = []
    per_pid = collections.defaultdict(collections.Counter)
    for ui, u in enumerate(units):
        sh = sheets[u["sid"]]
        for r, c in u["arr"].tolist():
            key = r * KEY_SHIFT + c
            got = state.raw(sh, key)
            got = 0.0 if got is None else got
            want = sh.values.get(key)
            eq = same(got, want)[0]
            tag = "external" if ui in ext_set else "converted"
            tot[tag + ":n"] += 1
            tot[tag + (":ok" if eq else ":bad")] += 1
            per_pid[u["pid"]]["ok" if eq else "bad"] += 1
            if not eq and len(ex) < 30:
                ex.append((tag, u["pid"], sh.name, r, c, repr(got)[:50], repr(want)[:50]))
    print(dict(tot), flush=True)
    for e in ex[:12]:
        print("  ", e, flush=True)
    pickle.dump(dict(book=book, improve=improve, totals=dict(tot), examples=ex, external=external, components=len(comps),
                     largest=max(len(c) for c in comps), evaluations=evals, iters_max=iters_max, nonconv=len(nonconv),
                     per_pid=dict(per_pid), seconds=time.time() - t0), open(outp, "wb"))


if __name__ == "__main__":
    main()
