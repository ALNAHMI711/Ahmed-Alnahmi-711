"""Fail-closed validation for market candles."""
from datetime import datetime, timezone
from decimal import Decimal

from .schemas import INTERVAL_MS, KlineRecord


def _utc_ms(value: datetime) -> int:
    if value.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return int(value.astimezone(timezone.utc).timestamp() * 1000)


def validate_kline(kline: KlineRecord, *, now: datetime | None = None) -> KlineRecord:
    """Validate temporal alignment and OHLCV invariants; return the unchanged record."""
    duration = INTERVAL_MS[kline.interval]
    if kline.open_time >= kline.close_time:
        raise ValueError("open_time must be strictly earlier than close_time")
    if kline.close_time - kline.open_time != duration:
        raise ValueError("close_time must equal open_time plus the interval duration")
    if kline.open_time % duration != 0:
        raise ValueError("open_time is not aligned to the interval boundary")

    reference_now = _utc_ms(now or datetime.now(timezone.utc))
    if kline.open_time > reference_now:
        raise ValueError("future candles are not accepted")
    if kline.is_closed and kline.close_time > reference_now:
        raise ValueError("a closed candle cannot end in the future")

    if kline.volume < 0 or kline.quote_volume < 0:
        raise ValueError("volume values must be non-negative")
    if min(kline.open, kline.high, kline.low, kline.close) <= Decimal(0):
        raise ValueError("OHLC prices must be strictly positive")
    if kline.high < max(kline.open, kline.close):
        raise ValueError("high must cover open and close")
    if kline.low > min(kline.open, kline.close):
        raise ValueError("low must cover open and close")
    return kline
