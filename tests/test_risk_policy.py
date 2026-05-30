import unittest

from app.agents.models import TradeTicket
from app.agents.risk_management import RiskManagementAgent
from app.policies.risk_policy import RiskPolicy


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


if __name__ == "__main__":
    unittest.main()
