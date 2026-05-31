from app.agents.models import MarketAnalysis, MarketSnapshot, Recommendation, TradeTicket


class TradingStrategyAgent:
    name = "trading_strategy_agent"

    def create_ticket_candidate(
        self,
        run_id: str,
        market: MarketAnalysis,
        recommendation: Recommendation,
        market_snapshot: MarketSnapshot | None = None,
    ) -> TradeTicket | None:
        if market.market_regime == "risk_off" or recommendation.action_bias == "avoid":
            return None
        limit_price = market_snapshot.current_price if market_snapshot else 10000
        return TradeTicket(
            ticket_id=f"TT-{run_id}-001",
            symbol=recommendation.symbol,
            side="buy",
            quantity=3,
            order_type="limit",
            limit_price=limit_price,
            created_by=self.name,
            status="pending_risk_review",
        )
