from dataclasses import dataclass
from decimal import Decimal
from .base import Market

@dataclass(frozen=True)
class BookLevel:
    price: Decimal
    quantity: Decimal

@dataclass(frozen=True)
class OrderBook:
    bids: tuple[BookLevel, ...]
    asks: tuple[BookLevel, ...]
    last_update_id: int | None = None

@dataclass(frozen=True)
class SlippageEstimate:
    side: str
    quantity: Decimal
    reference_price: Decimal
    estimated_average_price: Decimal
    slippage_bps: Decimal
    fully_fillable: bool

class BinanceMarketDepthMixin:
    async def order_book(self, symbol: str, limit: int = 20) -> OrderBook:
        if limit <= 0 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        path = "/api/v3/depth" if self.market in (Market.SPOT, Market.CROSS_MARGIN, Market.ISOLATED_MARGIN) else ("/dapi/v1/depth" if self.market == Market.COIN_M else "/fapi/v1/depth")
        response = await self.client.get(self.base_url + path, params={"symbol": symbol, "limit": limit})
        response.raise_for_status()
        payload = response.json()
        return OrderBook(tuple(BookLevel(Decimal(str(p)), Decimal(str(q))) for p, q in payload.get("bids", [])), tuple(BookLevel(Decimal(str(p)), Decimal(str(q))) for p, q in payload.get("asks", [])), payload.get("lastUpdateId"))

    @staticmethod
    def estimate_slippage(book: OrderBook, side: str, quantity: Decimal) -> SlippageEstimate:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        side = side.upper()
        levels = book.asks if side == "BUY" else book.bids if side == "SELL" else ()
        if not levels:
            raise ValueError("unsupported side or empty order book")
        reference = levels[0].price
        remaining = quantity
        notional = Decimal("0")
        for level in levels:
            take = min(remaining, level.quantity)
            notional += take * level.price
            remaining -= take
            if remaining <= 0:
                break
        filled = remaining <= 0
        average = notional / quantity if filled else Decimal("0")
        slippage = ((average - reference) / reference * Decimal("10000")) if filled else Decimal("0")
        if side == "SELL":
            slippage = ((reference - average) / reference * Decimal("10000")) if filled else Decimal("0")
        return SlippageEstimate(side, quantity, reference, average, slippage, filled)
