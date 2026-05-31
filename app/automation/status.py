from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.storage.repository import TradingRepository

KST = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class AutomationStatus:
    symbol: str
    trading_mode: str
    enable_live_trading: bool
    market_snapshot_at: str
    account_snapshot_at: str
    circuit_breaker_state: str
    circuit_breaker_reason: str
    pending_ticket_count: int
    latest_pending_ticket_id: str | None
    latest_pending_ticket_created_at: str
    latest_post_trade_analysis_at: str
    strategy_lessons_exists: bool
    strategy_lessons_path: str
    generated_at: str


class AutomationStatusBuilder:
    """Build a read-only local automation health summary.

    This intentionally reads local DB/files only. It does not authenticate with
    Kiwoom and never calls broker order APIs.
    """

    def __init__(
        self,
        repository: TradingRepository,
        *,
        symbol: str = "498270",
        trading_mode: str = "paper",
        enable_live_trading: bool = False,
        strategy_lessons_path: str | Path = Path("docs") / "strategy-lessons.md",
    ) -> None:
        self.repository = repository
        self.symbol = symbol
        self.trading_mode = trading_mode
        self.enable_live_trading = enable_live_trading
        self.strategy_lessons_path = Path(strategy_lessons_path)

    def build(self, now: datetime | None = None) -> AutomationStatus:
        self.repository.initialize()
        market = self.repository.get_latest_market_snapshot(self.symbol)
        account = self.repository.get_latest_account_snapshot()
        circuit = self.repository.get_runtime_state("circuit_breaker")
        pending = self.repository.list_trade_tickets_by_status("pending_user_approval")
        latest_analysis = self.repository.get_latest_post_trade_analysis_record()
        return AutomationStatus(
            symbol=self.symbol,
            trading_mode=self.trading_mode,
            enable_live_trading=self.enable_live_trading,
            market_snapshot_at=_format_row_time(market, "captured_at"),
            account_snapshot_at=_format_row_time(account, "captured_at"),
            circuit_breaker_state=str(circuit["state_value"]) if circuit is not None else "off",
            circuit_breaker_reason=str(circuit["reason"]) if circuit is not None else "",
            pending_ticket_count=len(pending),
            latest_pending_ticket_id=str(pending[0]["ticket_id"]) if pending else None,
            latest_pending_ticket_created_at=_format_row_time(pending[0], "created_at") if pending else "none",
            latest_post_trade_analysis_at=_format_row_time(latest_analysis, "created_at"),
            strategy_lessons_exists=self.strategy_lessons_path.exists(),
            strategy_lessons_path=str(self.strategy_lessons_path),
            generated_at=_format_datetime(now or datetime.now(tz=KST)),
        )


def format_automation_status(status: AutomationStatus) -> str:
    live_state = "enabled" if status.enable_live_trading else "disabled"
    strategy_state = "available" if status.strategy_lessons_exists else "missing"
    latest_pending = status.latest_pending_ticket_id or "none"
    lines = [
        "[Kiwoom Agent Trader 자동화 상태]",
        f"generated_at: {status.generated_at}",
        f"symbol: {status.symbol}",
        f"mode: {status.trading_mode}",
        f"live trading: {live_state}",
        "",
        "데이터 freshness:",
        f"market snapshot: {status.market_snapshot_at}",
        f"account snapshot: {status.account_snapshot_at}",
        f"latest post-trade analysis: {status.latest_post_trade_analysis_at}",
        f"strategy lessons: {strategy_state} ({status.strategy_lessons_path})",
        "",
        "운영 리스크:",
        f"circuit breaker: {status.circuit_breaker_state}"
        + (f" ({status.circuit_breaker_reason})" if status.circuit_breaker_reason else ""),
        f"pending approvals: {status.pending_ticket_count}",
        f"latest pending: {latest_pending}",
    ]
    if status.latest_pending_ticket_created_at != "none":
        lines.append(f"latest pending created_at: {status.latest_pending_ticket_created_at}")
    lines.extend(
        [
            "",
            "안전: read-only status command입니다. Kiwoom 주문 API를 호출하지 않습니다.",
        ]
    )
    return "\n".join(lines)


def _format_row_time(row, key: str) -> str:
    if row is None:
        return "none"
    return _format_datetime(datetime.fromisoformat(str(row[key])))


def _format_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=KST)
    return value.astimezone(KST).strftime("%Y-%m-%d %H:%M:%S KST")
