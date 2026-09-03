from celery import Celery
from backend.app.core.config import settings

celery = Celery(
    'worker',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

@celery.task
def check_api_account(api_account_id: str):
    # Placeholder: implement real checks (connect to exchange, validate permissions)
    return {"id": api_account_id, "status": "ok"}
