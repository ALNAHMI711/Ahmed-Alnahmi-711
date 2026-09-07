from decimal import Decimal
from backend.app.execution.exits import should_trigger

def test_should_trigger_tp_family_sell():
    assert should_trigger("TP1", Decimal("200"), Decimal("199"), "SELL") is True

def test_should_trigger_tp_family_buy():
    assert should_trigger("TP2", Decimal("99"), Decimal("100"), "BUY") is True

def test_should_trigger_sl_sell():
    assert should_trigger("SL", Decimal("90"), Decimal("95"), "SELL") is True

def test_should_trigger_trailing_behaves_like_tp_sell():
    assert should_trigger("TRAILING", Decimal("150"), Decimal("149"), "SELL") is True
