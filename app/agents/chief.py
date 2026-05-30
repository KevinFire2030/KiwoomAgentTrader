from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.agents.market_analysis import MarketAnalysisAgent
from app.agents.models import WorkflowResult
from app.agents.risk_management import RiskManagementAgent
from app.agents.stock_recommendation import StockRecommendationAgent
from app.agents.trade_execution import TradeExecutionAgent
from app.agents.trading_strategy import TradingStrategyAgent
from app.policies.risk_policy import RiskPolicy
from app.storage.repository import TradingRepository


class ChiefInvestmentAgent:
    name = "chief_investment_agent"

    def __init__(self, repository: TradingRepository | None = None) -> None:
        self.repository = repository or TradingRepository(Path("data") / "trading.db")

    def run_intraday_signal_scan(self, symbol: str, mode: str = "paper") -> WorkflowResult:
        self.repository.initialize()
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S")

        market = MarketAnalysisAgent().analyze()
        recommendation = StockRecommendationAgent().recommend(symbol)
        ticket_candidate = TradingStrategyAgent().create_ticket_candidate(run_id, market, recommendation)
        risk_review = RiskManagementAgent(RiskPolicy(mode=mode)).review(ticket_candidate)

        ticket = risk_review.ticket if risk_review.approved else None
        execution_result = "not_executed"
        if mode == "paper" and ticket is not None:
            execution_result = TradeExecutionAgent().execute_paper(ticket)

        report = self._format_report(run_id, symbol, market.market_regime, recommendation.action_bias, recommendation.score, risk_review.approved, ticket.ticket_id if ticket else "none", execution_result)
        self.repository.record_agent_run(run_id, "intraday_signal_scan", mode, "completed", report)
        if ticket is not None:
            self.repository.record_trade_ticket(run_id, ticket)
        self.repository.record_risk_review(run_id, risk_review)
        return WorkflowResult(run_id, report, ticket, risk_review)

    def _format_report(self, run_id: str, symbol: str, market_regime: str, action_bias: str, score: int, risk_approved: bool, ticket_id: str, execution_result: str) -> str:
        return "\n".join([
            "[Chief Investment Agent]",
            "Kiwoom Agent Trader workflow completed",
            f"run_id: {run_id}",
            f"대상: {symbol}",
            f"시장 분석: {market_regime}",
            f"종목 추천: {action_bias} / score={score}",
            f"리스크 승인: {risk_approved}",
            f"티켓: {ticket_id}",
            f"실행 결과: {execution_result}",
        ])
