from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config.dotenv import load_dotenv
from app.config.settings import KiwoomSettings, SettingsError
from app.kiwoom.account import KiwoomAccountClient
from app.kiwoom.auth import KiwoomAuthClient
from app.kiwoom.client import KiwoomRestClient
from app.kiwoom.market import KiwoomMarketClient


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
    return settings, KiwoomMarketClient(rest), KiwoomAccountClient(rest)


def main() -> None:
    try:
        settings, market, account = build_clients()
    except SettingsError as exc:
        print(f"설정 오류: {exc}")
        print(".env 파일을 .env.example 기준으로 채워주세요.")
        raise SystemExit(2)

    print("[Kiwoom Read API Check]")
    print(f"mode: {settings.trading_mode}")
    print(f"account_no: {settings.account_no}")
    print("현재가 조회: 498270")
    print(market.get_current_price("498270"))
    print("계좌 잔고 조회")
    print(account.get_balance(settings.account_no))


if __name__ == "__main__":
    main()
