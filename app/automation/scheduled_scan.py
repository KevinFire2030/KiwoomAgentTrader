from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from datetime import datetime, time
from pathlib import Path
from typing import Callable, Protocol
from zoneinfo import ZoneInfo

from app.agents.models import WorkflowResult
from app.automation.operational_risk import OperationalRiskDecision, OperationalRiskGuard, OperationalRiskPolicy
from app.storage.repository import TradingRepository
from app.telegram.client import TelegramBotClient, TelegramTarget

KST = ZoneInfo("Asia/Seoul")


class TelegramSender(Protocol):
    def send_message(self, target: TelegramTarget, text: str) -> dict:
        ...


@dataclass(frozen=True)
class MarketSessionDecision:
    is_open: bool
    reason: str
    now_kst: datetime


@dataclass(frozen=True)
class ScheduledScanConfig:
    symbol: str = "498270"
    mode: str = "paper"
    db_path: Path = Path("data") / "trading.db"
    chat_id: str | None = None
    message_thread_id: int | None = None
    bot_token: str | None = None
    force: bool = False
    notify_when_no_ticket: bool = True
    enforce_operational_risk: bool = True
    max_daily_buy_amount_krw: int = 300_000
    order_cooldown_minutes: int = 30
    circuit_breaker_enabled: bool = True
    market_open: time = time(9, 5)
    market_close: time = time(15, 10)
    holidays: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def from_env(cls) -> "ScheduledScanConfig":
        thread_raw = os.getenv("KIWOOM_TELEGRAM_THREAD_ID") or os.getenv("TELEGRAM_MESSAGE_THREAD_ID")
        holidays = frozenset(_normalize_holiday(value) for value in _split_csv(os.getenv("KRX_HOLIDAYS", "")))
        return cls(
            symbol=os.getenv("KIWOOM_SCAN_SYMBOL", "498270"),
            mode=os.getenv("TRADING_MODE", "paper"),
            db_path=Path(os.getenv("KIWOOM_TRADING_DB", str(Path("data") / "trading.db"))),
            chat_id=os.getenv("KIWOOM_TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID"),
            message_thread_id=int(thread_raw) if thread_raw else None,
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            force=_env_bool("KIWOOM_SCAN_FORCE", False),
            notify_when_no_ticket=_env_bool("KIWOOM_NOTIFY_WHEN_NO_TICKET", True),
            enforce_operational_risk=_env_bool("KIWOOM_ENFORCE_OPERATIONAL_RISK", True),
            max_daily_buy_amount_krw=int(os.getenv("MAX_DAILY_BUY_AMOUNT_KRW", "300000")),
            order_cooldown_minutes=int(os.getenv("ORDER_COOLDOWN_MINUTES", "30")),
            circuit_breaker_enabled=_env_bool("KIWOOM_CIRCUIT_BREAKER_ENABLED", True),
            holidays=holidays,
        )

    def with_overrides(self, **changes) -> "ScheduledScanConfig":
        return replace(self, **changes)


@dataclass(frozen=True)
class ScheduledScanResult:
    status: str
    message: str
    session: MarketSessionDecision
    workflow_result: WorkflowResult | None = None
    notification_sent: bool = False
    operational_risk: OperationalRiskDecision | None = None


def market_session_decision(config: ScheduledScanConfig, now: datetime | None = None) -> MarketSessionDecision:
    now_kst = _as_kst(now or datetime.now(tz=KST))
    day_key = now_kst.strftime("%Y-%m-%d")
    if now_kst.weekday() >= 5:
        return MarketSessionDecision(False, f"주말 휴장: {day_key}", now_kst)
    if day_key in config.holidays:
        return MarketSessionDecision(False, f"KRX 휴장일: {day_key}", now_kst)
    current = now_kst.time().replace(second=0, microsecond=0)
    if current < config.market_open:
        return MarketSessionDecision(False, f"장 시작 전: {current.strftime('%H:%M')} < {config.market_open.strftime('%H:%M')}", now_kst)
    if current > config.market_close:
        return MarketSessionDecision(False, f"신규주문 차단 시간 이후: {current.strftime('%H:%M')} > {config.market_close.strftime('%H:%M')}", now_kst)
    return MarketSessionDecision(True, "정규 스캔 가능 시간", now_kst)


