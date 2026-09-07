from .base import ExchangeAdapter, Market
from .binance import BinanceAdapter
from .market_depth import BinanceMarketDepthMixin

class SpotAdapter(BinanceMarketDepthMixin, BinanceAdapter):
    def __init__(self, *args, **kwargs): super().__init__(Market.SPOT, *args, **kwargs)
class CrossMarginAdapter(BinanceMarketDepthMixin, BinanceAdapter):
    def __init__(self, *args, **kwargs): super().__init__(Market.CROSS_MARGIN, *args, **kwargs)
class IsolatedMarginAdapter(BinanceMarketDepthMixin, BinanceAdapter):
    def __init__(self, *args, **kwargs): super().__init__(Market.ISOLATED_MARGIN, *args, **kwargs)
class USDSMAdapter(BinanceMarketDepthMixin, BinanceAdapter):
    def __init__(self, *args, **kwargs): super().__init__(Market.USDS_M, *args, **kwargs)
class COINMAdapter(BinanceMarketDepthMixin, BinanceAdapter):
    def __init__(self, *args, **kwargs): super().__init__(Market.COIN_M, *args, **kwargs)
class AlphaAdapter(ExchangeAdapter): market=Market.ALPHA
class StockAdapter(ExchangeAdapter): market=Market.STOCKS
