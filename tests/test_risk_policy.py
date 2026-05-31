import unittest

from app.agents.models import AccountState, TradeTicket
from app.agents.risk_management import RiskManagementAgent
from app.policies.risk_policy import RiskPolicy


def account_state(investable_cash: int, deposit: int = 303277, withdraw: int = 0, positions_count: int = 0) -> AccountState:
    return AccountState(
        agent="account_state_agent",
        account_no_masked="63***96",
        cash_balance_krw=303493,
        total_evaluation_krw=0,
        positions_count=positions_count,
        recent_deposit_krw=deposit,
        recent_withdraw_krw=withdraw,
        net_cash_flow_krw=deposit - withdraw,
        investable_cash_krw=investable_cash,
        summary="test account state",
    )


class RiskPolicyTest(unittest.TestCase):
    def test_allows_small_allowed_symbol_ticket(self):
        ticket = TradeTicket("TT-test-001", "498270", "buy", 3, "limit", 10000, "trading_strategy_agent")
        review = RiskManagementAgent(RiskPolicy()).review(ticket)
        self.assertTrue(review.approved)
        self.assertTrue(review.ticket.risk_approved)

    def test_rejects_disallowed_symbol(self):
        ticket = TradeTicket("TT-test-002", "000000", "buy", 1, "limit", 10000, "trading_strategy_agent")
        review = RiskManagementAgent(RiskPolicy()).review(ticket)
        self.assertFalse(review.approved)

    def test_shrinks_buy_quantity_to_investable_cash(self):
        ticket = TradeTicket("TT-test-003", "498270", "buy", 3, "limit", 40000, "trading_strategy_agent")

        review = RiskManagementAgent(RiskPolicy()).review(ticket, account_state=account_state(90_000))

        self.assertTrue(review.approved)
        self.assertEqual(review.ticket.quantity, 2)
        self.assertEqual(review.ticket.estimated_amount_krw, 80_000)
        self.assertIn("투자 가능 현금에 맞춰 수량을 3주에서 2주로 축소했습니다.", review.reasons)

    def test_rejects_when_investable_cash_cannot_buy_one_share(self):
        ticket = TradeTicket("TT-test-004", "498270", "buy", 1, "limit", 40000, "trading_strategy_agent")

        review = RiskManagementAgent(RiskPolicy()).review(ticket, account_state=account_state(30_000))

        self.assertFalse(review.approved)
        self.assertEqual(review.ticket.status, "risk_rejected")
        self.assertIn("투자 가능 현금으로 1주도 매수할 수 없습니다.", review.reasons)

    def test_marks_review_medium_when_recent_withdrawals_exceed_deposits(self):
        ticket = TradeTicket("TT-test-005", "498270", "buy", 1, "limit", 10000, "trading_strategy_agent")

        review = RiskManagementAgent(RiskPolicy()).review(ticket, account_state=account_state(90_000, deposit=10_000, withdraw=50_000))

        self.assertTrue(review.approved)
        self.assertEqual(review.risk_level, "medium")
        self.assertIn("최근 1년 출금액이 입금액보다 커서 보수적 검토가 필요합니다.", review.reasons)


if __name__ == "__main__":
    unittest.main()
