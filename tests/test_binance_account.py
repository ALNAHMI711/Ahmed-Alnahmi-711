import asyncio
from decimal import Decimal

import httpx

from backend.app.adapters.base import Market
from backend.app.adapters.binance import BinanceAdapter


def adapter(market, handler):
    transport = httpx.MockTransport(handler)
    return BinanceAdapter(market, "test-key", "test-secret", httpx.AsyncClient(transport=transport))


def test_futures_equity_uses_exchange_confirmed_balances():
    def handler(request):
        assert request.url.path == "/fapi/v2/account"
        assert request.headers["X-MBX-APIKEY"] == "test-key"
        assert request.url.params["signature"]
        return httpx.Response(200, json={"totalMarginBalance": "1250.50", "availableBalance": "900.25"})
    result = asyncio.run(adapter(Market.USDS_M, handler).account_equity())
    assert result.equity == Decimal("1250.50")
    assert result.available == Decimal("900.25")
    assert result.asset == "USDT"


def test_spot_equity_values_free_and_locked_balances_with_real_prices():
    def handler(request):
        if request.url.path == "/api/v3/account":
            return httpx.Response(200, json={"balances": [
                {"asset": "USDT", "free": "100", "locked": "10"},
                {"asset": "BTC", "free": "0.5", "locked": "0.1"},
            ]})
        assert request.url.path == "/api/v3/ticker/price"
        assert request.url.params["symbol"] == "BTCUSDT"
        return httpx.Response(200, json={"price": "50000"})
    result = asyncio.run(adapter(Market.SPOT, handler).account_equity())
    assert result.equity == Decimal("30110")
    assert result.available == Decimal("25100")


def test_cross_margin_uses_net_asset_btc_and_btc_usdt_price():
    def handler(request):
        if request.url.path == "/sapi/v1/margin/account":
            assert request.url.params["isIsolated"] == "FALSE"
            assert request.url.params["signature"]
            return httpx.Response(200, json={"totalNetAssetOfBtc": "0.02", "totalFreeAssetOfBtc": "0.015"})
        assert request.url.path == "/api/v3/ticker/price"
        return httpx.Response(200, json={"price": "50000"})
    result = asyncio.run(adapter(Market.CROSS_MARGIN, handler).account_equity())
    assert result.equity == Decimal("1000")
    assert result.available == Decimal("750")


def test_isolated_margin_requests_symbol_and_values_net_assets():
    def handler(request):
        if request.url.path == "/sapi/v1/margin/isolated/account":
            assert request.url.params["symbols"] == "BTCUSDT"
            return httpx.Response(200, json={"assets": [{
                "baseAsset": {"asset": "BTC", "netAsset": "0.1"},
                "quoteAsset": {"asset": "USDT", "netAsset": "250"},
            }]})
        if request.url.params["symbol"] == "BTCUSDT":
            return httpx.Response(200, json={"price": "50000"})
        return httpx.Response(404)
    result = asyncio.run(adapter(Market.ISOLATED_MARGIN, handler).account_equity("BTCUSDT"))
    assert result.equity == Decimal("5250")
    assert result.available == Decimal("5250")


def test_fills_preserve_exchange_fee_and_realized_pnl_without_network():
    def handler(request):
        assert request.url.path == "/fapi/v1/userTrades"
        return httpx.Response(200, json=[{
            "id": 7, "orderId": 9, "symbol": "BTCUSDT", "side": "SELL",
            "buyer": False, "qty": "0.2", "price": "30000", "quoteQty": "6000",
            "commission": "1.5", "commissionAsset": "USDT", "realizedPnl": "120",
            "time": 1760000000000,
        }])
    result = asyncio.run(adapter(Market.USDS_M, handler).fills("BTCUSDT"))
    assert result[0].trade_id == "7"
    assert result[0].fee == Decimal("1.5")
    assert result[0].fee_asset == "USDT"
    assert result[0].realized_pnl == Decimal("120")
