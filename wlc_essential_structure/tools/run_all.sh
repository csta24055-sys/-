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
python3 -B tools/band_and_realtime.py "$F" 08_verification/results | grep -E "^(BAND|REALTIME)"
python3 -I tools/make_connection.py 08_verification/results 06_connection > /dev/null
git -C "$F" status --short | head -5   # must print nothing: the earlier checkout is read only
echo "done"
