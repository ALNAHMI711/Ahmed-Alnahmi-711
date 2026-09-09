"""SQLAlchemy persistence model for market candles, isolated from execution ledger models."""
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base

KLINE_DECIMAL = Numeric(60, 30)
KLINE_ID = BigInteger().with_variant(Integer(), "sqlite")


class Kline(Base):
    __tablename__ = "market_klines"
    __table_args__ = (
        UniqueConstraint(
            "market",
            "symbol",
            "interval",
            "open_time",
            name="uq_market_kline_candle",
        ),
    )

    id: Mapped[int] = mapped_column(KLINE_ID, primary_key=True, autoincrement=True)
    market: Mapped[str] = mapped_column(String(32), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    interval: Mapped[str] = mapped_column(String(8), index=True)
    open_time: Mapped[int] = mapped_column(BigInteger, index=True)
    close_time: Mapped[int] = mapped_column(BigInteger)
    open: Mapped[Decimal] = mapped_column(KLINE_DECIMAL)
    high: Mapped[Decimal] = mapped_column(KLINE_DECIMAL)
    low: Mapped[Decimal] = mapped_column(KLINE_DECIMAL)
    close: Mapped[Decimal] = mapped_column(KLINE_DECIMAL)
    volume: Mapped[Decimal] = mapped_column(KLINE_DECIMAL)
    quote_volume: Mapped[Decimal] = mapped_column(KLINE_DECIMAL, default=Decimal(0))
    trades: Mapped[int] = mapped_column(BigInteger, default=0)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(64), default="binance")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
    )
