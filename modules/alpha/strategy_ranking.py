from dataclasses import dataclass
from modules.alpha.regime_detector import MarketRegime
@dataclass(frozen=True)
class StrategyEvidence: name:str; expected_return:float; win_rate:float; profit_factor:float; max_drawdown:float; oos_trades:int; supported_regimes:tuple[MarketRegime,...]
@dataclass(frozen=True)
class RankedStrategy: name:str; score:float; eligible:bool; reasons:tuple[str,...]
def rank(evidence:StrategyEvidence, regime:MarketRegime)->RankedStrategy:
    reasons=[]
    if evidence.oos_trades<30: reasons.append('عينة خارج العينة غير كافية')
    if evidence.max_drawdown>.25: reasons.append('السحب التاريخي أعلى من الحد')
    if evidence.profit_factor<1: reasons.append('عامل الربح أقل من واحد')
    if regime not in evidence.supported_regimes: reasons.append('الاستراتيجية غير مثبتة لحالة السوق الحالية')
    score=max(0.,min(100.,(evidence.expected_return*1000)+(evidence.win_rate*30)+(evidence.profit_factor*15)-(evidence.max_drawdown*100)))
    return RankedStrategy(evidence.name,score,not reasons,tuple(reasons))
