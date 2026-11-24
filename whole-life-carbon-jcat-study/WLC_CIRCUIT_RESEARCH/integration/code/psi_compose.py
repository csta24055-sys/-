"""G4 integration -- Psi side (sweep variable = evaluation horizon T, output C(T)).

DOCUMENTED COMPOSITION (not a re-implementation of the kernels):
  per-unit signals V_u(T)  <- route B's D-verified 𝒢 netlists, loaded read-only from B's grammar.py:
      * 12 constants (A13-01, A13-03, A13-04, X-01, A4-01, A4-02, A5-04, C1-01..C4-01, X-14) as DC sources
        whose amplitudes are msp P1 scalars (specs.system.CONST_VALUE);
      * B3-01, B4-02, B5-01, B6-03, B7-04: kernel netlists (atom theta_eps, year cell clip, gated cell, density
        integrator) on the msp P1 amplitude pieces (external T-independent table);
      * B2-01: gain block (share rho_B2 in [0,1], else 0) on the EL year-cell netlist;
      * B1-02/B1-03/B1-04: B's late-reset sample-hold refrigerant automaton from RAW scenario inputs.
  composition <- route C's verified rule (H-C1 / gate X4), re-written here: one weighted summing node per stage
      over the 22 COMP rows read from WLC_THEORY_RESEARCH_BASE/data/units70.json (sign sigma, beta in {1, iota_B2}),
      excluded stages absent, then one total summing node.  C(T) = sum_s iota_s sum_u sigma beta V_u(T).

What is new here relative to the routes: the two verified halves are joined in ONE object and evaluated on
scenarios that no route used (evaluation_set EV2, EV9; plus EV9 without B2 to exercise beta = iota_B2), against
refcalc (the declared reference, 03 S3.2/S3.4).  Agreement is float agreement [F], not equality.

Declared domain (Psi): fictional synth scenarios, 0 < T <= H (=130), (scenario, T) inside
tstudy.scenarios.valid_domain (knife window excluded); the original event rule tau < T(1-eps).
The refrigerant automaton also matches inside the open band (K, sw(tau)) (B/D [F]); this is recorded, not relied on.
"""
from __future__ import annotations

import math
import time

import int_common as IC

PIECE_UNITS = ("B3-01", "B4-02", "B5-01", "B6-03", "B7-04")
REFRIG_UNITS = ("B1-02", "B1-03", "B1-04")


def comp_rows() -> list:
    rows = []
    for u in IC.units70()["units"]:
        for c in u.get("composition") or []:
            rows.append((u["id"], c["stage"], int(c["sign"]), str(c["beta"])))
    return rows


class PsiComposed:
    def __init__(self, scn, cell_mode: str = "clip"):
        fz = IC.frozen()
        self.B = IC.route_b_grammar()
        self.scn = scn
        self.sy = fz["unified"].System(scn)
        self.H = int(self.sy.H)
        self.cell_mode = cell_mode
        self.inc = set(scn.boundary.included_lifecycle_stages)
        self.rows = comp_rows()
        self.consts = {uid: float(self.sy.eng.col("S", col).v[0]) for uid, col in fz["system"].CONST_VALUE.items()}
        share = scn.operation.facility_management_ratio
        self.share_ok = share is not None and 0.0 <= share <= 1.0
        self.share = share if self.share_ok else 0.0
        provided = set(self.consts) | set(PIECE_UNITS) | set(REFRIG_UNITS) | {"B2-01"}
        comp_units = {r[0] for r in self.rows}
        missing = comp_units - provided
        if missing:
            raise RuntimeError(f"COMP units without a signal source: {sorted(missing)}")
        self.comp_units = comp_units

    def sweep(self, Ts) -> dict:
        """One sorted sweep over the horizons Ts. Returns {T: {"units": V, "stages": {...}, "total": C}}."""
        Ts = sorted({float(t) for t in Ts})
        t0 = time.perf_counter()
        V = {T: dict(self.consts) for T in Ts}
        self.netcounts = {}
        for unit in PIECE_UNITS:
            res, net, nk = self.B.eval_kernel(self.sy.pieces.get(unit, []), self.H, Ts, cell_mode=self.cell_mode)
            self.netcounts[unit] = {"netlist": net.counts(), "pieces_by_kind": nk, "evals": net.evals}
            for T in Ts:
                V[T][unit] = res[T]["total"]
        res, net, nk = self.B.eval_kernel(self.sy.pieces.get("EL", []), self.H, Ts, cell_mode=self.cell_mode)
        self.netcounts["EL->B2-01"] = {"netlist": net.counts(), "pieces_by_kind": nk, "evals": net.evals}
        for T in Ts:
            V[T]["B2-01"] = res[T]["total"] * self.share          # gain block k = rho_B2 (0 if invalid)
        rc = self.B.RefrigerantCircuit(self.scn, self.H, late_reset=True)
        rr = rc.sweep(Ts)
        self.netcounts["refrigerant"] = {"primitives": dict(rc.prim), "state_tuple": rc.state_tuple(),
                                         "unexpected": rc.unexpected}
        out = {}
        for T in Ts:
            V[T].update({u: rr[T][u] for u in REFRIG_UNITS})
            stage = {}
            terms = {}
            for uid, s, sign, beta in self.rows:
                if s not in self.inc:
                    continue
                if beta == "1":
                    b = 1.0
                elif beta == "iota_B2":
                    b = 1.0 if "B2" in self.inc else 0.0
                else:
                    raise ValueError(f"unknown beta {beta!r}")
                terms.setdefault(s, []).append(sign * b * V[T][uid])  # gain block
            for s, ts in terms.items():
                stage[s] = math.fsum(ts)                              # stage summing node
            out[T] = {"units": V[T], "stages": stage, "total": math.fsum(stage.values())}  # total node
        self.seconds = time.perf_counter() - t0
        return out
