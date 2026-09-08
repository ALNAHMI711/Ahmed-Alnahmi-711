"""HTTP boundary protections: double-submit CSRF and bounded in-memory rate limits."""
from collections import defaultdict, deque
from secrets import token_urlsafe
from time import monotonic

from fastapi import HTTPException, Request

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class RateLimiter:
    def __init__(self, limit: int = 120, window_seconds: int = 60):
        self.limit, self.window, self.calls = limit, window_seconds, defaultdict(deque)

    def check(self, key: str) -> None:
        now, bucket = monotonic(), self.calls[key]
        while bucket and bucket[0] <= now - self.window:
            bucket.popleft()
        if len(bucket) >= self.limit:
            raise HTTPException(429, "rate limit exceeded")
        bucket.append(now)


def csrf_token() -> str:
    return token_urlsafe(32)


def require_csrf(request: Request) -> None:
    if request.method in SAFE_METHODS or request.url.path.endswith("/auth/login"):
        return
    cookie, header = request.cookies.get("csrf"), request.headers.get("X-CSRF-Token")
    if not cookie or not header or cookie != header:
        raise HTTPException(403, "CSRF validation failed")
