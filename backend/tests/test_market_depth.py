from decimal import Decimal
import pytest
from app.adapters.market_depth import BinanceMarketDepthMixin, BookLevel, OrderBook

class DepthHarness(BinanceMarketDepthMixin):
    pass

def test_buy_slippage_walks_multiple_ask_levels():
    book = OrderBook((BookLevel(Decimal("99"), Decimal("10")),), (BookLevel(Decimal("100"), Decimal("2")), BookLevel(Decimal("101"), Decimal("3"))))
    result = DepthHarness.estimate_slippage(book, "BUY", Decimal("5"))
    assert result.fully_fillable
    assert result.estimated_average_price == Decimal("100.6")
    assert result.slippage_bps == Decimal("60")

def test_sell_slippage_is_positive_when_crossing_lower_bid_levels():
    book = OrderBook((BookLevel(Decimal("100"), Decimal("2")), BookLevel(Decimal("99"), Decimal("3"))), (BookLevel(Decimal("101"), Decimal("5")),))
    result = DepthHarness.estimate_slippage(book, "SELL", Decimal("5"))
    assert result.fully_fillable
    assert result.estimated_average_price == Decimal("99.4")
    assert result.slippage_bps == Decimal("60")

def test_unfillable_quantity_fails_closed():
    book = OrderBook((BookLevel(Decimal("100"), Decimal("1")),), (BookLevel(Decimal("101"), Decimal("1")),))
    result = DepthHarness.estimate_slippage(book, "BUY", Decimal("2"))
    assert not result.fully_fillable
    assert result.estimated_average_price == Decimal("0")

@pytest.mark.asyncio
async def test_depth_uses_market_specific_public_endpoint():
    class Response:
        def raise_for_status(self): pass
        def json(self): return {"lastUpdateId": 7, "bids": [["100", "2"]], "asks": [["101", "3"]]}
    class Client:
        async def get(self, url, params):
            assert url.endswith("/fapi/v1/depth")
            assert params == {"symbol": "BTCUSDT", "limit": 20}
            return Response()
    adapter = DepthHarness()
    adapter.market = __import__("app.adapters.base", fromlist=["Market"]).Market.USDS_M
    adapter.base_url = "https://fapi.binance.com"
    adapter.client = Client()
    book = await adapter.order_book("BTCUSDT")
    assert book.last_update_id == 7
    assert book.bids[0].price == Decimal("100")
    assert book.asks[0].quantity == Decimal("3")
