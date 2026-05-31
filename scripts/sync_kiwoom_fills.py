from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.automation.fill_sync import KiwoomFillSync
from app.config.dotenv import load_dotenv
from app.config.settings import KiwoomSettings
from app.kiwoom.auth import KiwoomAuthClient
from app.kiwoom.client import KiwoomRestClient
from app.kiwoom.transactions import KiwoomTransactionClient
from app.storage.repository import TradingRepository

KST = ZoneInfo("Asia/Seoul")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read Kiwoom fill/transaction rows and sync derived realized P&L events idempotently.")
    parser.add_argument("--db", default=None, help="Trading SQLite DB path, default KIWOOM_TRADING_DB or data/trading.db")
    parser.add_argument("--sample-json", default=None, help="Use local sample rows instead of Kiwoom API")
    parser.add_argument("--start-date", default=None, help="YYYYMMDD, default yesterday KST")
    parser.add_argument("--end-date", default=None, help="YYYYMMDD, default today KST")
    parser.add_argument("--apply", action="store_true", help="Persist snapshots and realized P&L events")
    parser.add_argument("--dry-run", action="store_true", help="Force no writes; default when --apply is absent")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    db_path = Path(args.db or os.getenv("KIWOOM_TRADING_DB", "data/trading.db"))
    apply = bool(args.apply and not args.dry_run)
    rows = _load_rows(args)
    result = KiwoomFillSync(TradingRepository(db_path)).sync_rows(rows, apply=apply)
    print(f"rows_seen: {result.rows_seen}")
    print(f"events_derived: {result.events_derived}")
    print(f"events_recorded: {result.events_recorded}")
    print(f"duplicates_skipped: {result.duplicates_skipped}")
    print(f"snapshots_recorded: {result.snapshots_recorded}")
    print(f"apply: {result.apply}")
    if not apply:
        print("dry_run: true (no DB writes)")


def _load_rows(args: argparse.Namespace) -> list[dict]:
    if args.sample_json:
        data = json.loads(Path(args.sample_json).read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("rows") or data.get("data") or []
        if not isinstance(data, list):
            raise SystemExit("sample JSON must be a list or {'rows': [...]} object")
        return [row for row in data if isinstance(row, dict)]

    today = datetime.now(tz=KST).date()
    start_date = args.start_date or (today - timedelta(days=1)).strftime("%Y%m%d")
    end_date = args.end_date or today.strftime("%Y%m%d")
    settings = KiwoomSettings.from_env()
    auth = KiwoomAuthClient(settings.base_url, settings.app_key, settings.secret_key)
    token_cache = {}

    def token_provider():
        if "token" not in token_cache:
            token_cache["token"] = auth.issue_token()
        return token_cache["token"]

    client = KiwoomRestClient(settings.base_url, settings.app_key, token_provider)
    return KiwoomTransactionClient(client).get_deposit_withdraw_history(start_date, end_date)


if __name__ == "__main__":
    main()
