from .base import Market
from .binance import BinanceAdapter


class SpotAdapter(BinanceAdapter):
    def __init__(self, api_key: str, api_secret: str): super().__init__(Market.SPOT, api_key, api_secret)
class CrossMarginAdapter(BinanceAdapter):
    def __init__(self, api_key: str, api_secret: str): super().__init__(Market.CROSS_MARGIN, api_key, api_secret)
class IsolatedMarginAdapter(BinanceAdapter):
    def __init__(self, api_key: str, api_secret: str): super().__init__(Market.ISOLATED_MARGIN, api_key, api_secret)
class USDSMAdapter(BinanceAdapter):
    def __init__(self, api_key: str, api_secret: str): super().__init__(Market.USDS_M, api_key, api_secret)
class COINMAdapter(BinanceAdapter):
    def __init__(self, api_key: str, api_secret: str): super().__init__(Market.COIN_M, api_key, api_secret)
