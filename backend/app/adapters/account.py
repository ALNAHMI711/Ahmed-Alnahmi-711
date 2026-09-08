from decimal import Decimal
from typing import Protocol

from .base import AccountEquity, Market


class _AccountContext(Protocol):
    client: object
    base_url: str
    market: Market

    async def _signed_get(self, path: str, params: dict[str, object] | None = None) -> object: ...


class BinanceAccountMixin(_AccountContext):
    async def _asset_usdt_price(self: "BinanceAccountMixin", asset: str) -> Decimal:
        response = await self.client.get(self.base_url + "/api/v3/ticker/price", params={"symbol": asset + "USDT"})
        response.raise_for_status()
        return Decimal(str(response.json()["price"]))

    async def _value_balances(self, balances: list[dict[str, object]]) -> tuple[Decimal, Decimal]:
        equity = Decimal(0)
        available = Decimal(0)
        for row in balances:
            asset = str(row["asset"])
            total = Decimal(str(row.get("free", "0"))) + Decimal(str(row.get("locked", "0")))
            free = Decimal(str(row.get("free", "0")))
            if total == 0:
                continue
            price = await self._asset_usdt_price(asset)
            equity += total * price
            available += free * price
        return equity, available

    async def account_equity(self, symbol: str | None = None) -> AccountEquity:
        """Return exchange-confirmed equity; valuation fails closed when a price is unavailable."""
        if self.market == Market.USDS_M:
            payload = await self._signed_get("/fapi/v2/account")
            data = payload if isinstance(payload, dict) else {}
            return AccountEquity(Decimal(str(data["totalMarginBalance"])), Decimal(str(data["availableBalance"])), "USDT", "binance_usds_m_account")
        if self.market == Market.COIN_M:
            payload = await self._signed_get("/dapi/v1/account")
            data = payload if isinstance(payload, dict) else {}
            return AccountEquity(Decimal(str(data["totalMarginBalance"])), Decimal(str(data["availableBalance"])), "USD", "binance_coin_m_account")
        if self.market == Market.SPOT:
            payload = await self._signed_get("/api/v3/account")
            data = payload if isinstance(payload, dict) else {}
            balances = data.get("balances", [])
            if not isinstance(balances, list):
                raise ValueError("invalid Binance spot balances payload")
            equity, available = await self._value_balances([row for row in balances if isinstance(row, dict)])
            return AccountEquity(equity, available, "USDT", "binance_spot_balances")
        if self.market == Market.CROSS_MARGIN:
            payload = await self._signed_get("/sapi/v1/margin/account", {"isIsolated": "FALSE"})
            data = payload if isinstance(payload, dict) else {}
            btc_price = await self._asset_usdt_price("BTC")
            return AccountEquity(Decimal(str(data["totalNetAssetOfBtc"])) * btc_price, Decimal(str(data["totalFreeAssetOfBtc"])) * btc_price, "USDT", "binance_cross_margin_account")
        if self.market == Market.ISOLATED_MARGIN:
            payload = await self._signed_get("/sapi/v1/margin/isolated/account", {"symbols": symbol} if symbol else {})
            data = payload if isinstance(payload, dict) else {}
            balances: list[dict[str, object]] = []
            assets = data.get("assets", [])
            if not isinstance(assets, list):
                raise ValueError("invalid Binance isolated margin payload")
            for account in assets:
                if not isinstance(account, dict):
                    continue
                for key in ("baseAsset", "quoteAsset"):
                    asset = account.get(key)
                    if isinstance(asset, dict):
                        balances.append({"asset": asset.get("asset", ""), "free": asset.get("netAsset", "0"), "locked": "0"})
            equity, available = await self._value_balances([row for row in balances if row["asset"]])
            return AccountEquity(equity, available, "USDT", "binance_isolated_margin_account")
        raise ValueError("equity is unavailable for this market")
