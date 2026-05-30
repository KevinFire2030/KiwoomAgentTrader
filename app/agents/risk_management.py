from dataclasses import replace

from app.agents.models import RiskReview, TradeTicket
from app.policies.risk_policy import RiskPolicy


class RiskManagementAgent:
    name = "risk_management_agent"

    def __init__(self, policy: RiskPolicy) -> None:
        self.policy = policy

    def review(self, ticket: TradeTicket | None) -> RiskReview:
        if ticket is None:
            return RiskReview(self.name, False, "none", None, ["검토할 주문 티켓이 없습니다."])
        reasons: list[str] = []
        if ticket.symbol not in self.policy.allowed_symbols:
            reasons.append("허용 종목이 아닙니다.")
        if ticket.estimated_amount_krw > self.policy.max_order_amount_krw:
            reasons.append("1회 주문 최대 금액을 초과했습니다.")
        if reasons:
            return RiskReview(self.name, False, "high", replace(ticket, status="risk_rejected"), reasons)
        approved_ticket = replace(ticket, risk_approved=True, risk_approved_by=self.name, status="risk_approved")
        return RiskReview(self.name, True, "low", approved_ticket, ["MVP 리스크 정책을 통과했습니다."])
