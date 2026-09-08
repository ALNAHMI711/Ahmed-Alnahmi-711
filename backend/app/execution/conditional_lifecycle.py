"""Fail-closed lifecycle helpers for sibling TP/SL protection."""
from decimal import Decimal

ACTIVE = "ACTIVE"
SUBMITTED = "SUBMITTED"
FILLED = "FILLED"
CANCELED = "CANCELED"
REJECTED = "REJECTED"
EXPIRED = "EXPIRED"

TERMINAL = frozenset({FILLED, CANCELED, REJECTED, EXPIRED})


def sibling_action(*, filled_quantity: Decimal, position_quantity: Decimal, sibling_status: str) -> str:
    """Decide whether sibling protection should be canceled or resized.

    No exchange call is made here. The caller must reconcile the actual fill and
    actual remaining position before applying the returned action.
    """
    if filled_quantity <= 0 or position_quantity < 0:
        raise ValueError("invalid lifecycle quantities")
    if sibling_status not in {ACTIVE, SUBMITTED}:
        return "NOOP"
    if position_quantity == 0:
        return "CANCEL_SIBLING"
    if filled_quantity > position_quantity:
        raise ValueError("fill exceeds reconciled position")
    return "RESIZE_SIBLING" if filled_quantity > 0 else "NOOP"


def restart_action(status: str, exchange_order_id: str | None) -> str:
    """Never resubmit an ambiguous conditional order after restart."""
    if status == SUBMITTED and not exchange_order_id:
        return "RECONCILE_BEFORE_ACTION"
    if status == ACTIVE:
        return "RECONCILE_PLAN"
    if status in TERMINAL:
        return "NOOP"
    raise ValueError("unknown conditional order state")
