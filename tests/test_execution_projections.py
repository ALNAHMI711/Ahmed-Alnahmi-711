from datetime import datetime
from decimal import Decimal
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from backend.app.database import ApiAccount, Base
from backend.app.execution.models import Position, Trade
from backend.app.execution.projections import apply_fill
from backend.app.execution.reconciliation import ReconciliationWorker
from backend.app.execution.repositories import ProjectionRepository, TradeRepository
from backend.app.adapters.binance import ExchangeFill, ExchangePosition, FundingPayment

D = Decimal
NOW = datetime(2026, 1, 1)
def setup():
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions() as db:
        db.add(ApiAccount(id="account", name="test", market="usds_m", encrypted_key="x", encrypted_secret="x")); db.commit()
    return sessions
def fill(identifier, side, quantity, price, fee="0"):
    return Trade(account_id="account", market="usds_m", symbol="BTCUSDT", exchange_trade_id=identifier, side=side, quantity=D(quantity), price=D(price), quote_quantity=D(quantity)*D(price), fee=D(fee), occurred_at=NOW)
def test_projection_partial_close_reverse_and_full_close():
    sessions = setup()
    with sessions() as db:
        repo = ProjectionRepository(db)
        for item in (fill("1", "BUY", "2", "100", "1"), fill("2", "BUY", "1", "110", "1"), fill("3", "SELL", "1", "120", "1"), fill("4", "SELL", "3", "90", "1"), fill("5", "BUY", "1", "80", "1")):
            assert apply_fill(repo, item) is not None
        position = repo.position("account", "usds_m", "BTCUSDT")
        assert position.quantity == 0 and position.state == "CLOSED"
        # Gross closes: 13.333... + 80 - 10 = 83.333... after five fees.
        assert position.realized_pnl == D("-4.999999999999985789")
        assert position.fees == D("5")
        db.commit()
def test_trade_repository_duplicate_fill_is_not_inserted():
    sessions = setup()
    with sessions() as db:
        trades = TradeRepository(db); assert trades.add_once(fill("same", "BUY", "1", "100")); assert not trades.add_once(fill("same", "BUY", "1", "100")); db.commit()
        assert len(db.scalars(select(Trade)).all()) == 1
class Adapter:
    async def fills(self, symbol, start_time): return [ExchangeFill("t1", "o1", symbol, "BUY", D("2"), D("100"), D("200"), D("2"), "USDT", NOW)]
    async def funding(self, symbol, start_time): return [FundingPayment("fund-1", symbol, D("-3"), NOW)]
    async def positions(self): return [ExchangePosition("BTCUSDT", D("2"), D("100"), D("125"), D("50"))]
    async def mark_price(self, symbol): return D("125")
def test_reconciliation_is_restart_idempotent_and_uses_exchange_snapshot():
    sessions = setup(); worker = ReconciliationWorker(sessions, lambda account, market: Adapter())
    import asyncio
    asyncio.run(worker.reconcile("account", "usds_m", "BTCUSDT")); asyncio.run(worker.reconcile("account", "usds_m", "BTCUSDT"))
    with sessions() as db:
        assert len(db.scalars(select(Trade)).all()) == 1
        position = db.scalar(select(Position)); assert position.quantity == D("2") and position.unrealized_pnl == D("50")
        assert position.funding == D("-3") and position.realized_pnl == D("-5") # funding plus one fill fee
def test_reconciliation_publishes_only_after_commit():
    sessions = setup(); events = []
    async def publish(event_type, payload):
        with sessions() as db:
            assert db.scalar(select(Trade)) is not None
        events.append(event_type)
    worker = ReconciliationWorker(sessions, lambda account, market: Adapter(), publish)
    import asyncio
    asyncio.run(worker.reconcile("account", "usds_m", "BTCUSDT"))
    assert {"trade", "execution", "position"}.issubset(events)

def test_conditional_plan_rejects_bad_kind_and_duplicate_key():
 from backend.app.execution.models import ConditionalOrder
 from backend.app.execution.repositories import ConditionalOrderRepository
 sessions=setup()
 with sessions() as db:
  repo=ConditionalOrderRepository(db)
  plan=ConditionalOrder(account_id='account',market='usds_m',symbol='BTCUSDT',kind='TP1',side='SELL',quantity=D('1'),trigger_price=D('110'),idempotency_key='tp-1')
  assert repo.create_once(plan)[1]; assert not repo.create_once(plan)[1]


def test_apply_fill_records_net_realized_pnl_on_trade():
    sessions = setup()

    with sessions() as db:
        repo = ProjectionRepository(db)

        opening = fill("pnl-1", "BUY", "1", "100", "1")
        closing = fill("pnl-2", "SELL", "1", "120", "2")

        apply_fill(repo, opening)
        apply_fill(repo, closing)

        assert opening.realized_pnl == D("-1")
        assert closing.realized_pnl == D("18")

        position = repo.position("account", "usds_m", "BTCUSDT")
        assert position.realized_pnl == D("17")
        assert position.fees == D("3")
