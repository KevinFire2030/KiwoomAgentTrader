from app.agents.chief import ChiefInvestmentAgent
from app.agents.models import AccountSnapshot, AccountState, MarketSnapshot


def run_intraday_signal_scan(
    symbol: str,
    mode: str = "paper",
    market_snapshot: MarketSnapshot | None = None,
    account_snapshot: AccountSnapshot | None = None,
    account_state: AccountState | None = None,
):
    return ChiefInvestmentAgent().run_intraday_signal_scan(
        symbol=symbol,
        mode=mode,
        market_snapshot=market_snapshot,
        account_snapshot=account_snapshot,
        account_state=account_state,
    )
