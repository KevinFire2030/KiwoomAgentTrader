from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.storage.repository import TradingRepository

KST = ZoneInfo("Asia/Seoul")
START_MARKER = "<!-- KIWOOM_STRATEGY_LESSONS:START -->"
END_MARKER = "<!-- KIWOOM_STRATEGY_LESSONS:END -->"


@dataclass(frozen=True)
class StrategyLessonGroup:
    date_kst: str
    symbol: str
    outcome: str
    ticket_ids: tuple[str, ...]
    total_realized_pnl_krw: int
    lesson_counts: dict[str, int]
    lesson_ticket_ids: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class StrategyLessonExportResult:
    output_path: Path
    groups_exported: int


class StrategyLessonExporter:
    def __init__(self, repository: TradingRepository) -> None:
        self.repository = repository

    def export(self, output_path: str | Path, generated_at: datetime | None = None) -> StrategyLessonExportResult:
        path = Path(output_path)
        markdown = build_strategy_lessons_markdown(self.repository, generated_at=generated_at)
        groups_exported = len(build_strategy_lesson_groups(self.repository))
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        path.write_text(_merge_generated_block(existing, markdown), encoding="utf-8")
        return StrategyLessonExportResult(output_path=path, groups_exported=groups_exported)


def build_strategy_lessons_markdown(
    repository: TradingRepository,
    generated_at: datetime | None = None,
) -> str:
    groups = build_strategy_lesson_groups(repository)
    now = _as_kst(generated_at or datetime.now(tz=KST))
    lines = [
        "# Kiwoom Agent Trader Strategy Lessons",
        "",
        f"Generated at: {now.strftime('%Y-%m-%d %H:%M:%S KST')}",
        "Source: `post_trade_analyses`",
        "",
    ]
    if not groups:
        lines.append("No post-trade lessons exported yet.")
        return "\n".join(lines).rstrip() + "\n"

    for group in groups:
        lines.extend(
            [
                f"## {group.date_kst} / {group.symbol} / {group.outcome}",
                "",
                f"Tickets: {_format_ticket_ids(group.ticket_ids)}",
                f"Total realized P&L: {_format_signed_krw(group.total_realized_pnl_krw)}",
                "",
                "Lessons:",
            ]
        )
        for lesson, count in sorted(group.lesson_counts.items(), key=lambda item: (-item[1], item[0])):
            tickets = _format_ticket_ids(group.lesson_ticket_ids[lesson])
            lines.append(f"- {lesson} ({count}회; tickets: {tickets})")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_strategy_lesson_groups(repository: TradingRepository) -> list[StrategyLessonGroup]:
    repository.initialize()
    grouped_rows: dict[tuple[str, str, str], list] = defaultdict(list)
    for row in repository.list_post_trade_analyses():
        key = (_created_at_kst_date(row["created_at"]), str(row["symbol"]), str(row["outcome"]))
        grouped_rows[key].append(row)

    groups: list[StrategyLessonGroup] = []
    for (date_kst, symbol, outcome), rows in sorted(grouped_rows.items()):
        ticket_ids = tuple(str(row["ticket_id"]) for row in rows)
        lesson_counts: Counter[str] = Counter()
        lesson_tickets: dict[str, list[str]] = defaultdict(list)
        for row in rows:
            ticket_id = str(row["ticket_id"])
            for lesson in _load_lessons(row["lessons_json"]):
                lesson_counts[lesson] += 1
                if ticket_id not in lesson_tickets[lesson]:
                    lesson_tickets[lesson].append(ticket_id)
        groups.append(
            StrategyLessonGroup(
                date_kst=date_kst,
                symbol=symbol,
                outcome=outcome,
                ticket_ids=ticket_ids,
                total_realized_pnl_krw=sum(int(row["realized_pnl_krw"] or 0) for row in rows),
                lesson_counts=dict(lesson_counts),
                lesson_ticket_ids={lesson: tuple(ids) for lesson, ids in lesson_tickets.items()},
            )
        )
    return groups


def _merge_generated_block(existing: str, generated_markdown: str) -> str:
    block = f"{START_MARKER}\n{generated_markdown.rstrip()}\n{END_MARKER}\n"
    if START_MARKER in existing and END_MARKER in existing:
        before = existing.split(START_MARKER, 1)[0].rstrip()
        after = existing.split(END_MARKER, 1)[1].lstrip()
        parts = [before, block.rstrip(), after.rstrip()]
        return "\n\n".join(part for part in parts if part) + "\n"
    if existing.strip():
        return existing.rstrip() + "\n\n" + block
    return block


def _load_lessons(raw: str) -> list[str]:
    try:
        data = json.loads(str(raw))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [str(item).strip() for item in data if str(item).strip()]


def _created_at_kst_date(raw: str) -> str:
    dt = datetime.fromisoformat(str(raw))
    return _as_kst(dt).date().isoformat()


def _as_kst(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=KST)
    return value.astimezone(KST)


def _format_ticket_ids(ticket_ids: tuple[str, ...]) -> str:
    return ", ".join(f"`{ticket_id}`" for ticket_id in ticket_ids)


def _format_signed_krw(value: int) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:,}원"
