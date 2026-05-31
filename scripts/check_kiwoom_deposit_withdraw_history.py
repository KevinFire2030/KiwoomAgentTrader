from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config.dotenv import load_dotenv
from app.config.settings import KiwoomSettings, SettingsError
from app.kiwoom.auth import KiwoomAuthClient
from app.kiwoom.client import KiwoomRestClient
from app.kiwoom.transactions import KiwoomTransactionClient, format_krw, summarize_transactions


def build_client() -> tuple[KiwoomSettings, KiwoomTransactionClient]:
    load_dotenv()
    settings = KiwoomSettings.from_env()
    auth = KiwoomAuthClient(settings.base_url, settings.app_key, settings.secret_key)
    token_cache = {}

    def token_provider():
        if "token" not in token_cache:
            token_cache["token"] = auth.issue_token()
        return token_cache["token"]

    rest = KiwoomRestClient(settings.base_url, settings.app_key, token_provider)
    return settings, KiwoomTransactionClient(rest)


def one_year_range() -> tuple[str, str]:
    end = date.today()
    start = end.replace(year=end.year - 1) + timedelta(days=1)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def main() -> None:
    try:
        settings, client = build_client()
    except SettingsError as exc:
        print(f"설정 오류: {exc}")
        print(".env 파일을 .env.example 기준으로 채워주세요.")
        raise SystemExit(2)

    start_date, end_date = one_year_range()
    rows = client.get_deposit_withdraw_history(start_date, end_date)
    summary = summarize_transactions(rows)

    print("[Kiwoom Deposit/Withdraw History]")
    print(f"mode: {settings.trading_mode}")
    print(f"period: {start_date} ~ {end_date}")
    print(f"count: {summary.count}")
    print(f"deposit_total: {format_krw(summary.deposit_total)}")
    print(f"withdraw_total: {format_krw(summary.withdraw_total)}")
    print(f"latest_balance: {format_krw(summary.latest_balance)}")
    for index, row in enumerate(rows, 1):
        amount = format_krw(int(str(row.get("trde_amt") or row.get("exct_amt") or "0")))
        balance = format_krw(int(str(row.get("entra_remn") or "0")))
        print(
            f"[{index}] {row.get('trde_dt')} {row.get('proc_tm') or ''} "
            f"{row.get('io_tp_nm') or row.get('io_tp') or ''} "
            f"{row.get('rmrk_nm') or row.get('trde_kind_nm') or ''} "
            f"amount={amount} balance={balance} {row.get('crnc_cd') or ''}"
        )


if __name__ == "__main__":
    main()
