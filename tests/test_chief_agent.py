import tempfile
import unittest
from pathlib import Path

from app.agents.chief import ChiefInvestmentAgent
from app.storage.repository import TradingRepository


class ChiefInvestmentAgentTest(unittest.TestCase):
    def test_runs_paper_workflow_and_persists_decision_trail(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            chief = ChiefInvestmentAgent(repository=repo)

            result = chief.run_intraday_signal_scan(symbol="498270", mode="paper")

            self.assertTrue(result.risk_review.approved)
            self.assertIsNotNone(result.ticket)
            self.assertIn("Chief Investment Agent", result.report)
            self.assertIn("paper_order_recorded", result.report)
            self.assertIsNotNone(repo.get_agent_run(result.run_id))
            self.assertIsNotNone(repo.get_trade_ticket(result.ticket.ticket_id))
            self.assertIsNotNone(repo.get_latest_risk_review(result.ticket.ticket_id))

    def test_does_not_execute_disallowed_symbol(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            chief = ChiefInvestmentAgent(repository=repo)

            result = chief.run_intraday_signal_scan(symbol="000000", mode="paper")

            self.assertFalse(result.risk_review.approved)
            self.assertIsNone(result.ticket)
            self.assertIn("not_executed", result.report)
            self.assertIsNotNone(repo.get_agent_run(result.run_id))


if __name__ == "__main__":
    unittest.main()
