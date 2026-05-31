import unittest

from app.kiwoom.auth import KiwoomToken
from app.kiwoom.client import KiwoomRestClient
from app.kiwoom.transactions import KiwoomTransactionClient, summarize_transactions


class FakeTransport:
    def __init__(self):
        self.calls = []

    def request(self, method, url, headers=None, json=None, params=None, timeout=10):
        self.calls.append({"method": method, "url": url, "headers": headers or {}, "json": json})
        if url.endswith("/api/dostk/acnt") and (headers or {}).get("api-id") == "kt00015":
            return {
                "return_code": 0,
                "return_msg": "조회가 완료되었습니다",
                "trst_ovrl_trde_prps_array": [
                    {"trde_dt": "20250910", "io_tp_nm": "입금", "trde_amt": "000000000050000", "entra_remn": "000000000050000"},
                    {"trde_dt": "20250911", "io_tp_nm": "출금", "trde_amt": "000000000010000", "entra_remn": "000000000040000"},
                ],
            }
        raise AssertionError(f"unexpected request: {method} {url} {headers} {json}")


class KiwoomTransactionHistoryTest(unittest.TestCase):
    def test_requests_entrusted_transaction_history(self):
        transport = FakeTransport()
        rest = KiwoomRestClient(
            base_url="https://api.example",
            app_key="app",
            token_provider=lambda: KiwoomToken("Bearer", "token", 3600),
            transport=transport,
        )
        client = KiwoomTransactionClient(rest)

        rows = client.get_deposit_withdraw_history("20250601", "20260531")

        self.assertEqual(len(rows), 2)
        call = transport.calls[-1]
        self.assertEqual(call["method"], "POST")
        self.assertEqual(call["url"], "https://api.example/api/dostk/acnt")
        self.assertEqual(call["headers"]["api-id"], "kt00015")
        self.assertEqual(call["json"]["tp"], "1")
        self.assertEqual(call["json"]["strt_dt"], "20250601")
        self.assertEqual(call["json"]["end_dt"], "20260531")
        self.assertEqual(call["json"]["dmst_stex_tp"], "%")

    def test_summarizes_deposits_withdrawals_and_latest_balance(self):
        rows = [
            {"trde_dt": "20250910", "io_tp_nm": "입금", "trde_amt": "000000000050000", "entra_remn": "000000000050000"},
            {"trde_dt": "20250911", "io_tp_nm": "출금", "trde_amt": "000000000010000", "entra_remn": "000000000040000"},
            {"trde_dt": "20250912", "io_tp_nm": "입금", "trde_amt": "000000000000320", "entra_remn": "000000000040320"},
        ]

        summary = summarize_transactions(rows)

        self.assertEqual(summary.deposit_total, 50320)
        self.assertEqual(summary.withdraw_total, 10000)
        self.assertEqual(summary.count, 3)
        self.assertEqual(summary.latest_balance, 40320)


if __name__ == "__main__":
    unittest.main()
