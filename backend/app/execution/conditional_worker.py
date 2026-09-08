"""DB-backed conditional executor. It uses only exchange mark prices and confirmations."""
from sqlalchemy import select
from backend.app.database import KillSwitch
from .models import ConditionalOrder
from .exits import should_trigger


class ConditionalOrderWorker:
    def __init__(self, sessions, adapter_factory, execution_submit):
        self.sessions, self.adapter_factory, self.execution_submit = sessions, adapter_factory, execution_submit

    async def run_once(self):
        with self.sessions() as db:
            if (state := db.get(KillSwitch, 'global')) and state.enabled:
                return
            plans = list(db.scalars(select(ConditionalOrder).where(ConditionalOrder.status == 'ACTIVE')))
            for plan in plans:
                adapter = self.adapter_factory(plan.account_id, plan.market)
                mark = await adapter.mark_price(plan.symbol)
                if plan.trigger_price is not None and plan.trigger_price <= 0:
                    plan.status = 'REJECTED'
                    continue
                if plan.kind == 'TRAILING' and plan.trail_offset is not None:
                    if plan.trail_offset <= 0:
                        plan.status = 'REJECTED'
                        continue
                    candidate = mark - plan.trail_offset if plan.side == 'SELL' else mark + plan.trail_offset
                    if plan.trigger_price is None or (candidate > plan.trigger_price if plan.side == 'SELL' else candidate < plan.trigger_price):
                        plan.trigger_price = candidate
                if plan.trigger_price is None or not should_trigger(plan.kind, mark, plan.trigger_price, plan.side):
                    continue
                # execution_submit must apply Risk/ExecutionService and return Binance's confirmed response.
                try:
                    remote = await self.execution_submit(plan, adapter)
                except Exception:
                    # Unknown submission is never converted into a fabricated success.
                    continue
                exchange_order_id = remote.get('orderId')
                if exchange_order_id is None:
                    # A response without an exchange order id is not a confirmed order.
                    continue
                plan.exchange_order_id = str(exchange_order_id)
                plan.status = 'SUBMITTED'
            db.commit()
