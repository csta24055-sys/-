from h import *
for T, lives in ((300.0, [0.3, 7.5, 33.3]), (299.9, [1.0, 11.1]), (250.5, [0.5, 125.25, 250.5])):
    for seed in (2, 3):
        s = mk(seed, T, table_length=301, service_life_choices=lives, replacement_cycle=lives[-1], reconstruction_scenario="REBUILD_IDENTICAL")
        r = check(s, f"T={T}")
        if not r: print(f"[T={T} seed {seed}] no difference")
for T, lives in ((1e-3, [1e-4, 3e-4]), (0.3, [0.1, 0.05]), (1.0, [0.999999999, 1.0, 0.5]), (1.0000001, [0.5, 1.0]), (59.9999999999, [20.0, 30.0, 59.9999999999, 12.0])):
    for seed in (2, 3):
        s = mk(seed, T, service_life_choices=lives, replacement_cycle=lives[0], reconstruction_scenario="REBUILD_IDENTICAL")
        r = check(s, f"T={T}")
        if not r: print(f"[T={T} seed {seed}] no difference (strict, no floor)")
