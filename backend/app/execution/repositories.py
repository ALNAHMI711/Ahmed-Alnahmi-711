"""Repository layer: all writes are transactional and duplicate-safe."""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .models import Position, ProjectionEvent, Trade

class TradeRepository:
    def __init__(self, db: Session): self.db = db
    def add_once(self, trade: Trade) -> bool:
        """Insert a confirmed exchange fill; False means it was already processed."""
        try:
            with self.db.begin_nested(): self.db.add(trade); self.db.flush()
            return True
        except IntegrityError: return False
    def list_for_position(self, account_id: str, market: str, symbol: str) -> list[Trade]:
        return list(self.db.scalars(select(Trade).where(Trade.account_id == account_id, Trade.market == market, Trade.symbol == symbol).order_by(Trade.occurred_at, Trade.exchange_trade_id)))

class ProjectionRepository:
    def __init__(self, db: Session): self.db = db
    def claim_event(self, key: str, account_id: str, kind: str, occurred_at: datetime) -> bool:
        try:
            with self.db.begin_nested():
                self.db.add(ProjectionEvent(event_key=key, account_id=account_id, kind=kind, occurred_at=occurred_at)); self.db.flush()
            return True
        except IntegrityError: return False
    def position(self, account_id: str, market: str, symbol: str) -> Position | None:
        return self.db.scalar(select(Position).where(Position.account_id == account_id, Position.market == market, Position.symbol == symbol))
    def get_or_create_position(self, account_id: str, market: str, symbol: str) -> Position:
        result = self.position(account_id, market, symbol)
        if result is None:
            result = Position(account_id=account_id, market=market, symbol=symbol)
            self.db.add(result); self.db.flush()
        return result
    def add_funding_once(self, account_id: str, market: str, symbol: str, event_id: str, amount: Decimal, occurred_at: datetime) -> bool:
        if not self.claim_event(f"funding:{account_id}:{market}:{event_id}", account_id, "funding", occurred_at): return False
        position = self.get_or_create_position(account_id, market, symbol)
        position.funding += amount
        position.realized_pnl += amount
        position.version += 1
        return True

class OrderRepository:
    VALID = frozenset({"NEW", "PARTIALLY_FILLED", "FILLED", "CANCELED", "REJECTED", "EXPIRED", "UNKNOWN"})
    def __init__(self, db: Session): self.db = db
    def by_request(self, account_id: str, client_request_id: str):
        from .models import ExchangeOrder
        return self.db.scalar(select(ExchangeOrder).where(ExchangeOrder.account_id == account_id, ExchangeOrder.client_request_id == client_request_id))
    def create_once(self, order):
        existing = self.by_request(order.account_id, order.client_request_id)
        if existing: return existing, False
        self.db.add(order); self.db.flush(); return order, True
    def update_status(self, order, status: str, exchange_order_id: str | None = None):
        if status not in self.VALID: raise ValueError("invalid exchange order status")
        order.status = status
        if exchange_order_id: order.exchange_order_id = exchange_order_id
        return order

class ConditionalOrderRepository:
    KINDS=frozenset({'TP1','TP2','TP3','TP4','TP5','TP6','TP7','SL','PARTIAL_CLOSE','BREAK_EVEN','TRAILING'})
    STATES=frozenset({'ACTIVE','SUBMITTED','PARTIALLY_FILLED','FILLED','CANCELED','REJECTED','EXPIRED','UNKNOWN'})
    def __init__(self,db): self.db=db
    def create_once(self,plan):
        if plan.kind not in self.KINDS or plan.quantity <= 0: raise ValueError('invalid conditional order')
        if plan.kind != 'TRAILING' and plan.trigger_price is None: raise ValueError('trigger price required')
        from .models import ConditionalOrder
        current=self.db.scalar(select(ConditionalOrder).where(ConditionalOrder.account_id==plan.account_id,ConditionalOrder.idempotency_key==plan.idempotency_key))
        if current:return current,False
        self.db.add(plan);self.db.flush();return plan,True
    def transition(self,plan,status,exchange_order_id=None):
        if status not in self.STATES:raise ValueError('invalid conditional status')
        plan.status=status
        if exchange_order_id:plan.exchange_order_id=exchange_order_id
        return plan
