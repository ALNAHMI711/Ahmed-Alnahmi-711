"""Projection engine for signed-average-cost positions from exchange fills."""
from decimal import Decimal

from .models import Position, Trade
from .repositories import ProjectionRepository

ZERO = Decimal("0")
ONE = Decimal("1")


def _decimal_or_zero(value: Decimal | None) -> Decimal:
    """Return a Decimal value while tolerating SQLAlchemy constructor defaults."""
    return ZERO if value is None else value


def _state(quantity: Decimal) -> str:
    return "CLOSED" if quantity == ZERO else "OPEN"


def apply_fill(repository: ProjectionRepository, fill: Trade) -> Position | None:
    """Apply open/increase/partial close/reversal/full close exactly once.

    Fees are retained independently and also deducted from realized PnL. The
    function receives only confirmed exchange fills; no synthetic prices exist.
    """
    event_key = f"fill:{fill.account_id}:{fill.market}:{fill.exchange_trade_id}"
    if not repository.claim_event(event_key, fill.account_id, "fill", fill.occurred_at):
        return None

    position = repository.get_or_create_position(fill.account_id, fill.market, fill.symbol)
    # SQLAlchemy ``default=...`` values are applied at INSERT/flush time, not
    # necessarily when a model is constructed in memory. Normalize every
    # numeric position field used in arithmetic at the projection boundary.
    old_qty = _decimal_or_zero(position.quantity)
    old_realized = _decimal_or_zero(position.realized_pnl)
    old_fees = _decimal_or_zero(position.fees)
    old_funding = _decimal_or_zero(position.funding)
    delta = fill.quantity if fill.side == "BUY" else -fill.quantity
    old_entry = position.average_entry_price
    realized = ZERO

    if old_qty == ZERO or old_qty * delta > ZERO:  # open/increase
        new_qty = old_qty + delta
        if old_qty == ZERO:
            position.average_entry_price = fill.price
        else:
            if old_entry is None:
                raise ValueError("position average entry price is required for an open position")
            position.average_entry_price = (
                (abs(old_qty) * old_entry) + (abs(delta) * fill.price)
            ) / abs(new_qty)
    else:  # close, possibly beyond zero (reverse)
        if old_entry is None:
            raise ValueError("position average entry price is required for a closing fill")
        closed = min(abs(old_qty), abs(delta))
        # long closes at sell price; short closes at buy price
        realized = (
            (fill.price - old_entry)
            * closed
            * (ONE if old_qty > ZERO else -ONE)
        )
        new_qty = old_qty + delta
        if new_qty == ZERO:
            position.average_entry_price = None
        elif new_qty * old_qty < ZERO:
            position.average_entry_price = fill.price

    position.quantity = new_qty
    position.realized_pnl = old_realized + realized - _decimal_or_zero(fill.fee)
    position.fees = old_fees + _decimal_or_zero(fill.fee)
    position.funding = old_funding
    position.state = _state(new_qty)
    position.version = int(position.version or 0) + 1
    # A mark only exists when sourced from the exchange, so retain/compute only with it.
    if position.mark_price is not None and new_qty != ZERO:
        if position.average_entry_price is None:
            raise ValueError("position average entry price is required for unrealized PnL")
        position.unrealized_pnl = (
            position.mark_price - position.average_entry_price
        ) * new_qty
    elif new_qty == ZERO:
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
    if quantity == ZERO:
        position.unrealized_pnl = ZERO
    else:
        if position.average_entry_price is None:
            raise ValueError("position average entry price is required for an open position")
        position.unrealized_pnl = (mark_price - position.average_entry_price) * quantity
    position.version = int(position.version or 0) + 1
    return position
