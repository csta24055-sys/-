"""Compares the JSON results of two runs (two ``results`` folders) after removing the run times.

    python3 -B -m checks.compare_results <results A> <results B> <commit of B> [file names ...]

Writes ``<results A>/reproduction_check.json``. Used to confirm that a clean checkout of a commit regenerates
the saved results (REPRODUCE.md section 4).
"""
import json
import os
import sys

sys.dont_write_bytecode = True


def strip(x):
    if isinstance(x, dict):
        return {k: strip(v) for k, v in x.items() if not k.startswith("seconds")}
    if isinstance(x, list):
        return [strip(v) for v in x]
    return x


def main(argv):
    a, b, commit = argv[0], argv[1], argv[2]
    names = argv[3:] or sorted(n for n in os.listdir(b) if n.endswith(".json") and n != "reproduction_check.json")
    rows = []
    for n in names:
        pa, pb = os.path.join(a, n), os.path.join(b, n)
        if not (os.path.exists(pa) and os.path.exists(pb)):
            rows.append({"file": n, "equal": False, "why": "missing on one side"})
            continue
        ja, jb = strip(json.load(open(pa))), strip(json.load(open(pb)))
        rows.append({"file": n, "equal": ja == jb})
    doc = {"commit_checked_out": commit, "compared": rows, "all_equal": all(r["equal"] for r in rows),
           "note": "results of a clean checkout of the commit, re-run from scratch, against the saved results; run times removed"}
    with open(os.path.join(a, "reproduction_check.json"), "w") as f:
        json.dump(doc, f, indent=1)
    for r in rows:
        print("%-44s %s" % (r["file"], "equal" if r["equal"] else "DIFFERENT"))
    print("all equal:", doc["all_equal"])
    return 0 if doc["all_equal"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
