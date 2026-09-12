"""DB-backed conditional executor with fail-closed risk and reconciliation lifecycle."""
import logging

import httpx
from sqlalchemy import select

from backend.app.database import KillSwitch

from .exits import should_trigger
from .models import ConditionalOrder, Position

logger = logging.getLogger(__name__)


class ConditionalOrderWorker:
    def __init__(self, sessions, adapter_factory, execution_submit):
        self.sessions, self.adapter_factory, self.execution_submit = sessions, adapter_factory, execution_submit

    @staticmethod
    def _risk_allows(plan: ConditionalOrder, position: Position | None) -> bool:
        if position is None or position.state != "OPEN":
            return False
        if position.quantity == 0 or plan.quantity <= 0:
            return False
        return plan.quantity <= abs(position.quantity)

    async def run_once(self):
        with self.sessions() as db:
            if (state := db.get(KillSwitch, "global")) and state.enabled:
                return
            plans = list(db.scalars(select(ConditionalOrder).where(ConditionalOrder.status == "ACTIVE")))
            for plan in plans:
                position = db.get(Position, plan.position_id) if plan.position_id else None
                if not self._risk_allows(plan, position):
                    plan.status = "REJECTED"
                    continue
                adapter = self.adapter_factory(plan.account_id, plan.market)
                try:
                    mark = await adapter.mark_price(plan.symbol)
                except (httpx.HTTPError, ValueError, KeyError, TypeError, RuntimeError) as error:
                    logger.warning("conditional mark lookup failed for %s: %s", plan.symbol, error, exc_info=True)
                    continue
                if plan.trigger_price is not None and plan.trigger_price <= 0:
                    plan.status = "REJECTED"
                    continue
                if plan.kind == "TRAILING" and plan.trail_offset is not None:
                    if plan.trail_offset <= 0:
                        plan.status = "REJECTED"
                        continue
                    candidate = mark - plan.trail_offset if plan.side == "SELL" else mark + plan.trail_offset
                    if plan.trigger_price is None or (candidate > plan.trigger_price if plan.side == "SELL" else candidate < plan.trigger_price):
                        plan.trigger_price = candidate
                if plan.trigger_price is None or not should_trigger(plan.kind, mark, plan.trigger_price, plan.side):
                    continue
                try:
                    remote = await self.execution_submit(plan, adapter)
                except (httpx.HTTPError, ValueError, KeyError, TypeError, RuntimeError) as error:
                    logger.warning("conditional order submission failed for %s: %s", plan.symbol, error, exc_info=True)
                    continue
                exchange_order_id = remote.get("orderId")
                if exchange_order_id is None:
                    continue
                plan.exchange_order_id = str(exchange_order_id)
                plan.status = "SUBMITTED"
            db.commit()
