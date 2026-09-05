from backend.app.adapters.base import AccountCapabilities
from backend.app.security.guards import live_trading_allowed
def test_live_requires_ip_restriction():
 ok,_=live_trading_allowed(AccountCapabilities(True,False,False),('203.0.113.2',),'LIVE'); assert not ok
def test_withdrawal_blocks_live():
 ok,_=live_trading_allowed(AccountCapabilities(True,True,True),('203.0.113.2',),'LIVE'); assert not ok
