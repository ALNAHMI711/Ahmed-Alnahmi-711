from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
from backend.app.core.session_store import get_session, create_session, delete_session
from backend.app.core.config import settings

SESSION_COOKIE_NAME = "ah_session"

class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        sid = request.cookies.get(SESSION_COOKIE_NAME)
        request.state.session = get_session(sid) if sid else None
        response: Response = await call_next(request)
        # If endpoint set request.state.session_new, create cookie
        if getattr(request.state, "session_new", None):
            new_sid = create_session(request.state.session_new, settings.SESSION_TIMEOUT_MINUTES * 60)
            # Use ENVIRONMENT to determine secure cookie behavior
            is_prod = getattr(settings, "ENVIRONMENT", "development").lower() == "production"
            response.set_cookie(
                key=SESSION_COOKIE_NAME,
                value=new_sid,
                httponly=True,
                secure=is_prod,  # True فقط في الإنتاج مع TLS
                samesite="Strict",
                max_age=settings.SESSION_TIMEOUT_MINUTES * 60,
            )
        # If endpoint requested session_delete
        if getattr(request.state, "session_delete", False):
            sid_to_delete = request.cookies.get(SESSION_COOKIE_NAME)
            if sid_to_delete:
                delete_session(sid_to_delete)
                response.delete_cookie(SESSION_COOKIE_NAME)
        return response
