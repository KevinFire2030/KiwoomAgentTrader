from __future__ import annotations

from typing import Any

from app.kiwoom.client import KiwoomRestClient


class KiwoomAccountClient:
    def __init__(self, client: KiwoomRestClient) -> None:
        self.client = client

    def get_balance(self, account_no: str) -> dict[str, Any]:
        return self.client.get("/account/balance", params={"account_no": account_no})
