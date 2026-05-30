import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
