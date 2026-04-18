from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass

from fastapi import HTTPException, Request, status


@dataclass
class RateLimitRule:
    limit: int
    period: int
    scope: str


class RateLimiter:
    """In-memory sliding-window limiter keyed by scope + identity."""

    def __init__(self):
        self._usage: dict[str, deque[float]] = {}

    def allow(self, key: str, limit: int, period: int) -> bool:
        now = time.time()
        window = self._usage.setdefault(key, deque())
        while window and window[0] < now - period:
            window.popleft()
        if len(window) >= limit:
            return False
        window.append(now)
        return True

    def enforce(self, key: str, limit: int, period: int, detail: str = "Rate limit exceeded") -> None:
        if not self.allow(key, limit, period):
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)


rate_limiter = RateLimiter()


def build_client_key(request: Request, scope: str, user_id: str | None = None) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    ip = forwarded_for.split(",")[0].strip() if forwarded_for else (request.client.host if request.client else "unknown")
    identity = user_id or ip
    return f"{scope}:{identity}"

