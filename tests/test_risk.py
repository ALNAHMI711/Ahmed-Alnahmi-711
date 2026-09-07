from risk.engine import RiskLimits,evaluate
L=RiskLimits(100,.2,2,1000,500,3,.002,.003)
def test_kill_switch_always_blocks():
 assert not evaluate(L,daily_loss=0,open_positions=0,exposure=0,position_size=1,leverage=1,spread=0,slippage=0,kill_switch=True).approved
def test_limits_allow_safe_order():
 assert evaluate(L,daily_loss=0,open_positions=0,exposure=0,position_size=1,leverage=1,spread=0,slippage=0,kill_switch=False).approved

def test_daily_loss_limit_blocks():
    decision = evaluate(
        L,
        daily_loss=100,
        open_positions=0,
        exposure=0,
        position_size=1,
        leverage=1,
        spread=0,
        slippage=0,
        kill_switch=False,
    )
    assert not decision.approved


def test_open_positions_limit_blocks():
    decision = evaluate(
        L,
        daily_loss=0,
        open_positions=2,
        exposure=0,
        position_size=1,
        leverage=1,
        spread=0,
        slippage=0,
        kill_switch=False,
    )
    assert not decision.approved


def test_exposure_limit_blocks():
    decision = evaluate(
        L,
        daily_loss=0,
        open_positions=0,
        exposure=1000,
        position_size=1,
        leverage=1,
        spread=0,
        slippage=0,
        kill_switch=False,
    )
    assert not decision.approved


def test_position_size_limit_blocks():
    decision = evaluate(
        L,
        daily_loss=0,
        open_positions=0,
        exposure=0,
        position_size=500,
        leverage=1,
        spread=0,
        slippage=0,
        kill_switch=False,
    )
    assert not decision.approved


def test_leverage_limit_blocks():
    decision = evaluate(
        L,
        daily_loss=0,
        open_positions=0,
        exposure=0,
        position_size=1,
        leverage=3,
        spread=0,
        slippage=0,
        kill_switch=False,
    )
    assert not decision.approved


def test_spread_limit_blocks():
    decision = evaluate(
        L,
        daily_loss=0,
        open_positions=0,
        exposure=0,
        position_size=1,
        leverage=1,
        spread=0.003,
        slippage=0,
        kill_switch=False,
    )
    assert not decision.approved


def test_slippage_limit_blocks():
    decision = evaluate(
        L,
        daily_loss=0,
        open_positions=0,
        exposure=0,
        position_size=1,
        leverage=1,
        spread=0,
        slippage=0.002,
        kill_switch=False,
    )
    assert not decision.approved


def test_multiple_risk_violations_return_all_reasons():
    decision = evaluate(
        L,
        daily_loss=100,
        open_positions=2,
        exposure=1000,
        position_size=500,
        leverage=3,
        spread=0.003,
        slippage=0.002,
        kill_switch=True,
    )
    assert not decision.approved
    assert len(decision.reasons) == 8
