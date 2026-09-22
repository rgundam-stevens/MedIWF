#!/bin/bash
# Relaunches the generator until it finishes. The generator exits with code 3 when it detects a stall
# (no item completed for --stall-minutes); every relaunch resumes from the saved records.
# Usage: bash scripts/run_with_watchdog.sh --full --workers 8 --models ...   (same arguments as generate.py)
cd "$(dirname "$0")/.." || exit 1
attempt=0
while true; do
  attempt=$((attempt+1))
  echo "=== launch $attempt: $(date) ==="
  caffeinate -i python3 scripts/generate.py "$@"
  code=$?
  if [ $code -eq 0 ]; then echo "=== finished cleanly at $(date) ==="; break; fi
  if [ $code -eq 3 ]; then echo "=== stall detected; restarting in 20 s ==="; sleep 20; continue; fi
  echo "=== exited with code $code; restarting in 60 s (Ctrl+C to stop) ==="; sleep 60
done
