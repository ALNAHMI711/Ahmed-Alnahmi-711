from decimal import Decimal
import pytest
from backend.app.execution.models import ConditionalOrder, ExchangeOrder, Position
from backend.app.execution.reconciliation import ReconciliationWorker

class _Result:
    def __init__(self, rows): self.rows = rows
    def __iter__(self): return iter(self.rows)

class _DB:
    def __init__(self, plan, siblings): self.plan, self.siblings = plan, siblings
    def scalar(self, _query): return self.plan
    def scalars(self, _query): return _Result(self.siblings)

class _Adapter:
    def __init__(self, response): self.response = response; self.calls = []
    async def cancel_order(self, **kwargs):
        self.calls.append(kwargs)
        return self.response

@pytest.mark.asyncio
async def test_full_fill_cancels_exchange_confirmed_sibling():
    filled = ExchangeOrder(account_id="a", market="USDS_M", symbol="BTCUSDT", client_request_id="x", side="SELL", order_type="STOP_MARKET", quantity=Decimal("1"))
    filled.id = "parent"
    plan = ConditionalOrder(account_id="a", market="USDS_M", symbol="BTCUSDT", kind="SL", side="SELL", quantity=Decimal("1"), idempotency_key="sl", position_id="p", parent_order_id="parent")
    sibling = ConditionalOrder(account_id="a", market="USDS_M", symbol="BTCUSDT", kind="TP1", side="SELL", quantity=Decimal("1"), idempotency_key="tp", position_id="p", status="SUBMITTED", exchange_order_id="77")
    db = _DB(plan, [sibling])
    adapter = _Adapter({"status": "CANCELED", "orderId": "77"})
    position = Position(account_id="a", market="USDS_M", symbol="BTCUSDT", quantity=Decimal("0"))
    worker = ReconciliationWorker(lambda: None, lambda *_: adapter)
    emitted = []
    await worker._reconcile_exit_siblings(db, adapter, filled, position, emitted)
    assert sibling.status == "CANCELED"
    assert adapter.calls == [{"symbol": "BTCUSDT", "order_id": "77"}]

@pytest.mark.asyncio
async def test_partial_fill_cancels_oversized_sibling_without_replacement():
    filled = ExchangeOrder(account_id="a", market="USDS_M", symbol="BTCUSDT", client_request_id="x", side="SELL", order_type="TAKE_PROFIT_MARKET", quantity=Decimal("1"))
    filled.id = "parent"
    plan = ConditionalOrder(account_id="a", market="USDS_M", symbol="BTCUSDT", kind="TP1", side="SELL", quantity=Decimal("0.6"), idempotency_key="tp1", position_id="p", parent_order_id="parent")
    sibling = ConditionalOrder(account_id="a", market="USDS_M", symbol="BTCUSDT", kind="SL", side="SELL", quantity=Decimal("1"), idempotency_key="sl", position_id="p", status="SUBMITTED", exchange_order_id="88")
    db = _DB(plan, [sibling])
    adapter = _Adapter({"status": "CANCELED", "orderId": "88"})
    position = Position(account_id="a", market="USDS_M", symbol="BTCUSDT", quantity=Decimal("0.4"))
    worker = ReconciliationWorker(lambda: None, lambda *_: adapter)
    emitted = []
    await worker._reconcile_exit_siblings(db, adapter, filled, position, emitted)
    assert sibling.status == "CANCELED"
    assert adapter.calls[0]["order_id"] == "88"

@pytest.mark.asyncio
async def test_cancel_failure_does_not_fabricate_sibling_canceled():
    filled = ExchangeOrder(account_id="a", market="USDS_M", symbol="BTCUSDT", client_request_id="x", side="SELL", order_type="STOP_MARKET", quantity=Decimal("1"))
    filled.id = "parent"
    plan = ConditionalOrder(account_id="a", market="USDS_M", symbol="BTCUSDT", kind="SL", side="SELL", quantity=Decimal("1"), idempotency_key="sl", position_id="p", parent_order_id="parent")
    sibling = ConditionalOrder(account_id="a", market="USDS_M", symbol="BTCUSDT", kind="TP1", side="SELL", quantity=Decimal("1"), idempotency_key="tp", position_id="p", status="SUBMITTED", exchange_order_id="99")
    db = _DB(plan, [sibling])
    adapter = _Adapter({"status": "NEW", "orderId": "99"})
    worker = ReconciliationWorker(lambda: None, lambda *_: adapter)
    await worker._reconcile_exit_siblings(db, adapter, filled, Position(account_id="a", market="USDS_M", symbol="BTCUSDT", quantity=Decimal("0")), [])
    assert sibling.status == "SUBMITTED"
