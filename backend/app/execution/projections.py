"""Projection engine for signed-average-cost positions from exchange fills."""
from decimal import Decimal, localcontext

from .models import Position, Trade
from .repositories import ProjectionRepository

ZERO = Decimal(0)
ONE = Decimal(1)
PNL_SCALE = Decimal("1e-18")


def _decimal_or_zero(value: Decimal | None) -> Decimal:
    """Return a Decimal value while tolerating SQLAlchemy constructor defaults."""
    return ZERO if value is None else value


def _state(quantity: Decimal) -> str:
    return "CLOSED" if quantity == ZERO else "OPEN"


def _aggregate_fills(fills: list[Trade]) -> tuple[Decimal, Decimal | None, Decimal, Decimal]:
    """Rebuild quantity, average entry, gross realized PnL and fees exactly."""
    quantity = ZERO
    average_entry: Decimal | None = None
    gross_realized = ZERO
    fees = ZERO
    with localcontext() as context:
        context.prec = 60
        for fill in fills:
            delta = fill.quantity if fill.side == "BUY" else -fill.quantity
            fees += _decimal_or_zero(fill.fee)
            if quantity == ZERO or quantity * delta > ZERO:
                new_quantity = quantity + delta
                if quantity == ZERO:
                    average_entry = fill.price
                else:
                    if average_entry is None:
                        raise ValueError("position average entry price is required for an open position")
                    average_entry = ((abs(quantity) * average_entry) + (abs(delta) * fill.price)) / abs(new_quantity)
            else:
                if average_entry is None:
                    raise ValueError("position average entry price is required for a closing fill")
                closed = min(abs(quantity), abs(delta))
                gross_realized += (fill.price - average_entry) * closed * (ONE if quantity > ZERO else -ONE)
                new_quantity = quantity + delta
                if new_quantity == ZERO:
                    average_entry = None
                elif new_quantity * quantity < ZERO:
                    average_entry = fill.price
            quantity = new_quantity
    return quantity, average_entry, gross_realized, fees


def apply_fill(repository: ProjectionRepository, fill: Trade) -> Position | None:
    """Apply confirmed exchange fills with exact cumulative accounting."""
    event_key = f"fill:{fill.account_id}:{fill.market}:{fill.exchange_trade_id}"
    if not repository.claim_event(event_key, fill.account_id, "fill", fill.occurred_at):
        return None
    position = repository.get_or_create_position(fill.account_id, fill.market, fill.symbol)
    fills = repository.fills_for_position(fill.account_id, fill.market, fill.symbol, fill)
    quantity, average_entry, gross_realized, fees = _aggregate_fills(fills)
    funding = _decimal_or_zero(position.funding)
    position.quantity = quantity
    position.average_entry_price = average_entry
    with localcontext() as context:
        context.prec = 60
        position.realized_pnl = (funding + gross_realized - fees).quantize(PNL_SCALE)
        position.fees = fees.quantize(PNL_SCALE)
    position.state = _state(quantity)
    position.version = int(position.version or 0) + 1
    if position.mark_price is not None and quantity != ZERO:
        if average_entry is None:
            raise ValueError("position average entry price is required for unrealized PnL")
        with localcontext() as context:
            context.prec = 60
            position.unrealized_pnl = (position.mark_price - average_entry) * quantity
    elif quantity == ZERO:
        position.unrealized_pnl = ZERO
    else:
        position.unrealized_pnl = None
    return position


def apply_mark(position: Position, mark_price: Decimal) -> Position:
    """Apply an exchange-sourced mark price to an existing position."""
    quantity = _decimal_or_zero(position.quantity)
    position.quantity = quantity
    position.realized_pnl = _decimal_or_zero(position.realized_pnl)
    position.fees = _decimal_or_zero(position.fees)
    position.funding = _decimal_or_zero(position.funding)
    position.mark_price = mark_price
    with localcontext() as context:
        context.prec = 60
        if quantity == ZERO:
            position.unrealized_pnl = ZERO
        else:
            if position.average_entry_price is None:
                raise ValueError("position average entry price is required for an open position")
            position.unrealized_pnl = (mark_price - position.average_entry_price) * quantity
    position.version = int(position.version or 0) + 1
    return position
