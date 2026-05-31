from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.analysis.post_trade import PostTradeAnalyzer, format_post_trade_report
from app.config.dotenv import load_dotenv
from app.storage.repository import TradingRepository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a post-trade analysis report for a Kiwoom trade ticket.")
    parser.add_argument("ticket_id", help="Trade ticket id, e.g. TT-...")
    parser.add_argument("--db", default=None, help="Trading SQLite DB path, default KIWOOM_TRADING_DB or data/trading.db")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    db_path = Path(args.db or os.getenv("KIWOOM_TRADING_DB", "data/trading.db"))
    analysis = PostTradeAnalyzer(TradingRepository(db_path)).analyze_ticket(args.ticket_id)
    print(format_post_trade_report(analysis))


if __name__ == "__main__":
    main()
