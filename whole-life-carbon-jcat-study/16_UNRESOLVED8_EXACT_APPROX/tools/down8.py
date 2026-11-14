"""Downstream impact of the 8 equations (private, local only).
1. consumers: every formula cell of the workbook whose static references (single cells and ranges of the
   prepared formula tree) contain a cell of the equation; transitive closure by levels;
2. substitution: the cells of the equation take the values of method A / method B (baseline inputs); the
   closure is re-evaluated by the reference evaluator in level order; compared with Excel's cached values;
3. sensitivity: every numeric cell of the equation is moved by +-1 ulp (the size of method B's errors for
   x^a, log10; ROUND's B errors are a decimal unit and are covered by item 2); consumer cells whose value
   changes by more than a proportional 8 ulp (a rounding, a threshold or a look-up that flips) are counted.
Usage: down8.py <results of run8 (L1 values)> <out.pkl>"""
import os, sys, time, collections, pickle, math
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
S = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(S, "conv")); sys.path.insert(0, os.path.join(S, "jcat_tools"))
import warnings; warnings.simplefilter("ignore")
import numpy as np
import fx, excel_ref as X, compile2 as K, run_compile as RC
from overlay import OverlayStore
from store import KEY_SHIFT, Err
from validate_ref import same as same_tol
from synth import same            # exact comparison
import exact8 as E8
from run8 import TARGETS, builder


def refs_of(node, out):
    k = node[0]
    if k == "R":
        out.append(node)
    elif k in ("neg", "pct"):
        refs_of(node[1], out)
    elif k == "bin":
        refs_of(node[2], out); refs_of(node[3], out)
    elif k == "call":
        for a in node[2]:
            refs_of(a, out)
    return out


def rect(node, rows, cols, sheet):
    _, sh, corners = node
    n = len(rows)
    rs, cs = [], []
    for rr, cc in corners:
        rs.append(None if rr is None else (np.full(n, rr[1]) if rr[0] else rows + rr[1]))
        cs.append(None if cc is None else (np.full(n, cc[1]) if cc[0] else cols + cc[1]))
    if rs[0] is None:
        r1, r2 = np.full(n, 1), np.full(n, max(sheet.max_row, 1))
    else:
        r1, r2 = np.minimum.reduce(rs), np.maximum.reduce(rs)
    if cs[0] is None:
        c1, c2 = np.full(n, 1), np.full(n, max(sheet.max_col, 1))
    else:
        c1, c2 = np.minimum.reduce(cs), np.maximum.reduce(cs)
    return r1, r2, c1, c2


def build_index():
    """Per book: list of (pid, sheet name, instance array, tree, [(target sheet sid, r1, r2, c1, c2)])."""
    idx = collections.defaultdict(list)
    for pid, d in RC.DATA["instances"].items():
        p = RC.DATA["patterns"][pid]
        ast = fx.Parser(fx.tokenize(p["text"])).parse()
        for (book, sheet), arr in d.items():
            try:
                tree = X.prepare(ast, p["row"], RC.col_num(p["col"]), RC.STORE, book, sheet)
            except Exception:
                continue
            rows, cols = arr[:, 0].astype(np.int64), arr[:, 1].astype(np.int64)
            rl = []
            for node in refs_of(tree, []):
                sh = RC.STORE.sheet(book, node[1]) if node[1] else RC.STORE.sheet(book, sheet)
                if sh is None:
                    continue
                rl.append((sh.sid, sh) + rect(node, rows, cols, sh))
            idx[book].append((pid, sheet, arr, tree, rl))
    return idx


def consumers(idx, book, targets):
    """targets: set of (sid, r, c). Returns {(pid, sheet, r, c)} of cells reading a target."""
    by_sid = collections.defaultdict(list)
    for sid, r, c in targets:
        by_sid[sid].append((r, c))
    grids = {}
    for sid, cells in by_sid.items():
        R_ = max(r for r, _ in cells) + 1
        C_ = max(c for _, c in cells) + 1
        g = np.zeros((R_ + 1, C_ + 1), dtype=np.int64)
        for r, c in cells:
            g[r, c] += 1
        grids[sid] = (g.cumsum(0).cumsum(1), R_, C_)
    out = set()
    for pid, sheet, arr, tree, rl in idx[book]:
        hit = np.zeros(len(arr), dtype=bool)
        for sid, sh, r1, r2, c1, c2 in rl:
            if sid not in grids:
                continue
            P, R_, C_ = grids[sid]
            a1, a2 = np.clip(r1, 1, R_), np.clip(r2, 0, R_)
            b1, b2 = np.clip(c1, 1, C_), np.clip(c2, 0, C_)
            ok = (a1 <= a2) & (b1 <= b2) & (r1 <= R_) & (c1 <= C_)
            cnt = np.where(ok, P[a2, b2] - P[a1 - 1, b2] - P[a2, b1 - 1] + P[a1 - 1, b1 - 1], 0)
            hit |= cnt > 0
        for (r, c) in arr[hit].tolist():
            out.add((pid, sheet, r, c))
    return out


