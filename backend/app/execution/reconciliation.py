"""Reconcile exchange facts into durable projections; fail closed on ambiguity."""
from collections.abc import Awaitable, Callable
from decimal import Decimal
import httpx
from sqlalchemy import select
from backend.app.adapters.binance import BinanceAdapter
from .models import ConditionalOrder, ExchangeOrder, Trade
from .projections import apply_fill, apply_mark
from .repositories import OrderRepository, ProjectionRepository, TradeRepository

EventPublisher = Callable[[str, dict], Awaitable[None]]
_TERMINAL = frozenset({"FILLED", "CANCELED", "REJECTED", "EXPIRED"})

class ReconciliationWorker:
    def __init__(self, session_factory, adapter_factory, publish: EventPublisher | None = None):
        self.session_factory, self.adapter_factory, self.publish = session_factory, adapter_factory, publish

    async def reconcile(self, account_id: str, market: str, symbol: str, start_time: int | None = None) -> None:
        """Restart-safe reconciliation. Never turns an unknown exchange result into success."""
        adapter: BinanceAdapter = self.adapter_factory(account_id, market)
        fills, funding, snapshots, mark = await self._sources(adapter, symbol, start_time)
        emitted: list[tuple[str, dict]] = []
        with self.session_factory() as db:
            trades, projections, orders = TradeRepository(db), ProjectionRepository(db), OrderRepository(db)
            for source in fills:
                fill = Trade(account_id=account_id, market=market, symbol=source.symbol, exchange_trade_id=source.trade_id, exchange_order_id=source.order_id, side=source.side, quantity=source.quantity, price=source.price, quote_quantity=source.quote_quantity, fee=source.fee, fee_asset=source.fee_asset, realized_pnl=source.realized_pnl, occurred_at=source.occurred_at)
                if trades.add_once(fill):
                    emitted.extend((("trade", {"account_id": account_id, "trade_id": fill.exchange_trade_id, "symbol": fill.symbol}), ("execution", {"account_id": account_id, "symbol": fill.symbol, "fee": str(fill.fee)})))
                apply_fill(projections, fill)
            for payment in funding:
                if projections.add_funding_once(account_id, market, payment.symbol, payment.event_id, payment.amount, payment.occurred_at):
                    emitted.append(("execution", {"account_id": account_id, "symbol": payment.symbol, "funding": str(payment.amount)}))
            snapshot = next((item for item in snapshots if item.symbol == symbol), None)
            position = projections.get_or_create_position(account_id, market, symbol)
            if snapshot is not None:
                position.quantity, position.average_entry_price = snapshot.quantity, snapshot.entry_price
                position.mark_price, position.unrealized_pnl = snapshot.mark_price, snapshot.unrealized_pnl
                position.state = "CLOSED" if snapshot.quantity == Decimal("0") else "OPEN"
                position.version += 1
            else:
                apply_mark(position, mark)

            exchange_orders = list(db.scalars(select(ExchangeOrder).where(ExchangeOrder.account_id == account_id, ExchangeOrder.market == market, ExchangeOrder.symbol == symbol)))
            for order in exchange_orders:
                try:
                    remote = await adapter.order_status(symbol, order_id=order.exchange_order_id, client_order_id=None if order.exchange_order_id else order.client_request_id)
                except (httpx.HTTPError, ValueError, KeyError, TypeError, RuntimeError):
                    if order.status not in _TERMINAL:
                        orders.update_status(order, "UNKNOWN")
                    continue
                remote_status = remote.get("status")
                if remote_status not in {"NEW", "PARTIALLY_FILLED", "FILLED", "CANCELED", "REJECTED", "EXPIRED"}:
                    if order.status not in _TERMINAL: orders.update_status(order, "UNKNOWN")
                    continue
                orders.update_status(order, remote_status, str(remote.get("orderId")) if remote.get("orderId") is not None else None)
                if remote_status == "FILLED":
                    await self._reconcile_exit_siblings(db, adapter, order, position, emitted)

            plans = list(db.scalars(select(ConditionalOrder).where(
                ConditionalOrder.account_id == account_id,
                ConditionalOrder.market == market,
                ConditionalOrder.symbol == symbol,
                ConditionalOrder.status.in_(["SUBMITTED", "UNKNOWN"]),
            )))
            for plan in plans:
                if not plan.exchange_order_id:
                    plan.status = "UNKNOWN"
                    continue
                try:
                    remote = await adapter.order_status(symbol, order_id=plan.exchange_order_id)
                except (httpx.HTTPError, ValueError, KeyError, TypeError, RuntimeError):
                    plan.status = "UNKNOWN"
                    continue
                status = remote.get("status")
                if status == "PARTIALLY_FILLED":
                    plan.status = "PARTIALLY_FILLED"
                    emitted.append(("execution", {"account_id": account_id, "symbol": symbol, "event": "conditional_partial_fill", "conditional_id": plan.id, "executed_quantity": str(remote.get("executedQty", "0"))}))
                elif status in _TERMINAL:
                    plan.status = status
                    if status == "FILLED":
                        await self._reconcile_conditional_siblings(db, adapter, plan, position, emitted)
                elif status in {"NEW", "UNKNOWN"}:
                    plan.status = "SUBMITTED" if status == "NEW" else "UNKNOWN"
                else:
                    plan.status = "UNKNOWN"

            db.commit()
            emitted.append(("position", {"account_id": account_id, "symbol": symbol, "quantity": str(position.quantity), "realized_pnl": str(position.realized_pnl), "unrealized_pnl": str(position.unrealized_pnl) if position.unrealized_pnl is not None else None}))
        if self.publish:
            for event_type, payload in emitted:
                await self.publish(event_type, payload)

    async def _reconcile_exit_siblings(self, db, adapter: BinanceAdapter, filled_order: ExchangeOrder, position, emitted) -> None:
        plan = db.scalar(select(ConditionalOrder).where(ConditionalOrder.parent_order_id == filled_order.id))
        if plan is not None:
            await self._reconcile_conditional_siblings(db, adapter, plan, position, emitted)

    async def _reconcile_conditional_siblings(self, db, adapter, filled_plan, position, emitted) -> None:
        siblings = list(db.scalars(select(ConditionalOrder).where(
            ConditionalOrder.position_id == filled_plan.position_id,
            ConditionalOrder.id != filled_plan.id,
            ConditionalOrder.status.in_(["ACTIVE", "SUBMITTED", "PARTIALLY_FILLED", "UNKNOWN"]),
        ))) if filled_plan.position_id else []
        remaining = abs(position.quantity)
        for sibling in siblings:
            if remaining and sibling.quantity <= remaining and sibling.status != "UNKNOWN":
                continue
            if not sibling.exchange_order_id:
                sibling.status = "UNKNOWN"
                continue
            try:
                response = await adapter.cancel_order(symbol=sibling.symbol, order_id=sibling.exchange_order_id)
            except (httpx.HTTPError, ValueError, KeyError, TypeError, RuntimeError):
                sibling.status = "UNKNOWN"
                continue
            if response.get("status") == "CANCELED":
                sibling.status = "CANCELED"
                emitted.append(("execution", {"account_id": filled_plan.account_id, "symbol": sibling.symbol, "event": "sibling_protection_canceled", "conditional_id": sibling.id}))
            else:
                sibling.status = "UNKNOWN"

    async def _sources(self, adapter: BinanceAdapter, symbol: str, start_time: int | None):
        return await adapter.fills(symbol, start_time), await adapter.funding(symbol, start_time), await adapter.positions(), await adapter.mark_price(symbol)
