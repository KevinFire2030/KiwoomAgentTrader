from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

MarketRegime = Literal["risk_on", "neutral", "risk_off"]
TradeSide = Literal["buy", "sell"]
OrderType = Literal["market", "limit"]


@dataclass(frozen=True)
class MarketAnalysis:
    agent: str
    market_regime: MarketRegime
    confidence: float
    summary: str
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Recommendation:
    agent: str
    symbol: str
    name: str
    action_bias: str
    score: int
    reason: str


@dataclass(frozen=True)
class TradeTicket:
    ticket_id: str
    symbol: str
    side: TradeSide
    quantity: int
    order_type: OrderType
    limit_price: int | None
    created_by: str
    risk_approved: bool = False
    risk_approved_by: str | None = None
    user_approved: bool = False
    status: str = "draft"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def estimated_amount_krw(self) -> int:
        return self.quantity * (self.limit_price or 0)


@dataclass(frozen=True)
class RiskReview:
    agent: str
    approved: bool
    risk_level: str
    ticket: TradeTicket | None
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WorkflowResult:
    run_id: str
    report: str
    ticket: TradeTicket | None
    risk_review: RiskReview
