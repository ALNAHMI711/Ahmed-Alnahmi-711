from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
@dataclass(frozen=True)
class JournalEntry: strategy:str; symbol:str; regime:str; pnl:float; accepted:bool; risk_reasons:tuple[str,...]; timestamp:datetime=field(default_factory=lambda:datetime.now(timezone.utc))
class TradeJournal:
    """Append-only journal; production workers should point storage_path to encrypted durable storage."""
    def __init__(self, storage_path:Path|None=None): self._entries:list[JournalEntry]=[];self._storage_path=storage_path
    def record(self, entry:JournalEntry)->None:
        self._entries.append(entry)
        if self._storage_path:
            self._storage_path.parent.mkdir(parents=True,exist_ok=True)
            payload=asdict(entry);payload['timestamp']=entry.timestamp.isoformat();payload['risk_reasons']=list(entry.risk_reasons)
            with self._storage_path.open('a',encoding='utf-8') as file:file.write(json.dumps(payload,ensure_ascii=False)+'\n')
    def strategy_summary(self,strategy:str)->dict[str,float|int]:
        records=[e for e in self._entries if e.strategy==strategy]
        return {'trades':len(records),'accepted':sum(e.accepted for e in records),'net_pnl':sum(e.pnl for e in records),'rejected':sum(not e.accepted for e in records)}
    @property
    def entries(self)->tuple[JournalEntry,...]:return tuple(self._entries)
