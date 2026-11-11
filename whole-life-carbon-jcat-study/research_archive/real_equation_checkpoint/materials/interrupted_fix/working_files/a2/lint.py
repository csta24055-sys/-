"""Poor man's lint: compile, and report names that are loaded but never bound anywhere in a function or the module."""
import ast, builtins, sys
for path in sys.argv[1:]:
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    compile(src, path, "exec")
    module_names = set(dir(builtins))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            module_names.add(node.name)
        elif isinstance(node, ast.Import):
            module_names.update((a.asname or a.name).split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            module_names.update(a.asname or a.name for a in node.names)
    bound = set(module_names)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            bound.add(node.id)
        elif isinstance(node, ast.arg):
            bound.add(node.arg)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
    missing = sorted({(n.id, n.lineno) for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in bound})
    print(path, "unbound names:", missing)
    # per function: names loaded that are neither bound in the function (or an enclosing one) nor at module level
    def check(fn, outer):
        local = set(outer)
        for node in ast.walk(fn):
            if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                local.add(node.id)
            elif isinstance(node, ast.arg):
                local.add(node.arg)
            elif isinstance(node, (ast.FunctionDef,)) and node is not fn:
                local.add(node.name)
        mod_level = set(module_names)
        for node in tree.body:
            for sub in ast.walk(node) if not isinstance(node, (ast.FunctionDef, ast.ClassDef)) else []:
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                    mod_level.add(sub.id)
        bad = sorted({(n.id, n.lineno) for n in ast.walk(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
                      and n.id not in local and n.id not in mod_level})
        if bad:
            print("  in", fn.name, "not bound:", bad)
        # unused locals (assigned, never loaded) - informational
        loads = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        stores = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
        unused = sorted(stores - loads - {"_"})
        if unused:
            print("  in", fn.name, "assigned but never read:", unused)
        for node in ast.iter_child_nodes(fn):
            pass
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # enclosing scopes: approximate with all names bound in any enclosing function
            outer = set()
            for other in ast.walk(tree):
                if isinstance(other, ast.FunctionDef) and other is not node and any(n is node for n in ast.walk(other)):
                    for sub in ast.walk(other):
                        if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                            outer.add(sub.id)
                        elif isinstance(sub, ast.arg):
                            outer.add(sub.arg)
                        elif isinstance(sub, ast.FunctionDef):
                            outer.add(sub.name)
            check(node, outer)
