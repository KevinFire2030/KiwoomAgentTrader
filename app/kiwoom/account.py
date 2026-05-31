from __future__ import annotations

from typing import Any

from app.kiwoom.client import KiwoomRestClient


class KiwoomAccountClient:
    def __init__(self, client: KiwoomRestClient) -> None:
        self.client = client

    def get_balance(self, account_no: str) -> dict[str, Any]:
        # Kiwoom kt00018 uses the token/account context; account_no is kept in the
        # public API for call-site clarity and future multi-account validation.
        _ = account_no
        return self.client.post("/api/dostk/acnt", payload={"qry_tp": "1", "dmst_stex_tp": "KRX"}, api_id="kt00018")
