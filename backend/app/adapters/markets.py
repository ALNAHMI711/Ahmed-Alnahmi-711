from .base import ExchangeAdapter, Market
from .binance import BinanceAdapter


class SpotAdapter(BinanceAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__(Market.SPOT, *args, **kwargs)


class CrossMarginAdapter(BinanceAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__(Market.CROSS_MARGIN, *args, **kwargs)


class IsolatedMarginAdapter(BinanceAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__(Market.ISOLATED_MARGIN, *args, **kwargs)


class USDSMAdapter(BinanceAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__(Market.USDS_M, *args, **kwargs)


class COINMAdapter(BinanceAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__(Market.COIN_M, *args, **kwargs)


class AlphaAdapter(ExchangeAdapter):
    market = Market.ALPHA


class StockAdapter(ExchangeAdapter):
    market = Market.STOCKS
