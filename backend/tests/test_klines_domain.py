from datetime import datetime, timezone
from decimal import Decimal
from typing import cast

import pytest
from pydantic import ValidationError
from sqlalchemy import Table, UniqueConstraint

from backend.app.market_data.models import Kline
from backend.app.market_data.schemas import KlineInterval, KlineRecord
from backend.app.market_data.validation import validate_kline

NOW = datetime(2026, 1, 1, 0, 10, tzinfo=timezone.utc)
NOW_MS = 1_767_226_200_000


def candle(**overrides: object) -> KlineRecord:
    values: dict[str, object] = {
        "market": "spot",
        "symbol": "btcusdt",
        "interval": KlineInterval.M1,
        "open_time": 600_000,
        "close_time": 659_999,
        "open": Decimal("100.000000000000000001"),
        "high": Decimal("110.000000000000000001"),
        "low": Decimal("99.000000000000000001"),
        "close": Decimal("105.000000000000000001"),
        "volume": Decimal("1.123456789012345678901234567890"),
        "quote_volume": Decimal("118.000000000000000001"),
        "trades": 42,
        "is_closed": True,
    }
    values.update(overrides)
    return KlineRecord.model_validate(values)


def test_valid_kline_preserves_decimal_precision_and_normalizes_ids() -> None:
    result = validate_kline(candle(), now=NOW)
    assert result.market == "SPOT"
    assert result.symbol == "BTCUSDT"
    assert result.open == Decimal("100.000000000000000001")
    assert result.volume == Decimal("1.123456789012345678901234567890")


def test_open_time_must_align_to_interval() -> None:
    with pytest.raises(ValueError, match="aligned"):
        validate_kline(candle(open_time=610_000, close_time=669_999), now=NOW)


def test_close_time_must_match_inclusive_interval_boundary() -> None:
    with pytest.raises(ValueError, match="duration"):
        validate_kline(candle(close_time=660_000), now=NOW)


def test_future_open_time_is_rejected() -> None:
    open_time = NOW_MS + 60_000
    with pytest.raises(ValueError, match="future"):
        validate_kline(candle(open_time=open_time, close_time=open_time + 59_999), now=NOW)


def test_closed_candle_cannot_end_in_future() -> None:
    open_time = NOW_MS - 60_000
    with pytest.raises(ValueError, match="closed candle"):
        validate_kline(
            candle(open_time=open_time, close_time=NOW_MS - 1),
            now=datetime(2026, 1, 1, 0, 9, 59, 500_000, tzinfo=timezone.utc),
        )


def test_forming_candle_may_have_future_close_boundary() -> None:
    result = validate_kline(
        candle(open_time=NOW_MS, close_time=NOW_MS + 59_999, is_closed=False),
        now=NOW,
    )
    assert result.is_closed is False


def test_ohlc_and_volume_invariants_are_fail_closed() -> None:
    with pytest.raises(ValueError, match="high"):
        validate_kline(candle(high=Decimal(104)), now=NOW)
    with pytest.raises(ValueError, match="low"):
        validate_kline(candle(low=Decimal(106)), now=NOW)
    with pytest.raises(ValueError, match="non-negative"):
        validate_kline(candle(volume=Decimal(-1)), now=NOW)


def test_schema_rejects_non_finite_decimal() -> None:
    with pytest.raises(ValidationError, match="finite"):
        candle(open=Decimal("NaN"))


def test_schema_rejects_float_for_decimal_fields() -> None:
    with pytest.raises(ValidationError, match="Decimal"):
        candle(open=100.0)


def test_open_must_precede_close() -> None:
    with pytest.raises(ValueError, match="earlier"):
        validate_kline(candle(open_time=600_000, close_time=600_000), now=NOW)


def test_uniqueness_key_excludes_api_account() -> None:
    table = cast(Table, Kline.__table__)
    constraint = cast(
        UniqueConstraint,
        next(constraint for constraint in table.constraints if constraint.name == "uq_market_kline_candle"),
    )
    assert {column.name for column in constraint.columns} == {
        "market",
        "symbol",
        "interval",
        "open_time",
    }
