import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from app.agents.models import TradeTicket
from app.automation.operational_risk import OperationalRiskGuard, OperationalRiskPolicy
from app.storage.repository import RealizedPnlEvent, TradingRepository

KST = ZoneInfo("Asia/Seoul")


def ticket(ticket_id: str, *, created_at: datetime, status: str = "paper_executed", amount: int = 10_000) -> TradeTicket:
    return TradeTicket(
        ticket_id=ticket_id,
        symbol="498270",
        side="buy",
        quantity=amount // 10_000,
        order_type="limit",
        limit_price=10_000,
        created_by="trading_strategy_agent",
        risk_approved=True,
        risk_approved_by="risk_management_agent",
        user_approved=True,
        status=status,
        created_at=created_at,
    )


class OperationalRiskGuardTest(unittest.TestCase):
    def test_allows_when_no_runtime_blocks_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            guard = OperationalRiskGuard(repo, OperationalRiskPolicy(max_daily_buy_amount_krw=300_000, order_cooldown_minutes=30))

            decision = guard.evaluate(symbol="498270", now=datetime(2026, 6, 1, 10, 0, tzinfo=KST))

            self.assertTrue(decision.allowed)
            self.assertEqual(decision.status, "allowed")

    def test_blocks_when_circuit_breaker_is_on(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()
            repo.set_runtime_state("circuit_breaker", "on", "manual halt")
            guard = OperationalRiskGuard(repo)

            decision = guard.evaluate(symbol="498270", now=datetime(2026, 6, 1, 10, 0, tzinfo=KST))

            self.assertFalse(decision.allowed)
            self.assertEqual(decision.status, "blocked_circuit_breaker")
            self.assertIn("manual halt", decision.reason)

    def test_blocks_when_last_execution_is_inside_cooldown(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()
            repo.record_trade_ticket(
                "run-cooldown-001",
                ticket("TT-cooldown-001", created_at=datetime(2026, 6, 1, 9, 45, tzinfo=KST)),
            )
            guard = OperationalRiskGuard(repo, OperationalRiskPolicy(order_cooldown_minutes=30))

            decision = guard.evaluate(symbol="498270", now=datetime(2026, 6, 1, 10, 0, tzinfo=KST))

            self.assertFalse(decision.allowed)
            self.assertEqual(decision.status, "blocked_order_cooldown")
            self.assertIn("cooldown", decision.reason)

    def test_blocks_when_daily_buy_limit_reached(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()
            repo.record_trade_ticket(
                "run-limit-001",
                ticket("TT-limit-001", created_at=datetime(2026, 6, 1, 9, 0, tzinfo=KST), amount=300_000),
            )
            guard = OperationalRiskGuard(
                repo,
                OperationalRiskPolicy(max_daily_buy_amount_krw=300_000, order_cooldown_minutes=0),
            )

            decision = guard.evaluate(symbol="498270", now=datetime(2026, 6, 1, 10, 0, tzinfo=KST))

            self.assertFalse(decision.allowed)
            self.assertEqual(decision.status, "blocked_daily_buy_limit")
            self.assertIn("300,000원", decision.reason)

    def test_ignores_previous_day_for_daily_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()
            repo.record_trade_ticket(
                "run-yesterday-001",
                ticket("TT-yesterday-001", created_at=datetime(2026, 5, 31, 14, 0, tzinfo=KST), amount=300_000),
            )
            guard = OperationalRiskGuard(
                repo,
                OperationalRiskPolicy(max_daily_buy_amount_krw=300_000, order_cooldown_minutes=0),
            )

            decision = guard.evaluate(symbol="498270", now=datetime(2026, 6, 1, 10, 0, tzinfo=KST))

            self.assertTrue(decision.allowed)
            self.assertEqual(decision.status, "allowed")

    def test_blocks_when_daily_realized_loss_limit_reached(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()
            repo.record_realized_pnl_event(
                RealizedPnlEvent(
                    symbol="498270",
                    realized_pnl_krw=-55_000,
                    source="kiwoom_fill_sync",
                    raw={"ord_no": "masked"},
                    occurred_at=datetime(2026, 6, 1, 9, 30, tzinfo=KST),
                )
            )
            guard = OperationalRiskGuard(
                repo,
                OperationalRiskPolicy(max_daily_loss_krw=50_000, order_cooldown_minutes=0),
            )

            decision = guard.evaluate(symbol="498270", now=datetime(2026, 6, 1, 10, 0, tzinfo=KST))

            self.assertFalse(decision.allowed)
            self.assertEqual(decision.status, "blocked_daily_realized_loss_limit")
            self.assertIn("-55,000원", decision.reason)
            self.assertIn("50,000원", decision.reason)

    def test_daily_realized_loss_guard_uses_same_day_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()
            repo.record_realized_pnl_event(
                RealizedPnlEvent(
                    symbol="498270",
                    realized_pnl_krw=-100_000,
                    source="kiwoom_fill_sync",
                    raw={},
                    occurred_at=datetime(2026, 5, 31, 14, 0, tzinfo=KST),
                )
            )
            guard = OperationalRiskGuard(
                repo,
                OperationalRiskPolicy(max_daily_loss_krw=50_000, order_cooldown_minutes=0),
            )

            decision = guard.evaluate(symbol="498270", now=datetime(2026, 6, 1, 10, 0, tzinfo=KST))

            self.assertTrue(decision.allowed)
            self.assertEqual(decision.status, "allowed")


if __name__ == "__main__":
    unittest.main()
