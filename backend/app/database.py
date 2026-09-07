"""Persistence boundary. Secrets are encrypted before ORM persistence."""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Boolean, DateTime, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from backend.app.settings import settings

class Base(DeclarativeBase): pass
class User(Base):
    __tablename__='users'; id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4())); username:Mapped[str]=mapped_column(String(120),unique=True); password_hash:Mapped[str]=mapped_column(Text); role:Mapped[str]=mapped_column(String(32),default='viewer'); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class DbSession(Base):
    __tablename__="sessions"; id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4())); user_id:Mapped[str]=mapped_column(String(36)); token_hash:Mapped[str]=mapped_column(String(64),unique=True); expires_at:Mapped[datetime]=mapped_column(DateTime); revoked_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
class ApiAccount(Base):
    __tablename__='api_accounts'; id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4())); name:Mapped[str]=mapped_column(String(120),unique=True); market:Mapped[str]=mapped_column(String(32)); encrypted_key:Mapped[str]=mapped_column(Text); encrypted_secret:Mapped[str]=mapped_column(Text); enabled:Mapped[bool]=mapped_column(Boolean,default=False); status:Mapped[str]=mapped_column(String(32),default='not_connected'); ip_restriction:Mapped[str]=mapped_column(String(32),default='unknown'); capabilities:Mapped[str]=mapped_column(Text,default='{}'); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Strategy(Base):
    __tablename__='strategies'; id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4())); name:Mapped[str]=mapped_column(String(160)); status:Mapped[str]=mapped_column(String(32),default='PENDING_REVIEW'); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Trade(Base):
    __tablename__='trades'; id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4())); market:Mapped[str]=mapped_column(String(32)); symbol:Mapped[str]=mapped_column(String(32)); status:Mapped[str]=mapped_column(String(32)); pnl:Mapped[str|None]=mapped_column(String(64),nullable=True); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class AuditLog(Base):
    __tablename__='audit_logs'; id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4())); user_id:Mapped[str|None]=mapped_column(String(36),nullable=True); ip:Mapped[str|None]=mapped_column(String(45),nullable=True); action:Mapped[str]=mapped_column(String(120)); result:Mapped[str]=mapped_column(String(32)); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

def _url()->str: return settings.database_url.replace('postgresql://','postgresql+psycopg://')
engine=create_engine(_url(), pool_pre_ping=True)
SessionLocal=sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
def init_database()->None:
    # Register execution models before create_all for development SQLite deployments.
    import backend.app.execution.models  # noqa: F401
    Base.metadata.create_all(engine)
class KillSwitch(Base):
    __tablename__='kill_switches'; id:Mapped[str]=mapped_column(String(32),primary_key=True,default='global'); enabled:Mapped[bool]=mapped_column(Boolean,default=False); updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow); updated_by:Mapped[str|None]=mapped_column(String(36),nullable=True)

class ApiAccountOwner(Base):
    __tablename__='api_account_owners'; account_id:Mapped[str]=mapped_column(String(36),ForeignKey('api_accounts.id'),primary_key=True); user_id:Mapped[str]=mapped_column(String(36),ForeignKey('users.id'),primary_key=True)
