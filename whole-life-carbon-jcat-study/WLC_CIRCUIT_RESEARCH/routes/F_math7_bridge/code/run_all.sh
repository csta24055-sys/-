#!/usr/bin/env bash
# Route F: local five-Python-engine run of restricted Math IR 0.1 inputs.
# Usage: bash code/run_all.sh SCRATCH_DIR
# Never dispatches GitHub Actions, never calls math7-full, never writes /opt/math7.
set -uo pipefail
export PYTHONDONTWRITEBYTECODE=1
F="$(cd "$(dirname "$0")/.." && pwd)"
SCR="${1:?scratch dir required}"
mkdir -p "$SCR" "$F/results"
cd /tmp  # keep the interpreter's cwd outside the repository
math7-py -B "$F/code/build_inputs.py"
math7-py -B "$F/code/probe_ops.py" "$SCR"
math7-py -B - <<'PY' > "$F/results/engine_versions.txt"
import sys, sympy, numpy, scipy, mpmath, duckdb
print("python", sys.version.split()[0])
for m in (sympy, numpy, scipy, mpmath, duckdb):
    print(m.__name__, m.__version__)
PY
for name in wlc_pilots_p0_p1_p2 wlc_route_e_identities negative_wrong_expected; do
  out="$SCR/out_$name"; rm -rf "$out"; res="$F/results/$name"; mkdir -p "$res"
  {
    for step in "prepare $F/inputs/$name.json $out" "verify-python $out" "audit-python $out"; do
      echo "\$ math7 $step"
      math7 $step 2>&1; echo "exit=$?"
    done
    echo "\$ math7-py -B code/check_results.py inputs/$name.json inputs/$name.expected.json <out> results/$name/expected_check.json"
    math7-py -B "$F/code/check_results.py" "$F/inputs/$name.json" "$F/inputs/$name.expected.json" \
      "$out" "$res/expected_check.json" 2>&1; echo "exit=$?"
  } > "$res/log.txt"
  for f in plan.json manifest.json result.json python_graph.json; do cp "$out/$f" "$res/$f"; done
  sed -e "s|$F|<F>|g" -e "s|$SCR|<scratch>|g" -i "$res/log.txt"
  echo "== $name"; grep -E '^(\$|exit=|PORTABLE|PASS tamper|ROUTE-F)' "$res/log.txt"
done
find "$F" -name __pycache__ -prune -exec rm -rf {} +
