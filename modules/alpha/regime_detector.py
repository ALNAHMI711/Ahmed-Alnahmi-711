"""Deterministic market-regime classification; does not submit orders."""
from dataclasses import dataclass
from enum import StrEnum
from statistics import mean, pstdev

class MarketRegime(StrEnum): TRENDING_UP='TRENDING_UP'; TRENDING_DOWN='TRENDING_DOWN'; RANGING='RANGING'; VOLATILE='VOLATILE'; ILLIQUID='ILLIQUID'
@dataclass(frozen=True)
class RegimeSnapshot: regime:MarketRegime; trend:float; volatility:float; liquidity_ratio:float; confidence:float

def detect(closes:list[float], volumes:list[float], *, minimum_points:int=20)->RegimeSnapshot:
    if len(closes)!=len(volumes) or len(closes)<minimum_points: raise ValueError('بيانات سعر/سيولة غير كافية أو غير متطابقة')
    returns=[(current/previous)-1 for previous,current in zip(closes,closes[1:]) if previous>0]
    if not returns: raise ValueError('الأسعار يجب أن تكون موجبة')
    trend=(closes[-1]/closes[0])-1; volatility=pstdev(returns); liquidity_ratio=volumes[-1]/mean(volumes)
    if liquidity_ratio<.5: regime=MarketRegime.ILLIQUID
    elif volatility>.04: regime=MarketRegime.VOLATILE
    elif trend>.03: regime=MarketRegime.TRENDING_UP
    elif trend<-.03: regime=MarketRegime.TRENDING_DOWN
    else: regime=MarketRegime.RANGING
    return RegimeSnapshot(regime,trend,volatility,liquidity_ratio,min(1.0,abs(trend)/.03+liquidity_ratio/2))
