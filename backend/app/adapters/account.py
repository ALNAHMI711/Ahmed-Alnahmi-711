from decimal import Decimal

from .base import AccountEquity, Market

class BinanceAccountMixin:
    async def _asset_usdt_price(self, asset: str) -> Decimal:
        if asset == "USDT":
            return Decimal("1")
        response = await self.client.get(self.base_url + "/api/v3/ticker/price", params={"symbol": asset + "USDT"})
        response.raise_for_status()
        return Decimal(str(response.json()["price"]))

    async def _value_balances(self, balances: list[dict]) -> tuple[Decimal, Decimal]:
        equity = Decimal("0")
        available = Decimal("0")
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
            return AccountEquity(Decimal(str(payload["totalMarginBalance"])), Decimal(str(payload["availableBalance"])), "USDT", "binance_usds_m_account")
        if self.market == Market.COIN_M:
            payload = await self._signed_get("/dapi/v1/account")
            return AccountEquity(Decimal(str(payload["totalMarginBalance"])), Decimal(str(payload["availableBalance"])), "USD", "binance_coin_m_account")
        if self.market == Market.SPOT:
            payload = await self._signed_get("/api/v3/account")
            equity, available = await self._value_balances(payload["balances"])
            return AccountEquity(equity, available, "USDT", "binance_spot_balances")
        if self.market == Market.CROSS_MARGIN:
            payload = await self._signed_get("/sapi/v1/margin/account", {"isIsolated": "FALSE"})
            btc_price = await self._asset_usdt_price("BTC")
            return AccountEquity(Decimal(str(payload["totalNetAssetOfBtc"])) * btc_price, Decimal(str(payload["totalFreeAssetOfBtc"])) * btc_price, "USDT", "binance_cross_margin_account")
        if self.market == Market.ISOLATED_MARGIN:
            payload = await self._signed_get("/sapi/v1/margin/isolated/account", {"symbols": symbol} if symbol else {})
            balances: list[dict] = []
            for account in payload.get("assets", []):
                for key in ("baseAsset", "quoteAsset"):
                    asset = account.get(key) or {}
                    balances.append({"asset": asset.get("asset", ""), "free": asset.get("netAsset", "0"), "locked": "0"})
            equity, available = await self._value_balances([row for row in balances if row["asset"]])
            return AccountEquity(equity, available, "USDT", "binance_isolated_margin_account")
        raise ValueError("equity is unavailable for this market")
