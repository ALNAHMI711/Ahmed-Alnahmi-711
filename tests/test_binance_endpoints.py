import pytest

from backend.app.adapters.base import Market
from backend.app.adapters.binance import BinanceAdapter


@pytest.mark.parametrize(
    ("market", "expected"),
    [
        (Market.SPOT, "/api/v3/exchangeInfo"),
        (Market.CROSS_MARGIN, "/api/v3/exchangeInfo"),
        (Market.ISOLATED_MARGIN, "/api/v3/exchangeInfo"),
        (Market.USDS_M, "/fapi/v1/exchangeInfo"),
        (Market.COIN_M, "/dapi/v1/exchangeInfo"),
    ],
)
def test_symbol_validation_endpoint(market, expected):
    adapter = BinanceAdapter(market, "k", "s")

    if market == Market.SPOT:
        assert expected == "/api/v3/exchangeInfo"
    elif market in (Market.CROSS_MARGIN, Market.ISOLATED_MARGIN):
        assert expected == "/api/v3/exchangeInfo"
    elif market == Market.USDS_M:
        assert expected == "/fapi/v1/exchangeInfo"
    else:
        assert expected == "/dapi/v1/exchangeInfo"


@pytest.mark.parametrize(
    ("market", "expected"),
    [
        (Market.SPOT, "/api/v3/ticker/bookTicker"),
        (Market.CROSS_MARGIN, "/api/v3/ticker/bookTicker"),
        (Market.ISOLATED_MARGIN, "/api/v3/ticker/bookTicker"),
        (Market.USDS_M, "/fapi/v1/ticker/bookTicker"),
        (Market.COIN_M, "/dapi/v1/ticker/bookTicker"),
    ],
)
def test_order_book_endpoint_mapping(market, expected):
    adapter = BinanceAdapter(market, "k", "s")

    if adapter._is_spot_family:
        actual = "/api/v3/ticker/bookTicker"
    elif market == Market.USDS_M:
        actual = "/fapi/v1/ticker/bookTicker"
    else:
        actual = "/dapi/v1/ticker/bookTicker"

    assert actual == expected


@pytest.mark.parametrize(
    ("market", "expected"),
    [
        (Market.SPOT, "/api/v3/order"),
        (Market.CROSS_MARGIN, "/sapi/v1/margin/order"),
        (Market.ISOLATED_MARGIN, "/sapi/v1/margin/order"),
        (Market.USDS_M, "/fapi/v1/order"),
        (Market.COIN_M, "/dapi/v1/order"),
    ],
)
def test_order_endpoint_mapping(market, expected):
    adapter = BinanceAdapter(market, "k", "s")

    if market == Market.SPOT:
        actual = "/api/v3/order"
    elif market in (Market.CROSS_MARGIN, Market.ISOLATED_MARGIN):
        actual = "/sapi/v1/margin/order"
    elif market == Market.USDS_M:
        actual = "/fapi/v1/order"
    else:
        actual = "/dapi/v1/order"

    assert actual == expected


@pytest.mark.parametrize(
    ("market", "expected"),
    [
        (Market.SPOT, "/api/v3/openOrders"),
        (Market.CROSS_MARGIN, "/sapi/v1/margin/openOrders"),
        (Market.ISOLATED_MARGIN, "/sapi/v1/margin/openOrders"),
        (Market.USDS_M, "/fapi/v1/openOrders"),
        (Market.COIN_M, "/dapi/v1/openOrders"),
    ],
)
def test_open_orders_endpoint_mapping(market, expected):
    adapter = BinanceAdapter(market, "k", "s")

    if market == Market.SPOT:
        actual = "/api/v3/openOrders"
    elif market in (Market.CROSS_MARGIN, Market.ISOLATED_MARGIN):
        actual = "/sapi/v1/margin/openOrders"
    elif market == Market.USDS_M:
        actual = "/fapi/v1/openOrders"
    else:
        actual = "/dapi/v1/openOrders"

    assert actual == expected


def test_isolated_margin_adds_isolated_flag():
    adapter = BinanceAdapter(
        Market.ISOLATED_MARGIN,
        "k",
        "s",
    )
    assert adapter._margin_params() == {"isIsolated": "TRUE"}


def test_cross_margin_adds_cross_flag():
    adapter = BinanceAdapter(
        Market.CROSS_MARGIN,
        "k",
        "s",
    )
    assert adapter._margin_params() == {"isIsolated": "FALSE"}
