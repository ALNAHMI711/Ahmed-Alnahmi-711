from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordRequestForm
from ..core.security import verify_password, get_password_hash
from backend.app.core.config import settings

router = APIRouter()

class LoginResponse(BaseModel):
    message: str

@router.post("/login", response_model=LoginResponse)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    # Placeholder: implement real authentication against DB
    # For now accept admin/admin as dev credentials
    if form_data.username == "admin" and form_data.password == "admin":
        # create server-side session
        user = {"username": "admin", "role": "superuser"}
        request.state.session_new = {"user": user}
        return {"message": "logged_in"}
    raise HTTPException(status_code=400, detail="Invalid credentials")

@router.post("/logout")
async def logout(request: Request):
    # signal middleware to delete session
    request.state.session_delete = True
    return {"message": "logged_out"}
