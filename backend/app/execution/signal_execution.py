"""Signals are normalized into the same owned-account manual execution boundary."""

from types import SimpleNamespace

from backend.app.database import AuditLog
from signals.parser import parse

from .manual import submit_manual


async def submit_signal(db, user, *, account_id: str, client_request_id: str, message: str, confirmed: bool, policy_enabled: bool, risk: dict):
    signal=parse(message)
    if not policy_enabled: raise ValueError('signal auto-execution is disabled')
    # Parser output is normalized; it never receives exchange credentials.
    body=SimpleNamespace(account_id=account_id,client_request_id=client_request_id,symbol=signal.symbol,side=signal.side,quantity=risk['quantity'],order_type='MARKET',confirmed=confirmed,daily_loss=risk.get('daily_loss',0),open_positions=risk.get('open_positions',0),exposure=risk.get('exposure',0),leverage=risk.get('leverage',1),spread=risk.get('spread',0),slippage=risk.get('slippage',0))
    result = await submit_manual(db,user,body)
    db.add(AuditLog(user_id=user.id, action='SIGNAL_EXECUTION', result='SUCCESS')); db.commit()
    return result
