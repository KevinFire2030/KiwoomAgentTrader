import tempfile
import unittest
from pathlib import Path

from app.agents.models import TradeTicket
from app.storage.repository import TradingRepository
from app.telegram.approval_gateway import TelegramApprovalConfig, TelegramApprovalGateway


class FakeTelegramClient:
    def __init__(self):
        self.sent = []

    def send_message(self, target, text):
        self.sent.append((target, text))
        return {"ok": True, "result": {"message_id": 1}}


class TelegramApprovalGatewayTest(unittest.TestCase):
    def test_handles_telegram_update_and_replies_after_paper_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()
            repo.record_trade_ticket(
                "run-telegram-001",
                TradeTicket(
                    "TT-telegram-001",
                    "498270",
                    "buy",
                    2,
                    "limit",
                    18600,
                    "trading_strategy_agent",
                    risk_approved=True,
                    risk_approved_by="risk_management_agent",
                    status="pending_user_approval",
                ),
            )
            fake = FakeTelegramClient()
            gateway = TelegramApprovalGateway(
                TelegramApprovalConfig(db_path=Path(tmp) / "trading.db", mode="paper", chat_id="-1001", message_thread_id=502),
                repository=repo,
                telegram_client=fake,
            )

            response = gateway.handle_update(
                {"message": {"chat": {"id": -1001}, "message_thread_id": 502, "text": "승인 TT-telegram-001"}}
            )

            self.assertTrue(response.handled)
            self.assertTrue(response.should_reply)
            self.assertIn("paper_order_recorded:TT-telegram-001", response.text)
            self.assertEqual(len(fake.sent), 1)
            target, sent_text = fake.sent[0]
            self.assertEqual(target.chat_id, "-1001")
            self.assertEqual(target.message_thread_id, 502)
            self.assertEqual(sent_text, response.text)
            stored = repo.get_trade_ticket("TT-telegram-001")
            self.assertIsNotNone(stored)
            self.assertEqual(stored["status"], "paper_executed")

    def test_ignores_non_approval_message_without_reply(self):
        with tempfile.TemporaryDirectory() as tmp:
            gateway = TelegramApprovalGateway(TelegramApprovalConfig(db_path=Path(tmp) / "trading.db"))

            response = gateway.handle_message("다음 단계 구현해줘", chat_id="-1001", message_thread_id=502)

            self.assertFalse(response.handled)
            self.assertFalse(response.should_reply)

    def test_rejects_wrong_thread_without_execution_or_reply(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()
            repo.record_trade_ticket(
                "run-telegram-002",
                TradeTicket(
                    "TT-telegram-002",
                    "498270",
                    "buy",
                    1,
                    "limit",
                    18600,
                    "trading_strategy_agent",
                    risk_approved=True,
                    risk_approved_by="risk_management_agent",
                    status="pending_user_approval",
                ),
            )
            gateway = TelegramApprovalGateway(
                TelegramApprovalConfig(db_path=Path(tmp) / "trading.db", mode="paper", chat_id="-1001", message_thread_id=502),
                repository=repo,
            )

            response = gateway.handle_message("승인 TT-telegram-002", chat_id="-1001", message_thread_id=11)

            self.assertTrue(response.handled)
            self.assertFalse(response.should_reply)
            self.assertIn("허용되지 않은 Telegram 대상", response.text)
            stored = repo.get_trade_ticket("TT-telegram-002")
            self.assertIsNotNone(stored)
            self.assertEqual(stored["status"], "pending_user_approval")


if __name__ == "__main__":
    unittest.main()
