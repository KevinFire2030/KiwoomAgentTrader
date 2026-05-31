from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a read-only/paper market-open rehearsal checklist.")
    parser.add_argument("--db", default=None, help="Trading DB path passed to supported scripts")
    parser.add_argument("--symbol", default="498270", help="Symbol to scan")
    parser.add_argument("--fill-sample-json", default=None, help="Optional sample fill JSON for offline fill-sync dry run")
    parser.add_argument("--skip-read-api", action="store_true", help="Skip real Kiwoom read API smoke")
    parser.add_argument("--skip-scan", action="store_true", help="Skip scheduled paper scan")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print("[Kiwoom Agent Trader 개장 리허설]")
    print("안전: read-only/paper rehearsal입니다. Kiwoom 주문 API를 호출하지 않습니다.")
    _run_step("automation_status", [sys.executable, "scripts/show_automation_status.py", *_db_args(args)])
    if not args.skip_read_api:
        _run_step("kiwoom_read_api", [sys.executable, "scripts/check_kiwoom_read_api.py"])
    if not args.skip_scan:
        _run_step(
            "scheduled_scan_no_send",
            [sys.executable, "scripts/run_scheduled_kiwoom_scan.py", args.symbol, "--force", "--no-send", *_quiet_args()],
        )
    fill_cmd = [sys.executable, "scripts/sync_kiwoom_fills.py", *_db_args(args), "--dry-run"]
    if args.fill_sample_json:
        fill_cmd.extend(["--sample-json", args.fill_sample_json])
    _run_step("fill_sync_dry_run", fill_cmd)
    print("market_open_rehearsal: OK")


def _run_step(name: str, command: list[str]) -> None:
    print(f"\nstep: {name}")
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    if result.returncode != 0:
        raise SystemExit(f"step failed: {name} exit_code={result.returncode}")


def _db_args(args: argparse.Namespace) -> list[str]:
    return ["--db", args.db] if args.db else []


def _quiet_args() -> list[str]:
    return ["--quiet-no-notification"]


if __name__ == "__main__":
    main()
