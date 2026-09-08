"""Persistent conditional exit plans; submission is always fail-closed."""
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ExitTrigger:
    plan_id: str
    kind: str
    trigger_price: Decimal
    quantity: Decimal
    client_request_id: str


def validate_exit(kind: str, position_side: str, trigger_price: Decimal, mark_price: Decimal, quantity: Decimal) -> None:
    kind = kind.upper()
    position_side = position_side.upper()
    if kind not in {"TP", "SL", "TRAILING"}:
        raise ValueError("unsupported exit kind")
    if position_side not in {"LONG", "SHORT"}:
        raise ValueError("position_side must be LONG or SHORT")
    if trigger_price <= 0 or mark_price <= 0 or quantity <= 0:
        raise ValueError("exit price and quantity must be positive")
    if kind == "TP":
        valid = trigger_price > mark_price if position_side == "LONG" else trigger_price < mark_price
    elif kind == "SL":
        valid = trigger_price < mark_price if position_side == "LONG" else trigger_price > mark_price
    else:
        valid = True
    if not valid:
        raise ValueError("exit trigger is on the unsafe side of the current mark")


def exit_order_request(kind: str, position_side: str, quantity: Decimal, trigger_price: Decimal, client_request_id: str) -> dict:
    """Build a reduce-only conditional request without claiming exchange acceptance.

    The caller must map the conditional kind to a Binance-supported order type for
    the selected market and only transition the plan after Binance confirms it.
    """
    kind = kind.upper()
    position_side = position_side.upper()
    if kind not in {"TP", "SL"} or position_side not in {"LONG", "SHORT"}:
        raise ValueError("unsupported TP/SL request")
    if quantity <= 0 or trigger_price <= 0 or not client_request_id:
        raise ValueError("invalid TP/SL request")
    side = "SELL" if position_side == "LONG" else "BUY"
    return {
        "side": side,
        "quantity": quantity,
        "stop_price": trigger_price,
        "reduce_only": True,
        "client_order_id": client_request_id,
        "kind": kind,
    }


def should_trigger(kind: str, mark: Decimal, trigger: Decimal, side: str) -> bool:
    if kind in {'TP','TRAILING'}: return mark >= trigger if side == 'SELL' else mark <= trigger
    return mark <= trigger if side == 'SELL' else mark >= trigger
