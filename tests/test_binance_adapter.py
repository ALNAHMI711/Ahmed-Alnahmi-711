import hmac
from hashlib import sha256

import pytest

from backend.app.adapters.base import Market
from backend.app.adapters.binance import BinanceAdapter


def test_binance_signature_is_hmac_sha256(monkeypatch):
    monkeypatch.setattr('backend.app.adapters.binance.time.time', lambda: 1.0)
    adapter = BinanceAdapter(Market.SPOT, 'key', 'secret')
    params = adapter._signed({'symbol': 'BTCUSDT', 'quantity': 1})
    assert params['timestamp'] == '1000'
    expected = hmac.new(b'secret', b'quantity=1&symbol=BTCUSDT&timestamp=1000', sha256).hexdigest()
    assert params['signature'] == expected


def test_unverified_markets_cannot_create_binance_adapter():
    with pytest.raises(ValueError):
        BinanceAdapter(Market.ALPHA, 'key', 'secret')
