import pytest
from decimal import Decimal
from types import SimpleNamespace
from backend.app.adapters.binance import BinanceAdapter
from backend.app.adapters.base import Market

class DummyResponse:
    def __init__(self, payload):
        self._payload = payload
    def raise_for_status(self):
        pass
    def json(self):
        return self._payload

@pytest.mark.asyncio
async def test_mark_price_prefers_markPrice():
    adapter = BinanceAdapter(Market.SPOT, "k", "s", client=None)
    async def fake_get(url, params=None):
        return DummyResponse({"symbol":"X", "markPrice":"123.45"})
    adapter.client = SimpleNamespace(get=fake_get)
    price = await adapter.mark_price("ANY")
    assert price == Decimal("123.45")

@pytest.mark.asyncio
async def test_mark_price_fallback_to_price():
    adapter = BinanceAdapter(Market.SPOT, "k", "s", client=None)
    async def fake_get(url, params=None):
        return DummyResponse({"symbol":"X", "price":"67.89"})
    adapter.client = SimpleNamespace(get=fake_get)
    price = await adapter.mark_price("ANY")
    assert price == Decimal("67.89")
