from dataclasses import replace

from app.agents.models import AccountState, RiskReview, TradeTicket
from app.policies.risk_policy import RiskPolicy


class RiskManagementAgent:
    name = "risk_management_agent"

    def __init__(self, policy: RiskPolicy) -> None:
        self.policy = policy

    def review(self, ticket: TradeTicket | None, account_state: AccountState | None = None) -> RiskReview:
        if ticket is None:
            return RiskReview(self.name, False, "none", None, ["검토할 주문 티켓이 없습니다."])

        reasons: list[str] = []
        warnings: list[str] = []
        adjusted_ticket = ticket

        if adjusted_ticket.symbol not in self.policy.allowed_symbols:
            reasons.append("허용 종목이 아닙니다.")

        if account_state is not None:
            adjusted_ticket, cash_reasons = self._fit_to_account_state(adjusted_ticket, account_state)
            reasons.extend(cash_reasons)
            if account_state.recent_withdraw_krw > account_state.recent_deposit_krw:
                warnings.append("최근 1년 출금액이 입금액보다 커서 보수적 검토가 필요합니다.")

        if adjusted_ticket.estimated_amount_krw > self.policy.max_order_amount_krw:
            if account_state is None:
                reasons.append("1회 주문 최대 금액을 초과했습니다.")
            else:
                adjusted_ticket, cap_reasons = self._shrink_to_amount_cap(adjusted_ticket, self.policy.max_order_amount_krw, "1회 주문 최대 금액")
                reasons.extend(cap_reasons)

        hard_reasons = [reason for reason in reasons if "축소했습니다" not in reason]
        if hard_reasons:
            return RiskReview(self.name, False, "high", replace(adjusted_ticket, status="risk_rejected"), hard_reasons)

        approved_ticket = replace(adjusted_ticket, risk_approved=True, risk_approved_by=self.name, status="risk_approved")
        risk_level = "medium" if warnings else "low"
        final_reasons = reasons + warnings + ["MVP 리스크 정책을 통과했습니다."]
        return RiskReview(self.name, True, risk_level, approved_ticket, final_reasons)

    def _fit_to_account_state(self, ticket: TradeTicket, account_state: AccountState) -> tuple[TradeTicket, list[str]]:
        if ticket.side != "buy":
            return ticket, []
        return self._shrink_to_amount_cap(ticket, account_state.investable_cash_krw, "투자 가능 현금")

    def _shrink_to_amount_cap(self, ticket: TradeTicket, amount_cap_krw: int, label: str) -> tuple[TradeTicket, list[str]]:
        if ticket.limit_price is None or ticket.limit_price <= 0:
            return ticket, [f"{label} 검토를 위해 유효한 지정가가 필요합니다."]
        if ticket.estimated_amount_krw <= amount_cap_krw:
            return ticket, []

        adjusted_quantity = amount_cap_krw // ticket.limit_price
        if adjusted_quantity < 1:
            if label == "투자 가능 현금":
                return ticket, ["투자 가능 현금으로 1주도 매수할 수 없습니다."]
            return ticket, [f"{label}으로 1주도 매수할 수 없습니다."]

        adjusted_ticket = replace(ticket, quantity=adjusted_quantity, status="pending_risk_review_adjusted")
        return adjusted_ticket, [f"{label}에 맞춰 수량을 {ticket.quantity}주에서 {adjusted_quantity}주로 축소했습니다."]
