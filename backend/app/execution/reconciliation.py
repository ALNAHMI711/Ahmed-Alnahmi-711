"""Reconcile Binance REST facts into the durable projection layer."""
from collections.abc import Awaitable, Callable
from decimal import Decimal
from sqlalchemy import select
from backend.app.adapters.binance import BinanceAdapter
from .models import ExchangeOrder, Trade
from .projections import apply_fill, apply_mark
from .repositories import OrderRepository, ProjectionRepository, TradeRepository

EventPublisher = Callable[[str, dict], Awaitable[None]]
class ReconciliationWorker:
    def __init__(self, session_factory, adapter_factory, publish: EventPublisher | None = None):
        self.session_factory, self.adapter_factory, self.publish = session_factory, adapter_factory, publish
    async def reconcile(self, account_id: str, market: str, symbol: str, start_time: int | None = None) -> None:
        """Safe after restart/reconnect. Events are emitted strictly after commit."""
        adapter: BinanceAdapter = self.adapter_factory(account_id, market)
        fills, funding, snapshots, mark = await self._sources(adapter, symbol, start_time)
        emitted: list[tuple[str, dict]] = []
        with self.session_factory() as db:
            trades, projections, orders = TradeRepository(db), ProjectionRepository(db), OrderRepository(db)
            for source in fills:
                fill = Trade(account_id=account_id, market=market, symbol=source.symbol, exchange_trade_id=source.trade_id, exchange_order_id=source.order_id, side=source.side, quantity=source.quantity, price=source.price, quote_quantity=source.quote_quantity, fee=source.fee, fee_asset=source.fee_asset, realized_pnl=source.realized_pnl, occurred_at=source.occurred_at)
                if trades.add_once(fill): emitted.extend((("trade", {"account_id": account_id, "trade_id": fill.exchange_trade_id, "symbol": fill.symbol}), ("execution", {"account_id": account_id, "symbol": fill.symbol, "fee": str(fill.fee)})))
                apply_fill(projections, fill)
            for payment in funding:
                if projections.add_funding_once(account_id, market, payment.symbol, payment.event_id, payment.amount, payment.occurred_at): emitted.append(("execution", {"account_id": account_id, "symbol": payment.symbol, "funding": str(payment.amount)}))
            snapshot = next((item for item in snapshots if item.symbol == symbol), None)
            position = projections.get_or_create_position(account_id, market, symbol)
            if snapshot is not None:
                position.quantity, position.average_entry_price = snapshot.quantity, snapshot.entry_price
                position.mark_price, position.unrealized_pnl = snapshot.mark_price, snapshot.unrealized_pnl
                position.state = "CLOSED" if snapshot.quantity == Decimal("0") else "OPEN"; position.version += 1
            else: apply_mark(position, mark)
            # Binance confirms lifecycle independently of fills; retries are idempotent.
            for order in db.scalars(select(ExchangeOrder).where(ExchangeOrder.account_id == account_id, ExchangeOrder.market == market, ExchangeOrder.symbol == symbol)):
                try:
                    remote = await adapter.order_status(symbol, order_id=order.exchange_order_id, client_order_id=None if order.exchange_order_id else order.client_request_id)
                    orders.update_status(order, remote["status"], str(remote.get("orderId")) if remote.get("orderId") is not None else None)
                except Exception:
                    # A transient status lookup never mutates lifecycle to a fabricated state.
                    continue
            db.commit()
            emitted.append(("position", {"account_id": account_id, "symbol": symbol, "quantity": str(position.quantity), "realized_pnl": str(position.realized_pnl), "unrealized_pnl": str(position.unrealized_pnl) if position.unrealized_pnl is not None else None}))
        if self.publish:
            for event_type, payload in emitted: await self.publish(event_type, payload)
    async def _sources(self, adapter: BinanceAdapter, symbol: str, start_time: int | None):
        return await adapter.fills(symbol, start_time), await adapter.funding(symbol, start_time), await adapter.positions(), await adapter.mark_price(symbol)
