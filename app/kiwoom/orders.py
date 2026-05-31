from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.agents.models import TradeTicket
from app.kiwoom.client import KiwoomRestClient

KiwoomOrderSide = Literal["buy", "sell"]


@dataclass(frozen=True)
class KiwoomOrderRequest:
    ticket_id: str
    endpoint: str
    api_id: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class KiwoomOrderResult:
    ticket_id: str
    accepted: bool
    return_code: int | None
    return_msg: str
    raw: dict[str, Any]


class KiwoomOrderClient:
    """Kiwoom domestic stock order client.

    This client prepares and submits the TR-shaped Kiwoom REST order request.
    It is intentionally not used by the normal workflow unless live trading is
    explicitly enabled at a higher layer.
    """

    endpoint = "/api/dostk/ordr"
    buy_api_id = "kt10000"
    sell_api_id = "kt10001"

    def __init__(self, client: KiwoomRestClient) -> None:
        self.client = client

    def build_order_request(self, ticket: TradeTicket, domestic_exchange_type: str = "KRX") -> KiwoomOrderRequest:
        self._validate_ticket(ticket)
        api_id = self.buy_api_id if ticket.side == "buy" else self.sell_api_id
        payload = {
            "dmst_stex_tp": domestic_exchange_type,
            "stk_cd": ticket.symbol,
            "ord_qty": str(ticket.quantity),
            "ord_uv": str(ticket.limit_price or 0),
            "trde_tp": self._trade_type(ticket),
            "cond_uv": "",
        }
        return KiwoomOrderRequest(ticket.ticket_id, self.endpoint, api_id, payload)

    def place_order(self, ticket: TradeTicket, domestic_exchange_type: str = "KRX") -> KiwoomOrderResult:
        request = self.build_order_request(ticket, domestic_exchange_type=domestic_exchange_type)
        response = self.client.post(request.endpoint, payload=request.payload, api_id=request.api_id)
        return KiwoomOrderResult(
            ticket_id=ticket.ticket_id,
            accepted=str(response.get("return_code", "")).strip() in {"0", "0000"},
            return_code=_optional_int(response.get("return_code")),
            return_msg=str(response.get("return_msg", "")),
            raw=response,
        )

    def _validate_ticket(self, ticket: TradeTicket) -> None:
        if not ticket.risk_approved:
            raise PermissionError("Risk approval is required before live order preparation.")
        if not ticket.user_approved:
            raise PermissionError("User approval is required before live order preparation.")
        if ticket.quantity <= 0:
            raise ValueError("Order quantity must be positive.")
        if ticket.order_type == "limit" and (ticket.limit_price is None or ticket.limit_price <= 0):
            raise ValueError("Limit orders require a positive limit price.")
        if ticket.side not in {"buy", "sell"}:
            raise ValueError(f"Unsupported order side: {ticket.side}")

    def _trade_type(self, ticket: TradeTicket) -> str:
        # Kiwoom domestic stock order TR uses string trade-type codes. Keep this
        # mapping centralized so live validation can be adjusted if Kiwoom changes
        # the documented code set.
        if ticket.order_type == "limit":
            return "0"  # normal/limit
        if ticket.order_type == "market":
            return "3"  # market
        raise ValueError(f"Unsupported order type: {ticket.order_type}")


def _optional_int(value: Any) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None
