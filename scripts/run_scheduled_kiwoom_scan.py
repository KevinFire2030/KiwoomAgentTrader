from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.automation.scheduled_scan import ScheduledScanConfig, run_scheduled_scan
from app.config.dotenv import load_dotenv


class NoSendTelegramClient:
    def send_message(self, target, text):
        return {"ok": True, "dry_run": True, "target": target}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one scheduler-safe Kiwoom intraday scan and optional Telegram alert.")
    parser.add_argument("symbol", nargs="?", help="Symbol to scan, default KIWOOM_SCAN_SYMBOL or 498270")
    parser.add_argument("--force", action="store_true", help="Run even outside configured market scan hours")
    parser.add_argument("--no-send", action="store_true", help="Do not send Telegram; print notification text only")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    config = ScheduledScanConfig.from_env()
    if args.symbol:
        config = config.with_overrides(symbol=args.symbol)
    if args.force:
        config = config.with_overrides(force=True)

    telegram_client = NoSendTelegramClient() if args.no_send else None
    result = run_scheduled_scan(config, telegram_client=telegram_client)
    print(result.message)
    print(f"status: {result.status}")
    print(f"notification_sent: {result.notification_sent}")


if __name__ == "__main__":
    main()
