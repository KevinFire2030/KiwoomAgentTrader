import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.agents.models import RiskReview, TradeTicket
from app.storage.repository import TradingRepository


class TradingRepositoryTest(unittest.TestCase):
    def test_creates_database_schema_and_records_agent_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "trading.db"
            repo = TradingRepository(db_path)
            repo.initialize()

            repo.record_agent_run(
                run_id="run-001",
                workflow="intraday_signal_scan",
                mode="paper",
                status="completed",
                summary="paper workflow completed",
            )

            row = repo.get_agent_run("run-001")
            self.assertEqual(row["workflow"], "intraday_signal_scan")
            self.assertEqual(row["mode"], "paper")
            self.assertEqual(row["status"], "completed")

    def test_records_trade_ticket_and_risk_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()
            ticket = TradeTicket(
                ticket_id="TT-test-001",
                symbol="498270",
                side="buy",
                quantity=3,
                order_type="limit",
                limit_price=10000,
                created_by="trading_strategy_agent",
                risk_approved=True,
                risk_approved_by="risk_management_agent",
                status="risk_approved",
            )
            review = RiskReview(
                agent="risk_management_agent",
                approved=True,
                risk_level="low",
                ticket=ticket,
                reasons=["MVP 리스크 정책을 통과했습니다."],
            )

            repo.record_trade_ticket("run-001", ticket)
            repo.record_risk_review("run-001", review)

            stored_ticket = repo.get_trade_ticket("TT-test-001")
            stored_review = repo.get_latest_risk_review("TT-test-001")
            self.assertEqual(stored_ticket["symbol"], "498270")
            self.assertEqual(stored_ticket["status"], "risk_approved")
            self.assertEqual(stored_review["approved"], 1)
            self.assertIn("MVP 리스크", stored_review["reasons_json"])

    def test_records_order_event_audit_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()

            event_id = repo.record_order_event(
                "TT-order-event-001",
                "live_manual",
                "final_approval",
                "blocked_live_disabled",
                {"api_id": "kt10000"},
                {},
                "실주문 차단",
            )

            self.assertGreater(event_id, 0)
            events = repo.get_order_events("TT-order-event-001")
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["mode"], "live_manual")
            self.assertIn("kt10000", events[0]["order_request_json"])

    def test_sums_executed_buy_amount_and_latest_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()
            kst = ZoneInfo("Asia/Seoul")
            first = TradeTicket(
                "TT-runtime-001",
                "498270",
                "buy",
                2,
                "limit",
                10000,
                "trading_strategy_agent",
                risk_approved=True,
                user_approved=True,
                status="paper_executed",
                created_at=datetime(2026, 6, 1, 9, 10, tzinfo=kst),
            )
            second = TradeTicket(
                "TT-runtime-002",
                "498270",
                "buy",
                3,
                "limit",
                10000,
                "trading_strategy_agent",
                risk_approved=True,
                user_approved=True,
                status="pending_user_approval",
                created_at=datetime(2026, 6, 1, 9, 20, tzinfo=kst),
            )
            repo.record_trade_ticket("run-runtime-001", first)
            repo.record_trade_ticket("run-runtime-002", second)

            total = repo.sum_executed_buy_amount("2026-06-01T00:00:00+09:00", "2026-06-02T00:00:00+09:00", "498270")
            latest = repo.get_latest_executed_trade_ticket("498270")

            self.assertEqual(total, 20000)
            self.assertIsNotNone(latest)
            self.assertEqual(latest["ticket_id"], "TT-runtime-001")

    def test_runtime_state_upsert(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()

            repo.set_runtime_state("circuit_breaker", "on", "manual halt")
            repo.set_runtime_state("circuit_breaker", "off", "resumed")

            row = repo.get_runtime_state("circuit_breaker")
            self.assertIsNotNone(row)
            self.assertEqual(row["state_value"], "off")
            self.assertEqual(row["reason"], "resumed")


if __name__ == "__main__":
    unittest.main()
