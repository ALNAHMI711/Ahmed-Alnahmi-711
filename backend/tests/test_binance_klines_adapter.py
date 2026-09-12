from decimal import Decimal
from urllib.parse import parse_qs

import httpx
import pytest

from backend.app.adapters.base import Market
from backend.app.adapters.binance import BinanceAdapter
from backend.app.market_data import KlineInterval

BASE_OPEN_MS = 1_760_000_040_000
BASE_CLOSE_MS = BASE_OPEN_MS + 59_999


def kline_payload() -> list[list[object]]:
    # Binance closeTime is the inclusive final millisecond of the candle.
    return [
        [
            BASE_OPEN_MS,
            "100.10",
            "105.20",
            "99.90",
            "104.30",
            "12.500000",
            BASE_CLOSE_MS,
            "1301.250000",
            42,
            "6.25",
            "650.625",
            "0",
        ]
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("market", "path"),
    [
        (Market.SPOT, "/api/v3/klines"),
        (Market.CROSS_MARGIN, "/api/v3/klines"),
        (Market.ISOLATED_MARGIN, "/api/v3/klines"),
        (Market.USDS_M, "/fapi/v1/klines"),
        (Market.COIN_M, "/dapi/v1/klines"),
    ],
)
async def test_klines_routes_by_market_and_uses_domain_decimals(market, path):
    seen: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        query = request.url.query.decode() if isinstance(request.url.query, bytes) else request.url.query
        seen["params"] = {key: values[0] for key, values in parse_qs(query).items()}
        return httpx.Response(200, json=kline_payload())

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = BinanceAdapter(market, "test-key", "test-secret", client)

    records = await adapter.klines("BTCUSDT", KlineInterval.M1, limit=1)

    assert seen["method"] == "GET"
    assert seen["path"] == path
    assert seen["params"] == {"symbol": "BTCUSDT", "interval": "1m", "limit": "1"}
    assert len(records) == 1
    record = records[0]
    assert record.market == market.name
    assert record.symbol == "BTCUSDT"
    assert record.open == Decimal("100.10")
    assert record.high == Decimal("105.20")
    assert record.low == Decimal("99.90")
    assert record.close == Decimal("104.30")
    assert record.volume == Decimal("12.500000")
    assert record.quote_volume == Decimal("1301.250000")
    assert record.trades == 42
    assert record.is_closed

    await client.aclose()


@pytest.mark.asyncio
async def test_klines_passes_time_window_to_binance():
    seen: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        query = request.url.query.decode() if isinstance(request.url.query, bytes) else request.url.query
        seen["params"] = {key: values[0] for key, values in parse_qs(query).items()}
        return httpx.Response(200, json=kline_payload())

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = BinanceAdapter(Market.SPOT, "k", "s", client)

    await adapter.klines(
        "ETHUSDT",
        KlineInterval.M1,
        start_time=BASE_OPEN_MS,
        end_time=BASE_CLOSE_MS,
        limit=100,
    )

    assert seen["params"] == {
        "symbol": "ETHUSDT",
        "interval": "1m",
        "limit": "100",
        "startTime": str(BASE_OPEN_MS),
        "endTime": str(BASE_CLOSE_MS),
    }
    await client.aclose()


@pytest.mark.asyncio
async def test_klines_rejects_invalid_limits_before_network():
    async def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("network must not be called")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = BinanceAdapter(Market.SPOT, "k", "s", client)

    with pytest.raises(ValueError, match="limit"):
        await adapter.klines("BTCUSDT", KlineInterval.M1, limit=1001)

    await client.aclose()


@pytest.mark.asyncio
async def test_klines_rejects_malformed_exchange_row():
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[[BASE_OPEN_MS, "100"]])

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = BinanceAdapter(Market.SPOT, "k", "s", client)

    with pytest.raises(TypeError, match="kline row"):
        await adapter.klines("BTCUSDT", KlineInterval.M1)

    await client.aclose()
