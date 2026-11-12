#!/bin/bash
# Re-derive everything from worker transcripts (research tooling only).
# usage: scripts/refresh.sh STAGING_DIR CACHE_DIR TRANSCRIPT_ROOT
set -e
cd "$(dirname "$0")/.."
python3 -I scripts/recover_staging.py "$1" "$3"/wf_*          # staged outputs are rebuilt from what workers actually wrote
python3 -I scripts/transcript_audit.py "$1/trace.jsonl" "$3"/wf_*
python3 -I scripts/merge_staging.py "$1" "$2" "$1/trace.jsonl"
python3 -I scripts/build_status.py
