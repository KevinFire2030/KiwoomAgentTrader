from __future__ import annotations

from typing import Any

from app.kiwoom.client import KiwoomRestClient


class KiwoomMarketClient:
    def __init__(self, client: KiwoomRestClient) -> None:
        self.client = client

    def get_current_price(self, symbol: str) -> dict[str, Any]:
        return self.client.get("/market/current-price", params={"symbol": symbol})
