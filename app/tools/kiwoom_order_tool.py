from __future__ import annotations

from app.agents.models import TradeTicket
from app.kiwoom.orders import KiwoomOrderClient


class KiwoomOrderTool:
    """Thin tool boundary for the Trade Execution Agent.

    Live submission remains disabled unless the caller passes an explicitly
    enabled order client path. The default helper only prepares the request for
    inspection/audit.
    """

    def prepare_order(self, approved_ticket: TradeTicket, order_client: KiwoomOrderClient) -> dict:
        request = order_client.build_order_request(approved_ticket)
        return {
            "ticket_id": request.ticket_id,
            "endpoint": request.endpoint,
            "api_id": request.api_id,
            "payload": request.payload,
        }

    def place_order(self, approved_ticket: dict) -> dict:
        raise NotImplementedError("Live order execution is disabled until live_manual is explicitly enabled.")
