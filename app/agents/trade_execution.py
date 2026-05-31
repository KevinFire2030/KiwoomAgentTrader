from app.agents.models import TradeTicket
from app.kiwoom.orders import KiwoomOrderClient


class TradeExecutionAgent:
    name = "trade_execution_agent"

    def execute_paper(self, ticket: TradeTicket) -> str:
        if not ticket.risk_approved:
            raise PermissionError("Risk approval is required before execution.")
        return f"paper_order_recorded:{ticket.ticket_id}:{ticket.symbol}:{ticket.side}:{ticket.quantity}"

    def prepare_live_manual(self, ticket: TradeTicket) -> str:
        if not ticket.risk_approved:
            raise PermissionError("Risk approval is required before live_manual preparation.")
        if not ticket.user_approved:
            raise PermissionError("User approval is required before live_manual preparation.")
        return f"live_manual_ready:{ticket.ticket_id}:{ticket.symbol}:{ticket.side}:{ticket.quantity}"

    def execute_live_manual(self, ticket: TradeTicket, order_client: KiwoomOrderClient, *, enable_live_trading: bool) -> str:
        if not enable_live_trading:
            raise PermissionError("Live trading is disabled. Set ENABLE_LIVE_TRADING=true only after explicit user/broker readiness.")
        prepared = order_client.build_order_request(ticket)
        result = order_client.place_order(ticket)
        if not result.accepted:
            raise RuntimeError(f"Kiwoom live order rejected: return_code={result.return_code} return_msg={result.return_msg}")
        return f"live_order_submitted:{prepared.ticket_id}:{prepared.api_id}:{result.return_code}"
