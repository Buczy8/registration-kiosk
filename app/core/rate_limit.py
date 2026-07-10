from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock
from time import monotonic

from fastapi import HTTPException, status


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            # Periodically prune empty/expired deques to prevent memory leaks (DoS)
            if len(self._hits) > 1000:
                to_remove = []
                for k, v in self._hits.items():
                    while v and v[0] <= cutoff:
                        v.popleft()
                    if not v:
                        to_remove.append(k)
                for k in to_remove:
                    self._hits.pop(k, None)

            bucket = self._hits[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many login attempts. Try again later.",
                )
            bucket.append(now)


def build_rate_limit_key(*parts: str, normalizer: Callable[[str], str] | None = None) -> str:
    sanitize = normalizer or (lambda item: item.strip().lower())
    return ":".join(sanitize(part) for part in parts if part)
