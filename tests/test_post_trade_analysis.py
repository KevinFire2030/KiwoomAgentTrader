import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.agents.models import RiskReview, TradeTicket
from app.analysis.post_trade import PostTradeAnalyzer
from app.storage.repository import RealizedPnlEvent, TradingRepository

KST = ZoneInfo("Asia/Seoul")


def make_ticket(ticket_id: str = "TT-analysis-001") -> TradeTicket:
    return TradeTicket(
        ticket_id=ticket_id,
        symbol="498270",
        side="buy",
        quantity=2,
        order_type="limit",
        limit_price=18_600,
        created_by="trading_strategy_agent",
        risk_approved=True,
        risk_approved_by="risk_management_agent",
        user_approved=True,
        status="paper_executed",
        created_at=datetime(2026, 6, 1, 9, 30, tzinfo=KST),
    )


class PostTradeAnalysisTest(unittest.TestCase):
    def test_analyzes_executed_ticket_and_persists_lessons(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()
            ticket = make_ticket()
            repo.record_agent_run("run-analysis-001", "intraday_signal_scan", "paper", "completed", "risk_on signal")
            repo.record_trade_ticket("run-analysis-001", ticket)
            repo.record_risk_review(
                "run-analysis-001",
                RiskReview("risk_management_agent", True, "low", ticket, ["allowed symbol", "within cash limit"]),
            )
            repo.record_order_event(
                ticket.ticket_id,
                "paper",
                "paper_order",
                "accepted",
                order_request={"qty": 2},
                broker_response={"paper": True},
                message="paper filled",
            )
            repo.record_realized_pnl_event(
                RealizedPnlEvent(
                    symbol="498270",
                    realized_pnl_krw=12_000,
                    source="paper_fill_sync",
                    raw={"ticket_id": ticket.ticket_id, "exit_price": 24_600},
                    occurred_at=datetime(2026, 6, 1, 14, 30, tzinfo=KST),
                )
            )

            analysis = PostTradeAnalyzer(repo).analyze_ticket(ticket.ticket_id)

            self.assertEqual(analysis.ticket_id, ticket.ticket_id)
            self.assertEqual(analysis.outcome, "win")
            self.assertEqual(analysis.realized_pnl_krw, 12_000)
            self.assertIn("+12,000원", analysis.summary)
            self.assertTrue(any("risk" in lesson.lower() for lesson in analysis.lessons))
            stored = repo.get_latest_post_trade_analysis(ticket.ticket_id)
            self.assertIsNotNone(stored)
            if stored is None:
                self.fail("post trade analysis was not stored")
            self.assertEqual(stored["outcome"], "win")
            self.assertEqual(stored["realized_pnl_krw"], 12_000)

    def test_analyzes_loss_ticket_as_strategy_review_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()
            ticket = make_ticket("TT-analysis-loss")
            repo.record_agent_run("run-analysis-002", "intraday_signal_scan", "paper", "completed", "risk_on signal")
            repo.record_trade_ticket("run-analysis-002", ticket)
            repo.record_realized_pnl_event(
                RealizedPnlEvent(
                    symbol="498270",
                    realized_pnl_krw=-8_000,
                    source="paper_fill_sync",
                    raw={"ticket_id": ticket.ticket_id},
                    occurred_at=datetime(2026, 6, 1, 14, 30, tzinfo=KST),
                )
            )

            analysis = PostTradeAnalyzer(repo).analyze_ticket(ticket.ticket_id)

            self.assertEqual(analysis.outcome, "loss")
            self.assertEqual(analysis.realized_pnl_krw, -8_000)
            self.assertTrue(any("손실" in lesson for lesson in analysis.lessons))

    def test_missing_ticket_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()

            with self.assertRaises(ValueError):
                PostTradeAnalyzer(repo).analyze_ticket("TT-missing")


if __name__ == "__main__":
    unittest.main()
