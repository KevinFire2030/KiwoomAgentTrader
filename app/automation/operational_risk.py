from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.storage.repository import TradingRepository

KST = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class OperationalRiskPolicy:
    max_daily_buy_amount_krw: int = 300_000
    max_daily_loss_krw: int = 50_000
    order_cooldown_minutes: int = 30
    circuit_breaker_enabled: bool = True


@dataclass(frozen=True)
class OperationalRiskDecision:
    allowed: bool
    status: str
    reason: str


class OperationalRiskGuard:
    """Runtime safety guard for scheduler-driven scans.

    This is deliberately deterministic and repository-backed. It does not call
    broker order APIs; it only decides whether a new scan may produce a new
    approval ticket based on already recorded tickets/events and persistent
    circuit-breaker state.
    """

    def __init__(self, repository: TradingRepository, policy: OperationalRiskPolicy | None = None) -> None:
        self.repository = repository
        self.policy = policy or OperationalRiskPolicy()

    def evaluate(self, *, symbol: str, now: datetime | None = None) -> OperationalRiskDecision:
        now_kst = _as_kst(now or datetime.now(tz=KST))
        self.repository.initialize()

        if self.policy.circuit_breaker_enabled:
            breaker = self.repository.get_runtime_state("circuit_breaker")
            if breaker and breaker["state_value"] == "on":
                reason = breaker["reason"] or "수동 circuit breaker가 켜져 있습니다."
                return OperationalRiskDecision(False, "blocked_circuit_breaker", reason)

        latest = self.repository.get_latest_executed_trade_ticket(symbol=symbol)
        if latest is not None:
            latest_at = _parse_datetime(latest["created_at"])
            cooldown_until = latest_at.astimezone(KST) + timedelta(minutes=self.policy.order_cooldown_minutes)
            if now_kst < cooldown_until:
                return OperationalRiskDecision(
                    False,
                    "blocked_order_cooldown",
                    f"주문 cooldown 진행 중: 마지막 실행 {latest_at.astimezone(KST).strftime('%H:%M:%S KST')}, 재개 가능 {cooldown_until.strftime('%H:%M:%S KST')}",
                )

        day_start = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        daily_buy = self.repository.sum_executed_buy_amount(
            start_iso=day_start.astimezone(KST).isoformat(),
            end_iso=day_end.astimezone(KST).isoformat(),
            symbol=symbol,
        )
        if daily_buy >= self.policy.max_daily_buy_amount_krw:
            return OperationalRiskDecision(
                False,
                "blocked_daily_buy_limit",
                f"일일 매수 한도 도달: {daily_buy:,}원 >= {self.policy.max_daily_buy_amount_krw:,}원",
            )

        realized_pnl = self.repository.sum_realized_pnl(
            start_iso=day_start.astimezone(KST).isoformat(),
            end_iso=day_end.astimezone(KST).isoformat(),
            symbol=symbol,
        )
        if realized_pnl <= -self.policy.max_daily_loss_krw:
            return OperationalRiskDecision(
                False,
                "blocked_daily_realized_loss_limit",
                f"일일 실현손실 한도 도달: {realized_pnl:,}원 <= -{self.policy.max_daily_loss_krw:,}원",
            )

        return OperationalRiskDecision(
            True,
            "allowed",
            f"운영 리스크 통과: 일일 매수 {daily_buy:,}원 / 한도 {self.policy.max_daily_buy_amount_krw:,}원, 실현손익 {realized_pnl:,}원 / 손실한도 -{self.policy.max_daily_loss_krw:,}원",
        )


def _as_kst(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=KST)
    return value.astimezone(KST)


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=KST)
    return parsed
