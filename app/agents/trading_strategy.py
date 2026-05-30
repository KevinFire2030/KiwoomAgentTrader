from app.agents.models import MarketAnalysis, Recommendation, TradeTicket


class TradingStrategyAgent:
    name = "trading_strategy_agent"

    def create_ticket_candidate(self, run_id: str, market: MarketAnalysis, recommendation: Recommendation) -> TradeTicket | None:
        if market.market_regime == "risk_off" or recommendation.action_bias == "avoid":
            return None
        return TradeTicket(
            ticket_id=f"TT-{run_id}-001",
            symbol=recommendation.symbol,
            side="buy",
            quantity=3,
            order_type="limit",
            limit_price=10000,
            created_by=self.name,
            status="pending_risk_review",
        )
