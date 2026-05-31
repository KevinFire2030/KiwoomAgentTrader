from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.agents.market_analysis import MarketAnalysisAgent
from app.agents.models import AccountSnapshot, AccountState, MarketSnapshot, WorkflowResult
from app.agents.risk_management import RiskManagementAgent
from app.agents.stock_recommendation import StockRecommendationAgent
from app.agents.trading_strategy import TradingStrategyAgent
from app.policies.risk_policy import RiskPolicy
from app.storage.repository import TradingRepository


class ChiefInvestmentAgent:
    name = "chief_investment_agent"

    def __init__(self, repository: TradingRepository | None = None) -> None:
        self.repository = repository or TradingRepository(Path("data") / "trading.db")

    def run_intraday_signal_scan(
        self,
        symbol: str,
        mode: str = "paper",
        market_snapshot: MarketSnapshot | None = None,
        account_snapshot: AccountSnapshot | None = None,
        account_state: AccountState | None = None,
    ) -> WorkflowResult:
        self.repository.initialize()
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S")

        market = MarketAnalysisAgent().analyze()
        recommendation = StockRecommendationAgent().recommend(symbol)
        ticket_candidate = TradingStrategyAgent().create_ticket_candidate(run_id, market, recommendation, market_snapshot=market_snapshot)
        risk_review = RiskManagementAgent(RiskPolicy(mode=mode)).review(ticket_candidate, account_state=account_state)

        ticket = risk_review.ticket if risk_review.approved else None
        execution_result = "not_executed"
        if ticket is not None:
            execution_result = "pending_user_approval"

        report = self._format_report(
            run_id,
            symbol,
            market.market_regime,
            recommendation.action_bias,
            recommendation.score,
            risk_review.approved,
            ticket.ticket_id if ticket else "none",
            execution_result,
            market_snapshot,
            account_snapshot,
            account_state,
        )
        self.repository.record_agent_run(run_id, "intraday_signal_scan", mode, "completed", report)
        if market_snapshot is not None:
            self.repository.record_market_snapshot(run_id, market_snapshot)
        if account_snapshot is not None:
            self.repository.record_account_snapshot(run_id, account_snapshot)
        if account_state is not None:
            self.repository.record_account_state(run_id, account_state)
        if ticket is not None:
            self.repository.record_trade_ticket(run_id, ticket)
        self.repository.record_risk_review(run_id, risk_review)
        return WorkflowResult(run_id, report, ticket, risk_review)

    def _format_report(
        self,
        run_id: str,
        symbol: str,
        market_regime: str,
        action_bias: str,
        score: int,
        risk_approved: bool,
        ticket_id: str,
        execution_result: str,
        market_snapshot: MarketSnapshot | None = None,
        account_snapshot: AccountSnapshot | None = None,
        account_state: AccountState | None = None,
    ) -> str:
        lines = [
            "[Chief Investment Agent]",
            "Kiwoom Agent Trader workflow completed",
            f"run_id: {run_id}",
            f"대상: {symbol}",
            f"시장 분석: {market_regime}",
            f"종목 추천: {action_bias} / score={score}",
        ]
        if market_snapshot is not None:
            change_rate = "N/A" if market_snapshot.change_rate is None else f"{market_snapshot.change_rate:+.2f}%"
            lines.extend([
                f"현재가: {market_snapshot.current_price:,}원",
                f"등락률: {change_rate}",
            ])
        if account_snapshot is not None:
            lines.extend([
                f"예수금/추정자산: {account_snapshot.deposit_asset_amount:,}원",
                f"평가금액: {account_snapshot.total_evaluation_amount:,}원",
                f"보유종목 수: {account_snapshot.positions_count}",
            ])
        if account_state is not None:
            lines.extend([
                f"최근 입금합계: {account_state.recent_deposit_krw:,}원",
                f"최근 출금합계: {account_state.recent_withdraw_krw:,}원",
                f"최근 순입금: {account_state.net_cash_flow_krw:,}원",
                f"투자 가능 현금: {account_state.investable_cash_krw:,}원",
            ])
        lines.extend([
            f"리스크 승인: {risk_approved}",
            f"티켓: {ticket_id}",
            f"실행 결과: {execution_result}",
        ])
        return "\n".join(lines)
