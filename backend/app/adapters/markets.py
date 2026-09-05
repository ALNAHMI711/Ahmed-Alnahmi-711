from .base import ExchangeAdapter, Market
class SpotAdapter(ExchangeAdapter): market=Market.SPOT
class CrossMarginAdapter(ExchangeAdapter): market=Market.CROSS_MARGIN
class IsolatedMarginAdapter(ExchangeAdapter): market=Market.ISOLATED_MARGIN
class USDSMAdapter(ExchangeAdapter): market=Market.USDS_M
class COINMAdapter(ExchangeAdapter): market=Market.COIN_M
class AlphaAdapter(ExchangeAdapter): market=Market.ALPHA
class StockAdapter(ExchangeAdapter): market=Market.STOCKS
