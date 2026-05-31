from __future__ import annotations

from typing import Any

from app.agents.models import AccountSnapshot, MarketSnapshot


def market_snapshot_from_response(symbol: str, response: dict[str, Any]) -> MarketSnapshot:
    latest = _latest_market_payload(response)
    return MarketSnapshot(
        symbol=symbol,
        name=str(latest.get("stk_nm") or response.get("stk_nm") or ""),
        current_price=_parse_int(latest.get("cur_prc") or response.get("cur_prc")),
        change_rate=_parse_float(latest.get("pre_rt") or response.get("pre_rt")),
        source="kiwoom_rest",
        raw=response,
    )


def account_snapshot_from_response(account_no: str, response: dict[str, Any]) -> AccountSnapshot:
    positions = response.get("acnt_evlt_remn_indv_tot") or []
    if not isinstance(positions, list):
        positions = []
    return AccountSnapshot(
        account_no_masked=mask_account(account_no),
        deposit_asset_amount=_parse_int(response.get("prsm_dpst_aset_amt") or response.get("dnca_tot_amt")),
        total_evaluation_amount=_parse_int(response.get("tot_evlt_amt")),
        positions_count=len(positions),
        source="kiwoom_rest",
        raw=response,
    )


def mask_account(account_no: str) -> str:
    account_no = str(account_no)
    if len(account_no) <= 4:
        return "****"
    return account_no[:2] + "***" + account_no[-2:]


def _latest_market_payload(response: dict[str, Any]) -> dict[str, Any]:
    cntr_infr = response.get("cntr_infr")
    if isinstance(cntr_infr, list) and cntr_infr and isinstance(cntr_infr[0], dict):
        return cntr_infr[0]
    return response


def _parse_int(value: Any) -> int:
    if value is None or value == "":
        return 0
    normalized = str(value).strip().replace(",", "")
    if normalized.startswith("+"):
        normalized = normalized[1:]
    return abs(int(float(normalized)))


def _parse_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    normalized = str(value).strip().replace(",", "")
    if normalized.startswith("+"):
        normalized = normalized[1:]
    return float(normalized)
