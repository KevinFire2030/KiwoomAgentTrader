import unittest

from app.agents.models import OrderType, TradeSide, TradeTicket
from app.agents.trade_execution import TradeExecutionAgent
from app.kiwoom.auth import KiwoomToken
from app.kiwoom.client import KiwoomRestClient
from app.kiwoom.orders import KiwoomOrderClient


class FakeOrderTransport:
    def __init__(self):
        self.calls = []

    def request(self, method, url, headers=None, json=None, params=None, timeout=10):
        self.calls.append({"method": method, "url": url, "headers": headers or {}, "json": json, "params": params})
        if url.endswith("/api/dostk/ordr") and (headers or {}).get("api-id") in {"kt10000", "kt10001"}:
            return {"return_code": 0, "return_msg": "주문이 접수되었습니다", "ord_no": "12345"}
        raise AssertionError(f"unexpected request: {method} {url} {headers} {json} {params}")


def approved_ticket(side: TradeSide = "buy", order_type: OrderType = "limit", limit_price=18600):
    return TradeTicket(
        "TT-live-001",
        "498270",
        side,
        3,
        order_type,
        limit_price,
        "trading_strategy_agent",
        risk_approved=True,
        risk_approved_by="risk_management_agent",
        user_approved=True,
        status="user_approved",
    )


class KiwoomOrderClientTest(unittest.TestCase):
    def test_builds_live_manual_buy_order_request_without_submitting(self):
        transport = FakeOrderTransport()
        client = KiwoomRestClient(
            base_url="https://api.example",
            app_key="app",
            token_provider=lambda: KiwoomToken("Bearer", "token-123", 3600),
            transport=transport,
        )
        order = KiwoomOrderClient(client)

        request = order.build_order_request(approved_ticket())

        self.assertEqual(request.endpoint, "/api/dostk/ordr")
        self.assertEqual(request.api_id, "kt10000")
        self.assertEqual(request.payload["dmst_stex_tp"], "KRX")
        self.assertEqual(request.payload["stk_cd"], "498270")
        self.assertEqual(request.payload["ord_qty"], "3")
        self.assertEqual(request.payload["ord_uv"], "18600")
        self.assertEqual(request.payload["trde_tp"], "0")
        self.assertEqual(transport.calls, [])

    def test_builds_sell_order_with_sell_api_id(self):
        client = KiwoomRestClient("https://api.example", "app", lambda: KiwoomToken("Bearer", "token-123", 3600), transport=FakeOrderTransport())
        request = KiwoomOrderClient(client).build_order_request(approved_ticket(side="sell"))

        self.assertEqual(request.api_id, "kt10001")

    def test_rejects_live_order_preparation_without_user_approval(self):
        client = KiwoomRestClient("https://api.example", "app", lambda: KiwoomToken("Bearer", "token-123", 3600), transport=FakeOrderTransport())
        ticket = TradeTicket("TT-live-002", "498270", "buy", 1, "limit", 18600, "trading_strategy_agent", risk_approved=True)

        with self.assertRaises(PermissionError):
            KiwoomOrderClient(client).build_order_request(ticket)

    def test_place_order_uses_kiwoom_order_tr(self):
        transport = FakeOrderTransport()
        client = KiwoomRestClient("https://api.example", "app", lambda: KiwoomToken("Bearer", "token-123", 3600), transport=transport)

        result = KiwoomOrderClient(client).place_order(approved_ticket())

        self.assertTrue(result.accepted)
        call = transport.calls[-1]
        self.assertEqual(call["method"], "POST")
        self.assertEqual(call["url"], "https://api.example/api/dostk/ordr")
        self.assertEqual(call["headers"]["api-id"], "kt10000")
        self.assertEqual(call["json"]["stk_cd"], "498270")

    def test_execution_agent_blocks_real_live_submission_when_disabled(self):
        client = KiwoomRestClient("https://api.example", "app", lambda: KiwoomToken("Bearer", "token-123", 3600), transport=FakeOrderTransport())

        with self.assertRaises(PermissionError):
            TradeExecutionAgent().execute_live_manual(approved_ticket(), KiwoomOrderClient(client), enable_live_trading=False)


if __name__ == "__main__":
    unittest.main()
