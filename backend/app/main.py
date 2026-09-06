from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Response, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from backend.app.database import ApiAccount, AuditLog, SessionLocal, User, init_database
from backend.app.security.crypto import SecretCipher
from backend.app.services.upload_scan import inspect_upload
from backend.app.security.guards import live_trading_allowed
from backend.app.adapters.base import AccountCapabilities, Market
from backend.app.adapters.binance import BinanceAdapter, BinanceApiError
from backend.app.security.auth import admin, current_user, login, logout
from backend.app.settings import settings
from signals.parser import parse
from risk.engine import RiskLimits, evaluate
ROOT=Path(__file__).parents[2]
@asynccontextmanager
async def lifecycle(_:FastAPI):
    init_database(); yield
app=FastAPI(title='Ahmed Alnahmi 711 Trading Platform',docs_url='/api/docs',lifespan=lifecycle)
if settings.cors_origins:
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_credentials=True, allow_methods=['GET','POST','DELETE'], allow_headers=['Content-Type'])
class SignalBody(BaseModel): message:str=Field(max_length=10000)
class RiskRequest(BaseModel): daily_loss:float=0; open_positions:int=0; exposure:float=0; position_size:float; leverage:float=1; spread:float=0; slippage:float=0; kill_switch:bool=False
class LoginBody(BaseModel): username:str=Field(min_length=1,max_length=120); password:str=Field(min_length=1,max_length=512)
class ApiAccountCreate(BaseModel): name:str=Field(min_length=1,max_length=120); market:str=Field(pattern='^(spot|cross_margin|isolated_margin|usds_m|coin_m|alpha|stocks)$'); api_key:str=Field(min_length=8,max_length=512); api_secret:str=Field(min_length=8,max_length=512)
@app.post('/api/v1/auth/login')
def auth_login(body:LoginBody,response:Response): return login(body.username,body.password,response)
@app.post('/api/v1/auth/logout',status_code=204)
def auth_logout(response:Response,user:User=Depends(current_user)): logout(response)
@app.get('/api/v1/auth/me')
def auth_me(user:User=Depends(current_user)): return {'id':user.id,'username':user.username,'role':user.role}
@app.get('/health')
def health(): return {'status':'ok','live_trading':'disabled_by_default'}
@app.get('/api/v1/health')
def api_health(): return health()
@app.get('/api/v1/system/public-ip')
def public_ip(user:User=Depends(admin)):
    if not settings.public_egress_ip:
        return {'status':'unavailable','reason':'لم يُضبط عنوان الخروج العام للخادم في PUBLIC_EGRESS_IP.','ip':None}
    return {'status':'available','ip':settings.public_egress_ip}
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
@app.post('/api/v1/api-accounts/{account_id}/test')
async def test_api_account(account_id:str,user:User=Depends(admin)):
    """Verify a stored key from the server; credentials never leave this boundary."""
    with SessionLocal() as db:
        account=db.get(ApiAccount,account_id)
        if not account: raise HTTPException(404,'حساب التداول غير موجود')
        try:
            cipher=SecretCipher(); adapter=BinanceAdapter(Market(account.market),cipher.decrypt(account.encrypted_key),cipher.decrypt(account.encrypted_secret))
            await adapter.test_connection(); capabilities=await adapter.account_capabilities()
        except (RuntimeError, ValueError, BinanceApiError) as error:
            account.status='connection_failed';db.add(AuditLog(user_id=user.id,action='API_CONNECTION_TEST',result='FAILED'));db.commit()
            raise HTTPException(422,str(error)) from error
        account.status='connected';account.capabilities=str({'trading_enabled':capabilities.trading_enabled,'withdrawal_enabled':capabilities.withdrawal_enabled,'trusted_ip_restriction':capabilities.trusted_ip_restriction});db.add(AuditLog(user_id=user.id,action='API_CONNECTION_TEST',result='SUCCESS'));db.commit()
    return {'status':'connected','capabilities':{'trading_enabled':capabilities.trading_enabled,'withdrawal_enabled':capabilities.withdrawal_enabled,'trusted_ip_restriction':capabilities.trusted_ip_restriction},'live_allowed':False,'reason':'لا يفعّل اختبار الاتصال التداول الحقيقي؛ يجب التحقق من IP والصلاحيات وسياسة المخاطر.'}
@app.websocket('/api/v1/ws/notifications')
async def notifications(socket:WebSocket):
    try: current_user(socket.cookies.get('session'))
    except HTTPException:
        await socket.close(code=4401);return
    await socket.accept();await socket.send_json({'message':'تم الاتصال بقناة التنبيهات الآمنة.'})
    try:
        while True: await socket.receive_text()
    except WebSocketDisconnect: pass

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
@app.post('/api/v1/kill-switch',status_code=501)
def kill_switch(user:User=Depends(admin)): raise HTTPException(501,'لا يوجد محرك تنفيذ متصل لإيقافه بأمان')
