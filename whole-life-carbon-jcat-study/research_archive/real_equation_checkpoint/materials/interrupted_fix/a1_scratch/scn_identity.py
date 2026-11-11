"""Are the generated scenarios bit-identical before and after the change? (old synth package from git HEAD vs working tree)"""
import hashlib, importlib, json, sys
def digest(root):
    sys.path.insert(0, root)
    for name in [m for m in sys.modules if m == "synth" or m.startswith("synth.")]:
        del sys.modules[name]
    synth = importlib.import_module("synth")
    population = importlib.import_module("synth.population")
    model = importlib.import_module("synth.model")
    out = {}
    def add(key, scn):
        out[key] = hashlib.sha256(json.dumps(synth.to_dict(scn), sort_keys=True, default=str).encode()).hexdigest()
    for scn in population.standard_benchmark()[:2]:
        add("bench-" + scn.meta.size_class, scn)
    for name, scn in population.edge_cases():
        add("edge-" + name, scn)
    for i, scn in enumerate(population.verification_population(60, seed=20261111, max_size="M")):
        add(f"pop-{i}", scn)
    combos = [(s, u) for s in model.STRUCTURES for u in model.USES]
    for k in range(60):
        s, u = combos[k % len(combos)]
        add(f"dirty-{k}", synth.make_scenario(1000 + k, s, u, "S", (30.0, 60.0, 62.5)[k % 3], dirty=True))
    sys.path.remove(root)
    return out
old = digest(sys.argv[1]); new = digest(sys.argv[2])
common = set(old) & set(new)
print("scenarios compared:", len(common), "| identical:", sum(old[k] == new[k] for k in common), "| only in new:", sorted(set(new) - set(old)), "| only in old:", sorted(set(old) - set(new)))
print("different:", sorted(k for k in common if old[k] != new[k])[:10])
