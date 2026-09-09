"""Domain contract tests for strict Kline validation."""

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


def candle(
    open_time: int = 600_000,
    *,
    close_time: int | None = None,
    open: Decimal = Decimal(100),
    high: Decimal = Decimal(105),
    low: Decimal = Decimal(99),
    close: Decimal = Decimal(104),
    volume: Decimal = Decimal("1.5"),
    quote_volume: Decimal = Decimal("157.5"),
    trades: int = 10,
    is_closed: bool = True,
) -> KlineRecord:
    return KlineRecord(
        market="spot",
        symbol="btcusdt",
        interval=KlineInterval.M1,
        open_time=open_time,
        close_time=close_time if close_time is not None else open_time + 59_999,
        open=open,
        high=high,
        low=low,
        close=close,
        volume=volume,
        quote_volume=quote_volume,
        trades=trades,
        is_closed=is_closed,
        source="test",
    )


def test_decimal_contract_rejects_float_injection() -> None:
    payload: dict[str, object] = {
        "market": "spot",
        "symbol": "BTCUSDT",
        "interval": KlineInterval.M1,
        "open_time": 600_000,
        "close_time": 659_999,
        "open": 100.0,
        "high": 105.0,
        "low": 99.0,
        "close": 104.0,
        "volume": 1.0,
        "quote_volume": 157.5,
        "trades": 10,
        "is_closed": True,
    }
    with pytest.raises(ValidationError, match="finite Decimal"):
        KlineRecord.model_validate(payload)


def test_temporal_contract_is_strict() -> None:
    with pytest.raises(ValueError, match="strictly earlier"):
        validate_kline(candle(close_time=600_000), now=NOW)
    with pytest.raises(ValueError, match="close_time must equal"):
        validate_kline(candle(close_time=660_000), now=NOW)


def test_interval_alignment_is_required() -> None:
    with pytest.raises(ValueError, match="aligned"):
        validate_kline(candle(open_time=600_001), now=NOW)


def test_future_candle_is_rejected() -> None:
    with pytest.raises(ValueError, match="future"):
        validate_kline(candle(open_time=NOW.timestamp().__int__() * 1000 + 60_000), now=NOW)


def test_closed_candle_must_have_ended() -> None:
    current_boundary = (int(NOW.timestamp() * 1000) // 60_000) * 60_000
    with pytest.raises(ValueError, match="closed candle"):
        validate_kline(candle(open_time=current_boundary, is_closed=True), now=NOW)


def test_forming_candle_cannot_have_ended() -> None:
    with pytest.raises(ValueError, match="ended candle"):
        validate_kline(candle(open_time=600_000, is_closed=False), now=NOW)


def test_ohlc_and_volume_invariants_are_fail_closed() -> None:
    with pytest.raises(ValueError, match="high"):
        validate_kline(candle(high=Decimal(103)), now=NOW)
    with pytest.raises(ValueError, match="low"):
        validate_kline(candle(low=Decimal(105)), now=NOW)
    with pytest.raises(ValueError, match="non-negative"):
        validate_kline(candle(volume=Decimal(-1)), now=NOW)
    with pytest.raises(ValueError, match="positive"):
        validate_kline(candle(open=Decimal(0)), now=NOW)


def test_unique_constraint_matches_domain_key() -> None:
    table = cast(Table, Kline.__table__)
    constraints = {constraint for constraint in table.constraints if constraint.name == "uq_market_kline_candle"}
    assert len(constraints) == 1
    constraint = cast(UniqueConstraint, next(iter(constraints)))
    assert {column.name for column in constraint.columns} == {"market", "symbol", "interval", "open_time"}
