import asyncio
from decimal import Decimal

import httpx
import pytest

from backend.app.adapters.market_depth import OrderBook, BookLevel
from backend.app.adapters.markets import (
    COINMAdapter,
    CrossMarginAdapter,
    IsolatedMarginAdapter,
    SpotAdapter,
    USDSMAdapter,
)


ADAPTERS = [
    (SpotAdapter, "/api/v3/depth"),
    (CrossMarginAdapter, "/api/v3/depth"),
    (IsolatedMarginAdapter, "/api/v3/depth"),
    (USDSMAdapter, "/fapi/v1/depth"),
    (COINMAdapter, "/dapi/v1/depth"),
]


def adapter(adapter_type, handler):
    return adapter_type("test-key", "test-secret", httpx.AsyncClient(transport=httpx.MockTransport(handler)))


@pytest.mark.parametrize("adapter_type, expected_path", ADAPTERS)
def test_order_book_routes_to_correct_public_binance_endpoint(adapter_type, expected_path):
    def handler(request):
        assert request.url.path == expected_path
        assert request.url.params["symbol"] == "BTCUSDT"
        assert request.url.params["limit"] == "20"
        return httpx.Response(200, json={
            "lastUpdateId": 123,
            "bids": [["99.0", "2.0"], ["98.5", "3.0"]],
            "asks": [["100.0", "1.0"], ["101.0", "4.0"]],
        })

    result = asyncio.run(adapter(adapter_type, handler).order_book("BTCUSDT"))
    assert result.last_update_id == 123
    assert result.bids[0] == BookLevel(Decimal("99.0"), Decimal("2.0"))
    assert result.asks[0] == BookLevel(Decimal("100.0"), Decimal("1.0"))


def test_best_bid_ask_and_spread_are_deterministic():
    book = OrderBook(
        bids=(BookLevel(Decimal("99"), Decimal("2")),),
        asks=(BookLevel(Decimal("100"), Decimal("1")),),
    )
    assert book.best_bid == Decimal("99")
    assert book.best_ask == Decimal("100")
    assert book.spread == Decimal("1")
    assert book.spread_bps == Decimal("101.0101010101010101010101010101010")


def test_buy_slippage_walks_multiple_ask_levels():
    book = OrderBook(
        bids=(BookLevel(Decimal("99"), Decimal("10")),),
        asks=(BookLevel(Decimal("100"), Decimal("2")), BookLevel(Decimal("102"), Decimal("3"))),
    )
    result = USDSMAdapter.estimate_slippage(book, "BUY", Decimal("3"))
    assert result.fully_fillable is True
    assert result.reference_price == Decimal("100")
    assert result.estimated_average_price == Decimal("100.6666666666666666666666666666667")
    assert result.slippage_bps == Decimal("66.6666666666666666666666666666667")


def test_sell_slippage_walks_multiple_bid_levels():
    book = OrderBook(
        bids=(BookLevel(Decimal("99"), Decimal("2")), BookLevel(Decimal("98"), Decimal("3"))),
        asks=(BookLevel(Decimal("100"), Decimal("10")),),
    )
    result = USDSMAdapter.estimate_slippage(book, "SELL", Decimal("3"))
    assert result.fully_fillable is True
    assert result.reference_price == Decimal("99")
    assert result.estimated_average_price == Decimal("98.6666666666666666666666666666667")
    assert result.slippage_bps == Decimal("33.67003367003367003367003367003367")


def test_slippage_fails_closed_when_depth_is_insufficient():
    book = OrderBook(
        bids=(BookLevel(Decimal("99"), Decimal("1")),),
        asks=(BookLevel(Decimal("100"), Decimal("1")),),
    )
    result = USDSMAdapter.estimate_slippage(book, "BUY", Decimal("2"))
    assert result.fully_fillable is False
    assert result.estimated_average_price == Decimal("0")
    assert result.slippage_bps == Decimal("0")


def test_order_book_rejects_invalid_limit():
    async def run():
        with pytest.raises(ValueError):
            await adapter(SpotAdapter, lambda request: httpx.Response(500)).order_book("BTCUSDT", 0)
        with pytest.raises(ValueError):
            await adapter(SpotAdapter, lambda request: httpx.Response(500)).order_book("BTCUSDT", 1001)

    asyncio.run(run())


def test_slippage_rejects_invalid_side_and_quantity():
    book = OrderBook(
        bids=(BookLevel(Decimal("99"), Decimal("1")),),
        asks=(BookLevel(Decimal("100"), Decimal("1")),),
    )
    with pytest.raises(ValueError):
        USDSMAdapter.estimate_slippage(book, "HOLD", Decimal("1"))
    with pytest.raises(ValueError):
        USDSMAdapter.estimate_slippage(book, "BUY", Decimal("0"))
