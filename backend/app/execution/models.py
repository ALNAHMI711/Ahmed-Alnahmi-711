"""SQLAlchemy models backing exchange-confirmed execution projections."""
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base

DECIMAL = Numeric(38, 18)


def _id() -> str:
    return str(uuid4())


class Trade(Base):
    __tablename__ = "exchange_trades"
    __table_args__ = (UniqueConstraint("account_id", "market", "exchange_trade_id", name="uq_exchange_trade"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("api_accounts.id"), index=True)
    market: Mapped[str] = mapped_column(String(32), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    exchange_trade_id: Mapped[str] = mapped_column(String(96))
    exchange_order_id: Mapped[str | None] = mapped_column(String(96), nullable=True)
    side: Mapped[str] = mapped_column(String(4))
    quantity: Mapped[Decimal] = mapped_column(DECIMAL)
    price: Mapped[Decimal] = mapped_column(DECIMAL)
    quote_quantity: Mapped[Decimal] = mapped_column(DECIMAL)
    fee: Mapped[Decimal] = mapped_column(DECIMAL, default=Decimal(0))
    fee_asset: Mapped[str | None] = mapped_column(String(32), nullable=True)
    realized_pnl: Mapped[Decimal | None] = mapped_column(DECIMAL, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Position(Base):
    __tablename__ = "exchange_positions"
    __table_args__ = (UniqueConstraint("account_id", "market", "symbol", name="uq_exchange_position"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("api_accounts.id"), index=True)
    market: Mapped[str] = mapped_column(String(32), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    quantity: Mapped[Decimal] = mapped_column(DECIMAL, default=Decimal(0))
    average_entry_price: Mapped[Decimal | None] = mapped_column(DECIMAL, nullable=True)
    mark_price: Mapped[Decimal | None] = mapped_column(DECIMAL, nullable=True)
    realized_pnl: Mapped[Decimal] = mapped_column(DECIMAL, default=Decimal(0))
    unrealized_pnl: Mapped[Decimal | None] = mapped_column(DECIMAL, nullable=True)
    fees: Mapped[Decimal] = mapped_column(DECIMAL, default=Decimal(0))
    funding: Mapped[Decimal] = mapped_column(DECIMAL, default=Decimal(0))
    state: Mapped[str] = mapped_column(String(16), default="CLOSED")
    version: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProjectionEvent(Base):
    """The durable idempotency ledger for fills, funding and position snapshots."""
    __tablename__ = "projection_events"
    event_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(36), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    occurred_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ExchangeOrder(Base):
    __tablename__ = "exchange_orders"
    __table_args__ = (UniqueConstraint("account_id", "client_request_id", name="uq_exchange_order_request"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("api_accounts.id"), index=True)
    market: Mapped[str] = mapped_column(String(32))
    symbol: Mapped[str] = mapped_column(String(32))
    client_request_id: Mapped[str] = mapped_column(String(64))
    exchange_order_id: Mapped[str | None] = mapped_column(String(96), nullable=True, unique=True)
    side: Mapped[str] = mapped_column(String(4))
    order_type: Mapped[str] = mapped_column(String(32))
    quantity: Mapped[Decimal] = mapped_column(DECIMAL)
    status: Mapped[str] = mapped_column(String(24), default="NEW")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConditionalOrder(Base):
    __tablename__ = "conditional_orders"
    __table_args__ = (UniqueConstraint("account_id", "idempotency_key", name="uq_conditional_request"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("api_accounts.id"), index=True)
    position_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("exchange_positions.id"), nullable=True)
    parent_order_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("exchange_orders.id"), nullable=True)
    symbol: Mapped[str] = mapped_column(String(32))
    market: Mapped[str] = mapped_column(String(32))
    kind: Mapped[str] = mapped_column(String(16))
    side: Mapped[str] = mapped_column(String(4))
    quantity: Mapped[Decimal] = mapped_column(DECIMAL)
    trigger_price: Mapped[Decimal | None] = mapped_column(DECIMAL, nullable=True)
    trail_offset: Mapped[Decimal | None] = mapped_column(DECIMAL, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="ACTIVE")
    idempotency_key: Mapped[str] = mapped_column(String(64))
    exchange_order_id: Mapped[str | None] = mapped_column(String(96), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
