from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("APP_ENV", "development")
    secret_key: str = os.getenv("APP_SECRET_KEY", "")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./trading.sqlite3")
    session_timeout_minutes: int = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
    session_cookie_samesite: str = os.getenv("SESSION_COOKIE_SAMESITE", "strict").lower()
    first_run_password: str = os.getenv("FIRST_RUN_PASSWORD", "")
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    api_encryption_key: str = os.getenv("API_ENCRYPTION_KEY", "")
    trusted_outbound_ips: tuple[str, ...] = tuple(filter(None, os.getenv("TRUSTED_OUTBOUND_IPS", "").split(",")))
    cors_origins: tuple[str, ...] = tuple(filter(None, os.getenv("CORS_ORIGINS", "").split(",")))
    public_egress_ip: str = os.getenv("PUBLIC_EGRESS_IP", "")

settings = Settings()
