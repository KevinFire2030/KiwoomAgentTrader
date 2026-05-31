from __future__ import annotations

from app.agents.models import AccountSnapshot, AccountState
from app.kiwoom.transactions import TransactionSummary, format_krw


class AccountStateAgent:
    name = "account_state_agent"

    def __init__(self, investable_cash_ratio: float = 0.30) -> None:
        self.investable_cash_ratio = investable_cash_ratio

    def analyze(self, account_snapshot: AccountSnapshot, transaction_summary: TransactionSummary) -> AccountState:
        net_cash_flow = transaction_summary.deposit_total - transaction_summary.withdraw_total
        investable_cash = int(account_snapshot.deposit_asset_amount * self.investable_cash_ratio)
        warnings: list[str] = []
        if account_snapshot.deposit_asset_amount <= 0:
            warnings.append("사용 가능한 현금성 잔고가 없습니다.")
        if transaction_summary.withdraw_total > transaction_summary.deposit_total:
            warnings.append("최근 1년 출금액이 입금액보다 큽니다.")

        summary = " / ".join([
            f"현금성 잔고 {format_krw(account_snapshot.deposit_asset_amount)}",
            f"최근 순입금 {format_krw(net_cash_flow)}",
            f"투자 가능 현금 {format_krw(investable_cash)}",
        ])
        return AccountState(
            agent=self.name,
            account_no_masked=account_snapshot.account_no_masked,
            cash_balance_krw=account_snapshot.deposit_asset_amount,
            total_evaluation_krw=account_snapshot.total_evaluation_amount,
            positions_count=account_snapshot.positions_count,
            recent_deposit_krw=transaction_summary.deposit_total,
            recent_withdraw_krw=transaction_summary.withdraw_total,
            net_cash_flow_krw=net_cash_flow,
            investable_cash_krw=investable_cash,
            summary=summary,
            warnings=warnings,
        )
