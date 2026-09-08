"""Mandatory risk/confirmation gate for real Binance order submissions."""
from dataclasses import dataclass
from decimal import Decimal

from backend.app.adapters.binance import BinanceAdapter
from risk.engine import RiskDecision

@dataclass(frozen=True)
class OrderIntent:
    account_id: str; client_request_id: str; symbol: str; side: str; quantity: Decimal; order_type: str = "MARKET"; price: Decimal | None = None; reduce_only: bool = False
class ExecutionRejected(RuntimeError): pass
class ExecutionService:
    async def submit(self, adapter: BinanceAdapter, intent: OrderIntent, decision: RiskDecision, *, confirmed: bool, kill_switch: bool) -> dict:
        if kill_switch: raise ExecutionRejected("kill switch enabled")
        if not decision.approved: raise ExecutionRejected("risk rejected: " + "; ".join(decision.reasons))
        if not confirmed: raise ExecutionRejected("human confirmation required")
        # Deterministic client ID permits exchange-side duplicate prevention/recovery.
        client_id = f"tp-{intent.account_id[:8]}-{intent.client_request_id[:20]}"
        response = await adapter.place_order(intent.symbol, intent.side, intent.order_type, intent.quantity, price=intent.price, client_order_id=client_id, reduce_only=intent.reduce_only)
        if response.get("status") not in {"NEW", "PARTIALLY_FILLED", "FILLED"}: raise ExecutionRejected("exchange did not confirm accepted order")
        return response
