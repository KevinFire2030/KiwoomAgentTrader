from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.account_state import AccountStateAgent
from app.agents.chief import ChiefInvestmentAgent
from app.config.dotenv import load_dotenv
from app.config.settings import KiwoomSettings, SettingsError
from app.kiwoom.account import KiwoomAccountClient
from app.kiwoom.auth import KiwoomAuthClient
from app.kiwoom.client import KiwoomRestClient
from app.kiwoom.market import KiwoomMarketClient
from app.kiwoom.snapshots import account_snapshot_from_response, market_snapshot_from_response
from app.kiwoom.transactions import KiwoomTransactionClient, summarize_transactions
from app.storage.repository import TradingRepository


def build_clients():
    load_dotenv()
    settings = KiwoomSettings.from_env()
    auth = KiwoomAuthClient(settings.base_url, settings.app_key, settings.secret_key)
    token_cache = {}

    def token_provider():
        if "token" not in token_cache:
            token_cache["token"] = auth.issue_token()
        return token_cache["token"]

    rest = KiwoomRestClient(settings.base_url, settings.app_key, token_provider)
    return settings, KiwoomMarketClient(rest), KiwoomAccountClient(rest), KiwoomTransactionClient(rest)


def one_year_range() -> tuple[str, str]:
    end = date.today()
    start = end.replace(year=end.year - 1) + timedelta(days=1)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def run(symbol: str = "498270"):
    settings, market_client, account_client, transaction_client = build_clients()
    quote = market_client.get_current_price(symbol)
    balance = account_client.get_balance(settings.account_no)
    start_date, end_date = one_year_range()
    transactions = transaction_client.get_deposit_withdraw_history(start_date, end_date)

    market_snapshot = market_snapshot_from_response(symbol, quote)
    account_snapshot = account_snapshot_from_response(settings.account_no, balance)
    transaction_summary = summarize_transactions(transactions)
    account_state = AccountStateAgent().analyze(account_snapshot, transaction_summary)

    repository = TradingRepository(Path("data") / "trading.db")
    result = ChiefInvestmentAgent(repository=repository).run_intraday_signal_scan(
        symbol,
        mode=settings.trading_mode,
        market_snapshot=market_snapshot,
        account_snapshot=account_snapshot,
        account_state=account_state,
    )
    return result


def main() -> None:
    symbol = sys.argv[1] if len(sys.argv) > 1 else "498270"
    try:
        result = run(symbol)
    except SettingsError as exc:
        print(f"설정 오류: {exc}")
        print(".env 파일을 .env.example 기준으로 채워주세요.")
        raise SystemExit(2)
    print(result.report)


if __name__ == "__main__":
    main()
