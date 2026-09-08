from datetime import datetime, timezone
from decimal import Decimal
import pytest
from backend.app.execution.exits import exit_order_request, validate_exit
from backend.app.execution.models import Position, Trade
from backend.app.execution.projections import apply_fill


def test_long_tp_must_be_above_mark():
    validate_exit("TP", "LONG", Decimal("110"), Decimal("100"), Decimal("1"))
    with pytest.raises(ValueError):
        validate_exit("TP", "LONG", Decimal("90"), Decimal("100"), Decimal("1"))


def test_short_sl_must_be_above_mark():
    validate_exit("SL", "SHORT", Decimal("110"), Decimal("100"), Decimal("1"))
    with pytest.raises(ValueError):
        validate_exit("SL", "SHORT", Decimal("90"), Decimal("100"), Decimal("1"))


def test_exit_request_is_reduce_only_and_never_claims_confirmation():
    request = exit_order_request("SL", "LONG", Decimal("1.5"), Decimal("90"), "exit-123")
    assert request["side"] == "SELL"
    assert request["reduce_only"] is True
    assert request["client_order_id"] == "exit-123"
    assert "orderId" not in request


class FakeRepository:
    def __init__(self):
        self.events = set()
        self.position = None

    def claim_event(self, key, account_id, kind, occurred_at):
        if key in self.events:
            return False
        self.events.add(key)
        return True

    def get_or_create_position(self, account_id, market, symbol):
        if self.position is None:
            self.position = Position(account_id=account_id, market=market, symbol=symbol)
        return self.position


def test_projection_fill_is_idempotent():
    repository = FakeRepository()
    trade = Trade(account_id="a", market="usds_m", symbol="BTCUSDT", exchange_trade_id="7", side="BUY", quantity=Decimal("1"), price=Decimal("100"), quote_quantity=Decimal("100"), fee=Decimal("0.1"), occurred_at=datetime.now(timezone.utc))
    first = apply_fill(repository, trade)
    second = apply_fill(repository, trade)
    assert first is not None
    assert second is None
    assert repository.position.quantity == Decimal("1")
