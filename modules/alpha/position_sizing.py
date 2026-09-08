from dataclasses import dataclass

from risk.engine import RiskDecision, RiskLimits, evaluate


@dataclass(frozen=True)
class SizingRequest:
    equity: float
    entry: float
    stop_loss: float
    confidence: float
    daily_loss: float
    open_positions: int
    exposure: float
    leverage: float
    spread: float
    slippage: float
    kill_switch: bool
    ip_live_allowed: bool


@dataclass(frozen=True)
class SizingDecision:
    quantity: float
    notional: float
    risk: RiskDecision
    reason: str


def size(request: SizingRequest, limits: RiskLimits) -> SizingDecision:
    if request.entry <= 0 or request.stop_loss <= 0 or request.equity <= 0:
        raise ValueError("السعر ورأس المال يجب أن تكون موجبة")
    if not request.ip_live_allowed:
        return SizingDecision(0, 0, RiskDecision(False, ("فشل فحص IP أو صلاحيات LIVE",)), "مرفوض أمنيًا")
    per_unit = abs(request.entry - request.stop_loss)
    risk_budget = min(request.equity * 0.01 * max(0, min(1, request.confidence)), limits.max_position_size)
    quantity = risk_budget / per_unit if per_unit else 0
    notional = quantity * request.entry
    decision = evaluate(limits, daily_loss=request.daily_loss, open_positions=request.open_positions, exposure=request.exposure, position_size=notional, leverage=request.leverage, spread=request.spread, slippage=request.slippage, kill_switch=request.kill_switch)
    return SizingDecision(quantity if decision.approved else 0, notional if decision.approved else 0, decision, "مقبول ضمن Risk Engine" if decision.approved else "مرفوض بواسطة Risk Engine")
