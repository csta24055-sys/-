#!/usr/bin/env python3
"""冷媒の漏洩の二時刻の核 h(t,s) の訂正を、D-08 の漸化式と厳密な有理数で照合する（本基盤の点検用、2026-11-17）。

対象：07_動的LCAと工程時間.md §5.4、08_証明と検証結果.md §1.3 の 18.REL-STATE。
架空の例示の入力だけを使う（実在の機器・建物のデータではない）。研究コードは読み込まない。標準ライブラリだけ。

漸化式（10_TRANSFORM_STUDY/11_UNIFIED_SYSTEM/DERIVATIONS.md@b93201e D-08）：
    u_k = chi_{k-1} m0 + (1 - chi_{k-1}) q u_{k-1},  u_0 = m0
    chi_k = 1  <=>  交換が年セル k に属する、 k_tau = max(1, ceil(tau (1 - eps))) - 1、eps = 1e-9（有理数）
年セル k = floor(t) の漏洩の率は r GWP u_k（ここでは r GWP = 1 とおく）。

訂正した形（本基盤）：u_{floor t} = m0 q^(floor t - k+(s*))、k+(0) = 0、k+(tau) = k_tau + 1、
    s* は k+(s) が floor t 以下で最大の初期化（初期の充填 s = 0 を含む）。
原典の形（18_DYNAMIC_LCA_EXTENSION/03_工程間の関係.md@09e0765 §4）：q^(floor t - floor s - 1)、s は t より前の最後の交換。

使い方：  python3 -B tools/check_refrigerant_kernel.py   （約 1 秒。固定の種で決定的）
"""
import sys

sys.dont_write_bytecode = True

import math  # noqa: E402
import random  # noqa: E402
from fractions import Fraction as Q  # noqa: E402

EPS = Q(1, 10 ** 9)
H = 60            # 例示の年数
N_SCEN = 400      # 無作為な交換列の数
N_T = 30          # 交換列ごとの t の数
SEED = 7


def year_cell(tau):
    return max(1, math.ceil(tau * (1 - EPS))) - 1


def main():
    rng = random.Random(SEED)
    n = bad_new = bad_src = 0
    n_int = 0
    for _ in range(N_SCEN):
        q = Q(rng.randint(1, 99), 100)
        m0 = Q(1)
        taus = set()
        for _ in range(rng.randint(0, 5)):
            if rng.random() < 0.5:
                taus.add(Q(rng.randint(1, H - 1)))                  # 整数の時刻
            else:
                taus.add(Q(rng.randint(100, 100 * (H - 1)), 100))   # 0.01 年刻みの時刻
        taus = sorted(taus)
        n_int += sum(1 for tau in taus if tau.denominator == 1)
        chi = [0] * (H + 1)
        for tau in taus:
            chi[year_cell(tau)] = 1
        u = [m0]
        for k in range(1, H + 1):
            u.append(chi[k - 1] * m0 + (1 - chi[k - 1]) * q * u[k - 1])
        for _ in range(N_T):
            t = Q(rng.randint(0, 100 * H - 1), 100)
            k = math.floor(t)
            n += 1
            kplus = max([0] + [year_cell(tau) + 1 for tau in taus if year_cell(tau) + 1 <= k])
            if m0 * q ** (k - kplus) != u[k]:
                bad_new += 1
            prev = [tau for tau in taus if tau < t]
            e = (k - math.floor(prev[-1]) - 1) if prev else (k - 1)   # 原典の形（s = 0 の初期の充填を含む）
            if e < 0 or m0 * q ** e != u[k]:
                bad_src += 1
    print(f"scenarios {N_SCEN}, points {n}, integer replacement times {n_int}")
    print(f"corrected kernel: mismatches {bad_new}")
    print(f"source form (floor t - floor s - 1): mismatches {bad_src}")
    return 0 if bad_new == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
