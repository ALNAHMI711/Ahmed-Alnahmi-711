from types import SimpleNamespace

from fastapi import HTTPException

from backend.app.adapters.base import AccountCapabilities
from backend.app.security.guards import live_trading_allowed
from backend.app.security.web import RateLimiter, require_csrf


def test_live_requires_ip_restriction():
 ok,_=live_trading_allowed(AccountCapabilities(True,False,False),('203.0.113.2',),'LIVE'); assert not ok
def test_withdrawal_blocks_live():
 ok,_=live_trading_allowed(AccountCapabilities(True,True,True),('203.0.113.2',),'LIVE'); assert not ok

def test_rate_limiter_blocks_after_limit():
 limiter=RateLimiter(limit=1,window_seconds=60); limiter.check('client')
 try: limiter.check('client')
 except HTTPException as error: assert error.status_code==429
 else: assert False

def test_csrf_rejects_mutating_request_without_matching_token():
 request=SimpleNamespace(method='POST',url=SimpleNamespace(path='/api/v1/risk/evaluate'),cookies={'csrf':'one'},headers={'X-CSRF-Token':'two'})
 try: require_csrf(request)
 except HTTPException as error: assert error.status_code==403
 else: assert False
