"""Authoritative server-side risk context built from persisted projections."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from decimal import Decimal
from sqlalchemy import select

from backend.app.execution.models import Position, Trade

ZERO = Decimal("0")


@dataclass(frozen=True)
class RiskSnapshot:
    daily_loss: float
    drawdown: float
    open_positions: int
    exposure: float
    position_size: float
    leverage: float
    spread: float
    slippage: float
    kill_switch: bool


def _start_of_day() -> datetime:
    now = datetime.utcnow()
    return datetime.combine(now.date(), time.min)


def build_snapshot(
    db,
    *,
    account_id: str,
    symbol: str,
    requested_quantity: Decimal,
    mark_price: Decimal,
    wallet_equity: Decimal | None = None,
    spread: Decimal = ZERO,
    slippage: Decimal = ZERO,
    kill_switch: bool = False,
) -> RiskSnapshot:
    """Build risk inputs exclusively from server-side state.

    Client supplied risk metrics are intentionally not accepted here.
    """

    positions = list(
        db.scalars(
            select(Position).where(
                Position.account_id == account_id,
                Position.state == "OPEN",
            )
        )
    )

    open_positions = sum(
        1 for position in positions if position.quantity != ZERO
    )

    exposure = ZERO
    for p in positions:
        if p.mark_price is not None:
            exposure += abs(p.quantity * p.mark_price)

    requested_notional = abs(requested_quantity * mark_price)

    projected_exposure = exposure + requested_notional

    account_trades = list(
        db.scalars(
            select(Trade).where(
                Trade.account_id == account_id,
                Trade.occurred_at >= _start_of_day(),
            )
        )
    )

    daily_realized = sum(
        (trade.realized_pnl or ZERO)
        for trade in account_trades
    )

    daily_loss = max(ZERO, -daily_realized)

    # Until an authoritative historical equity peak exists, drawdown is
    # conservatively derived from current equity versus zero only when
    # equity is explicitly available. Otherwise it remains zero rather
    # than accepting a client supplied value.
    drawdown = ZERO

    if wallet_equity is not None and wallet_equity > ZERO:
        current_equity = wallet_equity + sum(
            (position.unrealized_pnl or ZERO)
            + position.realized_pnl
            - position.fees
            + position.funding
            for position in positions
        )
        if current_equity < ZERO:
            drawdown = abs(current_equity) / wallet_equity

    leverage = (
        projected_exposure / wallet_equity
        if wallet_equity is not None and wallet_equity > ZERO
        else ZERO
    )

    return RiskSnapshot(
        daily_loss=float(daily_loss),
        drawdown=float(drawdown),
        open_positions=open_positions,
        exposure=float(projected_exposure),
        position_size=float(requested_notional),
        leverage=float(leverage),
        spread=float(spread),
        slippage=float(slippage),
        kill_switch=kill_switch,
    )

