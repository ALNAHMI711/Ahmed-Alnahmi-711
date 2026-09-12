from modules.alpha.performance_monitor import PerformancePolicy, monitor
from modules.alpha.position_sizing import SizingRequest, size
from modules.alpha.regime_detector import MarketRegime, detect
from modules.alpha.strategy_ranking import StrategyEvidence, rank
from risk.engine import RiskLimits

L=RiskLimits(100,.2,3,1000,500,3,.002,.003)
def test_regime_and_rank():
 r=detect([100+i for i in range(20)],[10]*20); assert r.regime==MarketRegime.TRENDING_UP
 e=StrategyEvidence('trend',.01,.6,1.5,.1,40,(MarketRegime.TRENDING_UP,));assert rank(e,r.regime).eligible
def test_alpha_sizing_cannot_bypass_risk_or_ip():
 q=SizingRequest(1000,100,99,.9,0,0,0,1,0,0,False,False);assert size(q,L).quantity==0
 q=SizingRequest(1000,100,99,.9,0,0,0,4,0,0,False,True);assert size(q,L).quantity==0
def test_decay_pauses_strategy():
 assert monitor('x',[-.01]*20,PerformancePolicy()).paused
