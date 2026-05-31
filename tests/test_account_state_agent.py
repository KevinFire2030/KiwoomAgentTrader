import tempfile
import unittest
from pathlib import Path

from app.agents.account_state import AccountStateAgent
from app.agents.models import AccountSnapshot
from app.kiwoom.transactions import summarize_transactions
from app.storage.repository import TradingRepository


class AccountStateAgentTest(unittest.TestCase):
    def test_summarizes_cash_flow_and_investable_cash(self):
        account_snapshot = AccountSnapshot(
            account_no_masked="63***96",
            deposit_asset_amount=303493,
            total_evaluation_amount=0,
            positions_count=0,
            source="kiwoom_rest",
            raw={},
        )
        transaction_summary = summarize_transactions([
            {"io_tp_nm": "입금", "trde_amt": "000000000050000", "entra_remn": "000000000050000"},
            {"io_tp_nm": "출금", "trde_amt": "000000000010000", "entra_remn": "000000000040000"},
            {"io_tp_nm": "입금", "trde_amt": "000000000000320", "entra_remn": "000000000040320"},
        ])

        state = AccountStateAgent().analyze(account_snapshot, transaction_summary)

        self.assertEqual(state.agent, "account_state_agent")
        self.assertEqual(state.cash_balance_krw, 303493)
        self.assertEqual(state.total_evaluation_krw, 0)
        self.assertEqual(state.positions_count, 0)
        self.assertEqual(state.recent_deposit_krw, 50320)
        self.assertEqual(state.recent_withdraw_krw, 10000)
        self.assertEqual(state.net_cash_flow_krw, 40320)
        self.assertEqual(state.investable_cash_krw, 91047)
        self.assertIn("최근 순입금", state.summary)

    def test_chief_workflow_persists_account_state_when_provided(self):
        from app.agents.chief import ChiefInvestmentAgent
        from app.agents.models import AccountState, MarketSnapshot

        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            account_snapshot = AccountSnapshot("63***96", 303493, 0, 0, "kiwoom_rest", {})
            market_snapshot = MarketSnapshot("498270", "KIWOOM 미국양자컴퓨팅 ETF", 18600, 6.65, "kiwoom_rest", {})
            account_state = AccountState(
                agent="account_state_agent",
                account_no_masked="63***96",
                cash_balance_krw=303493,
                total_evaluation_krw=0,
                positions_count=0,
                recent_deposit_krw=303277,
                recent_withdraw_krw=0,
                net_cash_flow_krw=303277,
                investable_cash_krw=91047,
                summary="최근 순입금 303,277원, 투자 가능 현금 91,047원",
                warnings=[],
            )

            result = ChiefInvestmentAgent(repository=repo).run_intraday_signal_scan(
                "498270",
                mode="paper",
                market_snapshot=market_snapshot,
                account_snapshot=account_snapshot,
                account_state=account_state,
            )

            self.assertIn("투자 가능 현금: 91,047원", result.report)
            stored = repo.get_account_state(result.run_id)
            self.assertEqual(stored["investable_cash_krw"], 91047)
            self.assertEqual(stored["net_cash_flow_krw"], 303277)


if __name__ == "__main__":
    unittest.main()
