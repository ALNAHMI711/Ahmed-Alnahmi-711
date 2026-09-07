"""Cookie sessions with Argon2id hashes; no credentials are logged or returned."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from fastapi import Cookie, Depends, HTTPException, Response
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select
from backend.app.database import DbSession, SessionLocal, User
from backend.app.settings import settings
from backend.app.security.web import csrf_token
hasher=PasswordHasher()
def digest(value:str)->str:return sha256(value.encode()).hexdigest()
def bootstrap_admin(db):
    if db.scalar(select(User).limit(1)) is None and settings.first_run_password:
        db.add(User(username=settings.admin_username,password_hash=hasher.hash(settings.first_run_password),role='admin'));db.commit()
def login(username:str,password:str,response:Response)->dict:
    with SessionLocal() as db:
        bootstrap_admin(db);user=db.scalar(select(User).where(User.username==username))
        try: valid=bool(user) and hasher.verify(user.password_hash,password)
        except VerifyMismatchError: valid=False
        if not valid: raise HTTPException(401,'بيانات الدخول غير صحيحة')
        raw=token_urlsafe(32);db.add(DbSession(user_id=user.id,token_hash=digest(raw),expires_at=datetime.now(timezone.utc)+timedelta(minutes=settings.session_timeout_minutes)));db.commit()
        response.set_cookie('session',raw,httponly=True,secure=settings.environment=='production',samesite='strict',max_age=settings.session_timeout_minutes*60)
        response.set_cookie('csrf', csrf_token(), httponly=False, secure=settings.environment=='production', samesite='strict', max_age=settings.session_timeout_minutes*60)
        return {'id':user.id,'username':user.username,'role':user.role}
def current_user(session:str|None=Cookie(default=None)) -> User:
    if not session: raise HTTPException(401,'يلزم تسجيل الدخول')
    with SessionLocal() as db:
        record=db.scalar(select(DbSession).where(DbSession.token_hash==digest(session)))
        if not record or record.revoked_at or record.expires_at.replace(tzinfo=timezone.utc)<datetime.now(timezone.utc): raise HTTPException(401,'الجلسة غير صالحة أو منتهية')
        user=db.get(User,record.user_id)
        if not user: raise HTTPException(401,'الجلسة غير صالحة')
        db.expunge(user);return user
def admin(user:User=Depends(current_user))->User:
    if user.role!='admin':raise HTTPException(403,'صلاحية administrator مطلوبة')
    return user
def logout(response:Response,session:str|None=Cookie(default=None))->None:
    if session:
        with SessionLocal() as db:
            record=db.scalar(select(DbSession).where(DbSession.token_hash==digest(session)))
            if record:record.revoked_at=datetime.now(timezone.utc);db.commit()
    response.delete_cookie('session'); response.delete_cookie('csrf')
