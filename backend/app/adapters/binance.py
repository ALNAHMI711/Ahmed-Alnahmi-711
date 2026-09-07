"""Authenticated Binance REST adapter used by reconciliation and execution."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import hmac
from urllib.parse import urlencode

import httpx

from .base import (
    AccountCapabilities,
    AccountEquity,
    ExchangeAdapter,
    Market,
    OrderBookTicker,
)


@dataclass(frozen=True)
class ExchangeFill:
    trade_id: str
    order_id: str | None
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    quote_quantity: Decimal
    fee: Decimal
    fee_asset: str | None
    occurred_at: datetime
    realized_pnl: Decimal | None = None


@dataclass(frozen=True)
class FundingPayment:
    event_id: str
    symbol: str
    amount: Decimal
    occurred_at: datetime


@dataclass(frozen=True)
class ExchangePosition:
    symbol: str
    quantity: Decimal
    entry_price: Decimal | None
    mark_price: Decimal | None
    unrealized_pnl: Decimal | None


def _time(value: int | str) -> datetime:
    return datetime.fromtimestamp(
        int(value) / 1000,
        tz=timezone.utc,
    ).replace(tzinfo=None)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


class BinanceAdapter(ExchangeAdapter):
    """Binance REST adapter. Credentials are supplied by the backend vault."""

    def __init__(
        self,
        market: Market,
        api_key: str,
        api_secret: str,
        client: httpx.AsyncClient | None = None,
    ):
        self.market = market
        self.api_key = api_key
        self.api_secret = api_secret
        self.client = client or httpx.AsyncClient(timeout=15)

        if market in (
            Market.SPOT,
            Market.CROSS_MARGIN,
            Market.ISOLATED_MARGIN,
        ):
            self.base_url = "https://api.binance.com"
        elif market == Market.USDS_M:
            self.base_url = "https://fapi.binance.com"
        elif market == Market.COIN_M:
            self.base_url = "https://dapi.binance.com"
        else:
            raise ValueError(f"unsupported Binance market: {market}")

    @property
    def _is_margin(self) -> bool:
        return self.market in (
            Market.CROSS_MARGIN,
            Market.ISOLATED_MARGIN,
        )

    @property
    def _is_futures(self) -> bool:
        return self.market in (
            Market.USDS_M,
            Market.COIN_M,
        )

    @property
    def _is_spot_family(self) -> bool:
        return self.market in (
            Market.SPOT,
            Market.CROSS_MARGIN,
            Market.ISOLATED_MARGIN,
        )

    def _margin_params(self) -> dict[str, object]:
        if self.market == Market.ISOLATED_MARGIN:
            return {"isIsolated": "TRUE"}
        return {"isIsolated": "FALSE"}

    async def _signed_get(
        self,
        path: str,
        params: dict[str, object] | None = None,
    ) -> object:
        params = {
            **(params or {}),
            "timestamp": int(datetime.now(tz=timezone.utc).timestamp() * 1000),
            "recvWindow": 5000,
        }

        query = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode(),
            query.encode(),
            hashlib.sha256,
        ).hexdigest()

        response = await self.client.get(
            self.base_url + path,
            params={**params, "signature": signature},
            headers={"X-MBX-APIKEY": self.api_key},
        )
        response.raise_for_status()
        return response.json()

    async def _signed_post(
        self,
        path: str,
        params: dict[str, object],
    ) -> object:
        params = {
            **params,
            "timestamp": int(datetime.now(tz=timezone.utc).timestamp() * 1000),
            "recvWindow": 5000,
        }

        query = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode(),
            query.encode(),
            hashlib.sha256,
        ).hexdigest()

        response = await self.client.post(
            self.base_url + path,
            params={**params, "signature": signature},
            headers={"X-MBX-APIKEY": self.api_key},
        )
        response.raise_for_status()
        return response.json()

    async def account_capabilities(self) -> AccountCapabilities:
        if self.market == Market.SPOT:
            payload = await self._signed_get("/api/v3/account")
        elif self.market in (
            Market.CROSS_MARGIN,
            Market.ISOLATED_MARGIN,
        ):
            payload = await self._signed_get(
                "/sapi/v1/margin/account",
                self._margin_params(),
            )
        elif self.market == Market.USDS_M:
            payload = await self._signed_get("/fapi/v2/account")
        elif self.market == Market.COIN_M:
            payload = await self._signed_get("/dapi/v1/account")
        else:
            raise ValueError(f"unsupported Binance market: {self.market}")

        return AccountCapabilities(
            trading_enabled=bool(payload.get("canTrade", True)),
            withdrawal_enabled=bool(payload.get("canWithdraw", False)),
            trusted_ip_restriction=False,
        )

    async def account_equity(self) -> AccountEquity:
        if self.market == Market.SPOT:
            payload = await self._signed_get("/api/v3/account")

            # Spot does not expose one universal USD/USDT equity number.
            # Returning an unambiguous value is safer than inventing valuation.
            balances = payload.get("balances", [])
            quote_balance = next(
                (
                    row
                    for row in balances
                    if row.get("asset") == "USDT"
                ),
                None,
            )

            if quote_balance is None:
                raise RuntimeError(
                    "SPOT equity unavailable: USDT balance not present"
                )

            free = _d(quote_balance.get("free", "0"))
            locked = _d(quote_balance.get("locked", "0"))

            return AccountEquity(
                equity=free + locked,
                available=free,
            )

        if self.market in (
            Market.CROSS_MARGIN,
            Market.ISOLATED_MARGIN,
        ):
            payload = await self._signed_get(
                "/sapi/v1/margin/account",
                self._margin_params(),
            )

            if "totalNetAssetOfBtc" not in payload:
                raise RuntimeError(
                    "MARGIN equity unavailable from Binance response"
                )

            equity_btc = _d(payload["totalNetAssetOfBtc"])
            return AccountEquity(equity=equity_btc)

        if self.market == Market.USDS_M:
            payload = await self._signed_get("/fapi/v2/account")
            equity = _d(payload["totalMarginBalance"])
            available = _d(payload["availableBalance"])
            return AccountEquity(
                equity=equity,
                available=available,
            )

        if self.market == Market.COIN_M:
            payload = await self._signed_get("/dapi/v1/account")
            equity = _d(payload["totalMarginBalance"])
            available = _d(payload["availableBalance"])
            return AccountEquity(
                equity=equity,
                available=available,
            )

        raise ValueError(f"unsupported Binance market: {self.market}")

    async def validate_symbol(self, symbol: str) -> bool:
        if self.market == Market.SPOT:
            path = "/api/v3/exchangeInfo"
        elif self.market in (
            Market.CROSS_MARGIN,
            Market.ISOLATED_MARGIN,
        ):
            path = "/api/v3/exchangeInfo"
        elif self.market == Market.USDS_M:
            path = "/fapi/v1/exchangeInfo"
        elif self.market == Market.COIN_M:
            path = "/dapi/v1/exchangeInfo"
        else:
            raise ValueError(f"unsupported Binance market: {self.market}")

        response = await self.client.get(
            self.base_url + path,
        )
        response.raise_for_status()

        return any(
            item.get("symbol") == symbol
            for item in response.json().get("symbols", [])
        )

    async def order_book_ticker(self, symbol: str) -> OrderBookTicker:
        if self._is_spot_family:
            path = "/api/v3/ticker/bookTicker"
        elif self.market == Market.USDS_M:
            path = "/fapi/v1/ticker/bookTicker"
        elif self.market == Market.COIN_M:
            path = "/dapi/v1/ticker/bookTicker"
        else:
            raise ValueError(f"unsupported Binance market: {self.market}")

        response = await self.client.get(
            self.base_url + path,
            params={"symbol": symbol},
        )
        response.raise_for_status()

        payload = response.json()

        return OrderBookTicker(
            symbol=str(payload["symbol"]),
            bid_price=_d(payload["bidPrice"]),
            bid_qty=_d(payload["bidQty"]),
            ask_price=_d(payload["askPrice"]),
            ask_qty=_d(payload["askQty"]),
        )

    async def fills(
        self,
        symbol: str,
        start_time: int | None = None,
    ) -> list[ExchangeFill]:
        if self.market == Market.SPOT:
            path = "/api/v3/myTrades"
            params = {
                "symbol": symbol,
                **(
                    {"startTime": start_time}
                    if start_time is not None
                    else {}
                ),
            }

        elif self.market in (
            Market.CROSS_MARGIN,
            Market.ISOLATED_MARGIN,
        ):
            path = "/sapi/v1/margin/myTrades"
            params = {
                "symbol": symbol,
                **self._margin_params(),
                **(
                    {"startTime": start_time}
                    if start_time is not None
                    else {}
                ),
            }

        elif self.market == Market.USDS_M:
            path = "/fapi/v1/userTrades"
            params = {
                "symbol": symbol,
                **(
                    {"startTime": start_time}
                    if start_time is not None
                    else {}
                ),
            }

        elif self.market == Market.COIN_M:
            path = "/dapi/v1/userTrades"
            params = {
                "symbol": symbol,
                **(
                    {"startTime": start_time}
                    if start_time is not None
                    else {}
                ),
            }

        else:
            raise ValueError(f"unsupported Binance market: {self.market}")

        rows = await self._signed_get(path, params)

        result: list[ExchangeFill] = []

        for row in rows:
            trade_id = str(row.get("id"))
            order_id = (
                str(row["orderId"])
                if row.get("orderId") is not None
                else None
            )

            symbol_r = str(row.get("symbol", symbol))

            if self._is_spot_family:
                is_buyer = bool(row.get("isBuyer"))
            else:
                is_buyer = bool(row.get("buyer"))

            side = "BUY" if is_buyer else "SELL"

            qty = (
                row.get("qty")
                or row.get("quantity")
                or row.get("executedQty")
                or row.get("origQty")
            )

            price = (
                row.get("price")
                or row.get("p")
                or row.get("avgPrice")
            )

            quote_qty = (
                row.get("quoteQty")
                or row.get("cumQuote")
                or row.get("quoteQuantity")
                or "0"
            )

            fee = (
                row.get("commission")
                or row.get("fee")
                or row.get("realizedPnl")
                or "0"
            )

            fee_asset = (
                row.get("commissionAsset")
                or row.get("feeAsset")
            )

            time_val = (
                row.get("time")
                or row.get("transactTime")
                or row.get("updateTime")
            )

            if time_val is None:
                raise RuntimeError(
                    f"Binance fill has no timestamp: {trade_id}"
                )

            result.append(
                ExchangeFill(
                    trade_id=trade_id,
                    order_id=order_id,
                    symbol=symbol_r,
                    side=side,
                    quantity=_d(qty),
                    price=_d(price),
                    quote_quantity=_d(quote_qty),
                    fee=_d(fee),
                    fee_asset=fee_asset,
                    occurred_at=_time(time_val),
                    realized_pnl=(
                        _d(row["realizedPnl"])
                        if row.get("realizedPnl") is not None
                        else None
                    ),
                )
            )

        return result

    async def positions(self) -> list[ExchangePosition]:
        if self.market == Market.SPOT:
            # Spot holdings are balances, not futures positions.
            return []

        if self.market in (
            Market.CROSS_MARGIN,
            Market.ISOLATED_MARGIN,
        ):
            raise RuntimeError(
                "MARGIN positions require margin-account asset/debt "
                "projection and are not represented as futures positions"
            )

        if self.market == Market.USDS_M:
            rows = await self._signed_get("/fapi/v2/positionRisk")

        elif self.market == Market.COIN_M:
            rows = await self._signed_get("/dapi/v1/positionRisk")

        else:
            raise ValueError(f"unsupported Binance market: {self.market}")

        result: list[ExchangePosition] = []

        for row in rows:
            quantity = _d(row["positionAmt"])

            result.append(
                ExchangePosition(
                    symbol=str(row["symbol"]),
                    quantity=quantity,
                    entry_price=(
                        _d(row["entryPrice"])
                        if quantity
                        else None
                    ),
                    mark_price=_d(row["markPrice"]),
                    unrealized_pnl=_d(row["unRealizedProfit"]),
                )
            )

        return result

    async def funding(
        self,
        symbol: str,
        start_time: int | None = None,
    ) -> list[FundingPayment]:
        if self.market in (
            Market.SPOT,
            Market.CROSS_MARGIN,
            Market.ISOLATED_MARGIN,
        ):
            return []

        params = {
            "symbol": symbol,
            "incomeType": "FUNDING_FEE",
            **(
                {"startTime": start_time}
                if start_time is not None
                else {}
            ),
        }

        if self.market == Market.USDS_M:
            path = "/fapi/v1/income"
        elif self.market == Market.COIN_M:
            path = "/dapi/v1/income"
        else:
            raise ValueError(f"unsupported Binance market: {self.market}")

        rows = await self._signed_get(path, params)

        return [
            FundingPayment(
                event_id=str(row["tranId"]),
                symbol=str(row["symbol"]),
                amount=_d(row["income"]),
                occurred_at=_time(row["time"]),
            )
            for row in rows
        ]

    async def mark_price(self, symbol: str) -> Decimal:
        if self.market in (
            Market.SPOT,
            Market.CROSS_MARGIN,
            Market.ISOLATED_MARGIN,
        ):
            path = "/api/v3/ticker/price"

        elif self.market == Market.USDS_M:
            path = "/fapi/v1/premiumIndex"

        elif self.market == Market.COIN_M:
            path = "/dapi/v1/premiumIndex"

        else:
            raise ValueError(f"unsupported Binance market: {self.market}")

        response = await self.client.get(
            self.base_url + path,
            params={"symbol": symbol},
        )
        response.raise_for_status()

        payload = response.json()

        price_val = (
            payload.get("markPrice")
            if payload.get("markPrice") is not None
            else payload.get("price")
        )

        if price_val is None:
            raise RuntimeError(
                "unexpected mark/price payload from exchange"
            )

        return _d(price_val)

    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        *,
        price: Decimal | None = None,
        client_order_id: str | None = None,
        reduce_only: bool = False,
        stop_price: Decimal | None = None,
    ) -> dict:
        if self.market == Market.SPOT:
            path = "/api/v3/order"
            params: dict[str, object] = {
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "quantity": str(quantity),
            }

        elif self.market in (
            Market.CROSS_MARGIN,
            Market.ISOLATED_MARGIN,
        ):
            path = "/sapi/v1/margin/order"
            params = {
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "quantity": str(quantity),
                **self._margin_params(),
            }

        elif self.market == Market.USDS_M:
            path = "/fapi/v1/order"
            params = {
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "quantity": str(quantity),
            }

        elif self.market == Market.COIN_M:
            path = "/dapi/v1/order"
            params = {
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "quantity": str(quantity),
            }

        else:
            raise ValueError(f"unsupported Binance market: {self.market}")

        if price is not None:
            params["price"] = str(price)

        if order_type in ("LIMIT", "STOP", "TAKE_PROFIT"):
            params["timeInForce"] = "GTC"

        if client_order_id:
            params["newClientOrderId"] = client_order_id

        if reduce_only and self._is_futures:
            params["reduceOnly"] = "true"

        if stop_price is not None:
            params["stopPrice"] = str(stop_price)

        return await self._signed_post(path, params)

    async def open_orders(
        self,
        symbol: str | None = None,
    ) -> list[dict]:
        if self.market == Market.SPOT:
            path = "/api/v3/openOrders"
            params = {"symbol": symbol} if symbol else {}

        elif self.market in (
            Market.CROSS_MARGIN,
            Market.ISOLATED_MARGIN,
        ):
            path = "/sapi/v1/margin/openOrders"
            params = {
                **self._margin_params(),
                **({"symbol": symbol} if symbol else {}),
            }

        elif self.market == Market.USDS_M:
            path = "/fapi/v1/openOrders"
            params = {"symbol": symbol} if symbol else {}

        elif self.market == Market.COIN_M:
            path = "/dapi/v1/openOrders"
            params = {"symbol": symbol} if symbol else {}

        else:
            raise ValueError(f"unsupported Binance market: {self.market}")

        return await self._signed_get(path, params)

    async def order_status(
        self,
        symbol: str,
        *,
        order_id: str | None = None,
        client_order_id: str | None = None,
    ) -> dict:
        if not order_id and not client_order_id:
            raise ValueError(
                "order_id or client_order_id is required"
            )

        if self.market == Market.SPOT:
            path = "/api/v3/order"
            params: dict[str, object] = {"symbol": symbol}

        elif self.market in (
            Market.CROSS_MARGIN,
            Market.ISOLATED_MARGIN,
        ):
            path = "/sapi/v1/margin/order"
            params = {
                "symbol": symbol,
                **self._margin_params(),
            }

        elif self.market == Market.USDS_M:
            path = "/fapi/v1/order"
            params = {"symbol": symbol}

        elif self.market == Market.COIN_M:
            path = "/dapi/v1/order"
            params = {"symbol": symbol}

        else:
            raise ValueError(f"unsupported Binance market: {self.market}")

        if order_id:
            params["orderId"] = order_id
        else:
            params["origClientOrderId"] = client_order_id

        return await self._signed_get(path, params)
