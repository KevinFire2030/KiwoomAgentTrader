from datetime import datetime

from app.agents.market_analysis import MarketAnalysisAgent
from app.agents.risk_management import RiskManagementAgent
from app.agents.stock_recommendation import StockRecommendationAgent
from app.agents.trade_execution import TradeExecutionAgent
from app.agents.trading_strategy import TradingStrategyAgent
from app.agents.models import WorkflowResult
from app.policies.risk_policy import RiskPolicy


def run_intraday_signal_scan(symbol: str, mode: str = "paper") -> WorkflowResult:
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    market = MarketAnalysisAgent().analyze()
    recommendation = StockRecommendationAgent().recommend(symbol)
    ticket_candidate = TradingStrategyAgent().create_ticket_candidate(run_id, market, recommendation)
    risk_review = RiskManagementAgent(RiskPolicy(mode=mode)).review(ticket_candidate)
    execution_result = "not_executed"
    if mode == "paper" and risk_review.approved and risk_review.ticket is not None:
        execution_result = TradeExecutionAgent().execute_paper(risk_review.ticket)
    report = "\n".join([
        "[Kiwoom Agent Trader MVP]",
        f"run_id: {run_id}",
        f"대상: {symbol}",
        f"시장 분석: {market.market_regime} / confidence={market.confidence}",
        f"종목 추천: {recommendation.action_bias} / score={recommendation.score}",
        f"리스크 승인: {risk_review.approved}",
        f"티켓: {risk_review.ticket.ticket_id if risk_review.ticket else 'none'}",
        f"실행 결과: {execution_result}",
    ])
    return WorkflowResult(run_id, report, risk_review.ticket, risk_review)
