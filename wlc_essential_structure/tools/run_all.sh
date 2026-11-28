#!/usr/bin/env bash
# Re-run every step of this study. Arguments: <foundation checkout at 761da13> <theory-base checkout at 9416a1b>
set -euo pipefail
F=$(cd "$1" && pwd); TB=$(cd "$2" && pwd)
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1
python3 -I tools/freeze_baseline.py "$F" "$TB" 00_baseline/frozen_sources.json
python3 -I tools/build_ledger667.py "$F" 02_ledger667 > /dev/null
python3 -I tools/build_units70.py "$F" "$TB" 03_units70 04_graph > /dev/null
python3 -I tools/verify_families.py 08_verification/results/families_exact.json | tail -1
python3 -B tools/run_reconstruction.py "$F" 08_verification/results > 08_verification/results/reconstruction_log.txt
tail -1 08_verification/results/reconstruction_log.txt
python3 -B tools/independent_f4_refrigerant.py "$F" 08_verification/results/independent_f4_refrigerant.json | tail -1
python3 -B tools/band_and_realtime.py "$F" 08_verification/results | grep -E "^(BAND|REALTIME)"
python3 -I tools/make_connection.py 08_verification/results 06_connection > /dev/null
# coefficient database and the building calculation (need the collected coefficient files: COEF_DIR=<dir with out/ and downloads/>)
python3 -I tools/build_coef_demand.py 09_coefficients/coefficient_demand.csv
python3 -I tools/build_provisional.py 09_coefficients/provisional_fill.csv
if [ -n "${COEF_DIR:-}" ]; then
  TK="$COEF_DIR/downloads/jp_qty/tokyo/GlobalWarmingPreventionReportingSystemDateFY2024.csv"
  python3 -I tools/real_building_calc.py "$COEF_DIR/out" "$TK" 10_real_building 60 10_real_building/input_representative_rc_office.json > 10_real_building/run_T60.txt
  python3 -I tools/build_factor_db.py "$COEF_DIR/out" 09_coefficients/coefficient_demand.csv 09_coefficients 10_real_building/estimates.csv \
      10_real_building/representative_rc_office.json 09_coefficients/provisional_fill.csv | grep fill_rate
fi
git -C "$F" status --short | head -5   # must print nothing: the earlier checkout is read only
echo "done"
