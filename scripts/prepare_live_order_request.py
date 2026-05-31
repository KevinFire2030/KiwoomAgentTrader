from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.models import TradeTicket
from app.kiwoom.auth import KiwoomToken
from app.kiwoom.client import KiwoomRestClient
from app.kiwoom.orders import KiwoomOrderClient
from app.storage.repository import TradingRepository


def main() -> None:
    if len(sys.argv) < 2:
        print("사용법: python3 scripts/prepare_live_order_request.py TT-...")
        raise SystemExit(2)

    ticket_id = sys.argv[1]
    repo = TradingRepository(Path(os.getenv("KIWOOM_TRADING_DB", str(Path("data") / "trading.db"))))
    repo.initialize()
    row = repo.get_trade_ticket(ticket_id)
    if row is None:
        print(f"티켓을 찾을 수 없습니다: {ticket_id}")
        raise SystemExit(1)

    ticket = TradeTicket(
        ticket_id=row["ticket_id"],
        symbol=row["symbol"],
        side=row["side"],
        quantity=row["quantity"],
        order_type=row["order_type"],
        limit_price=row["limit_price"],
        created_by=row["created_by"],
        risk_approved=bool(row["risk_approved"]),
        risk_approved_by=row["risk_approved_by"],
        user_approved=bool(row["user_approved"]),
        status=row["status"],
        created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(timezone.utc),
    )
    dummy_client = KiwoomRestClient("https://api.kiwoom.com", "dry-run-app-key", lambda: KiwoomToken("Bearer", "dry-run-token", 0))
    request = KiwoomOrderClient(dummy_client).build_order_request(ticket)
    print(json.dumps({"ticket_id": request.ticket_id, "endpoint": request.endpoint, "api_id": request.api_id, "payload": request.payload}, ensure_ascii=False, indent=2))
    print("DRY RUN ONLY: 키움 주문 API를 호출하지 않았습니다.")


if __name__ == "__main__":
    main()
