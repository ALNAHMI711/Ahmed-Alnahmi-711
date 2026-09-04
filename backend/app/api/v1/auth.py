from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.db.session import get_db
from backend.app.db.models.audit_log import AuditLog
from backend.app.db.models.user import User

router = APIRouter()

class LoginResponse(BaseModel):
    message: str

@router.post("/login", response_model=LoginResponse)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Placeholder: implement real authentication against DB
    # For now accept admin/admin as dev credentials
    if form_data.username == "admin" and form_data.password == "admin":
        # attempt to resolve user id if exists
        user_obj = db.query(User).filter(User.username == form_data.username).first()
        user_id = getattr(user_obj, 'id', None)
        # create server-side session
        user = {"username": "admin", "role": "superuser"}
        request.state.session_new = {"user": user}
        # write audit log
        try:
            audit = AuditLog(user_id=user_id, ip=request.client.host if request.client else None, action="LOGIN", result="SUCCESS")
            db.add(audit)
            db.commit()
        except Exception:
            db.rollback()
        return {"message": "logged_in"}
    raise HTTPException(status_code=400, detail="Invalid credentials")

@router.post("/logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    # signal middleware to delete session
    # attempt to extract user_id from session if present
    user_id = None
    if getattr(request.state, 'session', None):
        user = request.state.session.get('user')
        if user:
            # if session stored username, try to find user id
            user_obj = db.query(User).filter(User.username == user.get('username')).first()
            user_id = getattr(user_obj, 'id', None)
    request.state.session_delete = True
    try:
        audit = AuditLog(user_id=user_id, ip=request.client.host if request.client else None, action="LOGOUT", result="SUCCESS")
        db.add(audit)
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "logged_out"}
