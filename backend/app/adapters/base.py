from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class Market(StrEnum):
    SPOT = "spot"
    CROSS_MARGIN = "cross_margin"
    ISOLATED_MARGIN = "isolated_margin"
    USDS_M = "usds_m"
    COIN_M = "coin_m"
    ALPHA = "alpha"
    STOCKS = "stocks"


@dataclass(frozen=True)
class AccountCapabilities:
    trading_enabled: bool
    withdrawal_enabled: bool
    trusted_ip_restriction: bool


@dataclass(frozen=True)
class AccountEquity:
    equity: Decimal
    available: Decimal | None = None


@dataclass(frozen=True)
class OrderBookTicker:
    symbol: str
    bid_price: Decimal
    bid_qty: Decimal
    ask_price: Decimal
    ask_qty: Decimal


class ExchangeAdapter(ABC):
    market: Market

    @abstractmethod
    async def account_capabilities(self) -> AccountCapabilities:
        ...

    @abstractmethod
    async def account_equity(self) -> AccountEquity:
        ...

    @abstractmethod
    async def validate_symbol(self, symbol: str) -> bool:
        ...

    @abstractmethod
    async def order_book_ticker(self, symbol: str) -> OrderBookTicker:
        ...

    @abstractmethod
    async def positions(self) -> list:
        ...

    @abstractmethod
    async def mark_price(self, symbol: str) -> Decimal:
        ...

    @abstractmethod
    async def fills(
        self,
        symbol: str,
        start_time: int | None = None,
    ) -> list:
        ...

    @abstractmethod
    async def funding(
        self,
        symbol: str,
        start_time: int | None = None,
    ) -> list:
        ...

    @abstractmethod
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
        ...

    @abstractmethod
    async def open_orders(self, symbol: str | None = None) -> list[dict]:
        ...

    @abstractmethod
    async def order_status(
        self,
        symbol: str,
        *,
        order_id: str | None = None,
        client_order_id: str | None = None,
    ) -> dict:
        ...
