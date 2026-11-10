#!/usr/bin/env python3
"""Recompute every derived number used in the reports (research tooling only).

Three blocks, each kept separate so that observed and assumed inputs never mix:

1. Wilson 95% intervals for survey proportions that have a known sample size.
   The interval reflects sampling error only; it does NOT correct selection bias.
2. What-if arithmetic on a published benchmark (other companies' apps). It shows
   how many paying users a given number of installs would yield IF this app
   behaved like the benchmark median. It is not a forecast for this app.
3. A minimax-regret comparison of product options A-G under four scenarios.
   Every payoff is an ordinal judgement (-2..+2) written down with its reason in
   scripts/decision_inputs.json. The result is conditional on those judgements;
   the sensitivity run changes every cell by +/-1 to show how fragile it is.
   No probabilities are produced.

Usage: python3 scripts/quant_recompute.py   (writes research/quant_outputs.json)
"""
from __future__ import annotations
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def wilson(p: float, n: int, z: float = 1.959964) -> tuple[float, float]:
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return centre - half, centre + half


def intervals() -> list[dict]:
    out = []
    with (ROOT / 'registry' / 'quant_results.csv').open(encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            # only proportions of respondents; counts of apps or models are not binomial trials
            if r['evidence_category'] != 'OBSERVED' or r['unit'] != '%' or not r['model_id'].startswith('M_WILSON95'):
                continue
            try:
                n = int(r['sample_n']); p = float(r['estimate']) / 100
            except ValueError:
                continue
            lo, hi = wilson(p, n)
            out.append({'result_id': r['result_id'], 'estimate_pct': float(r['estimate']), 'n': n,
                        'wilson95_low_pct': round(lo * 100, 1), 'wilson95_high_pct': round(hi * 100, 1),
                        'recorded_low': r['ci_lower'], 'recorded_high': r['ci_upper']})
    return out


def benchmark_what_if() -> dict:
    # Published medians for OTHER apps (source S040); installs are hypothetical inputs.
    rates = {'freemium_d35': 0.021, 'hard_paywall_d35': 0.107, 'north_america_median_d35': 0.026}
    grid = [1000, 5000, 20000]
    return {'label': 'ASSUMPTION_ONLY', 'source_of_rates': 'S040',
            'payers_if_this_app_matched_benchmark': {k: {str(i): round(i * v, 1) for i in grid} for k, v in rates.items()}}


def regret(payoff: dict[str, dict[str, int]], scenarios: list[str]) -> tuple[dict[str, int], list[str]]:
    best = {s: max(payoff[o][s] for o in payoff) for s in scenarios}
    worst = {o: max(best[s] - payoff[o][s] for s in scenarios) for o in payoff}
    m = min(worst.values())
    return worst, sorted(o for o, v in worst.items() if v == m)


def decision() -> dict:
    d = json.loads((Path(__file__).parent / 'decision_inputs.json').read_text(encoding='utf-8'))
    scenarios = list(d['scenarios'])
    payoff = {o: {s: d['payoffs'][o][s]['score'] for s in scenarios} for o in d['options']}
    worst, winners = regret(payoff, scenarios)
    counts = {o: 0 for o in payoff}
    variants = 0
    for o in payoff:
        for s in scenarios:
            for delta in (-1, 1):
                v = payoff[o][s] + delta
                if not -2 <= v <= 2:
                    continue
                alt = {k: dict(x) for k, x in payoff.items()}
                alt[o][s] = v
                _, w = regret(alt, scenarios)
                variants += 1
                for x in w:
                    counts[x] += 1
    drop = {}
    for s in scenarios:
        rest = [x for x in scenarios if x != s]
        drop[s] = regret(payoff, rest)[1]
    best = {s: max(payoff[o][s] for o in payoff) for s in scenarios}
    mean = {o: round(sum(best[s] - payoff[o][s] for s in scenarios) / len(scenarios), 2) for o in payoff}
    return {'label': 'ASSUMPTION_ONLY', 'not_a_probability': True, 'max_regret': worst, 'minimax_regret_set': winners,
            'mean_regret_if_scenarios_equally_weighted_reference_only': mean,
            'sensitivity_single_cell_variants': variants,
            'times_in_minimax_set_across_variants': counts,
            'minimax_set_if_one_scenario_removed': drop}


def main() -> None:
    out = {'wilson_intervals': intervals(), 'benchmark_what_if': benchmark_what_if(), 'decision': decision()}
    (ROOT / 'research' / 'quant_outputs.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
