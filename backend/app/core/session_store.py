import os
import json
import uuid
import redis
from backend.app.core.config import settings

r = redis.from_url(settings.REDIS_URL, decode_responses=True)

SESSION_PREFIX = "session:"


def create_session(data: dict, ttl_seconds: int):
    sid = str(uuid.uuid4())
    key = SESSION_PREFIX + sid
    r.set(key, json.dumps(data), ex=ttl_seconds)
    return sid


def get_session(sid: str):
    if not sid:
        return None
    key = SESSION_PREFIX + sid
    v = r.get(key)
    return json.loads(v) if v else None


def delete_session(sid: str):
    if not sid:
        return
    r.delete(SESSION_PREFIX + sid)
