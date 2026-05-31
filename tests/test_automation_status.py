import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.agents.models import AccountSnapshot, MarketSnapshot, TradeTicket
from app.automation.status import AutomationStatusBuilder, format_automation_status
from app.storage.repository import PostTradeAnalysisRecord, TradingRepository

KST = ZoneInfo("Asia/Seoul")


class AutomationStatusTest(unittest.TestCase):
    def test_builds_read_only_status_without_exposing_account_number_or_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "trading.db"
            strategy_path = Path(tmp) / "strategy-lessons.md"
            strategy_path.write_text("# lessons\n", encoding="utf-8")
            repo = TradingRepository(db_path)
            repo.initialize()
            repo.record_market_snapshot(
                "run-status-001",
                MarketSnapshot(
                    symbol="498270",
                    name="KIWOOM 미국양자컴퓨팅 ETF",
                    current_price=18_600,
                    change_rate=1.2,
                    source="kiwoom",
                    raw={"secret": "must-not-leak"},
                    captured_at=datetime(2026, 6, 1, 9, 31, tzinfo=KST),
                ),
            )
            repo.record_account_snapshot(
                "run-status-001",
                AccountSnapshot(
                    account_no_masked="63***96",
                    deposit_asset_amount=303_493,
                    total_evaluation_amount=0,
                    positions_count=0,
                    source="kiwoom",
                    raw={"account_no": "63123456"},
                    captured_at=datetime(2026, 6, 1, 9, 32, tzinfo=KST),
                ),
            )
            pending = TradeTicket(
                "TT-pending-001",
                "498270",
                "buy",
                1,
                "limit",
                18_600,
                "trading_strategy_agent",
                risk_approved=True,
                status="pending_user_approval",
                created_at=datetime(2026, 6, 1, 10, 0, tzinfo=KST),
            )
            older_pending = TradeTicket(
                "TT-pending-000",
                "498270",
                "buy",
                1,
                "limit",
                18_500,
                "trading_strategy_agent",
                risk_approved=True,
                status="pending_user_approval",
                created_at=datetime(2026, 6, 1, 9, 0, tzinfo=KST),
            )
            repo.record_trade_ticket("run-status-000", older_pending)
            repo.record_trade_ticket("run-status-001", pending)
            repo.set_runtime_state("circuit_breaker", "on", "manual halt")
            repo.record_post_trade_analysis(
                PostTradeAnalysisRecord(
                    ticket_id="TT-analysis-001",
                    run_id="run-analysis-001",
                    symbol="498270",
                    outcome="win",
                    realized_pnl_krw=3_000,
                    summary="analysis summary",
                    lessons=["lesson"],
                    created_at=datetime(2026, 6, 1, 15, 0, tzinfo=KST),
                )
            )

            status = AutomationStatusBuilder(
                repo,
                symbol="498270",
                trading_mode="paper",
                enable_live_trading=False,
                strategy_lessons_path=strategy_path,
            ).build(now=datetime(2026, 6, 1, 16, 0, tzinfo=KST))
            text = format_automation_status(status)

            self.assertEqual(status.trading_mode, "paper")
            self.assertFalse(status.enable_live_trading)
            self.assertEqual(status.market_snapshot_at, "2026-06-01 09:31:00 KST")
            self.assertEqual(status.account_snapshot_at, "2026-06-01 09:32:00 KST")
            self.assertEqual(status.circuit_breaker_state, "on")
            self.assertEqual(status.pending_ticket_count, 2)
            self.assertEqual(status.latest_pending_ticket_id, "TT-pending-001")
            self.assertEqual(status.latest_post_trade_analysis_at, "2026-06-01 15:00:00 KST")
            self.assertTrue(status.strategy_lessons_exists)
            self.assertIn("live trading: disabled", text)
            self.assertIn("pending approvals: 2", text)
            self.assertIn("latest pending: TT-pending-001", text)
            self.assertIn("strategy lessons: available", text)
            self.assertNotIn("63123456", text)
            self.assertNotIn("secret", text)
            self.assertNotIn("KIWOOM_SECRET", text)

    def test_empty_status_handles_missing_data_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()

            status = AutomationStatusBuilder(repo, symbol="498270", trading_mode="paper", enable_live_trading=False).build()
            text = format_automation_status(status)

            self.assertEqual(status.market_snapshot_at, "none")
            self.assertEqual(status.account_snapshot_at, "none")
            self.assertEqual(status.circuit_breaker_state, "off")
            self.assertEqual(status.pending_ticket_count, 0)
            self.assertIn("market snapshot: none", text)
            self.assertIn("account snapshot: none", text)

    def test_cli_prints_status_from_env_without_requiring_broker_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "trading.db"
            repo = TradingRepository(db_path)
            repo.initialize()
            repo.set_runtime_state("circuit_breaker", "off", "ready")
            env = os.environ.copy()
            env.update(
                {
                    "KIWOOM_TRADING_DB": str(db_path),
                    "TRADING_MODE": "paper",
                    "ENABLE_LIVE_TRADING": "false",
                    "KIWOOM_SCAN_SYMBOL": "498270",
                }
            )

            result = subprocess.run(
                [sys.executable, "scripts/show_automation_status.py"],
                cwd=Path(__file__).resolve().parents[1],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("[Kiwoom Agent Trader 자동화 상태]", result.stdout)
            self.assertIn("mode: paper", result.stdout)
            self.assertIn("live trading: disabled", result.stdout)


if __name__ == "__main__":
    unittest.main()
