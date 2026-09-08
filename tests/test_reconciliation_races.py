from decimal import Decimal
from types import SimpleNamespace
from backend.app.execution.conditional_lifecycle import restart_action, sibling_action


def test_restart_never_resubmits_ambiguous_submitted_order():
    assert restart_action("SUBMITTED", None) == "RECONCILE_BEFORE_ACTION"


def test_restart_reconciles_active_plan_before_action():
    assert restart_action("ACTIVE", None) == "RECONCILE_PLAN"


def test_terminal_restart_is_noop():
    assert restart_action("FILLED", "123") == "NOOP"


def test_partial_fill_resizes_only_against_reconciled_position():
    assert sibling_action(
        filled_quantity=Decimal("0.4"),
        position_quantity=Decimal("0.6"),
        sibling_status="SUBMITTED",
    ) == "RESIZE_SIBLING"


def test_full_close_cancels_sibling():
    assert sibling_action(
        filled_quantity=Decimal("1"),
        position_quantity=Decimal("0"),
        sibling_status="SUBMITTED",
    ) == "CANCEL_SIBLING"


def test_race_invalid_overfill_fails_closed():
    try:
        sibling_action(
            filled_quantity=Decimal("2"),
            position_quantity=Decimal("1"),
            sibling_status="SUBMITTED",
        )
    except ValueError:
        return
    raise AssertionError("overfill race must fail closed")
