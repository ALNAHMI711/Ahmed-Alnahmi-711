import pytest

from backend.app.adapters.base import Market
from backend.app.adapters.binance import BinanceAdapter


@pytest.mark.parametrize(
    ("market", "expected_base"),
    [
        (Market.SPOT, "https://api.binance.com"),
        (Market.CROSS_MARGIN, "https://api.binance.com"),
        (Market.ISOLATED_MARGIN, "https://api.binance.com"),
        (Market.USDS_M, "https://fapi.binance.com"),
        (Market.COIN_M, "https://dapi.binance.com"),
    ],
)
def test_binance_base_url_routing(market, expected_base):
    adapter = BinanceAdapter(market, "test-key", "test-secret")
    assert adapter.base_url == expected_base


def test_all_supported_binance_markets_are_instantiable():
    markets = (
        Market.SPOT,
        Market.CROSS_MARGIN,
        Market.ISOLATED_MARGIN,
        Market.USDS_M,
        Market.COIN_M,
    )

    for market in markets:
        adapter = BinanceAdapter(market, "test-key", "test-secret")
        assert adapter.market == market
