from h import *
s = mk(1)
r = check(s, "plain")
print("plain diffs:", len(r))
ref, full, tot = run3(s)
print(sorted(ref)[:80]); print(len(ref))
print({u: sorted(tot[u]) for u in tot if not u.startswith("_") and not tot[u]})
import inspect
print(inspect.signature(synth.make_scenario))
