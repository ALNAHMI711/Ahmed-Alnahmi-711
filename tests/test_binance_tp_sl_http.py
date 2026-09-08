from decimal import Decimal

import httpx
import pytest

from backend.app.adapters.base import Market
from backend.app.adapters.binance import BinanceAdapter

@pytest.mark.asyncio
@pytest.mark.parametrize("market,expected_path", [
    (Market.SPOT, "/api/v3/order"),
    (Market.CROSS_MARGIN, "/sapi/v1/margin/order"),
    (Market.ISOLATED_MARGIN, "/sapi/v1/margin/order"),
    (Market.USDS_M, "/fapi/v1/order"),
    (Market.COIN_M, "/dapi/v1/order"),
])
async def test_tp_sl_submission_uses_market_native_endpoint(market, expected_path):
    seen = {}
    def handler(request: httpx.Request):
        seen["path"] = request.url.path
        seen["params"] = dict(request.url.params)
        return httpx.Response(200, json={"orderId": 987, "status": "NEW"})
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = BinanceAdapter(market, "key", "secret", client=client)
    order_type = "STOP_MARKET" if market in (Market.USDS_M, Market.COIN_M) else "STOP_LOSS_LIMIT"
    response = await adapter.place_order(
        "BTCUSDT", "SELL", order_type, Decimal(1),
        price=Decimal(89) if market in (Market.SPOT, Market.CROSS_MARGIN, Market.ISOLATED_MARGIN) else None,
        client_order_id="sl-http-1", reduce_only=True, stop_price=Decimal(90),
    )
    assert seen["path"] == expected_path
    assert response["orderId"] == 987
    assert seen["params"]["type"] == order_type
    assert seen["params"]["stopPrice"] == "90"
    assert seen["params"]["newClientOrderId"] == "sl-http-1"
    if market in (Market.CROSS_MARGIN, Market.ISOLATED_MARGIN):
        assert seen["params"]["isIsolated"] == ("TRUE" if market == Market.ISOLATED_MARGIN else "FALSE")
    if market in (Market.USDS_M, Market.COIN_M):
        assert seen["params"]["reduceOnly"] == "true"
    else:
        assert "reduceOnly" not in seen["params"]
    await client.aclose()
