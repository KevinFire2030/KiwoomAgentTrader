from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config.dotenv import load_dotenv
from app.storage.repository import TradingRepository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect or change Kiwoom runtime circuit breaker state.")
    parser.add_argument("action", choices=["status", "on", "off"], help="Circuit breaker action")
    parser.add_argument("--reason", default="", help="Reason stored with on/off state")
    parser.add_argument("--db", default=None, help="Trading SQLite DB path, default KIWOOM_TRADING_DB or data/trading.db")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    db_path = args.db or os.getenv("KIWOOM_TRADING_DB", "data/trading.db")
    repo = TradingRepository(Path(db_path))
    repo.initialize()

    if args.action in {"on", "off"}:
        reason = args.reason or ("manual circuit breaker on" if args.action == "on" else "manual circuit breaker off")
        repo.set_runtime_state("circuit_breaker", args.action, reason)

    row = repo.get_runtime_state("circuit_breaker")
    if row is None:
        print("circuit_breaker: unset")
        raise SystemExit(0)
    print(f"circuit_breaker: {row['state_value']}")
    print(f"reason: {row['reason']}")
    print(f"updated_at: {row['updated_at']}")


if __name__ == "__main__":
    main()
