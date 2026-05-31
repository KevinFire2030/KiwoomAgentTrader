from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.storage.repository import TradingRepository

KST = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class DigestTicketSummary:
    ticket_id: str
    symbol: str
    outcome: str
    realized_pnl_krw: int
    summary: str


@dataclass(frozen=True)
class PostTradeDigest:
    date_kst: str
    ticket_count: int
    total_realized_pnl_krw: int
    outcome_counts: dict[str, int]
    tickets: list[DigestTicketSummary] = field(default_factory=list)
    best_ticket_id: str | None = None
    best_pnl_krw: int | None = None
    worst_ticket_id: str | None = None
    worst_pnl_krw: int | None = None
    top_lessons: list[str] = field(default_factory=list)
    circuit_breaker_state: str = "off"
    circuit_breaker_reason: str = ""


class PostTradeDigestBuilder:
    def __init__(self, repository: TradingRepository) -> None:
        self.repository = repository

    def build_for_date(self, target_date: str | date) -> PostTradeDigest:
        self.repository.initialize()
        date_key = _normalize_date_key(target_date)
        rows = [
            row
            for row in self.repository.list_post_trade_analyses()
            if _created_at_kst_date(row["created_at"]) == date_key
        ]
        tickets = [
            DigestTicketSummary(
                ticket_id=str(row["ticket_id"]),
                symbol=str(row["symbol"]),
                outcome=str(row["outcome"]),
                realized_pnl_krw=int(row["realized_pnl_krw"] or 0),
                summary=str(row["summary"]),
            )
            for row in rows
        ]
        total_pnl = sum(ticket.realized_pnl_krw for ticket in tickets)
        outcome_counts = {"win": 0, "loss": 0, "flat": 0}
        for ticket in tickets:
            outcome_counts[ticket.outcome] = outcome_counts.get(ticket.outcome, 0) + 1

        best = max(tickets, key=lambda ticket: ticket.realized_pnl_krw, default=None)
        worst = min(tickets, key=lambda ticket: ticket.realized_pnl_krw, default=None)
        state = self.repository.get_runtime_state("circuit_breaker")
        return PostTradeDigest(
            date_kst=date_key,
            ticket_count=len(tickets),
            total_realized_pnl_krw=total_pnl,
            outcome_counts=outcome_counts,
            tickets=tickets,
            best_ticket_id=best.ticket_id if best else None,
            best_pnl_krw=best.realized_pnl_krw if best else None,
            worst_ticket_id=worst.ticket_id if worst else None,
            worst_pnl_krw=worst.realized_pnl_krw if worst else None,
            top_lessons=_top_lessons(rows),
            circuit_breaker_state=str(state["state_value"]) if state is not None else "off",
            circuit_breaker_reason=str(state["reason"]) if state is not None else "",
        )


def format_post_trade_digest(digest: PostTradeDigest) -> str:
    win = digest.outcome_counts.get("win", 0)
    loss = digest.outcome_counts.get("loss", 0)
    flat = digest.outcome_counts.get("flat", 0)
    lines = [
        "[Kiwoom Agent Trader 일일 사후 분석]",
        f"날짜: {digest.date_kst} KST",
        f"티켓 수: {digest.ticket_count}",
        f"총 실현손익: {_format_signed_krw(digest.total_realized_pnl_krw)}",
        f"win/loss/flat: {win}/{loss}/{flat}",
        f"Circuit breaker: {digest.circuit_breaker_state}"
        + (f" ({digest.circuit_breaker_reason})" if digest.circuit_breaker_reason else ""),
    ]
    if digest.ticket_count == 0:
        lines.extend(["", "분석된 거래가 없습니다."])
        return "\n".join(lines)

    lines.extend(
        [
            "",
            f"최고 티켓: {digest.best_ticket_id} {_format_signed_krw(digest.best_pnl_krw or 0)}",
            f"최저 티켓: {digest.worst_ticket_id} {_format_signed_krw(digest.worst_pnl_krw or 0)}",
            "",
            "티켓별 요약:",
        ]
    )
    for ticket in digest.tickets:
        lines.append(
            f"- {ticket.ticket_id} / {ticket.symbol} / {ticket.outcome} / {_format_signed_krw(ticket.realized_pnl_krw)}: {ticket.summary}"
        )

    lines.extend(["", "주요 개선 메모:"])
    if digest.top_lessons:
        lines.extend(f"- {lesson}" for lesson in digest.top_lessons)
    else:
        lines.append("- 기록된 개선 메모가 없습니다.")
    return "\n".join(lines)


def _top_lessons(rows, limit: int = 5) -> list[str]:
    counter: Counter[str] = Counter()
    first_seen: dict[str, int] = {}
    sequence = 0
    for row in rows:
        try:
            lessons = json.loads(str(row["lessons_json"]))
        except json.JSONDecodeError:
            lessons = []
        if not isinstance(lessons, list):
            continue
        for lesson in lessons:
            text = str(lesson).strip()
            if not text:
                continue
            counter[text] += 1
            first_seen.setdefault(text, sequence)
            sequence += 1
    return [lesson for lesson, _ in sorted(counter.items(), key=lambda item: (-item[1], first_seen[item[0]]))[:limit]]


def _created_at_kst_date(raw: str) -> str:
    dt = datetime.fromisoformat(str(raw))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=KST)
    return dt.astimezone(KST).date().isoformat()


def _normalize_date_key(value: str | date) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return date.fromisoformat(value).isoformat()


def _format_signed_krw(value: int) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:,}원"
