from app.agents.chief import ChiefInvestmentAgent
from app.agents.models import AccountSnapshot, MarketSnapshot


def run_intraday_signal_scan(
    symbol: str,
    mode: str = "paper",
    market_snapshot: MarketSnapshot | None = None,
    account_snapshot: AccountSnapshot | None = None,
):
    return ChiefInvestmentAgent().run_intraday_signal_scan(
        symbol=symbol,
        mode=mode,
        market_snapshot=market_snapshot,
        account_snapshot=account_snapshot,
    )
