from decimal import Decimal

import httpx
import pytest

from backend.app.adapters.base import Market
from backend.app.adapters.binance import BinanceAdapter


class MockTransport(httpx.AsyncBaseTransport):
    def __init__(self, payload):
        self.payload = payload
        self.requests = []

    async def handle_async_request(self, request):
        self.requests.append(request)

        return httpx.Response(
            200,
            json=self.payload,
            request=request,
        )


@pytest.mark.asyncio
async def test_order_book_ticker_uses_binance_response():
    transport = MockTransport(
        {
            "symbol": "BTCUSDT",
            "bidPrice": "100.10",
            "bidQty": "2.5",
            "askPrice": "100.20",
            "askQty": "3.0",
        }
    )

    client = httpx.AsyncClient(
        transport=transport,
        base_url="https://test.local",
    )

    adapter = BinanceAdapter(
        Market.SPOT,
        "test-key",
        "test-secret",
        client=client,
    )

    ticker = await adapter.order_book_ticker("BTCUSDT")

    assert ticker.symbol == "BTCUSDT"
    assert ticker.bid_price == Decimal("100.10")
    assert ticker.bid_qty == Decimal("2.5")
    assert ticker.ask_price == Decimal("100.20")
    assert ticker.ask_qty == Decimal("3.0")

    assert len(transport.requests) == 1
    assert transport.requests[0].url.path == "/api/v3/ticker/bookTicker"

    await client.aclose()


@pytest.mark.asyncio
async def test_signed_account_request_contains_api_key_and_signature():
    transport = MockTransport(
        {
            "canTrade": True,
            "canWithdraw": False,
            "balances": [],
        }
    )

    client = httpx.AsyncClient(
        transport=transport,
        base_url="https://test.local",
    )

    adapter = BinanceAdapter(
        Market.SPOT,
        "test-key",
        "test-secret",
        client=client,
    )

    await adapter.account_capabilities()

    request = transport.requests[0]

    assert request.url.path == "/api/v3/account"
    assert request.headers["X-MBX-APIKEY"] == "test-key"

    query = dict(request.url.params)

    assert "timestamp" in query
    assert "recvWindow" in query
    assert "signature" in query
    assert len(query["signature"]) == 64

    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("market", "expected_path"),
    [
        (Market.SPOT, "/api/v3/order"),
        (Market.CROSS_MARGIN, "/sapi/v1/margin/order"),
        (Market.ISOLATED_MARGIN, "/sapi/v1/margin/order"),
        (Market.USDS_M, "/fapi/v1/order"),
        (Market.COIN_M, "/dapi/v1/order"),
    ],
)
async def test_place_order_uses_correct_endpoint(market, expected_path):
    transport = MockTransport(
        {
            "symbol": "BTCUSDT",
            "status": "NEW",
            "orderId": 123,
            "clientOrderId": "test-order",
        }
    )

    client = httpx.AsyncClient(
        transport=transport,
        base_url="https://test.local",
    )

    adapter = BinanceAdapter(
        market,
        "test-key",
        "test-secret",
        client=client,
    )

    result = await adapter.place_order(
        "BTCUSDT",
        "BUY",
        "LIMIT",
        Decimal("0.001"),
        price=Decimal("100"),
        client_order_id="test-order",
    )

    assert result["status"] == "NEW"
    assert transport.requests[0].url.path == expected_path

    params = dict(transport.requests[0].url.params)

    assert params["symbol"] == "BTCUSDT"
    assert params["side"] == "BUY"
    assert params["quantity"] == "0.001"
    assert params["newClientOrderId"] == "test-order"
    assert "signature" in params

    if market == Market.ISOLATED_MARGIN:
        assert params["isIsolated"] == "TRUE"

    if market == Market.CROSS_MARGIN:
        assert params["isIsolated"] == "FALSE"

    await client.aclose()
