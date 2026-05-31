from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Literal

from app.agents.models import AccountSnapshot, AccountState, MarketSnapshot, RiskReview, TradeTicket


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

CREATE TABLE IF NOT EXISTS market_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT NOT NULL,
    current_price INTEGER NOT NULL,
    change_rate REAL,
    source TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    captured_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS account_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    account_no_masked TEXT NOT NULL,
    deposit_asset_amount INTEGER NOT NULL,
    total_evaluation_amount INTEGER NOT NULL,
    positions_count INTEGER NOT NULL,
    source TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    captured_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS account_states (
    run_id TEXT PRIMARY KEY,
    agent TEXT NOT NULL,
    account_no_masked TEXT NOT NULL,
    cash_balance_krw INTEGER NOT NULL,
    total_evaluation_krw INTEGER NOT NULL,
    positions_count INTEGER NOT NULL,
    recent_deposit_krw INTEGER NOT NULL,
    recent_withdraw_krw INTEGER NOT NULL,
    net_cash_flow_krw INTEGER NOT NULL,
    investable_cash_krw INTEGER NOT NULL,
    summary TEXT NOT NULL,
    warnings_json TEXT NOT NULL,
    created_at TEXT NOT NULL
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


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback) -> Literal[False]:
        super().__exit__(exc_type, exc_value, traceback)
        self.close()
        return False


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

    def record_market_snapshot(self, run_id: str, snapshot: MarketSnapshot) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO market_snapshots (
                    run_id, symbol, name, current_price, change_rate, source, raw_json, captured_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    snapshot.symbol,
                    snapshot.name,
                    snapshot.current_price,
                    snapshot.change_rate,
                    snapshot.source,
                    json.dumps(snapshot.raw, ensure_ascii=False),
                    snapshot.captured_at.isoformat(),
                ),
            )

    def get_latest_market_snapshot(self, symbol: str) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM market_snapshots WHERE symbol = ? ORDER BY id DESC LIMIT 1",
                (symbol,),
            ).fetchone()

    def record_account_snapshot(self, run_id: str, snapshot: AccountSnapshot) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO account_snapshots (
                    run_id, account_no_masked, deposit_asset_amount, total_evaluation_amount,
                    positions_count, source, raw_json, captured_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    snapshot.account_no_masked,
                    snapshot.deposit_asset_amount,
                    snapshot.total_evaluation_amount,
                    snapshot.positions_count,
                    snapshot.source,
                    json.dumps(snapshot.raw, ensure_ascii=False),
                    snapshot.captured_at.isoformat(),
                ),
            )

    def get_latest_account_snapshot(self) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute("SELECT * FROM account_snapshots ORDER BY id DESC LIMIT 1").fetchone()

    def record_account_state(self, run_id: str, state: AccountState) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO account_states (
                    run_id, agent, account_no_masked, cash_balance_krw, total_evaluation_krw,
                    positions_count, recent_deposit_krw, recent_withdraw_krw, net_cash_flow_krw,
                    investable_cash_krw, summary, warnings_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    state.agent,
                    state.account_no_masked,
                    state.cash_balance_krw,
                    state.total_evaluation_krw,
                    state.positions_count,
                    state.recent_deposit_krw,
                    state.recent_withdraw_krw,
                    state.net_cash_flow_krw,
                    state.investable_cash_krw,
                    state.summary,
                    json.dumps(state.warnings, ensure_ascii=False),
                    state.created_at.isoformat(),
                ),
            )

    def get_account_state(self, run_id: str) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute("SELECT * FROM account_states WHERE run_id = ?", (run_id,)).fetchone()

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
        conn = sqlite3.connect(self.db_path, factory=ClosingConnection)
        conn.row_factory = sqlite3.Row
        return conn
