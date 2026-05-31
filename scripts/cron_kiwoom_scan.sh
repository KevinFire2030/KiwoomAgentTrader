#!/usr/bin/env bash
set -euo pipefail

# Scheduler entrypoint for Hermes cron / system cron.
# Stays silent on market-closed or no-notification ticks, so schedulers can run it frequently without chat spam.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOCK_FILE="${KIWOOM_SCAN_LOCK_FILE:-/tmp/kiwoom-agent-trader-scan.lock}"

cd "$REPO_DIR"

if command -v flock >/dev/null 2>&1; then
  flock -n "$LOCK_FILE" python3 scripts/run_scheduled_kiwoom_scan.py --quiet-skip --quiet-no-notification --quiet-after-send "$@"
else
  python3 scripts/run_scheduled_kiwoom_scan.py --quiet-skip --quiet-no-notification --quiet-after-send "$@"
fi
