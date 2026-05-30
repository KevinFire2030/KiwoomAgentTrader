from app.agents.models import TradeTicket


class TradeExecutionAgent:
    name = "trade_execution_agent"

    def execute_paper(self, ticket: TradeTicket) -> str:
        if not ticket.risk_approved:
            raise PermissionError("Risk approval is required before execution.")
        return f"paper_order_recorded:{ticket.ticket_id}:{ticket.symbol}:{ticket.side}:{ticket.quantity}"
