#!/usr/bin/env python3
"""証拠統合の性質テスト。python3 test_fusion.py が 0 で終われば合格。"""
import os, sys, shutil, tempfile, csv, importlib.util
H = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ef", os.path.join(H, "evidence_fusion.py")); ef = importlib.util.module_from_spec(spec); spec.loader.exec_module(ef)
it = lambda i, t, r, lin: {"id": i, "claim_type": t, "reliability": r, "lineage": lin}
prior = ef.fuse([])["H_high"]
# 1) 独立な2系統の一致は、同じ系統の2件より支持を強める
indep = ef.fuse([it("a", "three_high", .4, "L1"), it("b", "three_high", .4, "L2")])["H_high"]
dup = ef.fuse([it("a", "three_high", .4, "L1"), it("b", "three_high", .4, "L1")])["H_high"]
assert indep > dup > prior, (indep, dup, prior)
# 2) 同じ系統の転載をいくら増やしても、効果は 1/rho 倍で頭打ち（件数の足し算にならない）
many = ef.fuse([it(str(k), "three_high", .4, "L1") for k in range(200)], rho=0.9)["H_high"]
one = ef.fuse([it("a", "three_high", .4, "L1")], rho=0.9)["H_high"]
indep200 = ef.fuse([it(str(k), "three_high", .4, f"L{k}") for k in range(200)], rho=0.9)["H_high"]
assert many - one < 0.05, (many, one)        # 同一系統の転載200件は、1件からほぼ増えない
assert indep200 > 0.99, indep200             # 独立な200系統なら圧倒的になる
# 3) 信頼性0の情報源は事前分布を動かさない
z = ef.fuse([it("a", "three_high", 0.0, "L1"), it("b", "count_unrelated", 0.0, "L2")])
assert all(abs(v - 0.25) < 1e-9 for v in z.values()), z
# 4) 反対の証拠は支持を下げる
with_counter = ef.fuse([it("a", "three_high", .4, "L1"), it("c", "count_unrelated", .4, "L3")])["H_high"]
assert with_counter < ef.fuse([it("a", "three_high", .4, "L1")])["H_high"]
# 5) 非線形性：独立な一致が増えるほど、1件あたりの事後確率の伸びは逓減しつつ1に近づく
p = [ef.fuse([it(str(k), "three_high", .4, f"L{k}") for k in range(n)])["H_high"] for n in (1, 2, 4, 8)]
assert p[0] < p[1] < p[2] < p[3] < 1 and (p[1] - p[0]) > (p[3] - p[2]) / 4, p
# 6) 実データが結果に反映されている：reliability.csv の1行の型を変えると結果が変わる
tmp = tempfile.mkdtemp()
try:
    for d in ("step3", "step2", "step1"):
        shutil.copytree(os.path.join(H, "..", d), os.path.join(tmp, d))
    rel = os.path.join(tmp, "step3", "reliability.csv")
    rows = list(csv.DictReader(open(rel, encoding="utf-8")))
    base = ef.run()
    for r in rows:
        if r["id"] == "C07": r["claim_type"] = "count_unrelated"
    with open(rel, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    spec2 = importlib.util.spec_from_file_location("ef2", os.path.join(tmp, "step3", "evidence_fusion.py")); ef2 = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(ef2)
    changed = ef2.run()
    k = "r_scale=1.0|rho=0.5"
    assert abs(changed["sensitivity"][k]["H_none"] - base["sensitivity"][k]["H_none"]) > 1e-3, "データの変更が結果に反映されない"
finally:
    shutil.rmtree(tmp)
print("ALL TESTS PASSED")