def run_scheduled_scan(
    config: ScheduledScanConfig,
    *,
    workflow_runner: Callable[[str], WorkflowResult] | None = None,
    telegram_client: TelegramSender | None = None,
    operational_guard: OperationalRiskGuard | None = None,
    now: datetime | None = None,
) -> ScheduledScanResult:
    session = market_session_decision(config, now)
    if not config.force and not session.is_open:
        message = _format_skip_message(config, session)
        return ScheduledScanResult("skipped_market_closed", message, session)

    operational_risk = _evaluate_operational_risk(config, operational_guard, session.now_kst)
    if operational_risk is not None and not config.force and not operational_risk.allowed:
        message = _format_operational_skip_message(config, session, operational_risk)
        return ScheduledScanResult("skipped_operational_risk", message, session, operational_risk=operational_risk)

    runner = workflow_runner or _default_workflow_runner
    workflow_result = runner(config.symbol)
    notification_text = format_scan_notification(config, workflow_result, session)

    sent = False
    if _should_send_notification(config, workflow_result) and config.chat_id:
        sender = telegram_client or TelegramBotClient(config.bot_token or "")
        sender.send_message(
            TelegramTarget(chat_id=config.chat_id, message_thread_id=config.message_thread_id),
            notification_text,
        )
        sent = True

    status = "completed_notified" if sent else "completed_no_notification"
    return ScheduledScanResult(status, notification_text, session, workflow_result, sent, operational_risk)


def format_scan_notification(
    config: ScheduledScanConfig,
    workflow_result: WorkflowResult,
    session: MarketSessionDecision,
) -> str:
    lines = [
        "[Kiwoom Agent Trader 정기 스캔]",
        f"시간: {session.now_kst.strftime('%Y-%m-%d %H:%M:%S KST')}",
        f"대상: {config.symbol}",
        f"모드: {config.mode}",
        f"상태: {session.reason}",
        "",
        workflow_result.report,
    ]
    if workflow_result.ticket is not None:
        ticket = workflow_result.ticket
        lines.extend(
            [
                "",
                "사용자 승인 필요:",
                f"승인 {ticket.ticket_id}",
                f"거절 {ticket.ticket_id}",
            ]
        )
    else:
        lines.extend(["", "생성된 승인 대기 티켓 없음"])
    return "\n".join(lines)


def _format_skip_message(config: ScheduledScanConfig, session: MarketSessionDecision) -> str:
    return "\n".join(
        [
            "[Kiwoom Agent Trader 정기 스캔 생략]",
            f"시간: {session.now_kst.strftime('%Y-%m-%d %H:%M:%S KST')}",
            f"대상: {config.symbol}",
            f"사유: {session.reason}",
            "강제 실행이 필요하면 --force 또는 KIWOOM_SCAN_FORCE=true를 사용하세요.",
        ]
    )


def _format_operational_skip_message(
    config: ScheduledScanConfig,
    session: MarketSessionDecision,
    decision: OperationalRiskDecision,
) -> str:
    return "\n".join(
        [
            "[Kiwoom Agent Trader 운영 리스크 차단]",
            f"시간: {session.now_kst.strftime('%Y-%m-%d %H:%M:%S KST')}",
            f"대상: {config.symbol}",
            f"상태: {decision.status}",
            f"사유: {decision.reason}",
            "운영자가 의도적으로 우회 검증할 때만 --force 또는 KIWOOM_SCAN_FORCE=true를 사용하세요.",
        ]
    )


def _evaluate_operational_risk(
    config: ScheduledScanConfig,
    operational_guard: OperationalRiskGuard | None,
    now_kst: datetime,
) -> OperationalRiskDecision | None:
    if not config.enforce_operational_risk:
        return None
    guard = operational_guard or OperationalRiskGuard(
        TradingRepository(config.db_path),
        OperationalRiskPolicy(
            max_daily_buy_amount_krw=config.max_daily_buy_amount_krw,
            order_cooldown_minutes=config.order_cooldown_minutes,
            circuit_breaker_enabled=config.circuit_breaker_enabled,
        ),
    )
    return guard.evaluate(symbol=config.symbol, now=now_kst)


def _should_send_notification(config: ScheduledScanConfig, workflow_result: WorkflowResult) -> bool:
    return config.notify_when_no_ticket or workflow_result.ticket is not None


def _default_workflow_runner(symbol: str) -> WorkflowResult:
    from scripts.run_kiwoom_intraday_workflow import run

    return run(symbol)


def _as_kst(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=KST)
    return value.astimezone(KST)


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _normalize_holiday(value: str) -> str:
    value = value.strip()
    if len(value) == 8 and value.isdigit():
        return f"{value[:4]}-{value[4:6]}-{value[6:]}"
    return value


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}
