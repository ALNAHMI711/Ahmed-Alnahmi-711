"""Fail-closed validation for market candles."""
from datetime import datetime, timezone

from .schemas import INTERVAL_MS, KlineInterval, KlineRecord, utc_now_ms


def validate_kline(kline: KlineRecord, *, now: datetime | None = None) -> KlineRecord:
    """Validate temporal alignment and OHLCV invariants; return the unchanged record."""
    duration = INTERVAL_MS[kline.interval]

    if kline.open_time >= kline.close_time:
        raise ValueError("open_time must be strictly earlier than close_time")

    # Binance closeTime is the final millisecond in the candle, not an exclusive bound.
    if kline.close_time != kline.open_time + duration - 1:
        raise ValueError("close_time must equal open_time plus interval duration minus one millisecond")

    if kline.interval == KlineInterval.W1:
        weekday = datetime.fromtimestamp(kline.open_time // 1000, tz=timezone.utc).weekday()
        if weekday != 0:
            raise ValueError("weekly candle must open on a UTC Monday")
    elif kline.open_time % duration != 0:
        raise ValueError("open_time is not aligned to the interval boundary")

    reference_now = utc_now_ms(now)
    if kline.open_time > reference_now:
        raise ValueError("future candles are not accepted")

    if kline.is_closed:
        if kline.close_time >= reference_now:
            raise ValueError("a closed candle must already have ended")
    elif kline.close_time < reference_now:
        raise ValueError("an ended candle must be marked closed")

    if kline.volume < 0 or kline.quote_volume < 0:
        raise ValueError("volume values must be non-negative")
    if min(kline.open, kline.high, kline.low, kline.close) <= 0:
        raise ValueError("OHLC prices must be strictly positive")
    if kline.high < max(kline.open, kline.close):
        raise ValueError("high must cover open and close")
    if kline.low > min(kline.open, kline.close):
        raise ValueError("low must cover open and close")
    return kline
