from contextlib import asynccontextmanager
import asyncio
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Response, UploadFile, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from backend.app.database import ApiAccount, AuditLog, KillSwitch, SessionLocal, User, init_database
from backend.app.security.crypto import SecretCipher
from backend.app.services.upload_scan import inspect_upload
from backend.app.security.guards import live_trading_allowed
from backend.app.adapters.base import AccountCapabilities
from backend.app.security.auth import admin, current_user, login, logout
from backend.app.websocket import WebSocketDispatcher
from backend.app.execution.manual import submit_manual
from backend.app.execution.signal_execution import submit_signal
from backend.app.security.web import RateLimiter, require_csrf
from signals.parser import parse
from risk.engine import RiskLimits, evaluate
ROOT=Path(__file__).parents[2]
@asynccontextmanager
async def lifecycle(_:FastAPI):
    init_database(); yield
app=FastAPI(title='Ahmed Alnahmi 711 Trading Platform',docs_url='/api/docs',lifespan=lifecycle)
rate_limiter = RateLimiter()
@app.middleware('http')
async def security_headers(request: Request, call_next):
    try:
        rate_limiter.check(request.client.host if request.client else 'unknown')
        require_csrf(request)
        response = await call_next(request)
    except HTTPException as error:
        response = Response(error.detail, status_code=error.status_code)
    response.headers['Content-Security-Policy'] = "default-src 'self'; frame-ancestors 'none'; base-uri 'self'"
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response
class SignalBody(BaseModel): message:str=Field(max_length=10000)
class RiskRequest(BaseModel): daily_loss:float=0; open_positions:int=0; exposure:float=0; position_size:float; leverage:float=1; spread:float=0; slippage:float=0; kill_switch:bool=False
class LoginBody(BaseModel): username:str=Field(min_length=1,max_length=120); password:str=Field(min_length=1,max_length=512)
class ManualOrder(BaseModel):
    account_id:str; client_request_id:str=Field(min_length=8,max_length=64); symbol:str=Field(pattern='^[A-Z0-9]{3,32}$'); side:str=Field(pattern='^(BUY|SELL)$'); quantity:float=Field(gt=0); order_type:str=Field(default='MARKET',pattern='^(MARKET|LIMIT)$'); confirmed:bool=False; daily_loss:float=0; open_positions:int=0; exposure:float=0; leverage:float=1; spread:float=0; slippage:float=0
class SignalExecution(BaseModel):
    account_id:str; client_request_id:str; message:str=Field(max_length=10000); confirmed:bool=False; policy_enabled:bool=False; quantity:float=Field(gt=0); daily_loss:float=0; open_positions:int=0; exposure:float=0; leverage:float=1; spread:float=0; slippage:float=0
class ApiAccountCreate(BaseModel): name:str=Field(min_length=1,max_length=120); market:str=Field(pattern='^(spot|cross_margin|isolated_margin|usds_m|coin_m|alpha|stocks)$'); api_key:str=Field(min_length=8,max_length=512); api_secret:str=Field(min_length=8,max_length=512)
@app.post('/api/v1/auth/login')
def auth_login(body:LoginBody,response:Response): return login(body.username,body.password,response)
@app.post('/api/v1/auth/logout',status_code=204)
def auth_logout(response:Response,user:User=Depends(current_user)): logout(response)
@app.get('/api/v1/auth/me')
def auth_me(user:User=Depends(current_user)): return {'id':user.id,'username':user.username,'role':user.role}
@app.get('/health')
def health(): return {'status':'ok','live_trading':'disabled_by_default'}
@app.get('/')
def dashboard(): return FileResponse(ROOT/'frontend'/'dist'/'index.html') if (ROOT/'frontend'/'dist'/'index.html').exists() else FileResponse(ROOT/'frontend'/'index.html')
@app.post('/api/v1/signals/parse')
def parse_signal(body:SignalBody):
    try:return parse(body.message).__dict__
    except ValueError as error:raise HTTPException(422,str(error))
@app.post('/api/v1/strategies/scan')
async def scan_strategy(file:UploadFile,user:User=Depends(admin)):return inspect_upload(file.filename or '',await file.read())
@app.post('/api/v1/risk/evaluate')
def risk_check(body:RiskRequest,user:User=Depends(current_user)):return evaluate(RiskLimits(100,.2,3,1000,500,3,.002,.003),**body.model_dump()).__dict__
@app.get('/api/v1/live-readiness')
def live_readiness(user:User=Depends(current_user)):
    allowed,reason=live_trading_allowed(AccountCapabilities(True,False,False),(),'LIVE');return {'allowed':allowed,'reason':reason}
