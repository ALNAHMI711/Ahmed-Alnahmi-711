"""Projection engine for signed-average-cost positions from exchange fills."""
from decimal import Decimal
from .models import Position, Trade
from .repositories import ProjectionRepository
ZERO = Decimal("0")

def _state(quantity: Decimal) -> str: return "CLOSED" if quantity == ZERO else "OPEN"

def apply_fill(repository: ProjectionRepository, fill: Trade) -> Position | None:
    """Apply open/increase/partial close/reversal/full close exactly once.

    Fees are retained independently and also deducted from realized PnL.  The
    function receives only confirmed exchange fills; no synthetic prices exist.
    """
    event_key = f"fill:{fill.account_id}:{fill.market}:{fill.exchange_trade_id}"
    if not repository.claim_event(event_key, fill.account_id, "fill", fill.occurred_at): return None
    position = repository.get_or_create_position(fill.account_id, fill.market, fill.symbol)
    old_qty, delta = position.quantity, fill.quantity if fill.side == "BUY" else -fill.quantity
    old_entry = position.average_entry_price
    realized = ZERO
    if old_qty == ZERO or old_qty * delta > ZERO:  # open/increase
        new_qty = old_qty + delta
        if old_qty == ZERO: position.average_entry_price = fill.price
        else:
            position.average_entry_price = ((abs(old_qty) * old_entry) + (abs(delta) * fill.price)) / abs(new_qty)
    else:  # close, possibly beyond zero (reverse)
        closed = min(abs(old_qty), abs(delta))
        # long closes at sell price; short closes at buy price
        realized = (fill.price - old_entry) * closed * (Decimal("1") if old_qty > ZERO else Decimal("-1"))
        new_qty = old_qty + delta
        if new_qty == ZERO: position.average_entry_price = None
        elif new_qty * old_qty < ZERO: position.average_entry_price = fill.price
    position.quantity = new_qty
    # Persist the net PnL attributable to this individual confirmed fill.
    # Position.realized_pnl remains the cumulative projection.
    fill.realized_pnl = realized - fill.fee
    position.realized_pnl += fill.realized_pnl
    position.fees += fill.fee
    position.state = _state(new_qty)
    position.version += 1
    # A mark only exists when sourced from the exchange, so retain/compute only with it.
    if position.mark_price is not None and new_qty != ZERO:
        position.unrealized_pnl = (position.mark_price - position.average_entry_price) * new_qty
    elif new_qty == ZERO: position.unrealized_pnl = ZERO
    else: position.unrealized_pnl = None
    return position

def apply_mark(position: Position, mark_price: Decimal) -> Position:
    position.mark_price = mark_price
    position.unrealized_pnl = ZERO if position.quantity == ZERO else (mark_price - position.average_entry_price) * position.quantity
    position.version += 1
    return position
