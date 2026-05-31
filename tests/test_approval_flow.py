import tempfile
import unittest
from pathlib import Path

from app.agents.models import TradeTicket
from app.approval.commands import ApprovalCommand, parse_approval_command
from app.approval.workflow import ApprovalWorkflow
from app.storage.repository import TradingRepository


class ApprovalFlowTest(unittest.TestCase):
    def test_parses_korean_approval_and_rejection_commands(self):
        self.assertEqual(parse_approval_command("승인 TT-20260531-001"), ApprovalCommand("approve", "TT-20260531-001"))
        self.assertEqual(parse_approval_command("거절 TT-20260531-001"), ApprovalCommand("reject", "TT-20260531-001"))
        self.assertIsNone(parse_approval_command("잔액"))

    def test_approval_marks_ticket_user_approved_and_executes_paper_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()
            ticket = TradeTicket(
                "TT-test-approval-001",
                "498270",
                "buy",
                3,
                "limit",
                18600,
                "trading_strategy_agent",
                risk_approved=True,
                risk_approved_by="risk_management_agent",
                status="risk_approved",
            )
            repo.record_trade_ticket("run-001", ticket)

            result = ApprovalWorkflow(repo).handle_text("승인 TT-test-approval-001", mode="paper")

            self.assertTrue(result.accepted)
            self.assertEqual(result.action, "approve")
            self.assertIn("paper_order_recorded:TT-test-approval-001", result.message)
            stored = repo.get_trade_ticket("TT-test-approval-001")
            self.assertEqual(stored["user_approved"], 1)
            self.assertEqual(stored["status"], "paper_executed")

    def test_rejection_marks_ticket_rejected_without_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()
            ticket = TradeTicket(
                "TT-test-reject-001",
                "498270",
                "buy",
                3,
                "limit",
                18600,
                "trading_strategy_agent",
                risk_approved=True,
                risk_approved_by="risk_management_agent",
                status="risk_approved",
            )
            repo.record_trade_ticket("run-001", ticket)

            result = ApprovalWorkflow(repo).handle_text("거절 TT-test-reject-001", mode="paper")

            self.assertTrue(result.accepted)
            self.assertEqual(result.action, "reject")
            self.assertIn("거절 처리", result.message)
            stored = repo.get_trade_ticket("TT-test-reject-001")
            self.assertEqual(stored["user_approved"], 0)
            self.assertEqual(stored["status"], "user_rejected")

    def test_cannot_approve_ticket_without_risk_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()
            ticket = TradeTicket("TT-test-no-risk", "498270", "buy", 1, "limit", 18600, "trading_strategy_agent")
            repo.record_trade_ticket("run-001", ticket)

            result = ApprovalWorkflow(repo).handle_text("승인 TT-test-no-risk", mode="paper")

            self.assertFalse(result.accepted)
            self.assertIn("리스크 승인 전", result.message)
            stored = repo.get_trade_ticket("TT-test-no-risk")
            self.assertEqual(stored["status"], "draft")
    def test_approval_is_not_replayed_after_paper_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()
            ticket = TradeTicket(
                "TT-test-replay-001",
                "498270",
                "buy",
                3,
                "limit",
                18600,
                "trading_strategy_agent",
                risk_approved=True,
                risk_approved_by="risk_management_agent",
                status="pending_user_approval",
            )
            repo.record_trade_ticket("run-001", ticket)

            first = ApprovalWorkflow(repo).handle_text("승인 TT-test-replay-001", mode="paper")
            second = ApprovalWorkflow(repo).handle_text("승인 TT-test-replay-001", mode="paper")

            self.assertTrue(first.accepted)
            self.assertFalse(second.accepted)
            self.assertIn("이미 paper 실행", second.message)


if __name__ == "__main__":
    unittest.main()
