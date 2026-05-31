from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.kiwoom.client import KiwoomRestClient


@dataclass(frozen=True)
class TransactionSummary:
    count: int
    deposit_total: int
    withdraw_total: int
    latest_balance: int


class KiwoomTransactionClient:
    def __init__(self, client: KiwoomRestClient) -> None:
        self.client = client

    def get_deposit_withdraw_history(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        response = self.client.post(
            "/api/dostk/acnt",
            payload={
                "strt_dt": start_date,
                "end_dt": end_date,
                "tp": "1",
                "stk_cd": "",
                "crnc_cd": "",
                "gds_tp": "0",
                "frgn_stex_code": "",
                "dmst_stex_tp": "%",
            },
            api_id="kt00015",
        )
        rows = response.get("trst_ovrl_trde_prps_array") or []
        if not isinstance(rows, list):
            return []
        return [row for row in rows if isinstance(row, dict)]


def summarize_transactions(rows: list[dict[str, Any]]) -> TransactionSummary:
    deposit_total = 0
    withdraw_total = 0
    latest_balance = 0
    for row in rows:
        amount = _parse_int(row.get("trde_amt") or row.get("exct_amt"))
        io_name = str(row.get("io_tp_nm") or row.get("io_tp") or row.get("rmrk_nm") or "")
        if "출" in io_name and "입" not in io_name:
            withdraw_total += amount
        elif "입" in io_name:
            deposit_total += amount
        latest_balance = _parse_int(row.get("entra_remn")) or latest_balance
    return TransactionSummary(
        count=len(rows),
        deposit_total=deposit_total,
        withdraw_total=withdraw_total,
        latest_balance=latest_balance,
    )


def format_krw(value: int) -> str:
    return f"{value:,}원"


def _parse_int(value: Any) -> int:
    if value is None or value == "":
        return 0
    normalized = str(value).strip().replace(",", "")
    if normalized.startswith("+"):
        normalized = normalized[1:]
    return abs(int(float(normalized)))
