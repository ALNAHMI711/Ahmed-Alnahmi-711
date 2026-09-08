from decimal import Decimal

import pytest

from backend.app.adapters.base import Market
from backend.app.execution.exits import binance_exit_order

@pytest.mark.parametrize("market,sl,tp", [
    (Market.SPOT, "STOP_LOSS_LIMIT", "TAKE_PROFIT_LIMIT"),
    (Market.CROSS_MARGIN, "STOP_LOSS_LIMIT", "TAKE_PROFIT_LIMIT"),
    (Market.ISOLATED_MARGIN, "STOP_LOSS_LIMIT", "TAKE_PROFIT_LIMIT"),
    (Market.USDS_M, "STOP_MARKET", "TAKE_PROFIT_MARKET"),
    (Market.COIN_M, "STOP_MARKET", "TAKE_PROFIT_MARKET"),
])
def test_native_mapping_all_five_markets(market, sl, tp):
    stop = binance_exit_order("SL", "LONG", market, Decimal(1), Decimal(90), "sl-1")
    take = binance_exit_order("TP", "LONG", market, Decimal(1), Decimal(110), "tp-1")
    assert stop["order_type"] == sl
    assert take["order_type"] == tp
    assert stop["reduce_only"] is True
    assert take["reduce_only"] is True
    assert stop["client_order_id"] == "sl-1"
    assert take["client_order_id"] == "tp-1"
    assert "orderId" not in stop and "orderId" not in take

@pytest.mark.parametrize("market", [Market.SPOT, Market.CROSS_MARGIN, Market.ISOLATED_MARGIN])
def test_spot_margin_mapping_requires_limit_price(market):
    spec = binance_exit_order("SL", "LONG", market, Decimal(1), Decimal(90), "x")
    assert spec["requires_limit_price"] is True

@pytest.mark.parametrize("market", [Market.USDS_M, Market.COIN_M])
def test_futures_mapping_uses_native_market_exit(market):
    spec = binance_exit_order("TP", "SHORT", market, Decimal(1), Decimal(110), "x")
    assert spec["order_type"] == "TAKE_PROFIT_MARKET"
    assert spec["side"] == "BUY"
    assert spec["requires_limit_price"] is False

def test_unknown_market_fails_closed():
    with pytest.raises(ValueError):
        binance_exit_order("SL", "LONG", Market.ALPHA, Decimal(1), Decimal(90), "x")
