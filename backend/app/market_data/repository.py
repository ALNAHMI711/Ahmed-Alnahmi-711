"""Persistence operations for validated market candles."""
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from .models import Kline
from .schemas import KlineRecord
from .validation import validate_kline


class KlineRepository:
    """Idempotent candle persistence and bounded chronological queries."""

    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _values(kline: KlineRecord) -> dict[str, object]:
        return {
            "market": kline.market,
            "symbol": kline.symbol,
            "interval": kline.interval.value,
            "open_time": kline.open_time,
            "close_time": kline.close_time,
            "open": kline.open,
            "high": kline.high,
            "low": kline.low,
            "close": kline.close,
            "volume": kline.volume,
            "quote_volume": kline.quote_volume,
            "trades": kline.trades,
            "is_closed": kline.is_closed,
            "source": kline.source,
        }

    def upsert(self, kline: KlineRecord, *, now: datetime | int | None = None) -> Kline:
        """Validate and insert/update one candle using the domain uniqueness key."""
        validated = validate_kline(kline, now=now)
        values = self._values(validated)
        dialect = self.session.bind.dialect.name if self.session.bind is not None else ""

        if dialect == "postgresql":
            return self._native_upsert(pg_insert(Kline).values(**values), values)
        if dialect == "sqlite":
            return self._native_upsert(sqlite_insert(Kline).values(**values), values)
        return self._fallback_upsert(validated)

    def _native_upsert(self, statement: Any, values: dict[str, object]) -> Kline:
        """Execute a dialect-specific ON CONFLICT upsert and return its row."""
        update_values = {
            key: statement.excluded[key]
            for key in values
            if key not in {"market", "symbol", "interval", "open_time"}
        }
        conflict_statement = statement.on_conflict_do_update(
            index_elements=["market", "symbol", "interval", "open_time"],
            set_=update_values,
        ).returning(Kline.id)
        row_id = self.session.execute(conflict_statement).scalar_one()
        self.session.flush()
        row = self.session.get(Kline, row_id)
        if row is None:
            raise RuntimeError("Kline upsert returned no persisted row")
        self.session.refresh(row)
        return row

    def _fallback_upsert(self, kline: KlineRecord) -> Kline:
        """Portable fallback for dialects without native conflict handling."""
        filters = self._key_filters(kline)
        existing = self.session.scalar(select(Kline).filter_by(**filters))
        values = self._values(kline)
        if existing is None:
            existing = Kline(**values)
            self.session.add(existing)
        else:
            for key, value in values.items():
                setattr(existing, key, value)
        self.session.flush()
        return existing

    @staticmethod
    def _key_filters(kline: KlineRecord) -> dict[str, object]:
        return {
            "market": kline.market,
            "symbol": kline.symbol,
            "interval": kline.interval.value,
            "open_time": kline.open_time,
        }

    def get(
        self,
        market: str,
        symbol: str,
        interval: str,
        open_time: int,
    ) -> Kline | None:
        """Fetch one candle by its complete uniqueness key."""
        return self.session.scalar(
            select(Kline).filter_by(
                market=market.strip().upper(),
                symbol=symbol.strip().upper(),
                interval=interval,
                open_time=open_time,
            )
        )

    def list_range(
        self,
        market: str,
        symbol: str,
        interval: str,
        start_open_time: int,
        end_open_time: int,
        *,
        limit: int = 1_000,
    ) -> Sequence[Kline]:
        """Return candles in ascending open-time order within a bounded range."""
        if start_open_time > end_open_time:
            raise ValueError("start_open_time must not exceed end_open_time")
        if limit < 1:
            raise ValueError("limit must be positive")
        statement: Select[tuple[Kline]] = (
            select(Kline)
            .where(
                Kline.market == market.strip().upper(),
                Kline.symbol == symbol.strip().upper(),
                Kline.interval == interval,
                Kline.open_time >= start_open_time,
                Kline.open_time <= end_open_time,
            )
            .order_by(Kline.open_time.asc())
            .limit(limit)
        )
        return self.session.scalars(statement).all()

    def latest(
        self,
        market: str,
        symbol: str,
        interval: str,
    ) -> Kline | None:
        """Return the newest stored candle for a market/symbol/interval."""
        statement = (
            select(Kline)
            .where(
                Kline.market == market.strip().upper(),
                Kline.symbol == symbol.strip().upper(),
                Kline.interval == interval,
            )
            .order_by(Kline.open_time.desc())
            .limit(1)
        )
        return self.session.scalar(statement)
