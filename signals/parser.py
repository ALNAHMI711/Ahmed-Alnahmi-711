import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Signal:
    symbol: str
    market: str
    side: str
    entries: tuple[float, ...]
    take_profits: tuple[float, ...]
    stop_loss: float


def parse(message: str) -> Signal:
    normalized = message.upper().replace("USDT", "USDT")
    symbol_match = re.search(r"\b([A-Z0-9]+)\s*/\s*(USDT|BUSD|USD)\b", normalized)
    market_match = re.search(r"\b(FUTURE|FUTURES|SPOT)\b", normalized)
    side_match = re.search(r"\b(BUY|SELL)\b", normalized)

    def section(label):
        match = re.search(r"(?:" + label + r")\s*:?\s*([0-9.\s/,]+)", normalized)
        return tuple(float(x) for x in re.findall(r"\d+(?:\.\d+)?", match.group(1))) if match else ()

    entries, tps = section(r"BUY|SELL"), section(r"TP|TAKE\s*PROFIT")
    sl = section(r"SL|STOP\s*LOSS")
    if not (symbol_match and market_match and side_match and entries and tps and sl):
        raise ValueError("الإشارة غير مكتملة أو بصيغة غير مدعومة")
    if len(tps) > 7:
        raise ValueError("الحد الأقصى سبعة أهداف ربح")
    return Signal("".join(symbol_match.groups()), market_match.group(1), side_match.group(1), entries, tps, sl[0])
