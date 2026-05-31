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
    print(f"account_no: {_mask_account(settings.account_no)}")

    quote = market.get_current_price("498270")
    latest = (quote.get("cntr_infr") or [{}])[0]
    print("현재가 조회: OK")
    print({
        "symbol": "498270",
        "cur_prc": latest.get("cur_prc") or quote.get("cur_prc"),
        "pre_rt": latest.get("pre_rt") or quote.get("pre_rt"),
        "return_code": quote.get("return_code"),
        "return_msg": quote.get("return_msg"),
    })

    balance = account.get_balance(settings.account_no)
    print("계좌 잔고 조회: OK")
    print({
        "prsm_dpst_aset_amt": balance.get("prsm_dpst_aset_amt"),
        "tot_evlt_amt": balance.get("tot_evlt_amt"),
        "positions_count": len(balance.get("acnt_evlt_remn_indv_tot") or []),
        "return_code": balance.get("return_code"),
        "return_msg": balance.get("return_msg"),
    })


def _mask_account(account_no: str) -> str:
    if len(account_no) <= 4:
        return "****"
    return account_no[:2] + "***" + account_no[-2:]


if __name__ == "__main__":
    main()
