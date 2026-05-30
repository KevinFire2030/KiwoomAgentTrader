from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.agents.models import RiskReview, TradeTicket


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS agent_runs (
    run_id TEXT PRIMARY KEY,
    workflow TEXT NOT NULL,
    mode TEXT NOT NULL,
    status TEXT NOT NULL,
    summary TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trade_tickets (
    ticket_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    order_type TEXT NOT NULL,
    limit_price INTEGER,
    created_by TEXT NOT NULL,
    risk_approved INTEGER NOT NULL,
    risk_approved_by TEXT,
    user_approved INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    estimated_amount_krw INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS risk_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    ticket_id TEXT,
    agent TEXT NOT NULL,
    approved INTEGER NOT NULL,
    risk_level TEXT NOT NULL,
    reasons_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class TradingRepository:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)

    def record_agent_run(self, run_id: str, workflow: str, mode: str, status: str, summary: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO agent_runs (run_id, workflow, mode, status, summary)
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, workflow, mode, status, summary),
            )

    def get_agent_run(self, run_id: str) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute("SELECT * FROM agent_runs WHERE run_id = ?", (run_id,)).fetchone()

    def record_trade_ticket(self, run_id: str, ticket: TradeTicket) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO trade_tickets (
                    ticket_id, run_id, symbol, side, quantity, order_type, limit_price,
                    created_by, risk_approved, risk_approved_by, user_approved, status,
                    created_at, estimated_amount_krw
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticket.ticket_id,
                    run_id,
                    ticket.symbol,
                    ticket.side,
                    ticket.quantity,
                    ticket.order_type,
                    ticket.limit_price,
                    ticket.created_by,
                    int(ticket.risk_approved),
                    ticket.risk_approved_by,
                    int(ticket.user_approved),
                    ticket.status,
                    ticket.created_at.isoformat(),
                    ticket.estimated_amount_krw,
                ),
            )

    def get_trade_ticket(self, ticket_id: str) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute("SELECT * FROM trade_tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()

    def record_risk_review(self, run_id: str, review: RiskReview) -> None:
        ticket_id = review.ticket.ticket_id if review.ticket else None
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO risk_reviews (run_id, ticket_id, agent, approved, risk_level, reasons_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (run_id, ticket_id, review.agent, int(review.approved), review.risk_level, json.dumps(review.reasons, ensure_ascii=False)),
            )

    def get_latest_risk_review(self, ticket_id: str) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM risk_reviews WHERE ticket_id = ? ORDER BY id DESC LIMIT 1",
                (ticket_id,),
            ).fetchone()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
