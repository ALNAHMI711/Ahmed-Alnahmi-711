import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("APP_ENV", "development")
    secret_key: str = os.getenv("APP_SECRET_KEY", "")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./trading.sqlite3")
    session_timeout_minutes: int = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
    first_run_password: str = os.getenv("FIRST_RUN_PASSWORD", "")
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    api_encryption_key: str = os.getenv("API_ENCRYPTION_KEY", "")
    trusted_outbound_ips: tuple[str, ...] = tuple(filter(None, os.getenv("TRUSTED_OUTBOUND_IPS", "").split(",")))


settings = Settings()
