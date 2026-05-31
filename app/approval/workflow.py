from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from app.agents.models import TradeTicket
from app.agents.trade_execution import TradeExecutionAgent
from app.approval.commands import parse_approval_command
from app.storage.repository import TradingRepository


@dataclass(frozen=True)
class ApprovalResult:
    accepted: bool
    action: str
    ticket_id: str | None
    message: str


class OrderClientLike(Protocol):
    def build_order_request(self, ticket: TradeTicket) -> Any:
        ...

    def place_order(self, ticket: TradeTicket) -> Any:
        ...


class ApprovalWorkflow:
    def __init__(self, repository: TradingRepository, order_client: OrderClientLike | None = None, enable_live_trading: bool = False) -> None:
        self.repository = repository
        self.order_client = order_client
        self.enable_live_trading = enable_live_trading

    def handle_text(self, text: str, mode: str = "paper") -> ApprovalResult:
        command = parse_approval_command(text)
        if command is None:
            return ApprovalResult(False, "none", None, "승인/거절 명령이 아닙니다.")

        row = self.repository.get_trade_ticket(command.ticket_id)
        if row is None:
            return ApprovalResult(False, command.action, command.ticket_id, f"티켓을 찾을 수 없습니다: {command.ticket_id}")

        current_status = row["status"]
        if command.action == "final_approve":
            return self._handle_final_approval(row, mode)
        if current_status == "paper_executed":
            return ApprovalResult(False, command.action, command.ticket_id, f"이미 paper 실행된 티켓입니다: {command.ticket_id}")
        if current_status == "live_manual_ready":
            return ApprovalResult(False, command.action, command.ticket_id, f"이미 live_manual 준비 상태인 티켓입니다: {command.ticket_id}")
        if current_status == "live_order_submitted":
            return ApprovalResult(False, command.action, command.ticket_id, f"이미 실주문 제출된 티켓입니다: {command.ticket_id}")
        if current_status == "user_rejected":
            return ApprovalResult(False, command.action, command.ticket_id, f"이미 거절된 티켓입니다: {command.ticket_id}")

        if command.action == "reject":
            self.repository.update_trade_ticket_approval(command.ticket_id, False, "user_rejected")
            return ApprovalResult(True, "reject", command.ticket_id, f"거절 처리 완료: {command.ticket_id}")

        if not bool(row["risk_approved"]):
            return ApprovalResult(False, "approve", command.ticket_id, f"리스크 승인 전 티켓은 승인할 수 없습니다: {command.ticket_id}")

        ticket = self._ticket_from_row(row, user_approved=True, status="user_approved")
        execution_agent = TradeExecutionAgent()
        if mode == "paper":
            execution_result = execution_agent.execute_paper(ticket)
            self.repository.update_trade_ticket_approval(command.ticket_id, True, "paper_executed")
            return ApprovalResult(True, "approve", command.ticket_id, f"승인 및 paper 실행 완료: {execution_result}")
        if mode == "live_manual":
            execution_result = execution_agent.prepare_live_manual(ticket)
            self.repository.update_trade_ticket_approval(command.ticket_id, True, "live_manual_ready")
            return ApprovalResult(True, "approve", command.ticket_id, f"승인 완료, live_manual 주문 준비 상태: {execution_result}")

        self.repository.update_trade_ticket_approval(command.ticket_id, True, "user_approved")
        return ApprovalResult(True, "approve", command.ticket_id, f"승인 처리 완료: {command.ticket_id}")

    def _handle_final_approval(self, row, mode: str) -> ApprovalResult:
        ticket_id = row["ticket_id"]
        if mode != "live_manual":
            return ApprovalResult(False, "final_approve", ticket_id, "최종승인은 live_manual 모드에서만 사용할 수 있습니다.")
        if row["status"] == "live_order_submitted":
            return ApprovalResult(False, "final_approve", ticket_id, f"이미 실주문 제출된 티켓입니다: {ticket_id}")
        if row["status"] != "live_manual_ready":
            return ApprovalResult(False, "final_approve", ticket_id, f"live_manual_ready 상태가 아닌 티켓은 최종승인할 수 없습니다: {ticket_id}")

        ticket = self._ticket_from_row(row, user_approved=True, status="live_manual_ready")
        order_request = {}
        if self.order_client is not None:
            prepared = self.order_client.build_order_request(ticket)
            order_request = {
                "endpoint": prepared.endpoint,
                "api_id": prepared.api_id,
                "payload": prepared.payload,
            }

        if not self.enable_live_trading:
            message = "실주문 차단: ENABLE_LIVE_TRADING=true가 아니므로 주문 API를 호출하지 않았습니다."
            self.repository.record_order_event(ticket_id, mode, "final_approval", "blocked_live_disabled", order_request, {}, message)
            return ApprovalResult(False, "final_approve", ticket_id, message)
        if self.order_client is None:
            message = "실주문 차단: KiwoomOrderClient가 연결되지 않았습니다."
            self.repository.record_order_event(ticket_id, mode, "final_approval", "blocked_missing_order_client", order_request, {}, message)
            return ApprovalResult(False, "final_approve", ticket_id, message)

        result = self.order_client.place_order(ticket)
        broker_response = result.raw
        if not result.accepted:
            message = f"키움 주문 거절: return_code={result.return_code} return_msg={result.return_msg}"
            self.repository.record_order_event(ticket_id, mode, "live_order_submit", "broker_rejected", order_request, broker_response, message)
            return ApprovalResult(False, "final_approve", ticket_id, message)

        self.repository.update_trade_ticket_approval(ticket_id, True, "live_order_submitted")
        message = f"실주문 제출 완료: {ticket_id} return_code={result.return_code}"
        self.repository.record_order_event(ticket_id, mode, "live_order_submit", "submitted", order_request, broker_response, message)
        return ApprovalResult(True, "final_approve", ticket_id, message)

    def _ticket_from_row(self, row, user_approved: bool, status: str) -> TradeTicket:
        return TradeTicket(
            ticket_id=row["ticket_id"],
            symbol=row["symbol"],
            side=row["side"],
            quantity=row["quantity"],
            order_type=row["order_type"],
            limit_price=row["limit_price"],
            created_by=row["created_by"],
            risk_approved=bool(row["risk_approved"]),
            risk_approved_by=row["risk_approved_by"],
            user_approved=user_approved,
            status=status,
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(timezone.utc),
        )
