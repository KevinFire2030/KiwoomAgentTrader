from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.automation.status import AutomationStatusBuilder, format_automation_status
from app.config.dotenv import load_dotenv
from app.storage.repository import TradingRepository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Show read-only Kiwoom Agent Trader automation health status.")
    parser.add_argument("--db", default=None, help="Trading SQLite DB path, default KIWOOM_TRADING_DB or data/trading.db")
    parser.add_argument("--symbol", default=None, help="Symbol to inspect, default KIWOOM_SCAN_SYMBOL or 498270")
    parser.add_argument("--strategy-lessons", default="docs/strategy-lessons.md", help="Strategy lessons markdown path")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    db_path = Path(args.db or os.getenv("KIWOOM_TRADING_DB", str(Path("data") / "trading.db")))
    symbol = args.symbol or os.getenv("KIWOOM_SCAN_SYMBOL", "498270")
    trading_mode = os.getenv("TRADING_MODE", "paper")
    enable_live_trading = _env_bool("ENABLE_LIVE_TRADING", False)
    status = AutomationStatusBuilder(
        TradingRepository(db_path),
        symbol=symbol,
        trading_mode=trading_mode,
        enable_live_trading=enable_live_trading,
        strategy_lessons_path=args.strategy_lessons,
    ).build()
    print(format_automation_status(status))


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


if __name__ == "__main__":
    main()
