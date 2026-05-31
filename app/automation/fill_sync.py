from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.storage.repository import RealizedPnlEvent, TradingRepository

KST = ZoneInfo("Asia/Seoul")
SENSITIVE_KEYS = {"acnt_no", "account_no", "acc_no", "acct_no", "cano"}
PNL_KEYS = (
    "rlzt_pnl",
    "realized_pnl",
    "realized_pnl_krw",
    "trde_pfls_amt",
    "pl_amt",
    "pnl",
    "evlt_pfls_amt",
    "sell_pnl",
)
SYMBOL_KEYS = ("stk_cd", "symbol", "pdno", "isu_cd")
ORDER_KEYS = ("ord_no", "odno", "order_no", "broker_order_id")
FILL_KEYS = ("cntr_no", "exec_no", "fill_no", "broker_fill_id")


@dataclass(frozen=True)
class FillSyncResult:
    rows_seen: int
    events_derived: int
    events_recorded: int
    duplicates_skipped: int
    snapshots_recorded: int
    apply: bool


class KiwoomFillSync:
    def __init__(self, repository: TradingRepository) -> None:
        self.repository = repository

    def sync_rows(self, rows: list[dict[str, Any]], *, apply: bool, now: datetime | None = None) -> FillSyncResult:
        self.repository.initialize()
        events_derived = 0
        events_recorded = 0
        duplicates_skipped = 0
        snapshots_recorded = 0
        captured_at = _as_kst(now or datetime.now(tz=KST))
        for row in rows:
            event = derive_realized_pnl_event_from_row(row)
            if event is None:
                continue
            events_derived += 1
            dedupe_key = str(event.raw["dedupe_key"])
            if not apply:
                continue
            snapshot_id = self.repository.record_broker_fill_sync_snapshot(
                dedupe_key=dedupe_key,
                source="kiwoom_fill_sync",
                symbol=event.symbol,
                raw=_sanitize_row(row),
                captured_at=captured_at,
            )
            if snapshot_id is not None:
                snapshots_recorded += 1
            event_id = self.repository.record_realized_pnl_event_once(event, dedupe_key)
            if event_id is None:
                duplicates_skipped += 1
            else:
                events_recorded += 1
        return FillSyncResult(
            rows_seen=len(rows),
            events_derived=events_derived,
            events_recorded=events_recorded,
            duplicates_skipped=duplicates_skipped,
            snapshots_recorded=snapshots_recorded,
            apply=apply,
        )


def derive_realized_pnl_event_from_row(row: dict[str, Any]) -> RealizedPnlEvent | None:
    pnl = _first_int(row, PNL_KEYS)
    if pnl is None:
        return None
    symbol = _first_str(row, SYMBOL_KEYS) or "unknown"
    order_id = _first_str(row, ORDER_KEYS)
    fill_id = _first_str(row, FILL_KEYS)
    ticket_id = _extract_ticket_id(row)
    occurred_at = _parse_occurred_at(row)
    raw = {
        "ticket_id": ticket_id,
        "broker_order_id": order_id,
        "broker_fill_id": fill_id,
        "dedupe_key": _dedupe_key(row, symbol, order_id, fill_id, pnl),
        "source_fields": _sanitize_row(row),
    }
    event_raw = {key: value for key, value in raw.items() if value is not None and value != ""}
    return RealizedPnlEvent(
        symbol=symbol,
        realized_pnl_krw=pnl,
        source="kiwoom_fill_sync",
        raw=event_raw,
        occurred_at=occurred_at,
    )


def _extract_ticket_id(row: dict[str, Any]) -> str | None:
    for key in ("ticket_id", "local_ticket_id"):
        value = _clean(row.get(key))
        if value:
            return value
    raw_text = " ".join(str(value) for value in row.values() if value is not None)
    match = re.search(r"TT-[A-Za-z0-9_.:-]+", raw_text)
    return match.group(0) if match else None


def _dedupe_key(row: dict[str, Any], symbol: str, order_id: str | None, fill_id: str | None, pnl: int) -> str:
    if order_id or fill_id:
        return "|".join(["kiwoom", symbol, order_id or "", fill_id or "", str(pnl)])
    sanitized = json.dumps(_sanitize_row(row), ensure_ascii=False, sort_keys=True)
    return "kiwoom|hash|" + hashlib.sha256(sanitized.encode("utf-8")).hexdigest()


def _sanitize_row(row: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in row.items():
        key_text = str(key)
        if key_text.lower() in SENSITIVE_KEYS or "acnt" in key_text.lower() or "account" in key_text.lower():
            sanitized[key_text] = _mask_value(value)
        else:
            sanitized[key_text] = _mask_embedded_sensitive(value)
    return sanitized


def _mask_embedded_sensitive(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return re.sub(r"\b\d{6,12}\b", lambda match: _mask_value(match.group(0)), value)


def _mask_value(value: Any) -> str:
    text = str(value or "")
    if len(text) <= 4:
        return "****" if text else ""
    return f"{text[:2]}***{text[-2:]}"


def _first_str(row: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _clean(row.get(key))
        if value:
            return value
    return None


def _first_int(row: dict[str, Any], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        value = row.get(key)
        if value is None or value == "":
            continue
        try:
            return int(float(str(value).strip().replace(",", "").replace("+", "")))
        except ValueError:
            continue
    return None


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_occurred_at(row: dict[str, Any]) -> datetime:
    date_text = _first_str(row, ("trde_dt", "ord_dt", "date", "dt"))
    time_text = _first_str(row, ("trde_tm", "cntr_tm", "time", "tm")) or "000000"
    if date_text and len(date_text) == 8 and date_text.isdigit():
        time_text = re.sub(r"\D", "", time_text).ljust(6, "0")[:6]
        return datetime(
            int(date_text[:4]),
            int(date_text[4:6]),
            int(date_text[6:8]),
            int(time_text[:2]),
            int(time_text[2:4]),
            int(time_text[4:6]),
            tzinfo=KST,
        )
    return datetime.now(tz=KST)


def _as_kst(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=KST)
    return value.astimezone(KST)
