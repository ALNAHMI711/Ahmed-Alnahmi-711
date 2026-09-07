"""Authenticated Binance REST sources used by reconciliation (not WebSockets)."""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib, hmac
from urllib.parse import urlencode
import httpx
from .base import AccountCapabilities, ExchangeAdapter, Market

@dataclass(frozen=True)
class ExchangeFill:
    trade_id: str; order_id: str | None; symbol: str; side: str; quantity: Decimal; price: Decimal
    quote_quantity: Decimal; fee: Decimal; fee_asset: str | None; occurred_at: datetime; realized_pnl: Decimal | None = None
@dataclass(frozen=True)
class FundingPayment:
    event_id: str; symbol: str; amount: Decimal; occurred_at: datetime
@dataclass(frozen=True)
class ExchangePosition:
    symbol: str; quantity: Decimal; entry_price: Decimal | None; mark_price: Decimal | None; unrealized_pnl: Decimal | None

def _time(value: int | str) -> datetime: return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).replace(tzinfo=None)
def _d(value: object) -> Decimal: return Decimal(str(value))

class BinanceAdapter(ExchangeAdapter):
    """Binance API adapter. API credentials are supplied by the account vault."""
    def __init__(self, market: Market, api_key: str, api_secret: str, client: httpx.AsyncClient | None = None):
        self.market, self.api_key, self.api_secret = market, api_key, api_secret
        self.client = client or httpx.AsyncClient(timeout=15)
        self.base_url = "https://api.binance.com" if market in (Market.SPOT, Market.CROSS_MARGIN, Market.ISOLATED_MARGIN) else ("https://dapi.binance.com" if market == Market.COIN_M else "https://[...]")
    async def _signed_get(self, path: str, params: dict[str, object] | None = None) -> object:
        params = {**(params or {}), "timestamp": int(datetime.now(tz=timezone.utc).timestamp() * 1000), "recvWindow": 5000}
        query = urlencode(params); signature = hmac.new(self.api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        response = await self.client.get(self.base_url + path, params={**params, "signature": signature}, headers={"X-MBX-APIKEY": self.api_key})
        response.raise_for_status(); return response.json()
    async def account_capabilities(self) -> AccountCapabilities:
        payload = await self._signed_get("/api/v3/account" if self.market == Market.SPOT else "/fapi/v2/account")
        return AccountCapabilities(bool(payload.get("canTrade", True)), bool(payload.get("canWithdraw", False)), False)
    async def validate_symbol(self, symbol: str) -> bool:
        response = await self.client.get(self.base_url + ("/api/v3/exchangeInfo" if self.market == Market.SPOT else "/fapi/v1/exchangeInfo")); response.raise_for_status()
        return any(item["symbol"] == symbol for item in response.json()["symbols"])
    async def fills(self, symbol: str, start_time: int | None = None) -> list[ExchangeFill]:
        spot = self.market in (Market.SPOT, Market.CROSS_MARGIN, Market.ISOLATED_MARGIN)
        rows = await self._signed_get("/api/v3/myTrades" if spot else "/fapi/v1/userTrades", {k:v for k,v in {"symbol":symbol, "startTime":start_time}.items() if v is not None})
        return [ExchangeFill(str(row["id"]), str(row.get("orderId")) if row.get("orderId") is not None else None, row["symbol"], "BUY" if (row.get("isBuyer") if spot else row.get("buyer")) else "S[...]")
    async def positions(self) -> list[ExchangePosition]:
        if self.market in (Market.SPOT, Market.CROSS_MARGIN, Market.ISOLATED_MARGIN): return []
        rows = await self._signed_get("/dapi/v1/positionRisk" if self.market == Market.COIN_M else "/fapi/v2/positionRisk")
        return [ExchangePosition(row["symbol"], _d(row["positionAmt"]), _d(row["entryPrice"]) if _d(row["positionAmt"]) else None, _d(row["markPrice"]), _d(row["unRealizedProfit"])) for row in row[...]]
    async def funding(self, symbol: str, start_time: int | None = None) -> list[FundingPayment]:
        if self.market in (Market.SPOT, Market.CROSS_MARGIN, Market.ISOLATED_MARGIN): return []
        rows = await self._signed_get("/dapi/v1/income" if self.market == Market.COIN_M else "/fapi/v1/income", {k:v for k,v in {"symbol":symbol, "incomeType":"FUNDING_FEE", "startTime":start_time}.items() if v is not None})
        return [FundingPayment(str(row["tranId"]), row["symbol"], _d(row["income"]), _time(row["time"])) for row in rows]
    async def mark_price(self, symbol: str) -> Decimal:
        path = "/api/v3/ticker/price" if self.market in (Market.SPOT, Market.CROSS_MARGIN, Market.ISOLATED_MARGIN) else ("/dapi/v1/premiumIndex" if self.market == Market.COIN_M else "/fapi/v1/premiumIndex")
        response = await self.client.get(self.base_url + path, params={"symbol": symbol}); response.raise_for_status()
        payload = response.json()
        # Safe fallback: prefer markPrice when present, otherwise use price if available.
        price_val = payload.get("markPrice") if payload.get("markPrice") is not None else payload.get("price")
        if price_val is None:
            raise RuntimeError("unexpected mark/price payload from exchange")
        return _d(price_val)
    async def place_order(self, symbol: str, side: str, order_type: str, quantity: Decimal, *, price: Decimal | None = None, client_order_id: str | None = None, reduce_only: bool = False, stop_price: Decimal | None = None) -> dict:
        """Submit a signed Binance order and return only Binance's confirmed payload."""
        spot = self.market in (Market.SPOT, Market.CROSS_MARGIN, Market.ISOLATED_MARGIN)
        path = "/api/v3/order" if spot else ("/dapi/v1/order" if self.market == Market.COIN_M else "/fapi/v1/order")
        params: dict[str, object] = {"symbol": symbol, "side": side, "type": order_type, "quantity": str(quantity)}
        if price is not None: params["price"] = str(price); params["timeInForce"] = "GTC"
        if client_order_id: params["newClientOrderId"] = client_order_id
        if reduce_only and not spot: params["reduceOnly"] = "true"
        if stop_price is not None: params["stopPrice"] = str(stop_price)
        params.update(timestamp=int(datetime.now(tz=timezone.utc).timestamp()*1000), recvWindow=5000)
        query=urlencode(params); signature=hmac.new(self.api_secret.encode(),query.encode(),hashlib.sha256).hexdigest()
        response=await self.client.post(self.base_url+path,params={**params,"signature":signature},headers={"X-MBX-APIKEY":self.api_key})
        response.raise_for_status(); return response.json()
    async def open_orders(self, symbol: str | None = None) -> list[dict]:
        spot=self.market in (Market.SPOT,Market.CROSS_MARGIN,Market.ISOLATED_MARGIN)
        path="/api/v3/openOrders" if spot else ("/dapi/v1/openOrders" if self.market==Market.COIN_M else "/fapi/v1/openOrders")
        return await self._signed_get(path, {"symbol":symbol} if symbol else {})
    async def order_status(self, symbol: str, *, order_id: str | None = None, client_order_id: str | None = None) -> dict:
        spot=self.market in (Market.SPOT,Market.CROSS_MARGIN,Market.ISOLATED_MARGIN)
        path="/api/v3/order" if spot else ("/dapi/v1/order" if self.market == Market.COIN_M else "/fapi/v1/order")
        params={"symbol":symbol}; params.update({"orderId":order_id} if order_id else {"origClientOrderId":client_order_id})
        return await self._signed_get(path,params)
