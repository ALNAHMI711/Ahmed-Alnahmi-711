from risk.engine import RiskLimits, evaluate

L=RiskLimits(100,.2,2,1000,500,3,.002,.003)
def test_kill_switch_always_blocks():
 assert not evaluate(L,daily_loss=0,open_positions=0,exposure=0,position_size=1,leverage=1,spread=0,slippage=0,kill_switch=True).approved
def test_limits_allow_safe_order():
 assert evaluate(L,daily_loss=0,open_positions=0,exposure=0,position_size=1,leverage=1,spread=0,slippage=0,kill_switch=False).approved
