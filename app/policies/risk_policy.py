from dataclasses import dataclass


@dataclass(frozen=True)
class RiskPolicy:
    mode: str = "paper"
    allowed_symbols: tuple[str, ...] = ("498270",)
    max_order_amount_krw: int = 100_000
    max_daily_buy_amount_krw: int = 300_000
    max_daily_loss_krw: int = 50_000
    order_cooldown_minutes: int = 30
    live_trading_enabled: bool = False
    require_user_approval: bool = True
