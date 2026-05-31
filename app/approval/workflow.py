from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

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


class ApprovalWorkflow:
    def __init__(self, repository: TradingRepository) -> None:
        self.repository = repository

    def handle_text(self, text: str, mode: str = "paper") -> ApprovalResult:
        command = parse_approval_command(text)
        if command is None:
            return ApprovalResult(False, "none", None, "승인/거절 명령이 아닙니다.")

        row = self.repository.get_trade_ticket(command.ticket_id)
        if row is None:
            return ApprovalResult(False, command.action, command.ticket_id, f"티켓을 찾을 수 없습니다: {command.ticket_id}")

        current_status = row["status"]
        if current_status == "paper_executed":
            return ApprovalResult(False, command.action, command.ticket_id, f"이미 paper 실행된 티켓입니다: {command.ticket_id}")
        if current_status == "user_rejected":
            return ApprovalResult(False, command.action, command.ticket_id, f"이미 거절된 티켓입니다: {command.ticket_id}")

        if command.action == "reject":
            self.repository.update_trade_ticket_approval(command.ticket_id, False, "user_rejected")
            return ApprovalResult(True, "reject", command.ticket_id, f"거절 처리 완료: {command.ticket_id}")

        if not bool(row["risk_approved"]):
            return ApprovalResult(False, "approve", command.ticket_id, f"리스크 승인 전 티켓은 승인할 수 없습니다: {command.ticket_id}")

        ticket = self._ticket_from_row(row, user_approved=True, status="user_approved")
        if mode == "paper":
            execution_result = TradeExecutionAgent().execute_paper(ticket)
            self.repository.update_trade_ticket_approval(command.ticket_id, True, "paper_executed")
            return ApprovalResult(True, "approve", command.ticket_id, f"승인 및 paper 실행 완료: {execution_result}")

        self.repository.update_trade_ticket_approval(command.ticket_id, True, "user_approved")
        return ApprovalResult(True, "approve", command.ticket_id, f"승인 처리 완료: {command.ticket_id}")

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
