from decimal import Decimal
from types import SimpleNamespace
from backend.app.execution.conditional_worker import ConditionalOrderWorker


def test_conditional_risk_rejects_missing_or_closed_position():
    plan = SimpleNamespace(quantity=Decimal("1"))
    assert ConditionalOrderWorker._risk_allows(plan, None) is False
    assert ConditionalOrderWorker._risk_allows(plan, SimpleNamespace(state="CLOSED", quantity=Decimal("1"))) is False


def test_conditional_risk_rejects_exit_larger_than_position():
    plan = SimpleNamespace(quantity=Decimal("2"))
    position = SimpleNamespace(state="OPEN", quantity=Decimal("1.5"))
    assert ConditionalOrderWorker._risk_allows(plan, position) is False


def test_conditional_risk_allows_protective_exit_within_position():
    plan = SimpleNamespace(quantity=Decimal("1.5"))
    position = SimpleNamespace(state="OPEN", quantity=Decimal("2"))
    assert ConditionalOrderWorker._risk_allows(plan, position) is True
