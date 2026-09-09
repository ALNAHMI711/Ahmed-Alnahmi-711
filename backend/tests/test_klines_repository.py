from collections.abc import Generator
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from app.database import Base
from app.market_data.models import Kline
from app.market_data.repository import KlineRepository
from app.market_data.schemas import KlineInterval, KlineRecord
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

NOW = datetime(2026, 1, 1, 0, 10, tzinfo=timezone.utc)


def candle(open_time: int, *, close: Decimal = Decimal(105)) -> KlineRecord:
    return KlineRecord(
        market="spot",
        symbol="btcusdt",
        interval=KlineInterval.M1,
        open_time=open_time,
        close_time=open_time + 59_999,
        open=Decimal(100),
        high=max(Decimal(110), close),
        low=min(Decimal(99), close),
        close=close,
        volume=Decimal("1.5"),
        quote_volume=Decimal("157.5"),
        trades=10,
        is_closed=True,
    )


@pytest.fixture()
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


def test_upsert_is_idempotent_and_updates_same_unique_candle(session: Session) -> None:
    repository = KlineRepository(session)
    first = repository.upsert(candle(600_000), now=NOW)
    second = repository.upsert(candle(600_000, close=Decimal(106)), now=NOW)

    assert second.id == first.id
    assert second.close == Decimal(106)
    assert session.scalar(select(func.count(Kline.id))) == 1
    assert repository.get(" spot ", "btcusdt", "1m", 600_000) is not None


def test_upsert_keeps_distinct_candles_distinct(session: Session) -> None:
    repository = KlineRepository(session)
    repository.upsert(candle(600_000), now=NOW)
    repository.upsert(candle(660_000), now=NOW)

    assert session.scalar(select(func.count(Kline.id))) == 2
    assert repository.get("SPOT", "BTCUSDT", "1m", 660_000) is not None


def test_list_range_is_ordered_bounded_and_limited(session: Session) -> None:
    repository = KlineRepository(session)
    for open_time in (600_000, 660_000, 720_000):
        repository.upsert(candle(open_time), now=NOW)

    rows = repository.list_range(
        "SPOT",
        "BTCUSDT",
        "1m",
        600_000,
        720_000,
        limit=2,
    )
    assert [row.open_time for row in rows] == [600_000, 660_000]


def test_latest_returns_newest_candle(session: Session) -> None:
    repository = KlineRepository(session)
    repository.upsert(candle(600_000), now=NOW)
    repository.upsert(candle(720_000), now=NOW)

    latest = repository.latest("SPOT", "BTCUSDT", "1m")
    assert latest is not None
    assert latest.open_time == 720_000


def test_range_rejects_invalid_bounds_and_limit(session: Session) -> None:
    repository = KlineRepository(session)
    with pytest.raises(ValueError, match="start_open_time"):
        repository.list_range("SPOT", "BTCUSDT", "1m", 720_000, 600_000)
    with pytest.raises(ValueError, match="limit"):
        repository.list_range("SPOT", "BTCUSDT", "1m", 600_000, 720_000, limit=0)
