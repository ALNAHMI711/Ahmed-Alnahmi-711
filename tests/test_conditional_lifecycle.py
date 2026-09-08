from decimal import Decimal

import pytest

from backend.app.execution.conditional_lifecycle import restart_action, sibling_action

@pytest.mark.parametrize("status", ["ACTIVE", "SUBMITTED"])
def test_full_fill_cancels_sibling(status):
    assert sibling_action(filled_quantity=Decimal(1), position_quantity=Decimal(0), sibling_status=status) == "CANCEL_SIBLING"

def test_partial_fill_requires_sibling_resize():
    assert sibling_action(filled_quantity=Decimal("0.4"), position_quantity=Decimal("0.6"), sibling_status="SUBMITTED") == "RESIZE_SIBLING"

def test_terminal_sibling_is_not_touched():
    assert sibling_action(filled_quantity=Decimal(1), position_quantity=Decimal(0), sibling_status="FILLED") == "NOOP"

def test_fill_cannot_exceed_reconciled_position():
    with pytest.raises(ValueError):
        sibling_action(filled_quantity=Decimal(2), position_quantity=Decimal(1), sibling_status="SUBMITTED")

def test_restart_never_resubmits_ambiguous_submitted_order():
    assert restart_action("SUBMITTED", None) == "RECONCILE_BEFORE_ACTION"

def test_restart_reconciles_active_plan():
    assert restart_action("ACTIVE", None) == "RECONCILE_PLAN"

def test_restart_does_nothing_for_terminal_state():
    assert restart_action("CANCELED", "123") == "NOOP"

def test_unknown_state_fails_closed():
    with pytest.raises(ValueError):
        restart_action("UNKNOWN", None)
