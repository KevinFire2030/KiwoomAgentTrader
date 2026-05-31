from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.storage.repository import PostTradeAnalysisRecord, TradingRepository


@dataclass(frozen=True)
class PostTradeAnalysis:
    ticket_id: str
    run_id: str
    symbol: str
    outcome: str
    realized_pnl_krw: int
    summary: str
    lessons: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PostTradeAnalyzer:
    """Create deterministic post-trade lessons from stored ticket/run/fill data."""

    def __init__(self, repository: TradingRepository) -> None:
        self.repository = repository

    def analyze_ticket(self, ticket_id: str) -> PostTradeAnalysis:
        self.repository.initialize()
        ticket = self.repository.get_trade_ticket(ticket_id)
        if ticket is None:
            raise ValueError(f"ticket not found: {ticket_id}")

        run_id = str(ticket["run_id"])
        symbol = str(ticket["symbol"])
        pnl_events = self.repository.get_realized_pnl_events_for_ticket(ticket_id)
        realized_pnl = sum(int(row["realized_pnl_krw"] or 0) for row in pnl_events)
        outcome = _classify_outcome(realized_pnl)
        risk_review = self.repository.get_latest_risk_review(ticket_id)
        order_events = self.repository.get_order_events(ticket_id)
        summary = _build_summary(ticket, realized_pnl, outcome, len(pnl_events), len(order_events))
        lessons = _build_lessons(ticket, risk_review, order_events, realized_pnl, outcome)

        analysis = PostTradeAnalysis(
            ticket_id=ticket_id,
            run_id=run_id,
            symbol=symbol,
            outcome=outcome,
            realized_pnl_krw=realized_pnl,
            summary=summary,
            lessons=lessons,
        )
        self.repository.record_post_trade_analysis(
            PostTradeAnalysisRecord(
                ticket_id=analysis.ticket_id,
                run_id=analysis.run_id,
                symbol=analysis.symbol,
                outcome=analysis.outcome,
                realized_pnl_krw=analysis.realized_pnl_krw,
                summary=analysis.summary,
                lessons=analysis.lessons,
                created_at=analysis.created_at,
            )
        )
        return analysis


def format_post_trade_report(analysis: PostTradeAnalysis) -> str:
    lines = [
        "[Kiwoom Agent Trader 사후 분석]",
        f"티켓: {analysis.ticket_id}",
        f"대상: {analysis.symbol}",
        f"결과: {analysis.outcome}",
        f"실현손익: {_format_signed_krw(analysis.realized_pnl_krw)}",
        "",
        analysis.summary,
        "",
        "개선 메모:",
    ]
    lines.extend(f"- {lesson}" for lesson in analysis.lessons)
    return "\n".join(lines)


def _classify_outcome(realized_pnl: int) -> str:
    if realized_pnl > 0:
        return "win"
    if realized_pnl < 0:
        return "loss"
    return "flat"


def _build_summary(ticket, realized_pnl: int, outcome: str, pnl_event_count: int, order_event_count: int) -> str:
    return (
        f"{ticket['symbol']} {ticket['side']} 티켓 {ticket['ticket_id']}은 {outcome}으로 분류됩니다. "
        f"수량 {ticket['quantity']}주, 추정 진입금액 {int(ticket['estimated_amount_krw']):,}원, "
        f"실현손익 {_format_signed_krw(realized_pnl)}입니다. "
        f"연결된 손익 이벤트 {pnl_event_count}건, 주문 이벤트 {order_event_count}건을 확인했습니다."
    )


def _build_lessons(ticket, risk_review, order_events, realized_pnl: int, outcome: str) -> list[str]:
    lessons: list[str] = []
    if risk_review is not None:
        reasons = _load_json_list(risk_review["reasons_json"])
        lessons.append(f"Risk review 기준을 사후 검토하세요: {', '.join(reasons) if reasons else risk_review['risk_level']}")
    else:
        lessons.append("Risk review 기록이 없어 사후 원인 분석 신뢰도가 낮습니다.")

    if not order_events:
        lessons.append("주문 이벤트가 없어 실제 실행 경로와 체결 경로를 추가로 확인해야 합니다.")
    else:
        statuses = ", ".join(str(event["status"]) for event in order_events)
        lessons.append(f"주문 이벤트 상태 흐름을 확인하세요: {statuses}")

    if outcome == "loss":
        lessons.append(f"손실 거래입니다. 진입 근거와 손절/청산 조건을 재검토하세요: {_format_signed_krw(realized_pnl)}")
    elif outcome == "win":
        lessons.append("수익 거래입니다. 동일 조건을 반복 가능한 규칙으로 보존할지 검토하세요.")
    else:
        lessons.append("손익이 0원입니다. 수수료/세금 반영 여부와 체결 품질을 확인하세요.")

    if str(ticket["status"]) not in {"paper_executed", "live_order_submitted"}:
        lessons.append(f"티켓 상태가 실행 완료 계열이 아닙니다: {ticket['status']}")
    return lessons


def _load_json_list(raw: str) -> list[str]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [str(item) for item in data]


def _format_signed_krw(value: int) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:,}원"
