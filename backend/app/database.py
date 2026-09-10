
from __future__ import annotations

from importlib import import_module

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.app.config import settings


class Base(DeclarativeBase):
    pass


def _url() -> str:
    return settings.database_url.replace("postgresql://", "postgresql+psycopg://")


engine = create_engine(_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


def init_database() -> None:
    # Explicitly register ORM modules before create_all so their tables are discovered.
    import_module("backend.app.execution.models")
    import_module("backend.app.market_data")
    Base.metadata.create_all(engine)


class KillSwitch(Base):
    __tablename__ = "kill_switches"

    # ... existing model definitions remain unchanged ...
