import unittest

from app.kiwoom.auth import KiwoomAuthClient, KiwoomToken
from app.kiwoom.client import KiwoomRestClient
from app.kiwoom.market import KiwoomMarketClient
from app.kiwoom.account import KiwoomAccountClient


class FakeTransport:
    def __init__(self):
        self.calls = []

    def request(self, method, url, headers=None, json=None, params=None, timeout=10):
        self.calls.append({"method": method, "url": url, "headers": headers or {}, "json": json, "params": params})
        if url.endswith("/oauth2/token"):
            return {"token_type": "Bearer", "access_token": "token-123", "expires_in": 3600}
        if url.endswith("/market/current-price"):
            return {"symbol": "498270", "price": 12345, "name": "KIWOOM 미국양자컴퓨팅 ETF"}
        if url.endswith("/account/balance"):
            return {"account_no": "12345678", "cash_krw": 1000000, "positions": []}
        raise AssertionError(f"unexpected url: {url}")


class KiwoomRestClientTest(unittest.TestCase):
    def test_auth_client_requests_access_token(self):
        transport = FakeTransport()
        auth = KiwoomAuthClient(base_url="https://api.example", app_key="app", secret_key="secret", transport=transport)

        token = auth.issue_token()

        self.assertEqual(token.access_token, "token-123")
        self.assertEqual(token.token_type, "Bearer")
        self.assertEqual(transport.calls[0]["json"]["appkey"], "app")

    def test_rest_client_adds_bearer_token_and_app_key_headers(self):
        transport = FakeTransport()
        client = KiwoomRestClient(
            base_url="https://api.example",
            app_key="app",
            token_provider=lambda: KiwoomToken("Bearer", "token-123", 3600),
            transport=transport,
        )

        Market = KiwoomMarketClient(client)
        quote = Market.get_current_price("498270")

        self.assertEqual(quote["price"], 12345)
        headers = transport.calls[-1]["headers"]
        self.assertEqual(headers["Authorization"], "Bearer token-123")
        self.assertEqual(headers["appkey"], "app")

    def test_account_client_reads_balance(self):
        transport = FakeTransport()
        client = KiwoomRestClient(
            base_url="https://api.example",
            app_key="app",
            token_provider=lambda: KiwoomToken("Bearer", "token-123", 3600),
            transport=transport,
        )

        account = KiwoomAccountClient(client)
        balance = account.get_balance("12345678")

        self.assertEqual(balance["cash_krw"], 1000000)
        self.assertEqual(transport.calls[-1]["params"]["account_no"], "12345678")


if __name__ == "__main__":
    unittest.main()
