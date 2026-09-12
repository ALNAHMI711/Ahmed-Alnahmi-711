"""Alpha decision coordinator: ranking/sizing always terminates at Risk Engine."""
from dataclasses import dataclass

from modules.alpha.position_sizing import SizingDecision, SizingRequest, size
from modules.alpha.strategy_ranking import RankedStrategy
from modules.alpha.trade_journal import JournalEntry, TradeJournal
from risk.engine import RiskDecision, RiskLimits


@dataclass(frozen=True)
class AlphaDecision:
    accepted: bool
    strategy: RankedStrategy
    sizing: SizingDecision


def decide(strategy: RankedStrategy, request: SizingRequest, limits: RiskLimits, journal: TradeJournal, *, symbol: str, regime: str) -> AlphaDecision:
    sizing = size(request, limits) if strategy.eligible else SizingDecision(0, 0, RiskDecision(False, strategy.reasons), "الاستراتيجية غير مؤهلة")
    accepted = strategy.eligible and sizing.risk.approved
    journal.record(JournalEntry(strategy.name, symbol, regime, 0.0, accepted, sizing.risk.reasons))
    return AlphaDecision(accepted, strategy, sizing)
