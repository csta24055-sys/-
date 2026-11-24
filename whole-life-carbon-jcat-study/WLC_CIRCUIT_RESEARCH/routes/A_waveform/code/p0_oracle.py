"""Route A oracle: exact closed forms (fractions.Fraction) for pilots P0/P1/P2/Px.

All values are ILLUSTRATIVE (fictional) kgCO2e; t in years (physical time t, or
horizon T for the 'orig' convention). This module deliberately contains no circuit
code: it is the independent closed-form oracle against which circuit_a.py is tested.

Event-inclusion conventions (for an event at time tau, evaluated at t):
  RIGHT : counted iff tau <= t          (right-continuous, the declared P0 pilot rule)
  LEFT  : counted iff tau <  t          (left-continuous)
  ORIG  : counted iff tau <  t*(1-eps)  (original research rule, eps = 1e-9; this is a
          HORIZON rule for C(T), used here only on P0 data to compare conventions)
Initial value G0 is an initial condition (present at t=0 under every convention).
"""
from fractions import Fraction as F
import math

EPS = F(1, 10**9)
RIGHT, LEFT, ORIG = "right", "left", "orig"
CONVENTIONS = (RIGHT, LEFT, ORIG)

# P0 data (07_SHARED_CONTRACT, illustrative)
G0, R_OP = F(100), F(4)
C_A, A_A = F(10), F(20)   # air-con period [yr], charge [kgCO2e]
C_P, A_P = F(20), F(35)   # pipework period [yr], charge [kgCO2e]


def included(tau, t, conv, eps=EPS):
    """Is a single event at time tau counted at t under `conv`? (exact)"""
    tau, t = F(tau), F(t)
    if conv == RIGHT:
        return tau <= t
    if conv == LEFT:
        return tau < t
    if conv == ORIG:
        return tau < t * (1 - eps)
    raise ValueError(conv)


def n_periodic(t, c, conv, offset=F(0), eps=EPS):
    """Number of events at offset + k*c (k>=1 if offset==0 else k>=0) counted at t.

    Closed form, NOT a loop:
      RIGHT: floor(s)+[offset>0],  LEFT/ORIG: ceil(s)-1+[offset>0],  s=(t' - offset)/c,
    with t' = t (RIGHT/LEFT) or t(1-eps) (ORIG), and 0 when s is below the first event.
    """
    t, c, offset = F(t), F(c), F(offset)
    tt = t * (1 - eps) if conv == ORIG else t
    s = (tt - offset) / c
    first = 0 if offset > 0 else 1          # index of first event in units of s
    if conv == RIGHT:
        if s < first:
            return 0
        return math.floor(s) + (1 if offset > 0 else 0)
    # LEFT and ORIG are strict
    if s <= first:
        return 0
    return math.ceil(s) - 1 + (1 if offset > 0 else 0)


def g_p0(t, conv=RIGHT, eps=EPS):
    """P0: G(t) = 100 + 4t + 20 N_10(t) + 35 N_20(t)  (exact Fraction)."""
    t = F(t)
    return G0 + R_OP * t + A_A * n_periodic(t, C_A, conv, eps=eps) + A_P * n_periodic(t, C_P, conv, eps=eps)


def g_p1(t, conv=RIGHT, policy="substitute", A_R=F(50), tau_R=F(20)):
    """P1: renovation at tau_R=20 with A_R=50.

    substitute : the renovation's 50 REPLACES the individual AC(20)+pipe(35) charges
                 that fall at tau_R (no double count). Since those coincide with tau_R
                 and share its inclusion rule: G = G_P0 - 55*[R counted] + 50*[R counted].
    additional : renovation charge is incurred on top: G = G_P0 + 50*[R counted].
    Clocks restart at tau_R; with tau_R=20 this coincides with the nominal resets.
    """
    base = g_p0(t, conv)
    ind = 1 if included(tau_R, t, conv) else 0
    if policy == "substitute":
        return base - (A_A + A_P) * ind + A_R * ind
    if policy == "additional":
        return base + A_R * ind
    raise ValueError(policy)


def g_p2(t, conv=RIGHT, r_before=F(4), r_after=F(3)):
    """P2: operating rate 4 on [0,10), 3 on [10,inf) (switch at FIRST AC replacement,
    physical time 10; the rate switch is a kink so it is convention-free). Events as P0.
    Defined for RIGHT and LEFT only (ORIG on P2 is not declared: NOT_RUN)."""
    if conv not in (RIGHT, LEFT):
        raise ValueError("P2 defined for right/left only")
    t = F(t)
    t1 = C_A
    op = r_before * min(t, t1) + r_after * max(t - t1, F(0))
    return G0 + op + A_A * n_periodic(t, C_A, conv) + A_P * n_periodic(t, C_P, conv)


def g_px(t, conv=RIGHT, t_early=F(7)):
    """Px: AC replaced early at t=7 (charge 20) and ONLY the AC clock restarts there;
    AC events at 7,17,27,...; pipework at 20,40,60,... Defined for RIGHT and LEFT."""
    if conv not in (RIGHT, LEFT):
        raise ValueError("Px defined for right/left only")
    t = F(t)
    return G0 + R_OP * t + A_A * n_periodic(t, C_A, conv, offset=t_early) + A_P * n_periodic(t, C_P, conv)


# --- float versions (to expose the float knife-edge; not an oracle) ---
def g_p0_float(t, conv=RIGHT, eps=1e-9):
    t = float(t)
    tt = t * (1.0 - eps) if conv == ORIG else t

    def n(c):
        s = tt / c
        if conv == RIGHT:
            return math.floor(s) if s >= 1 else 0
        return (math.ceil(s) - 1) if s > 1 else 0
    return 100.0 + 4.0 * t + 20.0 * n(10.0) + 35.0 * n(20.0)


CONTRACT_POINTS = ["0", "1", "9.999999", "10", "10.000001", "19.999999", "20",
                   "20.000001", "30", "40", "60"]
KNIFE_POINTS = ["10.000000005", "10.00000002"]   # inside / outside the ORIG band
KNIFE_EDGE_UNDEFINED = "10.00000001"            # float knife-edge (recorded, not asserted for floats)
