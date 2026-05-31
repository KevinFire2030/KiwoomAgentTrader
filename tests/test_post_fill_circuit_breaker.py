import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.automation.post_fill_risk import PostFillCircuitBreaker, PostFillCircuitBreakerPolicy
from app.storage.repository import RealizedPnlEvent, TradingRepository

KST = ZoneInfo("Asia/Seoul")


class PostFillCircuitBreakerTest(unittest.TestCase):
    def test_records_fill_and_turns_circuit_breaker_on_when_daily_loss_limit_is_reached(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()
            repo.record_realized_pnl_event(
                RealizedPnlEvent(
                    symbol="498270",
                    realized_pnl_krw=-30_000,
                    source="kiwoom_fill_sync",
                    raw={"ord_no": "masked-prev"},
                    occurred_at=datetime(2026, 6, 1, 9, 30, tzinfo=KST),
                )
            )
            breaker = PostFillCircuitBreaker(repo, PostFillCircuitBreakerPolicy(max_daily_loss_krw=50_000))

            decision = breaker.process_fill(
                RealizedPnlEvent(
                    symbol="498270",
                    realized_pnl_krw=-25_000,
                    source="kiwoom_fill_sync",
                    raw={"ord_no": "masked-new"},
                    occurred_at=datetime(2026, 6, 1, 10, 0, tzinfo=KST),
                )
            )

            self.assertTrue(decision.triggered)
            self.assertEqual(decision.status, "circuit_breaker_on")
            self.assertEqual(decision.daily_realized_pnl_krw, -55_000)
            self.assertIn("-55,000원", decision.reason)
            state = repo.get_runtime_state("circuit_breaker")
            self.assertIsNotNone(state)
            if state is None:
                self.fail("circuit breaker state missing")
            self.assertEqual(state["state_value"], "on")
            self.assertIn("post-fill", state["reason"])

    def test_records_fill_without_breaker_when_loss_limit_not_reached(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()
            breaker = PostFillCircuitBreaker(repo, PostFillCircuitBreakerPolicy(max_daily_loss_krw=50_000))

            decision = breaker.process_fill(
                RealizedPnlEvent(
                    symbol="498270",
                    realized_pnl_krw=-10_000,
                    source="kiwoom_fill_sync",
                    raw={},
                    occurred_at=datetime(2026, 6, 1, 10, 0, tzinfo=KST),
                )
            )

            self.assertFalse(decision.triggered)
            self.assertEqual(decision.status, "recorded")
            self.assertEqual(decision.daily_realized_pnl_krw, -10_000)
            self.assertIsNone(repo.get_runtime_state("circuit_breaker"))

    def test_uses_kst_same_day_for_daily_loss(self):
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
            breaker = PostFillCircuitBreaker(repo, PostFillCircuitBreakerPolicy(max_daily_loss_krw=50_000))

            decision = breaker.process_fill(
                RealizedPnlEvent(
                    symbol="498270",
                    realized_pnl_krw=5_000,
                    source="kiwoom_fill_sync",
                    raw={},
                    occurred_at=datetime(2026, 6, 1, 10, 0, tzinfo=KST),
                )
            )

            self.assertFalse(decision.triggered)
            self.assertEqual(decision.daily_realized_pnl_krw, 5_000)


if __name__ == "__main__":
    unittest.main()
