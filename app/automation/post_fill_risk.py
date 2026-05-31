from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.storage.repository import RealizedPnlEvent, TradingRepository

KST = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class PostFillCircuitBreakerPolicy:
    max_daily_loss_krw: int = 50_000
    enabled: bool = True


@dataclass(frozen=True)
class PostFillCircuitBreakerDecision:
    triggered: bool
    status: str
    reason: str
    event_id: int
    daily_realized_pnl_krw: int


class PostFillCircuitBreaker:
    """Record realized fill P&L and automatically halt future scans after loss breach.

    This component is intentionally repository-only. It never calls Kiwoom order
    APIs; it records fill-derived realized P&L and flips runtime_state so the
    existing OperationalRiskGuard blocks later scheduled scans.
    """

    def __init__(self, repository: TradingRepository, policy: PostFillCircuitBreakerPolicy | None = None) -> None:
        self.repository = repository
        self.policy = policy or PostFillCircuitBreakerPolicy()

    def process_fill(self, event: RealizedPnlEvent) -> PostFillCircuitBreakerDecision:
        self.repository.initialize()
        event_id = self.repository.record_realized_pnl_event(event)
        occurred_kst = _as_kst(event.occurred_at)
        day_start = occurred_kst.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        daily_pnl = self.repository.sum_realized_pnl(
            start_iso=day_start.isoformat(),
            end_iso=day_end.isoformat(),
            symbol=event.symbol,
        )

        if self.policy.enabled and daily_pnl <= -self.policy.max_daily_loss_krw:
            reason = (
                f"post-fill circuit breaker: {event.symbol} 당일 실현손익 {daily_pnl:,}원 "
                f"<= -{self.policy.max_daily_loss_krw:,}원"
            )
            self.repository.set_runtime_state("circuit_breaker", "on", reason)
            return PostFillCircuitBreakerDecision(
                triggered=True,
                status="circuit_breaker_on",
                reason=reason,
                event_id=event_id,
                daily_realized_pnl_krw=daily_pnl,
            )

        reason = (
            f"post-fill recorded: {event.symbol} 당일 실현손익 {daily_pnl:,}원 / "
            f"손실한도 -{self.policy.max_daily_loss_krw:,}원"
        )
        return PostFillCircuitBreakerDecision(
            triggered=False,
            status="recorded",
            reason=reason,
            event_id=event_id,
            daily_realized_pnl_krw=daily_pnl,
        )


def _as_kst(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=KST)
    return value.astimezone(KST)
