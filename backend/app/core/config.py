from pydantic import BaseSettings
import os

class Settings(BaseSettings):
    APP_NAME: str = "Ahmed Alnahmi Trading"
    ENVIRONMENT: str = "development"  # development أو production
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+psycopg2://app:change-me@postgres:5432/appdb")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "please-change-this")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    SESSION_TIMEOUT_MINUTES: int = 30

settings = Settings()
