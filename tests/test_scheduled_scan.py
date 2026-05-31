import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.agents.models import RiskReview, TradeTicket, WorkflowResult
from app.automation.scheduled_scan import ScheduledScanConfig, market_session_decision, run_scheduled_scan
from app.storage.repository import TradingRepository


KST = ZoneInfo("Asia/Seoul")


class FakeTelegramClient:
    def __init__(self):
        self.sent = []

    def send_message(self, target, text):
        self.sent.append((target, text))
        return {"ok": True}


def make_result(ticket: TradeTicket | None = None) -> WorkflowResult:
    return WorkflowResult(
        run_id="run-scheduled-001",
        report="[Chief Investment Agent]\nworkflow completed",
        ticket=ticket,
        risk_review=RiskReview("risk_management_agent", bool(ticket), "low", ticket, []),
    )


class ScheduledScanTest(unittest.TestCase):
    def test_market_session_allows_weekday_inside_scan_window(self):
        config = ScheduledScanConfig()

        decision = market_session_decision(config, datetime(2026, 6, 1, 10, 0, tzinfo=KST))

        self.assertTrue(decision.is_open)
        self.assertEqual(decision.reason, "정규 스캔 가능 시간")

    def test_market_session_blocks_weekend(self):
        config = ScheduledScanConfig()

        decision = market_session_decision(config, datetime(2026, 6, 6, 10, 0, tzinfo=KST))

        self.assertFalse(decision.is_open)
        self.assertIn("주말 휴장", decision.reason)

    def test_market_session_blocks_configured_krx_holiday(self):
        config = ScheduledScanConfig(holidays=frozenset({"2026-06-03"}))

        decision = market_session_decision(config, datetime(2026, 6, 3, 10, 0, tzinfo=KST))

        self.assertFalse(decision.is_open)
        self.assertIn("KRX 휴장일", decision.reason)

    def test_market_session_blocks_before_open_and_after_close(self):
        config = ScheduledScanConfig()

        before = market_session_decision(config, datetime(2026, 6, 1, 8, 59, tzinfo=KST))
        after = market_session_decision(config, datetime(2026, 6, 1, 15, 11, tzinfo=KST))

        self.assertFalse(before.is_open)
        self.assertIn("장 시작 전", before.reason)
        self.assertFalse(after.is_open)
        self.assertIn("신규주문 차단 시간 이후", after.reason)

    def test_skips_workflow_outside_market_hours_without_force(self):
        calls = []
        config = ScheduledScanConfig(chat_id="-1001", message_thread_id=502)

        result = run_scheduled_scan(
            config,
            workflow_runner=lambda symbol: calls.append(symbol) or make_result(),
            telegram_client=FakeTelegramClient(),
            now=datetime(2026, 6, 6, 10, 0, tzinfo=KST),
        )

        self.assertEqual(result.status, "skipped_market_closed")
        self.assertEqual(calls, [])
        self.assertFalse(result.notification_sent)
        self.assertIn("정기 스캔 생략", result.message)

    def test_runs_workflow_and_sends_ticket_notification_inside_market_hours(self):
        ticket = TradeTicket(
            "TT-scheduled-001",
            "498270",
            "buy",
            1,
            "limit",
            18600,
            "trading_strategy_agent",
            risk_approved=True,
            risk_approved_by="risk_management_agent",
            status="pending_user_approval",
        )
        fake = FakeTelegramClient()
        config = ScheduledScanConfig(chat_id="-1001", message_thread_id=502)

        result = run_scheduled_scan(
            config,
            workflow_runner=lambda symbol: make_result(ticket),
            telegram_client=fake,
            now=datetime(2026, 6, 1, 10, 0, tzinfo=KST),
        )

        self.assertEqual(result.status, "completed_notified")
        self.assertTrue(result.notification_sent)
        self.assertEqual(len(fake.sent), 1)
        target, text = fake.sent[0]
        self.assertEqual(target.chat_id, "-1001")
        self.assertEqual(target.message_thread_id, 502)
        self.assertIn("승인 TT-scheduled-001", text)
        self.assertIn("거절 TT-scheduled-001", text)

    def test_can_suppress_no_ticket_notifications(self):
        fake = FakeTelegramClient()
        config = ScheduledScanConfig(chat_id="-1001", notify_when_no_ticket=False)

        result = run_scheduled_scan(
            config,
            workflow_runner=lambda symbol: make_result(None),
            telegram_client=fake,
            now=datetime(2026, 6, 1, 10, 0, tzinfo=KST),
        )

        self.assertEqual(result.status, "completed_no_notification")
        self.assertFalse(result.notification_sent)
        self.assertEqual(fake.sent, [])

    def test_force_runs_even_when_market_closed(self):
        fake = FakeTelegramClient()
        config = ScheduledScanConfig(chat_id="-1001", force=True)

        result = run_scheduled_scan(
            config,
            workflow_runner=lambda symbol: make_result(None),
            telegram_client=fake,
            now=datetime(2026, 6, 6, 10, 0, tzinfo=KST),
        )

        self.assertEqual(result.status, "completed_notified")
        self.assertTrue(result.notification_sent)
        self.assertIn("주말 휴장", result.message)

    def test_operational_risk_blocks_scan_before_workflow(self):
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()
            repo.set_runtime_state("circuit_breaker", "on", "manual halt")
            config = ScheduledScanConfig(db_path=Path(tmp) / "trading.db")

            result = run_scheduled_scan(
                config,
                workflow_runner=lambda symbol: calls.append(symbol) or make_result(None),
                now=datetime(2026, 6, 1, 10, 0, tzinfo=KST),
            )

        self.assertEqual(result.status, "skipped_operational_risk")
        self.assertEqual(calls, [])
        self.assertIsNotNone(result.operational_risk)
        self.assertIn("운영 리스크 차단", result.message)
        self.assertIn("manual halt", result.message)

    def test_force_bypasses_operational_risk_for_smoke_test(self):
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()
            repo.set_runtime_state("circuit_breaker", "on", "manual halt")
            config = ScheduledScanConfig(db_path=Path(tmp) / "trading.db", force=True, notify_when_no_ticket=False)

            result = run_scheduled_scan(
                config,
                workflow_runner=lambda symbol: calls.append(symbol) or make_result(None),
                now=datetime(2026, 6, 1, 10, 0, tzinfo=KST),
            )

        self.assertEqual(result.status, "completed_no_notification")
        self.assertEqual(calls, ["498270"])
        self.assertIsNotNone(result.operational_risk)


if __name__ == "__main__":
    unittest.main()
