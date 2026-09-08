"""Production boundary for manual orders; secrets never leave this module."""

from decimal import Decimal

import httpx
from fastapi import HTTPException
from sqlalchemy import select

from backend.app.adapters.base import Market
from backend.app.adapters.binance import BinanceAdapter
from backend.app.database import ApiAccount, ApiAccountOwner, KillSwitch
from backend.app.execution.models import ExchangeOrder
from backend.app.execution.orders import (
    ExecutionRejected,
    ExecutionService,
    OrderIntent,
)
from backend.app.execution.repositories import OrderRepository
from backend.app.security.crypto import SecretCipher
from risk.engine import RiskLimits, evaluate


async def submit_manual(db, user, body):
    account=db.get(ApiAccount, body.account_id)
    owned=db.scalar(select(ApiAccountOwner).where(ApiAccountOwner.account_id==body.account_id,ApiAccountOwner.user_id==user.id))
    if not account or (user.role != 'admin' and not owned): raise HTTPException(404,'account not found')
    if not account.enabled: raise HTTPException(409,'account disabled')
    if db.get(KillSwitch,'global') and db.get(KillSwitch,'global').enabled: raise HTTPException(423,'kill switch enabled')
    existing=OrderRepository(db).by_request(body.account_id,body.client_request_id)
    if existing: return {'id':existing.id,'status':existing.status,'exchange_order_id':existing.exchange_order_id}
    try: market=Market(account.market); adapter=BinanceAdapter(market,SecretCipher().decrypt(account.encrypted_key),SecretCipher().decrypt(account.encrypted_secret))
    except (ValueError,RuntimeError) as error: raise HTTPException(503,str(error))
    if not await adapter.validate_symbol(body.symbol): raise HTTPException(422,'invalid Binance symbol')
    decision=evaluate(RiskLimits(100,.2,3,1000,500,3,.002,.003),daily_loss=body.daily_loss,open_positions=body.open_positions,exposure=body.exposure,position_size=float(body.quantity),leverage=body.leverage,spread=body.spread,slippage=body.slippage,kill_switch=False)
    order=ExchangeOrder(account_id=body.account_id,market=account.market,symbol=body.symbol,client_request_id=body.client_request_id,side=body.side,order_type=body.order_type,quantity=Decimal(str(body.quantity)))
    OrderRepository(db).create_once(order); db.commit()
    try: remote=await ExecutionService().submit(adapter,OrderIntent(body.account_id,body.client_request_id,body.symbol,body.side,Decimal(str(body.quantity)),body.order_type),decision,confirmed=body.confirmed,kill_switch=False)
    except ExecutionRejected as error: order.status='REJECTED'; db.commit(); raise HTTPException(409,str(error))
    except (httpx.HTTPError, ValueError, KeyError, TypeError, RuntimeError) as error: db.rollback(); raise HTTPException(502,str(error))
    order.exchange_order_id=str(remote.get('orderId')); order.status=remote['status']; db.commit(); return {'id':order.id,'status':order.status,'exchange_order_id':order.exchange_order_id}
