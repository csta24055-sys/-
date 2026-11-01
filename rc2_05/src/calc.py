"""RC構造Ⅱ 第5回演習: FPC梁の必要プレストレス力・導入張力・PC鋼材本数（SymPyで記号的に求解・検算）.
符号: 圧縮を正、引張を負。PC鋼材は図心より下側（引張縁側）に偏心 e。
"""
import json, math, sys
import sympy as sp

# ---- 条件（課題指定） ----
b, D = 300, 600          # mm
M_kNm = 36               # kN·m
e = 100                  # mm（偏心距離）
eta = sp.Rational(60, 100)   # 有効率（有効プレストレス力 = 0.6 × 導入張力）
Py1 = 156                # kN/本（12.7φ SWPR7BL 降伏荷重相当, 講義資料値）
Pu1 = 183                # kN/本（同 引張荷重, JIS G3536 規格値, 参考）

def solve():
    P = sp.symbols('P', positive=True)                 # 有効プレストレス力 [N]
    A = sp.Integer(b * D)                               # mm2
    Z = sp.Rational(b * D**2, 6)                        # mm3
    M = sp.Integer(M_kNm) * 10**6                       # N·mm
    sig_bot = -M / Z + P / A + P * e / Z                # 引張縁（下縁）
    sig_top = +M / Z + P / A - P * e / Z                # 圧縮縁（上縁）
    Psol = sp.solve(sp.Eq(sig_bot, 0), P)
    assert len(Psol) == 1
    Pv = Psol[0]                                        # N
    Pe = Pv / eta                                       # 導入張力 N
    N_exact = Pe / (Py1 * 1000)
    N = math.ceil(N_exact)
    r = dict(
        A=int(A), Z=int(Z), M_Nmm=int(M),
        M_over_Z=float(M / Z),
        P_over_A_coef=str(1 / A), Pe_over_Z_coef=str(e / Z),
        P_N=int(Pv), P_kN=float(Pv / 1000),
        P_over_A=float(Pv / A), PeZ=float(Pv * e / Z),
        Pe_N=int(Pe), Pe_kN=float(Pe / 1000),
        N_exact=float(N_exact), N=N,
        N_if_183=math.ceil(float(Pe) / (Pu1 * 1000)),
        # 再代入検算
        sig_bot_check=float(sig_bot.subs(P, Pv)),
        sig_top_service=float(sig_top.subs(P, Pv)),
        sig_top_transfer=float((Pe / A - Pe * e / Z)),  # 導入直後・自重等無視
        sig_bot_transfer=float((Pe / A + Pe * e / Z)),
        provided_Pe_kN=int(N * Py1), provided_P_kN=float(N * Py1 * eta),
        sig_bot_provided=float(sig_bot.subs(P, N * Py1 * 1000 * eta)),
        kern=float(Z / A),
    )
    return r

def crosscheck(r):
    """SymPyを使わない別解（手計算と同じ流れ：P = (M/Z)/(1/A + e/Z)）と単位系kN・mでの別ルート."""
    A = b * D; Z = b * D * D / 6
    P1 = (M_kNm * 1e6 / Z) / (1 / A + e / Z)
    # kN・m単位での別ルート
    A_m = 0.3 * 0.6; Z_m = 0.3 * 0.6**2 / 6; e_m = 0.1
    P2 = (M_kNm / Z_m) / (1 / A_m + e_m / Z_m)          # kN (kN/m2 基準)
    # コア（核）による別解: e=Z/Aのとき P/A = P e/Z ⇒ 2P/A = M/Z
    P3 = (M_kNm * 1e6 / Z) * A / 2
    for v in (P1, P2 * 1000, P3):
        assert abs(v - r['P_N']) < 1e-6, v
    assert abs(r['sig_bot_check']) < 1e-12
    assert r['N'] == 2 and r['N_exact'] > 1
    return dict(P_route_mm=P1, P_route_kNm_kN=P2, P_route_kern=P3)

if __name__ == '__main__':
    r = solve(); r['crosscheck'] = crosscheck(r)
    out = sys.argv[1] if len(sys.argv) > 1 else 'calc.json'
    json.dump(r, open(out, "w"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps(r, ensure_ascii=False, indent=1, default=float))
