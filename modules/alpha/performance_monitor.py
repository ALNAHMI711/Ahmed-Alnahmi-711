from dataclasses import dataclass
from statistics import mean
@dataclass(frozen=True)
class PerformancePolicy: rolling_window:int=20; minimum_expectancy:float=0.; maximum_drawdown:float=.10
@dataclass(frozen=True)
class PerformanceStatus: strategy:str; paused:bool; rolling_expectancy:float; drawdown:float; reason:str
def monitor(strategy:str, pnl:list[float], policy:PerformancePolicy=PerformancePolicy())->PerformanceStatus:
    if len(pnl)<policy.rolling_window:return PerformanceStatus(strategy,False,0.,0.,'بيانات حية غير كافية')
    rolling=pnl[-policy.rolling_window:]; expectancy=mean(rolling); peak=0.; cumulative=0.; drawdown=0.
    for result in pnl:
        cumulative+=result;peak=max(peak,cumulative);drawdown=max(drawdown,peak-cumulative)
    paused=expectancy<policy.minimum_expectancy or drawdown>policy.maximum_drawdown
    reason='إيقاف تلقائي: تراجع الأداء أو تجاوز السحب' if paused else 'الأداء ضمن السياسة'
    return PerformanceStatus(strategy,paused,expectancy,drawdown,reason)