@app.get('/api/v1/api-accounts')
def list_api_accounts(user:User=Depends(current_user)):
    with SessionLocal() as db:return [{'id':a.id,'name':a.name,'market':a.market,'enabled':a.enabled,'status':a.status,'ip_restriction':a.ip_restriction,'capabilities':a.capabilities,'last_check':None} for a in db.scalars(select(ApiAccount)).all()]
@app.post('/api/v1/api-accounts',status_code=201)
def create_api_account(account:ApiAccountCreate,user:User=Depends(admin)):
    try:cipher=SecretCipher()
    except RuntimeError as error:raise HTTPException(503,str(error))
    with SessionLocal() as db:
        if db.scalar(select(ApiAccount).where(ApiAccount.name==account.name)):raise HTTPException(409,'اسم الحساب مستخدم بالفعل')
        db.add(ApiAccount(name=account.name,market=account.market,encrypted_key=cipher.encrypt(account.api_key),encrypted_secret=cipher.encrypt(account.api_secret)))
        db.add(AuditLog(action='API_ADD',result='SUCCESS'));db.commit()
    return {'status':'saved','message':'حُفظ المفتاح مشفرًا ولن يُعرض السر مرة أخرى.'}
dispatcher = WebSocketDispatcher()
@app.websocket('/api/v1/ws/notifications')
async def notifications(socket: WebSocket):
    connection = await dispatcher.connect(socket)
    if connection is None: return
    try:
        while True:
            try:
                message = await asyncio.wait_for(socket.receive_json(), timeout=30)
            except TimeoutError:
                # Revalidate idle connections too, so expired/revoked sessions close.
                message = {'action': 'ping'}
            response = await dispatcher.dispatch(message, connection)
            if response is not None: await socket.send_json(response)
            else: return
    except WebSocketDisconnect:
        dispatcher._connections.discard(connection)

@app.post('/api/v1/signals/execute',status_code=201)
async def execute_signal(body: SignalExecution, user: User = Depends(current_user)):
    try:
        with SessionLocal() as db: return await submit_signal(db,user,account_id=body.account_id,client_request_id=body.client_request_id,message=body.message,confirmed=body.confirmed,policy_enabled=body.policy_enabled,risk=body.model_dump())
    except ValueError as error: raise HTTPException(422,str(error))
@app.post('/api/v1/orders/manual',status_code=201)
async def manual_order(body: ManualOrder, user: User = Depends(current_user)):
    with SessionLocal() as db: return await submit_manual(db, user, body)
@app.get('/api/v1/portfolio')
def portfolio(user:User=Depends(current_user)): return {'status':'unavailable','reason':'لا يوجد حساب تداول متصل يوفّر بيانات محفظة حالياً','data':None}
@app.get('/api/v1/positions')
def positions(user:User=Depends(current_user)): return {'status':'unavailable','reason':'لا توجد بيانات مراكز من موصل تداول متصل','data':[]}
@app.get('/api/v1/orders')
def orders(user:User=Depends(current_user)): return {'status':'unavailable','reason':'لا توجد بيانات أوامر من موصل تداول متصل','data':[]}
@app.get('/api/v1/market-data')
def market_data(user:User=Depends(current_user)): return {'status':'unavailable','reason':'اتصال السوق غير متاح','data':[]}
@app.get('/api/v1/alpha/snapshot')
def alpha_snapshot(user:User=Depends(current_user)): return {'status':'unavailable','reason':'لا توجد نتيجة Alpha تشغيلية مسجلة','data':None}
@app.post('/api/v1/kill-switch')
def kill_switch(enabled: bool, user: User = Depends(admin)):
    with SessionLocal() as db:
        state = db.get(KillSwitch, 'global') or KillSwitch(id='global')
        state.enabled, state.updated_by = enabled, user.id
        db.add(state); db.add(AuditLog(user_id=user.id, action='KILL_SWITCH_ON' if enabled else 'KILL_SWITCH_OFF', result='SUCCESS')); db.commit()
    return {'enabled': enabled, 'message': 'يمنع أو يسمح بالأوامر الجديدة فقط؛ لا يغلق المراكز تلقائيًا.'}
