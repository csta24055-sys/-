# Benchmark (G4): direct Σ/knots vs circuit paths

**Verdict: representational value only. No circuit path is faster than the best direct baseline, and no smaller state was found that keeps the information.**

Integration run: `code/bench_int.py` → `results/benchmark.json`, at HEAD `2ae99ce`, on CPython 3.13.18 x86_64. Times are the median of 5 runs (3 runs or 1 run for the slow rows) with `time.perf_counter`. Memory is the `tracemalloc` peak of one separate run, and it includes the output containers. All numbers come from one machine and one session. They are not a statistical benchmark.

## Φ: P0, right convention; 11 contract points + 20,000 uniform k/1e6 in [0,60), seed 20261124
| method | µs/point | ops / state | memory peak | exact? |
|---|---|---|---|---|
| (a) closed form `100+4t+20⌊t/10⌋+35⌊t/20⌋`, Fraction | 4.41 | ~9 ops/query (D's count); state (0,0,0,0) with a floor readout | 2.4 MB | yes |
| (a′) same, float | 0.12 | — | 0.65 MB | max error 5.7e-14 kg |
| (b) knots + bisect, Fraction | **3.10** | 7 knots → (0,0,0,7) | 2.4 MB | yes |
| (c) route D ledger oracle, per query | 91.2 | rebuilds a ~30-event ledger per call | 0.27 MB | yes (oracle) |
| (d) integration hybrid, charge, one sorted sweep | 18.9 | 20,009 segments + 6 event instants (9 item firings) per sweep; (3,0,2,0) | 4.4 MB | yes |
| (d′) integration hybrid, joule, one sorted sweep | 21.8 | same; (4,0,2,0) | 5.7 MB | yes |
| (e) integration hybrid, per query from t=0 | 54.7 | 6 segments + 5 events at t=59 | 0.26 MB | yes |

The best circuit path (d) is **6.1× slower** than knots+bisect and **4.3× slower** than the Fraction closed form.

Route and D numbers on their own point sets agree in direction:
- D (100,011 points): hybrid sweep 12.4 vs knots 3.49 µs/pt (3.6×).
- A (2,000 points): R1 47.1, R3 15.2 vs closed form 11.8 µs/pt.
- E (1,000 points): sorted sweep 17.5 vs closed form 4.3 µs/pt.
- Fixed-step integration is faster per point (D: 0.43–1.24 µs) but **wrong by a full 20/55 kg** at event instants (D-18, E-5f). It is therefore not a valid competitor.

## Ψ: EV9 `SYN-RC-hospital-M-T30-seed571520556`, 200 random T in (0,60] (all in domain), seed 20261125
| method | ms per T | total for 200 T | notes |
|---|---|---|---|
| (p) composed circuit (B netlists + summing node), one sorted sweep, build included | 5.10 | 1.02 s | 7.0 MB peak |
| (p1) composed circuit, fresh build + sweep per T (random access) | 444 | — | 10 T |
| (q) msp `unified.System.at(T)` (built once) | 17.7 | 3.5 s | 4.8 MB peak (20 T) |
| (r) refcalc per T | 377 | (75 s) | computes all 70 units and every output: more work than SUM-03 |
| (s) canon KF exact knot form (built once, 0.75 s) | **0.0070** | 0.75 s incl. build | 30,706 terms |

- **Agreement on the same 200 T:** composed vs msp ≤5.5e-16 and composed vs canon ≤2.1e-16. No information is lost, and no size is gained.
- **Speed:** the composed sweep beats msp-per-T and refcalc-per-T only because those recompute a full model at each T. Against the knot form, the best direct baseline:
  - it is about **730× slower per query**;
  - for a 200-point sorted sweep the totals are comparable (1.02 s vs 0.75 s including the knot build);
  - for random access the knot form wins by about 6×10⁴× (444 ms vs 0.007 ms per T).
  - This matches D-23 / H-B4: a time–memory trade-off, no speed gain.
- **Size (EV9):**
  - composed netlists: B3-01 12,123 primitives, B4-02 11,048, B6-03/B7-04/EL 522 each, B5-01 2;
  - refrigerant automaton: 1,143 primitives, state tuple (160, 81, 371, 482);
  - total about 25.9k primitives, against 30,706 canon terms.
  - These are the same order (H-B4 not refuted). The counts use different units (primitives vs terms), so no reduction is claimed.

## State-count conclusions (Gate 3/4)
- **Φ:**
  - The hybrid needs (3,0,2,0) for P0. A single clock R3 (2,0,2,0) is exact for the known P0 schedule (A-8).
  - Merging clock capacitors loses events for every period (A-11, D-11): smaller, but not a reduction.
  - Under an online reset, ≥2 continuous states is [H] (D-9).
  - A single accumulator works only with an external schedule table that grows with the horizon (D-19).
- **Ψ:**
  - Rank 1 for the total does not mean one capacitor; every waveform still needs its knot schedule (C-3, D-26).
  - The refrigerant automaton stores about as many numbers as the merged knot form (D-23).

## Not measured
- SPICE or a physical circuit.
- Fixed-step simulation of the Ψ netlists.
- Memory of canon KF.
- Any timing on another machine or Python version.
