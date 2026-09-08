"""Pure domain schemas for historical and forming market candles."""
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class KlineInterval(StrEnum):
    M1 = "1m"
    M3 = "3m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H2 = "2h"
    H4 = "4h"
    H6 = "6h"
    H8 = "8h"
    H12 = "12h"
    D1 = "1d"
    D3 = "3d"
    W1 = "1w"


INTERVAL_MS: dict[KlineInterval, int] = {
    KlineInterval.M1: 60_000,
    KlineInterval.M3: 180_000,
    KlineInterval.M5: 300_000,
    KlineInterval.M15: 900_000,
    KlineInterval.M30: 1_800_000,
    KlineInterval.H1: 3_600_000,
    KlineInterval.H2: 7_200_000,
    KlineInterval.H4: 14_400_000,
    KlineInterval.H6: 21_600_000,
    KlineInterval.H8: 28_800_000,
    KlineInterval.H12: 43_200_000,
    KlineInterval.D1: 86_400_000,
    KlineInterval.D3: 259_200_000,
    KlineInterval.W1: 604_800_000,
}


class KlineRecord(BaseModel):
    """Immutable exchange candle contract; timestamps are UTC epoch milliseconds."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    market: str = Field(min_length=1, max_length=32)
    symbol: str = Field(min_length=1, max_length=32)
    interval: KlineInterval
    open_time: int = Field(ge=0)
    close_time: int = Field(ge=0)
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    quote_volume: Decimal = Field(default=Decimal(0))
    trades: int = Field(default=0, ge=0)
    is_closed: bool = False
    source: str = Field(default="binance", min_length=1, max_length=64)

    @field_validator("open", "high", "low", "close", "volume", "quote_volume")
    @classmethod
    def finite_non_negative_prices_or_volume(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("decimal values must be finite")
        return value

    @field_validator("symbol", "market")
    @classmethod
    def normalized_identifiers(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("identifier must not be blank")
        return normalized


def utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)
