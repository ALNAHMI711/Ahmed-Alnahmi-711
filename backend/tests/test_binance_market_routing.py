import hashlib
import hmac
from urllib.parse import parse_qs

import httpx
import pytest

from app.adapters.binance import BinanceAdapter
from app.adapters.base import Market

@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("market", "path", "extra"),
    [(Market.SPOT, "/api/v3/order", {}),(Market.CROSS_MARGIN, "/sapi/v1/margin/order", {"isIsolated": "FALSE"}),(Market.ISOLATED_MARGIN, "/sapi/v1/margin/order", {"isIsolated": "TRUE"}),(Market.USDS_M, "/fapi/v1/order", {}),(Market.COIN_M, "/dapi/v1/order", {})],
)
async def test_cancel_order_uses_correct_binance_market_endpoint(market, path, extra):
    seen={}
    async def handler(request:httpx.Request)->httpx.Response:
        seen["method"],seen["path"]=request.method,request.url.path
        seen["params"]={key:values[0] for key,values in parse_qs(request.url.query).items()}
        return httpx.Response(200,json={"symbol":"BTCUSDT","status":"CANCELED"})
    client=httpx.AsyncClient(transport=httpx.MockTransport(handler)); adapter=BinanceAdapter(market,"test-key","test-secret",client)
    payload=await adapter.cancel_order("BTCUSDT",client_order_id="cid-123")
    assert payload["status"]=="CANCELED"; assert seen["method"]=="DELETE"; assert seen["path"]==path
    assert seen["params"]["symbol"]=="BTCUSDT"; assert seen["params"]["origClientOrderId"]=="cid-123"
    for key,value in extra.items():assert seen["params"][key]==value
    signed={key:value for key,value in seen["params"].items() if key!="signature"}; query="&".join(f"{key}={value}" for key,value in signed.items())
    assert seen["params"]["signature"]==hmac.new(b"test-secret",query.encode(),hashlib.sha256).hexdigest(); await client.aclose()

@pytest.mark.asyncio
async def test_binance_adapter_exposes_market_depth():
    async def handler(request:httpx.Request)->httpx.Response:
        assert request.url.path=="/api/v3/depth"
        return httpx.Response(200,json={"lastUpdateId":7,"bids":[["100","2"]],"asks":[["101","3"]]})
    client=httpx.AsyncClient(transport=httpx.MockTransport(handler)); adapter=BinanceAdapter(Market.SPOT,"k","s",client)
    book=await adapter.order_book("BTCUSDT")
    assert book.best_bid==100 and book.best_ask==101 and book.spread==1
    await client.aclose()