def main(resp, outp):
    t0 = time.time()
    RC.setup(os.path.join(S, "jcat_work", "scan.sqlite3"), os.path.join(S, "conv", "instances.pkl"))
    idx = build_index()
    print("index", {b: len(v) for b, v in idx.items()}, round(time.time() - t0), "s", flush=True)
    trees = {(pid, sheet): tree for b, lst in idx.items() for pid, sheet, arr, tree, rl in lst}
    result = {}
    for eq, pids in TARGETS.items():
        rec = dict(levels=[], by_eq=collections.Counter(), closure=0)
        cells_by_book = collections.defaultdict(set)
        tcells = []
        for pid in pids:
            for (book, sheet), arr in RC.DATA["instances"][pid].items():
                sh = RC.STORE.sheet(book, sheet)
                for r, c in arr.tolist():
                    cells_by_book[book].add((sh.sid, r, c))
                    tcells.append((pid, book, sheet, r, c))
        closure = collections.OrderedDict()
        for book, tg in cells_by_book.items():
            frontier, seen, level = set(tg), set(tg), 0
            while frontier and level < 30:
                level += 1
                cons = consumers(idx, book, frontier)
                new = set()
                for pid, sheet, r, c in cons:
                    sid = RC.STORE.sheet(book, sheet).sid
                    if (sid, r, c) not in seen:
                        seen.add((sid, r, c))
                        new.add((sid, r, c))
                        closure[(book, pid, sheet, r, c)] = level
                        rec["by_eq"][RC.DATA["patterns"][pid]["eq"]] += 1
                if len(rec["levels"]) < level:
                    rec["levels"].append(0)
                rec["levels"][level - 1] += len(new)
                frontier = new
        rec["closure"] = len(closure)
        print(eq, "closure", len(closure), "levels", rec["levels"], round(time.time() - t0), "s", flush=True)
        result[eq] = dict(rec=rec, closure=closure, tcells=tcells)
    pickle.dump(result, open(outp, "wb"))
    # ---- substitution and sensitivity
    R8 = pickle.load(open(resp, "rb")) if os.path.exists(resp) else {}
    for eq, d in result.items():
        closure = d["closure"]
        imp = {}
        for mode in ("A", "B", "ulp+", "ulp-"):
            changes = collections.defaultdict(dict)
            n_sub = 0
            for pid in TARGETS[eq]:
                p = RC.DATA["patterns"][pid]
                for (book, sheet), arr in RC.DATA["instances"][pid].items():
                    sh = RC.STORE.sheet(book, sheet)
                    if mode in ("A", "B"):
                        ast = fx.Parser(fx.tokenize(p["text"])).parse()
                        tree = X.prepare(ast, p["row"], RC.col_num(p["col"]), RC.STORE, book, sheet)
                        b = builder(book, sheet, arr[:, 0], arr[:, 1], mode)
                        v = b.finish(b.ev(tree))
                        got, _, _ = b.run(v)
                    for i, (r, c) in enumerate(arr.tolist()):
                        key = r * KEY_SHIFT + c
                        old = sh.values.get(key)
                        if mode in ("A", "B"):
                            new = got[i]
                            if new == "<missing>" or same(new, old)[0]:
                                continue
                        else:
                            if not isinstance(old, float) or isinstance(old, bool) or old == 0.0 or not math.isfinite(old):
                                continue
                            new = math.nextafter(old, math.inf if mode == "ulp+" else -math.inf)
                        changes[sh.sid][key] = new
                        n_sub += 1
            changed = collections.Counter()
            examples = []
            if n_sub:
                ost = OverlayStore(RC.STORE, dict(changes))
                ordered = sorted(closure.items(), key=lambda kv: kv[1])
                for _pass in range(2):
                    for (book, pid, sheet, r, c), lev in ordered:
                        X._INDEX_CACHE.clear(); X._SUMIF_CACHE.clear()
                        try:
                            val = X.evaluate(trees[(pid, sheet)], ost, book, sheet, r, c)
                        except Exception as e:
                            val = Err(15)
                        sid = RC.STORE.sheet(book, sheet).sid
                        ost.changes.setdefault(sid, {})[r * KEY_SHIFT + c] = val if not isinstance(val, list) else val
                for (book, pid, sheet, r, c), lev in ordered:
                    sh = RC.STORE.sheet(book, sheet)
                    key = r * KEY_SHIFT + c
                    new = ost.changes.get(sh.sid, {}).get(key)
                    old = sh.values.get(key)
                    if same(new, old)[0]:
                        continue
                    if isinstance(new, float) and isinstance(old, float) and not isinstance(old, bool) and math.isfinite(old) and old != 0.0 \
                            and abs(new - old) <= 8 * math.ulp(old):
                        changed["proportional (<= 8 ulp)"] += 1
                        continue
                    changed["changed"] += 1
                    changed[RC.DATA["patterns"][pid]["eq"]] += 1
                    if len(examples) < 6:
                        examples.append((book, sheet, r, c, RC.DATA["patterns"][pid]["eq"], repr(old)[:40], repr(new)[:40]))
            imp[mode] = dict(substituted=n_sub, changed=dict(changed), examples=examples)
            print(eq, mode, "substituted", n_sub, dict(changed), examples[:2], round(time.time() - t0), "s", flush=True)
        d["impact"] = imp
        pickle.dump(result, open(outp, "wb"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
