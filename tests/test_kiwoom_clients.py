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
            return {"return_code": 0, "return_msg": "정상", "token_type": "Bearer", "token": "token-123", "expires_dt": "20260601094757"}
        if url.endswith("/api/dostk/stkinfo") and (headers or {}).get("api-id") == "ka10003":
            return {"return_code": 0, "stk_cd": "498270", "cur_prc": "12345", "stk_nm": "KIWOOM 미국양자컴퓨팅 ETF"}
        if url.endswith("/api/dostk/acnt") and (headers or {}).get("api-id") == "kt00018":
            return {"return_code": 0, "dnca_tot_amt": "1000000", "acnt_evlt_remn_indv_tot": []}
        raise AssertionError(f"unexpected request: {method} {url} {headers} {json} {params}")


class KiwoomRestClientTest(unittest.TestCase):
    def test_auth_client_requests_access_token(self):
        transport = FakeTransport()
        auth = KiwoomAuthClient(base_url="https://api.example", app_key="app", secret_key="secret", transport=transport)

        token = auth.issue_token()

        self.assertEqual(token.access_token, "token-123")
        self.assertEqual(token.token_type, "Bearer")
        self.assertEqual(transport.calls[0]["json"]["appkey"], "app")

    def test_market_client_uses_kiwoom_stock_info_tr(self):
        transport = FakeTransport()
        client = KiwoomRestClient(
            base_url="https://api.example",
            app_key="app",
            token_provider=lambda: KiwoomToken("Bearer", "token-123", 3600),
            transport=transport,
        )

        market = KiwoomMarketClient(client)
        quote = market.get_current_price("498270")

        self.assertEqual(quote["cur_prc"], "12345")
        call = transport.calls[-1]
        self.assertEqual(call["method"], "POST")
        self.assertEqual(call["url"], "https://api.example/api/dostk/stkinfo")
        self.assertEqual(call["json"], {"stk_cd": "498270"})
        self.assertEqual(call["headers"]["authorization"], "Bearer token-123")
        self.assertEqual(call["headers"]["api-id"], "ka10003")

    def test_account_client_uses_kiwoom_balance_tr(self):
        transport = FakeTransport()
        client = KiwoomRestClient(
            base_url="https://api.example",
            app_key="app",
            token_provider=lambda: KiwoomToken("Bearer", "token-123", 3600),
            transport=transport,
        )

        account = KiwoomAccountClient(client)
        balance = account.get_balance("12345678")

        self.assertEqual(balance["dnca_tot_amt"], "1000000")
        call = transport.calls[-1]
        self.assertEqual(call["method"], "POST")
        self.assertEqual(call["url"], "https://api.example/api/dostk/acnt")
        self.assertEqual(call["json"], {"qry_tp": "1", "dmst_stex_tp": "KRX"})
        self.assertEqual(call["headers"]["api-id"], "kt00018")


if __name__ == "__main__":
    unittest.main()
