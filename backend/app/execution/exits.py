"""Persistent conditional exits with market-specific Binance order mapping."""
from dataclasses import dataclass
from decimal import Decimal

from backend.app.adapters.base import Market


@dataclass(frozen=True)
class ExitTrigger:
    plan_id: str
    kind: str
    trigger_price: Decimal
    quantity: Decimal
    client_request_id: str


def validate_exit(kind: str, position_side: str, trigger_price: Decimal, mark_price: Decimal, quantity: Decimal) -> None:
    kind, position_side = kind.upper(), position_side.upper()
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
    kind, position_side = kind.upper(), position_side.upper()
    if kind not in {"TP", "SL"} or position_side not in {"LONG", "SHORT"}:
        raise ValueError("unsupported TP/SL request")
    if quantity <= 0 or trigger_price <= 0 or not client_request_id:
        raise ValueError("invalid TP/SL request")
    return {"side": "SELL" if position_side == "LONG" else "BUY", "quantity": quantity, "stop_price": trigger_price, "reduce_only": True, "client_order_id": client_request_id, "kind": kind}


def binance_exit_order(kind: str, position_side: str, market: Market, quantity: Decimal, trigger_price: Decimal, client_request_id: str) -> dict:
    """Return an exchange-native conditional order specification; never submits it."""
    base = exit_order_request(kind, position_side, quantity, trigger_price, client_request_id)
    kind = kind.upper()
    if market in (Market.SPOT, Market.CROSS_MARGIN, Market.ISOLATED_MARGIN):
        order_type = "STOP_LOSS_LIMIT" if kind == "SL" else "TAKE_PROFIT_LIMIT"
        return {**base, "order_type": order_type, "market": market.value, "requires_limit_price": True}
    if market in (Market.USDS_M, Market.COIN_M):
        return {**base, "order_type": "STOP_MARKET" if kind == "SL" else "TAKE_PROFIT_MARKET", "market": market.value, "requires_limit_price": False}
    raise ValueError("unsupported market for Binance TP/SL")


def should_trigger(kind: str, mark: Decimal, trigger: Decimal, side: str) -> bool:
    if kind in {"TP", "TRAILING"}:
        return mark >= trigger if side == "SELL" else mark <= trigger
    return mark <= trigger if side == "SELL" else mark >= trigger
