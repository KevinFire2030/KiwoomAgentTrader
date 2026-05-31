from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.automation.post_fill_risk import PostFillCircuitBreaker, PostFillCircuitBreakerPolicy
from app.config.dotenv import load_dotenv
from app.storage.repository import RealizedPnlEvent, TradingRepository

KST = ZoneInfo("Asia/Seoul")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record a realized P&L fill event and apply post-fill circuit breaker rules.")
    parser.add_argument("--symbol", default="498270", help="Symbol for the realized P&L event")
    parser.add_argument("--realized-pnl", type=int, required=True, help="Realized P&L in KRW; losses must be negative")
    parser.add_argument("--source", default="manual_fill_sync", help="Source label for the event")
    parser.add_argument("--occurred-at", default=None, help="ISO datetime for the event; default now in KST")
    parser.add_argument("--raw-json", default="{}", help="Optional raw JSON payload to store with the event")
    parser.add_argument("--db", default=None, help="Trading SQLite DB path, default KIWOOM_TRADING_DB or data/trading.db")
    parser.add_argument("--max-daily-loss", type=int, default=None, help="Daily loss threshold in KRW, default MAX_DAILY_LOSS_KRW or 50000")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    db_path = Path(args.db or os.getenv("KIWOOM_TRADING_DB", "data/trading.db"))
    max_daily_loss = args.max_daily_loss if args.max_daily_loss is not None else int(os.getenv("MAX_DAILY_LOSS_KRW", "50000"))
    raw = json.loads(args.raw_json)
    occurred_at = _parse_datetime(args.occurred_at) if args.occurred_at else datetime.now(tz=KST)

    repo = TradingRepository(db_path)
    decision = PostFillCircuitBreaker(
        repo,
        PostFillCircuitBreakerPolicy(max_daily_loss_krw=max_daily_loss),
    ).process_fill(
        RealizedPnlEvent(
            symbol=args.symbol,
            realized_pnl_krw=args.realized_pnl,
            source=args.source,
            raw=raw,
            occurred_at=occurred_at,
        )
    )

    print(f"status: {decision.status}")
    print(f"triggered: {str(decision.triggered).lower()}")
    print(f"event_id: {decision.event_id}")
    print(f"daily_realized_pnl_krw: {decision.daily_realized_pnl_krw}")
    print(f"reason: {decision.reason}")


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=KST)
    return parsed


if __name__ == "__main__":
    main()
