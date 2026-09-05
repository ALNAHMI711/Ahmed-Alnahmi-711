"""Risk is a mandatory gate; no strategy, signal, or AI may bypass it."""
from dataclasses import dataclass
@dataclass(frozen=True)
class RiskLimits:
    max_daily_loss: float; max_drawdown: float; max_open_positions: int
    max_exposure: float; max_position_size: float; max_leverage: float
    max_slippage: float; max_spread: float
@dataclass(frozen=True)
class RiskDecision: approved: bool; reasons: tuple[str,...]
def evaluate(limits: RiskLimits, *, daily_loss: float, open_positions: int, exposure: float, position_size: float, leverage: float, spread: float, slippage: float, kill_switch: bool) -> RiskDecision:
    checks=((kill_switch,"مفتاح الإيقاف مفعّل"),(daily_loss >= limits.max_daily_loss,"تم بلوغ حد الخسارة اليومية"),(open_positions >= limits.max_open_positions,"تم بلوغ حد المراكز المفتوحة"),(exposure + position_size > limits.max_exposure,"تم تجاوز حد التعرّض"),(position_size > limits.max_position_size,"حجم المركز كبير"),(leverage > limits.max_leverage,"الرافعة أعلى من الحد"),(spread > limits.max_spread,"الفارق السعري أعلى من الحد"),(slippage > limits.max_slippage,"الانزلاق السعري أعلى من الحد"))
    return RiskDecision(not any(x[0] for x in checks), tuple(msg for failed,msg in checks if failed))
