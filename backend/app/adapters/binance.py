"""Authenticated Binance REST sources used by reconciliation and dashboard reads."""
import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urlencode

import httpx

from .account import BinanceAccountMixin
from .base import AccountCapabilities, ExchangeAdapter, Market
from .market_depth import BinanceMarketDepthMixin

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

class BinanceAdapter(BinanceAccountMixin, BinanceMarketDepthMixin, ExchangeAdapter):
    """Binance API adapter. Credentials are supplied only by the encrypted account vault."""
    def __init__(self, market: Market, api_key: str, api_secret: str, client: httpx.AsyncClient | None = None):
        self.market, self.api_key, self.api_secret = market, api_key, api_secret
        self.client = client or httpx.AsyncClient(timeout=15)
        self.base_url = "https://api.binance.com" if market in (Market.SPOT, Market.CROSS_MARGIN, Market.ISOLATED_MARGIN) else ("https://dapi.binance.com" if market == Market.COIN_M else "https://fapi.binance.com")
    def _margin(self) -> bool: return self.market in (Market.CROSS_MARGIN, Market.ISOLATED_MARGIN)
    def _spot_like_path(self, spot_path: str, margin_path: str) -> str: return margin_path if self._margin() else spot_path
    def _margin_params(self) -> dict[str, object]: return {"isIsolated": "TRUE" if self.market == Market.ISOLATED_MARGIN else "FALSE"}
    async def _signed_get(self, path: str, params: dict[str, object] | None = None) -> object:
        params = {**(params or {}), "timestamp": int(datetime.now(tz=timezone.utc).timestamp() * 1000), "recvWindow": 5000}
        query = urlencode(params); signature = hmac.new(self.api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        response = await self.client.get(self.base_url + path, params={**params, "signature": signature}, headers={"X-MBX-APIKEY": self.api_key})
        response.raise_for_status(); return response.json()
    async def account_capabilities(self) -> AccountCapabilities:
        path = self._spot_like_path("/api/v3/account", "/sapi/v1/margin/account") if self._margin() or self.market == Market.SPOT else ("/dapi/v1/account" if self.market == Market.COIN_M else "/fapi/v2/account")
        payload = await self._signed_get(path, self._margin_params() if self._margin() else {})
        return AccountCapabilities(bool(payload.get("canTrade", True)), bool(payload.get("canWithdraw", False)), False)
    async def validate_symbol(self, symbol: str) -> bool:
        path = "/api/v3/exchangeInfo" if not self._margin() and self.market == Market.SPOT else ("/dapi/v1/exchangeInfo" if self.market == Market.COIN_M else "/fapi/v1/exchangeInfo")
        response = await self.client.get(self.base_url + path); response.raise_for_status()
        return any(item["symbol"] == symbol for item in response.json()["symbols"])
    async def fills(self, symbol: str, start_time: int | None = None) -> list[ExchangeFill]:
        spot = self.market == Market.SPOT
        path = self._spot_like_path("/api/v3/myTrades", "/sapi/v1/margin/myTrades") if self._margin() or spot else ("/dapi/v1/userTrades" if self.market == Market.COIN_M else "/fapi/v1/userTrades")
        params = {k:v for k,v in {"symbol":symbol, "startTime":start_time}.items() if v is not None}; params.update(self._margin_params() if self._margin() else {})
        rows = await self._signed_get(path, params)
        return [ExchangeFill(str(row["id"]), str(row.get("orderId")) if row.get("orderId") is not None else None, row["symbol"], "BUY" if (row.get("isBuyer") if spot or self._margin() else row.get("buyer")) else "SELL", _d(row["qty"]), _d(row["price"]), _d(row.get("quoteQty", _d(row["qty"])*_d(row["price"]))), _d(row.get("commission", "0")), row.get("commissionAsset"), _time(row["time"]), _d(row["realizedPnl"]) if row.get("realizedPnl") is not None else None) for row in rows]
    async def positions(self) -> list[ExchangePosition]:
        if self.market in (Market.SPOT, Market.CROSS_MARGIN, Market.ISOLATED_MARGIN): return []
        rows = await self._signed_get("/dapi/v1/positionRisk" if self.market == Market.COIN_M else "/fapi/v2/positionRisk")
        return [ExchangePosition(row["symbol"], _d(row["positionAmt"]), _d(row["entryPrice"]) if _d(row["positionAmt"]) else None, _d(row["markPrice"]), _d(row["unRealizedProfit"])) for row in rows]
    async def funding(self, symbol: str, start_time: int | None = None) -> list[FundingPayment]:
        if self.market in (Market.SPOT, Market.CROSS_MARGIN, Market.ISOLATED_MARGIN): return []
        rows = await self._signed_get("/dapi/v1/income" if self.market == Market.COIN_M else "/fapi/v1/income", {k:v for k,v in {"symbol":symbol, "incomeType":"FUNDING_FEE", "startTime":start_time}.items() if v is not None})
        return [FundingPayment(str(row["tranId"]), row["symbol"], _d(row["income"]), _time(row["time"])) for row in rows]
    async def mark_price(self, symbol: str) -> Decimal:
        path = "/api/v3/ticker/price" if self.market in (Market.SPOT, Market.CROSS_MARGIN, Market.ISOLATED_MARGIN) else ("/dapi/v1/premiumIndex" if self.market == Market.COIN_M else "/fapi/v1/premiumIndex")
        response = await self.client.get(self.base_url + path, params={"symbol": symbol}); response.raise_for_status()
        payload = response.json(); return _d(payload.get("markPrice", payload["price"]))
    async def place_order(self, symbol: str, side: str, order_type: str, quantity: Decimal, *, price: Decimal | None = None, client_order_id: str | None = None, reduce_only: bool = False, stop_price: Decimal | None = None) -> dict:
        spot = self.market == Market.SPOT
        path = self._spot_like_path("/api/v3/order", "/sapi/v1/margin/order") if self._margin() or spot else ("/dapi/v1/order" if self.market == Market.COIN_M else "/fapi/v1/order")
        params: dict[str, object] = {"symbol": symbol, "side": side, "type": order_type, "quantity": str(quantity)}
        if self._margin(): params.update(self._margin_params())
        if price is not None: params["price"] = str(price); params["timeInForce"] = "GTC"
        if client_order_id: params["newClientOrderId"] = client_order_id
        if reduce_only and not spot: params["reduceOnly"] = "true"
        if stop_price is not None: params["stopPrice"] = str(stop_price)
        params.update(timestamp=int(datetime.now(tz=timezone.utc).timestamp()*1000), recvWindow=5000)
        query=urlencode(params); signature=hmac.new(self.api_secret.encode(),query.encode(),hashlib.sha256).hexdigest()
        response=await self.client.post(self.base_url+path,params={**params,"signature":signature},headers={"X-MBX-APIKEY":self.api_key})
        response.raise_for_status(); return response.json()
    async def open_orders(self, symbol: str | None = None) -> list[dict]:
        spot=self.market == Market.SPOT
        path=self._spot_like_path("/api/v3/openOrders", "/sapi/v1/margin/openOrders") if self._margin() or spot else ("/dapi/v1/openOrders" if self.market==Market.COIN_M else "/fapi/v1/openOrders")
        params={"symbol":symbol} if symbol else {}; params.update(self._margin_params() if self._margin() else {})
        return await self._signed_get(path, params)
    async def order_status(self, symbol: str, *, order_id: str | None = None, client_order_id: str | None = None) -> dict:
        spot=self.market == Market.SPOT
        path=self._spot_like_path("/api/v3/order", "/sapi/v1/margin/order") if self._margin() or spot else ("/dapi/v1/order" if self.market==Market.COIN_M else "/fapi/v1/order")
        params={"symbol":symbol}; params.update({"orderId":order_id} if order_id else {"origClientOrderId":client_order_id}); params.update(self._margin_params() if self._margin() else {})
        return await self._signed_get(path,params)
    async def cancel_order(self, symbol: str, *, order_id: str | None = None, client_order_id: str | None = None) -> dict:
        if not order_id and not client_order_id: raise ValueError("order_id or client_order_id is required")
        spot=self.market == Market.SPOT
        path=self._spot_like_path("/api/v3/order", "/sapi/v1/margin/order") if self._margin() or spot else ("/dapi/v1/order" if self.market==Market.COIN_M else "/fapi/v1/order")
        params: dict[str, object] = {"symbol": symbol}; params.update({"orderId": order_id} if order_id else {"origClientOrderId": client_order_id}); params.update(self._margin_params() if self._margin() else {})
        params.update(timestamp=int(datetime.now(tz=timezone.utc).timestamp()*1000), recvWindow=5000)
        query=urlencode(params); signature=hmac.new(self.api_secret.encode(),query.encode(),hashlib.sha256).hexdigest()
        response=await self.client.delete(self.base_url+path,params={**params,"signature":signature},headers={"X-MBX-APIKEY":self.api_key})
        response.raise_for_status(); return response.json()
