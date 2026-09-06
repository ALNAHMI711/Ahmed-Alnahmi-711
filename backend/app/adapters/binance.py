"""Small, explicit Binance REST adapters.

Credentials stay in the backend.  The class deliberately defaults to a
fail-closed capability report: an account cannot be used for LIVE trading
until the exchange restriction check has completed successfully.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import asyncio
import hmac
import json
import time
from typing import Any
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base import AccountCapabilities, ExchangeAdapter, Market


class BinanceApiError(RuntimeError):
    """An exchange response that is safe to present as an operational error."""


@dataclass(frozen=True)
class BinanceEndpoints:
    base_url: str
    account: str
    ticker: str
    order_book: str
    order: str
    open_orders: str
    positions: str | None
    margin_params: dict[str, str] | None = None


ENDPOINTS: dict[Market, BinanceEndpoints] = {
    Market.SPOT: BinanceEndpoints("https://api.binance.com", "/api/v3/account", "/api/v3/ticker/24hr", "/api/v3/depth", "/api/v3/order", "/api/v3/openOrders", None),
    Market.CROSS_MARGIN: BinanceEndpoints("https://api.binance.com", "/sapi/v1/margin/account", "/api/v3/ticker/24hr", "/api/v3/depth", "/sapi/v1/margin/order", "/sapi/v1/margin/openOrders", None),
    Market.ISOLATED_MARGIN: BinanceEndpoints("https://api.binance.com", "/sapi/v1/margin/isolated/account", "/api/v3/ticker/24hr", "/api/v3/depth", "/sapi/v1/margin/order", "/sapi/v1/margin/openOrders", None, {"isIsolated": "TRUE"}),
    Market.USDS_M: BinanceEndpoints("https://fapi.binance.com", "/fapi/v2/account", "/fapi/v1/ticker/24hr", "/fapi/v1/depth", "/fapi/v1/order", "/fapi/v1/openOrders", "/fapi/v2/positionRisk"),
    Market.COIN_M: BinanceEndpoints("https://dapi.binance.com", "/dapi/v1/account", "/dapi/v1/ticker/24hr", "/dapi/v1/depth", "/dapi/v1/order", "/dapi/v1/openOrders", "/dapi/v1/positionRisk"),
}


class BinanceAdapter(ExchangeAdapter):
    """Authenticated Binance adapter for one supported market type.

    This adapter does not implement Alpha or Stocks because the repository has
    no verified provider contract for those markets.
    """

    def __init__(self, market: Market, api_key: str, api_secret: str, *, timeout: float = 15.0):
        if market not in ENDPOINTS:
            raise ValueError(f"No verified Binance adapter is available for {market.value}")
        self.market = market
        self._api_key = api_key
        self._api_secret = api_secret.encode()
        self._endpoints = ENDPOINTS[market]
        self._timeout = timeout

    def _signed(self, params: dict[str, Any] | None = None) -> dict[str, str]:
        values = {key: str(value) for key, value in (params or {}).items() if value is not None}
        values["timestamp"] = str(int(time.time() * 1000))
        payload = urlencode(sorted(values.items()))
        values["signature"] = hmac.new(self._api_secret, payload.encode(), sha256).hexdigest()
        return values

    def _sync_request(self, method: str, path: str, params: dict[str, Any] | None, signed: bool) -> Any:
        request_params = self._signed(params) if signed else params
        headers = {"X-MBX-APIKEY": self._api_key} if signed else {}
        query = urlencode({key: value for key, value in (request_params or {}).items() if value is not None})
        url = f"{self._endpoints.base_url}{path}" + (f"?{query}" if query else "")
        try:
            with urlopen(Request(url, headers=headers, method=method), timeout=self._timeout) as response:  # noqa: S310 -- fixed Binance host map
                return json.loads(response.read())
        except HTTPError as error:
            try:
                detail = json.loads(error.read()).get("msg", error.reason)
            except (ValueError, json.JSONDecodeError):
                detail = error.reason
            raise BinanceApiError(f"Binance: {detail}")
        except URLError as error:
            raise BinanceApiError(f"Binance connection failed: {error.reason}") from error

    async def _request(self, method: str, path: str, *, params: dict[str, Any] | None = None, signed: bool = False) -> Any:
        return await asyncio.to_thread(self._sync_request, method, path, params, signed)

    async def test_connection(self) -> None:
        await self._request("GET", "/api/v3/ping")

    async def account_capabilities(self) -> AccountCapabilities:
        # Binance exposes API-key restrictions on the spot API.  Missing or
        # incomplete data is deliberately treated as unsafe for LIVE.
        restrictions = await self._request("GET", "/sapi/v1/account/apiRestrictions", signed=True)
        return AccountCapabilities(
            trading_enabled=bool(restrictions.get("enableSpotAndMarginTrading") or restrictions.get("enableFutures")),
            withdrawal_enabled=bool(restrictions.get("enableWithdrawals", True)),
            trusted_ip_restriction=False,
        )

    async def validate_symbol(self, symbol: str) -> bool:
        try:
            await self.get_ticker(symbol)
        except BinanceApiError:
            return False
        return True

    async def get_account_state(self) -> Any:
        return await self._request("GET", self._endpoints.account, params=self._endpoints.margin_params, signed=True)

    async def get_balances(self) -> Any:
        return await self.get_account_state()

    async def get_ticker(self, symbol: str) -> Any:
        return await self._request("GET", self._endpoints.ticker, params={"symbol": symbol})

    async def get_order_book(self, symbol: str, limit: int = 20) -> Any:
        return await self._request("GET", self._endpoints.order_book, params={"symbol": symbol, "limit": limit})

    async def create_order(self, **order: Any) -> Any:
        params = {**(self._endpoints.margin_params or {}), **order}
        return await self._request("POST", self._endpoints.order, params=params, signed=True)

    async def cancel_order(self, symbol: str, order_id: str) -> Any:
        return await self._request("DELETE", self._endpoints.order, params={**(self._endpoints.margin_params or {}), "symbol": symbol, "orderId": order_id}, signed=True)

    async def get_order(self, symbol: str, order_id: str) -> Any:
        return await self._request("GET", self._endpoints.order, params={**(self._endpoints.margin_params or {}), "symbol": symbol, "orderId": order_id}, signed=True)

    async def get_open_orders(self, symbol: str | None = None) -> Any:
        return await self._request("GET", self._endpoints.open_orders, params={**(self._endpoints.margin_params or {}), "symbol": symbol}, signed=True)

    async def get_positions(self) -> Any:
        if not self._endpoints.positions:
            return []
        return await self._request("GET", self._endpoints.positions, signed=True)
