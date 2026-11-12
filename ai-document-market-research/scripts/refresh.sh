#!/bin/bash
# Re-derive everything from worker transcripts and staged outputs (research tooling only).
# usage: scripts/refresh.sh STAGING_DIR CACHE_DIR TRANSCRIPT_ROOT
set -e
cd "$(dirname "$0")/.."
python3 -I scripts/transcript_audit.py "$1/trace.jsonl" "$3"/wf_*
python3 -I scripts/merge_staging.py "$1" "$2" "$1/trace.jsonl"
python3 -I scripts/build_status.py
