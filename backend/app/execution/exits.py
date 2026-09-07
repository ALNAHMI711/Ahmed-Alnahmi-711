"""Persistent conditional exit plans; worker submits only on exchange-confirmed marks."""
from dataclasses import dataclass
from decimal import Decimal
@dataclass(frozen=True)
class ExitTrigger:
    plan_id:str; kind:str; trigger_price:Decimal; quantity:Decimal; client_request_id:str

def should_trigger(kind: str, mark: Decimal, trigger: Decimal, side: str) -> bool:
    if kind in {'TP','TRAILING'}: return mark >= trigger if side == 'SELL' else mark <= trigger
    return mark <= trigger if side == 'SELL' else mark >= trigger
