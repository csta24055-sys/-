import os, sys, json
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
import decision as d
import numpy as np
# 1) STEP5の仮説の確率を変えると結果が変わる(実データの反映)
d.rng = np.random.default_rng(1); d.N = 8000
rows_a, _ = d.run()
d.rng = np.random.default_rng(1)
rows_b, _ = d.run(hyp_weights={"H1": 0.0, "H2": 0.0, "H3": 1.0, "H4": 0.0})
ea = np.mean([r["EU"]["A"] for r in rows_a]); eb = np.mean([r["EU"]["A"] for r in rows_b])
assert abs(ea - eb) > 0.01, (ea, eb)
# 2) 同じ乱数の種なら再現する
d.rng = np.random.default_rng(1)
rows_c, _ = d.run()
assert abs(np.mean([r["EU"]["E"] for r in rows_c]) - np.mean([r["EU"]["E"] for r in rows_a])) < 1e-12
# 3) A と D は INPEX に届く結果が同一 → 期待効用の差はモンテカルロ誤差の範囲
diff = max(abs(r["EU"]["A"] - r["EU"]["D"]) for r in rows_a)
assert diff < 1e-12, diff   # 共通乱数法により A と D は完全に一致する
print("DECISION TESTS PASSED", round(ea, 4), round(eb, 4), round(diff, 5))
