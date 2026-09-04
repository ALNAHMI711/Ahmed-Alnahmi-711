from fastapi import FastAPI
from .api.v1 import auth
from .db.base import Base
from .db.session import engine
from .middleware.session_middleware import SessionMiddleware

app = FastAPI(title="Ahmed Alnahmi Trading Backend")

# Register session middleware
app.add_middleware(SessionMiddleware)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])

@app.on_event("startup")
def startup():
    # create tables in dev if needed (production: use alembic migrations)
    Base.metadata.create_all(bind=engine)

@app.get("/healthz")
async def health():
    return {"status": "ok"}
