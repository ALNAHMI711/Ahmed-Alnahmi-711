from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum

class Market(StrEnum):
    SPOT="spot"; CROSS_MARGIN="cross_margin"; ISOLATED_MARGIN="isolated_margin"; USDS_M="usds_m"; COIN_M="coin_m"; ALPHA="alpha"; STOCKS="stocks"
@dataclass(frozen=True)
class AccountCapabilities:
    trading_enabled: bool
    withdrawal_enabled: bool
    trusted_ip_restriction: bool
class ExchangeAdapter(ABC):
    market: Market
    @abstractmethod
    async def account_capabilities(self) -> AccountCapabilities: ...
    @abstractmethod
    async def validate_symbol(self, symbol: str) -> bool: ...
    @abstractmethod
    async def cancel_order(self, symbol: str, *, order_id: str | None = None, client_order_id: str | None = None) -> dict: ...
