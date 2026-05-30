from app.agents.chief import ChiefInvestmentAgent


def run_intraday_signal_scan(symbol: str, mode: str = "paper"):
    return ChiefInvestmentAgent().run_intraday_signal_scan(symbol=symbol, mode=mode)
