import tempfile
import unittest
from pathlib import Path

from app.agents.chief import ChiefInvestmentAgent
from app.agents.models import AccountSnapshot, MarketSnapshot
from app.storage.repository import TradingRepository


class LiveDataWorkflowTest(unittest.TestCase):
    def test_workflow_uses_market_price_for_ticket_and_persists_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            chief = ChiefInvestmentAgent(repository=repo)
            market_snapshot = MarketSnapshot(
                symbol="498270",
                name="KIWOOM 미국양자컴퓨팅 ETF",
                current_price=18600,
                change_rate=6.65,
                source="kiwoom_rest",
                raw={"cur_prc": "+18600", "pre_rt": "+6.65"},
            )
            account_snapshot = AccountSnapshot(
                account_no_masked="63***96",
                deposit_asset_amount=303493,
                total_evaluation_amount=0,
                positions_count=0,
                source="kiwoom_rest",
                raw={"prsm_dpst_aset_amt": "000000000303493"},
            )

            result = chief.run_intraday_signal_scan(
                "498270",
                mode="paper",
                market_snapshot=market_snapshot,
                account_snapshot=account_snapshot,
            )

            self.assertIsNotNone(result.ticket)
            self.assertEqual(result.ticket.limit_price, 18600)
            self.assertIn("현재가: 18,600원", result.report)
            self.assertIn("예수금/추정자산: 303,493원", result.report)

            stored_market = repo.get_latest_market_snapshot("498270")
            stored_account = repo.get_latest_account_snapshot()
            self.assertEqual(stored_market["current_price"], 18600)
            self.assertEqual(stored_market["change_rate"], 6.65)
            self.assertEqual(stored_account["deposit_asset_amount"], 303493)
            self.assertEqual(stored_account["account_no_masked"], "63***96")


if __name__ == "__main__":
    unittest.main()
